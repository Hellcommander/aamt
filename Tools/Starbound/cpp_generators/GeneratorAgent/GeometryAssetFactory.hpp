#pragma once
#include <future>
#include <vector>
#include "core/threading/ThreadPool.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/ConcurrentLRU.hpp"
#include "GeometryAssetTypes.hpp"

namespace MagiTech {
namespace Geometry {

// Mixes two 64-bit hashes into one cache key (boost-style combine).
inline uint64_t hashCombine(uint64_t seed, uint64_t value) {
    return seed ^ (value + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2));
}

// Forward declarations for generator functions
namespace PrimitiveGen { MeshHandle build(const PrimitiveParams& p); }
namespace ExtrusionGen { MeshHandle build(const ExtrusionParams& p); }
namespace LSystemGen { MeshHandle build(const LSystemParams& p); }
namespace SurfaceGen { MeshHandle build(const SurfaceParams& p); }
namespace BooleanGen { MeshHandle build(const BooleanParams& p); }
namespace UVGen { void generateAuto(MeshHandle mesh); }
namespace LODGen { LODData compute(const LODParams& lp, const std::vector<MeshHandle>& ms); }

class GeometryAssetFactory {
    ConcurrentLRUCache<uint64_t, GeometryBundle> m_cache;
    GeneratorTaskPool m_pool;
    bool m_initialized = false;

public:
    GeometryAssetFactory() = default;
    ~GeometryAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<GeometryBundle> generateAsync(
        const std::vector<GeometryRequest>& requests,
        const LODParams& lp
    );
};

} // namespace Geometry
} // namespace MagiTech
