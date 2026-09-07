#!/usr/bin/env python3
"""HTTP server + API for the SVG body graph editor."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_logic import apply_fixes, validate
from df_body_parser import compose_body, load_body_catalog
from df_body_raw_writer import compose_spec_body, is_custom_body
from df_creature_schema import (
    BODY_PRESETS,
    CULTURE_PRESETS,
    PHONOLOGY_PRESETS,
    PRESET_INFO,
    apply_preset,
    load_spec,
    new_spec,
    save_spec,
)
from df_mod_pack import assemble_mod, install_mod, list_generated_files, pack_zip, staging_dir
from df_paths import dfhack_present, dwarf_fortress_root, output_root
from df_raws_writer import write_creature_raw

EDITOR_DIR = _HERE / "editor"
_STATE: Dict[str, Any] = {
    "spec_path": None,
    "catalog": None,
}


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    data = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(data)


def _read_json(handler: BaseHTTPRequestHandler) -> Any:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def _current_spec_path() -> Path:
    if _STATE["spec_path"]:
        return Path(_STATE["spec_path"])
    raise FileNotFoundError("No spec loaded. POST /api/spec with path or body.")


def _try_load_spec() -> Optional[Dict[str, Any]]:
    try:
        return load_spec(_current_spec_path())
    except Exception:
        return None


def _list_projects() -> List[Dict[str, Any]]:
    root = output_root()
    items: List[Dict[str, Any]] = []
    if not root.is_dir():
        return items
    for child in sorted(root.iterdir()):
        spec_path = child / "creature.json"
        if not spec_path.is_file():
            continue
        try:
            spec = load_spec(spec_path)
        except Exception:
            continue
        cid = str(spec.get("id") or child.name).lower()
        images = child / "graphics" / "images"
        items.append(
            {
                "id": spec.get("id"),
                "name": spec.get("name_singular"),
                "preset": spec.get("preset"),
                "path": str(spec_path),
                "has_art": (images / f"{cid}_body.png").is_file(),
            }
        )
    return items


def _image_path(kind: str) -> Path:
    spec = load_spec(_current_spec_path())
    cid = str(spec["id"]).lower()
    images = staging_dir(spec) / "graphics" / "images"
    mapping = {
        "body": images / f"{cid}_body.png",
        "portrait": images / f"{cid}_portrait.png",
        "preview": images / f"{cid}_preview.png",
    }
    path = mapping.get(kind)
    if path is None:
        raise FileNotFoundError(f"Unknown image kind {kind}")
    if kind == "preview" and not path.is_file():
        alt = mapping["portrait"]
        if alt.is_file():
            return alt
    if not path.is_file():
        raise FileNotFoundError(f"No {kind} image yet — generate art first")
    return path


class EditorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[editor] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_file(EDITOR_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            self._serve_file(EDITOR_DIR / rel, None)
            return

        if path == "/api/catalog":
            cat = _STATE["catalog"] or load_body_catalog()
            _STATE["catalog"] = cat
            graph = None
            try:
                spec = load_spec(_current_spec_path())
                graph = compose_spec_body(spec)
                graph_payload = {
                    "fragments": graph.fragments,
                    "nodes": graph.nodes,
                    "edges": graph.edges,
                    "flags_present": graph.flags_present,
                    "warnings": graph.warnings,
                    "body_mode": spec.get("body_mode") or "fragments",
                    "custom": is_custom_body(spec),
                }
            except Exception:
                graph_payload = None
            _json_response(
                self,
                200,
                {
                    "bodies": sorted(cat.bodies.keys()),
                    "detail_plans": sorted(cat.detail_plans.keys()),
                    "body_count": len(cat.bodies),
                    "graph": graph_payload,
                    "catalog": {
                        name: {
                            "parts": [
                                {
                                    "id": p.id,
                                    "name": p.name,
                                    "flags": p.flags,
                                    "con": p.con,
                                    "category": p.category,
                                }
                                for p in frag.parts
                            ]
                        }
                        for name, frag in list(cat.bodies.items())[:80]
                    },
                },
            )
            return

        if path == "/api/spec":
            try:
                sp = _current_spec_path()
                spec = load_spec(sp)
                _json_response(self, 200, {"path": str(sp), "spec": spec})
            except Exception as exc:
                _json_response(self, 404, {"error": str(exc)})
            return

        if path == "/api/raw_preview":
            try:
                from df_body_raw_writer import write_custom_body_raws

                spec = load_spec(_current_spec_path())
                tmp = output_root() / "_editor_preview" / "objects"
                tmp.mkdir(parents=True, exist_ok=True)
                write_custom_body_raws(spec, tmp)
                out = write_creature_raw(spec, tmp)
                text = out.read_text(encoding="latin-1", errors="replace")
                _json_response(self, 200, {"path": str(out), "raw": text[:50000]})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/status":
            df = None
            try:
                df = str(dwarf_fortress_root())
            except Exception:
                df = None
            spec = _try_load_spec()
            _json_response(
                self,
                200,
                {
                    "spec_path": _STATE.get("spec_path"),
                    "spec_id": (spec or {}).get("id"),
                    "df_root": df,
                    "dfhack": bool(dfhack_present()),
                    "projects": _list_projects(),
                },
            )
            return

        if path == "/api/presets":
            entries = []
            for key, meta in PRESET_INFO.items():
                pdata = BODY_PRESETS.get(key) or {}
                entries.append(
                    {
                        "id": key,
                        "label": meta.get("label", key),
                        "playable": bool(meta.get("playable")),
                        "plan": meta.get("plan"),
                        "culture_preset": pdata.get("culture_preset"),
                        "graphics_profile": pdata.get("graphics_profile"),
                    }
                )
            _json_response(
                self,
                200,
                {
                    "body_presets": sorted(BODY_PRESETS.keys()),
                    "preset_info": PRESET_INFO,
                    "presets": entries,
                    "culture_presets": list(CULTURE_PRESETS),
                    "phonology_presets": list(PHONOLOGY_PRESETS),
                },
            )
            return

        if path == "/api/projects":
            _json_response(self, 200, {"projects": _list_projects()})
            return

        if path.startswith("/api/image/"):
            kind = path.split("/")[-1]
            try:
                img = _image_path(kind)
                self._serve_file(img, "image/png")
            except Exception as exc:
                _json_response(self, 404, {"error": str(exc)})
            return

        if path == "/api/cost":
            try:
                from df_body_cost import analyze_costs

                if "spec" in parse_qs(parsed.query):
                    pass
                spec = load_spec(_current_spec_path())
                _json_response(self, 200, analyze_costs(spec, full=True))
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = _read_json(self)

        if path == "/api/spec":
            # Load by path, or save full spec
            if "path" in body and "spec" not in body:
                sp = Path(body["path"])
                spec = load_spec(sp)
                _STATE["spec_path"] = str(sp.resolve())
                _json_response(self, 200, {"path": str(sp), "spec": spec})
                return
            if "spec" in body:
                spec = body["spec"]
                sp = Path(body.get("path") or _STATE.get("spec_path") or (output_root() / spec["id"] / "creature.json"))
                save_spec(spec, sp)
                _STATE["spec_path"] = str(sp.resolve())
                _json_response(self, 200, {"ok": True, "path": str(sp), "spec": spec})
                return
            _json_response(self, 400, {"error": "Provide path and/or spec"})
            return

        if path == "/api/validate":
            spec = body.get("spec")
            if not spec:
                try:
                    spec = load_spec(_current_spec_path())
                except Exception as exc:
                    _json_response(self, 400, {"error": str(exc)})
                    return
            fix = bool(body.get("fix"))
            if fix:
                spec = apply_fixes(spec)
                if _STATE.get("spec_path"):
                    save_spec(spec, _STATE["spec_path"])
            result = validate(spec)
            payload = result.to_dict()
            payload["spec"] = spec
            _json_response(self, 200, payload)
            return

        if path == "/api/new":
            cid = str(body.get("id") or "").strip()
            name = str(body.get("name") or "").strip()
            if not cid or not name:
                _json_response(self, 400, {"error": "id and name required"})
                return
            spec = new_spec(cid, name, preset=str(body.get("preset") or "humanoid_civ"))
            if body.get("culture"):
                spec["culture_preset"] = body["culture"]
            if body.get("phonology"):
                spec["phonology"] = body["phonology"]
            if body.get("description"):
                spec["description"] = body["description"]
            if body.get("art_prompt"):
                spec["art_prompt"] = body["art_prompt"]
            sp = staging_dir(spec) / "creature.json"
            save_spec(spec, sp)
            _STATE["spec_path"] = str(sp.resolve())
            preview = {}
            try:
                from df_tile_generator import generate_preview_for_spec

                preview = generate_preview_for_spec(spec, staging_dir(spec))
            except Exception as exc:
                preview = {"error": str(exc)}
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "path": str(sp),
                    "spec": spec,
                    "preview": {k: str(v) for k, v in preview.items()},
                },
            )
            return

        if path == "/api/apply-preset":
            try:
                spec = body.get("spec")
                if not spec:
                    spec = load_spec(_current_spec_path())
                spec = apply_preset(spec, str(body.get("preset") or ""))
                if _STATE.get("spec_path"):
                    save_spec(spec, _STATE["spec_path"])
                preview: Dict[str, Any] = {}
                try:
                    from df_tile_generator import generate_preview_for_spec

                    preview = generate_preview_for_spec(spec, staging_dir(spec))
                except Exception as exc:
                    preview = {"error": str(exc)}
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "spec": spec,
                        "preview": {k: str(v) for k, v in preview.items()},
                    },
                )
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/art":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                if _STATE.get("spec_path"):
                    save_spec(spec, _STATE["spec_path"])
                from df_graphics_writer import write_graphics
                from df_tile_generator import generate_art_for_spec

                root = staging_dir(spec)
                root.mkdir(parents=True, exist_ok=True)
                write_graphics(spec, root)
                arts = generate_art_for_spec(
                    spec,
                    root,
                    no_sd=bool(body.get("no_sd", True)),
                    force=bool(body.get("force")),
                    workers=body.get("workers"),
                )
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "sd_used": bool(arts.get("sd")),
                        "body": str(arts.get("body") or ""),
                        "portrait": str(arts.get("portrait") or ""),
                        "preview": str(arts.get("preview") or ""),
                    },
                )
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/preview":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                if _STATE.get("spec_path"):
                    save_spec(spec, _STATE["spec_path"])
                from df_tile_generator import generate_preview_for_spec

                arts = generate_preview_for_spec(spec, staging_dir(spec))
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "preview": str(arts.get("preview") or ""),
                        "portrait": str(arts.get("portrait") or ""),
                    },
                )
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/generate":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                if body.get("fix"):
                    spec = apply_fixes(spec)
                if _STATE.get("spec_path"):
                    save_spec(spec, _STATE["spec_path"])
                root = assemble_mod(spec, adventure_kit=bool(body.get("adventure_kit")))
                files = [str(p) for p in list_generated_files(root)]
                _json_response(self, 200, {"ok": True, "root": str(root), "files": files})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/analyze":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                if body.get("fix_layout"):
                    spec = apply_fixes(spec)
                    if _STATE.get("spec_path"):
                        save_spec(spec, _STATE["spec_path"])
                from df_body_cost import analyze_costs, save_cost_report

                report = analyze_costs(spec, full=True)
                out = staging_dir(spec) / "cost_report.json"
                save_cost_report(spec, out)
                _json_response(self, 200, {"ok": True, "cost": report, "path": str(out), "spec": spec})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/adventure-kit":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                from df_adventure_kit import stage_adventure_kit

                root = staging_dir(spec)
                root.mkdir(parents=True, exist_ok=True)
                written = stage_adventure_kit(spec, root)
                _json_response(
                    self,
                    200,
                    {"ok": True, "root": str(root), "files": [str(p) for p in written]},
                )
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/install":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                dest = install_mod(spec)
                _json_response(self, 200, {"ok": True, "dest": str(dest)})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/pack":
            try:
                spec = body.get("spec") or load_spec(_current_spec_path())
                z = pack_zip(spec)
                _json_response(self, 200, {"ok": True, "zip": str(z)})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        _json_response(self, 404, {"error": "not found"})

    def _serve_file(self, path: Path, content_type: Optional[str]) -> None:
        if not path.is_file():
            self.send_error(404, f"Missing {path.name}")
            return
        data = path.read_bytes()
        if content_type is None:
            if path.suffix == ".js":
                content_type = "application/javascript"
            elif path.suffix == ".css":
                content_type = "text/css"
            elif path.suffix == ".png":
                content_type = "image/png"
            elif path.suffix in (".jpg", ".jpeg"):
                content_type = "image/jpeg"
            elif path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            else:
                content_type = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if path.suffix == ".png":
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    spec: Optional[Path] = None,
    open_browser: bool = True,
) -> None:
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    if spec:
        _STATE["spec_path"] = str(Path(spec).resolve())
    _STATE["catalog"] = load_body_catalog()
    httpd = ThreadingHTTPServer((host, port), EditorHandler)
    url = f"http://{host}:{port}/"
    print(f"DF Creature Studio {url}", flush=True)
    if spec:
        print(f"  Spec: {spec}", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> int:
    ap = argparse.ArgumentParser(description="DF Creature Studio (body + graphics GUI)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--spec", type=Path, default=None)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    run_server(args.host, args.port, args.spec, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
