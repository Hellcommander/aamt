#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Geometry {

class GeometryAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Geometry
} // namespace MagiTech
