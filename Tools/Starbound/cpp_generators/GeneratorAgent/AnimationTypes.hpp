#pragma once

#include "ImageTypes.hpp"
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <chrono>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ImageGen {

// Animation-specific enums
enum class AnimationMode {
    SINGLE_FRAME,
    ANIMATED_SEQUENCE
};

enum class FrameOrder {
    ROW_MAJOR,
    COLUMN_MAJOR
};

enum class TimelineTrackType {
    MORPH_WEIGHT,
    MODULE_VISIBILITY,
    LOD_CHANGE,
    WEAPON_FIRE,
    EFFECTS,
    CUSTOM
};

enum class AnimationExportFormat {
    STARBOUND_ANIMATION,
    GENERIC_JSON,
    CUSTOM_FORMAT
};

// Timeline keyframe structure
struct TimelineKeyframe {
    float time;
    std::string trackName;
    TimelineTrackType trackType;
    std::any value;
    std::string interpolation; // "linear", "ease", "step"
    
    uint64_t hashKey() const;
};

// Animation timeline structure
struct AnimationTimeline {
    std::string id;
    float duration;
    std::vector<TimelineKeyframe> keyframes;
    bool looping;
    float frameRate;
    
    // Track management
    std::unordered_map<std::string, std::vector<TimelineKeyframe>> tracks;
    std::vector<std::string> trackNames;
    
    uint64_t hashKey() const;
};

// Animation parameters
struct AnimationParams {
    std::string id;
    AnimationMode mode;
    int frameCount;
    float frameDuration;
    FrameOrder frameOrder;
    bool looping;
    float frameRate;
    
    // Timeline parameters
    AnimationTimeline timeline;
    bool useTimeline;
    float timelineDuration;
    
    // Export parameters
    AnimationExportFormat exportFormat;
    bool generateAnimationJSON;
    bool generateAtlasJSON;
    std::string animationName;
    
    // Starbound-specific parameters
    bool starboundCompatible;
    std::string starboundCategory;
    std::string starboundType;
    
    uint64_t hashKey() const;
};

// Starbound animation metadata
struct StarboundAnimationMetadata {
    std::string name;
    std::string category;
    std::string type;
    int frameCount;
    float frameTime;
    bool loop;
    
    // Sheet information
    int sheetCols;
    int sheetRows;
    std::string order;
    
    // Additional metadata
    std::string description;
    std::string author;
    std::string version;
    std::chrono::system_clock::time_point creationTime;
    
    uint64_t hashKey() const;
};

// Animation bundle structure
struct AnimationBundle {
    SpritesheetBundle spritesheet;
    StarboundAnimationMetadata starboundMetadata;
    std::string animationJsonPath;
    std::string spritesheetPath;
    
    // Timeline data
    AnimationTimeline timeline;
    std::vector<float> frameTimes;
    std::vector<int> frameIndices;
    
    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime;
    uint64_t memoryUsage;
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const;
};

// Animation generator state
struct AnimationGeneratorState {
    std::string id;
    AnimationParams animationParams;
    SpritesheetParams spritesheetParams;
    CaptureParams captureParams;
    UIParams uiParams;
    
    // Runtime state
    AnimationBundle currentAnimation;
    bool isGenerating = false;
    bool isPreviewing = false;
    float generationProgress = 0.0f;
    float previewTime = 0.0f;
    
    // UI state
    bool showAnimationGenerator = true;
    bool showTimelineEditor = true;
    bool showPreview = true;
    bool showControls = true;
    
    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate;
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;
    
    uint64_t hashKey() const;
};

// Animation performance metrics
struct AnimationPerformanceMetrics {
    std::atomic<uint64_t> totalGenerations{0};
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> totalGenerationTime{0};
    std::atomic<uint64_t> peakMemoryUsage{0};
    std::atomic<uint64_t> activeGenerators{0};
    std::atomic<uint64_t> gpuGenerations{0};
    std::atomic<uint64_t> animationExports{0};
    
    void reset() {
        totalGenerations = 0;
        cacheHits = 0;
        cacheMisses = 0;
        totalGenerationTime = 0;
        peakMemoryUsage = 0;
        activeGenerators = 0;
        gpuGenerations = 0;
        animationExports = 0;
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

// Animation quality metrics
struct AnimationQualityMetrics {
    float averageFrameTime = 0.0f;
    float frameTimeVariance = 0.0f;
    float smoothness = 0.0f;
    float consistency = 0.0f;
    int droppedFrames = 0;
    float compressionRatio = 0.0f;
    
    bool isHighQuality() const {
        return averageFrameTime > 0.0f && 
               frameTimeVariance < 0.01f && 
               smoothness > 0.8f && 
               consistency > 0.9f &&
               droppedFrames == 0;
    }
};

// Utility functions for animation
namespace AnimationUtils {
    // Timeline utilities
    float evaluateTimeline(const AnimationTimeline& timeline, float time, const std::string& trackName);
    std::vector<TimelineKeyframe> getKeyframesForTrack(const AnimationTimeline& timeline, const std::string& trackName);
    TimelineKeyframe interpolateKeyframes(const TimelineKeyframe& k1, const TimelineKeyframe& k2, float t);
    
    // Frame utilities
    std::vector<int> generateFrameIndices(int frameCount, FrameOrder order, int cols, int rows);
    std::vector<float> generateFrameTimes(int frameCount, float frameDuration);
    int calculateFrameIndex(float time, float frameDuration, int frameCount);
    
    // Starbound utilities
    std::string generateStarboundAnimationJSON(const StarboundAnimationMetadata& metadata);
    StarboundAnimationMetadata createStarboundMetadata(const AnimationParams& params);
    bool validateStarboundCompatibility(const AnimationParams& params);
    
    // Export utilities
    std::string getAnimationModeString(AnimationMode mode);
    AnimationMode getAnimationModeFromString(const std::string& str);
    
    std::string getFrameOrderString(FrameOrder order);
    FrameOrder getFrameOrderFromString(const std::string& str);
    
    std::string getTimelineTrackTypeString(TimelineTrackType type);
    TimelineTrackType getTimelineTrackTypeFromString(const std::string& str);
    
    std::string getAnimationExportFormatString(AnimationExportFormat format);
    AnimationExportFormat getAnimationExportFormatFromString(const std::string& str);
}

// Hash function implementations
template<typename T>
uint64_t hashCombine(uint64_t seed, const T& value) {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, seed);
    XXH64_update(&hash_state, &value, sizeof(value));
    return XXH64_digest(&hash_state);
}

// Implementation of hashKey() methods
inline uint64_t TimelineKeyframe::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, &time, sizeof(time));
    XXH64_update(&hash_state, trackName.c_str(), trackName.length());
    XXH64_update(&hash_state, &trackType, sizeof(trackType));
    XXH64_update(&hash_state, interpolation.c_str(), interpolation.length());
    return XXH64_digest(&hash_state);
}

inline uint64_t AnimationTimeline::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &duration, sizeof(duration));
    XXH64_update(&hash_state, &looping, sizeof(looping));
    XXH64_update(&hash_state, &frameRate, sizeof(frameRate));
    
    for (const auto& keyframe : keyframes) {
        XXH64_update(&hash_state, &keyframe.hashKey(), sizeof(uint64_t));
    }
    
    for (const auto& trackName : trackNames) {
        XXH64_update(&hash_state, trackName.c_str(), trackName.length());
    }
    
    return XXH64_digest(&hash_state);
}

inline uint64_t AnimationParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &mode, sizeof(mode));
    XXH64_update(&hash_state, &frameCount, sizeof(frameCount));
    XXH64_update(&hash_state, &frameDuration, sizeof(frameDuration));
    XXH64_update(&hash_state, &frameOrder, sizeof(frameOrder));
    XXH64_update(&hash_state, &looping, sizeof(looping));
    XXH64_update(&hash_state, &frameRate, sizeof(frameRate));
    XXH64_update(&hash_state, &useTimeline, sizeof(useTimeline));
    XXH64_update(&hash_state, &timelineDuration, sizeof(timelineDuration));
    XXH64_update(&hash_state, &exportFormat, sizeof(exportFormat));
    XXH64_update(&hash_state, &generateAnimationJSON, sizeof(generateAnimationJSON));
    XXH64_update(&hash_state, &generateAtlasJSON, sizeof(generateAtlasJSON));
    XXH64_update(&hash_state, animationName.c_str(), animationName.length());
    XXH64_update(&hash_state, &starboundCompatible, sizeof(starboundCompatible));
    XXH64_update(&hash_state, starboundCategory.c_str(), starboundCategory.length());
    XXH64_update(&hash_state, starboundType.c_str(), starboundType.length());
    XXH64_update(&hash_state, &timeline.hashKey(), sizeof(uint64_t));
    return XXH64_digest(&hash_state);
}

inline uint64_t StarboundAnimationMetadata::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, name.c_str(), name.length());
    XXH64_update(&hash_state, category.c_str(), category.length());
    XXH64_update(&hash_state, type.c_str(), type.length());
    XXH64_update(&hash_state, &frameCount, sizeof(frameCount));
    XXH64_update(&hash_state, &frameTime, sizeof(frameTime));
    XXH64_update(&hash_state, &loop, sizeof(loop));
    XXH64_update(&hash_state, &sheetCols, sizeof(sheetCols));
    XXH64_update(&hash_state, &sheetRows, sizeof(sheetRows));
    XXH64_update(&hash_state, order.c_str(), order.length());
    XXH64_update(&hash_state, description.c_str(), description.length());
    XXH64_update(&hash_state, author.c_str(), author.length());
    XXH64_update(&hash_state, version.c_str(), version.length());
    return XXH64_digest(&hash_state);
}

inline uint64_t AnimationBundle::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, &spritesheet.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &starboundMetadata.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, animationJsonPath.c_str(), animationJsonPath.length());
    XXH64_update(&hash_state, spritesheetPath.c_str(), spritesheetPath.length());
    XXH64_update(&hash_state, &timeline.hashKey(), sizeof(uint64_t));
    
    for (const auto& frameTime : frameTimes) {
        XXH64_update(&hash_state, &frameTime, sizeof(frameTime));
    }
    
    for (const auto& frameIndex : frameIndices) {
        XXH64_update(&hash_state, &frameIndex, sizeof(frameIndex));
    }
    
    XXH64_update(&hash_state, &generationTime, sizeof(generationTime));
    XXH64_update(&hash_state, &memoryUsage, sizeof(memoryUsage));
    XXH64_update(&hash_state, &gpuAccelerated, sizeof(gpuAccelerated));
    return XXH64_digest(&hash_state);
}

inline uint64_t AnimationGeneratorState::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, &animationParams.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &spritesheetParams.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &captureParams.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &uiParams.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &currentAnimation.hashKey(), sizeof(uint64_t));
    XXH64_update(&hash_state, &isGenerating, sizeof(isGenerating));
    XXH64_update(&hash_state, &isPreviewing, sizeof(isPreviewing));
    XXH64_update(&hash_state, &generationProgress, sizeof(generationProgress));
    XXH64_update(&hash_state, &previewTime, sizeof(previewTime));
    return XXH64_digest(&hash_state);
}

} // namespace ImageGen
} // namespace MagiTech 
