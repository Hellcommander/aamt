#include "GPUAudioInterface.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <sstream>

namespace MagiTech {
namespace Audio {

namespace {

// Reads the "// kernel: <name>" marker that identifies the audio kernel of a compute shader.
std::string kernelFromSource(const std::string& source) {
    const std::string marker = "// kernel:";
    const size_t pos = source.find(marker);
    if (pos == std::string::npos) return "passthrough";
    size_t start = pos + marker.size();
    while (start < source.size() && (source[start] == ' ' || source[start] == '\t')) ++start;
    size_t end = start;
    while (end < source.size() && (std::isalnum(static_cast<unsigned char>(source[end])) || source[end] == '_')) ++end;
    return end > start ? source.substr(start, end - start) : std::string("passthrough");
}

std::vector<float> bytesToFloats(const std::vector<uint8_t>& bytes) {
    std::vector<float> out(bytes.size() / sizeof(float));
    if (!out.empty()) std::memcpy(out.data(), bytes.data(), out.size() * sizeof(float));
    return out;
}

std::vector<uint8_t> floatsToBytes(const std::vector<float>& floats) {
    std::vector<uint8_t> out(floats.size() * sizeof(float));
    if (!out.empty()) std::memcpy(out.data(), floats.data(), out.size());
    return out;
}

} // namespace

GPUAudioInterface::GPUAudioInterface()
    : m_initialized(false)
    , m_gpuMemoryUsage(0)
    , m_gpuUtilization(0.0f)
    , m_processedSamples(0)
    , m_processingTimeMs(0)
    , m_counterStart(std::chrono::steady_clock::now())
    , m_nextHandle(1) {
}

GPUAudioInterface::~GPUAudioInterface() {
    shutdown();
}

bool GPUAudioInterface::initialize(std::shared_ptr<IRenderDevice> renderDevice) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (m_initialized) {
        // Allow attaching a render device after a host-only initialisation
        if (renderDevice && !m_renderDevice) m_renderDevice = std::move(renderDevice);
        return true;
    }

    m_renderDevice = std::move(renderDevice);
    m_counterStart = std::chrono::steady_clock::now();
    m_initialized = true;
    m_lastError.clear();
    return true;
}

void GPUAudioInterface::shutdown() {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        return;
    }

    // Release mirrored device resources, then drop all host-side resources
    if (m_renderDevice) {
        for (auto* table : {&m_buffers, &m_textures, &m_pipelines}) {
            for (auto& [handle, resource] : *table) {
                if (resource.valid && resource.deviceHandle != 0) {
                    m_renderDevice->destroyResource(resource.deviceHandle);
                }
            }
        }
    }

    m_buffers.clear();
    m_textures.clear();
    m_pipelines.clear();
    m_descriptorSets.clear();
    m_shaders.clear();
    m_allocations.clear();
    m_gpuMemoryUsage = 0;

    m_renderDevice.reset();
    m_initialized = false;
}

bool GPUAudioInterface::isInitialized() const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    return m_initialized;
}

AudioBufferHandle GPUAudioInterface::createAudioBuffer(const void* data, size_t size) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return INVALID_HANDLE;
    }

    if (size > MAX_AUDIO_BUFFER_SIZE) {
        logError("Audio buffer size exceeds maximum allowed size");
        return INVALID_HANDLE;
    }

    uint32_t handle = INVALID_HANDLE;
    if (!allocateGPUMemory(size, handle)) {
        return INVALID_HANDLE;
    }

    GPUResource resource;
    resource.handle = handle;
    resource.size = size;
    resource.type = "AudioBuffer";
    resource.valid = true;
    resource.data.resize(size);
    if (data && size > 0) std::memcpy(resource.data.data(), data, size);

    m_buffers[handle] = std::move(resource);
    return handle;
}

bool GPUAudioInterface::updateAudioBuffer(AudioBufferHandle handle, const void* data, size_t size) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!validateHandle(handle)) {
        logError("Invalid audio buffer handle");
        return false;
    }

    auto it = m_buffers.find(handle);
    if (it == m_buffers.end() || !it->second.valid) {
        logError("Audio buffer not found or invalid");
        return false;
    }
    if (size > MAX_AUDIO_BUFFER_SIZE) {
        logError("Audio buffer size exceeds maximum allowed size");
        return false;
    }
    const size_t previous = it->second.size;
    if (size > previous && m_gpuMemoryUsage + (size - previous) > getTotalGPUMemory()) {
        logError("Audio memory budget exceeded");
        return false;
    }

    it->second.data.assign(static_cast<const uint8_t*>(data), static_cast<const uint8_t*>(data) + (data ? size : 0));
    it->second.data.resize(size);
    it->second.size = size;
    m_gpuMemoryUsage = m_gpuMemoryUsage - previous + size;
    m_allocations[handle] = size;
    return true;
}

bool GPUAudioInterface::readAudioBuffer(AudioBufferHandle handle, std::vector<float>& out) const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_buffers.find(handle);
    if (it == m_buffers.end() || !it->second.valid) return false;
    out = bytesToFloats(it->second.data);
    return true;
}

void GPUAudioInterface::destroyAudioBuffer(AudioBufferHandle handle) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_buffers.find(handle);
    if (it != m_buffers.end() && it->second.valid) {
        if (m_renderDevice && it->second.deviceHandle != 0) {
            m_renderDevice->destroyResource(it->second.deviceHandle);
        }
        freeGPUMemory(handle);
        m_buffers.erase(it);
    }
}

bool GPUAudioInterface::validateAudioBuffer(AudioBufferHandle handle) const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_buffers.find(handle);
    return it != m_buffers.end() && it->second.valid;
}

// 8-bit single-channel image, one row per audio channel (sample -1..1 mapped to 0..255).
std::vector<uint8_t> GPUAudioInterface::textureBytes(const float* data, size_t numSamples, uint32_t channels) const {
    std::vector<uint8_t> pixels(numSamples * channels, 128);
    if (!data) return pixels;
    for (size_t s = 0; s < numSamples; ++s) {
        for (uint32_t c = 0; c < channels; ++c) {
            const float v = std::clamp(data[s * channels + c], -1.0f, 1.0f);
            pixels[static_cast<size_t>(c) * numSamples + s] = static_cast<uint8_t>(std::lround((v * 0.5f + 0.5f) * 255.0f));
        }
    }
    return pixels;
}

AudioTextureHandle GPUAudioInterface::createAudioTexture(const float* data, size_t numSamples, uint32_t channels) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return INVALID_HANDLE;
    }
    if (channels == 0 || numSamples == 0) {
        logError("Audio texture needs at least one channel and one sample");
        return INVALID_HANDLE;
    }

    const size_t size = numSamples * channels * sizeof(float);
    uint32_t handle = INVALID_HANDLE;
    if (!allocateGPUMemory(size, handle)) {
        return INVALID_HANDLE;
    }

    GPUResource resource;
    resource.handle = handle;
    resource.size = size;
    resource.type = "AudioTexture";
    resource.valid = true;
    resource.width = static_cast<uint32_t>(numSamples);
    resource.channels = channels;
    resource.data.resize(size);
    if (data) std::memcpy(resource.data.data(), data, size);

    if (m_renderDevice) {
        std::vector<uint8_t> pixels = textureBytes(data, numSamples, channels);
        resource.deviceHandle = m_renderDevice->createTexture2D(pixels.data(), static_cast<int>(numSamples), static_cast<int>(channels), 1);
        if (resource.deviceHandle != 0) m_renderDevice->setDebugName(resource.deviceHandle, "AudioTexture");
    }

    m_textures[handle] = std::move(resource);
    return handle;
}

bool GPUAudioInterface::updateAudioTexture(AudioTextureHandle handle, const float* data, size_t numSamples) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!validateHandle(handle)) {
        logError("Invalid audio texture handle");
        return false;
    }

    auto it = m_textures.find(handle);
    if (it == m_textures.end() || !it->second.valid) {
        logError("Audio texture not found or invalid");
        return false;
    }

    GPUResource& tex = it->second;
    const size_t size = numSamples * tex.channels * sizeof(float);
    const size_t previous = tex.size;
    tex.data.assign(size, 0);
    if (data && size > 0) std::memcpy(tex.data.data(), data, size);
    tex.width = static_cast<uint32_t>(numSamples);
    tex.size = size;
    m_gpuMemoryUsage = m_gpuMemoryUsage - previous + size;
    m_allocations[handle] = size;

    // IRenderDevice has no texture update entry point: recreate the mirror
    if (m_renderDevice) {
        if (tex.deviceHandle != 0) m_renderDevice->destroyResource(tex.deviceHandle);
        std::vector<uint8_t> pixels = textureBytes(data, numSamples, tex.channels);
        tex.deviceHandle = m_renderDevice->createTexture2D(pixels.data(), static_cast<int>(numSamples), static_cast<int>(tex.channels), 1);
    }
    return true;
}

void GPUAudioInterface::destroyAudioTexture(AudioTextureHandle handle) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_textures.find(handle);
    if (it != m_textures.end() && it->second.valid) {
        if (m_renderDevice && it->second.deviceHandle != 0) {
            m_renderDevice->destroyResource(it->second.deviceHandle);
        }
        freeGPUMemory(handle);
        m_textures.erase(it);
    }
}

bool GPUAudioInterface::validateAudioTexture(AudioTextureHandle handle) const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_textures.find(handle);
    return it != m_textures.end() && it->second.valid;
}

AudioPipelineHandle GPUAudioInterface::createAudioProcessingPipeline(const std::string& vertexShader,
                                                                   const std::string& fragmentShader) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return INVALID_HANDLE;
    }

    uint32_t vertexHandle = 0, fragmentHandle = 0, programHandle = 0;
    if (!compileShader(vertexShader, "vertex", vertexHandle)) {
        return INVALID_HANDLE;
    }
    if (!compileShader(fragmentShader, "fragment", fragmentHandle)) {
        m_shaders.erase(vertexHandle);
        return INVALID_HANDLE;
    }
    if (!linkProgram(vertexHandle, fragmentHandle, programHandle)) {
        m_shaders.erase(vertexHandle);
        m_shaders.erase(fragmentHandle);
        return INVALID_HANDLE;
    }
    m_shaders.erase(vertexHandle);
    m_shaders.erase(fragmentHandle);

    GPUResource resource = std::move(m_shaders[programHandle]);
    m_shaders.erase(programHandle);
    resource.handle = generateHandle();
    resource.type = "AudioPipeline";
    resource.kernel = "passthrough"; // raster pipelines copy the bound audio
    if (m_renderDevice) {
        resource.deviceHandle = m_renderDevice->createPipeline(vertexShader, fragmentShader);
    }

    const uint32_t handle = resource.handle;
    m_pipelines[handle] = std::move(resource);
    return handle;
}

AudioPipelineHandle GPUAudioInterface::createAudioComputePipeline(const std::string& computeShader) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return INVALID_HANDLE;
    }

    uint32_t computeHandle = 0;
    if (!compileComputeShader(computeShader, computeHandle)) {
        return INVALID_HANDLE;
    }

    GPUResource resource = std::move(m_shaders[computeHandle]);
    m_shaders.erase(computeHandle);
    resource.handle = generateHandle();
    resource.size = 0;
    resource.type = "AudioComputePipeline";
    resource.valid = true;

    const uint32_t handle = resource.handle;
    m_pipelines[handle] = std::move(resource);
    return handle;
}

void GPUAudioInterface::destroyPipeline(AudioPipelineHandle handle) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    auto it = m_pipelines.find(handle);
    if (it != m_pipelines.end() && it->second.valid) {
        if (m_renderDevice && it->second.deviceHandle != 0) {
            m_renderDevice->destroyResource(it->second.deviceHandle);
        }
        m_pipelines.erase(it);
    }
}

AudioDescriptorSet GPUAudioInterface::createDescriptorSet(AudioBufferHandle buffer, AudioTextureHandle texture) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return INVALID_HANDLE;
    }
    if (buffer != INVALID_HANDLE && !validateAudioBuffer(buffer)) {
        logError("Descriptor set references an invalid audio buffer");
        return INVALID_HANDLE;
    }
    if (texture != INVALID_HANDLE && !validateAudioTexture(texture)) {
        logError("Descriptor set references an invalid audio texture");
        return INVALID_HANDLE;
    }

    uint32_t handle = generateHandle();
    GPUResource resource;
    resource.handle = handle;
    resource.size = 0;
    resource.type = "AudioDescriptorSet";
    resource.valid = true;
    resource.buffer = buffer;
    resource.texture = texture;

    m_descriptorSets[handle] = std::move(resource);
    return handle;
}

void GPUAudioInterface::destroyDescriptorSet(AudioDescriptorSet handle) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    m_descriptorSets.erase(handle);
}

bool GPUAudioInterface::processAudioOnGPU(AudioBufferHandle input, AudioBufferHandle output,
                                        AudioPipelineHandle pipeline, AudioDescriptorSet descriptor) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return false;
    }

    if (!validateAudioBuffer(input) || !validateAudioBuffer(output)) {
        logError("Invalid audio buffer handles");
        return false;
    }

    auto pipelineIt = m_pipelines.find(pipeline);
    if (pipelineIt == m_pipelines.end() || !pipelineIt->second.valid) {
        logError("Invalid pipeline handle");
        return false;
    }

    auto descriptorIt = m_descriptorSets.find(descriptor);
    if (descriptorIt == m_descriptorSets.end() || !descriptorIt->second.valid) {
        logError("Invalid descriptor set handle");
        return false;
    }

    const auto start = std::chrono::steady_clock::now();
    const std::vector<float> in = bytesToFloats(m_buffers[input].data);
    std::vector<float> out;
    if (!runKernel(pipelineIt->second.kernel, in, out, descriptorIt->second.parameters)) {
        return false;
    }

    GPUResource& target = m_buffers[output];
    const size_t previous = target.size;
    target.data = floatsToBytes(out);
    target.size = target.data.size();
    m_gpuMemoryUsage = m_gpuMemoryUsage - previous + target.size;
    m_allocations[output] = target.size;

    // Update performance counters
    const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    m_processingTimeSeconds += seconds;
    m_processingTimeMs = static_cast<uint64_t>(m_processingTimeSeconds * 1000.0);
    m_processedSamples += in.size();
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - m_counterStart).count();
    m_gpuUtilization = elapsed > 0.0 ? static_cast<float>(std::min(1.0, m_processingTimeSeconds / elapsed)) : 0.0f;
    return true;
}

bool GPUAudioInterface::applyEffectOnGPU(AudioBufferHandle buffer, const std::string& effectType,
                                       const std::vector<float>& parameters) {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    if (!m_initialized) {
        logError("GPU interface not initialized");
        return false;
    }

    if (!validateAudioBuffer(buffer)) {
        logError("Invalid audio buffer handle");
        return false;
    }

    AudioPipelineHandle effectPipeline = createAudioComputePipeline(generateAudioComputeShader(effectType));
    if (effectPipeline == INVALID_HANDLE) {
        return false;
    }
    AudioDescriptorSet descriptor = createDescriptorSet(buffer);
    if (descriptor == INVALID_HANDLE) {
        destroyPipeline(effectPipeline);
        return false;
    }
    m_descriptorSets[descriptor].parameters = parameters;

    // Apply the effect in place
    bool success = processAudioOnGPU(buffer, buffer, effectPipeline, descriptor);

    // Clean up
    destroyDescriptorSet(descriptor);
    destroyPipeline(effectPipeline);

    return success;
}

uint64_t GPUAudioInterface::getGPUMemoryUsage() const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    return m_gpuMemoryUsage;
}

float GPUAudioInterface::getGPUUtilization() const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    return m_gpuUtilization;
}

void GPUAudioInterface::resetPerformanceCounters() {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    m_processedSamples = 0;
    m_processingTimeMs = 0;
    m_processingTimeSeconds = 0.0;
    m_gpuUtilization = 0.0f;
    m_counterStart = std::chrono::steady_clock::now();
}

std::string GPUAudioInterface::getLastError() const {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    return m_lastError;
}

void GPUAudioInterface::clearLastError() {
    std::lock_guard<std::recursive_mutex> lock(m_mutex);
    m_lastError.clear();
}

// Private implementation methods

// Validates a GLSL stage source and registers it.
bool GPUAudioInterface::compileShader(const std::string& source, const std::string& type, uint32_t& shaderHandle) {
    if (source.find("#version") == std::string::npos || source.find("void main") == std::string::npos) {
        logError("Invalid " + type + " shader: missing #version or main()");
        return false;
    }
    GPUResource shader;
    shader.handle = generateHandle();
    shader.type = type + "_shader";
    shader.valid = true;
    shader.data.assign(source.begin(), source.end());
    shaderHandle = shader.handle;
    m_shaders[shaderHandle] = std::move(shader);
    return true;
}

bool GPUAudioInterface::linkProgram(uint32_t vertexShader, uint32_t fragmentShader, uint32_t& programHandle) {
    auto vs = m_shaders.find(vertexShader);
    auto fs = m_shaders.find(fragmentShader);
    if (vs == m_shaders.end() || fs == m_shaders.end() ||
        vs->second.type != "vertex_shader" || fs->second.type != "fragment_shader") {
        logError("Program link failed: vertex/fragment stage missing");
        return false;
    }
    GPUResource program;
    program.handle = generateHandle();
    program.type = "program";
    program.valid = true;
    program.data = vs->second.data;
    program.data.insert(program.data.end(), fs->second.data.begin(), fs->second.data.end());
    programHandle = program.handle;
    m_shaders[programHandle] = std::move(program);
    return true;
}

bool GPUAudioInterface::compileComputeShader(const std::string& source, uint32_t& shaderHandle) {
    if (source.find("#version") == std::string::npos || source.find("void main") == std::string::npos ||
        source.find("local_size_x") == std::string::npos) {
        logError("Invalid compute shader: missing #version, local_size_x or main()");
        return false;
    }
    const std::string kernel = kernelFromSource(source);
    if (kernel != "passthrough" && kernel != "gain" && kernel != "distortion" && kernel != "reverb") {
        logError("Compute shader references unknown audio kernel: " + kernel);
        return false;
    }
    GPUResource shader;
    shader.handle = generateHandle();
    shader.type = "compute_shader";
    shader.valid = true;
    shader.kernel = kernel;
    shader.data.assign(source.begin(), source.end());
    shaderHandle = shader.handle;
    m_shaders[shaderHandle] = std::move(shader);
    return true;
}

bool GPUAudioInterface::allocateGPUMemory(size_t size, uint32_t& handle) {
    if (m_gpuMemoryUsage + size > getTotalGPUMemory()) {
        logError("Audio memory budget exceeded");
        return false;
    }
    handle = generateHandle();
    m_allocations[handle] = size;
    m_gpuMemoryUsage += size;
    return true;
}

void GPUAudioInterface::freeGPUMemory(uint32_t handle) {
    auto it = m_allocations.find(handle);
    if (it == m_allocations.end()) return;
    m_gpuMemoryUsage -= std::min<uint64_t>(m_gpuMemoryUsage, it->second);
    m_allocations.erase(it);
}

size_t GPUAudioInterface::getTotalGPUMemory() const {
    return MAX_GPU_MEMORY;
}

// Executes an audio kernel; each one matches the GLSL produced by generateAudioComputeShader.
bool GPUAudioInterface::runKernel(const std::string& kernel, const std::vector<float>& input, std::vector<float>& output,
                                  const std::vector<float>& parameters) {
    output.resize(input.size());
    auto param = [&parameters](size_t i, float fallback) { return i < parameters.size() ? parameters[i] : fallback; };

    if (kernel == "passthrough") {
        output = input;
    } else if (kernel == "gain") {
        const float gain = param(0, 1.0f);
        for (size_t i = 0; i < input.size(); ++i) output[i] = input[i] * gain;
    } else if (kernel == "distortion") {
        const float drive = param(0, 2.0f);
        for (size_t i = 0; i < input.size(); ++i) output[i] = std::tanh(input[i] * drive);
    } else if (kernel == "reverb") {
        // Multi-tap early reflections: out[i] = in[i] + sum_k g^k * in[i - k*d]
        const size_t delay = static_cast<size_t>(std::max(1.0f, param(0, 1764.0f)));
        const float decay = std::clamp(param(1, 0.5f), 0.0f, 0.99f);
        const int taps = static_cast<int>(std::clamp(param(2, 4.0f), 1.0f, 16.0f));
        for (size_t i = 0; i < input.size(); ++i) {
            float acc = input[i];
            float g = decay;
            for (int k = 1; k <= taps; ++k) {
                const size_t offset = static_cast<size_t>(k) * delay;
                if (offset > i) break;
                acc += g * input[i - offset];
                g *= decay;
            }
            output[i] = acc;
        }
    } else {
        logError("Unknown audio kernel: " + kernel);
        return false;
    }
    return true;
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
// kernel: reverb
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;
layout(push_constant) uniform Params {
    uint delaySamples;
    float decay;
    int taps;
} params;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;

    // Multi-tap early reflections
    float acc = inputBuffer.samples[index];
    float g = params.decay;
    for (int k = 1; k <= params.taps; ++k) {
        uint offset = uint(k) * params.delaySamples;
        if (offset > index) break;
        acc += g * inputBuffer.samples[index - offset];
        g *= params.decay;
    }
    outputBuffer.samples[index] = acc;
}
)";
    } else if (effectType == "distortion") {
        return R"(
#version 450
// kernel: distortion
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;
layout(push_constant) uniform Params {
    float drive;
} params;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;

    // Soft-clipping distortion
    float sample = inputBuffer.samples[index];
    outputBuffer.samples[index] = tanh(sample * params.drive);
}
)";
    } else if (effectType == "gain") {
        return R"(
#version 450
// kernel: gain
layout(local_size_x = 256) in;
layout(binding = 0) buffer AudioBuffer {
    float samples[];
} inputBuffer;
layout(binding = 1) buffer OutputBuffer {
    float samples[];
} outputBuffer;
layout(push_constant) uniform Params {
    float gain;
} params;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= inputBuffer.samples.length()) return;
    outputBuffer.samples[index] = inputBuffer.samples[index] * params.gain;
}
)";
    } else {
        return R"(
#version 450
// kernel: passthrough
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
    Log::error("Audio", "GPUAudioInterface: {}", error);
}

} // namespace Audio
} // namespace MagiTech
