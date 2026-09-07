# Unified QA System

A comprehensive quality assurance system that integrates both data validation and visual regression testing for asset generation pipelines.

## Overview

The Unified QA System provides a single, cohesive framework for validating assets across multiple dimensions:

- **Data Validation**: Ensures asset files are properly formatted and contain valid data
- **Visual Regression Testing**: Compares generated assets against baseline images using multiple metrics
- **Parallel Processing**: Efficient batch testing with configurable threading
- **Comprehensive Reporting**: HTML reports and detailed statistics
- **Lua Integration**: Full scripting support for automated testing workflows

## Architecture

### Core Components

1. **UnifiedQASystem**: Main orchestrator that coordinates validation and visual testing
2. **IAssetValidator**: Interface for custom asset validators
3. **Built-in Validators**: JSON, Image, and Audio validators
4. **Visual QA Integration**: Leverages the VisualQASystem for image comparison
5. **Lua Bindings**: Complete scripting interface

### Data Flow

```
Asset Input → Type Detection → Validator Selection → Data Validation → Visual QA → Unified Result
```

## Features

### Data Validation

- **JSON Validation**: Syntax and structure validation
- **Image Validation**: Format and corruption detection
- **Audio Validation**: Format and header validation
- **Extensible**: Custom validators can be registered
- **Configurable**: Strict mode and field validation rules

### Visual Regression Testing

- **Multiple Metrics**: PSNR, SSIM, Histogram Correlation, Shape Difference, Color Distance, Edge Similarity
- **Configurable Thresholds**: Adjustable quality standards per metric
- **Baseline Management**: Automatic baseline generation and updates
- **Diff Generation**: Visual difference images for failed tests

### Performance

- **Parallel Processing**: Multi-threaded batch testing
- **Caching**: Efficient asset reuse and memory management
- **Statistics**: Comprehensive performance metrics
- **Timeout Protection**: Configurable execution limits

### Reporting

- **HTML Reports**: Detailed visual reports with pass/fail status
- **Summary Statistics**: Success rates, failure analysis, performance metrics
- **Error Categorization**: Failures by asset type and validator
- **Duration Tracking**: Execution time per asset and overall

## Usage

### C++ API

```cpp
#include "UnifiedQASystem.hpp"

// Create and configure the QA system
mt::qa::UnifiedQASystem qaSystem;
mt::qa::UnifiedTestConfig config;
config.enableDataValidation = true;
config.enableVisualQA = true;
config.baselineDirectory = "assets/baselines";
config.outputDirectory = "qa_output";
qaSystem.configure(config);

// Test individual assets
auto result = qaSystem.testAsset("assets/textures/player.png");
if (result.overallPassed) {
    std::cout << "Asset passed all tests" << std::endl;
} else {
    std::cout << "Asset failed: " << result.errorMessage << std::endl;
}

// Test batch of assets
std::vector<std::string> assetPaths = {"asset1.png", "asset2.json", "asset3.wav"};
auto batchResults = qaSystem.testBatch(assetPaths);

// Generate reports
qaSystem.generateReport(batchResults, "qa_report.html");
qaSystem.generateSummary(batchResults);
```

### Lua API

```lua
-- Configure the QA system
local config = UnifiedTestConfig()
config.enableDataValidation = true
config.enableVisualQA = true
config.baselineDirectory = "assets/baselines"
config.outputDirectory = "qa_output"
QA.configure(config)

-- Test individual asset
local result = QA.testAsset("assets/textures/player.png")
print("Passed: " .. tostring(result.overallPassed))

-- Test batch of assets
local assetPaths = {"asset1.png", "asset2.json", "asset3.wav"}
local results = QA.testBatch(assetPaths)

-- Generate reports
QA.generateReport(results, "qa_report.html")
QA.generateSummary(results)

-- Get statistics
local stats = QA.getStatistics()
print("Total Tests: " .. stats.totalTests)
print("Passed: " .. stats.passedTests)
print("Failed: " .. stats.failedTests)
```

## Configuration

### UnifiedTestConfig

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enableDataValidation` | bool | true | Enable data validation |
| `strictMode` | bool | false | Strict validation mode |
| `requiredFields` | vector<string> | {} | Required fields for validation |
| `fieldValidators` | map<string,string> | {} | Field validation rules |
| `enableVisualQA` | bool | true | Enable visual regression testing |
| `baselineDirectory` | string | "" | Directory for baseline images |
| `outputDirectory` | string | "" | Directory for output files |
| `generateDiffs` | bool | true | Generate difference images |
| `generateReports` | bool | true | Generate HTML reports |
| `parallelExecution` | bool | true | Enable parallel processing |
| `maxThreads` | int | 4 | Maximum number of threads |
| `timeout` | milliseconds | 30000 | Test timeout (30 seconds) |

### ImageScore Thresholds

| Metric | Default Threshold | Description |
|--------|------------------|-------------|
| PSNR | 30.0 | Peak Signal-to-Noise Ratio |
| SSIM | 0.95 | Structural Similarity Index |
| Histogram Correlation | 0.9 | Color histogram similarity |
| Shape Difference | 0.8 | Contour and shape similarity |
| Color Distance | 0.85 | HSV color space distance |
| Edge Similarity | 0.8 | Edge detection similarity |

## Built-in Validators

### JsonAssetValidator

Validates JSON files for syntax and structure.

**Supported Extensions**: `.json`

**Validation Checks**:
- File accessibility
- JSON syntax validation
- Exception handling

### ImageAssetValidator

Validates image files for format and corruption.

**Supported Extensions**: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tga`

**Validation Checks**:
- File accessibility
- OpenCV image loading
- Image format validation

### AudioAssetValidator

Validates audio files for format and headers.

**Supported Extensions**: `.wav`, `.mp3`, `.ogg`, `.flac`

**Validation Checks**:
- File accessibility
- WAV header validation
- MP3 header validation
- Format detection

## Custom Validators

Create custom validators by implementing the `IAssetValidator` interface:

```cpp
class CustomAssetValidator : public IAssetValidator {
public:
    ValidationResult validate(const std::string& assetPath) override {
        ValidationResult result;
        result.assetPath = assetPath;
        result.assetType = "Custom";
        result.isValid = true;
        
        // Custom validation logic here
        
        return result;
    }
    
    std::string getValidatorName() const override { 
        return "Custom"; 
    }
    
    std::vector<std::string> getSupportedExtensions() const override {
        return {".custom"};
    }
};

// Register the custom validator
qaSystem.registerValidator(std::make_shared<CustomAssetValidator>());
```

## Reporting

### HTML Reports

Generated HTML reports include:

- **Summary Statistics**: Total assets, pass/fail counts, success rate
- **Individual Results**: Detailed results for each asset
- **Error Details**: Specific validation errors and visual QA failures
- **Performance Metrics**: Execution time and duration statistics
- **Visual Indicators**: Color-coded pass/fail status

### Statistics

The system tracks comprehensive statistics:

- **Test Counts**: Total, passed, failed, skipped tests
- **Duration**: Total execution time
- **Failure Analysis**: Failures by asset type and validator
- **Performance**: Average duration per asset type

## Integration

### With Asset Generation Pipelines

The Unified QA System integrates seamlessly with asset generation pipelines:

```cpp
// After generating assets
auto generatedAssets = assetGenerator.generateBatch(parameters);

// Validate generated assets
auto qaResults = qaSystem.testBatch(generatedAssets);

// Check for failures
bool allPassed = true;
for (const auto& result : qaResults) {
    if (!result.overallPassed) {
        allPassed = false;
        std::cerr << "Asset failed QA: " << result.assetPath << std::endl;
    }
}

if (allPassed) {
    std::cout << "All generated assets passed QA" << std::endl;
} else {
    std::cerr << "Some assets failed QA - check report" << std::endl;
}
```

### With CI/CD Systems

```lua
-- In CI/CD pipeline
local results = QA.testDirectory("generated_assets")
local stats = QA.getStatistics()

-- Fail build if too many assets failed
if stats.failedTests > 0 then
    local failureRate = stats.failedTests / stats.totalTests
    if failureRate > 0.1 then  -- More than 10% failure rate
        error("Too many assets failed QA: " .. stats.failedTests .. "/" .. stats.totalTests)
    end
end

-- Generate report for artifacts
QA.generateReport(results, "qa_report.html")
```

## Performance Considerations

### Parallel Processing

- **Thread Pool**: Uses `mt::ThreadPoolManager` for efficient parallel execution
- **Configurable**: Adjust `maxThreads` based on system capabilities
- **Memory Efficient**: Processes assets in batches to manage memory usage

### Caching

- **Asset Caching**: Reuses validated assets to avoid redundant processing
- **Baseline Caching**: Caches baseline images for faster visual QA
- **Result Caching**: Caches validation results for repeated tests

### Optimization Tips

1. **Batch Processing**: Test multiple assets together for better efficiency
2. **Baseline Management**: Keep baselines up-to-date to avoid false positives
3. **Threshold Tuning**: Adjust quality thresholds based on project requirements
4. **Validator Selection**: Only enable necessary validators for each asset type

## Error Handling

### Validation Errors

- **File Access**: Handles missing or inaccessible files
- **Format Errors**: Detects corrupted or invalid file formats
- **Syntax Errors**: Validates JSON syntax and structure
- **Exception Safety**: Graceful handling of unexpected errors

### Visual QA Errors

- **Missing Baselines**: Automatic baseline generation for new assets
- **Comparison Failures**: Detailed metrics for failed visual comparisons
- **Image Loading**: Handles corrupted or unsupported image formats
- **Threshold Violations**: Configurable quality standards

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**: AI-powered quality assessment
2. **Advanced Metrics**: Additional image and audio quality metrics
3. **Real-time Monitoring**: Live QA dashboard and alerts
4. **Cloud Integration**: Distributed QA processing
5. **Custom Metrics**: User-defined quality assessment criteria

### Extension Points

- **Custom Validators**: Plugin system for specialized validation
- **Custom Metrics**: Extensible visual QA metrics
- **Custom Reports**: Template-based report generation
- **Custom Integrations**: Webhook and API integrations

## Troubleshooting

### Common Issues

1. **High Failure Rates**: Check baseline quality and threshold settings
2. **Performance Issues**: Adjust thread count and batch sizes
3. **Memory Usage**: Monitor cache size and clear periodically
4. **False Positives**: Review and update baseline images

### Debug Mode

Enable detailed logging for troubleshooting:

```cpp
// Enable debug output
qaSystem.setDebugMode(true);

// Test with verbose output
auto result = qaSystem.testAsset("asset.png", true);
```

## License

This QA system is part of the Magi-Tech Arcane Alchemy and Sorcery project and follows the same licensing terms. 