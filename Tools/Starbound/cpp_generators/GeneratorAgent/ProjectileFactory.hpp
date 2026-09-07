#pragma once

#include "ProjectileTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Projectiles {

class ProjectileFactory {
public:
    ProjectileFactory();
    ~ProjectileFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<ProjectileBundle> generateAsync(const ProjectileParams& p);

private:
    ConcurrentLRUCache<uint64_t, ProjectileBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

} // namespace Projectiles
} // namespace MagiTech
