# CustomRaceClassCreator Mod Checker - Guide

## Overview

Comprehensive AI-guided mod validation tool that checks code, assets, configuration, and dependencies for the CustomRaceClassCreator mod. Provides intelligent suggestions and can automatically fix common issues.

## Quick Start

### Basic Check

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"
```

### With AI Suggestions

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -UseAI
```

### Auto-Fix Issues

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -FixIssues
```

### Generate HTML Report

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -GenerateReport
```

## Features

### ✅ Code Validation

- **Compilation Check**: Attempts to build the mod and reports compilation errors
- **Code Structure**: Analyzes code for common issues:
  - Missing using statements
  - TODO/FIXME comments
  - Empty catch blocks
  - Missing XML documentation
- **Reference Validation**: Checks that all project references are available
- **AI-Powered Fixes**: Uses AI to analyze compilation errors and suggest specific fixes

### ✅ Asset Validation

- **Directory Structure**: Verifies expected asset directories exist
  - `Assets/Resources/`
  - `Assets/AssetBundles/`
- **File Checks**: Detects missing or empty asset directories
  - Empty texture directories
  - Missing icon files
- **Asset Bundle Validation**: Checks for empty or corrupted bundles
- **AI Suggestions**: Provides intelligent suggestions for missing assets

### ✅ Configuration Validation

- **Required Files**: Checks for essential mod files:
  - `manifest.json`
  - `README.md`
  - `CHANGELOG.md`
- **Manifest Validation**: Validates manifest.json structure and required fields:
  - `name`
  - `version_number`
  - `website_url`
  - `description`
- **Auto-Fix**: Can create missing directories automatically

### ✅ Dependency Validation

- **Dependency Check**: Verifies that all declared dependencies are present
- **Path Validation**: Checks if dependency mods exist in the expected locations

### ✅ CWL Integration Validation (CWL is REQUIRED but has Limitations)

- **Adapter Structure**: Validates CWL adapters extend BaseCwlAdapter (based on CWL wiki patterns)
- **Required Methods**: Checks for Initialize, ProcessSheetForSystem, IsSystemEnabled (patterns from CWL wiki)
- **Usage Patterns**: Analyzes CWL usage - CWL is mandatory where it can handle complexity
- **CWL Required**: Validates that SIMPLE data/config handling uses CWL (CWL is required for simple data)
- **Complex Code Exception**: Recognizes that complex functionality may intentionally use Harmony/custom code
- **Singleton Pattern**: Checks for proper adapter initialization (pattern from CWL wiki)
- **Missing CWL**: Only warns when SIMPLE files that should use CWL don't (complex code is exempt)
- **Wiki-Based Patterns**: Validation rules are converted from CWL wiki - actual implementations may vary
- **Accuracy Note**: CWL checks are based on CWL wiki patterns - actual implementations may vary, review suggestions manually
- **CWL Save/Load**: Validates CWL is used for save/load safety where it can handle it
- **Save Safety System**: Validates separate save safety system exists for complex functions CWL cannot handle
- **Hybrid Usage**: Recognizes that BOTH CWL and save safety system can be used at the same time
- **Different Parts**: Understands different parts of the same code can use different save/load approaches
- **Save Safety Integration**: Checks that complex systems use at least one save/load system (CWL, save safety, or both)

### ✅ Harmony Patch Validation (For Complex Core Functionality - REQUIRED)

- **Patch Attributes**: Validates [HarmonyPatch] attributes are properly used
- **Patch Methods**: Checks for matching Prefix/Postfix/Transpiler methods
- **Target Validation**: Verifies patch targets exist in Elin source
- **Namespace Checks**: Ensures HarmonyLib using statements are present
- **Target Method Validation**: Validates patched methods exist in game code
- **Complex Functionality**: Validates Harmony is used for complex functionality CWL cannot handle without losing complexity
- **Complexity Recognition**: Recognizes complex patches as intentional (not missing CWL)
- **CRITICAL**: Only remove Harmony patches if TRULY UNUSED (nothing references them, verified dead code)
- **Required Status**: Harmony patches that are used/referenced are required - they are essential for mod functionality
- **Unused Detection**: Checks if patches are referenced elsewhere - only unused patches can be safely removed

### ✅ AI-Powered Analysis

- **Intelligent Suggestions**: Uses Ollama AI to provide context-aware suggestions
- **Error Analysis**: Analyzes compilation errors and suggests specific fixes
- **Asset Recommendations**: Suggests solutions for missing assets
- **Model Selection**: Automatically selects appropriate AI model per check type
- **Source Context**: Builds context from decompiled Elin source for better suggestions
- **CWL-Required Understanding**: AI understands CWL is required but has limitations
- **Complex Mod Recognition**: AI understands this mod is complex and CWL cannot handle everything
- **CWL Save/Load**: AI understands CWL is used for save/load safety where it can handle it
- **Save Safety System**: AI understands there's a separate save safety system for complex functions CWL cannot handle
- **Hybrid Usage**: AI understands BOTH can be used simultaneously - different parts of same code can use different approaches
- **Harmony for Complexity**: AI understands Harmony is for complex functionality CWL cannot handle without "dumbing things down"
- **Intentional Complexity**: AI recognizes complex Harmony/custom code as intentional, not missing CWL

## Usage Examples

### Example 1: Quick Check

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator"
```

Runs all checks without AI assistance.

### Example 2: Full Check with AI

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -UseAI `
    -GenerateReport `
    -Verbose
```

Runs all checks with AI suggestions, generates HTML report, and shows detailed output.

### Example 3: Code-Only Check

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -CheckTypes "code" `
    -UseAI `
    -FixIssues
```

Only checks code, uses AI for suggestions, and automatically fixes issues where possible.

### Example 4: Asset Check with Auto-Fix

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -CheckTypes "assets" `
    -FixIssues
```

Checks assets and automatically creates missing directories.

### Example 5: Comprehensive Check

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -CheckTypes "all" `
    -UseAI `
    -FixIssues `
    -GenerateReport `
    -Verbose
```

Runs all checks with AI, auto-fixes issues, generates report, and shows detailed output.

### Example 6: CWL and Harmony Checks

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -CheckTypes "cwl,harmony" `
    -SourcePaths "G:\Elin_Decompiled_source\Elin,G:\Elin_Decompiled_source\Elin.Plugins-CWL-1.21.10" `
    -UseAI `
    -Verbose
```

Checks CWL integration and Harmony patches with source context validation.

## Parameters

### Required

- **`-ModPath`** - Path to CustomRaceClassCreator mod directory

### Optional

- **`-CheckTypes`** - Comma-separated list of checks to perform:
  - `code` - Code compilation and structure
  - `assets` - Asset files and directories
  - `config` - Configuration files
  - `dependencies` - Dependency validation
  - `cwl` - CWL integration and hybrid approach validation
  - `harmony` - Harmony patch validation
  - `all` - All checks (default)
  
- **`-UseAI`** - Enable AI-powered suggestions (requires Ollama)
- **`-OllamaModel`** - Specific Ollama model to use (default: auto-select)
- **`-FixIssues`** - Automatically fix issues where possible
- **`-GenerateReport`** - Generate detailed HTML report
- **`-Verbose`** - Show detailed output
- **`-SourcePaths`** - Comma-separated paths to decompiled source directories

## Check Types

### Code Checks

1. **Compilation**: Attempts to build the mod using `dotnet build`
2. **Structure**: Analyzes code for common issues and patterns
3. **References**: Validates that all project references exist

### Asset Checks

1. **Structure**: Verifies expected directories exist
2. **Files**: Checks for missing or empty asset files
3. **Bundles**: Validates asset bundle integrity

### Configuration Checks

1. **Files**: Checks for required configuration files
2. **Manifest**: Validates manifest.json structure

### CWL Integration Checks (CWL is REQUIRED but has Limitations)

1. **Adapters**: Validates CWL adapter structure and required methods
2. **Usage**: Analyzes CWL usage - CWL is mandatory where it can handle complexity
3. **CWL Required**: Validates that SIMPLE data/config handling uses CWL
4. **Complex Code Exception**: Recognizes complex implementations may intentionally use Harmony/custom code
5. **Missing CWL**: Only warns when SIMPLE files should use CWL but don't (complex code is exempt)
6. **CWL Save/Load**: Validates CWL is used for save/load safety where it can handle it
7. **Save Safety Systems**: Checks for ModSaveSafetyIntegration and save safety system usage
8. **Hybrid Usage**: Recognizes files using BOTH CWL and save safety system (this is correct)
9. **Save Safety Integration**: Validates complex systems use at least one save/load system (CWL, save safety, or both)
10. **Different Parts**: Understands different parts of same code can use different save/load approaches
11. **Accuracy Note**: CWL checks are based on CWL wiki patterns converted to validation rules - actual implementations may vary, suggestions should be reviewed manually

### Harmony Patch Checks (For Complex Core Functionality - REQUIRED)

1. **Patches**: Validates Harmony patch attributes and methods
2. **Targets**: Verifies patch targets exist in Elin source code
3. **Complex Functionality**: Validates Harmony is used for complex functionality CWL cannot handle without losing complexity
4. **Usage Analysis**: Analyzes Harmony usage patterns (complex runtime modifications, not simple data loading)
5. **Complexity Recognition**: Recognizes complex patches as intentional design choices
6. **CRITICAL**: Only remove Harmony patches if TRULY UNUSED (nothing references them, verified dead code)
7. **Required Status**: Harmony patches that are used/referenced are essential - they cannot be removed without breaking mod functionality
8. **Unused Detection**: Analyzes patch files to check if they're referenced elsewhere - only suggests removal if verified unused

### Dependency Checks

1. **Dependencies**: Verifies declared dependencies are present

## AI Integration

### Models Used

- **Code Analysis**: `codellama:34b` - For code structure and compilation errors
- **Asset Validation**: `wizardlm-uncensored:latest` - For asset suggestions
- **Configuration**: `codellama:34b` - For config validation
- **Dependencies**: `codellama:34b` - For dependency analysis

### AI Features

- **Error Analysis**: Analyzes compilation errors and suggests fixes
- **Context-Aware Suggestions**: Provides suggestions based on mod structure
- **Asset Recommendations**: Suggests solutions for missing assets
- **Best Practices**: Recommends improvements based on modding best practices
- **Source Context**: Uses decompiled Elin source to understand available APIs
- **CWL-Required Understanding**: AI knows CWL is required but has limitations for complex mods
- **Complex Mod Recognition**: AI understands this mod is complex and CWL cannot handle everything
- **Harmony for Complexity**: AI understands Harmony is for complex functionality CWL cannot handle without "dumbing things down"
- **Intentional Complexity**: AI recognizes complex Harmony/custom code as intentional design, not missing CWL
- **CRITICAL - Only Remove If Unused**: AI is instructed to only suggest removing Harmony patches if TRULY UNUSED (nothing references them)
- **Harmony Required When Used**: AI understands that removing used Harmony patches is a very bad idea and will break mod functionality
- **Usage Verification**: AI should verify patches are unused before suggesting removal
- **CWL Save/Load**: AI understands CWL is used for save/load safety where it can handle it
- **Save Safety System**: AI understands there's a separate save safety system (ModSaveSafetyIntegration) for complex functions CWL cannot handle
- **Hybrid Usage**: AI understands BOTH CWL and save safety system can be used at the same time
- **Different Parts**: AI understands different parts of the same code can use different save/load approaches
- **Not Either/Or**: AI recognizes using both systems together is correct, not an error

### Source Context Building

The checker scans decompiled source directories to build context:
- **Available Types**: Extracts all classes, interfaces, structs from Elin source
- **Available Methods**: Extracts method signatures for validation
- **CWL APIs**: Identifies CWL-specific APIs and classes
- **Target Validation**: Validates Harmony patch targets against source

This context is used to:
- Validate Harmony patch targets exist
- Suggest proper API usage
- Identify missing using statements
- Recommend CWL vs custom code usage

## Output

### Console Output

- **Color-Coded**: Different colors for errors (red), warnings (yellow), and success (green)
- **Progress Indicators**: Shows progress for long-running checks
- **Summary**: Displays summary of errors, warnings, and suggestions

### HTML Report

When using `-GenerateReport`, generates a detailed HTML report at:
```
[ModPath]/mod_check_report.html
```

The report includes:
- Summary statistics
- Detailed error list
- Warning list
- AI suggestions with formatting

## Auto-Fix Capabilities

When using `-FixIssues`, the checker can automatically:

- **Create Missing Directories**: Creates missing asset directories
- **Fix Common Issues**: Fixes simple configuration issues where possible

**Note**: The checker is conservative with auto-fixes. It will only fix issues that are safe and reversible.

## Requirements

- **PowerShell 5.1+** or PowerShell Core
- **.NET SDK** (for compilation checks)
- **Ollama** (optional, for AI suggestions)
  - Install from: https://ollama.ai
  - Required models will be auto-selected

### Installing Ollama

1. Download from https://ollama.ai
2. Install and start Ollama service
3. Pull required models (auto-selected, but can pre-install):
   ```bash
   ollama pull codellama:34b
   ollama pull wizardlm-uncensored:latest
   ```

## Integration with Other Tools

### Asset Generator

After running the checker, you can use the asset generator to fix missing assets:

```powershell
# Check for missing assets
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" -CheckTypes "assets"

# Generate missing assets
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" -AssetTypes "all"
```

### Build Process

Integrate into your build process:

```powershell
# Pre-build check
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" -CheckTypes "code,config"

# Build
dotnet build "E:\...\CustomRaceClassCreator\CustomRaceClassCreator.csproj"

# Post-build check
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" -CheckTypes "all" -GenerateReport
```

## Troubleshooting

### Compilation Check Fails

**Issue**: `dotnet build` not found or fails

**Solution**:
- Install .NET SDK
- Ensure project file is valid
- Check for missing dependencies

### AI Not Working

**Issue**: AI suggestions not appearing

**Solution**:
- Ensure Ollama is running: `ollama serve`
- Check connection: `curl http://localhost:11434/api/tags`
- Install required models
- Check firewall settings

### Missing References

**Issue**: References not found

**Solution**:
- Ensure all NuGet packages are restored
- Check HintPath values in .csproj
- Verify DLL files exist in expected locations

### Asset Issues

**Issue**: Missing asset directories

**Solution**:
- Use `-FixIssues` to auto-create directories
- Or manually create expected directories
- Use asset generator to create missing assets

## Best Practices

1. **Run Before Commits**: Check mod before committing changes
2. **Use AI for Complex Issues**: Enable AI for better suggestions on complex problems
3. **Generate Reports**: Use `-GenerateReport` for documentation
4. **Fix Issues Incrementally**: Fix errors first, then warnings
5. **Regular Checks**: Run checks regularly during development

## Advanced Usage

### Custom AI Models

```powershell
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -UseAI `
    -OllamaModel "llama2:70b"
```

### Selective Checks

```powershell
# Only check code and assets
.\CustomRaceClassCreatorModChecker.bat "E:\...\CustomRaceClassCreator" `
    -CheckTypes "code,assets"
```

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Check Mod
  run: |
    pwsh -File Tools/Elin/CustomRaceClassCreatorModChecker.ps1 `
      -ModPath ${{ github.workspace }}/Mod/CustomRaceClassCreator `
      -CheckTypes "all" `
      -GenerateReport
```

## See Also

- `CustomRaceClassCreatorAssetGenerator.ps1` - Asset generation tool
- `ElinSpellAssetGenerator.ps1` - Spell asset generator
- CustomRaceClassCreator mod documentation

---

**Version**: 1.0  
**Last Updated**: 2024-12-26  
**Focus**: Comprehensive mod validation with AI guidance

