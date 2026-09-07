#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace IconAssets {

class IconAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace IconAssets
} // namespace MagiTech
