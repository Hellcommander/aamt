"""
Space Whale FX Variation Generator and Quality Assessor
Generates multiple variations of each FX effect and selects the best ones based on quality metrics.
"""

import json
import random
import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
from queue import Queue

# Import 20-level quality system
try:
    from space_whale_quality_system import (
        QualityLevel, QualityScore20, get_quality_level,
        get_quality_threshold, format_quality_score, is_production_ready
    )
    QUALITY_20_AVAILABLE = True
except ImportError:
    QUALITY_20_AVAILABLE = False
    # Fallback to old system if import fails
    class QualityTier(Enum):
        EXCELLENT = 5
        VERY_GOOD = 4
        GOOD = 3
        ACCEPTABLE = 2
        POOR = 1
    
    @dataclass
    class QualityScore:
        visual_quality: float = 0.0
        feature_completeness: float = 0.0
        technical_quality: float = 0.0
        aesthetic_appeal: float = 0.0
        overall: float = 0.0
        tier: QualityTier = QualityTier.POOR
        notes: List[str] = field(default_factory=list)

# Backward compatibility: keep old QualityScore for transition
if QUALITY_20_AVAILABLE:
    @dataclass
    class QualityScore:
        """Legacy QualityScore for backward compatibility."""
        visual_quality: float = 0.0
        feature_completeness: float = 0.0
        technical_quality: float = 0.0
        aesthetic_appeal: float = 0.0
        overall: float = 0.0
        tier: QualityTier = None  # Will be converted
        notes: List[str] = field(default_factory=list)
        
        def to_quality_score_20(self) -> QualityScore20:
            """Convert legacy score to 20-level system."""
            return QualityScore20.from_scores(
                self.visual_quality,
                self.feature_completeness,
                self.technical_quality,
                self.aesthetic_appeal,
                self.notes
            )

class FXVariationGenerator:
    """Generates multiple variations of FX effects with different parameter combinations."""
    
    def __init__(self, base_registry_path: str):
        with open(base_registry_path, 'r') as f:
            self.base_registry = json.load(f)
    
    def generate_color_variations(self, base_color: str, count: int = 3) -> List[str]:
        """Generate color variations around a base color."""
        variations = [base_color]
        
        # Parse base color
        r = int(base_color[1:3], 16)
        g = int(base_color[3:5], 16)
        b = int(base_color[5:7], 16)
        
        for i in range(count - 1):
            # Vary saturation and brightness
            variation = random.randint(0, 2)
            if variation == 0:  # More saturated
                r = min(255, int(r * 1.2))
                g = min(255, int(g * 1.2))
                b = min(255, int(b * 1.2))
            elif variation == 1:  # Brighter
                r = min(255, int(r + (255 - r) * 0.3))
                g = min(255, int(g + (255 - g) * 0.3))
                b = min(255, int(b + (255 - b) * 0.3))
            else:  # Shift hue slightly
                r, g, b = self.shift_hue(r, g, b, random.uniform(-20, 20))
            
            variations.append(f"#{r:02x}{g:02x}{b:02x}")
        
        return variations
    
    def shift_hue(self, r: int, g: int, b: int, degrees: float) -> Tuple[int, int, int]:
        """Shift RGB color hue by degrees."""
        # Convert to HSV, shift, convert back
        # Simplified version
        if abs(degrees) < 5:
            return r, g, b
        
        # Simple hue shift approximation
        if degrees > 0:
            r, g, b = min(255, int(r * 1.1)), g, min(255, int(b * 1.1))
        else:
            r, g, b = r, min(255, int(g * 1.1)), min(255, int(b * 1.1))
        
        return r, g, b
    
    def generate_intensity_variations(self, base: float, count: int = 3) -> List[float]:
        """Generate intensity variations."""
        variations = [base]
        for i in range(count - 1):
            if i == 0:
                variations.append(base * 0.8)  # Softer
            else:
                variations.append(base * 1.2)  # Brighter
        return variations
    
    def generate_distortion_variations(self, base: float, count: int = 3) -> List[float]:
        """Generate distortion strength variations."""
        variations = [base]
        for i in range(count - 1):
            if i == 0:
                variations.append(base * 0.7)  # Subtle
            else:
                variations.append(base * 1.3)  # Strong
        return variations
    
    def generate_particle_variations(self, base_count: int, count: int = 3) -> List[int]:
        """Generate particle count variations."""
        variations = [base_count]
        for i in range(count - 1):
            if i == 0:
                variations.append(int(base_count * 0.75))  # Fewer (performance)
            else:
                variations.append(int(base_count * 1.25))  # More (visual impact)
        return variations
    
    def generate_effect_variations(self, effect_id: str, variation_count: int = 5) -> List[Dict]:
        """Generate multiple variations of a single effect."""
        # Find base effect
        base_effect = None
        for effect in self.base_registry['effects']:
            if effect['id'] == effect_id:
                base_effect = effect
                break
        
        if not base_effect:
            return []
        
        variations = []
        
        # Create more diverse variations
        for v in range(variation_count):
            variation = json.loads(json.dumps(base_effect))  # Deep copy
            
            # Modify ID
            variation['id'] = f"{effect_id}_v{v+1:02d}"
            
            visual = variation['visual']
            
            # More diverse color variations (5 different approaches)
            color_approach = v % 5
            if color_approach == 0:
                # Original color
                pass
            elif color_approach == 1:
                # More saturated
                color_vars = self.generate_color_variations(visual['coreColor'], 5)
                visual['coreColor'] = color_vars[min(1, v // 5)]
            elif color_approach == 2:
                # Brighter
                color_vars = self.generate_color_variations(visual['coreColor'], 5)
                visual['coreColor'] = color_vars[min(2, v // 5)]
            elif color_approach == 3:
                # Shifted hue
                color_vars = self.generate_color_variations(visual['coreColor'], 5)
                visual['coreColor'] = color_vars[min(3, v // 5)]
            else:
                # Complementary
                color_vars = self.generate_color_variations(visual['coreColor'], 5)
                visual['coreColor'] = color_vars[min(4, v // 5)]
            
            # More diverse intensity variations
            if 'coreGlow' in visual and visual['coreGlow']['enabled']:
                intensity_base = visual['coreGlow']['intensity']
                # Create 5 intensity levels
                intensity_levels = [
                    intensity_base * 0.7,  # Softer
                    intensity_base * 0.85, # Slightly softer
                    intensity_base,       # Original
                    intensity_base * 1.15, # Slightly brighter
                    intensity_base * 1.3  # Brighter
                ]
                visual['coreGlow']['intensity'] = intensity_levels[v % len(intensity_levels)]
                
                # Vary pulse/expand settings
                if v % 3 == 0:
                    visual['coreGlow']['pulse'] = True
                    visual['coreGlow']['expand'] = False
                elif v % 3 == 1:
                    visual['coreGlow']['pulse'] = False
                    visual['coreGlow']['expand'] = True
                else:
                    visual['coreGlow']['pulse'] = True
                    visual['coreGlow']['expand'] = True
            
            # More diverse distortion variations
            if 'distortionStrength' in visual:
                dist_base = visual['distortionStrength']
                dist_levels = [
                    dist_base * 0.6,   # Subtle
                    dist_base * 0.8,   # Moderate
                    dist_base,         # Original
                    dist_base * 1.2,  # Strong
                    dist_base * 1.4   # Very strong
                ]
                visual['distortionStrength'] = dist_levels[v % len(dist_levels)]
            
            # More diverse particle variations
            if 'particles' in variation:
                particles = variation['particles']
                
                # Burst particles
                if 'burstCount' in particles and particles['burstCount'] > 0:
                    base_count = particles['burstCount']
                    part_levels = [
                        int(base_count * 0.6),   # Fewer (performance)
                        int(base_count * 0.8),  # Slightly fewer
                        base_count,             # Original
                        int(base_count * 1.2),  # More
                        int(base_count * 1.4)   # Many (visual impact)
                    ]
                    particles['burstCount'] = part_levels[v % len(part_levels)]
                
                # Orbital particles
                if 'orbitalParticles' in particles and particles['orbitalParticles']['enabled']:
                    base_count = particles['orbitalParticles']['count']
                    part_levels = [
                        int(base_count * 0.7),
                        int(base_count * 0.85),
                        base_count,
                        int(base_count * 1.15),
                        int(base_count * 1.3)
                    ]
                    particles['orbitalParticles']['count'] = part_levels[v % len(part_levels)]
                
                # Core particles
                if 'coreParticles' in particles and particles['coreParticles']['enabled']:
                    base_count = particles['coreParticles']['count']
                    part_levels = [
                        max(4, int(base_count * 0.7)),
                        max(6, int(base_count * 0.85)),
                        base_count,
                        int(base_count * 1.15),
                        int(base_count * 1.3)
                    ]
                    particles['coreParticles']['count'] = part_levels[v % len(part_levels)]
            
            # More diverse timing variations
            if 'timing' in variation:
                timing = variation['timing']
                if 'coreExpandTime' in timing and timing['coreExpandTime'] > 0:
                    timing['coreExpandTime'] *= random.uniform(0.85, 1.15)
                if 'fadeOutTime' in timing and timing['fadeOutTime'] > 0:
                    timing['fadeOutTime'] *= random.uniform(0.85, 1.15)
                if 'shockwaveExpandTime' in timing and timing['shockwaveExpandTime'] > 0:
                    timing['shockwaveExpandTime'] *= random.uniform(0.85, 1.15)
            
            # Vary bloom settings
            if 'bloom' in visual and visual['bloom']['enabled']:
                bloom_intensity_base = visual['bloom']['intensity']
                bloom_levels = [
                    bloom_intensity_base * 0.8,
                    bloom_intensity_base * 0.9,
                    bloom_intensity_base,
                    bloom_intensity_base * 1.1,
                    bloom_intensity_base * 1.2
                ]
                visual['bloom']['intensity'] = bloom_levels[v % len(bloom_levels)]
            
            # Vary shockwave settings
            if 'shockwave' in visual and visual['shockwave']['enabled']:
                if v % 3 == 0:
                    visual['shockwave']['ringCount'] = 1
                elif v % 3 == 1:
                    visual['shockwave']['ringCount'] = 2
                else:
                    visual['shockwave']['ringCount'] = 3
            
            variations.append(variation)
        
        return variations

class FXQualityAssessor:
    """Assesses quality of FX effects based on multiple criteria."""
    
    def assess_visual_quality(self, effect: Dict) -> Tuple[float, List[str]]:
        """Assess visual quality: color harmony, smoothness, intensity balance."""
        score = 0.0
        notes = []
        
        visual = effect.get('visual', {})
        
        # Color harmony (0-2 points)
        core_color = visual.get('coreColor', '#ffffff')
        rim_color = visual.get('rimColor', '#ffffff')
        bloom_color = visual.get('bloomColor', '#ffffff')
        
        if self.colors_harmonize(core_color, rim_color, bloom_color):
            score += 2.0
            notes.append("Excellent color harmony")
        elif self.colors_acceptable(core_color, rim_color, bloom_color):
            score += 1.0
            notes.append("Good color harmony")
        else:
            notes.append("Color harmony could be improved")
        
        # Intensity balance (0-2 points)
        if 'coreGlow' in visual and visual['coreGlow']['enabled']:
            intensity = visual['coreGlow']['intensity']
            if 2.0 <= intensity <= 4.0:
                score += 2.0
                notes.append("Optimal intensity range")
            elif 1.5 <= intensity <= 5.0:
                score += 1.0
                notes.append("Acceptable intensity")
            else:
                notes.append(f"Intensity {intensity} may be too weak/strong")
        
        # Distortion balance (0-1 point)
        if 'distortionStrength' in visual:
            dist = visual['distortionStrength']
            if 0.02 <= dist <= 0.12:
                score += 1.0
                notes.append("Good distortion strength")
            elif dist > 0.15:
                notes.append("Distortion may be too strong")
        
        return min(5.0, score), notes
    
    def assess_feature_completeness(self, effect: Dict) -> Tuple[float, List[str]]:
        """Assess feature completeness: all required layers, particles, timing."""
        score = 0.0
        notes = []
        
        visual = effect.get('visual', {})
        particles = effect.get('particles', {})
        timing = effect.get('timing', {})
        
        # Core glow (1 point)
        if 'coreGlow' in visual and visual['coreGlow']['enabled']:
            score += 1.0
        else:
            notes.append("Missing core glow")
        
        # Bloom (0.5 points)
        if 'bloom' in visual and visual['bloom']['enabled']:
            score += 0.5
        else:
            notes.append("Missing bloom (recommended)")
        
        # Particles (1 point)
        has_particles = False
        if particles.get('burstCount', 0) > 0:
            has_particles = True
        if 'orbitalParticles' in particles and particles['orbitalParticles']['enabled']:
            has_particles = True
        if 'coreParticles' in particles and particles['coreParticles']['enabled']:
            has_particles = True
        
        if has_particles:
            score += 1.0
        else:
            notes.append("No particles (may lack visual interest)")
        
        # Distortion (0.5 points)
        if 'distortionStrength' in visual and visual['distortionStrength'] > 0:
            score += 0.5
        else:
            notes.append("No distortion (may lack depth)")
        
        # Timing (1 point)
        if timing:
            score += 1.0
        else:
            notes.append("Missing timing configuration")
        
        # Shockwave for appropriate types (1 point)
        effect_type = effect.get('type', '')
        if effect_type in ['shockwave', 'explosion', 'spawn']:
            if 'shockwave' in visual and visual['shockwave']['enabled']:
                score += 1.0
            else:
                notes.append("Shockwave recommended for this effect type")
        
        return min(5.0, score), notes
    
    def assess_technical_quality(self, effect: Dict) -> Tuple[float, List[str]]:
        """Assess technical quality: file size, performance, compatibility."""
        score = 0.0
        notes = []
        
        visual = effect.get('visual', {})
        particles = effect.get('particles', {})
        
        # Sprite size appropriateness (1 point)
        sprite_size = visual.get('spriteSize', 64)
        effect_type = effect.get('type', '')
        
        if effect_type == 'aura':
            if 128 <= sprite_size <= 512:
                score += 1.0
            else:
                notes.append(f"Sprite size {sprite_size} may not be optimal for aura")
        elif effect_type in ['shockwave', 'explosion']:
            if 256 <= sprite_size <= 512:
                score += 1.0
            else:
                notes.append(f"Sprite size {sprite_size} may not be optimal")
        else:
            if 64 <= sprite_size <= 256:
                score += 1.0
        
        # Frame count appropriateness (1 point)
        frames = visual.get('frames', 12)
        if 8 <= frames <= 24:
            score += 1.0
        elif frames > 24:
            notes.append(f"High frame count {frames} may impact performance")
        
        # Particle count performance (1 point)
        total_particles = 0
        if particles.get('burstCount', 0) > 0:
            total_particles += particles['burstCount']
        if 'orbitalParticles' in particles and particles['orbitalParticles']['enabled']:
            total_particles += particles['orbitalParticles']['count']
        if 'coreParticles' in particles and particles['coreParticles']['enabled']:
            total_particles += particles['coreParticles']['count']
        
        if total_particles <= 48:
            score += 1.0
            notes.append("Particle count optimized for performance")
        elif total_particles <= 64:
            score += 0.5
            notes.append("Particle count acceptable")
        else:
            notes.append(f"High particle count {total_particles} may impact performance")
        
        # Export configuration (1 point)
        if 'export' in effect and 'unid' in effect['export']:
            score += 1.0
        else:
            notes.append("Missing export configuration")
        
        # Resource paths (1 point)
        if 'export' in effect and 'resourcePaths' in effect['export']:
            score += 1.0
        else:
            notes.append("Missing resource paths")
        
        return min(5.0, score), notes
    
    def assess_aesthetic_appeal(self, effect: Dict) -> Tuple[float, List[str]]:
        """Assess aesthetic appeal: Nova Drift style match, visual interest."""
        score = 0.0
        notes = []
        
        visual = effect.get('visual', {})
        style = effect.get('style', '')
        
        # Nova Drift style match (2 points)
        if style == 'novaDrift':
            score += 2.0
            notes.append("Nova Drift style confirmed")
        else:
            notes.append("Style not explicitly Nova Drift")
        
        # High-energy feel (1 point)
        if 'coreGlow' in visual and visual['coreGlow']['enabled']:
            intensity = visual['coreGlow']['intensity']
            if intensity >= 3.0:
                score += 1.0
                notes.append("High-energy glow present")
        
        # Smooth transitions (1 point)
        timing = effect.get('timing', {})
        if 'easeIn' in timing and 'easeOut' in timing:
            score += 1.0
            notes.append("Smooth easing curves configured")
        
        # Layered composition (1 point)
        layers = visual.get('layers', [])
        if len(layers) >= 3:
            score += 1.0
            notes.append("Rich layered composition")
        elif len(layers) >= 2:
            score += 0.5
            notes.append("Good layer composition")
        
        return min(5.0, score), notes
    
    def colors_harmonize(self, c1: str, c2: str, c3: str) -> bool:
        """Check if colors harmonize well."""
        # Simple check: colors should be similar hue or complementary
        # For now, just check they're not too different
        def hex_to_rgb(hex_str):
            return tuple(int(hex_str[i:i+2], 16) for i in (1, 3, 5))
        
        rgb1 = hex_to_rgb(c1)
        rgb2 = hex_to_rgb(c2)
        rgb3 = hex_to_rgb(c3)
        
        # Check if colors are in similar ranges
        avg_r = (rgb1[0] + rgb2[0] + rgb3[0]) / 3
        avg_g = (rgb1[1] + rgb2[1] + rgb3[1]) / 3
        avg_b = (rgb1[2] + rgb2[2] + rgb3[2]) / 3
        
        # Colors should be within reasonable range of average
        threshold = 80
        for rgb in [rgb1, rgb2, rgb3]:
            if (abs(rgb[0] - avg_r) > threshold or 
                abs(rgb[1] - avg_g) > threshold or 
                abs(rgb[2] - avg_b) > threshold):
                return False
        
        return True
    
    def colors_acceptable(self, c1: str, c2: str, c3: str) -> bool:
        """Check if colors are at least acceptable."""
        # Less strict check
        def hex_to_rgb(hex_str):
            return tuple(int(hex_str[i:i+2], 16) for i in (1, 3, 5))
        
        rgb1 = hex_to_rgb(c1)
        rgb2 = hex_to_rgb(c2)
        rgb3 = hex_to_rgb(c3)
        
        # Check if at least two colors are similar
        def color_distance(rgb1, rgb2):
            return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
        
        dists = [
            color_distance(rgb1, rgb2),
            color_distance(rgb2, rgb3),
            color_distance(rgb1, rgb3)
        ]
        
        return min(dists) < 100  # At least two colors are similar
    
    def assess_effect(self, effect: Dict) -> QualityScore:
        """Assess overall quality of an effect using 20-level system."""
        visual_q, visual_notes = self.assess_visual_quality(effect)
        feature_q, feature_notes = self.assess_feature_completeness(effect)
        technical_q, technical_notes = self.assess_technical_quality(effect)
        aesthetic_q, aesthetic_notes = self.assess_aesthetic_appeal(effect)
        
        notes = visual_notes + feature_notes + technical_notes + aesthetic_notes
        
        # Use 20-level system if available
        if QUALITY_20_AVAILABLE:
            quality_20 = QualityScore20.from_scores(
                visual_q, feature_q, technical_q, aesthetic_q, notes
            )
            # Return legacy format for compatibility, but with 20-level overall
            return QualityScore(
                visual_quality=visual_q,
                feature_completeness=feature_q,
                technical_quality=technical_q,
                aesthetic_appeal=aesthetic_q,
                overall=quality_20.overall / 4.0,  # Convert 1-20 to 0-5 for legacy
                tier=None,  # Will use quality_20.level
                notes=notes
            )
        else:
            # Fallback to old 0-5 system
            overall = (
                visual_q * 0.3 +
                feature_q * 0.25 +
                technical_q * 0.25 +
                aesthetic_q * 0.2
            )
            
            # Determine tier
            if overall >= 4.5:
                tier = QualityTier.EXCELLENT
            elif overall >= 4.0:
                tier = QualityTier.VERY_GOOD
            elif overall >= 3.5:
                tier = QualityTier.GOOD
            elif overall >= 3.0:
                tier = QualityTier.ACCEPTABLE
            else:
                tier = QualityTier.POOR
            
            return QualityScore(
                visual_quality=visual_q,
                feature_completeness=feature_q,
                technical_quality=technical_q,
                aesthetic_appeal=aesthetic_q,
                overall=overall,
                tier=tier,
                notes=notes
            )

def generate_and_assess_variations(base_registry_path: str, variations_per_effect: int = 150, top_n: int = 10):
    """Generate variations and assess quality."""
    generator = FXVariationGenerator(base_registry_path)
    assessor = FXQualityAssessor()
    
    with open(base_registry_path, 'r') as f:
        base_registry = json.load(f)
    
    results = {}
    best_selections = {}
    top_selections = {}  # Multiple top selections per effect
    
    # Multithreaded generation across effects
    max_workers = min(32, cpu_count(), len(base_registry['effects']))
    print(f"Using {max_workers} worker threads for parallel effect generation")
    
    # Thread-safe collections
    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    
    def process_effect(base_effect: Dict) -> Tuple[str, List, Dict, List]:
        """Process a single effect (thread-safe)."""
        effect_id = base_effect['id']
        
        # Each thread gets its own generator/assessor instances
        thread_generator = FXVariationGenerator(base_registry_path)
        thread_assessor = FXQualityAssessor()
        
        try:
            # Generate variations (this is already fast, but we can parallelize assessment)
            variations = thread_generator.generate_effect_variations(effect_id, variations_per_effect)
            
            # Assess variations in parallel (multithreaded)
            # Each assessment gets its own assessor instance for thread safety
            def assess_single_variation(variation: Dict) -> Tuple[Dict, Any]:
                """Assess a single variation (thread-safe)."""
                # Create assessor instance per thread for thread safety
                local_assessor = FXQualityAssessor()
                score = local_assessor.assess_effect(variation)
                return (variation, score)
            
            # Use ThreadPoolExecutor for parallel assessment
            assessment_workers = min(32, cpu_count(), len(variations))
            assessed = []
            if len(variations) > 0:
                with ThreadPoolExecutor(max_workers=assessment_workers) as assess_executor:
                    assess_futures = {assess_executor.submit(assess_single_variation, var): var for var in variations}
                    for assess_future in as_completed(assess_futures):
                        try:
                            assessed.append(assess_future.result())
                        except Exception as e:
                            var = assess_futures[assess_future]
                            with progress_lock:
                                print(f"    ✗ Assessment error for {var.get('id', 'unknown')}: {e}")
            else:
                # Fallback if no variations
                assessed = []
            
            # Sort by overall score
            if len(assessed) > 0:
                assessed.sort(key=lambda x: x[1].overall, reverse=True)
                
                # Select best
                best_variation, best_score = assessed[0]
                best_selection = {effect_id: best_variation}
                
                # Select top N for placeholders
                top_n_variations = []
                for i in range(min(top_n, len(assessed))):
                    variation, score = assessed[i]
                    top_n_variations.append((variation, score))
                top_selection = {effect_id: top_n_variations}
            else:
                # No variations generated
                best_selection = {}
                top_selection = {}
            
            with progress_lock:
                if QUALITY_20_AVAILABLE and hasattr(best_score, 'to_quality_score_20'):
                    quality_20 = best_score.to_quality_score_20()
                    from space_whale_quality_system import format_quality_score
                    print(f"  [OK] {effect_id}: Best score {format_quality_score(quality_20.overall)}")
                else:
                    tier_name = best_score.tier.name if hasattr(best_score.tier, 'name') else "UNKNOWN"
                    print(f"  [OK] {effect_id}: Best score {best_score.overall:.2f} ({tier_name})")
            
            return effect_id, assessed, best_selection, top_selection
        except Exception as e:
            with progress_lock:
                print(f"  [ERROR] Error processing {effect_id}: {e}")
            return effect_id, [], {}, {}
    
    # Process effects in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_effect, effect): effect for effect in base_registry['effects']}
        
        for future in as_completed(futures):
            try:
                effect_id, assessed, best_sel, top_sel = future.result()
                with results_lock:
                    results[effect_id] = assessed
                    best_selections.update(best_sel)
                    top_selections.update(top_sel)
            except Exception as e:
                effect = futures[future]
                print(f"  ✗ Failed to process {effect.get('id', 'unknown')}: {e}")
    
    # Print summary
    for base_effect in base_registry['effects']:
        effect_id = base_effect['id']
        if effect_id in results and results[effect_id]:
            assessed = results[effect_id]
            best_variation, best_score = assessed[0]
            if QUALITY_20_AVAILABLE and hasattr(best_score, 'to_quality_score_20'):
                quality_20 = best_score.to_quality_score_20()
                from space_whale_quality_system import format_quality_score
                print(f"\n{effect_id}: Best score {format_quality_score(quality_20.overall)}")
            else:
                tier_name = best_score.tier.name if hasattr(best_score.tier, 'name') else "UNKNOWN"
                print(f"\n{effect_id}: Best score {best_score.overall:.2f} ({tier_name})")
            if top_n > 1:
                print(f"  Top {top_n} variations selected for placeholders")
    
    return results, best_selections, top_selections

def create_best_registry(best_selections: Dict, output_path: str):
    """Create registry with best selections."""
    # Restore original IDs (remove _v## suffix)
    best_registry = {
        "version": "1.0.0",
        "effects": []
    }
    
    for original_id, best_effect in best_selections.items():
        # Restore original ID
        best_effect['id'] = original_id
        best_registry['effects'].append(best_effect)
    
    with open(output_path, 'w') as f:
        json.dump(best_registry, f, indent=2)
    
    print(f"\nBest selections saved to: {output_path}")

def create_placeholder_registry(top_selections: Dict, output_path: str, top_n: int = 5):
    """Create registry with multiple quality placeholders per effect."""
    placeholder_registry = {
        "version": "1.0.0",
        "metadata": {
            "description": "Quality placeholders for Space Whale FX effects. Multiple variations per effect for manual selection/editing.",
            "top_n_per_effect": top_n,
            "usage": "Select the variation that best fits your needs, or use as a starting point for manual editing."
        },
        "effects": []
    }
    
    for original_id, top_variations in top_selections.items():
        # Create effect group with multiple placeholder variations
        effect_group = {
            "baseId": original_id,
            "variations": []
        }
        
        for i, (variation, score) in enumerate(top_variations):
            # Keep variation ID but add quality metadata (20-level system)
            placeholder = json.loads(json.dumps(variation))  # Deep copy
            
            # Convert to 20-level system if available
            if QUALITY_20_AVAILABLE and hasattr(score, 'to_quality_score_20'):
                quality_20 = score.to_quality_score_20()
                placeholder['quality'] = quality_20.to_dict()
                placeholder['quality']['rank'] = i + 1
            else:
                # Fallback to legacy format
                placeholder['quality'] = {
                    "rank": i + 1,
                    "overallScore": round(score.overall, 2),
                    "tier": score.tier.name if hasattr(score.tier, 'name') else "UNKNOWN",
                    "visualQuality": round(score.visual_quality, 2),
                    "featureCompleteness": round(score.feature_completeness, 2),
                    "technicalQuality": round(score.technical_quality, 2),
                    "aestheticAppeal": round(score.aesthetic_appeal, 2),
                    "notes": score.notes[:3] if score.notes else []
                }
            effect_group['variations'].append(placeholder)
        
        placeholder_registry['effects'].append(effect_group)
    
    with open(output_path, 'w') as f:
        json.dump(placeholder_registry, f, indent=2)
    
    print(f"\nPlaceholder registry saved to: {output_path}")
    print(f"  Contains {len(top_selections)} effect groups with {top_n} variations each")

def create_assessment_report(results: Dict, output_path: str):
    """Create detailed assessment report."""
    report = ["# Space Whale FX Quality Assessment Report\n"]
    report.append(f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for effect_id, assessed in results.items():
        report.append(f"## {effect_id}\n")
        report.append(f"### Variations Assessed: {len(assessed)}\n\n")
        
        for i, (variation, score) in enumerate(assessed, 1):
            report.append(f"#### Variation {i}: {variation['id']}\n")
            
            # Use 20-level system if available
            if QUALITY_20_AVAILABLE and hasattr(score, 'to_quality_score_20'):
                quality_20 = score.to_quality_score_20()
                from space_whale_quality_system import format_quality_score, get_quality_description
                report.append(f"- **Overall Score**: {format_quality_score(quality_20.overall)}\n")
                report.append(f"- **Description**: {get_quality_description(quality_20.overall)}\n")
                report.append(f"- **Visual Quality**: {quality_20.visual_quality}/20\n")
                report.append(f"- **Feature Completeness**: {quality_20.feature_completeness}/20\n")
                report.append(f"- **Technical Quality**: {quality_20.technical_quality}/20\n")
                report.append(f"- **Aesthetic Appeal**: {quality_20.aesthetic_appeal}/20\n")
            else:
                # Fallback to legacy format
                tier_name = score.tier.name if hasattr(score.tier, 'name') else "UNKNOWN"
                report.append(f"- **Overall Score**: {score.overall:.2f}/5.0 ({tier_name})\n")
                report.append(f"- **Visual Quality**: {score.visual_quality:.2f}/5.0\n")
                report.append(f"- **Feature Completeness**: {score.feature_completeness:.2f}/5.0\n")
                report.append(f"- **Technical Quality**: {score.technical_quality:.2f}/5.0\n")
                report.append(f"- **Aesthetic Appeal**: {score.aesthetic_appeal:.2f}/5.0\n")
            
            if score.notes:
                report.append("\n**Notes**:\n")
                for note in score.notes:
                    report.append(f"- {note}\n")
            
            report.append("\n")
        
        # Highlight best
        best_variation, best_score = assessed[0]
        report.append(f"### [SELECTED] {best_variation['id']}\n")
        if QUALITY_20_AVAILABLE and hasattr(best_score, 'to_quality_score_20'):
            quality_20 = best_score.to_quality_score_20()
            from space_whale_quality_system import format_quality_score
            report.append(f"**Reason**: Highest overall score ({format_quality_score(quality_20.overall)})\n\n")
        else:
            report.append(f"**Reason**: Highest overall score ({best_score.overall:.2f}/5.0)\n\n")
        report.append("---\n\n")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(report))
    
    print(f"Assessment report saved to: {output_path}")

if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Space Whale FX Variation Generator")
    parser.add_argument("registry", nargs="?", default="space_whale_fx_registry.json",
                       help="Base FX registry JSON file")
    parser.add_argument("variations", nargs="?", type=int, default=150,
                       help="Number of variations per effect (default: 150)")
    parser.add_argument("top_n", nargs="?", type=int, default=10,
                       help="Top N variations to keep per effect (default: 10)")
    parser.add_argument("--output-dir", type=str, default=".",
                       help="Output directory for generated files (default: current directory)")
    
    # Parse arguments (support both old positional and new argparse format)
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        args = parser.parse_args()
        base_registry = args.registry
        variations_per_effect = args.variations
        top_n = args.top_n
        output_dir = Path(args.output_dir)
    else:
        # Legacy positional arguments
        base_registry = sys.argv[1] if len(sys.argv) > 1 else "space_whale_fx_registry.json"
        variations_per_effect = int(sys.argv[2]) if len(sys.argv) > 2 else 150
        top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        # Check for --output-dir in legacy format
        output_dir = Path(".")
        if "--output-dir" in sys.argv:
            idx = sys.argv.index("--output-dir")
            if idx + 1 < len(sys.argv):
                output_dir = Path(sys.argv[idx + 1])
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {variations_per_effect} variations per effect...")
    print(f"Selecting top {top_n} variations per effect for placeholders...")
    print(f"Output directory: {output_dir}")
    results, best_selections, top_selections = generate_and_assess_variations(
        base_registry, variations_per_effect, top_n
    )
    
    # Save best selections (single best)
    best_path = output_dir / "space_whale_fx_registry_best.json"
    create_best_registry(best_selections, str(best_path))
    
    # Save placeholder registry (multiple top selections)
    if top_n > 1:
        placeholder_path = output_dir / "space_whale_fx_registry_placeholders.json"
        create_placeholder_registry(top_selections, str(placeholder_path), top_n)
    
    # Save assessment report
    report_path = output_dir / "SPACE_WHALE_FX_QUALITY_ASSESSMENT.md"
    create_assessment_report(results, str(report_path))
    
    print(f"\n[COMPLETE] Best variations and placeholders saved to: {output_dir}")

