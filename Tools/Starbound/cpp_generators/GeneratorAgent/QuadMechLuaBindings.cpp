#include "QuadMechLuaBindings.hpp"
#include "QuadMechFactory.hpp"
#include "core/Log.hpp"
#include <memory>
#include <mutex>
#include <chrono>

namespace MagiTech {
namespace QuadMech {

static std::unique_ptr<QuadMechLoader> g_quadMechLoader;
static std::unique_ptr<QuadMechEditor> g_quadMechEditor;

namespace {

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}

std::shared_ptr<QuadMechFactory>& factorySlot() {
    static std::shared_ptr<QuadMechFactory> f;
    return f;
}

// Standard quadruped mounting points (ids match ModuleType names and the
// bone names used by example_phoenix_quad.quadmechdef).
struct ModuleSlot {
    const char* id;
    ModuleType type;
    const char* bone;
};

constexpr ModuleSlot kLegSlots[] = {
    {"leg_front_left", ModuleType::LEG_FRONT_LEFT, "hip_FL"},
    {"leg_front_right", ModuleType::LEG_FRONT_RIGHT, "hip_FR"},
    {"leg_back_left", ModuleType::LEG_BACK_LEFT, "hip_BL"},
    {"leg_back_right", ModuleType::LEG_BACK_RIGHT, "hip_BR"},
};

constexpr ModuleSlot kWeaponSlots[] = {
    {"weapon_left", ModuleType::WEAPON_LEFT, "shoulder_L"},
    {"weapon_right", ModuleType::WEAPON_RIGHT, "shoulder_R"},
};

// Same rules as the package pipeline (chassis + legs, mesh paths, bones, mass, animation paths).
bool validateQuadMechDefinition(const QuadMechDefinition& def) {
    return QuadMechGen::DefinitionParser::validateDefinition(def);
}

} // namespace

void QuadMechLuaBindings::setFactory(std::shared_ptr<QuadMechFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<QuadMechFactory> QuadMechLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<QuadMechFactory>();
        slot->initialize(100, 4);
    }
    return slot;
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
    lua.new_usertype<ModuleDefinition>("QuadMechModuleDefinition",
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
    lua.new_usertype<CockpitDefinition>("QuadMechCockpitDefinition",
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
    
    lua.new_usertype<MagitechMaterials>("QuadMechMagitechMaterials",
        sol::constructors<MagitechMaterials()>(),
        "energyRunes", &MagitechMaterials::energyRunes,
        "energyCore", &MagitechMaterials::energyCore,
        "canopy", &MagitechMaterials::canopy,
        "hashKey", &MagitechMaterials::hashKey
    );
    
    // Bind animation definition
    lua.new_usertype<AnimationDefinition>("QuadMechAnimationDefinition",
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
    
    lua.new_usertype<PhysicsDefinition>("QuadMechPhysicsDefinition",
        sol::constructors<PhysicsDefinition()>(),
        "totalMass", &PhysicsDefinition::totalMass,
        // Maps are exposed as plain Lua tables (copied on get, replaced on set);
        // this sol2 build cannot bind std::unordered_map members as containers.
        "moduleMass", sol::property(
            [](const PhysicsDefinition& p, sol::this_state ts) {
                sol::state_view view(ts);
                sol::table t = view.create_table();
                for (const auto& [id, mass] : p.moduleMass) t[id] = mass;
                return t;
            },
            [](PhysicsDefinition& p, sol::table t) {
                p.moduleMass.clear();
                for (const auto& [key, value] : t) p.moduleMass[key.as<std::string>()] = value.as<float>();
            }),
        "jointLimits", sol::property(
            [](const PhysicsDefinition& p, sol::this_state ts) {
                sol::state_view view(ts);
                sol::table t = view.create_table();
                for (const auto& [joint, limit] : p.jointLimits) t[joint] = limit;
                return t;
            },
            [](PhysicsDefinition& p, sol::table t) {
                p.jointLimits.clear();
                for (const auto& [key, value] : t) p.jointLimits[key.as<std::string>()] = value.as<JointLimit>();
            }),
        "enableCCD", &PhysicsDefinition::enableCCD,
        "collisionMargin", &PhysicsDefinition::collisionMargin,
        "hashKey", &PhysicsDefinition::hashKey
    );
    
    // Bind LOD definition
    lua.new_usertype<LODDefinition>("QuadMechLODDefinition",
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
        "id", sol::readonly(&QuadMechInstance::id),
        "transform", &QuadMechInstance::transform,
        "currentAnimationTime", &QuadMechInstance::currentAnimationTime,
        "currentAnimation", &QuadMechInstance::currentAnimation,
        "currentLOD", &QuadMechInstance::currentLOD,
        "energyLevel", &QuadMechInstance::energyLevel,
        "runeGlowIntensity", &QuadMechInstance::runeGlowIntensity,
        "cockpitOpen", &QuadMechInstance::cockpitOpen,
        "pilotInside", &QuadMechInstance::pilotInside,
        "physicsBodies", &QuadMechInstance::physicsBodies,
        "accumulatedForce", &QuadMechInstance::accumulatedForce,
        "accumulatedTorque", &QuadMechInstance::accumulatedTorque,
        "hashKey", &QuadMechInstance::hashKey
    );
    
    // Initialize the loader/editor; the shared factory is created lazily by factory()
    // unless the host injected one with setFactory().
    g_quadMechLoader = std::make_unique<QuadMechLoader>();
    g_quadMechEditor = std::make_unique<QuadMechEditor>();
    
    // Bind factory functions
    lua.set_function("load_quad_mech_sync", [](const std::string& mechName, LODQuality quality) {
        return factory()->loadSync(mechName, quality);
    });
    
    lua.set_function("load_quad_mech_async", [](const std::string& mechName, LODQuality quality) {
        return factory()->loadAsync(mechName, quality);
    });
    
    lua.set_function("generate_quad_mech_package", [](const std::string& definitionPath, const std::string& outputPath) {
        return factory()->generatePackageSync(definitionPath, outputPath);
    });
    
    lua.set_function("generate_quad_mech_package_async", [](const std::string& definitionPath, const std::string& outputPath) {
        return factory()->generatePackageAsync(definitionPath, outputPath);
    });
    
    // Bind loader functions
    lua.set_function("create_quad_mech_instance", [](const std::string& mechName, LODQuality quality) {
        return g_quadMechLoader->createInstance(mechName, quality);
    });
    
    lua.set_function("destroy_quad_mech_instance", [](const std::string& instanceId) {
        g_quadMechLoader->destroyInstance(instanceId);
    });
    
    lua.set_function("get_quad_mech_instance", [](const std::string& instanceId) {
        return g_quadMechLoader->getInstance(instanceId);
    });
    
    lua.set_function("update_quad_mech_instance", [](const std::string& instanceId, const glm::mat4& transform) {
        g_quadMechLoader->updateInstance(instanceId, transform);
    });
    
    lua.set_function("set_quad_mech_animation", [](const std::string& instanceId, const std::string& animationName) {
        g_quadMechLoader->setInstanceAnimation(instanceId, animationName);
    });
    
    lua.set_function("set_quad_mech_lod", [](const std::string& instanceId, LODQuality quality) {
        g_quadMechLoader->setInstanceLOD(instanceId, quality);
    });
    
    // Bind Magitech runtime functions
    lua.set_function("set_quad_mech_energy_level", [](const std::string& instanceId, float energyLevel) {
        g_quadMechLoader->setEnergyLevel(instanceId, energyLevel);
    });
    
    lua.set_function("set_quad_mech_rune_glow", [](const std::string& instanceId, float intensity) {
        g_quadMechLoader->setRuneGlowIntensity(instanceId, intensity);
    });
    
    lua.set_function("set_quad_mech_cockpit_state", [](const std::string& instanceId, bool open, bool pilotInside) {
        g_quadMechLoader->setCockpitState(instanceId, open, pilotInside);
    });
    
    // Bind physics functions
    lua.set_function("apply_force_to_quad_mech", [](const std::string& instanceId, const glm::vec3& force, const glm::vec3& point) {
        g_quadMechLoader->applyForce(instanceId, force, point);
    });
    
    lua.set_function("set_quad_mech_physics_transform", [](const std::string& instanceId, const glm::mat4& transform) {
        g_quadMechLoader->setPhysicsTransform(instanceId, transform);
    });
    
    // Bind editor functions
    lua.set_function("load_quad_mech_for_editing", [](const std::string& mechName) {
        g_quadMechEditor->loadMechForEditing(mechName);
    });
    
    lua.set_function("save_current_quad_mech", [](const std::string& outputPath) {
        g_quadMechEditor->saveCurrentMech(outputPath);
    });
    
    lua.set_function("create_new_quad_mech", [](const std::string& name) {
        g_quadMechEditor->createNewMech(name);
    });
    
    // Bind module editing
    lua.set_function("add_quad_mech_module", [](const ModuleDefinition& module) {
        g_quadMechEditor->addModule(module);
    });
    
    lua.set_function("remove_quad_mech_module", [](const std::string& moduleId) {
        g_quadMechEditor->removeModule(moduleId);
    });
    
    lua.set_function("update_quad_mech_module", [](const std::string& moduleId, const ModuleDefinition& newDef) {
        g_quadMechEditor->updateModule(moduleId, newDef);
    });
    
    // Bind material editing
    lua.set_function("update_quad_mech_energy_runes", [](const EnergyRunes& runes) {
        g_quadMechEditor->updateEnergyRunes(runes);
    });
    
    lua.set_function("update_quad_mech_energy_core", [](const EnergyCore& core) {
        g_quadMechEditor->updateEnergyCore(core);
    });
    
    lua.set_function("update_quad_mech_canopy_material", [](const CanopyMaterial& canopy) {
        g_quadMechEditor->updateCanopyMaterial(canopy);
    });
    
    // Bind animation editing
    lua.set_function("add_quad_mech_animation", [](const AnimationDefinition& anim) {
        g_quadMechEditor->addAnimation(anim);
    });
    
    lua.set_function("remove_quad_mech_animation", [](const std::string& animId) {
        g_quadMechEditor->removeAnimation(animId);
    });
    
    lua.set_function("update_quad_mech_animation", [](const std::string& animId, const AnimationDefinition& newDef) {
        g_quadMechEditor->updateAnimation(animId, newDef);
    });
    
    // Bind physics editing
    lua.set_function("update_quad_mech_physics", [](const PhysicsDefinition& physics) {
        g_quadMechEditor->updatePhysicsDefinition(physics);
    });
    
    lua.set_function("update_quad_mech_joint_limits", [](const std::string& jointName, const JointLimit& limits) {
        g_quadMechEditor->updateJointLimits(jointName, limits);
    });
    
    // Bind LOD editing
    lua.set_function("add_quad_mech_lod", [](const LODDefinition& lod) {
        g_quadMechEditor->addLODDefinition(lod);
    });
    
    lua.set_function("update_quad_mech_lod", [](LODQuality quality, const LODDefinition& lod) {
        g_quadMechEditor->updateLODDefinition(quality, lod);
    });
    
    // Bind preview functions
    lua.set_function("set_quad_mech_preview_time", [](float time) {
        g_quadMechEditor->setPreviewTime(time);
    });
    
    lua.set_function("set_quad_mech_preview_lod", [](LODQuality quality) {
        g_quadMechEditor->setPreviewLOD(quality);
    });
    
    lua.set_function("set_quad_mech_preview_animation", [](const std::string& animName) {
        g_quadMechEditor->setPreviewAnimation(animName);
    });
    
    lua.set_function("get_quad_mech_preview_instance", []() {
        return g_quadMechEditor->getPreviewInstance();
    });
    
    // Bind utility functions
    lua.set_function("get_available_quad_mechs", []() {
        return factory()->getAvailableMechs();
    });
    
    lua.set_function("quad_mech_exists", [](const std::string& mechName) {
        return factory()->mechExists(mechName);
    });
    
    lua.set_function("validate_quad_mech_definition", [](const QuadMechDefinition& def) {
        return factory()->validateMechDefinition(def);
    });
    
    lua.set_function("get_quad_mech_performance_metrics", []() {
        return factory()->getPerformanceMetrics();
    });
    
    lua.set_function("reset_quad_mech_performance_metrics", []() {
        factory()->resetPerformanceMetrics();
    });
    
    // Bind cache management
    lua.set_function("clear_quad_mech_cache", []() {
        factory()->clearCache();
    });
    
    lua.set_function("get_quad_mech_cache_size", []() {
        return factory()->getCacheSize();
    });
    
    lua.set_function("get_quad_mech_cache_hit_rate", []() {
        return factory()->getCacheHitRate();
    });
    
    // Bind hot-reload functions
    lua.set_function("watch_quad_mech_for_changes", [](const std::string& mechName) {
        factory()->watchForChanges(mechName);
    });
    
    lua.set_function("unwatch_quad_mech_changes", [](const std::string& mechName) {
        factory()->unwatchForChanges(mechName);
    });
    
    lua.set_function("check_quad_mech_for_updates", [](const std::string& mechName) {
        return factory()->checkForUpdates(mechName);
    });
    
    lua.set_function("reload_quad_mech", [](const std::string& mechName) {
        factory()->reloadMech(mechName);
    });
    
    // Bind editor state functions
    lua.set_function("get_quad_mech_editor_state", []() {
        return g_quadMechEditor->getEditorState();
    });
    
    lua.set_function("set_quad_mech_editor_state", [](const EditorState& state) {
        g_quadMechEditor->setEditorState(state);
    });
    
    lua.set_function("is_quad_mech_editor_dirty", []() {
        return g_quadMechEditor->isDirty();
    });
    
    lua.set_function("mark_quad_mech_editor_dirty", [](bool dirty) {
        g_quadMechEditor->markDirty(dirty);
    });
    
    // Bind instance management
    lua.set_function("get_active_quad_mech_count", []() {
        return g_quadMechLoader->getActiveInstanceCount();
    });
    
    lua.set_function("get_active_quad_mech_ids", []() {
        return g_quadMechLoader->getActiveInstanceIds();
    });
    
    lua.set_function("clear_all_quad_mech_instances", []() {
        g_quadMechLoader->clearAllInstances();
    });
    
    // Helper functions for creating common configurations
    lua.set_function("create_scout_quad_mech", []() {
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
        for (const auto& legSlot : kLegSlots) {
            ModuleDefinition leg;
            leg.id = legSlot.id;
            leg.type = legSlot.type;
            leg.meshPath = "modules/scout_leg.fbx";
            leg.attachBone = legSlot.bone;
            leg.mass = 75.0f;
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
    
    lua.set_function("create_assault_quad_mech", []() {
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
        for (const auto& legSlot : kLegSlots) {
            ModuleDefinition leg;
            leg.id = legSlot.id;
            leg.type = legSlot.type;
            leg.meshPath = "modules/assault_leg.fbx";
            leg.attachBone = legSlot.bone;
            leg.mass = 200.0f;
            def.modules.push_back(leg);
        }

        // Add weapons
        for (const auto& weaponSlot : kWeaponSlots) {
            ModuleDefinition weapon;
            weapon.id = weaponSlot.id;
            weapon.type = weaponSlot.type;
            weapon.meshPath = "modules/assault_weapon.fbx";
            weapon.attachBone = weaponSlot.bone;
            weapon.mass = 100.0f;
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
    // Async loads hand their std::future straight to Lua (load_quad_mech_async),
    // so polling here only drives hot-reload of watched definition files.
    auto quadFactory = factory();
    for (const auto& mechName : quadFactory->getAvailableMechs()) {
        if (!quadFactory->checkForUpdates(mechName)) continue;

        Log::info("QuadMech", "QuadMech file changed, triggering reload: {}", mechName);
        quadFactory->reloadMech(mechName);

        // Call the Lua callback if one is defined
        sol::optional<sol::protected_function> callback = lua["on_quad_mech_reloaded"];
        if (callback) {
            sol::protected_function_result result = (*callback)(mechName);
            if (!result.valid()) {
                sol::error err = result;
                Log::error("QuadMech", "on_quad_mech_reloaded failed: {}", err.what());
            }
        }
    }

    if (g_quadMechEditor) {
        g_quadMechEditor->checkForChanges();
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
    
    // Drop our reference; the factory shuts down when its last owner releases it
    // (an injected host factory keeps running).
    setFactory(nullptr);
    
    Log::info("QuadMechLuaBindings shutdown complete");
}

} // namespace QuadMech
} // namespace MagiTech
