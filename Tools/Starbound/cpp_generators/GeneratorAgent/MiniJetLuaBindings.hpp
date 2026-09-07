#pragma once

#include <sol/sol.hpp>

namespace MiniJetGen {

class MiniJetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    static void shutdown();
    
private:
    static void bindEnums(sol::state& lua);
    static void bindStructs(sol::state& lua);
    static void bindFactory(sol::state& lua);
    static void bindLoader(sol::state& lua);
    static void bindEditor(sol::state& lua);
    static void bindValidation(sol::state& lua);
};

} // namespace MiniJetGen 
