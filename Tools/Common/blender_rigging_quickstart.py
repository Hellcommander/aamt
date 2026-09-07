"""
Blender Rigging Quickstart Script
Run this directly in Blender to create a space whale rig.
"""

import bpy
import json
import math
from mathutils import Vector

def clear_scene():
    """Clear all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_spine_rig(segment_count=6, segment_length=1.0):
    """Create spine rig with bones"""
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
        bone_name = f"Spine_{i:02d}"
        bone = armature.edit_bones.new(bone_name)
        
        if i == 0:
            bone.head = Vector((0, 0, 0))
            bone.tail = Vector((0, 0, segment_length))
        else:
            bone.head = prev_bone.tail
            bone.tail = bone.head + Vector((0, 0, segment_length))
        
        bone.use_connect = True if prev_bone else False
        bones.append(bone)
        prev_bone = bone
    
    # Add fin bones
    mid_bone_idx = segment_count // 2
    if mid_bone_idx < len(bones):
        mid_bone = bones[mid_bone_idx]
        
        # Dorsal fin
        dorsal = armature.edit_bones.new("DorsalFin")
        dorsal.parent = mid_bone
        dorsal.head = mid_bone.head + Vector((0, 0.5, 0))
        dorsal.tail = dorsal.head + Vector((0, 0.8, 0))
        dorsal.use_connect = False
        
        # Pectoral fins
        for side in ["Left", "Right"]:
            pectoral = armature.edit_bones.new(f"PectoralFin_{side}")
            pectoral.parent = bones[1] if len(bones) > 1 else mid_bone
            offset = Vector((-0.6, 0, 0)) if side == "Left" else Vector((0.6, 0, 0))
            pectoral.head = pectoral.parent.head + offset
            pectoral.tail = pectoral.head + offset * 0.8
            pectoral.use_connect = False
    
    # Add tail fins
    if bones:
        tail_bone = bones[-1]
        for position in ["Upper", "Lower"]:
            tail_fin = armature.edit_bones.new(f"TailFin_{position}")
            tail_fin.parent = tail_bone
            tail_fin.head = tail_bone.tail
            offset = Vector((0, 0.5, -0.3)) if position == "Upper" else Vector((0, -0.5, -0.3))
            tail_fin.tail = tail_fin.head + offset
            tail_fin.use_connect = False
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armature_obj

def apply_auto_weights(mesh_obj, armature_obj):
    """Apply automatic weights to mesh"""
    # Parent with automatic weights
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    # Add armature modifier if not present
    if "Armature" not in [m.name for m in mesh_obj.modifiers]:
        modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
        modifier.object = armature_obj
        modifier.use_vertex_groups = True

def main():
    """Main function - creates rig and applies to selected mesh"""
    print("Space Whale Rigging Quickstart")
    print("==============================")
    
    # Get selected mesh
    mesh_obj = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            mesh_obj = obj
            break
    
    if mesh_obj is None:
        print("ERROR: No mesh selected. Please select your space whale mesh first.")
        return
    
    print(f"Found mesh: {mesh_obj.name}")
    
    # Create rig (6 segments default)
    segment_count = 6
    print(f"Creating rig with {segment_count} spine segments...")
    armature_obj = create_spine_rig(segment_count, segment_length=1.0)
    
    # Apply to mesh
    print("Applying rig to mesh...")
    apply_auto_weights(mesh_obj, armature_obj)
    
    print("")
    print("Rig created successfully!")
    print("")
    print("Next steps:")
    print("1. Switch to Weight Paint mode to refine weights")
    print("2. Switch to Pose mode to test deformation")
    print("3. Add animations (breathing, tail sweep, etc.)")
    print("")
    print("Bones created:")
    for bone in armature_obj.data.bones:
        parent = f" (parent: {bone.parent.name})" if bone.parent else " (root)"
        print(f"  - {bone.name}{parent}")

# Run if executed in Blender
if __name__ == "__main__":
    main()

