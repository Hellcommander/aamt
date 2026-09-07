#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Rooms {

class RoomLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Rooms
} // namespace MagiTech
