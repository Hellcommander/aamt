#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caves of Qud Audio Generator
Generates procedural sound effects for Qud mods including creature sounds, attack sounds, ambient sounds, etc.
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

# Shared Stable Audio 3 backend (optional)
_SHARED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Shared")
if os.path.isdir(_SHARED) and _SHARED not in sys.path:
    sys.path.insert(0, os.path.abspath(_SHARED))
try:
    import aamt_stable_audio_backend as sa3
except ImportError:
    sa3 = None

class QudAudioGenerator:
    """Generates sound effects for Caves of Qud mods (Stable Audio 3 + procedural)."""
    
    def __init__(self, sample_rate: int = 44100, engine: str = "auto", model: str = None):
        self.sample_rate = sample_rate
        self.engine = engine
        self.model = model
        self.last_engine_used = "procedural"    
    def generate_attack_sound(self, creature_type: str = "generic", duration: float = 0.3, seed: int = None) -> np.ndarray:
        """Generate attack/swing sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Base frequency based on creature type
        base_freq = self._get_creature_base_freq(creature_type)
        
        # Sharp attack with quick decay
        freq = base_freq * 1.5
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.6 * np.sin(2 * np.pi * freq * 2 * t)
        signal += 0.3 * np.sin(2 * np.pi * freq * 3 * t)
        
        # Whoosh envelope
        envelope = np.exp(-t * 8) * (1 - np.exp(-t * 50))
        
        # Add transient for impact
        transient = np.random.normal(0, 0.2, int(0.01 * self.sample_rate))
        signal[:len(transient)] += transient
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
        
        return signal
    
    def generate_hit_sound(self, material: str = "flesh", duration: float = 0.2, seed: int = None) -> np.ndarray:
        """Generate hit/impact sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Material-based frequencies
        material_freqs = {
            "flesh": 200,
            "metal": 400,
            "stone": 300,
            "wood": 250,
            "crystal": 500,
            "generic": 300
        }
        base_freq = material_freqs.get(material.lower(), 300)
        
        # Sharp impact
        freq = base_freq * 2
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.8 * np.sin(2 * np.pi * freq * 1.5 * t)
        signal += 0.5 * np.sin(2 * np.pi * freq * 2.5 * t)
        
        # Very sharp attack, fast decay
        envelope = np.exp(-t * 15) * (1 - np.exp(-t * 100))
        
        # Impact transient
        transient = np.random.normal(0, 0.25, int(0.005 * self.sample_rate))
        signal[:len(transient)] += transient
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.8
        
        return signal
    
    def generate_death_sound(self, creature_type: str = "generic", duration: float = 0.5, seed: int = None) -> np.ndarray:
        """Generate death sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_creature_base_freq(creature_type)
        
        # Falling pitch with decay
        freq_sweep = base_freq * (1 - 0.5 * t / duration)
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 2 * t)
        
        # Decay envelope
        envelope = np.exp(-t * 3)
        
        # Add noise for texture
        noise = np.random.normal(0, 0.1, len(signal)) * envelope
        signal += noise
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.6
        
        return signal
    
    def generate_spawn_sound(self, creature_type: str = "generic", duration: float = 0.4, seed: int = None) -> np.ndarray:
        """Generate spawn/appear sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_creature_base_freq(creature_type)
        
        # Rising pitch
        freq_sweep = base_freq * (1 + 1.5 * t / duration)
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.4 * np.sin(2 * np.pi * freq_sweep * 2 * t)
        
        # Fade in, fade out
        envelope = np.exp(-t * 2) * (1 - np.exp(-t * 10))
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.6
        
        return signal
    
    def generate_ambient_sound(self, creature_type: str = "generic", duration: float = 2.0, seed: int = None) -> np.ndarray:
        """Generate ambient/idle sound (loopable)."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        base_freq = self._get_creature_base_freq(creature_type)
        
        # Low, steady tone with slow variation
        freq = base_freq * 0.7
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Slow modulation
        mod_freq = 0.3  # 0.3 Hz
        modulation = 1.0 + 0.1 * np.sin(2 * np.pi * mod_freq * t)
        signal *= modulation
        
        # Subtle noise
        noise = np.random.normal(0, 0.05, len(signal))
        signal += noise
        
        # Fade in/out for looping
        fade_samples = int(0.1 * self.sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        signal[:fade_samples] *= fade_in
        signal[-fade_samples:] *= fade_out
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.4
        
        return signal
    
    def generate_walk_sound(self, surface: str = "generic", duration: float = 0.15, seed: int = None) -> np.ndarray:
        """Generate walk/footstep sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Surface-based frequencies
        surface_freqs = {
            "dirt": 150,
            "stone": 200,
            "metal": 300,
            "wood": 180,
            "sand": 120,
            "generic": 170
        }
        base_freq = surface_freqs.get(surface.lower(), 170)
        
        # Thud-like sound
        freq = base_freq
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Quick attack, decay
        envelope = np.exp(-t * 6) * (1 - np.exp(-t * 30))
        
        # Add low-frequency thud
        thud = 0.3 * np.sin(2 * np.pi * 60 * t) * envelope
        signal += thud
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.5
        
        return signal
    
    def generate_use_sound(self, item_type: str = "generic", duration: float = 0.3, seed: int = None) -> np.ndarray:
        """Generate use/activate sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Item type frequencies
        item_freqs = {
            "mechanical": 300,
            "magical": 400,
            "electronic": 350,
            "generic": 250
        }
        base_freq = item_freqs.get(item_type.lower(), 250)
        
        # Click/activation sound
        freq = base_freq
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.6 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Quick click envelope
        envelope = np.exp(-t * 10) * (1 - np.exp(-t * 50))
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.6
        
        return signal
    
    def generate_missile_fire_sound(self, projectile_type: str = "generic", duration: float = 0.2, seed: int = None) -> np.ndarray:
        """Generate missile/projectile fire sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Projectile type frequencies
        proj_freqs = {
            "energy": 500,
            "physical": 300,
            "explosive": 400,
            "generic": 350
        }
        base_freq = proj_freqs.get(projectile_type.lower(), 350)
        
        # Sharp whoosh
        freq = base_freq * 1.2
        signal = np.sin(2 * np.pi * freq * t)
        signal += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        
        # Quick envelope
        envelope = np.exp(-t * 12) * (1 - np.exp(-t * 60))
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
        
        return signal
    
    def generate_detonated_sound(self, explosion_type: str = "generic", duration: float = 0.4, seed: int = None) -> np.ndarray:
        """Generate explosion/detonation sound."""
        if seed is not None:
            np.random.seed(seed)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Explosion: wide frequency range
        signal = np.zeros(len(t))
        
        # Low rumble
        signal += 0.5 * np.sin(2 * np.pi * 80 * t)
        
        # Mid frequencies
        signal += 0.4 * np.sin(2 * np.pi * 200 * t)
        signal += 0.3 * np.sin(2 * np.pi * 400 * t)
        
        # High crack
        signal += 0.2 * np.sin(2 * np.pi * 800 * t)
        
        # Decay envelope
        envelope = np.exp(-t * 4)
        
        # Add noise burst
        noise = np.random.normal(0, 0.3, len(signal)) * envelope
        signal += noise
        
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.8
        
        return signal
    
    def _get_creature_base_freq(self, creature_type: str) -> float:
        """Get base frequency for creature type."""
        creature_freqs = {
            "small": 400,      # High-pitched (small creatures)
            "medium": 250,     # Mid-range
            "large": 150,      # Low-pitched (large creatures)
            "insect": 500,     # Very high (insects)
            "beast": 200,      # Animal-like
            "robot": 300,      # Mechanical
            "mutant": 220,     # Organic but altered
            "generic": 250     # Default
        }
        return creature_freqs.get(creature_type.lower(), 250)
    
    def generate_from_spec(self, spec: Dict, sound_type: str, seed: int = None) -> np.ndarray:
        """
        Generate sound from specification (Stable Audio 3 preferred, procedural fallback).
        """
        if seed is None:
            sound_name = spec.get('name', 'unknown')
            seed = int(hashlib.md5(sound_name.encode()).hexdigest()[:8], 16) % (2**31)

        creature_type = spec.get('creatureType', 'generic')
        material = spec.get('material', 'generic')
        surface = spec.get('surface', 'generic')
        item_type = spec.get('itemType', 'generic')
        projectile_type = spec.get('projectileType', 'generic')
        explosion_type = spec.get('explosionType', 'generic')
        duration = float(spec.get('duration', 0.3))

        # Prefer Stable Audio 3 for asset quality
        use_sa3 = False
        if sa3 is not None:
            use_sa3 = sa3.resolve_engine(self.engine) == "stable-audio"
        if use_sa3:
            try:
                detail = (
                    f"creature={creature_type}, material={material}, surface={surface}, "
                    f"item={item_type}, projectile={projectile_type}, explosion={explosion_type}"
                )
                prompt = sa3.build_prompt(
                    game="Caves of Qud",
                    name=spec.get("name", sound_type),
                    description=spec.get("description", detail),
                    sound_type=sound_type,
                    extra="roguelike fantasy sci-fi, short SFX",
                )
                audio, sr = sa3.generate_array(
                    prompt,
                    duration=max(0.35, min(duration, 8.0)),
                    seed=seed,
                    model_name=self.model,
                )
                self.sample_rate = sr
                self.last_engine_used = "stable-audio"
                if audio.ndim == 2 and audio.shape[1] >= 1:
                    # Keep stereo or mono as generated; callers may stereo-up mono
                    return audio if audio.shape[1] > 1 else audio[:, 0]
                return audio
            except Exception as e:
                print(f"  [SA3->procedural] {sound_type}: {e}")

        self.last_engine_used = "procedural"
        if sound_type == 'attack':
            return self.generate_attack_sound(creature_type, duration, seed)
        elif sound_type == 'hit':
            return self.generate_hit_sound(material, duration, seed)
        elif sound_type == 'death':
            return self.generate_death_sound(creature_type, duration, seed)
        elif sound_type == 'spawn':
            return self.generate_spawn_sound(creature_type, duration, seed)
        elif sound_type == 'ambient' or sound_type == 'idle':
            return self.generate_ambient_sound(creature_type, duration, seed)
        elif sound_type == 'walk':
            return self.generate_walk_sound(surface, duration, seed)
        elif sound_type == 'run':
            return self.generate_walk_sound(surface, duration * 0.8, seed)  # Faster
        elif sound_type == 'jump':
            return self.generate_walk_sound(surface, duration * 0.5, seed)  # Quicker
        elif sound_type == 'land':
            return self.generate_hit_sound(surface, duration, seed)
        elif sound_type == 'use':
            return self.generate_use_sound(item_type, duration, seed)
        elif sound_type == 'missilefire' or sound_type == 'fire':
            return self.generate_missile_fire_sound(projectile_type, duration, seed)
        elif sound_type == 'detonated' or sound_type == 'explosion':
            return self.generate_detonated_sound(explosion_type, duration, seed)
        else:
            return self.generate_attack_sound(creature_type, duration, seed)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate Qud mod audio')
    parser.add_argument('--spec', required=True, help='JSON specification file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--name', required=True, help='Sound name (safe)')
    parser.add_argument('--type', required=True, help='Sound type (attack, hit, death, spawn, ambient, walk, use, etc.)')
    parser.add_argument('--engine', default=os.environ.get('AAMT_AUDIO_ENGINE', 'auto'),
                        choices=['auto', 'stable-audio', 'procedural'])
    parser.add_argument('--model', default=None, help='SA3 model (medium|small-sfx)')
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
    generator = QudAudioGenerator(engine=args.engine, model=args.model)
    
    # Generate sound
    audio = generator.generate_from_spec(spec, args.type.lower())
    
    # Convert to stereo
    if len(audio.shape) == 1:
        audio = np.column_stack([audio, audio])
    
    # Save as OGG (Qud supports OGG)
    output_path = os.path.join(sounds_dir, f"{args.name}.ogg")
    sf.write(output_path, audio, generator.sample_rate, format='OGG', subtype='VORBIS')
    
    print(f"Generated {args.type} sound via {generator.last_engine_used}: {output_path}")
    print("\n[OK] Qud audio generation complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
