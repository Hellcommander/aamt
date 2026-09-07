#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Audio {

class AudioAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Audio
} // namespace MagiTech
