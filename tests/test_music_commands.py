import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('voice', Path(__file__).resolve().parents[1] / 'extensions/music/voice.py')
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)

class MusicCommands(unittest.TestCase):
    def test_sources(self):
        for text, action in [('播放音乐', 'play'), ('播放热门音乐', 'hot'), ('播放热歌榜', 'hot'), ('随机播放音乐', 'shuffle'), ('随便放点歌', 'shuffle'), ('播放我的歌单', 'playlist'), ('播放推荐音乐', 'recommend'), ('继续播放', 'resume'), ('小麦同学，请帮我随机播放音乐吧', 'shuffle')]:
            with self.subTest(text=text):
                self.assertEqual(voice.request_for(text), {'action': action})

    def test_search_preserved(self):
        self.assertEqual(voice.request_for('播放周杰伦的晴天'), {'action': 'search', 'query': '周杰伦 晴天', 'singer': '周杰伦', 'title': '晴天'})

    def test_chat_and_negation(self):
        for text in ['不要播放音乐', '我不想播放热门音乐', '热门音乐是什么', '怎么播放推荐音乐？']:
            with self.subTest(text=text):
                self.assertIsNone(voice.request_for(text))

if __name__ == '__main__':
    unittest.main()
