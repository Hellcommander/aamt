#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace SegmentedWeapons {

class SegmentedWeaponLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);

private:
    static void bindEnums(sol::state& lua);
    static void bindParameterStructs(sol::state& lua);
    static void bindFactoryFunctions(sol::state& lua);
    static void bindUtilityFunctions(sol::state& lua);
    static void bindGlobalFactory(sol::state& lua);
};

} // namespace SegmentedWeapons
} // namespace MagiTech
