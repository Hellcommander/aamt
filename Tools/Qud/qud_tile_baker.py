#!/usr/bin/env python3
"""
Caves of Qud Tile Baker
Takes line-based drawings and converts them to Qud-ready tiles with procedural materials.
Fully editable with node groups, registry-driven, and quality-tiered.
"""

import bpy
import sys
import argparse
import os
import json

# ------------------------------------------------------------
# Argument Parsing
# ------------------------------------------------------------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description='Bake line drawing to Qud tile')
    parser.add_argument("--drawing", type=str, required=True, help="Path to line drawing image")
    parser.add_argument("--size", type=int, default=32, choices=[24, 32, 48], help="Tile size (24, 32, or 48)")
    parser.add_argument("--palette", type=str, help="Comma-separated hex colors (e.g., '#4caf50,#81c784,#2e7d32')")
    parser.add_argument("--output", type=str, required=True, help="Output PNG path")
    parser.add_argument("--blendOutput", type=str, help="Output .blend file path (for editable materials)")
    parser.add_argument("--registry", type=str, help="Registry JSON file path")
    parser.add_argument("--assetId", type=str, help="Asset ID from registry")
    parser.add_argument("--visualJson", type=str, help="Visual block JSON")
    parser.add_argument("--generationJson", type=str, help="Generation block JSON")
    parser.add_argument("--quality", type=str, default="standard", choices=["draft", "standard", "high", "ultra"], help="Material quality")
    parser.add_argument("--exportNodeGroups", action="store_true", help="Use node groups for editable materials")
    parser.add_argument("--style", type=str, default="painterly", choices=["painterly", "pixel", "flat", "procedural"], help="Material style")
    parser.add_argument("--contrast", type=str, default="high", choices=["low", "medium", "high"], help="Contrast level")
    
    return parser.parse_args(argv)


# ------------------------------------------------------------
# Utility: Clear Scene
# ------------------------------------------------------------

def clear_scene():
    """Clear all objects, materials, and images from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Clean up orphaned data
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


# ------------------------------------------------------------
# Import Drawing as Mask
# ------------------------------------------------------------

def import_drawing_as_mask(path):
    """
    Import a line drawing as a mask image.
    
    Args:
        path: Path to the drawing image file
    
    Returns:
        Tuple of (plane object, mask image)
    """
    if not os.path.exists(path):
        print(f"Error: Drawing file not found: {path}")
        return None, None
    
    # Load image
    img = bpy.data.images.load(path)
    img.name = "DrawingMask"
    
    # Create plane for reference (optional, can be hidden)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "DrawingPlane"
    
    # Create simple material to display the drawing
    mat = bpy.data.materials.new("DrawingDisplayMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Add nodes
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    
    # Layout
    tex.location = (-200, 0)
    emission.location = (0, 0)
    out.location = (200, 0)
    
    # Connect
    links.new(tex.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    
    # Assign material (optional - for preview)
    plane.data.materials.append(mat)
    
    # Hide from render (we'll use the image directly)
    plane.hide_render = True
    
    return plane, img


# ------------------------------------------------------------
# Build Procedural Material with Mask
# ------------------------------------------------------------

def hex_to_rgb(hex_str):
    """Convert '#RRGGBB' to linear RGB (0-1)."""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return (r, g, b)


def build_procedural_material_with_mask(mask_img, palette_hex, style="painterly", contrast="high", quality="standard", use_node_groups=False):
    """
    Build a procedural material using the drawing as a mask.
    
    Args:
        mask_img: Blender image object (the drawing)
        palette_hex: Comma-separated hex colors
        style: Material style ("painterly", "pixel", "flat", "procedural")
        contrast: Contrast level ("low", "medium", "high")
        quality: Quality tier ("draft", "standard", "high", "ultra")
        use_node_groups: Whether to use node groups for editability
    
    Returns:
        Blender material
    """
    # Parse palette
    palette = [c.strip() for c in palette_hex.split(",")]
    if not palette:
        palette = ["#ffffff", "#000000"]  # Default
    
    # Try to use material generator if available
    try:
        from material_generator import build_material_from_visual, build_palette_ramp_group
        
        # Create visual block from palette
        visual_block = {
            "icon": {
                "palette": palette,
                "style": style,
                "contrast": contrast,
                "size": 32  # Qud tile size
            }
        }
        
        # Build material
        mat = build_material_from_visual(
            visual_block,
            mat_name="QudTileMaterial",
            quality=quality,
            export_node_groups=use_node_groups
        )
        
        # Enhance with mask if node groups not used
        if not use_node_groups:
            # Add mask to drive the material
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            
            # Find the base color input
            principled = None
            for node in nodes:
                if node.type == "BSDF_PRINCIPLED":
                    principled = node
                    break
            
            if principled and principled.inputs["Base Color"].is_linked:
                # Add mask texture node
                mask_tex = nodes.new("ShaderNodeTexImage")
                mask_tex.image = mask_img
                mask_tex.location = (-800, 0)
                
                # Find the color source
                color_source = principled.inputs["Base Color"].links[0].from_node
                
                # Mix mask with color
                mix = nodes.new("ShaderNodeMixRGB")
                mix.location = (-200, 0)
                mix.blend_type = "MULTIPLY"
                mix.inputs["Fac"].default_value = 1.0
                
                # Connect: mask → mix → color source → principled
                links.new(mask_tex.outputs["Alpha"], mix.inputs["Fac"])
                links.new(color_source.outputs["Color"], mix.inputs["Color1"])
                mix.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1.0)  # Black for masked areas
                
                # Disconnect old link
                old_link = principled.inputs["Base Color"].links[0]
                links.remove(old_link)
                
                # Connect new chain
                links.new(mix.outputs["Color"], principled.inputs["Base Color"])
        
        return mat
    
    except ImportError:
        # Fallback: Build simple material without material_generator
        print("Warning: material_generator.py not found, using fallback material builder")
        return build_simple_material_with_mask(mask_img, palette, style, contrast)


def build_simple_material_with_mask(mask_img, palette, style="painterly", contrast="high"):
    """
    Fallback: Build a simple procedural material with mask.
    """
    mat = bpy.data.materials.new("QudTileMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    out = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    mask_tex = nodes.new("ShaderNodeTexImage")
    colorramp = nodes.new("ShaderNodeValToRGB")
    noise = nodes.new("ShaderNodeTexNoise")
    
    mask_tex.image = mask_img
    
    # Layout
    mask_tex.location = (-600, 0)
    noise.location = (-600, -200)
    colorramp.location = (-300, 0)
    principled.location = (0, 0)
    out.location = (300, 0)
    
    # Set up palette in color ramp
    while len(colorramp.color_ramp.elements) < len(palette):
        colorramp.color_ramp.elements.new(0.5)
    
    for i, hex_color in enumerate(palette):
        elem = colorramp.color_ramp.elements[i]
        rgb = hex_to_rgb(hex_color)
        elem.color = (*rgb, 1.0)
        elem.position = i / max(1, len(palette) - 1)
    
    # Connect nodes
    # Use mask alpha to drive color ramp
    links.new(mask_tex.outputs["Alpha"], colorramp.inputs["Fac"])
    links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(principled.outputs["BSDF"], out.inputs["Surface"])
    
    # Add noise for detail (optional)
    if style == "painterly":
        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-100, 0)
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.3
        
        links.new(noise.outputs["Fac"], mix.inputs["Color1"])
        links.new(colorramp.outputs["Color"], mix.inputs["Color2"])
        
        # Disconnect old link
        old_link = principled.inputs["Base Color"].links[0]
        links.remove(old_link)
        
        # Connect new chain
        links.new(mix.outputs["Color"], principled.inputs["Base Color"])
    
    return mat


# ------------------------------------------------------------
# Bake Tile
# ------------------------------------------------------------

def bake_tile(material, size, output_path):
    """
    Bake a material to Qud tile size.
    
    Args:
        material: Blender material to bake
        size: Tile size in pixels (24, 32, or 48)
        output_path: Output PNG path
    
    Returns:
        True if successful, False otherwise
    """
    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "BakePlane"
    
    # Assign material
    if len(plane.data.materials) == 0:
        plane.data.materials.append(material)
    else:
        plane.data.materials[0] = material
    
    # Ensure plane is active
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    
    # Create image for baking
    img = bpy.data.images.new("QudTileBake", width=size, height=size)
    output_path_abs = os.path.abspath(output_path)
    img.filepath_raw = output_path_abs
    img.file_format = "PNG"
    
    # Set up material for baking
    nodes = material.node_tree.nodes
    tex_node = None
    
    # Find or create image texture node
    for node in nodes:
        if node.type == 'TEX_IMAGE':
            tex_node = node
            break
    
    if not tex_node:
        tex_node = nodes.new("ShaderNodeTexImage")
    
    tex_node.image = img
    tex_node.select = True
    nodes.active = tex_node
    
    # Configure render settings
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 1
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    
    # Bake
    try:
        bpy.ops.object.bake(type="DIFFUSE")
        img.save_render(filepath=output_path_abs)
        print(f"Baked Qud tile: {output_path_abs} ({size}x{size})")
        return True
    except Exception as e:
        print(f"Error during bake: {e}")
        try:
            img.save()
            print(f"Saved using alternative method: {output_path_abs}")
            return True
        except Exception as e2:
            print(f"Alternative save also failed: {e2}")
            return False


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    """Main entry point."""
    args = parse_args()
    clear_scene()
    
    print("=" * 60)
    print("Qud Tile Baker - Drawing to Tile Pipeline")
    print("=" * 60)
    print()
    
    # Load palette and settings from registry if provided
    palette = args.palette
    style = args.style
    contrast = args.contrast
    quality = args.quality
    use_node_groups = args.exportNodeGroups
    
    if args.registry and args.assetId:
        # Load from registry
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            entry = None
            for e in registry.get("entries", []):
                if e.get("id") == args.assetId:
                    entry = e
                    break
            
            if entry:
                visual = entry.get("visual", {})
                icon_data = visual.get("icon", {})
                
                # Get palette
                if icon_data.get("palette"):
                    palette = ",".join(icon_data["palette"])
                elif not palette:
                    palette = "#ffffff,#000000"
                
                # Get style
                style = icon_data.get("style", style)
                contrast = icon_data.get("contrast", contrast)
                
                # Get quality
                generation = entry.get("generation", {})
                quality = generation.get("quality", quality)
                use_node_groups = generation.get("exportNodeGroups", use_node_groups)
                
                print(f"Loaded from registry: {args.assetId}")
        except Exception as e:
            print(f"Warning: Could not load registry: {e}")
    
    elif args.visualJson:
        # Load from JSON
        try:
            visual = json.loads(args.visualJson)
            icon_data = visual.get("icon", {})
            
            if icon_data.get("palette"):
                palette = ",".join(icon_data["palette"])
            
            style = icon_data.get("style", style)
            contrast = icon_data.get("contrast", contrast)
            
            if args.generationJson:
                generation = json.loads(args.generationJson)
                quality = generation.get("quality", quality)
                use_node_groups = generation.get("exportNodeGroups", use_node_groups)
        except Exception as e:
            print(f"Warning: Could not parse JSON: {e}")
    
    # Default palette if still not set
    if not palette:
        palette = "#ffffff,#000000"
    
    print(f"Drawing: {args.drawing}")
    print(f"Size: {args.size}x{args.size}")
    print(f"Palette: {palette}")
    print(f"Style: {style}")
    print(f"Quality: {quality}")
    print(f"Node Groups: {use_node_groups}")
    print()
    
    # 1. Import drawing as mask
    print("Step 1: Importing drawing as mask...")
    plane, mask_img = import_drawing_as_mask(args.drawing)
    if not mask_img:
        print("Error: Failed to import drawing")
        sys.exit(1)
    print(f"  ✓ Loaded: {mask_img.size[0]}x{mask_img.size[1]}")
    print()
    
    # 2. Build procedural material
    print("Step 2: Building procedural material...")
    material = build_procedural_material_with_mask(
        mask_img,
        palette,
        style=style,
        contrast=contrast,
        quality=quality,
        use_node_groups=use_node_groups
    )
    print(f"  ✓ Material created: {material.name}")
    print()
    
    # 3. Bake tile
    print("Step 3: Baking tile...")
    success = bake_tile(material, args.size, args.output)
    if not success:
        print("Error: Failed to bake tile")
        sys.exit(1)
    print()
    
    # 4. Save .blend file if requested
    if args.blendOutput:
        print("Step 4: Saving .blend file...")
        blend_path_abs = os.path.abspath(args.blendOutput)
        try:
            bpy.ops.wm.save_as_mainfile(filepath=blend_path_abs)
            print(f"  ✓ Saved: {blend_path_abs}")
        except Exception as e:
            print(f"  Warning: Could not save .blend file: {e}")
        print()
    
    print("=" * 60)
    print("Qud Tile Bake Complete!")
    print("=" * 60)
    print(f"Output: {args.output}")
    if args.blendOutput:
        print(f"Blend: {args.blendOutput}")
    print()


if __name__ == "__main__":
    main()

