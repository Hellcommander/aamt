# C++20 Migration Tools - Quick Reference

## ✅ Use These Files (In Tools Directory)

The **official** C++20 migration tool with AI assistance is:

- **`AutoUpdate-CPP20-API.ps1`** - Main PowerShell script with AI verification
- **`AutoUpdate-CPP20-API.bat`** - Batch wrapper for easy execution
- **`AutoUpdate-CPP20-API-README.md`** - Complete documentation

### Location
```
D:\games\Steam\steamapps\common\Transcendence\Tools\
```

### Features
- ✅ Auto-detects API version
- ✅ AI-assisted verification (Ollama + CodeLlama:34b)
- ✅ Works for any API version
- ✅ Comprehensive migration rules
- ✅ Safe with backups and dry-run mode

## ❌ Old Files (Removed)

The following files were **removed** (they were early test versions):
- `update_cpp_api20.ps1` (was in CCShell directory)
- `update_cpp_api20.bat` (was in CCShell directory)
- `update_cpp_api20_advanced.ps1` (was in CCShell directory)
- `API20_MIGRATION_README.md` (was in CCShell directory)

## Quick Start

```batch
# From Tools directory
AutoUpdate-CPP20-API.bat "D:\path\to\API\folder"
```

```powershell
# PowerShell
.\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder" -UseAI
```

## Related Tools

- **`Update-VSProjects-CPP20.ps1`** - Updates Visual Studio project files to C++20 standard
- **`Update-VSProjects-CPP20.bat`** - Batch wrapper for project file updates

These are separate tools that update `.vcxproj` files, not source code.

## Need Help?

See `AutoUpdate-CPP20-API-README.md` for complete documentation.

