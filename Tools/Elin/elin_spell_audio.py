#!/usr/bin/env python3
"""
Elin Spell Audio Generator
Generates procedural sound effects for Elin spells including cast sounds, impact sounds, and loop sounds.
"""

import os
import sys
import json
import argparse
import hashlib
from typing import Dict, List, Tuple

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

class SpellAudioGenerator:
    """Generates Elin spell SFX (Stable Audio 3 + procedural fallback)."""
    
    def __init__(self, sample_rate: int = 44100, engine: str = "auto", model: str = None):
        self.sample_rate = sample_rate
        self.engine = engine
        self.model = model
        self.last_engine_used = "procedural"
    
    def generate_cast_sound(self, spec: Dict, duration: float = 0.5, seed: int = None) -> np.ndarray:
        """
        Generate spell cast sound (whoosh, charge, etc.).
        
        Args:
            spec: Spell specification dictionary
            duration: Sound duration in seconds
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        spell_type = spec.get('spellType', 'magic').lower()
        school = spec.get('school', 'generic').lower()
        colors = spec.get('colors', ['#4caf50'])
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Base frequency based on spell school
        base_freq = self._get_school_base_freq(school)
        
        # Generate based on spell type
        if 'charge' in spell_type or 'cast' in spell_type:
            # Charging/charging sound - rising pitch
            freq_sweep = base_freq * (1 + 2 * t / duration)  # Rise from base to 3x
            signal = np.sin(2 * np.pi * freq_sweep * t)
            
            # Add harmonics
            signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 2 * t)
            signal += 0.3 * np.sin(2 * np.pi * freq_sweep * 3 * t)
            
            # Envelope: quick attack, sustain, release
            envelope = np.exp(-t * 2) * (1 - np.exp(-t * 20))
        elif 'burst' in spell_type or 'explosion' in spell_type:
            # Burst sound - sharp attack
            freq = base_freq * 2
            signal = np.sin(2 * np.pi * freq * t)
            signal += 0.7 * np.sin(2 * np.pi * freq * 1.5 * t)
            
            # Sharp envelope
            envelope = np.exp(-t * 8)
        elif 'beam' in spell_type or 'channel' in spell_type:
            # Beam/channel - steady with modulation
            freq = base_freq
            signal = np.sin(2 * np.pi * freq * t)
            signal += 0.4 * np.sin(2 * np.pi * freq * 2 * t)
            
            # Modulation
            mod = 1.0 + 0.2 * np.sin(2 * np.pi * 5 * t)
            signal *= mod
            
            # Envelope: fade in
            envelope = 1 - np.exp(-t * 5)
        else:
            # Default: magical whoosh
            freq = base_freq * (1 + 1.5 * t / duration)
            signal = np.sin(2 * np.pi * freq * t)
            signal += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
            envelope = np.exp(-t * 3)
        
        # Add school-specific character
        signal = self._apply_school_character(signal, school, t)
        
        # Apply envelope
        signal *= envelope
        
        # Add subtle noise for texture
        noise = np.random.normal(0, 0.05, len(signal))
        signal += noise
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
        
        return signal
    
    def generate_impact_sound(self, spec: Dict, duration: float = 0.3, seed: int = None) -> np.ndarray:
        """
        Generate spell impact/hit sound.
        
        Args:
            spec: Spell specification dictionary
            duration: Sound duration in seconds
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        school = spec.get('school', 'generic').lower()
        spell_type = spec.get('spellType', 'magic').lower()
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        base_freq = self._get_school_base_freq(school)
        
        # Impact: sharp attack with decay
        freq = base_freq * 2.5
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.8 * np.sin(2 * np.pi * freq * 1.5 * t)
        signal += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Sharp attack, fast decay
        envelope = np.exp(-t * 10) * (1 - np.exp(-t * 100))
        
        # Add school character
        signal = self._apply_school_character(signal, school, t)
        
        # Apply envelope
        signal *= envelope
        
        # Add impact transient
        transient = np.random.normal(0, 0.15, int(0.01 * self.sample_rate))
        signal[:len(transient)] += transient
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.8
        
        return signal
    
    def generate_loop_sound(self, spec: Dict, duration: float = 2.0, seed: int = None) -> np.ndarray:
        """
        Generate looping spell sound (for channeled spells, buffs, etc.).
        
        Args:
            spec: Spell specification dictionary
            duration: Sound duration in seconds (should be loopable)
            seed: Random seed for reproducibility
        
        Returns:
            Audio signal as numpy array
        """
        if seed is not None:
            np.random.seed(seed)
        
        school = spec.get('school', 'generic').lower()
        base_freq = self._get_school_base_freq(school)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Steady tone with slow modulation
        freq = base_freq
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.4 * np.sin(2 * np.pi * freq * 2 * t)
        signal += 0.2 * np.sin(2 * np.pi * freq * 3 * t)
        
        # Slow modulation for variation
        mod_freq = 0.5  # 0.5 Hz modulation
        modulation = 1.0 + 0.15 * np.sin(2 * np.pi * mod_freq * t)
        signal *= modulation
        
        # Add school character
        signal = self._apply_school_character(signal, school, t)
        
        # Fade in/out for smooth looping
        fade_samples = int(0.1 * self.sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        signal[:fade_samples] *= fade_in
        signal[-fade_samples:] *= fade_out
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.5
        
        return signal
    
    def _get_school_base_freq(self, school: str) -> float:
        """Get base frequency for spell school."""
        school_freqs = {
            'nature': 220,      # A3 - earthy, organic
            'fire': 330,        # E4 - bright, energetic
            'ice': 165,         # E3 - cold, deep
            'lightning': 440,   # A4 - sharp, electric
            'dark': 147,        # D3 - deep, ominous
            'light': 262,       # C4 - pure, clear
            'arachnomancy': 196, # G3 - dark, webby
            'dragon': 247,      # B3 - powerful, ancient
            'blood': 185,       # F#3 - visceral, dark
            'generic': 220      # A3 - default
        }
        return school_freqs.get(school.lower(), 220)
    
    def _apply_school_character(self, signal: np.ndarray, school: str, t: np.ndarray) -> np.ndarray:
        """Apply school-specific audio character."""
        if school == 'nature':
            # Organic, flowing - add slow vibrato
            vibrato = 1.0 + 0.05 * np.sin(2 * np.pi * 3 * t)
            signal *= vibrato
        elif school == 'fire':
            # Bright, crackling - add high-frequency content
            crackle = np.random.normal(0, 0.1, len(signal)) * np.exp(-t * 2)
            signal += crackle
        elif school == 'ice':
            # Cold, crystalline - add harmonics
            signal += 0.3 * np.sin(2 * np.pi * signal * 5)
        elif school == 'lightning':
            # Sharp, electric - add transients
            transients = np.random.normal(0, 0.2, len(signal))
            transients *= (np.random.rand(len(signal)) > 0.95).astype(float)
            signal += transients
        elif school == 'dark' or school == 'arachnomancy':
            # Dark, muffled - low-pass effect (simplified)
            # Add subtle distortion
            signal = np.tanh(signal * 1.2)
        elif school == 'light':
            # Pure, clear - minimal processing
            pass
        elif school == 'dragon':
            # Powerful, rumbling - add low frequencies
            low_freq = 55  # A1
            signal += 0.2 * np.sin(2 * np.pi * low_freq * t)
        
        return signal
    
    def generate_from_spec(self, spec: Dict, sound_type: str, seed: int = None) -> np.ndarray:
        """Generate sound from specification (SA3 preferred)."""
        if seed is None:
            spell_name = spec.get('spellName', 'unknown')
            seed = int(hashlib.md5(spell_name.encode()).hexdigest()[:8], 16) % (2**31)

        if sound_type == 'cast':
            duration = float(spec.get('castDuration', 0.5))
        elif sound_type == 'impact':
            duration = float(spec.get('impactDuration', 0.3))
        elif sound_type == 'loop':
            duration = float(spec.get('loopDuration', 2.0))
        else:
            duration = 0.5

        if sa3 is not None:
            prompt = sa3.build_prompt(
                game="Elin",
                name=spec.get("spellName", sound_type),
                description=spec.get("description") or spec.get("spellDescription", ""),
                sound_type=f"spell {sound_type}",
                extra=f"element={spec.get('element', 'arcane')}, fantasy magic SFX",
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
                return audio[:, 0] if audio.ndim == 2 and audio.shape[1] == 1 else (
                    audio if audio.ndim == 1 else audio
                )

        self.last_engine_used = "procedural"
        if sound_type == 'cast':
            return self.generate_cast_sound(spec, duration, seed)
        elif sound_type == 'impact':
            return self.generate_impact_sound(spec, duration, seed)
        elif sound_type == 'loop':
            return self.generate_loop_sound(spec, duration, seed)
        else:
            return self.generate_cast_sound(spec, 0.5, seed)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate Elin spell audio')
    parser.add_argument('--spec', required=True, help='JSON specification file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--name', required=True, help='Spell name (safe)')
    parser.add_argument('--cast', action='store_true', help='Generate cast sound')
    parser.add_argument('--impact', action='store_true', help='Generate impact sound')
    parser.add_argument('--loop', action='store_true', help='Generate loop sound')
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
    audio_dir = os.path.join(args.output, 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # Create generator
    generator = SpellAudioGenerator(engine=args.engine, model=args.model)
    
    # Generate cast sound
    if args.cast or args.all:
        cast_audio = generator.generate_from_spec(spec, 'cast')
        # Convert to stereo
        if len(cast_audio.shape) == 1:
            cast_audio = np.column_stack([cast_audio, cast_audio])
        
        cast_path = os.path.join(audio_dir, f"{args.name}_cast.ogg")
        sf.write(cast_path, cast_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated cast sound via {generator.last_engine_used}: {cast_path}")
    
    # Generate impact sound
    if args.impact or args.all:
        impact_audio = generator.generate_from_spec(spec, 'impact')
        # Convert to stereo
        if len(impact_audio.shape) == 1:
            impact_audio = np.column_stack([impact_audio, impact_audio])
        
        impact_path = os.path.join(audio_dir, f"{args.name}_impact.ogg")
        sf.write(impact_path, impact_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated impact sound via {generator.last_engine_used}: {impact_path}")
    
    # Generate loop sound
    if args.loop or args.all:
        loop_audio = generator.generate_from_spec(spec, 'loop')
        # Convert to stereo
        if len(loop_audio.shape) == 1:
            loop_audio = np.column_stack([loop_audio, loop_audio])
        
        loop_path = os.path.join(audio_dir, f"{args.name}_loop.ogg")
        sf.write(loop_path, loop_audio, generator.sample_rate, format='OGG', subtype='VORBIS')
        print(f"Generated loop sound via {generator.last_engine_used}: {loop_path}")
    
    print("\n[OK] Elin spell audio generation complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
