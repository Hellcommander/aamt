#pragma once

#include <sol/sol.hpp>
#include "AdvancedProjectileTypes.hpp"
#include "AdvancedProjectileFactories.hpp"
#include <memory>
#include <vector>

namespace MagiTech {
namespace AdvancedProjectiles {

class AdvancedProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    
private:
    static std::unique_ptr<AdvancedProjectileManager> g_manager;
    
    // Pending asset tracking
    static std::vector<std::pair<std::future<MissileBundle>, std::string>> pendingMissiles;
    static std::vector<std::pair<std::future<ShardBundle>, std::string>> pendingGrenades;
    static std::vector<std::pair<std::future<BeamBundle>, std::string>> pendingBeams;
    static std::vector<std::pair<std::future<BoomerangBundle>, std::string>> pendingBoomerangs;
    static std::vector<std::pair<std::future<GrapnelBundle>, std::string>> pendingGrapnels;
    
    // Validation functions
    static bool validateGuidanceParams(const GuidanceParams& p);
    static bool validatePropulsionParams(const PropulsionParams& p);
    static bool validateTargetParams(const TargetParams& p);
    static bool validateGrenadeParams(const GrenadeParams& p);
    static bool validateShardParams(const ShardParams& p);
    static bool validateBeamParams(const BeamParams& p);
    static bool validateGlowParams(const GlowParams& p);
    static bool validateBoomerangParams(const BoomerangParams& p);
    static bool validateGrapnelParams(const GrapnelParams& p);
    static bool validateHookParams(const HookParams& p);
    
    // Utility functions
    static GuidanceParams createDefaultGuidance();
    static PropulsionParams createDefaultPropulsion();
    static TargetParams createDefaultTarget();
    static GrenadeParams createDefaultGrenade();
    static ShardParams createDefaultShard();
    static BeamParams createDefaultBeam();
    static GlowParams createDefaultGlow();
    static BoomerangParams createDefaultBoomerang();
    static GrapnelParams createDefaultGrapnel();
    static HookParams createDefaultHook();
};

} // namespace AdvancedProjectiles
} // namespace MagiTech 
