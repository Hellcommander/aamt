"""Download the models the audio tools use, from Hugging Face, into the normal HF cache (sign in first: `hf auth login`).

    python download_audio_models.py            # the listeners (CPU): needed by the bench, agent, rebuild and remake tools
    python download_audio_models.py --sa3      # also Stable Audio 3 medium (GPU; a gated model: accept its terms on the
                                               # model page with the signed-in account first)
    python download_audio_models.py --list     # what each model is for, and whether it is already here

Models:
  laion/clap-htsat-unfused   the listener inside every loop (audio_listener.Listener, library search)       ~0.6 GB
  laion/larger_clap_general  the second judge: scores finished takes only, never steers (Listener.second)  ~0.8 GB
  stabilityai/stable-audio-3-medium  generation for packs whose terms allow AI tools (sfx_unique, --sa3)   large

Only weights and configs are fetched (safetensors, json, tokenizer files), never pickled .bin/.ckpt copies.
"""
import argparse
import sys

LISTENERS = [
    ("laion/clap-htsat-unfused", "listener inside every loop"),
    ("laion/larger_clap_general", "second judge, finished takes only"),
]
SA3 = [("stabilityai/stable-audio-3-medium", "Stable Audio 3 generation (gated: accept its terms first)")]
PATTERNS = ["*.json", "*.safetensors", "*.txt", "*.model", "*.md", "merges.txt", "vocab.json", "*.yaml"]


def have(repo):
    """'here', 'partly' (in the cache with missing files: run the download again) or 'missing'."""
    from huggingface_hub import scan_cache_dir
    try:
        info = scan_cache_dir()
    except Exception:
        return "missing"
    if any(r.repo_id == repo for r in info.repos):
        return "here"
    folder = "models--" + repo.replace("/", "--")
    return "partly" if any(folder in str(w) for w in info.warnings) else "missing"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sa3", action="store_true", help="also download Stable Audio 3 medium")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    try:
        from huggingface_hub import snapshot_download, whoami
    except ImportError:
        print("huggingface_hub is missing: pip install huggingface_hub"); return 1
    models = LISTENERS + (SA3 if a.sa3 else [])
    if a.list:
        for repo, why in LISTENERS + SA3:
            print(f"{have(repo):8s} {repo:38s} {why}")
        return 0
    try:
        print(f"signed in to Hugging Face as {whoami()['name']}")
    except Exception:
        print("not signed in to Hugging Face: the public listeners still download; Stable Audio 3 needs `hf auth login`")
    failed = 0
    for repo, why in models:
        print(f"{repo} ({why}) ...", flush=True)
        try:
            path = snapshot_download(repo, allow_patterns=PATTERNS)
            print(f"  ok: {path}")
        except Exception as e:
            failed += 1
            print(f"  FAILED: {e}")
            if "gated" in str(e).lower() or "401" in str(e) or "403" in str(e):
                print(f"  open https://huggingface.co/{repo} with the signed-in account and accept its terms, then run this again")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
