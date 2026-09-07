#pragma once

#include "SegmentedWeaponTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>
#include <vector>

namespace MagiTech {
namespace SegmentedWeapons {

// Forward declarations for the generator namespaces
namespace MeshGen {
    MeshHandle build(const SegmentedWeaponParams& p);
}

namespace TextureGen {
    TextureHandle build(const SegmentedWeaponParams& p);
}

namespace RigGen {
    SkeletonHandle build(const SegmentedWeaponParams& p);
}

namespace PhysicsGen {
    PhysicsHandle build(const SegmentedWeaponParams& w, const PhysicsParams& p);
}

template<typename P1, typename P2>
class SegmentedFactory {
public:
    SegmentedFactory() : m_initialized(false) {}
    ~SegmentedFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    std::future<AssetBundle> generateAsync(const P1& p1, const P2& p2) {
        uint64_t key = p1.hashKey();
        // A simple hash combine
        key ^= p2.hashKey() + 0x9e3779b9 + (key << 6) + (key >> 2);
        
        if (auto existing = m_cache.find(key)) {
            return std::async(std::launch::deferred, [existing]{ return *existing; });
        }

        return m_pool.enqueue([p1, p2, this, key] {
            AssetBundle b;
            b.mesh     = MeshGen::build(p1);
            b.texture  = TextureGen::build(p1);
            b.skeleton = RigGen::build(p1);
            b.physics  = PhysicsGen::build(p1, p2);
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation for immediate use
    AssetBundle generateSync(const P1& p1, const P2& p2) {
        uint64_t key = p1.hashKey();
        key ^= p2.hashKey() + 0x9e3779b9 + (key << 6) + (key >> 2);
        
        if (auto existing = m_cache.find(key)) {
            return *existing;
        }

        AssetBundle b;
        b.mesh     = MeshGen::build(p1);
        b.texture  = TextureGen::build(p1);
        b.skeleton = RigGen::build(p1);
        b.physics  = PhysicsGen::build(p1, p2);
        m_cache.insert(key, b);
        return b;
    }

    // Cache management
    void clearCache() { m_cache.clear(); }
    size_t getCacheSize() const { return m_cache.size(); }
    size_t getCacheCapacity() const { return m_cache.capacity(); }

private:
    ConcurrentLRUCache<uint64_t, AssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

// Specialized factory for segmented weapons
class SegmentedWeaponFactory : public SegmentedFactory<SegmentedWeaponParams, PhysicsParams> {
public:
    SegmentedWeaponFactory() = default;
    ~SegmentedWeaponFactory() = default;

    // Additional methods specific to segmented weapons
    std::future<AssetBundle> generateFromJson(const std::string& weaponJsonPath, const std::string& physicsJsonPath);
    std::future<AssetBundle> generateFromParams(const SegmentedWeaponParams& weaponParams, const PhysicsParams& physicsParams);
    
    // Batch generation
    std::vector<std::future<AssetBundle>> generateBatch(const std::vector<std::pair<SegmentedWeaponParams, PhysicsParams>>& params);
    
    // Validation
    bool validateWeaponParams(const SegmentedWeaponParams& params);
    std::string getWeaponValidationErrors(const SegmentedWeaponParams& params);
    bool validatePhysicsParams(const PhysicsParams& params);
    std::string getPhysicsValidationErrors(const PhysicsParams& params);
};

// Global factory instance
extern SegmentedWeaponFactory g_weaponFactory;

} // namespace SegmentedWeapons
} // namespace MagiTech
