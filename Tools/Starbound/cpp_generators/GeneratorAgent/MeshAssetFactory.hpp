#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "MeshAssetTypes.hpp"

namespace MagiTech {
namespace MeshAssets {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildMesh(const MeshParams& p);
    ComputeMeshHandle buildComputeMesh(const ComputeMeshParams& p);
}
namespace UVGen {
    UVHandle unwrap(const MeshHandle& mesh);
}
namespace MaterialGen {
    MaterialHandle build(const MaterialParams& m);
}
namespace LODGen {
    MeshHandle build(const LODParams& l, const MeshHandle& base);
    NaniteMeshHandle buildNaniteClusters(const NaniteParams& p, const MeshHandle& base);
}
namespace MorphGen {
    MorphHandle build(const MorphParams& r, const MeshHandle& mesh);
}
namespace TessellationGen {
    TessellationHandle build(const TessellationParams& p, const MeshHandle& base);
}
namespace MLGen {
    MLMeshHandle build(const MLMeshParams& p);
}
namespace CollisionGen {
    CollisionHandle build(const CollisionParams& p, const MeshHandle& base);
}


inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class MeshAssetFactory {
    ConcurrentLRUCache<uint64_t, MeshAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    MeshAssetFactory() = default;
    ~MeshAssetFactory() { shutdown(); }

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

    std::future<MeshAssetBundle> generateAsync(
        const MeshParams& m,
        const std::optional<LODParams>& l,
        const std::optional<MaterialParams>& p,
        const std::optional<MorphParams>& r,
        const std::optional<ComputeMeshParams>& cmp,
        const std::optional<NaniteParams>& np,
        const std::optional<TessellationParams>& tp,
        const std::optional<MLMeshParams>& mlp,
        const std::optional<CollisionParams>& cp
        )
    {
        uint64_t key = m.hashKey();
        // Extend hashing for new optional params
        
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }

        return m_pool.enqueue([=]() {
            MeshAssetBundle b;
            if (cmp) b.computeMesh = MeshGen::buildComputeMesh(*cmp);
            else b.mesh = MeshGen::buildMesh(m);
            
            if (m.generateUVs) b.uvLayout = UVGen::unwrap(b.mesh);
            if (p) b.material = MaterialGen::build(*p);
            if (l) b.lodMesh = LODGen::build(*l, b.mesh);
            if (np) b.naniteMesh = LODGen::buildNaniteClusters(*np, b.mesh);
            if (r) b.morphTargets = MorphGen::build(*r, b.mesh);
            if (tp) b.tessellationData = TessellationGen::build(*tp, b.mesh);
            if (mlp) b.mlMesh = MLGen::build(*mlp);
            if (cp) b.collisionMesh = CollisionGen::build(*cp, b.mesh);

            m_cache.insert(key, b);
            return b;
        });
    }
};

} // namespace MeshAssets
} // namespace MagiTech
