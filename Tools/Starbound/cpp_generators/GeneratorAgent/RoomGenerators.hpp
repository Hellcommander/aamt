#pragma once

#include "RoomTypes.hpp"

namespace MagiTech {
namespace Rooms {

namespace MeshGen {
    MeshHandle buildRoomMesh(const RoomParams& p);
}

namespace TextureGen {
    TextureHandle buildTileset(const RoomParams& p);
}

namespace MaterialGen {
    MaterialHandle buildRoomMaterial(const RoomParams& p);
}

namespace DecorationGen {
    LightHandle placeLights(const RoomParams& p, MeshHandle roomMesh);
}

namespace PropGen {
    void scatterProps(MeshHandle& mesh, const RoomParams& p);
}

namespace TrapGen {
    void scatterTraps(MeshHandle& mesh, const RoomParams& p);
}

} // namespace Rooms
} // namespace MagiTech
