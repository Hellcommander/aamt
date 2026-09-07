#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace DynamicAssets {

class DynamicAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace DynamicAssets
} // namespace MagiTech
