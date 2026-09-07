#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace IceShards {

class IceShardLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace IceShards
} // namespace MagiTech
