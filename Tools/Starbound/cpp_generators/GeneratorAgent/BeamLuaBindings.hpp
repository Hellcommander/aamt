#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Beams {

class BeamLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Beams
} // namespace MagiTech
