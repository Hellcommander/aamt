#pragma once

#include <future>
#include <memory>
#include <vector>
#include "GeneratorConcurrency.hpp"
#include "AdvancedProjectileTypes.hpp"

namespace MagiTech {
namespace AdvancedProjectiles {

// ============================================================================
// GUIDED MISSILE FACTORY
// ============================================================================

class GuidedMissileFactory {
    GeneratorTaskPool m_pool;
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
    struct MeshGen {
        static MeshHandle buildMissileMesh(const GuidanceParams& g, const PropulsionParams& p);
    };
    struct ShaderGen {
        static ShaderHandle compileTrailShader(const PropulsionParams& p);
    };
    struct ParticleGen {
        static ParticleHandle buildEngineExhaust(const PropulsionParams& p);
    };
    struct AudioGen {
        static AudioHandle loadHumAudio(const PropulsionParams& p);
    };
    struct GuidanceSim {
        static SimulationHandle setup(const GuidanceParams& g, const TargetParams& t);
    };
    struct PropulsionSim {
        static SimulationHandle setup(const PropulsionParams& p);
    };
};

// ============================================================================
// SHARD-BURST GRENADE FACTORY
// ============================================================================

class ShardGrenadeFactory {
    GeneratorTaskPool m_pool;
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
    struct MeshGen {
        static MeshHandle buildGrenadeBody(const GrenadeParams& g);
        /** Builds `count` shard meshes, each oriented inside a cone of `spreadAngleDeg`. */
        static std::vector<MeshHandle> generateShards(const ShardParams& s, int count, float spreadAngleDeg);
    };
    struct FragmentGen {
        static std::vector<MeshHandle> generateShards(const ShardParams& s, const GrenadeParams& g);
    };
    struct TimerSim {
        static SimulationHandle setup(const GrenadeParams& g);
    };
    struct VFXGen {
        static ParticleHandle buildBlast(const GrenadeParams& g);
    };
    struct AudioGen {
        static AudioHandle loadExplosionAudio(const GrenadeParams& g);
    };
};

// ============================================================================
// ARC BEAM FACTORY
// ============================================================================

class ArcBeamFactory {
    GeneratorTaskPool m_pool;
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
    struct BeamGen {
        static MeshHandle createSegments(const BeamParams& b);
    };
    struct ArcSim {
        static SimulationHandle setup(const BeamParams& b);
    };
    struct ShaderGen {
        static ShaderHandle compileBeamShader(const GlowParams& g);
    };
    struct AudioGen {
        static AudioHandle loadCrackleAudio(const BeamParams& b);
    };
};

// ============================================================================
// BOOMERANG FACTORY
// ============================================================================

class BoomerangFactory {
    GeneratorTaskPool m_pool;
    bool m_initialized = false;

public:
    BoomerangFactory() = default;
    ~BoomerangFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<BoomerangBundle> generateAsync(const BoomerangParams& params);

private:
    // Generator modules
    struct MeshGen {
        static MeshHandle buildBoomerangBlade(const BoomerangParams& b);
    };
    struct BoomerangSim {
        static SimulationHandle setup(const BoomerangParams& b);
    };
    struct AudioGen {
        static AudioHandle loadWhooshAudio(const BoomerangParams& b);
    };
    struct VFXGen {
        static ParticleHandle buildTrailVFX(const BoomerangParams& b);
    };
};

// ============================================================================
// GRAPNEL FACTORY
// ============================================================================

class GrapnelFactory {
    GeneratorTaskPool m_pool;
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
    struct MeshGen {
        static MeshHandle buildGrapnelHook(const HookParams& h);
    };
    struct TetherGen {
        static TetherHandle createRope(const GrapnelParams& g);
    };
    struct ProjectileSim {
        static SimulationHandle setupLinear(const GrapnelParams& g);
    };
    struct ReelSim {
        static SimulationHandle setup(const GrapnelParams& g);
    };
    struct AudioGen {
        static AudioHandle loadReelAudio(const GrapnelParams& g);
    };
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

    AdvancedProjectileManager(const AdvancedProjectileManager&) = delete;
    AdvancedProjectileManager& operator=(const AdvancedProjectileManager&) = delete;

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
