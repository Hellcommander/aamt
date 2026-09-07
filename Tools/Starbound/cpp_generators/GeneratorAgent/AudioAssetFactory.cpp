#include "AudioAssetFactory.hpp"
#include "SampleGen.hpp"
#include "SynthGen.hpp"
#include "EffectGen.hpp"
#include "MixerGen.hpp"
#include "ExportGen.hpp"
#include "LODGen.hpp"
#include "GPUAudioInterface.hpp"
#include "core/utils/HashCombine.hpp"
#include <future>
#include <chrono>
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

AudioAssetFactory::AudioAssetFactory() {
    // Initialize generator modules
    m_sampleGen = std::make_unique<SampleGen>();
    m_synthGen = std::make_unique<SynthGen>();
    m_effectGen = std::make_unique<EffectGen>();
    m_mixerGen = std::make_unique<MixerGen>();
    m_exportGen = std::make_unique<ExportGen>();
    m_lodGen = std::make_unique<LODGen>();
    m_gpuDevice = std::make_unique<GPUAudioInterface>();
    
    // Initialize metrics
    m_metrics.reset();
}

AudioAssetFactory::~AudioAssetFactory() {
    shutdown();
}

void AudioAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    
    m_cache = OptimizedLRUCache<uint64_t, AudioBundle>(cache_size);
    m_threadPool = std::make_unique<ThreadPool>(num_threads);
    m_bundlePool = ObjectPool<AudioBundle>(100);
    
    m_initialized = true;
}

void AudioAssetFactory::shutdown() {
    if (!m_initialized) return;
    
    if (m_threadPool) {
        m_threadPool->stop();
    }
    
    m_cache.clear();
    m_initialized = false;
}

// Core generation method (preserving existing interface)
std::future<AudioBundle> AudioAssetFactory::generateAsync(
    const SoundParams& sp,
    const std::vector<SampleParams>& samples,
    const std::vector<SynthParams>& synths,
    const EffectParams& ep,
    const MixerParams& mp,
    const ExportParams& xp,
    const LODParams& lp)
{
    uint64_t key = hashCombine(
        sp.hashKey(), hashVector(samples), hashVector(synths),
        ep.hashKey(), mp.hashKey(), xp.hashKey(), lp.hashKey()
    );

    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }

    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle;
        
        // Process samples
        std::vector<AudioBuffer> sampleBuffers;
        for (const auto& sample : samples) {
            auto sampleBundle = m_sampleGen->process(sample);
            if (!sampleBundle.buffer.empty()) {
                sampleBuffers.push_back(sampleBundle.buffer);
            }
        }
        
        // Process synths
        std::vector<AudioBuffer> synthBuffers;
        for (const auto& synth : synths) {
            auto synthBundle = m_synthGen->process(synth);
            if (!synthBundle.buffer.empty()) {
                synthBuffers.push_back(synthBundle.buffer);
            }
        }
        
        // Mix tracks (simplified for now)
        if (!sampleBuffers.empty() || !synthBuffers.empty()) {
            // Simple mixing - take the longest buffer and mix all into it
            size_t maxLength = 0;
            for (const auto& buffer : sampleBuffers) {
                maxLength = std::max(maxLength, buffer.size());
            }
            for (const auto& buffer : synthBuffers) {
                maxLength = std::max(maxLength, buffer.size());
            }
            
            if (maxLength > 0) {
                bundle.buffer.resize(maxLength, 0.0f);
                
                // Mix all samples
                for (const auto& buffer : sampleBuffers) {
                    for (size_t i = 0; i < std::min(buffer.size(), maxLength); ++i) {
                        bundle.buffer[i] += buffer[i] * mp.masterGain;
                    }
                }
                
                // Mix all synths
                for (const auto& buffer : synthBuffers) {
                    for (size_t i = 0; i < std::min(buffer.size(), maxLength); ++i) {
                        bundle.buffer[i] += buffer[i] * mp.masterGain;
                    }
                }
                
                // Clamp to prevent clipping
                for (auto& sample : bundle.buffer) {
                    sample = std::clamp(sample, -1.0f, 1.0f);
                }
            }
        }
        
        // Set metadata
        bundle.meta.id = sp.id;
        bundle.meta.duration = sp.duration;
        bundle.meta.loop = sp.loop;
        bundle.creationTime = std::chrono::system_clock::now();
        
        // Analyze quality
        analyzeAudioQuality(bundle);
        
        // Update performance metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

// Enhanced generation methods
std::future<AudioBundle> AudioAssetFactory::generateAsync(const SampleParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }
    
    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle = buildBundle(params);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const SynthParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }
    
    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle = buildBundle(params);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const EffectParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }
    
    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle = buildBundle(params);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const MixerParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }
    
    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle = buildBundle(params);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const ExportParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }
    
    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        AudioBundle bundle = buildBundle(params);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), false);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

// Synchronous generation methods
AudioBundle AudioAssetFactory::generateSync(const SampleParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }
    
    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();
    
    AudioBundle bundle = buildBundle(params);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), false);
    
    m_cache.insert(key, bundle);
    return bundle;
}

AudioBundle AudioAssetFactory::generateSync(const SynthParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }
    
    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();
    
    AudioBundle bundle = buildBundle(params);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), false);
    
    m_cache.insert(key, bundle);
    return bundle;
}

AudioBundle AudioAssetFactory::generateSync(const EffectParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }
    
    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();
    
    AudioBundle bundle = buildBundle(params);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), false);
    
    m_cache.insert(key, bundle);
    return bundle;
}

AudioBundle AudioAssetFactory::generateSync(const MixerParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }
    
    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();
    
    AudioBundle bundle = buildBundle(params);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), false);
    
    m_cache.insert(key, bundle);
    return bundle;
}

AudioBundle AudioAssetFactory::generateSync(const ExportParams& params) {
    uint64_t key = params.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }
    
    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();
    
    AudioBundle bundle = buildBundle(params);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), false);
    
    m_cache.insert(key, bundle);
    return bundle;
}

// Batch processing
std::vector<std::future<AudioBundle>> AudioAssetFactory::generateBatchAsync(
    const std::vector<SampleParams>& params) {
    std::vector<std::future<AudioBundle>> futures;
    futures.reserve(params.size());
    
    for (const auto& param : params) {
        futures.push_back(generateAsync(param));
    }
    
    return futures;
}

std::vector<std::future<AudioBundle>> AudioAssetFactory::generateBatchAsync(
    const std::vector<SynthParams>& params) {
    std::vector<std::future<AudioBundle>> futures;
    futures.reserve(params.size());
    
    for (const auto& param : params) {
        futures.push_back(generateAsync(param));
    }
    
    return futures;
}

// Cache management
void AudioAssetFactory::clearCache() {
    m_cache.clear();
}

size_t AudioAssetFactory::getCacheSize() const {
    return m_cache.size();
}

double AudioAssetFactory::getCacheHitRate() const {
    return m_metrics.getCacheHitRate();
}

void AudioAssetFactory::setCacheCapacity(size_t capacity) {
    // TODO: Implement cache capacity change
}

// Performance optimization
void AudioAssetFactory::preloadCommonAudio() {
    // Preload common audio samples
    std::vector<SampleParams> commonSamples = {
        {"ui_click.wav", glm::vec2(0.0f, 0.0f), 1.0f, 1.0f},
        {"ui_hover.wav", glm::vec2(0.0f, 0.0f), 1.0f, 0.8f},
        {"magic_spell.wav", glm::vec2(0.0f, 0.0f), 1.0f, 1.0f}
    };
    
    for (const auto& sample : commonSamples) {
        generateAsync(sample);
    }
}

void AudioAssetFactory::warmupCache() {
    // Generate some common sounds to warm up the cache
    SynthParams magicSpell;
    magicSpell.waveformType = WaveformType::SINE;
    magicSpell.frequency = 440.0f;
    magicSpell.amplitude = 0.8f;
    magicSpell.adsrEnvelope = glm::vec4(0.1f, 0.1f, 0.7f, 0.2f);
    
    generateAsync(magicSpell);
}

AudioPerformanceMetrics AudioAssetFactory::getPerformanceMetrics() const {
    return m_metrics;
}

void AudioAssetFactory::resetPerformanceMetrics() {
    m_metrics.reset();
}

// GPU acceleration
void AudioAssetFactory::enableGPUAcceleration(bool enabled) {
    m_gpuAccelerationEnabled = enabled;
}

bool AudioAssetFactory::isGPUAccelerationEnabled() const {
    return m_gpuAccelerationEnabled;
}

void AudioAssetFactory::setGPUDevice(std::unique_ptr<GPUAudioInterface> device) {
    m_gpuDevice = std::move(device);
}

// Configuration
void AudioAssetFactory::setThreadPool(std::unique_ptr<ThreadPool> pool) {
    m_threadPool = std::move(pool);
}

void AudioAssetFactory::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = threads;
}

void AudioAssetFactory::setQualitySettings(float multiplier) {
    m_qualityMultiplier = multiplier;
}

// LOD support
AudioBundle AudioAssetFactory::generateLOD(const AudioBundle& master, LODLevel level) {
    // TODO: Implement LOD generation
    return master;
}

std::vector<AudioBundle> AudioAssetFactory::generateLODChain(const AudioBundle& master) {
    // TODO: Implement LOD chain generation
    return {master};
}

// Private helper methods
AudioBundle AudioAssetFactory::buildBundle(const SampleParams& params) {
    return m_sampleGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const SynthParams& params) {
    return m_synthGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const EffectParams& params) {
    // TODO: Implement effect processing
    AudioBundle bundle;
    bundle.meta.id = "effect_processed";
    bundle.creationTime = std::chrono::system_clock::now();
    return bundle;
}

AudioBundle AudioAssetFactory::buildBundle(const MixerParams& params) {
    // TODO: Implement mixer processing
    AudioBundle bundle;
    bundle.meta.id = "mixed_audio";
    bundle.creationTime = std::chrono::system_clock::now();
    return bundle;
}

AudioBundle AudioAssetFactory::buildBundle(const ExportParams& params) {
    // TODO: Implement export processing
    AudioBundle bundle;
    bundle.meta.id = "exported_audio";
    bundle.creationTime = std::chrono::system_clock::now();
    return bundle;
}

void AudioAssetFactory::optimizeBundle(AudioBundle& bundle) {
    // Apply quality multiplier
    if (m_qualityMultiplier != 1.0f) {
        for (auto& sample : bundle.buffer) {
            sample *= m_qualityMultiplier;
        }
    }
    
    // Normalize if needed
    float peak = calculatePeakAmplitude(bundle.buffer);
    if (peak > 0.95f) {
        float scale = 0.95f / peak;
        for (auto& sample : bundle.buffer) {
            sample *= scale;
        }
    }
}

void AudioAssetFactory::prefetchRelatedAudio(const std::string& name) {
    // Simple heuristic: if name contains "magic", prefetch magic-related sounds
    if (name.find("magic") != std::string::npos) {
        SynthParams magicSound;
        magicSound.waveformType = WaveformType::SINE;
        magicSound.frequency = 440.0f;
        generateAsync(magicSound);
    }
}

bool AudioAssetFactory::shouldUseAsync(const std::string& name) const {
    // Simple heuristic: use async for longer sounds
    return name.length() > 10;
}

void AudioAssetFactory::updatePerformanceMetrics(uint64_t processingTime, bool gpuUsed) {
    m_metrics.totalProcessingTime += processingTime;
    m_metrics.totalGenerations++;
    
    if (gpuUsed) {
        m_metrics.gpuGenerations++;
    }
    
    // Update peak memory usage (simplified)
    m_metrics.peakMemoryUsage = std::max(m_metrics.peakMemoryUsage.load(), 
                                        static_cast<uint64_t>(1024 * 1024)); // 1MB placeholder
}

void AudioAssetFactory::createGPUResources(AudioBundle& bundle) {
    if (!m_gpuDevice || !m_gpuAccelerationEnabled) return;
    
    // TODO: Implement GPU resource creation
    bundle.gpuAccelerated = true;
}

void AudioAssetFactory::destroyGPUResources(AudioBundle& bundle) {
    if (!m_gpuDevice) return;
    
    // TODO: Implement GPU resource destruction
}

bool AudioAssetFactory::validateGPUResources(const AudioBundle& bundle) {
    if (!m_gpuDevice) return false;
    
    // TODO: Implement GPU resource validation
    return true;
}

void AudioAssetFactory::analyzeAudioQuality(AudioBundle& bundle) {
    if (bundle.buffer.empty()) return;
    
    bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
    bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
    bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
    bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
}

float AudioAssetFactory::calculatePeakAmplitude(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    
    float peak = 0.0f;
    for (float sample : buffer) {
        peak = std::max(peak, std::abs(sample));
    }
    return peak;
}

float AudioAssetFactory::calculateRMSAmplitude(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    
    float sum = 0.0f;
    for (float sample : buffer) {
        sum += sample * sample;
    }
    return std::sqrt(sum / buffer.size());
}

float AudioAssetFactory::calculateDynamicRange(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    
    float minVal = buffer[0], maxVal = buffer[0];
    for (float sample : buffer) {
        minVal = std::min(minVal, sample);
        maxVal = std::max(maxVal, sample);
    }
    return maxVal - minVal;
}

float AudioAssetFactory::calculateSignalToNoiseRatio(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    
    // Simplified SNR calculation
    float signalPower = 0.0f;
    float noisePower = 0.0f;
    
    for (float sample : buffer) {
        signalPower += sample * sample;
        // Assume noise is low-frequency components
        noisePower += (sample * 0.1f) * (sample * 0.1f);
    }
    
    if (noisePower <= 0.0f) return 100.0f;
    return 10.0f * std::log10(signalPower / noisePower);
}

// Utility function for hashing vectors
uint64_t hashVector(const auto& vec) {
    XXH64_state_t s; 
    XXH64_reset(&s, 0);
    for(const auto& item : vec) {
        uint64_t h = item.hashKey();
        XXH64_update(&s, &h, sizeof(h));
    }
    return XXH64_digest(&s);
}

} // namespace Audio
} // namespace MagiTech
