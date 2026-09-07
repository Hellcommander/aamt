#pragma once

#include "SegmentedCreatureAssetBundle.hpp"
#include "SegmentedCreatureParams.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace SegmentedCreatures {

// Forward declarations for the generator namespaces
template<typename P>
struct MeshGen {
    static MeshHandle build(const P& p);
};

template<typename P>
struct TextureGen {
    static TextureHandle build(const P& p);
};

template<typename P>
struct RigGen {
    static SkeletonHandle build(const P& p);
};

template<typename P>
struct AnimGen {
    static AnimationHandle build(const P& p);
};

template<typename P>
struct AIGen {
    static AIHandle build(const P& p);
};

// Specialized generators for segmented creatures
namespace MeshGen {
    MeshHandle build(const SegmentedCreatureParams& p);
}

namespace TextureGen {
    TextureHandle build(const SegmentedCreatureParams& p);
}

namespace RigGen {
    SkeletonHandle build(const SegmentedCreatureParams& p);
}

namespace AnimGen {
    AnimationHandle build(const SegmentedCreatureParams& p);
}

namespace AIGen {
    AIHandle build(const BehaviorParams& p);
}

template<typename P>
class ProceduralFactory {
public:
    ProceduralFactory() : m_initialized(false) {}
    ~ProceduralFactory() { shutdown(); }

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

    std::future<AssetBundle> generateAsync(const P& p) {
        uint64_t key = p.hashKey();
        
        if (auto existing = m_cache.find(key)) {
            return std::async(std::launch::deferred, [existing]{ return *existing; });
        }

        return m_pool.enqueue([p, this] {
            AssetBundle b;
            b.mesh     = MeshGen<P>::build(p);
            b.texture  = TextureGen<P>::build(p);
            b.skeleton = RigGen<P>::build(p);
            b.anim     = AnimGen<P>::build(p);
            b.ai       = AIGen<P>::build(p);
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation for immediate use
    AssetBundle generateSync(const P& p) {
        uint64_t key = p.hashKey();
        
        if (auto existing = m_cache.find(key)) {
            return *existing;
        }

        AssetBundle b;
        b.mesh     = MeshGen<P>::build(p);
        b.texture  = TextureGen<P>::build(p);
        b.skeleton = RigGen<P>::build(p);
        b.anim     = AnimGen<P>::build(p);
        b.ai       = AIGen<P>::build(p);
        m_cache.insert(key, b);
        return b;
    }

    // Cache management
    void clearCache() { m_cache.clear(); }
    size_t getCacheSize() const { return m_cache.size(); }
    size_t getCacheCapacity() const { return m_cache.capacity(); }

private:
    ConcurrentLRUCache<uint64_t, AssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

// Specialized factory for segmented creatures
class SegmentedCreatureFactory : public ProceduralFactory<SegmentedCreatureParams> {
public:
    SegmentedCreatureFactory() = default;
    ~SegmentedCreatureFactory() = default;

    // Additional methods specific to segmented creatures
    std::future<AssetBundle> generateFromJson(const std::string& jsonPath);
    std::future<AssetBundle> generateFromParams(const SegmentedCreatureParams& params);
    
    // Batch generation
    std::vector<std::future<AssetBundle>> generateBatch(const std::vector<SegmentedCreatureParams>& params);
    
    // Validation
    bool validateParams(const SegmentedCreatureParams& params);
    std::string getValidationErrors(const SegmentedCreatureParams& params);
};

// Specialized factory for behavior
class BehaviorFactory : public ProceduralFactory<BehaviorParams> {
public:
    BehaviorFactory() = default;
    ~BehaviorFactory() = default;

    // Additional methods specific to behavior
    std::future<AssetBundle> generateFromJson(const std::string& jsonPath);
    std::future<AssetBundle> generateFromParams(const BehaviorParams& params);
    
    // Batch generation
    std::vector<std::future<AssetBundle>> generateBatch(const std::vector<BehaviorParams>& params);
    
    // Validation
    bool validateParams(const BehaviorParams& params);
    std::string getValidationErrors(const BehaviorParams& params);
};

// Global factory instances
extern SegmentedCreatureFactory g_creatureFactory;
extern BehaviorFactory g_behaviorFactory;

} // namespace SegmentedCreatures
} // namespace MagiTech
