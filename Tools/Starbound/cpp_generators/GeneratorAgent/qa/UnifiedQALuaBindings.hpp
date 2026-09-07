#pragma once

#include <sol/sol.hpp>

namespace mt::qa {

class UnifiedQALuaBindings {
public:
    static void bind(sol::state& lua);
    static void update(sol::state& lua);
};

} // namespace mt::qa 
