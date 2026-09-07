#!/usr/bin/env python3
"""
Blender Space Whale Rigging Generator
Creates bone-driven rigging system for space whale ships in Blender.

Usage:
    blender --background --python blender_space_whale_rigging.py -- \
        --config space_whale_ship_example.json \
        --output Output/rig_info.json \
        --segment-count 6
"""

import bpy
import sys
import json
import math
import argparse
from pathlib import Path
from mathutils import Vector, Euler


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Blender Space Whale Rigging Generator")
    parser.add_argument("--config", required=True, help="Ship registry JSON file")
    parser.add_argument("--output", required=True, help="Output rig info JSON file")
    parser.add_argument("--segment-count", type=int, default=6, help="Number of spine segments")
    
    # Blender passes arguments after --
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        args = parser.parse_args(sys.argv[idx+1:])
    else:
        args = parser.parse_args()
    
    return args


def load_rig_config(config_path):
    """Load rigging configuration from JSON."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_spine_armature(segment_count, ship_id):
    """Create spine armature with specified number of segments."""
    print(f"Creating spine armature with {segment_count} segments...")
    
    # Create armature
    bpy.ops.object.armature_add(location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = f"{ship_id}_Armature"
    
    # Enter edit mode
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Get armature data
    armature_data = armature.data
    armature_data.name = f"{ship_id}_ArmatureData"
    
    # Clear default bone
    bones = armature_data.edit_bones
    if len(bones) > 0:
        bones.remove(bones[0])
    
    # Create spine bones
    spine_bones = []
    segment_length = 1.0
    
    for i in range(segment_count):
        bone_name = f"Spine_{i:02d}"
        bone = bones.new(bone_name)
        
        # Position bone
        if i == 0:
            bone.head = Vector((0, 0, 0))
            bone.tail = Vector((0, 0, segment_length))
        else:
            parent_bone = bones[f"Spine_{i-1:02d}"]
            bone.head = parent_bone.tail
            bone.tail = bone.head + Vector((0, 0, segment_length))
        
        # Set parent relationship
        if i > 0:
            bone.parent = bones[f"Spine_{i-1:02d}"]
        
        spine_bones.append(bone_name)
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Created {len(spine_bones)} spine bones")
    return armature, spine_bones


def create_fin_bones(armature, spine_bones, fin_config):
    """Create fin bones attached to spine."""
    print("Creating fin bones...")
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones = armature.data.edit_bones
    fin_bone_names = []
    
    # Dorsal fin
    if fin_config.get('dorsal', {}).get('enabled', False):
        attachment = fin_config['dorsal'].get('attachmentBone', 'Spine_03')
        if attachment in bones:
            fin_bone = bones.new('DorsalFin')
            parent = bones[attachment]
            fin_bone.head = parent.head + Vector((0, 0.5, 0))
            fin_bone.tail = fin_bone.head + Vector((0, 0.3, 0))
            fin_bone.parent = parent
            fin_bone_names.append('DorsalFin')
    
    # Pectoral fins
    if fin_config.get('pectoral', {}).get('enabled', False):
        attachment = fin_config['pectoral'].get('attachmentBone', 'Spine_02')
        if attachment in bones:
            for side in ['Left', 'Right']:
                fin_bone = bones.new(f'PectoralFin_{side}')
                parent = bones[attachment]
                offset = Vector((0.5 if side == 'Right' else -0.5, 0, 0))
                fin_bone.head = parent.head + offset
                fin_bone.tail = fin_bone.head + offset * 0.6
                fin_bone.parent = parent
                fin_bone_names.append(f'PectoralFin_{side}')
    
    # Tail fin
    if fin_config.get('tail', {}).get('enabled', False):
        attachment = fin_config['tail'].get('attachmentBone', f'Spine_{len(spine_bones)-1:02d}')
        if attachment in bones:
            fin_bone = bones.new('TailFin')
            parent = bones[attachment]
            fin_bone.head = parent.tail
            fin_bone.tail = fin_bone.head + Vector((0, 0, -0.5))
            fin_bone.parent = parent
            fin_bone_names.append('TailFin')
    
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Created {len(fin_bone_names)} fin bones")
    return fin_bone_names


def create_gill_bones(armature, spine_bones, gill_config):
    """Create gill vent bones."""
    if not gill_config.get('enabled', False):
        return []
    
    print("Creating gill bones...")
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones = armature.data.edit_bones
    gill_bone_names = []
    gill_count = gill_config.get('count', 3)
    attachment = gill_config.get('attachmentBone', 'Spine_03')
    
    if attachment in bones:
        parent = bones[attachment]
        for i in range(gill_count):
            gill_bone = bones.new(f'Gill_{i:02d}')
            angle = (i / gill_count) * 2 * 3.14159
            offset = Vector((math.cos(angle) * 0.3, math.sin(angle) * 0.3, 0))
            gill_bone.head = parent.head + offset
            gill_bone.tail = gill_bone.head + offset * 0.4
            gill_bone.parent = parent
            gill_bone_names.append(f'Gill_{i:02d}')
    
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Created {len(gill_bone_names)} gill bones")
    return gill_bone_names


def export_rig_info(armature, spine_bones, fin_bones, gill_bones, rig_config, output_path):
    """Export rig information to JSON."""
    print(f"Exporting rig info to {output_path}...")
    
    rig_info = {
        "version": "1.0.0",
        "shipId": rig_config.get("shipId", "unknown"),
        "armature": {
            "name": armature.name,
            "boneCount": len(spine_bones) + len(fin_bones) + len(gill_bones)
        },
        "bones": {
            "spine": spine_bones,
            "fins": fin_bones,
            "gills": gill_bones
        },
        "rigging": rig_config.get("rigging", {}),
        "blenderVersion": bpy.app.version_string,
        "exported": True
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rig_info, f, indent=2, ensure_ascii=False)
    
    print(f"Rig info exported: {output_path}")
    return rig_info


def main():
    """Main rigging generation function."""
    args = parse_args()
    
    print("="*60)
    print("Blender Space Whale Rigging Generator")
    print("="*60)
    print(f"Config: {args.config}")
    print(f"Output: {args.output}")
    print(f"Segment Count: {args.segment_count}")
    print()
    
    # Load registry to find ship ID
    registry_path = Path(args.config)
    if not registry_path.exists():
        print(f"ERROR: Registry file not found: {registry_path}")
        sys.exit(1)
    
    # Extract ship ID from registry
    ship_id = None
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
            if 'ships' in registry and len(registry['ships']) > 0:
                # Use first ship in registry
                ship_id = registry['ships'][0].get('id')
    except Exception as e:
        print(f"Warning: Could not load registry: {e}")
    
    # Find rig config JSON (created by PowerShell script)
    # Look in the same directory as the output
    output_path = Path(args.output)
    rig_config_dir = output_path.parent
    rig_config = None
    
    if ship_id:
        rig_config_file = rig_config_dir / f"{ship_id}_rig_config.json"
        if rig_config_file.exists():
            print(f"Loading rig config from: {rig_config_file}")
            try:
                with open(rig_config_file, 'r', encoding='utf-8') as f:
                    rig_config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load rig config: {e}")
    
    # If no rig config found, create default
    if not rig_config:
        print("No rig config found, creating default...")
        ship_id = ship_id or "unknown"
        rig_config = {
            "version": "1.0.0",
            "shipId": ship_id,
            "rigging": {
                "spine": {"segmentCount": args.segment_count, "segmentLength": 1.0},
                "fins": {
                    "dorsal": {"enabled": True, "attachmentBone": f"Spine_{args.segment_count//2:02d}"},
                    "pectoral": {"enabled": True, "attachmentBone": f"Spine_{args.segment_count//3:02d}"},
                    "tail": {"enabled": True, "attachmentBone": f"Spine_{args.segment_count-1:02d}"}
                },
                "gills": {"enabled": True, "count": 3, "attachmentBone": f"Spine_{args.segment_count//2:02d}"}
            }
        }
    
    # Clear default scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Get segment count from config
    segment_count = rig_config.get("rigging", {}).get("spine", {}).get("segmentCount", args.segment_count)
    ship_id = rig_config.get("shipId", "unknown")
    
    # Create armature
    armature, spine_bones = create_spine_armature(segment_count, ship_id)
    
    # Create fin bones
    fin_config = rig_config.get("rigging", {}).get("fins", {})
    fin_bones = create_fin_bones(armature, spine_bones, fin_config)
    
    # Create gill bones
    gill_config = rig_config.get("rigging", {}).get("gills", {})
    gill_bones = create_gill_bones(armature, spine_bones, gill_config)
    
    # Export rig info
    rig_info = export_rig_info(armature, spine_bones, fin_bones, gill_bones, rig_config, args.output)
    
    print()
    print("="*60)
    print("Rigging generation complete!")
    print(f"Total bones: {rig_info['armature']['boneCount']}")
    print("="*60)


if __name__ == "__main__":
    main()
