"""
Blender Space Whale Rigging System
Creates bone-driven rigging for space whale ships with spline-driven spine deformation.
Supports modular sections (head, mid, belly, tail, dorsal crest) with bone weights.
"""

import bpy
import json
import math
import mathutils
from mathutils import Vector, Matrix

def clear_rigging():
    """Clear existing armature and bones"""
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            bpy.data.objects.remove(obj, do_unlink=True)

def create_spine_bones(segment_count: int, segment_length: float = 1.0, bone_name_prefix: str = "Spine"):
    """Create bones along the spline spine for deformation"""
    # Create armature
    armature = bpy.data.armatures.new("SpaceWhaleRig")
    armature_obj = bpy.data.objects.new("SpaceWhaleRig", armature)
    bpy.context.collection.objects.link(armature_obj)
    
    # Enter edit mode
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones = []
    prev_bone = None
    
    for i in range(segment_count):
        bone_name = f"{bone_name_prefix}_{i:02d}"
        bone = armature.edit_bones.new(bone_name)
        
        # Position bone along spine
        if i == 0:
            # Head bone at origin
            bone.head = Vector((0, 0, 0))
            bone.tail = Vector((0, 0, segment_length))
        else:
            # Subsequent bones
            bone.head = prev_bone.tail
            bone.tail = bone.head + Vector((0, 0, segment_length))
        
        # Set bone properties
        bone.use_connect = True if prev_bone else False
        bone.roll = 0.0
        
        # Store reference
        bones.append(bone)
        prev_bone = bone
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armature_obj, bones

def create_fin_bones(armature_obj, parent_bone_name: str, side: str = "left"):
    """Create fin bones for dorsal and pectoral fins"""
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    armature = armature_obj.data
    parent_bone = armature.edit_bones[parent_bone_name]
    
    fin_bones = []
    
    # Dorsal fin
    dorsal_name = f"DorsalFin_{side}"
    dorsal_bone = armature.edit_bones.new(dorsal_name)
    dorsal_bone.parent = parent_bone
    dorsal_bone.head = parent_bone.head + Vector((0, 0.5, 0))
    dorsal_bone.tail = dorsal_bone.head + Vector((0, 0.8, 0))
    dorsal_bone.use_connect = False
    fin_bones.append(dorsal_bone)
    
    # Pectoral fin
    pectoral_name = f"PectoralFin_{side}"
    pectoral_bone = armature.edit_bones.new(pectoral_name)
    pectoral_bone.parent = parent_bone
    if side == "left":
        offset = Vector((-0.6, 0, 0))
    else:
        offset = Vector((0.6, 0, 0))
    pectoral_bone.head = parent_bone.head + offset
    pectoral_bone.tail = pectoral_bone.head + offset * 0.8
    pectoral_bone.use_connect = False
    fin_bones.append(pectoral_bone)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return fin_bones

def create_tail_bones(armature_obj, last_spine_bone_name: str):
    """Create tail fin bones"""
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    armature = armature_obj.data
    parent_bone = armature.edit_bones[last_spine_bone_name]
    
    tail_bones = []
    
    # Upper tail fin
    upper_tail = armature.edit_bones.new("TailFin_Upper")
    upper_tail.parent = parent_bone
    upper_tail.head = parent_bone.tail
    upper_tail.tail = parent_bone.tail + Vector((0, 0.5, -0.3))
    upper_tail.use_connect = False
    tail_bones.append(upper_tail)
    
    # Lower tail fin
    lower_tail = armature.edit_bones.new("TailFin_Lower")
    lower_tail.parent = parent_bone
    lower_tail.head = parent_bone.tail
    lower_tail.tail = parent_bone.tail + Vector((0, -0.5, -0.3))
    lower_tail.use_connect = False
    tail_bones.append(lower_tail)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return tail_bones

def create_gill_vent_bones(armature_obj, parent_bone_name: str, count: int = 6):
    """Create bones for gill vents along the sides"""
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    armature = armature_obj.data
    parent_bone = armature.edit_bones[parent_bone_name]
    
    gill_bones = []
    bone_length = (parent_bone.tail - parent_bone.head).length
    
    for i in range(count):
        # Left side
        left_name = f"GillVent_L_{i:02d}"
        left_bone = armature.edit_bones.new(left_name)
        left_bone.parent = parent_bone
        t = i / (count - 1) if count > 1 else 0.5
        pos = parent_bone.head.lerp(parent_bone.tail, t)
        left_bone.head = pos + Vector((-0.3, 0, 0))
        left_bone.tail = left_bone.head + Vector((-0.2, 0, 0))
        left_bone.use_connect = False
        gill_bones.append(left_bone)
        
        # Right side
        right_name = f"GillVent_R_{i:02d}"
        right_bone = armature.edit_bones.new(right_name)
        right_bone.parent = parent_bone
        right_bone.head = pos + Vector((0.3, 0, 0))
        right_bone.tail = right_bone.head + Vector((0.2, 0, 0))
        right_bone.use_connect = False
        gill_bones.append(right_bone)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return gill_bones

def apply_bone_weights_to_mesh(mesh_obj, armature_obj, influence_radius: float = 1.5):
    """Automatically assign bone weights to mesh vertices"""
    # Add armature modifier
    modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    modifier.object = armature_obj
    modifier.use_vertex_groups = True
    
    # Create vertex groups for each bone
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='OBJECT')
    
    armature = armature_obj.data
    mesh = mesh_obj.data
    
    # Create vertex groups
    for bone in armature.bones:
        vg = mesh_obj.vertex_groups.new(name=bone.name)
        
        # Calculate weights based on distance to bone
        bone_head = armature_obj.matrix_world @ bone.head_local
        bone_tail = armature_obj.matrix_world @ bone.tail_local
        bone_dir = (bone_tail - bone_head).normalized()
        bone_length = (bone_tail - bone_head).length
        
        weights = []
        for vert in mesh.vertices:
            vert_world = mesh_obj.matrix_world @ vert.co
            
            # Project vertex onto bone line
            to_vert = vert_world - bone_head
            proj_length = to_vert.dot(bone_dir)
            
            if 0 <= proj_length <= bone_length:
                # On bone segment
                proj_point = bone_head + bone_dir * proj_length
                dist = (vert_world - proj_point).length
            elif proj_length < 0:
                # Before bone
                dist = (vert_world - bone_head).length
            else:
                # After bone
                dist = (vert_world - bone_tail).length
            
            # Weight based on distance (closer = higher weight)
            if dist < influence_radius:
                weight = 1.0 - (dist / influence_radius)
                weight = max(0.0, min(1.0, weight))
            else:
                weight = 0.0
            
            weights.append((vert.index, weight))
        
        # Assign weights
        for vert_idx, weight in weights:
            if weight > 0.0:
                vg.add([vert_idx], weight, 'REPLACE')
    
    return mesh_obj

def create_rig_from_config(config_path: str):
    """Create complete rig from JSON configuration"""
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    ship_data = config.get('ships', [{}])[0] if isinstance(config.get('ships'), list) else config
    visual = ship_data.get('visual', {})
    modules = visual.get('modules', [])
    
    # Determine segment count from modules
    segment_count = len([m for m in modules if m.get('type') in ['head', 'mid', 'tail']])
    if segment_count == 0:
        segment_count = 6  # Default
    
    # Create spine bones
    armature_obj, spine_bones = create_spine_bones(segment_count, segment_length=1.0)
    
    # Create fin bones (attach to mid-section bones)
    mid_bone_idx = segment_count // 2
    if mid_bone_idx < len(spine_bones):
        mid_bone_name = f"Spine_{mid_bone_idx:02d}"
        create_fin_bones(armature_obj, mid_bone_name, "left")
        create_fin_bones(armature_obj, mid_bone_name, "right")
    
    # Create tail bones (attach to last spine bone)
    if spine_bones:
        last_bone_name = f"Spine_{len(spine_bones)-1:02d}"
        create_tail_bones(armature_obj, last_bone_name)
    
    # Create gill vent bones
    gill_count = visual.get('animations', {}).get('gillVentCount', 6)
    if spine_bones:
        mid_bone_name = f"Spine_{mid_bone_idx:02d}"
        create_gill_vent_bones(armature_obj, mid_bone_name, gill_count)
    
    return armature_obj

def export_rig_info(armature_obj, output_path: str):
    """Export rig information for use in game"""
    armature = armature_obj.data
    
    rig_info = {
        "version": "1.0.0",
        "armature": {
            "name": armature_obj.name,
            "boneCount": len(armature.bones)
        },
        "bones": []
    }
    
    for bone in armature.bones:
        bone_info = {
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "head": list(bone.head_local),
            "tail": list(bone.tail_local),
            "length": bone.length,
            "type": "spine" if "Spine" in bone.name else 
                   "fin" if "Fin" in bone.name else
                   "gill" if "Gill" in bone.name else "other"
        }
        rig_info["bones"].append(bone_info)
    
    with open(output_path, 'w') as f:
        json.dump(rig_info, f, indent=2)
    
    print(f"Rig info exported to: {output_path}")

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Create space whale rigging system')
    parser.add_argument('--config', required=True, help='Path to ship registry JSON')
    parser.add_argument('--output', help='Output path for rig info JSON')
    parser.add_argument('--segment-count', type=int, default=6, help='Number of spine segments')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    
    # Clear existing rigging
    clear_rigging()
    
    # Create rig from config
    armature_obj = create_rig_from_config(args.config)
    
    # Export rig info
    if args.output:
        export_rig_info(armature_obj, args.output)
    
    print(f"Space Whale rig created with {len(armature_obj.data.bones)} bones")

if __name__ == "__main__":
    main()

