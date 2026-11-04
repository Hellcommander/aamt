#include "IngredientLuaBindings.hpp"
#include "IngredientFactory.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace Ingredients {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<IngredientFactory>& factorySlot() {
    static std::shared_ptr<IngredientFactory> f;
    return f;
}
} // namespace

void IngredientLuaBindings::setFactory(std::shared_ptr<IngredientFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<IngredientFactory> IngredientLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<IngredientFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

static std::vector<std::pair<std::future<IngredientAssetBundle>, std::string>> pendingIngredients;

void IngredientLuaBindings::bind(sol::state& lua) {
    lua.new_enum("IngredientType",
        "Herb", IngredientType::Herb,
        "Crystal", IngredientType::Crystal,
        "Powder", IngredientType::Powder,
        "Liquid", IngredientType::Liquid,
        "Bone", IngredientType::Bone,
        "Runestone", IngredientType::Runestone
    );

    lua.new_usertype<IngredientParams>("IngredientParams",
        sol::constructors<IngredientParams()>(),
        "id", &IngredientParams::id,
        // Common
        "type", &IngredientParams::type,
        "scaleMin", &IngredientParams::scaleMin,
        "scaleMax", &IngredientParams::scaleMax,
        "rotationVarianceDeg", &IngredientParams::rotationVarianceDeg,
        // Herb
        "leafCount", &IngredientParams::leafCount,
        "leafLengthMin", &IngredientParams::leafLengthMin,
        "leafLengthMax", &IngredientParams::leafLengthMax,
        "stemThickness", &IngredientParams::stemThickness,
        // Crystal
        "facetCount", &IngredientParams::facetCount,
        "shardLengthMin", &IngredientParams::shardLengthMin,
        "shardLengthMax", &IngredientParams::shardLengthMax,
        "coreGlowColor", &IngredientParams::coreGlowColor,
        // Powder
        "moundRadius", &IngredientParams::moundRadius,
        "grainSize", &IngredientParams::grainSize,
        "powderColor", &IngredientParams::powderColor,
        // Liquid
        "liquidColor", &IngredientParams::liquidColor,
        "fillVolume", &IngredientParams::fillVolume,
        "viscosity", &IngredientParams::viscosity,
        // Bone
        "boneCount", &IngredientParams::boneCount,
        "fragmentScaleMin", &IngredientParams::fragmentScaleMin,
        "fragmentScaleMax", &IngredientParams::fragmentScaleMax,
        // Runestone
        "runeCount", &IngredientParams::runeCount,
        "bevelDepth", &IngredientParams::bevelDepth,
        "runeEmissiveColor", &IngredientParams::runeEmissiveColor
    );

    lua.new_usertype<IngredientAssetBundle>("IngredientAssetBundle",
        sol::no_constructor,
        "mesh", &IngredientAssetBundle::mesh,
        "albedoMap", &IngredientAssetBundle::albedoMap,
        "normalMap", &IngredientAssetBundle::normalMap,
        "detailMap", &IngredientAssetBundle::detailMap,
        "materialShader", &IngredientAssetBundle::materialShader,
        "ambientParticles", &IngredientAssetBundle::ambientParticles,
        "contextDecal", &IngredientAssetBundle::contextDecal,
        "physicsBody", &IngredientAssetBundle::physicsBody
    );

    lua.set_function("spawn_ingredient",
        [](const IngredientParams& p) {
            auto factory = IngredientLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_ingredient_async",
        [](const IngredientParams& p) {
            auto factory = IngredientLuaBindings::factory();
            pendingIngredients.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void IngredientLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingIngredients.begin(); it != pendingIngredients.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Ingredient ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("Ingredients", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingIngredients.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Ingredients
} // namespace MagiTech
