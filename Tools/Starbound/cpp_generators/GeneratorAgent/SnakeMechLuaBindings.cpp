#include "SnakeMechLuaBindings.hpp"
#include "SnakeMechFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace SnakeMechs {

static std::vector<std::pair<std::future<SnakeMechAssetBundle>, std::string>> pendingMechs;

void SnakeMechLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SnakeMechParams>("SnakeMechParams",
        sol::constructors<SnakeMechParams()>(),
        "id", &SnakeMechParams::id,
        "segmentCount", &SnakeMechParams::segmentCount,
        "segmentLength", &SnakeMechParams::segmentLength,
        "segmentRadius", &SnakeMechParams::segmentRadius,
        "connectorGap", &SnakeMechParams::connectorGap,
        "maxBendAngleDeg", &SnakeMechParams::maxBendAngleDeg,
        "bendStiffness", &SnakeMechParams::bendStiffness,
        "enablePlating", &SnakeMechParams::enablePlating,
        "platesPerSegment", &SnakeMechParams::platesPerSegment,
        "plateThickness", &SnakeMechParams::plateThickness,
        "platingColor", &SnakeMechParams::platingColor,
        "stripeCount", &SnakeMechParams::stripeCount,
        "stripeWidth", &SnakeMechParams::stripeWidth,
        "stripeColor", &SnakeMechParams::stripeColor,
        "stripeGlowIntensity", &SnakeMechParams::stripeGlowIntensity,
        "enableJointSparks", &SnakeMechParams::enableJointSparks,
        "sparkRate", &SnakeMechParams::sparkRate,
        "sparkLifetime", &SnakeMechParams::sparkLifetime,
        "sparkColor", &SnakeMechParams::sparkColor,
        "segmentMass", &SnakeMechParams::segmentMass,
        "jointDamping", &SnakeMechParams::jointDamping,
        "waveAmplitude", &SnakeMechParams::waveAmplitude,
        "waveFrequency", &SnakeMechParams::waveFrequency,
        "rebuildOnLOD", &SnakeMechParams::rebuildOnLOD,
        "lodCount", &SnakeMechParams::lodCount
    );

    lua.new_usertype<SnakeMechAssetBundle>("SnakeMechAssetBundle",
        sol::no_constructor,
        "segmentMesh", &SnakeMechAssetBundle::segmentMesh,
        "skeleton", &SnakeMechAssetBundle::skeleton,
        "proceduralAnimation", &SnakeMechAssetBundle::proceduralAnimation,
        "materialShader", &SnakeMechAssetBundle::materialShader,
        "sparkParticles", &SnakeMechAssetBundle::sparkParticles,
        "physicsAsset", &SnakeMechAssetBundle::physicsAsset
    );

    lua.set_function("spawn_snake_mech",
        [&](const SnakeMechParams& p) {
            auto factory = MainPlugin::instance().getSnakeMechFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_snake_mech_async",
        [&](const SnakeMechParams& p) {
            auto factory = MainPlugin::instance().getSnakeMechFactory();
            pendingMechs.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void SnakeMechLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingMechs.begin(); it != pendingMechs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Snake mech ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingMechs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace SnakeMechs
} // namespace MagiTech
