#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace Monsters {

class MonsterGenerator;
class BehaviorGenerator;

class MonsterLuaBindings {
public:
    static void bind(sol::state& lua);
    /** Delivers finished spawn_monster() results to Lua (call once per frame). */
    static void poll_assets(sol::state& lua);

    // Factories used by the bindings; the host (MainPlugin) injects its instances with the
    // setters, otherwise the getters lazily create and initialize default ones.
    static void setMonsterFactory(std::shared_ptr<MonsterGenerator> factory);
    static std::shared_ptr<MonsterGenerator> monsterFactory();
    static void setBehaviorFactory(std::shared_ptr<BehaviorGenerator> factory);
    static std::shared_ptr<BehaviorGenerator> behaviorFactory();
};

} // namespace Monsters
} // namespace MagiTech
