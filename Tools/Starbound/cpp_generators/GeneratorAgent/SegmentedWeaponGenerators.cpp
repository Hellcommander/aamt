#include "core/modules/segmented_weapon_generator/SegmentedWeaponFactory.hpp"
#include "core/modules/segmented_weapon_generator/SegmentedWeaponParams.hpp"
#include "core/Log.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace SegmentedWeapons {

// Global factory instance
SegmentedWeaponFactory g_weaponFactory;

// Enhanced placeholder functions for generation steps
namespace {
    MeshHandle createPrimitive(SegmentShape shape, float radius, float length) {
        Log::info("  - Creating primitive shape: {} with radius: {}, length: {}", 
                 ParamUtils::segmentShapeToString(shape), radius, length);
        return 101;
    }

    void applyNoise(MeshHandle mesh, float detail) {
        Log::info("  - Applying noise with detail: {}", detail);
    }

    void addOrnaments(MeshHandle mesh, bool ornamentation) {
        if (ornamentation) {
            Log::info("  - Adding ornamentation");
        }
    }

    MeshHandle assembleSegments(MeshHandle baseSeg, int count, TaperProfile taperProfile, 
                               const std::vector<float>& customCurve) {
        Log::info("  - Assembling {} segments with taper: {}", count, 
                 ParamUtils::taperProfileToString(taperProfile));
        return 201;
    }

    void attachEnd(MeshHandle fullMesh, EndAttachment endAttachment) {
        Log::info("  - Attaching end piece: {}", ParamUtils::endAttachmentToString(endAttachment));
    }

    void createCylinderSegment(MeshHandle mesh, float radius, float length) {
        Log::info("  - Creating cylinder segment with radius: {}, length: {}", radius, length);
    }

    void createBoxSegment(MeshHandle mesh, float radius, float length) {
        Log::info("  - Creating box segment with radius: {}, length: {}", radius, length);
    }

    void createSphereSegment(MeshHandle mesh, float radius, float length) {
        Log::info("  - Creating sphere segment with radius: {}, length: {}", radius, length);
    }

    void createCustomSegment(MeshHandle mesh, float radius, float length) {
        Log::info("  - Creating custom segment with radius: {}, length: {}", radius, length);
    }

    void applyLinearTaper(MeshHandle mesh, int segmentCount, float segmentLength) {
        Log::info("  - Applying linear taper to {} segments", segmentCount);
    }

    void applyExponentialTaper(MeshHandle mesh, int segmentCount, float segmentLength) {
        Log::info("  - Applying exponential taper to {} segments", segmentCount);
    }

    void applyCustomTaper(MeshHandle mesh, int segmentCount, float segmentLength, 
                         const std::vector<float>& customCurve) {
        Log::info("  - Applying custom taper to {} segments with {} curve points", 
                 segmentCount, customCurve.size());
    }

    void addBladeEnd(MeshHandle mesh, float radius) {
        Log::info("  - Adding blade end with radius: {}", radius);
    }

    void addWeightEnd(MeshHandle mesh, float radius) {
        Log::info("  - Adding weight end with radius: {}", radius);
    }

    void addSpikeEnd(MeshHandle mesh, float radius) {
        Log::info("  - Adding spike end with radius: {}", radius);
    }

    void addHookEnd(MeshHandle mesh, float radius) {
        Log::info("  - Adding hook end with radius: {}", radius);
    }
}

namespace MeshGen {
    MeshHandle build(const SegmentedWeaponParams& w) {
        Log::info("Building segmented weapon mesh for: {}", w.id);
        
        // Generate base segment mesh
        auto baseSeg = createPrimitive(w.segmentShape, w.segmentRadius, w.segmentLength);
        
        // Apply noise displacement
        if (w.noiseDetail > 0.0f) {
            applyNoise(baseSeg, w.noiseDetail);
        }
        
        // Add ornamentation
        if (w.ornamentation) {
            addOrnaments(baseSeg, w.ornamentation);
        }
        
        // Assemble segments along spline
        auto fullMesh = assembleSegments(baseSeg, w.segmentCount, w.taperProfile, w.customTaperCurve);
        
        // Add end attachment
        if (w.endAttachment != EndAttachment::NONE) {
            attachEnd(fullMesh, w.endAttachment);
        }
        
        Log::info("Finished building mesh for: {}", w.id);
        return fullMesh;
    }
}

namespace TextureGen {
    TextureHandle build(const SegmentedWeaponParams& w) {
        Log::info("Building PBR texture for material: {}", ParamUtils::materialTypeToString(w.materialType));
        
        // Generate base texture based on material type
        switch (w.materialType) {
            case MaterialType::LEATHER:
                Log::info("  - Generating leather texture with primary color: ({}, {}, {})", 
                         w.colorPrimary.x, w.colorPrimary.y, w.colorPrimary.z);
                break;
            case MaterialType::STEEL:
                Log::info("  - Generating steel texture with metallic properties");
                break;
            case MaterialType::ROPE:
                Log::info("  - Generating rope texture with fibrous properties");
                break;
            case MaterialType::CHAIN_METAL:
                Log::info("  - Generating chain metal texture with metallic properties");
                break;
        }
        
        // Apply texture scaling
        Log::info("  - Applying texture scale: {}", w.textureScale);
        
        // Generate PBR maps (roughness, metallic, normal)
        Log::info("  - Generating PBR material maps");
        
        return 301;
    }
}

namespace RigGen {
    SkeletonHandle build(const SegmentedWeaponParams& w) {
        Log::info("Building skeleton with {} segments", w.segmentCount);
        
        // Create handle bone
        Log::info("  - Added handle bone");
        
        // Create segment bones
        for (int i = 0; i < w.segmentCount; ++i) {
            Log::info("  - Added bone seg_{} with twist: {}, swing: {}, flexibility: {}", 
                     i, w.articulationLimits.twist, w.articulationLimits.swing, w.jointFlexibility);
        }
        
        // Set joint limits based on articulation limits
        Log::info("  - Setting joint limits for {} segments", w.segmentCount);
        
        // Configure joint flexibility
        Log::info("  - Configuring joint flexibility: {}", w.jointFlexibility);
        
        Log::info("Finalized skeleton rig.");
        return 401;
    }
}

namespace PhysicsGen {
    PhysicsHandle build(const SegmentedWeaponParams& w, const PhysicsParams& p) {
        Log::info("Building physics setup with {} solver iterations", p.solverIterations);
        
        // Create rigid bodies for each segment
        for (int i = 0; i < w.segmentCount; ++i) {
            Log::info("  - Added rigidbody and collider for seg_{} with mass: {}, collision radius: {}", 
                     i, p.massPerSegment, p.collisionRadius);
        }
        
        // Configure physics properties
        Log::info("  - Setting damping: {}, restitution: {}", p.damping, p.restitution);
        Log::info("  - Setting friction: {}, rolling friction: {}, spinning friction: {}", 
                 p.friction, p.rollingFriction, p.spinningFriction);
        
        // Configure joint properties
        Log::info("  - Setting joint damping: {}, joint friction: {}", p.jointDamping, p.jointFriction);
        
        // Configure joint limits
        if (p.enableJointLimits) {
            Log::info("  - Enabling joint limits with softness: {}, bias: {}, relaxation: {}", 
                     p.jointLimitSoftness, p.jointLimitBias, p.jointLimitRelaxation);
        }
        
        // Configure velocity limits
        Log::info("  - Setting max linear velocity: {}, max angular velocity: {}", 
                 p.maxLinearVelocity, p.maxAngularVelocity);
        
        // Configure gravity influence
        if (p.enableGravity) {
            Log::info("  - Enabling gravity with influence: {}", p.gravityInfluence);
        }
        
        Log::info("Finished physics setup.");
        return 501;
    }
}

// SegmentedWeaponFactory Implementation
std::future<AssetBundle> SegmentedWeaponFactory::generateFromJson(const std::string& weaponJsonPath, 
                                                                 const std::string& physicsJsonPath) {
    return std::async(std::launch::async, [this, weaponJsonPath, physicsJsonPath]() {
        // Load weapon parameters
        std::ifstream weaponFile(weaponJsonPath);
        if (!weaponFile.is_open()) {
            throw std::runtime_error("Could not open weapon file: " + weaponJsonPath);
        }
        
        std::stringstream weaponBuffer;
        weaponBuffer << weaponFile.rdbuf();
        auto weaponParams = ParamUtils::fromJson(nlohmann::json::parse(weaponBuffer.str()));
        
        // Load physics parameters
        std::ifstream physicsFile(physicsJsonPath);
        if (!physicsFile.is_open()) {
            throw std::runtime_error("Could not open physics file: " + physicsJsonPath);
        }
        
        std::stringstream physicsBuffer;
        physicsBuffer << physicsFile.rdbuf();
        auto physicsParams = ParamUtils::fromJson(nlohmann::json::parse(physicsBuffer.str()));
        
        return generateSync(weaponParams, physicsParams);
    });
}

std::future<AssetBundle> SegmentedWeaponFactory::generateFromParams(const SegmentedWeaponParams& weaponParams, 
                                                                   const PhysicsParams& physicsParams) {
    return generateAsync(weaponParams, physicsParams);
}

std::vector<std::future<AssetBundle>> SegmentedWeaponFactory::generateBatch(
    const std::vector<std::pair<SegmentedWeaponParams, PhysicsParams>>& params) {
    std::vector<std::future<AssetBundle>> futures;
    futures.reserve(params.size());
    
    for (const auto& param : params) {
        futures.push_back(generateAsync(param.first, param.second));
    }
    
    return futures;
}

bool SegmentedWeaponFactory::validateWeaponParams(const SegmentedWeaponParams& params) {
    return params.segmentCount > 0 && 
           params.segmentLength > 0.0f && 
           params.segmentRadius > 0.0f &&
           params.jointFlexibility >= 0.0f && 
           params.jointFlexibility <= 1.0f &&
           params.articulationLimits.twist >= 0.0f &&
           params.articulationLimits.swing >= 0.0f;
}

std::string SegmentedWeaponFactory::getWeaponValidationErrors(const SegmentedWeaponParams& params) {
    std::string errors;
    
    if (params.segmentCount <= 0) {
        errors += "segmentCount must be greater than 0\n";
    }
    if (params.segmentLength <= 0.0f) {
        errors += "segmentLength must be greater than 0\n";
    }
    if (params.segmentRadius <= 0.0f) {
        errors += "segmentRadius must be greater than 0\n";
    }
    if (params.jointFlexibility < 0.0f || params.jointFlexibility > 1.0f) {
        errors += "jointFlexibility must be between 0 and 1\n";
    }
    if (params.articulationLimits.twist < 0.0f) {
        errors += "articulationLimits.twist must be non-negative\n";
    }
    if (params.articulationLimits.swing < 0.0f) {
        errors += "articulationLimits.swing must be non-negative\n";
    }
    
    return errors;
}

bool SegmentedWeaponFactory::validatePhysicsParams(const PhysicsParams& params) {
    return params.massPerSegment > 0.0f && 
           params.damping >= 0.0f && 
           params.restitution >= 0.0f &&
           params.collisionRadius > 0.0f &&
           params.solverIterations > 0 &&
           params.gravityInfluence >= 0.0f;
}

std::string SegmentedWeaponFactory::getPhysicsValidationErrors(const PhysicsParams& params) {
    std::string errors;
    
    if (params.massPerSegment <= 0.0f) {
        errors += "massPerSegment must be greater than 0\n";
    }
    if (params.damping < 0.0f) {
        errors += "damping must be non-negative\n";
    }
    if (params.restitution < 0.0f) {
        errors += "restitution must be non-negative\n";
    }
    if (params.collisionRadius <= 0.0f) {
        errors += "collisionRadius must be greater than 0\n";
    }
    if (params.solverIterations <= 0) {
        errors += "solverIterations must be greater than 0\n";
    }
    if (params.gravityInfluence < 0.0f) {
        errors += "gravityInfluence must be non-negative\n";
    }
    
    return errors;
}

} // namespace SegmentedWeapons
} // namespace MagiTech
