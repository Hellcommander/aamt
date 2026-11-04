#pragma once
#include <future>
#include <algorithm>
#include <chrono>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "GeneratorConcurrency.hpp"
#include "AlchemicalLauncherTypes.hpp"

namespace MagiTech {
namespace AlchemicalLaunchers {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildLauncherBody(const AlchemicalLauncherParams& p);

    // PBR surface properties recorded per generated mesh handle (the generic
    // MagiTech::Mesh carries geometry only).
    struct LauncherSurfaceMaterial {
        float metallic = 0.0f;
        float roughness = 0.5f;
        float emissivePower = 0.0f;
    };
    void setMeshMaterial(MeshHandle mesh, const LauncherSurfaceMaterial& material);
    std::optional<LauncherSurfaceMaterial> getMeshMaterial(MeshHandle mesh);

    // Geometry statistics recorded per generated mesh handle.
    struct LauncherMeshStats {
        size_t vertexCount = 0;
        size_t triangleCount = 0;
    };
    void recordMeshStats(MeshHandle mesh, size_t vertexCount, size_t triangleCount);
    std::optional<LauncherMeshStats> getMeshStats(MeshHandle mesh);
}
namespace TextureGen {
    TextureHandle buildLauncherTexture(const AlchemicalLauncherParams& p);
}
namespace ShaderGen {
    ShaderHandle buildLauncherShader(const AlchemicalLauncherParams& p);
}
namespace ParticleGen {
    ParticleHandle buildMuzzleFlash(const AlchemicalLauncherParams& p);
    ParticleHandle buildMuzzleSmoke(const AlchemicalLauncherParams& p);
    ParticleHandle buildShellEjection(const AlchemicalLauncherParams& p);
    ParticleHandle buildHeatDistortion(const AlchemicalLauncherParams& p);
}
namespace PhysGen {
    PhysicsHandle buildRecoil(const AlchemicalLauncherParams& p);
    PhysicsHandle buildMagazinePhysics(const AlchemicalLauncherParams& p);
}
namespace AudioGen {
    AudioHandle buildFireSFX(const AlchemicalLauncherParams& p);
    AudioHandle buildReloadSFX(const AlchemicalLauncherParams& p);
    AudioHandle buildShellEjectSFX(const AlchemicalLauncherParams& p);
    AudioHandle buildHeatDistortionSFX(const AlchemicalLauncherParams& p);
}
namespace IconGen {
    TextureHandle buildLauncherIcon(const AlchemicalLauncherParams& p, const UIParams& u);
}

class AlchemicalLauncherFactory {
public:
    AlchemicalLauncherFactory() : m_initialized(false) {}
    ~AlchemicalLauncherFactory() { shutdown(); }

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

    std::future<LauncherAssetBundle> generateAsync(const AlchemicalLauncherParams& p, const UIParams& u) {
        uint64_t key = p.hashKey() ^ u.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([this, p, u, key]() {
            const auto start = std::chrono::steady_clock::now();
            LauncherAssetBundle b{};
            
            // Main launcher assets
            b.meshBody = MeshGen::buildLauncherBody(p);
            b.textureBody = TextureGen::buildLauncherTexture(p);
            b.shaderBody = ShaderGen::buildLauncherShader(p);
            
            // Effect assets
            b.muzzleFlash = ParticleGen::buildMuzzleFlash(p);
            b.muzzleSmoke = ParticleGen::buildMuzzleSmoke(p);
            
            // Additional particle effects
            if (p.enableShellEjection) {
                b.shellEjection = ParticleGen::buildShellEjection(p);
            }
            if (p.enableHeatDistortion) {
                b.heatDistortion = ParticleGen::buildHeatDistortion(p);
            }
            
            // Physics assets
            b.recoilPhysics = PhysGen::buildRecoil(p);
            b.magazinePhysics = PhysGen::buildMagazinePhysics(p);
            
            // Audio assets
            b.sfxFire = AudioGen::buildFireSFX(p);
            b.sfxReload = AudioGen::buildReloadSFX(p);
            
            // Additional audio effects
            if (p.enableShellEjection) {
                b.sfxShellEject = AudioGen::buildShellEjectSFX(p);
            }
            if (p.enableHeatDistortion) {
                b.sfxHeatDistortion = AudioGen::buildHeatDistortionSFX(p);
            }
            
            // UI assets
            b.icon = IconGen::buildLauncherIcon(p, u);
            
            // Performance metrics
            const auto stats = MeshGen::getMeshStats(b.meshBody);
            b.vertexCount = stats ? stats->vertexCount : 0;
            b.triangleCount = stats ? stats->triangleCount : 0;
            b.particleCount = getParticleCount(p, b);
            b.gpuAccelerated = false; // generated on the CPU worker pool
            b.generationTime = std::chrono::duration<float>(std::chrono::steady_clock::now() - start).count();
            
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, LauncherAssetBundle> m_cache;
    GeneratorTaskPool m_pool;
    bool m_initialized;
    
    // Particles spawned per shot by the bundle's emitters.
    static size_t getParticleCount(const AlchemicalLauncherParams& p, const LauncherAssetBundle& b) {
        size_t count = 0;
        if (b.muzzleFlash) count += 1;                                              // single flash burst
        if (b.muzzleSmoke) count += static_cast<size_t>(std::max(p.muzzleSmokeCount, 0));
        if (b.shellEjection) count += static_cast<size_t>(std::max(p.shellEjectionCount, 0));
        if (b.heatDistortion) count += 1;                                           // distortion volume
        return count;
    }
};

} // namespace AlchemicalLaunchers
} // namespace MagiTech
