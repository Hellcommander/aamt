#pragma once

#include "IMagiTechModule.hpp"
#include "SpellAssetTypes.hpp"
#include <cstdint>
#include <deque>
#include <filesystem>
#include <memory>
#include <optional>
#include <shared_mutex>
#include <unordered_map>
#include <vector>
#include <sol/sol.hpp>

namespace MagiTech {

class EnhancedRenderer; // Consumer of generated assets (core/modules/EnhancedRenderer.hpp).

namespace Procedural {

class ProceduralAssetModule : public IMagiTechModule {
public:
    ProceduralAssetModule();
    ~ProceduralAssetModule() override;

    // IMagiTechModule interface
    const char* getName() const override { return "ProceduralAssetModule"; }
    bool initialize() override;
    void shutdown() override;
    bool isInitialized() const override { return m_initialized; }
    using IMagiTechModule::registerBindings;
    void registerBindings(sol::state_view lua) override;

    // Core functionality
    AssetBundle getOrCreateSpellAsset(const SpellAssetParams& params);

    void setRenderer(EnhancedRenderer* renderer);

    /// Directory used for the persisted asset records (default: "proc_assets").
    void setStorageDirectory(std::filesystem::path dir) { m_storageDir = std::move(dir); }

    /// Maximum number of cached bundles before the least recently used one is evicted.
    void setCacheCapacity(size_t capacity) { m_cacheCapacity = capacity == 0 ? 1 : capacity; }

private:
    // Pipeline stages from user prompt
    std::optional<AssetBundle> cacheLookup(uint64_t key);
    void cacheInsert(uint64_t key, const AssetBundle& bundle);
    AssetBundle generateAsset(const SpellAssetParams& params);

    // Generation sub-stages
    TextureHandle generateTexture(const SpellAssetParams& params);
    MeshHandle generateMesh(const SpellAssetParams& params);

    void uploadToGpu();

    // Caching (key -> bundle) with LRU order (front = least recently used)
    using AssetCache = std::unordered_map<uint64_t, AssetBundle>;
    AssetCache m_cache;
    std::deque<uint64_t> m_lruQueue;
    size_t m_cacheCapacity = 256;
    mutable std::shared_mutex m_cacheMutex;

    // For save file serialization: each generated asset is stored as its
    // generation parameters, so it can be regenerated deterministically on load.
    void serializeAsset(uint64_t key, const SpellAssetParams& params);
    void deserializeAssets();
    std::filesystem::path m_storageDir = "proc_assets";

    EnhancedRenderer* m_renderer = nullptr; // Raw pointer to the renderer for resource creation.

    bool m_initialized = false;
};

} // namespace Procedural
} // namespace MagiTech
