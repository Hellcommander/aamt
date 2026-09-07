"""
Ollama-Powered Visual Variation Generator
Uses Ollama to generate 50 variations of visual language assets and assesses quality.
Uses WizardLM-uncensored for visual tasks (restricted from system files).
"""

import json
import hashlib
import os
import subprocess
from typing import Dict, List, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
from queue import Queue
from pathlib import Path

# Try to import requests, fallback if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests module not found. Install with: pip install requests")
    print("Will use fallback generation only.")

# Import model router for dual-model support
import os
import sys
_model_router_path = os.path.join(os.path.dirname(__file__), "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ollama_model_router import get_visual_model, TASK_VISUAL
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_VISUAL = "visual"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_VISUAL = "visual"

# Model context limits (in tokens, approximate: 1 token ≈ 4 characters)
# CodeLlama has 8k token limit, other models may vary
MODEL_CONTEXT_LIMITS = {
    'codellama:34b': 8000,  # CodeLlama limit: 8k tokens
    'codellama:13b': 8000,  # CodeLlama limit: 8k tokens
    'codellama:7b': 8000,   # CodeLlama limit: 8k tokens
    'wizardlm-uncensored:latest': 8192,  # WizardLM can handle more, but conservative
    'wizardlm-uncensored:13b': 8192,
    'wizardlm-uncensored:7b': 8192,
    'llama3.2': 128000,  # Llama 3.2 supports 128k context
    'llama3.1': 128000,  # Llama 3.1 supports 128k context
    'llama3': 8192,  # Llama 3 base: 8k
    'llama2': 4096,  # Llama 2: 4k
}

def estimate_token_count(text: str) -> int:
    """Estimate token count from text (rough approximation: 1 token ≈ 4 characters)."""
    return len(text) // 4

def truncate_prompt_for_model(prompt: str, model: str, max_response_tokens: int = 1000) -> str:
    """
    Truncate prompt to fit within model's context limit.
    
    Args:
        prompt: Full prompt text
        model: Model name
        max_response_tokens: Estimated tokens needed for response (default: 1000)
    
    Returns:
        Truncated prompt that fits within context limit
    """
    # Get context limit for model (default to 8000 for CodeLlama compatibility)
    context_limit = MODEL_CONTEXT_LIMITS.get(model.lower(), 8000)
    
    # Reserve tokens for response
    available_tokens = context_limit - max_response_tokens - 500  # Extra 500 for safety margin
    available_chars = available_tokens * 4  # Convert back to characters
    
    current_tokens = estimate_token_count(prompt)
    
    if current_tokens <= available_tokens:
        return prompt  # No truncation needed
    
    # Truncate by removing from detailed context section
    # Try to preserve the core prompt structure
    if "DESIGN CONTEXT:" in prompt:
        parts = prompt.split("DESIGN CONTEXT:", 1)
        if len(parts) == 2:
            header = parts[0] + "DESIGN CONTEXT:"
            context_and_rest = parts[1]
            
            # Calculate how much we can keep
            header_tokens = estimate_token_count(header)
            rest_tokens = estimate_token_count(context_and_rest.split("\n\n", 1)[1] if "\n\n" in context_and_rest else "")
            context_available = available_tokens - header_tokens - rest_tokens - 200  # Safety margin
            
            if context_available > 0:
                # Truncate the context section
                context_section = context_and_rest.split("\n\n", 1)[0] if "\n\n" in context_and_rest else context_and_rest
                context_chars = context_available * 4
                
                if len(context_section) > context_chars:
                    # Truncate and add ellipsis
                    truncated_context = context_section[:context_chars-50] + "\n\n[Context truncated to fit model context limit]"
                    rest = context_and_rest.split("\n\n", 1)[1] if "\n\n" in context_and_rest else ""
                    return header + truncated_context + "\n\n" + rest
    
    # Fallback: simple truncation
    if len(prompt) > available_chars:
        truncated = prompt[:available_chars-100] + "\n\n[Prompt truncated to fit model context limit]"
        return truncated
    
    return prompt

class OllamaVisualGenerator:
    """Generates visual variations using Ollama AI, then uses Blender and image tools to create actual visual assets."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = None, timeout: int = 300, max_retries: int = 3, blender_path: str = None):
        self.ollama_url = ollama_url
        # Use model router for visual tasks if available, otherwise auto-detect
        if model is None:
            if MODEL_ROUTER_AVAILABLE:
                model = get_visual_model()
            else:
                model = self.detect_best_model()
        self.model = model
        self.api_url = f"{ollama_url}/api/generate"
        self.timeout = timeout  # Default 5 minutes for large models
        self.max_retries = max_retries
        # Semaphore to limit concurrent requests (prevent overwhelming Ollama)
        # Reduced to 2 to prevent timeouts - each request can take 5+ minutes
        self.request_semaphore = threading.Semaphore(2)  # Max 2 concurrent requests
        
        # Blender path - use provided path or default location
        if blender_path:
            self.blender_path = Path(blender_path)
        else:
            # Default Blender 5.0 path
            default_blender = Path(r"D:\tools\Blender Foundation\Blender 5.0\blender.exe")
            if default_blender.exists():
                self.blender_path = default_blender
            else:
                # Try to find Blender
                self.blender_path = self.find_blender()
        
        # Check if PIL/Pillow is available for image drawing
        try:
            from PIL import Image, ImageDraw
            self.pil_available = True
        except ImportError:
            self.pil_available = False
            print("    WARNING: PIL/Pillow not available. Image drawing features will be limited.")
    
    def find_blender(self) -> Path:
        """Find Blender installation."""
        # Check common locations
        possible_paths = [
            Path(r"D:\tools\Blender Foundation\Blender 5.0\blender.exe"),
            Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
            Path(r"C:\Program Files (x86)\Blender Foundation\Blender 5.0\blender.exe"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Try to find via PATH
        try:
            result = subprocess.run(["where", "blender"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return None
    
    def detect_best_model(self) -> str:
        """
        Detect the best available Ollama model.
        Priority: CodeLlama-34B > CodeLlama-13B > WizardLM-uncensored-13B > other 13B+ > 7B > 3B
        """
        if not REQUESTS_AVAILABLE:
            return "wizardlm-uncensored:latest"  # Fallback
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    # Priority scoring: CodeLlama for code, then size, then instruction-tuned
                    def model_priority(m):
                        name = m.get('name', '').lower()
                        details = m.get('details', {})
                        param_size = details.get('parameter_size', '')
                        
                        # Highest priority: CodeLlama-34B (best for code generation)
                        if 'codellama' in name and ('34b' in name or '34' in name):
                            return 100
                        # High priority: CodeLlama-13B
                        elif 'codellama' in name and ('13b' in name or '13' in name):
                            return 90
                        # High priority: WizardLM-uncensored-13B (good for instructions)
                        elif 'wizardlm' in name and 'uncensored' in name and ('13b' in name or '13' in name):
                            return 85
                        # Medium-high: Other 34B models
                        elif '34b' in param_size or '34' in name:
                            return 70
                        # Medium: Other 13B+ models
                        elif '13b' in param_size or '13' in name or '70b' in param_size:
                            return 60
                        # Lower: 7B models
                        elif '7b' in param_size or '7' in name:
                            return 40
                        # Lowest: 3B models
                        elif '3b' in param_size or '3' in name:
                            return 20
                        return 10
                    
                    best_model = max(models, key=model_priority)
                    model_name = best_model.get('name', 'wizardlm-uncensored:latest')
                    print(f"Auto-detected best model: {model_name}")
                    return model_name
        except Exception as e:
            print(f"Warning: Could not detect Ollama models: {e}")
        
        return "wizardlm-uncensored:latest"  # Fallback
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate_color_palette_variation(self, base_palette: Dict, variation_id: int) -> Dict:
        """Generate a color palette variation using Ollama."""
        if not REQUESTS_AVAILABLE:
            return self.generate_fallback_palette(base_palette, variation_id)
        
        # Load detailed description
        detailed_desc_path = os.path.join(os.path.dirname(__file__), "SPACE_WHALE_AI_VISUAL_DESCRIPTION.md")
        detailed_context = ""
        if os.path.exists(detailed_desc_path):
            try:
                with open(detailed_desc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract the complete prompt
                    if "Complete AI Generation Prompt" in content:
                        start = content.find("```", content.find("Complete AI Generation Prompt"))
                        end = content.find("```", start + 3)
                        if start >= 0 and end > start:
                            detailed_context = content[start+3:end].strip()
            except:
                pass
        
        if not detailed_context:
            detailed_context = """Create a space whale capital ship that combines organic whale anatomy with advanced crystalline technology. Streamlined whale shape with bioluminescent skin - smooth, slightly translucent organic membrane with dark navy base and bright cyan vein network that pulses with energy. Crystalline armor plates overlay key sections. Nova Drift aesthetic - high-energy glows, smooth additive effects, procedural distortion, particle-driven motion."""
        
        prompt = f"""You are an expert color designer for sci-fi game assets. Your task is to generate JSON DATA ONLY - color specifications that will be used by rendering tools (Blender, texture generators) to create the actual visual assets.

CRITICAL: You are NOT creating images, drawings, or visual descriptions. You are generating JSON DATA with color hex codes that tools will use to render assets.

DESIGN CONTEXT:
{detailed_context}

BASE PALETTE REFERENCE:
- Base Color: {base_palette.get('baseColor', '#1a2a3a')} (dark navy - organic membrane)
- Vein Color: {base_palette.get('veinColor', '#66ccff')} (bright cyan - energy network)
- Emissive Color: {base_palette.get('emissiveColor', '#88ffff')} (intense white-cyan - core glow)

QUALITY REQUIREMENTS (CRITICAL):
1. COLOR HARMONY: Colors must harmonize - use analogous (adjacent on color wheel) or complementary schemes. Avoid clashing colors.
2. CONTRAST: Base color must be DARK (brightness < 60) for contrast. Emissive must be BRIGHT (brightness > 200) for visibility.
3. BIOLUMINESCENCE: Emissive colors should be vibrant cyan, blue, or white-cyan tones that suggest living energy.
4. AESTHETIC: Must fit "organic-meets-technological" - dark organic base with bright technological glows.
5. NOVA DRIFT STYLE: High saturation, smooth gradients, intense glows with additive blending feel.
6. COLOR VALIDITY: All colors must be valid hex codes (#RRGGBB format).

COLOR RELATIONSHIPS:
- baseColor: Dark (0-60 brightness) - organic membrane base
- veinColor: Medium-bright (100-180 brightness) - energy network, should complement base
- carapaceColor: Mid-tone between base and vein - crystalline armor overlay
- emissiveColor: Very bright (200-255 brightness) - bioluminescent core glow
- accentColor: Bright accent (150-220 brightness) - energy highlights

OUTPUT FORMAT (JSON DATA ONLY):
Generate a JSON object with:
{{
  "baseColor": "#hex (dark, 0-60 brightness)",
  "veinColor": "#hex (medium-bright, 100-180 brightness, harmonizes with base)",
  "carapaceColor": "#hex (mid-tone, blends base and vein)",
  "emissiveColor": "#hex (very bright, 200-255 brightness, cyan/blue/white-cyan)",
  "accentColor": "#hex (bright accent, 150-220 brightness)",
  "rationale": "Detailed 2-3 sentence explanation of color choices, harmony principles used, and how they achieve the bioluminescent space whale aesthetic"
}}

QUALITY STANDARDS:
- All colors must be valid hex codes
- Base must be dark enough for contrast (brightness < 60)
- Emissive must be bright enough for visibility (brightness > 200)
- Colors must harmonize (analogous or complementary scheme)
- Rationale must be detailed and specific

IMPORTANT: Return ONLY the JSON object. Do NOT generate images, drawings, visual descriptions, or any non-JSON content. This JSON will be used by Blender and texture generation tools to create the actual visual assets."""

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Use semaphore to limit concurrent requests
                with self.request_semaphore:
                    # Get context limit for explicit setting (matching Terraria mod reviewer)
                    context_limit = MODEL_CONTEXT_LIMITS.get(self.model.lower(), 8000)
                    
                    print(f"    Sending request to Ollama ({self.model})...")
                    print(f"    Context window: {context_limit} tokens (explicitly set)")
                    
                    response = requests.post(
                        self.api_url,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                    "options": {
                        "num_ctx": context_limit,  # Explicitly set context window (matching Terraria mod reviewer)
                        "temperature": 0.7,  # Balanced creativity and quality (reduced from 0.8)
                        "top_p": 0.85,  # Slightly more focused (reduced from 0.9)
                        "top_k": 40,  # Limit to top 40 tokens for better quality
                        "repeat_penalty": 1.1,  # Reduce repetition
                        "seed": variation_id  # Deterministic variation
                    }
                        },
                        timeout=self.timeout  # Configurable timeout (default 5 minutes)
                    )
            
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')
                    
                    # Log response size (matching Terraria mod reviewer style)
                    response_tokens = estimate_token_count(response_text)
                    print(f"    Received {len(response_text)} characters (~{response_tokens} tokens) from AI")
                    print(f"    NOTE: AI generated JSON data (color specifications), not images. Tools will use this data to render assets.")
                    
                    # Extract JSON from response
                    try:
                        # Try to find JSON in response
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = response_text[start:end]
                            palette = json.loads(json_str)
                            print(f"    ✓ Successfully parsed JSON data from AI response")
                            
                            # Validate and fix colors
                            for key in ['baseColor', 'veinColor', 'carapaceColor', 'emissiveColor', 'accentColor']:
                                if key in palette:
                                    color = palette[key]
                                    if not color.startswith('#'):
                                        palette[key] = '#' + color
                            
                            # Quality validation - ensure colors meet minimum standards
                            assessor = VisualQualityAssessor()
                            score, notes = assessor.assess_color_palette(palette)
                            
                            # If quality is acceptable (>= 7.0), use it and create visual assets
                            # Otherwise, continue to retry or use fallback
                            if score >= 7.0:
                                # Create visual assets using Blender and image tools, export spritesheets
                                # Note: output_dir will be set by the calling function
                                return palette
                            elif attempt < self.max_retries - 1:
                                # Low quality - retry with different seed
                                print(f"    Quality check failed (score: {score:.2f}), retrying...")
                                continue
                            else:
                                # Last attempt failed quality check - use fallback
                                print(f"    Quality check failed after all attempts (score: {score:.2f}), using fallback")
                    except json.JSONDecodeError:
                        pass
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                    print(f"    Ollama timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Ollama timeout after {self.max_retries} attempts, using fallback")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                    print(f"    Ollama error: {e} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Ollama error after {self.max_retries} attempts: {e}, using fallback")
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"    Unexpected error: {e} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Error after {self.max_retries} attempts: {e}, using fallback")
            
        # If we get here, all retries failed - use fallback
        fallback_palette = self.generate_fallback_palette(base_palette, variation_id)
        return fallback_palette
    
    def create_visual_assets_from_palette(self, palette: Dict, variation_id: int, output_dir: Path = None):
        """Create actual visual assets using texture generator, then Blender, then export as spritesheets."""
        print(f"    Creating visual assets from palette variation {variation_id}...")
        
        # Set up output directory
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "Transcendence" / "Output" / "SpaceWhaleAssets" / "VisualLanguage"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Create preview image using PIL (if available)
        if self.pil_available:
            try:
                self.create_palette_preview_image(palette, variation_id, output_dir)
            except Exception as e:
                print(f"    WARNING: Failed to create preview image: {e}")
        
        # 2. Generate textures using texture generator tool
        texture_dir = self.generate_textures_for_palette(palette, variation_id, output_dir)
        
        # 3. Call Blender to create 3D assets using the generated textures and export spritesheets
        if self.blender_path and self.blender_path.exists():
            try:
                self.call_blender_to_create_assets(palette, variation_id, output_dir, texture_dir)
            except Exception as e:
                print(f"    WARNING: Failed to call Blender renderer: {e}")
        else:
            print(f"    NOTE: Blender not found at {self.blender_path}, skipping 3D rendering")
            print(f"    Expected path: D:\\tools\\Blender Foundation\\Blender 5.0\\blender.exe")
    
    def generate_textures_for_palette(self, palette: Dict, variation_id: int, output_dir: Path) -> Path:
        """Generate textures using the texture generator tool."""
        print(f"    Generating textures using texture generator tool...")
        
        # Import the texture generator
        script_dir = Path(__file__).parent
        texture_gen_path = script_dir.parent / "Transcendence" / "space_whale_texture_generator.py"
        
        if not texture_gen_path.exists():
            print(f"    WARNING: Texture generator not found: {texture_gen_path}")
            return None
        
        # Create temporary visual registry with this palette
        temp_visual_registry = {
            "visualLanguage": {
                "colorPalettes": {
                    "primary": palette
                },
                "materials": {
                    "bioluminescentSkin": {
                        "properties": {
                            "baseColor": palette.get("baseColor", "#1a2a3a"),
                            "emission": {
                                "color": palette.get("emissiveColor", "#88ffff"),
                                "intensity": 3.5
                            },
                            "roughness": 0.6
                        }
                    }
                }
            }
        }
        
        # Create temporary ship registry
        temp_ship_registry = {
            "ships": [{
                "id": f"space_whale_variation_{variation_id:03d}",
                "visual": {
                    "modules": [
                        {"name": "head", "type": "head"},
                        {"name": "mid1", "type": "mid"},
                        {"name": "mid2", "type": "mid"},
                        {"name": "tail", "type": "tail"}
                    ]
                }
            }]
        }
        
        # Create temporary skinning registry (minimal)
        temp_skinning_registry = {
            "boneStructure": {
                "head": {"bones": []},
                "mid": {"bones": []},
                "tail": {"bones": []}
            }
        }
        
        # Save temporary registries
        temp_dir = output_dir / "temp_textures"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        visual_reg_path = temp_dir / f"visual_registry_v{variation_id:03d}.json"
        ship_reg_path = temp_dir / f"ship_registry_v{variation_id:03d}.json"
        skinning_reg_path = temp_dir / f"skinning_registry_v{variation_id:03d}.json"
        
        with open(visual_reg_path, 'w', encoding='utf-8') as f:
            json.dump(temp_visual_registry, f, indent=2)
        with open(ship_reg_path, 'w', encoding='utf-8') as f:
            json.dump(temp_ship_registry, f, indent=2)
        with open(skinning_reg_path, 'w', encoding='utf-8') as f:
            json.dump(temp_skinning_registry, f, indent=2)
        
        # Call texture generator
        texture_output_dir = output_dir / "Textures" / f"variation_{variation_id:03d}"
        texture_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(texture_gen_path),
                    "--ship-registry", str(ship_reg_path),
                    "--visual-registry", str(visual_reg_path),
                    "--skinning-registry", str(skinning_reg_path),
                    "--output", str(texture_output_dir)
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"    ✓ Textures generated successfully")
                # Check for generated textures
                if texture_output_dir.exists():
                    texture_files = list(texture_output_dir.rglob("*.png"))
                    if texture_files:
                        print(f"    ✓ Generated {len(texture_files)} texture files")
                return texture_output_dir
            else:
                print(f"    WARNING: Texture generator returned exit code {result.returncode}")
                if result.stderr:
                    print(f"    Texture generator error: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            print(f"    WARNING: Texture generation timed out")
        except Exception as e:
            print(f"    WARNING: Error calling texture generator: {e}")
        
        return None
    
    def create_palette_preview_image(self, palette: Dict, variation_id: int, output_dir: Path):
        """Create a 2D preview image showing the color palette."""
        from PIL import Image, ImageDraw
        
        # Create a simple color swatch image
        img = Image.new('RGB', (400, 200), color='#000000')
        draw = ImageDraw.Draw(img)
        
        # Draw color swatches
        colors = [
            ('baseColor', 'Base', 0),
            ('veinColor', 'Vein', 80),
            ('carapaceColor', 'Carapace', 160),
            ('emissiveColor', 'Emissive', 240),
            ('accentColor', 'Accent', 320)
        ]
        
        for i, (key, label, x) in enumerate(colors):
            color = palette.get(key, '#000000')
            # Draw color swatch
            draw.rectangle([x, 0, x + 60, 150], fill=color)
            # Draw label
            draw.text((x + 5, 160), label, fill='#ffffff')
        
        # Save preview
        preview_dir = output_dir / "Previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / f"palette_variation_{variation_id:03d}.png"
        img.save(preview_path)
        print(f"    ✓ Created preview image: {preview_path.name}")
    
    def call_blender_to_create_assets(self, palette: Dict, variation_id: int, output_dir: Path, texture_dir: Path = None):
        """Call Blender to create 3D assets using generated textures and export spritesheets."""
        # Find Blender renderer scripts
        script_dir = Path(__file__).parent
        blender_120_facings = script_dir / "blender_space_whale_120_facings.py"
        blender_renderer = script_dir / "blender_space_whale_renderer.py"
        
        if not blender_120_facings.exists() and not blender_renderer.exists():
            print(f"    NOTE: Blender renderer scripts not found")
            print(f"    Expected: {blender_120_facings} or {blender_renderer}")
            return
        
        # Create ship registry JSON with palette data for Blender
        ship_registry = {
            "ships": [{
                "id": f"space_whale_variation_{variation_id:03d}",
                "visual": {
                    "colorPalettes": {
                        "primary": palette
                    },
                    "materials": {
                        "bioluminescentSkin": {
                            "properties": {
                                "baseColor": palette.get("baseColor", "#1a2a3a"),
                                "emission": {
                                    "color": palette.get("emissiveColor", "#88ffff"),
                                    "intensity": 3.5
                                },
                                "roughness": 0.6
                            }
                        }
                    },
                    "silhouette": {
                        "length": 8.0,
                        "width": 3.5,
                        "height": 2.0
                    },
                    "modules": [
                        {"name": "head", "type": "head"},
                        {"name": "mid1", "type": "mid"},
                        {"name": "mid2", "type": "mid"},
                        {"name": "tail", "type": "tail"}
                    ]
                }
            }]
        }
        
        temp_json = output_dir / f"ship_variation_{variation_id:03d}.json"
        with open(temp_json, 'w', encoding='utf-8') as f:
            json.dump(ship_registry, f, indent=2)
        
        # Call Blender to create 120 facings spritesheet
        print(f"    Calling Blender to create 3D assets and export spritesheet...")
        print(f"    Using Blender: {self.blender_path}")
        if texture_dir:
            print(f"    Using textures from: {texture_dir}")
        
        # Use 120 facings script if available, otherwise use regular renderer
        blender_script = blender_120_facings if blender_120_facings.exists() else blender_renderer
        
        # Build Blender command
        blender_cmd = [
            str(self.blender_path),
            "--background",
            "--python", str(blender_script),
            "--",
            "--ship-registry", str(temp_json),
            "--output-dir", str(output_dir / "Spritesheets")
        ]
        
        # Add texture directory if available
        if texture_dir and texture_dir.exists():
            blender_cmd.extend(["--texture-dir", str(texture_dir)])
        
        # Add hero/selection image generation with mask
        selection_image_path = output_dir / "Spritesheets" / f"space_whale_variation_{variation_id:03d}_selection.jpg"
        blender_cmd.extend([
            "--hero-image", str(selection_image_path),
            "--generate-mask"  # Generate negative/outline mask
        ])
        
        try:
            result = subprocess.run(
                blender_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for 120 facings
            )
            
            if result.returncode == 0:
                print(f"    ✓ Blender created assets and exported spritesheet successfully")
                # Check for output files
                spritesheet_dir = output_dir / "Spritesheets"
                if spritesheet_dir.exists():
                    spritesheets = list(spritesheet_dir.glob(f"*variation_{variation_id:03d}*.png"))
                    if not spritesheets:
                        # Try finding any spritesheet files
                        spritesheets = list(spritesheet_dir.glob("*.png"))
                    if spritesheets:
                        print(f"    ✓ Spritesheet exported: {spritesheets[0].name}")
            else:
                print(f"    WARNING: Blender returned exit code {result.returncode}")
                if result.stdout:
                    print(f"    Blender output: {result.stdout[-500:]}")
                if result.stderr:
                    print(f"    Blender error: {result.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            print(f"    WARNING: Blender render timed out after 10 minutes")
        except Exception as e:
            print(f"    WARNING: Error calling Blender: {e}")
    
    def generate_fallback_palette(self, base_palette: Dict, variation_id: int) -> Dict:
        """Generate palette variation programmatically if Ollama fails."""
        import random
        random.seed(variation_id)
        
        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        def shift_hue(rgb, degrees):
            # Simple hue shift approximation
            r, g, b = rgb
            if degrees > 0:
                return (min(255, int(r * 1.1)), g, min(255, int(b * 1.1)))
            else:
                return (r, min(255, int(g * 1.1)), min(255, int(b * 1.1)))
        
        base_rgb = hex_to_rgb(base_palette.get('baseColor', '#1a2a3a'))
        vein_rgb = hex_to_rgb(base_palette.get('veinColor', '#66ccff'))
        
        # Enhanced variation algorithm for higher quality
        variation_type = variation_id % 8
        
        # Ensure base stays dark and emissive stays bright
        if variation_type == 0:
            # Darker base, brighter vein (best contrast)
            new_base = tuple(max(0, min(60, int(c * 0.7))) for c in base_rgb)  # Ensure dark
            new_vein = tuple(min(255, max(150, int(c * 1.4))) for c in vein_rgb)  # Ensure bright
        elif variation_type == 1:
            # Slight hue shift while maintaining contrast
            new_base = tuple(max(0, min(50, int(c * 0.75))) for c in base_rgb)
            new_vein = tuple(min(255, max(160, int(c * 1.3))) for c in vein_rgb)
            # Add slight cyan shift to vein
            new_vein = (min(255, new_vein[0] + 10), min(255, new_vein[1] + 20), min(255, new_vein[2] + 30))
        elif variation_type == 2:
            # Warmer tones (slight red shift)
            new_base = tuple(max(0, min(55, int(c * 0.8))) for c in base_rgb)
            new_vein = tuple(min(255, max(140, int(c * 1.25))) for c in vein_rgb)
            new_vein = (min(255, new_vein[0] + 15), new_vein[1], new_vein[2])
        elif variation_type == 3:
            # Cooler tones (more blue)
            new_base = tuple(max(0, min(45, int(c * 0.65))) for c in base_rgb)
            new_vein = tuple(min(255, max(170, int(c * 1.5))) for c in vein_rgb)
            new_vein = (new_vein[0], min(255, new_vein[1] + 10), min(255, new_vein[2] + 25))
        elif variation_type == 4:
            # High contrast - very dark base, very bright emissive
            new_base = tuple(max(0, min(40, int(c * 0.6))) for c in base_rgb)
            new_vein = tuple(min(255, max(180, int(c * 1.6))) for c in vein_rgb)
        elif variation_type == 5:
            # Balanced with slight desaturation on base
            new_base = tuple(max(0, min(50, int(sum(base_rgb) / 3 * 0.8))) for _ in range(3))  # Desaturated dark
            new_vein = tuple(min(255, max(150, int(c * 1.35))) for c in vein_rgb)
        elif variation_type == 6:
            # Purple-cyan theme
            new_base = tuple(max(0, min(50, int(c * 0.7))) for c in base_rgb)
            new_vein = (min(255, vein_rgb[0] + 20), min(255, vein_rgb[1] + 30), min(255, vein_rgb[2] + 40))
        else:
            # Green-cyan theme
            new_base = tuple(max(0, min(55, int(c * 0.75))) for c in base_rgb)
            new_vein = (min(255, vein_rgb[0] + 10), min(255, vein_rgb[1] + 35), min(255, vein_rgb[2] + 25))
        
        # Ensure quality constraints
        base_brightness = sum(new_base) / 3
        vein_brightness = sum(new_vein) / 3
        
        # Force base to be dark if needed
        if base_brightness > 60:
            new_base = tuple(max(0, int(c * 0.6)) for c in new_base)
        
        # Force emissive to be bright
        emissive = tuple(min(255, max(200, int(c * 1.3))) for c in new_vein)
        
        # Carapace is blend of base and vein
        carapace = tuple((a + b) // 2 for a, b in zip(new_base, new_vein))
        
        # Accent is slightly brighter than vein
        accent = tuple(min(255, int(c * 1.15)) for c in new_vein)
        
        return {
            "baseColor": rgb_to_hex(new_base),
            "veinColor": rgb_to_hex(new_vein),
            "carapaceColor": rgb_to_hex(carapace),
            "emissiveColor": rgb_to_hex(emissive),
            "accentColor": rgb_to_hex(accent),
            "rationale": f"High-quality programmatic variation {variation_id}: Dark organic base ({base_brightness:.0f} brightness) with bright bioluminescent veins ({vein_brightness:.0f} brightness) for optimal contrast and Nova Drift aesthetic"
        }
    
    def generate_material_variation(self, base_material: Dict, variation_id: int) -> Dict:
        """Generate material variation using Ollama."""
        if not REQUESTS_AVAILABLE:
            return self.generate_fallback_material(base_material, variation_id)
        
        prompt = f"""You are an expert material designer for sci-fi game assets. Your task is to generate JSON DATA ONLY - material property specifications that will be used by rendering tools (Blender, shader systems) to create the actual visual materials.

CRITICAL: You are NOT creating images, drawings, or visual descriptions. You are generating JSON DATA with material properties (emission intensity, roughness, metallic values) that tools will use to render materials.

BASE MATERIAL PROPERTIES:
- Base Color: {base_material.get('properties', {}).get('baseColor', '#1a2a3a')}
- Emission Color: {base_material.get('properties', {}).get('emission', {}).get('color', '#66ccff')}
- Emission Intensity: {base_material.get('properties', {}).get('emission', {}).get('intensity', 3.5)}
- Roughness: {base_material.get('properties', {}).get('roughness', 0.6)}

QUALITY REQUIREMENTS (CRITICAL):
1. EMISSION INTENSITY: Must be between 2.5-4.5 for optimal bioluminescent glow (optimal: 3.0-4.0)
2. ROUGHNESS: Must be between 0.5-0.7 for organic skin feel (optimal: 0.55-0.65)
3. METALLIC: Must be low (0.0-0.2) for organic material, not metallic
4. AESTHETIC: Must feel like living bioluminescent organic membrane, not synthetic material
5. NOVA DRIFT STYLE: High-energy glows with additive blending feel, smooth surfaces with subtle texture

MATERIAL PROPERTIES:
- Emission intensity: 2.5-4.5 (optimal: 3.0-4.0) - controls glow brightness
- Roughness: 0.5-0.7 (optimal: 0.55-0.65) - controls surface texture (organic, not plastic or matte)
- Metallic: 0.0-0.2 (organic, not metallic)
- Consider subsurface scattering for organic feel

OUTPUT FORMAT (JSON DATA ONLY):
Generate a JSON object with:
{{
  "emission": {{
    "intensity": <float between 2.5-4.5, optimal 3.0-4.0>,
    "color": "#hex (bright cyan/blue/white-cyan, 200+ brightness)"
  }},
  "roughness": <float between 0.5-0.7, optimal 0.55-0.65>,
  "metallic": <float between 0.0-0.2>,
  "rationale": "Detailed 2-3 sentence explanation of material choices and how they achieve bioluminescent organic skin aesthetic"
}}

QUALITY STANDARDS:
- Emission intensity must be in optimal range (2.5-4.5)
- Roughness must be in optimal range (0.5-0.7)
- Metallic must be low for organic feel (0.0-0.2)
- Rationale must be detailed and specific

IMPORTANT: Return ONLY the JSON object. Do NOT generate images, drawings, visual descriptions, or any non-JSON content. This JSON will be used by Blender and shader systems to create the actual material rendering."""

        # Check and truncate prompt if needed for context limits
        prompt_tokens = estimate_token_count(prompt)
        context_limit = MODEL_CONTEXT_LIMITS.get(self.model.lower(), 8000)  # Default to 8K for CodeLlama compatibility
        prompt_chars = len(prompt)
        
        # Log token usage (matching Terraria mod reviewer style)
        print(f"    Material prompt size: {prompt_chars} characters (~{prompt_tokens} tokens)")
        print(f"    Model context limit: {context_limit} tokens")
        print(f"    Available for response: {context_limit - prompt_tokens} tokens")
        
        if prompt_tokens > context_limit - 1000:  # Reserve 1000 tokens for response
            print(f"    WARNING: Material prompt ({prompt_tokens} tokens) exceeds safe limit ({context_limit - 1000} tokens), truncating...")
            original_tokens = prompt_tokens
            prompt = truncate_prompt_for_model(prompt, self.model, max_response_tokens=1000)
            new_tokens = estimate_token_count(prompt)
            print(f"    Truncated from {original_tokens} to {new_tokens} tokens ({original_tokens - new_tokens} tokens removed)")
        elif prompt_tokens > context_limit * 0.8:  # Warn if using >80% of context
            print(f"    WARNING: Material prompt uses {prompt_tokens}/{context_limit} tokens ({prompt_tokens*100//context_limit}%) - approaching limit")
        else:
            print(f"    Material prompt within safe limits ({prompt_tokens}/{context_limit} tokens, {prompt_tokens*100//context_limit}% used)")

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Use semaphore to limit concurrent requests
                with self.request_semaphore:
                    # Get context limit for explicit setting (matching Terraria mod reviewer)
                    context_limit = MODEL_CONTEXT_LIMITS.get(self.model.lower(), 8000)
                    
                    print(f"    Sending material request to Ollama ({self.model})...")
                    print(f"    Context window: {context_limit} tokens (explicitly set)")
                    
                    response = requests.post(
                        self.api_url,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "num_ctx": context_limit,  # Explicitly set context window (matching Terraria mod reviewer)
                                "temperature": 0.65,  # Slightly lower for more consistent quality
                                "top_p": 0.85,  # More focused
                                "top_k": 40,  # Limit to top tokens
                                "repeat_penalty": 1.1,  # Reduce repetition
                                "seed": variation_id
                            }
                        },
                        timeout=self.timeout  # Configurable timeout (default 5 minutes)
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        response_text = result.get('response', '')
                        
                        # Log response size (matching Terraria mod reviewer style)
                        response_tokens = estimate_token_count(response_text)
                        print(f"    Received {len(response_text)} characters (~{response_tokens} tokens) from AI")
                        print(f"    NOTE: AI generated JSON data (material properties), not images. Tools will use this data to render materials.")
                        
                        try:
                            start = response_text.find('{')
                            end = response_text.rfind('}') + 1
                            if start >= 0 and end > start:
                                json_str = response_text[start:end]
                                material_data = json.loads(json_str)
                                print(f"    ✓ Successfully parsed JSON data from AI response")
                                return material_data
                        except:
                            pass
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                    print(f"    Ollama timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Ollama timeout after {self.max_retries} attempts, using fallback")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                    print(f"    Ollama error: {e} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Ollama error after {self.max_retries} attempts: {e}, using fallback")
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"    Unexpected error: {e} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Error after {self.max_retries} attempts: {e}, using fallback")
        
        # If we get here, all retries failed - use fallback
        return self.generate_fallback_material(base_material, variation_id)
    
    def generate_fallback_material(self, base_material: Dict, variation_id: int) -> Dict:
        """Generate HIGH-QUALITY material variation programmatically."""
        import random
        random.seed(variation_id)
        
        base_intensity = base_material.get('properties', {}).get('emission', {}).get('intensity', 3.5)
        base_roughness = base_material.get('properties', {}).get('roughness', 0.6)
        emission_color = base_material.get('properties', {}).get('emission', {}).get('color', '#66ccff')
        
        # Enhanced variation algorithm - ensure optimal ranges
        variation_type = variation_id % 6
        
        if variation_type == 0:
            # Optimal intensity, optimal roughness
            intensity = 3.5 + random.uniform(-0.3, 0.3)  # 3.2-3.8
            roughness = 0.6 + random.uniform(-0.05, 0.05)  # 0.55-0.65
        elif variation_type == 1:
            # Higher intensity, slightly smoother
            intensity = 3.8 + random.uniform(-0.2, 0.2)  # 3.6-4.0
            roughness = 0.58 + random.uniform(-0.03, 0.03)  # 0.55-0.61
        elif variation_type == 2:
            # Lower intensity, slightly rougher
            intensity = 3.2 + random.uniform(-0.2, 0.2)  # 3.0-3.4
            roughness = 0.62 + random.uniform(-0.03, 0.03)  # 0.59-0.65
        elif variation_type == 3:
            # Balanced variation
            intensity = base_intensity + random.uniform(-0.4, 0.4)
            roughness = base_roughness + random.uniform(-0.08, 0.08)
        elif variation_type == 4:
            # High glow, organic texture
            intensity = 4.0 + random.uniform(-0.3, 0.3)  # 3.7-4.3
            roughness = 0.6 + random.uniform(-0.05, 0.05)  # 0.55-0.65
        else:
            # Subtle glow, smooth texture
            intensity = 3.0 + random.uniform(-0.3, 0.3)  # 2.7-3.3
            roughness = 0.58 + random.uniform(-0.05, 0.05)  # 0.53-0.63
        
        # Clamp to optimal ranges
        intensity = max(2.5, min(4.5, intensity))
        roughness = max(0.5, min(0.7, roughness))
        
        return {
            "emission": {
                "intensity": round(intensity, 2),
                "color": emission_color
            },
            "roughness": round(roughness, 2),
            "metallic": round(random.uniform(0.0, 0.15), 2),  # Low metallic for organic
            "rationale": f"High-quality programmatic material variation {variation_id}: Emission intensity {intensity:.2f} for optimal bioluminescent glow, roughness {roughness:.2f} for organic skin texture"
        }

class VisualQualityAssessor:
    """Assesses quality of visual variations."""
    
    def assess_color_palette(self, palette: Dict) -> Tuple[float, List[str]]:
        """Assess color palette quality with enhanced criteria."""
        score = 0.0
        notes = []
        
        # Get all colors
        colors = [
            palette.get('baseColor', '#000000'),
            palette.get('veinColor', '#000000'),
            palette.get('carapaceColor', '#000000'),
            palette.get('emissiveColor', '#000000'),
            palette.get('accentColor', '#000000')
        ]
        
        # Color validity (MANDATORY - 0 points if invalid, but blocks scoring)
        if not all(self.is_valid_hex(c) for c in colors):
            notes.append("INVALID: Invalid color format")
            return 0.0, notes
        
        # Color harmony (0-4 points) - Enhanced scoring
        if self.colors_harmonize(colors):
            score += 4.0
            notes.append("Excellent color harmony")
        elif self.colors_acceptable(colors):
            score += 2.5
            notes.append("Good color harmony")
        elif self.colors_partially_harmonize(colors):
            score += 1.0
            notes.append("Partial color harmony")
        else:
            score += 0.0
            notes.append("Color harmony needs improvement")
        
        # Contrast check (0-3 points) - Enhanced scoring
        base = self.hex_to_rgb(palette.get('baseColor', '#1a2a3a'))
        emissive = self.hex_to_rgb(palette.get('emissiveColor', '#88ffff'))
        vein = self.hex_to_rgb(palette.get('veinColor', '#66ccff'))
        
        base_brightness = sum(base) / 3
        emissive_brightness = sum(emissive) / 3
        vein_brightness = sum(vein) / 3
        
        # Base-emissive contrast (most important)
        contrast = abs(emissive_brightness - base_brightness)
        if contrast > 180:
            score += 3.0
            notes.append("Excellent base-emissive contrast")
        elif contrast > 150:
            score += 2.0
            notes.append("Very good contrast")
        elif contrast > 120:
            score += 1.0
            notes.append("Good contrast")
        else:
            notes.append("Contrast needs improvement (target: >150)")
        
        # Emissive brightness (0-2 points) - Stricter
        if emissive_brightness >= 220:
            score += 2.0
            notes.append("Excellent emissive brightness")
        elif emissive_brightness >= 200:
            score += 1.5
            notes.append("Very good emissive brightness")
        elif emissive_brightness >= 180:
            score += 1.0
            notes.append("Good emissive brightness")
        else:
            notes.append(f"Emissive too dim (current: {emissive_brightness:.0f}, target: >200)")
        
        # Base darkness (0-2 points) - Stricter
        if base_brightness <= 40:
            score += 2.0
            notes.append("Excellent dark base")
        elif base_brightness <= 60:
            score += 1.5
            notes.append("Very good dark base")
        elif base_brightness <= 80:
            score += 1.0
            notes.append("Good base darkness")
        else:
            notes.append(f"Base too bright (current: {base_brightness:.0f}, target: <60)")
        
        # Vein color appropriateness (0-1 point)
        if 100 <= vein_brightness <= 180:
            score += 1.0
            notes.append("Appropriate vein brightness")
        else:
            notes.append(f"Vein brightness out of range (current: {vein_brightness:.0f}, target: 100-180)")
        
        # Color saturation check (0-1 point)
        base_sat = self.get_saturation(base)
        emissive_sat = self.get_saturation(emissive)
        if base_sat < 0.3 and emissive_sat > 0.6:  # Dark desaturated base, bright saturated emissive
            score += 1.0
            notes.append("Good saturation contrast")
        elif base_sat < 0.4 and emissive_sat > 0.5:
            score += 0.5
            notes.append("Acceptable saturation contrast")
        
        # Rationale quality (0-1 point) - Stricter
        rationale = palette.get('rationale', '')
        if len(rationale) > 50 and ('harmony' in rationale.lower() or 'contrast' in rationale.lower() or 'bioluminescent' in rationale.lower()):
            score += 1.0
            notes.append("Detailed rationale")
        elif len(rationale) > 20:
            score += 0.5
            notes.append("Basic rationale")
        else:
            notes.append("Rationale too brief")
        
        # Bonus: All colors present (0-0.5 points)
        if all(c and c != '#000000' for c in colors):
            score += 0.5
            notes.append("All color slots filled")
        
        return min(10.0, score), notes
    
    def colors_partially_harmonize(self, colors: List[str]) -> bool:
        """Check if colors partially harmonize (less strict)."""
        rgbs = [self.hex_to_rgb(c) for c in colors]
        avg_r = sum(r[0] for r in rgbs) / len(rgbs)
        avg_g = sum(r[1] for r in rgbs) / len(rgbs)
        avg_b = sum(r[2] for r in rgbs) / len(rgbs)
        
        threshold = 100  # More lenient
        harmonizing = 0
        for rgb in rgbs:
            if (abs(rgb[0] - avg_r) <= threshold and 
                abs(rgb[1] - avg_g) <= threshold and 
                abs(rgb[2] - avg_b) <= threshold):
                harmonizing += 1
        
        return harmonizing >= len(rgbs) * 0.6  # At least 60% harmonize
    
    def get_saturation(self, rgb: tuple) -> float:
        """Calculate color saturation (0-1)."""
        r, g, b = rgb
        max_val = max(r, g, b) / 255.0
        min_val = min(r, g, b) / 255.0
        if max_val == 0:
            return 0.0
        if max_val == min_val:
            return 0.0
        return (max_val - min_val) / max_val
    
    def assess_material(self, material: Dict) -> Tuple[float, List[str]]:
        """Assess material quality with enhanced criteria."""
        score = 0.0
        notes = []
        
        # Emission intensity (0-3 points) - Enhanced scoring
        intensity = material.get('emission', {}).get('intensity', 3.5)
        if 3.0 <= intensity <= 4.0:
            score += 3.0
            notes.append("Excellent emission intensity (optimal range)")
        elif 2.5 <= intensity <= 4.5:
            score += 2.0
            notes.append("Very good emission intensity")
        elif 2.0 <= intensity <= 5.0:
            score += 1.0
            notes.append("Acceptable emission intensity")
        else:
            notes.append(f"Emission intensity out of optimal range (current: {intensity:.2f}, target: 2.5-4.5)")
        
        # Roughness (0-3 points) - Enhanced scoring
        roughness = material.get('roughness', 0.6)
        if 0.55 <= roughness <= 0.65:
            score += 3.0
            notes.append("Excellent roughness (optimal range)")
        elif 0.5 <= roughness <= 0.7:
            score += 2.0
            notes.append("Very good roughness")
        elif 0.4 <= roughness <= 0.8:
            score += 1.0
            notes.append("Acceptable roughness")
        else:
            notes.append(f"Roughness out of optimal range (current: {roughness:.2f}, target: 0.5-0.7)")
        
        # Metallic check (0-1 point) - Organic should be low
        metallic = material.get('metallic', 0.0)
        if 0.0 <= metallic <= 0.2:
            score += 1.0
            notes.append("Appropriate metallic value for organic material")
        elif metallic <= 0.3:
            score += 0.5
            notes.append("Acceptable metallic value")
        else:
            notes.append(f"Metallic too high for organic material (current: {metallic:.2f}, target: <0.2)")
        
        # Emission color brightness (0-1 point)
        emission_color = material.get('emission', {}).get('color', '#66ccff')
        if self.is_valid_hex(emission_color):
            emissive_rgb = self.hex_to_rgb(emission_color)
            emissive_brightness = sum(emissive_rgb) / 3
            if emissive_brightness >= 200:
                score += 1.0
                notes.append("Bright emission color")
            elif emissive_brightness >= 180:
                score += 0.5
                notes.append("Good emission brightness")
            else:
                notes.append(f"Emission color too dim (current: {emissive_brightness:.0f}, target: >200)")
        
        # Rationale quality (0-1 point)
        rationale = material.get('rationale', '')
        if len(rationale) > 40 and ('bioluminescent' in rationale.lower() or 'organic' in rationale.lower()):
            score += 1.0
            notes.append("Detailed rationale")
        elif len(rationale) > 20:
            score += 0.5
            notes.append("Basic rationale")
        else:
            notes.append("Rationale too brief")
        
        # Bonus: All properties present (0-1 point)
        if 'emission' in material and 'roughness' in material:
            score += 1.0
            notes.append("All required properties present")
        
        return min(10.0, score), notes
    
    def hex_to_rgb(self, hex_str: str) -> tuple:
        """Convert hex to RGB."""
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    
    def colors_harmonize(self, colors: List[str]) -> bool:
        """Check if colors harmonize."""
        rgbs = [self.hex_to_rgb(c) for c in colors]
        avg_r = sum(r[0] for r in rgbs) / len(rgbs)
        avg_g = sum(r[1] for r in rgbs) / len(rgbs)
        avg_b = sum(r[2] for r in rgbs) / len(rgbs)
        
        threshold = 60
        for rgb in rgbs:
            if (abs(rgb[0] - avg_r) > threshold or 
                abs(rgb[1] - avg_g) > threshold or 
                abs(rgb[2] - avg_b) > threshold):
                return False
        return True
    
    def colors_acceptable(self, colors: List[str]) -> bool:
        """Less strict color check."""
        rgbs = [self.hex_to_rgb(c) for c in colors]
        def dist(rgb1, rgb2):
            return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
        
        dists = [dist(rgbs[0], rgbs[1]), dist(rgbs[1], rgbs[2]), dist(rgbs[0], rgbs[2])]
        return min(dists) < 120
    
    def is_valid_hex(self, hex_str: str) -> bool:
        """Check if hex color is valid."""
        hex_str = hex_str.lstrip('#')
        return len(hex_str) == 6 and all(c in '0123456789abcdefABCDEF' for c in hex_str)

def generate_and_assess_variations(registry_path: str, output_dir: str, count: int = 50, model: str = None):
    """Generate variations using Ollama and assess quality."""
    import os
    
    # Load base registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    visual_lang = registry.get('visualLanguage', {})
    base_palette = visual_lang.get('colorPalettes', {}).get('primary', {})
    base_material = visual_lang.get('materials', {}).get('bioluminescentSkin', {})
    
    # Initialize generators
    generator = OllamaVisualGenerator(model=model)
    assessor = VisualQualityAssessor()
    
    # Check Ollama availability
    if not generator.check_ollama_available():
        print("WARNING: Ollama not available. Using fallback generation.")
        print("Start Ollama: ollama serve")
        print("Or install: https://ollama.ai")
    else:
        # Log model and context information (matching Terraria mod reviewer style)
        context_limit = MODEL_CONTEXT_LIMITS.get(model.lower() if model else "unknown", 8000)
        print(f"\n{'='*60}")
        print("Ollama Visual Variation Generator - Design Specification Tool")
        print(f"{'='*60}")
        print(f"Using Ollama model: {model or 'auto-detected'}")
        print(f"Model context limit: {context_limit} tokens")
        print(f"Generating {count} variations with token-aware prompt management")
        print("")
        print("WORKFLOW:")
        print("  1. AI generates JSON data (color palettes, material properties)")
        print("  2. Texture Generator creates texture maps (diffuse, emission, normal, etc.)")
        print("  3. Blender creates 3D models using the generated textures")
        print("  4. Blender renders 120 facings spritesheet (360° rotation)")
        print("  5. Spritesheets exported for use in Transcendence")
        print("")
        print("AI Output: JSON specifications (hex colors, material values)")
        print("Texture Generator: Creates texture maps from JSON data")
        print("Blender: Creates 3D models with textures and renders spritesheets")
        print("Tools Used:")
        print(f"  - Texture Generator: space_whale_texture_generator.py")
        print(f"  - Blender: {generator.blender_path if generator.blender_path and generator.blender_path.exists() else 'Not found'}")
        print(f"  - Image Tools (PIL/Pillow): {'Available' if generator.pil_available else 'Not available'}")
        print(f"{'='*60}\n")
    
    # Validate output directory to prevent system file modifications
    try:
        from file_safety_validator import validate_output_path, get_script_root
        script_root = get_script_root()
        is_valid, error_msg = validate_output_path(output_dir, script_root)
        if not is_valid:
            print(f"ERROR: {error_msg}")
            print(f"Cannot use output directory: {output_dir}")
            return
    except ImportError:
        # File safety validator not available - use basic check
        abs_path = os.path.abspath(output_dir)
        if abs_path.lower().startswith(('c:\\windows', 'c:\\program files', 'c:\\system32')):
            print(f"ERROR: Cannot write to system directory: {output_dir}")
            return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate color palette variations with multithreading
    print(f"Generating {count} color palette variations using multithreading...")
    
    # Determine optimal thread count (up to 32 cores, but limit for API rate limiting)
    # Limit Ollama concurrency to prevent timeouts (max 4 concurrent requests)
    # Ollama can't handle too many simultaneous requests - each request can take 5+ minutes
    max_workers = min(4, cpu_count(), 8)  # Cap at 4 for Ollama API stability
    print(f"Using {max_workers} worker threads (limited for Ollama API stability)")
    
    # Thread-safe collections
    palette_variations = []
    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    completed_count = [0]  # Use list for mutable shared state
    
    def generate_single_variation(variation_id: int) -> Tuple[Dict, float]:
        """Generate a single variation with quality validation (thread-safe)."""
        try:
            # Each thread gets its own generator instance to avoid conflicts
            thread_generator = OllamaVisualGenerator(model=model, timeout=300, max_retries=3)
            thread_assessor = VisualQualityAssessor()
            
            # Set up output directory for this variation
            output_dir_path = Path(output_dir)
            
            # Try to generate high-quality variation (up to 2 attempts)
            max_quality_attempts = 2
            best_variation = None
            best_score = 0.0
            best_notes = []
            
            for quality_attempt in range(max_quality_attempts):
                # Use different seed for retry to get different result
                attempt_id = variation_id * 100 + quality_attempt
                variation = thread_generator.generate_color_palette_variation(base_palette, attempt_id)
                score, notes = thread_assessor.assess_color_palette(variation)
                
                if score > best_score:
                    best_score = score
                    best_variation = variation
                    best_notes = notes
                
                # If we got high quality (>= 8.0), use it immediately
                if score >= 8.0:
                    break
            
            # Use best variation found
            if best_variation:
                best_variation['quality'] = {
                    'score': round(best_score, 2),
                    'notes': best_notes
                }
                best_variation['variation_id'] = variation_id
                
                # Create visual assets using Blender and export spritesheets
                print(f"  Creating visual assets for variation {variation_id}...")
                thread_generator.create_visual_assets_from_palette(best_variation, variation_id, output_dir_path)
            else:
                # Fallback if all attempts failed
                best_variation = thread_generator.generate_fallback_palette(base_palette, variation_id)
                score, notes = thread_assessor.assess_color_palette(best_variation)
                best_variation['quality'] = {'score': round(score, 2), 'notes': notes}
                best_variation['variation_id'] = variation_id
                best_score = score
                
                # Create visual assets from fallback too
                print(f"  Creating visual assets for fallback variation {variation_id}...")
                thread_generator.create_visual_assets_from_palette(best_variation, variation_id, output_dir_path)
            
            # Thread-safe progress update
            with progress_lock:
                completed_count[0] += 1
                current = completed_count[0]
                if current % 10 == 0 or current == count:
                    quality_tier = "EXCELLENT" if best_score >= 9.0 else "VERY_GOOD" if best_score >= 8.0 else "GOOD" if best_score >= 7.0 else "ACCEPTABLE"
                    print(f"  Progress: {current}/{count} ({current*100//count}%) - Latest: {best_score:.2f} ({quality_tier})")
            
            return (best_variation, best_score)
        except Exception as e:
            print(f"  Error generating variation {variation_id}: {e}")
            # Return fallback variation
            fallback = thread_generator.generate_fallback_palette(base_palette, variation_id)
            score, notes = thread_assessor.assess_color_palette(fallback)
            fallback['quality'] = {'score': round(score, 2), 'notes': notes}
            fallback['variation_id'] = variation_id
            return (fallback, score)
    
    # Use ThreadPoolExecutor for parallel generation
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_id = {executor.submit(generate_single_variation, i): i for i in range(count)}
        
        # Collect results as they complete (thread-safe)
        for future in as_completed(future_to_id):
            try:
                result = future.result()
                with results_lock:
                    palette_variations.append(result)
            except Exception as e:
                variation_id = future_to_id[future]
                print(f"  Error in variation {variation_id}: {e}")
    
    # Sort by score
    palette_variations.sort(key=lambda x: x[1], reverse=True)
    
    # Quality filtering and statistics
    high_quality = [v for v in palette_variations if v[1] >= 8.0]
    medium_quality = [v for v in palette_variations if 7.0 <= v[1] < 8.0]
    low_quality = [v for v in palette_variations if v[1] < 7.0]
    
    print(f"\n  Quality Summary:")
    print(f"    High quality (>= 8.0): {len(high_quality)} ({len(high_quality)*100//len(palette_variations) if palette_variations else 0}%)")
    print(f"    Medium quality (7.0-7.9): {len(medium_quality)} ({len(medium_quality)*100//len(palette_variations) if palette_variations else 0}%)")
    print(f"    Low quality (< 7.0): {len(low_quality)} ({len(low_quality)*100//len(palette_variations) if palette_variations else 0}%)")
    
    if palette_variations:
        avg_score = sum(v[1] for v in palette_variations) / len(palette_variations)
        print(f"    Average score: {avg_score:.2f}/10.0")
        print(f"    Best score: {palette_variations[0][1]:.2f}/10.0")
        print(f"    Worst score: {palette_variations[-1][1]:.2f}/10.0")
    
    # Save results with quality metadata
    results = {
        "version": "1.0.0",
        "generation": {
            "method": "ollama",
            "model": model,
            "count": count,
            "base_palette": base_palette,
            "quality_stats": {
                "total": len(palette_variations),
                "high_quality": len(high_quality),
                "medium_quality": len(medium_quality),
                "low_quality": len(low_quality),
                "average_score": round(avg_score, 2) if palette_variations else 0.0,
                "best_score": round(palette_variations[0][1], 2) if palette_variations else 0.0,
                "worst_score": round(palette_variations[-1][1], 2) if palette_variations else 0.0
            }
        },
        "variations": [v[0] for v in palette_variations],
        "top_10": [v[0] for v in palette_variations[:10]],
        "high_quality_only": [v[0] for v in high_quality]  # Only high-quality variations
    }
    
    output_path = os.path.join(output_dir, "ollama_palette_variations.json")
    # Validate output path to prevent system file modifications
    try:
        from file_safety_validator import validate_output_path, get_script_root
        script_root = get_script_root()
        is_valid, error_msg = validate_output_path(output_path, script_root)
        if not is_valid:
            print(f"ERROR: {error_msg}")
            print(f"Cannot write to: {output_path}")
            return
    except ImportError:
        # File safety validator not available - use basic check
        abs_path = os.path.abspath(output_path)
        if abs_path.lower().startswith(('c:\\windows', 'c:\\program files', 'c:\\system32')):
            print(f"ERROR: Cannot write to system directory: {output_path}")
            return
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    print(f"\nTop 10 Variations:")
    for i, (variation, score) in enumerate(palette_variations[:10], 1):
        notes = variation.get('quality', {}).get('notes', [])
        quality_tier = "EXCELLENT" if score >= 9.0 else "VERY_GOOD" if score >= 8.0 else "GOOD" if score >= 7.0 else "ACCEPTABLE"
        print(f"  {i}. Score: {score:.2f} ({quality_tier}) - {variation.get('baseColor')} / {variation.get('veinColor')}")
        if notes:
            print(f"     Notes: {', '.join(notes[:2])}")  # Show first 2 quality notes
        if variation.get('rationale'):
            rationale = variation['rationale'][:80]
            print(f"     {rationale}...")
    
    return palette_variations

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate visual variations using Ollama')
    parser.add_argument('--registry', required=True, help='Path to visual language registry')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--count', type=int, default=50, help='Number of variations')
    parser.add_argument('--model', default=None, help='Ollama model name (None = auto-detect via dual-model router)')
    
    args = parser.parse_args()
    
    print("Ollama Visual Variation Generator")
    print("=================================")
    print(f"Model: {args.model}")
    print(f"Variations: {args.count}")
    print("")
    
    generate_and_assess_variations(args.registry, args.output, args.count, args.model)
    print("\nGeneration complete!")

