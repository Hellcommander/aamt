#pragma once
#include <sol/sol.hpp>
#include <future>
#include <string>
#include "ParticleFieldTypes.hpp"

namespace MagiTech {
namespace ParticleFields {

/** Registers the particle field usertypes and functions on `lua`. */
void bindParticleFieldToLua(sol::state& lua);

class ParticleFieldLuaBindings {
public:
    static void bind(sol::state& lua);
    /** Delivers finished async generations to Lua on_particle_field_ready(id, bundle) /
        on_particle_field_error(id, message). */
    static void poll_assets(sol::state& lua);
    /** Tracks an async generation until poll_assets delivers it. */
    static void queue(std::future<ParticleFieldBundle> future, const std::string& id);
};

} // namespace ParticleFields
} // namespace MagiTech
