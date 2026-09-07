#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "AnimationAssetTypes.hpp"

namespace MagiTech {
namespace AnimationAssets {

// Forward declarations for generator functions
namespace SkeletonGen {
    SkeletonHandle buildSkeleton(const SkeletonParams& p);
}
namespace ClipGen {
    ClipHandle buildClip(const AnimationClipParams& c, const SkeletonParams& s);
}
namespace BlendSpaceGen {
    BlendSpaceHandle build(const BlendSpaceParams& b, const SkeletonParams& s);
}
namespace ProcLayerGen {
    ProcLayerHandle build(const ProcLayerParams& l, const SkeletonParams& s);
}

inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class AnimationAssetFactory {
    ConcurrentLRUCache<uint64_t, AnimationAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    AnimationAssetFactory() = default;
    ~AnimationAssetFactory() { shutdown(); }

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

    std::future<AnimationAssetBundle> generateAsync(
        const SkeletonParams& s,
        const AnimationClipParams& c,
        const std::optional<BlendSpaceParams>& b,
        const std::optional<ProcLayerParams>& l)
    {
        uint64_t key = s.hashKey();
        key = hashCombine(key, c.hashKey());
        if (b) key = hashCombine(key, b->hashKey());
        if (l) key = hashCombine(key, l->hashKey());
        
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }

        return m_pool.enqueue([=]() {
            AnimationAssetBundle bundle;
            bundle.skeleton = SkeletonGen::buildSkeleton(s);
            bundle.clip = ClipGen::buildClip(c, s);
            bundle.blendSpace = b ? BlendSpaceGen::build(*b, s) : BlendSpaceHandle{};
            bundle.procLayer = l ? ProcLayerGen::build(*l, s) : ProcLayerHandle{};
            m_cache.insert(key, bundle);
            return bundle;
        });
    }
};

} // namespace AnimationAssets
} // namespace MagiTech
