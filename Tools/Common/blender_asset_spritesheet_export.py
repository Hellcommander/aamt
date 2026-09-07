#!/usr/bin/env python3
"""
Blender Script: Export Asset Model as Spritesheet
General-purpose exporter for items, weapons, projectiles, etc.
Supports rotation frames, animation frames, or static spritesheets.

Usage:
    blender --background --python blender_asset_spritesheet_export.py -- \
        --model "item.blend" \
        --output "item_spritesheet.png" \
        --type "rotation" \
        --facings 120 \
        --columns 10 \
        --rows 12 \
        --frame-width 96 \
        --frame-height 96
"""

import bpy
import sys
import argparse
import os
from math import radians

def clear_scene():
    """Clear the default scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    # Clear meshes
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

def setup_camera(frame_width, frame_height, camera_type='orthographic'):
    """Setup camera for consistent rendering"""
    # Remove default camera
    if bpy.context.scene.camera:
        bpy.ops.object.delete({"selected_objects": [bpy.context.scene.camera]})
    
    # Create camera
    bpy.ops.object.camera_add(location=(0, -5, 0))
    camera = bpy.context.active_object
    camera.name = "SpritesheetCamera"
    
    # Set camera type
    if camera_type == 'orthographic':
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 3.0  # Adjust based on asset size
    else:
        camera.data.type = 'PERSP'
        camera.data.lens = 50.0
    
    # Point camera at origin (top-down for items, front for ships)
    camera.rotation_euler = (radians(90), 0, 0)
    
    # Set as active camera
    bpy.context.scene.camera = camera
    
    return camera

def setup_lighting(lighting_type='standard'):
    """Setup lighting for consistent rendering"""
    # Remove default light
    if bpy.data.objects.get("Light"):
        bpy.ops.object.delete({"selected_objects": [bpy.data.objects["Light"]]})
    
    if lighting_type == 'standard':
        # Add key light (main light)
        bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
        key_light = bpy.context.active_object
        key_light.name = "KeyLight"
        key_light.data.energy = 3.0
        key_light.rotation_euler = (radians(45), radians(45), 0)
        
        # Add fill light
        bpy.ops.object.light_add(type='SUN', location=(-3, -3, 5))
        fill_light = bpy.context.active_object
        fill_light.name = "FillLight"
        fill_light.data.energy = 1.0
        fill_light.rotation_euler = (radians(30), radians(-30), 0)
    
    elif lighting_type == 'item':
        # Softer lighting for items
        bpy.ops.object.light_add(type='SUN', location=(3, -3, 8))
        key_light = bpy.context.active_object
        key_light.name = "KeyLight"
        key_light.data.energy = 2.0
        key_light.rotation_euler = (radians(60), radians(30), 0)
        
        bpy.ops.object.light_add(type='SUN', location=(-2, -2, 4))
        fill_light = bpy.context.active_object
        fill_light.name = "FillLight"
        fill_light.data.energy = 0.8

def setup_render_settings(frame_width, frame_height, output_format='PNG', game_format='Generic'):
    """Configure render settings for spritesheet export"""
    scene = bpy.context.scene
    
    # Set render engine
    scene.render.engine = 'CYCLES'  # or 'BLENDER_EEVEE' for faster rendering
    
    # Set resolution
    scene.render.resolution_x = frame_width
    scene.render.resolution_y = frame_height
    scene.render.resolution_percentage = 100
    
    # Set output format based on game requirements
    if game_format == 'Transcendence':
        # Transcendence uses JPG for ships, PNG for items
        scene.render.image_settings.file_format = 'PNG'  # Render as PNG, convert later if needed
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
    elif game_format == 'Terraria':
        # Terraria uses PNG with transparency
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
    elif game_format == 'Starbound':
        # Starbound uses PNG
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
    else:
        # Generic: use specified format
        scene.render.image_settings.file_format = output_format
        if output_format == 'PNG':
            scene.render.image_settings.color_mode = 'RGBA'
            scene.render.film_transparent = True
        else:
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.film_transparent = False
    
    # Set samples for quality
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True

def load_asset_model(model_path):
    """Load asset model from file"""
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        return None
    
    file_ext = os.path.splitext(model_path)[1].lower()
    
    try:
        if file_ext == '.blend':
            # Load from blend file
            with bpy.data.libraries.load(model_path) as (data_from, data_to):
                data_to.objects = data_from.objects
            
            # Link objects to scene
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
            
            # Select all imported objects
            bpy.ops.object.select_all(action='SELECT')
            return bpy.context.selected_objects
        
        elif file_ext in ['.obj', '.fbx', '.dae', '.3ds', '.glb', '.gltf']:
            # Import using appropriate importer
            if file_ext == '.obj':
                bpy.ops.import_scene.obj(filepath=model_path)
            elif file_ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=model_path)
            elif file_ext in ('.glb', '.gltf'):
                bpy.ops.import_scene.gltf(filepath=model_path)
            elif file_ext == '.dae':
                bpy.ops.wm.collada_import(filepath=model_path)
            elif file_ext == '.3ds':
                bpy.ops.import_scene.autodesk_3ds(filepath=model_path)
            
            # Select imported objects
            bpy.ops.object.select_all(action='SELECT')
            return bpy.context.selected_objects
        
        else:
            print(f"Error: Unsupported file format: {file_ext}")
            return None
    
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def center_asset_objects(objects):
    """Center all asset objects at origin"""
    if not objects:
        return
    
    # Select all objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    
    # Set origin to geometry center
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    
    # Move to origin
    bpy.ops.object.location_clear()

def render_frame(angle=None, frame_index=0, frame_width, frame_height, output_path):
    """Render a single frame"""
    asset_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    # Apply rotation if specified
    if angle is not None:
        for obj in asset_objects:
            obj.rotation_euler = (0, 0, radians(angle))
    
    # Update scene
    bpy.context.view_layer.update()
    
    # Render
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    
    return output_path

def generate_mask_from_alpha(image_path, mask_path):
    """Generate black/white mask from image alpha channel
    Mask format: Black background with white asset outline (negative/outline image)
    """
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    
    if img.mode == 'RGBA':
        # Extract alpha channel
        alpha = img.split()[3]
        alpha_array = np.array(alpha)
        
        # Create mask: white where asset is (alpha > 0), black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Where alpha > 0, set to white (255, 255, 255)
        asset_pixels = alpha_array > 0
        mask_array[asset_pixels] = [255, 255, 255]
        
        # Convert to PIL Image
        mask = Image.fromarray(mask_array, 'RGB')
        
        # Save as BMP
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white asset outline)")
        return True
    elif img.mode == 'RGB':
        # For RGB images, create mask based on non-black pixels
        img_array = np.array(img)
        
        # Create mask: white where image is not black, black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Find non-black pixels (asset)
        non_black = np.any(img_array > [10, 10, 10], axis=2)  # Threshold to ignore near-black
        mask_array[non_black] = [255, 255, 255]
        
        mask = Image.fromarray(mask_array, 'RGB')
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white asset outline)")
        return True
    else:
        print(f"Warning: Image {image_path} format not supported for mask generation")
        return False

def create_spritesheet(export_type, facings, columns, rows, frame_width, frame_height, output_path, output_format='PNG', game_format='Generic'):
    """Create spritesheet by rendering all frames and compositing"""
    try:
        from PIL import Image
    except ImportError:
        print("Error: PIL (Pillow) not installed. Install with: pip install Pillow")
        return None
    
    import numpy as np
    import tempfile
    
    # Calculate total spritesheet dimensions
    spritesheet_width = columns * frame_width
    spritesheet_height = rows * frame_height
    
    # Determine color mode based on format
    if output_format == 'PNG' or game_format in ['Terraria', 'Starbound']:
        color_mode = 'RGBA'
        background_color = (0, 0, 0, 0)  # Transparent
    else:
        color_mode = 'RGB'
        background_color = (0, 0, 0)  # Black
    
    # Create blank spritesheet
    spritesheet = Image.new(color_mode, (spritesheet_width, spritesheet_height), background_color)
    
    # Temporary directory for individual frames
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Render each frame
        for frame_index in range(facings):
            # Calculate rotation angle or animation frame
            if export_type == 'rotation':
                angle = (360.0 / facings) * frame_index
            else:
                angle = None  # Static or animation frames
            
            # Calculate grid position
            col = frame_index % columns
            row = frame_index // columns
            
            # Render frame to temporary file (always PNG for compositing)
            frame_path = os.path.join(temp_dir, f"frame_{frame_index:03d}.png")
            render_frame(angle, frame_index, frame_width, frame_height, frame_path)
            
            # Load rendered frame
            frame_img = Image.open(frame_path)
            
            # Convert to spritesheet color mode if needed
            if spritesheet.mode == 'RGB' and frame_img.mode == 'RGBA':
                # Convert RGBA to RGB with black background
                rgb_frame = Image.new('RGB', frame_img.size, (0, 0, 0))
                rgb_frame.paste(frame_img, mask=frame_img.split()[3] if frame_img.mode == 'RGBA' else None)
                frame_img = rgb_frame
            elif spritesheet.mode == 'RGBA' and frame_img.mode == 'RGB':
                frame_img = frame_img.convert('RGBA')
            
            # Calculate position in spritesheet
            x = col * frame_width
            y = row * frame_height
            
            # Paste frame into spritesheet
            if spritesheet.mode == 'RGBA' and frame_img.mode == 'RGBA':
                spritesheet.paste(frame_img, (x, y), frame_img)
            else:
                spritesheet.paste(frame_img, (x, y))
            
            print(f"Rendered frame {frame_index + 1}/{facings}")
        
        # Save spritesheet in appropriate format
        save_format = output_format
        if game_format == 'Transcendence':
            # Transcendence: JPG for ships, PNG for items
            save_format = 'PNG'  # Default to PNG, can be overridden
        elif game_format in ['Terraria', 'Starbound']:
            save_format = 'PNG'
        
        if save_format == 'JPEG' or save_format == 'JPG':
            # Convert to RGB if needed
            if spritesheet.mode == 'RGBA':
                rgb_spritesheet = Image.new('RGB', spritesheet.size, (0, 0, 0))
                rgb_spritesheet.paste(spritesheet, mask=spritesheet.split()[3])
                spritesheet = rgb_spritesheet
            spritesheet.save(output_path, 'JPEG', quality=95)
        elif save_format == 'PNG':
            spritesheet.save(output_path, 'PNG')
        elif save_format == 'BMP':
            if spritesheet.mode == 'RGBA':
                rgb_spritesheet = Image.new('RGB', spritesheet.size, (0, 0, 0))
                rgb_spritesheet.paste(spritesheet, mask=spritesheet.split()[3])
                spritesheet = rgb_spritesheet
            spritesheet.save(output_path, 'BMP')
        
        print(f"Spritesheet saved: {output_path} (format: {save_format})")
        
        # Generate negative/outline mask for Transcendence (BMP format)
        # Always generate mask for Transcendence format spritesheets
        if game_format == 'Transcendence':
            mask_path = output_path.replace('.jpg', 'Mask.bmp').replace('.png', 'Mask.bmp').replace('.bmp', 'Mask.bmp')
            print(f"Generating spritesheet mask (negative/outline)...")
            generate_mask_from_alpha(output_path, mask_path)
            print(f"Spritesheet mask (negative/outline) saved: {mask_path}")
        
    finally:
        # Cleanup temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return output_path

def main():
    """Main function"""
    # Parse command line arguments
    argv = sys.argv
    if "--" not in argv:
        argv = []
    else:
        argv = argv[argv.index("--") + 1:]
    
    parser = argparse.ArgumentParser(description='Export asset model as spritesheet')
    parser.add_argument('--model', required=True, help='Path to asset model file')
    parser.add_argument('--output', required=True, help='Output spritesheet path')
    parser.add_argument('--type', choices=['rotation', 'animation', 'static'], default='rotation',
                       help='Type of spritesheet: rotation (360°), animation (sequence), or static (single)')
    parser.add_argument('--facings', type=int, default=120, help='Number of frames')
    parser.add_argument('--columns', type=int, default=10, help='Number of columns in grid')
    parser.add_argument('--rows', type=int, default=12, help='Number of rows in grid')
    parser.add_argument('--frame-width', type=int, default=96, help='Width of each frame')
    parser.add_argument('--frame-height', type=int, default=96, help='Height of each frame')
    parser.add_argument('--asset-type', choices=['ship', 'item', 'weapon', 'projectile'], default='item',
                       help='Type of asset (affects camera and lighting)')
    parser.add_argument('--output-format', choices=['PNG', 'JPG', 'BMP'], default='PNG',
                       help='Output image format (PNG for transparency, JPG for smaller size, BMP for compatibility)')
    parser.add_argument('--game-format', choices=['Transcendence', 'Terraria', 'Starbound', 'Generic'],
                       default='Generic', help='Target game format (affects output format and settings)')
    
    args = parser.parse_args(argv)
    
    # Validate arguments
    if args.facings != args.columns * args.rows:
        print(f"Warning: facings ({args.facings}) != columns × rows ({args.columns} × {args.rows} = {args.columns * args.rows})")
    
    print("=" * 60)
    print("Blender Asset Spritesheet Exporter")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Output: {args.output}")
    print(f"Type: {args.type}")
    print(f"Asset Type: {args.asset_type}")
    print(f"Frames: {args.facings}")
    print(f"Grid: {args.columns} × {args.rows}")
    print(f"Frame Size: {args.frame_width} × {args.frame_height}")
    print("=" * 60)
    
    # Clear scene
    clear_scene()
    
    # Setup render settings
    setup_render_settings(args.frame_width, args.frame_height, args.output_format, args.game_format)
    
    # Setup camera (orthographic for items, perspective for ships)
    camera_type = 'orthographic' if args.asset_type in ['item', 'weapon'] else 'orthographic'
    setup_camera(args.frame_width, args.frame_height, camera_type)
    
    # Setup lighting
    lighting_type = 'item' if args.asset_type in ['item', 'weapon'] else 'standard'
    setup_lighting(lighting_type)
    
    # Load asset model
    print(f"Loading model: {args.model}")
    asset_objects = load_asset_model(args.model)
    
    if not asset_objects:
        print("Error: Failed to load asset model")
        return 1
    
    # Center asset at origin
    center_asset_objects(asset_objects)
    
    # Create spritesheet
    print("Creating spritesheet...")
    create_spritesheet(
        args.type,
        args.facings,
        args.columns,
        args.rows,
        args.frame_width,
        args.frame_height,
        args.output,
        args.output_format,
        args.game_format
    )
    
    print("Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

