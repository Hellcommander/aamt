"""
Blender Script: Setup Textures for Space Whale Rigging
Loads texture maps and applies them to materials for rigging and spritesheet rendering.
"""

import bpy
import os
import json
from pathlib import Path

def load_texture_registry(registry_path: str):
    """Load texture registry JSON."""
    with open(registry_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_module_material(module_name: str, texture_paths: Dict, material_name: str = None):
    """Setup material with all texture maps for a module."""
    if material_name is None:
        material_name = f"{module_name}_Material"
    
    # Create or get material
    if material_name in bpy.data.materials:
        mat = bpy.data.materials[material_name]
    else:
        mat = bpy.data.materials.new(name=material_name)
    
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear existing nodes
    nodes.clear()
    
    # Output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    # Principled BSDF
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    # Load textures
    base_dir = Path(texture_paths.get('diffuse', '')).parent
    
    # Diffuse texture
    if 'diffuse' in texture_paths:
        diffuse_tex = nodes.new(type='ShaderNodeTexImage')
        diffuse_tex.location = (-400, 200)
        diffuse_path = base_dir / texture_paths['diffuse']
        if diffuse_path.exists():
            diffuse_img = bpy.data.images.load(str(diffuse_path))
            diffuse_tex.image = diffuse_img
            links.new(diffuse_tex.outputs['Color'], principled.inputs['Base Color'])
    
    # Emission texture
    if 'emission' in texture_paths:
        emission_tex = nodes.new(type='ShaderNodeTexImage')
        emission_tex.location = (-400, 0)
        emission_path = base_dir / texture_paths['emission']
        if emission_path.exists():
            emission_img = bpy.data.images.load(str(emission_path))
            emission_tex.image = emission_img
            
            # Emission shader
            emission = nodes.new(type='ShaderNodeEmission')
            emission.location = (-200, -200)
            links.new(emission_tex.outputs['Color'], emission.inputs['Color'])
            emission.inputs['Strength'].default_value = 3.5
            
            # Mix with base
            mix = nodes.new(type='ShaderNodeMix')
            mix.location = (200, 0)
            mix.data_type = 'RGBA'
            mix.blend_type = 'ADD'
            mix.inputs['Factor'].default_value = 0.6
            
            links.new(principled.outputs['BSDF'], mix.inputs[6])
            links.new(emission.outputs['Emission'], mix.inputs[7])
            links.new(mix.outputs['Result'], output.inputs['Surface'])
        else:
            links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    else:
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # Normal map
    if 'normal' in texture_paths:
        normal_tex = nodes.new(type='ShaderNodeTexImage')
        normal_tex.location = (-400, -200)
        normal_path = base_dir / texture_paths['normal']
        if normal_path.exists():
            normal_img = bpy.data.images.load(str(normal_path))
            normal_tex.image = normal_img
            
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            normal_map.location = (-200, -200)
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
    
    # Roughness map
    if 'roughness' in texture_paths:
        roughness_tex = nodes.new(type='ShaderNodeTexImage')
        roughness_tex.location = (-400, -400)
        roughness_path = base_dir / texture_paths['roughness']
        if roughness_path.exists():
            roughness_img = bpy.data.images.load(str(roughness_path))
            roughness_tex.image = roughness_img
            roughness_tex.image.colorspace_settings.name = 'Non-Color'
            links.new(roughness_tex.outputs['Color'], principled.inputs['Roughness'])
    
    # Metallic map
    if 'metallic' in texture_paths:
        metallic_tex = nodes.new(type='ShaderNodeTexImage')
        metallic_tex.location = (-400, -600)
        metallic_path = base_dir / texture_paths['metallic']
        if metallic_path.exists():
            metallic_img = bpy.data.images.load(str(metallic_path))
            metallic_tex.image = metallic_img
            metallic_tex.image.colorspace_settings.name = 'Non-Color'
            links.new(metallic_tex.outputs['Color'], principled.inputs['Metallic'])
    
    return mat

def setup_all_module_textures(registry_path: str, texture_base_dir: str):
    """Setup textures for all modules from registry."""
    registry = load_texture_registry(registry_path)
    
    materials = {}
    
    for module in registry.get('modules', []):
        module_name = module['module']
        texture_paths = module['textures']
        
        # Prepend base directory to paths
        full_paths = {}
        for key, path in texture_paths.items():
            full_paths[key] = os.path.join(texture_base_dir, path)
        
        mat = setup_module_material(module_name, full_paths)
        materials[module_name] = mat
    
    return materials

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup textures in Blender for Space Whale')
    parser.add_argument('--registry', required=True, help='Texture registry JSON path')
    parser.add_argument('--texture-dir', required=True, help='Base directory for textures')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    print("Setting up Space Whale textures in Blender...")
    materials = setup_all_module_textures(args.registry, args.texture_dir)
    
    print(f"Created {len(materials)} materials:")
    for name, mat in materials.items():
        print(f"  - {name}")

if __name__ == "__main__":
    main()

