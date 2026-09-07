"""
Blender Shield Renderer
Renders shield visuals with procedural node groups for rim, pulse, distortion.
Exports sprite strips for fallback and normal maps for lighting.
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

def create_shield_material(visual_config, output_dir):
    """Create procedural shield material with node groups"""
    mat_name = "ShieldMaterial"
    mat = bpy.data.materials.new(name=mat_name)
    # Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (600, 0)
    
    # Create node group for shield rim
    rim_group = create_shield_rim_group(visual_config)
    
    # Create node group for pulse effect
    pulse_group = create_pulse_group(visual_config)
    
    # Create node group for distortion
    if visual_config.get('distortionStrength', 0) > 0:
        distortion_group = create_distortion_group(visual_config)
    
    # Add group instances
    rim_node = nodes.new(type='ShaderNodeGroup')
    rim_node.node_tree = rim_group
    rim_node.location = (0, 0)
    
    pulse_node = nodes.new(type='ShaderNodeGroup')
    pulse_node.node_tree = pulse_group
    pulse_node.location = (0, -200)
    
    # Mix rim and pulse
    mix = nodes.new(type='ShaderNodeMixShader')
    mix.location = (400, 0)
    mix.inputs['Fac'].default_value = 0.7
    
    # Emission for glow
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (200, -100)
    
    # Set colors
    base_color = hex_to_rgb(visual_config.get('color', '#66ccff'))
    glow_color = hex_to_rgb(visual_config.get('glowColor', '#aaffff'))
    
    emission.inputs['Color'].default_value = (*glow_color, 1.0)
    emission.inputs['Strength'].default_value = visual_config.get('pulseStrength', 0.5) * 3.0
    
    # Connect nodes
    links.new(rim_node.outputs[0], mix.inputs[1])
    links.new(pulse_node.outputs[0], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    
    # Save node groups to .blend
    blend_path = os.path.join(output_dir, 'shield_node_groups.blend')
    bpy.data.libraries.write(blend_path, {rim_group, pulse_group}, fake_user=True)
    
    return mat

def create_shield_rim_group(visual_config):
    """Create node group for shield rim effect"""
    group = bpy.data.node_groups.new(name="ShieldRim", type='ShaderNodeTree')
    
    # Inputs
    group.inputs.new('NodeSocketFloat', 'Radius')
    group.inputs.new('NodeSocketFloat', 'Thickness')
    group.inputs.new('NodeSocketVector', 'Position')
    
    # Outputs
    group.outputs.new('NodeSocketFloat', 'Rim Mask')
    
    # Nodes
    nodes = group.nodes
    links = group.links
    
    # Input node
    input_node = nodes.new(type='NodeGroupInput')
    input_node.location = (-400, 0)
    
    # Geometry node
    geometry = nodes.new(type='ShaderNodeNewGeometry')
    geometry.location = (-400, -200)
    
    # Vector math for distance
    distance = nodes.new(type='ShaderNodeVectorMath')
    distance.location = (-200, 0)
    distance.operation = 'DISTANCE'
    
    # Map range for rim
    map_range = nodes.new(type='ShaderNodeMapRange')
    map_range.location = (0, 0)
    map_range.inputs['From Min'].default_value = visual_config.get('radius', 1.6) - visual_config.get('thickness', 0.08)
    map_range.inputs['From Max'].default_value = visual_config.get('radius', 1.6)
    map_range.inputs['To Min'].default_value = 1.0
    map_range.inputs['To Max'].default_value = 0.0
    
    # Output node
    output_node = nodes.new(type='NodeGroupOutput')
    output_node.location = (200, 0)
    
    # Connect
    links.new(input_node.outputs['Position'], distance.inputs[0])
    links.new(geometry.outputs['Position'], distance.inputs[1])
    links.new(distance.outputs['Value'], map_range.inputs['Value'])
    links.new(map_range.outputs['Result'], output_node.inputs['Rim Mask'])
    
    return group

def create_pulse_group(visual_config):
    """Create node group for pulse animation"""
    group = bpy.data.node_groups.new(name="ShieldPulse", type='ShaderNodeTree')
    
    # Inputs
    group.inputs.new('NodeSocketFloat', 'Time')
    group.inputs.new('NodeSocketFloat', 'Frequency')
    group.inputs.new('NodeSocketFloat', 'Strength')
    
    # Outputs
    group.outputs.new('NodeSocketFloat', 'Pulse')
    
    # Nodes
    nodes = group.nodes
    links = group.links
    
    # Input node
    input_node = nodes.new(type='NodeGroupInput')
    input_node.location = (-400, 0)
    
    # Math nodes for sine wave
    multiply = nodes.new(type='ShaderNodeMath')
    multiply.location = (-200, 0)
    multiply.operation = 'MULTIPLY'
    
    sine = nodes.new(type='ShaderNodeMath')
    sine.location = (0, 0)
    sine.operation = 'SINE'
    
    # Scale and offset
    scale = nodes.new(type='ShaderNodeMath')
    scale.location = (200, 0)
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = 0.5
    
    add = nodes.new(type='ShaderNodeMath')
    add.location = (400, 0)
    add.operation = 'ADD'
    add.inputs[1].default_value = 0.5
    
    # Mix with strength
    mix = nodes.new(type='ShaderNodeMix')
    mix.location = (600, 0)
    mix.data_type = 'FLOAT'
    
    # Output
    output_node = nodes.new(type='NodeGroupOutput')
    output_node.location = (800, 0)
    
    # Connect
    links.new(input_node.outputs['Time'], multiply.inputs[0])
    links.new(input_node.outputs['Frequency'], multiply.inputs[1])
    links.new(multiply.outputs['Value'], sine.inputs[0])
    links.new(sine.outputs['Value'], scale.inputs[0])
    links.new(scale.outputs['Value'], add.inputs[0])
    links.new(add.outputs['Value'], mix.inputs[6])
    links.new(input_node.outputs['Strength'], mix.inputs[0])
    links.new(mix.outputs[2], output_node.inputs['Pulse'])
    
    return group

def create_distortion_group(visual_config):
    """Create node group for visual distortion (noise-driven strength)."""
    group = bpy.data.node_groups.new(name="ShieldDistortion", type='ShaderNodeTree')
    nodes, links = group.nodes, group.links
    inp = nodes.new('NodeGroupInput')
    out = nodes.new('NodeGroupOutput')
    inp.location = (-400, 0)
    out.location = (400, 0)
    if hasattr(group, 'interface'):
        group.interface.new_socket(name='Strength', in_out='INPUT', socket_type='NodeSocketFloat')
        group.interface.new_socket(name='Distortion', in_out='OUTPUT', socket_type='NodeSocketFloat')
    else:
        group.inputs.new('NodeSocketFloat', 'Strength')
        group.outputs.new('NodeSocketFloat', 'Distortion')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 5.0
    noise.location = (-100, 0)
    mul = nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.location = (150, 0)
    links.new(noise.outputs['Fac'], mul.inputs[0])
    try:
        links.new(inp.outputs['Strength'], mul.inputs[1])
    except Exception:
        mul.inputs[1].default_value = float(visual_config.get('distortionStrength', 0.25) or 0.25)
    try:
        links.new(mul.outputs[0], out.inputs['Distortion'])
    except Exception:
        pass
    return group

def create_shield_mesh(radius, segments=64):
    """Create shield mesh (sphere or torus)"""
    clear_scene()
    
    # Create sphere for shield bubble
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=radius)
    obj = bpy.context.active_object
    obj.name = "Shield"
    
    # Center at origin
    obj.location = (0, 0, 0)
    
    return obj

def setup_camera_and_lighting(radius):
    """Setup orthographic camera and lighting for shield"""
    # Camera
    bpy.ops.object.camera_add(location=(0, 0, radius * 2))
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = radius * 4
    camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = camera
    
    # Lighting
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    
    # Rim light
    bpy.ops.object.light_add(type='AREA', location=(-5, -5, 5))
    rim = bpy.context.active_object
    rim.data.energy = 2.0
    rim.data.size = 5.0

def render_shield_frame(output_path, width, height, frame=0, visual_config=None):
    """Render a single shield frame"""
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.frame_set(frame)
    
    # Update material parameters for animation
    if visual_config:
        # Update pulse based on frame
        pulse_freq = visual_config.get('pulseFrequency', 0.9)
        time = frame / 30.0  # Assuming 30 FPS
        # Update material nodes here if needed
    
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)

def generate_mask_from_alpha(image_path, mask_path):
    """Generate black/white mask from image alpha channel
    Mask format: Black background with white shield outline (negative/outline image)
    """
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    
    if img.mode == 'RGBA':
        # Extract alpha channel
        alpha = img.split()[3]
        alpha_array = np.array(alpha)
        
        # Create mask: white where shield is (alpha > 0), black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Where alpha > 0, set to white (255, 255, 255)
        shield_pixels = alpha_array > 0
        mask_array[shield_pixels] = [255, 255, 255]
        
        # Convert to PIL Image
        mask = Image.fromarray(mask_array, 'RGB')
        
        # Save as BMP
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white shield outline)")
        return True
    elif img.mode == 'RGB':
        # For RGB images, create mask based on non-black pixels
        img_array = np.array(img)
        
        # Create mask: white where image is not black, black elsewhere
        mask_array = np.zeros((img.height, img.width, 3), dtype=np.uint8)
        
        # Find non-black pixels (shield)
        non_black = np.any(img_array > [10, 10, 10], axis=2)  # Threshold to ignore near-black
        mask_array[non_black] = [255, 255, 255]
        
        mask = Image.fromarray(mask_array, 'RGB')
        mask.save(mask_path, 'BMP')
        print(f"Mask generated: {mask_path} (black background, white shield outline)")
        return True
    else:
        print(f"Warning: Image {image_path} format not supported for mask generation")
        return False

def create_shield_spritesheet(shield_data, output_dir):
    """Create sprite strip for shield animation"""
    visual = shield_data['visual']
    radius = visual.get('radius', 1.6)
    frames = visual.get('spriteFrames', 8) if visual.get('spriteStrip', False) else 1
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup scene
    clear_scene()
    
    # Create shield mesh
    obj = create_shield_mesh(radius)
    
    # Create material
    material = create_shield_material(visual, output_dir)
    obj.data.materials.append(material)
    
    # Setup camera and lighting
    setup_camera_and_lighting(radius)
    
    # Render frames
    temp_dir = os.path.join(output_dir, 'temp_frames')
    os.makedirs(temp_dir, exist_ok=True)
    
    frame_files = []
    width = 256
    height = 256
    
    for frame_idx in range(frames):
        frame_path = os.path.join(temp_dir, f"frame_{frame_idx:02d}.png")
        render_shield_frame(frame_path, width, height, frame_idx, visual)
        frame_files.append(frame_path)
    
    # Composite into sprite strip
    if frames > 1:
        from PIL import Image
        
        spritesheet_width = frames * width
        spritesheet_height = height
        
        spritesheet = Image.new('RGBA', (spritesheet_width, spritesheet_height), (0, 0, 0, 0))
        
        for idx, frame_path in enumerate(frame_files):
            if os.path.exists(frame_path):
                frame_img = Image.open(frame_path)
                x = idx * width
                spritesheet.paste(frame_img, (x, 0), frame_img)
        
        # Save spritesheet
        output_path = os.path.join(output_dir, f"{shield_data['id']}_spritesheet.png")
        spritesheet.save(output_path, 'PNG')
        
        # Generate negative/outline mask for Transcendence (BMP format)
        # Always generate mask for spritesheets (black background, white shield outline)
        mask_path = os.path.join(output_dir, f"{shield_data['id']}_spritesheetMask.bmp")
        print(f"Generating spritesheet mask (negative/outline)...")
        generate_mask_from_alpha(output_path, mask_path)
        
        print(f"Spritesheet saved: {output_path}")
        print(f"Spritesheet mask (negative/outline) saved: {mask_path}")
    else:
        # Single frame - still generate mask
        if frame_files:
            output_path = frame_files[0]
            mask_path = output_path.replace('.png', 'Mask.bmp')
            print(f"Generating mask (negative/outline)...")
            generate_mask_from_alpha(output_path, mask_path)
            print(f"Mask (negative/outline) saved: {mask_path}")
    
    # Generate normal map if requested (flat tangent-space fallback from alpha)
    if visual.get('normalMap', False):
        try:
            from PIL import Image
            import numpy as np
            src = Image.open(output_path).convert('RGBA')
            a = np.array(src.split()[3], dtype=np.float32) / 255.0
            gy, gx = np.gradient(a)
            nx = -gx
            ny = -gy
            nz = np.ones_like(a)
            nlen = np.sqrt(nx*nx + ny*ny + nz*nz) + 1e-6
            nx, ny, nz = nx/nlen, ny/nlen, nz/nlen
            rgb = np.stack([(nx+1)*127.5, (ny+1)*127.5, (nz+1)*127.5], axis=-1).astype(np.uint8)
            npath = output_path.replace('.png', '_normal.png')
            Image.fromarray(rgb, 'RGB').save(npath)
            print(f"Normal map saved: {npath}")
        except Exception as e:
            print(f"Normal map generation failed: {e}")
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return output_path if frames > 1 else frame_files[0] if frame_files else None

def main():
    parser = argparse.ArgumentParser(description='Render shields from registry JSON')
    parser.add_argument('--registry', required=True, help='Path to shield registry JSON')
    parser.add_argument('--shield-id', help='Specific shield ID to render (renders all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for sprites')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    shields = registry.get('shields', [])
    
    if args.shield_id:
        shields = [s for s in shields if s['id'] == args.shield_id]
    
    for shield in shields:
        print(f"Rendering shield: {shield['id']}")
        create_shield_spritesheet(shield, args.output_dir)
    
    print("Rendering complete!")

if __name__ == "__main__":
    main()

