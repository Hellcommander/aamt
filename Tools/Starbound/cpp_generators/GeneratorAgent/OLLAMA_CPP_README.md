# Ollama C++ Integration

## Overview

Direct C++ integration for Ollama AI assistance in asset generation. This provides native C++ classes that can be used directly in generators without requiring PowerShell or Lua bridges.

## Files

- **`OllamaClient.hpp`** - Header file with client interface
- **`OllamaClient.cpp`** - Implementation (WinHTTP on Windows, libcurl on Linux/Mac)
- **`OllamaIntegrationExample.cpp`** - Example usage code

## Building

### Windows
- Uses WinHTTP (included with Windows SDK)
- No additional dependencies
- Link with: `winhttp.lib` (automatically via `#pragma comment`)

### Linux/Mac
- Requires libcurl: `sudo apt-get install libcurl4-openssl-dev` (Ubuntu/Debian)
- Link with: `-lcurl`

## Quick Start

```cpp
#include "OllamaClient.hpp"

// Create and configure client
GeneratorAgent::OllamaClient ollama;
GeneratorAgent::OllamaClient::Config config;
config.url = "http://localhost:11434";
config.model = "llama3.2";
config.enabled = true;
ollama.setConfig(config);

// Check if available
if (ollama.isAvailable()) {
    // Enhance description
    auto enhanced = ollama.enhanceDescription("A magical sword");
    if (enhanced && enhanced->wasEnhanced) {
        std::cout << "Enhanced: " << enhanced->enhanced << std::endl;
    }
    
    // Extract parameters
    auto params = ollama.extractParameters("A magical sword");
    if (params) {
        // Use params->colorPalette, params->style, etc.
    }
}
```

## Integration into ImageGenerator

To integrate into `ImageGenerator::generateImage()`:

1. Include the header:
```cpp
#include "OllamaClient.hpp"
```

2. Add Ollama enhancement before generation:
```cpp
ImageBundle ImageGenerator::generateImage(const ImageParams& params) {
    // ... existing cache check code ...
    
    // Enhance with Ollama if available
    ImageParams enhancedParams = params;
    if (!params.description.empty()) {
        GeneratorAgent::OllamaClient ollama;
        if (ollama.isAvailable()) {
            auto enhancement = ollama.enhance(params.description);
            if (enhancement && enhancement->description.wasEnhanced) {
                enhancedParams.description = enhancement->description.enhanced;
                // Apply extracted parameters as needed
            }
        }
    }
    
    // Continue with enhanced parameters
    ImageBundle bundle = processImageGeneration(enhancedParams);
    // ... rest of function ...
}
```

## API Reference

### OllamaClient::Config
- `url` - Ollama server URL (default: "http://localhost:11434")
- `model` - Model to use (default: "llama3.2")
- `timeoutSeconds` - Request timeout (default: 30)
- `enabled` - Enable/disable Ollama (default: true)

### Methods

#### `bool isAvailable() const`
Check if Ollama is available and reachable.

#### `std::optional<EnhancedDescription> enhanceDescription(const std::string& description) const`
Enhance a description with AI guidance.

Returns:
- `EnhancedDescription` with `original`, `enhanced`, and `wasEnhanced` fields

#### `std::optional<ExtractedParameters> extractParameters(const std::string& description) const`
Extract visual parameters from a description.

Returns:
- `ExtractedParameters` with:
  - `colorPalette` - Vector of RGB color arrays
  - `style` - Style string (e.g., "magical", "metallic")
  - `hasGradient`, `hasPattern`, `hasSparkles` - Boolean flags

#### `std::optional<EnhancementResult> enhance(const std::string& description) const`
Combined enhancement (description + parameters).

## Error Handling

All methods return `std::optional` and will return `std::nullopt` if:
- Ollama is not available
- Network error occurs
- Invalid response received
- Ollama is disabled in config

The client gracefully falls back - no exceptions are thrown for network errors.

## Performance

- Connection checks are cached (check once per session)
- Timeout is configurable (default 30 seconds)
- Non-blocking - returns immediately if Ollama unavailable

## See Also

- `OllamaIntegrationExample.cpp` - Full integration examples
- `CPP_OLLAMA_INTEGRATION.md` - Complete integration guide
- `OllamaLuaHelper.lua` - Lua bridge (alternative approach)
