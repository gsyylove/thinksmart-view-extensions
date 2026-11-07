"""Run on the device with sudo. Reapply after an official update, or pass --remove."""
from datetime import datetime
from pathlib import Path
import shutil
import sys

module = Path(__file__).resolve().parent
client = Path('/opt/thinksmart/client/current').resolve()
html_path = client / 'web/v2/index.html'
web_path = client / 'thinksmart_client/web.py'
html = html_path.read_text()
backend = web_path.read_text()
voice_path = Path('/home/ubuntu/xiaozhi-hub-server/main/xiaozhi-server/core/handle/receiveAudioHandle.py')
voice_source = voice_path.read_text()
voice_import = '''# BEGIN local-weather-voice
import importlib.util as _weather_import
_weather_spec = _weather_import.spec_from_file_location('local_weather_voice', '/opt/thinksmart/extensions/weather/voice.py')
_weather_voice = _weather_import.module_from_spec(_weather_spec)
_weather_spec.loader.exec_module(_weather_voice)
# END local-weather-voice
'''
voice_hook = '''    # BEGIN local-weather-route
    if await _weather_voice.handle(conn, actual_text):
        return
    # END local-weather-route
'''
voice_source = voice_source.replace(voice_import, '').replace(voice_hook, '')
voice_anchor = '    # 首先进行意图分析，使用实际文本内容\n'
hook = """    # BEGIN local-weather
    import importlib.util
    spec = importlib.util.spec_from_file_location('local_weather', '/opt/thinksmart/extensions/weather/backend.py')
    weather_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(weather_module)
    weather_module.register(app)
    # END local-weather
"""
tags = '<!-- local-weather -->\n<link rel="stylesheet" href="/extensions/weather/assets/weather.css">\n<script defer src="/extensions/weather/assets/weather.js"></script>\n<!-- /local-weather -->\n'
import re
html = re.sub(r'<!-- local-weather -->.*?<!-- /local-weather -->\n?', '', html, flags=re.S)
backend = backend.replace(hook, '')
# Migrate the earlier direct page edits into this independent module.
html = re.sub(r'\s*<button class="weather-card".*?</button>', '', html, flags=re.S)
html = re.sub(r'<link rel="stylesheet" href="/static/v2/weather.css">\s*', '', html)
html = re.sub(r'<script src="/static/v2/weather.js"></script>\s*', '', html)
remove = '--remove' in sys.argv
if not remove:
    if html.count('</head>') != 1 or backend.count('    return app\n') != 1:
        raise SystemExit('Official page structure changed. No files modified.')
    if voice_source.count(voice_anchor) != 1:
        raise SystemExit('Hub speech routing changed. No files modified.')
    voice_source = voice_import + voice_source.replace(voice_anchor, voice_hook + voice_anchor)
    html = html.replace('</head>', tags + '</head>')
    backend = backend.replace('    return app\n', hook + '    return app\n')
backup = Path('/home/ubuntu/thinksmart-backups') / ('weather-module-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.mkdir(parents=True)
shutil.copy2(html_path, backup / 'index.html')
shutil.copy2(web_path, backup / 'web.py')
shutil.copy2(voice_path, backup / 'receiveAudioHandle.py')
compile(backend, str(web_path), 'exec')
compile(voice_source, str(voice_path), 'exec')
html_path.write_text(html)
web_path.write_text(backend)
voice_path.write_text(voice_source)
print('Removed' if remove else 'Installed', 'weather module for', client)
print('Backup:', backup)
