#include "QuadMechLuaBindings.hpp"
#include "QuadMechFactory.hpp"
#include "core/Log.hpp"
#include <memory>
#include <chrono>

namespace MagiTech {
namespace QuadMech {

static std::unique_ptr<QuadMechFactory> g_quadMechFactory;
static std::unique_ptr<QuadMechLoader> g_quadMechLoader;
static std::unique_ptr<QuadMechEditor> g_quadMechEditor;

// Validation functions
bool validateQuadMechDefinition(const QuadMechDefinition& def) {
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
    
    return true;
}

void QuadMechLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum<LODQuality>("LODQuality", {
        {"HIGH", LODQuality::HIGH},
        {"MEDIUM", LODQuality::MEDIUM},
        {"LOW", LODQuality::LOW},
        {"ULTRA_LOW", LODQuality::ULTRA_LOW}
    });
    
    lua.new_enum<ModuleType>("ModuleType", {
        {"CHASSIS", ModuleType::CHASSIS},
        {"LEG_FRONT_LEFT", ModuleType::LEG_FRONT_LEFT},
        {"LEG_FRONT_RIGHT", ModuleType::LEG_FRONT_RIGHT},
        {"LEG_BACK_LEFT", ModuleType::LEG_BACK_LEFT},
        {"LEG_BACK_RIGHT", ModuleType::LEG_BACK_RIGHT},
        {"HEAD", ModuleType::HEAD},
        {"COCKPIT", ModuleType::COCKPIT},
        {"WEAPON_LEFT", ModuleType::WEAPON_LEFT},
        {"WEAPON_RIGHT", ModuleType::WEAPON_RIGHT},
        {"ENERGY_CORE", ModuleType::ENERGY_CORE}
    });
    
    lua.new_enum<AnimationType>("AnimationType", {
        {"WALK", AnimationType::WALK},
        {"TROT", AnimationType::TROT},
        {"GALLOP", AnimationType::GALLOP},
        {"COCKPIT_OPEN", AnimationType::COCKPIT_OPEN},
        {"COCKPIT_CLOSE", AnimationType::COCKPIT_CLOSE},
        {"PILOT_ENTRY", AnimationType::PILOT_ENTRY},
        {"PILOT_EXIT", AnimationType::PILOT_EXIT},
        {"IDLE", AnimationType::IDLE},
        {"ATTACK", AnimationType::ATTACK},
        {"DEFEND", AnimationType::DEFEND}
    });
    
    // Bind basic types
    lua.new_usertype<glm::vec2>("Vec2",
        sol::constructors<glm::vec2(), glm::vec2(float, float)>(),
        "x", &glm::vec2::x,
        "y", &glm::vec2::y
    );
    
    lua.new_usertype<glm::vec3>("Vec3",
        sol::constructors<glm::vec3(), glm::vec3(float, float, float)>(),
        "x", &glm::vec3::x,
        "y", &glm::vec3::y,
        "z", &glm::vec3::z
    );
    
    lua.new_usertype<glm::vec4>("Vec4",
        sol::constructors<glm::vec4(), glm::vec4(float, float, float, float)>(),
        "x", &glm::vec4::x,
        "y", &glm::vec4::y,
        "z", &glm::vec4::z,
        "w", &glm::vec4::w
    );
    
    // Bind module definition
    lua.new_usertype<ModuleDefinition>("ModuleDefinition",
        sol::constructors<ModuleDefinition()>(),
        "id", &ModuleDefinition::id,
        "type", &ModuleDefinition::type,
        "meshPath", &ModuleDefinition::meshPath,
        "attachBone", &ModuleDefinition::attachBone,
        "offset", &ModuleDefinition::offset,
        "scale", &ModuleDefinition::scale,
        "rotation", &ModuleDefinition::rotation,
        "mass", &ModuleDefinition::mass,
        "inertia", &ModuleDefinition::inertia,
        "materialOverride", &ModuleDefinition::materialOverride,
        "hashKey", &ModuleDefinition::hashKey
    );
    
    // Bind cockpit definition
    lua.new_usertype<CockpitDefinition>("CockpitDefinition",
        sol::constructors<CockpitDefinition()>(),
        "seatPosition", &CockpitDefinition::seatPosition,
        "canopyTint", &CockpitDefinition::canopyTint,
        "canopyMaterial", &CockpitDefinition::canopyMaterial,
        "hudAnchorPoints", &CockpitDefinition::hudAnchorPoints,
        "transparency", &CockpitDefinition::transparency,
        "enableHologram", &CockpitDefinition::enableHologram,
        "hashKey", &CockpitDefinition::hashKey
    );
    
    // Bind Magitech materials
    lua.new_usertype<EnergyRunes>("EnergyRunes",
        sol::constructors<EnergyRunes()>(),
        "emissiveColor", &EnergyRunes::emissiveColor,
        "glowIntensity", &EnergyRunes::glowIntensity,
        "animationRate", &EnergyRunes::animationRate,
        "pulseFrequency", &EnergyRunes::pulseFrequency,
        "enableFlicker", &EnergyRunes::enableFlicker,
        "flickerIntensity", &EnergyRunes::flickerIntensity,
        "hashKey", &EnergyRunes::hashKey
    );
    
    lua.new_usertype<EnergyCore>("EnergyCore",
        sol::constructors<EnergyCore()>(),
        "coreColor", &EnergyCore::coreColor,
        "energyLevel", &EnergyCore::energyLevel,
        "pulseRate", &EnergyCore::pulseRate,
        "enableArcs", &EnergyCore::enableArcs,
        "arcIntensity", &EnergyCore::arcIntensity,
        "arcCount", &EnergyCore::arcCount,
        "hashKey", &EnergyCore::hashKey
    );
    
    lua.new_usertype<CanopyMaterial>("CanopyMaterial",
        sol::constructors<CanopyMaterial()>(),
        "tint", &CanopyMaterial::tint,
        "transparency", &CanopyMaterial::transparency,
        "reflectivity", &CanopyMaterial::reflectivity,
        "enableScratches", &CanopyMaterial::enableScratches,
        "scratchDensity", &CanopyMaterial::scratchDensity,
        "hashKey", &CanopyMaterial::hashKey
    );
    
    lua.new_usertype<MagitechMaterials>("MagitechMaterials",
        sol::constructors<MagitechMaterials()>(),
        "energyRunes", &MagitechMaterials::energyRunes,
        "energyCore", &MagitechMaterials::energyCore,
        "canopy", &MagitechMaterials::canopy,
        "hashKey", &MagitechMaterials::hashKey
    );
    
    // Bind animation definition
    lua.new_usertype<AnimationDefinition>("AnimationDefinition",
        sol::constructors<AnimationDefinition()>(),
        "id", &AnimationDefinition::id,
        "type", &AnimationDefinition::type,
        "path", &AnimationDefinition::path,
        "speed", &AnimationDefinition::speed,
        "loop", &AnimationDefinition::loop,
        "blendTime", &AnimationDefinition::blendTime,
        "gaitPhase", &AnimationDefinition::gaitPhase,
        "strideLength", &AnimationDefinition::strideLength,
        "legLift", &AnimationDefinition::legLift,
        "hashKey", &AnimationDefinition::hashKey
    );
    
    // Bind physics types
    lua.new_usertype<JointLimit>("JointLimit",
        sol::constructors<JointLimit()>(),
        "swing", &JointLimit::swing,
        "twist", &JointLimit::twist,
        "damping", &JointLimit::damping,
        "friction", &JointLimit::friction,
        "hashKey", &JointLimit::hashKey
    );
    
    lua.new_usertype<PhysicsDefinition>("PhysicsDefinition",
        sol::constructors<PhysicsDefinition()>(),
        "totalMass", &PhysicsDefinition::totalMass,
        "moduleMass", &PhysicsDefinition::moduleMass,
        "jointLimits", &PhysicsDefinition::jointLimits,
        "enableCCD", &PhysicsDefinition::enableCCD,
        "collisionMargin", &PhysicsDefinition::collisionMargin,
        "hashKey", &PhysicsDefinition::hashKey
    );
    
    // Bind LOD definition
    lua.new_usertype<LODDefinition>("LODDefinition",
        sol::constructors<LODDefinition()>(),
        "quality", &LODDefinition::quality,
        "meshDecimate", &LODDefinition::meshDecimate,
        "materialDetail", &LODDefinition::materialDetail,
        "maxBones", &LODDefinition::maxBones,
        "enableMorphTargets", &LODDefinition::enableMorphTargets,
        "hashKey", &LODDefinition::hashKey
    );
    
    // Bind main definition
    lua.new_usertype<QuadMechDefinition>("QuadMechDefinition",
        sol::constructors<QuadMechDefinition()>(),
        "name", &QuadMechDefinition::name,
        "version", &QuadMechDefinition::version,
        "modules", &QuadMechDefinition::modules,
        "cockpit", &QuadMechDefinition::cockpit,
        "magitechMaterials", &QuadMechDefinition::magitechMaterials,
        "animations", &QuadMechDefinition::animations,
        "physics", &QuadMechDefinition::physics,
        "lods", &QuadMechDefinition::lods,
        "author", &QuadMechDefinition::author,
        "description", &QuadMechDefinition::description,
        "tags", &QuadMechDefinition::tags,
        "hashKey", &QuadMechDefinition::hashKey,
        "validate", [](const QuadMechDefinition& def) { return validateQuadMechDefinition(def); }
    );
    
    // Bind runtime types
    lua.new_usertype<QuadMechInstance>("QuadMechInstance",
        sol::no_constructor,
        "transform", &QuadMechInstance::transform,
        "currentAnimationTime", &QuadMechInstance::currentAnimationTime,
        "currentAnimation", &QuadMechInstance::currentAnimation,
        "currentLOD", &QuadMechInstance::currentLOD,
        "energyLevel", &QuadMechInstance::energyLevel,
        "runeGlowIntensity", &QuadMechInstance::runeGlowIntensity,
        "cockpitOpen", &QuadMechInstance::cockpitOpen,
        "pilotInside", &QuadMechInstance::pilotInside,
        "physicsBodies", &QuadMechInstance::physicsBodies,
        "hashKey", &QuadMechInstance::hashKey
    );
    
    // Initialize factories
    g_quadMechFactory = std::make_unique<QuadMechFactory>();
    g_quadMechFactory->initialize(100, 4);
    
    g_quadMechLoader = std::make_unique<QuadMechLoader>();
    g_quadMechEditor = std::make_unique<QuadMechEditor>();
    
    // Bind factory functions
    lua.set_function("load_quad_mech_sync", [&](const std::string& mechName, LODQuality quality) {
        return g_quadMechFactory->loadSync(mechName, quality);
    });
    
    lua.set_function("load_quad_mech_async", [&](const std::string& mechName, LODQuality quality) {
        return g_quadMechFactory->loadAsync(mechName, quality);
    });
    
    lua.set_function("generate_quad_mech_package", [&](const std::string& definitionPath, const std::string& outputPath) {
        return g_quadMechFactory->generatePackageSync(definitionPath, outputPath);
    });
    
    lua.set_function("generate_quad_mech_package_async", [&](const std::string& definitionPath, const std::string& outputPath) {
        return g_quadMechFactory->generatePackageAsync(definitionPath, outputPath);
    });
    
    // Bind loader functions
    lua.set_function("create_quad_mech_instance", [&](const std::string& mechName, LODQuality quality) {
        return g_quadMechLoader->createInstance(mechName, quality);
    });
    
    lua.set_function("destroy_quad_mech_instance", [&](const std::string& instanceId) {
        g_quadMechLoader->destroyInstance(instanceId);
    });
    
    lua.set_function("get_quad_mech_instance", [&](const std::string& instanceId) {
        return g_quadMechLoader->getInstance(instanceId);
    });
    
    lua.set_function("update_quad_mech_instance", [&](const std::string& instanceId, const glm::mat4& transform) {
        g_quadMechLoader->updateInstance(instanceId, transform);
    });
    
    lua.set_function("set_quad_mech_animation", [&](const std::string& instanceId, const std::string& animationName) {
        g_quadMechLoader->setInstanceAnimation(instanceId, animationName);
    });
    
    lua.set_function("set_quad_mech_lod", [&](const std::string& instanceId, LODQuality quality) {
        g_quadMechLoader->setInstanceLOD(instanceId, quality);
    });
    
    // Bind Magitech runtime functions
    lua.set_function("set_quad_mech_energy_level", [&](const std::string& instanceId, float energyLevel) {
        g_quadMechLoader->setEnergyLevel(instanceId, energyLevel);
    });
    
    lua.set_function("set_quad_mech_rune_glow", [&](const std::string& instanceId, float intensity) {
        g_quadMechLoader->setRuneGlowIntensity(instanceId, intensity);
    });
    
    lua.set_function("set_quad_mech_cockpit_state", [&](const std::string& instanceId, bool open, bool pilotInside) {
        g_quadMechLoader->setCockpitState(instanceId, open, pilotInside);
    });
    
    // Bind physics functions
    lua.set_function("apply_force_to_quad_mech", [&](const std::string& instanceId, const glm::vec3& force, const glm::vec3& point) {
        g_quadMechLoader->applyForce(instanceId, force, point);
    });
    
    lua.set_function("set_quad_mech_physics_transform", [&](const std::string& instanceId, const glm::mat4& transform) {
        g_quadMechLoader->setPhysicsTransform(instanceId, transform);
    });
    
    // Bind editor functions
    lua.set_function("load_quad_mech_for_editing", [&](const std::string& mechName) {
        g_quadMechEditor->loadMechForEditing(mechName);
    });
    
    lua.set_function("save_current_quad_mech", [&](const std::string& outputPath) {
        g_quadMechEditor->saveCurrentMech(outputPath);
    });
    
    lua.set_function("create_new_quad_mech", [&](const std::string& name) {
        g_quadMechEditor->createNewMech(name);
    });
    
    // Bind module editing
    lua.set_function("add_quad_mech_module", [&](const ModuleDefinition& module) {
        g_quadMechEditor->addModule(module);
    });
    
    lua.set_function("remove_quad_mech_module", [&](const std::string& moduleId) {
        g_quadMechEditor->removeModule(moduleId);
    });
    
    lua.set_function("update_quad_mech_module", [&](const std::string& moduleId, const ModuleDefinition& newDef) {
        g_quadMechEditor->updateModule(moduleId, newDef);
    });
    
    // Bind material editing
    lua.set_function("update_quad_mech_energy_runes", [&](const EnergyRunes& runes) {
        g_quadMechEditor->updateEnergyRunes(runes);
    });
    
    lua.set_function("update_quad_mech_energy_core", [&](const EnergyCore& core) {
        g_quadMechEditor->updateEnergyCore(core);
    });
    
    lua.set_function("update_quad_mech_canopy_material", [&](const CanopyMaterial& canopy) {
        g_quadMechEditor->updateCanopyMaterial(canopy);
    });
    
    // Bind animation editing
    lua.set_function("add_quad_mech_animation", [&](const AnimationDefinition& anim) {
        g_quadMechEditor->addAnimation(anim);
    });
    
    lua.set_function("remove_quad_mech_animation", [&](const std::string& animId) {
        g_quadMechEditor->removeAnimation(animId);
    });
    
    lua.set_function("update_quad_mech_animation", [&](const std::string& animId, const AnimationDefinition& newDef) {
        g_quadMechEditor->updateAnimation(animId, newDef);
    });
    
    // Bind physics editing
    lua.set_function("update_quad_mech_physics", [&](const PhysicsDefinition& physics) {
        g_quadMechEditor->updatePhysicsDefinition(physics);
    });
    
    lua.set_function("update_quad_mech_joint_limits", [&](const std::string& jointName, const JointLimit& limits) {
        g_quadMechEditor->updateJointLimits(jointName, limits);
    });
    
    // Bind LOD editing
    lua.set_function("add_quad_mech_lod", [&](const LODDefinition& lod) {
        g_quadMechEditor->addLODDefinition(lod);
    });
    
    lua.set_function("update_quad_mech_lod", [&](LODQuality quality, const LODDefinition& lod) {
        g_quadMechEditor->updateLODDefinition(quality, lod);
    });
    
    // Bind preview functions
    lua.set_function("set_quad_mech_preview_time", [&](float time) {
        g_quadMechEditor->setPreviewTime(time);
    });
    
    lua.set_function("set_quad_mech_preview_lod", [&](LODQuality quality) {
        g_quadMechEditor->setPreviewLOD(quality);
    });
    
    lua.set_function("set_quad_mech_preview_animation", [&](const std::string& animName) {
        g_quadMechEditor->setPreviewAnimation(animName);
    });
    
    lua.set_function("get_quad_mech_preview_instance", [&]() {
        return g_quadMechEditor->getPreviewInstance();
    });
    
    // Bind utility functions
    lua.set_function("get_available_quad_mechs", [&]() {
        return g_quadMechFactory->getAvailableMechs();
    });
    
    lua.set_function("quad_mech_exists", [&](const std::string& mechName) {
        return g_quadMechFactory->mechExists(mechName);
    });
    
    lua.set_function("validate_quad_mech_definition", [&](const QuadMechDefinition& def) {
        return g_quadMechFactory->validateMechDefinition(def);
    });
    
    lua.set_function("get_quad_mech_performance_metrics", [&]() {
        return g_quadMechFactory->getPerformanceMetrics();
    });
    
    lua.set_function("reset_quad_mech_performance_metrics", [&]() {
        g_quadMechFactory->resetPerformanceMetrics();
    });
    
    // Bind cache management
    lua.set_function("clear_quad_mech_cache", [&]() {
        g_quadMechFactory->clearCache();
    });
    
    lua.set_function("get_quad_mech_cache_size", [&]() {
        return g_quadMechFactory->getCacheSize();
    });
    
    lua.set_function("get_quad_mech_cache_hit_rate", [&]() {
        return g_quadMechFactory->getCacheHitRate();
    });
    
    // Bind hot-reload functions
    lua.set_function("watch_quad_mech_for_changes", [&](const std::string& mechName) {
        g_quadMechFactory->watchForChanges(mechName);
    });
    
    lua.set_function("unwatch_quad_mech_changes", [&](const std::string& mechName) {
        g_quadMechFactory->unwatchForChanges(mechName);
    });
    
    lua.set_function("check_quad_mech_for_updates", [&](const std::string& mechName) {
        return g_quadMechFactory->checkForUpdates(mechName);
    });
    
    lua.set_function("reload_quad_mech", [&](const std::string& mechName) {
        g_quadMechFactory->reloadMech(mechName);
    });
    
    // Bind editor state functions
    lua.set_function("get_quad_mech_editor_state", [&]() {
        return g_quadMechEditor->getEditorState();
    });
    
    lua.set_function("set_quad_mech_editor_state", [&](const EditorState& state) {
        g_quadMechEditor->setEditorState(state);
    });
    
    lua.set_function("is_quad_mech_editor_dirty", [&]() {
        return g_quadMechEditor->isDirty();
    });
    
    lua.set_function("mark_quad_mech_editor_dirty", [&](bool dirty) {
        g_quadMechEditor->markDirty(dirty);
    });
    
    // Bind instance management
    lua.set_function("get_active_quad_mech_count", [&]() {
        return g_quadMechLoader->getActiveInstanceCount();
    });
    
    lua.set_function("get_active_quad_mech_ids", [&]() {
        return g_quadMechLoader->getActiveInstanceIds();
    });
    
    lua.set_function("clear_all_quad_mech_instances", [&]() {
        g_quadMechLoader->clearAllInstances();
    });
    
    // Helper functions for creating common configurations
    lua.set_function("create_scout_quad_mech", [&]() {
        // Create a lightweight scout mech configuration
        QuadMechDefinition def;
        def.name = "scout_quad";
        def.version = "1.0.0";
        def.author = "MagiTech Engineering";
        def.description = "Lightweight scout quadraped mech";
        
        // Add basic modules
        ModuleDefinition chassis;
        chassis.id = "chassis";
        chassis.type = ModuleType::CHASSIS;
        chassis.meshPath = "modules/scout_body.fbx";
        chassis.attachBone = "root";
        chassis.mass = 400.0;
        def.modules.push_back(chassis);
        
        // Add legs
        for (const auto& legName : {"leg_front_left", "leg_front_right", "leg_back_left", "leg_back_right"}) {
            ModuleDefinition leg;
            leg.id = legName;
            leg.type = ModuleType::LEG_FRONT_LEFT; // Simplified for example
            leg.meshPath = "modules/scout_leg.fbx";
            leg.attachBone = "hip_" + std::string(legName.substr(4, 2));
            leg.mass = 75.0;
            def.modules.push_back(leg);
        }
        
        // Add cockpit
        ModuleDefinition cockpit;
        cockpit.id = "cockpit";
        cockpit.type = ModuleType::COCKPIT;
        cockpit.meshPath = "modules/scout_cockpit.fbx";
        cockpit.attachBone = "torso_mid";
        cockpit.mass = 50.0;
        def.modules.push_back(cockpit);
        
        // Setup basic physics
        def.physics.totalMass = 750.0;
        
        // Setup basic animations
        AnimationDefinition walk;
        walk.id = "walk";
        walk.type = AnimationType::WALK;
        walk.path = "animations/scout_walk.fbx";
        walk.speed = 1.2f;
        walk.loop = true;
        def.animations.push_back(walk);
        
        AnimationDefinition idle;
        idle.id = "idle";
        idle.type = AnimationType::IDLE;
        idle.path = "animations/scout_idle.fbx";
        idle.speed = 1.0f;
        idle.loop = true;
        def.animations.push_back(idle);
        
        return def;
    });
    
    lua.set_function("create_assault_quad_mech", [&]() {
        // Create a heavy assault mech configuration
        QuadMechDefinition def;
        def.name = "assault_quad";
        def.version = "1.0.0";
        def.author = "MagiTech Engineering";
        def.description = "Heavy assault quadraped mech";
        
        // Add modules with higher mass
        ModuleDefinition chassis;
        chassis.id = "chassis";
        chassis.type = ModuleType::CHASSIS;
        chassis.meshPath = "modules/assault_body.fbx";
        chassis.attachBone = "root";
        chassis.mass = 1200.0;
        def.modules.push_back(chassis);
        
        // Add heavy legs
        for (const auto& legName : {"leg_front_left", "leg_front_right", "leg_back_left", "leg_back_right"}) {
            ModuleDefinition leg;
            leg.id = legName;
            leg.type = ModuleType::LEG_FRONT_LEFT;
            leg.meshPath = "modules/assault_leg.fbx";
            leg.attachBone = "hip_" + std::string(legName.substr(4, 2));
            leg.mass = 200.0;
            def.modules.push_back(leg);
        }
        
        // Add weapons
        for (const auto& weaponName : {"weapon_left", "weapon_right"}) {
            ModuleDefinition weapon;
            weapon.id = weaponName;
            weapon.type = ModuleType::WEAPON_LEFT;
            weapon.meshPath = "modules/assault_weapon.fbx";
            weapon.attachBone = "shoulder_" + std::string(weaponName.substr(7, 1));
            weapon.mass = 100.0;
            def.modules.push_back(weapon);
        }
        
        // Setup heavy physics
        def.physics.totalMass = 2500.0;
        
        // Setup combat animations
        AnimationDefinition walk;
        walk.id = "walk";
        walk.type = AnimationType::WALK;
        walk.path = "animations/assault_walk.fbx";
        walk.speed = 0.8f;
        walk.loop = true;
        def.animations.push_back(walk);
        
        AnimationDefinition attack;
        attack.id = "attack";
        attack.type = AnimationType::ATTACK;
        attack.path = "animations/assault_attack.fbx";
        attack.speed = 1.5f;
        attack.loop = false;
        def.animations.push_back(attack);
        
        return def;
    });
    
    Log::info("QuadMechLuaBindings initialized with comprehensive interface");
}

void QuadMechLuaBindings::poll_assets(sol::state& lua) {
    // Poll for completed async operations
    // In a real implementation, this would check for completed futures
    // and call appropriate callbacks
    
    // Check for file changes and trigger hot-reload
    auto availableMechs = g_quadMechFactory->getAvailableMechs();
    for (const auto& mechName : availableMechs) {
        if (g_quadMechFactory->checkForUpdates(mechName)) {
            Log::info("QuadMech file changed, triggering reload: {}", mechName);
            g_quadMechFactory->reloadMech(mechName);
            
            // Call Lua callback if available
            if (lua["on_quad_mech_reloaded"]) {
                lua["on_quad_mech_reloaded"](mechName);
            }
        }
    }
}

void QuadMechLuaBindings::shutdown() {
    if (g_quadMechEditor) {
        g_quadMechEditor.reset();
    }
    
    if (g_quadMechLoader) {
        g_quadMechLoader->destroyAllInstances();
        g_quadMechLoader.reset();
    }
    
    if (g_quadMechFactory) {
        g_quadMechFactory->shutdown();
        g_quadMechFactory.reset();
    }
    
    Log::info("QuadMechLuaBindings shutdown complete");
}

} // namespace QuadMech
} // namespace MagiTech 
