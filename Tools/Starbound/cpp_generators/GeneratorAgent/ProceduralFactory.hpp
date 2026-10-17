#pragma once

#include "SegmentedCreatureAssetBundle.hpp"
#include "SegmentedCreatureParams.hpp"
#include "GeneratorConcurrency.hpp"
#include <concepts>
#include <cstdint>
#include <future>
#include <string>
#include <vector>

namespace MagiTech {
namespace SegmentedCreatures {

// Generators for segmented creatures. Each build() creates the asset, stores it in the
// shared CreatureAssets::AssetStore and returns its handle.
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
    /** Behaviour tree for a creature, derived from its aiProfile. */
    AIHandle build(const SegmentedCreatureParams& p);
    /** Behaviour parameters matching an AI profile (used by build(SegmentedCreatureParams)). */
    BehaviorParams presetFor(AIProfile profile);
}

/** Releases every asset referenced by the bundle from the shared asset store. */
void releaseBundle(const AssetBundle& bundle);

/**
 * Generic cached, thread-pooled asset factory. A bundle slot is filled by
 * <Generator>::build(p) whenever an overload for P exists; slots without a
 * generator for P stay 0 (e.g. behaviour bundles carry only `ai`).
 */
template<typename P>
class ProceduralFactory {
public:
    ProceduralFactory() : m_initialized(false) {}
    ~ProceduralFactory() { shutdown(); }

    ProceduralFactory(const ProceduralFactory&) = delete;
    ProceduralFactory& operator=(const ProceduralFactory&) = delete;

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

    bool isInitialized() const { return m_initialized; }

    std::future<AssetBundle> generateAsync(const P& p) {
        const uint64_t key = p.hashKey();

        if (usesCache(p)) {
            if (auto existing = m_cache.find(key)) {
                std::promise<AssetBundle> ready;
                ready.set_value(*existing);
                return ready.get_future();
            }
        }

        return m_pool.enqueue([this, p, key] {
            AssetBundle b = buildBundle(p);
            if (usesCache(p)) m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation for immediate use
    AssetBundle generateSync(const P& p) {
        const uint64_t key = p.hashKey();

        if (usesCache(p)) {
            if (auto existing = m_cache.find(key)) {
                return *existing;
            }
        }

        AssetBundle b = buildBundle(p);
        if (usesCache(p)) m_cache.insert(key, b);
        return b;
    }

    // Cache management
    void clearCache() { m_cache.clear(); }
    size_t getCacheSize() const { return m_cache.size(); }
    size_t getCacheCapacity() const { return m_cache.capacity(); }
    double getCacheHitRate() const { return m_cache.getHitRate(); }

    static AssetBundle buildBundle(const P& p) {
        AssetBundle b;
        if constexpr (requires(const P& q) { MeshGen::build(q); })    b.mesh     = MeshGen::build(p);
        if constexpr (requires(const P& q) { TextureGen::build(q); }) b.texture  = TextureGen::build(p);
        if constexpr (requires(const P& q) { RigGen::build(q); })     b.skeleton = RigGen::build(p);
        if constexpr (requires(const P& q) { AnimGen::build(q); })    b.anim     = AnimGen::build(p);
        if constexpr (requires(const P& q) { AIGen::build(q); })      b.ai       = AIGen::build(p);
        return b;
    }

protected:
    GeneratorTaskPool& pool() { return m_pool; }

private:
    static bool usesCache(const P& p) {
        if constexpr (requires(const P& q) { { q.enableCaching } -> std::convertible_to<bool>; }) {
            return p.enableCaching;
        } else {
            return true;
        }
    }

    ConcurrentLRUCache<uint64_t, AssetBundle> m_cache;
    GeneratorTaskPool m_pool;
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

} // namespace SegmentedCreatures
} // namespace MagiTech
