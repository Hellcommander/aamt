# Space Whale Skinning and Rigging Guide

## Overview

The Space Whale uses a **bone-driven deformation system** for smooth, organic movement. The rigging system creates bones along the spline spine that drive mesh deformation, allowing the whale to bend and undulate naturally.

## Architecture

### Bone Structure

```
SpaceWhaleRig (Armature)
├── Spine_00 (Head)
│   ├── PectoralFin_left
│   └── PectoralFin_right
├── Spine_01
├── Spine_02
│   └── DorsalFin_left
│   └── DorsalFin_right
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

### Bone Types

1. **Spine Bones** (`Spine_XX`)
   - Primary deformation bones
   - Connected chain along spline
   - Drive main body deformation

2. **Fin Bones** (`*Fin_*`)
   - Dorsal fin (top)
   - Pectoral fins (sides)
   - Tail fins (rear)
   - Secondary deformation

3. **Gill Bones** (`GillVent_*`)
   - Ventilation system
   - Pulsing animation
   - Tertiary deformation

## Rigging Process

### Step 1: Create Rig from Config

```powershell
.\SpaceWhaleRiggingGenerator.ps1 -RegistryPath "space_whale_ship_example.json" -OutputDir "Output/Rigging"
```

This creates:
- Armature with bones
- Bone hierarchy
- Rig info JSON

### Step 2: Apply to Mesh

1. **Select mesh object**
2. **Add Armature modifier**:
   - Object: SpaceWhaleRig
   - Use Vertex Groups: ✓
   - Preserve Volume: ✓

3. **Assign bone weights**:
   - Automatic: Use `apply_bone_weights_to_mesh()` function
   - Manual: Weight paint in Blender

### Step 3: Weight Painting

#### Spine Weights
- **Primary influence**: 0.6 - 1.0
- **Falloff**: Gaussian
- **Coverage**: Full body segments

#### Fin Weights
- **Secondary influence**: 0.3 - 0.7
- **Falloff**: Linear
- **Coverage**: Fin areas only

#### Gill Weights
- **Tertiary influence**: 0.1 - 0.4
- **Falloff**: Linear
- **Coverage**: Vent areas only

## Module-to-Bone Mapping

### Head Module
- **Primary**: `Spine_00` (80%)
- **Secondary**: `PectoralFin_left`, `PectoralFin_right` (10% each)

### Mid Section
- **Primary**: `Spine_01`, `Spine_02`, `Spine_03` (30% each)
- **Secondary**: `DorsalFin_left`, `DorsalFin_right` (5% each)
- **Gills**: `GillVent_*` (distributed)

### Belly Bay
- **Primary**: `Spine_02`, `Spine_03` (50% each)

### Tail Module
- **Primary**: `Spine_04`, `Spine_05` (40% each)
- **Secondary**: `TailFin_Upper`, `TailFin_Lower` (10% each)

### Dorsal Crest
- **Primary**: `DorsalFin_left`, `DorsalFin_right` (50% each)

## Animation Constraints

### Spine Bending
- **Range**: -45° to +45°
- **Smoothness**: 0.8
- **Driven by**: Spline curvature

### Fin Flexing
- **Range**: -60° to +60°
- **Stiffness**: 0.6
- **Driven by**: Movement speed

### Gill Pulsing
- **Range**: 0.5x to 1.5x scale
- **Speed**: 1.5 cycles/second
- **Phase offset**: 0.2 between gills

## Integration with Spline System

The rigging system integrates with the spline-driven spine:

1. **Spline computes target positions** for each segment
2. **Bones follow spline targets** via constraints
3. **Mesh deforms** based on bone positions
4. **Result**: Smooth, organic whale motion

### Bone-to-Spline Mapping

```python
# Each spine bone corresponds to a spline segment
spine_bone_00 → spline_segment_0 (head)
spine_bone_01 → spline_segment_1
spine_bone_02 → spline_segment_2
...
spine_bone_05 → spline_segment_5 (tail)
```

## Weight Painting Guidelines

### Automatic Weight Assignment

The `apply_bone_weights_to_mesh()` function automatically assigns weights based on:
- **Distance to bone**: Closer vertices get higher weights
- **Influence radius**: Configurable per bone type
- **Normalization**: Weights sum to 1.0

### Manual Weight Painting

For fine control, manually paint weights:

1. **Select mesh** → Weight Paint mode
2. **Select bone** from vertex group list
3. **Paint weights**:
   - **Add**: Increase influence
   - **Subtract**: Decrease influence
   - **Smooth**: Blend weights

### Best Practices

- **Spine bones**: Full weight (1.0) on their segment
- **Fin bones**: Gradual falloff from fin base
- **Gill bones**: Localized to vent areas
- **Normalize**: Ensure weights sum to 1.0
- **Limit influences**: Max 4 bones per vertex

## Export Settings

### FBX Export
- **Format**: FBX 7.4 Binary
- **Include**: Armature, Mesh, Weights
- **Scale**: 1.0
- **Up Axis**: Z

### JSON Export
- **Rig info**: Bone hierarchy and positions
- **Weight data**: Vertex group assignments
- **Animation**: Bone transforms (optional)

## Testing Checklist

- [ ] Armature created with correct bone count
- [ ] Bone hierarchy correct (parent-child relationships)
- [ ] Mesh has Armature modifier
- [ ] Vertex groups created for each bone
- [ ] Weights assigned (automatic or manual)
- [ ] Weights normalized (sum to 1.0)
- [ ] Spine deformation smooth
- [ ] Fin movement natural
- [ ] Gill pulsing works
- [ ] Export successful

## Troubleshooting

### Bones Not Deforming Mesh
- Check Armature modifier is enabled
- Verify vertex groups exist
- Ensure weights are assigned
- Check modifier order (Armature should be first)

### Deformation Too Stiff
- Increase influence radius
- Smooth weight falloff
- Add more bones for fine control

### Deformation Too Loose
- Decrease influence radius
- Sharpen weight falloff
- Reduce bone count

### Weights Not Normalizing
- Use "Normalize All" in Weight Paint mode
- Check for locked vertex groups
- Verify max influences setting

## Files

- `blender_space_whale_rigging.py` - Rigging script
- `space_whale_skinning_registry.json` - Skinning configuration
- `SpaceWhaleRiggingGenerator.ps1` - Generator script
- `SPACE_WHALE_SKINNING_GUIDE.md` - This guide

## Next Steps

1. **Generate rig** using `SpaceWhaleRiggingGenerator.ps1`
2. **Apply to mesh** in Blender
3. **Paint weights** (automatic or manual)
4. **Test deformation** with spline system
5. **Export** for game integration

## Integration with Game

The rigging system works with:
- **Spline-driven spine** (SPACE_WHALE_SYSTEM.md)
- **Spring-damped physics** (SPACE_WHALE_SPRING_DAMPED.md)
- **Traveling wave** (undulation)
- **Steering bias** (turning)

Bone transforms are computed from spline positions and applied to drive mesh deformation in real-time.

