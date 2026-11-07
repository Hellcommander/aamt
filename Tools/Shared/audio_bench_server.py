"""The Audio Bench's GUI server: a local page (audio_bench_gui.html) for people, on the same recipe format agents use.

Everything the page does goes through this JSON API, so an agent can drive the same bench without the page:

  GET  /                          the page
  GET  /api/catalog               effects, presets, EQ presets, recipe schema (audio_bench.catalog())
  GET  /api/sources               the named sources held in memory, with their analysis
  POST /api/source                {"name", "wav_base64"}          keep a sound as a named source; returns its analysis
  POST /api/source_path           {"name", "path"}                 same, from a file on disk
  POST /api/remove_source         {"name"}
  GET  /api/library?q=...&k=12    search the audio asset library (textures, references); license tier included
  POST /api/source_library        {"name", "id"}                   a library clip as a source
  GET  /api/source/<name>.wav     the source, to play it
  POST /api/render                {"recipe": {...}}                render; returns wav_base64 and analysis against "main"
  GET  /api/render.wav            the last render, to download it
  POST /api/export                {"path"}                         save the last render there (wav, ogg or flac by extension)
  POST /api/listen                {"purpose", "against": "<source>"}  the CLAP listener's verdict on the last render
  POST /api/handoff               {"recipe", "out_dir", "seeds", "stem"}  seed variants as WAVs for tuning in an outside editor;
                                  the reply lists sources whose license (direct / restricted) speaks against uploading them
  POST /api/takeback              {"tuned", "handoff_dir", "name"}    check a tuned file and keep it as a source
  POST /api/analyze               {"name"} or {"wav_base64"}
  POST /api/synth                 {"synth": "material"|"footstep", ...params, "name"}  a synthesized source (no clip, no license)
  POST /api/tags                  {"name"} or {"render": true}       semantic tags from the listener (0..1 each)
  POST /api/breed                 {"a": recipe, "b": recipe, "ratio", "mutation", "seed"}  an offspring recipe, validated
  POST /api/propose               {"purpose", "kind", "seconds", "seed", "candidates"}  the local audio agent (audio_agent) picks
                                  clips, decides layers and tuning, renders seeds, the listener chooses; the sources land in
                                  the store and the recipe comes back ready for the page

Only plain signal processing touches audio (audio_bench). The listener only listens. Binds to 127.0.0.1.

Usage: python audio_bench_server.py [--port 8765] [--open]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_bench as bench  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "audio_bench_gui.html")
SR = bench.SR

_sources: Dict[str, np.ndarray] = {}
_meta: Dict[str, Dict[str, Any]] = {}
_last: Optional[np.ndarray] = None
_lock = threading.Lock()
_library = None
_listener = None


def _wav_bytes(x: np.ndarray, sr: int = SR) -> bytes:
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.clip(bench.to_stereo(x), -1, 1), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _decode(b64: str) -> np.ndarray:
    import soundfile as sf

    x, sr = sf.read(io.BytesIO(base64.b64decode(b64)), always_2d=True, dtype="float32")
    x = bench.to_stereo(x)
    return bench.resample(x, int(sr), SR) if int(sr) != SR else x


def _library_obj():
    global _library
    if _library is None:
        from audio_asset_library import AudioLibrary

        _library = AudioLibrary()
        _library.load()
    return _library


def _listener_obj():
    global _listener
    if _listener is None:
        from audio_listener import Listener

        _listener = Listener()
    return _listener


def _resolve(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Named sources come from the store; anything else stays a path for the bench to load."""
    srcs = dict(recipe.get("sources") or {})
    for name in list(srcs) + [l.get("source") for l in recipe.get("layers", [])]:
        if isinstance(name, str) and name in _sources:
            srcs[name] = _sources[name]
    recipe = dict(recipe)
    recipe["sources"] = srcs
    recipe["sr"] = SR
    return recipe


def _keep(name: str, x: np.ndarray, **meta: Any) -> Dict[str, Any]:
    with _lock:
        _sources[name] = x
        _meta[name] = {**meta, "analysis": bench.analyze(x, SR)}
    return {"name": name, **_meta[name]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _body(self) -> Dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                self._send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
            elif u.path == "/api/catalog":
                self._json(bench.catalog())
            elif u.path == "/api/sources":
                self._json({"sources": {k: _meta.get(k, {}) for k in _sources}})
            elif u.path.startswith("/api/source/") and u.path.endswith(".wav"):
                name = u.path[len("/api/source/"):-4]
                if name not in _sources:
                    return self._json({"error": f"no source {name}"}, 404)
                self._send(200, _wav_bytes(_sources[name]), "audio/wav")
            elif u.path == "/api/render.wav":
                if _last is None:
                    return self._json({"error": "nothing rendered yet"}, 404)
                self._send(200, _wav_bytes(_last), "audio/wav")
            elif u.path == "/api/library":
                q = parse_qs(u.query)
                query = (q.get("q") or [""])[0]
                k = int((q.get("k") or ["12"])[0])
                lib = _library_obj()
                hits = lib.search_text(query, k=k) if query else []
                self._json({"hits": [{"id": h.record.id, "name": h.record.name, "pack": h.record.pack, "inner": h.record.inner,
                                      "seconds": round(float(h.record.duration), 2), "tier": h.record.license_tier(),
                                      "ai_allowed": h.record.ai_allowed(), "score": round(float(h.score), 3)} for h in hits]})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # the page shows the message
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        global _last
        u = urlparse(self.path)
        try:
            body = self._body()
            if u.path == "/api/source":
                name = str(body.get("name") or f"source{len(_sources) + 1}")
                self._json(_keep(name, _decode(body["wav_base64"]), origin=body.get("origin", "upload")))
            elif u.path == "/api/source_path":
                path = body["path"]
                name = str(body.get("name") or os.path.splitext(os.path.basename(path))[0])
                self._json(_keep(name, bench.load(path, SR)[0], origin=path))
            elif u.path == "/api/source_library":
                from audio_asset_library import load_asset_audio

                lib = _library_obj()
                rec = lib.get(body["id"])
                if rec is None:
                    return self._json({"error": "no such clip"}, 404)
                x, _ = load_asset_audio(rec, sr=SR, max_seconds=float(body.get("max_seconds", 12.0)))
                name = str(body.get("name") or rec.name)
                self._json(_keep(name, bench.to_stereo(x), origin=rec.label(), tier=rec.license_tier(), ai_allowed=rec.ai_allowed()))
            elif u.path == "/api/remove_source":
                with _lock:
                    _sources.pop(body["name"], None); _meta.pop(body["name"], None)
                self._json({"ok": True})
            elif u.path == "/api/render":
                recipe = _resolve(body["recipe"])
                problems = bench.validate(recipe)
                if problems:
                    return self._json({"error": "recipe problems: " + "; ".join(problems), "problems": problems}, 400)
                b = bench.Bench(SR)
                y, sr = b.render(recipe)
                with _lock:
                    _last = y
                used = [l.get("source") for l in recipe.get("layers", []) if isinstance(l.get("source"), str)]
                refs = {name: _sources[name] for name in dict.fromkeys(used) if name in _sources} or None
                analysis = bench.analyze(y, sr, refs)
                if refs:   # which sources are library clips under licensed terms, so the meter can say which bars matter
                    rules = {"reference": "unique result required (waveform under the bar), credit Noise Alchemy; may ship free",
                             "direct": "embedded only: programmatic processing, ships sealed inside the production, never loose, uploaded or shared",
                             "restricted": "embedded only, most restricted: programmatic processing, ships sealed inside the production, never standalone, never into any AI",
                             "own": "your own material: no rule", "given": "your own material: no rule"}
                    for name in analysis.get("against", {}):
                        tier = _meta.get(name, {}).get("tier", "own")
                        analysis["against"][name]["tier"] = tier
                        analysis["against"][name]["rule"] = rules.get(tier, "")
                self._json({"wav_base64": base64.b64encode(_wav_bytes(y, sr)).decode("ascii"), "analysis": analysis, "seconds": round(len(y) / sr, 3),
                            "checks": bench.check_render(y, sr), "layer_share": b.last_layer_share})
            elif u.path == "/api/synth":
                from audio_materials import synth
                spec = dict(body); name = str(spec.pop("name", None) or f"{spec.get('material') or spec.get('surface')}_{spec.get('synth')}")
                self._json(_keep(name, bench.to_stereo(synth(spec, SR)), origin="synthesized: " + json.dumps(spec), tier="own", ai_allowed=True))
            elif u.path == "/api/tags":
                x = _last if body.get("render") else _sources.get(body.get("name"))
                if x is None:
                    return self._json({"error": "no such source, or nothing rendered"}, 404)
                self._json({"tags": _listener_obj().tags(x, SR)})
            elif u.path == "/api/breed":
                child = bench.breed(body["a"], body["b"], ratio=float(body.get("ratio", 0.5)), mutation=float(body.get("mutation", 0.15)), seed=int(body.get("seed", 0)))
                self._json({"recipe": child, "problems": bench.validate(_resolve(child))})
            elif u.path == "/api/export":
                if _last is None:
                    return self._json({"error": "nothing rendered yet"}, 400)
                import soundfile as sf

                path = body["path"]
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                ext = os.path.splitext(path)[1].lower()
                y = np.clip(_last, -1, 1)
                if body.get("mono"):
                    y = y.mean(axis=1, keepdims=True)
                out_sr = int(body.get("sr") or SR)
                if out_sr != SR:
                    y = bench.resample(y, SR, out_sr)
                sf.write(path, y, out_sr, format={".ogg": "OGG", ".flac": "FLAC"}.get(ext, "WAV"), subtype={".ogg": "VORBIS", ".flac": "PCM_16"}.get(ext, "PCM_16"))
                self._json({"saved": os.path.abspath(path)})
            elif u.path == "/api/listen":
                if _last is None:
                    return self._json({"error": "nothing rendered yet"}, 400)
                purpose = str(body.get("purpose") or "")
                against = body.get("against")
                ears = _listener_obj()
                if against and against in _sources:
                    self._json(ears.compare(_last, _sources[against], SR, purpose))
                else:
                    self._json({"new": ears.score(_last, SR, purpose)})
            elif u.path == "/api/handoff":
                recipe = _resolve(body["recipe"])
                prov = {}
                for name in {l.get("source") for l in recipe.get("layers", [])} | set(body["recipe"].get("sources", {})):
                    if name in _meta:
                        m = _meta[name]
                        prov[name] = {"tier": m.get("tier", "own"), "origin": m.get("origin", "")}
                seeds = [int(s) for s in str(body.get("seeds", "1,2,3")).split(",") if str(s).strip()]
                note = bench.handoff(recipe, body["out_dir"], seeds=seeds, stem=str(body.get("stem") or "variant"), provenance=prov)
                self._json({"variants": [v["path"] for v in note["variants"]], "licensed_sources": note["licensed_sources"], "dir": os.path.abspath(body["out_dir"])})
            elif u.path == "/api/takeback":
                a = bench.takeback(body["tuned"], body["handoff_dir"])
                if a["ok"] and body.get("name"):
                    _keep(str(body["name"]), bench.load(body["tuned"], SR)[0], origin="tuned by hand: " + body["tuned"])
                self._json(a)
            elif u.path == "/api/propose":
                from audio_agent import Agent

                agent = Agent(library=_library_obj(), listener=_listener_obj())
                given = {n: _sources[n] for n in (body.get("use") or []) if n in _sources} or None
                secs = body.get("seconds")
                plan = agent.propose(str(body.get("purpose") or ""), kind=str(body.get("kind") or "auto"), seconds=float(secs) if secs else None,
                                     seed=int(body.get("seed") or 1), candidates=int(body.get("candidates") or 4), sources=given)
                recipe = dict(plan["recipe"])
                for name, arr in recipe["sources"].items():
                    o = plan["sources"].get(name, {})
                    _keep(name, arr, origin=o.get("origin", "agent"), tier=o.get("tier", "own"), ai_allowed=o.get("ai_allowed", True))
                recipe["sources"] = {n: n for n in recipe["sources"]}
                with _lock:
                    _last = plan["render"]
                self._json({"recipe": recipe, "report": plan["report"], "candidates": plan["candidates"], "chosen": plan["chosen"], "kind": plan["kind"],
                            "wav_base64": base64.b64encode(_wav_bytes(plan["render"], SR)).decode("ascii"), "seconds": round(len(plan["render"]) / SR, 3),
                            "analysis": bench.analyze(plan["render"], SR, {"main": recipe and _sources[recipe["layers"][0]["source"]]})})
            elif u.path == "/api/analyze":
                x = _sources[body["name"]] if "name" in body else _decode(body["wav_base64"])
                self._json(bench.analyze(x, SR))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audio Bench GUI server")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    a = ap.parse_args(argv)
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Audio Bench at {url}  (Ctrl+C stops it)", flush=True)
    if a.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
