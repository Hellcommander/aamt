#!/usr/bin/env python3
"""
Qud Asset Generator with Ollama Integration
Uses Ollama to generate high-quality design specifications for Caves of Qud mod assets.
Generates multiple candidates and selects the best quality ones.
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

# Fix Windows console encoding
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

# Import shared Ollama integration
_ollama_path = os.path.join(os.path.dirname(__file__), "..", "Shared", "ollama_integration.py")
OLLAMA_INTEGRATION_AVAILABLE = False
call_ollama = None
test_ollama_connection = None
TASK_VISUAL = "visual"

if os.path.exists(_ollama_path):
    try:
        shared_dir = os.path.join(os.path.dirname(__file__), "..", "Shared")
        if shared_dir not in sys.path:
            sys.path.insert(0, shared_dir)
        from ollama_integration import call_ollama, test_ollama_connection
        OLLAMA_INTEGRATION_AVAILABLE = True
    except ImportError as e:
        OLLAMA_INTEGRATION_AVAILABLE = False
else:
    OLLAMA_INTEGRATION_AVAILABLE = False

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


class QudOllamaAssetGenerator:
    """Generates Qud mod assets using Ollama for design guidance."""
    
    # Qud color palette
    COLORS = {
        'K': (0, 0, 0),        # Black
        'k': (64, 64, 64),    # Dark gray
        'R': (255, 0, 0),     # Red
        'r': (128, 0, 0),     # Dark red
        'G': (0, 255, 0),     # Green
        'g': (0, 128, 0),     # Dark green
        'Y': (255, 255, 0),   # Yellow
        'y': (128, 128, 0),   # Dark yellow
        'B': (0, 0, 255),     # Blue
        'b': (0, 0, 128),     # Dark blue
        'M': (255, 0, 255),   # Magenta
        'm': (128, 0, 128),   # Dark magenta
        'C': (0, 255, 255),   # Cyan
        'c': (0, 128, 128),   # Dark cyan
        'W': (255, 255, 255), # White
        'w': (192, 192, 192), # Light gray
        'O': (255, 128, 0),   # Orange
        'o': (128, 64, 0),    # Dark orange
    }
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = None):
        self.ollama_url = ollama_url
        if model is None:
            # Prioritize wizardlm-uncensored for image/visual tasks (better for creative, uncensored content)
            # This model is optimal for visual/creative tasks and can generate scarier/more grotesque images
            preferred_visual_model = "wizardlm-uncensored:latest"
            
            # Always check for preferred model first, regardless of model router
            if OLLAMA_INTEGRATION_AVAILABLE or REQUESTS_AVAILABLE:
                available_models = self._get_available_models()
                
                # First priority: Check if wizardlm-uncensored is available
                if preferred_visual_model in available_models:
                    model = preferred_visual_model
                    print(f"  Using {model} for image generation (optimal for visual/creative/scary content)")
                # Second priority: Look for any wizardlm variant
                elif available_models:
                    wizardlm_models = [m for m in available_models if 'wizardlm' in m.lower() and 'uncensored' in m.lower()]
                    if not wizardlm_models:
                        wizardlm_models = [m for m in available_models if 'wizardlm' in m.lower()]
                    if wizardlm_models:
                        model = wizardlm_models[0]
                        print(f"  Using {model} (wizardlm variant found)")
                    # Third priority: Use model router if available
                    elif MODEL_ROUTER_AVAILABLE:
                        model = get_visual_model()
                        print(f"  Using {model} from model router")
                    else:
                        model = available_models[0]
                        print(f"  Using {model} (first available)")
                # Fallback: Use model router if no models list available
                elif MODEL_ROUTER_AVAILABLE:
                    model = get_visual_model()
                    print(f"  Using {model} from model router")
                else:
                    model = preferred_visual_model
                    print(f"  Using {model} (default, may need to pull model)")
            else:
                model = preferred_visual_model
        self.model = model
        self.api_url = f"{ollama_url}/api"
        
        # Test Ollama connection
        if OLLAMA_INTEGRATION_AVAILABLE:
            self.ollama_available = test_ollama_connection()
        else:
            self.ollama_available = self._check_ollama_simple()
    
    def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if not REQUESTS_AVAILABLE:
            return []
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return []
    
    def _check_ollama_simple(self) -> bool:
        """Simple Ollama availability check."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate_creature_design(self, creature_name: str, description: str, 
                                 base_type: str = "insect", tier: int = 1,
                                 color_code: str = "&m") -> Dict:
        """Use Ollama to generate creature design specifications."""
        if not self.ollama_available or not OLLAMA_INTEGRATION_AVAILABLE:
            return self._generate_fallback_creature_design(creature_name, base_type, tier, color_code)
        
        prompt = f"""You are a pixel art designer for Caves of Qud, a roguelike game with a distinctive art style.

Create a detailed design specification for a HIGH QUALITY creature sprite.

Creature Name: {creature_name}
Description: {description}
Base Type: {base_type}
Tier: {tier} (affects size and detail level)
Color Code: {color_code} (Qud color scheme)
Tile Size: 48x48 pixels (high resolution, supports tile scaling mod)

Caves of Qud Style Guidelines:
- Pixel art aesthetic optimized for 48x48 tiles (high detail)
- Organic, slightly grotesque creatures
- High contrast for visibility
- Distinctive silhouettes
- Insect/arthropod themes common
- Magenta/purple tones for broodlings
- Cyan tones for flying creatures
- More detail possible at higher resolution (segments, texture, appendages)

HIGH QUALITY REQUIREMENTS:
- Include fine details like chitin segments, texture patterns, appendage details
- Specify multiple layers of detail (base, highlights, shadows, texture)
- Add distinctive features visible at 48x48 resolution
- Consider depth and dimensionality

Create a detailed, unique design specification in JSON format.

Required JSON structure:
{{
  "shape": {{
    "bodyType": "description (e.g., 'segmented oval with prominent head', 'rounded carapace with spiky edges')",
    "proportions": {{
      "headSize": 0.0-1.0,
      "bodySize": 0.0-1.0,
      "appendageSize": 0.0-1.0
    }},
    "appendages": ["specific appendage 1", "specific appendage 2"],
    "distinctiveFeatures": ["feature 1", "feature 2"]
  }},
  "colorScheme": {{
    "primary": "#hexcolor (main body color, match {color_code})",
    "secondary": "#hexcolor (accent/highlight color)",
    "detail": "#hexcolor (small details, eyes, etc.)",
    "outline": "#hexcolor (outline color, usually dark)"
  }},
  "texture": {{
    "style": "description (e.g., 'smooth chitin', 'rough segmented', 'glossy carapace')",
    "detailLevel": "low/medium/high",
    "patterns": ["pattern description 1", "pattern description 2"]
  }},
  "pose": "description (e.g., 'aggressive forward lean', 'alert stance', 'crouched ready')",
  "tierAdjustments": {{
    "sizeMultiplier": 1.0-2.0,
    "detailBonus": 0-3,
    "intimidationFactor": 0.0-1.0
  }}
}}

Make the design unique to {creature_name} based on: {description}
Use colors that match the {color_code} Qud color scheme but be creative.
Return ONLY valid JSON, no markdown, no explanation, no code blocks."""

        try:
            print(f"  Calling Ollama ({self.model}) for creature design (this may take 10-30 seconds)...")
            start_time = time.time()
            # Use wizardlm-uncensored directly for visual tasks (better for creative/scary images)
            response = call_ollama(
                prompt=prompt,
                task_type=TASK_VISUAL,
                response_length="standard",
                system_prompt="You are a pixel art designer specializing in roguelike game sprites. Always return valid JSON only.",
                model_name=self.model  # Force use of wizardlm-uncensored
            )
            elapsed = time.time() - start_time
            print(f"  Ollama response received in {elapsed:.1f} seconds")
            
            if not response:
                print(f"  Warning: Ollama returned None/empty response, using fallback")
                return self._generate_fallback_creature_design(creature_name, base_type, tier, color_code)
            
            if response:
                # Extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    design = json.loads(json_str)
                    
                    # Validate design
                    if 'shape' in design and 'colorScheme' in design:
                        print(f"  [OK] Ollama generated creature design")
                        return design
                    else:
                        print(f"  Warning: Ollama response missing required fields")
                else:
                    print(f"  Warning: Could not extract JSON from Ollama response")
            else:
                print(f"  Warning: Ollama returned no response")
        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse Ollama JSON: {e}")
        except Exception as e:
            print(f"  Warning: Ollama generation failed: {e}")
        
        # No fallback - return None to indicate failure
        print(f"  [ERROR] Ollama generation failed completely. No asset will be generated.")
        return None
    
    def _generate_fallback_creature_design(self, creature_name: str, base_type: str, 
                                          tier: int, color_code: str) -> Dict:
        """Generate fallback design without Ollama."""
        color = self._parse_color_code(color_code)
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        
        return {
            "shape": {
                "bodyType": f"{base_type}-like body",
                "proportions": {
                    "headSize": 0.3 + (tier * 0.05),
                    "bodySize": 0.5 + (tier * 0.1),
                    "appendageSize": 0.2 + (tier * 0.05)
                },
                "appendages": ["legs", "antennae"],
                "distinctiveFeatures": ["chitinous exoskeleton"]
            },
            "colorScheme": {
                "primary": hex_color,
                "secondary": self._lighten_color(hex_color),
                "detail": "#ffffff",
                "outline": "#000000"
            },
            "texture": {
                "style": "smooth chitin",
                "detailLevel": "medium",
                "patterns": []
            },
            "pose": "alert stance",
            "tierAdjustments": {
                "sizeMultiplier": 1.0 + (tier * 0.1),
                "detailBonus": tier,
                "intimidationFactor": tier * 0.1
            }
        }
    
    def generate_equipment_design(self, item_name: str, description: str,
                                   item_type: str = "sack", color_code: str = "&m") -> Dict:
        """Use Ollama to generate equipment design specifications."""
        if not self.ollama_available or not OLLAMA_INTEGRATION_AVAILABLE:
            return self._generate_fallback_equipment_design(item_name, item_type, color_code)
        
        prompt = f"""You are a pixel art designer for Caves of Qud.

Create a detailed design specification for a HIGH QUALITY equipment item sprite.

Item Name: {item_name}
Description: {description}
Item Type: {item_type}
Color Code: {color_code} (Qud color scheme)
Tile Size: 48x48 pixels (high resolution, supports tile scaling mod)

Caves of Qud Style Guidelines:
- Pixel art aesthetic optimized for 48x48 tiles (high detail)
- Organic, slightly grotesque items
- High contrast for visibility
- Distinctive shapes
- Magenta/purple tones common for organic items

HIGH QUALITY REQUIREMENTS:
- Include fine details like texture, surface patterns, depth cues
- Specify multiple layers (base, highlights, shadows, texture)
- Add distinctive features visible at 48x48 resolution
- Consider dimensionality and lighting

Create a detailed design specification in JSON format.

Required JSON structure:
{{
  "shape": {{
    "form": "description (e.g., 'bulging organic sack', 'crystalline structure', 'metallic device')",
    "size": "small/medium/large",
    "distinctiveFeatures": ["feature 1", "feature 2"]
  }},
  "colorScheme": {{
    "primary": "#hexcolor (main color, match {color_code})",
    "secondary": "#hexcolor (accent color)",
    "detail": "#hexcolor (small details)",
    "outline": "#hexcolor (outline)"
  }},
  "texture": {{
    "style": "description (e.g., 'pulsating organic', 'smooth chitin', 'rough metal')",
    "detailLevel": "low/medium/high",
    "patterns": ["pattern description"]
  }},
  "visualEffects": ["effect 1", "effect 2"],
  "uniqueness": "description of what makes this item visually distinct"
}}

Make the design unique to {item_name} based on: {description}
Return ONLY valid JSON, no markdown, no explanation, no code blocks."""

        try:
            print(f"  Calling Ollama ({self.model}) for equipment design...")
            response = call_ollama(
                prompt=prompt,
                task_type=TASK_VISUAL,
                response_length="standard",
                system_prompt="You are a pixel art designer specializing in roguelike game items. Always return valid JSON only.",
                model_name=self.model  # Force use of wizardlm-uncensored
            )
            
            if response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    design = json.loads(json_str)
                    
                    if 'shape' in design and 'colorScheme' in design:
                        print(f"  [OK] Ollama generated equipment design")
                        return design
        except Exception as e:
            print(f"  Warning: Ollama generation failed: {e}")
        
        # No fallback - return None to indicate failure
        print(f"  [ERROR] Ollama generation failed completely. No asset will be generated.")
        return None
    
    def _generate_fallback_equipment_design(self, item_name: str, item_type: str, color_code: str) -> Dict:
        """Generate fallback equipment design."""
        color = self._parse_color_code(color_code)
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        
        return {
            "shape": {
                "form": f"{item_type} shape",
                "size": "medium",
                "distinctiveFeatures": ["organic texture"]
            },
            "colorScheme": {
                "primary": hex_color,
                "secondary": self._lighten_color(hex_color),
                "detail": "#ffffff",
                "outline": "#000000"
            },
            "texture": {
                "style": "organic",
                "detailLevel": "medium",
                "patterns": []
            },
            "visualEffects": [],
            "uniqueness": "standard design"
        }
    
    def generate_biomod_design(self, biomod_name: str, display_name: str,
                               description: str, color_code: str = "&m") -> Dict:
        """Use Ollama to generate biomod icon design specifications."""
        if not self.ollama_available or not OLLAMA_INTEGRATION_AVAILABLE:
            return self._generate_fallback_biomod_design(biomod_name, color_code)
        
        prompt = f"""You are a pixel art designer for Caves of Qud.

Create a detailed design specification for a HIGH QUALITY icon representing a biomod upgrade.

Biomod Name: {biomod_name}
Display Name: {display_name}
Description: {description}
Color Code: {color_code} (Qud color scheme)
Icon Size: 48x48 pixels (high resolution, supports tile scaling mod)

Caves of Qud Style Guidelines:
- High quality icons optimized for 48x48 pixels
- High contrast for visibility
- Distinctive symbols
- Technical/biological aesthetic
- Color-coded by function

HIGH QUALITY REQUIREMENTS:
- Include fine details like patterns, gradients, depth
- Specify multiple layers (base, highlights, details)
- Add distinctive features visible at 48x48 resolution
- Consider technical/biological symbolism

Create a detailed design specification in JSON format.

Required JSON structure:
{{
  "symbol": {{
    "shape": "description (e.g., 'circular node with radiating lines', 'hexagonal pattern', 'spiral structure')",
    "complexity": "low/medium/high",
    "distinctiveElements": ["element 1", "element 2"]
  }},
  "colorScheme": {{
    "primary": "#hexcolor (main color, match {color_code})",
    "secondary": "#hexcolor (accent)",
    "detail": "#hexcolor (highlights)",
    "outline": "#hexcolor (outline)"
  }},
  "style": {{
    "aesthetic": "description (e.g., 'technical', 'organic', 'crystalline')",
    "detailLevel": "low/medium/high",
    "glow": true/false
  }},
  "uniqueness": "description of what makes this icon visually distinct"
}}

Make the design unique to {display_name} based on: {description}
Return ONLY valid JSON, no markdown, no explanation, no code blocks."""

        try:
            print(f"  Calling Ollama ({self.model}) for biomod design...")
            response = call_ollama(
                prompt=prompt,
                task_type=TASK_VISUAL,
                response_length="short",
                system_prompt="You are a pixel art designer specializing in game UI icons. Always return valid JSON only.",
                model_name=self.model  # Force use of wizardlm-uncensored
            )
            
            if response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    design = json.loads(json_str)
                    
                    if 'symbol' in design and 'colorScheme' in design:
                        print(f"  [OK] Ollama generated biomod design")
                        return design
        except Exception as e:
            print(f"  Warning: Ollama generation failed: {e}")
        
        # No fallback - return None to indicate failure
        print(f"  [ERROR] Ollama generation failed completely. No asset will be generated.")
        return None
    
    def _generate_fallback_biomod_design(self, biomod_name: str, color_code: str) -> Dict:
        """Generate fallback biomod design."""
        color = self._parse_color_code(color_code)
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        
        return {
            "symbol": {
                "shape": "circular node",
                "complexity": "medium",
                "distinctiveElements": ["radiating lines"]
            },
            "colorScheme": {
                "primary": hex_color,
                "secondary": self._lighten_color(hex_color),
                "detail": "#ffffff",
                "outline": "#000000"
            },
            "style": {
                "aesthetic": "technical",
                "detailLevel": "medium",
                "glow": False
            },
            "uniqueness": "standard design"
        }
    
    def _parse_color_code(self, color_code: str) -> Tuple[int, int, int]:
        """Parse Qud color code to RGB."""
        code = color_code.replace('&', '').replace('^', '').strip()
        if code and code[0] in self.COLORS:
            return self.COLORS[code[0]]
        return (128, 0, 128)  # Default magenta
    
    def _lighten_color(self, hex_color: str, factor: float = 0.3) -> str:
        """Lighten a hex color."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def assess_asset_quality(self, image: Image.Image) -> Dict:
        """Assess quality of a generated asset."""
        width, height = image.size
        score = 10.0
        notes = []
        
        # Check for alpha channel
        if image.mode != 'RGBA':
            score -= 2.0
            notes.append("Missing alpha channel")
        
        # Check for non-empty content
        pixels = list(image.getdata())
        non_transparent = sum(1 for p in pixels if len(p) > 3 and p[3] > 0)
        if non_transparent == 0:
            score -= 5.0
            notes.append("Completely transparent")
        elif non_transparent < len(pixels) * 0.1:
            score -= 1.0
            notes.append("Very sparse content")
        
        # Check color diversity
        unique_colors = len(set(pixels[:1000]))
        if unique_colors < 3:
            score -= 1.0
            notes.append("Low color diversity")
        
        return {
            'score': round(score, 2),
            'notes': notes,
            'width': width,
            'height': height
        }
