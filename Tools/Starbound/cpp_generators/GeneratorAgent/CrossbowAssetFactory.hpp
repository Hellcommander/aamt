#pragma once

#include "core/threading/ThreadPool.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Materials.hpp"
#include "core/animation/AssetAnimation.hpp"
#include "core/physics/Collision.hpp"
#include "core/simulation/Simulation.hpp"
#include <future>
#include <memory>
#include <string>
#include <unordered_map>
#include <cstdint>
#include <vector>

namespace MagiTech {
namespace Crossbows {

using MeshHandle = uint32_t;
using AnimationHandle = uint32_t;
using MaterialHandle = uint32_t;
using SimulationHandle = uint32_t;
using ColliderHandle = uint32_t;

struct MaterialSet {
    std::vector<std::pair<std::string, MaterialHandle>> materials;
};

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

// Combined Factory for Weapons and Projectiles
class CrossbowAssetFactory {
    std::unique_ptr<ThreadPool> pool;
    std::unordered_map<uint64_t, CrossbowBundle> crossbowCache;
    std::unordered_map<uint64_t, ProjectileBundle> projectileCache;

public:
    CrossbowAssetFactory();
    ~CrossbowAssetFactory();
    
    void initialize(size_t threadCount = 4);
    
    std::future<CrossbowBundle> generateCrossbowAsync(const CrossbowParams& p);
    std::future<ProjectileBundle> generateBoltAsync(const BoltParams& p);
    std::future<ProjectileBundle> generateArrowAsync(const ArrowParams& p);
    
    // Synchronous versions for immediate access
    CrossbowBundle generateCrossbow(const CrossbowParams& p);
    ProjectileBundle generateBolt(const BoltParams& p);
    ProjectileBundle generateArrow(const ArrowParams& p);
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    
private:
    CrossbowBundle buildCrossbowBundle(const CrossbowParams& p);
    ProjectileBundle buildBoltBundle(const BoltParams& p);
    ProjectileBundle buildArrowBundle(const ArrowParams& p);
};

// Global factory instance
extern std::unique_ptr<CrossbowAssetFactory> g_crossbowFactory;

} // namespace Crossbows
} // namespace MagiTech
