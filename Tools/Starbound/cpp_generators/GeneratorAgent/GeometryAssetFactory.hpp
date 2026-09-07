#pragma once
#include <future>
#include <vector>
#include "core/threading/ThreadPool.hpp"
#include "core/ConcurrentLRU.hpp"
#include "GeometryAssetTypes.hpp"

namespace MagiTech {
namespace Geometry {

// Forward declarations for generator functions
namespace PrimitiveGen { MeshHandle build(const PrimitiveParams& p); }
namespace ExtrusionGen { MeshHandle build(const ExtrusionParams& p); }
namespace LSystemGen { MeshHandle build(const LSystemParams& p); }
namespace SurfaceGen { MeshHandle build(const SurfaceParams& p); }
namespace BooleanGen { MeshHandle build(const BooleanParams& p); }
namespace UVGen { void generateAuto(MeshHandle mesh); }
namespace LODGen { LODData compute(const LODParams& lp, const std::vector<MeshHandle>& ms); }

class GeometryAssetFactory {
    ConcurrentLRU<uint64_t, GeometryBundle> m_cache;
    ThreadPool m_pool;
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
