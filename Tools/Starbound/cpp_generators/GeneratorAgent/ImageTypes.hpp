#pragma once

#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstddef>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ImageGen {

// Feed a by-value 64-bit hash (e.g. the result of a nested hashKey()) into an XXH64 state.
inline void xxhUpdateU64(XXH64_state_t* state, uint64_t value) {
    XXH64_update(state, &value, sizeof(value));
}

// GPU Handle Types for OpenStarbound Integration
using ImageHandle = uint32_t;
using TextureHandle = uint32_t;
using FramebufferHandle = uint32_t;
using ShaderHandle = uint32_t;

// Image Format Enums
enum class ImageFormat {
    PNG, JPG, BMP, TGA, HDR
};

enum class ImageCompression {
    NONE,
    LOSSY,
    LOSSLESS,
    BC1,
    BC3,
    BC7,
    ASTC_4x4,
    ASTC_8x8
};

enum class ImageQuality {
    ULTRA_LOW,
    LOW,
    MEDIUM,
    HIGH,
    ULTRA_HIGH
};

enum class SpritesheetLayout {
    GRID,
    HORIZONTAL,
    VERTICAL,
    CUSTOM
};

enum class PaddingStyle {
    NONE,
    SOLID,
    TRANSPARENT,
    PATTERN,
    GRADIENT
};

// Image Buffer Type
using ImageBuffer = std::vector<uint8_t>;

// CPU-side image: a GPU handle plus the 8-bit pixel data it was created from
// (row-major, top-left origin, `channels` interleaved bytes per pixel).
struct ImageData {
    ImageHandle handle = 0;
    int width = 0;
    int height = 0;
    int channels = 4;
    ImageBuffer data;

    bool empty() const { return data.empty() || width <= 0 || height <= 0; }
    size_t byteSize() const { return data.size(); }
    size_t stride() const { return static_cast<size_t>(width) * static_cast<size_t>(channels); }

    void allocate(int w, int h, int c = 4) {
        width = w;
        height = h;
        channels = c;
        data.assign(static_cast<size_t>(w > 0 ? w : 0) * static_cast<size_t>(h > 0 ? h : 0) * static_cast<size_t>(c), 0);
    }
};

// Parameter Structs with Enhanced Features
struct ImageParams {
    std::string id;
    int width;
    int height;
    ImageFormat format;
    ImageQuality quality;
    
    // Enhanced parameters
    bool enableAlpha = true;
    bool enableMipmaps = true;
    bool enableCompression = false;
    ImageCompression compressionType = ImageCompression::NONE;
    float compressionQuality = 0.8f;
    bool enableGPUAcceleration = false;
    bool enableAsyncProcessing = true;
    
    // Color space parameters
    bool sRGB = true;
    bool enableHDR = false;
    float exposure = 1.0f;
    float gamma = 2.2f;
    
    // Filtering parameters
    bool enableBilinear = true;
    bool enableTrilinear = false;
    bool enableAnisotropic = false;
    int maxAnisotropy = 16;
    
    uint64_t hashKey() const;
};

struct SpritesheetParams {
    std::string id;
    int columns;
    int rows;
    int tileWidth;
    int tileHeight;
    int padding;
    SpritesheetLayout layout;
    PaddingStyle paddingStyle;
    
    // Enhanced parameters
    glm::vec4 backgroundColor = glm::vec4(0.0f, 0.0f, 0.0f, 0.0f);
    glm::vec4 paddingColor = glm::vec4(0.0f, 0.0f, 0.0f, 0.0f);
    bool enableAutoResize = true;
    bool enableOptimization = true;
    bool enableMetadata = true;
    
    // Animation parameters
    float frameRate = 30.0f;
    bool enableLooping = true;
    std::string animationName = "default";
    
    // Export parameters
    ImageFormat exportFormat = ImageFormat::PNG;
    ImageCompression exportCompression = ImageCompression::LOSSLESS;
    float exportQuality = 1.0f;
    bool enableAtlasJSON = true;
    
    uint64_t hashKey() const;
};

struct CaptureParams {
    std::string id;
    int width;
    int height;
    bool enableDepth = false;
    bool enableStencil = false;
    bool enableMultisample = false;
    int sampleCount = 1;
    
    // Enhanced parameters
    bool enableHDR = false;
    bool enablePostProcessing = true;
    bool enableAntiAliasing = true;
    float exposure = 1.0f;
    float gamma = 2.2f;
    
    // Camera parameters
    glm::vec3 cameraPosition = glm::vec3(0.0f, 0.0f, 5.0f);
    glm::vec3 cameraTarget = glm::vec3(0.0f, 0.0f, 0.0f);
    glm::vec3 cameraUp = glm::vec3(0.0f, 1.0f, 0.0f);
    float fov = 45.0f;
    float nearPlane = 0.1f;
    float farPlane = 1000.0f;
    
    // Lighting parameters
    bool enableLighting = true;
    glm::vec3 lightPosition = glm::vec3(5.0f, 5.0f, 5.0f);
    glm::vec3 lightColor = glm::vec3(1.0f, 1.0f, 1.0f);
    float lightIntensity = 1.0f;
    bool enableShadows = false;

    // Output parameters
    int padding = 0;                 // transparent border (px) added around the captured frame
    bool gpuAccelerated = false;     // request the GPU capture path when available
    glm::vec4 clearColor = glm::vec4(0.0f, 0.0f, 0.0f, 0.0f);

    uint64_t hashKey() const;
};

struct UIParams {
    // Window parameters
    bool showWindow = true;
    bool enableDocking = true;
    bool enableResizing = true;
    glm::vec2 windowSize = glm::vec2(800.0f, 600.0f);
    glm::vec2 windowPosition = glm::vec2(100.0f, 100.0f);
    
    // Preview parameters
    bool showPreview = true;
    float previewScale = 1.0f;
    bool enableZoom = true;
    bool enablePan = true;
    bool enableRotation = true;
    
    // Control parameters
    bool showControls = true;
    bool enableRealTime = true;
    bool enableAutoSave = false;
    float autoSaveInterval = 5.0f;
    
    // Theme parameters
    std::string theme = "dark";
    glm::vec4 backgroundColor = glm::vec4(0.1f, 0.1f, 0.1f, 1.0f);
    glm::vec4 accentColor = glm::vec4(0.2f, 0.6f, 1.0f, 1.0f);
    
    uint64_t hashKey() const;
};

struct ImageMetadata {
    std::string id;
    std::string title;
    std::string description;
    std::string author;
    std::string version;
    std::chrono::system_clock::time_point creationTime;
    
    // Enhanced metadata
    std::string tags;
    std::string category;
    std::string license;
    std::string source;
    std::map<std::string, std::string> customFields;
    std::map<std::string, double> customData;   // numeric per-image data (e.g. animation_time)

    // Animation metadata
    float timestamp = 0.0f;   // time within the animation this image was captured at
    int frameIndex = -1;      // frame index within its animation, -1 when not part of one

    // Technical metadata
    int width;
    int height;
    ImageFormat format;
    ImageCompression compression;
    size_t fileSize;
    std::string checksum;
    
    uint64_t hashKey() const;
};

struct AtlasMetadata {
    std::string id;
    std::string name;
    std::string description;
    int frameCount;
    float frameRate;
    bool looping;
    
    // Frame information
    struct FrameInfo {
        std::string name;
        int x, y, width, height;
        float duration;
        std::map<std::string, std::string> properties;
    };
    std::vector<FrameInfo> frames;
    
    // Animation information
    struct AnimationInfo {
        std::string name;
        std::vector<int> frameIndices;
        float frameRate;
        bool looping;
    };
    std::vector<AnimationInfo> animations;
    
    uint64_t hashKey() const;
};

struct ImageBundle {
    ImageData image;                 // handle + CPU pixel data
    TextureHandle texture = 0;
    FramebufferHandle framebuffer = 0;

    // Additional assets for enhanced pipeline
    TextureHandle normalMap = 0;
    TextureHandle roughnessMap = 0;
    TextureHandle metallicMap = 0;
    TextureHandle emissiveMap = 0;

    // Metadata
    ImageMetadata metadata;
    AtlasMetadata atlasMetadata;

    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime = 0;
    uint64_t memoryUsage = 0;
    bool gpuAccelerated = false;

    uint64_t hashKey() const;
};

struct SpritesheetBundle {
    ImageHandle spritesheet = 0;
    TextureHandle spritesheetTexture = 0;
    std::vector<ImageHandle> individualFrames;
    std::vector<TextureHandle> individualTextures;

    // Combined sheet pixels and the grid it was laid out on
    ImageData combinedImage;
    int columns = 0;
    int rows = 0;
    int tileWidth = 0;
    int tileHeight = 0;
    int padding = 0;

    // Atlas data
    AtlasMetadata atlasMetadata;
    std::vector<glm::vec4> frameBounds; // x, y, width, height for each frame

    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime = 0;
    uint64_t memoryUsage = 0;
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const;
};

struct ImageGeneratorState {
    std::string id;
    ImageParams imageParams;
    SpritesheetParams spritesheetParams;
    CaptureParams captureParams;
    UIParams uiParams;
    
    // Runtime state
    ImageBundle currentImage;
    SpritesheetBundle currentSpritesheet;
    bool isGenerating = false;
    bool isCapturing = false;
    float generationProgress = 0.0f;
    
    // UI state
    bool showImageGenerator = true;
    bool showSpritesheetGenerator = true;
    bool showPreview = true;
    bool showControls = true;
    
    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate;
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;
    
    uint64_t hashKey() const;
};

struct ImagePerformanceMetrics {
    std::atomic<uint64_t> totalGenerations{0};
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> totalGenerationTime{0};
    std::atomic<uint64_t> peakMemoryUsage{0};
    std::atomic<uint64_t> activeGenerators{0};
    std::atomic<uint64_t> gpuGenerations{0};
    
    void reset() {
        totalGenerations = 0;
        cacheHits = 0;
        cacheMisses = 0;
        totalGenerationTime = 0;
        peakMemoryUsage = 0;
        activeGenerators = 0;
        gpuGenerations = 0;
    }
    
    double getCacheHitRate() const {
        uint64_t total = cacheHits.load() + cacheMisses.load();
        return total > 0 ? static_cast<double>(cacheHits.load()) / total : 0.0;
    }
    
    double getAverageGenerationTime() const {
        uint64_t generations = totalGenerations.load();
        return generations > 0 ? static_cast<double>(totalGenerationTime.load()) / generations : 0.0;
    }
};

struct ImageQualityMetrics {
    float peakBrightness = 0.0f;
    float averageBrightness = 0.0f;
    float contrast = 0.0f;
    float sharpness = 0.0f;
    float noise = 0.0f;
    float compressionArtifacts = 0.0f;
    
    bool isHighQuality() const {
        return peakBrightness > 0.1f && 
               averageBrightness > 0.01f && 
               contrast > 0.3f && 
               sharpness > 0.5f &&
               noise < 0.1f &&
               compressionArtifacts < 0.05f;
    }
};

// Hash function implementations
template<typename T>
uint64_t hashCombine(uint64_t seed, const T& value) {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, seed);
    XXH64_update(&hash_state, &value, sizeof(value));
    return XXH64_digest(&hash_state);
}

// Implementation of hashKey() methods
inline uint64_t ImageParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &width, sizeof(width));
    XXH64_update(&hash_state, &height, sizeof(height));
    XXH64_update(&hash_state, &format, sizeof(format));
    XXH64_update(&hash_state, &quality, sizeof(quality));
    XXH64_update(&hash_state, &enableAlpha, sizeof(enableAlpha));
    XXH64_update(&hash_state, &enableMipmaps, sizeof(enableMipmaps));
    XXH64_update(&hash_state, &enableCompression, sizeof(enableCompression));
    XXH64_update(&hash_state, &compressionType, sizeof(compressionType));
    XXH64_update(&hash_state, &compressionQuality, sizeof(compressionQuality));
    XXH64_update(&hash_state, &enableGPUAcceleration, sizeof(enableGPUAcceleration));
    XXH64_update(&hash_state, &sRGB, sizeof(sRGB));
    XXH64_update(&hash_state, &enableHDR, sizeof(enableHDR));
    XXH64_update(&hash_state, &exposure, sizeof(exposure));
    XXH64_update(&hash_state, &gamma, sizeof(gamma));
    return XXH64_digest(&hash_state);
}

inline uint64_t SpritesheetParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &columns, sizeof(columns));
    XXH64_update(&hash_state, &rows, sizeof(rows));
    XXH64_update(&hash_state, &tileWidth, sizeof(tileWidth));
    XXH64_update(&hash_state, &tileHeight, sizeof(tileHeight));
    XXH64_update(&hash_state, &padding, sizeof(padding));
    XXH64_update(&hash_state, &layout, sizeof(layout));
    XXH64_update(&hash_state, &paddingStyle, sizeof(paddingStyle));
    XXH64_update(&hash_state, &backgroundColor, sizeof(backgroundColor));
    XXH64_update(&hash_state, &paddingColor, sizeof(paddingColor));
    XXH64_update(&hash_state, &enableAutoResize, sizeof(enableAutoResize));
    XXH64_update(&hash_state, &enableOptimization, sizeof(enableOptimization));
    XXH64_update(&hash_state, &enableMetadata, sizeof(enableMetadata));
    XXH64_update(&hash_state, &frameRate, sizeof(frameRate));
    XXH64_update(&hash_state, &enableLooping, sizeof(enableLooping));
    XXH64_update(&hash_state, animationName.c_str(), animationName.length());
    XXH64_update(&hash_state, &exportFormat, sizeof(exportFormat));
    XXH64_update(&hash_state, &exportCompression, sizeof(exportCompression));
    XXH64_update(&hash_state, &exportQuality, sizeof(exportQuality));
    XXH64_update(&hash_state, &enableAtlasJSON, sizeof(enableAtlasJSON));
    return XXH64_digest(&hash_state);
}

inline uint64_t CaptureParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &width, sizeof(width));
    XXH64_update(&hash_state, &height, sizeof(height));
    XXH64_update(&hash_state, &enableDepth, sizeof(enableDepth));
    XXH64_update(&hash_state, &enableStencil, sizeof(enableStencil));
    XXH64_update(&hash_state, &enableMultisample, sizeof(enableMultisample));
    XXH64_update(&hash_state, &sampleCount, sizeof(sampleCount));
    XXH64_update(&hash_state, &enableHDR, sizeof(enableHDR));
    XXH64_update(&hash_state, &enablePostProcessing, sizeof(enablePostProcessing));
    XXH64_update(&hash_state, &enableAntiAliasing, sizeof(enableAntiAliasing));
    XXH64_update(&hash_state, &exposure, sizeof(exposure));
    XXH64_update(&hash_state, &gamma, sizeof(gamma));
    XXH64_update(&hash_state, &cameraPosition, sizeof(cameraPosition));
    XXH64_update(&hash_state, &cameraTarget, sizeof(cameraTarget));
    XXH64_update(&hash_state, &cameraUp, sizeof(cameraUp));
    XXH64_update(&hash_state, &fov, sizeof(fov));
    XXH64_update(&hash_state, &nearPlane, sizeof(nearPlane));
    XXH64_update(&hash_state, &farPlane, sizeof(farPlane));
    XXH64_update(&hash_state, &enableLighting, sizeof(enableLighting));
    XXH64_update(&hash_state, &lightPosition, sizeof(lightPosition));
    XXH64_update(&hash_state, &lightColor, sizeof(lightColor));
    XXH64_update(&hash_state, &lightIntensity, sizeof(lightIntensity));
    XXH64_update(&hash_state, &enableShadows, sizeof(enableShadows));
    XXH64_update(&hash_state, &padding, sizeof(padding));
    XXH64_update(&hash_state, &gpuAccelerated, sizeof(gpuAccelerated));
    XXH64_update(&hash_state, &clearColor, sizeof(clearColor));
    return XXH64_digest(&hash_state);
}

inline uint64_t UIParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, &showWindow, sizeof(showWindow));
    XXH64_update(&hash_state, &enableDocking, sizeof(enableDocking));
    XXH64_update(&hash_state, &enableResizing, sizeof(enableResizing));
    XXH64_update(&hash_state, &windowSize, sizeof(windowSize));
    XXH64_update(&hash_state, &windowPosition, sizeof(windowPosition));
    XXH64_update(&hash_state, &showPreview, sizeof(showPreview));
    XXH64_update(&hash_state, &previewScale, sizeof(previewScale));
    XXH64_update(&hash_state, &enableZoom, sizeof(enableZoom));
    XXH64_update(&hash_state, &enablePan, sizeof(enablePan));
    XXH64_update(&hash_state, &enableRotation, sizeof(enableRotation));
    XXH64_update(&hash_state, &showControls, sizeof(showControls));
    XXH64_update(&hash_state, &enableRealTime, sizeof(enableRealTime));
    XXH64_update(&hash_state, &enableAutoSave, sizeof(enableAutoSave));
    XXH64_update(&hash_state, &autoSaveInterval, sizeof(autoSaveInterval));
    XXH64_update(&hash_state, theme.c_str(), theme.length());
    XXH64_update(&hash_state, &backgroundColor, sizeof(backgroundColor));
    XXH64_update(&hash_state, &accentColor, sizeof(accentColor));
    return XXH64_digest(&hash_state);
}

inline uint64_t ImageMetadata::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, title.c_str(), title.length());
    XXH64_update(&hash_state, description.c_str(), description.length());
    XXH64_update(&hash_state, author.c_str(), author.length());
    XXH64_update(&hash_state, version.c_str(), version.length());
    XXH64_update(&hash_state, tags.c_str(), tags.length());
    XXH64_update(&hash_state, category.c_str(), category.length());
    XXH64_update(&hash_state, license.c_str(), license.length());
    XXH64_update(&hash_state, source.c_str(), source.length());
    XXH64_update(&hash_state, &width, sizeof(width));
    XXH64_update(&hash_state, &height, sizeof(height));
    XXH64_update(&hash_state, &format, sizeof(format));
    XXH64_update(&hash_state, &compression, sizeof(compression));
    XXH64_update(&hash_state, &fileSize, sizeof(fileSize));
    XXH64_update(&hash_state, checksum.c_str(), checksum.length());
    XXH64_update(&hash_state, &timestamp, sizeof(timestamp));
    XXH64_update(&hash_state, &frameIndex, sizeof(frameIndex));
    return XXH64_digest(&hash_state);
}

inline uint64_t AtlasMetadata::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, name.c_str(), name.length());
    XXH64_update(&hash_state, description.c_str(), description.length());
    XXH64_update(&hash_state, &frameCount, sizeof(frameCount));
    XXH64_update(&hash_state, &frameRate, sizeof(frameRate));
    XXH64_update(&hash_state, &looping, sizeof(looping));
    for (const auto& frame : frames) {
        XXH64_update(&hash_state, frame.name.c_str(), frame.name.length());
        XXH64_update(&hash_state, &frame.x, sizeof(frame.x));
        XXH64_update(&hash_state, &frame.y, sizeof(frame.y));
        XXH64_update(&hash_state, &frame.width, sizeof(frame.width));
        XXH64_update(&hash_state, &frame.height, sizeof(frame.height));
        XXH64_update(&hash_state, &frame.duration, sizeof(frame.duration));
    }
    for (const auto& anim : animations) {
        XXH64_update(&hash_state, anim.name.c_str(), anim.name.length());
        XXH64_update(&hash_state, anim.frameIndices.data(), anim.frameIndices.size() * sizeof(int));
        XXH64_update(&hash_state, &anim.frameRate, sizeof(anim.frameRate));
        XXH64_update(&hash_state, &anim.looping, sizeof(anim.looping));
    }
    return XXH64_digest(&hash_state);
}

inline uint64_t ImageBundle::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, &image.handle, sizeof(image.handle));
    XXH64_update(&hash_state, &image.width, sizeof(image.width));
    XXH64_update(&hash_state, &image.height, sizeof(image.height));
    XXH64_update(&hash_state, &image.channels, sizeof(image.channels));
    if (!image.data.empty()) {
        XXH64_update(&hash_state, image.data.data(), image.data.size());
    }
    XXH64_update(&hash_state, &texture, sizeof(texture));
    XXH64_update(&hash_state, &framebuffer, sizeof(framebuffer));
    XXH64_update(&hash_state, &normalMap, sizeof(normalMap));
    XXH64_update(&hash_state, &roughnessMap, sizeof(roughnessMap));
    XXH64_update(&hash_state, &metallicMap, sizeof(metallicMap));
    XXH64_update(&hash_state, &emissiveMap, sizeof(emissiveMap));
    xxhUpdateU64(&hash_state, metadata.hashKey());
    xxhUpdateU64(&hash_state, atlasMetadata.hashKey());
    XXH64_update(&hash_state, &generationTime, sizeof(generationTime));
    XXH64_update(&hash_state, &memoryUsage, sizeof(memoryUsage));
    XXH64_update(&hash_state, &gpuAccelerated, sizeof(gpuAccelerated));
    return XXH64_digest(&hash_state);
}

inline uint64_t SpritesheetBundle::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, &spritesheet, sizeof(spritesheet));
    XXH64_update(&hash_state, &spritesheetTexture, sizeof(spritesheetTexture));
    for (const auto& frame : individualFrames) {
        XXH64_update(&hash_state, &frame, sizeof(frame));
    }
    for (const auto& tex : individualTextures) {
        XXH64_update(&hash_state, &tex, sizeof(tex));
    }
    XXH64_update(&hash_state, &combinedImage.width, sizeof(combinedImage.width));
    XXH64_update(&hash_state, &combinedImage.height, sizeof(combinedImage.height));
    if (!combinedImage.data.empty()) {
        XXH64_update(&hash_state, combinedImage.data.data(), combinedImage.data.size());
    }
    XXH64_update(&hash_state, &columns, sizeof(columns));
    XXH64_update(&hash_state, &rows, sizeof(rows));
    XXH64_update(&hash_state, &tileWidth, sizeof(tileWidth));
    XXH64_update(&hash_state, &tileHeight, sizeof(tileHeight));
    XXH64_update(&hash_state, &padding, sizeof(padding));
    xxhUpdateU64(&hash_state, atlasMetadata.hashKey());
    for (const auto& bounds : frameBounds) {
        XXH64_update(&hash_state, &bounds, sizeof(bounds));
    }
    XXH64_update(&hash_state, &generationTime, sizeof(generationTime));
    XXH64_update(&hash_state, &memoryUsage, sizeof(memoryUsage));
    XXH64_update(&hash_state, &gpuAccelerated, sizeof(gpuAccelerated));
    return XXH64_digest(&hash_state);
}

inline uint64_t ImageGeneratorState::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    xxhUpdateU64(&hash_state, imageParams.hashKey());
    xxhUpdateU64(&hash_state, spritesheetParams.hashKey());
    xxhUpdateU64(&hash_state, captureParams.hashKey());
    xxhUpdateU64(&hash_state, uiParams.hashKey());
    xxhUpdateU64(&hash_state, currentImage.hashKey());
    xxhUpdateU64(&hash_state, currentSpritesheet.hashKey());
    XXH64_update(&hash_state, &isGenerating, sizeof(isGenerating));
    XXH64_update(&hash_state, &isCapturing, sizeof(isCapturing));
    XXH64_update(&hash_state, &generationProgress, sizeof(generationProgress));
    return XXH64_digest(&hash_state);
}

} // namespace ImageGen
} // namespace MagiTech 
