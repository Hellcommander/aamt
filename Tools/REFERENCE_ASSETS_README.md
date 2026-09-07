# Reference Assets (Isolated Third-Party Files)

## Overview

The `ReferenceAssets/` folder contains **isolated third-party reference files** that tools can benefit from but **do not require**. These files are kept separate from tool code to maintain clean separation between tools and reference content.

## Location

**Primary Location (Relative to Tools folder root):**
```
Tools/ReferenceAssets/TranscendenceArt
```

**Directory Structure:**
```
Tools/
├── ReferenceAssets/          # Isolated third-party reference files (gitignored)
│   └── TranscendenceArt/     # Transcendence art references
│       ├── Ships/
│       ├── Weapons/
│       ├── Items/
│       ├── Projectiles/
│       └── ...
├── Transcendence/            # Tool code (tracked in git)
└── Common/                    # Shared tool code (tracked in git)
```

Tools use the Tools folder as the root, so the path is resolved relative to `Tools/` regardless of which subdirectory the tool is in.

## Purpose

- **Isolation**: Third-party reference files are kept separate from tool code
- **Optional**: Tools work without these files, but benefit when they're available
- **Reference**: Used as style guides, templates, and quality examples
- **Not Required**: Tools function independently without these files

## Migration from Old Location

The old location `Transcendence/TranscendenceArt/` is being moved to the isolated reference location:

1. **Old Location** (deprecated): `Tools/Transcendence/TranscendenceArt/`
2. **New Location**: `Tools/ReferenceAssets/TranscendenceArt/` (uses Tools folder as root)

Tools check locations in this order:
1. `Tools/ReferenceAssets/TranscendenceArt/` (primary - relative to Tools root)
2. Old location `Tools/Transcendence/TranscendenceArt/` (backward compatibility)

## Git Ignore

The `ReferenceAssets/` folder is in `.gitignore` because:
- Contains third-party content
- Can be large (art assets, models, textures)
- Not required for tools to function
- Users can add their own reference files

## Tool Integration

Tools automatically detect and use reference assets if available:

```powershell
# Tools check for reference assets automatically
$referencePath = Get-ReferenceAssetsPath

if ($referencePath) {
    # Use reference assets for style matching, quality examples, etc.
    Write-Log "Reference assets available: $referencePath" "Info"
} else {
    # Tools work fine without them
    Write-Log "Reference assets not found (optional)" "Info"
}
```

## Adding Your Own Reference Assets

1. Create `ReferenceAssets/TranscendenceArt/` in the Tools folder root if it doesn't exist
2. Add your reference files (models, textures, examples)
3. Tools will automatically detect and use them (using Tools folder as root)
4. Files are gitignored, so they won't be tracked

## Structure

```
ReferenceAssets/
└── TranscendenceArt/
    ├── Ships/              # Ship model references
    ├── Weapons/            # Weapon icon references
    ├── Items/              # Item icon references
    ├── Projectiles/        # Projectile sprite references
    ├── Spritesheets/       # Spritesheet examples
    ├── Textures/           # Texture examples
    └── Models/             # 3D model references
```

## Benefits

- **Style Consistency**: Tools can match styles from reference assets
- **Quality Examples**: Reference high-quality examples for generation
- **Template Library**: Reusable templates and patterns
- **Isolation**: Keeps third-party content separate from tool code

## Notes

- **Not Required**: Tools work perfectly without reference assets
- **Optional Enhancement**: Reference assets improve output quality when available
- **User-Specific**: Each user can add their own reference files
- **Git Ignored**: Reference assets are not tracked in version control

