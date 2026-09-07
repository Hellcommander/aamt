#pragma once

#include "ImageGenerator.hpp"
#include <sol/sol.hpp>

namespace MagiTech {
namespace ImageGen {

// Lua binding functions for ImageGenerator
void bindImageGeneratorToLua(sol::state& lua);

// Individual binding functions
void bindImageTypesToLua(sol::state& lua);
void bindImageParamsToLua(sol::state& lua);
void bindSpritesheetParamsToLua(sol::state& lua);
void bindCaptureParamsToLua(sol::state& lua);
void bindUIParamsToLua(sol::state& lua);
void bindImageBundleToLua(sol::state& lua);
void bindSpritesheetBundleToLua(sol::state& lua);
void bindImageGeneratorStateToLua(sol::state& lua);
void bindImageGeneratorToLua(sol::state& lua);
void bindImageAssemblerToLua(sol::state& lua);
void bindImageWriterToLua(sol::state& lua);
void bindSpritesheetAssemblerToLua(sol::state& lua);
void bindUtilsToLua(sol::state& lua);

// Utility functions for Lua integration
namespace LuaUtils {
    // Conversion functions
    sol::table imageParamsToTable(sol::state& lua, const ImageParams& params);
    ImageParams tableToImageParams(const sol::table& table);
    
    sol::table spritesheetParamsToTable(sol::state& lua, const SpritesheetParams& params);
    SpritesheetParams tableToSpritesheetParams(const sol::table& table);
    
    sol::table captureParamsToTable(sol::state& lua, const CaptureParams& params);
    CaptureParams tableToCaptureParams(const sol::table& table);
    
    sol::table uiParamsToTable(sol::state& lua, const UIParams& params);
    UIParams tableToUIParams(const sol::table& table);
    
    sol::table imageBundleToTable(sol::state& lua, const ImageBundle& bundle);
    ImageBundle tableToImageBundle(const sol::table& table);
    
    sol::table spritesheetBundleToTable(sol::state& lua, const SpritesheetBundle& bundle);
    SpritesheetBundle tableToSpritesheetBundle(const sol::table& table);
    
    sol::table imageGeneratorStateToTable(sol::state& lua, const ImageGeneratorState& state);
    ImageGeneratorState tableToImageGeneratorState(const sol::table& table);
    
    // Validation functions
    bool validateImageParamsLua(const sol::table& params, std::string& errorMessage);
    bool validateSpritesheetParamsLua(const sol::table& params, std::string& errorMessage);
    bool validateCaptureParamsLua(const sol::table& params, std::string& errorMessage);
    
    // Helper functions
    std::string getFormatString(ImageFormat format);
    ImageFormat getFormatFromString(const std::string& str);
    
    std::string getQualityString(ImageQuality quality);
    ImageQuality getQualityFromString(const std::string& str);
    
    std::string getLayoutString(SpritesheetLayout layout);
    SpritesheetLayout getLayoutFromString(const std::string& str);
    
    std::string getPaddingStyleString(PaddingStyle style);
    PaddingStyle getPaddingStyleFromString(const std::string& str);
    
    std::string getCompressionString(ImageCompression compression);
    ImageCompression getCompressionFromString(const std::string& str);
}

// Lua wrapper classes for better integration
class ImageGeneratorLuaWrapper {
public:
    ImageGeneratorLuaWrapper();
    ~ImageGeneratorLuaWrapper();
    
    // Main functions exposed to Lua
    bool initialize();
    void shutdown();
    
    // Image generation
    sol::table generateImage(const sol::table& params);
    sol::table generateSpritesheet(const sol::table& params);
    sol::table captureFrame(const sol::table& params);
    
    // UI functions
    void showImageGeneratorWindow();
    void showSpritesheetGeneratorWindow();
    void showPreviewWindow();
    void showControlsWindow();
    
    // State management
    sol::table getState();
    void setState(const sol::table& state);
    
    // Parameter management
    void setImageParams(const sol::table& params);
    void setSpritesheetParams(const sol::table& params);
    void setCaptureParams(const sol::table& params);
    void setUIParams(const sol::table& params);
    
    // Generation control
    void startGeneration();
    void stopGeneration();
    bool isGenerating();
    float getGenerationProgress();
    
    // Capture control
    void startCapture();
    void stopCapture();
    bool isCapturing();
    
    // File operations
    bool saveImage(const sol::table& bundle, const std::string& filePath);
    bool saveSpritesheet(const sol::table& bundle, const std::string& filePath);
    sol::table loadImage(const std::string& filePath);
    sol::table loadSpritesheet(const std::string& filePath);
    
    // Export functions
    bool exportSpritesheet(const sol::table& params, const std::string& outputPath);
    bool exportAtlasJSON(const sol::table& bundle, const std::string& outputPath);
    bool exportIndividualFrames(const sol::table& bundle, const std::string& outputDir);
    
    // Utility functions
    std::string getFormatExtension(const std::string& format);
    std::string getCompressionName(const std::string& compression);
    std::string getQualityName(const std::string& quality);
    std::string getLayoutName(const std::string& layout);
    std::string getPaddingStyleName(const std::string& style);
    
    // Performance and metrics
    sol::table getPerformanceMetrics();
    void resetPerformanceMetrics();
    
    // Quality assessment
    sol::table assessImageQuality(const sol::table& bundle);
    bool validateImageParams(const sol::table& params);
    bool validateSpritesheetParams(const sol::table& params);
    bool validateCaptureParams(const sol::table& params);
    
    // Error handling
    std::string getLastError();
    void clearLastError();
    bool hasError();
    
    // Configuration
    void setProcessingQuality(int quality);
    void setCompressionQuality(float quality);
    void setGPUAcceleration(bool enable);
    void setAsyncProcessing(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Caching
    void enableCaching(bool enable);
    void clearCache();
    size_t getCacheSize();
    
    // Hot reload
    void enableHotReload(bool enable);
    void reloadConfiguration();
    
private:
    std::unique_ptr<ImageGenerator> m_generator;
    sol::state* m_lua;
    
    // Helper functions
    void initializeLua(sol::state& lua);
    sol::table createErrorTable(const std::string& error);
    sol::table createSuccessTable();
};

// Lua wrapper for ImageAssembler
class ImageAssemblerLuaWrapper {
public:
    ImageAssemblerLuaWrapper();
    ~ImageAssemblerLuaWrapper();
    
    // Main assembly function
    sol::table assembleSpritesheet(const sol::table& tiles, const sol::table& params);
    
    // Individual tile processing
    sol::table processTile(const sol::table& source, int targetWidth, int targetHeight);
    sol::table resizeTile(const sol::table& source, int newWidth, int newHeight);
    sol::table addPadding(const sol::table& source, int padding, const sol::table& paddingColor);
    
    // Layout functions
    sol::table calculateTilePositions(const sol::table& params);
    sol::table calculateSpritesheetSize(const sol::table& params);
    
    // Optimization functions
    sol::table optimizeSpritesheet(const sol::table& spritesheet, const sol::table& params);
    bool validateSpritesheetLayout(const sol::table& params);
    
private:
    std::unique_ptr<ImageAssembler> m_assembler;
    sol::state* m_lua;
};

// Lua wrapper for ImageWriter
class ImageWriterLuaWrapper {
public:
    ImageWriterLuaWrapper();
    ~ImageWriterLuaWrapper();
    
    // Main writing functions
    bool saveImage(const sol::table& bundle, const std::string& filePath, const std::string& format);
    bool saveSpritesheet(const sol::table& bundle, const std::string& filePath, const std::string& format);
    
    // Format-specific writers
    bool writePNG(const sol::table& bundle, const std::string& filePath);
    bool writeJPG(const sol::table& bundle, const std::string& filePath, float quality);
    bool writeBMP(const sol::table& bundle, const std::string& filePath);
    bool writeTGA(const sol::table& bundle, const std::string& filePath);
    bool writeHDR(const sol::table& bundle, const std::string& filePath);
    
    // Metadata writing
    bool writeMetadata(const sol::table& metadata, const std::string& filePath);
    bool writeAtlasMetadata(const sol::table& metadata, const std::string& filePath);
    
    // Async writing
    sol::function saveImageAsync(const sol::table& bundle, const std::string& filePath, const std::string& format);
    sol::function saveSpritesheetAsync(const sol::table& bundle, const std::string& filePath, const std::string& format);
    
private:
    std::unique_ptr<ImageWriter> m_writer;
    sol::state* m_lua;
};

// Lua wrapper for SpritesheetAssembler
class SpritesheetAssemblerLuaWrapper {
public:
    SpritesheetAssemblerLuaWrapper();
    ~SpritesheetAssemblerLuaWrapper();
    
    // Main assembly function
    sol::table assembleSpritesheet(const sol::table& frames, const sol::table& params);
    
    // Advanced assembly options
    sol::table assembleWithOptimization(const sol::table& frames, const sol::table& params);
    sol::table assembleWithCustomLayout(const sol::table& frames, const sol::table& params);
    
    // Atlas generation
    sol::table generateAtlasMetadata(const sol::table& frames, const sol::table& params);
    sol::table calculateOptimalFrameBounds(const sol::table& frames, const sol::table& params);
    
    // Animation support
    sol::table generateAnimations(const sol::table& frames, const sol::table& params);
    bool validateAnimationSequence(const sol::table& frames);
    
private:
    std::unique_ptr<SpritesheetAssembler> m_assembler;
    sol::state* m_lua;
};

// Global Lua functions
namespace LuaGlobals {
    // Create instances
    std::shared_ptr<ImageGeneratorLuaWrapper> createImageGenerator();
    std::shared_ptr<ImageAssemblerLuaWrapper> createImageAssembler();
    std::shared_ptr<ImageWriterLuaWrapper> createImageWriter();
    std::shared_ptr<SpritesheetAssemblerLuaWrapper> createSpritesheetAssembler();
    
    // Utility functions
    sol::table createImageParams(sol::state& lua);
    sol::table createSpritesheetParams(sol::state& lua);
    sol::table createCaptureParams(sol::state& lua);
    sol::table createUIParams(sol::state& lua);
    
    // Validation functions
    bool validateImageParams(const sol::table& params);
    bool validateSpritesheetParams(const sol::table& params);
    bool validateCaptureParams(const sol::table& params);
    
    // Conversion functions
    std::string formatToString(const std::string& format);
    std::string qualityToString(const std::string& quality);
    std::string layoutToString(const std::string& layout);
    std::string paddingStyleToString(const std::string& style);
    std::string compressionToString(const std::string& compression);
    
    // File utilities
    bool fileExists(const std::string& filePath);
    bool createDirectory(const std::string& dirPath);
    std::string getFileExtension(const std::string& filePath);
    std::string getFileName(const std::string& filePath);
    std::string getDirectory(const std::string& filePath);
    
    // Image utilities
    bool isValidImageSize(int width, int height);
    bool isValidSpritesheetSize(int cols, int rows, int tileW, int tileH);
    sol::table calculateAspectRatio(int width, int height);
    float calculateAspectRatioFloat(int width, int height);
    
    // Color utilities
    sol::table hexToColor(const std::string& hex);
    std::string colorToHex(const sol::table& color);
    sol::table blendColors(const sol::table& color1, const sol::table& color2, float factor);
    
    // String utilities
    std::string toLower(const std::string& str);
    std::string toUpper(const std::string& str);
    std::string trim(const std::string& str);
    sol::table split(const std::string& str, char delimiter);
    std::string join(const sol::table& strings, const std::string& delimiter);
    
    // Time utilities
    std::string getCurrentTimestamp();
    std::string formatDuration(int milliseconds);
    std::string formatFileSize(size_t bytes);
    
    // Validation utilities
    bool isValidFilename(const std::string& filename);
    bool isValidPath(const std::string& path);
    bool isSupportedFormat(const std::string& extension);
}

} // namespace ImageGen
} // namespace MagiTech 
