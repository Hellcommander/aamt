# Space Whale Quick Reference

## Tools Overview

| Tool | Purpose | Usage |
|------|---------|-------|
| `SpaceWhaleShipGenerator.ps1` | Generate visual assets (Blender) | `.\SpaceWhaleShipGenerator.ps1` |
| `SpaceWhaleImplementationGenerator.ps1` | Generate code implementation | `.\SpaceWhaleImplementationGenerator.ps1` |
| `blender_space_whale_renderer.py` | Render ship spritesheets | Called by generator |
| `transcendence_space_whale_exporter.py` | Export to XML | Called by generator |

## Implementation Status

**Core Systems**: ✅ 100% Complete
- Segmented ship system
- Spline-driven spine
- Swallow & metabolize
- Ramming (3 modes)
- Dynamic resizing (unified API)
- Backend API
- Nova Drift mutations

**Enhancements**: ⚠️ 60% Complete
- Armor regen (needs hybrid model)
- LOD system (needs implementation)
- Tail wave (needs full implementation)
- Contact mapping (needs enhancement)

**Optimization**: ❌ 0% Complete
- Memory layout (SoA)
- True multithreading
- Advanced batching

## Quick Commands

### Generate Implementation

```powershell
# Full hybrid implementation
.\SpaceWhaleImplementationGenerator.ps1

# Mod-only (no backend)
.\SpaceWhaleImplementationGenerator.ps1 -ImplementationMode modOnly

# With backend
.\SpaceWhaleImplementationGenerator.ps1 -ImplementationMode engineBackend
```

### Generate Visual Assets

```powershell
# Generate ship from registry
.\SpaceWhaleShipGenerator.ps1 -ShipId "leviathan_alpha"

# Custom registry
.\SpaceWhaleShipGenerator.ps1 -RegistryPath "my_ships.json"
```

### Test in Game

```lisp
; Resize
(resizePreview (objGetID gPlayerShip) 'spaceWhale 1.5 Nil)
(resizeApply (objGetID gPlayerShip) 'spaceWhale 1.5 Nil)

; Mutations
(swApplyMutation (objGetID gPlayerShip) "Leviathan")
(swApplyMutation (objGetID gPlayerShip) "GrowthSurge")

; State
(resizeGetState (objGetID gPlayerShip))
```

## File Locations

### Implementation Files
- `Extensions/ZZZ_CrossModCompatibility/parts/SpaceWhaleShip.xml`
- `Extensions/ZZZ_CrossModCompatibility/parts/ResizeAPI.xml`
- `Extensions/ZZZ_CrossModCompatibility/parts/SegmentedShipSystem.xml`
- `Extensions/ZZZ_CrossModCompatibility/backend/ModBackendAPI.h`

### Documentation
- `SPACE_WHALE_IMPLEMENTATION_GUIDE.md` - Complete guide
- `SPACE_WHALE_DESIGN_SPEC_ALIGNMENT.md` - Spec compliance
- `SPACE_WHALE_COMPLETE_IMPLEMENTATION.md` - Status summary

### Tools
- `SpaceWhaleImplementationGenerator.ps1` - Code generator
- `SpaceWhaleShipGenerator.ps1` - Asset generator
- `blender_space_whale_renderer.py` - Blender renderer

## Next Actions

1. **Implement armor regen hybrid model** (1-2 hours)
2. **Add LOD system** (2-3 hours)
3. **Enhance tail wave** (1-2 hours)
4. **Tune spring-damped physics** (1 hour)

**Total**: 5-8 hours to 100% spec compliance

