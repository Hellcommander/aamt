#include "AudioLODGen.hpp"
#include "AudioFileIO.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <numeric>
#include <random>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

namespace {
constexpr float kPi = 3.14159265359f;
constexpr float kTwoPi = 2.0f * kPi;
} // namespace

// LODGen Implementation
LODGen::LODGen()
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {

    // Initialize with default settings
    m_optimizationLevel = 2;
    m_targetQuality = 0.8f;
    m_maxFileSize = 1024 * 1024; // 1MB
}

LODGen::~LODGen() = default;

AudioBundle LODGen::process(const LODParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "lod_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f; // Will be calculated
        bundle.meta.loop = false;
        m_optimizationLevel = params.optimizationLevel;

        // Master audio: supplied source, or the reference signal
        const uint32_t sourceRate = params.sourceBuffer.empty() ? 44100u : std::max<uint32_t>(1, params.sourceSampleRate);
        std::vector<float> originalAudio = params.sourceBuffer.empty() ? generateTestAudio() : params.sourceBuffer;

        // Process LOD levels
        std::vector<std::vector<float>> lodBuffers;
        std::vector<LODLevel> lodLevels;
        std::vector<SampleRate> lodSampleRates;
        std::vector<BitDepth> lodBitDepths;
        std::vector<ChannelLayout> lodChannels;

        for (size_t i = 0; i < params.lodLevels.size(); ++i) {
            LODLevel level = params.lodLevels[i];
            SampleRate sampleRate = i < params.lodSampleRates.size() ? params.lodSampleRates[i]
                                  : (i < params.sampleRates.size() ? static_cast<SampleRate>(params.sampleRates[i]) : SampleRate::SR_44100);
            BitDepth bitDepth = i < params.lodBitDepths.size() ? params.lodBitDepths[i]
                              : (i < params.bitDepths.size() ? static_cast<BitDepth>(params.bitDepths[i]) : BitDepth::BD_16);
            ChannelLayout channels = i < params.lodChannels.size() ? params.lodChannels[i] : ChannelLayout::STEREO;

            std::vector<float> lodBuffer = generateLODLevel(originalAudio, level, sampleRate, bitDepth, channels, sourceRate);
            lodBuffers.push_back(std::move(lodBuffer));
            lodLevels.push_back(level);
            lodSampleRates.push_back(sampleRate);
            lodBitDepths.push_back(bitDepth);
            lodChannels.push_back(channels);
        }

        // Use the highest quality as the main buffer
        if (lodBuffers.empty()) {
            bundle.buffer = originalAudio;
            bundle.meta.duration = static_cast<float>(originalAudio.size()) / (static_cast<float>(sourceRate) * 2.0f);
        } else {
            bundle.buffer = lodBuffers[0];
            bundle.meta.duration = static_cast<float>(bundle.buffer.size()) /
                (static_cast<float>(static_cast<uint32_t>(lodSampleRates[0])) * static_cast<float>(static_cast<uint32_t>(lodChannels[0])));
        }

        // Set the LOD buffers
        bundle.lodBuffers = std::move(lodBuffers);
        bundle.lodLevels = lodLevels;
        bundle.lodSampleRates = lodSampleRates;
        bundle.lodBitDepths = lodBitDepths;
        bundle.lodChannels = lodChannels;
        bundle.meta.creationTime = std::chrono::system_clock::now();
        bundle.creationTime = bundle.meta.creationTime;

        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
        bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
        bundle.meta.quality = bundle.quality;

        return bundle;

    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// LOD Level Generation
std::vector<float> LODGen::generateLODLevel(const std::vector<float>& originalAudio, LODLevel level,
                                           SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels,
                                           uint32_t sourceSampleRate) {
    std::vector<float> lodAudio = originalAudio;
    m_workingSampleRate = std::max<uint32_t>(1, sourceSampleRate);
    m_workingChannels = 2;

    // Apply quality reduction based on LOD level
    switch (level) {
        case LODLevel::HIGH:
            applyHighQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::MEDIUM:
            applyMediumQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::LOW:
            applyLowQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::ULTRA_LOW:
            applyUltraLowQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
    }

    // Resample to the level's sample rate (band-limit first when going down)
    const uint32_t targetRate = static_cast<uint32_t>(sampleRate);
    if (targetRate > 0 && targetRate != m_workingSampleRate) {
        if (targetRate < m_workingSampleRate) {
            applyLowPassFilter(lodAudio, 0.45f * static_cast<float>(targetRate), 0.7071f);
        }
        lodAudio = FileIO::resampleLinear(lodAudio, m_workingChannels, m_workingSampleRate, targetRate);
        m_workingSampleRate = targetRate;
    }

    // Lay out the requested channel configuration
    const uint32_t targetChannels = static_cast<uint32_t>(channels);
    if (targetChannels != m_workingChannels) {
        lodAudio = FileIO::convertChannels(lodAudio, m_workingChannels, targetChannels);
        m_workingChannels = targetChannels;
    }

    // Quantise to the stored bit depth (float storage keeps full precision)
    if (bitDepth != BitDepth::BD_FLOAT) {
        applyBitDepthReduction(lodAudio, static_cast<float>(static_cast<int>(bitDepth)));
    }

    return lodAudio;
}

// Quality Reduction Algorithms
void LODGen::applyHighQualityReduction(std::vector<float>& audio, SampleRate sampleRate,
                                      BitDepth bitDepth, ChannelLayout channels) {
    // High quality: minimal reduction
    // Apply gentle low-pass filter to reduce high frequencies slightly
    applyLowPassFilter(audio, 15000.0f, 0.8f);

    // Slight bit depth reduction simulation
    applyBitDepthReduction(audio, 20.0f);

    // Maintain stereo width
    if (channels == ChannelLayout::STEREO) {
        maintainStereoWidth(audio);
    }
}

void LODGen::applyMediumQualityReduction(std::vector<float>& audio, SampleRate sampleRate,
                                        BitDepth bitDepth, ChannelLayout channels) {
    // Medium quality: moderate reduction
    // Apply more aggressive low-pass filter
    applyLowPassFilter(audio, 8000.0f, 0.6f);

    // Reduce dynamic range
    applyDynamicRangeCompression(audio, -20.0f, 4.0f);

    // Bit depth reduction
    applyBitDepthReduction(audio, 16.0f);

    // Slight stereo width reduction
    if (channels == ChannelLayout::STEREO) {
        reduceStereoWidth(audio, 0.8f);
    }
}

void LODGen::applyLowQualityReduction(std::vector<float>& audio, SampleRate sampleRate,
                                     BitDepth bitDepth, ChannelLayout channels) {
    // Low quality: significant reduction
    // Aggressive low-pass filter
    applyLowPassFilter(audio, 4000.0f, 0.4f);

    // Heavy dynamic range compression
    applyDynamicRangeCompression(audio, -15.0f, 8.0f);

    // Significant bit depth reduction
    applyBitDepthReduction(audio, 12.0f);

    // Convert to mono if stereo
    if (channels == ChannelLayout::STEREO) {
        convertToMono(audio);
    }
}

void LODGen::applyUltraLowQualityReduction(std::vector<float>& audio, SampleRate sampleRate,
                                          BitDepth bitDepth, ChannelLayout channels) {
    // Ultra low quality: maximum reduction
    // Very aggressive low-pass filter
    applyLowPassFilter(audio, 2000.0f, 0.2f);

    // Heavy compression
    applyDynamicRangeCompression(audio, -10.0f, 12.0f);

    // Maximum bit depth reduction
    applyBitDepthReduction(audio, 8.0f);

    // Convert to mono
    convertToMono(audio);

    // Downsample
    downsample(audio, 2);
}

// Audio Processing Functions

// RBJ low-pass, applied independently to every interleaved channel.
void LODGen::applyLowPassFilter(std::vector<float>& audio, float cutoffFreq, float resonance) {
    const float sr = static_cast<float>(m_workingSampleRate);
    const float cutoff = std::clamp(cutoffFreq, 10.0f, sr * 0.49f);
    float omega = kTwoPi * cutoff / sr;
    float alpha = std::sin(omega) / (2.0f * std::max(resonance, 0.05f));

    float b0 = (1.0f - std::cos(omega)) / 2.0f;
    float b1 = 1.0f - std::cos(omega);
    float b2 = (1.0f - std::cos(omega)) / 2.0f;
    float a1 = -2.0f * std::cos(omega);
    float a2 = 1.0f - alpha;

    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm; b1 /= norm; b2 /= norm; a1 /= norm; a2 /= norm;

    const uint32_t channels = std::max<uint32_t>(1, m_workingChannels);
    for (uint32_t c = 0; c < channels; ++c) {
        float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;
        for (size_t i = c; i < audio.size(); i += channels) {
            const float sample = audio[i];
            float output = b0 * sample + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
            x2 = x1; x1 = sample; y2 = y1; y1 = output;
            audio[i] = output;
        }
    }
}

// Feed-forward compressor; threshold in dBFS.
void LODGen::applyDynamicRangeCompression(std::vector<float>& audio, float threshold, float ratio) {
    float envelope = 1.0f;
    const float sr = static_cast<float>(m_workingSampleRate);
    const float attackCoeff = std::exp(-1.0f / (0.003f * sr));
    const float releaseCoeff = std::exp(-1.0f / (0.25f * sr));

    for (float& sample : audio) {
        const float levelDb = 20.0f * std::log10(std::abs(sample) + 1e-9f);

        // Calculate gain reduction
        float gainReduction = 1.0f;
        if (levelDb > threshold && ratio > 1.0f) {
            float overThreshold = levelDb - threshold;
            float gainReductionDb = overThreshold * (1.0f - 1.0f / ratio);
            gainReduction = std::pow(10.0f, -gainReductionDb / 20.0f);
        }

        if (gainReduction < envelope) {
            envelope = attackCoeff * envelope + (1.0f - attackCoeff) * gainReduction;
        } else {
            envelope = releaseCoeff * envelope + (1.0f - releaseCoeff) * gainReduction;
        }

        sample *= envelope;
    }
}

// Quantises [-1, 1] samples to the given number of bits.
void LODGen::applyBitDepthReduction(std::vector<float>& audio, float effectiveBits) {
    const float levels = std::pow(2.0f, std::clamp(effectiveBits, 2.0f, 31.0f) - 1.0f) - 1.0f;

    for (float& sample : audio) {
        sample = std::round(std::clamp(sample, -1.0f, 1.0f) * levels) / levels;
    }
}

void LODGen::maintainStereoWidth(std::vector<float>& audio) {
    if (m_workingChannels != 2) return;
    // Mid/side round trip: re-centres the image without changing its width
    for (size_t i = 0; i + 1 < audio.size(); i += 2) {
        float left = audio[i];
        float right = audio[i + 1];

        float mid = (left + right) * 0.5f;
        float side = (left - right) * 0.5f;

        audio[i] = mid + side;
        audio[i + 1] = mid - side;
    }
}

void LODGen::reduceStereoWidth(std::vector<float>& audio, float widthFactor) {
    if (m_workingChannels != 2) return;
    for (size_t i = 0; i + 1 < audio.size(); i += 2) {
        float left = audio[i];
        float right = audio[i + 1];

        // Mid-side processing
        float mid = (left + right) * 0.5f;
        float side = (left - right) * 0.5f;

        // Reduce side signal
        side *= widthFactor;

        audio[i] = mid + side;
        audio[i + 1] = mid - side;
    }
}

void LODGen::convertToMono(std::vector<float>& audio) {
    if (m_workingChannels <= 1) return;
    audio = FileIO::convertChannels(audio, m_workingChannels, 1);
    m_workingChannels = 1;
}

// Decimates by an integer factor (frame-wise); callers band-limit beforehand.
void LODGen::downsample(std::vector<float>& audio, int factor) {
    if (factor <= 1) return;
    const uint32_t channels = std::max<uint32_t>(1, m_workingChannels);
    const size_t frames = audio.size() / channels;
    std::vector<float> downsampledAudio;
    downsampledAudio.reserve((frames / factor + 1) * channels);

    for (size_t f = 0; f < frames; f += static_cast<size_t>(factor)) {
        for (uint32_t c = 0; c < channels; ++c) downsampledAudio.push_back(audio[f * channels + c]);
    }

    audio = std::move(downsampledAudio);
    m_workingSampleRate = std::max<uint32_t>(1, m_workingSampleRate / static_cast<uint32_t>(factor));
}

// Reference signal (5 s stereo chord with light noise, deterministic)
std::vector<float> LODGen::generateTestAudio() {
    std::vector<float> audioData;
    size_t numSamples = 44100 * 5; // 5 seconds at 44.1kHz
    size_t numChannels = 2; // Stereo
    std::mt19937 rng(1234u);
    std::uniform_real_distribution<float> noise(-0.5f, 0.5f);

    audioData.resize(numSamples * numChannels);

    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / 44100.0f;

        // Generate complex test signal
        float frequency1 = 440.0f; // A4
        float frequency2 = 880.0f; // A5
        float frequency3 = 1320.0f; // E6

        float sample1 = 0.3f * std::sin(kTwoPi * frequency1 * time);
        float sample2 = 0.2f * std::sin(kTwoPi * frequency2 * time);
        float sample3 = 0.1f * std::sin(kTwoPi * frequency3 * time);

        float leftSample = sample1 + sample2 + sample3;
        float rightSample = sample1 + sample2 * 0.8f + sample3 * 0.6f; // Stereo separation

        // Add some noise for realism
        leftSample += noise(rng) * 0.05f;
        rightSample += noise(rng) * 0.05f;

        audioData[i * 2] = leftSample;
        audioData[i * 2 + 1] = rightSample;
    }

    return audioData;
}

// Quality calculation functions
float LODGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
}

float LODGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float LODGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float LODGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void LODGen::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 10);
}

void LODGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = std::clamp(factor, 1, 8);
}

void LODGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void LODGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void LODGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 16);
}

// Error Handling
std::string LODGen::getLastError() const {
    return m_lastError;
}

void LODGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float LODGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech
