"""
Blender Shield Aura Renderer
Renders solar wind shield aura with alpha noise, wind streams, distortion, and orbital particles.
Exports as animated spritesheet for Transcendence.
"""

import bpy
import sys
import os
import json
import argparse
import math
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

def create_aura_material(visual_config, frame_time, shield_hp=1.0):
    """Create shield aura material with alpha noise"""
    mat = bpy.data.materials.new(name="AuraMaterial")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (600, 0)
    
    # Emission shader for glow
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (0, 0)
    
    # Base color
    base_color = hex_to_rgb(visual_config.get('baseColor', '#66ccff'))
    emission.inputs['Color'].default_value = (*base_color, 1.0)
    
    # Intensity scaled with shield HP
    intensity = 2.0 * shield_hp
    emission.inputs['Strength'].default_value = intensity
    
    # Alpha noise using noise texture
    noise_tex = nodes.new(type='ShaderNodeTexNoise')
    noise_tex.location = (-400, -200)
    noise_tex.inputs['Scale'].default_value = visual_config.get('alphaNoiseScale', 3.2)
    noise_tex.inputs['Detail'].default_value = 5.0
    noise_tex.inputs['Roughness'].default_value = 0.5
    
    # Animate noise
    time_node = nodes.new(type='ShaderNodeValue')
    time_node.outputs[0].default_value = frame_time * visual_config.get('alphaNoiseSpeed', 1.8)
    
    # Simplified: Use noise directly for intensity variation
    # Full implementation would use geometry nodes for proper radial mask
    # For now, multiply noise with base intensity
    math_mult = nodes.new(type='ShaderNodeMath')
    math_mult.location = (200, 0)
    math_mult.operation = 'MULTIPLY'
    
    # Base intensity scaled with shield HP
    base_intensity = 2.0 * shield_hp
    math_mult.inputs[0].default_value = base_intensity
    math_mult.inputs[1].default_value = visual_config.get('alphaNoiseStrength', 0.6)
    
    # Connect noise to multiply
    links.new(noise_tex.outputs['Fac'], math_mult.inputs[1])
    links.new(math_mult.outputs['Value'], emission.inputs['Strength'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_wind_stream_material(visual_config, frame_time):
    """Create solar wind stream material"""
    mat = bpy.data.materials.new(name="WindStreamMaterial")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (0, 0)
    
    wind_color = hex_to_rgb(visual_config.get('windColor', '#aaffff'))
    emission.inputs['Color'].default_value = (*wind_color, 1.0)
    emission.inputs['Strength'].default_value = 1.5
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_orbital_particle_material(visual_config):
    """Create material for orbital particles"""
    mat = bpy.data.materials.new(name="OrbitalParticleMaterial")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (0, 0)
    
    base_color = hex_to_rgb(visual_config.get('baseColor', '#66ccff'))
    emission.inputs['Color'].default_value = (*base_color, 1.0)
    emission.inputs['Strength'].default_value = 3.0
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_aura_mesh(radius, segments=64):
    """Create aura mesh (sphere or disk)"""
    # Create sphere for 3D aura
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=radius)
    obj = bpy.context.active_object
    obj.name = "Aura"
    obj.location = (0, 0, 0)
    return obj

def create_wind_streak_mesh(radius, count=12):
    """Create wind streak meshes"""
    streaks = []
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        # Create small elongated mesh for streak
        bpy.ops.mesh.primitive_cube_add(size=0.1)
        obj = bpy.context.active_object
        obj.name = f"WindStreak_{i}"
        obj.location = (math.cos(angle) * radius * 0.7, math.sin(angle) * radius * 0.7, 0)
        obj.scale = (1.0, 3.0, 0.1)  # Elongated
        obj.rotation_euler = (0, 0, angle)
        streaks.append(obj)
    return streaks

def setup_orbital_particles(obj, particles_config, frame_time, shield_hp=1.0):
    """Setup Blender particle system for orbital particles"""
    mod = obj.modifiers.new(name="OrbitalParticles", type='PARTICLE_SYSTEM')
    psys = obj.particle_systems[0]
    settings = psys.settings
    
    # Configure particles
    orbit_count = particles_config.get('orbitCount', 24)
    settings.count = orbit_count
    settings.frame_start = 1
    settings.frame_end = 1
    settings.lifetime = particles_config.get('particleLifetime', 5.0) * 30  # Convert to frames
    
    # Emission
    settings.emit_from = 'VERT'
    settings.use_emit_random = True
    
    # Velocity - orbital motion
    orbit_speed = particles_config.get('orbitSpeedMin', 0.4) + \
                  (particles_config.get('orbitSpeedMax', 1.6) - particles_config.get('orbitSpeedMin', 0.4)) * shield_hp
    settings.normal_factor = orbit_speed
    settings.factor_random = 0.3
    
    # Size
    settings.particle_size = particles_config.get('particleSize', 0.04)
    settings.size_random = 0.2
    
    # Material - assign material index instead
    mat = create_orbital_particle_material({})
    # In Blender 5.0, assign material to object first, then use material index
    obj.data.materials.append(mat)
    settings.material = len(obj.data.materials) - 1
    
    return psys

def setup_camera_and_lighting(size):
    """Setup orthographic camera and lighting"""
    # Camera
    bpy.ops.object.camera_add(location=(0, 0, size * 2))
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = size * 4
    camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = camera
    
    # Minimal lighting for additive effects
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 1.0

def apply_radius_scaling(radius_min, radius_max, shield_hp, curve_type="smooth"):
    """Calculate current radius based on shield HP"""
    if curve_type == "linear":
        return radius_min + (radius_max - radius_min) * shield_hp
    elif curve_type == "exponential":
        return radius_min + (radius_max - radius_min) * (shield_hp ** 2)
    elif curve_type == "logarithmic":
        return radius_min + (radius_max - radius_min) * (1.0 - (1.0 - shield_hp) ** 0.5)
    else:  # smooth
        t = shield_hp * shield_hp * (3.0 - 2.0 * shield_hp)  # Smoothstep
        return radius_min + (radius_max - radius_min) * t

def render_aura_frame(aura_data, output_path, frame_idx, total_frames, size, shield_hp=1.0):
    """Render a single aura frame"""
    visual = aura_data['visual']
    particles = aura_data.get('particles', {})
    behavior = aura_data.get('behavior', {})
    
    # Calculate frame time
    frame_time = frame_idx / total_frames
    
    # Calculate current radius
    radius_curve = behavior.get('radiusScaleCurve', 'smooth')
    current_radius = apply_radius_scaling(
        visual.get('radiusMin', 1.2),
        visual.get('radiusMax', 2.4),
        shield_hp,
        radius_curve
    )
    
    # Clear scene
    clear_scene()
    
    # Create aura mesh
    if 'base' in visual.get('layers', ['base']):
        aura_obj = create_aura_mesh(current_radius * size * 0.1)
        aura_mat = create_aura_material(visual, frame_time, shield_hp)
        aura_obj.data.materials.append(aura_mat)
        aura_obj.scale = (current_radius, current_radius, current_radius)
    
    # Create wind streaks
    if 'wind' in visual.get('layers', ['wind']):
        wind_count = visual.get('windStreakCount', 12)
        wind_streaks = create_wind_streak_mesh(current_radius * size * 0.1, wind_count)
        wind_mat = create_wind_stream_material(visual, frame_time)
        for streak in wind_streaks:
            streak.data.materials.append(wind_mat)
    
    # Setup orbital particles
    if 'particles' in visual.get('layers', ['particles']):
        # Create particle emitter
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=current_radius * size * 0.1)
        particle_emitter = bpy.context.active_object
        particle_emitter.name = "ParticleEmitter"
        setup_orbital_particles(particle_emitter, particles, frame_time, shield_hp)
    
    # Setup camera and lighting
    setup_camera_and_lighting(size)
    
    # Render
    bpy.context.scene.render.resolution_x = size
    bpy.context.scene.render.resolution_y = size
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.frame_set(frame_idx + 1)
    
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)

def generate_mask_from_alpha(image_path, mask_path):
    """Generate black/white mask from image alpha channel
    Mask format: Black background with white aura outline (negative/outline image)
    """
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    
    if img.mode == 'RGBA':
        # Extract alpha channel
        alpha = img.split()[3]
        alpha_array = np.array(alpha)
        
        # Create mask: white where aura is (alpha > 0), black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Where alpha > 0, set to white (255, 255, 255)
        aura_pixels = alpha_array > 0
        mask_array[aura_pixels] = [255, 255, 255]
        
        # Convert to PIL Image
        mask = Image.fromarray(mask_array, 'RGB')
        
        # Save as BMP
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white aura outline)")
        return True
    elif img.mode == 'RGB':
        # For RGB images, create mask based on non-black pixels
        img_array = np.array(img)
        
        # Create mask: white where image is not black, black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Find non-black pixels (aura)
        non_black = np.any(img_array > [10, 10, 10], axis=2)  # Threshold to ignore near-black
        mask_array[non_black] = [255, 255, 255]
        
        mask = Image.fromarray(mask_array, 'RGB')
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white aura outline)")
        return True
    else:
        print(f"Warning: Image {image_path} format not supported for mask generation")
        return False

def create_aura_spritesheet(aura_data, output_dir, shield_hp_levels=[0.0, 0.25, 0.5, 0.75, 1.0]):
    """Create aura spritesheet with multiple shield HP levels"""
    visual = aura_data['visual']
    size = visual.get('spriteSize', 64)
    frames = visual.get('frames', 12)
    
    # Ensure absolute path for Blender
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Render frames for each shield HP level
    temp_dir = os.path.join(output_dir, 'temp_frames')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    
    for hp_level in shield_hp_levels:
        for frame_idx in range(frames):
            frame_path = os.path.join(temp_dir, f"hp_{hp_level:.2f}_frame_{frame_idx:02d}.png")
            render_aura_frame(aura_data, frame_path, frame_idx, frames, size, hp_level)
            frame_files.append((hp_level, frame_idx, frame_path))
    
    # Composite into spritesheet using Blender's image API
    # Arrange: frames horizontally, HP levels vertically
    spritesheet_width = frames * size
    spritesheet_height = len(shield_hp_levels) * size
    
    # Create spritesheet image in Blender
    spritesheet = bpy.data.images.new(
        name=f"{aura_data['id']}_spritesheet",
        width=spritesheet_width,
        height=spritesheet_height,
        alpha=True
    )
    
    # Initialize with transparent pixels
    pixels = [0.0] * (spritesheet_width * spritesheet_height * 4)
    spritesheet.pixels = pixels
    
    # Load and composite each frame
    for hp_level, frame_idx, frame_path in frame_files:
        if os.path.exists(frame_path):
            # Load frame image
            frame_img = bpy.data.images.load(frame_path)
            
            # Calculate position in spritesheet
            hp_index = shield_hp_levels.index(hp_level)
            x_offset = frame_idx * size
            y_offset = hp_index * size
            
            # Copy pixels from frame to spritesheet
            for y in range(size):
                for x in range(size):
                    # Get pixel from frame
                    frame_idx_px = (y * size + x) * 4
                    if frame_idx_px < len(frame_img.pixels):
                        r = frame_img.pixels[frame_idx_px]
                        g = frame_img.pixels[frame_idx_px + 1]
                        b = frame_img.pixels[frame_idx_px + 2]
                        a = frame_img.pixels[frame_idx_px + 3]
                    else:
                        r, g, b, a = 0.0, 0.0, 0.0, 0.0
                    
                    # Set pixel in spritesheet
                    sheet_idx = ((y_offset + y) * spritesheet_width + x_offset + x) * 4
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
    output_path = os.path.join(output_dir, f"{aura_data['id']}.png")
    spritesheet.filepath = output_path
    spritesheet.file_format = 'PNG'
    spritesheet.save()
    
    # Generate negative/outline mask for Transcendence (BMP format)
    # Always generate mask for spritesheets (black background, white aura outline)
    mask_path = os.path.join(output_dir, f"{aura_data['id']}Mask.bmp")
    print(f"Generating spritesheet mask (negative/outline)...")
    if os.path.exists(output_path):
        generate_mask_from_alpha(output_path, mask_path)
    
    # Generate distortion map if needed (gradient from alpha)
    if visual.get('distortionStrength', 0) > 0 and os.path.exists(output_path):
        distortion_path = os.path.join(output_dir, f"{aura_data['id']}_distort.png")
        try:
            from PIL import Image
            import numpy as np
            src = Image.open(output_path).convert('RGBA')
            a = np.array(src.split()[3], dtype=np.float32) / 255.0
            gy, gx = np.gradient(a)
            strength = float(visual.get('distortionStrength', 1.0))
            mag = np.clip(np.sqrt(gx*gx + gy*gy) * 8.0 * strength, 0, 1)
            d = np.zeros((a.shape[0], a.shape[1], 3), dtype=np.uint8)
            d[..., 0] = ((gx / (np.abs(gx).max() + 1e-6) * 0.5 + 0.5) * 255).astype(np.uint8)
            d[..., 1] = ((gy / (np.abs(gy).max() + 1e-6) * 0.5 + 0.5) * 255).astype(np.uint8)
            d[..., 2] = (mag * 255).astype(np.uint8)
            Image.fromarray(d, 'RGB').save(distortion_path)
            print(f"Distortion map saved: {distortion_path}")
        except Exception as e:
            print(f"Distortion map generation failed: {e}")
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"Aura spritesheet saved: {output_path}")
    print(f"Aura spritesheet mask (negative/outline) saved: {mask_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Render shield aura from registry JSON')
    parser.add_argument('--registry', required=True, help='Path to aura registry JSON')
    parser.add_argument('--aura-id', help='Specific aura ID to render (renders all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for spritesheets')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    auras = registry.get('auras', [])
    
    if args.aura_id:
        auras = [a for a in auras if a['id'] == args.aura_id]
    
    for aura in auras:
        print(f"Rendering aura: {aura['id']}")
        create_aura_spritesheet(aura, args.output_dir)
    
    print("Rendering complete!")

if __name__ == "__main__":
    main()

