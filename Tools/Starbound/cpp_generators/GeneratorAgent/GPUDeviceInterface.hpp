#pragma once

#include "LightTypes.hpp"
#include <memory>
#include <string>
#include <vector>

// Forward declarations for OpenStarbound renderer
namespace Star {
    class Renderer;
    class Texture;
    class TextureGroup;
    class RenderBuffer;
    typedef std::shared_ptr<Renderer> RendererPtr;
    typedef std::shared_ptr<Texture> TexturePtr;
    typedef std::shared_ptr<TextureGroup> TextureGroupPtr;
    typedef std::shared_ptr<RenderBuffer> RenderBufferPtr;
}

namespace mt::light {

// GPU resource handles that map to OpenStarbound types
using LightHandle        = uint32_t;
using GpuDescriptorSet   = uint32_t;
using GpuBuffer          = uint32_t;
using GpuComputePipeline = uint32_t;
using GpuPipeline        = uint32_t;

// GPU device interface that integrates with OpenStarbound's Star renderer
class GPUDeviceInterface {
public:
    static GPUDeviceInterface& getInstance();
    
    // Initialize with OpenStarbound renderer
    void initialize(Star::RendererPtr renderer);
    bool isInitialized() const { return m_renderer != nullptr; }
    
    // Texture operations
    uint32_t createTexture2D(const std::string& path, bool generateMipmaps = true);
    uint32_t createTexture2D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height, uint32_t channels);
    void destroyTexture(uint32_t textureHandle);
    
    // Buffer operations
    uint32_t createUniformBuffer(size_t size, const void* data = nullptr);
    void updateUniformBuffer(uint32_t bufferHandle, const void* data, size_t size, size_t offset = 0);
    void destroyBuffer(uint32_t bufferHandle);
    
    // Sampler operations
    uint32_t createSampler(bool linearFiltering = true, bool clampToEdge = true);
    void destroySampler(uint32_t samplerHandle);
    
    // Descriptor set operations
    uint32_t createDescriptorSet(uint32_t uboHandle, uint32_t shadowMapHandle, uint32_t cookieTextureHandle, uint32_t volumetricTextureHandle);
    void destroyDescriptorSet(uint32_t descriptorSetHandle);
    
    // Pipeline operations
    uint32_t createGraphicsPipeline(const std::string& vertexShader, const std::string& fragmentShader);
    uint32_t createComputePipeline(const std::string& computeShader);
    void destroyPipeline(uint32_t pipelineHandle);
    
    // Utility functions
    Star::RendererPtr getRenderer() const { return m_renderer; }
    Star::TexturePtr getTexture(uint32_t handle) const;
    Star::TextureGroupPtr getTextureGroup() const { return m_textureGroup; }
    
private:
    GPUDeviceInterface() = default;
    ~GPUDeviceInterface() = default;
    
    // OpenStarbound integration
    Star::RendererPtr m_renderer;
    Star::TextureGroupPtr m_textureGroup;
    
    // Resource tracking
    std::unordered_map<uint32_t, Star::TexturePtr> m_textures;
    std::unordered_map<uint32_t, std::vector<uint8_t>> m_buffers;
    std::unordered_map<uint32_t, std::string> m_samplers;
    std::unordered_map<uint32_t, std::tuple<uint32_t, uint32_t, uint32_t, uint32_t>> m_descriptorSets;
    std::unordered_map<uint32_t, std::string> m_pipelines;
    
    // Handle generation
    static uint32_t generateHandle();
    static std::atomic<uint32_t> s_nextHandle;
    
    // Helper functions
    Star::TexturePtr loadTextureFromPath(const std::string& path);
    std::vector<uint8_t> createTextureData(const std::vector<uint8_t>& data, uint32_t width, uint32_t height, uint32_t channels);
};

// Global GPU device interface instance
extern GPUDeviceInterface& g_gpuDevice;

} // namespace mt::light 
