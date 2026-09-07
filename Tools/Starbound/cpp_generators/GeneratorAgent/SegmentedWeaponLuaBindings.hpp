#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace SegmentedWeapons {

class SegmentedWeaponLuaBindings {
public:
    static void bind(sol::state& lua);
};

} // namespace SegmentedWeapons
} // namespace MagiTech
