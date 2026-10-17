#pragma once
#include <memory>
#include <sol/sol.hpp>

namespace MagiTech {
namespace SnakeMechs {

class SnakeMechFactory;

class SnakeMechLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);

    // Factory used by the Lua API. The owner (MainPlugin) shares its instance
    // through setFactory(); if none was set, factory() creates and initializes
    // a default one on first use.
    static void setFactory(std::shared_ptr<SnakeMechFactory> factory);
    static std::shared_ptr<SnakeMechFactory> factory();
};

} // namespace SnakeMechs
} // namespace MagiTech
