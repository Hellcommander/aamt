#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace ShaderAssets {

class ShaderAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace ShaderAssets
} // namespace MagiTech
