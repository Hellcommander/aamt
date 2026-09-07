#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Particles {

class ParticleAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Particles
} // namespace MagiTech
