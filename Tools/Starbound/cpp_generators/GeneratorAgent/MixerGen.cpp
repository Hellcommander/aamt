#include "MixerGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;

// MixerGen Implementation
MixerGen::MixerGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize with default settings
    m_masterGain = 1.0f;
    m_sampleRate = 44100;
    m_bufferSize = 1024;
    m_numChannels = 2; // Stereo
}

MixerGen::~MixerGen() = default;

AudioBundle MixerGen::process(const MixerParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "mixer_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f; // Will be calculated
        bundle.meta.loop = false;
        
        // Process mixing based on parameters
        std::vector<float> mixedSamples;
        
        switch (params.mixerType) {
            case MixerType::LINEAR:
                mixedSamples = processLinearMix(params);
                break;
            case MixerType::LOGARITHMIC:
                mixedSamples = processLogarithmicMix(params);
                break;
            case MixerType::CUSTOM:
                mixedSamples = processCustomMix(params);
                break;
        }
        
        // Apply master gain and final processing
        applyMasterGain(mixedSamples, params.masterGain);
        
        // Set the mixed samples
        bundle.buffer = mixedSamples;
        bundle.meta.duration = static_cast<float>(mixedSamples.size()) / (m_sampleRate * m_numChannels);
        
        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(mixedSamples);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(mixedSamples);
        bundle.quality.dynamicRange = calculateDynamicRange(mixedSamples);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(mixedSamples);
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Linear Mixing Implementation
std::vector<float> MixerGen::processLinearMix(const MixerParams& params) {
    if (params.trackGains.empty()) {
        return std::vector<float>(m_bufferSize * m_numChannels, 0.0f);
    }
    
    std::vector<float> mixedSamples(m_bufferSize * m_numChannels, 0.0f);
    
    // Process each track
    for (size_t trackIndex = 0; trackIndex < params.trackGains.size(); ++trackIndex) {
        float trackGain = params.trackGains[trackIndex];
        
        // Generate or load track samples (placeholder for now)
        std::vector<float> trackSamples = generateTrackSamples(trackIndex, m_bufferSize);
        
        // Apply track gain and panning
        applyTrackProcessing(trackSamples, trackGain, trackIndex, params);
        
        // Mix into output
        for (size_t i = 0; i < trackSamples.size() && i < mixedSamples.size(); ++i) {
            mixedSamples[i] += trackSamples[i];
        }
    }
    
    // Apply automation curves if available
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }
    
    return mixedSamples;
}

// Logarithmic Mixing Implementation
std::vector<float> MixerGen::processLogarithmicMix(const MixerParams& params) {
    if (params.trackGains.empty()) {
        return std::vector<float>(m_bufferSize * m_numChannels, 0.0f);
    }
    
    std::vector<float> mixedSamples(m_bufferSize * m_numChannels, 0.0f);
    
    // Process each track with logarithmic scaling
    for (size_t trackIndex = 0; trackIndex < params.trackGains.size(); ++trackIndex) {
        float trackGain = params.trackGains[trackIndex];
        
        // Convert to logarithmic scale
        float logGain = trackGain > 0.0f ? std::log10(trackGain + 1.0f) : 0.0f;
        
        // Generate or load track samples
        std::vector<float> trackSamples = generateTrackSamples(trackIndex, m_bufferSize);
        
        // Apply logarithmic gain and panning
        applyTrackProcessing(trackSamples, logGain, trackIndex, params);
        
        // Mix into output
        for (size_t i = 0; i < trackSamples.size() && i < mixedSamples.size(); ++i) {
            mixedSamples[i] += trackSamples[i];
        }
    }
    
    // Apply automation curves
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }
    
    return mixedSamples;
}

// Custom Mixing Implementation
std::vector<float> MixerGen::processCustomMix(const MixerParams& params) {
    if (params.trackGains.empty()) {
        return std::vector<float>(m_bufferSize * m_numChannels, 0.0f);
    }
    
    std::vector<float> mixedSamples(m_bufferSize * m_numChannels, 0.0f);
    
    // Process each track with custom algorithms
    for (size_t trackIndex = 0; trackIndex < params.trackGains.size(); ++trackIndex) {
        float trackGain = params.trackGains[trackIndex];
        
        // Generate or load track samples
        std::vector<float> trackSamples = generateTrackSamples(trackIndex, m_bufferSize);
        
        // Apply custom processing
        applyCustomProcessing(trackSamples, trackGain, trackIndex, params);
        
        // Mix into output with custom algorithm
        for (size_t i = 0; i < trackSamples.size() && i < mixedSamples.size(); ++i) {
            // Custom mixing algorithm (e.g., RMS-based)
            float rmsMix = std::sqrt(mixedSamples[i] * mixedSamples[i] + trackSamples[i] * trackSamples[i]);
            mixedSamples[i] = rmsMix;
        }
    }
    
    // Apply automation curves
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }
    
    return mixedSamples;
}

// Track Processing
void MixerGen::applyTrackProcessing(std::vector<float>& trackSamples, float gain, size_t trackIndex, const MixerParams& params) {
    // Apply gain
    for (float& sample : trackSamples) {
        sample *= gain;
    }
    
    // Apply panning if available
    if (trackIndex < params.panPositions.size()) {
        applyPanning(trackSamples, params.panPositions[trackIndex]);
    }
    
    // Apply any track-specific effects
    applyTrackEffects(trackSamples, trackIndex, params);
}

// Panning Implementation
void MixerGen::applyPanning(std::vector<float>& samples, const glm::vec2& panPosition) {
    if (m_numChannels != 2) return; // Only stereo panning for now
    
    for (size_t i = 0; i < samples.size(); i += 2) {
        if (i + 1 >= samples.size()) break;
        
        float leftSample = samples[i];
        float rightSample = samples[i + 1];
        
        // Calculate pan coefficients
        float panLeft = 1.0f - panPosition.x;  // 0 = hard left, 1 = hard right
        float panRight = panPosition.x;
        
        // Apply panning
        samples[i] = leftSample * panLeft;
        samples[i + 1] = rightSample * panRight;
    }
}

// Automation Implementation
void MixerGen::applyAutomation(std::vector<float>& samples, const std::vector<float>& automationCurves) {
    if (automationCurves.empty()) return;
    
    size_t curveIndex = 0;
    for (size_t i = 0; i < samples.size(); ++i) {
        if (curveIndex < automationCurves.size()) {
            samples[i] *= automationCurves[curveIndex];
            curveIndex = (curveIndex + 1) % automationCurves.size();
        }
    }
}

// Track Effects
void MixerGen::applyTrackEffects(std::vector<float>& samples, size_t trackIndex, const MixerParams& params) {
    // Apply track-specific effects based on track index
    switch (trackIndex % 4) {
        case 0: // Bass track
            applyLowPassFilter(samples, 200.0f, 0.7f);
            break;
        case 1: // Mid track
            applyBandPassFilter(samples, 1000.0f, 0.5f);
            break;
        case 2: // High track
            applyHighPassFilter(samples, 2000.0f, 0.7f);
            break;
        case 3: // Effects track
            applyCompression(samples, -20.0f, 4.0f, 0.003f, 0.25f);
            break;
    }
}

// Filter Implementations
void MixerGen::applyLowPassFilter(std::vector<float>& samples, float cutoffFreq, float resonance) {
    // Simple IIR low-pass filter
    float omega = TWO_PI * cutoffFreq / m_sampleRate;
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
    for (float& sample : samples) {
        float output = b0 * sample + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = sample; y2 = y1; y1 = output;
        sample = output;
    }
}

void MixerGen::applyHighPassFilter(std::vector<float>& samples, float cutoffFreq, float resonance) {
    // Simple IIR high-pass filter
    float omega = TWO_PI * cutoffFreq / m_sampleRate;
    float alpha = std::sin(omega) / (2.0f * resonance);
    
    float b0 = (1.0f + std::cos(omega)) / 2.0f;
    float b1 = -(1.0f + std::cos(omega));
    float b2 = (1.0f + std::cos(omega)) / 2.0f;
    float a1 = -2.0f * std::cos(omega);
    float a2 = 1.0f - alpha;
    
    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm; b1 /= norm; b2 /= norm; a1 /= norm; a2 /= norm;
    
    // Apply filter
    float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;
    for (float& sample : samples) {
        float output = b0 * sample + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = sample; y2 = y1; y1 = output;
        sample = output;
    }
}

void MixerGen::applyBandPassFilter(std::vector<float>& samples, float centerFreq, float q) {
    // Simple IIR band-pass filter
    float omega = TWO_PI * centerFreq / m_sampleRate;
    float alpha = std::sin(omega) / (2.0f * q);
    
    float b0 = alpha;
    float b1 = 0.0f;
    float b2 = -alpha;
    float a1 = -2.0f * std::cos(omega);
    float a2 = 1.0f - alpha;
    
    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm; b1 /= norm; b2 /= norm; a1 /= norm; a2 /= norm;
    
    // Apply filter
    float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;
    for (float& sample : samples) {
        float output = b0 * sample + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = sample; y2 = y1; y1 = output;
        sample = output;
    }
}

// Compression Implementation
void MixerGen::applyCompression(std::vector<float>& samples, float threshold, float ratio, float attack, float release) {
    float envelope = 0.0f;
    
    for (float& sample : samples) {
        float inputLevel = std::abs(sample);
        
        // Calculate gain reduction
        float gainReduction = 1.0f;
        if (inputLevel > threshold) {
            float overThreshold = inputLevel - threshold;
            float gainReductionDb = overThreshold * (1.0f - 1.0f / ratio);
            gainReduction = std::pow(10.0f, -gainReductionDb / 20.0f);
        }
        
        // Apply attack/release
        float attackCoeff = std::exp(-1.0f / (attack * m_sampleRate));
        float releaseCoeff = std::exp(-1.0f / (release * m_sampleRate));
        
        if (gainReduction < envelope) {
            envelope = attackCoeff * envelope + (1.0f - attackCoeff) * gainReduction;
        } else {
            envelope = releaseCoeff * envelope + (1.0f - releaseCoeff) * gainReduction;
        }
        
        sample *= envelope;
    }
}

// Custom Processing
void MixerGen::applyCustomProcessing(std::vector<float>& samples, float gain, size_t trackIndex, const MixerParams& params) {
    // Apply gain
    for (float& sample : samples) {
        sample *= gain;
    }
    
    // Apply custom effects based on track type
    switch (trackIndex % 5) {
        case 0: // Drums
            applyTransientEnhancement(samples);
            break;
        case 1: // Bass
            applyHarmonicEnhancement(samples);
            break;
        case 2: // Vocals
            applyDeEsser(samples);
            break;
        case 3: // Synths
            applyStereoEnhancement(samples);
            break;
        case 4: // Effects
            applySaturation(samples);
            break;
    }
}

// Custom Effects
void MixerGen::applyTransientEnhancement(std::vector<float>& samples) {
    // Simple transient enhancement using high-pass filter
    applyHighPassFilter(samples, 5000.0f, 0.5f);
    
    // Boost transients
    for (float& sample : samples) {
        sample *= 1.2f;
    }
}

void MixerGen::applyHarmonicEnhancement(std::vector<float>& samples) {
    // Add harmonics using saturation
    for (float& sample : samples) {
        sample = std::tanh(sample * 1.5f);
    }
}

void MixerGen::applyDeEsser(std::vector<float>& samples) {
    // Simple de-esser using band-pass filter and compression
    std::vector<float> essBand = samples;
    applyBandPassFilter(essBand, 8000.0f, 2.0f);
    applyCompression(essBand, -30.0f, 8.0f, 0.001f, 0.1f);
    
    // Subtract from original
    for (size_t i = 0; i < samples.size(); ++i) {
        samples[i] -= essBand[i] * 0.3f;
    }
}

void MixerGen::applyStereoEnhancement(std::vector<float>& samples) {
    if (m_numChannels != 2) return;
    
    for (size_t i = 0; i < samples.size(); i += 2) {
        if (i + 1 >= samples.size()) break;
        
        float left = samples[i];
        float right = samples[i + 1];
        
        // Mid-side processing
        float mid = (left + right) * 0.5f;
        float side = (left - right) * 0.5f;
        
        // Enhance side signal
        side *= 1.5f;
        
        // Convert back to left-right
        samples[i] = mid + side;
        samples[i + 1] = mid - side;
    }
}

void MixerGen::applySaturation(std::vector<float>& samples) {
    for (float& sample : samples) {
        // Soft saturation
        sample = std::tanh(sample * 2.0f) / 2.0f;
    }
}

// Master Gain Application
void MixerGen::applyMasterGain(std::vector<float>& samples, float masterGain) {
    for (float& sample : samples) {
        sample *= masterGain;
    }
}

// Track Sample Generation (placeholder)
std::vector<float> MixerGen::generateTrackSamples(size_t trackIndex, size_t bufferSize) {
    std::vector<float> samples(bufferSize * m_numChannels);
    
    // Generate different content for each track
    for (size_t i = 0; i < samples.size(); ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        float frequency = 100.0f + trackIndex * 200.0f;
        
        switch (trackIndex % 4) {
            case 0: // Sine wave
                samples[i] = std::sin(TWO_PI * frequency * time) * 0.3f;
                break;
            case 1: // Square wave
                samples[i] = (std::sin(TWO_PI * frequency * time) > 0.0f ? 1.0f : -1.0f) * 0.2f;
                break;
            case 2: // Saw wave
                samples[i] = (2.0f * (frequency * time - std::floor(frequency * time + 0.5f))) * 0.15f;
                break;
            case 3: // Noise
                samples[i] = (static_cast<float>(rand()) / RAND_MAX - 0.5f) * 0.1f;
                break;
        }
    }
    
    return samples;
}

// Quality calculation functions
float MixerGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float MixerGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float MixerGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float MixerGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void MixerGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void MixerGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void MixerGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void MixerGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void MixerGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string MixerGen::getLastError() const {
    return m_lastError;
}

void MixerGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float MixerGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech 
