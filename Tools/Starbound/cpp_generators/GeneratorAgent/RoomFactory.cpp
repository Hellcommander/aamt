#include "RoomFactory.hpp"
#include "RoomGenerators.hpp"

namespace MagiTech {
namespace Rooms {

RoomFactory::RoomFactory() {}

RoomFactory::~RoomFactory() {
    shutdown();
}

void RoomFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void RoomFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<RoomBundle> RoomFactory::generateAsync(const RoomParams& p) {
    uint64_t key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        RoomBundle b;
        b.geometry = MeshGen::buildRoomMesh(p);
        b.tileset  = TextureGen::buildTileset(p);
        b.material = MaterialGen::buildRoomMaterial(p);
        b.lights   = DecorationGen::placeLights(p, b.geometry);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace Rooms
} // namespace MagiTech
