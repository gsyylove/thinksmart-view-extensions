"""China Weather local daily forecast, cached locally for thirty minutes."""
import asyncio
import json
import math
from html import unescape
from datetime import datetime, timedelta
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientSession, ClientTimeout, web

IP138_SOURCE = 'https://2026.ip138.com/'
LOCATION_SOURCE = 'https://r.inews.qq.com/api/ip2city'
SEARCH_SOURCE = 'https://toy1.weather.com.cn/search'


def place_name(value):
    return re.sub(r'(?:特别行政区|壮族自治区|回族自治区|维吾尔自治区|自治区|自治州|地区|省|市|区|县)$', '', value.strip())


def parse_city(text, city, province, parent_code=None):
    match = re.fullmatch(r'\s*weather\((.*)\)\s*;?\s*', text, re.S)
    if not match or not match[1]:
        raise ValueError('City lookup unavailable')
    candidates = set()
    for item in json.loads(match[1]):
        parts = item.get('ref', '').split('~')
        if len(parts) < 10 or not re.fullmatch(r'101[0-9]{6}', parts[0]):
            continue
        region = {place_name(part) for part in parts[4:]}
        if place_name(parts[2]) != place_name(city) or place_name(province) not in region:
            continue
        if parent_code:
            prefix = parent_code[:5] if place_name(province) in {'北京', '天津', '上海', '重庆'} else parent_code[:7]
            if not parts[0].startswith(prefix):
                continue
        candidates.add((parts[0], parts[2]))
    if len(candidates) != 1:
        raise ValueError('City lookup ambiguous')
    return candidates.pop()


def parse_ip138(text):
    locations = []
    for span in re.findall(r'<span\b[^>]*>(.*?)</span>', text, re.S | re.I):
        value = unescape(re.sub(r'<[^>]+>', '', span)).strip()
        if value.startswith(('来自：', '来自:')):
            fields = re.sub(r'^来自[：:]\s*', '', value).split()
            # Public page layout: country, province, city, optional district, ISP.
            if len(fields) not in (4, 5) or fields[0] != '中国':
                raise ValueError('Unsupported IP138 location')
            names = fields[1:-1]
            if any(not re.fullmatch(r'[\u3400-\u9fff·]{1,30}', name) for name in names):
                raise ValueError('Invalid IP138 location')
            locations.append((names[0], names[1], names[2] if len(names) == 3 else None))
    if len(locations) != 1:
        raise ValueError('IP138 location missing or ambiguous')
    return locations[0]


async def search_city(session, city, province, parent_code=None):
    async with session.get(SEARCH_SOURCE, params={'cityname': place_name(city), 'callback': 'weather'}) as response:
        response.raise_for_status()
        return parse_city(await response.text(), city, province, parent_code)


async def locate(session):
    try:
        # The IP138 homepage embeds this public page. No token or IP is stored.
        async with session.get(IP138_SOURCE, headers={'Referer': 'https://www.ip138.com/'}, allow_redirects=False) as response:
            if response.status != 200:
                raise ValueError('IP138 page unavailable')
            province, city, district = parse_ip138(await response.text())
        city_result = await search_city(session, city, province)
        if district:
            try:
                return await search_city(session, district, province, city_result[0])
            except (ClientError, ValueError, KeyError, TypeError, OSError, asyncio.TimeoutError):
                pass
        return city_result
    except (ClientError, ValueError, KeyError, TypeError, OSError, asyncio.TimeoutError):
        pass
    async with session.get(LOCATION_SOURCE) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)
    if data.get('ret') != 0 or not data.get('city') or not data.get('province'):
        raise ValueError('IP location unavailable')
    return await search_city(session, data['city'], data['province'])


def parse_details(html):
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    published = re.search(r'id="fc_24h_internal_update_time"\s+value="(\d{10})"', html)
    if not published or published[1][:8] != now.strftime('%Y%m%d'):
        raise ValueError('Stale weekly forecast')
    days = []
    for index, block in enumerate(re.findall(r'<li class="sky skyid[^\"]*">(.*?)</li>', html, re.S)):
        title = re.search(r'<h1>(.*?)</h1>', block)
        weather = re.search(r'class="wea">([^<]+)', block)
        temperatures = re.search(r'<p class="tem">(.*?)</p>', block, re.S)
        if not title or not weather or not temperatures:
            raise ValueError('Weekly fields missing')
        values = re.findall(r'-?\d+', re.sub(r'<[^>]+>', '', temperatures[1]))
        if not values or len(values) > 2:
            raise ValueError('Weekly temperatures invalid')
        date = now.date() + timedelta(days=index)
        if not title[1].startswith(f'{date.day}日'):
            raise ValueError('Weekly date mismatch')
        days.append({'date': date.isoformat(), 'label': title[1], 'weather': weather[1],
                     'high': int(values[0]) if len(values) == 2 else None, 'low': int(values[-1])})
    match = re.search(r'var hour3data=(\{[^\n]+\})', html)
    if len(days) != 7 or not match:
        raise ValueError('Incomplete weekly forecast')
    hourly = []
    for item in json.loads(match[1])['1d']:
        parts = item.split(',')
        if len(parts) < 4:
            raise ValueError('Hourly fields missing')
        hourly.append({'time': parts[0], 'weather': parts[2], 'temperature': parts[3]})
    return {'days': days, 'hourly': hourly, 'interval_hours': 3}


def parse_current(text, city_id):
    match = re.fullmatch(r'\s*var\s+dataSK\s*=\s*(\{.*\})\s*;?\s*', text, re.S)
    if not match:
        raise ValueError('Current weather fields missing')
    data = json.loads(match[1])
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    day = re.match(r'(\d+)月(\d+)日', data.get('date', ''))
    if not day or (int(day[1]), int(day[2])) != (now.month, now.day) or str(data.get('city')) != city_id:
        raise ValueError('Wrong observation date or city')
    stamp = datetime.strptime(f'{now:%Y-%m-%d} {data["time"]}', '%Y-%m-%d %H:%M').replace(tzinfo=now.tzinfo)
    age = (now - stamp).total_seconds()
    temp = float(data['temp'])
    if not -600 <= age <= 10800 or not math.isfinite(temp) or not -70 <= temp <= 60:
        raise ValueError('Invalid or stale observation')
    return {'temperature': temp, 'current_weather': data['weather'], 'observed': stamp.strftime('%Y-%m-%d %H:%M')}


def parse_forecast(html):
    title = re.search(r'id="hidden_title"\s+value="([^"]+)"', html)
    published = re.search(r'id="fc_24h_internal_update_time"\s+value="([^"]+)"', html)
    if not title or not published:
        raise ValueError('Forecast fields missing')
    stamp = datetime.strptime(published[1], '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    if stamp.date() != now.date() or (stamp - now).total_seconds() > 3600:
        raise ValueError('Forecast date is not current')
    match = re.search(r'\s(\S+)\s+(-?\d+)/(-?\d+)°C', title[1])
    if not match:
        raise ValueError('Forecast temperatures missing')
    return {'weather': match[1], 'high': int(match[2]), 'low': int(match[3]),
            'published': published[1], 'source': '中国天气网'}


def register(app):
    cache = {}
    lock = asyncio.Lock()

    async def forecast(request):
        async with lock:
            minimum_age = 60 if request.query.get('refresh') == '1' else 1800
            if time.monotonic() - cache.get('time', -1e9) < minimum_age:
                return web.json_response(cache['data'])
            try:
                async with ClientSession(timeout=ClientTimeout(total=6), headers={
                        'Referer': 'https://www.weather.com.cn/', 'User-Agent': 'Mozilla/5.0'}) as session:
                    city_id, name = await asyncio.wait_for(locate(session), timeout=12)
                    source = f'https://www.weather.com.cn/weather1d/{city_id}.shtml'
                    real_source = f'https://d1.weather.com.cn/sk_2d/{city_id}.html'
                    week_source = f'https://www.weather.com.cn/weather/{city_id}.shtml'
                    async with session.get(source) as response:
                        response.raise_for_status()
                        html = await response.text()
                        data = parse_forecast(html)
                        data.update(location={'name': name, 'method': 'egress_ip'}, source_url=source)
                    try:
                        async with session.get(real_source, params={'_': str(int(time.time() * 1000))}) as response:
                            response.raise_for_status()
                            data.update(parse_current(await response.text(), city_id))
                    except (ClientError, ValueError, KeyError, OSError, asyncio.TimeoutError):
                        data['current_error'] = '实况暂不可用'
                    try:
                        async with session.get(week_source) as response:
                            response.raise_for_status()
                            data.update(parse_details(await response.text()))
                    except (ClientError, ValueError, KeyError, OSError, asyncio.TimeoutError):
                        data['details_error'] = '小时和七天预报暂不可用'
                cache.update(data=data, time=time.monotonic())
                return web.json_response(data)
            except (ClientError, ValueError, KeyError, TypeError, OSError, asyncio.TimeoutError):
                return web.json_response({'error': '天气暂不可用'}, status=503)

    app.router.add_get('/extensions/weather/forecast', forecast)
    app.router.add_static('/extensions/weather/assets/', Path(__file__).parent)
