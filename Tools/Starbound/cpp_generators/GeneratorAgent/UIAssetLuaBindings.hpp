#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace UIAssets {

class UIAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace UIAssets
} // namespace MagiTech
