#pragma once

#include "RoomTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Rooms {

class RoomFactory {
public:
    RoomFactory();
    ~RoomFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<RoomBundle> generateAsync(const RoomParams& p);

private:
    ConcurrentLRUCache<uint64_t, RoomBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace Rooms
} // namespace MagiTech
