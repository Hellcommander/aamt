"""
Blender Space Whale Renderer with 120 Facings Support
Renders space whale ship with 120 rotation frames (3 degrees per frame) for complete 360-degree coverage.
"""

import bpy
import sys
import os
import json
import argparse
import math
from pathlib import Path
from mathutils import Color, Vector, noise

def clear_scene():
    """Clear all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple (0-1 range)"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)

def load_texture_maps(module_name: str, texture_dir: str):
    """Load texture maps for a module if available."""
    textures = {}
    base_path = Path(texture_dir) / module_name
    
    texture_files = {
        'diffuse': f"{module_name}_diffuse.png",
        'emission': f"{module_name}_emission.png",
        'normal': f"{module_name}_normal.png",
        'roughness': f"{module_name}_roughness.png",
        'metallic': f"{module_name}_metallic.png"
    }
    
    for map_type, filename in texture_files.items():
        file_path = base_path / filename
        if file_path.exists():
            img = bpy.data.images.load(str(file_path))
            textures[map_type] = img
    
    return textures

def create_bioluminescent_material(materials_config, frame_time, module_name: str = None, texture_dir: str = None):
    """Create bioluminescent skin material with subsurface scattering and vein flow.
    Uses texture maps if available, otherwise falls back to procedural generation."""
    mat = bpy.data.materials.new(name=f"BioluminescentSkin_{module_name or 'default'}")
    # In Blender 5.0+, materials use nodes by default (use_nodes deprecated)
    # Access node tree directly - it's always available in 5.0+
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (800, 0)
    
    # Principled BSDF for base material
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    # Try to load textures
    textures = {}
    if module_name and texture_dir:
        textures = load_texture_maps(module_name, texture_dir)
    
    # Base color (from texture or config)
    if 'diffuse' in textures:
        diffuse_tex = nodes.new(type='ShaderNodeTexImage')
        diffuse_tex.location = (-400, 200)
        diffuse_tex.image = textures['diffuse']
        links.new(diffuse_tex.outputs['Color'], principled.inputs['Base Color'])
    else:
        base_color = hex_to_rgb(materials_config.get('baseColor', '#1a2a3a'))
        principled.inputs['Base Color'].default_value = (*base_color, 1.0)
    
    # Subsurface scattering
    if materials_config.get('subsurfaceScattering', True):
        principled.inputs['Subsurface'].default_value = 0.3
        principled.inputs['Subsurface Radius'].default_value = (0.1, 0.1, 0.1)
        subsurface_color = hex_to_rgb(materials_config.get('baseColor', '#1a2a3a'))
        principled.inputs['Subsurface Color'].default_value = (*subsurface_color, 1.0)
    
    # Emission for bioluminescence (from texture or config)
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (200, -200)
    
    if 'emission' in textures:
        emission_tex = nodes.new(type='ShaderNodeTexImage')
        emission_tex.location = (-400, 0)
        emission_tex.image = textures['emission']
        links.new(emission_tex.outputs['Color'], emission.inputs['Color'])
    else:
        vein_color = hex_to_rgb(materials_config.get('veinColor', '#66ccff'))
        emission.inputs['Color'].default_value = (*vein_color, 1.0)
    
    emission.inputs['Strength'].default_value = materials_config.get('emissiveIntensity', 3.5)
    
    # Vein flow using noise texture
    noise_tex = nodes.new(type='ShaderNodeTexNoise')
    noise_tex.location = (-400, -200)
    noise_tex.inputs['Scale'].default_value = 5.0
    noise_tex.inputs['Detail'].default_value = 8.0
    noise_tex.inputs['Roughness'].default_value = 0.3
    
    # Animate noise for vein flow
    mapping = nodes.new(type='ShaderNodeMapping')
    mapping.location = (-600, -200)
    
    time_node = nodes.new(type='ShaderNodeValue')
    time_node.outputs[0].default_value = frame_time * materials_config.get('veinFlowSpeed', 1.2)
    
    # Add normal map if available
    if 'normal' in textures:
        normal_tex = nodes.new(type='ShaderNodeTexImage')
        normal_tex.location = (-400, -200)
        normal_tex.image = textures['normal']
        
        normal_map = nodes.new(type='ShaderNodeNormalMap')
        normal_map.location = (-200, -200)
        links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
    
    # Add roughness map if available
    if 'roughness' in textures:
        roughness_tex = nodes.new(type='ShaderNodeTexImage')
        roughness_tex.location = (-400, -400)
        roughness_tex.image = textures['roughness']
        roughness_tex.image.colorspace_settings.name = 'Non-Color'
        links.new(roughness_tex.outputs['Color'], principled.inputs['Roughness'])
    
    # Add metallic map if available
    if 'metallic' in textures:
        metallic_tex = nodes.new(type='ShaderNodeTexImage')
        metallic_tex.location = (-400, -600)
        metallic_tex.image = textures['metallic']
        metallic_tex.image.colorspace_settings.name = 'Non-Color'
        links.new(metallic_tex.outputs['Color'], principled.inputs['Metallic'])
    
    # Combine base and emission
    mix = nodes.new(type='ShaderNodeMix')
    mix.location = (400, 0)
    mix.data_type = 'RGBA'
    mix.blend_type = 'ADD'
    mix.inputs['Factor'].default_value = 0.6
    
    # Connect nodes
    if 'emission' not in textures:
        # Only use noise if no emission texture
        links.new(noise_tex.outputs['Fac'], mix.inputs['A'])
    else:
        mix.inputs['Factor'].default_value = 0.7  # Higher blend with texture
    
    links.new(principled.outputs['BSDF'], mix.inputs[6])
    links.new(emission.outputs['Emission'], mix.inputs[7])
    links.new(mix.outputs['Result'], output.inputs['Surface'])
    
    return mat

def create_ship_module(module_config, visual_config):
    """Create a modular ship section"""
    module_type = module_config.get('type', 'mid')
    pos = module_config.get('position', {})
    
    if module_type == 'head':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'head')
        obj.scale = (1.2, 0.8, 1.5)
        
    elif module_type == 'mid':
        bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'mid')
        obj.scale = (1.0, 1.0, 1.2)
        
    elif module_type == 'belly':
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, subdivisions=3)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'belly')
        obj.scale = (1.5, 1.5, 0.6)
        
    elif module_type == 'tail':
        bpy.ops.mesh.primitive_cone_add(radius1=0.8, radius2=0.2, depth=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'tail')
        obj.rotation_euler = (math.radians(90), 0, 0)
        
    elif module_type == 'dorsalCrest':
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'dorsalCrest')
        obj.scale = (0.3, 1.5, 1.0)
        obj.rotation_euler = (math.radians(90), 0, 0)
        
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'module')
    
    # Position module
    obj.location = (pos.get('x', 0), pos.get('y', 0), pos.get('z', 0))
    
    return obj

def setup_camera_and_lighting(size, rotation_angle=0):
    """Setup orthographic camera and lighting for ship rendering"""
    # Camera
    bpy.ops.object.camera_add(location=(0, -size * 3, size * 2))
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = size * 6
    camera.rotation_euler = (math.radians(60), 0, math.radians(45) + rotation_angle)
    bpy.context.scene.camera = camera
    
    # Lighting
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 2.0
    
    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-5, 5, 5))
    fill = bpy.context.active_object
    fill.data.energy = 1.0
    fill.data.size = 10.0

def render_ship_rotation(ship_data, output_path, facing_idx, total_facings, size, animation_frame=0, texture_dir=None):
    """Render a single rotation frame of the space whale ship"""
    visual = ship_data['visual']
    animations = visual.get('animations', {})
    materials = visual.get('materials', {})
    modules = visual.get('modules', [])
    
    # Calculate rotation angle (360 degrees / total_facings)
    rotation_angle = (facing_idx / total_facings) * 2 * math.pi
    
    # Calculate animation frame time
    frame_time = animation_frame / 16.0  # Assuming 16 animation frames
    
    # Clear scene
    clear_scene()
    
    # Create materials (with textures if available)
    skin_mat = create_bioluminescent_material(materials, frame_time, "default", texture_dir)
    
    # Create ship modules with per-module materials
    ship_objects = []
    for module_config in modules:
        module_obj = create_ship_module(module_config, visual)
        
        # Create material for this specific module (with textures if available)
        module_name = module_config.get('name', 'module')
        module_mat = create_bioluminescent_material(materials, frame_time, module_name, texture_dir)
        module_obj.data.materials.append(module_mat)
        
        # Rotate entire ship for facing
        module_obj.rotation_euler = (0, 0, rotation_angle)
        
        # Apply breathing animation
        if animations.get('breathingEnabled', True):
            speed = animations.get('breathingSpeed', 0.8)
            amplitude = animations.get('breathingAmplitude', 0.05)
            breath = 1.0 + math.sin(frame_time * speed * 2 * math.pi) * amplitude
            module_obj.scale = (module_obj.scale.x * breath, module_obj.scale.y * breath, module_obj.scale.z * breath)
        
        ship_objects.append(module_obj)
    
    # Setup camera and lighting
    setup_camera_and_lighting(size, rotation_angle)
    
    # Render
    bpy.context.scene.render.resolution_x = size
    bpy.context.scene.render.resolution_y = size
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.frame_set(animation_frame + 1)
    
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)

def create_120_facing_spritesheet(ship_data, output_dir, animation_frames=16, columns=10, rows=12, texture_dir=None):
    """Create spritesheet with 120 facings (10 columns × 12 rows)"""
    # Validate input data
    if not ship_data:
        raise ValueError("Ship data is empty or None")
    
    if 'visual' not in ship_data:
        raise ValueError(f"Ship '{ship_data.get('id', 'unknown')}' missing required 'visual' section")
    
    visual = ship_data['visual']
    silhouette = visual.get('silhouette', {})
    
    # Calculate size based on ship dimensions
    length = silhouette.get('length', 8.0)
    width = silhouette.get('width', 3.5)
    frame_size = int(max(length, width) * 64)  # Scale to pixels
    
    total_facings = columns * rows  # Should be 120
    
    # Ensure absolute path
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Check for texture directory
    if texture_dir is None:
        # Try to find texture directory
        possible_texture_dirs = [
            os.path.join(os.path.dirname(output_dir), 'Textures'),
            os.path.join(output_dir, '..', 'Textures'),
            'Output/SpaceWhaleTextures'
        ]
        for td in possible_texture_dirs:
            if os.path.exists(td):
                texture_dir = td
                print(f"Found texture directory: {texture_dir}")
                break
    
    # Render all facings
    temp_dir = os.path.join(output_dir, 'temp_facings')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    
    print(f"Rendering {total_facings} facings ({columns}×{rows} grid)...")
    if texture_dir:
        print(f"Using textures from: {texture_dir}")
    
    for facing_idx in range(total_facings):
        # Use first animation frame for base spritesheet
        frame_path = os.path.join(temp_dir, f"facing_{facing_idx:03d}.png")
        render_ship_rotation(ship_data, frame_path, facing_idx, total_facings, frame_size, animation_frame=0, texture_dir=texture_dir)
        frame_files.append(frame_path)
        
        if (facing_idx + 1) % 10 == 0:
            print(f"  Rendered {facing_idx + 1}/{total_facings} facings...")
    
    # Composite into spritesheet (10 columns × 12 rows)
    spritesheet_width = columns * frame_size
    spritesheet_height = rows * frame_size
    
    # Create spritesheet image
    spritesheet = bpy.data.images.new(
        name=f"{ship_data['id']}_spritesheet_120",
        width=spritesheet_width,
        height=spritesheet_height,
        alpha=True
    )
    
    # Initialize with transparent pixels
    pixels = [0.0] * (spritesheet_width * spritesheet_height * 4)
    spritesheet.pixels = pixels
    
    # Load and composite each facing
    for facing_idx, frame_path in enumerate(frame_files):
        if os.path.exists(frame_path):
            # Calculate grid position
            col = facing_idx % columns
            row = facing_idx // columns
            
            # Load frame image
            frame_img = bpy.data.images.load(frame_path)
            
            # Calculate position in spritesheet
            x_offset = col * frame_size
            y_offset = (rows - 1 - row) * frame_size  # Flip Y for top-to-bottom
            
            # Copy pixels from frame to spritesheet
            for y in range(frame_size):
                for x in range(frame_size):
                    # Get pixel from frame
                    frame_idx_px = (y * frame_size + x) * 4
                    if frame_idx_px < len(frame_img.pixels):
                        r = frame_img.pixels[frame_idx_px]
                        g = frame_img.pixels[frame_idx_px + 1]
                        b = frame_img.pixels[frame_idx_px + 2]
                        a = frame_img.pixels[frame_idx_px + 3]
                    else:
                        r, g, b, a = 0.0, 0.0, 0.0, 0.0
                    
                    # Set pixel in spritesheet
                    sheet_x = x_offset + x
                    sheet_y = y_offset + y
                    sheet_idx = (sheet_y * spritesheet_width + sheet_x) * 4
                    if sheet_idx < len(spritesheet.pixels):
                        spritesheet.pixels[sheet_idx] = r
                        spritesheet.pixels[sheet_idx + 1] = g
                        spritesheet.pixels[sheet_idx + 2] = b
                        spritesheet.pixels[sheet_idx + 3] = a
            
            # Remove frame image from memory
            bpy.data.images.remove(frame_img)
    
    # Update spritesheet
    spritesheet.update()
    
    # Save spritesheet
    output_path = os.path.join(output_dir, f"{ship_data['id']}_120facings.png")
    spritesheet.filepath = output_path
    spritesheet.file_format = 'PNG'
    spritesheet.save()
    
    # Generate negative/outline mask for Transcendence (BMP format)
    # Always generate mask for spritesheets (black background, white ship outline)
    mask_path = os.path.join(output_dir, f"{ship_data['id']}_120facingsMask.bmp")
    print(f"Generating spritesheet mask (negative/outline)...")
    
    # Use PIL-based method for consistency with selection image masks
    if os.path.exists(output_path):
        generate_mask_from_alpha(output_path, mask_path)
    else:
        # Fallback to Blender-based method if file doesn't exist yet
        generate_mask_from_spritesheet(spritesheet, mask_path)
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"Spritesheet saved: {output_path}")
    print(f"Spritesheet mask (negative/outline) saved: {mask_path}")
    return output_path, mask_path

def generate_mask_from_spritesheet(spritesheet, mask_path):
    """Generate BMP mask from spritesheet alpha channel"""
    width = spritesheet.size[0]
    height = spritesheet.size[1]
    
    # Create mask image (BMP format, RGB)
    mask_img = bpy.data.images.new(
        name="Mask",
        width=width,
        height=height,
        alpha=False
    )
    
    # Convert alpha to black/white mask
    pixels = list(spritesheet.pixels)
    mask_pixels = []
    
    for i in range(0, len(pixels), 4):
        alpha = pixels[i + 3]
        # White for opaque, black for transparent
        mask_val = 1.0 if alpha > 0.5 else 0.0
        mask_pixels.extend([mask_val, mask_val, mask_val])
    
    mask_img.pixels = mask_pixels
    mask_img.update()
    
    # Save as BMP
    mask_img.filepath = mask_path
    mask_img.file_format = 'BMP'
    mask_img.save()
    
    bpy.data.images.remove(mask_img)

def generate_mask_from_alpha(image_path, mask_path):
    """Generate black/white mask from image alpha channel
    Mask format: Black background with white ship outline (negative/outline image)
    """
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    
    if img.mode == 'RGBA':
        # Extract alpha channel
        alpha = img.split()[3]
        alpha_array = np.array(alpha)
        
        # Create mask: white where ship is (alpha > 0), black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Where alpha > 0, set to white (255, 255, 255)
        ship_pixels = alpha_array > 0
        mask_array[ship_pixels] = [255, 255, 255]
        
        # Convert to PIL Image
        mask = Image.fromarray(mask_array, 'RGB')
        
        # Save as BMP
        mask.save(mask_path, 'BMP')
        print(f"Selection mask generated: {mask_path} (black background, white ship outline)")
        return True
    elif img.mode == 'RGB':
        # For RGB images, create mask based on non-black pixels
        img_array = np.array(img)
        
        # Create mask: white where image is not black, black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Find non-black pixels (ship)
        non_black = np.any(img_array > [10, 10, 10], axis=2)  # Threshold to ignore near-black
        mask_array[non_black] = [255, 255, 255]
        
        mask = Image.fromarray(mask_array, 'RGB')
        mask.save(mask_path, 'BMP')
        print(f"Selection mask generated: {mask_path} (black background, white ship outline)")
        return True
    else:
        print(f"Warning: Image {image_path} format not supported for mask generation")
        return False

def render_selection_image(ship_data, output_path, size=320, texture_dir=None):
    """Render a front-facing selection/hero image for ship selection UI"""
    visual = ship_data['visual']
    materials = visual.get('materials', {})
    modules = visual.get('modules', [])
    silhouette = visual.get('silhouette', {})
    
    # Calculate size based on ship dimensions
    length = silhouette.get('length', 8.0)
    width = silhouette.get('width', 3.5)
    ship_size = max(length, width) * 1.2  # Add padding
    
    # Clear scene
    clear_scene()
    
    # Create materials (static frame, no animation)
    frame_time = 0.0
    skin_mat = create_bioluminescent_material(materials, frame_time, "default", texture_dir)
    
    # Create ship modules with per-module materials
    ship_objects = []
    for module_config in modules:
        module_obj = create_ship_module(module_config, visual)
        
        # Create material for this specific module (with textures if available)
        module_name = module_config.get('name', 'module')
        module_mat = create_bioluminescent_material(materials, frame_time, module_name, texture_dir)
        module_obj.data.materials.append(module_mat)
        
        # Front-facing (no rotation)
        module_obj.rotation_euler = (0, 0, 0)
        
        ship_objects.append(module_obj)
    
    # Setup camera and lighting for front-facing view
    setup_camera_and_lighting(ship_size, rotation_angle=0)
    
    # Render settings
    bpy.context.scene.render.resolution_x = size
    bpy.context.scene.render.resolution_y = size
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.film_transparent = True
    
    # Render to temporary PNG (for mask generation)
    temp_path = output_path.replace('.jpg', '_temp.png').replace('.png', '_temp.png')
    bpy.context.scene.render.filepath = temp_path
    bpy.ops.render.render(write_still=True)
    
    print(f"Rendered selection image: {temp_path}")
    
    # Generate mask from temporary PNG
    mask_path = output_path.replace('.jpg', 'Mask.bmp').replace('.png', 'Mask.bmp')
    if os.path.exists(temp_path):
        generate_mask_from_alpha(temp_path, mask_path)
    
    # Convert to final format (JPG for Transcendence)
    from PIL import Image
    hero_img = Image.open(temp_path)
    
    if output_path.endswith('.jpg'):
        # Convert to RGB and save as JPG
        if hero_img.mode == 'RGBA':
            rgb_hero = Image.new('RGB', hero_img.size, (0, 0, 0))
            rgb_hero.paste(hero_img, mask=hero_img.split()[3])
            hero_img = rgb_hero
        hero_img.save(output_path, 'JPEG', quality=95)
    else:
        hero_img.save(output_path, 'PNG')
    
    # Cleanup temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    print(f"Selection image saved: {output_path}")
    print(f"Selection mask (negative/outline) saved: {mask_path}")
    return output_path, mask_path

def main():
    try:
        parser = argparse.ArgumentParser(description='Render space whale ship with 120 facings')
        parser.add_argument('--registry', required=True, help='Path to ship registry JSON')
        parser.add_argument('--ship-id', help='Specific ship ID to render')
        parser.add_argument('--output-dir', required=True, help='Output directory for spritesheets')
        parser.add_argument('--columns', type=int, default=10, help='Number of columns (default: 10)')
        parser.add_argument('--rows', type=int, default=12, help='Number of rows (default: 12)')
        parser.add_argument('--animation-frames', type=int, default=16, help='Animation frames per facing')
        parser.add_argument('--texture-dir', type=str, default=None, help='Directory containing texture maps')
        parser.add_argument('--hero-image', type=str, default=None, help='Path for selection/hero image (larger single image for ship selection UI)')
        parser.add_argument('--hero-size', type=int, default=320, help='Size of hero/selection image (default: 320)')
        parser.add_argument('--generate-mask', action='store_true', help='Generate mask file for hero image (black background, white ship outline)')
        
        # Handle Blender's argument parsing (everything after --)
        if '--' in sys.argv:
            args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
        else:
            args = parser.parse_args()
        
        # Validate arguments
        if args.columns < 1 or args.rows < 1:
            raise ValueError(f"Columns and rows must be >= 1 (got {args.columns}×{args.rows})")
        
        if args.animation_frames < 1:
            raise ValueError(f"Animation frames must be >= 1 (got {args.animation_frames})")
        
        # Validate registry file exists
        if not os.path.exists(args.registry):
            raise FileNotFoundError(f"Registry file not found: {args.registry}")
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Validate texture directory if provided
        if args.texture_dir and not os.path.exists(args.texture_dir):
            print(f"Warning: Texture directory not found: {args.texture_dir}", file=sys.stderr)
            print("Continuing without textures...", file=sys.stderr)
            args.texture_dir = None
        
        # Load registry
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in registry file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read registry file: {e}")
        
        ships = registry.get('ships', [])
        
        if not ships:
            raise ValueError("No ships found in registry")
        
        if args.ship_id:
            ships = [s for s in ships if s.get('id') == args.ship_id]
            if not ships:
                raise ValueError(f"Ship ID '{args.ship_id}' not found in registry")
        
        total_facings = args.columns * args.rows
        print(f"Rendering {len(ships)} ship(s) with {total_facings} facings ({args.columns}×{args.rows})")
        
        successful = 0
        failed = 0
        
        for ship in ships:
            ship_id = ship.get('id', 'unknown')
            print(f"\nRendering ship: {ship_id}")
            try:
                create_120_facing_spritesheet(
                    ship, 
                    args.output_dir, 
                    animation_frames=args.animation_frames,
                    columns=args.columns,
                    rows=args.rows,
                    texture_dir=args.texture_dir
                )
                
                # Generate selection/hero image if requested
                if args.hero_image:
                    print(f"\nGenerating selection image for: {ship_id}")
                    try:
                        # Use ship-specific path if multiple ships, otherwise use provided path
                        if len(ships) > 1:
                            selection_path = args.hero_image.replace('.jpg', f'_{ship_id}.jpg').replace('.png', f'_{ship_id}.png')
                        else:
                            selection_path = args.hero_image
                        
                        render_selection_image(
                            ship,
                            selection_path,
                            size=args.hero_size,
                            texture_dir=args.texture_dir
                        )
                        print(f"✓ Selection image generated: {selection_path}")
                    except Exception as e:
                        print(f"✗ Failed to generate selection image for {ship_id}: {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
                        # Don't fail the whole process if selection image fails
                
                successful += 1
                print(f"✓ Successfully rendered: {ship_id}")
            except Exception as e:
                failed += 1
                print(f"✗ Failed to render {ship_id}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Continue with next ship
                continue
        
        print(f"\n{'='*60}")
        print(f"Rendering complete! Successful: {successful}, Failed: {failed}")
        if failed > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nRendering interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

