"""Speak local weather using the homepage data, without an LLM."""
from datetime import datetime
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import aiohttp


def matches(text):
    value = re.sub(r'[\s，。！？、,.!?：:]', '', text or '')
    value = re.sub(r'^(?:小麦小麦|小麦同学|哈喽小麦)', '', value)
    value = re.sub(r'^(?:请帮我|帮我|请)', '', value)
    value = re.sub(r'^(?:播报一下|播报|查一下|查询|报一下|告诉我)', '', value)
    value = re.sub(r'^(?:我们这里|本地|这里|这儿)(?:的)?', '', value)
    value = re.sub(r'(?:吧|呀|啊|呢)$', '', value)
    return bool(re.fullmatch(r'(?:现在|目前|今天|今日)?的?(?:天气|气温|温度)(?:怎么样|如何|是什么|多少|几度|是多少|有多少|情况|预报)?', value)
                or value in {'现在多少度', '现在几度', '今天多少度', '今天几度'})


def degrees(value):
    number = float(value)
    if not math.isfinite(number) or not -70 <= number <= 65:
        raise ValueError('Invalid temperature')
    return ('零下' if number < 0 else '') + f'{abs(number):g}度'


def weather_reply(data):
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    forecast_time = datetime.strptime(data['published'], '%Y-%m-%d %H:%M').replace(tzinfo=now.tzinfo)
    if forecast_time.date() != now.date():
        return '本地天气数据正在更新，请稍后再问一次。'
    current = ''
    if data.get('observed') and data.get('temperature') is not None:
        observation = datetime.strptime(data['observed'], '%Y-%m-%d %H:%M').replace(tzinfo=now.tzinfo)
        if observation.date() == now.date() and -600 <= (now - observation).total_seconds() <= 10800:
            current = f'本地现在{data["current_weather"]}，气温{degrees(data["temperature"])}。'
    if not current:
        current = '本地的实时气温暂时没有获取到。'
    return current + f'今天预报{data["weather"]}，最低{degrees(data["low"])}，最高{degrees(data["high"])}。'


async def handle(conn, text):
    if not matches(text):
        return False
    try:
        config = json.loads((Path.home() / '.config/thinksmart-client/config.json').read_text())
        if not config.get('device_id') or conn.headers.get('device-id') != config['device_id']:
            return False
    except (OSError, ValueError):
        return False
    from core.agent import clear_command
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as session:
            async with session.get('http://127.0.0.1:8090/extensions/weather/forecast', params={'refresh': '1'}) as response:
                response.raise_for_status()
                reply = weather_reply(await response.json())
    except (aiohttp.ClientError, KeyError, ValueError, TypeError, TimeoutError):
        reply = '本地天气数据暂时没有获取到，请稍后再试。'
    conn.logger.bind(tag='local_weather').info('本地天气播报，跳过模型')
    await clear_command._speak(conn, text, reply)
    return True
