#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace AnimationAssets {

class AnimationAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace AnimationAssets
} // namespace MagiTech
