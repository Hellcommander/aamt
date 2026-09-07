# Space Whale Asset Generator GUI

## Overview

The **Space Whale Asset Generator GUI** provides a user-friendly graphical interface for generating high-quality space whale capital ship assets. It combines both the multi-stage Quality Asset Generator pipeline and the creative SD3 Texture Generator into a single, easy-to-use control panel.

## Features

### Visual Interface Components

1. **Generator Mode Selection**
   - **Quality Asset Generator**: Multi-stage pipeline producing fewer, higher-quality assets
   - **SD3 Texture Generator**: Creative texture and artwork generation using Stable Diffusion 3

2. **Image Preview**
   - Real-time thumbnail display (380x240) of the last generated asset
   - Automatically updates during generation
   - Shows filename below preview
   - Manual refresh button available

3. **Progress Tracking**
   - **Progress Bar**: Visual indicator of overall completion (0-100%)
   - **Percentage Display**: Numeric percentage with stage information
   - **Current Stage**: Shows what operation is currently running
   - **Status Counters**: Real-time tracking of warnings and errors
     - Green: No issues
     - Yellow: Warnings detected
     - Red: Errors detected

4. **Warnings & Errors Box**
   - Dedicated display area for all warnings and errors
   - Color-coded entries:
     - `[WARNING]` in yellow/orange
     - `[ERROR]` in red
   - Automatic scrolling to latest entry
   - Separate from general output log for easy troubleshooting

5. **Output Log**
   - Real-time display of generation process
   - Color-coded console output
   - Auto-scrolls to show latest messages

### Configuration Options

#### Basic Settings

- **Output Directory**: Target location for generated assets (with browse button)
- **Ship ID Filter**: Generate assets for specific ships or all ships
  - `(All Ships)` - Process all ships in registry
  - `leviathan_alpha` - Process only Leviathan Alpha
  - `serpent_void` - Process only Serpent of the Void
- **Draft Count**: Number of initial draft variations (1-20, default: 6)
- **Final Count**: Number of final refined assets (1-10, default: 2)
- **Quick Mode**: Skip time-consuming validation steps
- **Enable Refinement**: Use AI-powered refinement stage

#### SD3 Texture Generation

- **Enable SD3 Textures**: Toggle SD3 integration on/off
- **Fast Mode**: Skip design drafts for faster generation
- **Texture Type**: What to generate
  - `all` - All texture types (Blender, Projectile, Design Drafts, Full Ship Artwork)
  - `blender` - Only Blender-compatible diffuse textures
  - `projectile` - Only projectile sprites
  - `design_draft` - Only conceptual design drafts
  - `full_ship_artwork` - Only complete ship renders
- **Variations**: Number of variations per texture type (1-10, default: 3)

#### Pipeline Stages (Quality Generator)

Toggleable checkboxes to skip specific stages:
- **Skip Draft**: Skip initial draft generation
- **Skip Assess**: Skip quality assessment
- **Skip Refine**: Skip refinement stage
- **Skip Select**: Skip final selection
- **Skip Integrate**: Skip integration stage
- **Skip Spritesheet**: Skip spritesheet creation
- **Skip Items**: Skip item generation
- **Resume**: Resume from last completed stage
- **Skip Completed**: Skip already-completed assets

### Action Buttons

- **Generate Assets**: Start the generation process (disabled during generation)
- **Open Output Folder**: Launch Windows Explorer to view generated assets
- **Refresh Preview**: Manually update the image preview
- **Save Settings**: Persist current configuration to JSON file
- **Close**: Exit the application

## Usage

### Starting the GUI

Run the batch file:

```batch
SpaceWhaleAssetGeneratorGUI.bat
```

Or directly launch the PowerShell script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File SpaceWhaleAssetGeneratorGUI.ps1
```

### Workflow

1. **Select Generator Mode**
   - Choose between Quality Asset Generator or SD3 Texture Generator

2. **Configure Settings**
   - Set output directory
   - Adjust draft/final counts
   - Select ship ID (or generate for all ships)
   - Configure SD3 options if needed
   - Toggle stage skip flags as desired

3. **Generate Assets**
   - Click "Generate Assets" button
   - Monitor progress via:
     - Progress bar and percentage
     - Current stage display
     - Output log
     - Warnings & errors box
     - Live image preview updates

4. **Review Results**
   - Check the image preview for latest generated asset
   - Review warnings/errors for any issues
   - Click "Open Output Folder" to browse all generated files

5. **Save Settings (Optional)**
   - Click "Save Settings" to remember your configuration for next time

### Progress Monitoring

The GUI provides comprehensive progress tracking:

#### Progress Bar
- Shows 0-100% completion
- Updates based on:
  - Stage completion (Quality Generator)
  - Texture generation steps (SD3 Generator)

#### Stage Information
- **Quality Generator**: Shows "Stage X/Y" format
  - Example: "75% Complete (Stage 6/8)"
- **SD3 Generator**: Shows "[X/Y] Description" format
  - Example: "67% Complete" with "Generating Blender Texture (3/6)"

#### Real-Time Status
- **Current Stage**: Displays what's currently being processed
- **Warnings Count**: Increments when warnings are detected
- **Errors Count**: Increments when errors occur
- **Status Color Coding**:
  - Gray: Initial state
  - Green: Completed successfully
  - Yellow: Warnings present
  - Red: Errors detected

### Warnings & Errors Detection

The GUI automatically detects and highlights:

**Warnings** (Yellow/Orange):
- Lines containing: `WARNING`, `Warning`, `warn:`
- Examples:
  - `WARNING: Low quality score detected`
  - `[WARNING] Texture resolution below recommended`

**Errors** (Red):
- Lines containing: `ERROR`, `Error`, `error:`, `FAILED`, `Failed`, `Exception`
- Examples:
  - `ERROR: Failed to load ship registry`
  - `[ERROR] SD3 server not responding`
  - `Exception: File not found`

All warnings and errors are:
1. Counted in the status display
2. Shown in the dedicated Warnings & Errors box
3. Color-coded for easy identification
4. Auto-scrolled to keep latest visible

### Settings Persistence

Settings are automatically saved to:
```
SpaceWhaleAssetGeneratorGUI_Settings.json
```

This includes:
- Output directory
- All toggle states
- Numeric values (draft count, variations, etc.)
- Selected generator mode preferences
- Last used ship ID filter

Settings are automatically loaded when you start the GUI.

## Output Structure

Generated assets are organized in the output directory:

### Quality Generator Output
```
Output\SpaceWhaleAssets_HQ\
├── Stage1_Draft\
│   ├── Textures\
│   │   ├── Blender\
│   │   ├── Projectiles\
│   │   ├── DesignDrafts\
│   │   ├── FullShipArtwork\
│   │   └── Best\
│   │       ├── blender\
│   │       ├── design_draft\
│   │       └── full_ship_artwork\
├── Stage2_Assessment\
├── Stage3_Refinement\
├── Stage4_Selection\
├── Stage5_Integration\
├── Stage6_Spritesheets\
└── Stage7_Items\
```

### SD3 Generator Output
```
Output\Stage1_Draft\Textures\
├── Blender\
│   └── {shipId}_diffuse_v{N}.png
├── Projectiles\
│   └── {shipId}_projectile_v{N}.png
├── DesignDrafts\
│   └── {shipId}_design_draft_v{N}.png
├── FullShipArtwork\
│   └── {shipId}_full_{view}_v{N}.png
└── Best\
    ├── blender\
    ├── design_draft\
    └── full_ship_artwork\
```

## Troubleshooting

### GUI Won't Start
- Ensure PowerShell execution policy allows scripts
- Check that .NET Framework is installed (required for Windows Forms)

### Generation Fails Immediately
- Check the Warnings & Errors box for specific error messages
- Verify Python is installed and accessible (for Quality Generator)
- Verify SD3 server is running (for SD3 Generator)
- Ensure all required JSON files exist in the script directory

### Progress Bar Not Updating
- Progress tracking relies on parsing output from the generators
- If generators don't output expected progress messages, the bar may not update accurately
- Check the Output Log to see if generation is actually progressing

### Image Preview Not Showing
- Verify that images are being generated in the output directory
- Click "Refresh Preview" manually
- Check that image files aren't locked by another process

### High Warning/Error Count
- Review the Warnings & Errors box for specific issues
- Common warnings (low quality scores) are normal and expected
- Errors usually indicate configuration issues or missing dependencies

## Performance

### Quality Generator (Full Pipeline)
- **Time**: 10-30 minutes per ship (depends on settings)
- **Memory**: 2-4 GB RAM
- **Disk**: 500MB - 2GB per ship
- **CPU**: Moderate to high usage

### SD3 Texture Generator
- **Time**: 
  - Fast mode: 2-5 minutes per ship
  - Full mode: 5-15 minutes per ship
- **Memory**: 4-8 GB RAM (SD3 server)
- **Disk**: 100-500MB per ship
- **GPU**: Recommended for SD3 server

## Technical Details

### Requirements
- **Operating System**: Windows 10/11
- **PowerShell**: 5.1 or later
- **.NET Framework**: 4.5 or later (for Windows Forms)
- **Python**: 3.8+ (for Quality Generator)
- **SD3 Server**: Running and accessible (for SD3 mode)

### Architecture
- **UI Framework**: Windows Forms (.NET)
- **Background Processing**: PowerShell background jobs
- **Progress Parsing**: Regex-based output parsing
- **Image Loading**: System.Drawing.Image
- **Settings Storage**: JSON

### Output Parsing Patterns

The GUI recognizes these progress patterns:

**Quality Generator**:
```
Stage 1/8: Draft Generation
Stage 2/8: Quality Assessment
...
```

**SD3 Generator**:
```
[1/12] Generating Blender Texture for leviathan_alpha (variation 1)
[2/12] Generating Blender Texture for leviathan_alpha (variation 2)
...
```

**Warnings**:
- Any line matching: `/WARNING|Warning|warn:/i`

**Errors**:
- Any line matching: `/ERROR|Error|error:|FAILED|Failed|Exception/i`

## Tips & Best Practices

1. **Start with Fast Mode**: Test your configuration with SD3 Fast Mode before running full generation
2. **Monitor Early**: Watch the first minute of generation to catch configuration errors early
3. **Use Ship ID Filtering**: Generate one ship at a time when testing or debugging
4. **Save Settings Frequently**: Click "Save Settings" after finding a good configuration
5. **Check Errors Box**: Always review the Warnings & Errors box after generation completes
6. **Preview Images**: Use the automatic preview to verify output quality during generation
7. **Open Output Folder**: Browse generated files while generation is still running (read-only)
8. **Resume Capability**: Use Resume + Skip Completed for interrupted generations

## Known Limitations

- Progress percentage may not be perfectly accurate if generators change their output format
- Image preview may occasionally fail to load if file is still being written
- Very long output logs (>10,000 lines) may slow down the UI slightly
- Background job monitoring adds ~500ms latency to log updates
- Closing the GUI does NOT stop the background generation process

## Future Enhancements

- [ ] Add "Cancel Generation" button to stop in-progress jobs
- [ ] Add ETA (estimated time remaining) calculation
- [ ] Add generation history log with timestamps
- [ ] Add batch processing queue for multiple ships
- [ ] Add preset configurations (Quick, Balanced, High Quality)
- [ ] Add dark/light theme toggle
- [ ] Add export settings to command-line format
- [ ] Add image comparison view (before/after)
