#include "EffectGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;

// EffectGen Implementation
EffectGen::EffectGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize processors with default sample rate
    uint32_t defaultSampleRate = 44100;
    m_reverbProcessor = std::make_unique<ReverbProcessor>(defaultSampleRate);
    m_delayProcessor = std::make_unique<DelayProcessor>(defaultSampleRate);
    m_chorusProcessor = std::make_unique<ChorusProcessor>(defaultSampleRate);
    m_distortionProcessor = std::make_unique<DistortionProcessor>();
    m_compressorProcessor = std::make_unique<CompressorProcessor>();
    m_equalizerProcessor = std::make_unique<EqualizerProcessor>(defaultSampleRate);
    m_filterProcessor = std::make_unique<FilterProcessor>(defaultSampleRate);
}

EffectGen::~EffectGen() = default;

AudioBundle EffectGen::process(const EffectParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "effect_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f; // Will be calculated
        bundle.meta.loop = false;
        
        // Process each effect type in the chain
        std::vector<float> processedSamples;
        uint32_t sampleRate = static_cast<uint32_t>(SampleRate::SR_44100);
        
        for (const auto& effectType : params.effectTypes) {
            switch (effectType) {
                case EffectType::REVERB:
                    processedSamples = applyReverb(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::DELAY:
                    processedSamples = applyDelay(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::CHORUS:
                    processedSamples = applyChorus(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::FLANGER:
                    processedSamples = applyFlanger(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::DISTORTION:
                    processedSamples = applyDistortion(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::COMPRESSOR:
                    processedSamples = applyCompressor(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::EQUALIZER:
                    processedSamples = applyEqualizer(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
                case EffectType::FILTER:
                    processedSamples = applyFilter(processedSamples.empty() ? std::vector<float>(1024, 0.0f) : processedSamples, params, sampleRate);
                    break;
            }
        }
        
        // Set the processed samples
        bundle.buffer = processedSamples;
        bundle.meta.duration = static_cast<float>(processedSamples.size()) / sampleRate;
        
        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(processedSamples);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(processedSamples);
        bundle.quality.dynamicRange = calculateDynamicRange(processedSamples);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(processedSamples);
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Reverb Implementation
std::vector<float> EffectGen::applyReverb(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    const auto& reverb = params.reverb;
    return m_reverbProcessor->process(samples, reverb.roomSize, reverb.damping, 
                                    reverb.wetLevel, reverb.dryLevel, reverb.width);
}

// Delay Implementation
std::vector<float> EffectGen::applyDelay(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    const auto& delay = params.delay;
    return m_delayProcessor->process(samples, delay.delayTime, delay.feedback, delay.wetLevel);
}

// Chorus Implementation
std::vector<float> EffectGen::applyChorus(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    // Use chorus processor with typical chorus parameters
    float rate = 0.5f;  // Hz
    float depth = 0.002f; // seconds
    float feedback = 0.3f;
    
    return m_chorusProcessor->process(samples, rate, depth, feedback);
}

// Flanger Implementation
std::vector<float> EffectGen::applyFlanger(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    // Flanger is similar to chorus but with different parameters
    float rate = 0.2f;  // Hz
    float depth = 0.001f; // seconds
    float feedback = 0.5f;
    
    return m_chorusProcessor->process(samples, rate, depth, feedback);
}

// Distortion Implementation
std::vector<float> EffectGen::applyDistortion(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    const auto& distortion = params.distortion;
    return m_distortionProcessor->process(samples, distortion.drive, distortion.range, distortion.blend);
}

// Compressor Implementation
std::vector<float> EffectGen::applyCompressor(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    const auto& compressor = params.compressor;
    return m_compressorProcessor->process(samples, compressor.threshold, compressor.ratio, 
                                        compressor.attack, compressor.release);
}

// Equalizer Implementation
std::vector<float> EffectGen::applyEqualizer(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    // Create frequency bands for equalization
    std::vector<float> frequencies = {60.0f, 250.0f, 1000.0f, 4000.0f, 16000.0f};
    std::vector<float> gains = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f}; // Flat response
    
    return m_equalizerProcessor->process(samples, frequencies, gains);
}

// Filter Implementation
std::vector<float> EffectGen::applyFilter(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;
    
    // Apply low-pass filter
    float cutoffFrequency = 2000.0f;
    float resonance = 0.5f;
    float filterType = 0.0f; // Low-pass
    
    return m_filterProcessor->process(samples, cutoffFrequency, resonance, filterType);
}

// Quality Settings
void EffectGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void EffectGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void EffectGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void EffectGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void EffectGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string EffectGen::getLastError() const {
    return m_lastError;
}

void EffectGen::clearLastError() {
    m_lastError.clear();
}

// ReverbProcessor Implementation
EffectGen::ReverbProcessor::ReverbProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    // Initialize delay lines for reverb
    const size_t numDelayLines = 8;
    m_delayLines.resize(numDelayLines);
    m_feedbackGains.resize(numDelayLines);
    
    // Different delay times for natural reverb
    std::vector<float> delayTimes = {0.0297f, 0.0371f, 0.0411f, 0.0437f, 0.0055f, 0.0017f, 0.0087f, 0.0113f};
    
    for (size_t i = 0; i < numDelayLines; ++i) {
        size_t delaySamples = static_cast<size_t>(delayTimes[i] * sampleRate);
        m_delayLines[i].resize(delaySamples, 0.0f);
        m_feedbackGains[i] = 0.6f + (i * 0.05f); // Varying feedback
    }
}

std::vector<float> EffectGen::ReverbProcessor::process(const std::vector<float>& input, float roomSize, float damping, 
                                                      float wetLevel, float dryLevel, float width) {
    std::vector<float> output(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        float reverbSample = 0.0f;
        
        // Process through all delay lines
        for (size_t j = 0; j < m_delayLines.size(); ++j) {
            auto& delayLine = m_delayLines[j];
            float feedback = m_feedbackGains[j] * roomSize;
            
            // Get delayed sample
            float delayedSample = delayLine[0];
            
            // Apply damping
            delayedSample *= (1.0f - damping);
            
            // Add to reverb output
            reverbSample += delayedSample;
            
            // Update delay line
            delayLine.erase(delayLine.begin());
            delayLine.push_back(inputSample + delayedSample * feedback);
        }
        
        // Mix dry and wet signals
        output[i] = inputSample * dryLevel + reverbSample * wetLevel;
    }
    
    return output;
}

// DelayProcessor Implementation
EffectGen::DelayProcessor::DelayProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    // Initialize delay buffer
    m_delayBuffer.resize(static_cast<size_t>(sampleRate * 2.0f), 0.0f); // 2 second max delay
}

std::vector<float> EffectGen::DelayProcessor::process(const std::vector<float>& input, float delayTime, float feedback, float mix) {
    std::vector<float> output(input.size());
    size_t delaySamples = static_cast<size_t>(delayTime * m_sampleRate);
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Get delayed sample
        size_t readIndex = (i + m_delayBuffer.size() - delaySamples) % m_delayBuffer.size();
        float delayedSample = m_delayBuffer[readIndex];
        
        // Mix input and delayed signal
        output[i] = inputSample * (1.0f - mix) + delayedSample * mix;
        
        // Update delay buffer
        m_delayBuffer[i % m_delayBuffer.size()] = inputSample + delayedSample * feedback;
    }
    
    return output;
}

// ChorusProcessor Implementation
EffectGen::ChorusProcessor::ChorusProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    // Initialize chorus with multiple delay lines
    const size_t numVoices = 3;
    m_delayBuffers.resize(numVoices);
    m_lfoPhases.resize(numVoices);
    
    for (size_t i = 0; i < numVoices; ++i) {
        m_delayBuffers[i].resize(static_cast<size_t>(sampleRate * 0.1f), 0.0f); // 100ms max delay
        m_lfoPhases[i] = static_cast<float>(i) * TWO_PI / numVoices; // Phase offset
    }
}

std::vector<float> EffectGen::ChorusProcessor::process(const std::vector<float>& input, float rate, float depth, float feedback) {
    std::vector<float> output(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        float chorusSample = 0.0f;
        
        // Process each voice
        for (size_t j = 0; j < m_delayBuffers.size(); ++j) {
            auto& delayBuffer = m_delayBuffers[j];
            float& lfoPhase = m_lfoPhases[j];
            
            // Calculate LFO
            float lfo = std::sin(lfoPhase);
            lfoPhase += TWO_PI * rate / m_sampleRate;
            if (lfoPhase >= TWO_PI) lfoPhase -= TWO_PI;
            
            // Calculate modulated delay
            float baseDelay = 0.005f; // 5ms base delay
            float modulatedDelay = baseDelay + depth * lfo;
            size_t delaySamples = static_cast<size_t>(modulatedDelay * m_sampleRate);
            
            // Get delayed sample
            size_t readIndex = (i + delayBuffer.size() - delaySamples) % delayBuffer.size();
            float delayedSample = delayBuffer[readIndex];
            
            // Add to chorus output
            chorusSample += delayedSample;
            
            // Update delay buffer
            delayBuffer[i % delayBuffer.size()] = inputSample + delayedSample * feedback;
        }
        
        // Mix input and chorus
        output[i] = inputSample + chorusSample * 0.5f;
    }
    
    return output;
}

// DistortionProcessor Implementation
EffectGen::DistortionProcessor::DistortionProcessor() = default;

std::vector<float> EffectGen::DistortionProcessor::process(const std::vector<float>& input, float drive, float range, float blend) {
    std::vector<float> output(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];
        
        // Apply drive
        sample *= drive;
        
        // Apply distortion
        float distorted = softClip(sample, range);
        
        // Blend original and distorted
        output[i] = sample * (1.0f - blend) + distorted * blend;
    }
    
    return output;
}

float EffectGen::DistortionProcessor::softClip(float sample, float drive) {
    return std::tanh(sample * drive) / std::tanh(drive);
}

float EffectGen::DistortionProcessor::hardClip(float sample, float threshold) {
    return clamp(sample, -threshold, threshold);
}

// CompressorProcessor Implementation
EffectGen::CompressorProcessor::CompressorProcessor() : m_envelope(0.0f) {}

std::vector<float> EffectGen::CompressorProcessor::process(const std::vector<float>& input, float threshold, float ratio, 
                                                         float attack, float release) {
    std::vector<float> output(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];
        float inputLevel = std::abs(sample);
        
        // Calculate gain reduction
        float gainReduction = calculateGain(inputLevel, threshold, ratio);
        
        // Apply attack/release
        float attackCoeff = std::exp(-1.0f / (attack * 44100.0f));
        float releaseCoeff = std::exp(-1.0f / (release * 44100.0f));
        
        if (gainReduction < m_envelope) {
            m_envelope = attackCoeff * m_envelope + (1.0f - attackCoeff) * gainReduction;
        } else {
            m_envelope = releaseCoeff * m_envelope + (1.0f - releaseCoeff) * gainReduction;
        }
        
        output[i] = sample * m_envelope;
    }
    
    return output;
}

float EffectGen::CompressorProcessor::calculateGain(float inputLevel, float threshold, float ratio) {
    if (inputLevel <= threshold) {
        return 1.0f;
    }
    
    float overThreshold = inputLevel - threshold;
    float gainReduction = overThreshold * (1.0f - 1.0f / ratio);
    return std::pow(10.0f, -gainReduction / 20.0f);
}

// EqualizerProcessor Implementation
EffectGen::EqualizerProcessor::EqualizerProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    // Initialize with default filters
    m_filters.resize(5); // 5-band equalizer
    for (auto& filter : m_filters) {
        filter = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    }
}

std::vector<float> EffectGen::EqualizerProcessor::process(const std::vector<float>& input, const std::vector<float>& frequencies, 
                                                        const std::vector<float>& gains) {
    std::vector<float> output(input.size());
    
    // Create filters for each frequency band
    for (size_t i = 0; i < frequencies.size() && i < gains.size(); ++i) {
        if (i < m_filters.size()) {
            m_filters[i] = createPeakFilter(frequencies[i], gains[i], 1.0f);
        }
    }
    
    // Process each sample through all filters
    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];
        
        for (const auto& filter : m_filters) {
            sample = processBiquad(filter, sample);
        }
        
        output[i] = sample;
    }
    
    return output;
}

EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createLowShelfFilter(float frequency, float gain, float q) {
    BiquadFilter filter = {};
    // Implementation would calculate biquad coefficients for low shelf
    return filter;
}

EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createHighShelfFilter(float frequency, float gain, float q) {
    BiquadFilter filter = {};
    // Implementation would calculate biquad coefficients for high shelf
    return filter;
}

EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createPeakFilter(float frequency, float gain, float q) {
    BiquadFilter filter = {};
    // Implementation would calculate biquad coefficients for peak filter
    return filter;
}

float EffectGen::EqualizerProcessor::processBiquad(const BiquadFilter& filter, float input) {
    float output = filter.b0 * input + filter.b1 * filter.x1 + filter.b2 * filter.x2
                   - filter.a1 * filter.y1 - filter.a2 * filter.y2;
    
    // Update state
    filter.x2 = filter.x1;
    filter.x1 = input;
    filter.y2 = filter.y1;
    filter.y1 = output;
    
    return output;
}

// FilterProcessor Implementation
EffectGen::FilterProcessor::FilterProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    m_state = {0.0f, 0.0f, 0.0f, 0.0f};
}

std::vector<float> EffectGen::FilterProcessor::process(const std::vector<float>& input, float cutoffFrequency, 
                                                     float resonance, float filterType) {
    std::vector<float> output(input.size());
    
    // Calculate filter coefficients
    float b0, b1, b2, a1, a2;
    calculateCoefficients(cutoffFrequency, resonance, filterType, b0, b1, b2, a1, a2);
    
    // Process each sample
    for (size_t i = 0; i < input.size(); ++i) {
        output[i] = processSample(input[i], b0, b1, b2, a1, a2);
    }
    
    return output;
}

void EffectGen::FilterProcessor::calculateCoefficients(float cutoff, float resonance, float filterType, 
                                                    float& b0, float& b1, float& b2, float& a1, float& a2) {
    // Simple low-pass filter implementation
    float omega = TWO_PI * cutoff / m_sampleRate;
    float alpha = std::sin(omega) / (2.0f * resonance);
    
    b0 = (1.0f - std::cos(omega)) / 2.0f;
    b1 = 1.0f - std::cos(omega);
    b2 = (1.0f - std::cos(omega)) / 2.0f;
    a1 = -2.0f * std::cos(omega);
    a2 = 1.0f - alpha;
    
    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm;
    b1 /= norm;
    b2 /= norm;
    a1 /= norm;
    a2 /= norm;
}

float EffectGen::FilterProcessor::processSample(float input, float b0, float b1, float b2, float a1, float a2) {
    float output = b0 * input + b1 * m_state.x1 + b2 * m_state.x2
                   - a1 * m_state.y1 - a2 * m_state.y2;
    
    // Update state
    m_state.x2 = m_state.x1;
    m_state.x1 = input;
    m_state.y2 = m_state.y1;
    m_state.y1 = output;
    
    return output;
}

// Utility Functions
float EffectGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

float EffectGen::lerp(float a, float b, float t) {
    return a + (b - a) * t;
}

float EffectGen::smoothstep(float edge0, float edge1, float x) {
    float t = clamp((x - edge0) / (edge1 - edge0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

std::vector<float> EffectGen::mixSignals(const std::vector<float>& dry, const std::vector<float>& wet, float mix) {
    std::vector<float> output(dry.size());
    for (size_t i = 0; i < dry.size(); ++i) {
        output[i] = dry[i] * (1.0f - mix) + wet[i] * mix;
    }
    return output;
}

// Quality calculation functions
float EffectGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float EffectGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float EffectGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float EffectGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

} // namespace Audio
} // namespace MagiTech 
