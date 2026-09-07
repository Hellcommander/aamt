#pragma once

#include "ImageTypes.hpp"
#include "AnimationTypes.hpp"
#include <memory>
#include <unordered_map>
#include <vector>
#include <string>
#include <functional>
#include <thread>
#include <future>
#include <mutex>
#include <condition_variable>

// Forward declarations
struct ImGuiContext;
struct ImDrawData;

namespace MagiTech {
namespace ImageGen {

// Forward declarations for external dependencies
class RenderContext;
class MechPipeline;
class ImageAssembler;
class ImageWriter;
class SpritesheetAssembler;
class AnimationAssembler;

// NEW: Dynamic Pipeline System
class IPipeline {
public:
    virtual ~IPipeline() = default;
    
    // Core pipeline interface
    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
    virtual bool isInitialized() const = 0;
    
    // Animation interface
    virtual void SetAnimTime(float time) = 0;
    virtual void SetMorphWeight(float weight) = 0;
    virtual void SetModuleVisibility(float visibility) = 0;
    virtual void SetLODLevel(int level) = 0;
    virtual void SetWeaponFiring(bool firing) = 0;
    virtual void SetEffectsActive(bool active) = 0;
    
    // Custom parameter interface
    virtual void SetParameter(const std::string& name, const std::any& value) = 0;
    virtual std::any GetParameter(const std::string& name) const = 0;
    virtual bool HasParameter(const std::string& name) const = 0;
    
    // Pipeline metadata
    virtual std::string GetName() const = 0;
    virtual std::string GetVersion() const = 0;
    virtual std::vector<std::string> GetSupportedParameters() const = 0;
    virtual std::vector<std::string> GetSupportedAnimations() const = 0;
};

// Pipeline factory for dynamic loading
class PipelineFactory {
public:
    using PipelineCreator = std::function<std::unique_ptr<IPipeline>()>;
    
    static PipelineFactory& getInstance();
    
    // Register pipeline types
    void registerPipeline(const std::string& name, PipelineCreator creator);
    void unregisterPipeline(const std::string& name);
    
    // Create pipeline instances
    std::unique_ptr<IPipeline> createPipeline(const std::string& name);
    std::vector<std::string> getAvailablePipelines() const;
    
    // Load pipeline from configuration
    std::unique_ptr<IPipeline> loadPipelineFromConfig(const std::string& configPath);
    
private:
    std::unordered_map<std::string, PipelineCreator> m_creators;
    std::mutex m_mutex;
};

// Pipeline manager for runtime pipeline switching
class PipelineManager {
public:
    PipelineManager();
    ~PipelineManager();
    
    // Pipeline management
    bool loadPipeline(const std::string& name);
    bool switchPipeline(const std::string& name);
    void unloadCurrentPipeline();
    
    // Current pipeline access
    IPipeline* getCurrentPipeline() { return m_currentPipeline.get(); }
    const IPipeline* getCurrentPipeline() const { return m_currentPipeline.get(); }
    std::string getCurrentPipelineName() const { return m_currentPipelineName; }
    
    // Pipeline information
    std::vector<std::string> getAvailablePipelines() const;
    bool isPipelineLoaded() const { return m_currentPipeline != nullptr; }
    
    // Configuration
    bool savePipelineConfig(const std::string& configPath) const;
    bool loadPipelineConfig(const std::string& configPath);
    
private:
    std::unique_ptr<IPipeline> m_currentPipeline;
    std::string m_currentPipelineName;
    std::unordered_map<std::string, std::any> m_pipelineConfig;
};

// Image Generator Class
class ImageGenerator {
public:
    ImageGenerator();
    ~ImageGenerator();
    
    // Main initialization
    bool initialize();
    void shutdown();
    
    // Main processing functions
    ImageBundle generateImage(const ImageParams& params);
    SpritesheetBundle generateSpritesheet(const SpritesheetParams& params);
    ImageBundle captureFrame(const CaptureParams& params);
    
    // NEW: Animation functions
    AnimationBundle generateAnimation(const AnimationParams& params);
    std::vector<ImageBundle> captureAnimationFrames(const AnimationParams& params);
    bool exportStarboundAnimation(const AnimationParams& params, const std::string& outputPath);
    
    // NEW: Enhanced tile capture and assembly functions
    std::vector<ImageBundle> CaptureTiles(
        IPipeline& pipeline, RenderContext& ctx,
        bool animMode, int frameCount, float frameDuration,
        int tileW, int tileH, int pad, int orderIdx
    );
    SpritesheetBundle MakeSheet(
        const std::vector<ImageBundle>& tiles,
        int cols, int rows, int tileW, int tileH, int padding
    );
    
    // NEW: Dynamic pipeline management
    bool loadPipeline(const std::string& pipelineName);
    bool switchPipeline(const std::string& pipelineName);
    void unloadCurrentPipeline();
    std::vector<std::string> getAvailablePipelines() const;
    std::string getCurrentPipelineName() const;
    bool isPipelineLoaded() const;
    
    // NEW: Pipeline configuration
    bool savePipelineConfig(const std::string& configPath) const;
    bool loadPipelineConfig(const std::string& configPath);
    bool setPipelineParameter(const std::string& name, const std::any& value);
    std::any getPipelineParameter(const std::string& name) const;
    std::vector<std::string> getPipelineSupportedParameters() const;
    
    // NEW: Starbound Animation JSON Generator
    void WriteStarboundAnimationJSON(
        const std::string& path,
        int frameCount,
        float frameDuration,
        int cols, int rows,
        int orderIdx
    );
    
    // UI functions
    void showImageGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    void showSpritesheetGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    void showAnimationGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    void showTimelineEditorWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    void showPreviewWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    void showControlsWindow(ImGuiContext* imgui, RenderContext& renderCtx);
    
    // State management
    ImageGeneratorState& getState() { return m_state; }
    const ImageGeneratorState& getState() const { return m_state; }
    void setState(const ImageGeneratorState& state) { m_state = state; }
    
    // NEW: Animation state management
    AnimationGeneratorState& getAnimationState() { return m_animationState; }
    const AnimationGeneratorState& getAnimationState() const { return m_animationState; }
    void setAnimationState(const AnimationGeneratorState& state) { m_animationState = state; }
    
    // Parameter management
    void setImageParams(const ImageParams& params) { m_state.imageParams = params; }
    void setSpritesheetParams(const SpritesheetParams& params) { m_state.spritesheetParams = params; }
    void setCaptureParams(const CaptureParams& params) { m_state.captureParams = params; }
    void setUIParams(const UIParams& params) { m_state.uiParams = params; }
    
    // NEW: Animation parameter management
    void setAnimationParams(const AnimationParams& params) { m_animationState.animationParams = params; }
    void setAnimationSpritesheetParams(const SpritesheetParams& params) { m_animationState.spritesheetParams = params; }
    void setAnimationCaptureParams(const CaptureParams& params) { m_animationState.captureParams = params; }
    
    // Generation control
    void startGeneration();
    void stopGeneration();
    bool isGenerating() const { return m_state.isGenerating; }
    float getGenerationProgress() const { return m_state.generationProgress; }
    
    // NEW: Animation generation control
    void startAnimationGeneration();
    void stopAnimationGeneration();
    bool isAnimationGenerating() const { return m_animationState.isGenerating; }
    float getAnimationGenerationProgress() const { return m_animationState.generationProgress; }
    
    // Capture control
    void startCapture();
    void stopCapture();
    bool isCapturing() const { return m_state.isCapturing; }
    
    // NEW: Animation preview control
    void startAnimationPreview();
    void stopAnimationPreview();
    bool isAnimationPreviewing() const { return m_animationState.isPreviewing; }
    float getAnimationPreviewTime() const { return m_animationState.previewTime; }
    
    // File operations
    bool saveImage(const ImageBundle& bundle, const std::string& filePath);
    bool saveSpritesheet(const SpritesheetBundle& bundle, const std::string& filePath);
    bool loadImage(const std::string& filePath, ImageBundle& bundle);
    bool loadSpritesheet(const std::string& filePath, SpritesheetBundle& bundle);
    
    // NEW: Animation file operations
    bool saveAnimation(const AnimationBundle& bundle, const std::string& filePath);
    bool loadAnimation(const std::string& filePath, AnimationBundle& bundle);
    bool exportAnimationJSON(const AnimationBundle& bundle, const std::string& outputPath);
    
    // Export functions
    bool exportSpritesheet(const SpritesheetParams& params, const std::string& outputPath);
    bool exportAtlasJSON(const SpritesheetBundle& bundle, const std::string& outputPath);
    bool exportIndividualFrames(const SpritesheetBundle& bundle, const std::string& outputDir);
    
    // NEW: Animation export functions
    bool exportStarboundAnimation(const AnimationParams& params, const std::string& outputPath);
    bool exportAnimationFrames(const AnimationBundle& bundle, const std::string& outputDir);
    bool exportTimelineData(const AnimationBundle& bundle, const std::string& outputPath);
    
    // Utility functions
    std::string getFormatExtension(ImageFormat format) const;
    std::string getCompressionName(ImageCompression compression) const;
    std::string getQualityName(ImageQuality quality) const;
    std::string getLayoutName(SpritesheetLayout layout) const;
    std::string getPaddingStyleName(PaddingStyle style) const;
    
    // NEW: Animation utility functions
    std::string getAnimationModeString(AnimationMode mode) const;
    std::string getFrameOrderString(FrameOrder order) const;
    std::string getTimelineTrackTypeString(TimelineTrackType type) const;
    std::string getAnimationExportFormatString(AnimationExportFormat format) const;
    
    // Performance and metrics
    ImagePerformanceMetrics& getPerformanceMetrics() { return m_performanceMetrics; }
    const ImagePerformanceMetrics& getPerformanceMetrics() const { return m_performanceMetrics; }
    void resetPerformanceMetrics() { m_performanceMetrics.reset(); }
    
    // NEW: Animation performance metrics
    AnimationPerformanceMetrics& getAnimationPerformanceMetrics() { return m_animationPerformanceMetrics; }
    const AnimationPerformanceMetrics& getAnimationPerformanceMetrics() const { return m_animationPerformanceMetrics; }
    void resetAnimationPerformanceMetrics() { m_animationPerformanceMetrics.reset(); }
    
    // Quality assessment
    ImageQualityMetrics assessImageQuality(const ImageBundle& bundle);
    bool validateImageParams(const ImageParams& params, std::string& errorMessage);
    bool validateSpritesheetParams(const SpritesheetParams& params, std::string& errorMessage);
    bool validateCaptureParams(const CaptureParams& params, std::string& errorMessage);
    
    // NEW: Animation quality assessment
    AnimationQualityMetrics assessAnimationQuality(const AnimationBundle& bundle);
    bool validateAnimationParams(const AnimationParams& params, std::string& errorMessage);
    bool validateTimelineData(const AnimationTimeline& timeline, std::string& errorMessage);
    
    // Error handling
    std::string getLastError() const { return m_lastError; }
    void clearLastError() { m_lastError.clear(); }
    bool hasError() const { return !m_lastError.empty(); }
    
    // Configuration
    void setProcessingQuality(int quality);
    void setCompressionQuality(float quality);
    void setGPUAcceleration(bool enable);
    void setAsyncProcessing(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Caching
    void enableCaching(bool enable);
    void clearCache();
    size_t getCacheSize() const;
    
    // Hot reload
    void enableHotReload(bool enable);
    void reloadConfiguration();
    
private:
    // Internal state
    ImageGeneratorState m_state;
    AnimationGeneratorState m_animationState;
    ImagePerformanceMetrics m_performanceMetrics;
    AnimationPerformanceMetrics m_animationPerformanceMetrics;
    std::string m_lastError;
    
    // Processing settings
    int m_processingQuality;
    float m_compressionQuality;
    bool m_gpuAccelerationEnabled;
    bool m_asyncProcessingEnabled;
    int m_maxProcessingThreads;
    bool m_cachingEnabled;
    bool m_hotReloadEnabled;
    
    // Threading
    std::mutex m_generationMutex;
    std::condition_variable m_generationCV;
    std::thread m_generationThread;
    std::atomic<bool> m_generationThreadRunning{false};
    
    // NEW: Animation threading
    std::mutex m_animationMutex;
    std::condition_variable m_animationCV;
    std::thread m_animationThread;
    std::atomic<bool> m_animationThreadRunning{false};
    
    // Caching
    std::unordered_map<uint64_t, ImageBundle> m_imageCache;
    std::unordered_map<uint64_t, SpritesheetBundle> m_spritesheetCache;
    std::unordered_map<uint64_t, AnimationBundle> m_animationCache;
    std::mutex m_cacheMutex;
    
    // External dependencies
    std::unique_ptr<RenderContext> m_renderContext;
    std::unique_ptr<IPipeline> m_pipeline;
    std::unique_ptr<ImageAssembler> m_imageAssembler;
    std::unique_ptr<ImageWriter> m_imageWriter;
    std::unique_ptr<SpritesheetAssembler> m_spritesheetAssembler;
    std::unique_ptr<AnimationAssembler> m_animationAssembler;
    
    // NEW: Dynamic pipeline management
    std::unique_ptr<PipelineManager> m_pipelineManager;
    
    // Internal helper functions
    void initializeUI();
    void shutdownUI();
    void updateGenerationProgress(float progress);
    void handleGenerationError(const std::string& error);
    
    // NEW: Animation helper functions
    void updateAnimationGenerationProgress(float progress);
    void updateAnimationPreviewTime(float time);
    void handleAnimationGenerationError(const std::string& error);
    
    // Image processing helpers
    ImageBundle processImageGeneration(const ImageParams& params);
    SpritesheetBundle processSpritesheetGeneration(const SpritesheetParams& params);
    ImageBundle processFrameCapture(const CaptureParams& params);
    
    // NEW: Animation processing helpers
    AnimationBundle processAnimationGeneration(const AnimationParams& params);
    std::vector<ImageBundle> processAnimationFrameCapture(const AnimationParams& params);
    StarboundAnimationMetadata processStarboundMetadata(const AnimationParams& params);
    
    // UI rendering helpers
    void renderImageGeneratorUI(ImGuiContext* imgui);
    void renderSpritesheetGeneratorUI(ImGuiContext* imgui);
    void renderPreviewUI(ImGuiContext* imgui);
    void renderControlsUI(ImGuiContext* imgui);
    void renderStatusBar(ImGuiContext* imgui);
    
    // NEW: Animation UI rendering helpers
    void renderAnimationGeneratorUI(ImGuiContext* imgui);
    void renderTimelineEditorUI(ImGuiContext* imgui);
    void renderAnimationPreviewUI(ImGuiContext* imgui);
    void renderAnimationControlsUI(ImGuiContext* imgui);
    void renderAnimationStatusBar(ImGuiContext* imgui);
    
    // Validation helpers
    bool validateImageDimensions(int width, int height);
    bool validateSpritesheetDimensions(int cols, int rows, int tileW, int tileH);
    bool validateFilePaths(const std::string& filePath);
    
    // NEW: Animation validation helpers
    bool validateAnimationFrameCount(int frameCount);
    bool validateAnimationDuration(float duration);
    bool validateTimelineKeyframes(const std::vector<TimelineKeyframe>& keyframes);
    
    // Utility helpers
    std::string generateUniqueID() const;
    std::string sanitizeFilename(const std::string& filename) const;
    std::string getTimestampString() const;
    
    // NEW: Animation utility helpers
    std::string generateAnimationID() const;
    std::string sanitizeAnimationFilename(const std::string& filename) const;
    std::string getAnimationTimestampString() const;
    
    // Threading helpers
    void generationThreadFunction();
    void processAsyncGeneration();
    void processAsyncCapture();
    
    // NEW: Animation threading helpers
    void animationThreadFunction();
    void processAsyncAnimationGeneration();
    void processAsyncAnimationPreview();
    
    // Cache helpers
    bool getCachedImage(uint64_t hash, ImageBundle& bundle);
    bool getCachedSpritesheet(uint64_t hash, SpritesheetBundle& bundle);
    void cacheImage(uint64_t hash, const ImageBundle& bundle);
    void cacheSpritesheet(uint64_t hash, const SpritesheetBundle& bundle);
    
    // NEW: Animation cache helpers
    bool getCachedAnimation(uint64_t hash, AnimationBundle& bundle);
    void cacheAnimation(uint64_t hash, const AnimationBundle& bundle);
    
    // Performance helpers
    void updatePerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage);
    void logPerformanceMetrics();
    
    // NEW: Animation performance helpers
    void updateAnimationPerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage);
    void logAnimationPerformanceMetrics();
    
    // Constants
    static constexpr size_t MAX_CACHE_SIZE = 100;
    static constexpr size_t MAX_THREADS = 8;
    static constexpr float DEFAULT_COMPRESSION_QUALITY = 0.8f;
    static constexpr int DEFAULT_PROCESSING_QUALITY = 3;
    
    // NEW: Animation constants
    static constexpr size_t MAX_ANIMATION_CACHE_SIZE = 50;
    static constexpr float DEFAULT_ANIMATION_FRAME_DURATION = 0.1f;
    static constexpr int DEFAULT_ANIMATION_FRAME_COUNT = 8;
    static constexpr float DEFAULT_ANIMATION_FRAME_RATE = 30.0f;
};

// Animation Assembler Class for Animation Assembly
class AnimationAssembler {
public:
    AnimationAssembler();
    ~AnimationAssembler();
    
    // Main assembly function
    AnimationBundle assembleAnimation(
        const std::vector<ImageBundle>& frames,
        const AnimationParams& params
    );
    
    // Frame processing
    std::vector<ImageBundle> processAnimationFrames(const std::vector<ImageBundle>& frames, const AnimationParams& params);
    std::vector<int> generateFrameIndices(const AnimationParams& params);
    std::vector<float> generateFrameTimes(const AnimationParams& params);
    
    // Timeline processing
    AnimationTimeline processTimeline(const AnimationParams& params);
    float evaluateTimelineAtTime(const AnimationTimeline& timeline, float time, const std::string& trackName);
    TimelineKeyframe interpolateKeyframes(const TimelineKeyframe& k1, const TimelineKeyframe& k2, float t);
    
    // Starbound metadata generation
    StarboundAnimationMetadata generateStarboundMetadata(const AnimationParams& params);
    std::string generateStarboundAnimationJSON(const StarboundAnimationMetadata& metadata);
    bool validateStarboundCompatibility(const AnimationParams& params);
    
    // Export functions
    bool exportAnimationJSON(const AnimationBundle& bundle, const std::string& outputPath);
    bool exportTimelineData(const AnimationBundle& bundle, const std::string& outputPath);
    bool exportIndividualFrames(const AnimationBundle& bundle, const std::string& outputDir);
    
private:
    // Internal state
    bool m_initialized;
    std::string m_lastError;
    
    // Processing settings
    bool m_enableOptimization;
    bool m_enableCompression;
    float m_compressionQuality;
    bool m_enableStarboundCompatibility;
    
    // Helper functions
    void initialize();
    void shutdown();
    bool validateAnimationFrames(const std::vector<ImageBundle>& frames, const AnimationParams& params);
    bool validateTimelineData(const AnimationTimeline& timeline);
    std::vector<TimelineKeyframe> sortKeyframesByTime(const std::vector<TimelineKeyframe>& keyframes);
};

// Utility functions for external use
namespace Utils {
    // Format conversion
    std::string formatToString(ImageFormat format);
    ImageFormat stringToFormat(const std::string& str);
    
    // Quality conversion
    std::string qualityToString(ImageQuality quality);
    ImageQuality stringToQuality(const std::string& str);
    
    // Layout conversion
    std::string layoutToString(SpritesheetLayout layout);
    SpritesheetLayout stringToLayout(const std::string& str);
    
    // Padding style conversion
    std::string paddingStyleToString(PaddingStyle style);
    PaddingStyle stringToPaddingStyle(const std::string& str);
    
    // NEW: Animation conversion functions
    std::string animationModeToString(AnimationMode mode);
    AnimationMode stringToAnimationMode(const std::string& str);
    
    std::string frameOrderToString(FrameOrder order);
    FrameOrder stringToFrameOrder(const std::string& str);
    
    std::string timelineTrackTypeToString(TimelineTrackType type);
    TimelineTrackType stringToTimelineTrackType(const std::string& str);
    
    std::string animationExportFormatToString(AnimationExportFormat format);
    AnimationExportFormat stringToAnimationExportFormat(const std::string& str);
    
    // File utilities
    bool fileExists(const std::string& filePath);
    bool createDirectory(const std::string& dirPath);
    std::string getFileExtension(const std::string& filePath);
    std::string getFileName(const std::string& filePath);
    std::string getDirectory(const std::string& filePath);
    
    // Image utilities
    bool isValidImageSize(int width, int height);
    bool isValidSpritesheetSize(int cols, int rows, int tileW, int tileH);
    glm::vec2 calculateAspectRatio(int width, int height);
    float calculateAspectRatioFloat(int width, int height);
    
    // NEW: Animation utilities
    bool isValidAnimationFrameCount(int frameCount);
    bool isValidAnimationDuration(float duration);
    bool isValidAnimationFrameRate(float frameRate);
    int calculateOptimalFrameCount(float duration, float frameRate);
    
    // Color utilities
    glm::vec4 hexToColor(const std::string& hex);
    std::string colorToHex(const glm::vec4& color);
    glm::vec4 blendColors(const glm::vec4& color1, const glm::vec4& color2, float factor);
    
    // String utilities
    std::string toLower(const std::string& str);
    std::string toUpper(const std::string& str);
    std::string trim(const std::string& str);
    std::vector<std::string> split(const std::string& str, char delimiter);
    std::string join(const std::vector<std::string>& strings, const std::string& delimiter);
    
    // Time utilities
    std::string getCurrentTimestamp();
    std::string formatDuration(std::chrono::milliseconds duration);
    std::string formatFileSize(size_t bytes);
    
    // Validation utilities
    bool isValidFilename(const std::string& filename);
    bool isValidPath(const std::string& path);
    bool isSupportedFormat(const std::string& extension);
    
    // NEW: Animation validation utilities
    bool isValidAnimationFilename(const std::string& filename);
    bool isValidAnimationPath(const std::string& path);
    bool isSupportedAnimationFormat(const std::string& extension);
}

} // namespace ImageGen
} // namespace MagiTech 
