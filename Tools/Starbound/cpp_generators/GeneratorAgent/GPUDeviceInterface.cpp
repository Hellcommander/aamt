#include "GPUDeviceInterface.hpp"
#include "core/Log.hpp"
#include <stb_image.h>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iterator>
#include <system_error>

namespace mt::light {

namespace {
std::string utf8(const std::filesystem::path& p) {
    const std::u8string s = p.u8string();
    return std::string(s.begin(), s.end());
}
} // namespace

// Static handle counter (0 is reserved for "no resource")
std::atomic<uint32_t> GPUDeviceInterface::s_nextHandle{1000};

// Global instance
GPUDeviceInterface& g_gpuDevice = GPUDeviceInterface::getInstance();

GPUDeviceInterface& GPUDeviceInterface::getInstance() {
    static GPUDeviceInterface instance;
    return instance;
}

uint32_t GPUDeviceInterface::generateHandle() {
    uint32_t handle = s_nextHandle.fetch_add(1, std::memory_order_relaxed);
    if (handle == 0) handle = s_nextHandle.fetch_add(1, std::memory_order_relaxed); // wrap-around guard
    return handle;
}

void GPUDeviceInterface::setAssetRoot(const std::filesystem::path& root) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_assetRoot = root;
}

std::filesystem::path GPUDeviceInterface::assetRoot() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_assetRoot;
}

std::filesystem::path GPUDeviceInterface::resolvePath(const std::string& path) const {
    std::filesystem::path p{std::u8string(path.begin(), path.end())};
    std::filesystem::path root;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        root = m_assetRoot;
    }
    if (p.is_relative() && !root.empty()) p = root / p;
    std::error_code ec;
    auto normal = std::filesystem::weakly_canonical(p, ec);
    return ec ? p.lexically_normal() : normal;
}

// ---------------------------------------------------------------------------------------------------------------------
// Textures
// ---------------------------------------------------------------------------------------------------------------------

std::vector<std::vector<uint8_t>> GPUDeviceInterface::buildMipChain(std::vector<uint8_t> base, uint32_t width,
                                                                     uint32_t height, uint32_t channels,
                                                                     bool generateMipmaps) {
    std::vector<std::vector<uint8_t>> mips;
    mips.push_back(std::move(base));
    if (!generateMipmaps) return mips;

    uint32_t w = width, h = height;
    while (w > 1 || h > 1) {
        const uint32_t nw = std::max(1u, w / 2), nh = std::max(1u, h / 2);
        const std::vector<uint8_t>& src = mips.back();
        std::vector<uint8_t> dst(static_cast<size_t>(nw) * nh * channels);
        // 2x2 box filter (clamped at odd edges)
        for (uint32_t y = 0; y < nh; ++y) {
            const uint32_t y0 = std::min(y * 2, h - 1), y1 = std::min(y * 2 + 1, h - 1);
            for (uint32_t x = 0; x < nw; ++x) {
                const uint32_t x0 = std::min(x * 2, w - 1), x1 = std::min(x * 2 + 1, w - 1);
                for (uint32_t c = 0; c < channels; ++c) {
                    const uint32_t sum = src[(static_cast<size_t>(y0) * w + x0) * channels + c] +
                                         src[(static_cast<size_t>(y0) * w + x1) * channels + c] +
                                         src[(static_cast<size_t>(y1) * w + x0) * channels + c] +
                                         src[(static_cast<size_t>(y1) * w + x1) * channels + c];
                    dst[(static_cast<size_t>(y) * nw + x) * channels + c] = static_cast<uint8_t>((sum + 2) / 4);
                }
            }
        }
        mips.push_back(std::move(dst));
        w = nw;
        h = nh;
    }
    return mips;
}

uint32_t GPUDeviceInterface::registerTexture(TextureResource&& texture) {
    if (texture.gpuBytes == 0) {
        for (const auto& level : texture.mips) texture.gpuBytes += level.size();
    }
    const uint32_t handle = generateHandle();
    std::lock_guard<std::mutex> lock(m_mutex);
    m_textures.emplace(handle, Counted<std::shared_ptr<const TextureResource>>{
                                   std::make_shared<const TextureResource>(std::move(texture)), 1});
    return handle;
}

uint32_t GPUDeviceInterface::createTexture2D(const std::string& path, bool generateMipmaps) {
    if (path.empty()) return 0;

    const std::filesystem::path resolved = resolvePath(path);
    const std::string key = utf8(resolved) + (generateMipmaps ? "|mips" : "|nomips");

    {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_texturesByPath.find(key);
        if (it != m_texturesByPath.end()) {
            auto tex = m_textures.find(it->second);
            if (tex != m_textures.end()) {
                ++tex->second.refs;
                return it->second;
            }
            m_texturesByPath.erase(it);
        }
    }

    // Read the file ourselves so non-ASCII Windows paths work, then decode from memory.
    std::ifstream file(resolved, std::ios::binary);
    if (!file) {
        MagiTech::Log::warn("LightGPU", "cannot open texture '{}'", utf8(resolved));
        return 0;
    }
    std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    if (bytes.empty()) {
        MagiTech::Log::warn("LightGPU", "texture '{}' is empty", utf8(resolved));
        return 0;
    }

    int w = 0, h = 0, n = 0;
    stbi_uc* pixels = stbi_load_from_memory(bytes.data(), static_cast<int>(bytes.size()), &w, &h, &n, 4);
    if (!pixels || w <= 0 || h <= 0) {
        MagiTech::Log::warn("LightGPU", "failed to decode texture '{}': {}", utf8(resolved),
                            stbi_failure_reason() ? stbi_failure_reason() : "unknown error");
        if (pixels) stbi_image_free(pixels);
        return 0;
    }
    std::vector<uint8_t> base(pixels, pixels + static_cast<size_t>(w) * h * 4);
    stbi_image_free(pixels);

    TextureResource tex;
    tex.kind = TextureKind::Texture2D;
    tex.sourcePath = utf8(resolved);
    tex.width = static_cast<uint32_t>(w);
    tex.height = static_cast<uint32_t>(h);
    tex.channels = 4;
    tex.mips = buildMipChain(std::move(base), tex.width, tex.height, 4, generateMipmaps);
    const uint32_t handle = registerTexture(std::move(tex));

    std::lock_guard<std::mutex> lock(m_mutex);
    auto existing = m_texturesByPath.find(key);
    if (existing != m_texturesByPath.end()) {
        // Another thread loaded the same file concurrently: keep the first one, drop ours.
        auto tex = m_textures.find(existing->second);
        if (tex != m_textures.end()) {
            ++tex->second.refs;
            m_textures.erase(handle);
            return existing->second;
        }
    }
    m_texturesByPath[key] = handle;
    return handle;
}

uint32_t GPUDeviceInterface::createTexture2D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height,
                                             uint32_t channels, bool generateMipmaps) {
    if (width == 0 || height == 0 || channels == 0 || channels > 4) return 0;
    const size_t expected = static_cast<size_t>(width) * height * channels;
    if (data.size() < expected) {
        MagiTech::Log::warn("LightGPU", "texture data too small: {} bytes, expected {}", data.size(), expected);
        return 0;
    }
    TextureResource tex;
    tex.kind = TextureKind::Texture2D;
    tex.width = width;
    tex.height = height;
    tex.channels = channels;
    tex.mips = buildMipChain(std::vector<uint8_t>(data.begin(), data.begin() + expected), width, height, channels,
                             generateMipmaps);
    return registerTexture(std::move(tex));
}

uint32_t GPUDeviceInterface::createTexture3D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height,
                                             uint32_t depth, uint32_t channels) {
    if (width == 0 || height == 0 || depth == 0 || channels == 0 || channels > 4) return 0;
    const size_t expected = static_cast<size_t>(width) * height * depth * channels;
    if (data.size() < expected) {
        MagiTech::Log::warn("LightGPU", "3D texture data too small: {} bytes, expected {}", data.size(), expected);
        return 0;
    }
    TextureResource tex;
    tex.kind = TextureKind::Texture3D;
    tex.width = width;
    tex.height = height;
    tex.depth = depth;
    tex.channels = channels;
    tex.mips.emplace_back(data.begin(), data.begin() + expected);
    return registerTexture(std::move(tex));
}

uint32_t GPUDeviceInterface::createDepthTexture(uint32_t width, uint32_t height, uint32_t layers) {
    if (width == 0 || height == 0 || layers == 0) return 0;
    TextureResource tex;
    tex.kind = TextureKind::DepthArray;
    tex.width = width;
    tex.height = height;
    tex.depth = layers;
    tex.channels = 4; // D32F
    tex.gpuBytes = static_cast<size_t>(width) * height * layers * sizeof(float);
    return registerTexture(std::move(tex));
}

bool GPUDeviceInterface::retainTexture(uint32_t textureHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_textures.find(textureHandle);
    if (it == m_textures.end()) return false;
    ++it->second.refs;
    return true;
}

void GPUDeviceInterface::destroyTexture(uint32_t textureHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_textures.find(textureHandle);
    if (it == m_textures.end()) return;
    if (--it->second.refs > 0) return;
    for (auto p = m_texturesByPath.begin(); p != m_texturesByPath.end(); ++p) {
        if (p->second == textureHandle) {
            m_texturesByPath.erase(p);
            break;
        }
    }
    m_textures.erase(it);
}

std::shared_ptr<const TextureResource> GPUDeviceInterface::getTexture(uint32_t handle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_textures.find(handle);
    return (it != m_textures.end()) ? it->second.value : nullptr;
}

// ---------------------------------------------------------------------------------------------------------------------
// Buffers
// ---------------------------------------------------------------------------------------------------------------------

uint32_t GPUDeviceInterface::createUniformBuffer(size_t size, const void* data) {
    if (size == 0) return 0;
    std::vector<uint8_t> bufferData(size, 0);
    if (data) std::memcpy(bufferData.data(), data, size);

    const uint32_t handle = generateHandle();
    std::lock_guard<std::mutex> lock(m_mutex);
    m_buffers.emplace(handle, std::move(bufferData));
    return handle;
}

bool GPUDeviceInterface::updateUniformBuffer(uint32_t bufferHandle, const void* data, size_t size, size_t offset) {
    if (!data) return false;
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_buffers.find(bufferHandle);
    if (it == m_buffers.end() || offset > it->second.size() || size > it->second.size() - offset) return false;
    std::memcpy(it->second.data() + offset, data, size);
    return true;
}

void GPUDeviceInterface::destroyBuffer(uint32_t bufferHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_buffers.erase(bufferHandle);
}

std::optional<std::vector<uint8_t>> GPUDeviceInterface::getBufferData(uint32_t bufferHandle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_buffers.find(bufferHandle);
    if (it == m_buffers.end()) return std::nullopt;
    return it->second;
}

// ---------------------------------------------------------------------------------------------------------------------
// Samplers
// ---------------------------------------------------------------------------------------------------------------------

uint32_t GPUDeviceInterface::createSampler(bool linearFiltering, bool clampToEdge, bool depthCompare,
                                           float maxAnisotropy) {
    const SamplerDesc desc{linearFiltering, clampToEdge, depthCompare, std::clamp(maxAnisotropy, 1.0f, 16.0f)};

    std::lock_guard<std::mutex> lock(m_mutex);
    for (auto& [handle, sampler] : m_samplers) {
        if (sampler.value == desc) {
            ++sampler.refs;
            return handle;
        }
    }
    const uint32_t handle = generateHandle();
    m_samplers.emplace(handle, Counted<SamplerDesc>{desc, 1});
    return handle;
}

void GPUDeviceInterface::destroySampler(uint32_t samplerHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_samplers.find(samplerHandle);
    if (it != m_samplers.end() && --it->second.refs == 0) m_samplers.erase(it);
}

std::optional<SamplerDesc> GPUDeviceInterface::getSampler(uint32_t samplerHandle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_samplers.find(samplerHandle);
    if (it == m_samplers.end()) return std::nullopt;
    return it->second.value;
}

// ---------------------------------------------------------------------------------------------------------------------
// Descriptor sets
// ---------------------------------------------------------------------------------------------------------------------

uint32_t GPUDeviceInterface::createDescriptorSet(const DescriptorSetDesc& desc) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto liveTexture = [&](uint32_t h) { return h == 0 || m_textures.count(h) != 0; };
    auto liveSampler = [&](uint32_t h) { return h == 0 || m_samplers.count(h) != 0; };

    if (desc.uniformBuffer == 0 || m_buffers.count(desc.uniformBuffer) == 0 || !liveTexture(desc.shadowMap) ||
        !liveTexture(desc.cookieTexture) || !liveTexture(desc.volumeTexture) || !liveSampler(desc.shadowSampler) ||
        !liveSampler(desc.cookieSampler) || !liveSampler(desc.volumeSampler)) {
        MagiTech::Log::warn("LightGPU", "descriptor set references a missing resource (ubo {})", desc.uniformBuffer);
        return 0;
    }

    const uint32_t handle = generateHandle();
    m_descriptorSets.emplace(handle, desc);
    return handle;
}

void GPUDeviceInterface::destroyDescriptorSet(uint32_t descriptorSetHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_descriptorSets.erase(descriptorSetHandle);
}

std::optional<DescriptorSetDesc> GPUDeviceInterface::getDescriptorSet(uint32_t descriptorSetHandle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_descriptorSets.find(descriptorSetHandle);
    if (it == m_descriptorSets.end()) return std::nullopt;
    return it->second;
}

// ---------------------------------------------------------------------------------------------------------------------
// Pipelines
// ---------------------------------------------------------------------------------------------------------------------

uint32_t GPUDeviceInterface::createPipeline(PipelineResource&& pipeline) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto byHash = m_pipelinesByHash.find(pipeline.sourceHash);
    if (byHash != m_pipelinesByHash.end()) {
        auto it = m_pipelines.find(byHash->second);
        if (it != m_pipelines.end()) {
            ++it->second.refs;
            return byHash->second;
        }
        m_pipelinesByHash.erase(byHash);
    }
    const uint32_t handle = generateHandle();
    const uint64_t hash = pipeline.sourceHash;
    m_pipelines.emplace(handle, Counted<std::shared_ptr<const PipelineResource>>{
                                    std::make_shared<const PipelineResource>(std::move(pipeline)), 1});
    m_pipelinesByHash[hash] = handle;
    return handle;
}

uint32_t GPUDeviceInterface::createGraphicsPipeline(const std::string& vertexShader, const std::string& fragmentShader) {
    if (vertexShader.empty() || fragmentShader.empty()) return 0;
    PipelineResource p;
    p.kind = PipelineKind::Graphics;
    p.vertexSource = vertexShader;
    p.fragmentSource = fragmentShader;
    ParamHasher h(0x47524150ull); // "GRAP"
    h.str(vertexShader);
    h.str(fragmentShader);
    p.sourceHash = h.digest();
    return createPipeline(std::move(p));
}

uint32_t GPUDeviceInterface::createComputePipeline(const std::string& computeShader) {
    if (computeShader.empty()) return 0;
    PipelineResource p;
    p.kind = PipelineKind::Compute;
    p.computeSource = computeShader;
    ParamHasher h(0x434F4D50ull); // "COMP"
    h.str(computeShader);
    p.sourceHash = h.digest();
    return createPipeline(std::move(p));
}

void GPUDeviceInterface::destroyPipeline(uint32_t pipelineHandle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_pipelines.find(pipelineHandle);
    if (it == m_pipelines.end() || --it->second.refs > 0) return;
    m_pipelinesByHash.erase(it->second.value->sourceHash);
    m_pipelines.erase(it);
}

std::shared_ptr<const PipelineResource> GPUDeviceInterface::getPipeline(uint32_t pipelineHandle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_pipelines.find(pipelineHandle);
    return (it != m_pipelines.end()) ? it->second.value : nullptr;
}

GPUDeviceStats GPUDeviceInterface::stats() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    GPUDeviceStats s;
    s.textures = m_textures.size();
    s.buffers = m_buffers.size();
    s.samplers = m_samplers.size();
    s.descriptorSets = m_descriptorSets.size();
    s.pipelines = m_pipelines.size();
    for (const auto& [h, t] : m_textures) s.textureBytes += t.value->gpuBytes;
    for (const auto& [h, b] : m_buffers) s.bufferBytes += b.size();
    return s;
}

} // namespace mt::light
