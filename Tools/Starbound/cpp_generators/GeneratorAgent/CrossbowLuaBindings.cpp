#include "CrossbowLuaBindings.hpp"
#include "CrossbowAssetFactory.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace Crossbows {

static std::vector<std::pair<std::future<CrossbowBundle>, std::string>> pendingCrossbows;
static std::vector<std::pair<std::future<ProjectileBundle>, std::string>> pendingProjectiles;
static std::mutex pendingMutex;

static std::mutex factoryMutex;
static std::shared_ptr<CrossbowAssetFactory> g_factory;

void CrossbowLuaBindings::setFactory(std::shared_ptr<CrossbowAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    g_factory = std::move(factory);
}

std::shared_ptr<CrossbowAssetFactory> CrossbowLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!g_factory) {
        g_factory = std::make_shared<CrossbowAssetFactory>();
        g_factory->initialize(4); // 4 threads for asset generation
    }
    return g_factory;
}

namespace {

// The OpenStarbound asset writer (g_assetGenerator), created on first use.
CrossbowAssetGenerator& assetGenerator() {
    static std::mutex generatorMutex;
    std::lock_guard<std::mutex> lock(generatorMutex);
    if (!g_assetGenerator) {
        g_assetGenerator = std::make_unique<CrossbowAssetGenerator>();
    }
    return *g_assetGenerator;
}

bool validateCrossbow(const CrossbowParams& p) {
    if (p.id.empty()) {
        Log::error("CrossbowParams: id cannot be empty");
        return false;
    }
    if (p.drawLength <= 0.0f || p.drawLength > 2.0f) {
        Log::error("CrossbowParams: drawLength must be in (0, 2.0]");
        return false;
    }
    if (p.drawWeight <= 0.0f || p.drawWeight > 1000.0f) {
        Log::error("CrossbowParams: drawWeight must be in (0, 1000]");
        return false;
    }
    if (p.reloadTime <= 0.0f || p.reloadTime > 10.0f) {
        Log::error("CrossbowParams: reloadTime must be in (0, 10.0]");
        return false;
    }
    return true;
}

bool validateBolt(const BoltParams& p) {
    if (p.id.empty()) {
        Log::error("BoltParams: id cannot be empty");
        return false;
    }
    if (p.length <= 0.0f || p.length > 1.0f) {
        Log::error("BoltParams: length must be in (0, 1.0]");
        return false;
    }
    if (p.shaftRadius <= 0.0f || p.shaftRadius > 0.02f) {
        Log::error("BoltParams: shaftRadius must be in (0, 0.02]");
        return false;
    }
    if (p.tipMass <= 0.0f || p.tipMass > 0.1f) {
        Log::error("BoltParams: tipMass must be in (0, 0.1]");
        return false;
    }
    return true;
}

bool validateArrow(const ArrowParams& p) {
    if (p.id.empty()) {
        Log::error("ArrowParams: id cannot be empty");
        return false;
    }
    if (p.shaftLength <= 0.0f || p.shaftLength > 2.0f) {
        Log::error("ArrowParams: shaftLength must be in (0, 2.0]");
        return false;
    }
    if (p.shaftDiameter <= 0.0f || p.shaftDiameter > 0.02f) {
        Log::error("ArrowParams: shaftDiameter must be in (0, 0.02]");
        return false;
    }
    if (p.spineRating <= 0 || p.spineRating > 2000) {
        Log::error("ArrowParams: spineRating must be in (0, 2000]");
        return false;
    }
    if (p.tipMass <= 0.0f || p.tipMass > 0.05f) {
        Log::error("ArrowParams: tipMass must be in (0, 0.05]");
        return false;
    }
    return true;
}

std::vector<std::string> stringList(const sol::table& config, const char* key) {
    std::vector<std::string> out;
    sol::optional<sol::table> list = config[key];
    if (list) {
        for (const auto& [k, v] : *list) {
            if (v.is<std::string>()) out.push_back(v.as<std::string>());
        }
    }
    return out;
}

// Builds an ItemConfig from a Lua table; `defaults` supplies the per-asset defaults.
CrossbowAssetGenerator::ItemConfig readItemConfig(const sol::table& config,
                                                  const std::string& defaultName,
                                                  const std::string& defaultCategory,
                                                  float defaultDamage,
                                                  const std::string& defaultAbility) {
    CrossbowAssetGenerator::ItemConfig itemConfig;
    itemConfig.itemName = config.get_or("itemName", defaultName);
    itemConfig.description = config.get_or("description", std::string());
    itemConfig.rarity = config.get_or("rarity", std::string("Common"));
    itemConfig.category = config.get_or("category", defaultCategory);
    itemConfig.level = config.get_or("level", std::string("1"));
    itemConfig.damageType = config.get_or("damageType", std::string("physical"));
    itemConfig.damage = config.get_or("damage", defaultDamage);
    itemConfig.fireRate = config.get_or("fireRate", 1.0f);
    itemConfig.abilityType = config.get_or("abilityType", defaultAbility);
    itemConfig.behaviorSystem = config.get_or("behaviorSystem", std::string("hybrid"));
    itemConfig.effectSystem = config.get_or("effectSystem", std::string("projectile"));
    itemConfig.materialSystem = config.get_or("materialSystem", std::string("magitech"));
    itemConfig.useAIArt = config.get_or("useAIArt", false);
    itemConfig.artStyle = config.get_or("artStyle", std::string("pixel-art"));
    itemConfig.colorPalette = config.get_or("colorPalette", std::string("starbound"));
    itemConfig.projectileTypes = stringList(config, "projectileTypes");
    itemConfig.specialEffects = stringList(config, "specialEffects");
    itemConfig.artEffects = stringList(config, "artEffects");
    return itemConfig;
}

// Calls an optional Lua callback; errors inside it are logged, not propagated.
template <typename... Args>
void notifyLua(sol::state& lua, const char* name, Args&&... args) {
    sol::protected_function callback = lua[name];
    if (!callback.valid()) return;
    auto result = callback(std::forward<Args>(args)...);
    if (!result.valid()) {
        sol::error err = result;
        Log::error("Crossbow", "Lua callback {} failed: {}", name, err.what());
    }
}

} // namespace

void CrossbowLuaBindings::bind(sol::state& lua) {
    // Initialize factory if not already done
    factory();

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
        "validate", [](const CrossbowParams& p) { return validateCrossbow(p); });

    lua.new_usertype<BoltParams>("BoltParams", sol::constructors<BoltParams()>(),
        "id", &BoltParams::id,
        "length", &BoltParams::length,
        "shaftRadius", &BoltParams::shaftRadius,
        "useFletching", &BoltParams::useFletching,
        "fletchMaterial", &BoltParams::fletchMaterial,
        "fletchLength", &BoltParams::fletchLength,
        "tipMass", &BoltParams::tipMass,
        "barbedTip", &BoltParams::barbedTip,
        "validate", [](const BoltParams& p) { return validateBolt(p); });

    lua.new_usertype<ArrowParams>("ArrowParams", sol::constructors<ArrowParams()>(),
        "id", &ArrowParams::id,
        "shaftLength", &ArrowParams::shaftLength,
        "shaftDiameter", &ArrowParams::shaftDiameter,
        "spineRating", &ArrowParams::spineRating,
        "useFletching", &ArrowParams::useFletching,
        "fletchStyle", &ArrowParams::fletchStyle,
        "nockSize", &ArrowParams::nockSize,
        "tipMass", &ArrowParams::tipMass,
        "validate", [](const ArrowParams& p) { return validateArrow(p); });

    lua.new_usertype<CrossbowBundle>("CrossbowBundle", sol::no_constructor,
        "mesh", &CrossbowBundle::mesh,
        "string", &CrossbowBundle::string,
        "reloadAnim", &CrossbowBundle::reloadAnim,
        "materials", sol::readonly_property([](const CrossbowBundle& b, sol::this_state ts) {
            // { [slot] = materialHandle }
            sol::state_view view(ts);
            sol::table out = view.create_table();
            for (const auto& [slot, handle] : b.materials.materials) out[slot] = handle;
            return out;
        }));

    lua.new_usertype<ProjectileBundle>("ProjectileBundle", sol::no_constructor,
        "mesh", &ProjectileBundle::mesh,
        "material", &ProjectileBundle::material,
        "vfxTrail", &ProjectileBundle::vfxTrail,
        "flightSim", &ProjectileBundle::flightSim,
        "collider", &ProjectileBundle::collider);

    // Main generation functions with validation (Async)
    lua.set_function("spawn_crossbow", [](const CrossbowParams& p) -> bool {
        if (!validateCrossbow(p)) return false;

        try {
            auto future = factory()->generateCrossbowAsync(p);
            {
                std::lock_guard<std::mutex> lock(pendingMutex);
                pendingCrossbows.emplace_back(std::move(future), p.id);
            }
            Log::info("Crossbow", "Crossbow generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to spawn crossbow {}: {}", p.id, e.what());
            return false;
        }
    });

    lua.set_function("spawn_bolt", [](const BoltParams& p) -> bool {
        if (!validateBolt(p)) return false;

        try {
            auto future = factory()->generateBoltAsync(p);
            {
                std::lock_guard<std::mutex> lock(pendingMutex);
                pendingProjectiles.emplace_back(std::move(future), p.id);
            }
            Log::info("Crossbow", "Bolt generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to spawn bolt {}: {}", p.id, e.what());
            return false;
        }
    });

    lua.set_function("spawn_arrow", [](const ArrowParams& p) -> bool {
        if (!validateArrow(p)) return false;

        try {
            auto future = factory()->generateArrowAsync(p);
            {
                std::lock_guard<std::mutex> lock(pendingMutex);
                pendingProjectiles.emplace_back(std::move(future), p.id);
            }
            Log::info("Crossbow", "Arrow generation started: {}", p.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to spawn arrow {}: {}", p.id, e.what());
            return false;
        }
    });

    // Synchronous factory methods for immediate access
    lua.set_function("generate_crossbow", [](const CrossbowParams& p) -> CrossbowBundle {
        if (!validateCrossbow(p)) {
            Log::error("Crossbow", "Invalid crossbow parameters for {}", p.id);
            return CrossbowBundle{};
        }

        try {
            return factory()->generateCrossbow(p);
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate crossbow {}: {}", p.id, e.what());
            return CrossbowBundle{};
        }
    });

    lua.set_function("generate_bolt", [](const BoltParams& p) -> ProjectileBundle {
        if (!validateBolt(p)) {
            Log::error("Crossbow", "Invalid bolt parameters for {}", p.id);
            return ProjectileBundle{};
        }

        try {
            return factory()->generateBolt(p);
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate bolt {}: {}", p.id, e.what());
            return ProjectileBundle{};
        }
    });

    lua.set_function("generate_arrow", [](const ArrowParams& p) -> ProjectileBundle {
        if (!validateArrow(p)) {
            Log::error("Crossbow", "Invalid arrow parameters for {}", p.id);
            return ProjectileBundle{};
        }

        try {
            return factory()->generateArrow(p);
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate arrow {}: {}", p.id, e.what());
            return ProjectileBundle{};
        }
    });

    // Cache management functions
    lua.set_function("clear_crossbow_cache", []() {
        factory()->clearCache();
        Log::info("Cleared crossbow asset cache");
    });

    lua.set_function("get_cache_size", []() -> size_t {
        return factory()->getCacheSize();
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
    lua.set_function("get_pending_count", [](sol::this_state ts) -> sol::table {
        sol::state_view view(ts);
        sol::table result = view.create_table();
        std::lock_guard<std::mutex> lock(pendingMutex);
        result["crossbows"] = pendingCrossbows.size();
        result["projectiles"] = pendingProjectiles.size();
        return result;
    });

    lua.set_function("clear_pending", []() {
        std::lock_guard<std::mutex> lock(pendingMutex);
        pendingCrossbows.clear();
        pendingProjectiles.clear();
        Log::info("Cleared all pending asset generations");
    });

    // Asset generation functions for complete OpenStarbound assets
    lua.set_function("generate_crossbow_assets", [](const CrossbowParams& p, const sol::table& config, sol::this_state ts) -> sol::table {
        sol::state_view view(ts);
        if (!validateCrossbow(p)) {
            Log::error("Crossbow", "Invalid crossbow parameters for {}", p.id);
            return view.create_table();
        }

        try {
            auto itemConfig = readItemConfig(config, "Crossbow", "weapon", 10.0f, "crossbow");
            auto output = assetGenerator().generateCrossbowAssets(p, itemConfig);

            // Return results as Lua table
            sol::table result = view.create_table();
            result["itemFile"] = output.itemFile;
            result["framesFile"] = output.framesFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["behaviorFile"] = output.behaviorFile;
            result["effectFile"] = output.effectFile;
            result["metadataFile"] = output.metadataFile;

            Log::info("Crossbow", "Generated crossbow assets: {}", p.id);
            return result;

        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate crossbow assets for {}: {}", p.id, e.what());
            return view.create_table();
        }
    });

    lua.set_function("generate_bolt_assets", [](const BoltParams& p, const sol::table& config, sol::this_state ts) -> sol::table {
        sol::state_view view(ts);
        if (!validateBolt(p)) {
            Log::error("Crossbow", "Invalid bolt parameters for {}", p.id);
            return view.create_table();
        }

        try {
            auto itemConfig = readItemConfig(config, "Bolt", "ammo", 5.0f, "projectile");
            auto output = assetGenerator().generateBoltAssets(p, itemConfig);

            // Return results as Lua table
            sol::table result = view.create_table();
            result["projectileFile"] = output.projectileFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["effectFile"] = output.effectFile;
            result["metadataFile"] = output.metadataFile;

            Log::info("Crossbow", "Generated bolt assets: {}", p.id);
            return result;

        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate bolt assets for {}: {}", p.id, e.what());
            return view.create_table();
        }
    });

    lua.set_function("generate_arrow_assets", [](const ArrowParams& p, const sol::table& config, sol::this_state ts) -> sol::table {
        sol::state_view view(ts);
        if (!validateArrow(p)) {
            Log::error("Crossbow", "Invalid arrow parameters for {}", p.id);
            return view.create_table();
        }

        try {
            auto itemConfig = readItemConfig(config, "Arrow", "ammo", 4.0f, "projectile");
            auto output = assetGenerator().generateArrowAssets(p, itemConfig);

            // Return results as Lua table
            sol::table result = view.create_table();
            result["projectileFile"] = output.projectileFile;
            result["spriteFile"] = output.spriteFile;
            result["iconFile"] = output.iconFile;
            result["effectFile"] = output.effectFile;
            result["metadataFile"] = output.metadataFile;

            Log::info("Crossbow", "Generated arrow assets: {}", p.id);
            return result;

        } catch (const std::exception& e) {
            Log::error("Crossbow", "Failed to generate arrow assets for {}: {}", p.id, e.what());
            return view.create_table();
        }
    });
}

void CrossbowLuaBindings::poll_assets(sol::state& lua) {
    // Take finished futures out under the lock; Lua callbacks run without it
    std::vector<std::pair<std::future<CrossbowBundle>, std::string>> readyCrossbows;
    std::vector<std::pair<std::future<ProjectileBundle>, std::string>> readyProjectiles;
    {
        std::lock_guard<std::mutex> lock(pendingMutex);
        for (auto it = pendingCrossbows.begin(); it != pendingCrossbows.end();) {
            if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                readyCrossbows.push_back(std::move(*it));
                it = pendingCrossbows.erase(it);
            } else {
                ++it;
            }
        }
        for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
            if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                readyProjectiles.push_back(std::move(*it));
                it = pendingProjectiles.erase(it);
            } else {
                ++it;
            }
        }
    }

    // Process completed crossbows
    for (auto& [future, id] : readyCrossbows) {
        try {
            auto bundle = future.get();
            Log::info("Crossbow", "Crossbow asset ready: {} (mesh: {}, string: {}, anim: {})",
                id, bundle.mesh, bundle.string, bundle.reloadAnim);
            notifyLua(lua, "on_crossbow_ready", id, bundle);
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Crossbow generation failed for {}: {}", id, e.what());
            notifyLua(lua, "on_crossbow_error", id, std::string(e.what()));
        }
    }

    // Process completed projectiles
    for (auto& [future, id] : readyProjectiles) {
        try {
            auto bundle = future.get();
            Log::info("Crossbow", "Projectile asset ready: {} (mesh: {}, material: {}, sim: {})",
                id, bundle.mesh, bundle.material, bundle.flightSim);
            notifyLua(lua, "on_projectile_ready", id, bundle);
        } catch (const std::exception& e) {
            Log::error("Crossbow", "Projectile generation failed for {}: {}", id, e.what());
            notifyLua(lua, "on_projectile_error", id, std::string(e.what()));
        }
    }
}

} // namespace Crossbows
} // namespace MagiTech
