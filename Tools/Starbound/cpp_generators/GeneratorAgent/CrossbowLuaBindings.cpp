#include "CrossbowLuaBindings.hpp"
#include "CrossbowAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "core/Log.hpp"
#include <vector>
#include <memory>

namespace MagiTech {
namespace Crossbows {

static std::vector<std::pair<std::future<CrossbowBundle>, std::string>> pendingCrossbows;
static std::vector<std::pair<std::future<ProjectileBundle>, std::string>> pendingProjectiles;
static std::unique_ptr<CrossbowAssetFactory> g_factory;

void CrossbowLuaBindings::bind(sol::state& lua) {
    // Initialize factory if not already done
    if (!g_factory) {
        g_factory = std::make_unique<CrossbowAssetFactory>();
        g_factory->initialize(4); // 4 threads for asset generation
    }

    // Parameter type bindings with validation
    lua.new_usertype<CrossbowParams>("CrossbowParams", sol::constructors<CrossbowParams()>(),
        "id", &CrossbowParams::id, 
        "drawLength", &CrossbowParams::drawLength, 
        "drawWeight", &CrossbowParams::drawWeight,
        "autoReload", &CrossbowParams::autoReload, 
        "reloadTime", &CrossbowParams::reloadTime, 
        "stockMaterial", &CrossbowParams::stockMaterial,
        "limbMaterial", &CrossbowParams::limbMaterial, 
        "stringMaterial", &CrossbowParams::stringMaterial,
        "validate", [](CrossbowParams& p) -> bool {
            if (p.id.empty()) {
                Log::error("CrossbowParams: id cannot be empty");
                return false;
            }
            if (p.drawLength <= 0.0f || p.drawLength > 2.0f) {
                Log::error("CrossbowParams: drawLength must be between 0.1 and 2.0");
                return false;
            }
            if (p.drawWeight <= 0.0f || p.drawWeight > 1000.0f) {
                Log::error("CrossbowParams: drawWeight must be between 10 and 1000");
                return false;
            }
            if (p.reloadTime <= 0.0f || p.reloadTime > 10.0f) {
                Log::error("CrossbowParams: reloadTime must be between 0.1 and 10.0");
                return false;
            }
            return true;
        });

    lua.new_usertype<BoltParams>("BoltParams", sol::constructors<BoltParams()>(),
        "id", &BoltParams::id, 
        "length", &BoltParams::length, 
        "shaftRadius", &BoltParams::shaftRadius,
        "useFletching", &BoltParams::useFletching, 
        "fletchMaterial", &BoltParams::fletchMaterial, 
        "fletchLength", &BoltParams::fletchLength,
        "tipMass", &BoltParams::tipMass, 
        "barbedTip", &BoltParams::barbedTip,
        "validate", [](BoltParams& p) -> bool {
            if (p.id.empty()) {
                Log::error("BoltParams: id cannot be empty");
                return false;
            }
            if (p.length <= 0.0f || p.length > 1.0f) {
                Log::error("BoltParams: length must be between 0.1 and 1.0");
                return false;
            }
            if (p.shaftRadius <= 0.0f || p.shaftRadius > 0.02f) {
                Log::error("BoltParams: shaftRadius must be between 0.001 and 0.02");
                return false;
            }
            if (p.tipMass <= 0.0f || p.tipMass > 0.1f) {
                Log::error("BoltParams: tipMass must be between 0.001 and 0.1");
                return false;
            }
            return true;
        });

    lua.new_usertype<ArrowParams>("ArrowParams", sol::constructors<ArrowParams()>(),
        "id", &ArrowParams::id, 
        "shaftLength", &ArrowParams::shaftLength, 
        "shaftDiameter", &ArrowParams::shaftDiameter,
        "spineRating", &ArrowParams::spineRating, 
        "useFletching", &ArrowParams::useFletching, 
        "fletchStyle", &ArrowParams::fletchStyle,
        "nockSize", &ArrowParams::nockSize, 
        "tipMass", &ArrowParams::tipMass,
        "validate", [](ArrowParams& p) -> bool {
            if (p.id.empty()) {
                Log::error("ArrowParams: id cannot be empty");
                return false;
            }
            if (p.shaftLength <= 0.0f || p.shaftLength > 2.0f) {
                Log::error("ArrowParams: shaftLength must be between 0.5 and 2.0");
                return false;
            }
            if (p.shaftDiameter <= 0.0f || p.shaftDiameter > 0.02f) {
                Log::error("ArrowParams: shaftDiameter must be between 0.002 and 0.02");
                return false;
            }
            if (p.spineRating <= 0 || p.spineRating > 2000) {
                Log::error("ArrowParams: spineRating must be between 100 and 2000");
                return false;
            }
            if (p.tipMass <= 0.0f || p.tipMass > 0.05f) {
                Log::error("ArrowParams: tipMass must be between 0.005 and 0.05");
                return false;
            }
            return true;
        });
        
    lua.new_usertype<CrossbowBundle>("CrossbowBundle", sol::no_constructor,
        "mesh", &CrossbowBundle::mesh, 
        "string", &CrossbowBundle::string, 
        "reloadAnim", &CrossbowBundle::reloadAnim, 
        "materials", &CrossbowBundle::materials);

    lua.new_usertype<ProjectileBundle>("ProjectileBundle", sol::no_constructor,
        "mesh", &ProjectileBundle::mesh, 
        "material", &ProjectileBundle::material, 
        "vfxTrail", &ProjectileBundle::vfxTrail,
        "flightSim", &ProjectileBundle::flightSim, 
        "collider", &ProjectileBundle::collider);

    // Main generation functions with validation (Async)
    lua.set_function("spawn_crossbow", [&](const CrossbowParams& p) -> bool {
        if (!p.validate()) return false;
        
        try {
            pendingCrossbows.emplace_back(g_factory->generateCrossbowAsync(p), p.id);
            Log::info("Crossbow generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn crossbow {}: {}", p.id, e.what());
            return false;
        }
    });

    lua.set_function("spawn_bolt", [&](const BoltParams& p) -> bool {
        if (!p.validate()) return false;
        
        try {
            pendingProjectiles.emplace_back(g_factory->generateBoltAsync(p), p.id);
            Log::info("Bolt generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn bolt {}: {}", p.id, e.what());
            return false;
        }
    });

    lua.set_function("spawn_arrow", [&](const ArrowParams& p) -> bool {
        if (!p.validate()) return false;
        
        try {
            pendingProjectiles.emplace_back(g_factory->generateArrowAsync(p), p.id);
            Log::info("Arrow generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn arrow {}: {}", p.id, e.what());
            return false;
        }
    });

    // Synchronous factory methods for immediate access
    lua.set_function("generate_crossbow", [&](const CrossbowParams& p) -> CrossbowBundle {
        if (!p.validate()) {
            Log::error("Invalid crossbow parameters for {}", p.id);
            return CrossbowBundle{};
        }
        
        try {
            return g_factory->generateCrossbow(p);
        } catch (const std::exception& e) {
            Log::error("Failed to generate crossbow {}: {}", p.id, e.what());
            return CrossbowBundle{};
        }
    });

    lua.set_function("generate_bolt", [&](const BoltParams& p) -> ProjectileBundle {
        if (!p.validate()) {
            Log::error("Invalid bolt parameters for {}", p.id);
            return ProjectileBundle{};
        }
        
        try {
            return g_factory->generateBolt(p);
        } catch (const std::exception& e) {
            Log::error("Failed to generate bolt {}: {}", p.id, e.what());
            return ProjectileBundle{};
        }
    });

    lua.set_function("generate_arrow", [&](const ArrowParams& p) -> ProjectileBundle {
        if (!p.validate()) {
            Log::error("Invalid arrow parameters for {}", p.id);
            return ProjectileBundle{};
        }
        
        try {
            return g_factory->generateArrow(p);
        } catch (const std::exception& e) {
            Log::error("Failed to generate arrow {}: {}", p.id, e.what());
            return ProjectileBundle{};
        }
    });

    // Cache management functions
    lua.set_function("clear_crossbow_cache", [&]() {
        g_factory->clearCache();
        Log::info("Cleared crossbow asset cache");
    });

    lua.set_function("get_cache_size", [&]() -> size_t {
        return g_factory->getCacheSize();
    });

    // Utility functions for common configurations
    lua.set_function("create_light_crossbow", []() -> CrossbowParams {
        CrossbowParams p;
        p.id = "light_crossbow";
        p.drawLength = 0.4f;
        p.drawWeight = 200.0f;
        p.autoReload = true;
        p.reloadTime = 0.8f;
        p.stockMaterial = "WoodOak";
        p.limbMaterial = "Fiberglass";
        p.stringMaterial = "Synthetic";
        return p;
    });

    lua.set_function("create_heavy_crossbow", []() -> CrossbowParams {
        CrossbowParams p;
        p.id = "heavy_crossbow";
        p.drawLength = 0.7f;
        p.drawWeight = 500.0f;
        p.autoReload = false;
        p.reloadTime = 2.5f;
        p.stockMaterial = "MetalSteel";
        p.limbMaterial = "CarbonFiber";
        p.stringMaterial = "Kevlar";
        return p;
    });

    lua.set_function("create_steel_bolt", []() -> BoltParams {
        BoltParams p;
        p.id = "steel_bolt";
        p.length = 0.35f;
        p.shaftRadius = 0.004f;
        p.useFletching = false;
        p.tipMass = 0.025f;
        p.barbedTip = true;
        return p;
    });

    lua.set_function("create_wood_arrow", []() -> ArrowParams {
        ArrowParams p;
        p.id = "wood_arrow";
        p.shaftLength = 1.0f;
        p.shaftDiameter = 0.008f;
        p.spineRating = 500;
        p.useFletching = true;
        p.fletchStyle = "Parabolic";
        p.nockSize = 0.018f;
        p.tipMass = 0.012f;
        return p;
    });

    // Status and management functions
    lua.set_function("get_pending_count", []() -> sol::table {
        sol::table result = lua.create_table();
        result["crossbows"] = pendingCrossbows.size();
        result["projectiles"] = pendingProjectiles.size();
        return result;
    });

    lua.set_function("clear_pending", []() {
        pendingCrossbows.clear();
        pendingProjectiles.clear();
        Log::info("Cleared all pending asset generations");
    });

    // Asset generation functions for complete OpenStarbound assets
    lua.set_function("generate_crossbow_assets", [&](const CrossbowParams& p, const sol::table& config) -> sol::table {
        if (!p.validate()) {
            Log::error("Invalid crossbow parameters for asset generation");
            return lua.create_table();
        }
        
        try {
            // Convert Lua table to ItemConfig
            CrossbowAssetGenerator::ItemConfig itemConfig;
            itemConfig.itemName = config.get<std::string>("itemName", "Crossbow");
            itemConfig.description = config.get<std::string>("description", "");
            itemConfig.rarity = config.get<std::string>("rarity", "Common");
            itemConfig.category = config.get<std::string>("category", "weapon");
            itemConfig.level = config.get<std::string>("level", "1");
            itemConfig.damageType = config.get<std::string>("damageType", "physical");
            itemConfig.damage = config.get<float>("damage", 10.0f);
            itemConfig.fireRate = config.get<float>("fireRate", 1.0f);
            itemConfig.abilityType = config.get<std::string>("abilityType", "crossbow");
            itemConfig.behaviorSystem = config.get<std::string>("behaviorSystem", "hybrid");
            itemConfig.effectSystem = config.get<std::string>("effectSystem", "projectile");
            itemConfig.materialSystem = config.get<std::string>("materialSystem", "magitech");
            
            // Get projectile types
            if (config.get_type() == sol::type::table) {
                auto projectileTypes = config.get<sol::table>("projectileTypes");
                if (projectileTypes.valid()) {
                    for (const auto& pair : projectileTypes) {
                        itemConfig.projectileTypes.push_back(pair.second.as<std::string>());
                    }
                }
            }
            
            // Get special effects
            if (config.get_type() == sol::type::table) {
                auto specialEffects = config.get<sol::table>("specialEffects");
                if (specialEffects.valid()) {
                    for (const auto& pair : specialEffects) {
                        itemConfig.specialEffects.push_back(pair.second.as<std::string>());
                    }
                }
            }
            
            // Generate assets
            auto output = g_assetGenerator->generateCrossbowAssets(p, itemConfig);
            
            // Return results as Lua table
            sol::table result = lua.create_table();
            result["itemFile"] = output.itemFile;
            result["framesFile"] = output.framesFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["behaviorFile"] = output.behaviorFile;
            result["effectFile"] = output.effectFile;
            
            Log::info("Generated crossbow assets: {}", p.id);
            return result;
            
        } catch (const std::exception& e) {
            Log::error("Failed to generate crossbow assets for {}: {}", p.id, e.what());
            return lua.create_table();
        }
    });

    lua.set_function("generate_bolt_assets", [&](const BoltParams& p, const sol::table& config) -> sol::table {
        if (!p.validate()) {
            Log::error("Invalid bolt parameters for asset generation");
            return lua.create_table();
        }
        
        try {
            // Convert Lua table to ItemConfig
            CrossbowAssetGenerator::ItemConfig itemConfig;
            itemConfig.itemName = config.get<std::string>("itemName", "Bolt");
            itemConfig.description = config.get<std::string>("description", "");
            itemConfig.rarity = config.get<std::string>("rarity", "Common");
            itemConfig.category = config.get<std::string>("category", "ammo");
            itemConfig.level = config.get<std::string>("level", "1");
            itemConfig.damageType = config.get<std::string>("damageType", "physical");
            itemConfig.damage = config.get<float>("damage", 5.0f);
            itemConfig.fireRate = config.get<float>("fireRate", 1.0f);
            itemConfig.abilityType = config.get<std::string>("abilityType", "projectile");
            itemConfig.effectSystem = config.get<std::string>("effectSystem", "projectile");
            
            // Get special effects
            if (config.get_type() == sol::type::table) {
                auto specialEffects = config.get<sol::table>("specialEffects");
                if (specialEffects.valid()) {
                    for (const auto& pair : specialEffects) {
                        itemConfig.specialEffects.push_back(pair.second.as<std::string>());
                    }
                }
            }
            
            // Generate assets
            auto output = g_assetGenerator->generateBoltAssets(p, itemConfig);
            
            // Return results as Lua table
            sol::table result = lua.create_table();
            result["projectileFile"] = output.projectileFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["effectFile"] = output.effectFile;
            
            Log::info("Generated bolt assets: {}", p.id);
            return result;
            
        } catch (const std::exception& e) {
            Log::error("Failed to generate bolt assets for {}: {}", p.id, e.what());
            return lua.create_table();
        }
    });

    lua.set_function("generate_arrow_assets", [&](const ArrowParams& p, const sol::table& config) -> sol::table {
        if (!p.validate()) {
            Log::error("Invalid arrow parameters for asset generation");
            return lua.create_table();
        }
        
        try {
            // Convert Lua table to ItemConfig
            CrossbowAssetGenerator::ItemConfig itemConfig;
            itemConfig.itemName = config.get<std::string>("itemName", "Arrow");
            itemConfig.description = config.get<std::string>("description", "");
            itemConfig.rarity = config.get<std::string>("rarity", "Common");
            itemConfig.category = config.get<std::string>("category", "ammo");
            itemConfig.level = config.get<std::string>("level", "1");
            itemConfig.damageType = config.get<std::string>("damageType", "physical");
            itemConfig.damage = config.get<float>("damage", 4.0f);
            itemConfig.fireRate = config.get<float>("fireRate", 1.0f);
            itemConfig.abilityType = config.get<std::string>("abilityType", "projectile");
            itemConfig.effectSystem = config.get<std::string>("effectSystem", "projectile");
            
            // Get special effects
            if (config.get_type() == sol::type::table) {
                auto specialEffects = config.get<sol::table>("specialEffects");
                if (specialEffects.valid()) {
                    for (const auto& pair : specialEffects) {
                        itemConfig.specialEffects.push_back(pair.second.as<std::string>());
                    }
                }
            }
            
            // Generate assets
            auto output = g_assetGenerator->generateArrowAssets(p, itemConfig);
            
            // Return results as Lua table
            sol::table result = lua.create_table();
            result["projectileFile"] = output.projectileFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["effectFile"] = output.effectFile;
            
            Log::info("Generated arrow assets: {}", p.id);
            return result;
            
        } catch (const std::exception& e) {
            Log::error("Failed to generate arrow assets for {}: {}", p.id, e.what());
            return lua.create_table();
        }
    });
}

void CrossbowLuaBindings::poll_assets(sol::state& lua) {
    // Process completed crossbows
    for (auto it = pendingCrossbows.begin(); it != pendingCrossbows.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Crossbow asset ready: {} (mesh: {}, string: {}, anim: {})", 
                    it->second, bundle.mesh, bundle.string, bundle.reloadAnim);
                
                // Notify Lua about completion
                lua["on_crossbow_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Crossbow generation failed for {}: {}", it->second, e.what());
                lua["on_crossbow_error"](it->second, e.what());
            }
            it = pendingCrossbows.erase(it);
        } else { 
            ++it; 
        }
    }
    
    // Process completed projectiles
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Projectile asset ready: {} (mesh: {}, material: {}, sim: {})", 
                    it->second, bundle.mesh, bundle.material, bundle.flightSim);
                
                // Notify Lua about completion
                lua["on_projectile_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Projectile generation failed for {}: {}", it->second, e.what());
                lua["on_projectile_error"](it->second, e.what());
            }
            it = pendingProjectiles.erase(it);
        } else { 
            ++it; 
        }
    }
}

} // namespace Crossbows
} // namespace MagiTech
