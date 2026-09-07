#include "GeometryAssetFactory.hpp"
#include "core/utils/HashCombine.hpp"
#include <future>

namespace MagiTech {
namespace Geometry {

void GeometryAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.init(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void GeometryAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

uint64_t hashRequests(const std::vector<GeometryRequest>& requests) {
    XXH64_state_t s; XXH64_reset(&s, 0);
    for(const auto& req : requests) {
        uint64_t h = std::visit([](auto&& arg) { return arg.hashKey(); }, req);
        XXH64_update(&s, &h, sizeof(h));
    }
    return XXH64_digest(&s);
}

std::future<GeometryBundle> GeometryAssetFactory::generateAsync(
    const std::vector<GeometryRequest>& requests,
    const LODParams& lp)
{
    uint64_t key = hashCombine(hashRequests(requests), lp.hashKey());
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }

    return m_pool.enqueue([=]() {
        GeometryBundle bundle;
        for (const auto& req : requests) {
            MeshHandle mesh = std::visit([&](auto&& p) -> MeshHandle {
                using P = std::decay_t<decltype(p)>;
                if constexpr (std::is_same_v<P, PrimitiveParams>) return PrimitiveGen::build(p);
                else if constexpr (std::is_same_v<P, ExtrusionParams>) return ExtrusionGen::build(p);
                else if constexpr (std::is_same_v<P, LSystemParams>) return LSystemGen::build(p);
                else if constexpr (std::is_same_v<P, SurfaceParams>) return SurfaceGen::build(p);
                else if constexpr (std::is_same_v<P, BooleanParams>) return BooleanGen::build(p);
                return 0; // Should not happen
            }, req);
            if(mesh) bundle.meshes.push_back(mesh);
        }

        for (auto& m : bundle.meshes) {
            UVGen::generateAuto(m);
        }
        bundle.lod = LODGen::compute(lp, bundle.meshes);
        m_cache.insert(key, bundle);
        return bundle;
    });
}

} // namespace Geometry
} // namespace MagiTech
