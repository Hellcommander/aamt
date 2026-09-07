# Manual Review Fix Application Tool (Best AI)

A specialized tool that uses the **best AI model** (codellama:34b) to apply complex fixes that require manual review.

## Overview

This tool is designed for:
- **Complex fixes** that need the smartest AI model
- **Manual review items** that were flagged for human attention
- **High-quality fixes** that require more intelligence than simple pattern matching
- **Large context** understanding for complex code relationships

## Features

- ✅ Uses best AI model by default (`codellama:34b` for maximum quality)
- ✅ Large context windows (16,000 tokens) for complex code understanding
- ✅ Handles multi-section fixes and complex relationships
- ✅ Reads from `manual_review.txt` file
- ✅ Longer delays (3 seconds) to allow quality model to process
- ✅ Extended timeouts (180 seconds) for complex fixes

## Usage

### Basic Usage

```powershell
# Apply manual review fixes (reads from manual_review.txt in current directory)
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59"

# Or use the batch file
Apply-ManualReviewFixes.bat "D:\path\to\API59"
```

### Advanced Options

```powershell
# Use a different model
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59" -OllamaModel "deepseek-coder"

# Specify a different review file
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59" -ManualReviewFile "my_review.txt"

# Dry run (see what would be changed)
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59" -DryRun

# Verbose output
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59" -ShowDetails
```

## Manual Review File Format

Create a `manual_review.txt` file with the issues that need fixing:

### Format 1: File-Specific Issues

```
file: D:\path\to\source\ComplexFile.cpp
issue: Template instantiation error with C++20 - need to update template syntax
context: The template uses old C++17 syntax that doesn't work in C++20
code:
template<typename T>
void Process(T* item) {
    // Problematic code here
}

---

file: D:\path\to\source\AnotherFile.cpp
issue: Complex smart pointer migration - multiple nested pointers
context: File has multiple levels of pointer indirection
```

### Format 2: Simple Format

```
file: path/to/file.cpp
issue: Description of the problem
```

### Format 3: General Issues

```
issue: Update all range-based for loops to use C++20 syntax
context: Some loops may need explicit type or const qualifiers
```

## File Format Details

- **file:** - Path to the file (absolute or relative to API folder)
- **issue:** - Description of the problem that needs fixing
- **context:** - Additional context about the issue
- **code:** - Problematic code block (optional, helps AI understand)
- **---** - Separator between items

## Performance Comparison

| Tool | Model | Context | Delay | Use Case |
|------|-------|---------|-------|----------|
| Apply-AIFixes | codellama:7b | 4000 tokens | 1s | Quick fixes |
| Apply-ManualReviewFixes | codellama:34b | 16000 tokens | 3s | Complex fixes |

## When to Use

### Use Apply-ManualReviewFixes when:
- ✅ You have complex issues that need the best AI
- ✅ Fixes require understanding large code contexts
- ✅ Multiple related changes need to be coordinated
- ✅ Template or advanced C++ features need updating
- ✅ You have a `manual_review.txt` file with flagged issues

### Use Apply-AIFixes when:
- ✅ You want quick fixes with a fast model
- ✅ Issues are straightforward
- ✅ You want to iterate quickly
- ✅ You have many simple suggestions

## Workflow Example

```powershell
# Step 1: Run full migration
.\AutoUpdate-CPP20-API.ps1 "D:\path\to\API59"

# Step 2: Compile and identify complex issues
.\CompileApiFolder.ps1 "D:\path\to\API59" > compile_errors.txt

# Step 3: Create manual_review.txt with complex issues
# (manually or using another tool)

# Step 4: Apply complex fixes with best AI
.\Apply-ManualReviewFixes.ps1 "D:\path\to\API59"

# Step 5: Apply remaining quick fixes
.\Apply-AIFixes.ps1 "D:\path\to\API59"
```

## Model Recommendations

### Best Quality (Default)
- `codellama:34b` - Best for complex fixes, large context
- `deepseek-coder` - Alternative high-quality model

### High Quality (Faster)
- `codellama:13b` - Good balance
- `qwen2.5-coder` - Alternative

## Output

The tool provides:
- Items processed count
- Files modified count
- Fixes applied count
- Detailed status for each fix
- Method used (replacement, append_review, etc.)

## Notes

- Files are automatically backed up before modification (`.backup` extension)
- Uses large context windows (16K tokens) for complex code understanding
- Longer timeouts (180s) to allow quality model to process
- Can handle multi-section fixes and complex code relationships
- Falls back to append mode if exact replacement isn't possible

## Troubleshooting

### "Manual review file not found"
- Create `manual_review.txt` in the current directory
- Or specify path with `-ManualReviewFile` parameter

### "Model not found"
- Pull the model: `ollama pull codellama:34b`
- Or use an available model with `-OllamaModel` parameter

### "Could not automatically apply fix"
- The AI fix may need manual integration
- Check the verbose output for the AI response
- The fix may be appended to the file with markers for review

## Integration

This tool works alongside:
- `AutoUpdate-CPP20-API.ps1` - Full migration tool
- `Apply-AIFixes.ps1` - Quick fix tool
- `FixApiCompatibilityAI.py` - Compilation error fixer

Use them together for a complete migration workflow:
1. Full migration → 2. Complex fixes (this tool) → 3. Quick fixes → 4. Compile

