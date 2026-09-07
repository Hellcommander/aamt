#pragma once

#include "SpellstoneTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Spellstones {

class SpellstoneFactory {
public:
    SpellstoneFactory();
    ~SpellstoneFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<SpellstoneBundle> generateAsync(const SpellstoneParams& p);

private:
    ConcurrentLRUCache<uint64_t, SpellstoneBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace Spellstones
} // namespace MagiTech
