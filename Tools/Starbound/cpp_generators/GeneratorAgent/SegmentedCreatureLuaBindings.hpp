#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace SegmentedCreatures {

class SegmentedCreatureLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace SegmentedCreatures
} // namespace MagiTech
