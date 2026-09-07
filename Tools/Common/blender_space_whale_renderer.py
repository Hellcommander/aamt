"""
Blender Space Whale Ship Renderer
Renders playable space whale ships with bioluminescent materials, breathing animations,
modular sections, and orbit field effects.
Exports as spritesheets for Transcendence.
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

def create_bioluminescent_material(materials_config, frame_time):
    """Create bioluminescent skin material with subsurface scattering and vein flow"""
    mat = bpy.data.materials.new(name="BioluminescentSkin")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (800, 0)
    
    # Principled BSDF for base material
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    # Base color
    base_color = hex_to_rgb(materials_config.get('baseColor', '#1a2a3a'))
    principled.inputs['Base Color'].default_value = (*base_color, 1.0)
    
    # Subsurface scattering
    if materials_config.get('subsurfaceScattering', True):
        principled.inputs['Subsurface'].default_value = 0.3
        principled.inputs['Subsurface Radius'].default_value = (0.1, 0.1, 0.1)
        subsurface_color = hex_to_rgb(materials_config.get('baseColor', '#1a2a3a'))
        principled.inputs['Subsurface Color'].default_value = (*subsurface_color, 1.0)
    
    # Emission for bioluminescence
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (200, -200)
    
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
    
    # Combine base and emission
    mix = nodes.new(type='ShaderNodeMix')
    mix.location = (400, 0)
    mix.data_type = 'RGBA'
    mix.blend_type = 'ADD'
    mix.inputs['Factor'].default_value = 0.6
    
    # Connect nodes
    links.new(noise_tex.outputs['Fac'], mix.inputs['A'])
    links.new(principled.outputs['BSDF'], mix.inputs[6])
    links.new(emission.outputs['Emission'], mix.inputs[7])
    links.new(mix.outputs['Result'], output.inputs['Surface'])
    
    return mat

def create_carapace_material(materials_config):
    """Create carapace plating material"""
    mat = bpy.data.materials.new(name="CarapacePlating")
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    carapace_color = hex_to_rgb(materials_config.get('carapaceColor', '#4a5a6a'))
    principled.inputs['Base Color'].default_value = (*carapace_color, 1.0)
    principled.inputs['Metallic'].default_value = 0.3
    principled.inputs['Roughness'].default_value = 0.6
    
    # Rim glow
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (200, -200)
    emission.inputs['Color'].default_value = (*carapace_color, 1.0)
    emission.inputs['Strength'].default_value = 1.5
    
    mix = nodes.new(type='ShaderNodeMix')
    mix.location = (200, 0)
    mix.data_type = 'RGBA'
    mix.inputs['Factor'].default_value = 0.3
    
    links.new(principled.outputs['BSDF'], mix.inputs[6])
    links.new(emission.outputs['Emission'], mix.inputs[7])
    links.new(mix.outputs['Result'], output.inputs['Surface'])
    
    return mat

def create_ship_module(module_config, visual_config):
    """Create a modular ship section"""
    module_type = module_config.get('type', 'mid')
    pos = module_config.get('position', {})
    
    if module_type == 'head':
        # Create streamlined head shape
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'head')
        # Scale to be more elongated
        obj.scale = (1.2, 0.8, 1.5)
        
    elif module_type == 'mid':
        # Create mid-section (cylindrical)
        bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'mid')
        obj.scale = (1.0, 1.0, 1.2)
        
    elif module_type == 'belly':
        # Create belly bay (wider, flatter)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, subdivisions=3)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'belly')
        obj.scale = (1.5, 1.5, 0.6)
        
    elif module_type == 'tail':
        # Create tail (tapered)
        bpy.ops.mesh.primitive_cone_add(radius1=0.8, radius2=0.2, depth=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'tail')
        obj.rotation_euler = (math.radians(90), 0, 0)
        
    elif module_type == 'dorsalCrest':
        # Create dorsal crest (fin-like)
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'dorsalCrest')
        obj.scale = (0.3, 1.5, 1.0)
        obj.rotation_euler = (math.radians(90), 0, 0)
        
    else:
        # Default: sphere
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        obj = bpy.context.active_object
        obj.name = module_config.get('name', 'module')
    
    # Position module
    obj.location = (pos.get('x', 0), pos.get('y', 0), pos.get('z', 0))
    
    return obj

def create_gill_vent(visual_config, index, total):
    """Create a gill vent mesh"""
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.1)
    obj = bpy.context.active_object
    obj.name = f"GillVent_{index}"
    
    # Position along side of ship
    angle = (index / total) * 2 * math.pi
    radius = 1.2
    obj.location = (math.cos(angle) * radius, math.sin(angle) * radius, 0)
    obj.rotation_euler = (math.radians(90), angle, 0)
    
    return obj

def apply_breathing_animation(obj, frame_time, breathing_config):
    """Apply breathing expansion animation to object"""
    if not breathing_config.get('breathingEnabled', True):
        return
    
    speed = breathing_config.get('breathingSpeed', 0.8)
    amplitude = breathing_config.get('breathingAmplitude', 0.05)
    
    # Breathing cycle
    breath = 1.0 + math.sin(frame_time * speed * 2 * math.pi) * amplitude
    
    # Apply to scale
    obj.scale = (obj.scale.x * breath, obj.scale.y * breath, obj.scale.z * breath)

def setup_camera_and_lighting(size):
    """Setup orthographic camera and lighting for ship rendering"""
    # Camera
    bpy.ops.object.camera_add(location=(0, -size * 3, size * 2))
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = size * 6
    camera.rotation_euler = (math.radians(60), 0, math.radians(45))
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

def render_ship_frame(ship_data, output_path, frame_idx, total_frames, size):
    """Render a single frame of the space whale ship"""
    visual = ship_data['visual']
    animations = visual.get('animations', {})
    materials = visual.get('materials', {})
    modules = visual.get('modules', [])
    
    # Calculate frame time
    frame_time = frame_idx / total_frames
    
    # Clear scene
    clear_scene()
    
    # Create materials
    skin_mat = create_bioluminescent_material(materials, frame_time)
    carapace_mat = create_carapace_material(materials)
    
    # Create ship modules
    ship_objects = []
    for module_config in modules:
        module_obj = create_ship_module(module_config, visual)
        
        # Apply material based on module type
        if module_config.get('type') in ['head', 'mid', 'belly', 'tail']:
            module_obj.data.materials.append(skin_mat)
        else:
            module_obj.data.materials.append(carapace_mat)
        
        # Apply breathing animation
        apply_breathing_animation(module_obj, frame_time, animations)
        
        ship_objects.append(module_obj)
    
    # Create gill vents
    gill_count = animations.get('gillVentCount', 6)
    for i in range(gill_count):
        gill = create_gill_vent(visual, i, gill_count)
        gill.data.materials.append(skin_mat)
        
        # Animate gill pulse
        pulse_speed = animations.get('gillPulseSpeed', 1.5)
        pulse = 0.5 + 0.5 * math.sin(frame_time * pulse_speed * 2 * math.pi + i)
        gill.scale = (pulse, pulse, pulse)
        
        ship_objects.append(gill)
    
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

def create_ship_spritesheet(ship_data, output_dir, frames=16):
    """Create complete ship spritesheet with breathing animation"""
    visual = ship_data['visual']
    silhouette = visual.get('silhouette', {})
    
    # Calculate size based on ship dimensions
    length = silhouette.get('length', 8.0)
    width = silhouette.get('width', 3.5)
    size = int(max(length, width) * 64)  # Scale to pixels
    
    # Ensure absolute path
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Render frames
    temp_dir = os.path.join(output_dir, 'temp_frames')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    
    for frame_idx in range(frames):
        frame_path = os.path.join(temp_dir, f"frame_{frame_idx:02d}.png")
        render_ship_frame(ship_data, frame_path, frame_idx, frames, size)
        frame_files.append(frame_path)
    
    # Composite into spritesheet using Blender's image API
    spritesheet_width = frames * size
    spritesheet_height = size
    
    # Create spritesheet image in Blender
    spritesheet = bpy.data.images.new(
        name=f"{ship_data['id']}_spritesheet",
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
                    frame_idx_px = (y * size + x) * 4
                    if frame_idx_px < len(frame_img.pixels):
                        r = frame_img.pixels[frame_idx_px]
                        g = frame_img.pixels[frame_idx_px + 1]
                        b = frame_img.pixels[frame_idx_px + 2]
                        a = frame_img.pixels[frame_idx_px + 3]
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
    output_path = os.path.join(output_dir, f"{ship_data['id']}.png")
    spritesheet.filepath = output_path
    spritesheet.file_format = 'PNG'
    spritesheet.save()
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"Ship spritesheet saved: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Render space whale ship from registry JSON')
    parser.add_argument('--registry', required=True, help='Path to ship registry JSON')
    parser.add_argument('--ship-id', help='Specific ship ID to render (renders all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for spritesheets')
    parser.add_argument('--frames', type=int, default=16, help='Number of animation frames')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    ships = registry.get('ships', [])
    
    if args.ship_id:
        ships = [s for s in ships if s['id'] == args.ship_id]
    
    for ship in ships:
        print(f"Rendering ship: {ship['id']}")
        create_ship_spritesheet(ship, args.output_dir, args.frames)
    
    print("Rendering complete!")

if __name__ == "__main__":
    main()

