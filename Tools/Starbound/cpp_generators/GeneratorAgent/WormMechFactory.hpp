#pragma once
#include <future>
#include <memory>
#include <unordered_map>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "WormMechTypes.hpp"

namespace MagiTech {
namespace WormMechs {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildWormMech(const WormMechParams& p);
    void buildSingleSegment(const WormMechParams& p, int segmentIndex);
}
namespace TextureGen {
    TextureHandle buildWormMech(const WormMechParams& p);
}
namespace ShaderGen {
    ShaderHandle buildWormMech(const WormMechParams& p);
}
namespace RigGen {
    SkeletonHandle buildWormMech(const WormMechParams& p);
}
namespace AnimGen {
    AnimationHandle buildProfile(const std::string& profile, int segCount);
}
namespace CockpitGen {
    MeshHandle build(const WormMechParams& p);
    TextureHandle buildTexture(const WormMechParams& p);
}
namespace ParticleGen {
    ParticleHandle buildExhaust(const WormMechParams& p);
}
namespace IconGen {
    TextureHandle buildMechIcon(const WormMechParams& m, const UIParams& u);
}

// Manages both static asset generation and live, dynamic instances
class WormMechFactory {
public:
    WormMechFactory() : m_initialized(false) {}
    ~WormMechFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }
    
    // Original async generation for static assets
    std::future<MechAssetBundle> generateAsync(const WormMechParams& params, const UIParams& ui) {
        uint64_t key = params.hashKey() ^ ui.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            MechAssetBundle bundle;
            bundle.mesh = MeshGen::buildWormMech(params);
            bundle.texture = TextureGen::buildWormMech(params);
            bundle.shader = ShaderGen::buildWormMech(params);
            bundle.skeleton = RigGen::buildWormMech(params);
            bundle.animation = AnimGen::buildProfile(params.animationProfile, params.segmentCount);
            bundle.cockpitMesh = CockpitGen::build(params);
            bundle.cockpitTexture = CockpitGen::buildTexture(params);
            bundle.exhaustFX = ParticleGen::buildExhaust(params);
            bundle.icon = IconGen::buildMechIcon(params, ui);
            m_cache.insert(key, bundle);
            return bundle;
        });
    }

    // Create a new dynamic mech instance from initial parameters
    std::shared_ptr<DynamicWormMech> createDynamicMech(const WormMechParams& initialParams) {
        auto mech = std::make_shared<DynamicWormMech>();
        mech->params.setSilently(initialParams);

        // Set up the callback for when parameters change
        mech->params.onChanged = [this, mech, ui = UIParams()](const WormMechParams& newParams) {
            this->regenerateDynamicMech(mech, newParams, ui);
        };

        // Perform the initial generation
        regenerateDynamicMech(mech, initialParams, UIParams());
        
        m_dynamicMechs[initialParams.id] = mech;
        return mech;
    }

    // Get a managed dynamic mech instance
    std::shared_ptr<DynamicWormMech> getDynamicMech(const std::string& id) {
        auto it = m_dynamicMechs.find(id);
        if (it != m_dynamicMechs.end()) {
            return it->second;
        }
        return nullptr;
    }

private:
    void regenerateDynamicMech(std::shared_ptr<DynamicWormMech> mech, const WormMechParams& params, const UIParams& ui) {
        generateAsync(params, ui).then([mech](std::future<MechAssetBundle> bundleFuture) {
            try {
                MechAssetBundle bundle = bundleFuture.get();
                mech->applyBundle(bundle);
            } catch (const std::exception& e) {
                // Log error
            }
        });
    }

    ConcurrentLRUCache<uint64_t, MechAssetBundle> m_cache;
    ThreadPool m_pool;
    std::unordered_map<std::string, std::shared_ptr<DynamicWormMech>> m_dynamicMechs;
    bool m_initialized;
};

} // namespace WormMechs
} // namespace MagiTech
