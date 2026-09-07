# Blender Rigging Setup Guide for Space Whale

## Quick Start

### Prerequisites
- Blender 3.0+ installed
- Python 3.10+ (comes with Blender)
- Space Whale ship model (mesh)

### Step 1: Prepare Your Ship Model

1. **Open Blender**
2. **Import or create your space whale mesh**
3. **Ensure mesh is at origin** (0, 0, 0)
4. **Check mesh orientation**: 
   - Head should face +Z direction
   - Tail should face -Z direction
   - Top should face +Y direction

### Step 2: Run Rigging Script

#### Option A: Command Line (Recommended)

```powershell
# Generate rig from ship registry
cd "D:\games\Steam\steamapps\common\Transcendence\Tools"
blender --background --python blender_space_whale_rigging.py -- --config space_whale_ship_example.json --output Output/Rigging/rig_info.json --segment-count 6
```

#### Option B: Blender Script Editor

1. **Open Blender**
2. **Switch to Scripting workspace**
3. **Open** `blender_space_whale_rigging.py`
4. **Modify** the `main()` call at bottom:
   ```python
   if __name__ == "__main__":
       # Direct call for Blender
       import sys
       sys.argv = ['blender_space_whale_rigging.py', '--config', 'space_whale_ship_example.json', '--output', 'rig_info.json', '--segment-count', '6']
       main()
   ```
5. **Run Script** (Alt+P or click Run)

### Step 3: Apply Rig to Mesh

1. **Select your mesh object**
2. **Add Armature Modifier**:
   - Modifier Properties → Add Modifier → Armature
   - Object: Select "SpaceWhaleRig"
   - ✓ Use Vertex Groups
   - ✓ Preserve Volume

3. **Parent Mesh to Armature**:
   - Select mesh, then Shift+Select armature
   - Ctrl+P → "With Automatic Weights"
   - Blender will auto-assign weights

### Step 4: Refine Weights (Optional)

1. **Select mesh** → Switch to **Weight Paint mode**
2. **Select bone** from vertex group list
3. **Paint weights**:
   - **Add** (Ctrl+Click): Increase influence
   - **Subtract** (Ctrl+Shift+Click): Decrease influence
   - **Smooth** (Shift): Blend weights
   - **Normalize All**: Ensure weights sum to 1.0

### Step 5: Test Deformation

1. **Select armature** → Switch to **Pose mode**
2. **Select spine bone** (e.g., Spine_02)
3. **Rotate bone** (R key)
4. **Check mesh deformation**:
   - Should bend smoothly
   - No unwanted stretching
   - Weights look correct

## Detailed Setup

### Bone Structure

The rig creates this hierarchy:

```
SpaceWhaleRig (Armature)
├── Spine_00 (Head) [Root]
│   ├── PectoralFin_left
│   └── PectoralFin_right
├── Spine_01
├── Spine_02
│   ├── DorsalFin_left
│   ├── DorsalFin_right
│   ├── GillVent_L_00
│   ├── GillVent_R_00
│   ├── GillVent_L_01
│   └── GillVent_R_01
├── Spine_03
├── Spine_04
└── Spine_05 (Tail)
    ├── TailFin_Upper
    └── TailFin_Lower
```

### Weight Painting Guidelines

#### Spine Bones
- **Full weight (1.0)** on their segment
- **Gradual falloff** to adjacent segments
- **No influence** on distant segments

#### Fin Bones
- **High weight (0.7-0.9)** on fin geometry
- **Gradual falloff** from fin base
- **Minimal influence** on body

#### Gill Bones
- **Localized weight (0.3-0.5)** on vent areas only
- **Sharp falloff** (no influence beyond vent)

### Animation Setup

#### Breathing Animation

1. **Select armature** → Pose mode
2. **Select all spine bones** (A key)
3. **Insert keyframe** at frame 1 (I → Location, Rotation, Scale)
4. **Go to frame 16**
5. **Scale bones** slightly (S → 1.05)
6. **Insert keyframe**
7. **Set to loop** (Animation → Repeat)

#### Tail Sweep Animation

1. **Select Spine_05** (tail bone)
2. **Frame 1**: Insert keyframe
3. **Frame 30**: Rotate 15° (R → Z → 15)
4. **Frame 60**: Rotate -15°
5. **Frame 90**: Return to 0°
6. **Set interpolation** to "Ease In Out"

#### Gill Vent Pulse

1. **Select all gill bones**
2. **Frame 1**: Scale 0.5 (S → 0.5)
3. **Frame 10**: Scale 1.5
4. **Frame 20**: Scale 0.5
5. **Add phase offset** per gill (stagger by 2 frames)

## Integration with Spline System

### Bone Constraints

To make bones follow spline targets:

1. **Add Copy Location constraint** to each spine bone:
   - Target: Empty object (spline target)
   - ✓ Offset
   - Influence: 1.0

2. **Add Copy Rotation constraint**:
   - Target: Same Empty
   - ✓ Offset
   - Influence: 1.0

3. **Drive Empty positions** from spline system (via Python script or drivers)

### Python Driver Example

```python
import bpy

# Create driver for bone position
bone = bpy.data.objects["SpaceWhaleRig"].pose.bones["Spine_02"]
bone.location[0] = 0.0

# Add driver
driver = bone.driver_add("location", 0).driver
driver.type = 'SCRIPTED'
driver.expression = "spline_target_x"  # Variable from spline system
```

## Export Settings

### FBX Export

1. **File** → Export → FBX
2. **Settings**:
   - ✓ Selected Objects
   - ✓ Apply Transform
   - ✓ Add Leaf Bones
   - ✓ Armature
   - ✓ Mesh
   - ✓ Use Armature Deform
   - Scale: 1.0
   - Forward: -Z Forward, Y Up

### Export Rig Info

The script exports JSON with:
- Bone hierarchy
- Bone positions
- Bone types
- Parent relationships

Use this for game integration.

## Troubleshooting

### Bones Not Visible
- **Viewport Display** → Show Bones: ✓
- **Armature Display** → Display As: Stick or Envelope

### Mesh Not Deforming
- Check **Armature modifier** is enabled
- Verify **vertex groups** exist
- Ensure **weights are assigned**
- Check **modifier order** (Armature should be first)

### Deformation Too Stiff
- **Increase influence radius** in script
- **Smooth weights** in Weight Paint mode
- **Add more bones** for fine control

### Deformation Too Loose
- **Decrease influence radius**
- **Sharpen weight falloff**
- **Reduce bone count**

### Weights Not Normalizing
- **Weight Paint mode** → Weights → Normalize All
- Check for **locked vertex groups**
- Verify **max influences** setting (4 recommended)

## Advanced Setup

### Custom Bone Shapes

1. **Create custom bone shape** (mesh object)
2. **Select bone** in Edit mode
3. **Bone Properties** → Custom Shape
4. **Select your shape object**

### IK Constraints

For automatic tail movement:

1. **Add IK constraint** to Spine_05
2. **Target**: Empty object
3. **Chain Length**: 3
4. **Pole Target**: Empty for control

### Constraints for Spline Following

```python
# Add Copy Transform constraint
constraint = bone.constraints.new('COPY_TRANSFORMS')
constraint.target = spline_target_empty
constraint.influence = 1.0
```

## Workflow Summary

1. ✅ **Generate rig** from registry
2. ✅ **Apply to mesh** (Armature modifier + parent)
3. ✅ **Paint weights** (automatic or manual)
4. ✅ **Test deformation** (pose bones)
5. ✅ **Set up animations** (breathing, tail sweep, gills)
6. ✅ **Add constraints** (for spline following)
7. ✅ **Export** (FBX + rig info JSON)

## Files

- `blender_space_whale_rigging.py` - Rigging script
- `space_whale_skinning_registry.json` - Skinning configuration
- `SpaceWhaleRiggingGenerator.ps1` - Generator orchestrator
- `BLENDER_RIGGING_SETUP_GUIDE.md` - This guide

## Next Steps

1. **Run rigging script** in Blender
2. **Apply rig to your mesh**
3. **Paint weights** for smooth deformation
4. **Test animations**
5. **Export** for game integration

Your Blender setup is ready! 🎨

