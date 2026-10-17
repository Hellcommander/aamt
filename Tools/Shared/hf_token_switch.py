#!/usr/bin/env python3
"""Hugging Face auth for AAMT tools.

Uses whatever this machine is already logged in with (`hf auth login`, or an
HF_TOKEN you set yourself). Nothing account-specific lives in this repo: no token
names, no profiles, no secrets.

The old profile names ("media", "training", ...) are still accepted so existing
callers keep working, but every profile resolves to the same login.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

_LOGIN_LABEL = "hf login"
_ACTIVE: Optional[str] = None


def _hub_token() -> Optional[str]:
    """The token huggingface_hub would use: HF_TOKEN env, else the `hf auth login` store."""
    try:
        from huggingface_hub import get_token

        return get_token() or None
    except Exception:
        return None


def _profile_login_token() -> Optional[str]:
    """`hf auth login` token in the default %USERPROFILE%\\.cache\\huggingface.

    Needed when a script moved HF_HOME (weights drive), which hides the login file."""
    try:
        from pathlib import Path

        f = Path.home() / ".cache" / "huggingface" / "token"
        if f.is_file():
            return f.read_text(encoding="utf-8").strip() or None
    except OSError:
        pass
    return None


def _login_token() -> Optional[str]:
    return _hub_token() or _profile_login_token()


def use_token_profile(profile: str = "default", *, quiet: bool = False) -> str:
    """Confirm a Hugging Face login exists and return its label.

    huggingface_hub reads the login by itself, so the token is only exported (as
    HF_TOKEN, this process only) when HF_HOME was moved and the login file is hidden.
    `profile` is accepted for backward compatibility and ignored.
    """
    global _ACTIVE
    token = _login_token()
    if not token:
        raise RuntimeError(
            "No Hugging Face login found. Run `hf auth login` (or set HF_TOKEN), then retry."
        )
    if not _hub_token():
        os.environ["HF_TOKEN"] = token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    _ACTIVE = _LOGIN_LABEL
    if not quiet:
        print(f"[HF] Using the existing Hugging Face login (profile {profile!r} ignored)")
    return _ACTIVE


def use_media_token(*, quiet: bool = False) -> str:
    return use_token_profile("media", quiet=quiet)


def use_training_token(*, quiet: bool = False) -> str:
    return use_token_profile("training", quiet=quiet)


def active_token_name() -> Optional[str]:
    return _ACTIVE


def list_stored_token_names() -> list[str]:
    """Display names of tokens saved by `hf auth login` (names only, never values)."""
    try:
        from huggingface_hub.utils._auth import get_stored_tokens

        return sorted((get_stored_tokens() or {}).keys())
    except Exception:
        return []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AAMT Hugging Face login check")
    parser.add_argument("profile", nargs="?", default="default", help="ignored; kept for old callers")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--print-env",
        action="store_true",
        help="Print NAME=value lines for PowerShell to apply (includes HF_TOKEN; do not log)",
    )
    args = parser.parse_args()
    try:
        name = use_token_profile(args.profile, quiet=True)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    if args.print_env:
        token = _login_token() or ""
        print(f"AAMT_HF_ACTIVE_TOKEN_NAME={name}")
        print(f"HF_TOKEN={token}")
        print(f"HUGGING_FACE_HUB_TOKEN={token}")
    elif not args.quiet:
        print(name)
