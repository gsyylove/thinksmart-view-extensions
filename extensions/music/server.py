"""Loopback-only QQ Music account verification service."""
import asyncio
from contextlib import suppress
import os
from pathlib import Path
import time
import traceback
import re
from html import unescape

from aiohttp import web
from qqmusic_api import Client, Credential
from qqmusic_api.models.login import QRLoginType
from qqmusic_api.modules.song import SongFileInfo, SongFileType

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / 'thinksmart-music/state'
STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chmod(STATE, 0o700)
CREDENTIAL = STATE / 'credential.json'
ORIGINS = {'http://127.0.0.1:8090', 'http://127.0.0.1:8091'}


@web.middleware
async def local_only(request, handler):
    if request.host not in {'127.0.0.1:8091', 'localhost:8091'}:
        raise web.HTTPForbidden()
    origin = request.headers.get('Origin')
    if origin and origin not in ORIGINS:
        raise web.HTTPForbidden()
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException:
            raise
        except Exception as error:
            # Upstream messages may contain authorization parameters.
            response = web.json_response({'error': '请求失败，请稍后重试', 'type': type(error).__name__}, status=502)
    response.headers['Cache-Control'] = 'no-store'
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


async def create_app():
    client = Client(device_path=str(STATE / 'device.json'))
    await client.__aenter__()
    if CREDENTIAL.exists():
        client.credential = Credential.model_validate_json(CREDENTIAL.read_text())
    state = {'status': 'logged_in' if client.credential.musicid else 'idle', 'message': ''}
    qr = None
    task = None
    lock = asyncio.Lock()
    songs = {}
    lyrics_cache = {}
    pending_commands = {}
    command_number = 0
    browser_seen = 0
    command_lock = asyncio.Lock()
    app = web.Application(middlewares=[local_only])

    async def watch(code):
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                result = await asyncio.wait_for(client.login.check_qrcode(code), 25)
                if result.done and result.credential:
                    temporary = STATE / 'credential.tmp'
                    with open(temporary, 'w', opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
                        output.write(result.credential.model_dump_json())
                    temporary.replace(CREDENTIAL)
                    client.credential = result.credential
                    state.update(status='logged_in', message='登录成功，可以读取歌单')
                    return
                name = result.event.name
                state.update(status=name.lower(), message={'SCAN': '请扫码', 'CONF': '已扫码，请在手机确认',
                             'TIMEOUT': '二维码已过期，请重新获取', 'REFUSE': '已取消授权'}.get(name, '等待授权'))
                if name in {'TIMEOUT', 'REFUSE'}:
                    return
                await asyncio.sleep(2)
            state.update(status='timeout', message='二维码已过期，请重新获取')
        except asyncio.CancelledError:
            raise
        except Exception as error:
            frames = [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)]
            (STATE / 'login-error.json').write_text(__import__('json').dumps(
                {'type': type(error).__name__, 'frames': frames}))
            state.update(status='error', message=f'登录检查失败（{type(error).__name__}），请重新获取二维码')

    async def start(request):
        nonlocal qr, task
        body = await request.json()
        kind = {'qq': QRLoginType.QQ, 'wx': QRLoginType.WX}.get(body.get('kind'))
        if kind is None:
            raise web.HTTPBadRequest()
        async with lock:
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            state.update(status='loading', message='正在获取二维码')
            try:
                qr = await asyncio.wait_for(client.login.get_qrcode(kind), 30)
            except Exception:
                state.update(status='error', message='二维码获取失败，请重试')
                raise
            state.update(status='scan', message='请用手机QQ扫码' if kind == QRLoginType.QQ else '请用微信扫码')
            task = asyncio.create_task(watch(qr))
            return web.json_response({'ok': True})

    async def qr_image(_request):
        if qr is None:
            raise web.HTTPNotFound()
        return web.Response(body=qr.data, content_type=qr.mimetype)

    async def status(_request):
        return web.json_response(state)

    async def playlists(_request):
        if not client.credential.musicid:
            return web.json_response({'error': '请先扫码登录'}, status=401)
        result = await asyncio.wait_for(client.user.get_created_songlist(client.credential.musicid), 25)
        # Return only playlist fields. Never serialize the entire SDK/client object.
        return web.json_response({'playlists': [{'id': item.id, 'title': item.title,
                                                'count': item.songnum, 'dirid': item.dirid} for item in result.playlists]})

    async def song_list(request):
        if not client.credential.musicid:
            raise web.HTTPUnauthorized()
        try:
            playlist_id = int(request.query.get('id', '0'))
            directory_id = int(request.query.get('dirid', '0'))
            page = int(request.query.get('page', '1'))
            if playlist_id < 0 or directory_id < 0 or page < 1:
                raise ValueError()
        except ValueError:
            raise web.HTTPBadRequest()
        result = await asyncio.wait_for(client.songlist.get_detail(playlist_id, dirid=directory_id, num=30, page=page), 25)
        output = []
        for song in result.songs:
            songs[song.mid] = song
            output.append({'mid': song.mid, 'title': song.title or song.name,
                           'singer': ' / '.join(item.name for item in song.singer), 'duration': song.interval,
                           'membership': bool(song.pay.pay_month or song.pay.pay_play)})
        return web.json_response({'songs': output, 'total': result.total, 'page': page})

    async def feed(request):
        kind = request.query.get('kind', 'hot')
        if kind not in {'hot', 'recommend'}:
            raise web.HTTPBadRequest()
        if not client.credential.musicid:
            return web.json_response({'error': '请先扫码登录音乐账号'}, status=401)

        async def fetch_feed():
            if kind == 'recommend':
                result = await client.recommend.get_guess_recommend()
                return result.songs, '猜你喜欢'
            categories = await client.top.get_category()
            chart = next((item for group in categories.group for item in group.toplist
                          if item.name == '热歌榜'), None)
            if chart is None:
                raise ValueError('Hot chart unavailable')
            result = await client.top.get_detail(chart.id, num=100, page=1)
            return result.songs, chart.name

        selected, title = await asyncio.wait_for(fetch_feed(), 25)
        output = []
        seen = set()
        for song in selected:
            if not song.mid or song.mid in seen:
                continue
            seen.add(song.mid)
            songs[song.mid] = song
            output.append({'mid': song.mid, 'title': song.title or song.name,
                           'singer': ' / '.join(item.name for item in song.singer), 'duration': song.interval})
        if not output:
            return web.json_response({'error': '暂时没有获取到歌曲，请稍后重试'}, status=502)
        return web.json_response({'songs': output, 'title': title})

    async def play_url(request):
        body = await request.json()
        mid = body.get('mid', '')
        song = songs.get(mid)
        if song is None:
            return web.json_response({'error': '请先从歌单选择歌曲'}, status=400)
        result = await asyncio.wait_for(client.song.get_song_urls(
            [SongFileInfo(mid=mid)], file_type=SongFileType.MP3_320), 25)
        info = next((item for item in result.data if item.mid == mid), None)
        if info is None or not info.purl or info.result != 0:
            return web.json_response({'error': '账号暂无此音质的播放权限，或歌曲暂不可用'}, status=403)
        cdn = await asyncio.wait_for(client.song.get_cdn_dispatch(), 15)
        domain = next((item for item in cdn.sip if item.startswith('https://')), None)
        if domain is None:
            domain = next((item for item in cdn.sip if item.startswith('http://')), None)
        if not domain or info.purl.startswith(('http:', 'https:', '//')):
            return web.json_response({'error': '播放地址暂不可用'}, status=502)
        url = domain.rstrip('/') + '/' + info.purl.lstrip('/')
        return web.json_response({'url': url, 'title': song.title or song.name, 'duration': song.interval,
                                  'mid': mid, 'singer': ' / '.join(item.name for item in song.singer),
                                  'cover': f'https://y.gtimg.cn/music/photo_new/T002R500x500M000{song.album.mid}.jpg'
                                  if re.fullmatch(r'[A-Za-z0-9]+', song.album.mid or '') else '',
                                  'quality': 'MP3 320kbps'})

    async def lyrics(request):
        mid = request.query.get('mid', '')
        if mid not in songs:
            raise web.HTTPBadRequest()
        if mid not in lyrics_cache:
            result = await asyncio.wait_for(client.lyric.get_lyric(mid), 25)
            lines = []
            raw = unescape(result.lyric or '')
            offset = re.search(r'\[offset:([+-]?\d+)\]', raw)
            adjustment = int(offset[1]) / 1000 if offset else 0
            for row in raw.splitlines():
                stamps = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', row)
                text = re.sub(r'\[[^\]]*\]', '', row).strip()
                if not text:
                    continue
                for minute, second in stamps:
                    lines.append({'time': max(0, int(minute) * 60 + float(second) - adjustment), 'text': text})
            lyrics_cache[mid] = sorted(lines, key=lambda item: item['time'])
        return web.json_response({'lines': lyrics_cache[mid]})

    async def search(request):
        body = await request.json()
        query = body.get('query', '')
        title = body.get('title', '')
        singer = body.get('singer', '')
        if not all(isinstance(value, str) and len(value) <= 80 for value in (query, title, singer)) or not query.strip():
            raise web.HTTPBadRequest()
        if not client.credential.musicid:
            return web.json_response({'error': '请先扫码登录音乐账号'}, status=401)
        result = await asyncio.wait_for(client.search.search_by_type(query, num=20, highlight=False), 20)
        normalize = lambda value: re.sub(r'[\W_]+', '', value).casefold()
        wanted_title, wanted_singer = normalize(title), normalize(singer)
        found = []
        exact = []
        for song in result.song:
            songs[song.mid] = song
            artist_names = [normalize(item.name) for item in song.singer]
            title_match = bool(wanted_title) and wanted_title in {normalize(song.title), normalize(song.name)}
            artist_match = bool(wanted_singer) and wanted_singer in artist_names
            score = (100 if title_match else 0) + (80 if artist_match else 0)
            if re.search(r'live|伴奏|翻唱|纯音乐|remix|加速|dj', song.title or song.name, re.I):
                score -= 10
            item = {'mid': song.mid, 'title': song.title or song.name,
                    'singer': ' / '.join(person.name for person in song.singer), 'duration': song.interval,
                    'score': score}
            found.append(item)
            if (title_match and (not wanted_singer or artist_match)) or (not wanted_title and artist_match):
                exact.append(item)
        found.sort(key=lambda item: item['score'], reverse=True)
        exact.sort(key=lambda item: item['score'], reverse=True)
        auto_mid = None
        if exact and (wanted_singer or len({normalize(item['singer']) for item in exact}) == 1):
            auto_mid = exact[0]['mid']
        return web.json_response({'songs': found, 'auto_mid': auto_mid})

    async def commands(_request):
        nonlocal browser_seen
        browser_seen = time.monotonic()
        return web.json_response({'commands': [item['command'] for item in pending_commands.values()
                                               if not item['future'].done()]})

    async def acknowledge(request):
        body = await request.json()
        item = pending_commands.get(body.get('id'))
        if item and not item['future'].done():
            item['future'].set_result({'ok': body.get('ok') is True, 'message': str(body.get('message', ''))[:120]})
        return web.json_response({'ok': True})

    async def control(request):
        nonlocal command_number
        body = await request.json()
        action = body.get('action')
        if action not in {'open', 'play', 'pause', 'resume', 'stop', 'next', 'previous', 'search', 'hot', 'shuffle', 'playlist', 'recommend'}:
            raise web.HTTPBadRequest()
        if time.monotonic() - browser_seen > 5:
            return web.json_response({'ok': False, 'message': '音乐页面还没连接，请先打开设备首页'})
        async with command_lock:
            command_number += 1
            key = f'{time.time_ns()}-{command_number}'
            future = asyncio.get_running_loop().create_future()
            timeout = 75 if action in {'search', 'play', 'hot', 'shuffle', 'playlist', 'recommend'} else 30
            command = {'id': key, 'action': action, 'expires': time.time() + timeout}
            if action == 'search':
                for name in ('query', 'title', 'singer'):
                    value = body.get(name, '')
                    if not isinstance(value, str) or len(value) > 80:
                        raise web.HTTPBadRequest()
                    command[name] = value
            pending_commands[key] = {'command': command, 'future': future}
            try:
                return web.json_response(await asyncio.wait_for(future, timeout))
            except asyncio.TimeoutError:
                return web.json_response({'ok': False, 'message': '音乐操作超时，请再试一次'})
            finally:
                pending_commands.pop(key, None)

    async def cleanup(_app):
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await client.__aexit__(None, None, None)

    app.router.add_post('/api/qr', start)
    app.router.add_get('/api/qr.png', qr_image)
    app.router.add_get('/api/status', status)
    app.router.add_get('/api/playlists', playlists)
    app.router.add_get('/api/songs', song_list)
    app.router.add_get('/api/feed', feed)
    app.router.add_post('/api/play', play_url)
    app.router.add_get('/api/lyrics', lyrics)
    app.router.add_post('/api/search', search)
    app.router.add_get('/api/commands', commands)
    app.router.add_post('/api/ack', acknowledge)
    app.router.add_post('/api/control', control)
    app.router.add_get('/music.js', lambda _: web.FileResponse(ROOT / 'music.js'))
    app.router.add_get('/music.css', lambda _: web.FileResponse(ROOT / 'music.css'))
    app.router.add_route('OPTIONS', '/{path:.*}', lambda _: web.Response())
    app.on_cleanup.append(cleanup)
    return app


if __name__ == '__main__':
    web.run_app(create_app(), host='127.0.0.1', port=8091, access_log=None, print=None)
