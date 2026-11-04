#include "AudioAssetFactory.hpp"
#include "GeneratorConcurrency.hpp"
#include "AudioAssetGenerators.hpp"
#include "SampleGen.hpp"
#include "SynthGen.hpp"
#include "EffectGen.hpp"
#include "MixerGen.hpp"
#include "ExportGen.hpp"
#include "AudioLODGen.hpp"
#include "GPUAudioInterface.hpp"
#include "core/Log.hpp"
#include "core/utils/HashCombine.hpp"
#include <future>
#include <chrono>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

namespace {

constexpr uint32_t kFactorySampleRate = 44100;
constexpr uint32_t kFactoryChannels = 2;

// Hash of a list of parameter structs (each provides hashKey()).
template<typename T>
uint64_t hashVector(const std::vector<T>& vec) {
    size_t seed = ud::hash::hash_combine(0, vec.size());
    for (const auto& item : vec) {
        seed = ud::hash::hash_combine(seed, item.hashKey());
    }
    return static_cast<uint64_t>(seed);
}

uint64_t bundleBytes(const AudioBundle& bundle) {
    uint64_t bytes = bundle.buffer.size() * sizeof(float);
    for (const auto& lod : bundle.lodBuffers) bytes += lod.size() * sizeof(float);
    return bytes;
}

// Per-level defaults of the LOD chain.
LODParams lodParamsFor(LODLevel level) {
    LODParams lp;
    lp.lodLevels = {level};
    switch (level) {
        case LODLevel::HIGH:
            lp.lodSampleRates = {SampleRate::SR_44100};
            lp.lodChannels = {ChannelLayout::STEREO};
            break;
        case LODLevel::MEDIUM:
            lp.lodSampleRates = {SampleRate::SR_22050};
            lp.lodChannels = {ChannelLayout::STEREO};
            break;
        case LODLevel::LOW:
            lp.lodSampleRates = {SampleRate::SR_11025};
            lp.lodChannels = {ChannelLayout::MONO};
            break;
        case LODLevel::ULTRA_LOW:
            lp.lodSampleRates = {SampleRate::SR_8000};
            lp.lodChannels = {ChannelLayout::MONO};
            break;
    }
    lp.lodBitDepths = {BitDepth::BD_16};
    return lp;
}

} // namespace

AudioAssetFactory::AudioAssetFactory() {
    // Initialize generator modules
    m_sampleGen = std::make_unique<SampleGen>();
    m_synthGen = std::make_unique<SynthGen>();
    m_effectGen = std::make_unique<EffectGen>();
    m_mixerGen = std::make_unique<MixerGen>();
    m_exportGen = std::make_unique<ExportGen>();
    m_lodGen = std::make_unique<LODGen>();
    m_gpuDevice = std::make_unique<GPUAudioInterface>();

    // Until initialize() starts workers the pool runs tasks inline
    m_threadPool = std::make_unique<GeneratorTaskPool>();

    // Initialize metrics
    m_metrics.reset();
}

AudioAssetFactory::~AudioAssetFactory() {
    shutdown();
    if (m_threadPool) {
        m_threadPool->stop();
    }
}

void AudioAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;

    m_cache.setCapacity(cache_size);
    if (!m_threadPool) {
        m_threadPool = std::make_unique<GeneratorTaskPool>();
    }
    m_threadPool->start(std::max<size_t>(1, num_threads));
    m_bundlePool.setMaxSize(100);
    m_maxProcessingThreads = static_cast<int>(std::max<size_t>(1, num_threads));

    m_initialized = true;
}

void AudioAssetFactory::shutdown() {
    if (!m_initialized) return;

    if (m_threadPool) {
        m_threadPool->stop();
    }

    // Release GPU resources held for cached bundles
    {
        std::lock_guard<std::recursive_mutex> gpuLock(m_gpuMutex);
        std::unique_lock<std::shared_mutex> lock(m_textureCacheMutex);
        if (m_gpuDevice) {
            for (const auto& [key, handle] : m_bufferCache) m_gpuDevice->destroyAudioBuffer(handle);
            for (const auto& [key, handle] : m_textureCache) m_gpuDevice->destroyAudioTexture(handle);
            m_gpuDevice->shutdown();
        }
        m_bufferCache.clear();
        m_textureCache.clear();
    }

    m_cache.clear();
    m_initialized = false;
}

// Generic cached generation ---------------------------------------------------
template<typename Params>
std::future<AudioBundle> AudioAssetFactory::generateCachedAsync(const Params& params) {
    const uint64_t key = params.hashKey();

    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [bundle = *hit]() { return bundle; });
    }

    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([this, params, key]() {
        auto startTime = std::chrono::high_resolution_clock::now();

        AudioBundle bundle = buildBundle(params);
        finalizeBundle(bundle, key);

        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), bundle.gpuAccelerated, bundleBytes(bundle));

        m_cache.insert(key, bundle);
        return bundle;
    });
}

template<typename Params>
AudioBundle AudioAssetFactory::generateCachedSync(const Params& params) {
    const uint64_t key = params.hashKey();

    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return *hit;
    }

    m_metrics.cacheMisses++;
    auto startTime = std::chrono::high_resolution_clock::now();

    AudioBundle bundle = buildBundle(params);
    finalizeBundle(bundle, key);

    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
    updatePerformanceMetrics(duration.count(), bundle.gpuAccelerated, bundleBytes(bundle));

    m_cache.insert(key, bundle);
    return bundle;
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
    const uint64_t key = static_cast<uint64_t>(ud::hash::hash_combine(
        static_cast<size_t>(sp.hashKey()), hashVector(samples), hashVector(synths),
        ep.hashKey(), mp.hashKey(), xp.hashKey(), lp.hashKey()));

    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits++;
        return std::async(std::launch::deferred, [bundle = *hit]() { return bundle; });
    }

    m_metrics.cacheMisses++;
    return m_threadPool->enqueue([this, sp, samples, synths, ep, mp, xp, lp, key]() {
        auto startTime = std::chrono::high_resolution_clock::now();

        AudioBundle bundle = buildComposite(sp, samples, synths, ep, mp, xp, lp);
        finalizeBundle(bundle, key);

        // Update performance metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        updatePerformanceMetrics(duration.count(), bundle.gpuAccelerated, bundleBytes(bundle));

        m_cache.insert(key, bundle);
        return bundle;
    });
}

// Samples + synths -> mixer -> effect chain -> (export definition) -> LOD chain
AudioBundle AudioAssetFactory::buildComposite(const SoundParams& sp, const std::vector<SampleParams>& samples,
                                              const std::vector<SynthParams>& synths, const EffectParams& ep,
                                              const MixerParams& mp, const ExportParams& xp, const LODParams& lp) {
    AudioBundle bundle;

    std::vector<AudioBuffer> sampleBuffers;
    {
        std::lock_guard<std::mutex> lock(m_sampleMutex);
        sampleBuffers = AudioGenerators::processSamples(*m_sampleGen, samples);
    }
    std::vector<AudioBuffer> synthBuffers;
    {
        std::lock_guard<std::mutex> lock(m_synthMutex);
        synthBuffers = AudioGenerators::generateSynths(*m_synthGen, synths, sp.duration);
    }

    // Mix all tracks (all generators render interleaved stereo at 44.1 kHz)
    MixerParams mix = mp;
    mix.channels = static_cast<int>(kFactoryChannels);
    {
        std::lock_guard<std::mutex> lock(m_mixerMutex);
        bundle.buffer = AudioGenerators::mixTracks(*m_mixerGen, sampleBuffers, synthBuffers, mix);
    }

    // Effect chain
    {
        EffectParams effects = ep;
        effects.sampleRate = kFactorySampleRate;
        std::lock_guard<std::mutex> lock(m_effectMutex);
        bundle.buffer = AudioGenerators::applyEffects(*m_effectGen, bundle.buffer, effects);
    }

    // Fit to the requested sound length
    if (sp.duration > 0.0f) {
        bundle.buffer.resize(static_cast<size_t>(sp.duration * kFactorySampleRate) * kFactoryChannels, 0.0f);
    }
    for (auto& sample : bundle.buffer) {
        sample = std::clamp(sample, -1.0f, 1.0f);
    }

    // An explicit export definition writes/distributes the result
    if (!xp.exportDefinitionPath.empty()) {
        ExportParams exportParams = xp;
        exportParams.exportSampleRate = SampleRate::SR_44100;
        exportParams.exportChannels = ChannelLayout::STEREO;
        std::lock_guard<std::mutex> lock(m_exportMutex);
        ExportResult exported = m_exportGen->exportAudio(exportParams, bundle.buffer);
        for (const auto& warning : exported.warnings) {
            Log::warn("Audio", "Export of {}: {}", sp.id, warning);
        }
    }

    // LOD chain
    if (!lp.lodLevels.empty() && !bundle.buffer.empty()) {
        LODParams lodParams = lp;
        lodParams.sourceSampleRate = kFactorySampleRate;
        std::lock_guard<std::mutex> lock(m_lodMutex);
        bundle.lodBuffers = AudioGenerators::resampleLODs(*m_lodGen, bundle.buffer, lodParams);
        bundle.lodLevels = lp.lodLevels;
        bundle.lodSampleRates = lp.lodSampleRates;
        bundle.lodBitDepths = lp.lodBitDepths;
        bundle.lodChannels = lp.lodChannels;
    }

    // Set metadata
    bundle.meta.id = sp.id;
    bundle.meta.duration = sp.duration > 0.0f
        ? sp.duration
        : static_cast<float>(bundle.buffer.size()) / (kFactorySampleRate * kFactoryChannels);
    bundle.meta.loop = sp.loop;
    return bundle;
}

// Enhanced generation methods
std::future<AudioBundle> AudioAssetFactory::generateAsync(const SampleParams& params) {
    return generateCachedAsync(params);
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const SynthParams& params) {
    return generateCachedAsync(params);
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const EffectParams& params) {
    return generateCachedAsync(params);
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const MixerParams& params) {
    return generateCachedAsync(params);
}

std::future<AudioBundle> AudioAssetFactory::generateAsync(const ExportParams& params) {
    return generateCachedAsync(params);
}

// Synchronous generation methods
AudioBundle AudioAssetFactory::generateSync(const SampleParams& params) {
    return generateCachedSync(params);
}

AudioBundle AudioAssetFactory::generateSync(const SynthParams& params) {
    return generateCachedSync(params);
}

AudioBundle AudioAssetFactory::generateSync(const EffectParams& params) {
    return generateCachedSync(params);
}

AudioBundle AudioAssetFactory::generateSync(const MixerParams& params) {
    return generateCachedSync(params);
}

AudioBundle AudioAssetFactory::generateSync(const ExportParams& params) {
    return generateCachedSync(params);
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
    m_cache.setCapacity(capacity);
}

// Performance optimization
void AudioAssetFactory::preloadCommonAudio() {
    // Preload common audio samples (file, trim range, pitch shift in semitones, gain)
    std::vector<SampleParams> commonSamples = {
        {"ui_click.wav", glm::vec2(0.0f, 0.0f), 0.0f, 1.0f},
        {"ui_hover.wav", glm::vec2(0.0f, 0.0f), 0.0f, 0.8f},
        {"magic_spell.wav", glm::vec2(0.0f, 0.0f), 0.0f, 1.0f}
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
    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    m_gpuAccelerationEnabled = enabled;
    if (enabled && m_gpuDevice && !m_gpuDevice->isInitialized()) {
        // Host-side resource mode; a render device can be attached via the interface later
        m_gpuDevice->initialize();
    }
}

bool AudioAssetFactory::isGPUAccelerationEnabled() const {
    return m_gpuAccelerationEnabled;
}

void AudioAssetFactory::setGPUDevice(std::unique_ptr<GPUAudioInterface> device) {
    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    {
        // Handles of the previous device are meaningless for the new one
        std::unique_lock<std::shared_mutex> cacheLock(m_textureCacheMutex);
        if (m_gpuDevice) {
            for (const auto& [key, handle] : m_bufferCache) m_gpuDevice->destroyAudioBuffer(handle);
            for (const auto& [key, handle] : m_textureCache) m_gpuDevice->destroyAudioTexture(handle);
        }
        m_bufferCache.clear();
        m_textureCache.clear();
    }
    m_gpuDevice = std::move(device);
    if (m_gpuDevice && m_gpuAccelerationEnabled && !m_gpuDevice->isInitialized()) {
        m_gpuDevice->initialize();
    }
}

// Configuration
void AudioAssetFactory::setThreadPool(std::unique_ptr<GeneratorTaskPool> pool) {
    if (!pool) return;
    if (m_threadPool) m_threadPool->stop();
    m_threadPool = std::move(pool);
}

void AudioAssetFactory::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 64);
    {
        std::lock_guard<std::mutex> lock(m_sampleMutex);
        m_sampleGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
    {
        std::lock_guard<std::mutex> lock(m_synthMutex);
        m_synthGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
    {
        std::lock_guard<std::mutex> lock(m_effectMutex);
        m_effectGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
    {
        std::lock_guard<std::mutex> lock(m_mixerMutex);
        m_mixerGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
    {
        std::lock_guard<std::mutex> lock(m_exportMutex);
        m_exportGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
    {
        std::lock_guard<std::mutex> lock(m_lodMutex);
        m_lodGen->setMaxProcessingThreads(m_maxProcessingThreads);
    }
}

void AudioAssetFactory::setQualitySettings(float multiplier) {
    m_qualityMultiplier = multiplier;
}

// LOD support
AudioBundle AudioAssetFactory::generateLOD(const AudioBundle& master, LODLevel level) {
    LODParams lp = lodParamsFor(level);
    lp.sourceBuffer = master.buffer;
    lp.sourceSampleRate = kFactorySampleRate;

    AudioBundle lodBundle;
    {
        std::lock_guard<std::mutex> lock(m_lodMutex);
        lodBundle = m_lodGen->process(lp);
    }

    AudioBundle result;
    result.buffer = lodBundle.buffer;
    result.meta = master.meta;
    result.meta.duration = lodBundle.meta.duration;
    result.lodBuffers = lodBundle.lodBuffers;
    result.lodLevels = lodBundle.lodLevels;
    result.lodSampleRates = lodBundle.lodSampleRates;
    result.lodBitDepths = lodBundle.lodBitDepths;
    result.lodChannels = lodBundle.lodChannels;
    result.creationTime = std::chrono::system_clock::now();
    analyzeAudioQuality(result);
    return result;
}

std::vector<AudioBundle> AudioAssetFactory::generateLODChain(const AudioBundle& master) {
    std::vector<AudioBundle> chain;
    for (LODLevel level : {LODLevel::HIGH, LODLevel::MEDIUM, LODLevel::LOW, LODLevel::ULTRA_LOW}) {
        chain.push_back(generateLOD(master, level));
    }
    return chain;
}

// Private helper methods
AudioBundle AudioAssetFactory::buildBundle(const SampleParams& params) {
    std::lock_guard<std::mutex> lock(m_sampleMutex);
    return m_sampleGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const SynthParams& params) {
    std::lock_guard<std::mutex> lock(m_synthMutex);
    return m_synthGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const EffectParams& params) {
    std::lock_guard<std::mutex> lock(m_effectMutex);
    return m_effectGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const MixerParams& params) {
    std::lock_guard<std::mutex> lock(m_mixerMutex);
    return m_mixerGen->process(params);
}

AudioBundle AudioAssetFactory::buildBundle(const ExportParams& params) {
    std::lock_guard<std::mutex> lock(m_exportMutex);
    return m_exportGen->process(params);
}

// Common post-processing of every generated bundle
void AudioAssetFactory::finalizeBundle(AudioBundle& bundle, uint64_t key) {
    optimizeBundle(bundle);
    analyzeAudioQuality(bundle);
    bundle.meta.quality = bundle.quality;
    bundle.creationTime = std::chrono::system_clock::now();
    if (bundle.meta.creationTime == std::chrono::system_clock::time_point{}) {
        bundle.meta.creationTime = bundle.creationTime;
    }
    if (m_gpuAccelerationEnabled) {
        createGPUResources(bundle);
        if (bundle.gpuAccelerated) {
            std::unique_lock<std::shared_mutex> lock(m_textureCacheMutex);
            m_bufferCache[key] = bundle.gpuBuffer;
            if (bundle.gpuTexture) m_textureCache[key] = bundle.gpuTexture;
        }
    }
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

void AudioAssetFactory::updatePerformanceMetrics(uint64_t processingTime, bool gpuUsed, uint64_t bundleBytesUsed) {
    m_metrics.totalProcessingTime += processingTime;
    m_metrics.totalGenerations++;

    if (gpuUsed) {
        m_metrics.gpuGenerations++;
    }

    // Largest single generated bundle (PCM + LOD buffers)
    uint64_t previous = m_metrics.peakMemoryUsage.load();
    while (bundleBytesUsed > previous && !m_metrics.peakMemoryUsage.compare_exchange_weak(previous, bundleBytesUsed)) {
    }

    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    if (m_gpuDevice && m_gpuDevice->isInitialized()) {
        m_metrics.gpuMemoryUsage = m_gpuDevice->getGPUMemoryUsage();
        m_metrics.gpuUtilization = static_cast<uint64_t>(std::lround(m_gpuDevice->getGPUUtilization() * 100.0f));
    }
}

void AudioAssetFactory::createGPUResources(AudioBundle& bundle) {
    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    if (!m_gpuDevice || !m_gpuAccelerationEnabled || bundle.buffer.empty()) return;
    if (!m_gpuDevice->isInitialized() && !m_gpuDevice->initialize()) return;

    bundle.gpuBuffer = m_gpuDevice->createAudioBuffer(bundle.buffer.data(), bundle.buffer.size() * sizeof(float));
    if (bundle.gpuBuffer == 0) {
        Log::warn("Audio", "GPU buffer creation failed: {}", m_gpuDevice->getLastError());
        return;
    }
    const size_t frames = bundle.buffer.size() / kFactoryChannels;
    if (frames > 0) {
        bundle.gpuTexture = m_gpuDevice->createAudioTexture(bundle.buffer.data(), frames, kFactoryChannels);
    }
    bundle.gpuDescriptorSet = m_gpuDevice->createDescriptorSet(bundle.gpuBuffer, bundle.gpuTexture);
    bundle.gpuAccelerated = validateGPUResources(bundle);
}

void AudioAssetFactory::destroyGPUResources(AudioBundle& bundle) {
    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    if (!m_gpuDevice) return;

    if (bundle.gpuDescriptorSet) m_gpuDevice->destroyDescriptorSet(bundle.gpuDescriptorSet);
    if (bundle.gpuPipeline) m_gpuDevice->destroyPipeline(bundle.gpuPipeline);
    if (bundle.gpuTexture) m_gpuDevice->destroyAudioTexture(bundle.gpuTexture);
    if (bundle.gpuBuffer) m_gpuDevice->destroyAudioBuffer(bundle.gpuBuffer);

    {
        std::unique_lock<std::shared_mutex> cacheLock(m_textureCacheMutex);
        for (auto it = m_bufferCache.begin(); it != m_bufferCache.end();) {
            it = it->second == bundle.gpuBuffer ? m_bufferCache.erase(it) : std::next(it);
        }
        for (auto it = m_textureCache.begin(); it != m_textureCache.end();) {
            it = it->second == bundle.gpuTexture ? m_textureCache.erase(it) : std::next(it);
        }
    }

    bundle.gpuDescriptorSet = 0;
    bundle.gpuPipeline = 0;
    bundle.gpuTexture = 0;
    bundle.gpuBuffer = 0;
    bundle.gpuAccelerated = false;
}

bool AudioAssetFactory::validateGPUResources(const AudioBundle& bundle) {
    std::lock_guard<std::recursive_mutex> lock(m_gpuMutex);
    if (!m_gpuDevice) return false;

    if (!m_gpuDevice->validateAudioBuffer(bundle.gpuBuffer)) return false;
    if (bundle.gpuTexture && !m_gpuDevice->validateAudioTexture(bundle.gpuTexture)) return false;
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

// Crest factor in dB (peak to RMS ratio)
float AudioAssetFactory::calculateDynamicRange(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;

    const float peak = calculatePeakAmplitude(buffer);
    const float rms = calculateRMSAmplitude(buffer);
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

// SNR estimate: signal RMS against the RMS of the sample-to-sample residual
// (high-frequency content above the signal band is treated as noise).
float AudioAssetFactory::calculateSignalToNoiseRatio(const AudioBuffer& buffer) {
    if (buffer.size() < 2) return 0.0f;

    double signalPower = 0.0;
    double noisePower = 0.0;
    for (size_t i = 0; i < buffer.size(); ++i) {
        signalPower += static_cast<double>(buffer[i]) * buffer[i];
        if (i >= kFactoryChannels) {
            // Second difference of the same channel isolates the highest-frequency residue
            const double prev = buffer[i - kFactoryChannels];
            const double prev2 = i >= 2 * kFactoryChannels ? buffer[i - 2 * kFactoryChannels] : prev;
            const double residual = buffer[i] - 2.0 * prev + prev2;
            noisePower += 0.25 * residual * residual;
        }
    }

    if (signalPower <= 0.0) return 0.0f;
    if (noisePower <= 1e-20) return 120.0f;
    return static_cast<float>(10.0 * std::log10(signalPower / noisePower));
}

} // namespace Audio
} // namespace MagiTech
