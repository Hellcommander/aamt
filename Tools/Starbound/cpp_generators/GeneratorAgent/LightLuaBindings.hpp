#pragma once

#include <sol/sol.hpp>
#include "LightAssetFactory.hpp"

namespace mt::light {

class LightLuaBindings {
public:
    static void bind(sol::state& lua);
};

} // namespace mt::light
