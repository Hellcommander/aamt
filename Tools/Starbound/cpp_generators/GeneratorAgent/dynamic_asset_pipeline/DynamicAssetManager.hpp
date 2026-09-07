#pragma once

#include "DynamicAssetTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace DynamicAssets {

class DynamicAssetManager {
public:
    DynamicAssetManager();
    ~DynamicAssetManager();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<AssetBundle> generateAsync(const SpellstoneParams& p);

private:
    ConcurrentLRUCache<uint64_t, AssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace DynamicAssets
} // namespace MagiTech
