#pragma once

#include "IMagiTechModule.hpp"
#include "core/modules/procedural/SpellAssetTypes.hpp"
#include <unordered_map>
#include <cstdint>
#include <memory>
#include <shared_mutex>
#include <vector>

// Forward declarations
namespace sol {
    class state_view;
}
class EnhancedRenderer; // Assuming this will be the consumer of generated assets.

namespace MagiTech {
namespace Procedural {

class ProceduralAssetModule : public IMagiTechModule {
public:
    ProceduralAssetModule();
    ~ProceduralAssetModule() override;

    // IMagiTechModule interface
    const char* getName() const override { return "ProceduralAssetModule"; }
    void initialize() override;
    void shutdown() override;
    void registerBindings(sol::state_view lua) override;

    // Core functionality
    AssetBundle getOrCreateSpellAsset(const SpellAssetParams& params);

    void setRenderer(EnhancedRenderer* renderer);

private:
    // Pipeline stages from user prompt
    std::optional<AssetBundle> cacheLookup(uint64_t key);
    AssetBundle generateAsset(const SpellAssetParams& params);

    // Generation sub-stages
    TextureHandle generateTexture(const SpellAssetParams& params);
    MeshHandle generateMesh(const SpellAssetParams& params);
    // void generateAnimationBuffers(...)

    void uploadToGpu();

    // Caching
    using AssetCache = std::unordered_map<uint64_t, AssetBundle>;
    AssetCache m_cache;
    mutable std::shared_mutex m_cacheMutex;
    
    // LRU data - just a vector of keys for now
    std::vector<uint64_t> m_lruQueue;


    // For save file serialization
    void serializeAsset(uint64_t key, const AssetBundle& bundle);
    void deserializeAssets();

    EnhancedRenderer* m_renderer = nullptr; // Raw pointer to the renderer for resource creation.
    
    bool m_initialized = false;
};

} // namespace Procedural
} // namespace MagiTech
