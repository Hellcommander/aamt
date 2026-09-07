# AI Fix Application Toolset (Fast Mode)

A specialized toolset for quickly applying AI-suggested fixes using faster AI models.

## Overview

This toolset is designed for:
- **Fast processing** using smaller, faster AI models (default: `codellama:7b`)
- **Automatic application** of AI suggestions without manual intervention
- **Focused workflow** - just apply fixes, no full migration analysis
- **Re-applying fixes** that were previously suggested but not applied

## Features

- ✅ Uses faster AI models by default (`codellama:7b` instead of `codellama:34b`)
- ✅ Automatically applies all AI suggestions
- ✅ Shorter delays between AI calls (1 second vs 2 seconds)
- ✅ Smaller context windows for faster processing
- ✅ Focused on code fixes only

## Usage

### Basic Usage

```powershell
# Apply AI fixes to an API folder
.\Apply-AIFixes.ps1 "D:\path\to\API59"

# Or use the batch file (drag and drop)
Apply-AIFixes.bat "D:\path\to\API59"
```

### Advanced Options

```powershell
# Use a different model (still fast)
.\Apply-AIFixes.ps1 "D:\path\to\API59" -OllamaModel "codellama:13b"

# Dry run (see what would be changed)
.\Apply-AIFixes.ps1 "D:\path\to\API59" -DryRun

# Verbose output
.\Apply-AIFixes.ps1 "D:\path\to\API59" -ShowDetails

# Apply suggestions from a file
.\Apply-AIFixes.ps1 "D:\path\to\API59" -SuggestionsFile "apply_these.txt"
```

### Batch File Options

```batch
# Basic usage
Apply-AIFixes.bat "D:\path\to\API59"

# With flags
Apply-AIFixes.bat "D:\path\to\API59" -dryrun -verbose -model codellama:13b
```

## Performance Comparison

| Tool | Model | Delay | Context | Speed |
|------|-------|-------|---------|-------|
| AutoUpdate-CPP20-API | codellama:34b | 2s | 6000 tokens | Slower, thorough |
| Apply-AIFixes | codellama:7b | 1s | 4000 tokens | Faster, focused |

**Speed improvement**: ~3-5x faster than using the full migration tool with large models.

## When to Use

### Use Apply-AIFixes when:
- ✅ You want quick fixes applied automatically
- ✅ You've already run the full migration and want to apply remaining suggestions
- ✅ You want to use a faster model for quick iterations
- ✅ You're testing fixes and want fast feedback

### Use AutoUpdate-CPP20-API when:
- ✅ You need comprehensive migration analysis
- ✅ You want the most thorough AI review
- ✅ You need interactive mode for manual review
- ✅ You're doing a full migration from scratch

## Workflow Example

```powershell
# Step 1: Run full migration (thorough analysis)
.\AutoUpdate-CPP20-API.ps1 "D:\path\to\API59" -AIStrategy aggressive

# Step 2: Apply remaining fixes quickly (fast iteration)
.\Apply-AIFixes.ps1 "D:\path\to\API59" -OllamaModel codellama:7b

# Step 3: Verify changes
.\CompileApiFolder.ps1 "D:\path\to\API59"
```

## Model Recommendations

### For Speed (Default)
- `codellama:7b` - Fastest, good for quick fixes
- `codellama:13b` - Balanced speed and quality

### For Quality (Slower)
- `codellama:34b` - Best quality, slower
- `deepseek-coder` - Alternative high-quality model

## Output

The tool provides:
- Files processed count
- Files modified count
- Suggestions applied count
- Detailed status for each file and suggestion

## Suggestions File Format

You can provide a file with suggestions to apply instead of generating them with AI:

### Text Format (Simple)
```
- Convert raw pointers to smart pointers
- Use std::string_view instead of const char*
- Add const correctness
```

### File-Based Format
```
file: D:\path\to\file1.cpp
suggestion: Convert ICCItem* to ICCItemPtr
suggestion: Use std::string_view

file: D:\path\to\file2.cpp
suggestion: Add const qualifier
```

### JSON Format
```json
{
  "suggestions": [
    {
      "file": "path/to/file.cpp",
      "suggestion": "Convert raw pointer to smart pointer"
    }
  ]
}
```

The tool auto-detects the format, or you can specify with `-SuggestionsFormat`.

## Notes

- Files are automatically backed up before modification (`.backup` extension)
- The tool skips files larger than 20KB for performance
- All suggestions are automatically applied (no interactive prompts)
- Uses smaller context windows for faster AI responses
- Can read suggestions from a file to avoid regenerating them

## Troubleshooting

### "Ollama not available"
- Ensure Ollama is running: `ollama serve`
- Check if the model is available: `ollama list`

### "Model not found"
- Pull the model: `ollama pull codellama:7b`
- Or use an available model with `-OllamaModel` parameter

### "No suggestions"
- The file may already be well-formatted
- Try with `-ShowDetails` to see what's being analyzed
- Some files may be too large (skipped if >20KB)

## Integration

This tool works alongside:
- `AutoUpdate-CPP20-API.ps1` - Full migration tool
- `FixApiCompatibilityAI.py` - Compilation error fixer
- `CompileApiFolder.ps1` - Compilation tool

Use them together for a complete migration workflow.

