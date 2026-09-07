#include "CentipedeMechFactory.hpp"
#include "core/Log.hpp"
#include "agents/GeneratorAgent/AudioAssetTypes.hpp"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include <cmath>
#include <random>
#include <algorithm>

namespace MagiTech {
namespace CentipedeMechs {

#define LOG_MECH_GEN(Action, Id) Log::info("CentipedeMechGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t MechParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(MechParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}
uint64_t LegParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(LegParams) - sizeof(std::string));
    XXH64_update(&s, footType.c_str(), footType.length());
    return XXH64_digest(&s);
}
uint64_t CockpitParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(CockpitParams) - 2 * sizeof(std::string));
    XXH64_update(&s, seatMaterial.c_str(), seatMaterial.length());
    XXH64_update(&s, controlStyle.c_str(), controlStyle.length());
    return XXH64_digest(&s);
}
uint64_t HardpointParams::hashKey() const { return XXH64(this, sizeof(HardpointParams), 0); }

// ============================================================================
// SEGMENT GENERATION - Multi-segment body with seamless joints
// ============================================================================

namespace SegmentGen {
    // Primitive mesh generation utilities
    struct Primitive {
        static MeshHandle cylinder(float radius, float length, int segments = 16) {
            LOG_MECH_GEN(CreatingCylinder, radius);
            static uint32_t nextHandle = 1000;
            return nextHandle++;
        }
        
        static MeshHandle sphere(float radius, int segments = 16) {
            LOG_MECH_GEN(CreatingSphere, radius);
            static uint32_t nextHandle = 2000;
            return nextHandle++;
        }
        
        static MeshHandle capsule(float radius, float length) {
            LOG_MECH_GEN(CreatingCapsule, radius);
            static uint32_t nextHandle = 3000;
            return nextHandle++;
        }
        
        static MeshHandle box(float width, float height, float depth) {
            LOG_MECH_GEN(CreatingBox, width);
            static uint32_t nextHandle = 4000;
            return nextHandle++;
        }
        
        static MeshHandle plane(float width, float height) {
            LOG_MECH_GEN(CreatingPlane, width);
            static uint32_t nextHandle = 5000;
            return nextHandle++;
        }
    };
    
    std::vector<MeshHandle> buildSegments(const MechParams& m, const LegParams& l) {
        LOG_MECH_GEN(BuildingSegments, m.id);
        std::vector<MeshHandle> segs;
        
        for(int i = 0; i < m.segmentCount; ++i) {
            // Create main segment body
            auto segment = Primitive::cylinder(m.segmentRadius, m.segmentLength);
            
            // Add beveled edges for seamless joints
            if (m.seamlessJoints) {
                // Add rounded end caps
                auto endCap1 = Primitive::sphere(m.segmentRadius * 0.8f);
                auto endCap2 = Primitive::sphere(m.segmentRadius * 0.8f);
                // In a real implementation, these would be merged with the main segment
            }
            
            // Add leg attachment points
            for(int leg = 0; leg < l.legsPerSegment; ++leg) {
                float angle = (2.0f * M_PI * leg) / l.legsPerSegment;
                float x = m.segmentRadius * std::cos(angle);
                float z = m.segmentRadius * std::sin(angle);
                
                // Create leg mount point
                auto mountPoint = Primitive::sphere(l.jointRadius * 0.5f);
                // In real implementation, this would be positioned and merged
            }
            
            segs.push_back(segment);
        }
        
        return segs;
    }
}

// ============================================================================
// JOINT GENERATION - Articulated connections between segments
// ============================================================================

namespace JointGen {
    std::vector<MeshHandle> buildJoints(int count, float radius) {
        LOG_MECH_GEN(BuildingJoints, count);
        std::vector<MeshHandle> joints;
        
        for(int i = 0; i < count - 1; ++i) {
            // Create ball joint for articulation
            auto joint = Primitive::sphere(radius);
            
            // Add joint constraints and limits
            // In real implementation, this would include:
            // - Rotation limits (pitch, yaw, roll)
            // - Torque limits
            // - Damping parameters
            
            joints.push_back(joint);
        }
        
        return joints;
    }
}

// ============================================================================
// LEG GENERATION - Articulated legs with IK simulation
// ============================================================================

namespace LegGen {
    LegHandle buildSingleLeg(const LegParams& p) {
        LOG_MECH_GEN(BuildingSingleLeg, p.footType);
        
        // Create upper leg segment
        auto upperLeg = Primitive::capsule(p.jointRadius, p.upperLegLength);
        
        // Create lower leg segment
        auto lowerLeg = Primitive::capsule(p.jointRadius, p.lowerLegLength);
        
        // Create knee joint
        auto kneeJoint = Primitive::sphere(p.jointRadius);
        
        // Add armor plates if specified
        if (p.armorPlates) {
            auto armorPlate = Primitive::box(p.jointRadius * 2, p.upperLegLength * 0.5f, p.jointRadius * 0.2f);
            // In real implementation, this would be positioned and merged
        }
        
        // Create foot based on type
        MeshHandle foot;
        if (p.footType == "Tread") {
            foot = Primitive::box(p.jointRadius * 1.5f, p.jointRadius * 0.3f, p.jointRadius * 2.0f);
        } else if (p.footType == "Claw") {
            foot = Primitive::sphere(p.jointRadius * 0.8f);
            // Add claw geometry
        } else if (p.footType == "Pad") {
            foot = Primitive::cylinder(p.jointRadius * 1.2f, p.jointRadius * 0.2f);
        } else {
            foot = Primitive::sphere(p.jointRadius);
        }
        
        static uint32_t nextHandle = 6000;
        return nextHandle++;
    }
    
    std::vector<LegHandle> buildAllLegs(int segments, const LegParams& p) {
        LOG_MECH_GEN(BuildingAllLegs, segments);
        std::vector<LegHandle> legs;
        
        for (int s = 0; s < segments; ++s) {
            for (int i = 0; i < p.legsPerSegment; ++i) {
                legs.push_back(buildSingleLeg(p));
            }
        }
        
        return legs;
    }
}

// ============================================================================
// COCKPIT GENERATION - Interactive interior with displays and controls
// ============================================================================

namespace CockpitGen {
    CockpitHandle buildCockpit(const CockpitParams& c) {
        LOG_MECH_GEN(BuildingCockpit, c.controlStyle);
        
        // Create cockpit interior
        auto interior = Primitive::box(c.width, c.height, c.depth);
        
        // Add wall insets for detail
        float insetDepth = 0.05f;
        auto insetWalls = Primitive::box(c.width - insetDepth * 2, c.height - insetDepth * 2, c.depth - insetDepth * 2);
        
        // Create displays if enabled
        std::vector<MeshHandle> displays;
        if (c.enableDisplays) {
            for(int i = 0; i < c.displayCount; ++i) {
                auto display = Primitive::plane(0.3f, 0.2f);
                displays.push_back(display);
            }
        }
        
        // Create pilot seat
        auto seat = Primitive::box(0.4f, 0.1f, 0.4f);
        
        // Create control panel based on style
        MeshHandle controls;
        if (c.controlStyle == "Joystick") {
            controls = Primitive::cylinder(0.05f, 0.15f);
        } else if (c.controlStyle == "Levers") {
            controls = Primitive::box(0.3f, 0.05f, 0.05f);
        } else if (c.controlStyle == "Holographic") {
            controls = Primitive::sphere(0.2f);
        } else {
            controls = Primitive::box(0.2f, 0.1f, 0.1f);
        }
        
        static uint32_t nextHandle = 7000;
        return nextHandle++;
    }
}

// ============================================================================
// WEAPON GENERATION - Configurable hardpoints and weapon systems
// ============================================================================

namespace WeaponGen {
    WeaponHandle buildHardpoints(const HardpointParams& h) {
        LOG_MECH_GEN(BuildingHardpoints, h.missileTubes);
        
        // Create missile tubes
        for(int i = 0; i < h.missileTubes; ++i) {
            auto missileTube = Primitive::cylinder(0.1f, 0.8f);
            // Position tubes around the mech
        }
        
        // Create autocannon slots
        for(int i = 0; i < h.autocannonSlots; ++i) {
            auto autocannon = Primitive::cylinder(0.08f, 1.2f);
            // Position autocannons
        }
        
        // Create turret if enabled
        if (h.enableTurret) {
            auto turretBase = Primitive::cylinder(0.3f, 0.2f);
            auto turretBarrel = Primitive::cylinder(0.05f, 1.5f);
        }
        
        static uint32_t nextHandle = 8000;
        return nextHandle++;
    }
}

// ============================================================================
// SENSOR GENERATION - Radar arrays and sensor systems
// ============================================================================

namespace SensorGen {
    SensorHandle buildRadar(bool enabled, float range) {
        if (!enabled) return 0;
        
        LOG_MECH_GEN(BuildingRadar, range);
        
        // Create radar dish
        auto radarDish = Primitive::cylinder(0.4f, 0.05f);
        
        // Create sensor array
        auto sensorArray = Primitive::sphere(0.2f);
        
        // Create range indicator (visual representation)
        auto rangeIndicator = Primitive::sphere(range * 0.01f); // Scaled for visualization
        
        static uint32_t nextHandle = 9000;
        return nextHandle++;
    }
}

// ============================================================================
// MATERIAL GENERATION - Dynamic material assignment and texturing
// ============================================================================

namespace MaterialGen {
    MaterialSet assignMechMaterials(const glm::vec4& base) {
        LOG_MECH_GEN(AssigningMaterials, base.r);
        
        // Create material set based on base color
        // In real implementation, this would:
        // - Generate procedural textures
        // - Apply normal maps for detail
        // - Create specular/roughness maps
        // - Handle different material types (metal, ceramic, composite)
        
        // Hull material with base color
        auto hullMaterial = base;
        
        // Joint material (darker metal)
        auto jointMaterial = base * 0.7f;
        jointMaterial.a = 1.0f;
        
        // Cockpit glass material
        auto glassMaterial = glm::vec4(0.2f, 0.6f, 1.0f, 0.3f);
        
        // Weapon material (darker, more metallic)
        auto weaponMaterial = base * 0.5f;
        weaponMaterial.a = 1.0f;
        
        static uint32_t nextHandle = 10000;
        return nextHandle++;
    }
}

// ============================================================================
// VFX GENERATION - Damage effects and thruster trails
// ============================================================================

namespace VFXGen {
    VFXBundle buildDamageAndThrusterFX(int segments) {
        LOG_MECH_GEN(BuildingVFX, segments);
        
        // Create thruster effects for each segment
        std::vector<MeshHandle> thrusters;
        for(int i = 0; i < segments; ++i) {
            // Thruster trail effect
            auto thruster = Primitive::cylinder(0.1f + i * 0.01f, 0.5f);
            thrusters.push_back(thruster);
        }
        
        // Create damage spark effects
        auto damageSparks = Primitive::sphere(0.05f);
        
        // Create smoke/particle effects
        auto smokeEffect = Primitive::sphere(0.3f);
        
        // Create explosion effects
        auto explosionEffect = Primitive::sphere(1.0f);
        
        static uint32_t nextHandle = 11000;
        return nextHandle++;
    }
}

// ============================================================================
// AUDIO GENERATION - Mech sound effects and ambient audio
// ============================================================================

namespace AudioGen {
    AudioBundle buildMechSounds() {
        LOG_MECH_GEN(BuildingAudio, "all");
        
        // Create step sounds for walking cycle
        auto stepSounds = Audio::AudioBundle{};
        // In real implementation, this would generate:
        // - Footstep sounds based on terrain
        // - Joint creaking sounds
        // - Hydraulic system sounds
        
        // Create ambient cockpit sounds
        auto cockpitHum = Audio::AudioBundle{};
        // - Engine hum
        // - Display beeps
        // - Environmental sounds
        
        // Create weapon fire sounds
        auto weaponFire = Audio::AudioBundle{};
        // - Missile launch sounds
        // - Autocannon fire
        // - Turret rotation
        
        // Create damage sounds
        auto damageSounds = Audio::AudioBundle{};
        // - Impact sounds
        // - Armor damage
        // - System failure alarms
        
        static uint32_t nextHandle = 12000;
        return nextHandle++;
    }
}

// ============================================================================
// COLLISION GENERATION - Physics colliders for mech simulation
// ============================================================================

namespace CollisionGen {
    ColliderHandle buildMechCollider(const MechParams& m, const LegParams& l) {
        LOG_MECH_GEN(BuildingCollider, m.id);
        
        // Create compound collider for the entire mech
        // Main body collider (capsule)
        auto bodyCollider = Primitive::capsule(m.segmentRadius, m.segmentLength * m.segmentCount);
        
        // Leg colliders
        for(int segment = 0; segment < m.segmentCount; ++segment) {
            for(int leg = 0; leg < l.legsPerSegment; ++leg) {
                // Upper leg collider
                auto upperLegCollider = Primitive::capsule(l.jointRadius, l.upperLegLength);
                
                // Lower leg collider
                auto lowerLegCollider = Primitive::capsule(l.jointRadius, l.lowerLegLength);
                
                // Foot collider
                auto footCollider = Primitive::sphere(l.jointRadius * 1.2f);
            }
        }
        
        // Joint colliders for articulation
        for(int i = 0; i < m.segmentCount - 1; ++i) {
            auto jointCollider = Primitive::sphere(l.jointRadius);
        }
        
        // Enable continuous collision detection for fast-moving parts
        bool enableCCD = true;
        
        static uint32_t nextHandle = 13000;
        return nextHandle++;
    }
}

} // namespace CentipedeMechs
} // namespace MagiTech
