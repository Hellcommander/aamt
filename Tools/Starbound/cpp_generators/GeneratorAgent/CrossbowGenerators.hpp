#pragma once
// Generator stages used by CrossbowAssetFactory (implemented in CrossbowGenerators.cpp).

#include "CrossbowAssetFactory.hpp"
#include <string>

namespace MagiTech {
namespace Crossbows {

namespace BowGen {
    MeshHandle buildCrossbowMesh(const CrossbowParams& p);
}
namespace StringGen {
    MeshHandle buildString(float drawLength, const std::string& material);
}
namespace AnimGen {
    AnimationHandle buildReload(bool autoReload, float reloadTime);
}
namespace MaterialGen {
    MaterialSet assignBowMaterials(const std::string& stockMat, const std::string& limbMat);
    MaterialHandle assignShaftMaterial(const std::string& id);
}
namespace BoltGen {
    MeshHandle buildBoltMesh(const BoltParams& p);
}
namespace ArrowGen {
    MeshHandle buildArrowMesh(const ArrowParams& p);
}
namespace VFXGen {
    MeshHandle buildTrail(const std::string& style, float intensity);
}
namespace ProjectileSim {
    SimulationHandle setupLinear(float length, float tipMass, float fletchLength);
    SimulationHandle setupFletched(float shaftLength, int spineRating, const std::string& fletchStyle);
}
namespace CollisionGen {
    ColliderHandle buildCylinder(float radius, float height);
}

} // namespace Crossbows
} // namespace MagiTech
