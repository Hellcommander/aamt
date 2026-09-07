#include "ImageGenerator.hpp"
#include <imgui.h>
#include <imgui_internal.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <future>
#include <stb_image.h>
#include <stb_image_write.h>
#include <deprecated/stb_image_resize.h>
#include <nlohmann/json.hpp>

namespace MagiTech {
namespace ImageGen {

// ImageGenerator Implementation
ImageGenerator::ImageGenerator()
    : m_processingQuality(DEFAULT_PROCESSING_QUALITY)
    , m_compressionQuality(DEFAULT_COMPRESSION_QUALITY)
    , m_gpuAccelerationEnabled(false)
    , m_asyncProcessingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_cachingEnabled(true)
    , m_hotReloadEnabled(false)
{
    // Initialize default state
    m_state.id = "image_generator";
    m_state.imageParams.id = "default_image";
    m_state.imageParams.width = 512;
    m_state.imageParams.height = 512;
    m_state.imageParams.format = ImageFormat::PNG;
    m_state.imageParams.quality = ImageQuality::HIGH;
    
    m_state.spritesheetParams.id = "default_spritesheet";
    m_state.spritesheetParams.columns = 4;
    m_state.spritesheetParams.rows = 3;
    m_state.spritesheetParams.tileWidth = 256;
    m_state.spritesheetParams.tileHeight = 256;
    m_state.spritesheetParams.padding = 2;
    m_state.spritesheetParams.layout = SpritesheetLayout::GRID;
    m_state.spritesheetParams.paddingStyle = PaddingStyle::TRANSPARENT;
    
    m_state.captureParams.id = "default_capture";
    m_state.captureParams.width = 512;
    m_state.captureParams.height = 512;
    
    m_state.uiParams.showWindow = true;
    m_state.uiParams.showPreview = true;
    m_state.uiParams.showControls = true;
    
    // Initialize animation state
    m_animationState.id = "animation_generator";
    m_animationState.animationParams.id = "default_animation";
    m_animationState.animationParams.mode = AnimationMode::ANIMATED_SEQUENCE;
    m_animationState.animationParams.frameCount = DEFAULT_ANIMATION_FRAME_COUNT;
    m_animationState.animationParams.frameDuration = DEFAULT_ANIMATION_FRAME_DURATION;
    m_animationState.animationParams.frameOrder = FrameOrder::ROW_MAJOR;
    m_animationState.animationParams.looping = true;
    m_animationState.animationParams.frameRate = DEFAULT_ANIMATION_FRAME_RATE;
    m_animationState.animationParams.useTimeline = false;
    m_animationState.animationParams.timelineDuration = 1.0f;
    m_animationState.animationParams.exportFormat = AnimationExportFormat::STARBOUND_ANIMATION;
    m_animationState.animationParams.generateAnimationJSON = true;
    m_animationState.animationParams.generateAtlasJSON = true;
    m_animationState.animationParams.animationName = "default";
    m_animationState.animationParams.starboundCompatible = true;
    m_animationState.animationParams.starboundCategory = "mech";
    m_animationState.animationParams.starboundType = "animation";
    
    m_animationState.spritesheetParams = m_state.spritesheetParams;
    m_animationState.captureParams = m_state.captureParams;
    m_animationState.uiParams = m_state.uiParams;
    
    m_animationState.showAnimationGenerator = true;
    m_animationState.showTimelineEditor = true;
    m_animationState.showPreview = true;
    m_animationState.showControls = true;
    
    // Initialize pipeline manager
    m_pipelineManager = std::make_unique<PipelineManager>();
}

ImageGenerator::~ImageGenerator() {
    shutdown();
}

bool ImageGenerator::initialize() {
    try {
        // Register default pipelines
        registerDefaultPipelines();
        
        // Initialize external dependencies
        m_renderContext = std::make_unique<RenderContext>();
        m_imageAssembler = std::make_unique<ImageAssembler>();
        m_imageWriter = std::make_unique<ImageWriter>();
        m_spritesheetAssembler = std::make_unique<SpritesheetAssembler>();
        m_animationAssembler = std::make_unique<AnimationAssembler>();
        
        // Initialize pipeline manager
        if (!m_pipelineManager) {
            m_pipelineManager = std::make_unique<PipelineManager>();
        }
        
        // Try to load default pipeline if available
        auto availablePipelines = m_pipelineManager->getAvailablePipelines();
        if (!availablePipelines.empty()) {
            m_pipelineManager->loadPipeline(availablePipelines[0]);
        }
        
        // Initialize UI
        initializeUI();
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Initialization failed: " + std::string(e.what());
        return false;
    }
}

void ImageGenerator::shutdown() {
    // Stop generation threads
    m_generationThreadRunning = false;
    m_animationThreadRunning = false;
    m_generationCV.notify_all();
    m_animationCV.notify_all();
    
    if (m_generationThread.joinable()) {
        m_generationThread.join();
    }
    
    if (m_animationThread.joinable()) {
        m_animationThread.join();
    }
    
    // Shutdown UI
    shutdownUI();
    
    // Clear caches
    clearCache();
}

// Main UI Functions
void ImageGenerator::showImageGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Image Generator", &m_state.uiParams.showWindow, 
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("Save Image", "Ctrl+S")) {
                // TODO: Implement save functionality
            }
            if (ImGui::MenuItem("Load Image", "Ctrl+O")) {
                // TODO: Implement load functionality
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_state.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Preview", nullptr, &m_state.uiParams.showPreview);
            ImGui::MenuItem("Controls", nullptr, &m_state.uiParams.showControls);
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderImageGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showSpritesheetGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Spritesheet Generator", &m_state.uiParams.showWindow,
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("Save Spritesheet", "Ctrl+Shift+S")) {
                // TODO: Implement save functionality
            }
            if (ImGui::MenuItem("Export Atlas JSON", "Ctrl+E")) {
                // TODO: Implement export functionality
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_state.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderSpritesheetGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showPreviewWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showPreview) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Preview", &m_state.uiParams.showPreview,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderPreviewUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showControlsWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showControls) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Controls", &m_state.uiParams.showControls,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderControlsUI(imgui);
    
    ImGui::End();
}

// NEW: Animation UI Functions
void ImageGenerator::showAnimationGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_animationState.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Animation Generator", &m_animationState.uiParams.showWindow,
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("Save Animation", "Ctrl+Shift+A")) {
                // TODO: Implement save functionality
            }
            if (ImGui::MenuItem("Export Starbound Animation", "Ctrl+E")) {
                // TODO: Implement export functionality
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_animationState.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Timeline Editor", nullptr, &m_animationState.showTimelineEditor);
            ImGui::MenuItem("Preview", nullptr, &m_animationState.showPreview);
            ImGui::MenuItem("Controls", nullptr, &m_animationState.showControls);
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderAnimationGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showTimelineEditorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_animationState.showTimelineEditor) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Timeline Editor", &m_animationState.showTimelineEditor,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderTimelineEditorUI(imgui);
    
    ImGui::End();
}

// UI Rendering Functions
void ImageGenerator::renderImageGeneratorUI(ImGuiContext* imgui) {
    // Configuration section
    if (ImGui::CollapsingHeader("Configuration", ImGuiTreeNodeFlags_DefaultOpen)) {
        // Image parameters
        ImGui::Text("Image Settings");
        ImGui::Separator();
        
        static char filename[64] = "mech_snapshot";
        ImGui::InputText("Filename", filename, sizeof(filename));
        
        static int resX = 512, resY = 512;
        ImGui::InputInt("Resolution X", &resX);
        ImGui::InputInt("Resolution Y", &resY);
        
        static int formatIdx = 0;
        const char* formats[] = { "PNG", "JPG", "BMP", "TGA", "HDR" };
        ImGui::Combo("Format", &formatIdx, formats, IM_ARRAYSIZE(formats));
        
        static int qualityIdx = 3; // HIGH
        const char* qualities[] = { "Ultra Low", "Low", "Medium", "High", "Ultra High" };
        ImGui::Combo("Quality", &qualityIdx, qualities, IM_ARRAYSIZE(qualities));
        
        // Update state
        m_state.imageParams.id = filename;
        m_state.imageParams.width = resX;
        m_state.imageParams.height = resY;
        m_state.imageParams.format = static_cast<ImageFormat>(formatIdx);
        m_state.imageParams.quality = static_cast<ImageQuality>(qualityIdx);
        
        // Export controls
        ImGui::Text("Export Controls");
        ImGui::Separator();
        
        if (ImGui::Button("Save Image")) {
            // TODO: Implement save functionality
            ImGui::OpenPopup("Save Image");
        }
        
        if (ImGui::BeginPopupModal("Save Image", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
            ImGui::Text("Image saved successfully!");
            if (ImGui::Button("OK")) {
                ImGui::CloseCurrentPopup();
            }
            ImGui::EndPopup();
        }
    }
    
    // Spritesheet section
    if (ImGui::CollapsingHeader("Spritesheet", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Spritesheet Settings");
        ImGui::Separator();
        
        static int cols = 4, rows = 3;
        ImGui::InputInt("Columns", &cols);
        ImGui::InputInt("Rows", &rows);
        
        static int tileW = 256, tileH = 256;
        ImGui::InputInt("Tile Width", &tileW);
        ImGui::InputInt("Tile Height", &tileH);
        
        static int padding = 2;
        ImGui::InputInt("Padding", &padding);
        
        // Update state
        m_state.spritesheetParams.columns = cols;
        m_state.spritesheetParams.rows = rows;
        m_state.spritesheetParams.tileWidth = tileW;
        m_state.spritesheetParams.tileHeight = tileH;
        m_state.spritesheetParams.padding = padding;
        
        if (ImGui::Button("Generate Spritesheet")) {
            startGeneration();
        }
        
        // Status display
        if (m_state.isGenerating) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Generating spritesheet... %.1f%%", 
                              m_state.generationProgress * 100.0f);
            
            ImGui::ProgressBar(m_state.generationProgress);
        } else if (!m_lastError.empty()) {
            ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), 
                              "Error: %s", m_lastError.c_str());
        } else {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Spritesheet saved: %s_sheet.%s",
                              filename, formats[formatIdx]);
        }
    }
    
    // Status bar
    renderStatusBar(imgui);
}

void ImageGenerator::renderSpritesheetGeneratorUI(ImGuiContext* imgui) {
    // Spritesheet configuration
    ImGui::Text("Spritesheet Configuration");
    ImGui::Separator();
    
    static int cols = 4, rows = 3;
    ImGui::InputInt("Columns", &cols);
    ImGui::InputInt("Rows", &rows);
    
    static int tileW = 256, tileH = 256;
    ImGui::InputInt("Tile Width", &tileW);
    ImGui::InputInt("Tile Height", &tileH);
    
    static int padding = 2;
    ImGui::InputInt("Padding", &padding);
    
    // Layout options
    static int layoutIdx = 0;
    const char* layouts[] = { "Grid", "Horizontal", "Vertical", "Custom" };
    ImGui::Combo("Layout", &layoutIdx, layouts, IM_ARRAYSIZE(layouts));
    
    // Padding style
    static int paddingStyleIdx = 2; // TRANSPARENT
    const char* paddingStyles[] = { "None", "Solid", "Transparent", "Pattern", "Gradient" };
    ImGui::Combo("Padding Style", &paddingStyleIdx, paddingStyles, IM_ARRAYSIZE(paddingStyles));
    
    // Update state
    m_state.spritesheetParams.columns = cols;
    m_state.spritesheetParams.rows = rows;
    m_state.spritesheetParams.tileWidth = tileW;
    m_state.spritesheetParams.tileHeight = tileH;
    m_state.spritesheetParams.padding = padding;
    m_state.spritesheetParams.layout = static_cast<SpritesheetLayout>(layoutIdx);
    m_state.spritesheetParams.paddingStyle = static_cast<PaddingStyle>(paddingStyleIdx);
    
    // Generate button
    if (ImGui::Button("Generate Spritesheet", ImVec2(200, 30))) {
        startGeneration();
    }
    
    // Progress and status
    if (m_state.isGenerating) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                          "Generating spritesheet... %.1f%%", 
                          m_state.generationProgress * 100.0f);
        
        ImGui::ProgressBar(m_state.generationProgress);
    }
    
    // Results
    if (!m_state.currentSpritesheet.individualFrames.empty()) {
        ImGui::Text("Generated %zu frames", m_state.currentSpritesheet.individualFrames.size());
        ImGui::Text("Spritesheet size: %dx%d", 
                   m_state.spritesheetParams.columns * m_state.spritesheetParams.tileWidth + 
                   (m_state.spritesheetParams.columns + 1) * m_state.spritesheetParams.padding,
                   m_state.spritesheetParams.rows * m_state.spritesheetParams.tileHeight + 
                   (m_state.spritesheetParams.rows + 1) * m_state.spritesheetParams.padding);
    }
}

void ImageGenerator::renderPreviewUI(ImGuiContext* imgui) {
    // Preview area
    ImGui::Text("Preview");
    ImGui::Separator();
    
    // Placeholder for preview rendering
    ImVec2 previewSize(400, 300);
    ImGui::BeginChild("PreviewArea", previewSize, true, ImGuiWindowFlags_NoScrollbar);
    
    // Draw a placeholder rectangle
    ImVec2 minPos = ImGui::GetWindowPos();
    ImVec2 maxPos = ImVec2(minPos.x + previewSize.x, minPos.y + previewSize.y);
    ImGui::GetWindowDrawList()->AddRectFilled(minPos, maxPos, 
                                             IM_COL32(50, 50, 50, 255));
    
    // Draw preview text
    ImVec2 textPos = ImVec2(minPos.x + 10, minPos.y + 10);
    ImGui::GetWindowDrawList()->AddText(textPos, IM_COL32(255, 255, 255, 255), 
                                       "Preview Area");
    
    ImGui::EndChild();
    
    // Preview controls
    ImGui::Text("Preview Controls");
    ImGui::Separator();
    
    static float previewScale = 1.0f;
    ImGui::SliderFloat("Scale", &previewScale, 0.1f, 3.0f, "%.2f");
    
    static bool enableZoom = true;
    ImGui::Checkbox("Enable Zoom", &enableZoom);
    
    static bool enablePan = true;
    ImGui::Checkbox("Enable Pan", &enablePan);
}

void ImageGenerator::renderControlsUI(ImGuiContext* imgui) {
    // Generation controls
    ImGui::Text("Generation Controls");
    ImGui::Separator();
    
    if (ImGui::Button("Start Generation")) {
        startGeneration();
    }
    
    if (ImGui::Button("Stop Generation")) {
        stopGeneration();
    }
    
    ImGui::SameLine();
    
    if (ImGui::Button("Clear Cache")) {
        clearCache();
    }
    
    // Processing settings
    ImGui::Text("Processing Settings");
    ImGui::Separator();
    
    static int processingQuality = m_processingQuality;
    if (ImGui::SliderInt("Processing Quality", &processingQuality, 1, 5)) {
        setProcessingQuality(processingQuality);
    }
    
    static float compressionQuality = m_compressionQuality;
    if (ImGui::SliderFloat("Compression Quality", &compressionQuality, 0.0f, 1.0f, "%.2f")) {
        setCompressionQuality(compressionQuality);
    }
    
    static bool gpuAcceleration = m_gpuAccelerationEnabled;
    if (ImGui::Checkbox("GPU Acceleration", &gpuAcceleration)) {
        setGPUAcceleration(gpuAcceleration);
    }
    
    static bool asyncProcessing = m_asyncProcessingEnabled;
    if (ImGui::Checkbox("Async Processing", &asyncProcessing)) {
        setAsyncProcessing(asyncProcessing);
    }
    
    // Performance metrics
    ImGui::Text("Performance Metrics");
    ImGui::Separator();
    
    ImGui::Text("Total Generations: %llu", m_performanceMetrics.totalGenerations.load());
    ImGui::Text("Cache Hit Rate: %.2f%%", m_performanceMetrics.getCacheHitRate() * 100.0);
    ImGui::Text("Average Generation Time: %.2f ms", m_performanceMetrics.getAverageGenerationTime());
    ImGui::Text("Peak Memory Usage: %llu MB", m_performanceMetrics.peakMemoryUsage.load() / (1024 * 1024));
    ImGui::Text("Active Generators: %llu", m_performanceMetrics.activeGenerators.load());
}

void ImageGenerator::renderStatusBar(ImGuiContext* imgui) {
    ImGui::Separator();
    
    // Status information
    std::string statusText;
    if (m_state.isGenerating) {
        statusText = "Generating...";
    } else if (m_state.isCapturing) {
        statusText = "Capturing...";
    } else if (!m_lastError.empty()) {
        statusText = "Error: " + m_lastError;
    } else {
        statusText = "Ready";
    }
    
    ImGui::TextColored(ImVec4(0.8f, 0.8f, 0.8f, 1.0f), "%s", statusText.c_str());
    
    // Performance info
    ImGui::SameLine(ImGui::GetWindowWidth() - 200);
    ImGui::Text("Cache: %zu items", getCacheSize());
}

// Generation Control Functions
void ImageGenerator::startGeneration() {
    if (m_state.isGenerating) return;
    
    m_state.isGenerating = true;
    m_state.generationProgress = 0.0f;
    m_generationCV.notify_one();
}

void ImageGenerator::stopGeneration() {
    m_state.isGenerating = false;
    m_state.generationProgress = 0.0f;
}

void ImageGenerator::startCapture() {
    if (m_state.isCapturing) return;
    
    m_state.isCapturing = true;
    m_generationCV.notify_one();
}

void ImageGenerator::stopCapture() {
    m_state.isCapturing = false;
}

// Main Processing Functions
ImageBundle ImageGenerator::generateImage(const ImageParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        ImageBundle cachedBundle;
        if (m_cachingEnabled && getCachedImage(hash, cachedBundle)) {
            m_performanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_performanceMetrics.cacheMisses++;
        m_performanceMetrics.activeGenerators++;
        
        // Generate image
        ImageBundle bundle = processImageGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheImage(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return ImageBundle{};
    }
}

SpritesheetBundle ImageGenerator::generateSpritesheet(const SpritesheetParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        SpritesheetBundle cachedBundle;
        if (m_cachingEnabled && getCachedSpritesheet(hash, cachedBundle)) {
            m_performanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_performanceMetrics.cacheMisses++;
        m_performanceMetrics.activeGenerators++;
        
        // Generate spritesheet
        SpritesheetBundle bundle = processSpritesheetGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheSpritesheet(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return SpritesheetBundle{};
    }
}

ImageBundle ImageGenerator::captureFrame(const CaptureParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        m_performanceMetrics.activeGenerators++;
        
        // Capture frame
        ImageBundle bundle = processFrameCapture(params);
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return ImageBundle{};
    }
}

// Processing Helper Functions
ImageBundle ImageGenerator::processImageGeneration(const ImageParams& params) {
    // TODO: Implement actual image generation
    // This is a placeholder implementation
    
    ImageBundle bundle;
    bundle.image = 1; // Placeholder handle
    bundle.texture = 1; // Placeholder handle
    bundle.framebuffer = 1; // Placeholder handle
    
    // Create metadata
    bundle.metadata.id = params.id;
    bundle.metadata.title = "Generated Image";
    bundle.metadata.description = "Generated by MagiTech Image Generator";
    bundle.metadata.author = "MagiTech";
    bundle.metadata.version = "1.0.0";
    bundle.metadata.creationTime = std::chrono::system_clock::now();
    bundle.metadata.width = params.width;
    bundle.metadata.height = params.height;
    bundle.metadata.format = params.format;
    bundle.metadata.compression = params.compressionType;
    bundle.metadata.fileSize = params.width * params.height * 4; // RGBA8
    bundle.metadata.checksum = "placeholder_checksum";
    
    return bundle;
}

SpritesheetBundle ImageGenerator::processSpritesheetGeneration(const SpritesheetParams& params) {
    // TODO: Implement actual spritesheet generation
    // This is a placeholder implementation
    
    SpritesheetBundle bundle;
    bundle.spritesheet = 1; // Placeholder handle
    bundle.spritesheetTexture = 1; // Placeholder handle
    
    // Generate individual frames
    int totalFrames = params.columns * params.rows;
    for (int i = 0; i < totalFrames; ++i) {
        bundle.individualFrames.push_back(i + 2); // Placeholder handles
        bundle.individualTextures.push_back(i + 2); // Placeholder handles
        
        // Calculate frame bounds
        int col = i % params.columns;
        int row = i / params.columns;
        int x = params.padding + col * (params.tileWidth + params.padding);
        int y = params.padding + row * (params.tileHeight + params.padding);
        
        bundle.frameBounds.push_back(glm::vec4(x, y, params.tileWidth, params.tileHeight));
    }
    
    // Create atlas metadata
    bundle.atlasMetadata.id = params.id;
    bundle.atlasMetadata.name = "Generated Spritesheet";
    bundle.atlasMetadata.description = "Generated by MagiTech Image Generator";
    bundle.atlasMetadata.frameCount = totalFrames;
    bundle.atlasMetadata.frameRate = params.frameRate;
    bundle.atlasMetadata.looping = params.enableLooping;
    
    // Create frame info
    for (int i = 0; i < totalFrames; ++i) {
        AtlasMetadata::FrameInfo frameInfo;
        frameInfo.name = "frame_" + std::to_string(i);
        frameInfo.x = bundle.frameBounds[i].x;
        frameInfo.y = bundle.frameBounds[i].y;
        frameInfo.width = bundle.frameBounds[i].z;
        frameInfo.height = bundle.frameBounds[i].w;
        frameInfo.duration = 1.0f / params.frameRate;
        
        bundle.atlasMetadata.frames.push_back(frameInfo);
    }
    
    // Create animation info
    AtlasMetadata::AnimationInfo animInfo;
    animInfo.name = params.animationName;
    animInfo.frameRate = params.frameRate;
    animInfo.looping = params.enableLooping;
    for (int i = 0; i < totalFrames; ++i) {
        animInfo.frameIndices.push_back(i);
    }
    bundle.atlasMetadata.animations.push_back(animInfo);
    
    return bundle;
}

ImageBundle ImageGenerator::processFrameCapture(const CaptureParams& params) {
    // TODO: Implement actual frame capture
    // This is a placeholder implementation
    
    ImageBundle bundle;
    bundle.image = 1; // Placeholder handle
    bundle.texture = 1; // Placeholder handle
    bundle.framebuffer = 1; // Placeholder handle
    
    // Create metadata
    bundle.metadata.id = params.id;
    bundle.metadata.title = "Captured Frame";
    bundle.metadata.description = "Captured by MagiTech Image Generator";
    bundle.metadata.author = "MagiTech";
    bundle.metadata.version = "1.0.0";
    bundle.metadata.creationTime = std::chrono::system_clock::now();
    bundle.metadata.width = params.width;
    bundle.metadata.height = params.height;
    bundle.metadata.format = ImageFormat::PNG;
    bundle.metadata.compression = ImageCompression::NONE;
    bundle.metadata.fileSize = params.width * params.height * 4; // RGBA8
    bundle.metadata.checksum = "placeholder_checksum";
    
    return bundle;
}

// Threading Functions
void ImageGenerator::generationThreadFunction() {
    while (m_generationThreadRunning) {
        std::unique_lock<std::mutex> lock(m_generationMutex);
        m_generationCV.wait(lock, [this] { 
            return !m_generationThreadRunning || m_state.isGenerating || m_state.isCapturing; 
        });
        
        if (!m_generationThreadRunning) break;
        
        if (m_state.isGenerating) {
            processAsyncGeneration();
        }
        
        if (m_state.isCapturing) {
            processAsyncCapture();
        }
    }
}

void ImageGenerator::processAsyncGeneration() {
    try {
        // Simulate generation progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_state.isGenerating) break;
            
            m_state.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
        
        // Generate spritesheet
        SpritesheetBundle bundle = generateSpritesheet(m_state.spritesheetParams);
        m_state.currentSpritesheet = bundle;
        
        m_state.isGenerating = false;
        m_state.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_state.isGenerating = false;
        m_state.generationProgress = 0.0f;
    }
}

void ImageGenerator::processAsyncCapture() {
    try {
        // Simulate capture progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_state.isCapturing) break;
            
            m_state.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        
        // Capture frame
        ImageBundle bundle = captureFrame(m_state.captureParams);
        m_state.currentImage = bundle;
        
        m_state.isCapturing = false;
        m_state.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_state.isCapturing = false;
        m_state.generationProgress = 0.0f;
    }
}

// Cache Functions
bool ImageGenerator::getCachedImage(uint64_t hash, ImageBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_imageCache.find(hash);
    if (it != m_imageCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

bool ImageGenerator::getCachedSpritesheet(uint64_t hash, SpritesheetBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_spritesheetCache.find(hash);
    if (it != m_spritesheetCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

void ImageGenerator::cacheImage(uint64_t hash, const ImageBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_imageCache.size() >= MAX_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_imageCache.erase(m_imageCache.begin());
    }
    
    m_imageCache[hash] = bundle;
}

void ImageGenerator::cacheSpritesheet(uint64_t hash, const SpritesheetBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_spritesheetCache.size() >= MAX_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_spritesheetCache.erase(m_spritesheetCache.begin());
    }
    
    m_spritesheetCache[hash] = bundle;
}

// Configuration Functions
void ImageGenerator::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 5);
}

void ImageGenerator::setCompressionQuality(float quality) {
    m_compressionQuality = std::clamp(quality, 0.0f, 1.0f);
}

void ImageGenerator::setGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void ImageGenerator::setAsyncProcessing(bool enable) {
    m_asyncProcessingEnabled = enable;
}

void ImageGenerator::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, static_cast<int>(MAX_THREADS));
}

void ImageGenerator::enableCaching(bool enable) {
    m_cachingEnabled = enable;
}

void ImageGenerator::clearCache() {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    m_imageCache.clear();
    m_spritesheetCache.clear();
}

size_t ImageGenerator::getCacheSize() const {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    return m_imageCache.size() + m_spritesheetCache.size();
}

void ImageGenerator::enableHotReload(bool enable) {
    m_hotReloadEnabled = enable;
}

void ImageGenerator::reloadConfiguration() {
    // TODO: Implement configuration reload
}

// Utility Functions
std::string ImageGenerator::getFormatExtension(ImageFormat format) const {
    switch (format) {
        case ImageFormat::PNG: return "png";
        case ImageFormat::JPG: return "jpg";
        case ImageFormat::BMP: return "bmp";
        case ImageFormat::TGA: return "tga";
        case ImageFormat::HDR: return "hdr";
        default: return "png";
    }
}

std::string ImageGenerator::getCompressionName(ImageCompression compression) const {
    switch (compression) {
        case ImageCompression::NONE: return "None";
        case ImageCompression::LOSSY: return "Lossy";
        case ImageCompression::LOSSLESS: return "Lossless";
        case ImageCompression::BC1: return "BC1";
        case ImageCompression::BC3: return "BC3";
        case ImageCompression::BC7: return "BC7";
        case ImageCompression::ASTC_4x4: return "ASTC 4x4";
        case ImageCompression::ASTC_8x8: return "ASTC 8x8";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getQualityName(ImageQuality quality) const {
    switch (quality) {
        case ImageQuality::ULTRA_LOW: return "Ultra Low";
        case ImageQuality::LOW: return "Low";
        case ImageQuality::MEDIUM: return "Medium";
        case ImageQuality::HIGH: return "High";
        case ImageQuality::ULTRA_HIGH: return "Ultra High";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getLayoutName(SpritesheetLayout layout) const {
    switch (layout) {
        case SpritesheetLayout::GRID: return "Grid";
        case SpritesheetLayout::HORIZONTAL: return "Horizontal";
        case SpritesheetLayout::VERTICAL: return "Vertical";
        case SpritesheetLayout::CUSTOM: return "Custom";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getPaddingStyleName(PaddingStyle style) const {
    switch (style) {
        case PaddingStyle::NONE: return "None";
        case PaddingStyle::SOLID: return "Solid";
        case PaddingStyle::TRANSPARENT: return "Transparent";
        case PaddingStyle::PATTERN: return "Pattern";
        case PaddingStyle::GRADIENT: return "Gradient";
        default: return "Unknown";
    }
}

// Error Handling Functions
void ImageGenerator::handleGenerationError(const std::string& error) {
    m_lastError = error;
    m_state.isGenerating = false;
    m_state.isCapturing = false;
    m_state.generationProgress = 0.0f;
}

// UI Helper Functions
void ImageGenerator::initializeUI() {
    // TODO: Initialize ImGui context and resources
}

void ImageGenerator::shutdownUI() {
    // TODO: Cleanup ImGui resources
}

void ImageGenerator::updateGenerationProgress(float progress) {
    m_state.generationProgress = std::clamp(progress, 0.0f, 1.0f);
}

// Validation Functions
bool ImageGenerator::validateImageDimensions(int width, int height) {
    return width > 0 && height > 0 && width <= 8192 && height <= 8192;
}

bool ImageGenerator::validateSpritesheetDimensions(int cols, int rows, int tileW, int tileH) {
    return cols > 0 && rows > 0 && tileW > 0 && tileH > 0 &&
           cols * tileW <= 8192 && rows * tileH <= 8192;
}

bool ImageGenerator::validateFilePaths(const std::string& filePath) {
    return !filePath.empty() && filePath.length() < 1024;
}

// Utility Helper Functions
std::string ImageGenerator::generateUniqueID() const {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    return "img_" + std::to_string(millis);
}

std::string ImageGenerator::sanitizeFilename(const std::string& filename) const {
    std::string sanitized = filename;
    const std::string invalidChars = "<>:\"|?*";
    
    for (char& c : sanitized) {
        if (invalidChars.find(c) != std::string::npos) {
            c = '_';
        }
    }
    
    return sanitized;
}

std::string ImageGenerator::getTimestampString() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
    return oss.str();
}

// Performance Helper Functions
void ImageGenerator::updatePerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage) {
    m_performanceMetrics.totalGenerationTime += generationTime;
    m_performanceMetrics.peakMemoryUsage = std::max(m_performanceMetrics.peakMemoryUsage.load(), memoryUsage);
}

void ImageGenerator::logPerformanceMetrics() {
    // TODO: Implement performance logging
}

// Quality Assessment Functions
ImageQualityMetrics ImageGenerator::assessImageQuality(const ImageBundle& bundle) {
    // TODO: Implement image quality assessment
    ImageQualityMetrics metrics;
    return metrics;
}

bool ImageGenerator::validateImageParams(const ImageParams& params, std::string& errorMessage) {
    if (!validateImageDimensions(params.width, params.height)) {
        errorMessage = "Invalid image dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Image ID cannot be empty";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateSpritesheetParams(const SpritesheetParams& params, std::string& errorMessage) {
    if (!validateSpritesheetDimensions(params.columns, params.rows, params.tileWidth, params.tileHeight)) {
        errorMessage = "Invalid spritesheet dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Spritesheet ID cannot be empty";
        return false;
    }
    
    if (params.padding < 0) {
        errorMessage = "Padding cannot be negative";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateCaptureParams(const CaptureParams& params, std::string& errorMessage) {
    if (!validateImageDimensions(params.width, params.height)) {
        errorMessage = "Invalid capture dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Capture ID cannot be empty";
        return false;
    }
    
    return true;
}

// File Operation Functions
bool ImageGenerator::saveImage(const ImageBundle& bundle, const std::string& filePath) {
    // TODO: Implement image saving
    return true;
}

bool ImageGenerator::saveSpritesheet(const SpritesheetBundle& bundle, const std::string& filePath) {
    // TODO: Implement spritesheet saving
    return true;
}

bool ImageGenerator::loadImage(const std::string& filePath, ImageBundle& bundle) {
    // TODO: Implement image loading
    return true;
}

bool ImageGenerator::loadSpritesheet(const std::string& filePath, SpritesheetBundle& bundle) {
    // TODO: Implement spritesheet loading
    return true;
}

// Export Functions
bool ImageGenerator::exportSpritesheet(const SpritesheetParams& params, const std::string& outputPath) {
    // TODO: Implement spritesheet export
    return true;
}

bool ImageGenerator::exportAtlasJSON(const SpritesheetBundle& bundle, const std::string& outputPath) {
    // TODO: Implement atlas JSON export
    return true;
}

bool ImageGenerator::exportIndividualFrames(const SpritesheetBundle& bundle, const std::string& outputDir) {
    // TODO: Implement individual frame export
    return true;
}

// NEW: Animation UI Rendering Functions
void ImageGenerator::renderAnimationGeneratorUI(ImGuiContext* imgui) {
    // Enhanced Animation UI with requested layout
    ImGui::Columns(3, "AnimationLayout", true);
    
    // Configuration Panel
    ImGui::BeginChild("Configuration", ImVec2(0, 0), true);
    ImGui::Text("Configuration");
    ImGui::Separator();
    
    // Mode Selector
    static int modeIdx = 1; // ANIMATED_SEQUENCE
    const char* modes[] = { "Single Frame", "Animated Sequence" };
    ImGui::Text("Mode Selector");
    ImGui::Combo("Mode", &modeIdx, modes, IM_ARRAYSIZE(modes));
    
    // Frame Settings
    ImGui::Text("Frame Settings");
    static int frameCount = DEFAULT_ANIMATION_FRAME_COUNT;
    ImGui::InputInt("Frame Count", &frameCount);
    
    static float frameDuration = DEFAULT_ANIMATION_FRAME_DURATION;
    ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
    
    static int orderIdx = 0; // ROW_MAJOR
    const char* orders[] = { "Row-Major", "Column-Major" };
    ImGui::Combo("Frame Order", &orderIdx, orders, IM_ARRAYSIZE(orders));
    
    // Timeline Editor
    ImGui::Text("Timeline Editor");
    static bool useTimeline = false;
    ImGui::Checkbox("Use Timeline", &useTimeline);
    
    if (useTimeline) {
        static float timelineDuration = 1.0f;
        ImGui::InputFloat("Timeline Duration", &timelineDuration, 0.1f, 1.0f, "%.2f");
        
        // Timeline scrubber
        static float animTime = 0.0f;
        ImGui::SliderFloat("Time", &animTime, 0.0f, timelineDuration, "%.3f");
        
        // Update preview time
        m_animationState.previewTime = animTime;
        
        m_animationState.animationParams.useTimeline = true;
        m_animationState.animationParams.timelineDuration = timelineDuration;
    } else {
        m_animationState.animationParams.useTimeline = false;
    }
    
    // Update state
    m_animationState.animationParams.mode = static_cast<AnimationMode>(modeIdx);
    m_animationState.animationParams.frameCount = frameCount;
    m_animationState.animationParams.frameDuration = frameDuration;
    m_animationState.animationParams.frameOrder = static_cast<FrameOrder>(orderIdx);
    
    ImGui::EndChild();
    ImGui::NextColumn();
    
    // Preview Panel
    ImGui::BeginChild("Preview", ImVec2(0, 0), true);
    ImGui::Text("Preview");
    ImGui::Separator();
    
    // 3D Viewport placeholder
    ImGui::BeginChild("3DViewport", ImVec2(0, 200), true, ImGuiWindowFlags_NoScrollbar);
    ImGui::TextColored(ImVec4(0.7f, 0.7f, 0.7f, 1.0f), "[3D Viewport]");
    ImGui::Text("Animation Preview");
    
    // Preview controls
    if (ImGui::Button("Play", ImVec2(60, 25))) {
        startAnimationPreview();
    }
    ImGui::SameLine();
    if (ImGui::Button("Stop", ImVec2(60, 25))) {
        stopAnimationPreview();
    }
    ImGui::SameLine();
    if (ImGui::Button("Reset", ImVec2(60, 25))) {
        m_animationState.previewTime = 0.0f;
    }
    
    // Preview time display
    ImGui::Text("Time: %.3f", m_animationState.previewTime);
    
    ImGui::EndChild();
    
    // Status display
    if (m_animationState.isPreviewing) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), "Previewing...");
    }
    
    ImGui::EndChild();
    ImGui::NextColumn();
    
    // Export & Animation Panel
    ImGui::BeginChild("Export", ImVec2(0, 0), true);
    ImGui::Text("Export & Animation");
    ImGui::Separator();
    
    // Filename
    static char filename[64] = "mech_animation";
    ImGui::Text("Filename");
    ImGui::InputText("##Filename", filename, sizeof(filename));
    
    // Format options
    ImGui::Text("Format");
    static int formatIdx = 0; // PNG
    const char* formats[] = { "PNG", "JPG", "BMP", "TGA" };
    ImGui::Combo("##Format", &formatIdx, formats, IM_ARRAYSIZE(formats));
    
    // Sheet Layout
    ImGui::Text("Sheet Layout");
    static int cols = 4, rows = 3;
    ImGui::InputInt("Cols", &cols);
    ImGui::InputInt("Rows", &rows);
    
    // Tile dimensions
    ImGui::Text("Tile Dimensions");
    static int tileW = 256, tileH = 256;
    ImGui::InputInt("W", &tileW);
    ImGui::InputInt("H", &tileH);
    
    // Padding
    static int padding = 2;
    ImGui::InputInt("Padding", &padding);
    
    // Frame settings
    ImGui::Text("Frame Settings");
    ImGui::InputInt("Frame Count", &frameCount);
    ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
    
    // Mode
    ImGui::Combo("Mode", &modeIdx, modes, IM_ARRAYSIZE(modes));
    
    // Generate options
    static bool generateSheet = true;
    static bool generateJSON = true;
    ImGui::Checkbox("Generate Sheet+JSON", &generateSheet);
    ImGui::Checkbox("Generate JSON", &generateJSON);
    
    // Generate button
    if (ImGui::Button("Generate Animation Sheet", ImVec2(200, 30))) {
        // Update spritesheet params
        m_animationState.spritesheetParams.columns = cols;
        m_animationState.spritesheetParams.rows = rows;
        m_animationState.spritesheetParams.tileWidth = tileW;
        m_animationState.spritesheetParams.tileHeight = tileH;
        m_animationState.spritesheetParams.padding = padding;
        
        // Update animation params
        m_animationState.animationParams.id = filename;
        m_animationState.animationParams.frameCount = frameCount;
        m_animationState.animationParams.frameDuration = frameDuration;
        m_animationState.animationParams.mode = static_cast<AnimationMode>(modeIdx);
        m_animationState.animationParams.generateAnimationJSON = generateJSON;
        
        startAnimationGeneration();
    }
    
    // Enhanced ImGui snippet for animation controls
    if (ImGui::CollapsingHeader("Animation Controls", ImGuiTreeNodeFlags_DefaultOpen)) {
        static bool animMode = true;       // true = sequence, false = single
        ImGui::Checkbox("Sequence Mode", &animMode);
        
        if (animMode) {
            ImGui::InputInt("Frame Count", &frameCount);
            ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
            ImGui::Combo("Order", &orderIdx, orders, IM_ARRAYSIZE(orders));
            
            // Simple timeline scrubber
            static float animTime = 0.0f;
            ImGui::SliderFloat("Time", &animTime, 0.0f, (frameCount-1)*frameDuration, "%.3f");
            m_animationState.previewTime = animTime;
            
            // Update pipeline with animation time
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline()) {
                m_pipelineManager->getCurrentPipeline()->SetAnimTime(animTime);
            }
        }
        
        if (ImGui::Button(animMode ? "Generate Animation Sheet" : "Capture Frame")) {
            // Capture tiles using enhanced function
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline() && m_renderContext) {
                auto tiles = CaptureTiles(*m_pipelineManager->getCurrentPipeline(), *m_renderContext,
                                       animMode, frameCount, frameDuration,
                                       tileW, tileH, padding, orderIdx);
                
                // Create spritesheet
                auto sheet = MakeSheet(tiles, cols, rows, tileW, tileH, padding);
                
                // Generate output filename
                std::string outPng = filename + (animMode ? "_anim.png" : ".png");
                std::string outJson = filename + ".animation";
                
                // Save spritesheet
                if (saveSpritesheet(sheet, outPng)) {
                    // Generate Starbound animation JSON
                    if (animMode && generateJSON) {
                        WriteStarboundAnimationJSON(outJson, frameCount, frameDuration, cols, rows, orderIdx);
                        
                        // Update status message
                        m_animationState.currentAnimation.spritesheet = sheet;
                        m_animationState.currentAnimation.animationJsonPath = outJson;
                        m_animationState.currentAnimation.spritesheetPath = outPng;
                    }
                }
            }
        }
    }
    
    // NEW: Pipeline Management UI
    if (ImGui::CollapsingHeader("Pipeline Management", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Dynamic Pipeline System");
        ImGui::Separator();
        
        // Current pipeline info
        std::string currentPipeline = getCurrentPipelineName();
        if (currentPipeline.empty()) {
            ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "No pipeline loaded");
        } else {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), "Current: %s", currentPipeline.c_str());
            
            // Pipeline info
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline()) {
                auto pipeline = m_pipelineManager->getCurrentPipeline();
                ImGui::Text("Name: %s", pipeline->GetName().c_str());
                ImGui::Text("Version: %s", pipeline->GetVersion().c_str());
                
                // Supported parameters
                auto params = pipeline->GetSupportedParameters();
                if (!params.empty()) {
                    if (ImGui::TreeNode("Supported Parameters")) {
                        for (const auto& param : params) {
                            ImGui::Text("• %s", param.c_str());
                        }
                        ImGui::TreePop();
                    }
                }
                
                // Supported animations
                auto animations = pipeline->GetSupportedAnimations();
                if (!animations.empty()) {
                    if (ImGui::TreeNode("Supported Animations")) {
                        for (const auto& anim : animations) {
                            ImGui::Text("• %s", anim.c_str());
                        }
                        ImGui::TreePop();
                    }
                }
            }
        }
        
        ImGui::Separator();
        
        // Pipeline selection
        auto availablePipelines = getAvailablePipelines();
        if (!availablePipelines.empty()) {
            static int selectedPipeline = 0;
            std::vector<const char*> pipelineNames;
            for (const auto& name : availablePipelines) {
                pipelineNames.push_back(name.c_str());
            }
            
            ImGui::Text("Available Pipelines:");
            if (ImGui::Combo("##PipelineSelect", &selectedPipeline, pipelineNames.data(), pipelineNames.size())) {
                if (selectedPipeline < availablePipelines.size()) {
                    switchPipeline(availablePipelines[selectedPipeline]);
                }
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Load")) {
                if (selectedPipeline < availablePipelines.size()) {
                    loadPipeline(availablePipelines[selectedPipeline]);
                }
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Unload")) {
                unloadCurrentPipeline();
            }
        } else {
            ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No pipelines available");
        }
        
        // Pipeline configuration
        if (isPipelineLoaded()) {
            ImGui::Separator();
            ImGui::Text("Pipeline Configuration");
            
            static char configPath[256] = "pipeline_config.json";
            ImGui::InputText("Config Path", configPath, sizeof(configPath));
            
            if (ImGui::Button("Save Config")) {
                savePipelineConfig(configPath);
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Load Config")) {
                loadPipelineConfig(configPath);
            }
        }
    }
    
    // Progress and status
    if (m_animationState.isGenerating) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                          "Generating animation... %.1f%%", 
                          m_animationState.generationProgress * 100.0f);
        
        ImGui::ProgressBar(m_animationState.generationProgress);
    }
    
    // Results
    if (!m_animationState.currentAnimation.spritesheet.individualFrames.empty()) {
        ImGui::Text("Generated %zu frames", m_animationState.currentAnimation.spritesheet.individualFrames.size());
        ImGui::Text("Animation duration: %.3f seconds", 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration);
        
        // Show saved files
        if (!m_animationState.currentAnimation.spritesheetPath.empty()) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Saved: %s", m_animationState.currentAnimation.spritesheetPath.c_str());
        }
        
        if (!m_animationState.currentAnimation.animationJsonPath.empty()) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Saved: %s", m_animationState.currentAnimation.animationJsonPath.c_str());
        }
    }
    
    ImGui::EndChild();
    ImGui::Columns(1);
    
    // Timeline scrubber at bottom
    ImGui::Text("Timeline: ");
    ImGui::SameLine();
    static float timelineTime = 0.0f;
    float maxTime = m_animationState.animationParams.useTimeline ? 
                   m_animationState.animationParams.timelineDuration : 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
    
    if (ImGui::SliderFloat("##Timeline", &timelineTime, 0.0f, maxTime, "%.3f")) {
        m_animationState.previewTime = timelineTime;
    }
    
    // Status bar
    renderAnimationStatusBar(imgui);
}

void ImageGenerator::renderTimelineEditorUI(ImGuiContext* imgui) {
    ImGui::Text("Timeline Editor");
    ImGui::Separator();
    
    // Timeline tracks
    if (ImGui::CollapsingHeader("Tracks", ImGuiTreeNodeFlags_DefaultOpen)) {
        // Morph weight track
        if (ImGui::TreeNode("Morph Weight")) {
            static float morphWeight = 0.0f;
            ImGui::SliderFloat("Weight", &morphWeight, 0.0f, 1.0f, "%.3f");
            ImGui::TreePop();
        }
        
        // Module visibility track
        if (ImGui::TreeNode("Module Visibility")) {
            static bool weaponVisible = true;
            static bool shieldVisible = true;
            static bool effectsVisible = true;
            
            ImGui::Checkbox("Weapon", &weaponVisible);
            ImGui::Checkbox("Shield", &shieldVisible);
            ImGui::Checkbox("Effects", &effectsVisible);
            
            ImGui::TreePop();
        }
        
        // LOD change track
        if (ImGui::TreeNode("LOD Changes")) {
            static int currentLOD = 0;
            ImGui::SliderInt("LOD Level", &currentLOD, 0, 3);
            ImGui::TreePop();
        }
        
        // Weapon fire track
        if (ImGui::TreeNode("Weapon Fire")) {
            static bool weaponFiring = false;
            ImGui::Checkbox("Firing", &weaponFiring);
            ImGui::TreePop();
        }
        
        // Effects track
        if (ImGui::TreeNode("Effects")) {
            static bool effectsActive = false;
            ImGui::Checkbox("Active", &effectsActive);
            ImGui::TreePop();
        }
    }
    
    // Keyframe editor
    if (ImGui::CollapsingHeader("Keyframes", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Keyframe Editor");
        // TODO: Implement keyframe editing interface
    }
    
    // Timeline scrubber
    ImGui::Text("Timeline");
    ImGui::Separator();
    
    static float timelineTime = 0.0f;
    float maxTime = m_animationState.animationParams.useTimeline ? 
                   m_animationState.animationParams.timelineDuration : 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
    
    if (ImGui::SliderFloat("Time", &timelineTime, 0.0f, maxTime, "%.3f")) {
        m_animationState.previewTime = timelineTime;
    }
    
    // Playback controls
    ImGui::SameLine();
    if (ImGui::Button("Play")) {
        startAnimationPreview();
    }
    
    ImGui::SameLine();
    if (ImGui::Button("Stop")) {
        stopAnimationPreview();
    }
    
    ImGui::SameLine();
    if (ImGui::Button("Reset")) {
        timelineTime = 0.0f;
        m_animationState.previewTime = 0.0f;
    }
}

void ImageGenerator::renderAnimationPreviewUI(ImGuiContext* imgui) {
    // Preview area
    ImGui::Text("Animation Preview");
    ImGui::Separator();
    
    // Placeholder for animation preview rendering
    ImVec2 previewSize(400, 300);
    ImGui::BeginChild("AnimationPreviewArea", previewSize, true, ImGuiWindowFlags_NoScrollbar);
    
    // Draw a placeholder rectangle
    ImVec2 minPos = ImGui::GetWindowPos();
    ImVec2 maxPos = ImVec2(minPos.x + previewSize.x, minPos.y + previewSize.y);
    ImGui::GetWindowDrawList()->AddRectFilled(minPos, maxPos, 
                                             IM_COL32(50, 50, 50, 255));
    
    // Draw preview text
    ImVec2 textPos = ImVec2(minPos.x + 10, minPos.y + 10);
    ImGui::GetWindowDrawList()->AddText(textPos, IM_COL32(255, 255, 255, 255), 
                                       "Animation Preview Area");
    
    // Draw current frame info
    std::string frameInfo = "Frame: " + std::to_string(static_cast<int>(m_animationState.previewTime / m_animationState.animationParams.frameDuration));
    ImVec2 frameTextPos = ImVec2(minPos.x + 10, minPos.y + 30);
    ImGui::GetWindowDrawList()->AddText(frameTextPos, IM_COL32(255, 255, 0, 255), 
                                       frameInfo.c_str());
    
    ImGui::EndChild();
    
    // Preview controls
    ImGui::Text("Preview Controls");
    ImGui::Separator();
    
    static float previewScale = 1.0f;
    ImGui::SliderFloat("Scale", &previewScale, 0.1f, 3.0f, "%.2f");
    
    static bool enableLooping = true;
    ImGui::Checkbox("Loop Preview", &enableLooping);
    
    static float previewSpeed = 1.0f;
    ImGui::SliderFloat("Speed", &previewSpeed, 0.1f, 5.0f, "%.2f");
}

void ImageGenerator::renderAnimationControlsUI(ImGuiContext* imgui) {
    // Animation generation controls
    ImGui::Text("Animation Generation Controls");
    ImGui::Separator();
    
    if (ImGui::Button("Start Animation Generation")) {
        startAnimationGeneration();
    }
    
    if (ImGui::Button("Stop Animation Generation")) {
        stopAnimationGeneration();
    }
    
    ImGui::SameLine();
    
    if (ImGui::Button("Clear Animation Cache")) {
        clearCache();
    }
    
    // Animation processing settings
    ImGui::Text("Animation Processing Settings");
    ImGui::Separator();
    
    static int animationProcessingQuality = m_processingQuality;
    if (ImGui::SliderInt("Processing Quality", &animationProcessingQuality, 1, 5)) {
        setProcessingQuality(animationProcessingQuality);
    }
    
    static float animationCompressionQuality = m_compressionQuality;
    if (ImGui::SliderFloat("Compression Quality", &animationCompressionQuality, 0.0f, 1.0f, "%.2f")) {
        setCompressionQuality(animationCompressionQuality);
    }
    
    static bool animationGPUAcceleration = m_gpuAccelerationEnabled;
    if (ImGui::Checkbox("GPU Acceleration", &animationGPUAcceleration)) {
        setGPUAcceleration(animationGPUAcceleration);
    }
    
    static bool animationAsyncProcessing = m_asyncProcessingEnabled;
    if (ImGui::Checkbox("Async Processing", &animationAsyncProcessing)) {
        setAsyncProcessing(animationAsyncProcessing);
    }
    
    // Animation performance metrics
    ImGui::Text("Animation Performance Metrics");
    ImGui::Separator();
    
    ImGui::Text("Total Animations: %llu", m_animationPerformanceMetrics.totalGenerations.load());
    ImGui::Text("Animation Cache Hit Rate: %.2f%%", m_animationPerformanceMetrics.getCacheHitRate() * 100.0);
    ImGui::Text("Average Animation Time: %.2f ms", m_animationPerformanceMetrics.getAverageGenerationTime());
    ImGui::Text("Animation Exports: %llu", m_animationPerformanceMetrics.animationExports.load());
    ImGui::Text("Active Animations: %llu", m_animationPerformanceMetrics.activeGenerators.load());
}

void ImageGenerator::renderAnimationStatusBar(ImGuiContext* imgui) {
    ImGui::Separator();
    
    // Status information
    std::string statusText;
    if (m_animationState.isGenerating) {
        statusText = "Generating Animation...";
    } else if (m_animationState.isPreviewing) {
        statusText = "Previewing Animation...";
    } else if (!m_lastError.empty()) {
        statusText = "Error: " + m_lastError;
    } else {
        statusText = "Animation Ready";
    }
    
    ImGui::TextColored(ImVec4(0.8f, 0.8f, 0.8f, 1.0f), "%s", statusText.c_str());
    
    // Performance info
    ImGui::SameLine(ImGui::GetWindowWidth() - 200);
    ImGui::Text("Animation Cache: %zu items", getCacheSize());
}

// NEW: Animation Generation Control Functions
void ImageGenerator::startAnimationGeneration() {
    if (m_animationState.isGenerating) return;
    
    m_animationState.isGenerating = true;
    m_animationState.generationProgress = 0.0f;
    m_animationCV.notify_one();
}

void ImageGenerator::stopAnimationGeneration() {
    m_animationState.isGenerating = false;
    m_animationState.generationProgress = 0.0f;
}

void ImageGenerator::startAnimationPreview() {
    if (m_animationState.isPreviewing) return;
    
    m_animationState.isPreviewing = true;
    m_animationCV.notify_one();
}

void ImageGenerator::stopAnimationPreview() {
    m_animationState.isPreviewing = false;
}

// NEW: Animation Processing Functions
AnimationBundle ImageGenerator::generateAnimation(const AnimationParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        AnimationBundle cachedBundle;
        if (m_cachingEnabled && getCachedAnimation(hash, cachedBundle)) {
            m_animationPerformanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_animationPerformanceMetrics.cacheMisses++;
        m_animationPerformanceMetrics.activeGenerators++;
        
        // Generate animation
        AnimationBundle bundle = processAnimationGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheAnimation(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_animationPerformanceMetrics.totalGenerations++;
        m_animationPerformanceMetrics.totalGenerationTime += duration.count();
        m_animationPerformanceMetrics.activeGenerators--;
        m_animationPerformanceMetrics.animationExports++;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationPerformanceMetrics.activeGenerators--;
        return AnimationBundle{};
    }
}

std::vector<ImageBundle> ImageGenerator::captureAnimationFrames(const AnimationParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        m_animationPerformanceMetrics.activeGenerators++;
        
        // Capture animation frames
        std::vector<ImageBundle> frames = processAnimationFrameCapture(params);
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        m_animationPerformanceMetrics.totalGenerations++;
        m_animationPerformanceMetrics.totalGenerationTime += duration.count();
        m_animationPerformanceMetrics.activeGenerators--;
        
        return frames;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationPerformanceMetrics.activeGenerators--;
        return std::vector<ImageBundle>{};
    }
}

// NEW: Animation Processing Helper Functions
AnimationBundle ImageGenerator::processAnimationGeneration(const AnimationParams& params) {
    // Capture animation frames
    std::vector<ImageBundle> frames = processAnimationFrameCapture(params);
    
    // Create spritesheet from frames
    SpritesheetParams spParams = m_animationState.spritesheetParams;
    spParams.columns = static_cast<int>(std::sqrt(params.frameCount));
    spParams.rows = (params.frameCount + spParams.columns - 1) / spParams.columns;
    
    SpritesheetBundle spritesheet = processSpritesheetGeneration(spParams);
    
    // Create animation bundle
    AnimationBundle bundle;
    bundle.spritesheet = spritesheet;
    bundle.starboundMetadata = processStarboundMetadata(params);
    bundle.timeline = params.timeline;
    
    // Generate frame data
    bundle.frameTimes = AnimationUtils::generateFrameTimes(params.frameCount, params.frameDuration);
    bundle.frameIndices = AnimationUtils::generateFrameIndices(params.frameCount, params.frameOrder, spParams.columns, spParams.rows);
    
    // Set file paths
    bundle.animationJsonPath = params.id + ".animation";
    bundle.spritesheetPath = params.id + "_anim.png";
    
    return bundle;
}

std::vector<ImageBundle> ImageGenerator::processAnimationFrameCapture(const AnimationParams& params) {
    std::vector<ImageBundle> frames;
    frames.reserve(params.frameCount);
    
    // Get current pipeline
    IPipeline* pipeline = m_pipelineManager ? m_pipelineManager->getCurrentPipeline() : nullptr;
    if (!pipeline) {
        m_lastError = "No pipeline loaded for animation capture";
        return frames;
    }
    
    // Enhanced tile capture for animations
    for (int i = 0; i < params.frameCount; ++i) {
        // Set animation time
        float time = i * params.frameDuration;
        
        // Update pipeline with animation time
        pipeline->SetAnimTime(time);
        
        // Evaluate timeline if enabled
        if (params.useTimeline) {
            // Evaluate timeline at this time
            float morphWeight = AnimationUtils::evaluateTimeline(params.timeline, time, "morph_weight");
            float moduleVisibility = AnimationUtils::evaluateTimeline(params.timeline, time, "module_visibility");
            float lodLevel = AnimationUtils::evaluateTimeline(params.timeline, time, "lod_change");
            
            // Apply timeline values to pipeline
            pipeline->SetMorphWeight(morphWeight);
            pipeline->SetModuleVisibility(moduleVisibility);
            pipeline->SetLODLevel(static_cast<int>(lodLevel));
        }
        
        // Capture frame with enhanced parameters
        CaptureParams captureParams = m_animationState.captureParams;
        captureParams.width = m_animationState.spritesheetParams.tileWidth;
        captureParams.height = m_animationState.spritesheetParams.tileHeight;
        
        // Use GPU acceleration if enabled
        if (m_gpuAccelerationEnabled) {
            captureParams.gpuAccelerated = true;
        }
        
        ImageBundle frame = processFrameCapture(captureParams);
        
        // Set enhanced frame metadata
        frame.metadata.id = params.id + "_frame_" + std::to_string(i);
        frame.metadata.title = "Animation Frame " + std::to_string(i);
        frame.metadata.description = "Generated animation frame at time " + std::to_string(time);
        frame.metadata.timestamp = time;
        frame.metadata.frameIndex = i;
        
        // Add animation-specific metadata
        frame.metadata.customData["animation_time"] = time;
        frame.metadata.customData["frame_index"] = i;
        frame.metadata.customData["frame_duration"] = params.frameDuration;
        
        frames.push_back(frame);
        
        // Update progress
        float progress = static_cast<float>(i + 1) / params.frameCount;
        updateAnimationGenerationProgress(progress);
    }
    
    return frames;
}

StarboundAnimationMetadata ImageGenerator::processStarboundMetadata(const AnimationParams& params) {
    StarboundAnimationMetadata metadata;
    metadata.name = params.animationName;
    metadata.category = params.starboundCategory;
    metadata.type = params.starboundType;
    metadata.frameCount = params.frameCount;
    metadata.frameTime = params.frameDuration;
    metadata.loop = params.looping;
    metadata.sheetCols = static_cast<int>(std::sqrt(params.frameCount));
    metadata.sheetRows = (params.frameCount + metadata.sheetCols - 1) / metadata.sheetCols;
    metadata.order = (params.frameOrder == FrameOrder::ROW_MAJOR) ? "row-major" : "column-major";
    metadata.description = "Generated by MagiTech Animation Generator";
    metadata.author = "MagiTech";
    metadata.version = "1.0.0";
    metadata.creationTime = std::chrono::system_clock::now();
    
    return metadata;
}

// NEW: Animation Threading Functions
void ImageGenerator::animationThreadFunction() {
    while (m_animationThreadRunning) {
        std::unique_lock<std::mutex> lock(m_animationMutex);
        m_animationCV.wait(lock, [this] { 
            return !m_animationThreadRunning || m_animationState.isGenerating || m_animationState.isPreviewing; 
        });
        
        if (!m_animationThreadRunning) break;
        
        if (m_animationState.isGenerating) {
            processAsyncAnimationGeneration();
        }
        
        if (m_animationState.isPreviewing) {
            processAsyncAnimationPreview();
        }
    }
}

void ImageGenerator::processAsyncAnimationGeneration() {
    try {
        // Simulate animation generation progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_animationState.isGenerating) break;
            
            m_animationState.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(30));
        }
        
        // Generate animation
        AnimationBundle bundle = generateAnimation(m_animationState.animationParams);
        m_animationState.currentAnimation = bundle;
        
        m_animationState.isGenerating = false;
        m_animationState.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationState.isGenerating = false;
        m_animationState.generationProgress = 0.0f;
    }
}

void ImageGenerator::processAsyncAnimationPreview() {
    try {
        // Simulate animation preview
        float maxTime = m_animationState.animationParams.useTimeline ? 
                       m_animationState.animationParams.timelineDuration : 
                       m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
        
        while (m_animationState.isPreviewing) {
            m_animationState.previewTime += 0.016f; // ~60 FPS
            if (m_animationState.previewTime >= maxTime) {
                if (m_animationState.animationParams.looping) {
                    m_animationState.previewTime = 0.0f;
                } else {
                    m_animationState.isPreviewing = false;
                    break;
                }
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(16));
        }
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationState.isPreviewing = false;
    }
}

// NEW: Animation Cache Functions
bool ImageGenerator::getCachedAnimation(uint64_t hash, AnimationBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_animationCache.find(hash);
    if (it != m_animationCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

void ImageGenerator::cacheAnimation(uint64_t hash, const AnimationBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_animationCache.size() >= MAX_ANIMATION_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_animationCache.erase(m_animationCache.begin());
    }
    
    m_animationCache[hash] = bundle;
}

// NEW: Animation Helper Functions
void ImageGenerator::updateAnimationGenerationProgress(float progress) {
    m_animationState.generationProgress = std::clamp(progress, 0.0f, 1.0f);
}

void ImageGenerator::updateAnimationPreviewTime(float time) {
    m_animationState.previewTime = time;
}

void ImageGenerator::handleAnimationGenerationError(const std::string& error) {
    m_lastError = "Animation Error: " + error;
    m_animationState.isGenerating = false;
    m_animationState.isPreviewing = false;
    m_animationState.generationProgress = 0.0f;
}

// NEW: Animation Validation Functions
bool ImageGenerator::validateAnimationFrameCount(int frameCount) {
    return frameCount > 0 && frameCount <= 1000;
}

bool ImageGenerator::validateAnimationDuration(float duration) {
    return duration > 0.0f && duration <= 60.0f;
}

bool ImageGenerator::validateTimelineKeyframes(const std::vector<TimelineKeyframe>& keyframes) {
    if (keyframes.empty()) return true;
    
    // Check for valid time ordering
    for (size_t i = 1; i < keyframes.size(); ++i) {
        if (keyframes[i].time < keyframes[i-1].time) {
            return false;
        }
    }
    
    return true;
}

// NEW: Animation Utility Functions
std::string ImageGenerator::getAnimationModeString(AnimationMode mode) const {
    switch (mode) {
        case AnimationMode::SINGLE_FRAME: return "Single Frame";
        case AnimationMode::ANIMATED_SEQUENCE: return "Animated Sequence";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getFrameOrderString(FrameOrder order) const {
    switch (order) {
        case FrameOrder::ROW_MAJOR: return "Row-Major";
        case FrameOrder::COLUMN_MAJOR: return "Column-Major";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getTimelineTrackTypeString(TimelineTrackType type) const {
    switch (type) {
        case TimelineTrackType::MORPH_WEIGHT: return "Morph Weight";
        case TimelineTrackType::MODULE_VISIBILITY: return "Module Visibility";
        case TimelineTrackType::LOD_CHANGE: return "LOD Change";
        case TimelineTrackType::WEAPON_FIRE: return "Weapon Fire";
        case TimelineTrackType::EFFECTS: return "Effects";
        case TimelineTrackType::CUSTOM: return "Custom";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getAnimationExportFormatString(AnimationExportFormat format) const {
    switch (format) {
        case AnimationExportFormat::STARBOUND_ANIMATION: return "Starbound Animation";
        case AnimationExportFormat::GENERIC_JSON: return "Generic JSON";
        case AnimationExportFormat::CUSTOM_FORMAT: return "Custom Format";
        default: return "Unknown";
    }
}

// NEW: Animation Performance Helper Functions
void ImageGenerator::updateAnimationPerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage) {
    m_animationPerformanceMetrics.totalGenerationTime += generationTime;
    m_animationPerformanceMetrics.peakMemoryUsage = std::max(m_animationPerformanceMetrics.peakMemoryUsage.load(), memoryUsage);
}

void ImageGenerator::logAnimationPerformanceMetrics() {
    // TODO: Implement animation performance logging
}

// NEW: Animation Quality Assessment Functions
AnimationQualityMetrics ImageGenerator::assessAnimationQuality(const AnimationBundle& bundle) {
    // TODO: Implement animation quality assessment
    AnimationQualityMetrics metrics;
    return metrics;
}

bool ImageGenerator::validateAnimationParams(const AnimationParams& params, std::string& errorMessage) {
    if (!validateAnimationFrameCount(params.frameCount)) {
        errorMessage = "Invalid animation frame count";
        return false;
    }
    
    if (!validateAnimationDuration(params.frameDuration)) {
        errorMessage = "Invalid animation frame duration";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Animation ID cannot be empty";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateTimelineData(const AnimationTimeline& timeline, std::string& errorMessage) {
    if (!validateTimelineKeyframes(timeline.keyframes)) {
        errorMessage = "Invalid timeline keyframes";
        return false;
    }
    
    if (timeline.duration <= 0.0f) {
        errorMessage = "Invalid timeline duration";
        return false;
    }
    
    return true;
}

// NEW: Animation File Operation Functions
bool ImageGenerator::saveAnimation(const AnimationBundle& bundle, const std::string& filePath) {
    // TODO: Implement animation saving
    return true;
}

bool ImageGenerator::loadAnimation(const std::string& filePath, AnimationBundle& bundle) {
    // TODO: Implement animation loading
    return true;
}

bool ImageGenerator::exportAnimationJSON(const AnimationBundle& bundle, const std::string& outputPath) {
    try {
        // Create output directory if it doesn't exist
        std::filesystem::path outputDir = std::filesystem::path(outputPath).parent_path();
        if (!std::filesystem::exists(outputDir)) {
            std::filesystem::create_directories(outputDir);
        }
        
        // Generate Starbound animation JSON
        nlohmann::json animationJson;
        
        // Frame indices array
        animationJson["frames"] = nlohmann::json::array();
        for (int i = 0; i < bundle.starboundMetadata.frameCount; ++i) {
            animationJson["frames"].push_back(i);
        }
        
        // Frame timing
        animationJson["frameTime"] = bundle.starboundMetadata.frameTime;
        animationJson["loop"] = bundle.starboundMetadata.loop;
        
        // Optional sheet layout information for mod tools
        animationJson["sheetCols"] = bundle.starboundMetadata.sheetCols;
        animationJson["sheetRows"] = bundle.starboundMetadata.sheetRows;
        animationJson["order"] = bundle.starboundMetadata.order;
        
        // Additional metadata
        animationJson["name"] = bundle.starboundMetadata.name;
        animationJson["category"] = bundle.starboundMetadata.category;
        animationJson["type"] = bundle.starboundMetadata.type;
        animationJson["description"] = bundle.starboundMetadata.description;
        animationJson["author"] = bundle.starboundMetadata.author;
        animationJson["version"] = bundle.starboundMetadata.version;
        
        // Timeline data if available
        if (!bundle.timeline.keyframes.empty()) {
            nlohmann::json timelineJson;
            timelineJson["duration"] = bundle.timeline.duration;
            timelineJson["looping"] = bundle.timeline.looping;
            timelineJson["frameRate"] = bundle.timeline.frameRate;
            
            // Keyframes
            timelineJson["keyframes"] = nlohmann::json::array();
            for (const auto& keyframe : bundle.timeline.keyframes) {
                nlohmann::json kfJson;
                kfJson["time"] = keyframe.time;
                kfJson["trackName"] = keyframe.trackName;
                kfJson["trackType"] = static_cast<int>(keyframe.trackType);
                kfJson["interpolation"] = keyframe.interpolation;
                
                // Handle different value types
                if (keyframe.value.type() == typeid(float)) {
                    kfJson["value"] = std::any_cast<float>(keyframe.value);
                } else if (keyframe.value.type() == typeid(int)) {
                    kfJson["value"] = std::any_cast<int>(keyframe.value);
                } else if (keyframe.value.type() == typeid(bool)) {
                    kfJson["value"] = std::any_cast<bool>(keyframe.value);
                } else if (keyframe.value.type() == typeid(std::string)) {
                    kfJson["value"] = std::any_cast<std::string>(keyframe.value);
                }
                
                timelineJson["keyframes"].push_back(kfJson);
            }
            
            animationJson["timeline"] = timelineJson;
        }
        
        // Write JSON file
        std::ofstream jsonFile(outputPath);
        if (!jsonFile.is_open()) {
            m_lastError = "Failed to open output file: " + outputPath;
            return false;
        }
        
        jsonFile << animationJson.dump(2);
        jsonFile.close();
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Export failed: " + std::string(e.what());
        return false;
    }
}

// NEW: Animation Export Functions
bool ImageGenerator::exportStarboundAnimation(const AnimationParams& params, const std::string& outputPath) {
    try {
        // Generate animation bundle
        AnimationBundle bundle = generateAnimation(params);
        
        // Create output directory if it doesn't exist
        std::filesystem::path outputDir = std::filesystem::path(outputPath).parent_path();
        if (!std::filesystem::exists(outputDir)) {
            std::filesystem::create_directories(outputDir);
        }
        
        // Generate Starbound animation JSON
        nlohmann::json animationJson;
        
        // Frame indices array
        animationJson["frames"] = nlohmann::json::array();
        for (int i = 0; i < params.frameCount; ++i) {
            animationJson["frames"].push_back(i);
        }
        
        // Frame timing
        animationJson["frameTime"] = params.frameDuration;
        animationJson["loop"] = params.looping;
        
        // Optional sheet layout information for mod tools
        animationJson["sheetCols"] = bundle.starboundMetadata.sheetCols;
        animationJson["sheetRows"] = bundle.starboundMetadata.sheetRows;
        animationJson["order"] = bundle.starboundMetadata.order;
        
        // Additional metadata
        animationJson["name"] = params.animationName;
        animationJson["category"] = params.starboundCategory;
        animationJson["type"] = params.starboundType;
        animationJson["description"] = bundle.starboundMetadata.description;
        animationJson["author"] = bundle.starboundMetadata.author;
        animationJson["version"] = bundle.starboundMetadata.version;
        
        // Write JSON file
        std::ofstream jsonFile(outputPath);
        if (!jsonFile.is_open()) {
            m_lastError = "Failed to open output file: " + outputPath;
            return false;
        }
        
        jsonFile << animationJson.dump(2);
        jsonFile.close();
        
        // Save spritesheet if it exists
        if (!bundle.spritesheet.individualFrames.empty()) {
            std::string sheetPath = outputPath.substr(0, outputPath.find_last_of('.')) + "_sheet.png";
            
            // Assemble spritesheet from frames
            SpritesheetParams spParams = m_animationState.spritesheetParams;
            spParams.columns = bundle.starboundMetadata.sheetCols;
            spParams.rows = bundle.starboundMetadata.sheetRows;
            
            SpritesheetBundle sheetBundle = processSpritesheetGeneration(spParams);
            
            // Save spritesheet
            if (!saveSpritesheet(sheetBundle, sheetPath)) {
                m_lastError = "Failed to save spritesheet: " + sheetPath;
                return false;
            }
        }
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Export failed: " + std::string(e.what());
        return false;
    }
}

bool ImageGenerator::exportAnimationFrames(const AnimationBundle& bundle, const std::string& outputDir) {
    // TODO: Implement individual frame export
    return true;
}

bool ImageGenerator::exportTimelineData(const AnimationBundle& bundle, const std::string& outputPath) {
    // TODO: Implement timeline data export
    return true;
}

// NEW: Animation Utility Helper Functions
std::string ImageGenerator::generateAnimationID() const {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    return "anim_" + std::to_string(millis);
}

std::string ImageGenerator::sanitizeAnimationFilename(const std::string& filename) const {
    std::string sanitized = filename;
    const std::string invalidChars = "<>:\"|?*";
    
    for (char& c : sanitized) {
        if (invalidChars.find(c) != std::string::npos) {
            c = '_';
        }
    }
    
    return sanitized;
}

std::string ImageGenerator::getAnimationTimestampString() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
    return oss.str();
}

// NEW: Enhanced Tile Capture & Assembly Function
std::vector<ImageBundle> ImageGenerator::CaptureTiles(
    IPipeline& pipeline, RenderContext& ctx,
    bool animMode, int frameCount, float frameDuration,
    int tileW, int tileH, int pad, int orderIdx
) {
    std::vector<ImageBundle> tiles;
    int total = animMode ? frameCount : 1;
    
    for (int i = 0; i < total; ++i) {
        if (animMode) {
            float t = i * frameDuration;
            pipeline.SetAnimTime(t);
        }
        
        // Capture frame with specified dimensions
        CaptureParams captureParams;
        captureParams.width = tileW;
        captureParams.height = tileH;
        captureParams.padding = pad;
        captureParams.gpuAccelerated = m_gpuAccelerationEnabled;
        
        ImageBundle tile = processFrameCapture(captureParams);
        
        // Set tile metadata
        tile.metadata.id = "tile_" + std::to_string(i);
        tile.metadata.title = "Animation Tile " + std::to_string(i);
        tile.metadata.description = "Generated animation tile";
        tile.metadata.frameIndex = i;
        
        if (animMode) {
            tile.metadata.timestamp = i * frameDuration;
            tile.metadata.customData["animation_time"] = i * frameDuration;
        }
        
        tiles.push_back(tile);
        
        // Update progress
        float progress = static_cast<float>(i + 1) / total;
        updateAnimationGenerationProgress(progress);
    }
    
    return tiles;
}

// NEW: Image Assembly Function for Sprite Sheets
SpritesheetBundle ImageGenerator::MakeSheet(
    const std::vector<ImageBundle>& tiles,
    int cols, int rows, int tileW, int tileH, int padding
) {
    SpritesheetBundle sheet;
    
    // Calculate sheet dimensions
    int sheetWidth = cols * (tileW + padding) - padding;
    int sheetHeight = rows * (tileH + padding) - padding;
    
    // Create sheet image
    ImageBundle sheetImage;
    sheetImage.image.width = sheetWidth;
    sheetImage.image.height = sheetHeight;
    sheetImage.image.channels = 4; // RGBA
    sheetImage.image.data.resize(sheetWidth * sheetHeight * 4);
    
    // Fill with transparent background
    std::fill(sheetImage.image.data.begin(), sheetImage.image.data.end(), 0);
    
    // Place tiles in sheet
    for (int i = 0; i < tiles.size() && i < cols * rows; ++i) {
        int row = i / cols;
        int col = i % cols;
        
        int x = col * (tileW + padding);
        int y = row * (tileH + padding);
        
        // Copy tile data to sheet
        const auto& tile = tiles[i];
        for (int ty = 0; ty < tileH && y + ty < sheetHeight; ++ty) {
            for (int tx = 0; tx < tileW && x + tx < sheetWidth; ++tx) {
                int tileIdx = (ty * tileW + tx) * 4;
                int sheetIdx = ((y + ty) * sheetWidth + (x + tx)) * 4;
                
                if (tileIdx < tile.image.data.size() && sheetIdx < sheetImage.image.data.size()) {
                    sheetImage.image.data[sheetIdx + 0] = tile.image.data[tileIdx + 0]; // R
                    sheetImage.image.data[sheetIdx + 1] = tile.image.data[tileIdx + 1]; // G
                    sheetImage.image.data[sheetIdx + 2] = tile.image.data[tileIdx + 2]; // B
                    sheetImage.image.data[sheetIdx + 3] = tile.image.data[tileIdx + 3]; // A
                }
            }
        }
    }
    
    // Set sheet metadata
    sheet.combinedImage = sheetImage;
    sheet.individualFrames = tiles;
    sheet.metadata.id = "animation_sheet";
    sheet.metadata.title = "Animation Sprite Sheet";
    sheet.metadata.description = "Generated animation sprite sheet";
    sheet.metadata.columns = cols;
    sheet.metadata.rows = rows;
    sheet.metadata.tileWidth = tileW;
    sheet.metadata.tileHeight = tileH;
    sheet.metadata.padding = padding;
    
    return sheet;
}

// NEW: Starbound Animation JSON Generator
void ImageGenerator::WriteStarboundAnimationJSON(
    const std::string& path,
    int frameCount,
    float frameDuration,
    int cols, int rows,
    int orderIdx
) {
    nlohmann::json j;
    
    // Frame indices array
    j["frames"] = nlohmann::json::array();
    for (int i = 0; i < frameCount; ++i) {
        j["frames"].push_back(i);
    }
    
    // Frame timing
    j["frameTime"] = frameDuration;
    j["loop"] = true;
    
    // Optional sheet layout information for mod tools
    j["sheetCols"] = cols;
    j["sheetRows"] = rows;
    j["order"] = orderIdx == 0 ? "row-major" : "column-major";
    
    // Additional metadata
    j["name"] = "Generated Animation";
    j["category"] = "mech";
    j["type"] = "animation";
    j["description"] = "Generated by MagiTech Animation Generator";
    j["author"] = "MagiTech";
    j["version"] = "1.0.0";
    
    // Write JSON file
    std::ofstream out(path);
    if (out.is_open()) {
        out << j.dump(2);
        out.close();
    }
}

// NEW: PipelineFactory Implementation
PipelineFactory& PipelineFactory::getInstance() {
    static PipelineFactory instance;
    return instance;
}

void PipelineFactory::registerPipeline(const std::string& name, PipelineCreator creator) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators[name] = creator;
}

void PipelineFactory::unregisterPipeline(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators.erase(name);
}

std::unique_ptr<IPipeline> PipelineFactory::createPipeline(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_creators.find(name);
    if (it != m_creators.end()) {
        return it->second();
    }
    return nullptr;
}

std::vector<std::string> PipelineFactory::getAvailablePipelines() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    std::vector<std::string> names;
    for (const auto& pair : m_creators) {
        names.push_back(pair.first);
    }
    return names;
}

std::unique_ptr<IPipeline> PipelineFactory::loadPipelineFromConfig(const std::string& configPath) {
    try {
        std::ifstream file(configPath);
        if (!file.is_open()) {
            return nullptr;
        }
        
        nlohmann::json config;
        file >> config;
        
        std::string pipelineType = config.value("pipeline_type", "");
        if (pipelineType.empty()) {
            return nullptr;
        }
        
        auto pipeline = createPipeline(pipelineType);
        if (pipeline) {
            // Load pipeline-specific configuration
            if (config.contains("parameters")) {
                for (const auto& [key, value] : config["parameters"].items()) {
                    if (value.is_number()) {
                        pipeline->SetParameter(key, value.get<double>());
                    } else if (value.is_string()) {
                        pipeline->SetParameter(key, value.get<std::string>());
                    } else if (value.is_boolean()) {
                        pipeline->SetParameter(key, value.get<bool>());
                    }
                }
            }
        }
        
        return pipeline;
        
    } catch (const std::exception& e) {
        return nullptr;
    }
}

// NEW: PipelineManager Implementation
PipelineManager::PipelineManager() {
    // Initialize with default pipeline if available
}

PipelineManager::~PipelineManager() {
    unloadCurrentPipeline();
}

bool PipelineManager::loadPipeline(const std::string& name) {
    auto pipeline = PipelineFactory::getInstance().createPipeline(name);
    if (pipeline && pipeline->initialize()) {
        m_currentPipeline = std::move(pipeline);
        m_currentPipelineName = name;
        return true;
    }
    return false;
}

bool PipelineManager::switchPipeline(const std::string& name) {
    if (m_currentPipelineName == name) {
        return true; // Already loaded
    }
    
    unloadCurrentPipeline();
    return loadPipeline(name);
}

void PipelineManager::unloadCurrentPipeline() {
    if (m_currentPipeline) {
        m_currentPipeline->shutdown();
        m_currentPipeline.reset();
        m_currentPipelineName.clear();
    }
}

std::vector<std::string> PipelineManager::getAvailablePipelines() const {
    return PipelineFactory::getInstance().getAvailablePipelines();
}

bool PipelineManager::savePipelineConfig(const std::string& configPath) const {
    try {
        nlohmann::json config;
        config["pipeline_type"] = m_currentPipelineName;
        config["pipeline_name"] = m_currentPipeline ? m_currentPipeline->GetName() : "";
        config["pipeline_version"] = m_currentPipeline ? m_currentPipeline->GetVersion() : "";
        
        // Save pipeline parameters
        if (m_currentPipeline) {
            nlohmann::json params;
            for (const auto& paramName : m_currentPipeline->GetSupportedParameters()) {
                auto value = m_currentPipeline->GetParameter(paramName);
                if (value.has_value()) {
                    if (value.type() == typeid(float)) {
                        params[paramName] = std::any_cast<float>(value);
                    } else if (value.type() == typeid(int)) {
                        params[paramName] = std::any_cast<int>(value);
                    } else if (value.type() == typeid(bool)) {
                        params[paramName] = std::any_cast<bool>(value);
                    } else if (value.type() == typeid(std::string)) {
                        params[paramName] = std::any_cast<std::string>(value);
                    }
                }
            }
            config["parameters"] = params;
        }
        
        // Save custom configuration
        config["custom_config"] = m_pipelineConfig;
        
        std::ofstream file(configPath);
        file << config.dump(2);
        return true;
        
    } catch (const std::exception& e) {
        return false;
    }
}

bool PipelineManager::loadPipelineConfig(const std::string& configPath) {
    auto pipeline = PipelineFactory::getInstance().loadPipelineFromConfig(configPath);
    if (pipeline) {
        m_currentPipeline = std::move(pipeline);
        return true;
    }
    return false;
}

// NEW: Dynamic Pipeline Management Functions
bool ImageGenerator::loadPipeline(const std::string& pipelineName) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->loadPipeline(pipelineName);
}

bool ImageGenerator::switchPipeline(const std::string& pipelineName) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->switchPipeline(pipelineName);
}

void ImageGenerator::unloadCurrentPipeline() {
    if (m_pipelineManager) {
        m_pipelineManager->unloadCurrentPipeline();
    }
}

std::vector<std::string> ImageGenerator::getAvailablePipelines() const {
    if (!m_pipelineManager) {
        return {};
    }
    return m_pipelineManager->getAvailablePipelines();
}

std::string ImageGenerator::getCurrentPipelineName() const {
    if (!m_pipelineManager) {
        return "";
    }
    return m_pipelineManager->getCurrentPipelineName();
}

bool ImageGenerator::isPipelineLoaded() const {
    if (!m_pipelineManager) {
        return false;
    }
    return m_pipelineManager->isPipelineLoaded();
}

bool ImageGenerator::savePipelineConfig(const std::string& configPath) const {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->savePipelineConfig(configPath);
}

bool ImageGenerator::loadPipelineConfig(const std::string& configPath) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->loadPipelineConfig(configPath);
}

bool ImageGenerator::setPipelineParameter(const std::string& name, const std::any& value) {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        m_lastError = "No pipeline loaded";
        return false;
    }
    
    m_pipelineManager->getCurrentPipeline()->SetParameter(name, value);
    return true;
}

std::any ImageGenerator::getPipelineParameter(const std::string& name) const {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        return std::any{};
    }
    
    return m_pipelineManager->getCurrentPipeline()->GetParameter(name);
}

std::vector<std::string> ImageGenerator::getPipelineSupportedParameters() const {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        return {};
    }
    
    return m_pipelineManager->getCurrentPipeline()->GetSupportedParameters();
}

// NEW: Example MechPipeline Implementation
class MechPipeline : public IPipeline {
public:
    MechPipeline() : m_initialized(false), m_animTime(0.0f), m_morphWeight(0.0f), 
                    m_moduleVisibility(1.0f), m_lodLevel(0), m_weaponFiring(false), 
                    m_effectsActive(false) {}
    
    ~MechPipeline() {
        shutdown();
    }
    
    // Core pipeline interface
    bool initialize() override {
        m_initialized = true;
        return true;
    }
    
    void shutdown() override {
        m_initialized = false;
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    // Animation interface
    void SetAnimTime(float time) override {
        m_animTime = time;
    }
    
    void SetMorphWeight(float weight) override {
        m_morphWeight = std::clamp(weight, 0.0f, 1.0f);
    }
    
    void SetModuleVisibility(float visibility) override {
        m_moduleVisibility = std::clamp(visibility, 0.0f, 1.0f);
    }
    
    void SetLODLevel(int level) override {
        m_lodLevel = std::clamp(level, 0, 3);
    }
    
    void SetWeaponFiring(bool firing) override {
        m_weaponFiring = firing;
    }
    
    void SetEffectsActive(bool active) override {
        m_effectsActive = active;
    }
    
    // Custom parameter interface
    void SetParameter(const std::string& name, const std::any& value) override {
        m_customParams[name] = value;
    }
    
    std::any GetParameter(const std::string& name) const override {
        auto it = m_customParams.find(name);
        if (it != m_customParams.end()) {
            return it->second;
        }
        return std::any{};
    }
    
    bool HasParameter(const std::string& name) const override {
        return m_customParams.find(name) != m_customParams.end();
    }
    
    // Pipeline metadata
    std::string GetName() const override {
        return "MechPipeline";
    }
    
    std::string GetVersion() const override {
        return "1.0.0";
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {
            "anim_time", "morph_weight", "module_visibility", "lod_level",
            "weapon_firing", "effects_active", "custom_param1", "custom_param2"
        };
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {
            "idle", "walk", "run", "attack", "defend", "special"
        };
    }
    
private:
    bool m_initialized;
    float m_animTime;
    float m_morphWeight;
    float m_moduleVisibility;
    int m_lodLevel;
    bool m_weaponFiring;
    bool m_effectsActive;
    std::unordered_map<std::string, std::any> m_customParams;
};

// NEW: Example CharacterPipeline Implementation
class CharacterPipeline : public IPipeline {
public:
    CharacterPipeline() : m_initialized(false), m_animTime(0.0f), m_expression(0.0f),
                        m_pose(0.0f), m_emotion(0.0f), m_action(0.0f) {}
    
    ~CharacterPipeline() {
        shutdown();
    }
    
    // Core pipeline interface
    bool initialize() override {
        m_initialized = true;
        return true;
    }
    
    void shutdown() override {
        m_initialized = false;
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    // Animation interface (mapped to character-specific parameters)
    void SetAnimTime(float time) override {
        m_animTime = time;
    }
    
    void SetMorphWeight(float weight) override {
        m_expression = std::clamp(weight, 0.0f, 1.0f);
    }
    
    void SetModuleVisibility(float visibility) override {
        m_pose = std::clamp(visibility, 0.0f, 1.0f);
    }
    
    void SetLODLevel(int level) override {
        m_emotion = static_cast<float>(std::clamp(level, 0, 3)) / 3.0f;
    }
    
    void SetWeaponFiring(bool firing) override {
        m_action = firing ? 1.0f : 0.0f;
    }
    
    void SetEffectsActive(bool active) override {
        // Character-specific effect handling
    }
    
    // Custom parameter interface
    void SetParameter(const std::string& name, const std::any& value) override {
        m_customParams[name] = value;
    }
    
    std::any GetParameter(const std::string& name) const override {
        auto it = m_customParams.find(name);
        if (it != m_customParams.end()) {
            return it->second;
        }
        return std::any{};
    }
    
    bool HasParameter(const std::string& name) const override {
        return m_customParams.find(name) != m_customParams.end();
    }
    
    // Pipeline metadata
    std::string GetName() const override {
        return "CharacterPipeline";
    }
    
    std::string GetVersion() const override {
        return "1.0.0";
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {
            "expression", "pose", "emotion", "action", "gesture", "speech"
        };
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {
            "idle", "walk", "talk", "gesture", "emote", "action"
        };
    }
    
private:
    bool m_initialized;
    float m_animTime;
    float m_expression;
    float m_pose;
    float m_emotion;
    float m_action;
    std::unordered_map<std::string, std::any> m_customParams;
};

// NEW: Pipeline Registration Function
void registerDefaultPipelines() {
    auto& factory = PipelineFactory::getInstance();
    
    // Register MechPipeline
    factory.registerPipeline("mech", []() -> std::unique_ptr<IPipeline> {
        return std::make_unique<MechPipeline>();
    });
    
    // Register CharacterPipeline
    factory.registerPipeline("character", []() -> std::unique_ptr<IPipeline> {
        return std::make_unique<CharacterPipeline>();
    });
}

} // namespace ImageGen
} // namespace MagiTech 
