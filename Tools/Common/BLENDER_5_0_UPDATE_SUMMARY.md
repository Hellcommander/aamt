# Blender 5.0+ API Update Summary

## Changes Made

All Blender scripts have been updated to use Blender 5.0+ compatible code, removing deprecated API calls.

### Main Change: Removed `Material.use_nodes`

**Deprecated (Blender 5.0):**
```python
mat = bpy.data.materials.new(name="MaterialName")
mat.use_nodes = True  # ❌ Deprecated - will be removed in Blender 6.0
nodes = mat.node_tree.nodes
```

**Updated (Blender 5.0+):**
```python
mat = bpy.data.materials.new(name="MaterialName")
# Blender 5.0+: Materials use nodes by default (use_nodes deprecated)
nodes = mat.node_tree.nodes
```

### Updated Scripts

All Space Whale and related Blender scripts have been updated:

1. ✅ `blender_space_whale_120_facings.py` - Main spritesheet generator
2. ✅ `blender_space_whale_texture_setup.py` - Texture setup
3. ✅ `blender_space_whale_renderer.py` - Renderer (2 materials updated)
4. ✅ `blender_nova_drift_fx_renderer.py` - FX renderer (3 materials updated)
5. ✅ `blender_shield_aura_renderer.py` - Shield aura renderer (3 materials updated)
6. ✅ `blender_shield_renderer.py` - Shield renderer
7. ✅ `blender_projectile_renderer.py` - Projectile renderer

### Verification

All scripts have been verified:
- ✅ Python syntax is valid
- ✅ No deprecated `use_nodes` assignments remain
- ✅ Comments added explaining the change

### Blender Version Compatibility

- **Blender 5.0+**: ✅ Fully compatible (materials use nodes by default)
- **Blender 4.x**: ⚠️ May need `use_nodes = True` if materials don't have nodes by default
- **Blender 6.0+**: ✅ Will work (deprecated code removed)

### Testing

To test the updated scripts:
```powershell
# Test spritesheet generation
SpaceWhale120FacingsGenerator.ps1 -RegistryPath "space_whale_ship_example.json" -OutputDir "Output\Test"
```

The scripts should now run without deprecation warnings in Blender 5.0+.

---

**Last Updated:** Current session  
**Blender Version Target:** 5.0 and above

