#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "AlchemicalLauncherTypes.hpp"

namespace MagiTech {
namespace AlchemicalLaunchers {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildLauncherBody(const AlchemicalLauncherParams& p);
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
        return m_pool.enqueue([=]() {
            LauncherAssetBundle b;
            
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
            b.generationTime = getGenerationTime();
            b.vertexCount = getVertexCount(b.meshBody);
            b.triangleCount = getTriangleCount(b.meshBody);
            b.particleCount = getParticleCount(b);
            b.gpuAccelerated = isGPUAccelerated();
            
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, LauncherAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
    
    // Performance measurement helpers
    float getGenerationTime() const;
    size_t getVertexCount(MeshHandle mesh) const;
    size_t getTriangleCount(MeshHandle mesh) const;
    size_t getParticleCount(const LauncherAssetBundle& bundle) const;
    bool isGPUAccelerated() const;
};

} // namespace AlchemicalLaunchers
} // namespace MagiTech
