"""
AI Material Generator for Projectiles
Generates procedural material specifications using AI (Ollama) based on projectile descriptions.
Uses dual-model router: visual model for material descriptions.
"""

import json
import argparse
import subprocess
import sys
import os

# Import model router for dual-model support
_model_router_path = os.path.join(os.path.dirname(__file__), "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ollama_model_router import get_visual_model, TASK_VISUAL
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
else:
    MODEL_ROUTER_AVAILABLE = False

def call_ollama(prompt, model=None):
    """Call Ollama API to generate material spec"""
    # Use dual-model router: material generation is a visual task
    if model is None:
        if MODEL_ROUTER_AVAILABLE:
            model = get_visual_model()
            print(f"Using visual model: {model}")
        else:
            model = "wizardlm-uncensored:latest"  # Fallback
    
    try:
        # Use ollama CLI
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        print("Error: Ollama not found. Install Ollama from https://ollama.ai")
        return None
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None

def generate_material_spec(projectile_type, description, palette_hint=None, model=None):
    """Generate material specification using AI"""
    prompt = f"""Generate a procedural material specification for a {projectile_type} projectile in a space game.

Description: {description}

Generate a JSON object with the following structure:
{{
  "type": "Energy|Plasma|Kinetic|Crystal|Organic|Exotic",
  "glowIntensity": 0.0-10.0,
  "emissionStrength": 0.0-10.0,
  "roughness": 0.0-1.0,
  "metallic": 0.0-1.0
}}

Also suggest a color palette with primary, secondary, glow, and trail colors in hex format.

Return only valid JSON, no additional text."""

    if palette_hint:
        prompt += f"\n\nColor hint: {palette_hint}"

    response = call_ollama(prompt)
    
    if not response:
        return None
    
    # Try to extract JSON from response
    try:
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None

def enhance_registry_with_ai(registry_path, output_path, model=None):
    """Enhance projectile registry with AI-generated material specs
    
    Uses dual-model router: visual model for material descriptions.
    If model is None, auto-detects best visual model (WizardLM-uncensored preferred).
    """
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    projectiles = registry.get('projectiles', [])
    
    for projectile in projectiles:
        # Skip if material already defined
        if 'material' in projectile.get('visual', {}) and projectile['visual']['material']:
            continue
        
        print(f"Generating material for: {projectile['id']}")
        
        # Generate description from projectile data
        description = f"{projectile.get('type', 'Projectile')} projectile"
        if 'damage' in projectile:
            damage = projectile['damage']
            description += f" dealing {damage.get('baseDamage', 0)} {damage.get('damageType', 'laser')} damage"
        
        # Generate material spec (uses visual model from router)
        material_spec = generate_material_spec(
            projectile.get('type', 'Laser'),
            description,
            palette_hint=projectile.get('visual', {}).get('palette'),
            model=model  # None = auto-detect via dual-model router
        )
        
        if material_spec:
            # Update registry
            if 'visual' not in projectile:
                projectile['visual'] = {}
            
            projectile['visual']['material'] = material_spec
            
            # Generate palette if not present
            if 'palette' not in projectile['visual']:
                projectile['visual']['palette'] = {
                    "primary": "#FF6B00",
                    "secondary": "#FFD700",
                    "glow": "#FF4500",
                    "trail": "#FF8C00"
                }
            
            print(f"  Generated material: {material_spec['type']}")
        else:
            print(f"  Failed to generate material, using defaults")
    
    # Save enhanced registry
    with open(output_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\nEnhanced registry saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate AI material specs for projectiles')
    parser.add_argument('--registry', required=True, help='Path to projectile registry JSON')
    parser.add_argument('--output', required=True, help='Output path for enhanced registry')
    parser.add_argument('--model', default=None, help='Ollama model to use (None = auto-detect via dual-model router)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.registry):
        print(f"Error: Registry file not found: {args.registry}")
        sys.exit(1)
    
    enhance_registry_with_ai(args.registry, args.output, args.model)

if __name__ == "__main__":
    main()

