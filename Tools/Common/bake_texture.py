#!/usr/bin/env python3
"""
Blender Texture Baker - Production-ready procedural texture generator
Bakes procedural materials to PNG textures for mod asset pipelines.
"""

import bpy
import argparse
import sys
import os
import json

# Import material generator
try:
    from material_generator import build_material_from_visual
    HAS_MATERIAL_GENERATOR = True
except ImportError:
    HAS_MATERIAL_GENERATOR = False
    print("Warning: material_generator.py not found, using fallback material builders")

# ------------------------------------------------------------
# Argument parsing
# ------------------------------------------------------------
def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description='Bake procedural textures from Blender materials')
    parser.add_argument("--material", type=str, help="Material type name (e.g., 'wood', 'stone', 'metal')")
    parser.add_argument("--json", type=str, help="JSON file with material definition")
    parser.add_argument("--visualJson", type=str, help="Visual block JSON from asset registry")
    parser.add_argument("--registry", type=str, help="Registry JSON file path")
    parser.add_argument("--assetId", type=str, help="Asset ID from registry")
    parser.add_argument("--quality", type=str, default="standard", choices=["draft", "standard", "high", "ultra"], help="Quality level for material generation")
    parser.add_argument("--size", type=int, default=512, help="Texture size in pixels")
    parser.add_argument("--output", type=str, help="Output PNG path (or base path for multi-map baking)")
    parser.add_argument("--outputDir", type=str, help="Output directory for multi-map baking")
    parser.add_argument("--pass", type=str, default="DIFFUSE", choices=["DIFFUSE", "ROUGHNESS", "NORMAL", "EMIT", "COMBINED", "ALL"], help="Bake pass type (ALL bakes all maps)")
    parser.add_argument("--textures", type=str, help="JSON string specifying which textures to bake: {\"baseColor\":true,\"normal\":false,...}")
    parser.add_argument("--exportNodeGroups", action="store_true", help="Export materials as node groups for manual tweaking (saves .blend file)")
    parser.add_argument("--blendOutput", type=str, help="Output path for .blend file with node groups")
    parser.add_argument("--seamless", action="store_true", help="Make texture tileable/seamless")
    parser.add_argument("--samples", type=int, default=1, help="Cycles render samples (1 for fast, higher for quality)")
    
    return parser.parse_args(argv)


# ------------------------------------------------------------
# Utility: Clear scene
# ------------------------------------------------------------
def clear_scene():
    """Clear all objects and materials from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Clean up orphaned data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


# ------------------------------------------------------------
# Procedural Material Builders
# Extend this with your own material types
# ------------------------------------------------------------

def build_material_wood(name="WoodMaterial"):
    """Build a procedural wood material."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Create nodes
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    noise1 = nodes.new("ShaderNodeTexNoise")
    noise2 = nodes.new("ShaderNodeTexNoise")
    wave = nodes.new("ShaderNodeTexWave")
    colorramp1 = nodes.new("ShaderNodeValToRGB")
    colorramp2 = nodes.new("ShaderNodeValToRGB")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")
    mix = nodes.new("ShaderNodeMixRGB")

    # Layout
    output.location = (600, 0)
    principled.location = (400, 0)
    mix.location = (200, 0)
    colorramp2.location = (0, 0)
    colorramp1.location = (-200, 0)
    wave.location = (-400, -100)
    noise2.location = (-400, 0)
    noise1.location = (-400, 100)
    mapping.location = (-600, 0)
    tex_coord.location = (-800, 0)

    # Wood grain setup
    noise1.inputs["Scale"].default_value = 10.0
    noise2.inputs["Scale"].default_value = 50.0
    wave.inputs["Scale"].default_value = 5.0
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"

    # Color ramps for wood tones
    colorramp1.color_ramp.elements[0].color = (0.3, 0.2, 0.1, 1.0)  # Dark brown
    colorramp1.color_ramp.elements[1].color = (0.5, 0.35, 0.2, 1.0)  # Light brown
    colorramp2.color_ramp.elements[0].color = (0.2, 0.15, 0.1, 1.0)  # Very dark
    colorramp2.color_ramp.elements[1].color = (0.4, 0.3, 0.2, 1.0)  # Medium brown

    # Connect nodes
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise1.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise2.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    
    links.new(noise1.outputs["Fac"], colorramp1.inputs["Fac"])
    links.new(wave.outputs["Fac"], colorramp2.inputs["Fac"])
    links.new(colorramp1.outputs["Color"], mix.inputs["Color1"])
    links.new(colorramp2.outputs["Color"], mix.inputs["Color2"])
    links.new(noise2.outputs["Fac"], mix.inputs["Fac"])
    
    links.new(mix.outputs["Color"], principled.inputs["Base Color"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    # Set roughness
    principled.inputs["Roughness"].default_value = 0.7

    return mat


def build_material_stone(name="StoneMaterial"):
    """Build a procedural stone material."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    noise = nodes.new("ShaderNodeTexNoise")
    colorramp = nodes.new("ShaderNodeValToRGB")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")

    output.location = (400, 0)
    principled.location = (200, 0)
    colorramp.location = (0, 0)
    voronoi.location = (-200, 0)
    noise.location = (-400, 0)
    mapping.location = (-600, 0)
    tex_coord.location = (-800, 0)

    # Stone texture setup
    voronoi.inputs["Scale"].default_value = 15.0
    noise.inputs["Scale"].default_value = 25.0
    noise.inputs["Detail"].default_value = 5.0

    # Gray stone colors
    colorramp.color_ramp.elements[0].color = (0.3, 0.3, 0.3, 1.0)  # Dark gray
    colorramp.color_ramp.elements[1].color = (0.6, 0.6, 0.6, 1.0)  # Light gray

    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], colorramp.inputs["Fac"])
    links.new(noise.outputs["Fac"], colorramp.inputs["Fac"])
    links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    principled.inputs["Roughness"].default_value = 0.9

    return mat


def build_material_metal(name="MetalMaterial"):
    """Build a procedural metal material."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    colorramp = nodes.new("ShaderNodeValToRGB")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")

    output.location = (400, 0)
    principled.location = (200, 0)
    colorramp.location = (0, 0)
    noise.location = (-200, 0)
    mapping.location = (-400, 0)
    tex_coord.location = (-600, 0)

    # Metal texture setup
    noise.inputs["Scale"].default_value = 100.0
    noise.inputs["Detail"].default_value = 10.0

    # Metallic colors (rusty/orange-brown)
    colorramp.color_ramp.elements[0].color = (0.4, 0.25, 0.15, 1.0)  # Rust
    colorramp.color_ramp.elements[1].color = (0.6, 0.5, 0.4, 1.0)  # Light rust

    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], colorramp.inputs["Fac"])
    links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    principled.inputs["Metallic"].default_value = 0.8
    principled.inputs["Roughness"].default_value = 0.3

    return mat


def build_material_from_json(json_path):
    """Build a material from a JSON definition (for AI-generated materials)."""
    with open(json_path, 'r') as f:
        material_def = json.load(f)
    
    mat = bpy.data.materials.new(material_def.get("name", "JSONMaterial"))
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # This is a simplified version - extend based on your JSON schema
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    
    # Add nodes based on JSON definition
    if "noise" in material_def:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = material_def["noise"].get("scale", 10.0)
        colorramp = nodes.new("ShaderNodeValToRGB")
        
        # Set colors from JSON
        if "colors" in material_def:
            colors = material_def["colors"]
            if len(colors) > 0:
                colorramp.color_ramp.elements[0].color = tuple(colors[0] + [1.0])
            if len(colors) > 1:
                colorramp.color_ramp.elements[1].color = tuple(colors[1] + [1.0])
        
        links.new(noise.outputs["Fac"], colorramp.inputs["Fac"])
        links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])
    
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    
    if "roughness" in material_def:
        principled.inputs["Roughness"].default_value = material_def["roughness"]
    if "metallic" in material_def:
        principled.inputs["Metallic"].default_value = material_def["metallic"]
    
    return mat


# Material registry
MATERIAL_BUILDERS = {
    "wood": build_material_wood,
    "stone": build_material_stone,
    "metal": build_material_metal,
    "rusty_metal": build_material_metal,
}


# ------------------------------------------------------------
# Bake texture
# ------------------------------------------------------------
def bake_map(obj, material, map_type, size, output_path, samples=1):
    """
    Bake a specific texture map from a material.
    Returns True on success, False on failure.
    """
    # Ensure object is active and selected
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Create image to bake into
    img_name = f"Bake_{map_type}"
    img = bpy.data.images.new(img_name, width=size, height=size)
    output_path_abs = os.path.abspath(output_path)
    img.filepath_raw = output_path_abs
    img.file_format = "PNG"

    # Set up material for baking
    nodes = material.node_tree.nodes
    
    # Create or find image texture node for baking
    tex_node = None
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image == img:
            tex_node = node
            break
    
    if not tex_node:
        tex_node = nodes.new("ShaderNodeTexImage")
    
    tex_node.image = img
    tex_node.select = True
    nodes.active = tex_node

    # Configure render settings
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False

    # Map type to Blender bake type
    bake_type_map = {
        "baseColor": "DIFFUSE",
        "diffuse": "DIFFUSE",
        "normal": "NORMAL",
        "roughness": "ROUGHNESS",
        "emission": "EMIT",
        "emit": "EMIT",
        "metallic": "ROUGHNESS",  # Metallic is typically baked as roughness in Cycles
        "combined": "COMBINED"
    }
    bake_type = bake_type_map.get(map_type.lower(), "DIFFUSE")

    # Bake
    try:
        bpy.ops.object.bake(type=bake_type)
        # Save with absolute path
        img.save_render(filepath=output_path_abs)
        print(f"Successfully baked {map_type} texture to: {output_path_abs}")
        return True
    except Exception as e:
        print(f"Error during bake of {map_type}: {e}")
        # Try alternative save method
        try:
            img.save()
            print(f"Saved using alternative method to: {output_path_abs}")
            return True
        except Exception as e2:
            print(f"Alternative save also failed: {e2}")
            return False


def bake_texture(material, size, output_path, bake_pass="DIFFUSE", samples=1):
    """Bake a material to a texture image (legacy single-map function)."""
    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "BakePlane"
    
    # Assign material
    if len(plane.data.materials) == 0:
        plane.data.materials.append(material)
    else:
        plane.data.materials[0] = material

    # Map bake_pass to map_type
    map_type_map = {
        "DIFFUSE": "baseColor",
        "ROUGHNESS": "roughness",
        "NORMAL": "normal",
        "EMIT": "emission",
        "COMBINED": "combined"
    }
    map_type = map_type_map.get(bake_pass, "baseColor")

    return bake_map(plane, material, map_type, size, output_path, samples)


def bake_multiple_maps(material, size, output_dir, texture_config, samples=1):
    """
    Bake multiple texture maps based on configuration.
    texture_config: dict with keys like "baseColor", "normal", "roughness", "emission"
    Returns dict of {map_type: success_bool}
    """
    # Create plane once
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "BakePlane"
    
    # Assign material
    if len(plane.data.materials) == 0:
        plane.data.materials.append(material)
    else:
        plane.data.materials[0] = material

    # Ensure output directory exists
    output_dir_abs = os.path.abspath(output_dir)
    if not os.path.exists(output_dir_abs):
        os.makedirs(output_dir_abs)

    results = {}
    
    # Bake each requested texture map
    for map_type, should_bake in texture_config.items():
        if should_bake:
            output_path = os.path.join(output_dir_abs, f"{map_type}.png")
            success = bake_map(plane, material, map_type, size, output_path, samples)
            results[map_type] = success
        else:
            results[map_type] = None  # Skipped

    return results


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    args = parse_args()
    clear_scene()

    # Build or load material
    material = None
    
    # Priority 1: Visual JSON from registry (new method)
    if args.visualJson:
        if HAS_MATERIAL_GENERATOR:
            try:
                visual = json.loads(args.visualJson)
                material = build_material_from_visual(
                    visual, 
                    mat_name="RegistryMaterial", 
                    quality=args.quality,
                    export_node_groups=args.exportNodeGroups
                )
                print(f"Built material from visual JSON (quality: {args.quality}, node groups: {args.exportNodeGroups})")
                
                # Save .blend file if node groups are enabled
                if args.exportNodeGroups:
                    blend_output = args.blendOutput if args.blendOutput else "RegistryMaterial.blend"
                    blend_output_abs = os.path.abspath(blend_output)
                    try:
                        bpy.ops.wm.save_as_mainfile(filepath=blend_output_abs)
                        print(f"Saved material with node groups to: {blend_output_abs}")
                    except Exception as e:
                        print(f"Warning: Could not save .blend file: {e}")
            except Exception as e:
                print(f"Error building material from visual JSON: {e}")
                return
        else:
            print("Error: material_generator.py not available for --visualJson")
            return
    
    # Priority 2: Registry + Asset ID
    elif args.registry and args.assetId:
        if HAS_MATERIAL_GENERATOR:
            try:
                with open(args.registry, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                # Find entry by ID
                entry = None
                for e in registry.get("entries", []):
                    if e.get("id") == args.assetId:
                        entry = e
                        break
                
                if not entry:
                    print(f"Error: Asset ID '{args.assetId}' not found in registry")
                    return
                
                # Build material from visual block
                visual = entry.get("visual", {})
                quality = entry.get("generation", {}).get("quality", args.quality)
                material = build_material_from_visual(
                    visual, 
                    mat_name=args.assetId, 
                    quality=quality,
                    export_node_groups=args.exportNodeGroups
                )
                print(f"Built material from registry entry: {args.assetId} (quality: {quality}, node groups: {args.exportNodeGroups})")
                
                # Save .blend file if node groups are enabled
                if args.exportNodeGroups:
                    blend_output = args.blendOutput if args.blendOutput else os.path.join(
                        os.path.dirname(args.output) if args.output else ".",
                        f"{args.assetId}_material.blend"
                    )
                    blend_output_abs = os.path.abspath(blend_output)
                    try:
                        bpy.ops.wm.save_as_mainfile(filepath=blend_output_abs)
                        print(f"Saved material with node groups to: {blend_output_abs}")
                    except Exception as e:
                        print(f"Warning: Could not save .blend file: {e}")
            except Exception as e:
                print(f"Error loading from registry: {e}")
                return
        else:
            print("Error: material_generator.py not available for --registry")
            return
    
    # Priority 3: JSON material definition
    elif args.json:
        if os.path.exists(args.json):
            material = build_material_from_json(args.json)
        else:
            print(f"Error: JSON file not found: {args.json}")
            return
    
    # Priority 4: Predefined material type
    elif args.material:
        builder = MATERIAL_BUILDERS.get(args.material.lower())
        if builder:
            material = builder()
        else:
            print(f"Error: Unknown material type: {args.material}")
            print(f"Available types: {', '.join(MATERIAL_BUILDERS.keys())}")
            return
    else:
        print("Error: Must specify --material, --json, --visualJson, or --registry+--assetId")
        return

    # Determine texture configuration
    texture_config = {}
    bake_all = (getattr(args, 'pass') == "ALL")
    
    if args.textures:
        # Parse texture config from JSON
        try:
            texture_config = json.loads(args.textures)
        except Exception as e:
            print(f"Error parsing --textures JSON: {e}")
            texture_config = {"baseColor": True}
    elif args.registry and args.assetId:
        # Get texture config from registry entry
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            entry = None
            for e in registry.get("entries", []):
                if e.get("id") == args.assetId:
                    entry = e
                    break
            if entry and "textures" in entry:
                texture_config = entry["textures"]
            else:
                texture_config = {"baseColor": True}
        except Exception as e:
            print(f"Warning: Could not load texture config from registry: {e}")
            texture_config = {"baseColor": True}
    else:
        # Default: just base color
        texture_config = {"baseColor": True}

    # If ALL is requested, bake all available maps
    if bake_all:
        texture_config = {
            "baseColor": True,
            "normal": True,
            "roughness": True,
            "emission": True
        }

    # Multi-map baking
    if args.outputDir or bake_all or len([v for v in texture_config.values() if v]) > 1:
        output_dir = args.outputDir if args.outputDir else os.path.dirname(args.output) if args.output else "."
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        results = bake_multiple_maps(material, args.size, output_dir, texture_config, args.samples)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Baking Summary:")
        print("=" * 60)
        for map_type, result in results.items():
            if result is True:
                print(f"  ✓ {map_type}")
            elif result is False:
                print(f"  ✗ {map_type} (failed)")
            else:
                print(f"  - {map_type} (skipped)")
        print("=" * 60)
        
        # Exit with error if any bake failed
        if any(r is False for r in results.values()):
            sys.exit(1)
    
    # Single-map baking (legacy mode)
    elif args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        success = bake_texture(
            material,
            args.size,
            args.output,
            getattr(args, 'pass'),
            args.samples
        )

        if success:
            print(f"Texture saved to: {args.output}")
        else:
            print(f"Failed to bake texture")
            sys.exit(1)
    else:
        print("Error: Must specify --output or --outputDir")
        sys.exit(1)


if __name__ == "__main__":
    main()

