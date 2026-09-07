#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Ingredients {

class IngredientLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Ingredients
} // namespace MagiTech
