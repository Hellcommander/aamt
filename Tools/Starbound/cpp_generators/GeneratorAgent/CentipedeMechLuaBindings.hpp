#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace CentipedeMechs {

class CentipedeMechLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    static void shutdown();
};

} // namespace CentipedeMechs
} // namespace MagiTech
