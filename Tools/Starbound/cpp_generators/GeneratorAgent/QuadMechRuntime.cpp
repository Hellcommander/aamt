// Runtime instance management (QuadMechLoader) and editor integration
// (QuadMechEditor) for the QuadMech family. Declared in QuadMechFactory.hpp.
#include "QuadMechFactory.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace MagiTech {
namespace QuadMech {

namespace {
constexpr const char* kLoaderCategory = "QuadMechLoader";
constexpr const char* kEditorCategory = "QuadMechEditor";
} // namespace

// ============================================================================
// QUAD MECH LOADER
// ============================================================================

QuadMechLoader::QuadMechLoader()
    : m_factory(std::make_unique<QuadMechFactory>()) {
    m_factory->initialize();
}

QuadMechLoader::~QuadMechLoader() {
    destroyAllInstances();
}

template<typename Fn>
bool QuadMechLoader::withInstance(const std::string& instanceId, Fn&& fn) {
    std::unique_lock<std::shared_mutex> lock(m_instancesMutex);
    auto it = m_activeInstances.find(instanceId);
    if (it == m_activeInstances.end()) {
        Log::warn(kLoaderCategory, "Unknown QuadMech instance: {}", instanceId);
        return false;
    }
    fn(it->second);
    return true;
}

QuadMechInstance QuadMechLoader::createInstance(const std::string& mechName, LODQuality quality) {
    QuadMechInstance instance = m_factory->loadSync(mechName, quality);
    instance.id = mechName + "#" + std::to_string(m_nextInstanceId++);

    std::unique_lock<std::shared_mutex> lock(m_instancesMutex);
    m_activeInstances[instance.id] = instance;
    Log::info(kLoaderCategory, "Created QuadMech instance {}", instance.id);
    return instance;
}

void QuadMechLoader::destroyInstance(const std::string& instanceId) {
    std::unique_lock<std::shared_mutex> lock(m_instancesMutex);
    if (m_activeInstances.erase(instanceId) == 0) {
        Log::warn(kLoaderCategory, "Cannot destroy unknown QuadMech instance: {}", instanceId);
    }
}

QuadMechInstance QuadMechLoader::getInstance(const std::string& instanceId) {
    std::shared_lock<std::shared_mutex> lock(m_instancesMutex);
    auto it = m_activeInstances.find(instanceId);
    if (it == m_activeInstances.end()) {
        throw std::runtime_error("Unknown QuadMech instance: " + instanceId);
    }
    return it->second;
}

std::vector<QuadMechInstance> QuadMechLoader::createBatchInstances(const std::vector<std::string>& mechNames, LODQuality quality) {
    // Load the distinct assets in parallel first; createInstance then hits the cache.
    std::vector<std::future<QuadMechInstance>> warmups;
    std::vector<std::string> seen;
    for (const auto& name : mechNames) {
        if (std::find(seen.begin(), seen.end(), name) != seen.end()) continue;
        seen.push_back(name);
        warmups.push_back(m_factory->loadAsync(name, quality));
    }
    for (auto& f : warmups) f.get(); // rethrows load errors

    std::vector<QuadMechInstance> instances;
    instances.reserve(mechNames.size());
    for (const auto& name : mechNames) {
        instances.push_back(createInstance(name, quality));
    }
    return instances;
}

void QuadMechLoader::destroyAllInstances() {
    std::unique_lock<std::shared_mutex> lock(m_instancesMutex);
    m_activeInstances.clear();
}

void QuadMechLoader::updateInstance(const std::string& instanceId, const glm::mat4& transform) {
    withInstance(instanceId, [&](QuadMechInstance& inst) { inst.transform = transform; });
}

void QuadMechLoader::setInstanceAnimation(const std::string& instanceId, const std::string& animationName) {
    withInstance(instanceId, [&](QuadMechInstance& inst) {
        if (inst.asset && !inst.asset->animations.empty() && !inst.asset->animations.count(animationName)) {
            Log::warn(kLoaderCategory, "Instance {} has no animation '{}'", instanceId, animationName);
            return;
        }
        inst.currentAnimation = animationName;
        inst.currentAnimationTime = 0.0f;
    });
}

void QuadMechLoader::setInstanceLOD(const std::string& instanceId, LODQuality quality) {
    std::string mechName;
    {
        std::shared_lock<std::shared_mutex> lock(m_instancesMutex);
        auto it = m_activeInstances.find(instanceId);
        if (it == m_activeInstances.end()) {
            Log::warn(kLoaderCategory, "Unknown QuadMech instance: {}", instanceId);
            return;
        }
        if (it->second.currentLOD == quality) return;
        mechName = instanceId.substr(0, instanceId.rfind('#'));
    }

    // Swap in the asset generated for the requested LOD, keeping runtime state.
    QuadMechInstance lodInstance = m_factory->loadSync(mechName, quality);
    withInstance(instanceId, [&](QuadMechInstance& inst) {
        inst.asset = lodInstance.asset;
        inst.physicsBodies = lodInstance.physicsBodies;
        inst.currentLOD = quality;
    });
}

void QuadMechLoader::setEnergyLevel(const std::string& instanceId, float energyLevel) {
    withInstance(instanceId, [&](QuadMechInstance& inst) { inst.energyLevel = std::clamp(energyLevel, 0.0f, 1.0f); });
}

void QuadMechLoader::setRuneGlowIntensity(const std::string& instanceId, float intensity) {
    withInstance(instanceId, [&](QuadMechInstance& inst) { inst.runeGlowIntensity = std::max(0.0f, intensity); });
}

void QuadMechLoader::setCockpitState(const std::string& instanceId, bool open, bool pilotInside) {
    withInstance(instanceId, [&](QuadMechInstance& inst) {
        inst.cockpitOpen = open;
        inst.pilotInside = pilotInside;
    });
}

void QuadMechLoader::applyForce(const std::string& instanceId, const glm::vec3& force, const glm::vec3& point) {
    withInstance(instanceId, [&](QuadMechInstance& inst) {
        // Accumulate for the physics step: torque about the instance origin.
        const glm::vec3 origin(inst.transform[3]);
        inst.accumulatedForce += force;
        inst.accumulatedTorque += glm::cross(point - origin, force);
    });
}

void QuadMechLoader::setPhysicsTransform(const std::string& instanceId, const glm::mat4& transform) {
    withInstance(instanceId, [&](QuadMechInstance& inst) {
        inst.transform = transform;
        // A teleport invalidates forces gathered for the previous pose.
        inst.accumulatedForce = glm::vec3(0.0f);
        inst.accumulatedTorque = glm::vec3(0.0f);
    });
}

size_t QuadMechLoader::getActiveInstanceCount() const {
    std::shared_lock<std::shared_mutex> lock(m_instancesMutex);
    return m_activeInstances.size();
}

std::vector<std::string> QuadMechLoader::getActiveInstanceIds() const {
    std::shared_lock<std::shared_mutex> lock(m_instancesMutex);
    std::vector<std::string> ids;
    ids.reserve(m_activeInstances.size());
    for (const auto& [id, inst] : m_activeInstances) ids.push_back(id);
    std::sort(ids.begin(), ids.end());
    return ids;
}

void QuadMechLoader::clearAllInstances() {
    destroyAllInstances();
    Log::info("QuadMech instances cleared");
}

// ============================================================================
// QUAD MECH EDITOR
// ============================================================================

QuadMechEditor::QuadMechEditor()
    : m_factory(std::make_unique<QuadMechFactory>()) {
    m_factory->initialize();
}

QuadMechEditor::~QuadMechEditor() = default;

void QuadMechEditor::loadMechForEditing(const std::string& mechName) {
    const std::string path = QuadMechFactory::definitionPathFor(mechName);
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error(kEditorCategory, "Cannot open QuadMech definition for editing: {}", path);
        return;
    }
    std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());

    try {
        m_editorState.currentDefinition = QuadMechGen::DefinitionParser::parseFromYAML(content);
    } catch (const std::exception& e) {
        Log::error(kEditorCategory, "Failed to parse {}: {}", path, e.what());
        return;
    }
    m_editorState.currentMechName = mechName;
    m_editorState.isDirty = false;
    if (m_hotReload) m_factory->watchForChanges(mechName);
    rebuildPreviewInstance();
    Log::info(kEditorCategory, "Loaded QuadMech for editing: {}", mechName);
}

void QuadMechEditor::saveCurrentMech(const std::string& outputPath) {
    const QuadMechDefinition& def = m_editorState.currentDefinition;
    if (!QuadMechGen::DefinitionParser::validateDefinition(def)) {
        Log::warn(kEditorCategory, "Saving QuadMech '{}' although it does not validate", def.name);
    }

    const std::filesystem::path path(outputPath);
    std::error_code ec;
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream out(path, std::ios::trunc);
    if (!out.is_open()) {
        Log::error(kEditorCategory, "Cannot write QuadMech definition: {}", outputPath);
        return;
    }
    out << QuadMechGen::DefinitionParser::serializeDefinition(def) << "\n";
    if (!out) {
        Log::error(kEditorCategory, "Failed while writing QuadMech definition: {}", outputPath);
        return;
    }
    m_editorState.isDirty = false;
    Log::info(kEditorCategory, "Saved QuadMech '{}' to {}", def.name, outputPath);
}

void QuadMechEditor::createNewMech(const std::string& name) {
    if (m_hotReload && !m_editorState.currentMechName.empty()) {
        m_factory->unwatchForChanges(m_editorState.currentMechName);
    }
    m_editorState.currentMechName = name;
    m_editorState.currentDefinition = QuadMechDefinition{};
    m_editorState.currentDefinition.name = name;
    m_editorState.previewTime = 0.0f;
    markDirty();
    m_previewInstance.reset(); // nothing to preview until modules exist
}

void QuadMechEditor::addModule(const ModuleDefinition& module) {
    auto& modules = m_editorState.currentDefinition.modules;
    auto it = std::find_if(modules.begin(), modules.end(), [&](const ModuleDefinition& m) { return m.id == module.id; });
    if (it != modules.end()) {
        Log::warn(kEditorCategory, "Module '{}' already exists; use updateModule", module.id);
        return;
    }
    modules.push_back(module);
    applyEditorChanges();
}

void QuadMechEditor::removeModule(const std::string& moduleId) {
    auto& modules = m_editorState.currentDefinition.modules;
    auto it = std::remove_if(modules.begin(), modules.end(), [&](const ModuleDefinition& m) { return m.id == moduleId; });
    if (it == modules.end()) {
        Log::warn(kEditorCategory, "No module '{}' to remove", moduleId);
        return;
    }
    modules.erase(it, modules.end());
    m_editorState.currentDefinition.physics.moduleMass.erase(moduleId);
    applyEditorChanges();
}

void QuadMechEditor::updateModule(const std::string& moduleId, const ModuleDefinition& newDef) {
    auto& modules = m_editorState.currentDefinition.modules;
    auto it = std::find_if(modules.begin(), modules.end(), [&](const ModuleDefinition& m) { return m.id == moduleId; });
    if (it == modules.end()) {
        Log::warn(kEditorCategory, "No module '{}' to update", moduleId);
        return;
    }
    *it = newDef;
    applyEditorChanges();
}

void QuadMechEditor::updateEnergyRunes(const EnergyRunes& runes) {
    m_editorState.currentDefinition.magitechMaterials.energyRunes = runes;
    applyEditorChanges();
}

void QuadMechEditor::updateEnergyCore(const EnergyCore& core) {
    m_editorState.currentDefinition.magitechMaterials.energyCore = core;
    applyEditorChanges();
}

void QuadMechEditor::updateCanopyMaterial(const CanopyMaterial& canopy) {
    m_editorState.currentDefinition.magitechMaterials.canopy = canopy;
    applyEditorChanges();
}

void QuadMechEditor::addAnimation(const AnimationDefinition& anim) {
    auto& anims = m_editorState.currentDefinition.animations;
    auto it = std::find_if(anims.begin(), anims.end(), [&](const AnimationDefinition& a) { return a.id == anim.id; });
    if (it != anims.end()) {
        Log::warn(kEditorCategory, "Animation '{}' already exists; use updateAnimation", anim.id);
        return;
    }
    anims.push_back(anim);
    applyEditorChanges();
}

void QuadMechEditor::removeAnimation(const std::string& animId) {
    auto& anims = m_editorState.currentDefinition.animations;
    auto it = std::remove_if(anims.begin(), anims.end(), [&](const AnimationDefinition& a) { return a.id == animId; });
    if (it == anims.end()) {
        Log::warn(kEditorCategory, "No animation '{}' to remove", animId);
        return;
    }
    anims.erase(it, anims.end());
    applyEditorChanges();
}

void QuadMechEditor::updateAnimation(const std::string& animId, const AnimationDefinition& newDef) {
    auto& anims = m_editorState.currentDefinition.animations;
    auto it = std::find_if(anims.begin(), anims.end(), [&](const AnimationDefinition& a) { return a.id == animId; });
    if (it == anims.end()) {
        Log::warn(kEditorCategory, "No animation '{}' to update", animId);
        return;
    }
    *it = newDef;
    applyEditorChanges();
}

void QuadMechEditor::updatePhysicsDefinition(const PhysicsDefinition& physics) {
    m_editorState.currentDefinition.physics = physics;
    applyEditorChanges();
}

void QuadMechEditor::updateJointLimits(const std::string& jointName, const JointLimit& limits) {
    m_editorState.currentDefinition.physics.jointLimits[jointName] = limits;
    applyEditorChanges();
}

void QuadMechEditor::addLODDefinition(const LODDefinition& lod) {
    auto& lods = m_editorState.currentDefinition.lods;
    auto it = std::find_if(lods.begin(), lods.end(), [&](const LODDefinition& l) { return l.quality == lod.quality; });
    if (it != lods.end()) {
        *it = lod; // one definition per quality level
    } else {
        lods.push_back(lod);
    }
    applyEditorChanges();
}

void QuadMechEditor::updateLODDefinition(LODQuality quality, const LODDefinition& lod) {
    auto& lods = m_editorState.currentDefinition.lods;
    auto it = std::find_if(lods.begin(), lods.end(), [&](const LODDefinition& l) { return l.quality == quality; });
    if (it == lods.end()) {
        Log::warn(kEditorCategory, "No LOD definition for quality {}", static_cast<int>(quality));
        return;
    }
    *it = lod;
    it->quality = quality;
    applyEditorChanges();
}

void QuadMechEditor::setPreviewTime(float time) {
    m_editorState.previewTime = std::max(0.0f, time);
    updatePreviewInstance();
}

void QuadMechEditor::setPreviewLOD(LODQuality quality) {
    if (m_editorState.previewLOD == quality) return;
    m_editorState.previewLOD = quality;
    rebuildPreviewInstance();
}

void QuadMechEditor::setPreviewAnimation(const std::string& animName) {
    if (!m_previewInstance) rebuildPreviewInstance();
    if (!m_previewInstance) return;
    m_previewInstance->currentAnimation = animName;
    m_editorState.previewTime = 0.0f;
    updatePreviewInstance();
}

QuadMechInstance* QuadMechEditor::getPreviewInstance() {
    if (!m_previewInstance) rebuildPreviewInstance();
    return m_previewInstance.get();
}

void QuadMechEditor::setEditorState(const EditorState& state) {
    const bool definitionChanged = state.currentDefinition.hashKey() != m_editorState.currentDefinition.hashKey();
    const bool lodChanged = state.previewLOD != m_editorState.previewLOD;
    m_editorState = state;
    if (definitionChanged || lodChanged) {
        rebuildPreviewInstance();
    } else {
        updatePreviewInstance();
    }
}

void QuadMechEditor::markDirty(bool dirty) {
    m_editorState.isDirty = dirty;
}

void QuadMechEditor::enableHotReload(bool enabled) {
    if (m_hotReload == enabled) return;
    m_hotReload = enabled;
    const std::string& name = m_editorState.currentMechName;
    if (name.empty()) return;
    if (enabled) m_factory->watchForChanges(name);
    else m_factory->unwatchForChanges(name);
}

void QuadMechEditor::checkForChanges() {
    const std::string name = m_editorState.currentMechName;
    if (!m_hotReload || name.empty() || !m_factory->checkForUpdates(name)) return;

    m_factory->reloadMech(name);
    if (m_editorState.isDirty) {
        // Keep unsaved edits; the on-disk change is reported but not applied.
        Log::warn(kEditorCategory, "{} changed on disk while it has unsaved edits; keeping the editor copy", name);
        return;
    }
    loadMechForEditing(name);
}

void QuadMechEditor::updatePreviewInstance() {
    if (!m_previewInstance) return;
    m_previewInstance->currentAnimationTime = m_editorState.previewTime;
    m_previewInstance->currentLOD = m_editorState.previewLOD;
}

void QuadMechEditor::rebuildPreviewInstance() {
    const QuadMechDefinition& def = m_editorState.currentDefinition;
    if (def.modules.empty()) {
        m_previewInstance.reset();
        return;
    }
    const std::string animation = m_previewInstance ? m_previewInstance->currentAnimation : std::string("idle");
    try {
        m_previewInstance = std::make_unique<QuadMechInstance>(
            m_factory->instantiateDefinition(def, m_editorState.previewLOD));
        m_previewInstance->currentAnimation = animation;
        updatePreviewInstance();
    } catch (const std::exception& e) {
        Log::error(kEditorCategory, "Preview rebuild failed for {}: {}", def.name, e.what());
        m_previewInstance.reset();
    }
}

void QuadMechEditor::applyEditorChanges() {
    markDirty();
    rebuildPreviewInstance();
}

} // namespace QuadMech
} // namespace MagiTech
