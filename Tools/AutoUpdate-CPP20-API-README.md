# Auto C++20 Migration Tool for Transcendence API

Generic migration script that automatically detects API version and applies C++20 migration rules based on online resources and best practices.

## Features

- **Auto-detects API version** from folder names, project files, or source code
- **Searches online** for C++20 migration requirements (can be skipped with `-SkipOnlineCheck`)
- **Applies code transformations** based on detected patterns
- **Works for any API version** - not hardcoded to a specific version
- **Safe by default** - creates backups and supports dry-run mode

## Usage

### Quick Start (Batch Script)
```batch
# Process current directory
AutoUpdate-CPP20-API.bat

# Process specific API folder
AutoUpdate-CPP20-API.bat "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API59"

# Dry run (preview changes)
AutoUpdate-CPP20-API.bat "path\to\api" -dryrun

# Verbose output
AutoUpdate-CPP20-API.bat "path\to\api" -verbose
```

### PowerShell Script
```powershell
# Basic usage
.\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder"

# Dry run to preview changes
.\AutoUpdate-CPP20-API.ps1 -Path "." -DryRun -Verbose

# Skip online check (use only built-in rules)
.\AutoUpdate-CPP20-API.ps1 -Path "." -SkipOnlineCheck

# No backups
.\AutoUpdate-CPP20-API.ps1 -Path "." -Backup:$false
```

## Options

| Parameter | Description |
|-----------|-------------|
| `-Path` | Directory to process (default: current directory) |
| `-DryRun` | Preview changes without modifying files |
| `-Backup` | Create .backup files before modifying (default: true) |
| `-ShowDetails` | Show detailed output for each file (use `-Verbose` in batch file) |
| `-SkipOnlineCheck` | Skip online rule fetching, use only built-in rules |
| `-UseAI` | Enable AI-assisted verification using Ollama (default: true) |
| `-OllamaModel` | Ollama model to use (default: codellama:34b) |
| `-OllamaUrl` | Ollama API URL (default: http://localhost:11434) |

## What Gets Fixed

The script automatically applies these C++20 migration rules:

### Standard Library Updates
- `std::experimental::optional` → `std::optional`
- `std::experimental::filesystem` → `std::filesystem`
- `std::experimental::string_view` → `std::string_view`

### CodeChain API Updates
- `CC.Link(sInput, 0, NULL)` → `CCodeChain::LinkCode(sInput)`
- `Print(&CC)` → `Print()`
- `Discard(&CC)` → `Discard()`
- `TopLevel(pCode, &Ctx)` → `TopLevel(*pCode, RunOptions)`
- Adds `SRunOptions` setup when needed

### XML Util Updates
- `CreateXMLElementFromCommandLine(argc, argv, ...)` → `CreateXMLElementFromCommandLine(argc, const_cast<const char **>(argv), ...)`

### Smart Pointer Conversions
- `ICCItem *pCode = CCodeChain::LinkCode(...)` → `ICCItemPtr pCode = CCodeChain::LinkCode(...)`

## API Version Detection

The script automatically detects API version from:
1. Folder name (e.g., `TranscendenceDev-integration-API59`)
2. Parent folder name
3. Project files (`.vcxproj`)
4. Source code comments or defines

If detection fails, it uses generic C++20 rules.

## Examples

### Example 1: Preview Changes
```powershell
.\AutoUpdate-CPP20-API.ps1 -Path "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API59" -DryRun -Verbose
```

### Example 2: Apply Changes with Backup
```powershell
.\AutoUpdate-CPP20-API.ps1 -Path "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API59" -Backup
```

### Example 3: Process Multiple API Versions
```powershell
# Process API 59
.\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API59"

# Process API 20
.\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API20"
```

## Safety Features

1. **Backup Files**: Creates `.backup` files by default before modifying
2. **Dry Run Mode**: Test changes without modifying files
3. **Verbose Output**: See exactly what changes are being made
4. **Error Handling**: Continues processing even if individual files fail

## Migration Rules Source

The script uses:
- **Built-in rules**: Based on actual C++20 standard changes and Transcendence API patterns
- **Online resources**: Can fetch additional rules (can be disabled with `-SkipOnlineCheck`)

## Troubleshooting

### PowerShell Execution Policy Error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### API Version Not Detected
- The script will still work using generic C++20 rules
- You can manually specify patterns if needed

### No Changes Detected
- Use `-Verbose` to see what files are being processed
- Check that your files match the patterns being searched
- Some changes may require manual review

### Backup Files
Backup files are created with `.backup` extension. Delete after verifying:
```powershell
Get-ChildItem -Recurse -Filter "*.backup" | Remove-Item
```

## AI-Assisted Verification

The script uses **Ollama with CodeLlama:34b** to:
- **Verify transformations** are correct for C++20
- **Identify missing changes** that should be applied
- **Suggest improvements** for better C++20 compliance
- **Review modified files** for additional opportunities

### AI Features

1. **Real-time Verification**: After each transformation, AI verifies correctness
2. **Issue Detection**: Identifies potential problems in the changes
3. **Suggestions**: Provides actionable improvement suggestions
4. **Final Review**: Optional comprehensive review of all modified files

### Using AI

```powershell
# Enable AI (default)
.\AutoUpdate-CPP20-API.ps1 -Path "." -UseAI

# Disable AI
.\AutoUpdate-CPP20-API.ps1 -Path "." -UseAI:$false

# Use different model
.\AutoUpdate-CPP20-API.ps1 -Path "." -OllamaModel "codellama:13b"
```

### Ollama Setup

1. **Install Ollama**: https://ollama.ai
2. **Pull CodeLlama model**:
   ```bash
   ollama pull codellama:34b
   ```
3. **Start Ollama service** (usually runs automatically)

The script will automatically detect if Ollama is available and use it if enabled.

## How It Works

1. **Detects API version** from project structure
2. **Checks Ollama availability** (if AI enabled)
3. **Loads migration rules** (built-in + optional online)
4. **Scans C++ files** recursively
5. **Applies transformations** based on detected patterns
6. **AI verifies each change** for correctness (if enabled)
7. **Creates backups** (if enabled)
8. **Saves modified files** (unless dry-run)
9. **Final AI review** of all modified files (if enabled)

## AI Verification Example

When AI is enabled, you'll see output like:

```
[*] Modified: CCShell.cpp (3 change(s))
[*]   Verifying changes with AI...
[+]   AI verified: Changes are correct
[!]   AI detected issues:
    - Consider using const reference for RunOptions parameter
[+]   AI suggestions:
    + Use std::optional for nullable return values
    + Consider using std::string_view instead of CString where possible
```

## Troubleshooting AI

### Ollama Not Found
```powershell
# Check if Ollama is running
ollama list

# Start Ollama (usually automatic)
ollama serve
```

### Model Not Available
```bash
# Pull CodeLlama:34b
ollama pull codellama:34b

# Or use a different model
.\AutoUpdate-CPP20-API.ps1 -Path "." -OllamaModel "codellama:13b"
```

### AI Timeout
If AI analysis times out, the script will continue without AI verification. You can:
- Use a smaller model: `-OllamaModel "codellama:7b"`
- Disable AI: `-UseAI:$false`
- Process smaller files first

## See Also

- `Update-VSProjects-CPP20.ps1` - Updates Visual Studio project files to C++20
- C++20 Standard Documentation
- Transcendence API Documentation
- Ollama Documentation: https://ollama.ai

