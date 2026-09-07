#include "GPUAudioInterface.hpp"
#include <iostream>
#include <algorithm>
#include <cmath>

namespace MagiTech {
namespace Audio {

GPUAudioInterface::GPUAudioInterface() 
    : m_initialized(false)
    , m_gpuMemoryUsage(0)
    , m_gpuUtilization(0.0f)
    , m_processedSamples(0)
    , m_processingTimeMs(0)
    , m_nextHandle(1) {
}

GPUAudioInterface::~GPUAudioInterface() {
    shutdown();
}

bool GPUAudioInterface::initialize(Star::RendererPtr renderer) {
    if (m_initialized) {
        return true;
    }
    
    if (!renderer) {
        m_lastError = "Invalid renderer pointer";
        return false;
    }
    
    m_renderer = renderer;
    
    // Create texture group for audio textures
    try {
        m_textureGroup = m_renderer->createTextureGroup("AudioTextures");
        if (!m_textureGroup) {
            m_lastError = "Failed to create audio texture group";
            return false;
        }
    } catch (const std::exception& e) {
        m_lastError = "Exception during texture group creation: " + std::string(e.what());
        return false;
    }
    
    m_initialized = true;
    m_lastError.clear();
    return true;
}

void GPUAudioInterface::shutdown() {
    if (!m_initialized) {
        return;
    }
    
    // Destroy all resources
    for (auto& [handle, resource] : m_buffers) {
        if (resource.valid) {
            destroyAudioBuffer(handle);
        }
    }
    
    for (auto& [handle, resource] : m_textures) {
        if (resource.valid) {
            destroyAudioTexture(handle);
        }
    }
    
    for (auto& [handle, resource] : m_pipelines) {
        if (resource.valid) {
            destroyPipeline(handle);
        }
    }
    
    for (auto& [handle, resource] : m_descriptorSets) {
        if (resource.valid) {
            destroyDescriptorSet(handle);
        }
    }
    
    m_buffers.clear();
    m_textures.clear();
    m_pipelines.clear();
    m_descriptorSets.clear();
    
    m_renderer.reset();
    m_textureGroup.reset();
    m_initialized = false;
}

bool GPUAudioInterface::isInitialized() const {
    return m_initialized;
}

AudioBufferHandle GPUAudioInterface::createAudioBuffer(const void* data, size_t size) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return INVALID_HANDLE;
    }
    
    if (size > MAX_AUDIO_BUFFER_SIZE) {
        m_lastError = "Audio buffer size exceeds maximum allowed size";
        return INVALID_HANDLE;
    }
    
    uint32_t handle = generateHandle();
    
    // Placeholder for actual GPU buffer creation
    // In a real implementation, this would call the renderer's buffer creation methods
    try {
        // m_renderer->createBuffer(data, size, handle);
        
        GPUResource resource;
        resource.handle = handle;
        resource.size = size;
        resource.type = "AudioBuffer";
        resource.valid = true;
        
        m_buffers[handle] = resource;
        m_gpuMemoryUsage += size;
        
        return handle;
    } catch (const std::exception& e) {
        m_lastError = "Failed to create audio buffer: " + std::string(e.what());
        return INVALID_HANDLE;
    }
}

bool GPUAudioInterface::updateAudioBuffer(AudioBufferHandle handle, const void* data, size_t size) {
    if (!validateHandle(handle)) {
        m_lastError = "Invalid audio buffer handle";
        return false;
    }
    
    auto it = m_buffers.find(handle);
    if (it == m_buffers.end() || !it->second.valid) {
        m_lastError = "Audio buffer not found or invalid";
        return false;
    }
    
    // Placeholder for actual GPU buffer update
    // In a real implementation, this would call the renderer's buffer update methods
    try {
        // m_renderer->updateBuffer(handle, data, size);
        it->second.size = size;
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Failed to update audio buffer: " + std::string(e.what());
        return false;
    }
}

void GPUAudioInterface::destroyAudioBuffer(AudioBufferHandle handle) {
    auto it = m_buffers.find(handle);
    if (it != m_buffers.end() && it->second.valid) {
        // Placeholder for actual GPU buffer destruction
        // m_renderer->destroyBuffer(handle);
        
        m_gpuMemoryUsage -= it->second.size;
        it->second.valid = false;
        m_buffers.erase(it);
    }
}

bool GPUAudioInterface::validateAudioBuffer(AudioBufferHandle handle) const {
    auto it = m_buffers.find(handle);
    return it != m_buffers.end() && it->second.valid;
}

AudioTextureHandle GPUAudioInterface::createAudioTexture(const float* data, size_t numSamples, uint32_t channels) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return INVALID_HANDLE;
    }
    
    uint32_t handle = generateHandle();
    
    // Placeholder for actual GPU texture creation
    // In a real implementation, this would call the renderer's texture creation methods
    try {
        // m_renderer->createTexture(data, numSamples, channels, handle);
        
        GPUResource resource;
        resource.handle = handle;
        resource.size = numSamples * channels * sizeof(float);
        resource.type = "AudioTexture";
        resource.valid = true;
        
        m_textures[handle] = resource;
        m_gpuMemoryUsage += resource.size;
        
        return handle;
    } catch (const std::exception& e) {
        m_lastError = "Failed to create audio texture: " + std::string(e.what());
        return INVALID_HANDLE;
    }
}

bool GPUAudioInterface::updateAudioTexture(AudioTextureHandle handle, const float* data, size_t numSamples) {
    if (!validateHandle(handle)) {
        m_lastError = "Invalid audio texture handle";
        return false;
    }
    
    auto it = m_textures.find(handle);
    if (it == m_textures.end() || !it->second.valid) {
        m_lastError = "Audio texture not found or invalid";
        return false;
    }
    
    // Placeholder for actual GPU texture update
    // In a real implementation, this would call the renderer's texture update methods
    try {
        // m_renderer->updateTexture(handle, data, numSamples);
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Failed to update audio texture: " + std::string(e.what());
        return false;
    }
}

void GPUAudioInterface::destroyAudioTexture(AudioTextureHandle handle) {
    auto it = m_textures.find(handle);
    if (it != m_textures.end() && it->second.valid) {
        // Placeholder for actual GPU texture destruction
        // m_renderer->destroyTexture(handle);
        
        m_gpuMemoryUsage -= it->second.size;
        it->second.valid = false;
        m_textures.erase(it);
    }
}

bool GPUAudioInterface::validateAudioTexture(AudioTextureHandle handle) const {
    auto it = m_textures.find(handle);
    return it != m_textures.end() && it->second.valid;
}

AudioPipelineHandle GPUAudioInterface::createAudioProcessingPipeline(const std::string& vertexShader, 
                                                                   const std::string& fragmentShader) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return INVALID_HANDLE;
    }
    
    uint32_t handle = generateHandle();
    
    // Placeholder for actual GPU pipeline creation
    // In a real implementation, this would compile and link the shaders
    try {
        uint32_t vertexHandle, fragmentHandle, programHandle;
        
        if (!compileShader(vertexShader, "vertex", vertexHandle)) {
            return INVALID_HANDLE;
        }
        
        if (!compileShader(fragmentShader, "fragment", fragmentHandle)) {
            return INVALID_HANDLE;
        }
        
        if (!linkProgram(vertexHandle, fragmentHandle, programHandle)) {
            return INVALID_HANDLE;
        }
        
        GPUResource resource;
        resource.handle = handle;
        resource.size = 0; // Pipeline doesn't consume GPU memory directly
        resource.type = "AudioPipeline";
        resource.valid = true;
        
        m_pipelines[handle] = resource;
        
        return handle;
    } catch (const std::exception& e) {
        m_lastError = "Failed to create audio processing pipeline: " + std::string(e.what());
        return INVALID_HANDLE;
    }
}

AudioPipelineHandle GPUAudioInterface::createAudioComputePipeline(const std::string& computeShader) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return INVALID_HANDLE;
    }
    
    uint32_t handle = generateHandle();
    
    // Placeholder for actual GPU compute pipeline creation
    try {
        uint32_t computeHandle;
        
        if (!compileComputeShader(computeShader, computeHandle)) {
            return INVALID_HANDLE;
        }
        
        GPUResource resource;
        resource.handle = handle;
        resource.size = 0;
        resource.type = "AudioComputePipeline";
        resource.valid = true;
        
        m_pipelines[handle] = resource;
        
        return handle;
    } catch (const std::exception& e) {
        m_lastError = "Failed to create audio compute pipeline: " + std::string(e.what());
        return INVALID_HANDLE;
    }
}

void GPUAudioInterface::destroyPipeline(AudioPipelineHandle handle) {
    auto it = m_pipelines.find(handle);
    if (it != m_pipelines.end() && it->second.valid) {
        // Placeholder for actual GPU pipeline destruction
        // m_renderer->destroyPipeline(handle);
        
        it->second.valid = false;
        m_pipelines.erase(it);
    }
}

AudioDescriptorSet GPUAudioInterface::createDescriptorSet(AudioBufferHandle buffer, AudioTextureHandle texture) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return INVALID_HANDLE;
    }
    
    uint32_t handle = generateHandle();
    
    // Placeholder for actual GPU descriptor set creation
    try {
        // m_renderer->createDescriptorSet(buffer, texture, handle);
        
        GPUResource resource;
        resource.handle = handle;
        resource.size = 0;
        resource.type = "AudioDescriptorSet";
        resource.valid = true;
        
        m_descriptorSets[handle] = resource;
        
        return handle;
    } catch (const std::exception& e) {
        m_lastError = "Failed to create descriptor set: " + std::string(e.what());
        return INVALID_HANDLE;
    }
}

void GPUAudioInterface::destroyDescriptorSet(AudioDescriptorSet handle) {
    auto it = m_descriptorSets.find(handle);
    if (it != m_descriptorSets.end() && it->second.valid) {
        // Placeholder for actual GPU descriptor set destruction
        // m_renderer->destroyDescriptorSet(handle);
        
        it->second.valid = false;
        m_descriptorSets.erase(it);
    }
}

bool GPUAudioInterface::processAudioOnGPU(AudioBufferHandle input, AudioBufferHandle output, 
                                        AudioPipelineHandle pipeline, AudioDescriptorSet descriptor) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return false;
    }
    
    if (!validateAudioBuffer(input) || !validateAudioBuffer(output)) {
        m_lastError = "Invalid audio buffer handles";
        return false;
    }
    
    auto pipelineIt = m_pipelines.find(pipeline);
    if (pipelineIt == m_pipelines.end() || !pipelineIt->second.valid) {
        m_lastError = "Invalid pipeline handle";
        return false;
    }
    
    auto descriptorIt = m_descriptorSets.find(descriptor);
    if (descriptorIt == m_descriptorSets.end() || !descriptorIt->second.valid) {
        m_lastError = "Invalid descriptor set handle";
        return false;
    }
    
    // Placeholder for actual GPU processing
    // In a real implementation, this would dispatch the compute shader or draw call
    try {
        // m_renderer->dispatchCompute(input, output, pipeline, descriptor);
        
        // Update performance counters
        m_processedSamples += m_buffers[input].size / sizeof(float);
        m_processingTimeMs += 1; // Placeholder timing
        
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Failed to process audio on GPU: " + std::string(e.what());
        return false;
    }
}

bool GPUAudioInterface::applyEffectOnGPU(AudioBufferHandle buffer, const std::string& effectType, 
                                       const std::vector<float>& parameters) {
    if (!m_initialized) {
        m_lastError = "GPU interface not initialized";
        return false;
    }
    
    if (!validateAudioBuffer(buffer)) {
        m_lastError = "Invalid audio buffer handle";
        return false;
    }
    
    // Placeholder for actual GPU effect application
    // In a real implementation, this would create a compute shader for the specific effect
    try {
        std::string computeShader = generateAudioComputeShader(effectType);
        AudioPipelineHandle effectPipeline = createAudioComputePipeline(computeShader);
        
        if (effectPipeline == INVALID_HANDLE) {
            return false;
        }
        
        // Apply the effect
        bool success = processAudioOnGPU(buffer, buffer, effectPipeline, 0);
        
        // Clean up
        destroyPipeline(effectPipeline);
        
        return success;
    } catch (const std::exception& e) {
        m_lastError = "Failed to apply effect on GPU: " + std::string(e.what());
        return false;
    }
}

uint64_t GPUAudioInterface::getGPUMemoryUsage() const {
    return m_gpuMemoryUsage;
}

float GPUAudioInterface::getGPUUtilization() const {
    return m_gpuUtilization;
}

void GPUAudioInterface::resetPerformanceCounters() {
    m_processedSamples = 0;
    m_processingTimeMs = 0;
    m_gpuUtilization = 0.0f;
}

std::string GPUAudioInterface::getLastError() const {
    return m_lastError;
}

void GPUAudioInterface::clearLastError() {
    m_lastError.clear();
}

// Private implementation methods

bool GPUAudioInterface::compileShader(const std::string& source, const std::string& type, uint32_t& shaderHandle) {
    // Placeholder for shader compilation
    // In a real implementation, this would use OpenGL/Vulkan shader compilation
    shaderHandle = generateHandle();
    return true;
}

bool GPUAudioInterface::linkProgram(uint32_t vertexShader, uint32_t fragmentShader, uint32_t& programHandle) {
    // Placeholder for program linking
    // In a real implementation, this would link the shaders into a program
    programHandle = generateHandle();
    return true;
}

bool GPUAudioInterface::compileComputeShader(const std::string& source, uint32_t& shaderHandle) {
    // Placeholder for compute shader compilation
    shaderHandle = generateHandle();
    return true;
}

bool GPUAudioInterface::allocateGPUMemory(size_t size, uint32_t& handle) {
    // Placeholder for GPU memory allocation
    handle = generateHandle();
    return true;
}

void GPUAudioInterface::freeGPUMemory(uint32_t handle) {
    // Placeholder for GPU memory deallocation
}

size_t GPUAudioInterface::getTotalGPUMemory() const {
    return MAX_GPU_MEMORY;
}

std::string GPUAudioInterface::generateAudioProcessingVertexShader() {
    return R"(
#version 450
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texCoord;
layout(location = 0) out vec2 fragTexCoord;

void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    fragTexCoord = texCoord;
}
)";
}

std::string GPUAudioInterface::generateAudioProcessingFragmentShader() {
    return R"(
#version 450
layout(location = 0) in vec2 fragTexCoord;
layout(location = 0) out vec4 fragColor;

layout(binding = 0) uniform sampler2D audioTexture;

void main() {
    vec4 sample = texture(audioTexture, fragTexCoord);
    fragColor = sample;
}
)";
}

std::string GPUAudioInterface::generateAudioComputeShader(const std::string& effectType) {
    if (effectType == "reverb") {
        return R"(
#version 450
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;
    
    // Simple reverb effect placeholder
    outputBuffer.samples[index] = inputBuffer.samples[index] * 0.8;
}
)";
    } else if (effectType == "distortion") {
        return R"(
#version 450
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;
    
    // Simple distortion effect placeholder
    float sample = inputBuffer.samples[index];
    outputBuffer.samples[index] = tanh(sample * 2.0);
}
)";
    } else {
        return R"(
#version 450
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;
    
    // Pass-through effect
    outputBuffer.samples[index] = inputBuffer.samples[index];
}
)";
    }
}

uint32_t GPUAudioInterface::generateHandle() {
    return m_nextHandle++;
}

bool GPUAudioInterface::validateHandle(uint32_t handle) const {
    return handle != INVALID_HANDLE;
}

void GPUAudioInterface::logError(const std::string& error) {
    m_lastError = error;
    std::cerr << "GPUAudioInterface Error: " << error << std::endl;
}

} // namespace Audio
} // namespace MagiTech 
