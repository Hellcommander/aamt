#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace Audio {

class AudioAssetFactory;

class AudioAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates (and initializes) a default one.
    static void setFactory(std::shared_ptr<AudioAssetFactory> factory);
    static std::shared_ptr<AudioAssetFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace Audio
} // namespace MagiTech
