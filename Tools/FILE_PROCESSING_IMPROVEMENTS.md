# File Processing Improvements

This document describes the improvements made to file processing tools to provide better safety, user feedback, and control.

## Shared Utilities

A new shared utility module has been created at `Shared/file_processing_utils.py` that provides:

### Features

1. **Sequential Processing**: Process items one at a time in alphabetical order
2. **Automatic Backups**: Always create backups before making changes
3. **User Prompts**: Prompt before processing each item with timeout (defaults to "yes")
4. **Enhanced Output**: Show which file is being worked on, what task is being performed, why it needs processing, and how it's being processed
5. **Progress Tracking**: Display progress as "[X/Total] Processing: ItemName"

### Functions

- `prompt_with_timeout()`: Prompt user with timeout, defaults to "yes" if no response
- `create_backup()`: Create timestamped backups of files or directories
- `process_items_sequentially()`: Main function for processing items with all safety features
- `format_file_processing_output()`: Format output showing file processing details

## Updated Tools

### 1. Qud Mod Fixer (`Qud/qud_mod_fixer.py`)

**Changes:**
- Processes mods one at a time in alphabetical order
- Always creates backups before making changes (ignores `--no-backup` flag)
- Prompts for each mod with timeout (defaults to "yes")
- Shows enhanced output: `[FILE]`, `[TASK]`, `[WHY]`, `[HOW]`
- Displays progress: `[1/5] Processing: ModName`

**Wrapper Scripts:**
- `QudModFixer.ps1`: Enhanced output formatting for PowerShell
- `QudModFixer.bat`: Passes through to PowerShell script

### 2. Terraria Mod Fixer (`TerrariaMods/tmodloader_mod_fixer.py`)

**Changes:**
- Uses shared utilities for sequential file processing (non-GUI mode)
- Processes files one at a time in alphabetical order
- Creates backups before fixing each file
- Prompts before processing each file
- Shows enhanced output about what's being fixed and why

**Note:** GUI mode uses original processing logic to maintain compatibility.

## How to Use in Other Tools

### Basic Example: Processing Files

```python
from file_processing_utils import process_items_sequentially, format_file_processing_output

# Process files one at a time
def process_file(file_path, idx, total):
    format_file_processing_output(
        file_path,
        "Fixing API compatibility",
        "File uses outdated API calls",
        "Updating to match current API"
    )
    # ... your processing logic ...
    return {'success': True}

files = list(Path("mods").glob("*.cs"))
results = process_items_sequentially(
    items=files,
    item_name="file",
    process_func=process_file,
    create_backups=True,
    prompt_before_processing=True
)
```

### Example: Processing Mods

```python
from file_processing_utils import process_items_sequentially

def analyze_mod(mod_path):
    # Analyze mod and return issue count
    issues = find_issues(mod_path)
    return {'total_issues': len(issues)}

def fix_mod(mod_path, idx, total):
    # Fix the mod
    fix_issues(mod_path)
    return {'success': True}

mods = [Path("mods") / d for d in os.listdir("mods") if (Path("mods") / d).is_dir()]
results = process_items_sequentially(
    items=mods,
    item_name="mod",
    process_func=fix_mod,
    analyze_func=analyze_mod,
    create_backups=True,
    prompt_before_processing=True
)
```

## Benefits

1. **Safety**: Backups are always created before changes
2. **Control**: User can skip items they don't want to process
3. **Transparency**: Clear output showing what's happening and why
4. **Order**: Alphabetical processing makes it predictable
5. **Recovery**: Backups are kept even after successful fixes

## Migration Guide

To update an existing tool:

1. Import the shared utilities:
   ```python
   from file_processing_utils import (
       process_items_sequentially,
       format_file_processing_output,
       prompt_with_timeout
   )
   ```

2. Replace your processing loop with `process_items_sequentially()`

3. Create a processing function that takes `(item, index, total)` and returns a result dict

4. Optionally create an analysis function that takes `item` and returns analysis dict

5. Update wrapper scripts to format output (see `QudModFixer.ps1` for examples)

## Notes

- Backups are always created (the `--no-backup` flag is ignored for safety)
- Prompts default to "yes" after 5 seconds if no response
- Processing is always sequential (one item at a time)
- Items are sorted alphabetically before processing
- Backups are kept even after successful fixes (in case AI makes mistakes)

