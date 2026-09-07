# AI-Powered Code Change Implementation Tool

## Overview

The **AIImplementChanges** tool uses AI (Ollama/CodeLlama) to analyze C++ code and automatically implement suggested changes for C++20 migration and Transcendence CodeChain API updates.

This tool is designed to work alongside `AutoUpdate-CPP20-API.ps1`:
- **AutoUpdate-CPP20-API.ps1**: Applies predefined migration rules and uses AI to verify changes
- **AIImplementChanges.ps1**: Uses AI to discover and implement new changes that aren't covered by predefined rules

## Features

- **AI-Driven Analysis**: Uses Ollama/CodeLlama to analyze code and identify needed changes
- **Automatic Implementation**: Applies AI-suggested changes automatically
- **Interactive Mode**: Optionally ask for confirmation before applying each change
- **Focus Areas**: Target specific areas (C++20, CodeChain, SmartPointers, etc.)
- **Progress Tracking**: GUI version with real-time progress and statistics
- **Safe Operation**: Backup files before modification, dry-run mode available

## Requirements

- PowerShell 5.1 or later
- Ollama installed and running
- CodeLlama model (e.g., `codellama:34b`) available in Ollama

## Installation

1. Ensure Ollama is installed and running:
   ```bash
   ollama serve
   ```

2. Pull the CodeLlama model:
   ```bash
   ollama pull codellama:34b
   ```

3. The scripts are ready to use - no additional installation needed.

## Usage

### Command Line

**Basic usage:**
```powershell
.\AIImplementChanges.ps1 -Path "D:\path\to\API\folder"
```

**With options:**
```powershell
.\AIImplementChanges.ps1 -Path "D:\path\to\API\folder" `
    -DryRun `
    -Interactive `
    -Focus "CodeChain" `
    -OllamaModel "codellama:34b"
```

**Batch file:**
```batch
AIImplementChanges.bat "D:\path\to\API\folder" -dryrun -interactive
```

### GUI Version

**Launch GUI:**
```powershell
.\AIImplementChanges-GUI.ps1 -Path "D:\path\to\API\folder"
```

Or use the batch file:
```batch
AIImplementChanges-GUI.bat
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-Path` | Directory to process | `.` (current directory) |
| `-DryRun` | Preview changes without modifying files | `$false` |
| `-Backup` | Create backup files before modification | `$true` |
| `-ShowDetails` | Show detailed change information | `$false` |
| `-OllamaModel` | Ollama model to use | `codellama:34b` |
| `-OllamaUrl` | Ollama API URL | `http://localhost:11434` |
| `-MaxCodeLength` | Maximum characters per file for AI analysis | `8000` |
| `-MaxAITimePerFile` | Maximum seconds per file for AI analysis | `300` (5 minutes) |
| `-Interactive` | Ask for confirmation before each change | `$false` |
| `-Focus` | Focus area: `C++20`, `CodeChain`, `SmartPointers`, or `All` | `All` |

## How It Works

1. **File Discovery**: Scans the specified directory for C++ files (`.cpp`, `.h`, `.hpp`)

2. **AI Analysis**: For each file:
   - Sends code to Ollama/CodeLlama for analysis
   - AI identifies specific changes needed
   - Returns structured JSON with change suggestions

3. **Change Application**: 
   - Sorts changes by priority (highest first)
   - Applies each change sequentially
   - In interactive mode, asks for confirmation

4. **File Saving**:
   - Creates backup (if enabled)
   - Saves modified content
   - Reports statistics

## AI Response Format

The AI returns JSON with this structure:

```json
{
  "changes": [
    {
      "priority": 10,
      "description": "Replace CC.Link with CCodeChain::LinkCode",
      "find": "CC.Link(",
      "replace": "CCodeChain::LinkCode(",
      "category": "CodeChain",
      "reason": "CodeChain API updated in C++20"
    }
  ],
  "summary": "3 CodeChain API updates needed",
  "estimated_impact": "High"
}
```

## Examples

### Example 1: Dry Run (Preview Only)

```powershell
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59" -DryRun
```

This will analyze files and show what changes would be made without actually modifying files.

### Example 2: Interactive Mode

```powershell
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59" -Interactive
```

You'll be prompted for each change:
```
Change: Replace CC.Link with CCodeChain::LinkCode
Category: CodeChain
Priority: 10/10
Reason: CodeChain API updated in C++20
Find: CC.Link(
Replace: CCodeChain::LinkCode(
Apply this change? (Y/N/Skip remaining):
```

### Example 3: Focus on CodeChain API

```powershell
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59" -Focus "CodeChain"
```

This focuses AI analysis specifically on CodeChain API changes.

### Example 4: Using Different Model

```powershell
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59" -OllamaModel "llama3.2:latest"
```

## Comparison with AutoUpdate-CPP20-API

| Feature | AutoUpdate-CPP20-API | AIImplementChanges |
|---------|---------------------|-------------------|
| **Change Discovery** | Predefined rules | AI-driven discovery |
| **Change Application** | Automatic | Automatic (with optional interactive) |
| **AI Usage** | Verification only | Analysis + Implementation |
| **Best For** | Known migration patterns | Unknown/new patterns |
| **Speed** | Fast (pattern matching) | Slower (AI analysis per file) |

## Best Practices

1. **Always use `-DryRun` first** to preview changes
2. **Use `-Backup`** (enabled by default) to create safety backups
3. **Start with `-Focus`** to target specific areas
4. **Use `-Interactive`** for critical files to review each change
5. **Process in batches** for large codebases (use `-MaxCodeLength` to limit file size)

## Troubleshooting

### Ollama Not Available

```
ERROR: Ollama not available - cannot proceed
```

**Solution**: Ensure Ollama is running:
```bash
ollama serve
```

### Model Not Found

```
Model codellama:34b not found
```

**Solution**: Pull the model:
```bash
ollama pull codellama:34b
```

### AI Analysis Timeout

If files are timing out, try:
- Reducing `-MaxCodeLength` (e.g., `-MaxCodeLength 4000`)
- Increasing `-MaxAITimePerFile` (e.g., `-MaxAITimePerFile 600`)
- Using a faster model

### JSON Parsing Errors

If AI returns invalid JSON:
- Check Ollama logs
- Try a different model
- Reduce `-MaxCodeLength` to simplify analysis

## Integration with AutoUpdate-CPP20-API

Recommended workflow:

1. **First pass**: Run `AutoUpdate-CPP20-API.ps1` to apply known migration rules
2. **Second pass**: Run `AIImplementChanges.ps1` to find and apply additional changes
3. **Review**: Check modified files and test compilation

```powershell
# Step 1: Apply predefined rules
.\AutoUpdate-CPP20-API.ps1 -Path "D:\Transcendence\API59"

# Step 2: Find additional changes with AI
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59" -DryRun

# Step 3: Review and apply
.\AIImplementChanges.ps1 -Path "D:\Transcendence\API59"
```

## Output

The tool provides:
- **Console output**: Real-time progress and change logs
- **Backup files**: `.backup` files created before modification
- **Statistics**: Summary of files processed, modified, changes applied

## Limitations

- **AI Model Quality**: Results depend on the quality of the Ollama model
- **Processing Time**: AI analysis is slower than pattern matching
- **Token Limits**: Very large files may be truncated
- **Context Understanding**: AI may miss some context-dependent changes

## License

Part of the Transcendence Tools suite.

## Support

For issues or questions:
1. Check Ollama is running and model is available
2. Try with `-DryRun` first to preview changes
3. Use `-Interactive` mode to review changes before applying
4. Check backup files if something goes wrong

