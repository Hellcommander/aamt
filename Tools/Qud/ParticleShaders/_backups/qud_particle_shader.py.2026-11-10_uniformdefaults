#!/usr/bin/env python3
"""
Qud particle shader pipeline: a particle spec (JSON) -> a Qud Shader Library effect.

    spec.particles.json  ->  <out>/shaders/<Name>.shader      full-screen HLSL particle effect, ShaderKit contract
                             <out>/ShaderEffects.fragment.xml   <bundle> line + one <preset> per effect, ready to merge
                             <out>/usage.cs.txt                  how each mod's *ShaderFX wrapper plays the presets
                             <out>/previews/<Name>.gif           numpy render of the same maths over a map shot
                             <out>/manifest.json                 what was generated, for the build/install steps

The shaders draw procedural particles (sparks, embers, spores, motes, shards, rings) in the fragment shader: every
pixel visits every particle, each particle is a deterministic function of its index and the library's clock, so
nothing is simulated or stored. They follow the Qud Shader Library ShaderKit contract (QudFX.cginc: vUv, _Amt, _T,
_Click, _Focus, _CellMap, ...) and are built into a bundle with Build-QudShaderBundle.ps1 (Unity 6000.0.77f1), then
played by name from the mods' ShaderFX wrappers or any ShaderEffects.xml preset.

Commands
    generate <spec> [--out DIR] [--lint] [--preview] [--mapshot PNG] [--frames N]
    lint     <file.shader ...>                         offline HLSL check with fxc (Windows SDK), no Unity needed
    preview  <spec> --out DIR [--mapshot PNG]          only the GIFs
    install  <out DIR> --mod-path DIR [--force]        copy Bundles/ into the mod and merge ShaderEffects.xml
    draft    --describe "..." --out spec.json          Ollama writes a first spec from a description
    schema                                             print the spec reference

Run with `python -I` from anywhere; paths in a spec are relative to the spec file.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
TOOLS_ROOT = HERE.parent.parent
MAX_PARTICLES = 160
SHADER_LIBRARY_WORKSHOP_ID = "3822020203"

# ----------------------------------------------------------------------------------------------------------- spec

EFFECT_DEFAULTS = {
    # who / where
    "name": None,                 # plays under this name; last part of the shader path
    "anchor": "focus",            # focus | click | player
    "emitter": {"shape": "point", "radius": 0.0},   # point | ring | disc | cells | screen; radius in screen heights
    # when
    "mode": "burst",              # burst: born at a (re)fire, die after life; continuous: a steady stream
    "count": 48,                  # particles, 1..160
    "life": [0.6, 1.4],           # seconds, min..max per particle
    "stagger": 0.25,              # burst only: seconds over which births are spread
    # motion (screen heights per second; a map cell is 0.04)
    "direction": "radial",        # radial | inward | degrees (0 = right, 90 = up)
    "spread": 360,                # degrees around the direction
    "speed": [0.05, 0.25],
    "gravity": 0.0,               # + is down
    "drag": 0.0,                  # per second
    "swirl": 0.0,                 # radians per second around the anchor
    "wobble": 0.0,                # noise displacement, screen heights
    "cellSnap": False,            # snap positions to map cells (tile look)
    # look
    "shape": "dot",               # dot | spark | ring | streak | glyph
    "size": [0.004, 0.010],       # radius, screen heights
    "endSize": 1.0,               # size multiplier at death
    "stretch": 3.0,               # spark: length along the velocity, in sizes; streak: trail length in sizes
    "colors": ["#ffffff", "#ffffff"],   # birth -> death
    "glow": 1.0,
    "blend": "add",               # add | alpha | screen
    "fadeIn": 0.1,                # fraction of life
    "fadeOut": 0.5,
    "flicker": 0.0,               # 0..1
    "distort": 0.0,               # refraction of the map under particles, screen heights
    "seed": 1.0,
    # the preset written to ShaderEffects.xml
    "preset": {},                 # name, seconds, amount, fadeIn, fadeOut, refire, layer
}

SPEC_DEFAULTS = {
    "mod": "MyMod",               # mod id, for messages and the usage snippet
    "modFolder": None,            # folder name under Mods/ when it differs from the id
    "modPath": None,              # explicit install path (overrides modFolder)
    "bundle": "mymod_fx",         # bundle name: Bundles/windows/<bundle>_windows
    "shaderPath": None,           # "Hidden/<mod>" by default; the effect name is appended
    "presetPrefix": "",           # e.g. "BM_"; preset names default to prefix + effect name
    "wrapper": None,              # C# wrapper call used in usage.cs.txt, e.g. "BroodmotherShaderFX.Play"
    "effects": [],
}

SHAPES = ("dot", "spark", "ring", "streak", "glyph")
BLENDS = ("add", "alpha", "screen")
EMITTERS = ("point", "ring", "disc", "cells", "screen")
ANCHORS = ("focus", "click", "player")
MODES = ("burst", "continuous")


def load_spec(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    spec = dict(SPEC_DEFAULTS)
    spec.update({k: v for k, v in raw.items() if k != "effects"})
    spec["_path"] = path
    if not spec.get("shaderPath"):
        spec["shaderPath"] = "Hidden/" + re.sub(r"[^A-Za-z0-9_]", "", spec["mod"])
    effects = []
    for i, e in enumerate(raw.get("effects") or []):
        eff = json.loads(json.dumps(EFFECT_DEFAULTS))
        for k, v in e.items():
            if k == "emitter" and isinstance(v, dict):
                eff["emitter"].update(v)
            else:
                eff[k] = v
        effects.append(normalize_effect(eff, i))
    spec["effects"] = effects
    return spec


def _pair(v, name):
    if isinstance(v, (int, float)):
        return [float(v), float(v)]
    if isinstance(v, list) and len(v) == 2:
        return [float(v[0]), float(v[1])]
    raise ValueError(f"{name}: expected a number or [min, max], got {v!r}")


def _hex(c: str) -> tuple[float, float, float]:
    s = c.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) not in (6, 8):
        raise ValueError(f"bad colour {c!r}")
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def normalize_effect(e: dict, index: int) -> dict:
    name = e.get("name")
    if not name or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"effects[{index}]: name must be an identifier (letters, digits, _), got {name!r}")
    if e["anchor"] not in ANCHORS:
        raise ValueError(f"{name}: anchor must be one of {ANCHORS}")
    if e["emitter"]["shape"] not in EMITTERS:
        raise ValueError(f"{name}: emitter.shape must be one of {EMITTERS}")
    if e["mode"] not in MODES:
        raise ValueError(f"{name}: mode must be one of {MODES}")
    if e["shape"] not in SHAPES:
        raise ValueError(f"{name}: shape must be one of {SHAPES}")
    if e["blend"] not in BLENDS:
        raise ValueError(f"{name}: blend must be one of {BLENDS}")
    e["count"] = int(max(1, min(MAX_PARTICLES, int(e["count"]))))
    e["life"] = _pair(e["life"], f"{name}.life")
    e["speed"] = _pair(e["speed"], f"{name}.speed")
    e["size"] = _pair(e["size"], f"{name}.size")
    e["emitter"]["radius"] = float(e["emitter"].get("radius", 0.0))
    d = e["direction"]
    if isinstance(d, str):
        if d not in ("radial", "inward"):
            raise ValueError(f"{name}: direction must be radial, inward or degrees")
    else:
        e["direction"] = float(d)
    cols = e["colors"]
    if isinstance(cols, str):
        cols = [cols, cols]
    if len(cols) == 1:
        cols = [cols[0], cols[0]]
    e["_c0"], e["_c1"] = _hex(cols[0]), _hex(cols[1])
    for k in ("stagger", "spread", "gravity", "drag", "swirl", "wobble", "endSize", "stretch", "glow",
              "fadeIn", "fadeOut", "flicker", "distort", "seed"):
        e[k] = float(e[k])
    e["fadeIn"] = min(max(e["fadeIn"], 0.0), 0.95)
    e["fadeOut"] = min(max(e["fadeOut"], 0.0), 0.95)
    e["flicker"] = min(max(e["flicker"], 0.0), 1.0)
    return e


# ---------------------------------------------------------------------------------------------------------- HLSL

def f(x: float) -> str:
    """An HLSL float literal."""
    s = f"{float(x):.6g}"
    if "e" in s or "E" in s:
        s = f"{float(x):.8f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s


def f3(c) -> str:
    return f"float3({f(c[0])}, {f(c[1])}, {f(c[2])})"


def hlsl_for(e: dict, spec: dict) -> str:
    name = e["name"]
    anchor = {"focus": "_Focus.xy", "click": "_Click.xy", "player": "cellToScreen(_Player.xy)"}[e["anchor"]]
    em = e["emitter"]
    R = f(em["radius"])

    # birth offset (square space, around the anchor); r6/r7 are the particle's shape randoms
    if em["shape"] == "point":
        born = "float2 born = A;"
    elif em["shape"] == "ring":
        born = f"float2 born = A + float2(cos(r6 * 6.2831853), sin(r6 * 6.2831853)) * {R};"
    elif em["shape"] == "disc":
        born = f"float2 born = A + float2(cos(r6 * 6.2831853), sin(r6 * 6.2831853)) * sqrt(r7) * {R};"
    elif em["shape"] == "cells":
        cells = f(max(0.0, em["radius"]) / 0.04)
        born = (f"float2 bc = screenToCell(A / asp) + floor((float2(r6, r7) - 0.5) * 2.0 * {cells} + 0.5);\n"
                "                float2 born = cellToScreen(bc) * asp;")
    else:  # screen
        born = "float2 born = float2(r6 * _Aspect, r7);"

    d = e["direction"]
    if d in ("radial", "inward") and em["shape"] == "point":
        # born == A for a point emitter: radial just means a random heading (and avoids normalize(0))
        base = "float2 base = float2(cos(r3 * 6.2831853), sin(r3 * 6.2831853));"
    elif d == "radial":
        base = "float2 bd = born - A; float2 base = length(bd) > 1e-5 ? bd / max(length(bd), 1e-5) : float2(cos(r3 * 6.2831853), sin(r3 * 6.2831853));"
    elif d == "inward":
        base = "float2 bd = A - born; float2 base = length(bd) > 1e-5 ? bd / max(length(bd), 1e-5) : float2(cos(r3 * 6.2831853), sin(r3 * 6.2831853));"
    else:
        a = math.radians(float(d))
        base = f"float2 base = float2({f(math.cos(a))}, {f(-math.sin(a))});"   # screen y points down

    if e["mode"] == "burst":
        timing = (f"float life = lerp({f(e['life'][0])}, {f(e['life'][1])}, r0);\n"
                  f"                float age = _Click.z - r1 * {f(e['stagger'])};\n"
                  "                float t = age / life;\n"
                  "                if (t < 0.0 || t > 1.0) continue;\n"
                  "                float fj = fi;")
    else:
        timing = (f"float life = lerp({f(e['life'][0])}, {f(e['life'][1])}, r0);\n"
                  "                float phase = (_T + r1 * life) / life;\n"
                  "                float t = frac(phase);\n"
                  "                float fj = fi + floor(phase) * 131.0;   // a new random particle every cycle")

    if e["drag"] > 0:
        travel = f"(1.0 - exp(-{f(e['drag'])} * tt)) / {f(e['drag'])}"
    else:
        travel = "tt"

    motion = [f"float2 pos = born + dir * spd * ({travel});",
              "pos.y += 0.5 * _Gravity * tt * tt;"]
    if e["swirl"] != 0:
        motion.append(f"pos = A + rotv(pos - A, {f(e['swirl'])} * tt);")
    if e["wobble"] != 0:
        motion.append(f"pos += (float2(noise(float2(fj * 3.1, tt * 2.0 + 7.0)), noise(float2(tt * 2.0, fj * 5.7 + 3.0))) - 0.5) * {f(e['wobble'])};")
    if e["cellSnap"]:
        motion.append("pos = cellToScreen(screenToCell(pos / asp)) * asp;")

    shape = e["shape"]
    if shape == "dot":
        kernel = "float k = exp(-dot(dd, dd) / (size * size)) + 0.35 * exp(-dot(dd, dd) / (size * size * 0.15));"
    elif shape == "spark":
        kernel = (f"float along = dot(dd, dir); float perp = dd.x * dir.y - dd.y * dir.x;\n"
                  f"                float k = exp(-(along * along / (size * size * {f(e['stretch'] * e['stretch'])}) + perp * perp / (size * size)));")
    elif shape == "ring":
        kernel = "float rr = length(dd) - size; float k = exp(-rr * rr / (size * size * 0.09));"
    elif shape == "streak":
        kernel = (f"float2 tail = -dir * size * {f(e['stretch'])};\n"
                  "                float h = saturate(dot(dd, tail) / max(dot(tail, tail), 1e-6));\n"
                  "                float2 seg = dd - tail * h;\n"
                  "                float k = exp(-dot(seg, seg) / (size * size * 0.3)) * (1.0 - 0.6 * h);")
    else:  # glyph: a crisp map-cell-ish square
        kernel = "float2 ad = abs(dd); float k = 1.0 - smoothstep(size * 0.8, size, max(ad.x, ad.y));"

    env = [f"float env = smoothstep(0.0, {f(max(e['fadeIn'], 1e-4))}, t) * (1.0 - smoothstep({f(1.0 - e['fadeOut'])}, 1.0, t));"]
    if e["flicker"] > 0:
        env.append(f"env *= lerp({f(1.0 - e['flicker'])}, 1.0, noise(float2(_T * 14.0, fj * 0.37)));")

    if e["blend"] == "add":
        blend = "col += glow * _Amt;"
    elif e["blend"] == "alpha":
        blend = "col = lerp(col, glow / max(cover, 1e-4), saturate(cover) * saturate(_Amt));"
    else:
        blend = "col = 1.0 - (1.0 - col) * (1.0 - saturate(glow * _Amt));"

    shader_path = f"{spec['shaderPath']}/{name}"
    lines = f"""// Generated by AAMT qud_particle_shader.py from {spec['_path'].name}: effect "{name}" for {spec['mod']}.
// Qud Shader Library effect: a full-screen pass over the map; every pixel visits every particle, each particle a
// deterministic function of its index and the library's clock. Plays by name "{name}"; see ShaderEffects.fragment.xml.
Shader "{shader_path}"
{{
    Properties {{ _MainTex ("Screen", 2D) = "white" {{}} }}
    SubShader
    {{
        ZTest Always Cull Off ZWrite Off
        Pass
        {{
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #pragma target 3.0
            #include "../QudFX.cginc"

            #define MAXP {MAX_PARTICLES}

            // Tunables with the spec's values baked in. Override from C# with ShaderFX.Set("_Count", 24f) or from a
            // preset with <float Name="_Count" Value="24" /> / <color Name="_Tint" Value="#ff8800" />.
            float _Count = {f(e['count'])};      // particles in flight (max MAXP)
            float _Scale = 1.0;                  // size multiplier
            float _Speed = 1.0;                  // speed multiplier
            float _Gravity = {f(e['gravity'])};  // screen heights per s^2, + is down
            float _Seed = {f(e['seed'])};
            float4 _Tint = float4(0, 0, 0, 0);   // alpha > 0 replaces the birth colour
            float4 _Tint2 = float4(0, 0, 0, 0);  // alpha > 0 replaces the death colour

            float prand(float i, float k) {{ return hash(float2(i * 1.6180339 + _Seed * 7.13, k * 3.71 + 0.5)); }}

            float4 frag(v2f_img i) : SV_Target
            {{
                float2 vUv = float2(i.uv.x, 1.0 - i.uv.y);
                float2 asp = float2(_Aspect, 1.0);         // square space: x scaled so circles stay round
                float2 A = ({anchor}) * asp;
                float2 P = vUv * asp;
                float3 c0 = _Tint.a > 0.0 ? _Tint.rgb : {f3(e['_c0'])};
                float3 c1 = _Tint2.a > 0.0 ? _Tint2.rgb : {f3(e['_c1'])};
                float3 glow = float3(0, 0, 0);
                float cover = 0.0;
                float2 disp = float2(0, 0);
                float n = min(_Count, (float)MAXP);

                [loop] for (int p = 0; p < MAXP; p++)
                {{
                    float fi = (float)p;
                    if (fi >= n) break;
                    float r0 = prand(fi, 0.0), r1 = prand(fi, 1.0);
                    {timing}
                    float r2 = prand(fj, 2.0), r3 = prand(fj, 3.0), r4 = prand(fj, 4.0), r5 = prand(fj, 5.0);
                    float r6 = prand(fj, 6.0), r7 = prand(fj, 7.0);
                    float tt = t * life;

                    {born}
                    {base}
                    float2 dir = rotv(base, radians((r2 - 0.5) * {f(e['spread'])}));
                    float spd = lerp({f(e['speed'][0])}, {f(e['speed'][1])}, r4) * _Speed;
                    {chr(10).join('                    ' + m for m in motion)}

                    float size = lerp({f(e['size'][0])}, {f(e['size'][1])}, r5) * _Scale * lerp(1.0, {f(e['endSize'])}, t);
                    {chr(10).join('                    ' + m for m in env)}
                    float2 dd = P - pos;
                    {kernel}
                    k *= env;
                    float3 c = lerp(c0, c1, t);
                    glow += c * k * {f(e['glow'])};
                    cover += k;
                    disp += dd * k;
                }}

                float3 col = tex(vUv - disp * {f(e['distort'])} / asp).rgb;
                {blend}
                return float4(col, 1.0);
            }}
            ENDCG
        }}
    }}
    Fallback Off
}}
"""
    return lines


# ------------------------------------------------------------------------------------------------- presets, usage

def preset_for(e: dict, spec: dict) -> dict:
    p = dict(e.get("preset") or {})
    p.setdefault("name", spec["presetPrefix"] + e["name"])
    p.setdefault("seconds", round(e["life"][1] + e["stagger"] + 0.3, 2) if e["mode"] == "burst" else 3.0)
    p.setdefault("amount", 1.25)
    p.setdefault("fadeIn", 0.0 if e["mode"] == "burst" else 0.35)
    p.setdefault("fadeOut", 0.3 if e["mode"] == "burst" else 0.6)
    p.setdefault("refire", 0)
    return p


def fragment_xml(spec: dict) -> str:
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           f'<!-- Generated by AAMT qud_particle_shader.py for {spec["mod"]}: merge into the mod\'s ShaderEffects.xml',
           f'     (the install step does this). The bundle line loads Bundles/windows/{spec["bundle"]}_windows. -->',
           "<shadereffects>",
           f'  <bundle Name="{spec["bundle"]}" />']
    for e in spec["effects"]:
        p = preset_for(e, spec)
        attrs = (f'Name="{p["name"]}" Shader="{e["name"]}" Seconds="{p["seconds"]}" Amount="{p["amount"]}" '
                 f'FadeIn="{p["fadeIn"]}" FadeOut="{p["fadeOut"]}" Refire="{p["refire"]}"')
        if p.get("layer"):
            attrs += f' Layer="{p["layer"]}"'
        out.append(f"  <preset {attrs} />")
    out.append("</shadereffects>")
    return "\n".join(out) + "\n"


def usage_snippet(spec: dict) -> str:
    wrapper = spec.get("wrapper") or "QudShaders.Play"
    lines = [f"// {spec['mod']}: how to play the generated particle presets (bundle {spec['bundle']}).",
             "// Presets are merged into the mod's ShaderEffects.xml by the install step and play by name:", ""]
    for e in spec["effects"]:
        p = preset_for(e, spec)
        lines.append(f'{wrapper}("{p["name"]}", cell);        // {e["mode"]} {e["shape"]}s: {e["name"]}')
    lines += ["", "// Raw shader with your own timing/strength, or tuned values:",
              f'QudShaders.Play(new ShaderFX("{spec["effects"][0]["name"]}").At(cell).For(2f).Strength(1.4f)'
              '.Set("_Count", 32f).Set("_Tint", new UnityEngine.Color(1f, 0.5f, 0.1f)));' if spec["effects"] else ""]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------------------------- library, lint

def find_shader_library(explicit: str | None = None) -> Path | None:
    """The Qud Shader Library mod folder (holds ShaderKit/QudFX.cginc and BuildQudFX.cs.txt)."""
    cands = []
    if explicit:
        cands.append(Path(explicit))
    if os.environ.get("QUD_SHADER_LIBRARY"):
        cands.append(Path(os.environ["QUD_SHADER_LIBRARY"]))
    settings = HERE.parent / "settings.json"
    game_root = None
    if settings.exists():
        try:
            s = json.loads(settings.read_text(encoding="utf-8-sig"))
            if s.get("shaderLibraryPath"):
                cands.append(Path(s["shaderLibraryPath"]))
            game_root = s.get("gameRoot")
        except Exception:
            pass
    if game_root:
        cands.append(Path(game_root).parent.parent / "workshop" / "content" / "333640" / SHADER_LIBRARY_WORKSHOP_ID)
    for lib in ("D:/games/Steam", "C:/Program Files (x86)/Steam", "E:/SteamLibrary", "D:/SteamLibrary", "C:/SteamLibrary"):
        cands.append(Path(lib) / "steamapps" / "workshop" / "content" / "333640" / SHADER_LIBRARY_WORKSHOP_ID)
    mods = Path(os.environ.get("COQ_MODS_ROOT") or (Path.home() / "AppData/LocalLow/Freehold Games/CavesOfQud/Mods"))
    cands.append(mods / "QudShaderLibrary")
    for c in cands:
        if (c / "ShaderKit" / "QudFX.cginc").exists():
            return c
    return None


def find_fxc() -> str | None:
    if os.environ.get("FXC") and Path(os.environ["FXC"]).exists():
        return os.environ["FXC"]
    hits = sorted(glob.glob(r"C:/Program Files (x86)/Windows Kits/10/bin/*/x64/fxc.exe"))
    if hits:
        return hits[-1]
    w = shutil.which("fxc")
    return w


def lint_shader(shader: Path, library: Path | None, workdir: Path) -> tuple[bool, str]:
    """Compile the fragment program with fxc (DX9 intrinsics on) against the real QudFX.cginc and a stub UnityCG."""
    fxc = find_fxc()
    if not fxc:
        return (True, "fxc not found (Windows SDK); lint skipped")
    if not library:
        return (True, "Qud Shader Library not found; lint skipped (set QUD_SHADER_LIBRARY)")
    workdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / "ShaderKit" / "QudFX.cginc", workdir / "QudFX.cginc")
    shutil.copy2(HERE / "lint" / "UnityCG.cginc", workdir / "UnityCG.cginc")
    src = shader.read_text(encoding="utf-8")
    m = re.search(r"CGPROGRAM(.*?)ENDCG", src, re.S)
    if not m:
        return (False, "no CGPROGRAM block")
    body = re.sub(r"^\s*#pragma .*$", "", m.group(1), flags=re.M)
    body = body.replace('#include "../QudFX.cginc"', '#include "QudFX.cginc"')
    hlsl = workdir / (shader.stem + ".hlsl")
    hlsl.write_text(body, encoding="utf-8")
    cso = workdir / (shader.stem + ".cso")
    cmd = [fxc, "/nologo", "/T", "ps_4_0", "/E", "frag", "/Gec", "/I", str(workdir), "/Fo", str(cso), str(hlsl)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    msg = (r.stdout + r.stderr).strip()
    msg = re.sub(r"^\s*warning X3206.*$", "", msg, flags=re.M)             # implicit truncation chatter
    msg = re.sub(r"^compilation object save succeeded.*$", "", msg, flags=re.M).strip()
    ok = r.returncode == 0 and cso.exists()
    return (ok, msg if msg else ("ok" if ok else "fxc failed"))


# --------------------------------------------------------------------------------------------------- preview (numpy)

def _np():
    try:
        import numpy as np
        from PIL import Image
        return np, Image
    except Exception as ex:   # pragma: no cover
        raise SystemExit(f"preview needs numpy and Pillow: {ex}")


def _hash_np(np, p):
    v = np.sin(p[..., 0] * 127.1 + p[..., 1] * 311.7) * 43758.5453
    return v - np.floor(v)


def _noise_np(np, p):
    i = np.floor(p)
    fr = p - i
    u = fr * fr * (3.0 - 2.0 * fr)
    def h(dx, dy):
        return _hash_np(np, i + np.stack([np.full_like(i[..., 0], dx), np.full_like(i[..., 1], dy)], -1))
    a, b, c, d = h(0, 0), h(1, 0), h(0, 1), h(1, 1)
    return (a + (b - a) * u[..., 0]) + ((c + (d - c) * u[..., 0]) - (a + (b - a) * u[..., 0])) * u[..., 1]


def _background(np, Image, mapshot: Path | None, W: int, H: int):
    if mapshot and mapshot.exists():
        im = Image.open(mapshot).convert("RGB").resize((W, H), Image.BILINEAR)
        return np.asarray(im).astype(np.float32) / 255.0
    bg = np.zeros((H, W, 3), np.float32)
    cw, ch = W / 80.0, H / 25.0
    ys, xs = np.mgrid[0:H, 0:W]
    cx, cy = np.floor(xs / cw), np.floor(ys / ch)
    r = _hash_np(np, np.stack([cx, cy], -1))
    floor = 0.04 + 0.03 * r[..., None]
    bg += floor
    glyph = (r > 0.82)[..., None] & ((xs % cw) > cw * 0.3)[..., None] & ((xs % cw) < cw * 0.7)[..., None] & ((ys % ch) > ch * 0.25)[..., None] & ((ys % ch) < ch * 0.8)[..., None]
    tint = np.stack([0.55 + 0.4 * r, 0.5 + 0.3 * (1 - r), 0.35 + 0.2 * r], -1)
    bg = np.where(glyph, tint, bg)
    return bg


def render_preview(e: dict, spec: dict, out_gif: Path, mapshot: Path | None, frames: int, fps: int, size: tuple[int, int],
                   anchor_uv=(0.5, 0.5)):
    """A numpy twin of hlsl_for: same randoms, timing, motion and kernels, so the GIF shows what the shader will draw."""
    np, Image = _np()
    W, H = size
    aspect = W / H
    bg = _background(np, Image, mapshot, W, H)
    ys, xs = np.mgrid[0:H, 0:W]
    P = np.stack([(xs + 0.5) / W * aspect, (ys + 0.5) / H], -1).astype(np.float32)   # square space
    A = np.array([anchor_uv[0] * aspect, anchor_uv[1]], np.float32)
    n = e["count"]
    idx = np.arange(n, dtype=np.float32)
    seed = e["seed"]

    def prand(i, k):
        return _hash_np(np, np.stack([i * 1.6180339 + seed * 7.13, np.full_like(i, k * 3.71 + 0.5)], -1))

    r0, r1 = prand(idx, 0.0), prand(idx, 1.0)
    life = e["life"][0] + (e["life"][1] - e["life"][0]) * r0
    p = preset_for(e, spec)
    total = float(p["seconds"]) if e["mode"] == "burst" else 2.0 * max(e["life"])
    frames_out = []
    c0 = np.array(e["_c0"], np.float32)
    c1 = np.array(e["_c1"], np.float32)
    for fr in range(frames):
        T = total * fr / max(1, frames - 1)
        env_amt = 1.25
        if e["mode"] == "burst":
            age = T - r1 * e["stagger"]
            t = age / life
            fj = idx
            env_amt *= 1.0 if T < total - float(p["fadeOut"]) else max(0.0, (total - T) / max(1e-3, float(p["fadeOut"])))
        else:
            phase = (T + r1 * life) / life
            t = phase - np.floor(phase)
            fj = idx + np.floor(phase) * 131.0
            env_amt *= min(1.0, T / max(1e-3, float(p["fadeIn"])))
        alive = (t >= 0) & (t <= 1)
        r2, r3, r4, r5, r6, r7 = (prand(fj, k) for k in (2.0, 3.0, 4.0, 5.0, 6.0, 7.0))
        tt = t * life
        em = e["emitter"]
        R = em["radius"]
        ang6 = r6 * 2 * np.pi
        if em["shape"] == "point":
            born = np.repeat(A[None], n, 0)
        elif em["shape"] == "ring":
            born = A + np.stack([np.cos(ang6), np.sin(ang6)], -1) * R
        elif em["shape"] == "disc":
            born = A + np.stack([np.cos(ang6), np.sin(ang6)], -1) * np.sqrt(r7)[:, None] * R
        elif em["shape"] == "cells":
            cellw, cellh = aspect / 80.0, 1.0 / 25.0
            bc = np.floor(A / [cellw, cellh]) + np.floor((np.stack([r6, r7], -1) - 0.5) * 2.0 * (R / 0.04) + 0.5)
            born = (bc + 0.5) * [cellw, cellh]
        else:
            born = np.stack([r6 * aspect, r7], -1)
        d = e["direction"]
        if d in ("radial", "inward"):
            bd = (born - A) if d == "radial" else (A - born)
            L = np.linalg.norm(bd, axis=-1, keepdims=True)
            rnd = np.stack([np.cos(r3 * 2 * np.pi), np.sin(r3 * 2 * np.pi)], -1)
            base = np.where(L > 1e-5, bd / np.maximum(L, 1e-9), rnd)
        else:
            a = math.radians(float(d))
            base = np.repeat(np.array([[math.cos(a), -math.sin(a)]], np.float32), n, 0)
        rot = np.radians((r2 - 0.5) * e["spread"])
        cs, sn = np.cos(rot), np.sin(rot)
        dirv = np.stack([cs * base[:, 0] + sn * base[:, 1], -sn * base[:, 0] + cs * base[:, 1]], -1)
        spd = e["speed"][0] + (e["speed"][1] - e["speed"][0]) * r4
        travel = (1 - np.exp(-e["drag"] * tt)) / e["drag"] if e["drag"] > 0 else tt
        pos = born + dirv * (spd * travel)[:, None]
        pos[:, 1] += 0.5 * e["gravity"] * tt * tt
        if e["swirl"] != 0:
            q = pos - A
            a2 = e["swirl"] * tt
            pos = A + np.stack([np.cos(a2) * q[:, 0] + np.sin(a2) * q[:, 1], -np.sin(a2) * q[:, 0] + np.cos(a2) * q[:, 1]], -1)
        if e["wobble"] != 0:
            nx = _noise_np(np, np.stack([fj * 3.1, tt * 2.0 + 7.0], -1))
            ny = _noise_np(np, np.stack([tt * 2.0, fj * 5.7 + 3.0], -1))
            pos += (np.stack([nx, ny], -1) - 0.5) * e["wobble"]
        if e["cellSnap"]:
            cellw, cellh = aspect / 80.0, 1.0 / 25.0
            pos = (np.floor(pos / [cellw, cellh]) + 0.5) * [cellw, cellh]
        sz = (e["size"][0] + (e["size"][1] - e["size"][0]) * r5) * (1.0 + (e["endSize"] - 1.0) * t)
        fi_, fo_ = max(e["fadeIn"], 1e-4), e["fadeOut"]
        def sstep(a, b, x):
            u = np.clip((x - a) / max(b - a, 1e-6), 0, 1)
            return u * u * (3 - 2 * u)
        env = sstep(0, fi_, t) * (1 - sstep(1 - fo_, 1, t))
        if e["flicker"] > 0:
            env *= (1 - e["flicker"]) + e["flicker"] * _noise_np(np, np.stack([np.full_like(fj, T * 14.0), fj * 0.37], -1))
        env = np.where(alive, env, 0.0).astype(np.float32)

        glow = np.zeros((H, W, 3), np.float32)
        cover = np.zeros((H, W), np.float32)
        disp = np.zeros((H, W, 2), np.float32)
        for j in np.nonzero(env > 1e-4)[0]:
            dd = P - pos[j]
            s = float(sz[j])
            if e["shape"] == "dot":
                q = (dd * dd).sum(-1)
                k = np.exp(-q / (s * s)) + 0.35 * np.exp(-q / (s * s * 0.15))
            elif e["shape"] == "spark":
                along = dd[..., 0] * dirv[j, 0] + dd[..., 1] * dirv[j, 1]
                perp = dd[..., 0] * dirv[j, 1] - dd[..., 1] * dirv[j, 0]
                k = np.exp(-(along * along / (s * s * e["stretch"] ** 2) + perp * perp / (s * s)))
            elif e["shape"] == "ring":
                rr = np.sqrt((dd * dd).sum(-1)) - s
                k = np.exp(-rr * rr / (s * s * 0.09))
            elif e["shape"] == "streak":
                tail = -dirv[j] * s * e["stretch"]
                h = np.clip((dd @ tail) / max(float(tail @ tail), 1e-6), 0, 1)
                seg = dd - tail[None, None] * h[..., None]
                k = np.exp(-(seg * seg).sum(-1) / (s * s * 0.3)) * (1 - 0.6 * h)
            else:
                ad = np.abs(dd).max(-1)
                k = 1 - sstep(s * 0.8, s, ad)
            k = (k * env[j]).astype(np.float32)
            c = c0 + (c1 - c0) * float(t[j])
            glow += k[..., None] * c * e["glow"]
            cover += k
            disp += dd * k[..., None]
        amt = env_amt
        shifted = bg
        if e["distort"] > 0:
            off = disp * e["distort"] / [aspect, 1.0]
            sx = np.clip(xs - off[..., 0] * W / aspect, 0, W - 1).astype(int)
            sy = np.clip(ys - off[..., 1] * H, 0, H - 1).astype(int)
            shifted = bg[sy, sx]
        if e["blend"] == "add":
            col = shifted + glow * amt
        elif e["blend"] == "alpha":
            col = shifted + (glow / np.maximum(cover, 1e-4)[..., None] - shifted) * (np.clip(cover, 0, 1) * min(amt, 1.0))[..., None]
        else:
            col = 1 - (1 - shifted) * (1 - np.clip(glow * amt, 0, 1))
        frames_out.append(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)))
    out_gif.parent.mkdir(parents=True, exist_ok=True)
    frames_out[0].save(out_gif, save_all=True, append_images=frames_out[1:], duration=int(1000 / fps), loop=0)
    return out_gif


# --------------------------------------------------------------------------------------------------------- install

def resolve_mod_path(spec: dict, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    if spec.get("modPath"):
        return Path(spec["modPath"])
    mods = Path(os.environ.get("COQ_MODS_ROOT") or (Path.home() / "AppData/LocalLow/Freehold Games/CavesOfQud/Mods"))
    return mods / (spec.get("modFolder") or spec["mod"])


def merge_shader_effects(mod_xml: Path, fragment: Path, force: bool) -> list[str]:
    """Text merge that keeps the mod's own comments and layout: adds the <bundle> line and any preset not yet present."""
    frag = fragment.read_text(encoding="utf-8")
    bundle = re.search(r'<bundle\s+Name="([^"]+)"', frag)
    presets = re.findall(r"^\s*<preset .*?/>\s*$", frag, flags=re.M)
    notes = []
    if not mod_xml.exists():
        mod_xml.write_text('<?xml version="1.0" encoding="utf-8"?>\n<shadereffects>\n</shadereffects>\n', encoding="utf-8")
        notes.append(f"created {mod_xml.name}")
    text = mod_xml.read_text(encoding="utf-8-sig")
    nl = "\r\n" if "\r\n" in text else "\n"
    if bundle and not re.search(rf'<bundle\s+Name="{re.escape(bundle.group(1))}"', text):
        text = re.sub(r"(<shadereffects[^>]*>)", lambda m: m.group(1) + nl + f'  <bundle Name="{bundle.group(1)}" />', text, count=1)
        notes.append(f"added bundle {bundle.group(1)}")
    for p in presets:
        name = re.search(r'Name="([^"]+)"', p).group(1)
        existing = re.search(rf'^\s*<preset\s+Name="{re.escape(name)}".*?/>\s*$', text, flags=re.M)
        if existing and not force:
            notes.append(f"kept existing preset {name}")
            continue
        if existing:
            text = text.replace(existing.group(0), "  " + p.strip(), 1)
            notes.append(f"replaced preset {name}")
        else:
            text = text.replace("</shadereffects>", "  " + p.strip() + nl + "</shadereffects>", 1)
            notes.append(f"added preset {name}")
    mod_xml.write_text(text, encoding="utf-8")
    return notes


def install(outdir: Path, mod_path: Path, force: bool) -> int:
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    bundle = manifest["bundle"]
    if not mod_path.exists():
        print(f"[ERROR] mod folder not found: {mod_path}")
        return 2
    copied = 0
    for plat in ("windows", "osx", "linux"):
        src = outdir / "Bundles" / plat / f"{bundle}_{plat}"
        if src.exists():
            dst = mod_path / "Bundles" / plat / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            for stray in dst.parent.glob("*.manifest"):
                stray.unlink()
            copied += 1
            print(f"[OK] {plat}: {dst}")
    if copied == 0:
        print(f"[WARN] no built bundle under {outdir / 'Bundles'}; run Build-QudShaderBundle.ps1 first "
              "(the presets are merged anyway and play once the bundle exists)")
    for note in merge_shader_effects(mod_path / "ShaderEffects.xml", outdir / "ShaderEffects.fragment.xml", force):
        print(f"[OK] ShaderEffects.xml: {note}")
    print("[OK] restart the game: ShaderEffects.xml is read once per launch")
    return 0


# ---------------------------------------------------------------------------------------------------------- draft

DRAFT_SYSTEM = """You design particle effects for a 2D top-down roguelike drawn as a grid of glyph tiles.
Answer with ONE JSON object only, no prose, following this schema exactly:
{"effects":[{"name":"Identifier","anchor":"focus|click|player","emitter":{"shape":"point|ring|disc|cells|screen","radius":0.0-0.4},
"mode":"burst|continuous","count":1-160,"life":[min,max seconds],"stagger":0-2,"direction":"radial|inward|degrees number (90 = up)",
"spread":0-360,"speed":[min,max screen heights per second; a map cell is 0.04],"gravity":number (+ down),"drag":0-6,"swirl":-6..6,
"wobble":0-0.05,"cellSnap":bool,"shape":"dot|spark|ring|streak|glyph","size":[min,max; 0.004 is a small mote, 0.02 half a cell],
"endSize":0-3,"stretch":1-8,"colors":["#rrggbb birth","#rrggbb death"],"glow":0.3-2,"blend":"add|alpha|screen",
"fadeIn":0-0.9,"fadeOut":0-0.9,"flicker":0-1,"distort":0-0.02}]}
Use one to three effects. Pick values that read on a dark map: additive glows for light, alpha for dust and debris."""


def draft_spec(description: str, model: str | None, url: str) -> dict:
    if not model:
        with urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=10) as r:
            tags = json.load(r).get("models", [])
        names = [t["name"] for t in tags]
        pref = [n for n in names if any(k in n.lower() for k in ("qwen2.5-coder", "codestral", "deepseek-coder", "llama3", "mistral"))]
        model = (pref or names or [None])[0]
        if not model:
            raise SystemExit("no Ollama models installed")
    body = json.dumps({"model": model, "system": DRAFT_SYSTEM, "prompt": description, "format": "json", "stream": False,
                       "options": {"temperature": 0.4}}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.load(r)["response"]
    data = json.loads(resp)
    if "effects" not in data:
        data = {"effects": [data]}
    return data


# ------------------------------------------------------------------------------------------------------------ CLI

def cmd_generate(args) -> int:
    spec_path = Path(args.spec).resolve()
    spec = load_spec(spec_path)
    if not spec["effects"]:
        print("[ERROR] the spec has no effects")
        return 2
    out = Path(args.out) if args.out else TOOLS_ROOT / "Output" / "QudShaderForge" / spec["bundle"]
    shaders = out / "shaders"
    shaders.mkdir(parents=True, exist_ok=True)
    library = find_shader_library(args.shader_library)
    print(f"[Info] spec {spec_path.name}: {len(spec['effects'])} effect(s), bundle {spec['bundle']}, out {out}")
    if library:
        print(f"[Info] Qud Shader Library: {library}")
    else:
        print("[WARN] Qud Shader Library not found; lint and bundle build need it (set QUD_SHADER_LIBRARY or settings.json shaderLibraryPath)")
    manifest = {"spec": str(spec_path), "mod": spec["mod"], "modFolder": spec.get("modFolder"), "modPath": spec.get("modPath"),
                "bundle": spec["bundle"], "shaderPath": spec["shaderPath"], "library": str(library) if library else None,
                "effects": [], "lint": {}}
    failures = 0
    for e in spec["effects"]:
        path = shaders / f"{e['name']}.shader"
        path.write_text(hlsl_for(e, spec), encoding="utf-8")
        p = preset_for(e, spec)
        manifest["effects"].append({"name": e["name"], "preset": p["name"], "shader": str(path)})
        print(f"[OK] {path.name}  ->  preset {p['name']}")
        if args.lint:
            ok, msg = lint_shader(path, library, out / "lint")
            manifest["lint"][e["name"]] = {"ok": ok, "message": msg}
            print(f"     lint: {'ok' if ok else 'FAILED'}" + ("" if msg in ("ok",) else f" - {msg}"))
            if not ok:
                failures += 1
        if args.preview:
            gif = out / "previews" / f"{e['name']}.gif"
            render_preview(e, spec, gif, Path(args.mapshot) if args.mapshot else None, args.frames, args.fps,
                           (args.width, int(round(args.width / 2.1333))))
            print(f"     preview: {gif}")
    (out / "ShaderEffects.fragment.xml").write_text(fragment_xml(spec), encoding="utf-8")
    (out / "usage.cs.txt").write_text(usage_snippet(spec), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] {out / 'ShaderEffects.fragment.xml'}")
    print(f"[OK] {out / 'manifest.json'}")
    if failures:
        print(f"[ERROR] {failures} shader(s) failed lint")
        return 1
    return 0


def cmd_lint(args) -> int:
    library = find_shader_library(args.shader_library)
    bad = 0
    for s in args.shaders:
        ok, msg = lint_shader(Path(s), library, Path(args.workdir) if args.workdir else TOOLS_ROOT / "Output" / "QudShaderForge" / "_lint")
        print(f"{'ok     ' if ok else 'FAILED '} {s}" + ("" if msg == "ok" else f"\n        {msg}"))
        bad += 0 if ok else 1
    return 1 if bad else 0


def cmd_preview(args) -> int:
    spec = load_spec(Path(args.spec).resolve())
    out = Path(args.out) if args.out else TOOLS_ROOT / "Output" / "QudShaderForge" / spec["bundle"]
    for e in spec["effects"]:
        gif = out / "previews" / f"{e['name']}.gif"
        render_preview(e, spec, gif, Path(args.mapshot) if args.mapshot else None, args.frames, args.fps,
                       (args.width, int(round(args.width / 2.1333))))
        print(f"[OK] {gif}")
    return 0


def cmd_install(args) -> int:
    out = Path(args.out).resolve()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    spec = {"mod": manifest["mod"], "modFolder": manifest.get("modFolder"), "modPath": manifest.get("modPath")}
    return install(out, resolve_mod_path(spec, args.mod_path), args.force)


def cmd_draft(args) -> int:
    data = draft_spec(args.describe, args.model, args.ollama_url)
    spec = {"mod": args.mod or "MyMod", "bundle": args.bundle or (re.sub(r"[^a-z0-9]", "", (args.mod or "mymod").lower()) + "_fx"),
            "presetPrefix": args.prefix or "", "effects": data["effects"]}
    # validate by loading through the same path the generator uses
    tmp = Path(args.out)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    try:
        loaded = load_spec(tmp)
    except Exception as ex:
        print(f"[WARN] the model's spec needed fixing: {ex}")
        return 1
    print(f"[OK] {tmp}: {', '.join(e['name'] for e in loaded['effects'])}")
    return 0


def cmd_schema(args) -> int:
    print(__doc__)
    print("Spec fields (top level):")
    print(json.dumps({k: v for k, v in SPEC_DEFAULTS.items() if k != "effects"}, indent=2))
    print("\nEffect fields and defaults:")
    print(json.dumps(EFFECT_DEFAULTS, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qud particle shader pipeline (AAMT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="spec -> shaders, presets, usage, previews")
    g.add_argument("spec")
    g.add_argument("--out")
    g.add_argument("--lint", action="store_true")
    g.add_argument("--preview", action="store_true")
    g.add_argument("--mapshot", help="PNG from the library's `shader mapshot` wish, used as the preview background")
    g.add_argument("--frames", type=int, default=24)
    g.add_argument("--fps", type=int, default=12)
    g.add_argument("--width", type=int, default=480)
    g.add_argument("--shader-library")
    g.set_defaults(fn=cmd_generate)
    l = sub.add_parser("lint", help="fxc-compile .shader files offline")
    l.add_argument("shaders", nargs="+")
    l.add_argument("--workdir")
    l.add_argument("--shader-library")
    l.set_defaults(fn=cmd_lint)
    p = sub.add_parser("preview", help="GIF previews only")
    p.add_argument("spec")
    p.add_argument("--out")
    p.add_argument("--mapshot")
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--width", type=int, default=480)
    p.set_defaults(fn=cmd_preview)
    i = sub.add_parser("install", help="copy the built bundle into the mod and merge presets")
    i.add_argument("out")
    i.add_argument("--mod-path")
    i.add_argument("--force", action="store_true", help="replace presets that already exist in the mod")
    i.set_defaults(fn=cmd_install)
    d = sub.add_parser("draft", help="Ollama drafts a spec from a description")
    d.add_argument("--describe", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--mod")
    d.add_argument("--bundle")
    d.add_argument("--prefix")
    d.add_argument("--model")
    d.add_argument("--ollama-url", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    d.set_defaults(fn=cmd_draft)
    s = sub.add_parser("schema", help="print the spec reference")
    s.set_defaults(fn=cmd_schema)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as ex:
        print(f"[ERROR] {ex}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
