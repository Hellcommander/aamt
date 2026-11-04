#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MiniJetGen {

class MiniJetFactory;

class MiniJetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    static void shutdown();

    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates (and initializes) a default one.
    static void setFactory(std::shared_ptr<MiniJetFactory> factory);
    static std::shared_ptr<MiniJetFactory> factory();

private:
    static void bindEnums(sol::state& lua);
    static void bindStructs(sol::state& lua);
    static void bindFactory(sol::state& lua);
    static void bindLoader(sol::state& lua);
    static void bindEditor(sol::state& lua);
    static void bindValidation(sol::state& lua);
};

} // namespace MiniJetGen
