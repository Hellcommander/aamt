# Blender Quick Start - Space Whale Rigging

## Fastest Way to Get Started

### Method 1: Quickstart Script (Easiest)

1. **Open Blender**
2. **Import or create your space whale mesh**
3. **Select the mesh** (click on it)
4. **Open Scripting workspace**
5. **Open** `blender_rigging_quickstart.py` in script editor
6. **Run Script** (Alt+P or click Run button)
7. **Done!** Rig is created and applied

### Method 2: Command Line

```powershell
# Open Blender with your mesh file
blender your_ship_model.blend --python blender_rigging_quickstart.py
```

### Method 3: Full Registry-Based Setup

```powershell
# Generate rig from ship registry
.\SpaceWhaleRiggingGenerator.ps1 -RegistryPath "space_whale_ship_example.json" -OutputDir "Output/Rigging"
```

## What Gets Created

- ✅ **Armature** with spine bones (6 segments)
- ✅ **Fin bones** (dorsal, pectoral, tail)
- ✅ **Automatic weight assignment** to your mesh
- ✅ **Armature modifier** added to mesh

## Verify It Works

1. **Select armature** (SpaceWhaleRig)
2. **Switch to Pose mode** (Tab or mode selector)
3. **Select a spine bone** (e.g., Spine_02)
4. **Rotate it** (R key, then drag)
5. **Mesh should bend!** ✅

## Refine Weights (Optional)

1. **Select mesh**
2. **Switch to Weight Paint mode**
3. **Select bone** from vertex group list
4. **Paint weights**:
   - **Add**: Ctrl+Click
   - **Subtract**: Ctrl+Shift+Click
   - **Smooth**: Shift+Click
   - **Normalize**: Weights → Normalize All

## Add Animations

### Breathing (16 frames)

1. **Pose mode** → Select all spine bones (A)
2. **Frame 1**: Insert keyframe (I → Scale)
3. **Frame 16**: Scale 1.05 (S → 1.05), Insert keyframe
4. **Set to loop**: Timeline → Repeat

### Tail Sweep

1. **Pose mode** → Select Spine_05 (tail)
2. **Frame 1**: Insert keyframe
3. **Frame 30**: Rotate Z 15° (R → Z → 15), Insert keyframe
4. **Frame 60**: Rotate Z -15°, Insert keyframe
5. **Frame 90**: Rotate Z 0°, Insert keyframe

## Export

1. **File** → Export → FBX
2. **Settings**:
   - ✓ Selected Objects
   - ✓ Apply Transform
   - ✓ Add Leaf Bones
   - ✓ Armature
   - ✓ Mesh
   - ✓ Use Armature Deform

## Troubleshooting

**Mesh doesn't deform?**
- Check Armature modifier is enabled
- Verify vertex groups exist
- Try re-parenting: Select mesh + armature → Ctrl+P → "With Automatic Weights"

**Bones not visible?**
- Viewport Display → Show Bones: ✓
- Armature Display → Display As: Stick

**Weights look wrong?**
- Weight Paint mode → Weights → Normalize All
- Manually paint problem areas

## Files

- `blender_rigging_quickstart.py` - **Use this first!** (Simplest)
- `blender_space_whale_rigging.py` - Full-featured rigging script
- `BLENDER_RIGGING_SETUP_GUIDE.md` - Detailed guide
- `BLENDER_QUICK_START.md` - This quick start

## That's It!

Your space whale is now rigged and ready for animation! 🎉

