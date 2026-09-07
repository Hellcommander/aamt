#pragma once

#include "MagicalItemTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace MagicalItems {

class MagicalItemFactory {
public:
    MagicalItemFactory();
    ~MagicalItemFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<MagicalItemBundle> generateAsync(const MagicalItemParams& p);

private:
    ConcurrentLRUCache<uint64_t, MagicalItemBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace MagicalItems
} // namespace MagiTech
