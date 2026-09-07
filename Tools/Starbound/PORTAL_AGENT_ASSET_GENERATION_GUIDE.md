# PortalAgent System Asset Generation Guide

Generate visual assets for the PortalAgent System including portal sprites, particle effects, editor UI elements, extension visuals, state indicators, preview visuals, and network visuals.

## Quick Start

```powershell
# Generate all PortalAgent assets
.\GeneratePortalAgentAssets.ps1

# Use C++ backend for better quality
.\GeneratePortalAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Portal Sprites (7 portals)

1. **portal_standard** - Standard portal
2. **portal_dimensional** - Dimensional portal
3. **portal_temporal** - Temporal portal
4. **portal_quantum** - Quantum portal
5. **portal_void** - Void portal
6. **portal_recursive** - Recursive portal
7. **portal_network** - Network portal

### Portal Particle Effects (6 effects)

1. **portal_spark_trail** - Spark trail particle effect
2. **portal_embers** - Embers particle effect
3. **portal_swirl** - Swirl particle effect
4. **portal_pulse** - Pulse particle effect
5. **portal_distortion** - Distortion particle effect
6. **portal_rift** - Rift particle effect

### Portal Editor UI Elements (8 elements)

1. **editor_ring_designer** - Ring designer UI icon
2. **editor_shader** - Shader editor UI icon
3. **editor_particle_profiler** - Particle profiler UI icon
4. **editor_link_manager** - Link manager UI icon
5. **editor_collider_debug** - Collider debug UI icon
6. **editor_preview** - Preview UI icon
7. **editor_save** - Save UI icon
8. **editor_load** - Load UI icon

### Portal Extension Visuals (7 visuals)

1. **extension_recursive** - Recursive portal extension
2. **extension_env_blend** - Environmental blend extension
3. **extension_rift** - Dimensional rift extension
4. **extension_ai_nav** - AI navigation extension
5. **extension_network** - Network sync extension
6. **extension_cubemap** - Cubemap probe
7. **extension_render_target** - Render target

### Portal State Indicators (8 indicators)

1. **state_open** - Portal open state
2. **state_closed** - Portal closed state
3. **state_opening** - Portal opening state
4. **state_closing** - Portal closing state
5. **state_traversing** - Portal traversing state
6. **state_cooldown** - Portal cooldown state
7. **state_linked** - Portal linked state
8. **state_unlinked** - Portal unlinked state

### Portal Preview Visuals (4 visuals)

1. **preview_portal** - Portal preview sprite
2. **preview_rim_collider** - Rim collider preview
3. **preview_trigger_volume** - Trigger volume preview
4. **preview_destination** - Destination preview

### Portal Network Visuals (4 visuals)

1. **network_node** - Portal network node
2. **network_edge** - Portal network edge
3. **network_path** - Portal network path
4. **network_sync** - Network sync indicator

## Total: ~44 Assets

## Output Structure

```
assets/
└── portals/
    ├── sprites/
    │   ├── portal_standard.png
    │   ├── portal_dimensional.png
    │   └── ... (all portal sprites)
    ├── particles/
    │   ├── portal_spark_trail.particle
    │   ├── portal_embers.particle
    │   └── ... (all particle effects)
    ├── editor/
    │   ├── editor_ring_designer.png
    │   ├── editor_shader.png
    │   └── ... (all editor UI elements)
    ├── extensions/
    │   ├── extension_recursive.png
    │   ├── extension_env_blend.png
    │   └── ... (all extension visuals)
    ├── states/
    │   ├── state_open.png
    │   ├── state_closed.png
    │   └── ... (all state indicators)
    ├── preview/
    │   ├── preview_portal.png
    │   ├── preview_rim_collider.png
    │   └── ... (all preview visuals)
    └── network/
        ├── network_node.png
        ├── network_edge.png
        └── ... (all network visuals)
```

## Integration

### PortalFactory

```cpp
// Generate portal
PortalFactory::generateAsync(portalParams, swirlParams, particleParams, audioParams, teleportParams, collisionParams);
// Uses: /assets/portals/sprites/portal_standard.png
// Uses: /assets/portals/particles/portal_spark_trail.particle
// Uses: /assets/portals/particles/portal_embers.particle

// Build portal ring
MeshGen::buildPortalRing(portalParams);
// Uses: /assets/portals/sprites/portal_*.png

// Build portal particles
ParticleGen::buildPortalParticles(particleParams);
// Uses: /assets/portals/particles/portal_spark_trail.particle
// Uses: /assets/portals/particles/portal_embers.particle
```

### PortalEditorTools

```cpp
// Show ring designer
PortalEditorTools::showRingDesigner(portalBundle, portalParams);
// Uses: /assets/portals/editor/editor_ring_designer.png

// Show shader editor
PortalEditorTools::showShaderEditor(shaderHandle, swirlParams);
// Uses: /assets/portals/editor/editor_shader.png

// Show particle profiler
PortalEditorTools::showParticleProfiler(particleHandle, particleParams);
// Uses: /assets/portals/editor/editor_particle_profiler.png

// Show link manager
PortalEditorTools::showLinkManager(teleportLinks);
// Uses: /assets/portals/editor/editor_link_manager.png

// Show collider debug
PortalEditorTools::showColliderDebug(colliderHandle, showRim, showTrigger);
// Uses: /assets/portals/editor/editor_collider_debug.png
// Uses: /assets/portals/preview/preview_rim_collider.png
// Uses: /assets/portals/preview/preview_trigger_volume.png
```

### PortalExtensions

```cpp
// Setup recursive RTT
RecursiveGen::setupRecursiveRTT(srcId, dstId, recursiveParams);
// Uses: /assets/portals/extensions/extension_recursive.png
// Uses: /assets/portals/extensions/extension_render_target.png

// Apply environmental blend
EnvProbeGen::applyEnvBlend(materialHandle, envBlendParams);
// Uses: /assets/portals/extensions/extension_env_blend.png
// Uses: /assets/portals/extensions/extension_cubemap.png

// Build rift shader
RiftGen::buildRiftShader(shaderHandle, riftParams);
// Uses: /assets/portals/extensions/extension_rift.png
// Uses: /assets/portals/particles/portal_rift.particle

// Build portal graph
PortalGraphGen::buildGraph(teleportLinks);
// Uses: /assets/portals/extensions/extension_ai_nav.png
// Uses: /assets/portals/network/network_node.png
// Uses: /assets/portals/network/network_edge.png
// Uses: /assets/portals/network/network_path.png

// Setup network sync
PortalNetworkGen::setupReplication(netSyncParams);
// Uses: /assets/portals/extensions/extension_network.png
// Uses: /assets/portals/network/network_sync.png
```

### PortalPreviewActor

```cpp
// Initialize preview
PortalPreviewActor::initialize();
// Uses: /assets/portals/preview/preview_portal.png

// Update portal
PortalPreviewActor::updatePortal(portalParams, swirlParams, particleParams, audioParams, teleportParams, collisionParams);
// Uses: /assets/portals/sprites/portal_*.png
// Uses: /assets/portals/particles/portal_*.particle

// Show rim collider
PortalPreviewActor::getShowRimCollider();
// Uses: /assets/portals/preview/preview_rim_collider.png

// Show trigger volume
PortalPreviewActor::getShowTriggerVolume();
// Uses: /assets/portals/preview/preview_trigger_volume.png
```

## Portal Types

### Portal Variants
- **Standard**: Basic portal ring
- **Dimensional**: Dimensional rift portal
- **Temporal**: Time portal
- **Quantum**: Quantum portal
- **Void**: Void portal
- **Recursive**: Recursive portal (nested reflections)
- **Network**: Network portal (multiplayer sync)

## Portal Parameters

### PortalParams
- **outerRadius**: Outer ring radius
- **thickness**: Ring thickness
- **rimColor**: Rim color (default: purple)
- **coreColor**: Core color (default: dark purple)
- **doubleRing**: Enable double ring

### SwirlParams
- **swirlSpeed**: Swirl rotation speed
- **distortionAmplitude**: UV distortion strength
- **noiseScale**: Procedural noise frequency
- **pulseFrequency**: Core pulse rate

### ParticleParams
- **sparkTrail**: Enable spark trail
- **sparkCount**: Number of sparks
- **sparkLifetime**: Spark lifetime
- **sparkColor**: Spark color
- **embers**: Enable embers
- **emberCount**: Number of embers

## Portal Extensions

### Extension Types
- **Recursive**: Recursive portal reflections (RTT)
- **Environmental Blend**: Environmental blending with cubemaps
- **Dimensional Rift**: Dimensional rift effects
- **AI Navigation**: Portal network AI pathfinding
- **Network Sync**: Multiplayer synchronization

## Portal States

### State Types
- **Open**: Portal is open
- **Closed**: Portal is closed
- **Opening**: Portal is opening
- **Closing**: Portal is closing
- **Traversing**: Entity is traversing portal
- **Cooldown**: Portal is on cooldown
- **Linked**: Portal is linked to destination
- **Unlinked**: Portal is not linked

## Portal Editor

### Editor Tools
- **Ring Designer**: Real-time geometry editing
- **Shader Editor**: Live shader reload
- **Particle Profiler**: Performance monitoring
- **Link Manager**: Portal destination mapping
- **Collider Debug**: Visual collision validation
- **Preview**: Live portal preview

## Portal Network

### Network Components
- **Node**: Portal network node
- **Edge**: Portal network connection
- **Path**: Portal network path
- **Sync**: Network synchronization

## Workflow

### Step 1: Generate Assets

```powershell
.\GeneratePortalAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure PortalFactory

Set up PortalFactory with asset paths.

### Step 3: Create Portal

```cpp
PortalFactory factory;
factory.initialize(cacheSize, numThreads);
auto bundle = factory.generateAsync(portalParams, swirlParams, particleParams, audioParams, teleportParams, collisionParams);
```

### Step 4: Use Portal Editor

```cpp
PortalEditorTools::showPortalEditor(portalBundle, portalParams, swirlParams, particleParams, audioParams, teleportParams, collisionParams);
```

### Step 5: Enable Extensions

```cpp
PortalExtensionManager manager;
manager.initializeExtensions(portalExtensions);
```

### Step 6: Test in Game

Load the mod and test portal system in-game.

## Advanced Options

### Custom Portal Types

Edit `GeneratePortalAgentAssets.ps1` to add custom portal types.

### Custom Particle Effects

Add custom particle effects as needed.

### Custom Extensions

Add custom portal extensions with unique visuals.

## Tips

1. **Portal sprites**: Use 64x64 for portal sprites
2. **Particle effects**: Use appropriate sizes for particle effects
3. **Editor icons**: Use 32x32 for editor UI icons
4. **State indicators**: Make states clearly visible
5. **Extension visuals**: Keep extensions distinct
6. **Network visuals**: Make network connections clear
7. **Preview visuals**: Keep preview elements simple

## Troubleshooting

### Portals Not Displaying

- Check portal sprite paths
- Verify sprites are in `assets/portals/sprites/`
- Ensure PortalFactory is initialized

### Particle Effects Not Showing

- Check particle effect paths
- Verify effects are in `assets/portals/particles/`
- Ensure particle system is initialized

### Editor Not Working

- Check editor icon paths
- Verify icons are in `assets/portals/editor/`
- Ensure editor system is initialized

### Extensions Not Functioning

- Check extension visual paths
- Verify visuals are in `assets/portals/extensions/`
- Ensure extension system is enabled

### Network Not Syncing

- Check network visual paths
- Verify visuals are in `assets/portals/network/`
- Ensure network system is configured

---

*Part of the Starbound Ollama Asset Generator suite*
