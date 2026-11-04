#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace SegmentedCreatures {

class SegmentedCreatureFactory;
class BehaviorFactory;

class SegmentedCreatureLuaBindings {
public:
    static void bind(sol::state& lua);
    /** Delivers finished request_segmented_creature() results to Lua (call once per frame). */
    static void poll_assets(sol::state& lua);

    // Factories used by the bindings; the host (MainPlugin) injects its instances with the
    // setters, otherwise the getters lazily create and initialize default ones.
    static void setCreatureFactory(std::shared_ptr<SegmentedCreatureFactory> factory);
    static std::shared_ptr<SegmentedCreatureFactory> creatureFactory();
    static void setBehaviorFactory(std::shared_ptr<BehaviorFactory> factory);
    static std::shared_ptr<BehaviorFactory> behaviorFactory();

private:
    static void bindParameterStructs(sol::state& lua);
    static void bindEnums(sol::state& lua);
    static void bindFactoryFunctions(sol::state& lua);
    static void bindUtilityFunctions(sol::state& lua);
    static void bindGlobalFactories(sol::state& lua);
};

} // namespace SegmentedCreatures
} // namespace MagiTech
