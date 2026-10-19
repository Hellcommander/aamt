#pragma once

#include "AudioAssetTypes.hpp"
#include "core/render/IRenderDevice.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <vector>
#include <unordered_map>
#include <string>

namespace MagiTech {
namespace Audio {

// Audio "GPU" resource interface.
//
// Resources (buffers, textures, pipelines, descriptor sets) are owned and processed
// host-side: buffer contents live in system memory and compute pipelines execute their
// audio kernels on the CPU, so the interface works without any graphics API. When an
// IRenderDevice is supplied, audio textures (e.g. waveform / spectrogram views) and
// raster pipelines are additionally mirrored to that device for rendering.
class GPUAudioInterface {
public:
    GPUAudioInterface();
    ~GPUAudioInterface();

    // Initialization (renderDevice may be null: host-only mode)
    bool initialize(std::shared_ptr<IRenderDevice> renderDevice = nullptr);
    void shutdown();
    bool isInitialized() const;

    // Audio buffer management
    AudioBufferHandle createAudioBuffer(const void* data, size_t size);
    bool updateAudioBuffer(AudioBufferHandle handle, const void* data, size_t size);
    bool readAudioBuffer(AudioBufferHandle handle, std::vector<float>& out) const;
    void destroyAudioBuffer(AudioBufferHandle handle);
    bool validateAudioBuffer(AudioBufferHandle handle) const;

    // Audio texture management (for spectrograms, etc.)
    AudioTextureHandle createAudioTexture(const float* data, size_t numSamples, uint32_t channels);
    bool updateAudioTexture(AudioTextureHandle handle, const float* data, size_t numSamples);
    void destroyAudioTexture(AudioTextureHandle handle);
    bool validateAudioTexture(AudioTextureHandle handle) const;

    // Audio processing pipelines
    AudioPipelineHandle createAudioProcessingPipeline(const std::string& vertexShader,
                                                   const std::string& fragmentShader);
    AudioPipelineHandle createAudioComputePipeline(const std::string& computeShader);
    void destroyPipeline(AudioPipelineHandle handle);

    // Descriptor set management
    AudioDescriptorSet createDescriptorSet(AudioBufferHandle buffer, AudioTextureHandle texture = 0);
    void destroyDescriptorSet(AudioDescriptorSet handle);

    // Processing
    bool processAudioOnGPU(AudioBufferHandle input, AudioBufferHandle output,
                          AudioPipelineHandle pipeline, AudioDescriptorSet descriptor);
    bool applyEffectOnGPU(AudioBufferHandle buffer, const std::string& effectType,
                         const std::vector<float>& parameters);

    // Performance monitoring
    uint64_t getGPUMemoryUsage() const;
    float getGPUUtilization() const;
    void resetPerformanceCounters();

    // Error handling
    std::string getLastError() const;
    void clearLastError();

private:
    // Resource tracking
    struct GPUResource {
        uint32_t handle = 0;
        size_t size = 0;
        std::string type;
        bool valid = false;
        std::vector<uint8_t> data;          // buffer / texture contents
        uint32_t width = 0;                 // texture: samples per row
        uint32_t channels = 0;              // texture: rows
        uint64_t deviceHandle = 0;          // mirrored IRenderDevice resource (0 = none)
        std::string kernel;                 // compute pipeline kernel name
        std::vector<float> parameters;      // descriptor set: kernel parameters
        AudioBufferHandle buffer = 0;       // descriptor set bindings
        AudioTextureHandle texture = 0;
    };

    // Audio processing state
    struct AudioProcessingState {
        AudioBufferHandle inputBuffer = 0;
        AudioBufferHandle outputBuffer = 0;
        AudioPipelineHandle pipeline = 0;
        AudioDescriptorSet descriptor = 0;
        std::vector<float> parameters;
    };

    // Shader compilation (validation + kernel resolution)
    bool compileShader(const std::string& source, const std::string& type, uint32_t& shaderHandle);
    bool linkProgram(uint32_t vertexShader, uint32_t fragmentShader, uint32_t& programHandle);
    bool compileComputeShader(const std::string& source, uint32_t& shaderHandle);

    // Memory management
    bool allocateGPUMemory(size_t size, uint32_t& handle);
    void freeGPUMemory(uint32_t handle);
    size_t getTotalGPUMemory() const;

    // Audio processing shaders
    std::string generateAudioProcessingVertexShader();
    std::string generateAudioProcessingFragmentShader();
    std::string generateAudioComputeShader(const std::string& effectType);

    // Kernel execution
    bool runKernel(const std::string& kernel, const std::vector<float>& input, std::vector<float>& output,
                   const std::vector<float>& parameters);
    std::vector<uint8_t> textureBytes(const float* data, size_t numSamples, uint32_t channels) const;

    // Utility functions
    uint32_t generateHandle();
    bool validateHandle(uint32_t handle) const;
    void logError(const std::string& error);

    // Member variables
    bool m_initialized;
    std::shared_ptr<IRenderDevice> m_renderDevice;
    mutable std::recursive_mutex m_mutex;

    // Resource tracking
    std::unordered_map<uint32_t, GPUResource> m_buffers;
    std::unordered_map<uint32_t, GPUResource> m_textures;
    std::unordered_map<uint32_t, GPUResource> m_pipelines;
    std::unordered_map<uint32_t, GPUResource> m_descriptorSets;
    std::unordered_map<uint32_t, GPUResource> m_shaders;
    std::unordered_map<uint32_t, size_t> m_allocations;

    // Performance tracking
    uint64_t m_gpuMemoryUsage;
    float m_gpuUtilization;
    uint64_t m_processedSamples;
    uint64_t m_processingTimeMs;
    double m_processingTimeSeconds = 0.0;
    std::chrono::steady_clock::time_point m_counterStart;

    // Handle generation
    uint32_t m_nextHandle;

    // Error handling
    std::string m_lastError;

    // Constants
    static constexpr size_t MAX_GPU_MEMORY = 1024 * 1024 * 1024; // 1GB
    static constexpr size_t MAX_AUDIO_BUFFER_SIZE = 1024 * 1024 * 100; // 100MB
    static constexpr uint32_t INVALID_HANDLE = 0;
};

} // namespace Audio
} // namespace MagiTech
