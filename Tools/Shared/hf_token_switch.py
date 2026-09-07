#!/usr/bin/env python3
"""
AAMT Hugging Face token auto-switch (by display name only).

Tokens live in `%USERPROFILE%\\.cache\\huggingface\\stored_tokens` **or** `hf_home()/stored_tokens` (`D:\\hf-cache`, INI sections). Never commit secrets.
Tools call use_token_profile(\"media\") or use_token_profile(\"training\") before HF downloads/training.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

# Purpose -> Hugging Face token *display name* (as saved by `hf auth login`)
DEFAULT_PROFILES: Dict[str, str] = {
    # SD3.5 / Stable Audio gated downloads
    "media": "SD3.5 Token",
    "sd": "SD3.5 Token",
    "stable-audio": "SD3.5 Token",
    "sd35": "SD3.5 Token",
    # Primordialis / custom LoRA training forks
    "training": "Custom Modul for creation",
    "primordialis": "Custom Modul for creation",
    "lora": "Custom Modul for creation",
    "peft": "Custom Modul for creation",
}

_ACTIVE_PROFILE: Optional[str] = None
_ACTIVE_TOKEN_NAME: Optional[str] = None


def _stored_token_files() -> list[Path]:
    """HF_HOME may be D:\\hf-cache (weights) while `hf auth login` wrote to %USERPROFILE%."""
    candidates = [
        Path.home() / ".cache" / "huggingface" / "stored_tokens",
    ]
    user = os.environ.get("USERPROFILE")
    if user:
        candidates.append(Path(user) / ".cache" / "huggingface" / "stored_tokens")
    hf = os.environ.get("HF_HOME")
    if hf:
        hp = Path(hf)
        candidates.append(hp / "stored_tokens")
        candidates.append(hp / ".cache" / "huggingface" / "stored_tokens")
    try:
        from tool_paths import hf_home

        candidates.append(hf_home() / "stored_tokens")
    except Exception:
        candidates.append(Path(r"D:\hf-cache") / "stored_tokens")
    seen: set[str] = set()
    out: list[Path] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _tokens_from_files() -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for path in _stored_token_files():
        if not path.is_file():
            continue
        text = ""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            data = json.loads(text)
        except Exception:
            data = None
        if isinstance(data, dict):
            for name, token in data.items():
                if name and token and str(name) not in merged:
                    merged[str(name)] = str(token)
            continue
        # huggingface_hub stored_tokens is INI: [Display Name] / hf_token = ...
        try:
            import configparser

            cfg = configparser.ConfigParser()
            cfg.read_string(text)
            for name in cfg.sections():
                token = cfg.get(name, "hf_token", fallback="") or cfg.get(name, "token", fallback="")
                if name and token and name not in merged:
                    merged[name] = token
        except Exception:
            continue
    return merged


def list_stored_token_names() -> list[str]:
    names: list[str] = []
    try:
        from huggingface_hub.utils._auth import get_stored_tokens

        stored = get_stored_tokens() or {}
        names.extend(str(k) for k in stored.keys())
    except Exception:
        pass
    for name in _tokens_from_files():
        if name not in names:
            names.append(name)
    return names


def get_token_by_name(token_name: str) -> Optional[str]:
    if not token_name:
        return None
    try:
        from huggingface_hub.utils._auth import _get_token_by_name

        hit = _get_token_by_name(token_name)
        if hit:
            return hit
    except Exception:
        pass
    return _tokens_from_files().get(token_name)


def resolve_token_name(profile: str) -> str:
    """Map profile alias -> stored token display name. Env overrides win."""
    key = (profile or "").strip().lower()
    env_map = {
        "media": os.environ.get("AAMT_HF_TOKEN_MEDIA"),
        "sd": os.environ.get("AAMT_HF_TOKEN_MEDIA"),
        "stable-audio": os.environ.get("AAMT_HF_TOKEN_MEDIA"),
        "sd35": os.environ.get("AAMT_HF_TOKEN_MEDIA"),
        "training": os.environ.get("AAMT_HF_TOKEN_TRAINING"),
        "primordialis": os.environ.get("AAMT_HF_TOKEN_TRAINING"),
        "lora": os.environ.get("AAMT_HF_TOKEN_TRAINING"),
        "peft": os.environ.get("AAMT_HF_TOKEN_TRAINING"),
    }
    if key in env_map and env_map[key]:
        return env_map[key]
    if os.environ.get("AAMT_HF_TOKEN_NAME") and key in ("", "default", "active"):
        return os.environ["AAMT_HF_TOKEN_NAME"]
    return DEFAULT_PROFILES.get(key, profile)


def use_token_profile(profile: str, *, quiet: bool = False) -> str:
    """
    Activate a named HF token for this process via HF_TOKEN.
    Returns the token display name used.
    """
    global _ACTIVE_PROFILE, _ACTIVE_TOKEN_NAME
    token_name = resolve_token_name(profile)
    token = get_token_by_name(token_name)
    if not token:
        names = list_stored_token_names()
        raise RuntimeError(
            f"HF token named {token_name!r} not found in stored_tokens. "
            f"Available: {names or '(none — run hf auth login)'}"
        )
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token  # older libs
    os.environ["AAMT_HF_ACTIVE_TOKEN_NAME"] = token_name
    os.environ["AAMT_HF_ACTIVE_PROFILE"] = profile
    _ACTIVE_PROFILE = profile
    _ACTIVE_TOKEN_NAME = token_name
    if not quiet:
        print(f"[HF] Using token profile {profile!r} -> {token_name!r}")
    return token_name


def use_media_token(*, quiet: bool = False) -> str:
    return use_token_profile("media", quiet=quiet)


def use_training_token(*, quiet: bool = False) -> str:
    return use_token_profile("training", quiet=quiet)


def active_token_name() -> Optional[str]:
    return _ACTIVE_TOKEN_NAME or os.environ.get("AAMT_HF_ACTIVE_TOKEN_NAME")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AAMT HF token profile switch")
    parser.add_argument("profile", help="media | training | primordialis | …")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--print-env",
        action="store_true",
        help="Print NAME=value lines for PowerShell to apply (includes HF_TOKEN)",
    )
    args = parser.parse_args()
    name = use_token_profile(args.profile, quiet=True)
    if args.print_env:
        token = os.environ["HF_TOKEN"]
        # Machine-local only; callers must not log this output
        print(f"AAMT_HF_ACTIVE_TOKEN_NAME={name}")
        print(f"AAMT_HF_ACTIVE_PROFILE={args.profile}")
        print(f"HF_TOKEN={token}")
        print(f"HUGGING_FACE_HUB_TOKEN={token}")
    elif not args.quiet:
        print(name)
