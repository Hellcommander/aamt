#pragma once
#include <future>
#include <memory>
#include <optional>
#include <unordered_map>
#include <shared_mutex>
#include <mutex>
#include <atomic>
#include <chrono>
#include "GeneratorConcurrency.hpp"
#include "QuadMechTypes.hpp"
#include "core/Log.hpp"

namespace MagiTech {

// Generator modules (implemented in QuadMechGenerators.cpp)
namespace QuadMechGen {
    using QuadMech::QuadMechDefinition;
    using QuadMech::ModuleEntry;
    using QuadMech::ModuleDefinition;
    using QuadMech::LODQuality;
    using QuadMech::LODDefinition;
    using QuadMech::SkeletonHandle;
    using QuadMech::MaterialHandle;
    using QuadMech::MeshHandle;
    using QuadMech::AnimationHandle;
    using QuadMech::AnimationType;
    using QuadMech::PhysicsBodyHandle;
    using QuadMech::EnergyRunes;
    using QuadMech::EnergyCore;
    using QuadMech::CanopyMaterial;
    using QuadMech::MagitechMaterials;
    using QuadMech::QuadMechAsset;
    using QuadMech::MechPackage;

    namespace DefinitionParser {
        // Parses a .quadmechdef document (YAML subset, or JSON).
        QuadMechDefinition parseFromYAML(const std::string& yamlContent);
        // Serializes a definition back to a document parseFromYAML accepts (JSON).
        std::string serializeDefinition(const QuadMechDefinition& def);
        bool validateDefinition(const QuadMechDefinition& def);
    }

    namespace ModuleAssembler {
        std::vector<ModuleEntry> assembleModules(const QuadMechDefinition& def, LODQuality quality);
        SkeletonHandle buildSkeleton(const QuadMechDefinition& def);
    }

    namespace MaterialSynthesizer {
        MaterialHandle createEnergyRunesMaterial(const EnergyRunes& runes);
        MaterialHandle createEnergyCoreMaterial(const EnergyCore& core);
        MaterialHandle createCanopyMaterial(const CanopyMaterial& canopy);
        std::vector<MaterialHandle> generateLODMaterials(const MagitechMaterials& materials, LODQuality quality);
    }

    namespace AnimationProcessor {
        AnimationHandle retargetAnimation(const std::string& path, const SkeletonHandle& skeleton, AnimationType type);
        std::unordered_map<std::string, AnimationHandle> processAllAnimations(const QuadMechDefinition& def, const SkeletonHandle& skeleton);
    }

    namespace PhysicsRigBuilder {
        PhysicsBodyHandle createModulePhysics(const ModuleDefinition& module, float mass);
        std::vector<PhysicsBodyHandle> buildPhysicsRig(const QuadMechDefinition& def);
        void setupJointConstraints(const QuadMechDefinition& def, std::vector<PhysicsBodyHandle>& bodies);
    }

    namespace LODGenerator {
        MeshHandle generateLODMesh(const MeshHandle& original, LODQuality quality, float decimateFactor);
        MaterialHandle generateLODMaterial(const MaterialHandle& original, LODQuality quality, float detailFactor);
        std::array<MeshHandle, 4> generateAllLODs(const MeshHandle& original, const std::vector<LODDefinition>& lods);
    }

    namespace PackageWriter {
        bool writeMechPackage(const QuadMechAsset& asset, const std::string& outputPath);
        MechPackage createPackageStructure(const std::string& mechName, const std::string& outputDir);
    }

    namespace PackageReader {
        QuadMechAsset readMechPackage(const std::string& packagePath);
        MechPackage readPackageMetadata(const std::string& packagePath);
    }
} // namespace QuadMechGen

namespace QuadMech {

// Thread-safe LRU cache for QuadMech assets.
template<typename K, typename V>
class QuadMechCache {
    struct Node {
        K key;
        V value;
        std::chrono::system_clock::time_point timestamp;
        Node* prev = nullptr;
        Node* next = nullptr;
    };

    std::unordered_map<K, std::unique_ptr<Node>> m_cache;
    Node* m_head = nullptr;
    Node* m_tail = nullptr;
    size_t m_capacity;
    // find() reorders the recency list, so every access takes the lock exclusively.
    mutable std::mutex m_mutex;
    std::atomic<uint64_t> m_hits{0};
    std::atomic<uint64_t> m_misses{0};

public:
    explicit QuadMechCache(size_t capacity = 100) : m_capacity(capacity == 0 ? 1 : capacity) {}

    QuadMechCache(const QuadMechCache&) = delete;
    QuadMechCache& operator=(const QuadMechCache&) = delete;

    std::optional<V> find(const K& key) {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_cache.find(key);
        if (it != m_cache.end()) {
            m_hits++;
            moveToFront(it->second.get());
            return it->second->value;
        }
        m_misses++;
        return std::nullopt;
    }

    void insert(const K& key, const V& value) {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_cache.find(key);
        if (it != m_cache.end()) {
            it->second->value = value;
            it->second->timestamp = std::chrono::system_clock::now();
            moveToFront(it->second.get());
            return;
        }

        while (m_cache.size() >= m_capacity && m_tail) {
            evictLRU();
        }

        auto node = std::make_unique<Node>();
        node->key = key;
        node->value = value;
        node->timestamp = std::chrono::system_clock::now();
        insertAtFront(node.get());
        m_cache[key] = std::move(node);
    }

    bool erase(const K& key) {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_cache.find(key);
        if (it == m_cache.end()) return false;
        unlink(it->second.get());
        m_cache.erase(it);
        return true;
    }

    void clear() {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_cache.clear();
        m_head = m_tail = nullptr;
    }

    // Changes the capacity, evicting least-recently-used entries if needed.
    void setCapacity(size_t capacity) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_capacity = capacity == 0 ? 1 : capacity;
        while (m_cache.size() > m_capacity && m_tail) {
            evictLRU();
        }
    }

    size_t capacity() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_capacity;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_cache.size();
    }

    double getHitRate() const {
        uint64_t total = m_hits.load() + m_misses.load();
        return total > 0 ? static_cast<double>(m_hits.load()) / total : 0.0;
    }

private:
    // All helpers below require m_mutex to be held.
    void unlink(Node* node) {
        if (node->prev) node->prev->next = node->next;
        else m_head = node->next;
        if (node->next) node->next->prev = node->prev;
        else m_tail = node->prev;
        node->prev = node->next = nullptr;
    }

    void moveToFront(Node* node) {
        if (node == m_head) return;
        unlink(node);
        insertAtFront(node);
    }

    void insertAtFront(Node* node) {
        node->next = m_head;
        node->prev = nullptr;
        if (m_head) m_head->prev = node;
        m_head = node;
        if (!m_tail) m_tail = node;
    }

    void evictLRU() {
        if (!m_tail) return;
        Node* victim = m_tail;
        unlink(victim);
        m_cache.erase(victim->key); // destroys victim; do not touch it afterwards
    }
};

class QuadMechFactory {
    using AssetPtr = std::shared_ptr<QuadMechAsset>;

    QuadMechCache<uint64_t, AssetPtr> m_cache;
    std::unique_ptr<GeneratorTaskPool> m_threadPool;
    std::atomic<bool> m_initialized{false};

    // File watcher for hot-reload
    std::unordered_map<std::string, std::chrono::system_clock::time_point> m_fileTimestamps;
    mutable std::shared_mutex m_fileWatcherMutex;

    // Performance metrics
    std::atomic<uint64_t> m_totalLoads{0};
    std::atomic<uint64_t> m_cacheHits{0};
    std::atomic<uint64_t> m_cacheMisses{0};
    std::atomic<uint64_t> m_totalLoadTime{0};

public:
    QuadMechFactory();
    ~QuadMechFactory();

    // Initialization and shutdown
    void initialize(size_t cache_size = 100, size_t num_threads = 4);
    void shutdown();
    bool isInitialized() const { return m_initialized.load(); }

    // Core loading methods
    std::future<QuadMechInstance> loadAsync(const std::string& mechName, LODQuality quality = LODQuality::HIGH);
    QuadMechInstance loadSync(const std::string& mechName, LODQuality quality = LODQuality::HIGH);

    // Package generation
    std::future<bool> generatePackageAsync(const std::string& definitionPath, const std::string& outputPath);
    bool generatePackageSync(const std::string& definitionPath, const std::string& outputPath);

    // Hot-reload support
    void watchForChanges(const std::string& mechName);
    void unwatchForChanges(const std::string& mechName);
    bool checkForUpdates(const std::string& mechName);
    void reloadMech(const std::string& mechName);

    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    double getCacheHitRate() const;
    void setCacheCapacity(size_t capacity);

    // Performance monitoring
    struct PerformanceMetrics {
        uint64_t totalLoads = 0;
        uint64_t cacheHits = 0;
        uint64_t cacheMisses = 0;
        uint64_t totalLoadTime = 0;
        double averageLoadTime = 0.0;
        double cacheHitRate = 0.0;
    };

    PerformanceMetrics getPerformanceMetrics() const;
    void resetPerformanceMetrics();

    // Utility methods
    bool validateMechDefinition(const QuadMechDefinition& def);
    std::vector<std::string> getAvailableMechs() const;
    bool mechExists(const std::string& mechName) const;

    // Location of a mech's definition file / package directory.
    static std::string definitionPathFor(const std::string& mechName);
    static std::string packagePathFor(const std::string& mechName);

    // Builds an asset directly from a definition (used by the editor preview).
    QuadMechInstance instantiateDefinition(const QuadMechDefinition& def, LODQuality quality);

private:
    // Private helper methods
    AssetPtr loadMechAsset(const std::string& mechName, LODQuality quality);
    AssetPtr loadMechAssetCached(const std::string& mechName, LODQuality quality, bool& cacheHit);
    static uint64_t cacheKeyFor(const std::string& mechName, LODQuality quality);
    QuadMechInstance createInstance(const AssetPtr& asset, LODQuality quality);

    // File watching
    uint64_t computeFileHash(const std::string& filePath);
    void updateFileTimestamp(const std::string& filePath);
    bool hasFileChanged(const std::string& filePath);

    // Package generation helpers
    QuadMechAsset generateMechAsset(const QuadMechDefinition& def, LODQuality quality);
    bool writePackageToDisk(const QuadMechAsset& asset, const std::string& outputPath);

    // Performance tracking
    void updatePerformanceMetrics(uint64_t loadTime, bool cacheHit);
};

// ============================================================================
// RUNTIME LOADER & CACHE IMPLEMENTATION
// ============================================================================

class QuadMechLoader {
    std::unique_ptr<QuadMechFactory> m_factory;
    std::unordered_map<std::string, QuadMechInstance> m_activeInstances;
    mutable std::shared_mutex m_instancesMutex;
    std::atomic<uint64_t> m_nextInstanceId{1};

public:
    QuadMechLoader();
    ~QuadMechLoader();

    // Instance management
    QuadMechInstance createInstance(const std::string& mechName, LODQuality quality = LODQuality::HIGH);
    void destroyInstance(const std::string& instanceId);
    QuadMechInstance getInstance(const std::string& instanceId);

    // Batch operations
    std::vector<QuadMechInstance> createBatchInstances(const std::vector<std::string>& mechNames, LODQuality quality = LODQuality::HIGH);
    void destroyAllInstances();

    // Runtime updates
    void updateInstance(const std::string& instanceId, const glm::mat4& transform);
    void setInstanceAnimation(const std::string& instanceId, const std::string& animationName);
    void setInstanceLOD(const std::string& instanceId, LODQuality quality);

    // Magitech runtime state
    void setEnergyLevel(const std::string& instanceId, float energyLevel);
    void setRuneGlowIntensity(const std::string& instanceId, float intensity);
    void setCockpitState(const std::string& instanceId, bool open, bool pilotInside);

    // Physics interaction
    void applyForce(const std::string& instanceId, const glm::vec3& force, const glm::vec3& point);
    void setPhysicsTransform(const std::string& instanceId, const glm::mat4& transform);

    // Utility
    size_t getActiveInstanceCount() const;
    std::vector<std::string> getActiveInstanceIds() const;
    void clearAllInstances();

private:
    // Runs fn on the instance under the write lock; logs and returns false if unknown.
    template<typename Fn>
    bool withInstance(const std::string& instanceId, Fn&& fn);
};

// ============================================================================
// EDITOR INTEGRATION
// ============================================================================

class QuadMechEditor {
    std::unique_ptr<QuadMechFactory> m_factory;
    EditorState m_editorState;
    std::unique_ptr<QuadMechInstance> m_previewInstance;
    bool m_hotReload = false;

public:
    QuadMechEditor();
    ~QuadMechEditor();

    // Editor state management
    void loadMechForEditing(const std::string& mechName);
    void saveCurrentMech(const std::string& outputPath);
    void createNewMech(const std::string& name);

    // Module editing
    void addModule(const ModuleDefinition& module);
    void removeModule(const std::string& moduleId);
    void updateModule(const std::string& moduleId, const ModuleDefinition& newDef);

    // Material editing
    void updateEnergyRunes(const EnergyRunes& runes);
    void updateEnergyCore(const EnergyCore& core);
    void updateCanopyMaterial(const CanopyMaterial& canopy);

    // Animation editing
    void addAnimation(const AnimationDefinition& anim);
    void removeAnimation(const std::string& animId);
    void updateAnimation(const std::string& animId, const AnimationDefinition& newDef);

    // Physics editing
    void updatePhysicsDefinition(const PhysicsDefinition& physics);
    void updateJointLimits(const std::string& jointName, const JointLimit& limits);

    // LOD editing
    void addLODDefinition(const LODDefinition& lod);
    void updateLODDefinition(LODQuality quality, const LODDefinition& lod);

    // Preview functionality
    void setPreviewTime(float time);
    void setPreviewLOD(LODQuality quality);
    void setPreviewAnimation(const std::string& animName);
    QuadMechInstance* getPreviewInstance();

    // Editor state
    const EditorState& getEditorState() const { return m_editorState; }
    void setEditorState(const EditorState& state);
    bool isDirty() const { return m_editorState.isDirty; }
    void markDirty(bool dirty = true);

    // Hot-reload support
    void enableHotReload(bool enabled = true);
    void checkForChanges();

private:
    void updatePreviewInstance();
    void rebuildPreviewInstance();
    void applyEditorChanges();
};

} // namespace QuadMech
} // namespace MagiTech
