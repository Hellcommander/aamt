#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace FrostNovas {

class FrostNovaLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace FrostNovas
} // namespace MagiTech
