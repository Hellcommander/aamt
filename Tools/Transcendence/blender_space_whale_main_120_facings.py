#!/usr/bin/env python3
"""
Blender Space Whale Main Ship 120 Facings Renderer
Renders the main space whale ship (256x256) from 120 angles.

Usage:
    blender --background --python blender_space_whale_main_120_facings.py -- \
        --output-dir Output/120Facings \
        --ship-id scSpaceWhale
"""

import bpy
import sys
import json
import os
import math
import argparse
from pathlib import Path
from mathutils import Vector, Euler, Color


def validate_facing_frame(path, min_coverage=0.002, min_luma_variance=8.0):
    """Mechanical quality gate for a single rendered facing (rejects empty/flat
    frames). Returns (ok, reason). Fails safe to OK if PIL is unavailable."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return True, "PIL unavailable; frame QA skipped"
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False, "missing or empty file"
        with Image.open(path) as img:
            img = img.convert("RGBA")
            w, h = img.size
            if w < 2 or h < 2:
                return False, f"degenerate size {w}x{h}"
            alpha = img.split()[3]
            opaque = sum(1 for p in alpha.getdata() if p > 16)
            coverage = opaque / max(1, w * h)
            if coverage < min_coverage:
                return False, f"empty frame (coverage {coverage:.3%})"
            var = ImageStat.Stat(img.convert("RGB").convert("L")).var[0]
            if var < min_luma_variance:
                return False, f"flat frame (luma variance {var:.1f})"
        return True, f"ok (coverage {coverage:.1%})"
    except Exception as exc:  # noqa: BLE001
        return False, f"unreadable ({exc})"


class SpaceWhaleMainRenderer:
    """Renders the main space whale ship with 120 facings for Transcendence."""
    
    def __init__(self, output_dir, ship_id="scSpaceWhale", columns=10, rows=12, 
                 texture_dir=None, frame_size=256):
        self.ship_id = ship_id
        self.output_dir = Path(output_dir)
        self.columns = columns
        self.rows = rows
        self.texture_dir = Path(texture_dir) if texture_dir else None
        self.frame_size = frame_size
        self.total_facings = columns * rows
        self.rotation_step = 360.0 / self.total_facings
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Rendering main space whale ship: {self.ship_id}")
        print(f"Rendering {self.total_facings} facings at {self.rotation_step}° per frame")
    
    def setup_scene(self):
        """Setup Blender scene for rendering."""
        print("Setting up Blender scene...")
        
        # Clear existing scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # Setup render settings
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        
        # Try GPU, fallback to CPU
        try:
            scene.cycles.device = 'GPU'
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'CUDA'  # or 'OPTIX' or 'METAL'
            for device in prefs.devices:
                device.use = True
        except:
            print("  GPU not available, using CPU rendering")
            scene.cycles.device = 'CPU'
        
        scene.cycles.samples = 256  # High quality for main ship
        scene.render.resolution_x = self.frame_size
        scene.render.resolution_y = self.frame_size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
        
        # Denoising for quality
        scene.cycles.use_denoising = True
        
        # Setup world (space background)
        scene.world.use_nodes = True
        world_nodes = scene.world.node_tree.nodes
        world_nodes.clear()
        
        bg_node = world_nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs['Strength'].default_value = 0.0
        
        output_node = world_nodes.new('ShaderNodeOutputWorld')
        scene.world.node_tree.links.new(bg_node.outputs['Background'], 
                                        output_node.inputs['Surface'])
        
        print("  Scene configured for high-quality rendering")
    
    def setup_camera(self):
        """Setup orthographic camera for top-down view."""
        print("Setting up camera...")
        
        # Create camera
        bpy.ops.object.camera_add(location=(0, 0, 15))
        camera = bpy.context.object
        camera.name = "RenderCamera"
        
        # Set as active camera
        bpy.context.scene.camera = camera
        
        # Configure orthographic view
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 16.0  # Larger ship needs more space
        
        # Point camera straight down
        camera.rotation_euler = (0, 0, 0)
        
        print(f"  Camera positioned at {camera.location}")
        return camera
    
    def setup_lighting(self):
        """Setup professional lighting for the main space whale."""
        print("Setting up lighting...")
        
        # Key light (main directional light)
        bpy.ops.object.light_add(type='SUN', location=(8, -8, 12))
        key_light = bpy.context.object
        key_light.name = "KeyLight"
        key_light.data.energy = 4.0
        key_light.data.color = (1.0, 0.98, 0.95)  # Slightly warm white
        key_light.rotation_euler = (math.radians(50), 0, math.radians(45))
        
        # Fill light (softer from opposite side)
        bpy.ops.object.light_add(type='SUN', location=(-6, 6, 10))
        fill_light = bpy.context.object
        fill_light.name = "FillLight"
        fill_light.data.energy = 2.0
        fill_light.data.color = (0.85, 0.9, 1.0)  # Cool blue fill
        fill_light.rotation_euler = (math.radians(60), 0, math.radians(-50))
        
        # Rim light (edge definition)
        bpy.ops.object.light_add(type='SUN', location=(0, 10, 8))
        rim_light = bpy.context.object
        rim_light.name = "RimLight"
        rim_light.data.energy = 3.0
        rim_light.data.color = (0.7, 0.85, 1.0)  # Blue rim
        rim_light.rotation_euler = (math.radians(25), 0, math.radians(180))
        
        # Ambient/environment light
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 6))
        ambient_light = bpy.context.object
        ambient_light.name = "AmbientLight"
        ambient_light.data.energy = 300
        ambient_light.data.color = (0.75, 0.8, 0.9)
        
        # Accent glow light (for bio-luminescence effect)
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 2))
        glow_light = bpy.context.object
        glow_light.name = "GlowLight"
        glow_light.data.energy = 150
        glow_light.data.color = (0.2, 0.6, 1.0)  # Blue glow
        
        print("  Professional lighting setup complete")
    
    def create_main_whale_ship(self):
        """Create the main space whale ship model."""
        print("Creating main space whale model...")
        
        # Create main body (elongated organic shape)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=3, location=(0, 0, 0))
        body = bpy.context.object
        body.name = "WhaleBody"
        body.scale = (3.5, 1.8, 1.2)  # Large elongated whale shape
        
        # Add subdivision for organic smoothness
        subsurf = body.modifiers.new(name="Subdivision", type='SUBSURF')
        subsurf.levels = 3
        subsurf.render_levels = 3
        
        # Add slight deformation for organic feel
        displace = body.modifiers.new(name="Displacement", type='DISPLACE')
        displace.strength = 0.3
        
        # Create head section (forward bulge)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=2, location=(4, 0, 0))
        head = bpy.context.object
        head.name = "WhaleHead"
        head.scale = (1.8, 1.3, 1.0)
        
        head_subsurf = head.modifiers.new(name="Subdivision", type='SUBSURF')
        head_subsurf.levels = 2
        
        # Create tail section
        bpy.ops.mesh.primitive_cone_add(radius1=1.2, radius2=0.1, depth=4, location=(-5, 0, 0))
        tail = bpy.context.object
        tail.name = "WhaleTail"
        tail.rotation_euler = (0, math.radians(90), 0)
        
        tail_subsurf = tail.modifiers.new(name="Subdivision", type='SUBSURF')
        tail_subsurf.levels = 2
        
        # Create dorsal fins
        bpy.ops.mesh.primitive_cone_add(radius1=0.8, radius2=0.1, depth=2, location=(0, 0, 1.5))
        dorsal_fin = bpy.context.object
        dorsal_fin.name = "DorsalFin"
        dorsal_fin.rotation_euler = (0, 0, 0)
        
        # Join all parts
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        head.select_set(True)
        tail.select_set(True)
        dorsal_fin.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        
        ship_obj = bpy.context.object
        ship_obj.name = "SpaceWhaleMain"
        
        # Apply materials
        self.apply_whale_material(ship_obj)
        
        print(f"  Main whale ship created: {ship_obj.name}")
        return ship_obj
    
    def apply_whale_material(self, obj):
        """Apply bio-organic material with glow effects."""
        print("  Applying bio-organic material...")
        
        mat = bpy.data.materials.new(name="WhaleMainMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        # Base Principled BSDF
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 300)
        principled.inputs['Base Color'].default_value = (0.25, 0.45, 0.65, 1.0)  # Blue-grey
        principled.inputs['Metallic'].default_value = 0.3
        principled.inputs['Roughness'].default_value = 0.4
        principled.inputs['Specular IOR Level'].default_value = 0.6
        principled.inputs['Subsurface Weight'].default_value = 0.15  # Organic translucency
        principled.inputs['Subsurface Radius'].default_value = (0.3, 0.4, 0.5)
        
        # Emission shader for bio-luminescence
        emission = nodes.new('ShaderNodeEmission')
        emission.location = (0, 0)
        emission.inputs['Color'].default_value = (0.15, 0.5, 1.0, 1.0)  # Blue glow
        emission.inputs['Strength'].default_value = 2.0
        
        # Noise texture for variation
        noise = nodes.new('ShaderNodeTexNoise')
        noise.location = (-400, 150)
        noise.inputs['Scale'].default_value = 5.0
        noise.inputs['Detail'].default_value = 8.0
        
        # Color ramp for glow patterns
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.location = (-200, 0)
        color_ramp.color_ramp.elements[0].position = 0.4
        color_ramp.color_ramp.elements[1].position = 0.6
        
        # Mix shaders
        mix_shader = nodes.new('ShaderNodeMixShader')
        mix_shader.location = (200, 200)
        
        # Output
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 200)
        
        # Connect nodes
        links = mat.node_tree.links
        links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Color'], mix_shader.inputs['Fac'])
        links.new(principled.outputs['BSDF'], mix_shader.inputs[1])
        links.new(emission.outputs['Emission'], mix_shader.inputs[2])
        links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])
        
        # Apply material
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat
        
        print("  Bio-organic material applied")
    
    def render_facing(self, ship_obj, facing_index, output_path):
        """Render a single facing."""
        angle = facing_index * self.rotation_step
        ship_obj.rotation_euler.z = math.radians(angle)
        
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
    
    def render_all_facings(self, ship_obj):
        """Render all 120 facings."""
        print(f"\nRendering {self.total_facings} facings...")
        
        temp_dir = self.output_dir / "temp_main_facings"
        temp_dir.mkdir(exist_ok=True)
        
        facing_paths = []
        failed = 0
        
        for i in range(self.total_facings):
            angle = i * self.rotation_step
            facing_path = temp_dir / f"facing_{i:03d}.png"
            
            print(f"  Rendering facing {i+1}/{self.total_facings} ({angle:.1f}°)...", end='\r')
            
            try:
                self.render_facing(ship_obj, i, facing_path)
            except Exception as exc:  # noqa: BLE001 - partial capture: skip bad frame
                failed += 1
                print(f"\n  [WARN] facing {i} render failed: {exc}")
                continue

            ok, reason = validate_facing_frame(facing_path)
            if not ok:
                failed += 1
                print(f"\n  [WARN] facing {i} rejected: {reason}")
                continue
            facing_paths.append((i, facing_path))
        
        print(f"\n  Facings rendered: {len(facing_paths)}/{self.total_facings} ok, {failed} failed/rejected")
        if not facing_paths:
            raise RuntimeError("No valid facings were rendered; cannot build spritesheet")
        return facing_paths
    
    def composite_spritesheet(self, facing_paths):
        """Composite individual facings into spritesheet."""
        print(f"\nCompositing spritesheet ({self.columns}x{self.rows})...")
        
        try:
            from PIL import Image
        except ImportError:
            print("  ERROR: PIL/Pillow required")
            print("  Install with: pip install Pillow")
            return None
        
        sheet_width = self.frame_size * self.columns
        sheet_height = self.frame_size * self.rows
        
        spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        
        placed = 0
        for entry in facing_paths:
            i, facing_path = entry if isinstance(entry, tuple) else (facing_paths.index(entry), entry)
            if not os.path.exists(facing_path):
                continue
            row = i // self.columns
            col = i % self.columns
            
            x = col * self.frame_size
            y = row * self.frame_size
            
            try:
                with Image.open(facing_path) as facing_img:
                    spritesheet.paste(facing_img.convert('RGBA'), (x, y))
                placed += 1
            except Exception as exc:  # noqa: BLE001
                print(f"\n  [WARN] could not composite facing {i}: {exc}")
            
            if placed % 10 == 0:
                print(f"  Composited {placed}/{len(facing_paths)}...", end='\r')
        
        print(f"\n  Spritesheet composited: {sheet_width}x{sheet_height} ({placed}/{self.total_facings} facings present)")
        
        output_path = self.output_dir / f"{self.ship_id}_120facings.png"
        spritesheet.save(output_path, 'PNG')
        print(f"  Saved: {output_path}")
        
        self.generate_mask(spritesheet)
        
        return output_path
    
    def generate_mask(self, spritesheet_pil):
        """Generate transparency mask as BMP."""
        print("Generating transparency mask...")
        
        if spritesheet_pil.mode == 'RGBA':
            alpha = spritesheet_pil.split()[3]
        else:
            alpha = spritesheet_pil.convert('L')
        
        mask = alpha.point(lambda x: 255 if x > 128 else 0)
        mask_rgb = Image.new('RGB', mask.size)
        mask_rgb.paste(mask)
        
        mask_path = self.output_dir / f"{self.ship_id}_120facingsMask.bmp"
        mask_rgb.save(mask_path, 'BMP')
        print(f"  Saved mask: {mask_path}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files."""
        temp_dir = self.output_dir / "temp_main_facings"
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            print("  Cleaned up temporary files")
    
    def render(self):
        """Main rendering pipeline."""
        print("\n" + "="*60)
        print("Main Space Whale Ship 120 Facings Renderer")
        print("="*60)
        
        try:
            self.setup_scene()
            self.setup_camera()
            self.setup_lighting()
            
            ship_obj = self.create_main_whale_ship()
            
            facing_paths = self.render_all_facings(ship_obj)
            self.composite_spritesheet(facing_paths)
            self.cleanup_temp_files()
            
            print("\n" + "="*60)
            print("Rendering Complete!")
            print("="*60)
            print(f"Output: {self.output_dir}")
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    try:
        argv = sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        argv = []
    
    parser = argparse.ArgumentParser(description="Render main space whale ship")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ship-id", default="scSpaceWhale")
    parser.add_argument("--texture-dir", default=None)
    parser.add_argument("--frame-size", type=int, default=256)
    
    args = parser.parse_args(argv)
    
    renderer = SpaceWhaleMainRenderer(
        output_dir=args.output_dir,
        ship_id=args.ship_id,
        texture_dir=args.texture_dir,
        frame_size=args.frame_size
    )
    
    renderer.render()


if __name__ == "__main__":
    main()
