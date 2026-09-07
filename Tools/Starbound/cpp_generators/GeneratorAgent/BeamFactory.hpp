#pragma once

#include "BeamTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Beams {

class BeamFactory {
public:
    BeamFactory();
    ~BeamFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<BeamBundle> generateAsync(const BeamParams& p);

private:
    ConcurrentLRUCache<uint64_t, BeamBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace Beams
} // namespace MagiTech
