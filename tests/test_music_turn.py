import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

spec = importlib.util.spec_from_file_location('music_voice', Path(__file__).resolve().parents[1] / 'extensions/music/voice.py')
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)


class MusicTurnTests(unittest.IsolatedAsyncioTestCase):
    async def run_turn(self, response=True, failure=False):
        conn = SimpleNamespace(headers={'device-id': 'test-device'}, close_after_chat=False,
                               close=AsyncMock(), logger=MagicMock())
        async def speak(*args):
            self.assertTrue(conn.close_after_chat)
            return response
        speaker = SimpleNamespace(_speak=AsyncMock(side_effect=speak))
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        reply = MagicMock()
        reply.json = AsyncMock(return_value={'ok': True, 'message': '音乐已暂停'})
        request = MagicMock()
        request.__aenter__ = AsyncMock(return_value=reply)
        if failure:
            request.__aenter__.side_effect = voice.aiohttp.ClientError()
        request.__aexit__ = AsyncMock(return_value=False)
        session.post.return_value = request
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / '.config/thinksmart-client/config.json'
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({'device_id': 'test-device'}))
            with patch.object(voice.Path, 'home', return_value=root), patch.object(voice.aiohttp, 'ClientSession', return_value=session), patch.dict(sys.modules, {'core.agent': SimpleNamespace(clear_command=speaker)}):
                self.assertTrue(await voice.handle(conn, '暂停音乐'))
        self.assertTrue(conn.close_after_chat)
        speaker._speak.assert_awaited_once()
        if response:
            conn.close.assert_not_awaited()  # The hub closes after the queued audio is sent.
        else:
            conn.close.assert_awaited_once()

    async def test_close_after_success_audio(self):
        await self.run_turn()

    async def test_close_after_failure_audio(self):
        await self.run_turn(failure=True)

    async def test_close_when_tts_unavailable(self):
        await self.run_turn(response=False)

    async def test_unrelated_chat_unchanged(self):
        conn = SimpleNamespace(close_after_chat=False)
        self.assertFalse(await voice.handle(conn, '今天天气如何'))
        self.assertFalse(conn.close_after_chat)


if __name__ == '__main__':
    unittest.main()
