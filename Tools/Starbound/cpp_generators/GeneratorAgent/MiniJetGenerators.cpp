#include "MiniJetFactory.hpp"
#include "core/Log.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>

namespace MiniJetGen {

// DefinitionParser implementation
namespace DefinitionParser {

MiniJetDefinition parseFromYAML(const std::string& filePath) {
    MiniJetDefinition def;
    
    try {
        YAML::Node root = YAML::LoadFile(filePath);
        
        // Parse basic info
        def.name = root["name"].as<std::string>();
        def.version = root["version"].as<std::string>();
        
        // Parse modules
        if (root["modules"]) {
            for (const auto& moduleNode : root["modules"]) {
                ModuleDefinition module;
                module.id = moduleNode.first.as<std::string>();
                
                const auto& moduleData = moduleNode.second;
                module.meshPath = moduleData["mesh"].as<std::string>();
                module.attachBone = moduleData["attachBone"].as<std::string>();
                
                if (moduleData["offset"]) {
                    auto offset = moduleData["offset"];
                    module.offset = {offset[0].as<float>(), offset[1].as<float>(), offset[2].as<float>()};
                }
                
                if (moduleData["scale"]) {
                    auto scale = moduleData["scale"];
                    module.scale = {scale[0].as<float>(), scale[1].as<float>(), scale[2].as<float>()};
                }
                
                // Parse thruster-specific parameters
                if (moduleData["thrustForce"]) {
                    module.thrustForce = moduleData["thrustForce"].as<float>();
                }
                
                if (moduleData["thrustDirection"]) {
                    auto dir = moduleData["thrustDirection"];
                    module.thrustDirection = {dir[0].as<float>(), dir[1].as<float>(), dir[2].as<float>()};
                }
                
                if (moduleData["heatDistortion"]) {
                    module.heatDistortion = moduleData["heatDistortion"].as<float>();
                }
                
                // Parse control surface parameters
                if (moduleData["controlSurface"]) {
                    std::string surfaceType = moduleData["controlSurface"].as<std::string>();
                    if (surfaceType == "aileron") module.controlSurface = ControlSurfaceType::Aileron;
                    else if (surfaceType == "elevator") module.controlSurface = ControlSurfaceType::Elevator;
                    else if (surfaceType == "rudder") module.controlSurface = ControlSurfaceType::Rudder;
                    else if (surfaceType == "flap") module.controlSurface = ControlSurfaceType::Flap;
                    else if (surfaceType == "spoiler") module.controlSurface = ControlSurfaceType::Spoiler;
                }
                
                if (moduleData["maxDeflection"]) {
                    module.maxDeflection = moduleData["maxDeflection"].as<float>();
                }
                
                // Parse weapon parameters
                if (moduleData["weaponType"]) {
                    module.weaponType = moduleData["weaponType"].as<std::string>();
                }
                
                if (moduleData["weaponRange"]) {
                    module.weaponRange = moduleData["weaponRange"].as<float>();
                }
                
                def.modules.push_back(module);
            }
        }
        
        // Parse cockpit
        if (root["cockpit"]) {
            const auto& cockpitNode = root["cockpit"];
            def.cockpit.meshPath = cockpitNode["mesh"].as<std::string>();
            def.cockpit.attachBone = cockpitNode["attachBone"].as<std::string>();
            
            if (cockpitNode["seatPosition"]) {
                auto pos = cockpitNode["seatPosition"];
                def.cockpit.seatPosition = {pos[0].as<float>(), pos[1].as<float>(), pos[2].as<float>()};
            }
            
            if (cockpitNode["hudAnchors"]) {
                const auto& anchors = cockpitNode["hudAnchors"];
                for (size_t i = 0; i < 4 && i < anchors.size(); ++i) {
                    auto anchor = anchors[i];
                    def.cockpit.hudAnchors[i] = {anchor[0].as<float>(), anchor[1].as<float>(), anchor[2].as<float>()};
                }
            }
            
            if (cockpitNode["canopyMaterial"]) {
                def.cockpit.canopyMaterial = cockpitNode["canopyMaterial"].as<std::string>();
            }
            
            if (cockpitNode["canopyTransparency"]) {
                def.cockpit.canopyTransparency = cockpitNode["canopyTransparency"].as<float>();
            }
            
            if (cockpitNode["enableHolographicHUD"]) {
                def.cockpit.enableHolographicHUD = cockpitNode["enableHolographicHUD"].as<bool>();
            }
        }
        
        // Parse Magitech materials
        if (root["magitechMaterials"]) {
            const auto& materials = root["magitechMaterials"];
            
            if (materials["runeGlow"]) {
                const auto& runeGlow = materials["runeGlow"];
                if (runeGlow["emissiveColor"]) {
                    auto color = runeGlow["emissiveColor"];
                    def.magitechMaterials.runeGlow.emissiveColor = {color[0].as<float>(), color[1].as<float>(), color[2].as<float>()};
                }
                if (runeGlow["pulseRate"]) def.magitechMaterials.runeGlow.pulseRate = runeGlow["pulseRate"].as<float>();
                if (runeGlow["patternScale"]) def.magitechMaterials.runeGlow.patternScale = runeGlow["patternScale"].as<float>();
                if (runeGlow["glowIntensity"]) def.magitechMaterials.runeGlow.glowIntensity = runeGlow["glowIntensity"].as<float>();
            }
            
            if (materials["engineHeat"]) {
                const auto& engineHeat = materials["engineHeat"];
                if (engineHeat["distortionIntensity"]) def.magitechMaterials.engineHeat.distortionIntensity = engineHeat["distortionIntensity"].as<float>();
                if (engineHeat["flickerRate"]) def.magitechMaterials.engineHeat.flickerRate = engineHeat["flickerRate"].as<float>();
                if (engineHeat["heatColor"]) {
                    auto color = engineHeat["heatColor"];
                    def.magitechMaterials.engineHeat.heatColor = {color[0].as<float>(), color[1].as<float>(), color[2].as<float>()};
                }
                if (engineHeat["maxTemperature"]) def.magitechMaterials.engineHeat.maxTemperature = engineHeat["maxTemperature"].as<float>();
            }
            
            if (materials["energyTrail"]) {
                const auto& energyTrail = materials["energyTrail"];
                if (energyTrail["trailColor"]) {
                    auto color = energyTrail["trailColor"];
                    def.magitechMaterials.energyTrail.trailColor = {color[0].as<float>(), color[1].as<float>(), color[2].as<float>()};
                }
                if (energyTrail["trailLength"]) def.magitechMaterials.energyTrail.trailLength = energyTrail["trailLength"].as<float>();
                if (energyTrail["trailWidth"]) def.magitechMaterials.energyTrail.trailWidth = energyTrail["trailWidth"].as<float>();
                if (energyTrail["fadeRate"]) def.magitechMaterials.energyTrail.fadeRate = energyTrail["fadeRate"].as<float>();
            }
        }
        
        // Parse flight parameters
        if (root["flightParameters"]) {
            const auto& flight = root["flightParameters"];
            if (flight["maxSpeed"]) def.flightParameters.maxSpeed = flight["maxSpeed"].as<float>();
            if (flight["maxAltitude"]) def.flightParameters.maxAltitude = flight["maxAltitude"].as<float>();
            if (flight["maxThrust"]) def.flightParameters.maxThrust = flight["maxThrust"].as<float>();
            if (flight["liftCoefficient"]) def.flightParameters.liftCoefficient = flight["liftCoefficient"].as<float>();
            if (flight["dragCoefficient"]) def.flightParameters.dragCoefficient = flight["dragCoefficient"].as<float>();
            if (flight["turnRate"]) def.flightParameters.turnRate = flight["turnRate"].as<float>();
            if (flight["climbRate"]) def.flightParameters.climbRate = flight["climbRate"].as<float>();
            
            if (flight["controlSurface"]) {
                for (const auto& surface : flight["controlSurface"]) {
                    std::string name = surface.first.as<std::string>();
                    float limit = surface.second["maxDeflection"].as<float>();
                    def.flightParameters.controlSurfaceLimits[name] = limit;
                }
            }
        }
        
        // Parse animations
        if (root["animations"]) {
            for (const auto& animNode : root["animations"]) {
                AnimationDefinition anim;
                anim.id = animNode["id"].as<std::string>();
                anim.path = animNode["path"].as<std::string>();
                
                std::string typeStr = animNode["type"].as<std::string>();
                if (typeStr == "takeoff") anim.type = AnimationType::Takeoff;
                else if (typeStr == "hover") anim.type = AnimationType::Hover;
                else if (typeStr == "forward_flight") anim.type = AnimationType::ForwardFlight;
                else if (typeStr == "banking") anim.type = AnimationType::Banking;
                else if (typeStr == "landing") anim.type = AnimationType::Landing;
                else if (typeStr == "cockpit_open") anim.type = AnimationType::CockpitOpen;
                else if (typeStr == "cockpit_close") anim.type = AnimationType::CockpitClose;
                else if (typeStr == "weapon_deploy") anim.type = AnimationType::WeaponDeploy;
                else if (typeStr == "weapon_retract") anim.type = AnimationType::WeaponRetract;
                
                if (animNode["speed"]) anim.speed = animNode["speed"].as<float>();
                if (animNode["loop"]) anim.loop = animNode["loop"].as<bool>();
                if (animNode["blendTime"]) anim.blendTime = animNode["blendTime"].as<float>();
                
                def.animations.push_back(anim);
            }
        }
        
        // Parse physics
        if (root["physics"]) {
            const auto& physics = root["physics"];
            if (physics["totalMass"]) def.physics.totalMass = physics["totalMass"].as<float>();
            if (physics["centerOfMass"]) {
                auto com = physics["centerOfMass"];
                def.physics.centerOfMass = {com[0].as<float>(), com[1].as<float>(), com[2].as<float>()};
            }
            
            if (physics["moduleMass"]) {
                for (const auto& mass : physics["moduleMass"]) {
                    std::string moduleName = mass.first.as<std::string>();
                    float massValue = mass.second.as<float>();
                    def.physics.moduleMass[moduleName] = massValue;
                }
            }
        }
        
        // Parse LODs
        if (root["lods"]) {
            for (const auto& lodNode : root["lods"]) {
                LODDefinition lod;
                std::string qualityStr = lodNode["quality"].as<std::string>();
                if (qualityStr == "ultra") lod.quality = Quality::Ultra;
                else if (qualityStr == "high") lod.quality = Quality::High;
                else if (qualityStr == "medium") lod.quality = Quality::Medium;
                else if (qualityStr == "low") lod.quality = Quality::Low;
                
                if (lodNode["meshDecimate"]) lod.meshDecimate = lodNode["meshDecimate"].as<float>();
                if (lodNode["materialDetail"]) lod.materialDetail = lodNode["materialDetail"].as<float>();
                if (lodNode["maxBoneInfluences"]) lod.maxBoneInfluences = lodNode["maxBoneInfluences"].as<int>();
                if (lodNode["enableShadows"]) lod.enableShadows = lodNode["enableShadows"].as<bool>();
                if (lodNode["enableReflections"]) lod.enableReflections = lodNode["enableReflections"].as<bool>();
                
                def.lods.push_back(lod);
            }
        }
        
        Log::info("Successfully parsed MiniJet definition: {}", def.name);
        
    } catch (const YAML::Exception& e) {
        Log::error("Failed to parse MiniJet definition from {}: {}", filePath, e.what());
    } catch (const std::exception& e) {
        Log::error("Error parsing MiniJet definition from {}: {}", filePath, e.what());
    }
    
    return def;
}

bool validateDefinition(const MiniJetDefinition& def) {
    if (def.name.empty()) {
        Log::error("MiniJet definition validation failed: name is empty");
        return false;
    }
    
    if (def.modules.empty()) {
        Log::error("MiniJet definition validation failed: no modules defined");
        return false;
    }
    
    // Check for required modules
    bool hasFuselage = false;
    bool hasCockpit = false;
    
    for (const auto& module : def.modules) {
        if (module.id.empty()) {
            Log::error("MiniJet definition validation failed: module has empty ID");
            return false;
        }
        
        if (module.meshPath.empty()) {
            Log::error("MiniJet definition validation failed: module {} has empty mesh path", module.id);
            return false;
        }
        
        if (module.type == ModuleType::Fuselage) hasFuselage = true;
        if (module.type == ModuleType::Cockpit) hasCockpit = true;
    }
    
    if (!hasFuselage) {
        Log::error("MiniJet definition validation failed: no fuselage module found");
        return false;
    }
    
    if (!hasCockpit) {
        Log::error("MiniJet definition validation failed: no cockpit module found");
        return false;
    }
    
    // Validate flight parameters
    if (def.flightParameters.maxSpeed <= 0) {
        Log::error("MiniJet definition validation failed: invalid max speed");
        return false;
    }
    
    if (def.flightParameters.maxAltitude <= 0) {
        Log::error("MiniJet definition validation failed: invalid max altitude");
        return false;
    }
    
    Log::info("MiniJet definition validation passed: {}", def.name);
    return true;
}

} // namespace DefinitionParser

// ModuleAssembler implementation
namespace ModuleAssembler {

AssemblyResult assembleModules(const MiniJetDefinition& def) {
    AssemblyResult result;
    
    Log::info("Assembling modules for MiniJet: {}", def.name);
    
    // Load and process each module
    for (const auto& moduleDef : def.modules) {
        // Load mesh from file
        MeshHandle mesh = loadMeshFromFile(moduleDef.meshPath);
        if (!mesh.isValid()) {
            Log::error("Failed to load mesh for module {}: {}", moduleDef.id, moduleDef.meshPath);
            continue;
        }
        
        // Apply module transformations
        mesh = applyTransform(mesh, moduleDef.offset, moduleDef.scale, moduleDef.rotation);
        
        // Create default material
        MaterialHandle material = createDefaultMaterial();
        
        result.meshes[moduleDef.id] = mesh;
        result.materials[moduleDef.id] = material;
        
        Log::debug("Assembled module: {}", moduleDef.id);
    }
    
    // Build skeleton from module attachments
    result.skeleton = buildSkeletonFromModules(def.modules);
    
    Log::info("Module assembly completed for MiniJet: {}", def.name);
    return result;
}

void weldModuleSeams(AssemblyResult& result, const MiniJetDefinition& def) {
    Log::info("Welding module seams for MiniJet: {}", def.name);
    
    // Find adjacent modules and weld their seams
    for (const auto& module1 : def.modules) {
        for (const auto& module2 : def.modules) {
            if (module1.id == module2.id) continue;
            
            // Check if modules are adjacent based on attachment bones
            if (areModulesAdjacent(module1, module2)) {
                auto& mesh1 = result.meshes[module1.id];
                auto& mesh2 = result.meshes[module2.id];
                
                // Weld vertices at the seam
                weldMeshesAtSeam(mesh1, mesh2, module1.attachBone, module2.attachBone);
                
                Log::debug("Welded seam between {} and {}", module1.id, module2.id);
            }
        }
    }
    
    Log::info("Module seam welding completed");
}

void bakeSkinWeights(AssemblyResult& result, const MiniJetDefinition& def) {
    Log::info("Baking skin weights for MiniJet: {}", def.name);
    
    // Bake skin weights for each module based on skeleton
    for (const auto& moduleDef : def.modules) {
        auto& mesh = result.meshes[moduleDef.id];
        
        // Calculate skin weights based on distance to bones
        bakeSkinWeightsForMesh(mesh, result.skeleton, moduleDef.attachBone);
        
        Log::debug("Baked skin weights for module: {}", moduleDef.id);
    }
    
    Log::info("Skin weight baking completed");
}

} // namespace ModuleAssembler

// MaterialSynthesizer implementation
namespace MaterialSynthesizer {

MaterialResult synthesizeMagitechMaterials(const MiniJetDefinition& def) {
    MaterialResult result;
    
    Log::info("Synthesizing Magitech materials for MiniJet: {}", def.name);
    
    // Create rune glow material
    result.materials["runeGlow"] = createRuneGlowMaterial(def.magitechMaterials.runeGlow);
    result.shaderGraphs["runeGlow"] = generateRuneGlowShaderGraph(def.magitechMaterials.runeGlow);
    
    // Create engine heat material
    result.materials["engineHeat"] = createEngineHeatMaterial(def.magitechMaterials.engineHeat);
    result.shaderGraphs["engineHeat"] = generateEngineHeatShaderGraph(def.magitechMaterials.engineHeat);
    
    // Create energy trail material
    result.materials["energyTrail"] = createEnergyTrailMaterial(def.magitechMaterials.energyTrail);
    result.shaderGraphs["energyTrail"] = generateEnergyTrailShaderGraph(def.magitechMaterials.energyTrail);
    
    // Create canopy material
    result.materials["canopy"] = createCanopyMaterial(def.cockpit.canopyTransparency);
    result.shaderGraphs["canopy"] = generateCanopyShaderGraph(def.cockpit.canopyTransparency);
    
    Log::info("Magitech material synthesis completed");
    return result;
}

MaterialHandle createRuneGlowMaterial(const MagitechMaterials::RuneGlow& params) {
    MaterialHandle material = createMaterial("RuneGlow");
    
    // Set material properties
    setMaterialProperty(material, "emissiveColor", params.emissiveColor);
    setMaterialProperty(material, "pulseRate", params.pulseRate);
    setMaterialProperty(material, "patternScale", params.patternScale);
    setMaterialProperty(material, "glowIntensity", params.glowIntensity);
    
    // Set shader
    setMaterialShader(material, "MagitechRuneGlow");
    
    return material;
}

MaterialHandle createEngineHeatMaterial(const MagitechMaterials::EngineHeat& params) {
    MaterialHandle material = createMaterial("EngineHeat");
    
    // Set material properties
    setMaterialProperty(material, "distortionIntensity", params.distortionIntensity);
    setMaterialProperty(material, "flickerRate", params.flickerRate);
    setMaterialProperty(material, "heatColor", params.heatColor);
    setMaterialProperty(material, "maxTemperature", params.maxTemperature);
    
    // Set shader
    setMaterialShader(material, "MagitechEngineHeat");
    
    return material;
}

MaterialHandle createEnergyTrailMaterial(const MagitechMaterials::EnergyTrail& params) {
    MaterialHandle material = createMaterial("EnergyTrail");
    
    // Set material properties
    setMaterialProperty(material, "trailColor", params.trailColor);
    setMaterialProperty(material, "trailLength", params.trailLength);
    setMaterialProperty(material, "trailWidth", params.trailWidth);
    setMaterialProperty(material, "fadeRate", params.fadeRate);
    
    // Set shader
    setMaterialShader(material, "MagitechEnergyTrail");
    
    return material;
}

} // namespace MaterialSynthesizer

// AnimationProcessor implementation
namespace AnimationProcessor {

AnimationResult processAnimations(const MiniJetDefinition& def, const Skeleton& skeleton) {
    AnimationResult result;
    
    Log::info("Processing animations for MiniJet: {}", def.name);
    
    for (const auto& animDef : def.animations) {
        // Load animation from file
        Animation sourceAnim = loadAnimationFromFile(animDef.path);
        if (!sourceAnim.isValid()) {
            Log::error("Failed to load animation: {}", animDef.path);
            continue;
        }
        
        // Retarget animation to the assembled skeleton
        Animation retargetedAnim = retargetAnimation(sourceAnim, skeleton);
        
        // Optimize animation based on quality settings
        optimizeAnimation(retargetedAnim, Quality::High); // Default to high quality for processing
        
        result.animations[animDef.id] = retargetedAnim;
        result.blendTimes[animDef.id] = animDef.blendTime;
        
        Log::debug("Processed animation: {}", animDef.id);
    }
    
    Log::info("Animation processing completed");
    return result;
}

Animation retargetAnimation(const Animation& source, const Skeleton& target) {
    Animation retargeted = source.clone();
    
    // Map bone names between source and target skeletons
    std::unordered_map<std::string, std::string> boneMapping = createBoneMapping(source.getSkeleton(), target);
    
    // Retarget animation data
    for (auto& track : retargeted.getTracks()) {
        std::string newBoneName = boneMapping[track.boneName];
        if (!newBoneName.empty()) {
            track.boneName = newBoneName;
        }
    }
    
    return retargeted;
}

void optimizeAnimation(Animation& anim, Quality quality) {
    switch (quality) {
        case Quality::Ultra:
            // No optimization for ultra quality
            break;
        case Quality::High:
            // Light optimization
            reduceKeyframeDensity(anim, 0.8f);
            break;
        case Quality::Medium:
            // Medium optimization
            reduceKeyframeDensity(anim, 0.6f);
            simplifyCurves(anim);
            break;
        case Quality::Low:
            // Heavy optimization
            reduceKeyframeDensity(anim, 0.3f);
            simplifyCurves(anim);
            removeUnusedTracks(anim);
            break;
    }
}

} // namespace AnimationProcessor

// PhysicsRigBuilder implementation
namespace PhysicsRigBuilder {

PhysicsResult buildPhysicsRig(const MiniJetDefinition& def) {
    PhysicsResult result;
    
    Log::info("Building physics rig for MiniJet: {}", def.name);
    
    // Create physics bodies for each module
    for (const auto& moduleDef : def.modules) {
        // Get collision shape for this module
        auto shapeIt = def.physics.collisionShapes.find(moduleDef.id);
        if (shapeIt != def.physics.collisionShapes.end()) {
            PhysicsBody body = createModuleCollider(moduleDef, shapeIt->second);
            result.bodies[moduleDef.id] = body;
        }
        
        // Create thruster node if this is a thruster module
        if (moduleDef.thrustForce > 0) {
            ThrusterNode thruster = createThrusterNode(moduleDef);
            result.thrusters[moduleDef.id] = thruster;
        }
    }
    
    // Create joints between modules
    for (const auto& module1 : def.modules) {
        for (const auto& module2 : def.modules) {
            if (module1.id == module2.id) continue;
            
            if (areModulesConnected(module1, module2)) {
                std::string jointName = module1.id + "_to_" + module2.id;
                result.joints.push_back({module1.id, module2.id});
                
                Log::debug("Created joint: {}", jointName);
            }
        }
    }
    
    Log::info("Physics rig building completed");
    return result;
}

PhysicsBody createModuleCollider(const ModuleDefinition& module, const PhysicsDefinition::CollisionShape& shape) {
    PhysicsBody body = createPhysicsBody();
    
    switch (shape.type) {
        case PhysicsDefinition::CollisionShape::Type::Box:
            setBoxCollider(body, shape.size);
            break;
        case PhysicsDefinition::CollisionShape::Type::Capsule:
            setCapsuleCollider(body, shape.radius, shape.height);
            break;
        case PhysicsDefinition::CollisionShape::Type::ConvexHull:
            setConvexHullCollider(body, module.meshPath);
            break;
    }
    
    // Set mass based on module type
    float mass = getModuleMass(module.type);
    setBodyMass(body, mass);
    
    return body;
}

ThrusterNode createThrusterNode(const ModuleDefinition& module) {
    ThrusterNode thruster = createThrusterNode();
    
    // Set thruster properties
    setThrusterForce(thruster, module.thrustForce);
    setThrusterDirection(thruster, module.thrustDirection);
    setThrusterHeat(thruster, module.heatDistortion);
    
    return thruster;
}

} // namespace PhysicsRigBuilder

// LODGenerator implementation
namespace LODGenerator {

LODResult generateLODs(const MiniJetDefinition& def, const ModuleAssembler::AssemblyResult& assembly) {
    LODResult result;
    
    Log::info("Generating LODs for MiniJet: {}", def.name);
    
    // Generate LODs for each module
    for (const auto& moduleDef : def.modules) {
        const auto& sourceMesh = assembly.meshes[moduleDef.id];
        const auto& sourceMaterial = assembly.materials[moduleDef.id];
        
        // Generate LOD meshes
        for (const auto& lodDef : def.lods) {
            MeshHandle lodMesh = decimateMesh(sourceMesh, lodDef.meshDecimate);
            MaterialHandle lodMaterial = simplifyMaterial(sourceMaterial, lodDef.materialDetail);
            
            result.lodMeshes[moduleDef.id][static_cast<size_t>(lodDef.quality)] = lodMesh;
            result.lodMaterials[moduleDef.id][static_cast<size_t>(lodDef.quality)] = lodMaterial;
        }
        
        Log::debug("Generated LODs for module: {}", moduleDef.id);
    }
    
    Log::info("LOD generation completed");
    return result;
}

MeshHandle decimateMesh(const MeshHandle& mesh, float decimateFactor) {
    if (decimateFactor <= 0.0f) {
        return mesh; // No decimation
    }
    
    // Create decimated mesh
    MeshHandle decimatedMesh = createMesh();
    
    // Apply mesh decimation algorithm
    decimateMeshGeometry(mesh, decimatedMesh, decimateFactor);
    
    return decimatedMesh;
}

MaterialHandle simplifyMaterial(const MaterialHandle& material, float detailLevel) {
    if (detailLevel >= 1.0f) {
        return material; // No simplification
    }
    
    // Create simplified material
    MaterialHandle simplifiedMaterial = createMaterial();
    
    // Copy base properties
    copyMaterialProperties(material, simplifiedMaterial);
    
    // Reduce texture resolution
    reduceTextureResolution(simplifiedMaterial, detailLevel);
    
    // Simplify shader complexity
    simplifyShader(simplifiedMaterial, detailLevel);
    
    return simplifiedMaterial;
}

} // namespace LODGenerator

// PackageWriter implementation
namespace PackageWriter {

bool writePackage(const std::string& name, const MiniJetAsset& asset) {
    std::string packagePath = "assets/minijets/" + name + ".mjpack";
    
    Log::info("Writing MiniJet package: {}", packagePath);
    
    try {
        // Create package directory
        std::filesystem::create_directories(packagePath);
        
        // Write meshes
        for (const auto& [moduleName, moduleAssets] : asset.modules) {
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string meshPath = packagePath + "/meshes/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleName + ".bin";
                std::filesystem::create_directories(std::filesystem::path(meshPath).parent_path());
                writeMesh(meshPath, moduleAssets.lodMeshes[i]);
            }
        }
        
        // Write materials
        for (const auto& [moduleName, moduleAssets] : asset.modules) {
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string materialPath = packagePath + "/materials/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleName + ".mat";
                std::filesystem::create_directories(std::filesystem::path(materialPath).parent_path());
                writeMaterial(materialPath, moduleAssets.lodMaterials[i]);
            }
        }
        
        // Write animations
        for (const auto& [animName, animation] : asset.animations) {
            std::string animPath = packagePath + "/animations/" + animName + ".anim";
            std::filesystem::create_directories(std::filesystem::path(animPath).parent_path());
            writeAnimation(animPath, animation);
        }
        
        // Write physics
        std::string physicsPath = packagePath + "/physics/rig.bin";
        std::filesystem::create_directories(std::filesystem::path(physicsPath).parent_path());
        // Note: This would need the physics result from the build process
        // writePhysics(physicsPath, physicsResult);
        
        // Write metadata
        std::string metadataPath = packagePath + "/metadata.json";
        writeMetadata(metadataPath, asset.definition);
        
        Log::info("MiniJet package written successfully: {}", packagePath);
        return true;
        
    } catch (const std::exception& e) {
        Log::error("Failed to write MiniJet package: {}", e.what());
        return false;
    }
}

bool writeMesh(const std::string& path, const MeshHandle& mesh) {
    // Serialize mesh data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open mesh file for writing: {}", path);
        return false;
    }
    
    // Write mesh data
    serializeMesh(mesh, file);
    
    return true;
}

bool writeMaterial(const std::string& path, const MaterialHandle& material) {
    // Serialize material data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open material file for writing: {}", path);
        return false;
    }
    
    // Write material data
    serializeMaterial(material, file);
    
    return true;
}

bool writeAnimation(const std::string& path, const Animation& animation) {
    // Serialize animation data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open animation file for writing: {}", path);
        return false;
    }
    
    // Write animation data
    serializeAnimation(animation, file);
    
    return true;
}

bool writePhysics(const std::string& path, const PhysicsRigBuilder::PhysicsResult& physics) {
    // Serialize physics data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open physics file for writing: {}", path);
        return false;
    }
    
    // Write physics data
    serializePhysics(physics, file);
    
    return true;
}

bool writeMetadata(const std::string& path, const MiniJetDefinition& def) {
    // Write metadata as JSON
    std::ofstream file(path);
    if (!file.is_open()) {
        Log::error("Failed to open metadata file for writing: {}", path);
        return false;
    }
    
    // Convert definition to JSON and write
    std::string json = definitionToJson(def);
    file << json;
    
    return true;
}

} // namespace PackageWriter

// PackageReader implementation
namespace PackageReader {

MiniJetAsset readPackage(const std::string& name) {
    std::string packagePath = "assets/minijets/" + name + ".mjpack";
    
    Log::info("Reading MiniJet package: {}", packagePath);
    
    MiniJetAsset asset;
    
    try {
        // Read metadata
        std::string metadataPath = packagePath + "/metadata.json";
        asset.definition = readMetadata(metadataPath);
        
        // Read meshes and materials for each module
        for (const auto& moduleDef : asset.definition.modules) {
            ModuleAssets moduleAssets;
            
            // Read LOD meshes and materials
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string meshPath = packagePath + "/meshes/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleDef.id + ".bin";
                std::string materialPath = packagePath + "/materials/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleDef.id + ".mat";
                
                moduleAssets.lodMeshes[i] = readMesh(meshPath);
                moduleAssets.lodMaterials[i] = readMaterial(materialPath);
            }
            
            asset.modules[moduleDef.id] = moduleAssets;
        }
        
        // Read animations
        for (const auto& animDef : asset.definition.animations) {
            std::string animPath = packagePath + "/animations/" + animDef.id + ".anim";
            asset.animations[animDef.id] = readAnimation(animPath);
        }
        
        // Read physics
        std::string physicsPath = packagePath + "/physics/rig.bin";
        // asset.physicsBodies = readPhysics(physicsPath);
        
        Log::info("MiniJet package read successfully: {}", packagePath);
        
    } catch (const std::exception& e) {
        Log::error("Failed to read MiniJet package: {}", e.what());
    }
    
    return asset;
}

MeshHandle readMesh(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open mesh file for reading: {}", path);
        return MeshHandle{};
    }
    
    // Deserialize mesh data
    return deserializeMesh(file);
}

MaterialHandle readMaterial(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open material file for reading: {}", path);
        return MaterialHandle{};
    }
    
    // Deserialize material data
    return deserializeMaterial(file);
}

Animation readAnimation(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open animation file for reading: {}", path);
        return Animation{};
    }
    
    // Deserialize animation data
    return deserializeAnimation(file);
}

PhysicsBody readPhysics(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("Failed to open physics file for reading: {}", path);
        return PhysicsBody{};
    }
    
    // Deserialize physics data
    return deserializePhysics(file);
}

MiniJetDefinition readMetadata(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        Log::error("Failed to open metadata file for reading: {}", path);
        return MiniJetDefinition{};
    }
    
    // Read JSON and convert to definition
    std::string json((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return jsonToDefinition(json);
}

} // namespace PackageReader

// Utility functions (placeholder implementations)
namespace {
    std::string getQualityName(Quality quality) {
        switch (quality) {
            case Quality::Ultra: return "ultra";
            case Quality::High: return "high";
            case Quality::Medium: return "medium";
            case Quality::Low: return "low";
            default: return "high";
        }
    }
    
    // Placeholder implementations for engine-specific functions
    MeshHandle loadMeshFromFile(const std::string& path) { return MeshHandle{}; }
    MaterialHandle createDefaultMaterial() { return MaterialHandle{}; }
    MeshHandle applyTransform(const MeshHandle& mesh, const glm::vec3& offset, const glm::vec3& scale, const glm::quat& rotation) { return mesh; }
    Skeleton buildSkeletonFromModules(const std::vector<ModuleDefinition>& modules) { return Skeleton{}; }
    bool areModulesAdjacent(const ModuleDefinition& m1, const ModuleDefinition& m2) { return false; }
    void weldMeshesAtSeam(MeshHandle& mesh1, MeshHandle& mesh2, const std::string& bone1, const std::string& bone2) {}
    void bakeSkinWeightsForMesh(MeshHandle& mesh, const Skeleton& skeleton, const std::string& attachBone) {}
    
    MaterialHandle createMaterial(const std::string& name) { return MaterialHandle{}; }
    void setMaterialProperty(MaterialHandle& material, const std::string& name, const glm::vec3& value) {}
    void setMaterialProperty(MaterialHandle& material, const std::string& name, float value) {}
    void setMaterialShader(MaterialHandle& material, const std::string& shaderName) {}
    
    std::string generateRuneGlowShaderGraph(const MagitechMaterials::RuneGlow& params) { return ""; }
    std::string generateEngineHeatShaderGraph(const MagitechMaterials::EngineHeat& params) { return ""; }
    std::string generateEnergyTrailShaderGraph(const MagitechMaterials::EnergyTrail& params) { return ""; }
    MaterialHandle createCanopyMaterial(float transparency) { return MaterialHandle{}; }
    std::string generateCanopyShaderGraph(float transparency) { return ""; }
    
    Animation loadAnimationFromFile(const std::string& path) { return Animation{}; }
    Animation cloneAnimation(const Animation& anim) { return anim; }
    std::unordered_map<std::string, std::string> createBoneMapping(const Skeleton& source, const Skeleton& target) { return {}; }
    void reduceKeyframeDensity(Animation& anim, float factor) {}
    void simplifyCurves(Animation& anim) {}
    void removeUnusedTracks(Animation& anim) {}
    
    PhysicsBody createPhysicsBody() { return PhysicsBody{}; }
    void setBoxCollider(PhysicsBody& body, const glm::vec3& size) {}
    void setCapsuleCollider(PhysicsBody& body, float radius, float height) {}
    void setConvexHullCollider(PhysicsBody& body, const std::string& meshPath) {}
    float getModuleMass(ModuleType type) { return 100.0f; }
    void setBodyMass(PhysicsBody& body, float mass) {}
    
    ThrusterNode createThrusterNode() { return ThrusterNode{}; }
    void setThrusterForce(ThrusterNode& thruster, float force) {}
    void setThrusterDirection(ThrusterNode& thruster, const glm::vec3& direction) {}
    void setThrusterHeat(ThrusterNode& thruster, float heat) {}
    
    bool areModulesConnected(const ModuleDefinition& m1, const ModuleDefinition& m2) { return false; }
    
    MeshHandle createMesh() { return MeshHandle{}; }
    void decimateMeshGeometry(const MeshHandle& source, MeshHandle& target, float factor) {}
    
    MaterialHandle createMaterial() { return MaterialHandle{}; }
    void copyMaterialProperties(const MaterialHandle& source, MaterialHandle& target) {}
    void reduceTextureResolution(MaterialHandle& material, float factor) {}
    void simplifyShader(MaterialHandle& material, float factor) {}
    
    void serializeMesh(const MeshHandle& mesh, std::ofstream& file) {}
    void serializeMaterial(const MaterialHandle& material, std::ofstream& file) {}
    void serializeAnimation(const Animation& animation, std::ofstream& file) {}
    void serializePhysics(const PhysicsRigBuilder::PhysicsResult& physics, std::ofstream& file) {}
    std::string definitionToJson(const MiniJetDefinition& def) { return "{}"; }
    
    MeshHandle deserializeMesh(std::ifstream& file) { return MeshHandle{}; }
    MaterialHandle deserializeMaterial(std::ifstream& file) { return MaterialHandle{}; }
    Animation deserializeAnimation(std::ifstream& file) { return Animation{}; }
    PhysicsBody deserializePhysics(std::ifstream& file) { return PhysicsBody{}; }
    MiniJetDefinition jsonToDefinition(const std::string& json) { return MiniJetDefinition{}; }
}

} // namespace MiniJetGen 
