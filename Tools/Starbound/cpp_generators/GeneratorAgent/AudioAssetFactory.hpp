#pragma once
#include <future>
#include <vector>
#include <memory>
#include <atomic>
#include <shared_mutex>
#include <unordered_map>
#include <optional>
#include <chrono>
#include <mutex>
#include "GeneratorConcurrency.hpp"
#include "AudioAssetTypes.hpp"

namespace MagiTech {
namespace Audio {

// Forward declarations for generator classes
class SampleGen;
class SynthGen;
class EffectGen;
class MixerGen;
class ExportGen;
class LODGen;            // AudioLODGen.hpp
class GPUAudioInterface;

// Object Pool for AudioBundle optimization
template<typename T>
class ObjectPool {
    std::vector<std::unique_ptr<T>> m_pool;
    mutable std::mutex m_mutex;
    size_t m_maxSize;

public:
    explicit ObjectPool(size_t maxSize = 100) : m_maxSize(maxSize) {}
    ObjectPool(const ObjectPool&) = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;

    std::unique_ptr<T> acquire() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_pool.empty()) {
            return std::make_unique<T>();
        }
        auto obj = std::move(m_pool.back());
        m_pool.pop_back();
        return obj;
    }

    void release(std::unique_ptr<T> obj) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (obj && m_pool.size() < m_maxSize) {
            *obj = T{};
            m_pool.push_back(std::move(obj));
        }
    }

    void setMaxSize(size_t maxSize) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_maxSize = maxSize;
        if (m_pool.size() > m_maxSize) m_pool.resize(m_maxSize);
    }

    size_t available() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_pool.size();
    }
};

// Optimized LRU Cache with shared mutex
template<typename K, typename V>
class OptimizedLRUCache {
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
    mutable std::shared_mutex m_mutex;
    std::atomic<uint64_t> m_hits{0};
    std::atomic<uint64_t> m_misses{0};

public:
    explicit OptimizedLRUCache(size_t capacity = 1000) : m_capacity(capacity > 0 ? capacity : 1) {}
    OptimizedLRUCache(const OptimizedLRUCache&) = delete;
    OptimizedLRUCache& operator=(const OptimizedLRUCache&) = delete;

    // Not const: a hit moves the entry to the front of the LRU list.
    std::optional<V> find(const K& key) {
        std::unique_lock<std::shared_mutex> lock(m_mutex);
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
        std::unique_lock<std::shared_mutex> lock(m_mutex);
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

    // Changes the capacity, evicting least recently used entries if needed.
    void setCapacity(size_t capacity) {
        std::unique_lock<std::shared_mutex> lock(m_mutex);
        m_capacity = capacity > 0 ? capacity : 1;
        while (m_cache.size() > m_capacity && m_tail) {
            evictLRU();
        }
    }

    size_t capacity() const {
        std::shared_lock<std::shared_mutex> lock(m_mutex);
        return m_capacity;
    }

    void clear() {
        std::unique_lock<std::shared_mutex> lock(m_mutex);
        m_cache.clear();
        m_head = m_tail = nullptr;
    }

    size_t size() const {
        std::shared_lock<std::shared_mutex> lock(m_mutex);
        return m_cache.size();
    }

    double getHitRate() const {
        uint64_t total = m_hits.load() + m_misses.load();
        return total > 0 ? static_cast<double>(m_hits.load()) / total : 0.0;
    }

private:
    void moveToFront(Node* node) {
        if (node == m_head) return;

        // Remove from current position
        if (node->prev) node->prev->next = node->next;
        if (node->next) node->next->prev = node->prev;
        if (node == m_tail) m_tail = node->prev;

        // Insert at front
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
        m_tail = victim->prev;
        if (m_tail) {
            m_tail->next = nullptr;
        } else {
            m_head = nullptr;
        }
        m_cache.erase(victim->key); // frees victim
    }
};

class AudioAssetFactory {
    OptimizedLRUCache<uint64_t, AudioBundle> m_cache;
    std::unique_ptr<GeneratorTaskPool> m_threadPool;
    std::unique_ptr<GPUAudioInterface> m_gpuDevice;
    AudioPerformanceMetrics m_metrics;
    ObjectPool<AudioBundle> m_bundlePool;

    // Generator modules (each is stateful; calls are serialised per generator)
    std::unique_ptr<SampleGen> m_sampleGen;
    std::unique_ptr<SynthGen> m_synthGen;
    std::unique_ptr<EffectGen> m_effectGen;
    std::unique_ptr<MixerGen> m_mixerGen;
    std::unique_ptr<ExportGen> m_exportGen;
    std::unique_ptr<LODGen> m_lodGen;
    std::mutex m_sampleMutex;
    std::mutex m_synthMutex;
    std::mutex m_effectMutex;
    std::mutex m_mixerMutex;
    std::mutex m_exportMutex;
    std::mutex m_lodMutex;
    std::recursive_mutex m_gpuMutex;

    // Configuration
    bool m_initialized = false;
    bool m_gpuAccelerationEnabled = false;
    int m_maxProcessingThreads = 4;
    float m_qualityMultiplier = 1.0f;

    // GPU resource caches (bundle hash -> handle)
    std::unordered_map<uint64_t, AudioBufferHandle> m_bufferCache;
    std::unordered_map<uint64_t, AudioTextureHandle> m_textureCache;
    mutable std::shared_mutex m_textureCacheMutex;

public:
    AudioAssetFactory();
    ~AudioAssetFactory();

    // Initialization and shutdown
    void initialize(size_t cache_size = 1000, size_t num_threads = 4);
    void shutdown();
    bool isInitialized() const { return m_initialized; }

    // Core generation methods (preserving existing interface)
    std::future<AudioBundle> generateAsync(
        const SoundParams& sp,
        const std::vector<SampleParams>& samples,
        const std::vector<SynthParams>& synths,
        const EffectParams& ep,
        const MixerParams& mp,
        const ExportParams& xp,
        const LODParams& lp
    );

    // Enhanced generation methods
    std::future<AudioBundle> generateAsync(const SampleParams& params);
    std::future<AudioBundle> generateAsync(const SynthParams& params);
    std::future<AudioBundle> generateAsync(const EffectParams& params);
    std::future<AudioBundle> generateAsync(const MixerParams& params);
    std::future<AudioBundle> generateAsync(const ExportParams& params);

    // Synchronous generation methods
    AudioBundle generateSync(const SampleParams& params);
    AudioBundle generateSync(const SynthParams& params);
    AudioBundle generateSync(const EffectParams& params);
    AudioBundle generateSync(const MixerParams& params);
    AudioBundle generateSync(const ExportParams& params);

    // Batch processing
    std::vector<std::future<AudioBundle>> generateBatchAsync(
        const std::vector<SampleParams>& params);
    std::vector<std::future<AudioBundle>> generateBatchAsync(
        const std::vector<SynthParams>& params);

    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    double getCacheHitRate() const;
    void setCacheCapacity(size_t capacity);

    // Performance optimization
    void preloadCommonAudio();
    void warmupCache();
    AudioPerformanceMetrics getPerformanceMetrics() const;
    void resetPerformanceMetrics();

    // GPU acceleration
    void enableGPUAcceleration(bool enabled = true);
    bool isGPUAccelerationEnabled() const;
    void setGPUDevice(std::unique_ptr<GPUAudioInterface> device);

    // Configuration
    void setThreadPool(std::unique_ptr<GeneratorTaskPool> pool);
    void setMaxProcessingThreads(int threads);
    void setQualitySettings(float multiplier);

    // LOD support
    AudioBundle generateLOD(const AudioBundle& master, LODLevel level);
    std::vector<AudioBundle> generateLODChain(const AudioBundle& master);

private:
    // Generic cached generation
    template<typename Params>
    std::future<AudioBundle> generateCachedAsync(const Params& params);
    template<typename Params>
    AudioBundle generateCachedSync(const Params& params);

    // Private helper methods
    AudioBundle buildBundle(const SampleParams& params);
    AudioBundle buildBundle(const SynthParams& params);
    AudioBundle buildBundle(const EffectParams& params);
    AudioBundle buildBundle(const MixerParams& params);
    AudioBundle buildBundle(const ExportParams& params);
    AudioBundle buildComposite(const SoundParams& sp, const std::vector<SampleParams>& samples,
                               const std::vector<SynthParams>& synths, const EffectParams& ep,
                               const MixerParams& mp, const ExportParams& xp, const LODParams& lp);
    void finalizeBundle(AudioBundle& bundle, uint64_t key);

    void optimizeBundle(AudioBundle& bundle);
    void prefetchRelatedAudio(const std::string& name);
    bool shouldUseAsync(const std::string& name) const;
    void updatePerformanceMetrics(uint64_t processingTime, bool gpuUsed, uint64_t bundleBytes = 0);

    // GPU resource management
    void createGPUResources(AudioBundle& bundle);
    void destroyGPUResources(AudioBundle& bundle);
    bool validateGPUResources(const AudioBundle& bundle);

    // Audio quality analysis
    void analyzeAudioQuality(AudioBundle& bundle);
    float calculatePeakAmplitude(const AudioBuffer& buffer);
    float calculateRMSAmplitude(const AudioBuffer& buffer);
    float calculateDynamicRange(const AudioBuffer& buffer);
    float calculateSignalToNoiseRatio(const AudioBuffer& buffer);
};

} // namespace Audio
} // namespace MagiTech
