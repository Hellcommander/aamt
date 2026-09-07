#pragma once

#include <future>
#include <memory>
#include "core/threading/ThreadPool.hpp"
#include "AdvancedProjectileTypes.hpp"

namespace MagiTech {
namespace AdvancedProjectiles {

// ============================================================================
// GUIDED MISSILE FACTORY
// ============================================================================

class GuidedMissileFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    GuidedMissileFactory() = default;
    ~GuidedMissileFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<MissileBundle> generateAsync(
        const GuidanceParams& guidance,
        const PropulsionParams& propulsion,
        const TargetParams& target);

private:
    // Generator modules
    namespace MeshGen {
        MeshHandle buildMissileMesh(const GuidanceParams& g, const PropulsionParams& p);
    }
    namespace ShaderGen {
        ShaderHandle compileTrailShader(const PropulsionParams& p);
    }
    namespace ParticleGen {
        ParticleHandle buildEngineExhaust(const PropulsionParams& p);
    }
    namespace AudioGen {
        AudioHandle loadHumAudio(const PropulsionParams& p);
    }
    namespace GuidanceSim {
        SimulationHandle setup(const GuidanceParams& g, const TargetParams& t);
    }
    namespace PropulsionSim {
        SimulationHandle setup(const PropulsionParams& p);
    }
};

// ============================================================================
// SHARD-BURST GRENADE FACTORY
// ============================================================================

class ShardGrenadeFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    ShardGrenadeFactory() = default;
    ~ShardGrenadeFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<ShardBundle> generateAsync(
        const GrenadeParams& grenade,
        const ShardParams& shard);

private:
    // Generator modules
    namespace MeshGen {
        MeshHandle buildGrenadeBody(const GrenadeParams& g);
        std::vector<MeshHandle> generateShards(const ShardParams& s, int count);
    }
    namespace FragmentGen {
        std::vector<MeshHandle> generateShards(const ShardParams& s, const GrenadeParams& g);
    }
    namespace TimerSim {
        SimulationHandle setup(const GrenadeParams& g);
    }
    namespace VFXGen {
        ParticleHandle buildBlast(const GrenadeParams& g);
    }
    namespace AudioGen {
        AudioHandle loadExplosionAudio(const GrenadeParams& g);
    }
};

// ============================================================================
// ARC BEAM FACTORY
// ============================================================================

class ArcBeamFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    ArcBeamFactory() = default;
    ~ArcBeamFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<BeamBundle> generateAsync(
        const BeamParams& beam,
        const GlowParams& glow);

private:
    // Generator modules
    namespace BeamGen {
        MeshHandle createSegments(const BeamParams& b);
    }
    namespace ArcSim {
        SimulationHandle setup(const BeamParams& b);
    }
    namespace ShaderGen {
        ShaderHandle compileBeamShader(const GlowParams& g);
    }
    namespace AudioGen {
        AudioHandle loadCrackleAudio(const BeamParams& b);
    }
};

// ============================================================================
// BOOMERANG FACTORY
// ============================================================================

class BoomerangFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    BoomerangFactory() = default;
    ~BoomerangFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<BoomerangBundle> generateAsync(const BoomerangParams& params);

private:
    // Generator modules
    namespace MeshGen {
        MeshHandle buildBoomerangBlade(const BoomerangParams& b);
    }
    namespace BoomerangSim {
        SimulationHandle setup(const BoomerangParams& b);
    }
    namespace AudioGen {
        AudioHandle loadWhooshAudio(const BoomerangParams& b);
    }
    namespace VFXGen {
        ParticleHandle buildTrailVFX(const BoomerangParams& b);
    }
};

// ============================================================================
// GRAPNEL FACTORY
// ============================================================================

class GrapnelFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    GrapnelFactory() = default;
    ~GrapnelFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<GrapnelBundle> generateAsync(
        const GrapnelParams& grapnel,
        const HookParams& hook);

private:
    // Generator modules
    namespace MeshGen {
        MeshHandle buildGrapnelHook(const HookParams& h);
    }
    namespace TetherGen {
        TetherHandle createRope(const GrapnelParams& g);
    }
    namespace ProjectileSim {
        SimulationHandle setupLinear(const GrapnelParams& g);
    }
    namespace ReelSim {
        SimulationHandle setup(const GrapnelParams& g);
    }
    namespace AudioGen {
        AudioHandle loadReelAudio(const GrapnelParams& g);
    }
};

// ============================================================================
// GLOBAL FACTORY MANAGER
// ============================================================================

class AdvancedProjectileManager {
    std::unique_ptr<GuidedMissileFactory> m_missileFactory;
    std::unique_ptr<ShardGrenadeFactory> m_grenadeFactory;
    std::unique_ptr<ArcBeamFactory> m_beamFactory;
    std::unique_ptr<BoomerangFactory> m_boomerangFactory;
    std::unique_ptr<GrapnelFactory> m_grapnelFactory;

public:
    AdvancedProjectileManager();
    ~AdvancedProjectileManager();

    void initialize(size_t num_threads);
    void shutdown();

    // Factory accessors
    GuidedMissileFactory* getMissileFactory() { return m_missileFactory.get(); }
    ShardGrenadeFactory* getGrenadeFactory() { return m_grenadeFactory.get(); }
    ArcBeamFactory* getBeamFactory() { return m_beamFactory.get(); }
    BoomerangFactory* getBoomerangFactory() { return m_boomerangFactory.get(); }
    GrapnelFactory* getGrapnelFactory() { return m_grapnelFactory.get(); }
};

} // namespace AdvancedProjectiles
} // namespace MagiTech 
