# Space Whale Asset Generator GUI - Quick Start

## What You Get

A graphical control panel with:
- ✅ **Real-time progress tracking** with percentage and stage display
- ✅ **Dedicated warnings/errors box** showing all issues as they occur
- ✅ **Live image preview** of last generated asset
- ✅ **All settings in one place** with toggles and dropdowns
- ✅ **Settings persistence** - your preferences are saved
- ✅ **Two generation modes** - Quality pipeline or SD3 textures

## How to Use

### 1. Launch the GUI

Double-click:
```
SpaceWhaleAssetGeneratorGUI.bat
```

### 2. Configure (First Time)

**Basic Setup:**
- Set your **Output Directory** (use Browse button)
- Choose **Ship ID** or leave as "(All Ships)"
- Adjust **Draft Count** (more = better variety, slower)
- Adjust **Final Count** (how many assets you want)

**For Quick Testing:**
- ☑ **Quick Mode** (faster)
- ☑ **SD3 Fast Mode** (skip design drafts)
- Set Draft Count to 3
- Set Final Count to 1

**For Best Quality:**
- ☐ Quick Mode (unchecked)
- ☑ Enable Refinement
- ☑ Enable SD3 Textures
- ☐ SD3 Fast Mode (unchecked)
- Set Draft Count to 6+
- Set Final Count to 2+

### 3. Generate

Click **"Generate Assets"**

### 4. Monitor Progress

Watch these areas:
1. **Progress Bar** - Shows 0-100% completion
2. **Percentage Label** - Shows "X% Complete (Stage Y/Z)"
3. **Current Stage** - Shows what's running now
4. **Status Counters** - "Warnings: X | Errors: X"
   - Green = All good
   - Yellow = Warnings detected
   - Red = Errors found
5. **Warnings & Errors Box** - See specific issues
6. **Image Preview** - Updates as new assets are created

### 5. Review Results

When complete:
- Check **Image Preview** for latest asset
- Review **Warnings & Errors Box** for any issues
- Click **"Open Output Folder"** to see all files

## What Gets Generated

### Quality Generator Mode
```
Output\SpaceWhaleAssets_HQ\
├── Stage1_Draft\Textures\     ← Initial textures (Blender, SD3)
├── Stage2_Assessment\          ← Quality scores
├── Stage3_Refinement\          ← Enhanced versions
├── Stage4_Selection\           ← Best picks
├── Stage5_Integration\         ← Game-ready assets
├── Stage6_Spritesheets\        ← Sprite sheets
└── Stage7_Items\               ← Item definitions
```

### SD3 Texture Generator Mode
```
Output\Stage1_Draft\Textures\
├── Blender\                    ← Diffuse textures
├── Projectiles\                ← Projectile sprites
├── DesignDrafts\               ← Concept art
├── FullShipArtwork\            ← Complete renders
└── Best\                       ← Top-quality selections
```

## Progress Tracking Features

### Progress Bar
- Visual indicator: 0-100%
- Updates every 500ms
- Based on actual stage/step completion

### Percentage Display
Shows format like:
- `"42% Complete (Stage 3/7)"` - Quality mode
- `"67% Complete"` - SD3 mode

### Current Stage
Shows what's happening:
- `"Current: Generating Blender Texture for leviathan_alpha"`
- `"Current: Stage 2 - Quality Assessment"`

### Status Counters
- **Warnings**: `WARNING`, `Warning`, `warn:` in output
- **Errors**: `ERROR`, `error:`, `FAILED`, `Exception` in output
- **Color-coded**:
  - Gray = Starting
  - Green = No issues
  - Yellow = Warnings present
  - Red = Errors detected

### Warnings & Errors Box
Dedicated display showing:
```
[WARNING] Low quality score: 0.45 (threshold: 0.5)
[WARNING] Image resolution below recommended: 512x512
[ERROR] Failed to connect to SD3 server
[ERROR] Ship registry file not found
```

Features:
- Auto-scrolls to latest entry
- Color-coded background (dark red tint)
- Orange text for visibility
- Separate from general log

## Understanding the Displays

### During Generation

**Output Log** (left):
```
Starting Quality Asset Generator...
Command: python space_whale_quality_asset_generator.py ...
Stage 1/8: Draft Generation
Generating draft 1/6...
```

**Warnings & Errors** (right):
```
[WARNING] Low quality score detected for draft 2
[ERROR] SD3 server timeout, retrying...
```

**Progress Area** (top right):
```
[Progress Bar: ████████████░░░░░░░░] 
67% Complete (Stage 5/8)
Current: Refinement stage - enhancing textures
Warnings: 3 | Errors: 1
```

**Image Preview** (center right):
- Shows latest generated PNG
- Updates automatically every 500ms
- Displays filename below image

### After Completion

**Success:**
- Progress bar at 100%
- "Generation complete!" message (green)
- Popup: "Asset generation completed successfully!"
- Shows final warning/error counts

**Failure:**
- Progress bar stuck at last position
- "Generation failed!" message (red)
- Popup: "Asset generation failed..."
- Check Warnings & Errors box for details

## Troubleshooting

### "No progress updates"
- Check Output Log - generation may still be running
- Progress tracking depends on output format
- Wait at least 30 seconds before assuming failure

### "Many warnings"
- Warnings are often normal (quality thresholds)
- Check Warnings & Errors box to see if they're critical
- Low quality scores are expected for some drafts

### "Errors immediately"
- Check first error in Warnings & Errors box
- Common causes:
  - Python not installed
  - SD3 server not running
  - Missing JSON files
  - Wrong output directory path

### "Image preview not updating"
- Click "Refresh Preview" button
- Check if files are being created in output folder
- May take 1-2 minutes before first image appears

## Settings Explained

### Generator Mode
- **Quality**: Full pipeline, game-ready assets
- **SD3 Only**: Just textures and artwork

### Basic Settings
- **Output Directory**: Where files are saved
- **Ship ID Filter**: Which ship(s) to generate
- **Draft Count**: Initial variations to try (more = slower, better variety)
- **Final Count**: How many to keep (usually 1-3)
- **Quick Mode**: Skip validation (faster, less thorough)
- **Enable Refinement**: Use AI enhancement (slower, better quality)

### SD3 Settings
- **Enable SD3**: Use Stable Diffusion 3 for textures
- **Fast Mode**: Skip design drafts (2-3x faster)
- **Texture Type**: What to generate
- **Variations**: Versions per texture (1-10)

### Stage Skips
- Skip individual pipeline stages
- Useful for testing or partial regeneration
- **Resume**: Continue from where you left off
- **Skip Completed**: Don't regenerate existing files

## Tips

1. **Start Small**: Test with 1 ship, Quick mode, Fast SD3
2. **Watch Progress**: Monitor for first 1-2 minutes to catch errors early
3. **Save Settings**: Once you find a good config, click "Save Settings"
4. **Check Errors Box**: Always review warnings/errors after completion
5. **Use Ship Filter**: Generate one ship at a time when debugging
6. **Open Output Early**: You can browse files while generation is running

## Performance Expectations

### Quick Test (1 ship, Quick mode, SD3 Fast)
- **Time**: 3-5 minutes
- **Progress updates**: Every 10-20 seconds
- **Output**: ~50MB

### Standard Quality (1 ship, normal settings)
- **Time**: 15-25 minutes
- **Progress updates**: Every 30-60 seconds
- **Output**: ~300MB

### Full Quality (1 ship, all features, no skips)
- **Time**: 25-40 minutes
- **Progress updates**: Every 1-2 minutes
- **Output**: ~500MB-1GB

## Visual Guide to the Interface

```
┌─────────────────────────────────────────────────────────────┐
│ Space Whale Asset Generator - Control Panel                 │
├─────────────────────────────────┬───────────────────────────┤
│ [Generator Mode]                │ [Image Preview]           │
│  ⦿ Quality Asset Generator      │ ┌───────────────────────┐ │
│  ○ SD3 Texture Generator        │ │                       │ │
│                                 │ │   [Latest Asset]      │ │
│ [Basic Settings]                │ │                       │ │
│  Output: [____________] Browse  │ └───────────────────────┘ │
│  Ship ID: [All Ships ▼]        │   filename.png            │
│  Draft: [6] Final: [2]         ├───────────────────────────┤
│  ☑ Quick  ☑ Refinement         │ [Progress]                │
│                                 │ ████████████░░░░░░ 67%    │
│ [SD3 Settings]                  │ Stage 5/8                 │
│  ☑ Enable SD3  ☐ Fast Mode     │ Current: Refining...      │
│  Type: [all ▼]  Vars: [3]      │ Warnings: 2 | Errors: 0   │
│                                 │                           │
│ [Pipeline Stages]               │                           │
│  ☐ Skip Draft   ☐ Skip Assess  │                           │
│  ☐ Skip Refine  ☐ Skip Select  │                           │
│  ☐ Resume       ☐ Skip Done    │                           │
├─────────────────────────────────┴───────────────────────────┤
│ [Output Log]              │ [Warnings & Errors]             │
│ Starting generation...    │ [WARNING] Low quality: 0.45     │
│ Stage 1/8: Draft...      │ [ERROR] Timeout, retrying...    │
│ Generating texture 1/6... │                                 │
├─────────────────────────────────────────────────────────────┤
│ [Generate] [Open Folder] [Refresh] [Save] [Close]          │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

1. Launch the GUI: `SpaceWhaleAssetGeneratorGUI.bat`
2. Configure for your needs (or use defaults)
3. Click "Generate Assets"
4. Monitor progress in real-time
5. Review results in output folder

For detailed information, see `GUI_DOCUMENTATION.md`.
