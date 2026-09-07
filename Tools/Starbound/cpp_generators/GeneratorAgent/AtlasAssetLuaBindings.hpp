#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace AtlasAssets {

class AtlasAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace AtlasAssets
} // namespace MagiTech
