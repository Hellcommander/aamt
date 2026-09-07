#!/usr/bin/env python3
"""
Caves of Qud Tile Exporter
Exports assets as individual PNG tiles in Qud's format (32x32, 24x24, or 48x48).
No atlas required - each tile is a standalone PNG file.
"""

import bpy
import os
import sys
import json
import argparse

# ------------------------------------------------------------
# Qud Tile Sizes
# ------------------------------------------------------------

QUD_TILE_SIZES = {
    "default": 32,
    "classic": 24,
    "highres": 48
}

# ------------------------------------------------------------
# Tile Baking
# ------------------------------------------------------------

def bake_tile_to_qud_size(material, size=32, output_path=None, tile_name="tile"):
    """
    Bake a material to Qud tile size (32x32, 24x24, or 48x48).
    
    Args:
        material: Blender material to bake
        size: Tile size in pixels (32, 24, or 48)
        output_path: Output directory for tile PNG
        tile_name: Base name for the tile file
    
    Returns:
        Path to the generated tile PNG
    """
    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "TilePlane"
    
    # Assign material
    if len(plane.data.materials) == 0:
        plane.data.materials.append(material)
    else:
        plane.data.materials[0] = material
    
    # Ensure plane is active
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    
    # Create image for baking
    img = bpy.data.images.new("QudTile", width=size, height=size)
    
    # Set up output path
    if not output_path:
        output_path = os.path.join(os.getcwd(), f"{tile_name}.png")
    else:
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        output_path = os.path.join(output_path, f"{tile_name}.png")
    
    output_path_abs = os.path.abspath(output_path)
    img.filepath_raw = output_path_abs
    img.file_format = "PNG"
    
    # Set up material for baking
    nodes = material.node_tree.nodes
    tex_node = None
    
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
        return output_path_abs
    except Exception as e:
        print(f"Error baking tile: {e}")
        try:
            img.save()
            return output_path_abs
        except Exception as e2:
            print(f"Alternative save also failed: {e2}")
            return None


def bake_animation_frames(material, num_frames=4, size=32, output_dir=None, tile_name="tile"):
    """
    Bake animation frames for Qud tile.
    
    Args:
        material: Blender material to bake
        num_frames: Number of animation frames
        size: Tile size in pixels
        output_dir: Output directory for frames
        tile_name: Base name for tile files
    
    Returns:
        List of paths to generated frame PNGs
    """
    if not output_dir:
        output_dir = os.getcwd()
    
    os.makedirs(output_dir, exist_ok=True)
    
    frame_paths = []
    
    # For now, bake same material multiple times
    # In full implementation, you'd animate the material between frames
    for i in range(num_frames):
        frame_name = f"{tile_name}_frame{i:02d}"
        frame_path = bake_tile_to_qud_size(
            material,
            size=size,
            output_path=output_dir,
            tile_name=frame_name
        )
        if frame_path:
            frame_paths.append(frame_path)
    
    return frame_paths


def create_horizontal_strip(frames, output_path, tile_name="tile", size=32):
    """
    Create a horizontal strip from individual frame tiles.
    
    Args:
        frames: List of frame image paths
        output_path: Output directory
        tile_name: Base name for strip file
        size: Tile size in pixels
    
    Returns:
        Path to the generated strip PNG
    """
    from PIL import Image
    os.makedirs(output_path, exist_ok=True)
    strip_path = os.path.join(output_path, f"{tile_name}_strip.png")
    images = []
    for fp in frames:
        if not fp or not os.path.exists(fp):
            continue
        im = Image.open(fp).convert("RGBA")
        if im.size != (size, size):
            im = im.resize((size, size), Image.Resampling.NEAREST)
        images.append(im)
    if not images:
        Image.new("RGBA", (size, size), (0, 0, 0, 0)).save(strip_path)
        print(f"Horizontal strip (empty) saved: {strip_path}")
        return strip_path
    strip = Image.new("RGBA", (size * len(images), size), (0, 0, 0, 0))
    for i, im in enumerate(images):
        strip.paste(im, (i * size, 0))
    strip.save(strip_path)
    print(f"Horizontal strip saved: {strip_path} ({len(images)} frames)")
    return strip_path


# ------------------------------------------------------------
# Qud Mod Metadata Generation
# ------------------------------------------------------------

def generate_qud_tile_xml(tile_name, tile_path, frame_count=1, animated=False):
    """
    Generate Qud mod XML for a tile.
    
    Args:
        tile_name: Name of the tile
        tile_path: Path to tile PNG (relative to mod root)
        frame_count: Number of frames (for animation)
        animated: Whether tile is animated
    
    Returns:
        XML string
    """
    if animated and frame_count > 1:
        # Animated tile
        xml = f'''<Tile Name="{tile_name}" Animated="true" Frames="{frame_count}">
    <Frame Index="0" Path="{tile_path}_frame00.png" />
'''
        for i in range(1, frame_count):
            xml += f'    <Frame Index="{i}" Path="{tile_path}_frame{i:02d}.png" />\n'
        xml += '</Tile>'
    else:
        # Static tile
        xml = f'<Tile Name="{tile_name}" Path="{tile_path}.png" />'
    
    return xml


def generate_qud_tile_json(tile_name, tile_path, frame_count=1, animated=False):
    """
    Generate Qud mod JSON for a tile.
    
    Args:
        tile_name: Name of the tile
        tile_path: Path to tile PNG (relative to mod root)
        frame_count: Number of frames (for animation)
        animated: Whether tile is animated
    
    Returns:
        JSON string
    """
    if animated and frame_count > 1:
        frames = []
        for i in range(frame_count):
            frames.append({
                "index": i,
                "path": f"{tile_path}_frame{i:02d}.png"
            })
        tile_data = {
            "tile": {
                "name": tile_name,
                "animated": True,
                "frames": frames
            }
        }
    else:
        tile_data = {
            "tile": {
                "name": tile_name,
                "path": f"{tile_path}.png"
            }
        }
    
    return json.dumps(tile_data, indent=2)


# ------------------------------------------------------------
# Complete Qud Tile Export Pipeline
# ------------------------------------------------------------

def export_to_qud_tile(
    material,
    tile_name,
    output_dir,
    size=32,
    animated=False,
    frame_count=1,
    generate_metadata=True,
    metadata_format="xml"
):
    """
    Complete pipeline: Material → Qud Tile → Metadata
    
    Args:
        material: Blender material
        tile_name: Name for the tile
        output_dir: Output directory
        size: Tile size (32, 24, or 48)
        animated: Whether to generate animation frames
        frame_count: Number of frames if animated
        generate_metadata: Whether to generate mod metadata
        metadata_format: "xml" or "json"
    
    Returns:
        Dictionary with export results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "tile_name": tile_name,
        "size": size,
        "tiles": [],
        "metadata": None
    }
    
    # Bake tile(s)
    if animated and frame_count > 1:
        print(f"Baking {frame_count} animation frames...")
        frame_paths = bake_animation_frames(
            material,
            num_frames=frame_count,
            size=size,
            output_dir=output_dir,
            tile_name=tile_name
        )
        results["tiles"] = frame_paths
    else:
        print("Baking static tile...")
        tile_path = bake_tile_to_qud_size(
            material,
            size=size,
            output_path=output_dir,
            tile_name=tile_name
        )
        if tile_path:
            results["tiles"] = [tile_path]
    
    # Generate metadata
    if generate_metadata:
        print("Generating Qud mod metadata...")
        tile_path_rel = f"assets/textures/tiles/{tile_name}"
        
        if metadata_format == "xml":
            metadata = generate_qud_tile_xml(
                tile_name,
                tile_path_rel,
                frame_count=frame_count,
                animated=animated
            )
            metadata_path = os.path.join(output_dir, f"{tile_name}.xml")
        else:
            metadata = generate_qud_tile_json(
                tile_name,
                tile_path_rel,
                frame_count=frame_count,
                animated=animated
            )
            metadata_path = os.path.join(output_dir, f"{tile_name}.json")
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(metadata)
        
        results["metadata"] = metadata_path
        print(f"Metadata saved to: {metadata_path}")
    
    return results


# ------------------------------------------------------------
# CLI Interface
# ------------------------------------------------------------

def parse_args():
    """Parse command-line arguments."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    parser = argparse.ArgumentParser(description='Export material as Qud tile')
    parser.add_argument("--material", type=str, help="Material name (must exist in Blender)")
    parser.add_argument("--registry", type=str, help="Registry JSON file path")
    parser.add_argument("--assetId", type=str, help="Asset ID from registry")
    parser.add_argument("--visualJson", type=str, help="Visual block JSON")
    parser.add_argument("--generationJson", type=str, help="Generation block JSON")
    parser.add_argument("--tileName", type=str, help="Name for the tile (defaults to assetId)")
    parser.add_argument("--outputDir", type=str, required=True, help="Output directory")
    parser.add_argument("--size", type=int, default=32, choices=[24, 32, 48], help="Tile size (24, 32, or 48)")
    parser.add_argument("--animated", action="store_true", help="Generate animation frames")
    parser.add_argument("--frameCount", type=int, default=4, help="Number of frames if animated")
    parser.add_argument("--metadataFormat", type=str, default="xml", choices=["xml", "json"], help="Metadata format")
    parser.add_argument("--noMetadata", action="store_true", help="Skip metadata generation")
    parser.add_argument("--quality", type=str, default="standard", choices=["draft", "standard", "high", "ultra"], help="Material quality")
    parser.add_argument("--exportNodeGroups", action="store_true", help="Use node groups for materials")
    
    return parser.parse_args(argv)


def main():
    """Main entry point."""
    args = parse_args()
    
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    material = None
    tile_name = args.tileName
    
    # Generate material from registry if provided
    if args.registry and args.assetId:
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            entry = None
            for e in registry.get("entries", []):
                if e.get("id") == args.assetId:
                    entry = e
                    break
            
            if not entry:
                print(f"Error: Asset ID '{args.assetId}' not found in registry")
                sys.exit(1)
            
            # Get tile name from asset ID if not provided
            if not tile_name:
                tile_name = args.assetId.replace('-', '_').replace(' ', '_')
            
            # Get visual and generation blocks
            visual_block = entry.get("visual", {})
            generation_block = entry.get("generation", {})
            
            # Get quality
            quality = generation_block.get("quality", args.quality)
            export_node_groups = generation_block.get("exportNodeGroups", args.exportNodeGroups)
            
            # Build material
            try:
                from material_generator import build_material_from_visual
                material = build_material_from_visual(
                    visual_block,
                    mat_name=f"{tile_name}_Material",
                    quality=quality,
                    export_node_groups=export_node_groups
                )
                print(f"Built material from registry entry: {args.assetId}")
            except ImportError:
                print("Error: material_generator.py not found")
                sys.exit(1)
            except Exception as e:
                print(f"Error building material: {e}")
                sys.exit(1)
        
        except Exception as e:
            print(f"Error loading registry: {e}")
            sys.exit(1)
    
    # Or use visual/generation JSON directly
    elif args.visualJson:
        try:
            visual_block = json.loads(args.visualJson)
            generation_block = json.loads(args.generationJson) if args.generationJson else {}
            
            if not tile_name:
                tile_name = "qud_tile"
            
            quality = generation_block.get("quality", args.quality)
            export_node_groups = generation_block.get("exportNodeGroups", args.exportNodeGroups)
            
            try:
                from material_generator import build_material_from_visual
                material = build_material_from_visual(
                    visual_block,
                    mat_name=f"{tile_name}_Material",
                    quality=quality,
                    export_node_groups=export_node_groups
                )
                print(f"Built material from visual JSON")
            except ImportError:
                print("Error: material_generator.py not found")
                sys.exit(1)
            except Exception as e:
                print(f"Error building material: {e}")
                sys.exit(1)
        
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            sys.exit(1)
    
    # Or find existing material
    elif args.material:
        material = bpy.data.materials.get(args.material)
        if not material:
            print(f"Error: Material '{args.material}' not found")
            sys.exit(1)
        if not tile_name:
            tile_name = args.material
    else:
        # Use first material in scene
        materials = [mat for mat in bpy.data.materials if mat.use_nodes]
        if not materials:
            print("Error: No materials found in scene")
            sys.exit(1)
        material = materials[0]
        if not tile_name:
            tile_name = material.name
        print(f"Using material: {material.name}")
    
    if not material:
        print("Error: No material available")
        sys.exit(1)
    
    # Export to Qud tile
    results = export_to_qud_tile(
        material=material,
        tile_name=tile_name,
        output_dir=args.outputDir,
        size=args.size,
        animated=args.animated,
        frame_count=args.frameCount,
        generate_metadata=not args.noMetadata,
        metadata_format=args.metadataFormat
    )
    
    print()
    print("=" * 60)
    print("Qud Tile Export Complete!")
    print("=" * 60)
    print(f"Tile: {results['tile_name']}")
    print(f"Size: {results['size']}x{results['size']}")
    print(f"Tiles generated: {len(results['tiles'])}")
    if results['metadata']:
        print(f"Metadata: {results['metadata']}")
    print()


if __name__ == "__main__":
    main()

