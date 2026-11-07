"""Install the QQ Music page module against the current official client."""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

module = Path(__file__).resolve().parent
client = Path('/opt/thinksmart/client/current').resolve()
page = client / 'web/v2/index.html'
link = client / 'web/local-music'
html = page.read_text()
voice_path = Path('/home/ubuntu/xiaozhi-hub-server/main/xiaozhi-server/core/handle/receiveAudioHandle.py')
voice_source = voice_path.read_text()
voice_import = '''# BEGIN local-music-voice
import importlib.util as _music_import
_music_spec = _music_import.spec_from_file_location('local_music_voice', '/opt/thinksmart/extensions/music/voice.py')
_music_voice = _music_import.module_from_spec(_music_spec)
_music_spec.loader.exec_module(_music_voice)
# END local-music-voice
'''
voice_hook = '''    # BEGIN local-music-route
    if await _music_voice.handle(conn, actual_text):
        return
    # END local-music-route
'''
voice_source = voice_source.replace(voice_import, '').replace(voice_hook, '')
voice_anchor = '    # 首先进行意图分析，使用实际文本内容\n'
html = re.sub(r'<!-- local-music -->.*?<!-- /local-music -->\n?', '', html, flags=re.S)
remove = '--remove' in sys.argv
if not remove and html.count('</head>') != 1:
    raise SystemExit('Page structure changed. No files modified.')
if not remove:
    if voice_source.count(voice_anchor) != 1:
        raise SystemExit('Hub speech routing changed. No files modified.')
    voice_source = voice_import + voice_source.replace(voice_anchor, voice_hook + voice_anchor)
compile(voice_source, str(voice_path), 'exec')
if link.exists() and (not link.is_symlink() or link.resolve() != module):
    raise SystemExit('Unexpected asset path. No files modified.')
backup = Path('/home/ubuntu/thinksmart-backups') / ('music-module-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.mkdir(parents=True)
shutil.copy2(page, backup / 'index.html')
shutil.copy2(voice_path, backup / 'receiveAudioHandle.py')
if remove:
    if link.is_symlink():
        link.unlink()
else:
    if not link.is_symlink():
        link.symlink_to(module, target_is_directory=True)
    html = html.replace('</head>', '<!-- local-music -->\n<link rel="stylesheet" href="http://127.0.0.1:8091/music.css">\n<script defer src="http://127.0.0.1:8091/music.js"></script>\n<!-- /local-music -->\n</head>')
page.write_text(html)
voice_path.write_text(voice_source)
startup = Path('/etc/systemd/system/thinksmart-client.service.d/local-music.conf')
if remove:
    startup.unlink(missing_ok=True)
else:
    startup.parent.mkdir(parents=True, exist_ok=True)
    startup.write_text('[Unit]\nWants=thinksmart-music.service\nAfter=thinksmart-music.service\n')
print('Removed' if remove else 'Installed', 'music module for', client)
