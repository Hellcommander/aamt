#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "IngredientTypes.hpp"

namespace MagiTech {
namespace Ingredients {

// Forward declarations for all generator functions, namespaced by type
namespace Gen {
    namespace Herb {
        MeshHandle buildMesh(const IngredientParams& p);
        TextureHandle buildAlbedo(const IngredientParams& p);
        ParticleHandle buildParticles(const IngredientParams& p);
    }
    namespace Crystal {
        MeshHandle buildMesh(const IngredientParams& p);
        TextureHandle buildAlbedo(const IngredientParams& p);
        ParticleHandle buildParticles(const IngredientParams& p);
    }
    // ... similar namespaces for Powder, Liquid, Bone, Runestone
}


class IngredientFactory {
public:
    IngredientFactory() : m_initialized(false) {}
    ~IngredientFactory() { shutdown(); }

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

    std::future<IngredientAssetBundle> generateAsync(const IngredientParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            IngredientAssetBundle b;
            // Dispatch to the correct generator set based on type
            switch (p.type) {
                case IngredientType::Herb:
                    b.mesh = Gen::Herb::buildMesh(p);
                    b.albedoMap = Gen::Herb::buildAlbedo(p);
                    b.ambientParticles = Gen::Herb::buildParticles(p);
                    break;
                case IngredientType::Crystal:
                    b.mesh = Gen::Crystal::buildMesh(p);
                    b.albedoMap = Gen::Crystal::buildAlbedo(p);
                    b.ambientParticles = Gen::Crystal::buildParticles(p);
                    break;
                // Add cases for Powder, Liquid, Bone, Runestone
                default:
                    // Log error or generate a placeholder
                    break;
            }
            // Common generators can be called here
            // b.normalMap = Gen::Common::buildNormalMap(p);
            // b.materialShader = Gen::Common::buildShader(p);
            
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, IngredientAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace Ingredients
} // namespace MagiTech
