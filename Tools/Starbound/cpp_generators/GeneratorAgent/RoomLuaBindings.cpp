#include "RoomLuaBindings.hpp"
#include "RoomFactory.hpp"
#include "RoomTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Rooms {

static std::vector<std::pair<std::future<RoomBundle>, std::string>> pendingRooms;

void RoomLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<RoomParams>("RoomParams",
        "id", &RoomParams::id,
        "width", &RoomParams::width,
        "height", &RoomParams::height,
        "theme", &RoomParams::theme,
        "floorTile", &RoomParams::floorTile,
        "wallTile", &RoomParams::wallTile,
        "ceilingTile", &RoomParams::ceilingTile,
        "propDensity", &RoomParams::propDensity,
        "props", &RoomParams::props,
        "trapDensity", &RoomParams::trapDensity,
        "trapTypes", &RoomParams::trapTypes,
        "secretCount", &RoomParams::secretCount,
        "backgroundStyle", &RoomParams::backgroundStyle,
        "lightCount", &RoomParams::lightCount,
        "detailLevel", &RoomParams::detailLevel
    );

    lua.set_function("spawn_room", [&](RoomParams p) {
        auto factory = MainPlugin::instance().getRoomFactory();
        auto fut = factory->generateAsync(p);
        pendingRooms.emplace_back(std::move(fut), p.id);
    });
}

void RoomLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingRooms.begin(); it != pendingRooms.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            // This would call a Lua function to spawn the room.
            // For now, we'll just print a message.
            lua["print"]("Room ready: " + it->second);
            it = pendingRooms.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Rooms
} // namespace MagiTech
