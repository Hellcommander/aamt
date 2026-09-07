# ToME Mod Checker & Ollama-Guided Fixing Assistant

## Overview

A comprehensive mod validation tool for **Tales of Maj'Eyal** with:
- **Mod Structure Validation** - Checks mod files and structure
- **Lua Syntax Checking** - Validates Lua code
- **Ollama AI Integration** - Suggests fixes using CodeLlama
- **Drag & Drop GUI** - Easy-to-use graphical interface
- **Export Results** - JSON export for integration

## Features

### Mod Validation

- **Structure Checks**
  - Required files (init.lua)
  - Directory structure
  - Data directory organization
  
- **Lua Validation**
  - Syntax checking
  - Common mistakes detection
  - loadPrevious(...) usage
  - String literal validation
  
- **Graphics Validation**
  - Sprite metadata checking
  - Missing files detection
  
- **Localization Checks**
  - Locale directory structure
  - Missing translations

### AI-Powered Fixing

- **Automatic Fix Suggestions** - Uses Ollama (CodeLlama) to suggest fixes
- **Issue Explanation** - AI explains what's wrong and why
- **Code Generation** - Generates fixed code snippets
- **Context-Aware** - Uses file context for better suggestions

### GUI Features

- **Drag & Drop** - Drop mod folders directly onto the window
- **Issue Tree View** - Color-coded severity (Error/Warning/Info)
- **Detailed View** - See issue details and code
- **AI Suggestions** - Get AI-generated fixes
- **Export** - Save results as JSON

## Installation

### Requirements

```bash
pip install tkinterdnd2 requests
```

### Ollama Setup (Optional, for AI features)

```bash
# Install Ollama
# https://ollama.ai

# Start Ollama
ollama serve

# Pull CodeLlama model
ollama pull codellama:34b
```

## Usage

### GUI Mode

```bash
python tome_mod_checker_gui.py
```

1. **Drag & Drop** a mod folder onto the window, or
2. **Browse** for a mod directory
3. Click **"Check Mod"** to validate
4. Review issues in the tree view
5. Select an issue to see details
6. Click **"Get AI Fixes"** for AI suggestions

### Command Line Mode

```bash
# Basic check
python tome_mod_checker.py /path/to/mod

# With ToME source reference
python tome_mod_checker.py /path/to/mod --tome-source /path/to/tome/source

# JSON output
python tome_mod_checker.py /path/to/mod --json > results.json
```

## What Gets Checked

### Required Files

- `init.lua` - Mod initialization file
  - Required fields: `long_name`, `short_name`, `for_module`
  - Syntax validation
  - loadPrevious usage

### Directory Structure

- `data/` - Data directory
  - `gfx/` - Graphics files
  - `lua/` - Lua scripts
  - `locale/` - Localization files

### Lua Files

- Syntax errors
- Missing `loadPrevious(...)`
- Unclosed strings
- Common API mistakes
- Function usage validation

### Graphics

- Missing `.meta.json` files for sprites
- File existence checks

## Issue Severity

- **ERROR** - Critical issues that will prevent mod loading
- **WARNING** - Issues that may cause problems
- **INFO** - Suggestions and best practices

## AI Fixing

The AI fixer uses Ollama (CodeLlama-34B) to:

1. **Analyze Issues** - Understands the problem
2. **Suggest Fixes** - Generates corrected code
3. **Explain Problems** - Provides context and reasoning

### Example AI Fix

**Issue:**
```
Missing loadPrevious(...) in talent file
```

**AI Suggestion:**
```lua
local _M = loadPrevious(...)

newTalent{
  -- ... rest of code
}
```

## Export Format

Results can be exported as JSON:

```json
{
  "mod_path": "/path/to/mod",
  "summary": {
    "errors": 2,
    "warnings": 5,
    "info": 1
  },
  "issues": [
    {
      "severity": "error",
      "file": "init.lua",
      "line": null,
      "message": "Missing required field: long_name",
      "code": null,
      "suggestion": null,
      "fixable": false
    }
  ]
}
```

## Integration

### With Mod Generator

Use the checker to validate generated mods:

```python
from tome_mod_checker import check_mod
from tome_asset_generator_ai import AIEnhancedToMEGenerator

# Generate mod
generator = AIEnhancedToMEGenerator("./mods/my_mod")
generator.generate(...)

# Check mod
result = check_mod("./mods/my_mod")
if result.summary['errors'] > 0:
    print("Mod has errors!")
```

### CI/CD Integration

```bash
# In CI pipeline
python tome_mod_checker.py ./mods/my_mod --json > results.json
if [ $(jq '.summary.errors' results.json) -gt 0 ]; then
    echo "Mod validation failed"
    exit 1
fi
```

## Troubleshooting

### Drag & Drop Not Working

**Solution:** Install tkinterdnd2:
```bash
pip install tkinterdnd2
```

### Ollama Not Available

**Symptoms:** AI fixes don't work

**Solutions:**
1. Start Ollama: `ollama serve`
2. Pull model: `ollama pull codellama:34b`
3. Check connection: `curl http://localhost:11434/api/tags`

### False Positives

Some warnings may be false positives:
- Complex Lua patterns
- Dynamic code generation
- Mod-specific patterns

Review warnings manually and ignore if appropriate.

## Best Practices

1. **Check Before Publishing** - Always validate mods before sharing
2. **Fix Errors First** - Address errors before warnings
3. **Review AI Suggestions** - AI suggestions need human review
4. **Test After Fixes** - Always test mods after applying fixes
5. **Use loadPrevious** - Always use `loadPrevious(...)` for compatibility

## See Also

- `TOME_ASSET_GENERATOR_README.md` - Mod generation guide
- `TOME_AI_GENERATOR_GUIDE.md` - AI-enhanced generation
- [ToME Modding Guide](https://te4.org/wiki/Modding)

