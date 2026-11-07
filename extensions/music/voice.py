"""Exact local music commands, handled before the hub's model routing."""
import json
from pathlib import Path
import re

import aiohttp

COMMANDS = {
    '打开音乐': 'open', '打开播放器': 'open', '打开音乐播放器': 'open', '打开QQ音乐': 'open',
    '播放音乐': 'play', '放音乐': 'play', '放首歌': 'play', '放一首歌': 'play', '播放歌曲': 'play',
    '播放热门音乐': 'hot', '播放热门歌曲': 'hot', '播放热歌榜': 'hot', '播放热歌': 'hot',
    '播放随机音乐': 'shuffle', '我想听随机音乐': 'shuffle', '随机播放歌曲': 'shuffle',
    '随机播放音乐': 'shuffle', '随机播放': 'shuffle', '随机放歌': 'shuffle',
    '随便放点歌': 'shuffle', '随便放首歌': 'shuffle', '随便放一首歌': 'shuffle',
    '播放我的歌单': 'playlist', '播放歌单': 'playlist',
    '播放推荐音乐': 'recommend', '播放推荐歌曲': 'recommend', '播放猜你喜欢': 'recommend',
    '暂停': 'pause', '暂停音乐': 'pause', '暂停播放': 'pause',
    '继续': 'resume', '继续音乐': 'resume', '继续播放': 'resume', '继续播放音乐': 'resume',
    '停止音乐': 'stop', '停止播放音乐': 'stop', '停止播放': 'stop',
    '下一首': 'next', '下一首歌': 'next', '切下一首': 'next', '换一首': 'next', '换首歌': 'next',
    '上一首': 'previous', '上一首歌': 'previous', '切上一首': 'previous',
}


def recognize(text):
    normalized = re.sub(r'[\s，。！？、,.!?：:]', '', text or '')
    normalized = re.sub(r'^(?:小麦小麦|小麦同学|哈喽小麦)', '', normalized)
    normalized = re.sub(r'^(?:请帮我|麻烦帮我|帮我|请)', '', normalized)
    normalized = re.sub(r'(?:一下|吧)$', '', normalized)
    return COMMANDS.get(normalized)


def request_for(text):
    action = recognize(text)
    if action:
        return {'action': action}
    value = re.sub(r'^(?:小麦小麦|小麦同学|哈喽小麦)[\s，,]*', '', (text or '').strip())
    value = re.sub(r'^(?:请帮我|麻烦帮我|帮我|请)', '', value)
    if re.search(r'[？?]|(?:为什么|怎么|如何|能否|是不是|有什么|什么意思)', value):
        return None
    match = re.fullmatch(r'(?:播放歌曲|播放一首|播放|放一首|放首|我想听一首|我想听|想听|听一首)\s*(.{1,80}?)[。！!]*', value)
    if not match:
        return None
    query = match[1].strip(' 《》「」“”"')
    if re.match(r'(?:你(?:讲|说|介绍|解释)|(?:一个|一段|一则)?(?:故事|笑话|新闻|天气))', query):
        return None
    if not query or query in {'歌', '歌曲', '音乐', '一首歌'}:
        return {'action': 'play'}
    singer = ''
    title = query
    singer_only = re.fullmatch(r'(.{1,30})的(?:歌|歌曲|音乐)', query)
    if singer_only:
        singer, title = singer_only[1], ''
    elif not match[1].strip().startswith(('《', '「', '“', '"')) and '的' in query and len(query.split('的', 1)[0]) >= 2:
        singer, title = query.split('的', 1)
        title = title.strip(' 《》「」“”"')
    return {'action': 'search', 'query': f'{singer} {title}'.strip(), 'title': title, 'singer': singer}


async def handle(conn, text):
    command = request_for(text)
    if not command:
        return False
    try:
        config = json.loads((Path.home() / '.config/thinksmart-client/config.json').read_text())
        if not config.get('device_id') or conn.headers.get('device-id') != config['device_id']:
            return False
    except (OSError, ValueError):
        return False
    from core.agent import clear_command
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=80)) as session:
            async with session.post('http://127.0.0.1:8091/api/control', json=command) as response:
                response.raise_for_status()
                result = await response.json()
        reply = result.get('message') or '音乐操作暂时没有完成'
    except (aiohttp.ClientError, ValueError, TimeoutError):
        reply = '音乐服务暂时没有响应，请稍后再试'
    conn.logger.bind(tag='local_music').info(f'本地音乐指令 action={command["action"]}，跳过模型')
    await clear_command._speak(conn, text, reply)
    return True
