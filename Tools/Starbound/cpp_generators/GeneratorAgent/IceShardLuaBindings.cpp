#include "IceShardLuaBindings.hpp"
#include "IceShardAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace IceShards {

static std::vector<std::pair<std::future<IceShardBundle>, std::string>> pendingAssets;

void IceShardLuaBindings::bind(sol::state& lua) {
    lua.new_enum("ShardDistribution",
        "RadialBurst", ShardDistribution::RadialBurst,
        "StreamLine", ShardDistribution::StreamLine,
        "RandomScatter", ShardDistribution::RandomScatter
    );

    lua.new_usertype<IceShardParams>("IceShardParams", sol::constructors<IceShardParams()>(),
        "id", &IceShardParams::id, "coreRadius", &IceShardParams::coreRadius, "shardCount", &IceShardParams::shardCount,
        "shardLength", &IceShardParams::shardLength, "shardVariance", &IceShardParams::shardVariance,
        "distribution", &IceShardParams::distribution, "dynamicTess", &IceShardParams::dynamicTess);

    lua.new_usertype<FrostTrailParams>("FrostTrailParams", sol::constructors<FrostTrailParams()>(),
        "enableTrail", &FrostTrailParams::enableTrail, "trailLength", &FrostTrailParams::trailLength, "width", &FrostTrailParams::width,
        "tipColor", &FrostTrailParams::tipColor, "baseColor", &FrostTrailParams::baseColor, "uvScrollSpeed", &FrostTrailParams::uvScrollSpeed);

    lua.new_usertype<FrostVFXParams>("FrostVFXParams", sol::constructors<FrostVFXParams()>(),
        "shaderTemplate", &FrostVFXParams::shaderTemplate, "defines", &FrostVFXParams::defines,
        "noiseIntensity", &FrostVFXParams::noiseIntensity, "rimPower", &FrostVFXParams::rimPower);

    lua.new_usertype<FrostParticleParams>("FrostParticleParams", sol::constructors<FrostParticleParams()>(),
        "enableParticles", &FrostParticleParams::enableParticles, "burstCount", &FrostParticleParams::burstCount,
        "spawnRate", &FrostParticleParams::spawnRate, "lifeTime", &FrostParticleParams::lifeTime,
        "initialVelocity", &FrostParticleParams::initialVelocity, "spreadAngle", &FrostParticleParams::spreadAngle);

    lua.new_usertype<FrostLightParams>("FrostLightParams", sol::constructors<FrostLightParams()>(),
        "enableLight", &FrostLightParams::enableLight, "color", &FrostLightParams::color,
        "intensity", &FrostLightParams::intensity, "flickerFreq", &FrostLightParams::flickerFreq);

    lua.new_usertype<FrostAudioParams>("FrostAudioParams", sol::constructors<FrostAudioParams()>(),
        "playOnCast", &FrostAudioParams::playOnCast, "whooshFile", &FrostAudioParams::whooshFile,
        "crackFile", &FrostAudioParams::crackFile, "volume", &FrostAudioParams::volume);

    lua.new_usertype<FrostCollisionParams>("FrostCollisionParams", sol::constructors<FrostCollisionParams()>(),
        "enableCollider", &FrostCollisionParams::enableCollider, "radius", &FrostCollisionParams::radius,
        "convexHull", &FrostCollisionParams::convexHull, "triggerOnly", &FrostCollisionParams::triggerOnly);

    lua.new_usertype<IceShardBundle>("IceShardBundle", sol::no_constructor,
        "shardMeshes", &IceShardBundle::shardMeshes, "trailMesh", &IceShardBundle::trailMesh, "vfxShader", &IceShardBundle::vfxShader,
        "particleSys", &IceShardBundle::particleSys, "light", &IceShardBundle::light,
        "audioWhoosh", &IceShardBundle::audioWhoosh, "audioCrack", &IceShardBundle::audioCrack, "collider", &IceShardBundle::collider);

    lua.set_function("spawn_ice_shard",
        [&](const IceShardParams& s, const FrostTrailParams& t, const FrostVFXParams& v,
            const FrostParticleParams& p, const FrostLightParams& l, const FrostAudioParams& a,
            const FrostCollisionParams& c) {
            auto factory = MainPlugin::instance().getIceShardAssetFactory();
            pendingAssets.emplace_back(factory->generateAsync(s, t, v, p, l, a, c), s.id);
        }
    );
}

void IceShardLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Ice shard asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingAssets.erase(it);
        } else { ++it; }
    }
}

} // namespace IceShards
} // namespace MagiTech
