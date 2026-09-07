#include "QuadMechFactory.hpp"
#include "core/Log.hpp"
#include "vendor/yaml-cpp/yaml.h"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include <fstream>
#include <filesystem>
#include <algorithm>
#include <random>

namespace MagiTech {
namespace QuadMechGen {

#define LOG_QUAD_MECH(Action, Id) Log::info("QuadMechGen - {}: {}", #Action, Id)

// ============================================================================
// DEFINITION PARSER
// ============================================================================

namespace DefinitionParser {

QuadMechDefinition parseFromYAML(const std::string& yamlContent) {
    LOG_QUAD_MECH(ParsingDefinition, "YAML");
    
    YAML::Node node = YAML::Load(yamlContent);
    QuadMechDefinition def;
    
    // Parse basic info
    def.name = node["name"].as<std::string>();
    def.version = node["version"].as<std::string>();
    def.author = node["author"].as<std::string>();
    def.description = node["description"].as<std::string>();
    
    // Parse modules
    if (node["modules"]) {
        for (const auto& moduleNode : node["modules"]) {
            ModuleDefinition module;
            module.id = moduleNode.first.as<std::string>();
            module.meshPath = moduleNode.second["mesh"].as<std::string>();
            module.attachBone = moduleNode.second["attachBone"].as<std::string>();
            
            if (moduleNode.second["offset"]) {
                auto offset = moduleNode.second["offset"];
                module.offset = {offset[0].as<float>(), offset[1].as<float>(), offset[2].as<float>()};
            }
            
            if (moduleNode.second["scale"]) {
                auto scale = moduleNode.second["scale"];
                module.scale = {scale[0].as<float>(), scale[1].as<float>(), scale[2].as<float>()};
            }
            
            if (moduleNode.second["mass"]) {
                module.mass = moduleNode.second["mass"].as<float>();
            }
            
            def.modules.push_back(module);
        }
    }
    
    // Parse cockpit
    if (node["cockpit"]) {
        auto cockpitNode = node["cockpit"];
        if (cockpitNode["seatPosition"]) {
            auto pos = cockpitNode["seatPosition"];
            def.cockpit.seatPosition = {pos[0].as<float>(), pos[1].as<float>(), pos[2].as<float>()};
        }
        if (cockpitNode["canopyMaterial"]) {
            def.cockpit.canopyMaterial = cockpitNode["canopyMaterial"].as<std::string>();
        }
    }
    
    // Parse Magitech materials
    if (node["magitechMaterials"]) {
        auto matNode = node["magitechMaterials"];
        
        // Energy runes
        if (matNode["energyRunes"]) {
            auto runesNode = matNode["energyRunes"];
            if (runesNode["emissiveColor"]) {
                auto color = runesNode["emissiveColor"];
                def.magitechMaterials.energyRunes.emissiveColor = {color[0].as<float>(), color[1].as<float>(), color[2].as<float>()};
            }
            if (runesNode["glowIntensity"]) {
                auto intensity = runesNode["glowIntensity"];
                def.magitechMaterials.energyRunes.glowIntensity = {intensity["min"].as<float>(), intensity["max"].as<float>()};
            }
            if (runesNode["animationRate"]) {
                def.magitechMaterials.energyRunes.animationRate = runesNode["animationRate"].as<float>();
            }
        }
        
        // Energy core
        if (matNode["energyCore"]) {
            auto coreNode = matNode["energyCore"];
            if (coreNode["coreColor"]) {
                auto color = coreNode["coreColor"];
                def.magitechMaterials.energyCore.coreColor = {color[0].as<float>(), color[1].as<float>(), color[2].as<float>()};
            }
            if (coreNode["energyLevel"]) {
                def.magitechMaterials.energyCore.energyLevel = coreNode["energyLevel"].as<float>();
            }
            if (coreNode["pulseRate"]) {
                def.magitechMaterials.energyCore.pulseRate = coreNode["pulseRate"].as<float>();
            }
        }
        
        // Canopy material
        if (matNode["canopy"]) {
            auto canopyNode = matNode["canopy"];
            if (canopyNode["tint"]) {
                auto tint = canopyNode["tint"];
                def.magitechMaterials.canopy.tint = {tint[0].as<float>(), tint[1].as<float>(), tint[2].as<float>(), tint[3].as<float>()};
            }
            if (canopyNode["transparency"]) {
                def.magitechMaterials.canopy.transparency = canopyNode["transparency"].as<float>();
            }
        }
    }
    
    // Parse animations
    if (node["animations"]) {
        for (const auto& animNode : node["animations"]) {
            AnimationDefinition anim;
            anim.id = animNode["id"].as<std::string>();
            anim.path = animNode["path"].as<std::string>();
            anim.speed = animNode["speed"].as<float>();
            anim.loop = animNode["loop"].as<bool>();
            
            // Parse animation type
            std::string typeStr = animNode["type"].as<std::string>();
            if (typeStr == "walk") anim.type = AnimationType::WALK;
            else if (typeStr == "trot") anim.type = AnimationType::TROT;
            else if (typeStr == "gallop") anim.type = AnimationType::GALLOP;
            else if (typeStr == "cockpit_open") anim.type = AnimationType::COCKPIT_OPEN;
            else if (typeStr == "cockpit_close") anim.type = AnimationType::COCKPIT_CLOSE;
            else if (typeStr == "pilot_entry") anim.type = AnimationType::PILOT_ENTRY;
            else if (typeStr == "pilot_exit") anim.type = AnimationType::PILOT_EXIT;
            else if (typeStr == "idle") anim.type = AnimationType::IDLE;
            else if (typeStr == "attack") anim.type = AnimationType::ATTACK;
            else if (typeStr == "defend") anim.type = AnimationType::DEFEND;
            
            def.animations.push_back(anim);
        }
    }
    
    // Parse physics
    if (node["physics"]) {
        auto physicsNode = node["physics"];
        def.physics.totalMass = physicsNode["totalMass"].as<float>();
        
        if (physicsNode["moduleMass"]) {
            for (const auto& massNode : physicsNode["moduleMass"]) {
                std::string moduleId = massNode.first.as<std::string>();
                float mass = massNode.second.as<float>();
                def.physics.moduleMass[moduleId] = mass;
            }
        }
        
        if (physicsNode["jointLimits"]) {
            for (const auto& jointNode : physicsNode["jointLimits"]) {
                std::string jointName = jointNode.first.as<std::string>();
                JointLimit limit;
                
                if (jointNode.second["swing"]) {
                    auto swing = jointNode.second["swing"];
                    limit.swing = {swing[0].as<float>(), swing[1].as<float>()};
                }
                if (jointNode.second["twist"]) {
                    auto twist = jointNode.second["twist"];
                    limit.twist = {twist[0].as<float>(), twist[1].as<float>()};
                }
                
                def.physics.jointLimits[jointName] = limit;
            }
        }
    }
    
    // Parse LODs
    if (node["lods"]) {
        for (const auto& lodNode : node["lods"]) {
            LODDefinition lod;
            std::string qualityStr = lodNode["quality"].as<std::string>();
            if (qualityStr == "high") lod.quality = LODQuality::HIGH;
            else if (qualityStr == "medium") lod.quality = LODQuality::MEDIUM;
            else if (qualityStr == "low") lod.quality = LODQuality::LOW;
            else if (qualityStr == "ultra_low") lod.quality = LODQuality::ULTRA_LOW;
            
            lod.meshDecimate = lodNode["meshDecimate"].as<float>();
            lod.materialDetail = lodNode["materialDetail"].as<float>();
            lod.maxBones = lodNode["maxBones"].as<int>();
            lod.enableMorphTargets = lodNode["enableMorphTargets"].as<bool>();
            
            def.lods.push_back(lod);
        }
    }
    
    return def;
}

bool validateDefinition(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(ValidatingDefinition, def.name);
    
    // Check basic requirements
    if (def.name.empty()) {
        Log::error("QuadMech definition must have a name");
        return false;
    }
    
    if (def.modules.empty()) {
        Log::error("QuadMech definition must have at least one module");
        return false;
    }
    
    // Check for required modules
    bool hasChassis = false;
    bool hasLegs = false;
    
    for (const auto& module : def.modules) {
        if (module.id == "chassis") hasChassis = true;
        if (module.id.find("leg") != std::string::npos) hasLegs = true;
        
        if (module.meshPath.empty()) {
            Log::error("Module {} must have a mesh path", module.id);
            return false;
        }
        
        if (module.attachBone.empty()) {
            Log::error("Module {} must have an attach bone", module.id);
            return false;
        }
    }
    
    if (!hasChassis) {
        Log::error("QuadMech must have a chassis module");
        return false;
    }
    
    if (!hasLegs) {
        Log::error("QuadMech must have leg modules");
        return false;
    }
    
    // Validate physics
    if (def.physics.totalMass <= 0) {
        Log::error("Total mass must be positive");
        return false;
    }
    
    // Validate animations
    for (const auto& anim : def.animations) {
        if (anim.path.empty()) {
            Log::error("Animation {} must have a path", anim.id);
            return false;
        }
    }
    
    Log::info("QuadMech definition validation passed for: {}", def.name);
    return true;
}

} // namespace DefinitionParser

// ============================================================================
// MODULE ASSEMBLER
// ============================================================================

namespace ModuleAssembler {

std::vector<ModuleEntry> assembleModules(const QuadMechDefinition& def, LODQuality quality) {
    LOG_QUAD_MECH(AssemblingModules, def.name);
    
    std::vector<ModuleEntry> modules;
    
    for (const auto& moduleDef : def.modules) {
        ModuleEntry entry;
        
        // Load mesh for all LOD levels
        for (int i = 0; i < 4; ++i) {
            LODQuality lodQuality = static_cast<LODQuality>(i);
            
            // In real implementation, this would load the actual mesh
            // For now, we create placeholder handles
            static uint32_t nextMeshHandle = 1000;
            entry.lodMeshes[i] = nextMeshHandle++;
            
            // Load material for this LOD
            static uint32_t nextMaterialHandle = 2000;
            entry.lodMaterials[i] = nextMaterialHandle++;
        }
        
        // Create physics body
        static uint32_t nextPhysicsHandle = 3000;
        entry.physicsBody = nextPhysicsHandle++;
        
        // Calculate transform from module definition
        glm::mat4 transform = glm::mat4(1.0f);
        transform = glm::translate(transform, moduleDef.offset);
        transform = glm::scale(transform, moduleDef.scale);
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.x), glm::vec3(1, 0, 0));
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.y), glm::vec3(0, 1, 0));
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.z), glm::vec3(0, 0, 1));
        
        entry.transform = transform;
        
        modules.push_back(entry);
    }
    
    return modules;
}

SkeletonHandle buildSkeleton(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(BuildingSkeleton, def.name);
    
    // Create quadraped skeleton
    // Root -> Spine -> Neck -> Head
    // Root -> Spine -> Hip_FL -> Thigh_FL -> Shin_FL -> Foot_FL
    // Root -> Spine -> Hip_FR -> Thigh_FR -> Shin_FR -> Foot_FR
    // Root -> Spine -> Hip_BL -> Thigh_BL -> Shin_BL -> Foot_BL
    // Root -> Spine -> Hip_BR -> Thigh_BR -> Shin_BR -> Foot_BR
    
    static uint32_t nextSkeletonHandle = 4000;
    SkeletonHandle skeleton = nextSkeletonHandle++;
    
    // In real implementation, this would create the actual bone hierarchy
    // For now, we return a placeholder handle
    
    return skeleton;
}

} // namespace ModuleAssembler

// ============================================================================
// MATERIAL SYNTHESIZER
// ============================================================================

namespace MaterialSynthesizer {

MaterialHandle createEnergyRunesMaterial(const EnergyRunes& runes) {
    LOG_QUAD_MECH(CreatingEnergyRunesMaterial, runes.hashKey());
    
    // Create procedural material for energy runes
    // This would generate a shader with:
    // - Emissive color with pulsing intensity
    // - Noise-based flicker effect
    // - Animated glow patterns
    
    static uint32_t nextMaterialHandle = 5000;
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

MaterialHandle createEnergyCoreMaterial(const EnergyCore& core) {
    LOG_QUAD_MECH(CreatingEnergyCoreMaterial, core.hashKey());
    
    // Create procedural material for energy core
    // This would generate a shader with:
    // - Pulsing core color
    // - Energy arc effects
    // - Dynamic intensity based on energy level
    
    static uint32_t nextMaterialHandle = 6000;
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

MaterialHandle createCanopyMaterial(const CanopyMaterial& canopy) {
    LOG_QUAD_MECH(CreatingCanopyMaterial, canopy.hashKey());
    
    // Create procedural material for cockpit canopy
    // This would generate a shader with:
    // - Transparency with tint
    // - Reflectivity
    // - Optional scratch effects
    
    static uint32_t nextMaterialHandle = 7000;
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

std::vector<MaterialHandle> generateLODMaterials(const MagitechMaterials& materials, LODQuality quality) {
    LOG_QUAD_MECH(GeneratingLODMaterials, static_cast<int>(quality));
    
    std::vector<MaterialHandle> lodMaterials;
    
    // Generate LOD versions of all Magitech materials
    for (int i = 0; i < 4; ++i) {
        LODQuality lodQuality = static_cast<LODQuality>(i);
        
        // Create simplified versions for lower LODs
        static uint32_t nextLODMaterialHandle = 8000;
        MaterialHandle lodMaterial = nextLODMaterialHandle++;
        
        lodMaterials.push_back(lodMaterial);
    }
    
    return lodMaterials;
}

} // namespace MaterialSynthesizer

// ============================================================================
// ANIMATION PROCESSOR
// ============================================================================

namespace AnimationProcessor {

AnimationHandle retargetAnimation(const std::string& path, const SkeletonHandle& skeleton, AnimationType type) {
    LOG_QUAD_MECH(RetargetingAnimation, path);
    
    // Retarget animation to the quadraped skeleton
    // This would:
    // - Load the animation from file
    // - Map bone names to the target skeleton
    // - Adjust timing for quadraped locomotion
    // - Apply gait-specific modifications
    
    static uint32_t nextAnimationHandle = 9000;
    AnimationHandle animation = nextAnimationHandle++;
    
    return animation;
}

std::unordered_map<std::string, AnimationHandle> processAllAnimations(const QuadMechDefinition& def, const SkeletonHandle& skeleton) {
    LOG_QUAD_MECH(ProcessingAllAnimations, def.name);
    
    std::unordered_map<std::string, AnimationHandle> animations;
    
    for (const auto& animDef : def.animations) {
        AnimationHandle anim = retargetAnimation(animDef.path, skeleton, animDef.type);
        animations[animDef.id] = anim;
    }
    
    return animations;
}

} // namespace AnimationProcessor

// ============================================================================
// PHYSICS RIG BUILDER
// ============================================================================

namespace PhysicsRigBuilder {

PhysicsBodyHandle createModulePhysics(const ModuleDefinition& module, float mass) {
    LOG_QUAD_MECH(CreatingModulePhysics, module.id);
    
    // Create physics body for module
    // This would:
    // - Generate collision shape based on mesh
    // - Set mass and inertia
    // - Configure physics properties
    
    static uint32_t nextPhysicsHandle = 10000;
    PhysicsBodyHandle body = nextPhysicsHandle++;
    
    return body;
}

std::vector<PhysicsBodyHandle> buildPhysicsRig(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(BuildingPhysicsRig, def.name);
    
    std::vector<PhysicsBodyHandle> bodies;
    
    for (const auto& module : def.modules) {
        float mass = def.physics.moduleMass.count(module.id) ? 
                    def.physics.moduleMass.at(module.id) : module.mass;
        
        PhysicsBodyHandle body = createModulePhysics(module, mass);
        bodies.push_back(body);
    }
    
    return bodies;
}

void setupJointConstraints(const QuadMechDefinition& def, std::vector<PhysicsBodyHandle>& bodies) {
    LOG_QUAD_MECH(SettingUpJointConstraints, def.name);
    
    // Setup joint constraints between physics bodies
    // This would:
    // - Create joints between connected modules
    // - Apply joint limits from definition
    // - Configure damping and friction
    
    for (const auto& jointLimit : def.physics.jointLimits) {
        // Apply joint limits
        // In real implementation, this would create actual physics joints
    }
}

} // namespace PhysicsRigBuilder

// ============================================================================
// LOD GENERATOR
// ============================================================================

namespace LODGenerator {

MeshHandle generateLODMesh(const MeshHandle& original, LODQuality quality, float decimateFactor) {
    LOG_QUAD_MECH(GeneratingLODMesh, static_cast<int>(quality));
    
    // Generate LOD mesh by decimating the original
    // This would:
    // - Reduce vertex count based on decimateFactor
    // - Preserve important features
    // - Optimize for rendering performance
    
    static uint32_t nextLODMeshHandle = 11000;
    MeshHandle lodMesh = nextLODMeshHandle++;
    
    return lodMesh;
}

MaterialHandle generateLODMaterial(const MaterialHandle& original, LODQuality quality, float detailFactor) {
    LOG_QUAD_MECH(GeneratingLODMaterial, static_cast<int>(quality));
    
    // Generate LOD material by simplifying the original
    // This would:
    // - Reduce texture resolution
    // - Simplify shader complexity
    // - Remove expensive effects for lower LODs
    
    static uint32_t nextLODMaterialHandle = 12000;
    MaterialHandle lodMaterial = nextLODMaterialHandle++;
    
    return lodMaterial;
}

std::array<MeshHandle, 4> generateAllLODs(const MeshHandle& original, const std::vector<LODDefinition>& lods) {
    LOG_QUAD_MECH(GeneratingAllLODs, original);
    
    std::array<MeshHandle, 4> lodMeshes = {0, 0, 0, 0};
    
    for (const auto& lod : lods) {
        MeshHandle lodMesh = generateLODMesh(original, lod.quality, lod.meshDecimate);
        lodMeshes[static_cast<int>(lod.quality)] = lodMesh;
    }
    
    return lodMeshes;
}

} // namespace LODGenerator

// ============================================================================
// PACKAGE WRITER
// ============================================================================

namespace PackageWriter {

bool writeMechPackage(const QuadMechAsset& asset, const std::string& outputPath) {
    LOG_QUAD_MECH(WritingMechPackage, outputPath);
    
    // Write mech package to disk
    // This would:
    // - Serialize all meshes, materials, animations
    // - Write physics data
    // - Create package structure
    // - Compress and optimize
    
    // Create package directory structure
    std::filesystem::create_directories(outputPath);
    
    // Write metadata
    std::ofstream metadataFile(outputPath + "/metadata.json");
    if (metadataFile.is_open()) {
        metadataFile << "{\n";
        metadataFile << "  \"name\": \"" << asset.definition.name << "\",\n";
        metadataFile << "  \"version\": \"" << asset.definition.version << "\",\n";
        metadataFile << "  \"hashKey\": " << asset.hashKey << "\n";
        metadataFile << "}\n";
        metadataFile.close();
    }
    
    // Write LOD-specific data
    for (const auto& modulePair : asset.modules) {
        const std::string& moduleId = modulePair.first;
        const ModuleEntry& module = modulePair.second;
        
        for (int i = 0; i < 4; ++i) {
            LODQuality quality = static_cast<LODQuality>(i);
            std::string qualityStr;
            switch (quality) {
                case LODQuality::HIGH: qualityStr = "high"; break;
                case LODQuality::MEDIUM: qualityStr = "medium"; break;
                case LODQuality::LOW: qualityStr = "low"; break;
                case LODQuality::ULTRA_LOW: qualityStr = "ultra_low"; break;
            }
            
            // Write mesh data
            std::string meshPath = outputPath + "/meshes/" + qualityStr + "/" + moduleId + ".bin";
            std::filesystem::create_directories(std::filesystem::path(meshPath).parent_path());
            
            // Write material data
            std::string materialPath = outputPath + "/materials/" + qualityStr + "/" + moduleId + ".mat";
            std::filesystem::create_directories(std::filesystem::path(materialPath).parent_path());
        }
    }
    
    // Write skeleton
    std::string skeletonPath = outputPath + "/skeleton/skeleton.bin";
    std::filesystem::create_directories(std::filesystem::path(skeletonPath).parent_path());
    
    // Write animations
    for (const auto& animPair : asset.animations) {
        std::string animPath = outputPath + "/animations/" + animPair.first + ".anim";
        std::filesystem::create_directories(std::filesystem::path(animPath).parent_path());
    }
    
    // Write physics data
    std::string physicsPath = outputPath + "/physics/rig.bin";
    std::filesystem::create_directories(std::filesystem::path(physicsPath).parent_path());
    
    Log::info("Mech package written successfully to: {}", outputPath);
    return true;
}

MechPackage createPackageStructure(const std::string& mechName, const std::string& outputDir) {
    LOG_QUAD_MECH(CreatingPackageStructure, mechName);
    
    MechPackage package;
    package.name = mechName;
    package.version = "1.0.0";
    package.definitionPath = outputDir + "/definition.yaml";
    package.skeletonPath = outputDir + "/skeleton/skeleton.bin";
    package.physicsPath = outputDir + "/physics/rig.bin";
    package.metadataPath = outputDir + "/metadata.json";
    
    // Setup LOD paths
    std::vector<std::string> qualityStrs = {"high", "medium", "low", "ultra_low"};
    for (int i = 0; i < 4; ++i) {
        LODQuality quality = static_cast<LODQuality>(i);
        std::string qualityStr = qualityStrs[i];
        
        package.meshPaths[quality] = outputDir + "/meshes/" + qualityStr + "/";
        package.materialPaths[quality] = outputDir + "/materials/" + qualityStr + "/";
    }
    
    return package;
}

} // namespace PackageWriter

// ============================================================================
// PACKAGE READER
// ============================================================================

namespace PackageReader {

QuadMechAsset readMechPackage(const std::string& packagePath) {
    LOG_QUAD_MECH(ReadingMechPackage, packagePath);
    
    QuadMechAsset asset;
    
    // Read metadata
    std::string metadataPath = packagePath + "/metadata.json";
    std::ifstream metadataFile(metadataPath);
    if (metadataFile.is_open()) {
        // Parse metadata JSON
        // In real implementation, this would use a JSON parser
    }
    
    // Read skeleton
    std::string skeletonPath = packagePath + "/skeleton/skeleton.bin";
    static uint32_t nextSkeletonHandle = 13000;
    asset.skeleton = nextSkeletonHandle++;
    
    // Read modules for all LODs
    std::vector<std::string> qualityStrs = {"high", "medium", "low", "ultra_low"};
    for (int i = 0; i < 4; ++i) {
        LODQuality quality = static_cast<LODQuality>(i);
        std::string qualityStr = qualityStrs[i];
        
        std::string meshDir = packagePath + "/meshes/" + qualityStr + "/";
        std::string materialDir = packagePath + "/materials/" + qualityStr + "/";
        
        // Read all module files in this LOD directory
        for (const auto& entry : std::filesystem::directory_iterator(meshDir)) {
            if (entry.is_regular_file() && entry.path().extension() == ".bin") {
                std::string moduleId = entry.path().stem().string();
                
                ModuleEntry moduleEntry;
                static uint32_t nextMeshHandle = 14000;
                static uint32_t nextMaterialHandle = 15000;
                
                moduleEntry.lodMeshes[i] = nextMeshHandle++;
                moduleEntry.lodMaterials[i] = nextMaterialHandle++;
                
                asset.modules[moduleId] = moduleEntry;
            }
        }
    }
    
    // Read animations
    std::string animDir = packagePath + "/animations/";
    for (const auto& entry : std::filesystem::directory_iterator(animDir)) {
        if (entry.is_regular_file() && entry.path().extension() == ".anim") {
            std::string animId = entry.path().stem().string();
            static uint32_t nextAnimationHandle = 16000;
            asset.animations[animId] = nextAnimationHandle++;
        }
    }
    
    // Read physics data
    std::string physicsPath = packagePath + "/physics/rig.bin";
    static uint32_t nextPhysicsHandle = 17000;
    asset.rootBody = nextPhysicsHandle++;
    
    // Create Magitech materials
    static uint32_t nextMaterialHandle = 18000;
    asset.energyRunesMaterial = nextMaterialHandle++;
    asset.energyCoreMaterial = nextMaterialHandle++;
    asset.canopyMaterial = nextMaterialHandle++;
    
    return asset;
}

MechPackage readPackageMetadata(const std::string& packagePath) {
    LOG_QUAD_MECH(ReadingPackageMetadata, packagePath);
    
    MechPackage package;
    
    // Read metadata from JSON
    std::string metadataPath = packagePath + "/metadata.json";
    std::ifstream metadataFile(metadataPath);
    if (metadataFile.is_open()) {
        // Parse metadata
        // In real implementation, this would use a JSON parser
    }
    
    return package;
}

} // namespace PackageReader

} // namespace QuadMechGen
} // namespace MagiTech 
