#include "CrossbowAssetFactory.hpp"
#include "CrossbowGenerators.cpp"
#include "core/Log.hpp"
#include <xxhash.h>

namespace MagiTech {
namespace Crossbows {

// Global factory instance
std::unique_ptr<CrossbowAssetFactory> g_crossbowFactory;

CrossbowAssetFactory::CrossbowAssetFactory() {
    pool = std::make_unique<ThreadPool>(4);
}

CrossbowAssetFactory::~CrossbowAssetFactory() = default;

void CrossbowAssetFactory::initialize(size_t threadCount) {
    pool = std::make_unique<ThreadPool>(threadCount);
}

std::future<CrossbowBundle> CrossbowAssetFactory::generateCrossbowAsync(const CrossbowParams& p) {
    return pool->enqueue([this, p]() {
        return buildCrossbowBundle(p);
    });
}

std::future<ProjectileBundle> CrossbowAssetFactory::generateBoltAsync(const BoltParams& p) {
    return pool->enqueue([this, p]() {
        return buildBoltBundle(p);
    });
}

std::future<ProjectileBundle> CrossbowAssetFactory::generateArrowAsync(const ArrowParams& p) {
    return pool->enqueue([this, p]() {
        return buildArrowBundle(p);
    });
}

CrossbowBundle CrossbowAssetFactory::generateCrossbow(const CrossbowParams& p) {
    uint64_t key = p.hashKey();
    auto it = crossbowCache.find(key);
    if (it != crossbowCache.end()) {
        return it->second;
    }
    
    CrossbowBundle bundle = buildCrossbowBundle(p);
    crossbowCache[key] = bundle;
    return bundle;
}

ProjectileBundle CrossbowAssetFactory::generateBolt(const BoltParams& p) {
    uint64_t key = p.hashKey();
    auto it = projectileCache.find(key);
    if (it != projectileCache.end()) {
        return it->second;
    }
    
    ProjectileBundle bundle = buildBoltBundle(p);
    projectileCache[key] = bundle;
    return bundle;
}

ProjectileBundle CrossbowAssetFactory::generateArrow(const ArrowParams& p) {
    uint64_t key = p.hashKey();
    auto it = projectileCache.find(key);
    if (it != projectileCache.end()) {
        return it->second;
    }
    
    ProjectileBundle bundle = buildArrowBundle(p);
    projectileCache[key] = bundle;
    return bundle;
}

void CrossbowAssetFactory::clearCache() {
    crossbowCache.clear();
    projectileCache.clear();
}

size_t CrossbowAssetFactory::getCacheSize() const {
    return crossbowCache.size() + projectileCache.size();
}

CrossbowBundle CrossbowAssetFactory::buildCrossbowBundle(const CrossbowParams& p) {
    CrossbowBundle bundle;
    
    // Generate crossbow mesh using BowGen
    bundle.mesh = BowGen::buildCrossbowMesh(p);
    
    // Generate string using StringGen
    bundle.string = StringGen::buildString(p.drawLength, p.stringMaterial);
    
    // Generate reload animation using AnimGen
    bundle.reloadAnim = AnimGen::buildReload(p.autoReload, p.reloadTime);
    
    // Assign materials using MaterialGen
    bundle.materials = MaterialGen::assignBowMaterials(p.stockMaterial, p.limbMaterial);
    
    return bundle;
}

ProjectileBundle CrossbowAssetFactory::buildBoltBundle(const BoltParams& p) {
    ProjectileBundle bundle;
    
    // Generate bolt mesh using BoltGen
    bundle.mesh = BoltGen::buildBoltMesh(p);
    
    // Assign shaft material
    bundle.material = MaterialGen::assignShaftMaterial(p.id);
    
    // Generate VFX trail
    bundle.vfxTrail = VFXGen::buildTrail("spark", p.tipMass * 0.1f);
    
    // Setup flight simulation
    bundle.flightSim = ProjectileSim::setupLinear(p.length, p.tipMass, p.fletchLength);
    
    // Generate collision cylinder
    bundle.collider = CollisionGen::buildCylinder(p.shaftRadius, p.length);
    
    return bundle;
}

ProjectileBundle CrossbowAssetFactory::buildArrowBundle(const ArrowParams& p) {
    ProjectileBundle bundle;
    
    // Generate arrow mesh using ArrowGen
    bundle.mesh = ArrowGen::buildArrowMesh(p);
    
    // Assign shaft material
    bundle.material = MaterialGen::assignShaftMaterial(p.id);
    
    // Generate VFX trail
    bundle.vfxTrail = VFXGen::buildTrail("feather", p.spineRating * 0.05f);
    
    // Setup flight simulation
    bundle.flightSim = ProjectileSim::setupFletched(p.shaftLength, p.spineRating, p.fletchStyle);
    
    // Generate collision cylinder
    bundle.collider = CollisionGen::buildCylinder(p.shaftDiameter * 0.5f, p.shaftLength);
    
    return bundle;
}

} // namespace Crossbows
} // namespace MagiTech
