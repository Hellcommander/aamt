"""
Blender Projectile Renderer
Renders projectiles from registry JSON with procedural materials and spritesheet export.
Supports rotations, animation frames, normal maps, and distortion maps.
"""

import bpy
import sys
import os
import json
import argparse
from math import radians
from mathutils import Color, Vector

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

def create_procedural_material(material_config, palette):
    """Create procedural material based on registry configuration"""
    mat_name = "ProjectileMaterial"
    mat = bpy.data.materials.new(name=mat_name)
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Set base color from palette
    if palette.get('primary'):
        primary_color = hex_to_rgb(palette['primary'])
        bsdf.inputs['Base Color'].default_value = (*primary_color, 1.0)
    
    # Set material properties
    mat_type = material_config.get('type', 'Energy')
    glow_intensity = material_config.get('glowIntensity', 2.0)
    emission_strength = material_config.get('emissionStrength', 1.0)
    roughness = material_config.get('roughness', 0.3)
    metallic = material_config.get('metallic', 0.0)
    
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    
    # Emission for glow
    if glow_intensity > 0:
        emission = nodes.new(type='ShaderNodeEmission')
        emission.location = (-200, -200)
        
        if palette.get('glow'):
            glow_color = hex_to_rgb(palette['glow'])
            emission.inputs['Color'].default_value = (*glow_color, 1.0)
        else:
            emission.inputs['Color'].default_value = (*primary_color, 1.0)
        
        emission.inputs['Strength'].default_value = emission_strength * glow_intensity
        
        # Mix emission with BSDF
        mix = nodes.new(type='ShaderNodeMixShader')
        mix.location = (200, 0)
        mix.inputs['Fac'].default_value = 0.7  # Blend factor
        
        links.new(bsdf.outputs['BSDF'], mix.inputs[1])
        links.new(emission.outputs['Emission'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])
    else:
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Material type-specific adjustments
    if mat_type == "Plasma":
        # Add noise texture for plasma effect
        noise = nodes.new(type='ShaderNodeTexNoise')
        noise.location = (-400, -100)
        noise.inputs['Scale'].default_value = 10.0
        
        color_ramp = nodes.new(type='ShaderNodeValToRGB')
        color_ramp.location = (-200, -100)
        
        links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Color'], bsdf.inputs['Emission'])
    
    elif mat_type == "Crystal":
        # Glass-like shader
        glass = nodes.new(type='ShaderNodeBsdfGlass')
        glass.location = (-200, 100)
        glass.inputs['IOR'].default_value = 1.5
        
        mix = nodes.new(type='ShaderNodeMixShader')
        mix.location = (200, 0)
        mix.inputs['Fac'].default_value = 0.8
        
        links.new(bsdf.outputs['BSDF'], mix.inputs[1])
        links.new(glass.outputs['BSDF'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])
    
    return mat

def create_projectile_mesh(projectile_type, size):
    """Create base mesh for projectile based on type"""
    clear_scene()
    
    if projectile_type == "Missile":
        # Cylindrical missile
        bpy.ops.mesh.primitive_cylinder_add(radius=size[0]/4, depth=size[1]/2)
        obj = bpy.context.active_object
        obj.rotation_euler = (radians(90), 0, 0)
    elif projectile_type == "Laser":
        # Small sphere or elongated shape
        bpy.ops.mesh.primitive_ico_sphere_add(radius=size[0]/3, subdivisions=2)
        obj = bpy.context.active_object
    elif projectile_type == "Ballistic":
        # Small bullet shape
        bpy.ops.mesh.primitive_cylinder_add(radius=size[0]/6, depth=size[1]/3)
        obj = bpy.context.active_object
        obj.rotation_euler = (radians(90), 0, 0)
    else:  # Exotic
        # Complex shape - octahedron
        bpy.ops.mesh.primitive_octahedron_add(radius=size[0]/3)
        obj = bpy.context.active_object
    
    # Center at origin
    obj.location = (0, 0, 0)
    
    return obj

def setup_camera_and_lighting(width, height):
    """Setup orthographic camera and lighting"""
    # Camera
    bpy.ops.object.camera_add(location=(0, 0, 10))
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(width, height) / 10
    camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = camera
    
    # Lighting
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    
    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-5, -5, 5))
    fill = bpy.context.active_object
    fill.data.energy = 1.0
    fill.data.size = 5.0

def render_frame(output_path, width, height, frame=0):
    """Render a single frame"""
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.frame_set(frame)
    
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)

def render_rotation_frame(angle, output_path, width, height, frame=0):
    """Render a single rotation frame"""
    # Rotate projectile around Z-axis
    obj = bpy.context.active_object
    obj.rotation_euler = (0, 0, radians(angle))
    bpy.context.view_layer.update()
    
    render_frame(output_path, width, height, frame)

def generate_mask_from_alpha(image_path, mask_path):
    """Generate black/white mask from image alpha channel
    Mask format: Black background with white projectile outline (negative/outline image)
    """
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    
    if img.mode == 'RGBA':
        # Extract alpha channel
        alpha = img.split()[3]
        alpha_array = np.array(alpha)
        
        # Create mask: white where projectile is (alpha > 0), black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Where alpha > 0, set to white (255, 255, 255)
        projectile_pixels = alpha_array > 0
        mask_array[projectile_pixels] = [255, 255, 255]
        
        # Convert to PIL Image
        mask = Image.fromarray(mask_array, 'RGB')
        
        # Save as BMP
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white projectile outline)")
        return True
    elif img.mode == 'RGB':
        # For RGB images, create mask based on non-black pixels
        img_array = np.array(img)
        
        # Create mask: white where image is not black, black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Find non-black pixels (projectile)
        non_black = np.any(img_array > [10, 10, 10], axis=2)  # Threshold to ignore near-black
        mask_array[non_black] = [255, 255, 255]
        
        mask = Image.fromarray(mask_array, 'RGB')
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white projectile outline)")
        return True
    else:
        print(f"Warning: Image {image_path} format not supported for mask generation")
        return False

def create_spritesheet(projectile_data, output_dir):
    """Create spritesheet from projectile registry data"""
    visual = projectile_data['visual']
    width, height = visual['spriteSize']
    rotations = visual.get('rotations', 1)
    frames = visual.get('frames', 1)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup scene
    clear_scene()
    
    # Create projectile mesh
    projectile_type = projectile_data.get('type', 'Laser')
    obj = create_projectile_mesh(projectile_type, [width, height])
    
    # Create material
    material = create_procedural_material(
        visual.get('material', {}),
        visual.get('palette', {})
    )
    obj.data.materials.append(material)
    
    # Setup camera and lighting
    setup_camera_and_lighting(width, height)
    
    # Render frames
    temp_dir = os.path.join(output_dir, 'temp_frames')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    
    for frame_idx in range(frames):
        for rot_idx in range(rotations):
            angle = (360.0 / rotations) * rot_idx if rotations > 1 else 0
            frame_path = os.path.join(temp_dir, f"frame_{frame_idx:02d}_rot_{rot_idx:02d}.png")
            render_rotation_frame(angle, frame_path, width, height, frame_idx)
            frame_files.append((frame_idx, rot_idx, frame_path))
    
    # Composite into spritesheet
    from PIL import Image
    
    if rotations > 1:
        # Rotation spritesheet: arrange by rotation
        cols = rotations
        rows = frames
    else:
        # Animation spritesheet: arrange by frame
        cols = frames
        rows = 1
    
    spritesheet_width = cols * width
    spritesheet_height = rows * height
    
    spritesheet = Image.new('RGBA', (spritesheet_width, spritesheet_height), (0, 0, 0, 0))
    
    for frame_idx, rot_idx, frame_path in frame_files:
        if os.path.exists(frame_path):
            frame_img = Image.open(frame_path)
            x = rot_idx * width if rotations > 1 else frame_idx * width
            y = frame_idx * height if rotations > 1 else 0
            spritesheet.paste(frame_img, (x, y), frame_img)
    
    # Save spritesheet
    output_path = os.path.join(output_dir, f"{projectile_data['id']}.png")
    spritesheet.save(output_path, 'PNG')
    
    # Generate negative/outline mask for Transcendence (BMP format)
    # Always generate mask for spritesheets (black background, white projectile outline)
    mask_path = os.path.join(output_dir, f"{projectile_data['id']}Mask.bmp")
    print(f"Generating spritesheet mask (negative/outline)...")
    generate_mask_from_alpha(output_path, mask_path)
    
    # Generate normal / distortion maps from rendered alpha (real PNG fallbacks)
    if visual.get('normalMap', False) or visual.get('distortionMap', False):
        try:
            from PIL import Image
            import numpy as np
            src = Image.open(output_path).convert('RGBA')
            a = np.array(src.split()[3], dtype=np.float32) / 255.0
            gy, gx = np.gradient(a)
            if visual.get('normalMap', False):
                nx, ny, nz = -gx, -gy, np.ones_like(a)
                nlen = np.sqrt(nx*nx + ny*ny + nz*nz) + 1e-6
                nx, ny, nz = nx/nlen, ny/nlen, nz/nlen
                rgb = np.stack([(nx+1)*127.5, (ny+1)*127.5, (nz+1)*127.5], axis=-1).astype(np.uint8)
                npath = os.path.join(output_dir, f"{projectile_data['id']}_normal.png")
                Image.fromarray(rgb, 'RGB').save(npath)
                print(f"Normal map saved: {npath}")
            if visual.get('distortionMap', False):
                mag = np.clip(np.sqrt(gx*gx + gy*gy) * 8.0, 0, 1)
                d = np.zeros((a.shape[0], a.shape[1], 3), dtype=np.uint8)
                d[..., 0] = ((gx / (np.abs(gx).max() + 1e-6) * 0.5 + 0.5) * 255).astype(np.uint8)
                d[..., 1] = ((gy / (np.abs(gy).max() + 1e-6) * 0.5 + 0.5) * 255).astype(np.uint8)
                d[..., 2] = (mag * 255).astype(np.uint8)
                dpath = os.path.join(output_dir, f"{projectile_data['id']}_distort.png")
                Image.fromarray(d, 'RGB').save(dpath)
                print(f"Distortion map saved: {dpath}")
        except Exception as e:
            print(f"Map generation failed: {e}")
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"Spritesheet saved: {output_path}")
    print(f"Spritesheet mask (negative/outline) saved: {mask_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Render projectiles from registry JSON')
    parser.add_argument('--registry', required=True, help='Path to projectile registry JSON')
    parser.add_argument('--projectile-id', help='Specific projectile ID to render (renders all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for spritesheets')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    projectiles = registry.get('projectiles', [])
    
    if args.projectile_id:
        projectiles = [p for p in projectiles if p['id'] == args.projectile_id]
    
    for projectile in projectiles:
        print(f"Rendering projectile: {projectile['id']}")
        create_spritesheet(projectile, args.output_dir)
    
    print("Rendering complete!")

if __name__ == "__main__":
    main()


