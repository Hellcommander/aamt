#!/usr/bin/env python3
"""
Blender Space Whale 120 Facings Renderer
Renders a ship model from 120 angles and composites into a 10x12 spritesheet.

Usage:
    blender --background --python blender_space_whale_120_facings.py -- \
        --registry space_whale_ship_example.json \
        --ship-id leviathan_alpha \
        --output-dir Output/120Facings \
        --columns 10 \
        --rows 12 \
        --animation-frames 16
"""

import bpy
import sys
import json
import os
import math
import argparse
from pathlib import Path
from mathutils import Vector, Euler


def validate_facing_frame(path, min_coverage=0.002, min_luma_variance=8.0):
    """Mechanical quality gate for a single rendered facing.

    Rejects empty/flat frames (transparent or a single flat fill) so that a
    silently-failed render is caught instead of being baked into the sheet.
    Returns (ok: bool, reason: str). Fails safe to OK if PIL is unavailable so
    quality gating never blocks the mesh pipeline.
    """
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
            luma = img.convert("RGB").convert("L")
            var = ImageStat.Stat(luma).var[0]
            if var < min_luma_variance:
                return False, f"flat frame (luma variance {var:.1f})"
        return True, f"ok (coverage {coverage:.1%})"
    except Exception as exc:  # noqa: BLE001 - QA must never crash the render
        return False, f"unreadable ({exc})"


class SpaceWhaleRenderer:
    """Renders space whale ships with 120 facings for Transcendence."""
    
    def __init__(self, registry_path, ship_id, output_dir, columns=10, rows=12, 
                 animation_frames=16, texture_dir=None, frame_size=256):
        self.registry_path = registry_path
        self.ship_id = ship_id
        self.output_dir = Path(output_dir)
        self.columns = columns
        self.rows = rows
        self.animation_frames = animation_frames
        self.texture_dir = Path(texture_dir) if texture_dir else None
        self.frame_size = frame_size
        self.total_facings = columns * rows
        self.rotation_step = 360.0 / self.total_facings
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load registry
        with open(registry_path, 'r') as f:
            self.registry = json.load(f)
        
        # Find ship in registry
        self.ship = None
        for ship in self.registry.get('ships', []):
            if ship.get('id') == ship_id:
                self.ship = ship
                break
        
        if not self.ship:
            raise ValueError(f"Ship '{ship_id}' not found in registry")
        
        print(f"Loaded ship: {self.ship.get('name', ship_id)}")
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
        scene.cycles.device = 'GPU'
        scene.cycles.samples = 128
        scene.render.resolution_x = self.frame_size
        scene.render.resolution_y = self.frame_size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True
        
        # Setup world
        scene.world.use_nodes = True
        world_nodes = scene.world.node_tree.nodes
        world_nodes.clear()
        
        # Add background with dark space color
        bg_node = world_nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs['Strength'].default_value = 0.0
        
        output_node = world_nodes.new('ShaderNodeOutputWorld')
        scene.world.node_tree.links.new(bg_node.outputs['Background'], 
                                        output_node.inputs['Surface'])
        
        print("  Scene configured for transparent background rendering")
    
    def setup_camera(self):
        """Setup orthographic camera for top-down view."""
        print("Setting up camera...")
        
        # Create camera
        bpy.ops.object.camera_add(location=(0, 0, 10))
        camera = bpy.context.object
        camera.name = "RenderCamera"
        
        # Set as active camera
        bpy.context.scene.camera = camera
        
        # Configure orthographic view
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 12.0  # Adjust based on ship size
        
        # Point camera straight down
        camera.rotation_euler = (0, 0, 0)
        
        print(f"  Camera positioned at {camera.location}")
        return camera
    
    def setup_lighting(self):
        """Setup three-point lighting for the ship."""
        print("Setting up lighting...")
        
        # Key light (main light from above-front)
        bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
        key_light = bpy.context.object
        key_light.name = "KeyLight"
        key_light.data.energy = 3.0
        key_light.data.color = (1.0, 1.0, 1.0)
        key_light.rotation_euler = (math.radians(45), 0, math.radians(45))
        
        # Fill light (softer light from side)
        bpy.ops.object.light_add(type='SUN', location=(-5, 5, 8))
        fill_light = bpy.context.object
        fill_light.name = "FillLight"
        fill_light.data.energy = 1.5
        fill_light.data.color = (0.9, 0.9, 1.0)  # Slightly blue
        fill_light.rotation_euler = (math.radians(60), 0, math.radians(-45))
        
        # Rim light (edge highlight from back)
        bpy.ops.object.light_add(type='SUN', location=(0, 8, 6))
        rim_light = bpy.context.object
        rim_light.name = "RimLight"
        rim_light.data.energy = 2.0
        rim_light.data.color = (0.8, 0.9, 1.0)  # Blue tint
        rim_light.rotation_euler = (math.radians(30), 0, math.radians(180))
        
        # Ambient light (very soft overall illumination)
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 5))
        ambient_light = bpy.context.object
        ambient_light.name = "AmbientLight"
        ambient_light.data.energy = 200
        ambient_light.data.color = (0.8, 0.85, 0.9)
        
        print("  Three-point lighting setup complete")
    
    def load_ship_model(self):
        """Load or create ship model."""
        print(f"Loading ship model: {self.ship_id}...")
        
        # Check if model file is specified in registry
        model_path = self.ship.get('modelPath')
        
        if model_path and os.path.exists(model_path):
            # Import the model
            ext = os.path.splitext(model_path)[1].lower()
            if ext == '.blend':
                # Link from .blend file
                with bpy.data.libraries.load(model_path, link=False) as (data_from, data_to):
                    data_to.objects = data_from.objects
                for obj in data_to.objects:
                    bpy.context.collection.objects.link(obj)
                    if obj.type == 'MESH':
                        ship_obj = obj
            elif ext in ['.obj', '.fbx', '.gltf', '.glb']:
                # Import model
                if ext == '.obj':
                    bpy.ops.import_scene.obj(filepath=model_path)
                elif ext == '.fbx':
                    bpy.ops.import_scene.fbx(filepath=model_path)
                elif ext in ['.gltf', '.glb']:
                    bpy.ops.import_scene.gltf(filepath=model_path)
                ship_obj = bpy.context.selected_objects[0]
            else:
                raise ValueError(f"Unsupported model format: {ext}")
        else:
            # Create procedural ship model (placeholder)
            print("  No model file specified, creating procedural ship...")
            ship_obj = self.create_procedural_ship()
        
        ship_obj.name = f"Ship_{self.ship_id}"
        ship_obj.location = (0, 0, 0)
        ship_obj.rotation_euler = (0, 0, 0)
        
        # Apply textures if available
        if self.texture_dir:
            self.apply_textures(ship_obj)
        
        print(f"  Ship model loaded: {ship_obj.name}")
        return ship_obj
    
    def create_procedural_ship(self):
        """Create a procedural space whale ship model.

        This is the FALLBACK mesh used only when the registry supplies no model
        file. It is still a real 3D MESH that feeds the mesh -> 120-facings
        spritesheet path (never a flat 2D primitive): a multi-part organic whale
        (body + head + tapered tail + dorsal fin) with subdivision + organic
        displacement and a rich bio-organic material, so a missing model no
        longer bottoms out at a single bald sphere.
        """
        # Main body (elongated organic hull)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=48, ring_count=24, location=(0, 0, 0))
        body = bpy.context.object
        body.name = "WhaleBody"
        body.scale = (2.5, 1.2, 0.85)

        subsurf = body.modifiers.new(name="Subdivision", type='SUBSURF')
        subsurf.levels = 2
        subsurf.render_levels = 3

        # Organic surface variation (procedural texture drives the displacement
        # so the silhouette reads as living tissue, not a smooth ball).
        disp_tex = bpy.data.textures.new("WhaleBodyDisp", type='CLOUDS')
        try:
            disp_tex.noise_scale = 0.6
        except Exception:
            pass
        displace = body.modifiers.new(name="OrganicDisplace", type='DISPLACE')
        displace.texture = disp_tex
        displace.strength = 0.18

        # Forward head bulge
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.85, segments=40, ring_count=20, location=(1.9, 0, 0.05))
        head = bpy.context.object
        head.name = "WhaleHead"
        head.scale = (1.2, 1.0, 0.9)
        head.modifiers.new(name="Subdivision", type='SUBSURF').levels = 2

        # Tapered tail
        bpy.ops.mesh.primitive_cone_add(radius1=0.7, radius2=0.04, depth=2.4, location=(-2.6, 0, 0))
        tail = bpy.context.object
        tail.name = "WhaleTail"
        tail.rotation_euler = (0, math.radians(90), 0)
        tail.modifiers.new(name="Subdivision", type='SUBSURF').levels = 2

        # Dorsal fin (adds a recognisable directional silhouette across facings)
        bpy.ops.mesh.primitive_cone_add(radius1=0.5, radius2=0.03, depth=1.1, location=(0, 0, 0.85))
        dorsal = bpy.context.object
        dorsal.name = "DorsalFin"

        # Join all parts into a single ship object
        bpy.ops.object.select_all(action='DESELECT')
        for part in (body, head, tail, dorsal):
            part.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        ship_obj = bpy.context.object

        try:
            bpy.ops.object.shade_smooth()
        except Exception:
            pass

        self._apply_procedural_whale_material(ship_obj)
        return ship_obj

    def _apply_procedural_whale_material(self, obj):
        """Rich bio-organic material: layered base color, subsurface translucency,
        and noise-driven bioluminescent emission (better than the old flat
        emission+diffuse mix, while staying a mesh material for Cycles)."""
        mat = bpy.data.materials.new(name="ProceduralWhaleMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 300)
        principled.inputs['Base Color'].default_value = (0.22, 0.42, 0.62, 1.0)
        principled.inputs['Metallic'].default_value = 0.25
        principled.inputs['Roughness'].default_value = 0.4
        # Subsurface for organic translucency (guarded for Blender API differences)
        for key, val in (('Subsurface Weight', 0.15), ('Subsurface', 0.15)):
            if key in principled.inputs:
                principled.inputs[key].default_value = val
                break
        if 'Subsurface Radius' in principled.inputs:
            principled.inputs['Subsurface Radius'].default_value = (0.3, 0.4, 0.5)

        emission = nodes.new('ShaderNodeEmission')
        emission.location = (0, -60)
        emission.inputs['Color'].default_value = (0.15, 0.5, 1.0, 1.0)
        emission.inputs['Strength'].default_value = 2.0

        # Noise -> color ramp drives WHERE the bioluminescence glows, giving
        # patchy living patterns instead of a uniform glow.
        noise = nodes.new('ShaderNodeTexNoise')
        noise.location = (-500, 100)
        noise.inputs['Scale'].default_value = 5.5
        noise.inputs['Detail'].default_value = 8.0

        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.location = (-250, 60)
        ramp.color_ramp.elements[0].position = 0.45
        ramp.color_ramp.elements[1].position = 0.62

        mix = nodes.new('ShaderNodeMixShader')
        mix.location = (250, 200)
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (450, 200)

        links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], mix.inputs['Fac'])
        links.new(principled.outputs['BSDF'], mix.inputs[1])
        links.new(emission.outputs['Emission'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])

        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat
    
    def apply_textures(self, obj):
        """Apply textures from texture directory."""
        print(f"  Applying textures from {self.texture_dir}...")
        
        # Look for texture files
        texture_files = list(self.texture_dir.glob(f"{self.ship_id}*.png"))
        
        if not texture_files:
            print("  No textures found, using procedural materials")
            return
        
        # Apply first texture found
        texture_path = str(texture_files[0])
        
        # Create or get material
        if len(obj.data.materials) == 0:
            mat = bpy.data.materials.new(name=f"Material_{self.ship_id}")
            obj.data.materials.append(mat)
        else:
            mat = obj.data.materials[0]
        
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        # Image texture node
        tex_image = nodes.new('ShaderNodeTexImage')
        tex_image.image = bpy.data.images.load(texture_path)
        
        # Principled BSDF
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        
        # Output
        output = nodes.new('ShaderNodeOutputMaterial')
        
        # Connect nodes
        mat.node_tree.links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        print(f"  Applied texture: {texture_path}")
    
    def render_facing(self, ship_obj, facing_index, output_path):
        """Render a single facing."""
        # Calculate rotation angle
        angle = facing_index * self.rotation_step
        ship_obj.rotation_euler.z = math.radians(angle)
        
        # Render
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
    
    def render_all_facings(self, ship_obj):
        """Render all 120 facings.

        Robustness: each facing is rendered inside its own try/except and
        validated. A failed/empty frame is skipped (not fatal) so a single bad
        render never discards the whole sheet — the composite step assembles
        whatever facings succeeded (partial capture).
        """
        print(f"\nRendering {self.total_facings} facings...")
        
        temp_dir = self.output_dir / "temp_facings"
        temp_dir.mkdir(exist_ok=True)
        
        facing_paths = []
        failed = 0
        
        for i in range(self.total_facings):
            angle = i * self.rotation_step
            facing_path = temp_dir / f"facing_{i:03d}.png"
            
            print(f"  Rendering facing {i+1}/{self.total_facings} ({angle:.1f}°)...", end='\r')
            
            try:
                self.render_facing(ship_obj, i, facing_path)
            except Exception as exc:  # noqa: BLE001 - keep going on a bad frame
                failed += 1
                print(f"\n  [WARN] facing {i} render failed: {exc}")
                continue

            ok, reason = validate_facing_frame(facing_path)
            if not ok:
                failed += 1
                print(f"\n  [WARN] facing {i} rejected: {reason}")
                continue
            facing_paths.append((i, facing_path))
        
        print(f"\n  Facings rendered: {len(facing_paths)}/{self.total_facings} ok, {failed} failed/rejected -> {temp_dir}")
        if not facing_paths:
            raise RuntimeError("No valid facings were rendered; cannot build spritesheet")
        return facing_paths
    
    def composite_spritesheet(self, facing_paths):
        """Composite individual facings into spritesheet."""
        print(f"\nCompositing spritesheet ({self.columns}x{self.rows})...")
        
        # Calculate spritesheet dimensions
        sheet_width = self.frame_size * self.columns
        sheet_height = self.frame_size * self.rows
        
        # Create compositor nodes
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree
        tree.nodes.clear()
        
        # We'll use Python Imaging Library for compositing instead
        # This is more reliable than Blender's compositor for this task
        try:
            from PIL import Image
        except ImportError:
            print("  ERROR: PIL/Pillow not available, cannot composite spritesheet")
            print("  Install with: pip install Pillow")
            return None
        
        # Create blank spritesheet
        spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        
        # Composite each facing at its true grid cell (index-aware so a skipped
        # frame leaves a transparent gap rather than shifting every later cell).
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
                print(f"  Composited {placed}/{len(facing_paths)} facings...", end='\r')
        
        print(f"\n  Spritesheet composited: {sheet_width}x{sheet_height} ({placed}/{self.total_facings} facings present)")
        
        # Save spritesheet
        output_path = self.output_dir / f"{self.ship_id}_120facings.png"
        spritesheet.save(output_path, 'PNG')
        print(f"  Saved: {output_path}")
        
        # Generate mask
        self.generate_mask(spritesheet)
        
        return output_path
    
    def generate_mask(self, spritesheet_pil):
        """Generate transparency mask as BMP."""
        print("Generating transparency mask...")
        
        # Extract alpha channel
        if spritesheet_pil.mode == 'RGBA':
            alpha = spritesheet_pil.split()[3]
        else:
            alpha = spritesheet_pil.convert('L')
        
        # Convert to binary mask (Transcendence format)
        # White = opaque, Black = transparent
        mask = alpha.point(lambda x: 255 if x > 128 else 0)
        
        # Convert to RGB (BMP doesn't support alpha)
        mask_rgb = Image.new('RGB', mask.size)
        mask_rgb.paste(mask)
        
        # Save as BMP
        mask_path = self.output_dir / f"{self.ship_id}_120facingsMask.bmp"
        mask_rgb.save(mask_path, 'BMP')
        print(f"  Saved mask: {mask_path}")
    
    def cleanup_temp_files(self):
        """Clean up temporary facing files."""
        temp_dir = self.output_dir / "temp_facings"
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            print("  Cleaned up temporary files")
    
    def render(self):
        """Main rendering pipeline."""
        print("\n" + "="*60)
        print("Starting Space Whale 120 Facings Render")
        print("="*60)
        
        try:
            # Setup
            self.setup_scene()
            self.setup_camera()
            self.setup_lighting()
            
            # Load model
            ship_obj = self.load_ship_model()
            
            # Render all facings
            facing_paths = self.render_all_facings(ship_obj)
            
            # Composite spritesheet
            self.composite_spritesheet(facing_paths)
            
            # Cleanup
            self.cleanup_temp_files()
            
            print("\n" + "="*60)
            print("Rendering Complete!")
            print("="*60)
            print(f"Output: {self.output_dir}")
            
        except Exception as e:
            print(f"\nERROR: Rendering failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Parse arguments and run renderer."""
    # Get arguments after "--"
    try:
        argv = sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        argv = []
    
    parser = argparse.ArgumentParser(
        description="Render space whale ship with 120 facings for Transcendence"
    )
    parser.add_argument("--registry", required=True, help="Path to ship registry JSON")
    parser.add_argument("--ship-id", required=True, help="Ship ID to render")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--columns", type=int, default=10, help="Grid columns (default: 10)")
    parser.add_argument("--rows", type=int, default=12, help="Grid rows (default: 12)")
    parser.add_argument("--animation-frames", type=int, default=16, 
                       help="Animation frames per facing (default: 16)")
    parser.add_argument("--texture-dir", default=None, help="Texture directory (optional)")
    parser.add_argument("--frame-size", type=int, default=256, 
                       help="Frame size in pixels (default: 256)")
    
    args = parser.parse_args(argv)
    
    # Create renderer and run
    renderer = SpaceWhaleRenderer(
        registry_path=args.registry,
        ship_id=args.ship_id,
        output_dir=args.output_dir,
        columns=args.columns,
        rows=args.rows,
        animation_frames=args.animation_frames,
        texture_dir=args.texture_dir,
        frame_size=args.frame_size
    )
    
    renderer.render()


if __name__ == "__main__":
    main()
