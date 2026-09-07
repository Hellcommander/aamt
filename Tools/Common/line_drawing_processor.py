#!/usr/bin/env python3
"""
Line Drawing Processor (experimental Blender helper)

Role: preprocess a line drawing and convert it to a mesh via sketch_to_mesh.
Full OpenCV/NetworkX skeletonization is not required for the pipeline to work —
PIL thresholding + silhouette extrusion fills the role. Advanced skeleton fields
are best-effort when pixel samples are available.
"""

import bpy
import os
import sys
import json
import bmesh
from mathutils import Vector

# ------------------------------------------------------------
# Image Preprocessing
# ------------------------------------------------------------

def preprocess_line_drawing(image_path, threshold=0.5, stroke_unify=True):
    """
    Preprocess a line drawing: convert to pure black/white, clean edges.
    Returns a Blender image datablock (and writes a cleaned sidecar when PIL works).
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return None

    cleaned_path = image_path
    try:
        from PIL import Image, ImageFilter, ImageOps
        im = Image.open(image_path).convert("L")
        bw = im.point(lambda p: 255 if p < int(threshold * 255) else 0)
        if stroke_unify:
            bw = bw.filter(ImageFilter.MinFilter(3))
            bw = bw.filter(ImageFilter.MaxFilter(3))
        cleaned_path = os.path.splitext(image_path)[0] + "_bw.png"
        ImageOps.invert(bw).save(cleaned_path)  # white lines on black for silhouette tools
        print(f"Wrote cleaned line drawing: {cleaned_path}")
    except Exception as e:
        print(f"PIL preprocess skipped ({e}); using original image")

    image = bpy.data.images.load(cleaned_path)
    print(f"Loaded line drawing: {cleaned_path}")
    print(f"  Size: {image.size[0]}x{image.size[1]}")
    return image


def extract_line_structure(image_path, method="skeleton"):
    """
    Extract coarse structure from dark ink pixels (PIL). Enough for color mapping
    and diagnostics; mesh build still uses sketch_to_mesh silhouette extrusion.
    """
    structure = {
        "method": method,
        "lines": [],
        "regions": [],
        "outline": [],
        "intersections": [],
        "endpoints": [],
    }
    print(f"Extracting structure using method: {method}")
    try:
        from PIL import Image
        im = Image.open(image_path).convert("L")
        w, h = im.size
        pix = im.load()
        # Sample dark pixels as endpoints / outline points (grid subsample)
        step = max(1, min(w, h) // 32)
        dark = []
        for y in range(0, h, step):
            for x in range(0, w, step):
                if pix[x, y] < 128:
                    dark.append({"x": x / max(1, w), "y": 1.0 - (y / max(1, h)), "u": x, "v": y})
        structure["endpoints"] = dark[:256]
        structure["outline"] = dark[:128]
        # Pair sequential samples into crude segments for color mapping
        for i in range(0, min(len(dark) - 1, 64), 2):
            structure["lines"].append({
                "id": i // 2,
                "start": dark[i],
                "end": dark[i + 1],
                "length": abs(dark[i]["u"] - dark[i + 1]["u"]) + abs(dark[i]["v"] - dark[i + 1]["v"]),
            })
        # Bounding box as one region
        if dark:
            xs = [d["u"] for d in dark]
            ys = [d["v"] for d in dark]
            structure["regions"].append({
                "id": 0,
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "vertices": [
                    [min(xs) / w, 1 - min(ys) / h],
                    [max(xs) / w, 1 - min(ys) / h],
                    [max(xs) / w, 1 - max(ys) / h],
                    [min(xs) / w, 1 - max(ys) / h],
                ],
            })
        print(f"  Found {len(structure['lines'])} segments, {len(structure['endpoints'])} sample points")
    except Exception as e:
        print(f"  Structure extract fallback ({e})")
    return structure


# ------------------------------------------------------------
# Line-to-Mesh Conversion
# ------------------------------------------------------------

def lines_to_curve(lines_data, name="LineCurve"):
    """
    Convert line data to Blender curve.
    
    Args:
        lines_data: List of line segments (each with start/end points)
        name: Name for the curve object
    
    Returns:
        Blender curve object
    """
    # Create curve
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '2D'
    curve_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    # Add splines for each line
    for line in lines_data:
        spline = curve_data.splines.new('POLY')
        spline.points.add(1)
        spline.points[0].co = (*line['start'], 0, 1)
        spline.points[1].co = (*line['end'], 0, 1)
    
    return curve_obj


def curve_to_mesh(curve_obj, extrude_depth=0.1, bevel_amount=0.01):
    """
    Convert curve to mesh by extruding.
    
    Args:
        curve_obj: Blender curve object
        extrude_depth: Extrusion depth
        bevel_amount: Bevel amount
    
    Returns:
        Mesh object
    """
    # Select curve
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)
    
    # Convert to mesh
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Extrude
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={
            "value": (0, 0, extrude_depth),
            "constraint_axis": (False, False, True)
        }
    )
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Add bevel modifier
    bevel = mesh_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.amount = bevel_amount
    bevel.segments = 2
    
    return mesh_obj


def create_region_meshes(regions_data, name_prefix="Region"):
    """
    Create separate meshes for each closed region.
    
    Args:
        regions_data: List of closed region polygons
        name_prefix: Prefix for mesh names
    
    Returns:
        List of mesh objects
    """
    mesh_objects = []
    
    for i, region in enumerate(regions_data):
        # Create mesh from region polygon
        mesh_data = bpy.data.meshes.new(f"{name_prefix}_{i}")
        mesh_obj = bpy.data.objects.new(f"{name_prefix}_{i}", mesh_data)
        bpy.context.collection.objects.link(mesh_obj)
        
        # Create vertices and faces from region
        vertices = [Vector((v[0], v[1], 0)) for v in region['vertices']]
        faces = [list(range(len(vertices)))]  # Single face
        
        mesh_data.from_pydata(vertices, [], faces)
        mesh_data.update()
        
        mesh_objects.append(mesh_obj)
    
    return mesh_objects


# ------------------------------------------------------------
# Line-to-Color Mapping
# ------------------------------------------------------------

def map_lines_to_colors(lines_data, palette, mapping_strategy="hierarchical"):
    """
    Map line segments to palette colors based on structure.
    
    Strategies:
    - "hierarchical": Outer lines → dark, inner → mid, intersections → light
    - "distance": Based on distance from center
    - "thickness": Based on line thickness
    - "region": Based on which region the line belongs to
    
    Args:
        lines_data: List of line segments
        palette: List of hex color strings
        mapping_strategy: Color mapping strategy
    
    Returns:
        Dictionary mapping line IDs to colors
    """
    color_map = {}
    
    print(f"Mapping lines to colors using strategy: {mapping_strategy}")
    
    # Hierarchical mapping (default)
    if mapping_strategy == "hierarchical":
        # Sort lines by distance from center (outer = darker)
        center = Vector((0.5, 0.5, 0))
        lines_with_dist = []
        
        for i, line in enumerate(lines_data):
            mid_point = Vector((line['start'][0] + line['end'][0], 
                               line['start'][1] + line['end'][1], 0)) / 2
            dist = (mid_point - center).length
            lines_with_dist.append((i, dist, line))
        
        # Sort by distance (outer first)
        lines_with_dist.sort(key=lambda x: x[1], reverse=True)
        
        # Map to palette
        num_colors = len(palette)
        for idx, (line_idx, dist, line) in enumerate(lines_with_dist):
            color_idx = min(int((idx / len(lines_with_dist)) * num_colors), num_colors - 1)
            color_map[line_idx] = palette[color_idx]
    
    # Distance-based mapping
    elif mapping_strategy == "distance":
        center = Vector((0.5, 0.5, 0))
        max_dist = 0
        
        # Find max distance
        for line in lines_data:
            mid_point = Vector((line['start'][0] + line['end'][0], 
                               line['start'][1] + line['end'][1], 0)) / 2
            dist = (mid_point - center).length
            max_dist = max(max_dist, dist)
        
        # Map based on distance
        for i, line in enumerate(lines_data):
            mid_point = Vector((line['start'][0] + line['end'][0], 
                               line['start'][1] + line['end'][1], 0)) / 2
            dist = (mid_point - center).length
            color_idx = int((dist / max_dist) * (len(palette) - 1))
            color_map[i] = palette[color_idx]
    
    # Region-based mapping
    elif mapping_strategy == "region":
        # Map each region to a color
        for i, line in enumerate(lines_data):
            region_id = line.get('region_id', 0)
            color_idx = region_id % len(palette)
            color_map[i] = palette[color_idx]
    
    return color_map


def create_material_from_line_mapping(mesh_obj, color_map, palette, base_material=None):
    """
    Create or modify material based on line color mapping.
    
    Args:
        mesh_obj: Mesh object to apply material to
        color_map: Dictionary mapping line/region IDs to colors
        palette: Full palette for fallback
        base_material: Base material to modify (optional)
    
    Returns:
        Material object
    """
    # Create material
    if base_material:
        mat = base_material.copy()
        mat.name = f"{base_material.name}_LineMapped"
    else:
        mat = bpy.data.materials.new("LineMappedMaterial")
        mat.use_nodes = True
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear existing nodes if new material
    if not base_material:
        nodes.clear()
    
    # Create color ramp based on mapping
    colorramp = nodes.new("ShaderNodeValToRGB")
    colorramp.location = (0, 0)
    
    # Set up color ramp with mapped colors
    # This is simplified - full implementation would create
    # a more complex node setup based on the color map
    
    # Assign material
    if len(mesh_obj.data.materials) == 0:
        mesh_obj.data.materials.append(mat)
    else:
        mesh_obj.data.materials[0] = mat
    
    return mat


# ------------------------------------------------------------
# Complete Pipeline
# ------------------------------------------------------------

def process_line_drawing_to_asset(
    image_path,
    visual_block,
    generation_block,
    output_path=None,
    mapping_strategy="hierarchical"
):
    """
    Complete pipeline: Line drawing → Structure → Mesh → Material → Asset
    
    Args:
        image_path: Path to line drawing image
        visual_block: Visual specification from registry
        generation_block: Generation specification from registry
        output_path: Optional path to save .blend file
        mapping_strategy: Color mapping strategy
    
    Returns:
        Dictionary with created objects and materials
    """
    print("=" * 60)
    print("Processing Line Drawing to Asset")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Strategy: {mapping_strategy}")
    print()
    
    # 1. Preprocess image
    print("Step 1: Preprocessing line drawing...")
    image = preprocess_line_drawing(image_path)
    if not image:
        return None
    
    # 2. Extract structure
    print("Step 2: Extracting line structure...")
    structure = extract_line_structure(image_path, method="skeleton")
    
    # 3. Get palette from visual block
    palette = visual_block.get("icon", {}).get("palette", ["#ffffff", "#000000"])
    print(f"Step 3: Using palette: {palette}")
    
    # 4. Map lines to colors
    print("Step 4: Mapping lines to colors...")
    if structure.get("lines"):
        color_map = map_lines_to_colors(structure["lines"], palette, mapping_strategy)
    else:
        # Fallback: use image as mask
        color_map = {}
        print("  Using image as mask (no line structure extracted)")
    
    # 5. Create mesh from structure via sketch_to_mesh (role-filling path)
    print("Step 5: Creating mesh from structure via sketch_to_mesh...")
    extrude_depth = generation_block.get("extrudeDepth", 0.1)
    bevel_amount = generation_block.get("bevelAmount", 0.01)
    
    from sketch_to_mesh import process_sketch
    
    use_as = generation_block.get("useSketchAs", "silhouette")
    # Prefer cleaned BW sidecar from preprocess when present
    mesh_src = image_path
    bw_sidecar = os.path.splitext(image_path)[0] + "_bw.png"
    if os.path.exists(bw_sidecar):
        mesh_src = bw_sidecar
    mesh_obj = process_sketch(
        mesh_src,
        use_as=use_as,
        extrude_depth=extrude_depth,
        bevel_amount=bevel_amount
    )
    
    if not mesh_obj:
        print("Error: Failed to create mesh")
        return None
    
    # 6. Apply procedural material
    print("Step 6: Applying procedural material...")
    from material_generator import build_material_from_visual
    
    quality = generation_block.get("quality", "standard")
    export_node_groups = generation_block.get("exportNodeGroups", False)
    
    base_material = build_material_from_visual(
        visual_block,
        mat_name=f"{mesh_obj.name}_Material",
        quality=quality,
        export_node_groups=export_node_groups
    )
    
    # 7. Enhance material with line mapping
    if color_map:
        print("Step 7: Enhancing material with line color mapping...")
        material = create_material_from_line_mapping(
            mesh_obj,
            color_map,
            palette,
            base_material=base_material
        )
    else:
        material = base_material
    
    # 8. Save .blend file
    if output_path:
        output_path_abs = os.path.abspath(output_path)
        try:
            bpy.ops.wm.save_as_mainfile(filepath=output_path_abs)
            print(f"Step 8: Saved to: {output_path_abs}")
        except Exception as e:
            print(f"Warning: Could not save .blend file: {e}")
    
    print()
    print("=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    
    return {
        "mesh": mesh_obj,
        "material": material,
        "structure": structure,
        "color_map": color_map
    }


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
    
    import argparse
    parser = argparse.ArgumentParser(description='Process line drawing to asset')
    parser.add_argument("--lineDrawing", type=str, required=True, help="Path to line drawing image")
    parser.add_argument("--visualJson", type=str, help="Visual block JSON")
    parser.add_argument("--generationJson", type=str, help="Generation block JSON")
    parser.add_argument("--registry", type=str, help="Registry JSON file path")
    parser.add_argument("--assetId", type=str, help="Asset ID from registry")
    parser.add_argument("--output", type=str, help="Output .blend file path")
    parser.add_argument("--mappingStrategy", type=str, default="hierarchical",
                       choices=["hierarchical", "distance", "region", "thickness"],
                       help="Color mapping strategy")
    
    return parser.parse_args(argv)


def main():
    """Main entry point."""
    args = parse_args()
    
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Load visual and generation blocks
    visual_block = {}
    generation_block = {}
    
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
            
            if not entry:
                print(f"Error: Asset ID '{args.assetId}' not found in registry")
                return
            
            visual_block = entry.get("visual", {})
            generation_block = entry.get("generation", {})
        except Exception as e:
            print(f"Error loading registry: {e}")
            return
    else:
        # Load from JSON strings
        if args.visualJson:
            visual_block = json.loads(args.visualJson)
        if args.generationJson:
            generation_block = json.loads(args.generationJson)
    
    # Process line drawing
    result = process_line_drawing_to_asset(
        args.lineDrawing,
        visual_block,
        generation_block,
        output_path=args.output,
        mapping_strategy=args.mappingStrategy
    )
    
    if result:
        print(f"Successfully created asset from line drawing: {result['mesh'].name}")
    else:
        print("Failed to create asset from line drawing")
        sys.exit(1)


if __name__ == "__main__":
    main()

