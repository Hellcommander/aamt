#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Editor {

class EditorUILuaBindings {
public:
    static void bind(sol::state& lua);
};

} // namespace Editor
} // namespace MagiTech
