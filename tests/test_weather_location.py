"""Location parser and provider fallback checks. Uses fictional page fixtures."""
import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

spec = importlib.util.spec_from_file_location('weather', Path(__file__).resolve().parents[1] / 'extensions/weather/backend.py')
weather = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weather)

PAGE = '<span>来自：中国 浙江 杭州 西湖 电信</span>'


class Response:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def text(self):
        return PAGE

    async def json(self, **kwargs):
        return {'ret': 0, 'province': '浙江', 'city': '杭州'}


class Session:
    def get(self, *args, **kwargs):
        return Response()


class LocationTests(unittest.IsolatedAsyncioTestCase):
    def test_district_and_city_pages(self):
        self.assertEqual(weather.parse_ip138(PAGE), ('浙江', '杭州', '西湖'))
        self.assertEqual(weather.parse_ip138('<span>来自：中国 浙江 杭州 电信</span>'), ('浙江', '杭州', None))
        self.assertEqual(weather.parse_ip138('<span>来自：中国&nbsp;浙江 杭州 西湖 电信</span>'), ('浙江', '杭州', '西湖'))

    def test_invalid_pages(self):
        for text in ['', '<span>来自：美国 华盛顿 微软云</span>', PAGE * 2, '<span>来自：中国 浙江 未知</span>', '<span>来自：中国 浙江 127.0.0.1 电信</span>']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                weather.parse_ip138(text)

    def test_parent_city_and_ambiguity(self):
        payload = 'weather([{"ref":"101210101~hangzhou~杭州~Hangzhou~杭州~Hangzhou~21~0~HZ~浙江"}])'
        self.assertEqual(weather.parse_city(payload, '杭州市', '浙江省'), ('101210101', '杭州'))
        with self.assertRaises(ValueError):
            weather.parse_city(payload, '杭州市', '江苏省')
        with self.assertRaises(ValueError):
            weather.parse_city(payload, '杭州市', '浙江省', '101210401')
        with self.assertRaises(ValueError):
            weather.parse_city('weather()', '杭州', '浙江')

    async def test_district_preferred(self):
        with patch.object(weather, 'search_city', new_callable=AsyncMock, side_effect=[('101210101', '杭州'), ('101210113', '西湖')]) as search:
            self.assertEqual(await weather.locate(Session()), ('101210113', '西湖'))
            self.assertEqual(search.await_args.args[1:], ('西湖', '浙江', '101210101'))

    async def test_missing_district_falls_back_to_city(self):
        with patch.object(weather, 'search_city', new_callable=AsyncMock, side_effect=[('101210101', '杭州'), ValueError()]) as search:
            self.assertEqual(await weather.locate(Session()), ('101210101', '杭州'))
            self.assertEqual(search.await_args_list[0].args[1:], ('杭州', '浙江'))

    async def test_bad_page_falls_back_to_tencent(self):
        with patch.object(weather, 'parse_ip138', side_effect=ValueError()), patch.object(weather, 'search_city', new_callable=AsyncMock, return_value=('101210101', '杭州')) as search:
            self.assertEqual(await weather.locate(Session()), ('101210101', '杭州'))
            self.assertEqual(search.await_args.args[1:], ('杭州', '浙江'))


if __name__ == '__main__':
    unittest.main()
