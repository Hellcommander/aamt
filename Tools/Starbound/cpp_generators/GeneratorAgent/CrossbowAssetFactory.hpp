#pragma once

#include "core/threading/ThreadPool.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Materials.hpp"
#include "core/animation/AssetAnimation.hpp"
#include "core/physics/Collision.hpp"
#include "core/simulation/Simulation.hpp"
#include <future>
#include <memory>
#include <mutex>
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
    float          drawLength = 0.6f;          // max string pull distance
    float          drawWeight = 800.0f;          // launch force (N)
    bool           autoReload = false;          // reload on fire
    float          reloadTime = 1.5f;          // seconds
    std::string    stockMaterial;       // e.g., WoodOak, MetalSteel
    std::string    limbMaterial;        // e.g., Fiberglass
    std::string    stringMaterial;      // e.g., Hemp, Synthetic
    
    uint64_t hashKey() const;
};

struct BoltParams {
    std::string    id;
    float          length = 0.4f;              // total length
    float          shaftRadius = 0.005f;
    bool           useFletching = true;        
    std::string    fletchMaterial;      // e.g., Feather, Plastic
    float          fletchLength = 0.05f;
    float          tipMass = 0.02f;             // tip weight influences balance
    bool           barbedTip = false;          
    
    uint64_t hashKey() const;
};

struct ArrowParams {
    std::string    id;
    float          shaftLength = 0.75f;         
    float          shaftDiameter = 0.008f;
    int            spineRating = 400;         // stiffness factor
    bool           useFletching = true;        
    std::string    fletchStyle;         // Parabolic, Shield, Flu-Flu
    float          nockSize = 0.006f;            
    float          tipMass = 0.02f;
    
    uint64_t hashKey() const;
};

// Bundle structures for generated assets
struct CrossbowBundle {
    MeshHandle mesh = 0;
    MeshHandle string = 0;
    AnimationHandle reloadAnim = 0;
    MaterialSet materials;
};

struct ProjectileBundle {
    MeshHandle mesh = 0;
    MaterialHandle material = 0;
    MeshHandle vfxTrail = 0;
    SimulationHandle flightSim = 0;
    ColliderHandle collider = 0;
};

// Combined Factory for Weapons and Projectiles
class CrossbowAssetFactory {
    std::unique_ptr<GeneratorTaskPool> pool;
    std::unordered_map<uint64_t, CrossbowBundle> crossbowCache;
    std::unordered_map<uint64_t, ProjectileBundle> projectileCache;
    mutable std::mutex cacheMutex;

public:
    CrossbowAssetFactory();
    ~CrossbowAssetFactory();
    
    void initialize(size_t threadCount = 4);
    void shutdown();
    
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
