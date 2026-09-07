#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Spellstones {

class SpellstoneLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Spellstones
} // namespace MagiTech
