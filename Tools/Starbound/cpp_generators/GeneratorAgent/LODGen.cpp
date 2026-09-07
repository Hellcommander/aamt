#include "LODGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;

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
        
        // Generate test audio data for LOD processing
        std::vector<float> originalAudio = generateTestAudio();
        
        // Process LOD levels
        std::vector<std::vector<float>> lodBuffers;
        std::vector<LODLevel> lodLevels;
        std::vector<SampleRate> lodSampleRates;
        std::vector<BitDepth> lodBitDepths;
        std::vector<ChannelLayout> lodChannels;
        
        for (size_t i = 0; i < params.lodLevels.size(); ++i) {
            LODLevel level = params.lodLevels[i];
            SampleRate sampleRate = i < params.lodSampleRates.size() ? params.lodSampleRates[i] : SampleRate::SR_44100;
            BitDepth bitDepth = i < params.lodBitDepths.size() ? params.lodBitDepths[i] : BitDepth::BD_16;
            ChannelLayout channels = i < params.lodChannels.size() ? params.lodChannels[i] : ChannelLayout::STEREO;
            
            std::vector<float> lodBuffer = generateLODLevel(originalAudio, level, sampleRate, bitDepth, channels);
            lodBuffers.push_back(lodBuffer);
            lodLevels.push_back(level);
            lodSampleRates.push_back(sampleRate);
            lodBitDepths.push_back(bitDepth);
            lodChannels.push_back(channels);
        }
        
        // Set the LOD buffers
        bundle.lodBuffers = lodBuffers;
        bundle.lodLevels = lodLevels;
        bundle.lodSampleRates = lodSampleRates;
        bundle.lodBitDepths = lodBitDepths;
        bundle.lodChannels = lodChannels;
        
        // Use the highest quality as the main buffer
        bundle.buffer = lodBuffers.empty() ? originalAudio : lodBuffers[0];
        bundle.meta.duration = static_cast<float>(bundle.buffer.size()) / (static_cast<uint32_t>(lodSampleRates[0]) * static_cast<uint32_t>(lodChannels[0]));
        
        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
        bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// LOD Level Generation
std::vector<float> LODGen::generateLODLevel(const std::vector<float>& originalAudio, LODLevel level, 
                                           SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels) {
    std::vector<float> lodAudio = originalAudio;
    
    // Apply quality reduction based on LOD level
    switch (level) {
        case LODLevel::HIGH:
            // Minimal quality reduction
            applyHighQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::MEDIUM:
            // Moderate quality reduction
            applyMediumQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::LOW:
            // Significant quality reduction
            applyLowQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
        case LODLevel::ULTRA_LOW:
            // Maximum quality reduction
            applyUltraLowQualityReduction(lodAudio, sampleRate, bitDepth, channels);
            break;
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
void LODGen::applyLowPassFilter(std::vector<float>& audio, float cutoffFreq, float resonance) {
    // Simple IIR low-pass filter
    float omega = TWO_PI * cutoffFreq / 44100.0f; // Assume 44.1kHz
    float alpha = std::sin(omega) / (2.0f * resonance);
    
    float b0 = (1.0f - std::cos(omega)) / 2.0f;
    float b1 = 1.0f - std::cos(omega);
    float b2 = (1.0f - std::cos(omega)) / 2.0f;
    float a1 = -2.0f * std::cos(omega);
    float a2 = 1.0f - alpha;
    
    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm; b1 /= norm; b2 /= norm; a1 /= norm; a2 /= norm;
    
    // Apply filter
    float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;
    for (float& sample : audio) {
        float output = b0 * sample + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = sample; y2 = y1; y1 = output;
        sample = output;
    }
}

void LODGen::applyDynamicRangeCompression(std::vector<float>& audio, float threshold, float ratio) {
    float envelope = 0.0f;
    
    for (float& sample : audio) {
        float inputLevel = std::abs(sample);
        
        // Calculate gain reduction
        float gainReduction = 1.0f;
        if (inputLevel > threshold) {
            float overThreshold = inputLevel - threshold;
            float gainReductionDb = overThreshold * (1.0f - 1.0f / ratio);
            gainReduction = std::pow(10.0f, -gainReductionDb / 20.0f);
        }
        
        // Apply attack/release
        float attackCoeff = std::exp(-1.0f / (0.003f * 44100.0f));
        float releaseCoeff = std::exp(-1.0f / (0.25f * 44100.0f));
        
        if (gainReduction < envelope) {
            envelope = attackCoeff * envelope + (1.0f - attackCoeff) * gainReduction;
        } else {
            envelope = releaseCoeff * envelope + (1.0f - releaseCoeff) * gainReduction;
        }
        
        sample *= envelope;
    }
}

void LODGen::applyBitDepthReduction(std::vector<float>& audio, float effectiveBits) {
    float maxValue = std::pow(2.0f, effectiveBits - 1.0f) - 1.0f;
    float scale = maxValue / 32767.0f; // Assuming 16-bit reference
    
    for (float& sample : audio) {
        // Quantize to target bit depth
        sample = std::round(sample * scale) / scale;
    }
}

void LODGen::maintainStereoWidth(std::vector<float>& audio) {
    // Maintain stereo width by preserving mid-side balance
    for (size_t i = 0; i < audio.size(); i += 2) {
        if (i + 1 >= audio.size()) break;
        
        float left = audio[i];
        float right = audio[i + 1];
        
        // Mid-side processing to maintain width
        float mid = (left + right) * 0.5f;
        float side = (left - right) * 0.5f;
        
        // Preserve side signal
        audio[i] = mid + side;
        audio[i + 1] = mid - side;
    }
}

void LODGen::reduceStereoWidth(std::vector<float>& audio, float widthFactor) {
    for (size_t i = 0; i < audio.size(); i += 2) {
        if (i + 1 >= audio.size()) break;
        
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
    std::vector<float> monoAudio;
    monoAudio.reserve(audio.size() / 2);
    
    for (size_t i = 0; i < audio.size(); i += 2) {
        if (i + 1 >= audio.size()) break;
        
        // Average left and right channels
        float mono = (audio[i] + audio[i + 1]) * 0.5f;
        monoAudio.push_back(mono);
    }
    
    audio = monoAudio;
}

void LODGen::downsample(std::vector<float>& audio, int factor) {
    std::vector<float> downsampledAudio;
    downsampledAudio.reserve(audio.size() / factor);
    
    for (size_t i = 0; i < audio.size(); i += factor) {
        downsampledAudio.push_back(audio[i]);
    }
    
    audio = downsampledAudio;
}

// Test Audio Generation
std::vector<float> LODGen::generateTestAudio() {
    std::vector<float> audioData;
    size_t numSamples = 44100 * 5; // 5 seconds at 44.1kHz
    size_t numChannels = 2; // Stereo
    
    audioData.resize(numSamples * numChannels);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / 44100.0f;
        
        // Generate complex test signal
        float frequency1 = 440.0f; // A4
        float frequency2 = 880.0f; // A5
        float frequency3 = 1320.0f; // E6
        
        float sample1 = 0.3f * std::sin(TWO_PI * frequency1 * time);
        float sample2 = 0.2f * std::sin(TWO_PI * frequency2 * time);
        float sample3 = 0.1f * std::sin(TWO_PI * frequency3 * time);
        
        float leftSample = sample1 + sample2 + sample3;
        float rightSample = sample1 + sample2 * 0.8f + sample3 * 0.6f; // Stereo separation
        
        // Add some noise for realism
        leftSample += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * 0.05f;
        rightSample += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * 0.05f;
        
        audioData[i * 2] = leftSample;
        audioData[i * 2 + 1] = rightSample;
    }
    
    return audioData;
}

// Quality calculation functions
float LODGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
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
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float LODGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void LODGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void LODGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void LODGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void LODGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void LODGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
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
