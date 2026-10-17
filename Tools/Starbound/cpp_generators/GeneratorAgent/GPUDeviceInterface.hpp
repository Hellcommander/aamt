#pragma once

#include "LightTypes.hpp"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace mt::light {

// ---------------------------------------------------------------------------------------------------------------------
// CPU-side GPU resource registry used by the light generators.
//
// The light generators run inside the backend DLL, which has no direct access to the game renderer. This
// interface owns the resource *descriptions and data* (decoded texture pixels with mip chains, uniform buffer
// bytes, sampler states, descriptor sets, shader sources) under stable integer handles. A renderer backend
// uploads them by handle (getTexture / getBufferData / getPipeline / getDescriptorSet). Immutable shared
// resources (path textures, samplers, pipelines) are de-duplicated and reference counted.
// ---------------------------------------------------------------------------------------------------------------------

enum class TextureKind : uint32_t { Texture2D = 0, Texture3D = 1, DepthArray = 2 };

struct TextureResource {
    TextureKind kind{TextureKind::Texture2D};
    std::string sourcePath;                   // empty for generated textures
    uint32_t    width{};
    uint32_t    height{};
    uint32_t    depth{1};                     // 3D depth or array layer count
    uint32_t    channels{4};                  // bytes per texel for colour textures (R8 .. RGBA8)
    std::vector<std::vector<uint8_t>> mips;   // CPU texel data per mip level (empty for render targets)
    size_t      gpuBytes{};                   // bytes the renderer has to allocate for this texture
};

struct SamplerDesc {
    bool  linearFiltering{true};
    bool  clampToEdge{true};
    bool  depthCompare{false};
    float maxAnisotropy{1.0f};

    bool operator==(const SamplerDesc&) const = default;
};

struct DescriptorSetDesc {
    GpuBuffer  uniformBuffer{};
    GpuTexture shadowMap{};
    GpuSampler shadowSampler{};
    GpuTexture cookieTexture{};
    GpuSampler cookieSampler{};
    GpuTexture volumeTexture{};
    GpuSampler volumeSampler{};
};

enum class PipelineKind : uint32_t { Graphics = 0, Compute = 1 };

struct PipelineResource {
    PipelineKind kind{PipelineKind::Graphics};
    std::string  vertexSource;
    std::string  fragmentSource;
    std::string  computeSource;
    uint64_t     sourceHash{};
};

struct GPUDeviceStats {
    size_t textures{};
    size_t buffers{};
    size_t samplers{};
    size_t descriptorSets{};
    size_t pipelines{};
    size_t textureBytes{};
    size_t bufferBytes{};
};

class GPUDeviceInterface {
public:
    static GPUDeviceInterface& getInstance();

    GPUDeviceInterface(const GPUDeviceInterface&) = delete;
    GPUDeviceInterface& operator=(const GPUDeviceInterface&) = delete;

    // Root directory that relative texture paths are resolved against (defaults to the working directory).
    void setAssetRoot(const std::filesystem::path& root);
    std::filesystem::path assetRoot() const;

    // Texture operations ----------------------------------------------------------------------------------------------
    // Loads (or re-uses, reference counted) an image file decoded to RGBA8. Returns 0 on failure.
    uint32_t createTexture2D(const std::string& path, bool generateMipmaps = true);
    // Creates a texture from raw texels (channels = bytes per texel, 1..4). Returns 0 on invalid input.
    uint32_t createTexture2D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height, uint32_t channels,
                             bool generateMipmaps = false);
    uint32_t createTexture3D(const std::vector<uint8_t>& data, uint32_t width, uint32_t height, uint32_t depth,
                             uint32_t channels);
    // Depth render target (array of `layers` slices, 32-bit float depth). No CPU texel storage.
    uint32_t createDepthTexture(uint32_t width, uint32_t height, uint32_t layers);
    // Adds a reference to a live texture; false when the handle is no longer alive.
    bool retainTexture(uint32_t textureHandle);
    void destroyTexture(uint32_t textureHandle);
    std::shared_ptr<const TextureResource> getTexture(uint32_t handle) const;

    // Buffer operations -----------------------------------------------------------------------------------------------
    uint32_t createUniformBuffer(size_t size, const void* data = nullptr);
    bool updateUniformBuffer(uint32_t bufferHandle, const void* data, size_t size, size_t offset = 0);
    void destroyBuffer(uint32_t bufferHandle);
    std::optional<std::vector<uint8_t>> getBufferData(uint32_t bufferHandle) const;

    // Sampler operations (identical sampler states share one handle) --------------------------------------------------
    uint32_t createSampler(bool linearFiltering = true, bool clampToEdge = true, bool depthCompare = false,
                           float maxAnisotropy = 1.0f);
    void destroySampler(uint32_t samplerHandle);
    std::optional<SamplerDesc> getSampler(uint32_t samplerHandle) const;

    // Descriptor set operations ---------------------------------------------------------------------------------------
    // Every non-zero handle in the description must reference a live resource; returns 0 otherwise.
    uint32_t createDescriptorSet(const DescriptorSetDesc& desc);
    void destroyDescriptorSet(uint32_t descriptorSetHandle);
    std::optional<DescriptorSetDesc> getDescriptorSet(uint32_t descriptorSetHandle) const;

    // Pipeline operations (identical shader sources share one handle) -------------------------------------------------
    uint32_t createGraphicsPipeline(const std::string& vertexShader, const std::string& fragmentShader);
    uint32_t createComputePipeline(const std::string& computeShader);
    void destroyPipeline(uint32_t pipelineHandle);
    std::shared_ptr<const PipelineResource> getPipeline(uint32_t pipelineHandle) const;

    GPUDeviceStats stats() const;

private:
    GPUDeviceInterface() = default;
    ~GPUDeviceInterface() = default;

    template <typename T>
    struct Counted {
        T        value;
        uint32_t refs{1};
    };

    static uint32_t generateHandle();
    static std::atomic<uint32_t> s_nextHandle;

    std::filesystem::path resolvePath(const std::string& path) const;
    uint32_t registerTexture(TextureResource&& texture);
    uint32_t createPipeline(PipelineResource&& pipeline);
    static std::vector<std::vector<uint8_t>> buildMipChain(std::vector<uint8_t> base, uint32_t width, uint32_t height,
                                                           uint32_t channels, bool generateMipmaps);

    mutable std::mutex m_mutex;
    std::filesystem::path m_assetRoot;

    std::unordered_map<uint32_t, Counted<std::shared_ptr<const TextureResource>>> m_textures;
    std::unordered_map<std::string, uint32_t> m_texturesByPath;
    std::unordered_map<uint32_t, std::vector<uint8_t>> m_buffers;
    std::unordered_map<uint32_t, Counted<SamplerDesc>> m_samplers;
    std::unordered_map<uint32_t, DescriptorSetDesc> m_descriptorSets;
    std::unordered_map<uint32_t, Counted<std::shared_ptr<const PipelineResource>>> m_pipelines;
    std::unordered_map<uint64_t, uint32_t> m_pipelinesByHash;
};

// Global GPU device interface instance (same object as GPUDeviceInterface::getInstance()).
extern GPUDeviceInterface& g_gpuDevice;

} // namespace mt::light
