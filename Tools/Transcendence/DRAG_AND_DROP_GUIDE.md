# Drag-and-Drop API Rules Generation

## Overview

The `GenerateApiRules.ps1` script and `GenerateApiRules.bat` wrapper now support **drag-and-drop** functionality. You can simply drag a new API folder onto the script to automatically generate rules for it.

## How to Use

### Method 1: Drag-and-Drop on Batch File (Easiest)

1. **Locate the API folder** you want to generate rules for:
   ```
   D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API60
   ```

2. **Drag the folder** onto `GenerateApiRules.bat`

3. The script will:
   - Auto-detect the API version from the folder name
   - Generate API rules for that version
   - Save to `api_rules_60.json`

### Method 2: Drag-and-Drop on PowerShell Script

1. **Drag the API folder** onto `GenerateApiRules.ps1`

2. Same auto-detection and generation as Method 1

### Method 3: Command Line (Traditional)

```powershell
.\GenerateApiRules.ps1 -ApiVersion 60
```

## Supported Folder Patterns

The script recognizes these folder name patterns:

- ✅ `TranscendenceDev-integration-API##` (e.g., `TranscendenceDev-integration-API60`)
- ✅ Any folder containing the pattern in its path

## What Happens

When you drag-and-drop a folder:

1. **Detection**: Script extracts API version from folder name
2. **Registration**: If not already registered, the API version is added to the available list
3. **Generation**: API rules are generated for that version
4. **Output**: Rules saved to `api_rules_##.json` and `api_rules.json`

## Example Output

```
═══════════════════════════════════════════════════════════
  DRAG-AND-DROP DETECTED
═══════════════════════════════════════════════════════════

Detected API version: 60
From folder: TranscendenceDev-integration-API60
Path: D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API60

Generating API rules for API 60...
```

## Troubleshooting

### "API version not found" Error

**Cause**: The folder doesn't contain the expected `Transcendence\TransCore` subdirectory.

**Solution**: Ensure the API folder structure is:
```
TranscendenceDev-integration-API60/
  └── Transcendence/
      └── TransCore/
          └── (XML files)
```

### "Not an API folder" Warning

**Cause**: The dropped folder doesn't match the expected naming pattern.

**Solution**: Rename the folder to match `TranscendenceDev-integration-API##` pattern.

### Script Doesn't Respond to Drag-and-Drop

**Cause**: PowerShell execution policy or path issues.

**Solution**: 
- Use the `.bat` wrapper file instead
- Or run: `powershell -ExecutionPolicy Bypass -File GenerateApiRules.ps1 "path\to\folder"`

## Tips

- **Double-click** `GenerateApiRules.bat` to use the default API version (no drag-and-drop needed)
- The script **auto-detects** all available API versions on startup
- Use `-Compare` flag to compare all versions: `.\GenerateApiRules.ps1 -Compare`
- Use `-ListVersions` to see all detected versions: `.\GenerateApiRules.ps1 -ListVersions`

