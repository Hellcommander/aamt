#!/usr/bin/env python3
"""
Blender Script: Convert 2D Sketch to 3D Mesh
Integrates with the unified asset registry and procedural material pipeline.
"""

import bpy
import os
import sys
import json

# ------------------------------------------------------------
# Sketch Import and Processing
# ------------------------------------------------------------

def import_sketch_as_plane(sketch_path, name="SketchReference"):
    """
    Import a sketch image as a plane in Blender.
    
    Args:
        sketch_path: Path to the sketch image file
        name: Name for the plane object
    
    Returns:
        The created plane object
    """
    # Load image
    if not os.path.exists(sketch_path):
        print(f"Error: Sketch file not found: {sketch_path}")
        return None
    
    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = name
    
    # Create material for the image
    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Add nodes
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    image_tex = nodes.new("ShaderNodeTexImage")
    
    output.location = (200, 0)
    emission.location = (0, 0)
    image_tex.location = (-200, 0)
    
    # Load image
    image = bpy.data.images.load(sketch_path)
    image_tex.image = image
    
    # Connect nodes
    links.new(image_tex.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    
    # Assign material
    plane.data.materials.append(mat)
    
    return plane


def trace_silhouette_to_curve(sketch_path, threshold=0.5):
    """
    Convert a sketch image to a curve by tracing its silhouette.
    
    Args:
        sketch_path: Path to the sketch image file
        threshold: Brightness threshold for edge detection (0-1)
    
    Returns:
        The created curve object
    """
    # Import sketch as plane first
    plane = import_sketch_as_plane(sketch_path, "SketchPlane")
    if not plane:
        return None
    
    # Select the plane
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    
    # Convert to curve (this is a simplified approach)
    # In a full implementation, you'd use edge detection or manual tracing
    # For now, we'll use Blender's built-in conversion
    try:
        bpy.ops.object.convert(target='CURVE')
        curve = bpy.context.active_object
        curve.name = "SketchCurve"
        return curve
    except:
        print("Warning: Could not convert to curve, returning plane")
        return plane


def create_mesh_from_silhouette(sketch_path, extrude_depth=0.1, bevel_amount=0.01):
    """
    Create a 3D mesh by extruding a sketch silhouette.
    
    Args:
        sketch_path: Path to the sketch image file
        extrude_depth: How far to extrude the silhouette (Blender units)
        bevel_amount: Bevel amount for edges (Blender units)
    
    Returns:
        The created mesh object
    """
    # Import sketch as plane
    plane = import_sketch_as_plane(sketch_path, "SketchBase")
    if not plane:
        return None
    
    # Select plane
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Extrude (this is a simplified approach)
    # In practice, you'd trace the silhouette first, then extrude
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={
            "value": (0, 0, extrude_depth),
            "constraint_axis": (False, False, True)
        }
    )
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Add bevel modifier
    bevel = plane.modifiers.new(name="Bevel", type='BEVEL')
    bevel.amount = bevel_amount
    bevel.segments = 2
    
    plane.name = "SketchMesh"
    return plane


def create_mesh_from_displacement(sketch_path, strength=0.1):
    """
    Create a 3D mesh using the sketch as a displacement map.
    
    Args:
        sketch_path: Path to the sketch image file
        strength: Displacement strength (Blender units)
    
    Returns:
        The created mesh object with displacement
    """
    # Create a subdivided plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "DisplacementMesh"
    
    # Subdivide for detail
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=4)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Add displacement modifier
    displace = plane.modifiers.new(name="Displace", type='DISPLACE')
    
    # Load image as texture
    if os.path.exists(sketch_path):
        image = bpy.data.images.load(sketch_path)
        texture = bpy.data.textures.new(name="DisplacementTex", type='IMAGE')
        texture.image = image
        displace.texture = texture
        displace.strength = strength
    
    return plane


def process_sketch(sketch_path, use_as="silhouette", extrude_depth=0.1, bevel_amount=0.01, displacement_strength=0.1):
    """
    Process a sketch based on the specified method.
    
    Args:
        sketch_path: Path to the sketch image file
        use_as: How to use the sketch ("silhouette", "displacement", "mask", "reference", "heightmap")
        extrude_depth: Extrusion depth for silhouette method
        bevel_amount: Bevel amount for edges
        displacement_strength: Displacement strength for displacement method
    
    Returns:
        The created object
    """
    if not os.path.exists(sketch_path):
        print(f"Error: Sketch file not found: {sketch_path}")
        return None
    
    sketch_path_abs = os.path.abspath(sketch_path)
    
    if use_as == "silhouette":
        return create_mesh_from_silhouette(sketch_path_abs, extrude_depth, bevel_amount)
    elif use_as == "displacement":
        return create_mesh_from_displacement(sketch_path_abs, displacement_strength)
    elif use_as == "heightmap":
        return create_mesh_from_displacement(sketch_path_abs, displacement_strength)
    elif use_as == "mask":
        # Use as alpha mask for materials
        plane = import_sketch_as_plane(sketch_path_abs, "MaskPlane")
        return plane
    elif use_as == "reference":
        # Just import as reference image
        plane = import_sketch_as_plane(sketch_path_abs, "ReferencePlane")
        # Make it non-rendering
        plane.hide_render = True
        return plane
    else:
        print(f"Warning: Unknown use_as value: {use_as}, using silhouette")
        return create_mesh_from_silhouette(sketch_path_abs, extrude_depth, bevel_amount)


# ------------------------------------------------------------
# Integration with Material Generator
# ------------------------------------------------------------

def apply_material_to_sketch_mesh(mesh_obj, visual_block, quality="standard", export_node_groups=False):
    """
    Apply procedural material to a sketch-derived mesh.
    
    Args:
        mesh_obj: The mesh object from sketch processing
        visual_block: Visual specification from registry
        quality: Quality tier
        export_node_groups: Whether to use node groups
    
    Returns:
        The material applied to the mesh
    """
    # Import material generator
    try:
        from material_generator import build_material_from_visual
    except ImportError:
        print("Error: material_generator.py not found")
        return None
    
    # Build material
    mat_name = f"{mesh_obj.name}_Material"
    material = build_material_from_visual(
        visual_block,
        mat_name=mat_name,
        quality=quality,
        export_node_groups=export_node_groups
    )
    
    # Assign to mesh
    if len(mesh_obj.data.materials) == 0:
        mesh_obj.data.materials.append(material)
    else:
        mesh_obj.data.materials[0] = material
    
    return material


# ------------------------------------------------------------
# Main Processing Function
# ------------------------------------------------------------

def process_sketch_to_asset(sketch_path, visual_block, generation_block, output_path=None):
    """
    Complete pipeline: Sketch → Mesh → Material → Asset
    
    Args:
        sketch_path: Path to sketch image
        visual_block: Visual specification dict
        generation_block: Generation specification dict
        output_path: Optional path to save .blend file
    
    Returns:
        The created mesh object with material
    """
    # Get generation parameters
    use_as = generation_block.get("useSketchAs", "silhouette")
    extrude_depth = generation_block.get("extrudeDepth", 0.1)
    bevel_amount = generation_block.get("bevelAmount", 0.01)
    quality = generation_block.get("quality", "standard")
    export_node_groups = generation_block.get("exportNodeGroups", False)
    displacement_strength = generation_block.get("displacementStrength", 0.1)
    
    # Process sketch
    print(f"Processing sketch: {sketch_path}")
    print(f"  Method: {use_as}")
    print(f"  Quality: {quality}")
    
    mesh_obj = process_sketch(
        sketch_path,
        use_as=use_as,
        extrude_depth=extrude_depth,
        bevel_amount=bevel_amount,
        displacement_strength=displacement_strength
    )
    
    if not mesh_obj:
        print("Error: Failed to process sketch")
        return None
    
    # Apply material
    print("Applying procedural material...")
    material = apply_material_to_sketch_mesh(
        mesh_obj,
        visual_block,
        quality=quality,
        export_node_groups=export_node_groups
    )
    
    if material:
        print(f"Material '{material.name}' applied successfully")
    
    # Save .blend file if requested
    if output_path:
        output_path_abs = os.path.abspath(output_path)
        try:
            bpy.ops.wm.save_as_mainfile(filepath=output_path_abs)
            print(f"Saved to: {output_path_abs}")
        except Exception as e:
            print(f"Warning: Could not save .blend file: {e}")
    
    return mesh_obj


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
    parser = argparse.ArgumentParser(description='Convert 2D sketch to 3D asset')
    parser.add_argument("--sketch", type=str, required=True, help="Path to sketch image file")
    parser.add_argument("--visualJson", type=str, help="Visual block JSON")
    parser.add_argument("--generationJson", type=str, help="Generation block JSON")
    parser.add_argument("--registry", type=str, help="Registry JSON file path")
    parser.add_argument("--assetId", type=str, help="Asset ID from registry")
    parser.add_argument("--output", type=str, help="Output .blend file path")
    
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
    
    # Process sketch
    mesh_obj = process_sketch_to_asset(
        args.sketch,
        visual_block,
        generation_block,
        output_path=args.output
    )
    
    if mesh_obj:
        print(f"Successfully created asset from sketch: {mesh_obj.name}")
    else:
        print("Failed to create asset from sketch")
        sys.exit(1)


if __name__ == "__main__":
    main()

