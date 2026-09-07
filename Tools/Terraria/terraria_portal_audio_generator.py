#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terraria Portal Audio Generator
Generates procedural sound effects for Terraria portal mods including activation, ambient, teleport, and deactivation sounds.
"""

import os
import sys
import json
import argparse
import hashlib
from typing import Dict, List, Tuple, Optional

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

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

_SHARED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Shared")
if os.path.isdir(_SHARED) and _SHARED not in sys.path:
    sys.path.insert(0, os.path.abspath(_SHARED))
try:
    import aamt_stable_audio_backend as sa3
except ImportError:
    sa3 = None

class TerrariaPortalAudioGenerator:
    """Generates Terraria portal SFX (Stable Audio 3 + procedural)."""
    
    def __init__(self, sample_rate: int = 44100, engine: str = "auto", model: str = None):
        self.sample_rate = sample_rate
        self.engine = engine
        self.model = model
        self.last_engine_used = "procedural"
    
    def generate_activation_sound(self, preset: str = "Void", duration: float = 1.0, seed: int = None) -> np.ndarray:
        """
        Generate portal activation sound (opening).
        
        Args:
            preset: Portal preset (Void, Fire, Ice, Electric, Nature, Shadow, Light)
            duration: Sound duration in seconds
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Base frequency based on preset
        base_freq = self._get_preset_base_freq(preset)
        
        # Rising pitch with energy buildup
        freq_sweep = base_freq * (0.5 + 2.0 * t / duration)  # Rise from 0.5x to 2.5x
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.6 * np.sin(2 * np.pi * freq_sweep * 2 * t)
        signal += 0.3 * np.sin(2 * np.pi * freq_sweep * 3 * t)
        
        # Build-up envelope
        envelope = (1 - np.exp(-t * 3)) * np.exp(-t * 0.5)
        
        # Add preset-specific character
        signal = self._apply_preset_character(signal, preset, t)
        
        # Apply envelope
        signal *= envelope
        
        # Add energy burst at end
        burst = np.random.normal(0, 0.2, int(0.1 * self.sample_rate))
        signal[-len(burst):] += burst * envelope[-len(burst):]
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
        
        return signal
    
    def generate_ambient_sound(self, preset: str = "Void", duration: float = 3.0, seed: int = None) -> np.ndarray:
        """
        Generate portal ambient/loop sound (while active).
        
        Args:
            preset: Portal preset
            duration: Sound duration in seconds (should be loopable)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_preset_base_freq(preset)
        
        # Steady tone with slow modulation
        freq = base_freq
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.4 * np.sin(2 * np.pi * freq * 2 * t)
        signal += 0.2 * np.sin(2 * np.pi * freq * 3 * t)
        
        # Slow modulation for variation
        mod_freq = 0.4  # 0.4 Hz
        modulation = 1.0 + 0.15 * np.sin(2 * np.pi * mod_freq * t)
        signal *= modulation
        
        # Add preset character
        signal = self._apply_preset_character(signal, preset, t)
        
        # Fade in/out for smooth looping
        fade_samples = int(0.15 * self.sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        signal[:fade_samples] *= fade_in
        signal[-fade_samples:] *= fade_out
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.5
        
        return signal
    
    def generate_teleport_sound(self, preset: str = "Void", duration: float = 0.5, seed: int = None) -> np.ndarray:
        """
        Generate teleport sound (when using portal).
        
        Args:
            preset: Portal preset
            duration: Sound duration in seconds
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_preset_base_freq(preset)
        
        # Quick whoosh with pitch sweep
        freq_sweep = base_freq * 2.0 * (1 + 1.5 * t / duration)  # Rising
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 1.5 * t)
        
        # Quick envelope
        envelope = np.exp(-t * 4) * (1 - np.exp(-t * 20))
        
        # Add preset character
        signal = self._apply_preset_character(signal, preset, t)
        
        # Apply envelope
        signal *= envelope
        
        # Add teleport "pop" transient
        transient = np.random.normal(0, 0.15, int(0.02 * self.sample_rate))
        signal[:len(transient)] += transient
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.8
        
        return signal
    
    def generate_deactivation_sound(self, preset: str = "Void", duration: float = 0.8, seed: int = None) -> np.ndarray:
        """
        Generate portal deactivation sound (closing).
        
        Args:
            preset: Portal preset
            duration: Sound duration in seconds
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_preset_base_freq(preset)
        
        # Falling pitch with decay
        freq_sweep = base_freq * 2.0 * (1 - 0.6 * t / duration)  # Fall from 2x to 0.8x
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 2 * t)
        
        # Decay envelope
        envelope = np.exp(-t * 2)
        
        # Add preset character
        signal = self._apply_preset_character(signal, preset, t)
        
        # Apply envelope
        signal *= envelope
        
        # Add closing "snap"
        snap = np.random.normal(0, 0.1, int(0.05 * self.sample_rate))
        signal[-len(snap):] += snap * envelope[-len(snap):]
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.6
        
        return signal
    
    def _get_preset_base_freq(self, preset: str) -> float:
        """Get base frequency for portal preset."""
        preset_freqs = {
            'Void': 220,        # A3 - deep, mysterious
            'Fire': 330,        # E4 - bright, energetic
            'Ice': 165,         # E3 - cold, deep
            'Electric': 440,    # A4 - sharp, electric
            'Nature': 262,      # C4 - organic, earthy
            'Shadow': 196,      # G3 - dark, ominous
            'Light': 330,       # E4 - bright, pure
            'Generic': 220      # A3 - default
        }
        return preset_freqs.get(preset, 220)
    
    def _apply_preset_character(self, signal: np.ndarray, preset: str, t: np.ndarray) -> np.ndarray:
        """Apply preset-specific audio character."""
        if preset == 'Void':
            # Deep, spacey - add reverb-like tail
            tail = np.exp(-t * 0.5) * np.random.normal(0, 0.05, len(signal))
            signal += tail
        elif preset == 'Fire':
            # Bright, crackling - add high-frequency content
            crackle = np.random.normal(0, 0.1, len(signal)) * np.exp(-t * 1.5)
            signal += crackle
        elif preset == 'Ice':
            # Cold, crystalline - add harmonics
            signal += 0.2 * np.sin(2 * np.pi * signal * 5)
        elif preset == 'Electric':
            # Sharp, electric - add transients
            transients = np.random.normal(0, 0.15, len(signal))
            transients *= (np.random.rand(len(signal)) > 0.95).astype(float)
            signal += transients
        elif preset == 'Nature':
            # Organic, flowing - add slow vibrato
            vibrato = 1.0 + 0.05 * np.sin(2 * np.pi * 2 * t)
            signal *= vibrato
        elif preset == 'Shadow':
            # Dark, muffled - add subtle distortion
            signal = np.tanh(signal * 1.1)
        elif preset == 'Light':
            # Pure, clear - minimal processing
            pass
        
        return signal
    
    def generate_from_spec(self, spec: Dict, sound_type: str, seed: int = None) -> np.ndarray:
        """Generate portal sound (SA3 preferred)."""
        if seed is None:
            portal_name = spec.get('portalName', 'unknown')
            seed = int(hashlib.md5(portal_name.encode()).hexdigest()[:8], 16) % (2**31)

        preset = spec.get('preset', 'Void')
        duration = float(spec.get('duration', 1.0))

        if sa3 is not None:
            prompt = sa3.build_prompt(
                game="Terraria",
                name=spec.get("portalName", sound_type),
                description=spec.get("description", f"{preset} portal {sound_type}"),
                sound_type=f"portal {sound_type}",
                extra=f"preset={preset}, dimensional rift, fantasy",
            )
            result = sa3.maybe_generate(
                engine=self.engine,
                model_name=self.model,
                prompt=prompt,
                duration=max(0.4, min(duration, 8.0)),
                seed=seed,
            )
            if result is not None:
                audio, sr = result
                self.sample_rate = sr
                self.last_engine_used = "stable-audio"
                return audio[:, 0] if (audio.ndim == 2 and audio.shape[1] == 1) else audio

        self.last_engine_used = "procedural"
        if sound_type == 'activation':
            return self.generate_activation_sound(preset, duration, seed)
        elif sound_type == 'ambient':
            return self.generate_ambient_sound(preset, duration, seed)
        elif sound_type == 'teleport':
            return self.generate_teleport_sound(preset, duration, seed)
        elif sound_type == 'deactivation':
            return self.generate_deactivation_sound(preset, duration, seed)
        else:
            return self.generate_activation_sound(preset, duration, seed)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate Terraria portal audio')
    parser.add_argument('--spec', required=True, help='JSON specification file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--name', required=True, help='Portal name (safe)')
    parser.add_argument('--activation', action='store_true', help='Generate activation sound')
    parser.add_argument('--ambient', action='store_true', help='Generate ambient sound')
    parser.add_argument('--teleport', action='store_true', help='Generate teleport sound')
    parser.add_argument('--deactivation', action='store_true', help='Generate deactivation sound')
    parser.add_argument('--all', action='store_true', help='Generate all sound types')
    parser.add_argument('--engine', default=os.environ.get('AAMT_AUDIO_ENGINE', 'auto'),
                        choices=['auto', 'stable-audio', 'procedural'])
    parser.add_argument('--model', default=None)
    return parser.parse_args()

def main():
    if not DEPENDENCIES_AVAILABLE:
        print(f"ERROR: Cannot generate audio - missing dependency: {MISSING_DEPENDENCY}")
        print("Please install: pip install numpy soundfile")
        return 1
    
    args = parse_args()
    
    # Load specification
    with open(args.spec, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    # Create output directory
    sounds_dir = os.path.join(args.output, 'Sounds')
    os.makedirs(sounds_dir, exist_ok=True)
    
    # Create generator
    generator = TerrariaPortalAudioGenerator(engine=args.engine, model=args.model)
    
    # Generate activation sound
    if args.activation or args.all:
        activation_audio = generator.generate_from_spec(spec, 'activation')
        if len(activation_audio.shape) == 1:
            activation_audio = np.column_stack([activation_audio, activation_audio])
        
        activation_path = os.path.join(sounds_dir, f"{args.name}_activation.ogg")
        sf.write(activation_path, activation_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated activation sound: {activation_path}")
    
    # Generate ambient sound
    if args.ambient or args.all:
        ambient_audio = generator.generate_from_spec(spec, 'ambient')
        if len(ambient_audio.shape) == 1:
            ambient_audio = np.column_stack([ambient_audio, ambient_audio])
        
        ambient_path = os.path.join(sounds_dir, f"{args.name}_ambient.ogg")
        sf.write(ambient_path, ambient_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated ambient sound: {ambient_path}")
    
    # Generate teleport sound
    if args.teleport or args.all:
        teleport_audio = generator.generate_from_spec(spec, 'teleport')
        if len(teleport_audio.shape) == 1:
            teleport_audio = np.column_stack([teleport_audio, teleport_audio])
        
        teleport_path = os.path.join(sounds_dir, f"{args.name}_teleport.ogg")
        sf.write(teleport_path, teleport_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated teleport sound: {teleport_path}")
    
    # Generate deactivation sound
    if args.deactivation or args.all:
        deactivation_audio = generator.generate_from_spec(spec, 'deactivation')
        if len(deactivation_audio.shape) == 1:
            deactivation_audio = np.column_stack([deactivation_audio, deactivation_audio])
        
        deactivation_path = os.path.join(sounds_dir, f"{args.name}_deactivation.ogg")
        sf.write(deactivation_path, deactivation_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated deactivation sound: {deactivation_path}")
    
    print("\n[OK] Terraria portal audio generation complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
