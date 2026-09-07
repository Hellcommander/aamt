#pragma once

#include "core/mesh/Mesh.hpp"
#include "core/rendering/Materials.hpp"
#include "core/animation/AssetAnimation.hpp"
#include "core/physics/Collision.hpp"
#include "core/simulation/Simulation.hpp"
#include <string>
#include <vector>
#include <unordered_map>

namespace MagiTech {
namespace Crossbows {

using MeshHandle = uint32_t;
using AnimationHandle = uint32_t;
using MaterialHandle = uint32_t;
using SimulationHandle = uint32_t;
using ColliderHandle = uint32_t;

// Parameter Schemas
struct CrossbowParams {
    std::string    id;                  
    float          drawLength;          // max string pull distance
    float          drawWeight;          // launch force (N)
    bool           autoReload;          // reload on fire
    float          reloadTime;          // seconds
    std::string    stockMaterial;       // e.g., WoodOak, MetalSteel
    std::string    limbMaterial;        // e.g., Fiberglass
    std::string    stringMaterial;      // e.g., Hemp, Synthetic
    
    uint64_t hashKey() const;
};

struct BoltParams {
    std::string    id;
    float          length;              // total length
    float          shaftRadius;
    bool           useFletching;        
    std::string    fletchMaterial;      // e.g., Feather, Plastic
    float          fletchLength;
    float          tipMass;             // tip weight influences balance
    bool           barbedTip;          
    
    uint64_t hashKey() const;
};

struct ArrowParams {
    std::string    id;
    float          shaftLength;         
    float          shaftDiameter;
    int            spineRating;         // stiffness factor
    bool           useFletching;        
    std::string    fletchStyle;         // Parabolic, Shield, Flu-Flu
    float          nockSize;            
    float          tipMass;
    
    uint64_t hashKey() const;
};

// Bundle structures for generated assets
struct CrossbowBundle {
    MeshHandle mesh;
    MeshHandle string;
    AnimationHandle reloadAnim;
    MaterialSet materials;
};

struct ProjectileBundle {
    MeshHandle mesh;
    MaterialHandle material;
    MeshHandle vfxTrail;
    SimulationHandle flightSim;
    ColliderHandle collider;
};

// Material set for multiple materials
struct MaterialSet {
    std::vector<std::pair<std::string, MaterialHandle>> materials;
    
    MaterialHandle getMaterial(const std::string& name) const {
        for (const auto& mat : materials) {
            if (mat.first == name) {
                return mat.second;
            }
        }
        return MaterialHandle{};
    }
};

} // namespace Crossbows
} // namespace MagiTech 
