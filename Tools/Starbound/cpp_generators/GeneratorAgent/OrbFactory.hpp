#pragma once

#include "OrbTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Orbs {

class OrbFactory {
public:
    OrbFactory();
    ~OrbFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<OrbBundle> generateAsync(const OrbParams& p);

private:
    ConcurrentLRUCache<uint64_t, OrbBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace Orbs
} // namespace MagiTech
