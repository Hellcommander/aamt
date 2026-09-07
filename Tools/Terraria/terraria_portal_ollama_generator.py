#!/usr/bin/env python3
"""
Terraria Portal Ollama Spritesheet Generator
Uses Ollama to generate animated portal spritesheets for tModLoader
Follows Transcendence pattern for AI-powered asset generation
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter
import math
import random

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Try to import requests for Ollama API
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests module not found. Install with: pip install requests")
    print("Will use fallback generation only.")

# Import model router if available
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import get_visual_model, TASK_VISUAL
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_VISUAL = "visual"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_VISUAL = "visual"

class TerrariaPortalGenerator:
    """Generates Terraria portal spritesheets using Ollama for design guidance."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = None):
        self.ollama_url = ollama_url
        if model is None:
            if MODEL_ROUTER_AVAILABLE:
                model = get_visual_model()
            else:
                model = self.detect_best_model()
        self.model = model
        self.api_url = f"{ollama_url}/api/generate"
    
    def detect_best_model(self) -> str:
        """Detect best available Ollama model for visual tasks."""
        if not REQUESTS_AVAILABLE:
            return "llama3.2:latest"
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    # Prefer visual/artistic models
                    visual_models = [m for m in models if any(x in m.get('name', '').lower() 
                        for x in ['llama3.2', 'llama3', 'mistral', 'wizardlm'])]
                    if visual_models:
                        return visual_models[0].get('name', 'llama3.2:latest')
                    return models[0].get('name', 'llama3.2:latest')
        except Exception as e:
            print(f"Warning: Could not detect Ollama models: {e}")
        
        return "llama3.2:latest"
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate_portal_design(self, portal_name: str, description: str, preset: str = "Void", require_ollama: bool = True) -> Dict:
        """Use Ollama to generate portal design specifications."""
        if not REQUESTS_AVAILABLE:
            if require_ollama:
                raise RuntimeError("Ollama requests module not available. Install with: pip install requests")
            print("Warning: requests module not available, using fallback design")
            return self.generate_fallback_design(portal_name, preset)
        
        if not self.check_ollama_available():
            if require_ollama:
                raise RuntimeError(f"Ollama is not available at {self.ollama_url}. Start Ollama with: ollama serve")
            print("Warning: Ollama not available, using fallback design")
            return self.generate_fallback_design(portal_name, preset)
        
        prompt = f"""You are a pixel art designer for Terraria mods. Design a unique portal sprite.

Portal Name: {portal_name}
Description: {description}
Theme: {preset}

Create a detailed, unique design specification in JSON format. Be creative and specific - avoid generic designs.

Required JSON structure:
{{
  "colorScheme": {{
    "core": "#hexcolor (main portal color, be specific)",
    "rim": "#hexcolor (outer edge color)",
    "accent": "#hexcolor (highlight/particle color)"
  }},
  "animationStyle": "detailed description (e.g., 'spiral inward with energy trails', 'pulsing with outward particle bursts', 'swirling vortex with distortion waves')",
  "visualFeatures": ["specific feature 1", "specific feature 2", "specific feature 3"],
  "frameCount": 8,
  "glowIntensity": 0.0-1.0,
  "particleCount": 8-16,
  "complexity": "low/medium/high",
  "uniqueElements": ["element 1", "element 2"]
}}

Make the design unique to {portal_name} based on: {description}
Use colors that match the {preset} theme but be creative.
Return ONLY valid JSON, no markdown, no explanation, no code blocks."""

        try:
            print(f"  Calling Ollama API with model: {self.model}")
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,  # Higher temperature for more creativity
                        "top_p": 0.95,
                        "top_k": 40
                    }
                },
                timeout=60  # Increased timeout for better models
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    design = json.loads(json_str)
                    
                    # Validate design has required fields
                    required_fields = ['colorScheme', 'animationStyle']
                    if all(field in design for field in required_fields):
                        checkmark = "[OK]" if sys.platform == 'win32' else "✓"
                        print(f"  {checkmark} Ollama generated unique design")
                        print(f"    Colors: {design.get('colorScheme', {})}")
                        print(f"    Animation: {design.get('animationStyle', 'unknown')}")
                        return design
                    else:
                        print(f"  Warning: Ollama response missing required fields, using fallback")
                else:
                    print(f"  Warning: Could not extract JSON from Ollama response")
            else:
                print(f"  Warning: Ollama API returned status {response.status_code}")
        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse Ollama JSON response: {e}")
        except Exception as e:
            print(f"  Warning: Ollama generation failed: {e}")
        
        if require_ollama:
            raise RuntimeError("Failed to generate design with Ollama. Check Ollama is running and model is available.")
        
        print("  Using fallback design...")
        return self.generate_fallback_design(portal_name, preset)
    
    def generate_fallback_design(self, portal_name: str, preset: str) -> Dict:
        """Generate fallback design based on preset."""
        presets = {
            "Void": {
                "colorScheme": {"core": "#b3f0ff", "rim": "#3b7fff", "accent": "#ff66ff"},
                "animationStyle": "swirling inward",
                "visualFeatures": ["energy particles", "distortion waves"],
                "frameCount": 8,
                "glowIntensity": 0.8
            },
            "Shadow": {
                "colorScheme": {"core": "#6600ff", "rim": "#330066", "accent": "#ff00ff"},
                "animationStyle": "spiral inward",
                "visualFeatures": ["dark particles", "purple glow"],
                "frameCount": 8,
                "glowIntensity": 0.7
            },
            "Fire": {
                "colorScheme": {"core": "#ff6600", "rim": "#ff3300", "accent": "#ffff00"},
                "animationStyle": "outward flow",
                "visualFeatures": ["flame particles", "heat distortion"],
                "frameCount": 8,
                "glowIntensity": 0.9
            }
        }
        
        return presets.get(preset, presets["Void"])
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def generate_portal_frame(self, frame_index: int, total_frames: int, design: Dict, 
                             tile_size: int = 16) -> Image.Image:
        """Generate a single animation frame using the Ollama-generated design."""
        img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = tile_size // 2, tile_size // 2
        max_radius = tile_size // 2 - 1
        
        # Get colors from Ollama design
        color_scheme = design.get('colorScheme', {})
        core_color = self.hex_to_rgb(color_scheme.get('core', '#ffffff'))
        rim_color = self.hex_to_rgb(color_scheme.get('rim', '#000000'))
        accent_color = self.hex_to_rgb(color_scheme.get('accent', '#ff00ff'))
        
        # Animation progress (0.0 to 1.0)
        progress = frame_index / total_frames
        
        # Get particle count from design if specified
        particle_count = design.get('particleCount', 8)
        glow_intensity = design.get('glowIntensity', 0.8)
        
        # Generate portal based on animation style from Ollama
        style = design.get('animationStyle', 'swirling').lower()
        
        if 'spiral' in style or 'swirl' in style:
            # Spiral animation
            angle = progress * math.pi * 4  # 2 full rotations
            for i in range(3):
                radius = max_radius * (0.3 + i * 0.2)
                x = center_x + radius * math.cos(angle + i * math.pi / 3)
                y = center_y + radius * math.sin(angle + i * math.pi / 3)
                size = 2 + i
                alpha = int(200 * (1 - abs(progress - 0.5) * 2))
                color = (*core_color, alpha)
                draw.ellipse([x-size, y-size, x+size, y+size], fill=color)
            
            # Outer rim
            rim_alpha = int(150 + 50 * math.sin(progress * math.pi * 2))
            for r in range(max_radius - 2, max_radius):
                alpha = int(rim_alpha * (1 - (r - (max_radius - 2)) / 2))
                color = (*rim_color, alpha)
                draw.ellipse([center_x-r, center_y-r, center_x+r, center_y+r], 
                           outline=color, width=1)
        
        elif 'flow' in style or 'outward' in style:
            # Outward flow animation
            wave = math.sin(progress * math.pi * 2)
            for r in range(2, max_radius):
                alpha = int(100 + 100 * wave * (1 - r / max_radius))
                color = (*core_color, alpha)
                draw.ellipse([center_x-r, center_y-r, center_x+r, center_y+r], 
                           outline=color, width=1)
            
            # Particles flowing outward (use count from design)
            for i in range(particle_count):
                angle = (i / particle_count) * math.pi * 2 + progress * math.pi
                distance = 3 + (max_radius - 3) * (progress + i * 0.1) % 1.0
                x = center_x + distance * math.cos(angle)
                y = center_y + distance * math.sin(angle)
                particle_alpha = int(255 * (1 - distance / max_radius))
                color = (*accent_color, particle_alpha)
                draw.ellipse([x-1, y-1, x+1, y+1], fill=color)
        
        else:
            # Default pulsing animation
            pulse = 0.5 + 0.5 * math.sin(progress * math.pi * 2)
            radius = int(max_radius * (0.3 + 0.4 * pulse))
            alpha = int(200 * pulse)
            
            # Core
            color = (*core_color, alpha)
            draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], 
                        fill=color)
            
            # Rim
            rim_alpha = int(150 * pulse)
            rim_color_rgba = (*rim_color, rim_alpha)
            draw.ellipse([center_x-max_radius+1, center_y-max_radius+1, 
                         center_x+max_radius-1, center_y+max_radius-1], 
                        outline=rim_color_rgba, width=2)
        
        return img
    
    def generate_single_spritesheet(self, portal_name: str, description: str, preset: str = "Void",
                                    tile_size: int = 16, frame_count: int = 8, 
                                    design: Dict = None, candidate_id: int = 0) -> Image.Image:
        """Generate a single spritesheet candidate."""
        # Generate design if not provided
        if design is None:
            design = self.generate_portal_design(portal_name, description, preset, require_ollama=True)
        
        # Override frame count if specified
        if frame_count:
            design['frameCount'] = frame_count
        
        actual_frame_count = design.get('frameCount', 8)
        
        # Generate frames
        frames = []
        for i in range(actual_frame_count):
            frame = self.generate_portal_frame(i, actual_frame_count, design, tile_size)
            frames.append(frame)
        
        # Assemble spritesheet (horizontal strip)
        spritesheet_width = tile_size * actual_frame_count
        spritesheet_height = tile_size
        spritesheet = Image.new('RGBA', (spritesheet_width, spritesheet_height), (0, 0, 0, 0))
        
        for i, frame in enumerate(frames):
            x_offset = i * tile_size
            spritesheet.paste(frame, (x_offset, 0))
        
        return spritesheet
    
    def assess_spritesheet_quality(self, spritesheet: Image.Image, tile_size: int = 16) -> Dict:
        """Assess quality of a generated spritesheet."""
        width, height = spritesheet.size
        score = 10.0
        notes = []
        
        # Check dimensions (should be frame_count * tile_size x tile_size)
        expected_width = (width // tile_size) * tile_size
        if width != expected_width:
            score -= 1.0
            notes.append(f"Width {width} not multiple of {tile_size}")
        
        if height != tile_size:
            score -= 1.0
            notes.append(f"Height {height} should be {tile_size}")
        
        # Check for alpha channel
        if spritesheet.mode != 'RGBA':
            score -= 2.0
            notes.append("Missing alpha channel")
        
        # Check for non-empty content (not all transparent)
        pixels = list(spritesheet.getdata())
        non_transparent = sum(1 for p in pixels if len(p) > 3 and p[3] > 0)
        if non_transparent == 0:
            score -= 5.0
            notes.append("Completely transparent (blank)")
        elif non_transparent < len(pixels) * 0.1:
            score -= 1.0
            notes.append("Very sparse content")
        
        # Check color diversity (should have some variation)
        unique_colors = len(set(pixels[:1000]))  # Sample first 1000 pixels
        if unique_colors < 3:
            score -= 1.0
            notes.append("Low color diversity")
        
        # Check animation frames are different (not all identical)
        frame_count = width // tile_size
        if frame_count > 1:
            first_frame = spritesheet.crop((0, 0, tile_size, tile_size))
            frames_different = False
            for i in range(1, frame_count):
                frame = spritesheet.crop((i * tile_size, 0, (i + 1) * tile_size, tile_size))
                if first_frame.tobytes() != frame.tobytes():
                    frames_different = True
                    break
            if not frames_different:
                score -= 2.0
                notes.append("All frames identical (no animation)")
        
        return {
            'score': round(score, 2),
            'notes': notes,
            'width': width,
            'height': height,
            'frame_count': frame_count
        }
    
    def generate_spritesheet(self, portal_name: str, description: str, preset: str = "Void",
                            tile_size: int = 16, frame_count: int = 8, 
                            output_path: Path = None, require_ollama: bool = True,
                            candidates: int = 5, min_quality: float = 8.0) -> Path:
        """Generate complete animated spritesheet with quality-based selection."""
        print(f"Generating portal spritesheet: {portal_name}")
        print(f"  Preset: {preset}")
        print(f"  Tile size: {tile_size}x{tile_size}")
        print(f"  Frames: {frame_count}")
        print(f"  Require Ollama: {require_ollama}")
        print(f"  Generating {candidates} candidates, keeping best (score >= {min_quality})")
        
        # Generate multiple candidates
        candidates_list = []
        print(f"\n  Generating {candidates} candidate designs...")
        
        for i in range(candidates):
            print(f"    Candidate {i+1}/{candidates}...", end=" ", flush=True)
            try:
                # Generate unique design for each candidate
                design = self.generate_portal_design(
                    portal_name, 
                    f"{description} (variation {i+1})", 
                    preset, 
                    require_ollama=require_ollama
                )
                
                # Generate spritesheet
                spritesheet = self.generate_single_spritesheet(
                    portal_name, description, preset, tile_size, frame_count, design, i
                )
                
                # Assess quality
                quality = self.assess_spritesheet_quality(spritesheet, tile_size)
                
                candidates_list.append({
                    'design': design,
                    'spritesheet': spritesheet,
                    'quality': quality,
                    'candidate_id': i
                })
                
                # Use ASCII-safe checkmark for Windows
                checkmark = "[OK]" if sys.platform == 'win32' else "✓"
                print(f"{checkmark} Score: {quality['score']:.2f}")
                
            except Exception as e:
                # Use ASCII-safe X for Windows
                x_mark = "[FAIL]" if sys.platform == 'win32' else "✗"
                try:
                    print(f"{x_mark} Failed: {e}")
                except UnicodeEncodeError:
                    print(f"[FAIL] Failed: {e}")
                continue
        
        if not candidates_list:
            raise RuntimeError("Failed to generate any candidates")
        
        # Sort by quality score (highest first)
        candidates_list.sort(key=lambda x: x['quality']['score'], reverse=True)
        
        # Filter by minimum quality
        high_quality = [c for c in candidates_list if c['quality']['score'] >= min_quality]
        
        print(f"\n  Quality Results:")
        print(f"    Total candidates: {len(candidates_list)}")
        print(f"    High quality (>= {min_quality}): {len(high_quality)}")
        print(f"    Low quality (< {min_quality}): {len(candidates_list) - len(high_quality)}")
        
        if high_quality:
            # Use best candidate
            best = high_quality[0]
            print(f"\n  Selected best candidate (score: {best['quality']['score']:.2f})")
            if best['quality']['notes']:
                print(f"    Notes: {', '.join(best['quality']['notes'])}")
            
            selected_spritesheet = best['spritesheet']
        else:
            # Use best available even if below threshold
            best = candidates_list[0]
            print(f"\n  WARNING: No candidates met quality threshold ({min_quality})")
            print(f"  Using best available (score: {best['quality']['score']:.2f})")
            if best['quality']['notes']:
                print(f"    Notes: {', '.join(best['quality']['notes'])}")
            selected_spritesheet = best['spritesheet']
        
        # Save spritesheet
        if output_path is None:
            output_path = Path(f"{portal_name}_spritesheet.png")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Save with XNA/MonoGame compatible settings
        selected_spritesheet.save(output_path, 'PNG', optimize=False, compress_level=1)
        
        print(f"\n  Spritesheet saved: {output_path}")
        print(f"  Dimensions: {selected_spritesheet.size[0]}x{selected_spritesheet.size[1]}")
        print(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
        print(f"  Final quality score: {best['quality']['score']:.2f}")
        
        # Save quality report
        report_path = output_path.parent / f"{portal_name}_quality_report.json"
        report_data = {
            'portal_name': portal_name,
            'selected_candidate': best['candidate_id'],
            'selected_score': best['quality']['score'],
            'min_quality_threshold': min_quality,
            'candidates': [
                {
                    'id': c['candidate_id'],
                    'score': c['quality']['score'],
                    'notes': c['quality']['notes']
                }
                for c in candidates_list
            ]
        }
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        print(f"  Quality report saved: {report_path}")
        
        return output_path

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Terraria portal spritesheets using Ollama')
    parser.add_argument('--portal-name', required=True, help='Portal name')
    parser.add_argument('--description', required=True, help='Portal description')
    parser.add_argument('--preset', default='Void', 
                       choices=['Void', 'Shadow', 'Fire', 'Ice', 'Electric', 'Nature', 'Light'],
                       help='Portal preset')
    parser.add_argument('--tile-size', type=int, default=16, choices=[16, 32],
                       help='Tile size in pixels')
    parser.add_argument('--frame-count', type=int, default=8,
                       help='Number of animation frames')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--ollama-url', default='http://localhost:11434',
                       help='Ollama API URL')
    parser.add_argument('--model', help='Ollama model to use')
    parser.add_argument('--require-ollama', action='store_true', default=True,
                       help='Require Ollama to be available (fail if not)')
    parser.add_argument('--allow-fallback', action='store_true',
                       help='Allow fallback design if Ollama fails (overrides --require-ollama)')
    parser.add_argument('--candidates', type=int, default=5,
                       help='Number of candidate spritesheets to generate (default: 5)')
    parser.add_argument('--min-quality', type=float, default=8.0,
                       help='Minimum quality score to accept (default: 8.0)')
    
    args = parser.parse_args()
    
    # Determine if Ollama is required
    require_ollama = args.require_ollama and not args.allow_fallback
    
    generator = TerrariaPortalGenerator(ollama_url=args.ollama_url, model=args.model)
    
    output_path = Path(args.output) if args.output else None
    if output_path is None:
        output_path = Path(f"{args.portal_name}_spritesheet.png")
    
    generator.generate_spritesheet(
        portal_name=args.portal_name,
        description=args.description,
        preset=args.preset,
        tile_size=args.tile_size,
        frame_count=args.frame_count,
        output_path=output_path,
        require_ollama=require_ollama,
        candidates=args.candidates,
        min_quality=args.min_quality
    )

if __name__ == "__main__":
    main()

