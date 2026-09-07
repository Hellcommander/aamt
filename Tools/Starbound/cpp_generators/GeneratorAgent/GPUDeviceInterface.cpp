#include "GPUDeviceInterface.hpp"
#include <unordered_map>
#include <atomic>
#include <mutex>

namespace mt::light {

// Static handle counter
std::atomic<uint32_t> GPUDeviceInterface::s_nextHandle{1000};

// Global instance
GPUDeviceInterface& g_gpuDevice = GPUDeviceInterface::getInstance();

GPUDeviceInterface& GPUDeviceInterface::getInstance() {
    static GPUDeviceInterface instance;
    return instance;
}

void GPUDeviceInterface::initialize(Star::RendererPtr renderer) {
    m_renderer = renderer;
    
    if (m_renderer) {
        // Create texture group for light textures
        m_textureGroup = m_renderer->createTextureGroup(
            Star::TextureGroupSize::Medium, 
            Star::TextureFiltering::Linear
        );
    }
}

uint32_t GPUDeviceInterface::generateHandle() {
    return s_nextHandle.fetch_add(1, std::memory_order_relaxed);
}

uint32_t GPUDeviceInterface::createTexture2D(const std::string& path, bool generateMipmaps) {
    if (!m_renderer) return 0;
    
    try {
        Star::TexturePtr texture = loadTextureFromPath(path);
        if (texture) {
            uint32_t handle = generateHandle();
            m_textures[handle] = texture;
            return handle;
        }
    } catch (const std::exception& e) {
        // Log error: failed to load texture from path
    }
    
    return 0;
}

uint32_t GPUDeviceInterface::createTexture2D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height, uint32_t channels) {
    if (!m_renderer) return 0;
    
    try {
        // Convert data to Star::Image format
        auto textureData = createTextureData(data, width, height, channels);
        
        // Create Star::Image from data
        // Note: This would need the actual Star::Image constructor
        // For now, we'll create a placeholder texture
        
        uint32_t handle = generateHandle();
        // m_textures[handle] = texture; // Would be set with actual texture
        return handle;
    } catch (const std::exception& e) {
        // Log error: failed to create texture from data
    }
    
    return 0;
}

void GPUDeviceInterface::destroyTexture(uint32_t textureHandle) {
    auto it = m_textures.find(textureHandle);
    if (it != m_textures.end()) {
        m_textures.erase(it);
    }
}

uint32_t GPUDeviceInterface::createUniformBuffer(size_t size, const void* data) {
    uint32_t handle = generateHandle();
    
    // Create buffer data
    std::vector<uint8_t> bufferData(size);
    if (data) {
        std::memcpy(bufferData.data(), data, size);
    }
    
    m_buffers[handle] = std::move(bufferData);
    return handle;
}

void GPUDeviceInterface::updateUniformBuffer(uint32_t bufferHandle, const void* data, size_t size, size_t offset) {
    auto it = m_buffers.find(bufferHandle);
    if (it != m_buffers.end()) {
        if (offset + size <= it->second.size()) {
            std::memcpy(it->second.data() + offset, data, size);
        }
    }
}

void GPUDeviceInterface::destroyBuffer(uint32_t bufferHandle) {
    m_buffers.erase(bufferHandle);
}

uint32_t GPUDeviceInterface::createSampler(bool linearFiltering, bool clampToEdge) {
    uint32_t handle = generateHandle();
    
    // Create sampler configuration string
    std::string config = "linear:" + std::to_string(linearFiltering) + 
                        ",clamp:" + std::to_string(clampToEdge);
    
    m_samplers[handle] = config;
    return handle;
}

void GPUDeviceInterface::destroySampler(uint32_t samplerHandle) {
    m_samplers.erase(samplerHandle);
}

uint32_t GPUDeviceInterface::createDescriptorSet(uint32_t uboHandle, uint32_t shadowMapHandle, 
                                                uint32_t cookieTextureHandle, uint32_t volumetricTextureHandle) {
    uint32_t handle = generateHandle();
    
    // Store descriptor set configuration
    m_descriptorSets[handle] = std::make_tuple(uboHandle, shadowMapHandle, cookieTextureHandle, volumetricTextureHandle);
    
    return handle;
}

void GPUDeviceInterface::destroyDescriptorSet(uint32_t descriptorSetHandle) {
    m_descriptorSets.erase(descriptorSetHandle);
}

uint32_t GPUDeviceInterface::createGraphicsPipeline(const std::string& vertexShader, const std::string& fragmentShader) {
    uint32_t handle = generateHandle();
    
    // Store pipeline configuration
    std::string config = "vertex:" + vertexShader + ",fragment:" + fragmentShader;
    m_pipelines[handle] = config;
    
    return handle;
}

uint32_t GPUDeviceInterface::createComputePipeline(const std::string& computeShader) {
    uint32_t handle = generateHandle();
    
    // Store compute pipeline configuration
    std::string config = "compute:" + computeShader;
    m_pipelines[handle] = config;
    
    return handle;
}

void GPUDeviceInterface::destroyPipeline(uint32_t pipelineHandle) {
    m_pipelines.erase(pipelineHandle);
}

Star::TexturePtr GPUDeviceInterface::getTexture(uint32_t handle) const {
    auto it = m_textures.find(handle);
    return (it != m_textures.end()) ? it->second : nullptr;
}

Star::TexturePtr GPUDeviceInterface::loadTextureFromPath(const std::string& path) {
    // This would integrate with OpenStarbound's asset loading system
    // For now, return nullptr as placeholder
    return nullptr;
}

std::vector<uint8_t> GPUDeviceInterface::createTextureData(const std::vector<uint8_t>& data, 
                                                          uint32_t width, uint32_t height, uint32_t channels) {
    // Convert raw data to appropriate format for Star::Image
    // This would depend on the specific image format requirements
    return data;
}

} // namespace mt::light 
