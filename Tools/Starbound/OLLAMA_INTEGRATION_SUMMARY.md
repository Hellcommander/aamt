# Ollama Integration Summary

## Overview

The Starbound asset generators have been enhanced to use the shared Ollama integration module from `../Shared/OllamaIntegration.psm1`. This provides better performance, automatic model selection, and improved resource management.

## Updated Files

1. **StarboundOllamaAssetGenerator.ps1**
   - Now imports and uses `OllamaIntegration.psm1` if available
   - Falls back to basic implementation if module not found
   - Uses shared module's `Invoke-OllamaRequest` with task type selection
   - Uses shared module's `Test-OllamaConnection` for better connection handling

2. **StarboundParticleGenerator.ps1**
   - Enhanced AI integration to use shared module
   - Maintains backward compatibility with fallback implementation

3. **STARBOUND_OLLAMA_GENERATOR_GUIDE.md**
   - Updated documentation to mention shared module integration

## Features from Shared Module

### Automatic Ollama Startup
- Automatically starts Ollama if not running
- Waits for Ollama to become available (up to 30 seconds)
- Provides helpful error messages if startup fails

### Model Auto-Selection
- Automatically selects best available model for each task type:
  - **visual**: For asset descriptions (wizardlm-uncensored, llama3.2, mistral)
  - **analysis**: For parameter extraction (codellama:7b-instruct, starcoder, llama3.2)
  - **code**: For code generation tasks
  - **simple**: For quick responses

### Performance Optimizations
- **Optimal thread usage**: Uses 94% of available CPU cores (leaves 6% headroom)
- **CPU throttling**: Prevents system overload during intensive operations
- **Rate limiting**: Prevents overwhelming Ollama with too many concurrent requests
- **Large context window**: Supports up to 256k tokens for complex tasks

### Better Error Handling
- Connection retry logic
- Graceful fallback if shared module unavailable
- Clear error messages with troubleshooting steps

## Usage

The generators work the same way as before, but now benefit from the shared module:

```powershell
# Basic usage (uses shared module automatically)
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "magicportal" `
    -Prompt "purple swirling magical energy"

# With specific model (still works)
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Texture `
    -AssetName "runicstone" `
    -OllamaModel "codellama:7b-instruct" `
    -Prompt "weathered ancient stone"
```

## Module Location

The shared module is expected at:
```
../Shared/OllamaIntegration.psm1
```

Relative to the Starbound tools directory:
```
d:\games\Steam\steamapps\common\Transcendence\Tools\Shared\OllamaIntegration.psm1
```

## Fallback Behavior

If the shared module is not found:
- Generator continues to work with basic implementation
- Warning message is displayed
- All features still function, just without advanced optimizations

## Benefits

1. **Better Performance**: Optimal thread usage and CPU throttling
2. **Automatic Model Selection**: No need to manually specify models
3. **Resource Management**: Prevents system overload
4. **Consistency**: Same Ollama integration across all Transcendence tools
5. **Maintainability**: Centralized Ollama integration code

## Testing

To verify the integration works:

```powershell
# Test with shared module
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "test" `
    -Prompt "test particle" `
    -OllamaModel "codellama:7b-instruct"
```

You should see:
- "Using shared Ollama integration module" message (if module found)
- Connection test using shared module's `Test-OllamaConnection`
- Model auto-selection information
- Optimal thread count display

## Future Enhancements

Potential improvements:
- Use shared module's RAG system for better context-aware generation
- Integrate with tool_helpers for parallel processing
- Add support for streaming responses
- Use shared module's file processing utilities for batch operations

---

*Last updated: Integration with Shared Ollama Module*
