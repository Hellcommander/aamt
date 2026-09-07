"""
Blender Nova Drift Style FX Renderer
Generates layered special effects: core glow, shockwave ring, distortion, particles, bloom.
Exports as animated spritesheet for Transcendence.
"""

import bpy
import sys
import os
import json
import argparse
from math import radians, sin, cos, pi
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

def create_core_glow_material(visual_config, frame_time):
    """Create core glow material with emission and pulse"""
    mat = bpy.data.materials.new(name="CoreGlow")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    # Emission shader
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (0, 0)
    
    # Color
    core_color = hex_to_rgb(visual_config.get('coreColor', '#ff66ff'))
    emission.inputs['Color'].default_value = (*core_color, 1.0)
    
    # Intensity with pulse
    core_glow = visual_config.get('coreGlow', {})
    intensity = core_glow.get('intensity', 3.0)
    
    if core_glow.get('pulse', True):
        # Add pulse animation
        pulse = 0.5 + 0.5 * sin(frame_time * 10.0)
        intensity *= (0.8 + 0.2 * pulse)
    
    emission.inputs['Strength'].default_value = intensity
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_shockwave_material(visual_config):
    """Create shockwave ring material"""
    mat = bpy.data.materials.new(name="Shockwave")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    # Emission
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (0, 0)
    
    shockwave_color = hex_to_rgb(visual_config.get('shockwaveColor', '#ff99ff'))
    emission.inputs['Color'].default_value = (*shockwave_color, 1.0)
    emission.inputs['Strength'].default_value = 2.0
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_core_mesh(radius, segments=64):
    """Create core glow mesh (sphere)"""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=radius)
    obj = bpy.context.active_object
    obj.name = "CoreGlow"
    obj.location = (0, 0, 0)
    return obj

def create_shockwave_mesh(radius, thickness, segments=64):
    """Create shockwave ring mesh (torus)"""
    # Create torus for ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=thickness,
        major_segments=segments,
        minor_segments=8
    )
    obj = bpy.context.active_object
    obj.name = "Shockwave"
    obj.location = (0, 0, 0)
    obj.rotation_euler = (radians(90), 0, 0)  # Rotate to face camera
    return obj

def create_distortion_map(visual_config, output_path, size=256):
    """Generate distortion map texture"""
    # This would create a procedural distortion texture
    # For now, create a simple noise-based texture
    noise_type = visual_config.get('noiseType', 'perlin')
    noise_scale = visual_config.get('noiseScale', 4.0)
    
    # Create image
    image = bpy.data.images.new(name="DistortionMap", width=size, height=size)
    pixels = [0.0] * (size * size * 4)
    
    # Generate noise pattern
    for y in range(size):
        for x in range(size):
            nx = x / size * noise_scale
            ny = y / size * noise_scale
            
            # Simple noise (would use proper Perlin/Voronoi in production)
            value = sin(nx * 10) * cos(ny * 10) * 0.5 + 0.5
            
            idx = (y * size + x) * 4
            pixels[idx] = value  # R
            pixels[idx + 1] = value  # G
            pixels[idx + 2] = 0.5  # B
            pixels[idx + 3] = 1.0  # A
    
    image.pixels = pixels
    image.filepath = output_path
    image.file_format = 'PNG'
    image.save()
    
    return image

def setup_particle_system(obj, particles_config, frame_time):
    """Setup Blender particle system for FX particles"""
    # Add particle system
    mod = obj.modifiers.new(name="Particles", type='PARTICLE_SYSTEM')
    psys = obj.particle_systems[0]
    settings = psys.settings
    
    # Configure particles
    settings.count = particles_config.get('burstCount', 24)
    settings.frame_start = 1
    settings.frame_end = 1
    settings.lifetime = particles_config.get('lifetimeMax', 0.6) * 30  # Convert to frames
    
    # Emission
    settings.emit_from = 'VERT'
    settings.use_emit_random = True
    
    # Velocity
    settings.normal_factor = particles_config.get('burstSpeedMax', 2.4)
    settings.factor_random = 0.5
    
    # Size
    settings.particle_size = particles_config.get('sizeMax', 0.08)
    settings.size_random = 0.5
    
    # Material
    mat = bpy.data.materials.new(name="ParticleMaterial")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    output = nodes.new(type='ShaderNodeOutputMaterial')
    emission = nodes.new(type='ShaderNodeEmission')
    
    # Use core color for particles
    core_color = hex_to_rgb(particles_config.get('color', '#ffffff'))
    emission.inputs['Color'].default_value = (*core_color, 1.0)
    emission.inputs['Strength'].default_value = 3.0
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    settings.material = mat
    
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
    
    # Lighting (minimal for additive effects)
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 1.0

def apply_easing(value, ease_type):
    """Apply easing curve to value (0.0-1.0)"""
    if ease_type == "linear":
        return value
    elif ease_type == "easeIn":
        return value * value
    elif ease_type == "easeOut":
        return 1.0 - (1.0 - value) * (1.0 - value)
    elif ease_type == "easeInOut":
        if value < 0.5:
            return 2 * value * value
        else:
            return 1.0 - 2 * (1.0 - value) * (1.0 - value)
    else:
        return value

def render_fx_frame(fx_data, output_path, frame_idx, total_frames, size):
    """Render a single FX frame with all layers"""
    visual = fx_data['visual']
    timing = fx_data.get('timing', {})
    particles = fx_data.get('particles', {})
    
    # Calculate frame time (0.0-1.0)
    frame_time = frame_idx / total_frames
    
    # Calculate expansion based on timing
    core_expand_time = timing.get('coreExpandTime', 0.12)
    shockwave_expand_time = timing.get('shockwaveExpandTime', 0.18)
    fade_out_time = timing.get('fadeOutTime', 0.3)
    
    total_duration = core_expand_time + fade_out_time
    normalized_time = frame_time * total_duration
    
    # Core expansion
    if normalized_time <= core_expand_time:
        core_progress = normalized_time / core_expand_time
        core_progress = apply_easing(core_progress, timing.get('easeIn', 'easeOut'))
        core_scale = 0.1 + core_progress * 0.9
    else:
        core_scale = 1.0
    
    # Shockwave expansion
    if normalized_time <= shockwave_expand_time:
        shockwave_progress = normalized_time / shockwave_expand_time
        shockwave_progress = apply_easing(shockwave_progress, timing.get('easeIn', 'easeOut'))
        shockwave_radius = 0.3 + shockwave_progress * 1.5
    else:
        shockwave_radius = 1.8
    
    # Fade out
    fade_start = core_expand_time
    if normalized_time > fade_start:
        fade_progress = (normalized_time - fade_start) / fade_out_time
        fade_progress = apply_easing(fade_progress, timing.get('easeOut', 'easeIn'))
        alpha = 1.0 - fade_progress
    else:
        alpha = 1.0
    
    # Clear scene
    clear_scene()
    
    # Create core glow
    if 'core' in visual.get('layers', []):
        core_obj = create_core_mesh(size * 0.3 * core_scale)
        core_mat = create_core_glow_material(visual, frame_time)
        core_obj.data.materials.append(core_mat)
        core_obj.scale = (core_scale, core_scale, core_scale)
    
    # Create shockwave
    if 'shockwave' in visual.get('layers', []):
        shockwave_config = visual.get('shockwave', {})
        thickness = shockwave_config.get('thickness', 0.02) * size
        shockwave_obj = create_shockwave_mesh(shockwave_radius * size * 0.5, thickness)
        shockwave_mat = create_shockwave_material(visual)
        shockwave_obj.data.materials.append(shockwave_mat)
        shockwave_obj.scale = (shockwave_radius, shockwave_radius, shockwave_radius)
    
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

def create_fx_spritesheet(fx_data, output_dir):
    """Create complete FX spritesheet from registry data"""
    visual = fx_data['visual']
    size = visual.get('spriteSize', 64)
    frames = visual.get('frames', 12)
    
    # Ensure absolute path for Blender
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Render frames
    temp_dir = os.path.join(output_dir, 'temp_frames')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    
    for frame_idx in range(frames):
        frame_path = os.path.join(temp_dir, f"frame_{frame_idx:02d}.png")
        render_fx_frame(fx_data, frame_path, frame_idx, frames, size)
        frame_files.append(frame_path)
    
    # Composite into spritesheet using Blender's image API
    spritesheet_width = frames * size
    spritesheet_height = size
    
    # Create spritesheet image in Blender
    spritesheet = bpy.data.images.new(
        name=f"{fx_data['id']}_spritesheet",
        width=spritesheet_width,
        height=spritesheet_height,
        alpha=True
    )
    
    # Initialize with transparent pixels
    pixels = [0.0] * (spritesheet_width * spritesheet_height * 4)
    spritesheet.pixels = pixels
    
    # Load and composite each frame
    for idx, frame_path in enumerate(frame_files):
        if os.path.exists(frame_path):
            # Load frame image
            frame_img = bpy.data.images.load(frame_path)
            
            # Calculate position in spritesheet
            x_offset = idx * size
            
            # Copy pixels from frame to spritesheet
            for y in range(size):
                for x in range(size):
                    # Get pixel from frame
                    frame_idx = (y * size + x) * 4
                    if frame_idx < len(frame_img.pixels):
                        r = frame_img.pixels[frame_idx]
                        g = frame_img.pixels[frame_idx + 1]
                        b = frame_img.pixels[frame_idx + 2]
                        a = frame_img.pixels[frame_idx + 3]
                    else:
                        r, g, b, a = 0.0, 0.0, 0.0, 0.0
                    
                    # Set pixel in spritesheet
                    sheet_idx = (y * spritesheet_width + x_offset + x) * 4
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
    output_path = os.path.join(output_dir, f"{fx_data['id']}.png")
    spritesheet.filepath = output_path
    spritesheet.file_format = 'PNG'
    spritesheet.save()
    
    # Generate distortion map if needed
    if visual.get('distortionStrength', 0) > 0:
        distortion_path = os.path.join(output_dir, f"{fx_data['id']}_distort.png")
        create_distortion_map(visual, distortion_path, size)
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"FX spritesheet saved: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Render Nova Drift style FX from registry JSON')
    parser.add_argument('--registry', required=True, help='Path to FX registry JSON')
    parser.add_argument('--fx-id', help='Specific FX ID to render (renders all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for spritesheets')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    effects = registry.get('effects', [])
    
    if args.fx_id:
        effects = [e for e in effects if e['id'] == args.fx_id]
    
    for effect in effects:
        print(f"Rendering FX: {effect['id']}")
        create_fx_spritesheet(effect, args.output_dir)
    
    print("Rendering complete!")

if __name__ == "__main__":
    main()

