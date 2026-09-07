#pragma once

#include "AudioAssetTypes.hpp"
#include <memory>
#include <vector>
#include <unordered_map>
#include <string>

// Forward declarations for OpenStarbound types
namespace Star {
    class Renderer;
    class Texture;
    class TextureGroup;
    using RendererPtr = std::shared_ptr<Renderer>;
    using TexturePtr = std::shared_ptr<Texture>;
    using TextureGroupPtr = std::shared_ptr<TextureGroup>;
}

namespace MagiTech {
namespace Audio {

// GPU-accelerated audio processing interface
class GPUAudioInterface {
public:
    GPUAudioInterface();
    ~GPUAudioInterface();
    
    // Initialization
    bool initialize(Star::RendererPtr renderer);
    void shutdown();
    bool isInitialized() const;
    
    // Audio buffer management
    AudioBufferHandle createAudioBuffer(const void* data, size_t size);
    bool updateAudioBuffer(AudioBufferHandle handle, const void* data, size_t size);
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
    
    // GPU processing
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
    // GPU resource tracking
    struct GPUResource {
        uint32_t handle;
        size_t size;
        std::string type;
        bool valid;
    };
    
    // Audio processing state
    struct AudioProcessingState {
        AudioBufferHandle inputBuffer;
        AudioBufferHandle outputBuffer;
        AudioPipelineHandle pipeline;
        AudioDescriptorSet descriptor;
        std::vector<float> parameters;
    };
    
    // Shader compilation
    bool compileShader(const std::string& source, const std::string& type, uint32_t& shaderHandle);
    bool linkProgram(uint32_t vertexShader, uint32_t fragmentShader, uint32_t& programHandle);
    bool compileComputeShader(const std::string& source, uint32_t& shaderHandle);
    
    // GPU memory management
    bool allocateGPUMemory(size_t size, uint32_t& handle);
    void freeGPUMemory(uint32_t handle);
    size_t getTotalGPUMemory() const;
    
    // Audio processing shaders
    std::string generateAudioProcessingVertexShader();
    std::string generateAudioProcessingFragmentShader();
    std::string generateAudioComputeShader(const std::string& effectType);
    
    // Utility functions
    uint32_t generateHandle();
    bool validateHandle(uint32_t handle) const;
    void logError(const std::string& error);
    
    // Member variables
    bool m_initialized;
    Star::RendererPtr m_renderer;
    Star::TextureGroupPtr m_textureGroup;
    
    // Resource tracking
    std::unordered_map<uint32_t, GPUResource> m_buffers;
    std::unordered_map<uint32_t, GPUResource> m_textures;
    std::unordered_map<uint32_t, GPUResource> m_pipelines;
    std::unordered_map<uint32_t, GPUResource> m_descriptorSets;
    
    // Performance tracking
    uint64_t m_gpuMemoryUsage;
    float m_gpuUtilization;
    uint64_t m_processedSamples;
    uint64_t m_processingTimeMs;
    
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
