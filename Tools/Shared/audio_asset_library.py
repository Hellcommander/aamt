#!/usr/bin/env python3
"""Purchased/made audio library → queryable conditioning space.

Turns zip packs (and loose files) under audio_library_dir() into a catalog with
tag, spectral, and optional CLAP embeddings so an agent can retrieve, blend,
and condition generation on real assets instead of hallucinating SFX.

Default library: D:\\assets\\audio
Default index:   D:\\assets\\audio\\_aamt_index
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif", ".m4a"}
SKIP_DIR_PARTS = {"__macosx", "_aamt_index", ".ds_store"}
INDEX_VERSION = 1
FINGERPRINT_DIM = 64
EMBED_SECONDS = 8.0
EMBED_SR = 16000
CLAP_SR = 48000

# Pack-name → sound archetypes the AI can request by tag.
ARCHETYPE_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("laser", ("lightgun", "futurgun", "gun reload", "electric spell", "electric")),
    ("ui", ("interface", "button", "inventory", "flashlight", "uiactivation", "puzzle")),
    ("alien", ("alien", "creature", "beast", "monster", "unseen", "insects", "microscale", "bugs")),
    ("mech", ("cyborg", "robotic", "ancientmechanism", "metallic", "steam", "hybrid")),
    ("ship", ("spaceship", "cynetic", "door", "protocol", "warhorn")),
    ("magic", ("spell", "thunder", "chaos", "portal", "magic", "stinger")),
    ("ambience", ("wind", "darkbackground", "breathing", "doom", "uneasy", "tension", "textures", "nerve")),
    ("voice", ("voices", "zombie", "book")),
    ("impact", ("rocks", "glass", "boom", "whoosh", "smash", "rip", "swords")),
    ("organic", ("flesh", "blood", "slimy", "dragon", "crow", "horse", "footstep", "wood", "wings")),
    # Bodily waste / gas DNA (e.g. Dark Fantasy Studio Farts!). Reference-only:
    # unique SA3 must transform these for SFMAG crapping / accident SFX — never ship
    # pack WAVs or near copies into Data/Sound.
    ("bodily", ("fart", "farts", "flatulen", "bowel", "gas release", "poop", "toilet", "defecat")),
    ("horror", ("agony", "horror", "ghostly", "madness", "hostile")),
    ("water", ("water", "ice", "mud")),
    ("fire", ("fire",)),
)

# Pack license tiers, from the license files next to the packs in D:\assets\audio:
#   direct    — royalty-free use inside a game/project (Function Loops bt25 bundle,
#               via Humble; Tao & Sound $5 bundle: Magic Spells / Inventory / Puzzle
#               Audio Kit / Buttons). Close-copy allowed, but AAMT still alters every
#               clip before it ships so no original can be pulled out of a mod.
#   reference — Noise Alchemy EULA (Dark Fantasy Studio packs are Noise Alchemy's),
#               and any pack without its own license file: DNA only — never ship raw or slightly modified
#               clips, and credit NOISE_ALCHEMY_CREDIT once in the project.
#   own       — audio we made (D:\assets\audio\made, filled by `--keep`): ships and
#               is reused as-is. Its sidecar .meta.json carries any credit still owed.
DIRECT_USE_PACKS = ("magicspellssfxbundle", "inventorysfxbundle", "puzzleaudiokit", "buttonssfxlibrary")
DIRECT_USE_DIRS = ("bt25_ultimatesfxforgames_softwarebundle",)
OWN_DIR = "made"
NOISE_ALCHEMY_CREDIT = "Sound effects created with NOISE ALCHEMY – NOISEALCHEMY.COM"


def _library_dir() -> Path:
    try:
        from tool_paths import audio_library_dir

        return audio_library_dir()
    except Exception:
        return Path(os.environ.get("AAMT_AUDIO_LIBRARY_DIR", r"D:\assets\audio"))


def _index_dir() -> Path:
    try:
        from tool_paths import audio_index_dir

        return audio_index_dir()
    except Exception:
        return _library_dir() / "_aamt_index"


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t and len(t) > 1]


def _pack_stem(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"(?i)^dark fantasy studio-?\s*", "", stem)
    stem = re.sub(r"(?i)^noise alchemy-?\s*", "", stem)
    stem = re.sub(r"(?i)\s*sound fx pack.*$", "", stem)
    stem = re.sub(r"(?i)_audio$", "", stem)
    return stem.strip(" -_")


def infer_archetypes(*parts: str) -> List[str]:
    blob = " ".join(p.lower() for p in parts if p)
    hits: List[str] = []
    for archetype, needles in ARCHETYPE_RULES:
        if any(n in blob for n in needles):
            hits.append(archetype)
    return hits


def infer_tags(pack: str, inner: str) -> List[str]:
    tags = _tokenize(_pack_stem(pack)) + _tokenize(inner)
    blob = f"{pack} {inner}".lower()
    # Semantic aliases so retrieval finds DNA without naming pack files in prompts.
    if any(n in blob for n in ("fart", "flatulen", "bowel gas")):
        tags.extend(
            [
                "bodily",
                "gas",
                "flatulence",
                "waste",
                "organic",
                "accident",
                "crapping",
                "mess",
                "sfmag",
            ]
        )
    # Keep order, drop junk
    skip = {"wav", "mp3", "ogg", "flac", "stereo", "mono", "48k", "44k", "24bit", "16bit"}
    out: List[str] = []
    seen = set()
    for t in tags:
        if t in skip or t in seen or t.isdigit():
            continue
        seen.add(t)
        out.append(t)
    return out[:24]


def license_tier(pack: str, inner: str = "") -> str:
    """'own', 'direct' or 'reference' — see OWN_DIR / DIRECT_USE_PACKS / DIRECT_USE_DIRS."""
    head = inner.replace("\\", "/").split("/", 1)[0].lower()
    if head == OWN_DIR:
        return "own"
    if head in DIRECT_USE_DIRS:
        return "direct"
    stem = Path(pack).stem.lower()
    if any(stem.startswith(p) for p in DIRECT_USE_PACKS):
        return "direct"
    return "reference"


def asset_id(pack: str, inner: str) -> str:
    raw = f"{pack}::{inner}".encode("utf-8", errors="replace")
    return hashlib.sha1(raw).hexdigest()[:16]


@dataclass
class AssetRecord:
    id: str
    pack: str
    inner: str
    name: str
    tags: List[str] = field(default_factory=list)
    archetypes: List[str] = field(default_factory=list)
    duration: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    transcript: str = ""
    loop_like: bool = False
    source: str = "zip"  # zip | file

    def label(self) -> str:
        return f"{self.pack} :: {self.inner}"

    def license_tier(self) -> str:
        return license_tier(self.pack, self.inner)

    def search_text(self) -> str:
        bits = [self.name, _pack_stem(self.pack), " ".join(self.tags), " ".join(self.archetypes)]
        if self.transcript:
            bits.append(self.transcript)
        return " ".join(b for b in bits if b)


@dataclass
class RetrievalHit:
    record: AssetRecord
    score: float
    via: str


# ---------------------------------------------------------------------------
# decode / features
# ---------------------------------------------------------------------------


def _is_audio_name(name: str) -> bool:
    p = Path(name.replace("\\", "/"))
    if any(part.lower() in SKIP_DIR_PARTS for part in p.parts):
        return False
    if p.name.startswith("."):
        return False
    return p.suffix.lower() in AUDIO_EXTS


def _to_mono_float32(audio: Any) -> np.ndarray:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 2:
        # soundfile: (T, C); torchaudio: (C, T)
        arr = arr.mean(axis=1) if arr.shape[1] < arr.shape[0] else arr.mean(axis=0)
    return np.asarray(arr, dtype=np.float32).reshape(-1)


def _resample_audio(arr: np.ndarray, in_sr: int, sr: int) -> np.ndarray:
    """Resample without librosa/numba (torchaudio → scipy → linear)."""
    audio = np.asarray(arr, dtype=np.float32).reshape(-1)
    if int(in_sr) == int(sr) or audio.size == 0:
        return audio
    try:
        import torch
        import torchaudio

        wav = torch.from_numpy(audio).unsqueeze(0)
        out = torchaudio.functional.resample(wav, int(in_sr), int(sr))
        return out.squeeze(0).detach().cpu().numpy().astype(np.float32)
    except Exception:
        pass
    try:
        from scipy.signal import resample_poly

        g = int(np.gcd(int(in_sr), int(sr)))
        return np.asarray(
            resample_poly(audio, int(sr) // g, int(in_sr) // g),
            dtype=np.float32,
        )
    except Exception:
        pass
    n = max(1, int(round(audio.shape[0] * sr / float(in_sr))))
    x_old = np.linspace(0.0, 1.0, audio.shape[0], endpoint=False)
    x_new = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _decode_compressed(data: bytes) -> Tuple[np.ndarray, int]:
    """Decode MP3/OGG/M4A/etc from memory: PyAV (bundles FFmpeg), then torchcodec
    (needs a shared FFmpeg on PATH). No librosa/numba — avoids numpy pin fights."""
    errors: List[str] = []
    try:
        import av

        with av.open(io.BytesIO(data)) as container:
            stream = container.streams.audio[0]
            in_sr = int(stream.rate or 0)
            # Resampler normalizes any sample format/layout to float mono.
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=in_sr or None)
            chunks: List[np.ndarray] = []
            for frame in container.decode(stream):
                chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(frame))
            chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
        if not chunks or not in_sr:
            raise RuntimeError("no audio frames")
        return np.concatenate(chunks).astype(np.float32), in_sr
    except Exception as exc:
        errors.append(f"av: {exc}")
    try:
        from torchcodec.decoders import AudioDecoder

        samples = AudioDecoder(data).get_all_samples()  # (C, T) float32
        return _to_mono_float32(samples.data.numpy()), int(samples.sample_rate)
    except Exception as exc:
        errors.append(f"torchcodec: {exc}")
    raise RuntimeError("; ".join(errors))


def _decode_bytes(data: bytes, *, max_seconds: float = EMBED_SECONDS, sr: int = EMBED_SR) -> Tuple[np.ndarray, int]:
    """Return (samples,) float32 mono at `sr`, clipped to max_seconds."""
    bio = io.BytesIO(data)
    audio = None
    in_sr = sr
    try:
        import soundfile as sf

        audio, in_sr = sf.read(bio, dtype="float32", always_2d=False)
    except Exception:
        audio = None
    if audio is None:
        try:
            audio, in_sr = _decode_compressed(data)
        except Exception as exc:
            raise RuntimeError(f"decode failed: {exc}") from exc
    arr = _to_mono_float32(audio)
    if in_sr != sr and arr.size:
        arr = _resample_audio(arr, int(in_sr), int(sr))
        in_sr = sr
    max_n = int(max_seconds * in_sr)
    if arr.shape[0] > max_n:
        arr = arr[:max_n]
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if peak > 1e-8:
        arr = (arr / peak).astype(np.float32)
    return arr, int(in_sr)


def _wav_info(data: bytes) -> Tuple[float, int, int]:
    try:
        import soundfile as sf

        info = sf.info(io.BytesIO(data))
        return float(info.duration or 0.0), int(info.samplerate or 0), int(info.channels or 0)
    except Exception:
        pass
    # MP3 / formats soundfile cannot probe — PyAV header read (no decode)
    try:
        import av

        with av.open(io.BytesIO(data)) as container:
            stream = container.streams.audio[0]
            if stream.duration and stream.time_base:
                dur = float(stream.duration * stream.time_base)
            else:
                dur = float(container.duration or 0) / 1e6
            return dur, int(stream.rate or 0), int(stream.channels or 0)
    except Exception:
        return 0.0, 0, 0


def spectral_fingerprint(mono: np.ndarray, sr: int) -> np.ndarray:
    """64-d acoustic vector: log-band energies + envelope stats. CPU, no model."""
    y = np.asarray(mono, dtype=np.float32).ravel()
    if y.size < 32:
        return np.zeros(FINGERPRINT_DIM, dtype=np.float32)
    y = y - float(y.mean())
    n_fft = 1024
    hop = 256
    window = np.hanning(n_fft).astype(np.float32)
    frames = 1 + max(0, (y.size - n_fft) // hop)
    frames = min(frames, 256)
    mag = np.zeros((n_fft // 2, frames), dtype=np.float32)
    for i in range(frames):
        sl = y[i * hop : i * hop + n_fft]
        if sl.size < n_fft:
            sl = np.pad(sl, (0, n_fft - sl.size))
        spec = np.fft.rfft(sl * window)
        mag[:, i] = np.abs(spec[1 : n_fft // 2 + 1])
    # 40 log-spaced band means
    freqs = np.linspace(1, sr / 2.0, mag.shape[0], endpoint=False)
    edges = np.geomspace(40.0, max(80.0, sr / 2.0), 41)
    bands = np.zeros(40, dtype=np.float32)
    for b in range(40):
        mask = (freqs >= edges[b]) & (freqs < edges[b + 1])
        if not np.any(mask):
            continue
        bands[b] = float(np.log1p(mag[mask, :].mean()))
    rms_frames = np.sqrt((mag**2).mean(axis=0) + 1e-12)
    peak = float(np.max(np.abs(y)) + 1e-8)
    rms = float(np.sqrt(np.mean(y * y) + 1e-12))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(y)))))
    centroid = float((freqs[:, None] * mag).sum() / (mag.sum() + 1e-8))
    energy = mag.sum(axis=0) + 1e-8
    rolloff_idx = np.argmax(np.cumsum(mag, axis=0) > 0.85 * mag.sum(axis=0, keepdims=True), axis=0)
    rolloff = float(freqs[min(int(rolloff_idx.mean()), len(freqs) - 1)]) if rolloff_idx.size else 0.0
    attack = float(np.argmax(rms_frames) / max(1, rms_frames.size))
    decay = float(rms_frames[-1] / (float(rms_frames.max()) + 1e-8))
    extras = np.array(
        [
            np.log1p(peak),
            np.log1p(rms),
            zcr,
            np.log1p(centroid),
            np.log1p(rolloff),
            attack,
            decay,
            float(np.std(rms_frames)),
            float(np.percentile(rms_frames, 90)),
            float(y.size / float(sr)),
        ],
        dtype=np.float32,
    )
    vec = np.concatenate([bands, extras, np.zeros(14, dtype=np.float32)])[:FINGERPRINT_DIM]
    nrm = float(np.linalg.norm(vec))
    if nrm > 1e-8:
        vec = vec / nrm
    return vec.astype(np.float32)


def _hash_embed(text: str, dim: int = 384) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    toks = _tokenize(text)
    if not toks:
        return vec
    for i, tok in enumerate(toks):
        h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
        vec[h % dim] += 1.0 + 0.15 * (len(toks) - i) / len(toks)
        vec[(h // 7) % dim] += 0.35
    nrm = float(np.linalg.norm(vec))
    if nrm > 1e-8:
        vec = vec / nrm
    return vec


# ---------------------------------------------------------------------------
# optional model embedders (CPU by default — 11 GB GPU is for SA3)
# ---------------------------------------------------------------------------


class _ClapEmbedder:
    def __init__(self, device: str = "cpu"):
        self.ok = False
        self.device = device
        self.dim = 512
        self.model = None
        self.processor = None
        try:
            from hf_token_switch import use_media_token

            use_media_token(quiet=True)
        except Exception:
            pass
        try:
            import torch
            from transformers import ClapModel, ClapProcessor

            name = os.environ.get("AAMT_CLAP_MODEL", "laion/clap-htsat-unfused")
            self.processor = ClapProcessor.from_pretrained(name)
            self.model = ClapModel.from_pretrained(name).to(device).eval()
            self.dim = int(getattr(self.model.config, "projection_dim", 512) or 512)
            self._torch = torch
            self.target_sr = int(
                getattr(getattr(self.processor, "feature_extractor", None), "sampling_rate", CLAP_SR)
                or CLAP_SR
            )
            self.ok = True
        except Exception:
            self.ok = False

    def _resample(self, mono: np.ndarray, sr: int, target_sr: int) -> np.ndarray:
        return _resample_audio(mono, int(sr), int(target_sr))

    def _embedding_from_output(self, feat) -> np.ndarray:
        if hasattr(feat, "pooler_output") and feat.pooler_output is not None:
            tensor = feat.pooler_output
        elif isinstance(feat, (tuple, list)):
            tensor = feat[0]
        else:
            tensor = feat
        vec = tensor.detach().float().cpu().numpy().astype(np.float32).reshape(-1)
        nrm = float(np.linalg.norm(vec))
        return vec / nrm if nrm > 1e-8 else vec

    def audio(self, mono: np.ndarray, sr: int) -> Optional[np.ndarray]:
        if not self.ok:
            return None
        try:
            target_sr = int(getattr(self, "target_sr", CLAP_SR) or CLAP_SR)
            audio = self._resample(mono, sr, target_sr)
            try:
                inputs = self.processor(
                    audio=audio, sampling_rate=target_sr, return_tensors="pt", padding=True
                )
            except TypeError:
                inputs = self.processor(
                    audios=audio, sampling_rate=target_sr, return_tensors="pt", padding=True
                )
            kwargs = {}
            for key in ("input_features", "is_longer"):
                if key in inputs:
                    kwargs[key] = inputs[key].to(self.device)
            with self._torch.no_grad():
                feat = self.model.get_audio_features(**kwargs)
            vec = self._embedding_from_output(feat)
            self.dim = int(vec.shape[0])
            return vec
        except Exception:
            return None

    def text(self, query: str) -> Optional[np.ndarray]:
        if not self.ok:
            return None
        try:
            inputs = self.processor(text=[query], return_tensors="pt", padding=True)
            kwargs = {}
            for key in ("input_ids", "attention_mask", "position_ids"):
                if key in inputs:
                    kwargs[key] = inputs[key].to(self.device)
            with self._torch.no_grad():
                feat = self.model.get_text_features(**kwargs)
            vec = self._embedding_from_output(feat)
            self.dim = int(vec.shape[0])
            return vec
        except Exception:
            return None


class _TagEmbedder:
    def __init__(self):
        self.ok = False
        self.dim = 384
        self.model = None
        self.name = "hash-384"  # stored in catalog.json as tag_model
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            # sentence-transformers 6 renamed get_sentence_embedding_dimension
            get_dim = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
            self.dim = int(get_dim() or 384)
            self.name = "all-MiniLM-L6-v2"
            self.ok = True
        except Exception:
            self.ok = False

    def embed(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Sequence[str], batch_size: int = 128) -> np.ndarray:
        if self.ok:
            vecs = np.asarray(
                self.model.encode(list(texts), batch_size=batch_size, show_progress_bar=False),
                dtype=np.float32,
            ).reshape(len(texts), -1)
            nrm = np.linalg.norm(vecs, axis=1, keepdims=True)
            return (vecs / np.maximum(nrm, 1e-8)).astype(np.float32)
        return np.stack([_hash_embed(t, self.dim) for t in texts]).astype(np.float32)


class _Whisper:
    def __init__(self, model_name: str = "base"):
        self.ok = False
        self.model = None
        try:
            import whisper

            self.model = whisper.load_model(model_name, device="cpu")
            self.ok = True
        except Exception:
            self.ok = False

    def transcribe(self, mono: np.ndarray, sr: int) -> str:
        if not self.ok:
            return ""
        try:
            audio = mono.astype(np.float32)
            if sr != 16000:
                n = max(1, int(round(audio.shape[0] * 16000 / float(sr))))
                audio = np.interp(np.linspace(0, 1, n, endpoint=False), np.linspace(0, 1, audio.shape[0], endpoint=False), audio).astype(np.float32)
            result = self.model.transcribe(audio, fp16=False, language=None, verbose=False)
            return (result.get("text") or "").strip()
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# zip / file iteration
# ---------------------------------------------------------------------------


def _open_zip(path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(path, "r", allowZip64=True)


def iter_library_entries(root: Path) -> Iterable[Tuple[str, str, bytes, str]]:
    """Yield (pack, inner, bytes, source) for every audio clip under root."""
    root = Path(root)
    if not root.is_dir():
        return
    for zip_path in sorted(root.glob("*.zip")):
        pack = zip_path.name
        try:
            zf = _open_zip(zip_path)
        except zipfile.BadZipFile:
            print(f"  [audio-lib] skip bad zip: {pack}")
            continue
        with zf:
            for info in zf.infolist():
                if info.is_dir() or not _is_audio_name(info.filename):
                    continue
                low = info.filename.lower()
                if "reverse" in low or re.search(r"\brev\b", low):
                    continue
                try:
                    data = zf.read(info.filename)
                except Exception as exc:
                    print(f"  [audio-lib] read fail {pack}::{info.filename}: {exc}")
                    continue
                yield pack, info.filename.replace("\\", "/"), data, "zip"
    for p in sorted(root.rglob("*")):
        if not p.is_file() or not _is_audio_name(p.name):
            continue
        if "_aamt_index" in p.parts:
            continue
        if p.suffix.lower() == ".zip":
            continue
        rel = p.relative_to(root).as_posix()
        try:
            yield p.parent.name or "loose", rel, p.read_bytes(), "file"
        except Exception as exc:
            print(f"  [audio-lib] read fail {rel}: {exc}")


def load_asset_audio(record: AssetRecord, library: Optional[Path] = None, *, max_seconds: float = 30.0, sr: int = 48000) -> Tuple[np.ndarray, int]:
    """Load a catalogued clip as (samples, channels) float32 at `sr`."""
    library = Path(library or _library_dir())
    if record.source == "file":
        path = library / record.inner
        data = path.read_bytes()
    else:
        zpath = library / record.pack
        with _open_zip(zpath) as zf:
            data = zf.read(record.inner)
    mono, in_sr = _decode_bytes(data, max_seconds=max_seconds, sr=sr)
    # Return stereo-shaped [samples, 2] for generators
    stereo = np.stack([mono, mono], axis=1)
    return stereo.astype(np.float32), int(in_sr)


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------


class AudioLibrary:
    def __init__(self, library: Optional[Path] = None, index_dir: Optional[Path] = None):
        self.library = Path(library or _library_dir())
        self.index_dir = Path(index_dir or _index_dir())
        self.records: List[AssetRecord] = []
        self._by_id: Dict[str, int] = {}
        self.tag_vectors: Optional[np.ndarray] = None
        self.clap_vectors: Optional[np.ndarray] = None
        self.spectral: Optional[np.ndarray] = None
        self._clap: Optional[_ClapEmbedder] = None
        self._tags: Optional[_TagEmbedder] = None
        self._whisper: Optional[_Whisper] = None
        # Embedder that built tag.npy; "" = legacy index from before this was recorded.
        self.tag_model: str = ""

    def status(self) -> Dict[str, Any]:
        self.load()
        packs = sorted({r.pack for r in self.records})
        return {
            "library": str(self.library),
            "library_exists": self.library.is_dir(),
            "index_dir": str(self.index_dir),
            "assets": len(self.records),
            "packs": len(packs),
            "has_tag_index": self.tag_vectors is not None,
            "has_clap_index": self.clap_vectors is not None,
            "has_spectral_index": self.spectral is not None,
            "archetypes": sorted({a for r in self.records for a in r.archetypes}),
            "license_tiers": {
                t: sum(1 for r in self.records if r.license_tier() == t)
                for t in ("own", "direct", "reference")
            },
        }

    def _catalog_path(self) -> Path:
        return self.index_dir / "catalog.json"

    def load(self) -> None:
        cat = self._catalog_path()
        if not cat.is_file():
            return
        data = json.loads(cat.read_text(encoding="utf-8"))
        self.tag_model = str(data.get("tag_model", ""))
        self.records = [AssetRecord(**r) for r in data.get("records", [])]
        self._reindex_ids()
        self.tag_vectors = _load_npy(self.index_dir / "tag.npy")
        self.clap_vectors = _load_npy(self.index_dir / "clap.npy")
        self.spectral = _load_npy(self.index_dir / "spectral.npy")

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": INDEX_VERSION,
            "library": str(self.library),
            "tag_model": self.tag_model,
            "records": [asdict(r) for r in self.records],
        }
        self._catalog_path().write_text(json.dumps(payload, indent=0), encoding="utf-8")
        if self.tag_vectors is not None:
            np.save(self.index_dir / "tag.npy", self.tag_vectors)
        if self.clap_vectors is not None:
            np.save(self.index_dir / "clap.npy", self.clap_vectors)
        if self.spectral is not None:
            np.save(self.index_dir / "spectral.npy", self.spectral)

    def _reindex_ids(self) -> None:
        self._by_id = {r.id: i for i, r in enumerate(self.records)}

    def get(self, aid: str) -> Optional[AssetRecord]:
        if not self.records:
            self.load()
        idx = self._by_id.get(aid)
        return self.records[idx] if idx is not None else None

    def _ensure_tags(self) -> _TagEmbedder:
        if self._tags is None:
            self._tags = _TagEmbedder()
            if not self.records:
                self.tag_model = self._tags.name
            elif self.tag_model and self.tag_model != self._tags.name:
                print(
                    f"  [audio-lib] WARNING: tag index built with {self.tag_model} but the "
                    f"embedder is {self._tags.name} — run `audio_pipeline.py rebuild-tags`"
                )
        return self._tags

    def rebuild_tags(self) -> Dict[str, Any]:
        """Re-embed every record's tag text with the current embedder (no audio decode)."""
        self.load()
        tagger = self._ensure_tags()
        before = self.tag_model or "unrecorded"
        texts = [r.search_text() for r in self.records]
        self.tag_vectors = tagger.embed_many(texts) if texts else None
        self.tag_model = tagger.name
        self.save()
        return {"rebuilt": len(texts), "tag_model": self.tag_model, "previous": before}

    def _ensure_clap(self) -> _ClapEmbedder:
        if self._clap is None:
            self._clap = _ClapEmbedder(device=os.environ.get("AAMT_CLAP_DEVICE", "cpu"))
        return self._clap

    def _ensure_whisper(self) -> _Whisper:
        if self._whisper is None:
            self._whisper = _Whisper(os.environ.get("AAMT_WHISPER_MODEL", "base"))
        return self._whisper

    def ingest(
        self,
        *,
        src: Optional[Path] = None,
        fast: bool = False,
        clap: bool = True,
        whisper: bool = True,
        pack_glob: str = "",
        limit: int = 0,
        resume: bool = True,
    ) -> Dict[str, Any]:
        """Scan packs, extract embeddings, write the index. Incremental."""
        root = Path(src or self.library)
        self.library = root
        if resume:
            self.load()
        existing = set(self._by_id)
        tagger = self._ensure_tags()
        clap_e = None if (fast or not clap) else self._ensure_clap()
        if clap_e is not None and not clap_e.ok:
            print("  [audio-lib] CLAP unavailable — tag + spectral index only")
            clap_e = None
        whisper_e = None
        if whisper and not fast:
            whisper_e = self._ensure_whisper()
            if not whisper_e.ok:
                whisper_e = None

        added = 0
        skipped = 0
        failed = 0
        pack_filter = pack_glob.lower().strip()

        tag_rows: List[np.ndarray] = [] if self.tag_vectors is None else [self.tag_vectors]
        clap_rows: List[np.ndarray] = [] if self.clap_vectors is None else [self.clap_vectors]
        spec_rows: List[np.ndarray] = [] if self.spectral is None else [self.spectral]

        last_pack = ""
        for pack, inner, data, source in iter_library_entries(root):
            if pack_filter and pack_filter not in pack.lower():
                continue
            aid = asset_id(pack, inner)
            if aid in existing:
                skipped += 1
                continue
            if pack != last_pack:
                last_pack = pack
                print(f"  [audio-lib] pack {pack}")
                if added and added % 50 == 0:
                    self._stack_and_save(tag_rows, clap_rows, spec_rows)

            try:
                rec, tag_v, clap_v, spec_v = self._ingest_one(
                    pack, inner, data, source, tagger, clap_e, whisper_e
                )
            except Exception as exc:
                failed += 1
                print(f"  [audio-lib] fail {pack}::{inner}: {exc}")
                continue
            self.records.append(rec)
            existing.add(aid)
            self._by_id[aid] = len(self.records) - 1
            tag_rows.append(tag_v.reshape(1, -1))
            spec_rows.append(spec_v.reshape(1, -1))
            if clap_e is not None:
                if clap_v is None:
                    clap_v = np.zeros((int(getattr(clap_e, "dim", 512)),), dtype=np.float32)
                clap_rows.append(clap_v.reshape(1, -1))
            added += 1
            if limit and added >= limit:
                break

        self._stack_and_save(tag_rows, clap_rows, spec_rows)
        return {
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "total": len(self.records),
            "clap": bool(self.clap_vectors is not None),
            "index_dir": str(self.index_dir),
        }

    def backfill_clap(self, *, resume: bool = True, save_every: int = 100) -> Dict[str, Any]:
        """Build or resume CLAP embeddings for every catalogued clip."""
        self.load()
        clap_e = self._ensure_clap()
        if not clap_e.ok:
            return {
                "built": 0,
                "skipped": 0,
                "failed": 0,
                "total": len(self.records),
                "clap": False,
                "error": "CLAP unavailable (install transformers + torch; set AAMT_CLAP_DEVICE)",
            }
        n = len(self.records)
        if n == 0:
            return {"built": 0, "skipped": 0, "failed": 0, "total": 0, "clap": False}

        existing = self.clap_vectors
        if resume and existing is not None and existing.shape[0] == n:
            return {
                "built": 0,
                "skipped": n,
                "failed": 0,
                "total": n,
                "clap": True,
                "index_dir": str(self.index_dir),
            }

        rows: List[np.ndarray] = []
        built = 0
        skipped = 0
        failed = 0
        start = 0
        if resume and existing is not None and existing.shape[0] <= n:
            for i in range(existing.shape[0]):
                rows.append(existing[i])
            start = existing.shape[0]
            skipped = start

        for i in range(start, n):
            rec = self.records[i]
            try:
                mono, sr = self._load_record_mono(rec, sr=CLAP_SR)
                vec = clap_e.audio(mono, sr)
                if vec is None:
                    vec = np.zeros((clap_e.dim,), dtype=np.float32)
                    failed += 1
                else:
                    built += 1
            except Exception as exc:
                print(f"  [audio-lib] clap fail {rec.label()}: {exc}")
                vec = np.zeros((clap_e.dim,), dtype=np.float32)
                failed += 1
            rows.append(vec)
            if built and built % save_every == 0:
                self.clap_vectors = np.stack(rows, axis=0)
                self.save()
                print(f"  [audio-lib] clap {len(rows)}/{n}")
        self.clap_vectors = np.stack(rows, axis=0)
        self.save()
        return {
            "built": built,
            "skipped": skipped,
            "failed": failed,
            "total": n,
            "clap": True,
            "index_dir": str(self.index_dir),
        }

    def add_file(self, path: Path) -> AssetRecord:
        """Index one loose file under the library (e.g. a kept own clip) without a full rescan."""
        self.load()
        path = Path(path)
        inner = path.relative_to(self.library).as_posix()
        pack = path.parent.name or "loose"
        aid = asset_id(pack, inner)
        if aid in self._by_id:
            return self.records[self._by_id[aid]]
        n = len(self.records)
        clap_e = None
        if self.clap_vectors is not None and self.clap_vectors.shape[0] == n:
            clap_e = self._ensure_clap()
            if not clap_e.ok:
                clap_e = None
        rec, tag_v, clap_v, spec_v = self._ingest_one(
            pack, inner, path.read_bytes(), "file", self._ensure_tags(), clap_e, None
        )
        self.records.append(rec)
        self._reindex_ids()
        self.tag_vectors = _vstack([r for r in (self.tag_vectors, tag_v) if r is not None])
        self.spectral = _vstack([r for r in (self.spectral, spec_v) if r is not None])
        if clap_e is not None:
            if clap_v is None:
                clap_v = np.zeros((int(clap_e.dim),), dtype=np.float32)
            self.clap_vectors = _vstack([self.clap_vectors, clap_v])
        # else: CLAP stays short until `backfill-clap` (search ignores a mismatched matrix)
        self.save()
        return rec

    def _load_record_mono(self, rec: AssetRecord, *, sr: int = EMBED_SR) -> Tuple[np.ndarray, int]:
        if rec.source == "file":
            data = (self.library / rec.inner).read_bytes()
        else:
            zpath = self.library / rec.pack
            with _open_zip(zpath) as zf:
                data = zf.read(rec.inner)
        return _decode_bytes(data, max_seconds=EMBED_SECONDS, sr=sr)

    def _stack_and_save(self, tag_rows, clap_rows, spec_rows) -> None:
        if tag_rows:
            self.tag_vectors = _vstack(tag_rows)
            tag_rows.clear()
            tag_rows.append(self.tag_vectors)
        if spec_rows:
            self.spectral = _vstack(spec_rows)
            spec_rows.clear()
            spec_rows.append(self.spectral)
        if clap_rows:
            # Only keep CLAP matrix if every row so far has one, or pad later
            try:
                stacked = _vstack(clap_rows)
                if stacked.shape[0] == len(self.records):
                    self.clap_vectors = stacked
                    clap_rows.clear()
                    clap_rows.append(self.clap_vectors)
            except Exception:
                pass
        self.save()

    def _ingest_one(
        self,
        pack: str,
        inner: str,
        data: bytes,
        source: str,
        tagger: _TagEmbedder,
        clap_e: Optional[_ClapEmbedder],
        whisper_e: Optional[_Whisper],
    ) -> Tuple[AssetRecord, np.ndarray, Optional[np.ndarray], np.ndarray]:
        name = Path(inner).stem
        tags = infer_tags(pack, inner)
        archetypes = infer_archetypes(pack, inner, name)
        if source == "file" and license_tier(pack, inner) == "own":
            # Kept clips: the generate prompt/archetype describe them better than a filename.
            side = self.library / Path(inner).with_suffix(".meta.json")
            try:
                meta = json.loads(side.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
            extra = [t for t in _tokenize(meta.get("prompt", "")) if t not in tags]
            tags = (tags + extra)[:24]
            if meta.get("archetype") and meta["archetype"] not in archetypes:
                archetypes.append(meta["archetype"])
        duration, sample_rate, channels = _wav_info(data)
        mono, sr = _decode_bytes(data, max_seconds=EMBED_SECONDS, sr=EMBED_SR)
        if duration <= 0 and sr:
            duration = float(mono.shape[0]) / float(sr)
        spec = spectral_fingerprint(mono, sr)
        rec = AssetRecord(
            id=asset_id(pack, inner),
            pack=pack,
            inner=inner,
            name=name,
            tags=tags,
            archetypes=archetypes,
            duration=round(duration, 3),
            sample_rate=sample_rate or sr,
            channels=channels or 1,
            loop_like="loop" in inner.lower() or "loop" in name.lower(),
            source=source,
        )
        if whisper_e is not None and "voice" in archetypes and mono.size:
            rec.transcript = whisper_e.transcribe(mono, sr)
        tag_v = tagger.embed(rec.search_text())
        clap_v = clap_e.audio(mono, sr) if clap_e is not None else None
        return rec, tag_v, clap_v, spec

    def search_text(
        self,
        query: str,
        *,
        k: int = 8,
        archetype: str = "",
        tags: Optional[Sequence[str]] = None,
        license: Union[str, Sequence[str]] = "",
    ) -> List[RetrievalHit]:
        if not self.records:
            self.load()
        if not self.records:
            return []
        mask = self._filter_mask(archetype=archetype, tags=tags, license=license)
        scores = np.zeros(len(self.records), dtype=np.float32)
        via = "tag"
        clap = self._ensure_clap()
        q_clap = clap.text(query) if clap.ok else None
        if q_clap is not None and self.clap_vectors is not None and self.clap_vectors.shape[0] == len(self.records):
            scores = 0.6 * _cosine_scores(q_clap, self.clap_vectors)
            via = "clap+tag"
        if self.tag_vectors is not None and self.tag_vectors.shape[0] == len(self.records):
            q_tag = self._ensure_tags().embed(query)
            tag_s = _cosine_scores(q_tag, self.tag_vectors)
            scores = scores + (0.4 if via.startswith("clap") else 1.0) * tag_s
        else:
            # lexical fallback
            qset = set(_tokenize(query))
            for i, rec in enumerate(self.records):
                rset = set(rec.tags + rec.archetypes + _tokenize(rec.name))
                scores[i] += len(qset & rset) / max(1, len(qset))
            via = "lexical" if via == "tag" else via
        scores = np.where(mask, scores, -1.0)
        return self._hits_from_scores(scores, k, via)

    def search_audio(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        k: int = 8,
        archetype: str = "",
        license: Union[str, Sequence[str]] = "",
    ) -> List[RetrievalHit]:
        if not self.records:
            self.load()
        if audio.ndim == 2:
            mono = audio.mean(axis=1) if audio.shape[1] < audio.shape[0] else audio.mean(axis=0)
        else:
            mono = np.asarray(audio, dtype=np.float32).ravel()
        if sr != EMBED_SR and mono.size:
            n = max(1, int(round(mono.shape[0] * EMBED_SR / float(sr))))
            mono = np.interp(
                np.linspace(0, 1, n, endpoint=False),
                np.linspace(0, 1, mono.shape[0], endpoint=False),
                mono,
            ).astype(np.float32)
            sr = EMBED_SR
        spec = spectral_fingerprint(mono, sr)
        scores = np.zeros(len(self.records), dtype=np.float32)
        via = "spectral"
        if self.spectral is not None and self.spectral.shape[0] == len(self.records):
            scores = _cosine_scores(spec, self.spectral)
        clap = self._ensure_clap()
        q = clap.audio(mono, sr) if clap.ok else None
        if q is not None and self.clap_vectors is not None and self.clap_vectors.shape[0] == len(self.records):
            scores = 0.55 * _cosine_scores(q, self.clap_vectors) + 0.45 * scores
            via = "clap+spectral"
        mask = self._filter_mask(archetype=archetype, license=license)
        scores = np.where(mask, scores, -1.0)
        return self._hits_from_scores(scores, k, via)

    def _filter_mask(
        self,
        *,
        archetype: str = "",
        tags: Optional[Sequence[str]] = None,
        license: Union[str, Sequence[str]] = "",
    ) -> np.ndarray:
        mask = np.ones(len(self.records), dtype=bool)
        if license:
            allowed = {license} if isinstance(license, str) else set(license)
            mask &= np.array([r.license_tier() in allowed for r in self.records])
        if archetype:
            a = archetype.lower().strip()
            mask &= np.array([a in r.archetypes or a in r.tags for r in self.records])
        if tags:
            want = {t.lower() for t in tags if t}
            mask &= np.array([bool(want & set(r.tags + r.archetypes)) for r in self.records])
        return mask

    def _hits_from_scores(self, scores: np.ndarray, k: int, via: str) -> List[RetrievalHit]:
        k = max(1, min(int(k), scores.size))
        idx = np.argpartition(-scores, kth=k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        hits = []
        for i in idx:
            if scores[i] < 0:
                continue
            hits.append(RetrievalHit(self.records[int(i)], float(scores[i]), via))
        return hits

    def mix_references(
        self,
        hits: Sequence[RetrievalHit],
        *,
        max_seconds: float = 4.0,
        sr: int = 48000,
    ) -> Tuple[np.ndarray, int, List[str]]:
        """Weighted mix of retrieved clips → (samples, channels) init audio."""
        if not hits:
            raise ValueError("no reference hits to mix")
        weights = np.array([max(0.05, h.score) for h in hits], dtype=np.float32)
        weights = weights / weights.sum()
        n = int(max_seconds * sr)
        mix = np.zeros((n, 2), dtype=np.float32)
        used: List[str] = []
        for w, hit in zip(weights, hits):
            try:
                wav, in_sr = load_asset_audio(hit.record, self.library, max_seconds=max_seconds, sr=sr)
            except Exception as exc:
                print(f"  [audio-lib] mix skip {hit.record.label()}: {exc}")
                continue
            if wav.ndim == 1:
                wav = np.stack([wav, wav], axis=1)
            if wav.shape[0] < n:
                wav = np.pad(wav, ((0, n - wav.shape[0]), (0, 0)))
            mix += w * wav[:n, :2]
            used.append(hit.record.id)
        peak = float(np.max(np.abs(mix)))
        if peak > 1e-8:
            mix = mix / peak
        return mix, sr, used


def _load_npy(path: Path) -> Optional[np.ndarray]:
    if not path.is_file():
        return None
    return np.load(path)


def _vstack(rows: List[np.ndarray]) -> np.ndarray:
    parts = [np.asarray(r, dtype=np.float32) for r in rows if r is not None]
    parts = [p if p.ndim == 2 else p.reshape(1, -1) for p in parts]
    return np.concatenate(parts, axis=0).astype(np.float32)


def _cosine_scores(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = np.asarray(query, dtype=np.float32).ravel()
    n = float(np.linalg.norm(q))
    if n > 1e-8:
        q = q / n
    # matrices are stored L2-normalized; re-normalize in case they aren't
    m = matrix.astype(np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    return (m / norms) @ q


def blend_waveforms(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    """z = alpha * a + (1-alpha) * b, length-matched, peak-normalized."""
    alpha = float(np.clip(alpha, 0.0, 1.0))
    n = max(a.shape[0], b.shape[0])
    aa = a if a.ndim == 2 else a.reshape(-1, 1)
    bb = b if b.ndim == 2 else b.reshape(-1, 1)
    ch = max(aa.shape[1], bb.shape[1])
    if aa.shape[1] < ch:
        aa = np.repeat(aa, ch, axis=1)
    if bb.shape[1] < ch:
        bb = np.repeat(bb, ch, axis=1)
    if aa.shape[0] < n:
        aa = np.pad(aa, ((0, n - aa.shape[0]), (0, 0)))
    if bb.shape[0] < n:
        bb = np.pad(bb, ((0, n - bb.shape[0]), (0, 0)))
    out = alpha * aa[:n] + (1.0 - alpha) * bb[:n]
    peak = float(np.max(np.abs(out)))
    if peak > 1e-8:
        out = out / peak
    return out.astype(np.float32)
