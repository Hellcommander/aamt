#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace LightningProjectiles {

class LightningProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace LightningProjectiles
} // namespace MagiTech
