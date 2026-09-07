#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace ParticleFields {

class ParticleFieldLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace ParticleFields
} // namespace MagiTech
