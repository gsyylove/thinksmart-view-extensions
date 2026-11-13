"""Load extensions in memory for known upstream files."""
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import logging
from pathlib import Path
import sys

ROOT = Path('/opt/thinksmart/extensions')
WEB = 'thinksmart_client.web'
HUB = 'core.handle.receiveAudioHandle'
HASHES = {
    WEB: 'c2ef3318efe08f36bdbfcd4ca00932cf12a0368bf87e84d506490d774a3ecbcd',
    HUB: '59d77807c320a3ec5c04ef4095b2c605ccf36d3dc1b897b9ce65c95e49c5fb84',
    'index.html': '20d398f332d2412e9071d1f19f99de7161c4ebb0dc0ee31f70c1f54cfe2f3cf9',
}


def checked(path, key):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != HASHES[key]:
        raise ValueError(f'Unsupported upstream file: {key}')
    return data.decode('utf-8')


def enabled(name):
    return (ROOT / 'runtime' / (name + '.enabled')).is_file()


def load(name, file):
    spec = importlib.util.spec_from_file_location(f'local_{name}', ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Unexpected upstream entry point')
    return source.replace(old, new)


def prepare(name, path):
    source = checked(path, name)
    bindings = {}
    if name == WEB:
        html = checked(path.parent.parent / 'web/v2/index.html', 'index.html')
        tags = []
        if enabled('weather'):
            bindings['_local_weather'] = load('weather_backend', 'weather/backend.py')
            tags.append('<link rel="stylesheet" href="/extensions/weather/assets/weather.css"><script defer src="/extensions/weather/assets/weather.js"></script>')
            source = replace_once(source, '    return app\n', '    _local_weather.register(app)\n    return app\n')
        if enabled('music'):
            tags.append('<link rel="stylesheet" href="http://127.0.0.1:8091/music.css"><script defer src="http://127.0.0.1:8091/music.js"></script>')
        bindings['_local_html'] = replace_once(html, '</head>', '\n'.join(tags) + '\n</head>')
        source = replace_once(
            source, "return web.FileResponse(WEB / 'v2' / 'index.html', headers={'Cache-Control': 'no-cache'})",
            "return web.Response(text=_local_html, content_type='text/html', headers={'Cache-Control': 'no-cache'})",
        )
    else:
        anchor = '    # 首先进行意图分析，使用实际文本内容\n'
        hooks = []
        for extension in ('music', 'weather'):
            if enabled(extension):
                alias = '_local_' + extension
                bindings[alias] = load(extension + '_voice', extension + '/voice.py')
                hooks.append(f'    if await {alias}.handle(conn, actual_text):\n        return\n')
        source = replace_once(source, anchor, ''.join(hooks) + anchor)
    return compile(source, str(path), 'exec'), bindings


class Loader(importlib.abc.Loader):
    def __init__(self, upstream, name, path):
        self.upstream = upstream
        self.name = name
        self.path = path

    def exec_module(self, module):
        try:
            code, bindings = prepare(self.name, self.path)
        except Exception as error:
            logging.getLogger(__name__).warning('ThinkSmart extensions skipped for %s: %s', self.name, type(error).__name__)
            self.upstream.exec_module(module)
            return
        module.__dict__.update(bindings)
        exec(code, module.__dict__)


class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in (WEB, HUB):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            spec.loader = Loader(spec.loader, fullname, Path(spec.origin))
            return spec
        return None


if any(enabled(name) for name in ('music', 'weather')):
    sys.meta_path.insert(0, Finder())
