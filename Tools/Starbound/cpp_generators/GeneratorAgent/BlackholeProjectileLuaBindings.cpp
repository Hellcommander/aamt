#include "BlackholeProjectileLuaBindings.hpp"
#include "BlackholeProjectileFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "core/Log.hpp"
#include <vector>
#include <chrono>
#include <memory>

namespace MagiTech {
namespace BlackholeProjectiles {

static std::vector<std::pair<std::future<BlackholeAssetBundle>, std::string>> pendingProjectiles;
static std::unique_ptr<BlackholeProjectileFactory> g_factory;

// Initialize the factory if not already done
static BlackholeProjectileFactory* getFactory() {
    if (!g_factory) {
        g_factory = std::make_unique<BlackholeProjectileFactory>();
        g_factory->initialize(1000, 4); // 1000 cache entries, 4 threads
        Log::info("BlackholeProjectileFactory initialized");
    }
    return g_factory.get();
}

void BlackholeProjectileLuaBindings::bind(sol::state& lua) {
    // Bind the parameter struct with all properties
    lua.new_usertype<BlackholeProjectileParams>("BlackholeProjectileParams",
        sol::constructors<BlackholeProjectileParams()>(),
        "id", &BlackholeProjectileParams::id,
        "coreRadius", &BlackholeProjectileParams::coreRadius,
        "diskInnerRadius", &BlackholeProjectileParams::diskInnerRadius,
        "diskOuterRadius", &BlackholeProjectileParams::diskOuterRadius,
        "diskTilt", &BlackholeProjectileParams::diskTilt,
        "warpIntensity", &BlackholeProjectileParams::warpIntensity,
        "warpScale", &BlackholeProjectileParams::warpScale,
        "spinSpeed", &BlackholeProjectileParams::spinSpeed,
        "trailLength", &BlackholeProjectileParams::trailLength,
        "particleVortexCount", &BlackholeProjectileParams::particleVortexCount,
        "vortexLifetime", &BlackholeProjectileParams::vortexLifetime,
        "starSuckRadius", &BlackholeProjectileParams::starSuckRadius,
        "starAbsorbColor", &BlackholeProjectileParams::starAbsorbColor,
        "lensFlareIntensity", &BlackholeProjectileParams::lensFlareIntensity,
        "soundDepth", &BlackholeProjectileParams::soundDepth,
        "soundPitch", &BlackholeProjectileParams::soundPitch,
        // Add utility methods
        "validate", [](const BlackholeProjectileParams& p) -> bool {
            return p.coreRadius > 0 && p.diskInnerRadius > 0 && p.diskOuterRadius > p.diskInnerRadius;
        },
        "getHash", [](const BlackholeProjectileParams& p) -> uint64_t {
            return p.hashKey();
        }
    );

    // Bind the asset bundle struct
    lua.new_usertype<BlackholeAssetBundle>("BlackholeAssetBundle",
        sol::no_constructor,
        "coreMesh", &BlackholeAssetBundle::coreMesh,
        "diskMesh", &BlackholeAssetBundle::diskMesh,
        "trailMesh", &BlackholeAssetBundle::trailMesh,
        "warpShader", &BlackholeAssetBundle::warpShader,
        "diskTexture", &BlackholeAssetBundle::diskTexture,
        "vortexParticles", &BlackholeAssetBundle::vortexParticles,
        "sfx", &BlackholeAssetBundle::sfx,
        // Add utility methods
        "isValid", [](const BlackholeAssetBundle& b) -> bool {
            return b.coreMesh != 0 && b.diskMesh != 0 && b.warpShader != 0;
        },
        "getAssetCount", [](const BlackholeAssetBundle& b) -> int {
            int count = 0;
            if (b.coreMesh) count++;
            if (b.diskMesh) count++;
            if (b.trailMesh) count++;
            if (b.warpShader) count++;
            if (b.diskTexture) count++;
            if (b.vortexParticles) count++;
            if (b.sfx) count++;
            return count;
        }
    );

    // Main generation function
    lua.set_function("spawn_blackhole_projectile",
        [&](const BlackholeProjectileParams& p) -> BlackholeAssetBundle {
            try {
                auto factory = getFactory();
                
                // Validate parameters
                if (!p.validate()) {
                    Log::error("Invalid blackhole projectile parameters for: {}", p.id);
                    return BlackholeAssetBundle{}; // Return empty bundle
                }
                
                Log::info("Generating blackhole projectile: {}", p.id);
                auto future = factory->generateAsync(p);
                auto bundle = future.get();
                
                Log::info("Blackhole projectile generated successfully: {} ({} assets)", 
                         p.id, bundle.getAssetCount());
                return bundle;
            } catch (const std::exception& e) {
                Log::error("Error generating blackhole projectile {}: {}", p.id, e.what());
                return BlackholeAssetBundle{}; // Return empty bundle on error
            }
        }
    );

    // Async generation function
    lua.set_function("spawn_blackhole_projectile_async",
        [&](const BlackholeProjectileParams& p) -> bool {
            try {
                auto factory = getFactory();
                
                if (!p.validate()) {
                    Log::error("Invalid blackhole projectile parameters for: {}", p.id);
                    return false;
                }
                
                auto fut = factory->generateAsync(p);
                pendingProjectiles.emplace_back(std::move(fut), p.id);
                Log::info("Queued async blackhole projectile generation: {}", p.id);
                return true;
            } catch (const std::exception& e) {
                Log::error("Error queuing blackhole projectile {}: {}", p.id, e.what());
                return false;
            }
        }
    );

    // Utility functions for parameter creation
    lua.set_function("create_void_spiral_params", []() -> BlackholeProjectileParams {
        BlackholeProjectileParams p;
        p.id = "void_spiral";
        p.coreRadius = 0.5f;
        p.diskInnerRadius = 0.6f;
        p.diskOuterRadius = 1.2f;
        p.diskTilt = 15.0f;
        p.warpIntensity = 1.0f;
        p.warpScale = 2.5f;
        p.spinSpeed = 2.0f;
        p.trailLength = 1.5f;
        p.particleVortexCount = 80;
        p.vortexLifetime = 1.0f;
        p.starSuckRadius = 2.0f;
        p.starAbsorbColor = {0.0f, 0.0f, 0.0f, 1.0f};
        p.lensFlareIntensity = 1.5f;
        p.soundDepth = 0.8f;
        p.soundPitch = 0.5f;
        return p;
    });

    lua.set_function("create_void_maelstrom_params", []() -> BlackholeProjectileParams {
        BlackholeProjectileParams p;
        p.id = "void_maelstrom";
        p.coreRadius = 0.7f;
        p.diskInnerRadius = 0.8f;
        p.diskOuterRadius = 1.5f;
        p.diskTilt = 20.0f;
        p.warpIntensity = 1.2f;
        p.warpScale = 3.5f;
        p.spinSpeed = 3.0f;
        p.trailLength = 2.0f;
        p.particleVortexCount = 120;
        p.vortexLifetime = 1.2f;
        p.starSuckRadius = 3.0f;
        p.starAbsorbColor = {0.0f, 0.0f, 0.0f, 1.0f};
        p.lensFlareIntensity = 2.0f;
        p.soundDepth = 0.6f;
        p.soundPitch = 0.4f;
        return p;
    });

    lua.set_function("create_singularity_params", []() -> BlackholeProjectileParams {
        BlackholeProjectileParams p;
        p.id = "singularity";
        p.coreRadius = 1.0f;
        p.diskInnerRadius = 1.2f;
        p.diskOuterRadius = 2.0f;
        p.diskTilt = 25.0f;
        p.warpIntensity = 1.5f;
        p.warpScale = 4.0f;
        p.spinSpeed = 4.0f;
        p.trailLength = 3.0f;
        p.particleVortexCount = 200;
        p.vortexLifetime = 1.5f;
        p.starSuckRadius = 4.0f;
        p.starAbsorbColor = {0.0f, 0.0f, 0.0f, 1.0f};
        p.lensFlareIntensity = 3.0f;
        p.soundDepth = 1.0f;
        p.soundPitch = 0.3f;
        return p;
    });

    // Parameter validation and utility functions
    lua.set_function("validate_blackhole_params", [](const BlackholeProjectileParams& p) -> sol::table {
        sol::table result = lua.create_table();
        
        bool isValid = true;
        std::vector<std::string> errors;
        
        if (p.coreRadius <= 0) {
            errors.push_back("coreRadius must be positive");
            isValid = false;
        }
        
        if (p.diskInnerRadius <= 0) {
            errors.push_back("diskInnerRadius must be positive");
            isValid = false;
        }
        
        if (p.diskOuterRadius <= p.diskInnerRadius) {
            errors.push_back("diskOuterRadius must be greater than diskInnerRadius");
            isValid = false;
        }
        
        if (p.diskTilt < -90 || p.diskTilt > 90) {
            errors.push_back("diskTilt must be between -90 and 90 degrees");
            isValid = false;
        }
        
        if (p.warpIntensity < 0) {
            errors.push_back("warpIntensity must be non-negative");
            isValid = false;
        }
        
        if (p.warpScale <= 0) {
            errors.push_back("warpScale must be positive");
            isValid = false;
        }
        
        if (p.spinSpeed < 0) {
            errors.push_back("spinSpeed must be non-negative");
            isValid = false;
        }
        
        if (p.trailLength < 0) {
            errors.push_back("trailLength must be non-negative");
            isValid = false;
        }
        
        if (p.particleVortexCount < 0) {
            errors.push_back("particleVortexCount must be non-negative");
            isValid = false;
        }
        
        if (p.vortexLifetime <= 0) {
            errors.push_back("vortexLifetime must be positive");
            isValid = false;
        }
        
        if (p.starSuckRadius < 0) {
            errors.push_back("starSuckRadius must be non-negative");
            isValid = false;
        }
        
        if (p.lensFlareIntensity < 0) {
            errors.push_back("lensFlareIntensity must be non-negative");
            isValid = false;
        }
        
        if (p.soundDepth < 0 || p.soundDepth > 1) {
            errors.push_back("soundDepth must be between 0 and 1");
            isValid = false;
        }
        
        if (p.soundPitch <= 0) {
            errors.push_back("soundPitch must be positive");
            isValid = false;
        }
        
        result["valid"] = isValid;
        result["errors"] = errors;
        
        return result;
    });

    // Factory management functions
    lua.set_function("initialize_blackhole_factory", [](size_t cache_size, size_t num_threads) -> bool {
        try {
            if (!g_factory) {
                g_factory = std::make_unique<BlackholeProjectileFactory>();
            }
            g_factory->initialize(cache_size, num_threads);
            Log::info("BlackholeProjectileFactory initialized with cache_size={}, threads={}", 
                     cache_size, num_threads);
            return true;
        } catch (const std::exception& e) {
            Log::error("Error initializing BlackholeProjectileFactory: {}", e.what());
            return false;
        }
    });

    lua.set_function("shutdown_blackhole_factory", []() {
        if (g_factory) {
            g_factory->shutdown();
            Log::info("BlackholeProjectileFactory shutdown");
        }
    });

    // Cache management
    lua.set_function("get_blackhole_cache_stats", []() -> sol::table {
        sol::table stats = lua.create_table();
        if (g_factory) {
            // Note: This would require adding cache statistics to the factory
            stats["initialized"] = true;
        } else {
            stats["initialized"] = false;
        }
        return stats;
    });

    Log::info("BlackholeProjectileLuaBindings bound successfully");
}

void BlackholeProjectileLuaBindings::poll_assets(sol::state& lua) {
    auto start = std::chrono::steady_clock::now();
    int completed = 0;
    
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Blackhole projectile ready: {} ({} assets)", 
                         it->second, bundle.getAssetCount());
                
                // Call Lua callback if available
                if (lua["on_blackhole_ready"]) {
                    lua["on_blackhole_ready"](it->second, bundle);
                }
                
                completed++;
            } catch (const std::exception& e) {
                Log::error("Error getting blackhole projectile {}: {}", it->second, e.what());
            }
            it = pendingProjectiles.erase(it);
        } else {
            ++it;
        }
    }
    
    if (completed > 0) {
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
        Log::info("Completed {} blackhole projectiles in {}ms", completed, duration.count());
    }
}

void BlackholeProjectileLuaBindings::cleanup() {
    if (g_factory) {
        g_factory->shutdown();
        g_factory.reset();
    }
    pendingProjectiles.clear();
    Log::info("BlackholeProjectileLuaBindings cleaned up");
}

} // namespace BlackholeProjectiles
} // namespace MagiTech
