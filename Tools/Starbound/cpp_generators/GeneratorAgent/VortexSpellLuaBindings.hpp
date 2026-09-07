#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace VortexSpells {

class VortexSpellLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace VortexSpells
} // namespace MagiTech
