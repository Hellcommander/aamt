#pragma once

#include "BehaviorTypes.hpp"
#include "monster_assets/MonsterGenerators.hpp"
#include "GeneratorConcurrency.hpp"
#include <cstdint>
#include <future>
#include <memory>

namespace MagiTech {
namespace Monsters {

// The behaviour generators themselves (AIGen::BehaviorTreeBuilder / StateMachineBuilder / build)
// are declared in monster_assets/MonsterGenerators.hpp and implemented in BehaviorGenerators.cpp.

/**
 * Behaviour asset factory: builds a BehaviorAssetBundle (full AI plus the separate patrol,
 * combat, social and environmental state machines) with caching and a worker pool.
 */
class BehaviorGenerator {
public:
    BehaviorGenerator() = default;
    ~BehaviorGenerator();

    BehaviorGenerator(const BehaviorGenerator&) = delete;
    BehaviorGenerator& operator=(const BehaviorGenerator&) = delete;

    void initialize(size_t cacheSize = 256, size_t numThreads = 2);
    void shutdown();
    bool isInitialized() const { return m_initialized; }

    std::future<BehaviorAssetBundle> generateAsync(const BehaviorParams& params);
    BehaviorAssetBundle generate(const BehaviorParams& params);

    void clearCache();
    size_t getCacheSize() const;
    double getCacheHitRate() const;

private:
    BehaviorAssetBundle generateBehaviorAssets(const BehaviorParams& params);

    bool m_initialized = false;
    std::unique_ptr<ConcurrentLRUCache<uint64_t, BehaviorAssetBundle>> m_cache;
    std::unique_ptr<GeneratorTaskPool> m_threadPool;
};

} // namespace Monsters
} // namespace MagiTech
