#include "MonsterLuaBindings.hpp"
#include "ProceduralFactory.hpp"
#include "monster_assets/MonsterTypes.hpp"
#include "behavior_assets/BehaviorTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Monsters {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingMonsters;
static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingBehaviors;


void MonsterLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<MonsterParams>("MonsterParams",
        "id", &MonsterParams::id,
        "bodyType", &MonsterParams::bodyType,
        "size", &MonsterParams::size,
        "complexity", &MonsterParams::complexity,
        "limbCount", &MonsterParams::limbCount,
        "headCount", &MonsterParams::headCount,
        "eyeCount", &MonsterParams::eyeCount,
        "hornType", &MonsterParams::hornType,
        "tailType", &MonsterParams::tailType,
        "patternType", &MonsterParams::patternType,
        "colorPrimary", &MonsterParams::colorPrimary,
        "colorSecondary", &MonsterParams::colorSecondary,
        "noiseDetail", &MonsterParams::noiseDetail,
        "textureScale", &MonsterParams::textureScale,
        "materialRoughness", &MonsterParams::materialRoughness,
        "materialMetallic", &MonsterParams::materialMetallic,
        "animationProfile", &MonsterParams::animationProfile,
        "aiProfile", &MonsterParams::aiProfile
    );

    lua.new_usertype<BehaviorParams>("BehaviorParams",
        "aggression", &BehaviorParams::aggression,
        "speed", &BehaviorParams::speed,
        "detectionRange", &BehaviorParams::detectionRange,
        "wanderRadius", &BehaviorParams::wanderRadius,
        "packSize", &BehaviorParams::packSize
    );

    lua.set_function("spawn_monster", [&](MonsterParams m, BehaviorParams b) {
        auto monsterFactory = MainPlugin::instance().getMonsterFactory();
        auto monsterFut = monsterFactory->generateAsync(m);
        pendingMonsters.emplace_back(std::move(monsterFut), m.id);

        auto behaviorFactory = MainPlugin::instance().getBehaviorFactory();
        auto behaviorFut = behaviorFactory->generateAsync(b);
        pendingBehaviors.emplace_back(std::move(behaviorFut), m.id);
    });
}

void MonsterLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingMonsters.begin(); it != pendingMonsters.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Monster assets ready for: " + it->second);
            it = pendingMonsters.erase(it);
        } else {
            ++it;
        }
    }

    for (auto it = pendingBehaviors.begin(); it != pendingBehaviors.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Behavior assets ready for: " + it->second);
            it = pendingBehaviors.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Monsters
} // namespace MagiTech
