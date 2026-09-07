#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Starbound Audio Generator
Generates procedural sound effects for Starbound mods including impact, charge, ambient, magic, mechanical, organic, explosion, whoosh, and roar sounds.
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

# Optional scipy for advanced signal processing
try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

_SHARED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Shared")
if os.path.isdir(_SHARED) and _SHARED not in sys.path:
    sys.path.insert(0, os.path.abspath(_SHARED))
try:
    import aamt_stable_audio_backend as sa3
except ImportError:
    sa3 = None

class StarboundAudioGenerator:
    """Generates Starbound mod SFX (Stable Audio 3 + procedural)."""
    
    def __init__(self, sample_rate: int = 44100, engine: str = "auto", model: str = None):
        self.sample_rate = sample_rate
        self.engine = engine
        self.model = model
        self.last_engine_used = "procedural"
    
    def generate_impact_sound(self, duration: float = 0.2, frequency: float = 200, volume: float = 0.8, seed: int = None) -> np.ndarray:
        """
        Generate impact sound (hits, strikes, collisions).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Sharp attack with quick decay
        signal = np.sin(2 * np.pi * frequency * t) * np.exp(-t * 10)
        
        # Add noise for impact texture
        noise = np.random.normal(0, 0.1, len(t)) * np.exp(-t * 15)
        signal += noise
        
        # Add low-frequency thud
        thud = np.sin(2 * np.pi * frequency * 0.3 * t) * np.exp(-t * 5)
        signal += 0.3 * thud
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_charge_sound(self, duration: float = 0.5, frequency: float = 300, volume: float = 0.7, seed: int = None) -> np.ndarray:
        """
        Generate charge sound (building energy, charging up).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Rising pitch
        freq_sweep = np.linspace(frequency * 0.5, frequency * 1.5, len(t))
        signal = np.sin(2 * np.pi * freq_sweep * t)
        
        # Build-up envelope
        envelope = (1 - np.exp(-t * 2)) * np.exp(-t * 0.5)
        signal *= envelope
        
        # Add harmonics for energy feel
        signal += 0.4 * np.sin(2 * np.pi * freq_sweep * 2 * t) * envelope
        signal += 0.2 * np.sin(2 * np.pi * freq_sweep * 3 * t) * envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_ambient_sound(self, duration: float = 2.0, frequency: float = 220, volume: float = 0.4, seed: int = None) -> np.ndarray:
        """
        Generate ambient sound (background, loopable).
        
        Args:
            duration: Sound duration in seconds (should be loopable)
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Steady tone with slow modulation
        signal = np.sin(2 * np.pi * frequency * t)
        signal += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
        
        # Slow modulation for variation
        mod_freq = 0.3  # 0.3 Hz
        modulation = 1.0 + 0.1 * np.sin(2 * np.pi * mod_freq * t)
        signal *= modulation
        
        # Fade in/out for smooth looping
        fade_samples = int(0.1 * self.sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        signal[:fade_samples] *= fade_in
        signal[-fade_samples:] *= fade_out
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_magic_sound(self, duration: float = 0.8, frequency: float = 600, volume: float = 0.6, seed: int = None) -> np.ndarray:
        """
        Generate magic sound (ethereal, mystical energy).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Multiple harmonics with modulation
        signal = np.sin(2 * np.pi * frequency * t)
        signal += 0.5 * np.sin(2 * np.pi * frequency * 2 * t)
        signal += 0.3 * np.sin(2 * np.pi * frequency * 3 * t)
        
        # Ethereal modulation
        modulation = np.sin(2 * np.pi * 2 * t)
        signal *= (0.7 + 0.3 * modulation)
        
        # Add shimmer
        shimmer = np.random.normal(0, 0.05, len(t)) * np.exp(-t * 0.5)
        signal += shimmer
        
        # Envelope
        envelope = (1 - np.exp(-t * 1.5)) * np.exp(-t * 0.3)
        signal *= envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_mechanical_sound(self, duration: float = 0.3, frequency: float = 400, volume: float = 0.7, seed: int = None) -> np.ndarray:
        """
        Generate mechanical sound (machines, gears, clicks).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Square wave with harmonics (mechanical character)
        if SCIPY_AVAILABLE:
            signal = signal.square(2 * np.pi * frequency * t, duty=0.5) * 0.5
        else:
            # Fallback: approximate square wave with harmonics
            signal = np.sin(2 * np.pi * frequency * t)
            signal += 0.33 * np.sin(2 * np.pi * frequency * 3 * t)
            signal += 0.2 * np.sin(2 * np.pi * frequency * 5 * t)
            signal *= 0.5
        
        signal += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
        
        # Add clicking transients
        clicks = np.random.normal(0, 0.1, len(t))
        click_mask = (np.random.rand(len(t)) > 0.9).astype(float)
        signal += clicks * click_mask
        
        # Quick envelope
        envelope = np.exp(-t * 3)
        signal *= envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_organic_sound(self, duration: float = 0.6, frequency: float = 150, volume: float = 0.6, seed: int = None) -> np.ndarray:
        """
        Generate organic sound (biological, natural).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Natural resonance with vibrato
        signal = np.sin(2 * np.pi * frequency * t)
        signal += 0.4 * np.sin(2 * np.pi * frequency * 1.5 * t)
        
        # Organic vibrato
        vibrato = 1.0 + 0.08 * np.sin(2 * np.pi * 3 * t)
        signal *= vibrato
        
        # Natural decay
        envelope = (1 - np.exp(-t * 1)) * np.exp(-t * 0.8)
        signal *= envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_explosion_sound(self, duration: float = 0.4, frequency: float = 100, volume: float = 0.9, seed: int = None) -> np.ndarray:
        """
        Generate explosion sound (booms, blasts).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Low frequency rumble
        signal = np.sin(2 * np.pi * frequency * 0.5 * t)
        signal += 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Explosive noise burst
        noise = np.random.normal(0, 0.3, len(t))
        noise_envelope = np.exp(-t * 8)
        signal += noise * noise_envelope
        
        # Decay envelope
        envelope = np.exp(-t * 2)
        signal *= envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_whoosh_sound(self, duration: float = 0.3, frequency: float = 500, volume: float = 0.6, seed: int = None) -> np.ndarray:
        """
        Generate whoosh sound (air movement, fast motion).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # White noise with frequency sweep
        noise = np.random.normal(0, 0.3, len(t))
        freq_sweep = np.linspace(frequency * 2, frequency * 0.5, len(t))
        signal = noise * np.sin(2 * np.pi * freq_sweep * t)
        
        # Quick envelope
        envelope = (1 - np.exp(-t * 10)) * np.exp(-t * 5)
        signal *= envelope
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_roar_sound(self, duration: float = 1.0, frequency: float = 80, volume: float = 0.8, seed: int = None) -> np.ndarray:
        """
        Generate roar sound (powerful, deep vocalizations).
        
        Args:
            duration: Sound duration in seconds
            frequency: Base frequency in Hz
            volume: Volume level (0.0-1.0)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Low frequency with noise
        signal = np.sin(2 * np.pi * frequency * 0.3 * t)
        signal += 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Build-up and sustain
        envelope = (1 - np.exp(-t * 0.5)) * (0.3 + 0.7 * np.exp(-t * 0.2))
        signal *= envelope
        
        # Add growling noise
        noise = np.random.normal(0, 0.2, len(t)) * np.exp(-t * 1)
        signal += noise
        
        # Normalize and apply volume
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * volume
        
        return signal
    
    def generate_from_spec(self, spec: Dict, sound_type: str, seed: int = None) -> np.ndarray:
        """Generate sound from specification (SA3 preferred)."""
        if seed is None:
            sound_name = spec.get('soundName', 'unknown')
            seed = int(hashlib.md5(sound_name.encode()).hexdigest()[:8], 16) % (2**31)

        duration = float(spec.get('duration', 0.5))
        frequency = spec.get('frequency', 440)
        volume = spec.get('volume', 0.7)
        sound_type_lower = sound_type.lower()

        if sa3 is not None:
            prompt = sa3.build_prompt(
                game="Starbound",
                name=spec.get("soundName", sound_type),
                description=spec.get("description", f"{sound_type} SFX"),
                sound_type=sound_type_lower,
                extra=f"frequency≈{frequency}Hz, sci-fi pixel-game style",
            )
            result = sa3.maybe_generate(
                engine=self.engine,
                model_name=self.model,
                prompt=prompt,
                duration=max(0.35, min(duration, 8.0)),
                seed=seed,
            )
            if result is not None:
                audio, sr = result
                self.sample_rate = sr
                self.last_engine_used = "stable-audio"
                # Soft volume scale
                peak = np.max(np.abs(audio)) + 1e-8
                audio = audio / peak * float(volume)
                return audio[:, 0] if (audio.ndim == 2 and audio.shape[1] == 1) else audio

        self.last_engine_used = "procedural"
        if sound_type_lower == 'impact':
            return self.generate_impact_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'charge':
            return self.generate_charge_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'ambient':
            return self.generate_ambient_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'magic':
            return self.generate_magic_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'mechanical':
            return self.generate_mechanical_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'organic':
            return self.generate_organic_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'explosion':
            return self.generate_explosion_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'whoosh':
            return self.generate_whoosh_sound(duration, frequency, volume, seed)
        elif sound_type_lower == 'roar':
            return self.generate_roar_sound(duration, frequency, volume, seed)
        else:
            return self.generate_impact_sound(duration, frequency, volume, seed)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate Starbound audio')
    parser.add_argument('--spec', required=True, help='JSON specification file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--name', required=True, help='Sound name (safe)')
    parser.add_argument('--type', required=True, help='Sound type (impact, charge, ambient, magic, mechanical, organic, explosion, whoosh, roar)')
    parser.add_argument('--format', default='ogg', choices=['wav', 'ogg'], help='Output format')
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
    sounds_dir = os.path.join(args.output, 'sounds')
    os.makedirs(sounds_dir, exist_ok=True)
    
    # Create generator
    generator = StarboundAudioGenerator(engine=args.engine, model=args.model)
    
    # Generate sound
    audio = generator.generate_from_spec(spec, args.type)
    
    # Convert to stereo
    if len(audio.shape) == 1:
        audio = np.column_stack([audio, audio])
    
    # Save audio
    output_path = os.path.join(sounds_dir, f"{args.name}.{args.format}")
    if args.format == 'ogg':
        sf.write(output_path, audio, generator.sample_rate, format='OGG', subtype='VORBIS')
    else:
        sf.write(output_path, audio, generator.sample_rate, format='WAV')
    
    print(f"Generated sound: {output_path}")
    print("\n[OK] Starbound audio generation complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
