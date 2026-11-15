"""Web editor for Diablo II: Resurrected particle effects.

Starts a small local web server and serves EffectEditor.html. The page lists the
game's effects, shows an effect's layers with their textures, settings, script
constants and curves, lets you change them, and saves the result into a mod folder:

  <out>\\hd\\...                 the new .particles file and the textures made from PNGs
  <out>\\effect_recipes\\*.json  the recipe (what was changed), which EffectEdit.py can
                               apply again from the command line
  <out>\\effect_art\\*.png       the PNG files imported as textures

usage:
  EffectEditor.py --out <mod folder> [--game <D2R folder>] [--port 8765] [--no-browser]

Only this computer can reach the server (it listens on 127.0.0.1).
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import EffectEdit  # noqa: E402
import HdTexture  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SAFE_NAME = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')


class App:
    def __init__(self, game, out):
        self.game = EffectEdit.Game(game)
        self.out = os.path.abspath(out)
        self.lock = threading.Lock()       # the archive reader is used from one thread at a time
        self.thumbs = {}
        self.recipes = os.path.join(self.out, 'effect_recipes')
        self.art = os.path.join(self.out, 'effect_art')

    # -- helpers ----------------------------------------------------------
    def read(self, path):
        with self.lock:
            return self.game.read(path, [self.out])

    def names(self, suffix, query, limit=400):
        with self.lock:
            names = self.game.names()
        words = [w for w in query.lower().split() if w]
        out = []
        for n in names:
            low = n.lower()
            if low.endswith(suffix) and all(w in low for w in words):
                out.append(n if low.startswith('data/') else 'data/' + n)
                if len(out) >= limit:
                    break
        return out

    def texture_png(self, path, size):
        key = (path.lower(), size)
        if key in self.thumbs:
            return self.thumbs[key]
        from PIL import Image
        img = None
        base = os.path.splitext(os.path.basename(path))[0]
        art = os.path.join(self.art, base + '.png')
        try:
            img = HdTexture.to_image(self.read(path))
        except (EffectEdit.EditError, ValueError, OSError):
            if os.path.isfile(art):          # a texture the recipe will make from this PNG
                img = Image.open(art).convert('RGBA')
        if img is None:
            raise EffectEdit.EditError('no preview for %s' % path)
        if max(img.size) > size:
            img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        data = buf.getvalue()
        if not os.path.isfile(art):
            self.thumbs[key] = data
        return data

    def describe(self, recipe, scripts=False):
        with self.lock:
            if recipe.get('edits') or recipe.get('textures'):
                _, _, effect = EffectEdit.run_recipe(dict(recipe, textures=[]), self.game, None, self.recipes)
            else:
                effect = EffectEdit.Effect(self.game.read(recipe['source'], [self.out]), recipe['source'])
        return effect.describe(scripts=scripts)

    def save(self, recipe, name):
        if not SAFE_NAME.match(name or ''):
            raise EffectEdit.EditError('the name may use letters, digits, _ and - only')
        os.makedirs(self.recipes, exist_ok=True)
        with self.lock:
            data, textures, effect = EffectEdit.run_recipe(recipe, self.game, self.out, self.recipes)
        path = os.path.join(self.recipes, name + '.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, indent=1)
        return {'recipe': path, 'bytes': len(data), 'manifest': EffectEdit.manifest(recipe, effect)}

    def import_png(self, name, data):
        if not SAFE_NAME.match(name or ''):
            raise EffectEdit.EditError('the texture name may use letters, digits, _ and - only')
        from PIL import Image
        raw = base64.b64decode(data.split(',', 1)[-1])
        img = Image.open(io.BytesIO(raw))
        img.load()
        os.makedirs(self.art, exist_ok=True)
        img.convert('RGBA').save(os.path.join(self.art, name + '.png'))
        self.thumbs = {k: v for k, v in self.thumbs.items() if os.path.splitext(os.path.basename(k[0]))[0] != name.lower()}
        return {'png': '../effect_art/%s.png' % name, 'width': img.size[0], 'height': img.size[1]}

    def list_recipes(self):
        if not os.path.isdir(self.recipes):
            return []
        return sorted(f[:-5] for f in os.listdir(self.recipes) if f.endswith('.json'))

    def load_recipe(self, name):
        if not SAFE_NAME.match(name or ''):
            raise EffectEdit.EditError('bad recipe name')
        with open(os.path.join(self.recipes, name + '.json'), encoding='utf-8') as f:
            return json.load(f)


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):   # quiet
            pass

        def _send(self, code, body, ctype='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def _run(self, fn):
            try:
                result = fn()
                if isinstance(result, tuple):
                    self._send(200, result[0], result[1])
                else:
                    self._send(200, result)
            except EffectEdit.EditError as e:
                self._send(400, {'error': str(e)})
            except Exception as e:  # noqa: BLE001 - report, do not kill the server
                self._send(500, {'error': '%s: %s' % (type(e).__name__, e)})

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            if url.path in ('/', '/index.html'):
                with open(os.path.join(HERE, 'EffectEditor.html'), 'rb') as f:
                    return self._send(200, f.read(), 'text/html; charset=utf-8')
            if url.path == '/api/info':
                return self._run(lambda: {'out': app.out, 'game': app.game.game, 'recipes': app.list_recipes()})
            if url.path == '/api/effects':
                return self._run(lambda: app.names('.particles', q.get('q', '')))
            if url.path == '/api/textures':
                return self._run(lambda: app.names('.texture', 'hd/vfx ' + q.get('q', ''), 120))
            if url.path == '/api/texture':
                return self._run(lambda: (app.texture_png(q['path'], int(q.get('size', 192))), 'image/png'))
            if url.path == '/api/recipe':
                return self._run(lambda: app.load_recipe(q.get('name', '')))
            self._send(404, {'error': 'not found'})

        def do_POST(self):
            url = urllib.parse.urlparse(self.path)
            length = int(self.headers.get('Content-Length', 0))
            if length > 64 * 1024 * 1024:
                return self._send(413, {'error': 'too large'})
            try:
                body = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
            except ValueError:
                return self._send(400, {'error': 'bad JSON'})
            if url.path == '/api/describe':
                return self._run(lambda: app.describe(body['recipe'], bool(body.get('scripts'))))
            if url.path == '/api/save':
                return self._run(lambda: app.save(body['recipe'], body.get('name', '')))
            if url.path == '/api/import':
                return self._run(lambda: app.import_png(body.get('name', ''), body.get('data', '')))
            self._send(404, {'error': 'not found'})

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='mod folder to save into')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    args = ap.parse_args()
    if not args.game:
        ap.error('pass --game or set D2R_PATH to the folder that contains D2R.exe')
    app = App(args.game, args.out)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    url = 'http://127.0.0.1:%d/' % args.port
    print('Effect editor at %s  (saving into %s). Ctrl+C stops it.' % (url, app.out), flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
