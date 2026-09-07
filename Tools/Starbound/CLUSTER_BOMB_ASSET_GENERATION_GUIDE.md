# Cluster Bomb Generator Asset Generation Guide

Generate assets for the Cluster Bomb Generator system including bomb sprites, fragments, explosions, animations, and decals.

## Quick Start

```powershell
# Generate all cluster bomb assets
.\GenerateClusterBombAssets.ps1

# Use C++ backend for better quality
.\GenerateClusterBombAssets.ps1 -UseCppBackend

# Or generate everything including cluster bomb assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Cluster Bomb Sprites (5 sprites)

1. **cluster_bomb_basic** - Basic cluster bomb
2. **cluster_bomb_incendiary** - Incendiary cluster bomb
3. **cluster_bomb_emp** - EMP cluster bomb
4. **cluster_bomb_frag** - Fragmentation cluster bomb
5. **cluster_bomb_fuse** - Bomb fuse sprite

### Fragment Sprites (5 sprites)

1. **fragment_shard** - Jagged metal shard
2. **fragment_bolt** - Metal bolt
3. **fragment_sphere** - Metal sphere
4. **fragment_incendiary** - Burning fragment
5. **fragment_emp** - Electrical fragment

### Explosion Effects (5 effects)

1. **explosion_core** - Core explosion burst
2. **explosion_smoke** - Smoke ring
3. **explosion_debris** - Debris particles
4. **explosion_incendiary** - Fire explosion
5. **explosion_emp** - Electrical explosion

### Bomb Animations (3 animations)

1. **bomb_fuse_burning** - Fuse burning (8 frames, 1.0s)
2. **bomb_shell_cracking** - Shell cracking (10 frames, 0.3s)
3. **bomb_detonating** - Bomb detonating (12 frames, 0.4s)

### Explosion Decals (4 decals)

1. **explosion_decal_scorch** - Scorch mark
2. **explosion_decal_crack** - Crack pattern
3. **explosion_decal_incendiary** - Fire scorch mark
4. **explosion_decal_emp** - Electrical burn mark

## Total: ~22 Assets

## Output Structure

```
assets/
└── projectiles/
    └── cluster_bombs/
        ├── cluster_bomb_basic.png
        ├── cluster_bomb_incendiary.png
        ├── cluster_bomb_emp.png
        ├── cluster_bomb_frag.png
        ├── cluster_bomb_fuse.png
        ├── fragment_shard.png
        ├── fragment_bolt.png
        ├── fragment_sphere.png
        ├── fragment_incendiary.png
        ├── fragment_emp.png
        ├── explosion_core.particle
        ├── explosion_smoke.particle
        ├── explosion_debris.particle
        ├── explosion_incendiary.particle
        ├── explosion_emp.particle
        ├── bomb_fuse_burning/
        │   ├── bomb_fuse_burning.png
        │   ├── bomb_fuse_burning.animation
        │   └── bomb_fuse_burning.frames
        ├── bomb_shell_cracking/
        │   ├── bomb_shell_cracking.png
        │   ├── bomb_shell_cracking.animation
        │   └── bomb_shell_cracking.frames
        ├── bomb_detonating/
        │   ├── bomb_detonating.png
        │   ├── bomb_detonating.animation
        │   └── bomb_detonating.frames
        ├── explosion_decal_scorch.png
        ├── explosion_decal_crack.png
        ├── explosion_decal_incendiary.png
        └── explosion_decal_emp.png
```

## Integration

### Cluster Bomb Creation

```lua
-- Create cluster bomb
local bomb = ClusterBombGenerator:createBomb({
    shellRadius = 0.5,
    fuseLength = 0.2,
    fragmentCount = 12,
    explosionRadius = 5.0,
    sprite = "/projectiles/cluster_bombs/cluster_bomb_basic.png",
    fuseSprite = "/projectiles/cluster_bombs/cluster_bomb_fuse.png"
})
```

### Fragment Spawning

```lua
-- Spawn fragments on detonation
ClusterBombGenerator:spawnFragments({
    fragmentType = "shard",
    fragmentSprite = "/projectiles/cluster_bombs/fragment_shard.png",
    count = 12,
    spreadAngle = 45.0
})
```

### Explosion Effects

```lua
-- Spawn explosion effects
ClusterBombGenerator:spawnExplosion({
    position = bombPosition,
    coreEffect = "/projectiles/cluster_bombs/explosion_core.particle",
    smokeEffect = "/projectiles/cluster_bombs/explosion_smoke.particle",
    debrisEffect = "/projectiles/cluster_bombs/explosion_debris.particle",
    decal = "/projectiles/cluster_bombs/explosion_decal_scorch.png"
})
```

### Bomb Animations

```lua
-- Set bomb animation based on state
if bombState == "FUSE_BURNING" then
    bomb:setAnimation("/projectiles/cluster_bombs/bomb_fuse_burning/bomb_fuse_burning.animation")
elseif bombState == "SHELL_CRACKING" then
    bomb:setAnimation("/projectiles/cluster_bombs/bomb_shell_cracking/bomb_shell_cracking.animation")
elseif bombState == "DETONATING" then
    bomb:setAnimation("/projectiles/cluster_bombs/bomb_detonating/bomb_detonating.animation")
end
```

## Bomb Types

### Basic Cluster Bomb
- **Visual**: Metallic shell, standard fuse
- **Fragments**: Shards, bolts, spheres
- **Explosion**: Core burst, smoke, debris

### Incendiary Cluster Bomb
- **Visual**: Red/orange shell, fire appearance
- **Fragments**: Burning fragments
- **Explosion**: Fire explosion, fire scorch decal

### EMP Cluster Bomb
- **Visual**: Blue/cyan shell, electrical appearance
- **Fragments**: Electrical fragments
- **Explosion**: Electrical explosion, EMP burn decal

### Fragmentation Cluster Bomb
- **Visual**: Jagged shell, shrapnel appearance
- **Fragments**: Sharp shards, bolts
- **Explosion**: Intense debris, crack decal

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateClusterBombAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Bombs

Configure cluster bombs with asset references.

### Step 3: Integrate Effects

Integrate explosion effects, animations, and decals.

### Step 4: Test in Game

Load the mod and test cluster bombs in-game.

## Advanced Options

### Custom Bomb Types

Edit `GenerateClusterBombAssets.ps1` to add custom bomb types:

```powershell
@{
    Id = "cluster_bomb_custom"
    Name = "Custom Cluster Bomb"
    Description = "Custom cluster bomb description"
}
```

### Custom Fragments

Add custom fragment types to the `$fragmentSprites` array.

### Custom Explosions

Add custom explosion effects to the `$explosionEffects` array.

## Tips

1. **Bomb size**: Use 32x32 for bomb sprites
2. **Fragment size**: Use 16x16 for fragment sprites
3. **Decal size**: Use 64x64 for decals
4. **Animation frames**: 8-12 frames work well for bomb animations
5. **Explosion effects**: Create distinct effects for each bomb type

## Troubleshooting

### Bombs Not Appearing

- Check bomb definitions reference correct asset paths
- Verify sprites are in `assets/projectiles/cluster_bombs/`
- Check bomb system is initialized

### Fragments Not Spawning

- Check fragment sprite paths
- Verify fragment spawning logic
- Ensure fragment system is initialized

### Explosions Not Playing

- Verify particle files are in correct location
- Check effect paths in bomb definitions
- Ensure particle system is initialized

### Decals Not Rendering

- Check decal texture paths
- Verify decal system is initialized
- Ensure decal textures are in correct format

---

*Part of the Starbound Ollama Asset Generator suite*
