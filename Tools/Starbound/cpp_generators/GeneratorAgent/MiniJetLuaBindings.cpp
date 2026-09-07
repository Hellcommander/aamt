#include "MiniJetLuaBindings.hpp"
#include "MiniJetFactory.hpp"
#include "core/Log.hpp"
#include <memory>

namespace MiniJetGen {

// Global instances
static std::unique_ptr<MiniJetFactory> g_factory;
static std::unique_ptr<MiniJetLoader> g_loader;
static std::unique_ptr<MiniJetEditor> g_editor;

void MiniJetLuaBindings::bind(sol::state& lua) {
    Log::info("Binding MiniJetMechGen to Lua");
    
    // Create global instances
    g_factory = std::make_unique<MiniJetFactory>();
    g_factory->initialize(4);
    
    g_loader = std::make_unique<MiniJetLoader>(g_factory);
    g_editor = std::make_unique<MiniJetEditor>(g_factory);
    
    // Bind all components
    bindEnums(lua);
    bindStructs(lua);
    bindFactory(lua);
    bindLoader(lua);
    bindEditor(lua);
    bindValidation(lua);
    
    Log::info("MiniJetMechGen Lua bindings completed");
}

void MiniJetLuaBindings::poll_assets(sol::state& lua) {
    if (g_factory) {
        g_factory->checkForUpdates();
    }
}

void MiniJetLuaBindings::shutdown() {
    if (g_factory) {
        g_factory->shutdown();
    }
    
    g_editor.reset();
    g_loader.reset();
    g_factory.reset();
    
    Log::info("MiniJetMechGen Lua bindings shutdown");
}

void MiniJetLuaBindings::bindEnums(sol::state& lua) {
    // Quality levels
    lua.new_enum<Quality>("Quality", {
        {"Ultra", Quality::Ultra},
        {"High", Quality::High},
        {"Medium", Quality::Medium},
        {"Low", Quality::Low}
    });
    
    // Module types
    lua.new_enum<ModuleType>("ModuleType", {
        {"Fuselage", ModuleType::Fuselage},
        {"Wing_Left", ModuleType::Wing_Left},
        {"Wing_Right", ModuleType::Wing_Right},
        {"Tailplane", ModuleType::Tailplane},
        {"Thruster_Main", ModuleType::Thruster_Main},
        {"Thruster_Aux", ModuleType::Thruster_Aux},
        {"Cockpit", ModuleType::Cockpit},
        {"Weapon_Left", ModuleType::Weapon_Left},
        {"Weapon_Right", ModuleType::Weapon_Right},
        {"Energy_Core", ModuleType::Energy_Core}
    });
    
    // Control surface types
    lua.new_enum<ControlSurfaceType>("ControlSurfaceType", {
        {"Aileron", ControlSurfaceType::Aileron},
        {"Elevator", ControlSurfaceType::Elevator},
        {"Rudder", ControlSurfaceType::Rudder},
        {"Flap", ControlSurfaceType::Flap},
        {"Spoiler", ControlSurfaceType::Spoiler}
    });
    
    // Magitech effect types
    lua.new_enum<MagitechEffectType>("MagitechEffectType", {
        {"RuneGlow", MagitechEffectType::RuneGlow},
        {"EngineHeat", MagitechEffectType::EngineHeat},
        {"EnergyTrail", MagitechEffectType::EnergyTrail},
        {"CanopyShield", MagitechEffectType::CanopyShield},
        {"WeaponCharge", MagitechEffectType::WeaponCharge}
    });
    
    // Animation types
    lua.new_enum<AnimationType>("AnimationType", {
        {"Takeoff", AnimationType::Takeoff},
        {"Hover", AnimationType::Hover},
        {"ForwardFlight", AnimationType::ForwardFlight},
        {"Banking", AnimationType::Banking},
        {"Landing", AnimationType::Landing},
        {"CockpitOpen", AnimationType::CockpitOpen},
        {"CockpitClose", AnimationType::CockpitClose},
        {"WeaponDeploy", AnimationType::WeaponDeploy},
        {"WeaponRetract", AnimationType::WeaponRetract}
    });
}

void MiniJetLuaBindings::bindStructs(sol::state& lua) {
    // ModuleDefinition
    lua.new_usertype<ModuleDefinition>("ModuleDefinition",
        "id", &ModuleDefinition::id,
        "type", &ModuleDefinition::type,
        "meshPath", &ModuleDefinition::meshPath,
        "attachBone", &ModuleDefinition::attachBone,
        "offset", &ModuleDefinition::offset,
        "scale", &ModuleDefinition::scale,
        "rotation", &ModuleDefinition::rotation,
        "thrustForce", &ModuleDefinition::thrustForce,
        "thrustDirection", &ModuleDefinition::thrustDirection,
        "heatDistortion", &ModuleDefinition::heatDistortion,
        "controlSurface", &ModuleDefinition::controlSurface,
        "maxDeflection", &ModuleDefinition::maxDeflection,
        "weaponType", &ModuleDefinition::weaponType,
        "weaponRange", &ModuleDefinition::weaponRange
    );
    
    // CockpitDefinition
    lua.new_usertype<CockpitDefinition>("CockpitDefinition",
        "meshPath", &CockpitDefinition::meshPath,
        "attachBone", &CockpitDefinition::attachBone,
        "seatPosition", &CockpitDefinition::seatPosition,
        "hudAnchors", &CockpitDefinition::hudAnchors,
        "canopyMaterial", &CockpitDefinition::canopyMaterial,
        "canopyTransparency", &CockpitDefinition::canopyTransparency,
        "enableHolographicHUD", &CockpitDefinition::enableHolographicHUD
    );
    
    // MagitechMaterials::RuneGlow
    lua.new_usertype<MagitechMaterials::RuneGlow>("RuneGlow",
        "emissiveColor", &MagitechMaterials::RuneGlow::emissiveColor,
        "pulseRate", &MagitechMaterials::RuneGlow::pulseRate,
        "patternScale", &MagitechMaterials::RuneGlow::patternScale,
        "glowIntensity", &MagitechMaterials::RuneGlow::glowIntensity
    );
    
    // MagitechMaterials::EngineHeat
    lua.new_usertype<MagitechMaterials::EngineHeat>("EngineHeat",
        "distortionIntensity", &MagitechMaterials::EngineHeat::distortionIntensity,
        "flickerRate", &MagitechMaterials::EngineHeat::flickerRate,
        "heatColor", &MagitechMaterials::EngineHeat::heatColor,
        "maxTemperature", &MagitechMaterials::EngineHeat::maxTemperature
    );
    
    // MagitechMaterials::EnergyTrail
    lua.new_usertype<MagitechMaterials::EnergyTrail>("EnergyTrail",
        "trailColor", &MagitechMaterials::EnergyTrail::trailColor,
        "trailLength", &MagitechMaterials::EnergyTrail::trailLength,
        "trailWidth", &MagitechMaterials::EnergyTrail::trailWidth,
        "fadeRate", &MagitechMaterials::EnergyTrail::fadeRate
    );
    
    // MagitechMaterials
    lua.new_usertype<MagitechMaterials>("MagitechMaterials",
        "runeGlow", &MagitechMaterials::runeGlow,
        "engineHeat", &MagitechMaterials::engineHeat,
        "energyTrail", &MagitechMaterials::energyTrail
    );
    
    // FlightParameters
    lua.new_usertype<FlightParameters>("FlightParameters",
        "maxSpeed", &FlightParameters::maxSpeed,
        "maxAltitude", &FlightParameters::maxAltitude,
        "maxThrust", &FlightParameters::maxThrust,
        "liftCoefficient", &FlightParameters::liftCoefficient,
        "dragCoefficient", &FlightParameters::dragCoefficient,
        "turnRate", &FlightParameters::turnRate,
        "climbRate", &FlightParameters::climbRate,
        "controlSurfaceLimits", &FlightParameters::controlSurfaceLimits
    );
    
    // AnimationDefinition
    lua.new_usertype<AnimationDefinition>("AnimationDefinition",
        "id", &AnimationDefinition::id,
        "type", &AnimationDefinition::type,
        "path", &AnimationDefinition::path,
        "speed", &AnimationDefinition::speed,
        "loop", &AnimationDefinition::loop,
        "blendTime", &AnimationDefinition::blendTime
    );
    
    // PhysicsDefinition::JointConstraint
    lua.new_usertype<PhysicsDefinition::JointConstraint>("JointConstraint",
        "minAngle", &PhysicsDefinition::JointConstraint::minAngle,
        "maxAngle", &PhysicsDefinition::JointConstraint::maxAngle,
        "damping", &PhysicsDefinition::JointConstraint::damping,
        "stiffness", &PhysicsDefinition::JointConstraint::stiffness
    );
    
    // PhysicsDefinition::CollisionShape
    lua.new_usertype<PhysicsDefinition::CollisionShape>("CollisionShape",
        "type", &PhysicsDefinition::CollisionShape::type,
        "size", &PhysicsDefinition::CollisionShape::size,
        "radius", &PhysicsDefinition::CollisionShape::radius,
        "height", &PhysicsDefinition::CollisionShape::height
    );
    
    // PhysicsDefinition
    lua.new_usertype<PhysicsDefinition>("PhysicsDefinition",
        "totalMass", &PhysicsDefinition::totalMass,
        "centerOfMass", &PhysicsDefinition::centerOfMass,
        "moduleMass", &PhysicsDefinition::moduleMass,
        "jointConstraints", &PhysicsDefinition::jointConstraints,
        "collisionShapes", &PhysicsDefinition::collisionShapes
    );
    
    // LODDefinition
    lua.new_usertype<LODDefinition>("LODDefinition",
        "quality", &LODDefinition::quality,
        "meshDecimate", &LODDefinition::meshDecimate,
        "materialDetail", &LODDefinition::materialDetail,
        "maxBoneInfluences", &LODDefinition::maxBoneInfluences,
        "enableShadows", &LODDefinition::enableShadows,
        "enableReflections", &LODDefinition::enableReflections
    );
    
    // MiniJetDefinition
    lua.new_usertype<MiniJetDefinition>("MiniJetDefinition",
        "name", &MiniJetDefinition::name,
        "version", &MiniJetDefinition::version,
        "modules", &MiniJetDefinition::modules,
        "cockpit", &MiniJetDefinition::cockpit,
        "magitechMaterials", &MiniJetDefinition::magitechMaterials,
        "flightParameters", &MiniJetDefinition::flightParameters,
        "animations", &MiniJetDefinition::animations,
        "physics", &MiniJetDefinition::physics,
        "lods", &MiniJetDefinition::lods
    );
    
    // MiniJetInstance
    lua.new_usertype<MiniJetInstance>("MiniJetInstance",
        "asset", &MiniJetInstance::asset,
        "currentLOD", &MiniJetInstance::currentLOD,
        "currentAnimation", &MiniJetInstance::currentAnimation,
        "animationTime", &MiniJetInstance::animationTime,
        "position", &MiniJetInstance::position,
        "rotation", &MiniJetInstance::rotation,
        "velocity", &MiniJetInstance::velocity,
        "throttle", &MiniJetInstance::throttle,
        "altitude", &MiniJetInstance::altitude,
        "speed", &MiniJetInstance::speed,
        "isFlying", &MiniJetInstance::isFlying,
        "isLanding", &MiniJetInstance::isLanding,
        "isTakingOff", &MiniJetInstance::isTakingOff,
        "flightTime", &MiniJetInstance::flightTime,
        "runeGlowIntensity", &MiniJetInstance::runeGlowIntensity,
        "engineHeatLevel", &MiniJetInstance::engineHeatLevel,
        "energyTrailLength", &MiniJetInstance::energyTrailLength
    );
    
    // MiniJetEditorState
    lua.new_usertype<MiniJetEditorState>("MiniJetEditorState",
        "selectedModule", &MiniJetEditorState::selectedModule,
        "selectedAnimation", &MiniJetEditorState::selectedAnimation,
        "previewLOD", &MiniJetEditorState::previewLOD,
        "previewTime", &MiniJetEditorState::previewTime,
        "showPhysics", &MiniJetEditorState::showPhysics,
        "showThrusters", &MiniJetEditorState::showThrusters,
        "showMagitechEffects", &MiniJetEditorState::showMagitechEffects,
        "runeGlowColor", &MiniJetEditorState::runeGlowColor,
        "runeGlowIntensity", &MiniJetEditorState::runeGlowIntensity,
        "engineHeatDistortion", &MiniJetEditorState::engineHeatDistortion,
        "energyTrailOpacity", &MiniJetEditorState::energyTrailOpacity,
        "maxSpeed", &MiniJetEditorState::maxSpeed,
        "maxAltitude", &MiniJetEditorState::maxAltitude,
        "thrustForce", &MiniJetEditorState::thrustForce,
        "moduleOffset", &MiniJetEditorState::moduleOffset,
        "moduleScale", &MiniJetEditorState::moduleScale,
        "moduleRotation", &MiniJetEditorState::moduleRotation
    );
}

void MiniJetLuaBindings::bindFactory(sol::state& lua) {
    // Factory namespace
    auto factory = lua["MiniJetFactory"].get_or_create<sol::table>();
    
    // Factory functions
    factory["initialize"] = [](size_t num_threads) {
        if (g_factory) g_factory->initialize(num_threads);
    };
    
    factory["shutdown"] = []() {
        if (g_factory) g_factory->shutdown();
    };
    
    factory["isInitialized"] = []() -> bool {
        return g_factory ? g_factory->isInitialized() : false;
    };
    
    factory["load"] = [](const std::string& name, Quality quality) -> std::shared_ptr<MiniJetAsset> {
        return g_factory ? g_factory->load(name, quality) : nullptr;
    };
    
    factory["generate"] = [](const std::string& definitionPath, Quality quality) -> std::shared_ptr<MiniJetAsset> {
        return g_factory ? g_factory->generate(definitionPath, quality) : nullptr;
    };
    
    factory["generatePackage"] = [](const std::string& name, const std::string& definitionPath) -> bool {
        return g_factory ? g_factory->generatePackage(name, definitionPath) : false;
    };
    
    factory["loadAsync"] = [](const std::string& name, Quality quality) -> std::future<std::shared_ptr<MiniJetAsset>> {
        return g_factory ? g_factory->loadAsync(name, quality) : std::future<std::shared_ptr<MiniJetAsset>>{};
    };
    
    factory["generateAsync"] = [](const std::string& definitionPath, Quality quality) -> std::future<std::shared_ptr<MiniJetAsset>> {
        return g_factory ? g_factory->generateAsync(definitionPath, quality) : std::future<std::shared_ptr<MiniJetAsset>>{};
    };
    
    factory["generatePackageAsync"] = [](const std::string& name, const std::string& definitionPath) -> std::future<bool> {
        return g_factory ? g_factory->generatePackageAsync(name, definitionPath) : std::future<bool>{};
    };
    
    factory["clearCache"] = []() {
        if (g_factory) g_factory->clearCache();
    };
    
    factory["preload"] = [](const std::vector<std::string>& names) {
        if (g_factory) g_factory->preload(names);
    };
    
    factory["getCacheSize"] = []() -> size_t {
        return g_factory ? g_factory->getCacheSize() : 0;
    };
    
    factory["watchForChanges"] = [](const std::string& definitionPath) {
        if (g_factory) g_factory->watchForChanges(definitionPath);
    };
    
    factory["checkForUpdates"] = []() {
        if (g_factory) g_factory->checkForUpdates();
    };
    
    factory["reloadAsset"] = [](const std::string& name) {
        if (g_factory) g_factory->reloadAsset(name);
    };
    
    factory["getMetrics"] = []() -> const MiniJetFactory::Metrics& {
        static MiniJetFactory::Metrics empty;
        return g_factory ? g_factory->getMetrics() : empty;
    };
    
    factory["resetMetrics"] = []() {
        if (g_factory) g_factory->resetMetrics();
    };
    
    factory["validateDefinition"] = [](const std::string& definitionPath) -> bool {
        return g_factory ? g_factory->validateDefinition(definitionPath) : false;
    };
    
    factory["getAvailableAssets"] = []() -> std::vector<std::string> {
        return g_factory ? g_factory->getAvailableAssets() : std::vector<std::string>{};
    };
    
    factory["getAssetHash"] = [](const std::string& name) -> size_t {
        return g_factory ? g_factory->getAssetHash(name) : 0;
    };
}

void MiniJetLuaBindings::bindLoader(sol::state& lua) {
    // Loader namespace
    auto loader = lua["MiniJetLoader"].get_or_create<sol::table>();
    
    // Loader functions
    loader["createInstance"] = [](const std::string& name, Quality quality) -> MiniJetInstance {
        return g_loader ? g_loader->createInstance(name, quality) : MiniJetInstance{};
    };
    
    loader["createInstanceFromAsset"] = [](std::shared_ptr<MiniJetAsset> asset) -> MiniJetInstance {
        return g_loader ? g_loader->createInstance(asset) : MiniJetInstance{};
    };
    
    loader["updateInstance"] = [](MiniJetInstance& instance, float deltaTime) {
        if (g_loader) g_loader->updateInstance(instance, deltaTime);
    };
    
    loader["setAnimation"] = [](MiniJetInstance& instance, const std::string& animationName) {
        if (g_loader) g_loader->setAnimation(instance, animationName);
    };
    
    loader["setLOD"] = [](MiniJetInstance& instance, Quality quality) {
        if (g_loader) g_loader->setLOD(instance, quality);
    };
    
    loader["setThrottle"] = [](MiniJetInstance& instance, float throttle) {
        if (g_loader) g_loader->setThrottle(instance, throttle);
    };
    
    loader["setControlInput"] = [](MiniJetInstance& instance, const glm::vec3& input) {
        if (g_loader) g_loader->setControlInput(instance, input);
    };
    
    loader["updateFlightPhysics"] = [](MiniJetInstance& instance, float deltaTime) {
        if (g_loader) g_loader->updateFlightPhysics(instance, deltaTime);
    };
    
    loader["setRuneGlowIntensity"] = [](MiniJetInstance& instance, float intensity) {
        if (g_loader) g_loader->setRuneGlowIntensity(instance, intensity);
    };
    
    loader["setEngineHeatLevel"] = [](MiniJetInstance& instance, float heat) {
        if (g_loader) g_loader->setEngineHeatLevel(instance, heat);
    };
    
    loader["setEnergyTrailLength"] = [](MiniJetInstance& instance, float length) {
        if (g_loader) g_loader->setEnergyTrailLength(instance, length);
    };
}

void MiniJetLuaBindings::bindEditor(sol::state& lua) {
    // Editor namespace
    auto editor = lua["MiniJetEditor"].get_or_create<sol::table>();
    
    // Editor functions
    editor["showEditorPanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showEditorPanel(assetName);
    };
    
    editor["showModulePanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showModulePanel(assetName);
    };
    
    editor["showMaterialPanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showMaterialPanel(assetName);
    };
    
    editor["showAnimationPanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showAnimationPanel(assetName);
    };
    
    editor["showPhysicsPanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showPhysicsPanel(assetName);
    };
    
    editor["showFlightPanel"] = [](const std::string& assetName) {
        if (g_editor) g_editor->showFlightPanel(assetName);
    };
    
    editor["getPreviewInstance"] = [](const std::string& assetName) -> MiniJetInstance& {
        static MiniJetInstance empty;
        return g_editor ? g_editor->getPreviewInstance(assetName) : empty;
    };
    
    editor["updatePreview"] = [](const std::string& assetName, float deltaTime) {
        if (g_editor) g_editor->updatePreview(assetName, deltaTime);
    };
    
    editor["rebuildAsset"] = [](const std::string& assetName) {
        if (g_editor) g_editor->rebuildAsset(assetName);
    };
    
    editor["exportAsset"] = [](const std::string& assetName, const std::string& outputPath) {
        if (g_editor) g_editor->exportAsset(assetName, outputPath);
    };
    
    editor["importAsset"] = [](const std::string& inputPath) {
        if (g_editor) g_editor->importAsset(inputPath);
    };
    
    editor["getEditorState"] = [](const std::string& assetName) -> MiniJetEditorState& {
        static MiniJetEditorState empty;
        return g_editor ? g_editor->getEditorState(assetName) : empty;
    };
    
    editor["saveEditorState"] = [](const std::string& assetName) {
        if (g_editor) g_editor->saveEditorState(assetName);
    };
    
    editor["loadEditorState"] = [](const std::string& assetName) {
        if (g_editor) g_editor->loadEditorState(assetName);
    };
}

void MiniJetLuaBindings::bindValidation(sol::state& lua) {
    // Validation namespace
    auto validation = lua["MiniJetValidation"].get_or_create<sol::table>();
    
    // Validation functions
    validation["validateDefinition"] = [](const MiniJetDefinition& def) -> bool {
        return DefinitionParser::validateDefinition(def);
    };
    
    validation["validateModule"] = [](const ModuleDefinition& module) -> bool {
        if (module.id.empty()) return false;
        if (module.meshPath.empty()) return false;
        if (module.attachBone.empty()) return false;
        return true;
    };
    
    validation["validateCockpit"] = [](const CockpitDefinition& cockpit) -> bool {
        if (cockpit.meshPath.empty()) return false;
        if (cockpit.attachBone.empty()) return false;
        if (cockpit.canopyTransparency < 0.0f || cockpit.canopyTransparency > 1.0f) return false;
        return true;
    };
    
    validation["validateFlightParameters"] = [](const FlightParameters& params) -> bool {
        if (params.maxSpeed <= 0) return false;
        if (params.maxAltitude <= 0) return false;
        if (params.maxThrust <= 0) return false;
        if (params.liftCoefficient <= 0) return false;
        if (params.dragCoefficient <= 0) return false;
        return true;
    };
    
    validation["validatePhysics"] = [](const PhysicsDefinition& physics) -> bool {
        if (physics.totalMass <= 0) return false;
        return true;
    };
    
    validation["validateLOD"] = [](const LODDefinition& lod) -> bool {
        if (lod.meshDecimate < 0.0f || lod.meshDecimate > 1.0f) return false;
        if (lod.materialDetail < 0.0f || lod.materialDetail > 1.0f) return false;
        if (lod.maxBoneInfluences <= 0) return false;
        return true;
    };
    
    validation["validateMagitechMaterials"] = [](const MagitechMaterials& materials) -> bool {
        // Validate rune glow
        if (materials.runeGlow.pulseRate < 0) return false;
        if (materials.runeGlow.patternScale <= 0) return false;
        if (materials.runeGlow.glowIntensity < 0) return false;
        
        // Validate engine heat
        if (materials.engineHeat.distortionIntensity < 0 || materials.engineHeat.distortionIntensity > 1) return false;
        if (materials.engineHeat.flickerRate < 0) return false;
        if (materials.engineHeat.maxTemperature <= 0) return false;
        
        // Validate energy trail
        if (materials.energyTrail.trailLength <= 0) return false;
        if (materials.energyTrail.trailWidth <= 0) return false;
        if (materials.energyTrail.fadeRate < 0 || materials.energyTrail.fadeRate > 1) return false;
        
        return true;
    };
}

} // namespace MiniJetGen 
