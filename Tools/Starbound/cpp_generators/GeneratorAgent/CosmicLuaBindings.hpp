#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Cosmic {

class CosmicLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Cosmic
} // namespace MagiTech
