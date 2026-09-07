#!/usr/bin/env python3
"""
Blender Space Whale Segment 120 Facings Renderer
Renders space whale segment (128x128) from 120 angles.

Usage:
    blender --background --python blender_space_whale_segment_120_facings.py -- \
        --output-dir Output/120Facings \
        --ship-id scSpaceWhaleSegment
"""

import bpy
import sys
import os
import math
import argparse
from pathlib import Path
from mathutils import Vector


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


class SpaceWhaleSegmentRenderer:
    """Renders space whale segment with 120 facings."""
    
    def __init__(self, output_dir, ship_id="scSpaceWhaleSegment", frame_size=128):
        self.ship_id = ship_id
        self.output_dir = Path(output_dir)
        self.frame_size = frame_size
        self.columns = 10
        self.rows = 12
        self.total_facings = 120
        self.rotation_step = 3.0
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Rendering whale segment: {self.ship_id} ({self.frame_size}x{self.frame_size})")
    
    def setup_scene(self):
        """Setup scene for segment rendering."""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        
        try:
            scene.cycles.device = 'GPU'
        except:
            scene.cycles.device = 'CPU'
        
        scene.cycles.samples = 128
        scene.render.resolution_x = self.frame_size
        scene.render.resolution_y = self.frame_size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
        scene.cycles.use_denoising = True
        
        # Space background
        scene.world.use_nodes = True
        world_nodes = scene.world.node_tree.nodes
        world_nodes.clear()
        
        bg_node = world_nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs['Strength'].default_value = 0.0
        
        output_node = world_nodes.new('ShaderNodeOutputWorld')
        scene.world.node_tree.links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])
    
    def setup_camera(self):
        """Setup orthographic camera."""
        bpy.ops.object.camera_add(location=(0, 0, 8))
        camera = bpy.context.object
        camera.name = "RenderCamera"
        bpy.context.scene.camera = camera
        
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 8.0
        camera.rotation_euler = (0, 0, 0)
        
        return camera
    
    def setup_lighting(self):
        """Setup lighting for segment."""
        # Key light
        bpy.ops.object.light_add(type='SUN', location=(4, -4, 8))
        key_light = bpy.context.object
        key_light.data.energy = 3.5
        key_light.data.color = (1.0, 0.98, 0.95)
        key_light.rotation_euler = (math.radians(50), 0, math.radians(45))
        
        # Fill light
        bpy.ops.object.light_add(type='SUN', location=(-3, 3, 6))
        fill_light = bpy.context.object
        fill_light.data.energy = 1.8
        fill_light.data.color = (0.85, 0.9, 1.0)
        fill_light.rotation_euler = (math.radians(60), 0, math.radians(-50))
        
        # Rim light
        bpy.ops.object.light_add(type='SUN', location=(0, 6, 5))
        rim_light = bpy.context.object
        rim_light.data.energy = 2.5
        rim_light.data.color = (0.7, 0.85, 1.0)
        rim_light.rotation_euler = (math.radians(25), 0, math.radians(180))
        
        # Glow light
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 3))
        glow_light = bpy.context.object
        glow_light.data.energy = 120
        glow_light.data.color = (0.2, 0.6, 1.0)
    
    def create_segment(self):
        """Create whale segment model."""
        print("Creating segment model...")
        
        # Main segment body (cylindrical with taper)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=2.5, location=(0, 0, 0))
        segment = bpy.context.object
        segment.name = "WhaleSegment"
        segment.rotation_euler = (0, math.radians(90), 0)
        
        # Add subdivision
        subsurf = segment.modifiers.new(name="Subdivision", type='SUBSURF')
        subsurf.levels = 2
        subsurf.render_levels = 2
        
        # Add organic deformation
        displace = segment.modifiers.new(name="Displacement", type='DISPLACE')
        displace.strength = 0.15
        
        # Add connecting joints
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(1.0, 0, 0))
        joint1 = bpy.context.object
        joint1.scale = (0.8, 0.6, 0.6)
        
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(-1.0, 0, 0))
        joint2 = bpy.context.object
        joint2.scale = (0.8, 0.6, 0.6)
        
        # Join parts
        bpy.ops.object.select_all(action='DESELECT')
        segment.select_set(True)
        joint1.select_set(True)
        joint2.select_set(True)
        bpy.context.view_layer.objects.active = segment
        bpy.ops.object.join()
        
        ship_obj = bpy.context.object
        self.apply_segment_material(ship_obj)
        
        print(f"  Segment created: {ship_obj.name}")
        return ship_obj
    
    def apply_segment_material(self, obj):
        """Apply segment material."""
        mat = bpy.data.materials.new(name="SegmentMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        # Principled BSDF
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 300)
        principled.inputs['Base Color'].default_value = (0.28, 0.48, 0.68, 1.0)
        principled.inputs['Metallic'].default_value = 0.25
        principled.inputs['Roughness'].default_value = 0.45
        principled.inputs['Subsurface Weight'].default_value = 0.12
        principled.inputs['Subsurface Radius'].default_value = (0.25, 0.35, 0.45)
        
        # Emission
        emission = nodes.new('ShaderNodeEmission')
        emission.location = (0, 0)
        emission.inputs['Color'].default_value = (0.18, 0.52, 1.0, 1.0)
        emission.inputs['Strength'].default_value = 1.5
        
        # Noise texture
        noise = nodes.new('ShaderNodeTexNoise')
        noise.location = (-400, 150)
        noise.inputs['Scale'].default_value = 6.0
        noise.inputs['Detail'].default_value = 7.0
        
        # Color ramp
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.location = (-200, 0)
        color_ramp.color_ramp.elements[0].position = 0.45
        color_ramp.color_ramp.elements[1].position = 0.55
        
        # Mix shader
        mix_shader = nodes.new('ShaderNodeMixShader')
        mix_shader.location = (200, 200)
        
        # Output
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 200)
        
        # Connect
        links = mat.node_tree.links
        links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Color'], mix_shader.inputs['Fac'])
        links.new(principled.outputs['BSDF'], mix_shader.inputs[1])
        links.new(emission.outputs['Emission'], mix_shader.inputs[2])
        links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat
    
    def render_all_facings(self, ship_obj):
        """Render all facings."""
        print(f"\nRendering {self.total_facings} facings...")
        
        temp_dir = self.output_dir / "temp_segment_facings"
        temp_dir.mkdir(exist_ok=True)
        
        facing_paths = []
        failed = 0
        
        for i in range(self.total_facings):
            angle = i * self.rotation_step
            facing_path = temp_dir / f"facing_{i:03d}.png"
            
            try:
                ship_obj.rotation_euler.z = math.radians(angle)
                bpy.context.scene.render.filepath = str(facing_path)
                bpy.ops.render.render(write_still=True)
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
            
            if len(facing_paths) % 10 == 0:
                print(f"  Rendered {len(facing_paths)}/{self.total_facings}...", end='\r')
        
        print(f"\n  Facings rendered: {len(facing_paths)}/{self.total_facings} ok, {failed} failed/rejected")
        if not facing_paths:
            raise RuntimeError("No valid facings were rendered; cannot build spritesheet")
        return facing_paths
    
    def composite_spritesheet(self, facing_paths):
        """Composite spritesheet."""
        print(f"\nCompositing spritesheet...")
        
        try:
            from PIL import Image
        except ImportError:
            print("  ERROR: PIL/Pillow required")
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
        
        print(f"  Spritesheet: {placed}/{self.total_facings} facings present")
        output_path = self.output_dir / f"{self.ship_id}_120facings.png"
        spritesheet.save(output_path, 'PNG')
        print(f"  Saved: {output_path}")
        
        # Generate mask
        if spritesheet.mode == 'RGBA':
            alpha = spritesheet.split()[3]
        else:
            alpha = spritesheet.convert('L')
        
        mask = alpha.point(lambda x: 255 if x > 128 else 0)
        mask_rgb = Image.new('RGB', mask.size)
        mask_rgb.paste(mask)
        
        mask_path = self.output_dir / f"{self.ship_id}_120facingsMask.bmp"
        mask_rgb.save(mask_path, 'BMP')
        print(f"  Saved mask: {mask_path}")
        
        return output_path
    
    def cleanup_temp_files(self):
        """Cleanup temp files."""
        temp_dir = self.output_dir / "temp_segment_facings"
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            print("  Cleaned up temporary files")
    
    def render(self):
        """Main render pipeline."""
        print("\n" + "="*60)
        print("Space Whale Segment 120 Facings Renderer")
        print("="*60)
        
        try:
            self.setup_scene()
            self.setup_camera()
            self.setup_lighting()
            
            ship_obj = self.create_segment()
            
            facing_paths = self.render_all_facings(ship_obj)
            self.composite_spritesheet(facing_paths)
            self.cleanup_temp_files()
            
            print("\n" + "="*60)
            print("Rendering Complete!")
            print("="*60)
            
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
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ship-id", default="scSpaceWhaleSegment")
    parser.add_argument("--frame-size", type=int, default=128)
    
    args = parser.parse_args(argv)
    
    renderer = SpaceWhaleSegmentRenderer(
        output_dir=args.output_dir,
        ship_id=args.ship_id,
        frame_size=args.frame_size
    )
    
    renderer.render()


if __name__ == "__main__":
    main()
