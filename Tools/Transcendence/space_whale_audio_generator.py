"""
Space Whale Audio Generator

Default path: Shared audio stage — retrieve from D:\\assets\\audio (6464+ clips),
then condition Stable Audio 3 on those refs (`init_audio`). That is how new
whale SFX are "trained" from the library; not numpy sine songs.

Channels: EM / Plasma / Acoustic / Mechanical.
`--engine procedural` is opt-in only (legacy whale-song synth).
"""
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Shared SA3 backend
_SHARED = Path(__file__).resolve().parent.parent / "Shared"
if _SHARED.is_dir() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import json
import hashlib
import os
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading

try:
    import aamt_stable_audio_backend as sa3
except ImportError:
    sa3 = None

# Check for required dependencies
try:
    import numpy as np
    import soundfile as sf
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    MISSING_DEPENDENCY = str(e)
    print(f"WARNING: Missing required dependency: {MISSING_DEPENDENCY}")
    print("Please install missing dependencies:")
    print("  pip install numpy soundfile")
    print("Audio generation will be skipped.")

class WhaleSongGenerator:
    """Generates procedural whale songs based on communication channel type."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
    
    def generate_em_chirp(self, base_freq: float, duration: float, seed: int = None) -> np.ndarray:
        """Generate EM chirp (rendered as whale song)."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Base frequency with slow sweep
        freq_sweep = base_freq + 5 * np.sin(2 * np.pi * 0.1 * t)
        
        # Add harmonics
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 2 * t)  # 2nd harmonic
        signal += 0.3 * np.sin(2 * np.pi * freq_sweep * 3 * t)  # 3rd harmonic
        signal += 0.2 * np.sin(2 * np.pi * freq_sweep * 5 * t)  # 5th harmonic
        
        # Add subtle noise for EM character
        noise = np.random.normal(0, 0.05, len(signal))
        signal += noise
        
        # Envelope (slow pulse)
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t)
        signal *= envelope
        
        # Normalize
        signal = signal / np.max(np.abs(signal)) * 0.7
        
        return signal
    
    def generate_plasma_oscillation(self, base_freq: float, duration: float, seed: int = None) -> np.ndarray:
        """Generate plasma oscillations and magnetosonic waves."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Base frequency with oscillation
        freq_osc = base_freq + 10 * np.sin(2 * np.pi * 1.0 * t)
        
        # Complex harmonic series
        signal = np.sin(2 * np.pi * freq_osc * t)
        signal += 0.6 * np.sin(2 * np.pi * freq_osc * 1.5 * t)
        signal += 0.4 * np.sin(2 * np.pi * freq_osc * 2 * t)
        signal += 0.3 * np.sin(2 * np.pi * freq_osc * 2.5 * t)
        signal += 0.2 * np.sin(2 * np.pi * freq_osc * 3 * t)
        
        # Add plasma-like modulation
        mod_freq = 5.0
        modulation = 1.0 + 0.3 * np.sin(2 * np.pi * mod_freq * t)
        signal *= modulation
        
        # Envelope (pulsing)
        envelope = 0.4 + 0.6 * np.sin(2 * np.pi * 1.0 * t)
        signal *= envelope
        
        # Normalize
        signal = signal / np.max(np.abs(signal)) * 0.6
        
        return signal
    
    def generate_acoustic_pressure(self, base_freq: float, duration: float, seed: int = None) -> np.ndarray:
        """Generate acoustic pressure waves (nebular medium only)."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Lower frequency for acoustic
        freq = base_freq + 2 * np.sin(2 * np.pi * 0.8 * t)
        
        # Simple harmonic (muffled)
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Heavy low-pass filter simulation (nebula muffling)
        # Simple approximation: reduce high frequencies
        from scipy import signal as scipy_signal
        b, a = scipy_signal.butter(3, 0.1, 'low')
        signal = scipy_signal.filtfilt(b, a, signal)
        
        # Breathing envelope
        envelope = 0.3 + 0.7 * np.sin(2 * np.pi * 0.8 * t)
        signal *= envelope
        
        # Normalize
        signal = signal / np.max(np.abs(signal)) * 0.5
        
        return signal
    
    def generate_mechanical_vibration(self, base_freq: float, duration: float, seed: int = None) -> np.ndarray:
        """Generate mechanical hull vibrations."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Higher frequency for impact
        freq = base_freq + 20 * np.exp(-t * 2)  # Decay
        
        # Rich harmonic content
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.8 * np.sin(2 * np.pi * freq * 2 * t)
        signal += 0.6 * np.sin(2 * np.pi * freq * 3 * t)
        signal += 0.4 * np.sin(2 * np.pi * freq * 4 * t)
        
        # Impact envelope (sharp attack, exponential decay)
        envelope = np.exp(-t * 3)
        signal *= envelope
        
        # Add impact transient
        transient = np.random.normal(0, 0.2, int(0.01 * self.sample_rate))
        signal[:len(transient)] += transient
        
        # Normalize
        signal = signal / np.max(np.abs(signal)) * 0.8
        
        return signal
    
    def generate_from_config(self, sound_config: Dict, seed: int = None) -> np.ndarray:
        """Generate sound from configuration."""
        channel = sound_config.get('channel', 'em')
        freq_config = sound_config.get('frequency', {})
        duration_config = sound_config.get('duration', {})
        
        base_freq = freq_config.get('base', 30)
        duration = duration_config.get('max', 3.0)
        
        # Generate seed from sound ID if not provided
        if seed is None:
            sound_id = sound_config.get('id', 'unknown')
            seed = int(hashlib.md5(sound_id.encode()).hexdigest()[:8], 16) % (2**31)
        
        # Generate based on channel
        if channel == 'em':
            return self.generate_em_chirp(base_freq, duration, seed)
        elif channel == 'plasma':
            return self.generate_plasma_oscillation(base_freq, duration, seed)
        elif channel == 'acoustic':
            return self.generate_acoustic_pressure(base_freq, duration, seed)
        elif channel == 'mechanical':
            return self.generate_mechanical_vibration(base_freq, duration, seed)
        else:
            return self.generate_em_chirp(base_freq, duration, seed)

    def prompt_from_config(self, sound_config: Dict) -> str:
        return prompt_from_sound(sound_config)


CHANNEL_ARCHETYPE = {
    "em": "alien",
    "plasma": "laser",
    "acoustic": "organic",
    "mechanical": "ship",
}
CHANNEL_TAGS = {
    "em": ("alien", "organic", "ambience"),
    "plasma": ("laser", "magic", "fire"),
    "acoustic": ("organic", "water", "ambience"),
    "mechanical": ("ship", "impact", "mech"),
}


def prompt_from_sound(sound: Dict) -> str:
    """Text prompt for library search + SA3."""
    channel = sound.get("channel") or "em"
    name = sound.get("name") or sound.get("id") or "space whale"
    desc = sound.get("description") or ""
    kind = sound.get("type") or ""
    return (
        f"Transcendence space whale {kind} SFX, {name}, {desc}, "
        f"{channel} channel, organic living starship creature, sci-fi, "
        f"no music, no singing, no speech, no lyrics"
    )


def _duration_from_sound(sound: Dict) -> float:
    dur = sound.get("duration") or {}
    raw = dur.get("max") or dur.get("min") or 4.0
    try:
        return min(float(raw), 12.0)
    except (TypeError, ValueError):
        return 4.0


def _seed_for(sound_id: str, variation_id: int) -> int:
    h = hashlib.md5(f"{sound_id}:{variation_id}".encode()).hexdigest()[:8]
    return int(h, 16) % (2**31)


def _write_dest(src_wav: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() in (".wav", ""):
        if src_wav.resolve() != dest.resolve():
            dest.write_bytes(src_wav.read_bytes())
        return dest
    data, sr = sf.read(str(src_wav))
    sf.write(str(dest), data, sr, format="OGG", subtype="VORBIS")
    if src_wav != dest and src_wav.is_file() and src_wav.suffix.lower() == ".wav":
        try:
            src_wav.unlink()
        except OSError:
            pass
    return dest


def _generate_ai_clip(
    sound: Dict,
    dest: Path,
    *,
    variation_id: int,
    engine: str,
    model: Optional[str],
    strength: float,
) -> Path:
    import tx_ai_pipeline as tx

    channel = (sound.get("channel") or "em").lower()
    wav_tmp = dest.with_suffix(".wav") if dest.suffix.lower() != ".wav" else dest
    path = tx.generate_audio(
        prompt_from_sound(sound),
        wav_tmp,
        duration=_duration_from_sound(sound),
        archetype=CHANNEL_ARCHETYPE.get(channel, "alien"),
        strength=strength,
        tags=list(CHANNEL_TAGS.get(channel, ("alien",))),
        seed=_seed_for(sound.get("id", dest.stem), variation_id),
        engine=engine,
        model_name=model,
    )
    if not path or not Path(path).is_file():
        raise RuntimeError(
            f"Shared audio stage wrote nothing for {sound.get('id')} "
            "(need SA3 and/or D:\\assets\\audio). No procedural fallback."
        )
    return _write_dest(Path(path), dest)


def generate_all_audio(
    registry_path: str,
    output_dir: str,
    variations: int = 150,
    resume: bool = False,
    skip_completed: bool = False,
    engine: str = "auto",
    model: Optional[str] = None,
    strength: float = 0.7,
):
    """Generate registry clips via Shared make_audio (library DNA + SA3)."""
    if not DEPENDENCIES_AVAILABLE:
        print(f"ERROR: Cannot generate audio - missing dependency: {MISSING_DEPENDENCY}")
        print("Please install: pip install numpy soundfile")
        return False

    use_procedural = (engine or "auto").strip().lower() in ("procedural", "proc", "synth")
    resolved = "procedural" if use_procedural else "stable-audio"
    print(f"Audio engine: {resolved}" + (f" (requested={engine})" if engine != resolved else ""))
    if not use_procedural:
        print("  Library: D:\\assets\\audio (retrieve + condition SA3 init_audio)")
        print(f"  Strength: {strength} (0=text-only, 1=stay on retrieved refs)")
        if sa3 is not None and not sa3.is_available():
            print(f"  NOTE: SA3 import probe failed ({sa3.last_error()}); library mix still used")
        if variations > 6:
            print("  NOTE: SA3 is sequential on GPU; prefer --variations 1-3 for drafts.")

    with open(registry_path, 'r') as f:
        registry = json.load(f)

    audio_config = registry.get('audio', {})
    sounds = audio_config.get('sounds', [])

    os.makedirs(output_dir, exist_ok=True)
    output_path = Path(output_dir)

    existing_files = set()
    if resume or skip_completed:
        if output_path.exists():
            for wav_file in output_path.rglob("*.wav"):
                existing_files.add(wav_file.name)
            for ogg_file in output_path.rglob("*.ogg"):
                existing_files.add(ogg_file.name)
        if existing_files:
            print(f"Resume mode: Found {len(existing_files)} existing audio files")
            if skip_completed:
                print("  Skipping completed sounds")

    max_workers = 1 if not use_procedural else min(
        32, cpu_count(), len(sounds) * variations if variations > 1 else max(1, len(sounds))
    )
    print(f"Generating audio with {max_workers} worker thread(s)...")

    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    completed_count = [0]
    skipped_count = [0]
    sa3_count = [0]
    proc_count = [0]
    total_tasks = len(sounds) * variations if variations > 1 else len(sounds)

    def generate_single_audio(sound: Dict, variation_id: int = 0) -> Tuple[str, bool]:
        """Generate a single audio file (thread-safe)."""
        try:
            thread_generator = WhaleSongGenerator()

            sound_id = sound['id']
            resource_path = sound.get('resourcePath', f'Resources/Audio/{sound_id}.ogg')

            filename = os.path.basename(resource_path)
            if variations > 1:
                base_name, ext = os.path.splitext(filename)
                filename = f"{base_name}_v{variation_id:03d}{ext}"

            out_file = os.path.join(output_dir, filename)

            if skip_completed and filename in existing_files:
                with progress_lock:
                    skipped_count[0] += 1
                    completed_count[0] += 1
                    current = completed_count[0]
                    if current % 10 == 0 or current == total_tasks:
                        print(f"  Progress: {current}/{total_tasks} ({current*100//total_tasks}%) [Skipped: {skipped_count[0]}]")
                return (out_file, True)

            seed = variation_id if variations > 1 else None
            used = "stable-audio"
            sample_rate = thread_generator.sample_rate

            if not use_procedural:
                try:
                    _generate_ai_clip(
                        sound,
                        Path(out_file),
                        variation_id=variation_id,
                        engine=engine,
                        model=model,
                        strength=strength,
                    )
                    used = "stable-audio"
                    with progress_lock:
                        sa3_count[0] += 1
                except Exception as e:
                    with progress_lock:
                        print(f"  ✗ {sound_id}: {e}")
                    raise
            else:
                audio_data = thread_generator.generate_from_config(sound, seed=seed)
                with progress_lock:
                    proc_count[0] += 1
                if len(audio_data.shape) == 1:
                    audio_data = np.column_stack([audio_data, audio_data])
                with results_lock:
                    sf.write(out_file, audio_data, sample_rate, format='OGG', subtype='VORBIS')

            with progress_lock:
                completed_count[0] += 1
                current = completed_count[0]
                skipped = skipped_count[0]
                if current % 1 == 0 or current == total_tasks or current % 10 == 0:
                    skipped_text = f" [Skipped: {skipped}]" if skipped > 0 else ""
                    print(f"  Progress: {current}/{total_tasks} ({current*100//max(total_tasks,1)}%){skipped_text} [{used}] {sound_id}")

            return (out_file, True)
        except Exception as e:
            with progress_lock:
                print(f"  ✗ Error generating {sound.get('id', 'unknown')}: {e}")
            return (None, False)
    
    # Generate all audio files in parallel
    tasks = []
    if variations > 1:
        # Generate multiple variations per sound
        for sound in sounds:
            for v in range(variations):
                tasks.append((sound, v))
    else:
        # Single generation per sound
        for sound in sounds:
            tasks.append((sound, 0))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_single_audio, sound, var_id): (sound, var_id) for sound, var_id in tasks}

        # SA3 generations are slow; procedural stays short
        per_file_timeout = 600 if not use_procedural else 30

        completed_futures = 0
        for future in as_completed(futures):
            completed_futures += 1
            try:
                file_path, success = future.result(timeout=per_file_timeout)
                if success and file_path:
                    with progress_lock:
                        checkmark = "[OK]" if sys.platform == 'win32' and not hasattr(sys.stdout, 'reconfigure') else "✓"
                        try:
                            print(f"  {checkmark} Generated: {os.path.basename(file_path)}")
                        except UnicodeEncodeError:
                            print(f"  [OK] Generated: {os.path.basename(file_path)}")
            except TimeoutError:
                sound, var_id = futures[future]
                print(f"  ✗ Timeout: {sound.get('id', 'unknown')} variation {var_id} (took >{per_file_timeout}s)")
            except Exception as e:
                sound, var_id = futures[future]
                print(f"  ✗ Failed: {sound.get('id', 'unknown')} variation {var_id}: {e}")

            if completed_futures % 50 == 0:
                with progress_lock:
                    print(f"  Status: {completed_futures}/{total_tasks} futures completed...")
    
    # Final summary
    print(f"\nGeneration Summary:")
    print(f"  Engine: {resolved}")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Completed: {completed_count[0]}")
    if sa3_count[0] or proc_count[0]:
        print(f"  Via Stable Audio 3: {sa3_count[0]}")
        print(f"  Via procedural: {proc_count[0]}")
    if skipped_count[0] > 0:
        print(f"  Skipped (already existed): {skipped_count[0]}")
    print(f"  Failed: {total_tasks - completed_count[0]}")

    generated_files = list(output_path.rglob("*.wav")) + list(output_path.rglob("*.ogg"))
    if generated_files:
        total_size = sum(f.stat().st_size for f in generated_files)
        print(f"  Total files: {len(generated_files)}")
        print(f"  Total size: {total_size / (1024*1024):.2f} MB")
    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate space whale audio from D:\\assets\\audio + Stable Audio 3"
    )
    parser.add_argument('--registry', required=True, help='Path to audio registry JSON')
    parser.add_argument('--output', required=True, help='Output directory for audio files')
    parser.add_argument('--variations', type=int, default=1, help='Number of variations per sound (default: 1; keep low for SA3)')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted generation (check for existing files)')
    parser.add_argument('--skip-completed', action='store_true', help='Skip sounds that already have generated files')
    parser.add_argument('--engine', default=os.environ.get('AAMT_AUDIO_ENGINE', 'auto'),
                        choices=['auto', 'stable-audio', 'library', 'procedural'],
                        help='auto/stable-audio = library refs + SA3; library = mix only; procedural = legacy synth')
    parser.add_argument('--model', default=None, help='SA3 model id (medium|small-sfx|small-music)')
    parser.add_argument('--strength', type=float, default=0.7,
                        help='How closely to stay on retrieved library refs (0=text-only, 1=near-clone)')

    args = parser.parse_args()

    generate_all_audio(
        args.registry,
        args.output,
        variations=args.variations,
        resume=args.resume,
        skip_completed=args.skip_completed,
        engine=args.engine,
        model=args.model,
        strength=args.strength,
    )
    print("\nAudio generation complete!")

