#include "ProjectileLuaBindings.hpp"
#include "ProjectileFactory.hpp"
#include "ProjectileTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Projectiles {

static std::vector<std::pair<std::future<ProjectileBundle>, std::string>> pendingProjectiles;
static std::map<std::string, ProjectileBundle> loadedProjectiles;

void ProjectileLuaBindings::bind(sol::state& lua) {
    // Bind ProjectileParams with all properties
    lua.new_usertype<ProjectileParams>("ProjectileParams",
        sol::constructors<ProjectileParams()>(),
        "id", &ProjectileParams::id,
        "projType", &ProjectileParams::projType,
        "length", &ProjectileParams::length,
        "radius", &ProjectileParams::radius,
        "colorCore", &ProjectileParams::colorCore,
        "colorEdge", &ProjectileParams::colorEdge,
        "shapeDetail", &ProjectileParams::shapeDetail,
        "trailEffect", &ProjectileParams::trailEffect,
        "trailLength", &ProjectileParams::trailLength,
        "impactEffect", &ProjectileParams::impactEffect,
        "speed", &ProjectileParams::speed,
        "gravityInfluence", &ProjectileParams::gravityInfluence,
        "damageType", &ProjectileParams::damageType,
        "fragmentationCount", &ProjectileParams::fragmentationCount,
        "homingStrength", &ProjectileParams::homingStrength
    );

    // Function to spawn projectiles asynchronously
    lua.set_function("spawn_proj", [&](ProjectileParams p) {
        auto factory = MainPlugin::instance().getProjectileFactory();
        if (!factory) {
            Log::error("ProjectileFactory not available");
            return;
        }
        
        auto fut = factory->generateAsync(p);
        pendingProjectiles.emplace_back(std::move(fut), p.id);
        Log::info("Queued projectile generation for: {}", p.id);
    });

    // Function to create predefined projectile types
    lua.set_function("create_fireball", [&](std::string id, float radius, float speed) {
        ProjectileParams p;
        p.id = id;
        p.projType = "fireball";
        p.radius = radius;
        p.length = radius * 2.0f;
        p.speed = speed;
        p.colorCore = glm::vec3(1.0f, 0.3f, 0.0f);
        p.colorEdge = glm::vec3(1.0f, 0.8f, 0.2f);
        p.shapeDetail = 1;
        p.trailEffect = "ember_trail";
        p.trailLength = 0.75f;
        p.impactEffect = "explosion_small";
        p.damageType = "fire";
        p.gravityInfluence = 0.0f;
        p.fragmentationCount = 0;
        p.homingStrength = 0.0f;
        
        spawn_proj(p);
    });

    lua.set_function("create_arrow", [&](std::string id, float length, float speed) {
        ProjectileParams p;
        p.id = id;
        p.projType = "arrow";
        p.length = length;
        p.radius = length * 0.05f;
        p.speed = speed;
        p.colorCore = glm::vec3(0.8f, 0.6f, 0.4f);
        p.colorEdge = glm::vec3(0.6f, 0.4f, 0.2f);
        p.shapeDetail = 1;
        p.trailEffect = "";
        p.trailLength = 0.0f;
        p.impactEffect = "arrow_impact";
        p.damageType = "physical";
        p.gravityInfluence = 1.0f;
        p.fragmentationCount = 0;
        p.homingStrength = 0.0f;
        
        spawn_proj(p);
    });

    lua.set_function("create_laser", [&](std::string id, float length, float speed) {
        ProjectileParams p;
        p.id = id;
        p.projType = "laser";
        p.length = length;
        p.radius = 0.02f;
        p.speed = speed;
        p.colorCore = glm::vec3(0.2f, 0.8f, 1.0f);
        p.colorEdge = glm::vec3(0.8f, 0.9f, 1.0f);
        p.shapeDetail = 0;
        p.trailEffect = "laser_trail";
        p.trailLength = 0.5f;
        p.impactEffect = "laser_impact";
        p.damageType = "energy";
        p.gravityInfluence = 0.0f;
        p.fragmentationCount = 0;
        p.homingStrength = 0.0f;
        
        spawn_proj(p);
    });

    lua.set_function("create_bolt", [&](std::string id, float length, float speed) {
        ProjectileParams p;
        p.id = id;
        p.projType = "bolt";
        p.length = length;
        p.radius = length * 0.1f;
        p.speed = speed;
        p.colorCore = glm::vec3(0.8f, 0.2f, 0.8f);
        p.colorEdge = glm::vec3(1.0f, 0.6f, 1.0f);
        p.shapeDetail = 1;
        p.trailEffect = "arcane_trail";
        p.trailLength = 1.0f;
        p.impactEffect = "arcane_explosion";
        p.damageType = "arcane";
        p.gravityInfluence = 0.2f;
        p.fragmentationCount = 3;
        p.homingStrength = 0.3f;
        
        spawn_proj(p);
    });

    // Function to check if projectile is ready
    lua.set_function("is_projectile_ready", [&](std::string id) {
        return loadedProjectiles.find(id) != loadedProjectiles.end();
    });

    // Function to get projectile bundle
    lua.set_function("get_projectile", [&](std::string id) {
        auto it = loadedProjectiles.find(id);
        if (it != loadedProjectiles.end()) {
            return it->second;
        }
        return ProjectileBundle{};
    });

    // Function to clear projectile cache
    lua.set_function("clear_projectile_cache", [&]() {
        loadedProjectiles.clear();
        Log::info("Projectile cache cleared");
    });
}

void ProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                loadedProjectiles[it->second] = bundle;
                
                // Call Lua callback if available
                if (lua["on_projectile_ready"]) {
                    lua["on_projectile_ready"](it->second, bundle);
                }
                
                Log::info("Projectile ready: {}", it->second);
                it = pendingProjectiles.erase(it);
            }
            catch (const std::exception& e) {
                Log::error("Failed to load projectile {}: {}", it->second, e.what());
                it = pendingProjectiles.erase(it);
            }
        } else {
            ++it;
        }
    }
}

} // namespace Projectiles
} // namespace MagiTech
