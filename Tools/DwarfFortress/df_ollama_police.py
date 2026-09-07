#!/usr/bin/env python3
"""
Optional Ollama critique of a DF creature body plan.

Soft-skips (returns skipped JSON + heuristics) when Ollama is missing,
unreachable, or slow — never crashes the CLI. Uses a short direct HTTP
call (avoids Shared GPU-hub locks that can hang smoke tests).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
_SHARED = _HERE.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

OLLAMA_API = (os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
POLICE_TIMEOUT_SEC = float(os.environ.get("AAMT_DF_POLICE_TIMEOUT", "12"))
FORCE_HEURISTIC = (os.environ.get("AAMT_DF_POLICE_HEURISTIC") or "").strip() in ("1", "true", "yes")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _heuristic_suggestions(spec: Dict[str, Any], cost: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    suggestions: List[Dict[str, str]] = []
    frags = [str(f).upper() for f in (spec.get("body_fragments") or [])]
    frag_set = set(frags)

    if spec.get("site_controllable") and not any(f.startswith("HUMANOID") for f in frag_set):
        suggestions.append(
            {
                "code": "PLAYABLE_SHAPE",
                "severity": "warning",
                "message": "Site-controllable civ without a HUMANOID* body may feel awkward in fortress mode.",
                "suggestion": "Prefer humanoid_civ or winged_humanoid preset for playable civs.",
            }
        )

    if "2WINGS" in frag_set:
        suggestions.append(
            {
                "code": "WINGS_NOTE",
                "severity": "info",
                "message": "2WINGS present; ensure FLIER semantics match your intent.",
                "suggestion": "Consider HUMANOID_NECK_FLIER or documenting flight limits in description.",
            }
        )

    if spec.get("graphics_profile") == "humanoid" and any(
        f.startswith("INSECT") or f.startswith("SPIDER") for f in frag_set
    ):
        suggestions.append(
            {
                "code": "GFX_PROFILE",
                "severity": "warning",
                "message": "Insectoid body with humanoid graphics profile.",
                "suggestion": "Switch graphics_profile to simple or use a humanoid body preset.",
            }
        )

    if cost:
        axes = cost.get("axes") or {}
        role = cost.get("role")
        if role:
            suggestions.append(
                {
                    "code": "COST_ROLE",
                    "severity": "info",
                    "message": f"Heuristic gameplay role: {role}",
                    "suggestion": f"Axes energy={axes.get('energy')} offense={axes.get('offense')} defense={axes.get('defense')} utility={axes.get('utility')}",
                }
            )
        if int(axes.get("energy") or 0) >= 70 and int(axes.get("utility") or 0) < 45:
            suggestions.append(
                {
                    "code": "ENERGY_COST",
                    "severity": "warning",
                    "message": "High energy cost vs utility — consider fewer limbs/wings or more grasp/sapience payoff.",
                    "suggestion": "Reduce FLIER/limb count or increase intelligent/equips utility.",
                }
            )
        for w in cost.get("warnings") or []:
            if isinstance(w, dict) and w.get("code") in ("THOUGHT_EXPOSED", "HEART_ON_LIMB", "EVO_JUMP"):
                suggestions.append(
                    {
                        "code": str(w.get("code")),
                        "severity": str(w.get("severity") or "warning"),
                        "message": str(w.get("message") or ""),
                        "suggestion": str(w.get("suggestion") or "See cost_report.json"),
                    }
                )

    if not suggestions:
        suggestions.append(
            {
                "code": "OK",
                "severity": "info",
                "message": "Heuristic check found no major body-plan concerns.",
                "suggestion": "Optional: add a distinctive BODYGLOSS or prefstring for cultural flavor.",
            }
        )
    return suggestions


def _ollama_tags_ok(timeout: float = 2.0) -> bool:
    try:
        import urllib.request

        req = urllib.request.Request(f"{OLLAMA_API}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return bool(data.get("models"))
    except Exception:
        return False


def _pick_model() -> str:
    env = (os.environ.get("AAMT_DF_POLICE_MODEL") or "").strip()
    if env:
        return env
    try:
        import urllib.request

        req = urllib.request.Request(f"{OLLAMA_API}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        names = [m.get("name") for m in data.get("models") or [] if m.get("name")]
        for prefer in ("llama3.2:3b", "llama3.2", "llama3.1:8b", "qwen2.5:3b", "mistral"):
            for n in names:
                if n == prefer or n.startswith(prefer.split(":")[0]):
                    return n
        return names[0] if names else "llama3.2:3b"
    except Exception:
        return "llama3.2:3b"


def _call_ollama_http(prompt: str, system: str) -> Optional[str]:
    """Direct /api/chat with short timeout — does not use Shared GPU hub."""
    import urllib.error
    import urllib.request

    model = _pick_model()
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.2, "num_predict": 400},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_API}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=POLICE_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        msg = (data.get("message") or {}).get("content")
        return msg if isinstance(msg, str) else None
    except Exception:
        return None


def police_body_plan(
    spec: Dict[str, Any],
    *,
    validation: Optional[Dict[str, Any]] = None,
    timeout_note: bool = True,
) -> Dict[str, Any]:
    """
    Critique body plan; return suggestions JSON.

    Always returns:
      { skipped, reason, suggestions, raw, source }
    """
    base: Dict[str, Any] = {
        "skipped": False,
        "reason": None,
        "suggestions": [],
        "raw": None,
        "source": "ollama",
    }

    cost_report = None
    if validation and isinstance(validation.get("cost"), dict):
        cost_report = validation["cost"]
    else:
        try:
            from df_body_cost import analyze_costs

            cost_report = analyze_costs(spec, full=True)
        except Exception:
            cost_report = None

    if FORCE_HEURISTIC:
        base["skipped"] = True
        base["reason"] = "AAMT_DF_POLICE_HEURISTIC set"
        base["source"] = "heuristic"
        base["suggestions"] = _heuristic_suggestions(spec, cost_report)
        if timeout_note:
            print(f"[police] Soft-skip Ollama ({base['reason']}); using heuristics.")
        return base

    if not _ollama_tags_ok():
        base["skipped"] = True
        base["reason"] = "Ollama not reachable or no models"
        base["source"] = "heuristic"
        base["suggestions"] = _heuristic_suggestions(spec, cost_report)
        if timeout_note:
            print(f"[police] Soft-skip Ollama ({base['reason']}); using heuristics.")
        return base

    payload = {
        "id": spec.get("id"),
        "name": spec.get("name_singular"),
        "body_fragments": spec.get("body_fragments"),
        "detail_plans": spec.get("detail_plans"),
        "intelligent": spec.get("intelligent"),
        "equips": spec.get("equips"),
        "can_open_doors": spec.get("can_open_doors"),
        "site_controllable": spec.get("site_controllable"),
        "graphics_profile": spec.get("graphics_profile"),
        "culture_preset": spec.get("culture_preset"),
        "validation": validation,
        "cost": {
            "role": (cost_report or {}).get("role"),
            "axes": (cost_report or {}).get("axes"),
        }
        if cost_report
        else None,
    }
    system = (
        "You are a Dwarf Fortress raws expert. Critique creature body plans for "
        "playability, anatomy completeness, graphics profile fit, and heuristic "
        "energy/role balance. "
        "Respond with ONLY JSON: "
        '{"suggestions":[{"code":"...","severity":"info|warning|error",'
        '"message":"...","suggestion":"..."}]}'
    )
    prompt = (
        "Critique this AAMT creature.json body plan for DF Premium:\n"
        + json.dumps(payload, indent=2)
        + "\n\nReturn JSON suggestions only."
    )

    raw = _call_ollama_http(prompt, system)
    base["raw"] = raw
    if not raw:
        base["skipped"] = True
        base["reason"] = f"Ollama chat timed out or failed (>{POLICE_TIMEOUT_SEC}s)"
        base["source"] = "heuristic"
        base["suggestions"] = _heuristic_suggestions(spec, cost_report)
        if timeout_note:
            print(f"[police] Soft-skip Ollama ({base['reason']}); using heuristics.")
        return base

    parsed = _extract_json(raw)
    if parsed and isinstance(parsed.get("suggestions"), list):
        base["suggestions"] = parsed["suggestions"]
        return base

    base["skipped"] = True
    base["reason"] = "Could not parse Ollama JSON; using heuristics"
    base["source"] = "heuristic+ollama_raw"
    base["suggestions"] = _heuristic_suggestions(spec, cost_report)
    if timeout_note:
        print(f"[police] {base['reason']}")
    return base


def main() -> int:
    import argparse
    from df_creature_schema import load_spec

    ap = argparse.ArgumentParser(description="Ollama body-plan police")
    ap.add_argument("--spec", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(police_body_plan(load_spec(args.spec)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
