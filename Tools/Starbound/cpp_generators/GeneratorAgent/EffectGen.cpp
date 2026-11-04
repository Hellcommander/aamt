#include "EffectGen.hpp"
#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace MagiTech {
namespace Audio {

namespace {

constexpr float kPi = 3.14159265359f;
constexpr float kTwoPi = 2.0f * kPi;

// Reads a numeric effect setting from EffectParams::settings (float/double/int), or a default.
float settingOr(const EffectParams& params, const std::string& key, float fallback) {
    auto it = params.settings.find(key);
    if (it == params.settings.end()) return fallback;
    const std::any& v = it->second;
    if (const float* f = std::any_cast<float>(&v)) return *f;
    if (const double* d = std::any_cast<double>(&v)) return static_cast<float>(*d);
    if (const int* i = std::any_cast<int>(&v)) return static_cast<float>(*i);
    return fallback;
}

std::vector<float> settingVectorOr(const EffectParams& params, const std::string& key, std::vector<float> fallback) {
    auto it = params.settings.find(key);
    if (it == params.settings.end()) return fallback;
    if (const auto* v = std::any_cast<std::vector<float>>(&it->second)) return *v;
    return fallback;
}

} // namespace

// EffectGen Implementation
EffectGen::EffectGen()
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {

    // Initialize processors with default sample rate
    prepare(44100);
}

EffectGen::~EffectGen() = default;

void EffectGen::prepare(uint32_t sampleRate) {
    if (sampleRate == 0) sampleRate = 44100;
    if (sampleRate == m_sampleRate && m_reverbProcessor) return;
    m_sampleRate = sampleRate;
    m_reverbProcessor = std::make_unique<ReverbProcessor>(sampleRate);
    m_delayProcessor = std::make_unique<DelayProcessor>(sampleRate);
    m_chorusProcessor = std::make_unique<ChorusProcessor>(sampleRate);
    m_distortionProcessor = std::make_unique<DistortionProcessor>();
    m_compressorProcessor = std::make_unique<CompressorProcessor>(sampleRate);
    m_equalizerProcessor = std::make_unique<EqualizerProcessor>(sampleRate);
    m_filterProcessor = std::make_unique<FilterProcessor>(sampleRate);
}

bool EffectGen::effectTypeFromString(const std::string& name, EffectType& out) {
    std::string n = name;
    std::transform(n.begin(), n.end(), n.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (n == "reverb") out = EffectType::REVERB;
    else if (n == "delay" || n == "echo") out = EffectType::DELAY;
    else if (n == "chorus") out = EffectType::CHORUS;
    else if (n == "flanger") out = EffectType::FLANGER;
    else if (n == "distortion" || n == "overdrive") out = EffectType::DISTORTION;
    else if (n == "compressor" || n == "compression") out = EffectType::COMPRESSOR;
    else if (n == "equalizer" || n == "eq") out = EffectType::EQUALIZER;
    else if (n == "filter" || n == "lowpass") out = EffectType::FILTER;
    else return false;
    return true;
}

std::vector<EffectType> EffectGen::resolveChain(const EffectParams& params) {
    if (!params.effectTypes.empty()) return params.effectTypes;
    std::vector<EffectType> chain;
    for (const auto& name : params.chain) {
        EffectType type;
        if (effectTypeFromString(name, type)) chain.push_back(type);
    }
    return chain;
}

std::vector<float> EffectGen::processChain(const std::vector<float>& samples, const EffectParams& params) {
    const uint32_t sampleRate = params.sampleRate ? params.sampleRate : 44100;
    prepare(sampleRate);

    std::vector<float> processed = samples;
    for (const auto& effectType : resolveChain(params)) {
        switch (effectType) {
            case EffectType::REVERB: processed = applyReverb(processed, params, sampleRate); break;
            case EffectType::DELAY: processed = applyDelay(processed, params, sampleRate); break;
            case EffectType::CHORUS: processed = applyChorus(processed, params, sampleRate); break;
            case EffectType::FLANGER: processed = applyFlanger(processed, params, sampleRate); break;
            case EffectType::DISTORTION: processed = applyDistortion(processed, params, sampleRate); break;
            case EffectType::COMPRESSOR: processed = applyCompressor(processed, params, sampleRate); break;
            case EffectType::EQUALIZER: processed = applyEqualizer(processed, params, sampleRate); break;
            case EffectType::FILTER: processed = applyFilter(processed, params, sampleRate); break;
        }
    }
    return processed;
}

AudioBundle EffectGen::process(const EffectParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "effect_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f; // Will be calculated
        bundle.meta.loop = false;

        const uint32_t sampleRate = params.sampleRate ? params.sampleRate : 44100;

        // Input: the supplied audio, or a unit impulse (renders the impulse response).
        std::vector<float> input = params.inputBuffer;
        if (input.empty()) {
            input.assign(sampleRate, 0.0f);
            input[0] = 1.0f;
        }

        std::vector<float> processedSamples = processChain(input, params);

        // Set the processed samples
        bundle.buffer = processedSamples;
        bundle.meta.duration = static_cast<float>(processedSamples.size()) / sampleRate;
        bundle.meta.creationTime = std::chrono::system_clock::now();
        bundle.creationTime = bundle.meta.creationTime;

        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(processedSamples);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(processedSamples);
        bundle.quality.dynamicRange = calculateDynamicRange(processedSamples);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(processedSamples);
        bundle.meta.quality = bundle.quality;

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

    // Typical chorus parameters, overridable through EffectParams::settings
    float rate = settingOr(params, "chorusRate", 0.5f);       // Hz
    float depth = settingOr(params, "chorusDepth", 0.002f);   // seconds
    float feedback = settingOr(params, "chorusFeedback", 0.3f);

    return m_chorusProcessor->process(samples, rate, depth, feedback);
}

// Flanger Implementation
std::vector<float> EffectGen::applyFlanger(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;

    // Flanger is similar to chorus but with different parameters
    float rate = settingOr(params, "flangerRate", 0.2f);      // Hz
    float depth = settingOr(params, "flangerDepth", 0.001f);  // seconds
    float feedback = settingOr(params, "flangerFeedback", 0.5f);

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

    // 5-band equalizer; flat unless gains are supplied in EffectParams::settings["eqGains"] (dB)
    std::vector<float> frequencies = settingVectorOr(params, "eqFrequencies", {60.0f, 250.0f, 1000.0f, 4000.0f, 16000.0f});
    std::vector<float> gains = settingVectorOr(params, "eqGains", std::vector<float>(frequencies.size(), 0.0f));
    std::vector<float> qFactors = settingVectorOr(params, "eqQ", std::vector<float>(frequencies.size(), 1.0f));

    return m_equalizerProcessor->process(samples, frequencies, gains, qFactors);
}

// Filter Implementation
std::vector<float> EffectGen::applyFilter(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate) {
    if (samples.empty()) return samples;

    float cutoffFrequency = settingOr(params, "filterCutoff", 2000.0f);
    float resonance = settingOr(params, "filterResonance", 0.7071f);
    float filterType = settingOr(params, "filterType", 0.0f); // 0 = low-pass

    return m_filterProcessor->process(samples, cutoffFrequency, resonance, filterType);
}

// Quality Settings
void EffectGen::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 10);
}

void EffectGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = std::clamp(factor, 1, 8);
}

void EffectGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void EffectGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void EffectGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 16);
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
        size_t delaySamples = std::max<size_t>(1, static_cast<size_t>(delayTimes[i] * sampleRate));
        m_delayLines[i].resize(delaySamples, 0.0f);
        m_feedbackGains[i] = 0.6f + (i * 0.05f); // Varying feedback
    }
}

std::vector<float> EffectGen::ReverbProcessor::process(const std::vector<float>& input, float roomSize, float damping,
                                                      float wetLevel, float dryLevel, float width) {
    std::vector<float> output(input.size());
    const float lineGain = 1.0f / static_cast<float>(m_delayLines.size());

    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        float reverbSample = 0.0f;

        // Process through all delay lines
        for (size_t j = 0; j < m_delayLines.size(); ++j) {
            auto& delayLine = m_delayLines[j];
            float feedback = std::min(0.98f, m_feedbackGains[j] * roomSize);

            // Get delayed sample
            float delayedSample = delayLine.front();

            // Apply damping
            delayedSample *= (1.0f - damping);

            // Add to reverb output (alternate lines feed the side signal for width)
            reverbSample += ((j & 1u) && width < 1.0f ? width : 1.0f) * delayedSample * lineGain;

            // Update delay line
            delayLine.pop_front();
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
    const size_t bufferSize = m_delayBuffer.size();
    size_t delaySamples = std::clamp<size_t>(static_cast<size_t>(delayTime * m_sampleRate), 1, bufferSize - 1);

    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];

        // Get delayed sample
        size_t readIndex = (m_writeIndex + bufferSize - delaySamples) % bufferSize;
        float delayedSample = m_delayBuffer[readIndex];

        // Mix input and delayed signal
        output[i] = inputSample * (1.0f - mix) + delayedSample * mix;

        // Update delay buffer
        m_delayBuffer[m_writeIndex] = inputSample + delayedSample * feedback;
        m_writeIndex = (m_writeIndex + 1) % bufferSize;
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
        m_lfoPhases[i] = static_cast<float>(i) * kTwoPi / numVoices; // Phase offset
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
            const size_t bufferSize = delayBuffer.size();

            // Calculate LFO
            float lfo = std::sin(lfoPhase);
            lfoPhase += kTwoPi * rate / m_sampleRate;
            if (lfoPhase >= kTwoPi) lfoPhase -= kTwoPi;

            // Calculate modulated delay
            float baseDelay = 0.005f; // 5ms base delay
            float modulatedDelay = std::max(0.0f, baseDelay + depth * lfo);
            size_t delaySamples = std::clamp<size_t>(static_cast<size_t>(modulatedDelay * m_sampleRate), 1, bufferSize - 1);

            // Get delayed sample
            size_t readIndex = (m_writeIndex + bufferSize - delaySamples) % bufferSize;
            float delayedSample = delayBuffer[readIndex];

            // Add to chorus output
            chorusSample += delayedSample / static_cast<float>(m_delayBuffers.size());

            // Update delay buffer
            delayBuffer[m_writeIndex % bufferSize] = inputSample + delayedSample * feedback;
        }
        m_writeIndex = (m_writeIndex + 1) % m_delayBuffers.front().size();

        // Mix input and chorus
        output[i] = inputSample + chorusSample * 0.5f;
    }

    return output;
}

// DistortionProcessor Implementation
EffectGen::DistortionProcessor::DistortionProcessor() = default;

std::vector<float> EffectGen::DistortionProcessor::process(const std::vector<float>& input, float drive, float range, float blend) {
    std::vector<float> output(input.size());
    // "range" scales the drive (2400 = unity, as in the classic waveshaper parameterisation)
    const float shaping = std::max(0.01f, drive * range / 2400.0f * 10.0f);

    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];

        // Apply distortion
        float distorted = softClip(sample, shaping);

        // Blend original and distorted
        output[i] = sample * (1.0f - blend) + distorted * blend;
    }

    return output;
}

float EffectGen::DistortionProcessor::softClip(float sample, float drive) {
    return std::tanh(sample * drive) / std::tanh(drive);
}

float EffectGen::DistortionProcessor::hardClip(float sample, float threshold) {
    return std::clamp(sample, -threshold, threshold);
}

// CompressorProcessor Implementation
EffectGen::CompressorProcessor::CompressorProcessor(uint32_t sampleRate) : m_envelope(1.0f), m_sampleRate(sampleRate) {}

std::vector<float> EffectGen::CompressorProcessor::process(const std::vector<float>& input, float threshold, float ratio,
                                                         float attack, float release) {
    std::vector<float> output(input.size());

    // Attack/release smoothing coefficients
    const float attackCoeff = std::exp(-1.0f / (std::max(attack, 1e-5f) * m_sampleRate));
    const float releaseCoeff = std::exp(-1.0f / (std::max(release, 1e-5f) * m_sampleRate));

    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];
        float inputLevel = std::abs(sample);

        // Calculate target gain
        float targetGain = calculateGain(inputLevel, threshold, ratio);

        if (targetGain < m_envelope) {
            m_envelope = attackCoeff * m_envelope + (1.0f - attackCoeff) * targetGain;
        } else {
            m_envelope = releaseCoeff * m_envelope + (1.0f - releaseCoeff) * targetGain;
        }

        output[i] = sample * m_envelope;
    }

    return output;
}

float EffectGen::CompressorProcessor::calculateGain(float inputLevel, float threshold, float ratio) {
    const float levelDb = 20.0f * std::log10(inputLevel + 1e-9f);
    if (levelDb <= threshold || ratio <= 1.0f) {
        return 1.0f;
    }

    float overThreshold = levelDb - threshold;
    float gainReduction = overThreshold * (1.0f - 1.0f / ratio);
    return std::pow(10.0f, -gainReduction / 20.0f);
}

// EqualizerProcessor Implementation
EffectGen::EqualizerProcessor::EqualizerProcessor(uint32_t sampleRate) : m_sampleRate(sampleRate) {
    // Initialize with default (pass-through) filters
    m_filters.resize(5); // 5-band equalizer
    for (auto& filter : m_filters) {
        filter = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    }
}

std::vector<float> EffectGen::EqualizerProcessor::process(const std::vector<float>& input, const std::vector<float>& frequencies,
                                                        const std::vector<float>& gains, const std::vector<float>& qFactors) {
    std::vector<float> output(input.size());

    // Create filters for each frequency band: low shelf, peaking bands, high shelf
    const size_t bands = std::min(frequencies.size(), gains.size());
    m_filters.resize(bands);
    for (size_t i = 0; i < bands; ++i) {
        const float q = i < qFactors.size() && qFactors[i] > 0.0f ? qFactors[i] : 1.0f;
        if (i == 0 && bands > 1) {
            m_filters[i] = createLowShelfFilter(frequencies[i], gains[i], q);
        } else if (i + 1 == bands && bands > 1) {
            m_filters[i] = createHighShelfFilter(frequencies[i], gains[i], q);
        } else {
            m_filters[i] = createPeakFilter(frequencies[i], gains[i], q);
        }
    }

    // Process each sample through all filters
    for (size_t i = 0; i < input.size(); ++i) {
        float sample = input[i];

        for (auto& filter : m_filters) {
            sample = processBiquad(filter, sample);
        }

        output[i] = sample;
    }

    return output;
}

// RBJ audio-EQ-cookbook coefficient formulas (gain in dB)
EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createLowShelfFilter(float frequency, float gain, float q) {
    const float A = std::pow(10.0f, gain / 40.0f);
    const float w0 = kTwoPi * std::clamp(frequency, 10.0f, m_sampleRate * 0.49f) / m_sampleRate;
    const float alpha = std::sin(w0) / (2.0f * q);
    const float c = std::cos(w0);
    const float sqrtA2alpha = 2.0f * std::sqrt(A) * alpha;
    const float a0 = (A + 1) + (A - 1) * c + sqrtA2alpha;
    BiquadFilter filter = {};
    filter.b0 = A * ((A + 1) - (A - 1) * c + sqrtA2alpha) / a0;
    filter.b1 = 2 * A * ((A - 1) - (A + 1) * c) / a0;
    filter.b2 = A * ((A + 1) - (A - 1) * c - sqrtA2alpha) / a0;
    filter.a1 = -2 * ((A - 1) + (A + 1) * c) / a0;
    filter.a2 = ((A + 1) + (A - 1) * c - sqrtA2alpha) / a0;
    return filter;
}

EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createHighShelfFilter(float frequency, float gain, float q) {
    const float A = std::pow(10.0f, gain / 40.0f);
    const float w0 = kTwoPi * std::clamp(frequency, 10.0f, m_sampleRate * 0.49f) / m_sampleRate;
    const float alpha = std::sin(w0) / (2.0f * q);
    const float c = std::cos(w0);
    const float sqrtA2alpha = 2.0f * std::sqrt(A) * alpha;
    const float a0 = (A + 1) - (A - 1) * c + sqrtA2alpha;
    BiquadFilter filter = {};
    filter.b0 = A * ((A + 1) + (A - 1) * c + sqrtA2alpha) / a0;
    filter.b1 = -2 * A * ((A - 1) + (A + 1) * c) / a0;
    filter.b2 = A * ((A + 1) + (A - 1) * c - sqrtA2alpha) / a0;
    filter.a1 = 2 * ((A - 1) - (A + 1) * c) / a0;
    filter.a2 = ((A + 1) - (A - 1) * c - sqrtA2alpha) / a0;
    return filter;
}

EffectGen::EqualizerProcessor::BiquadFilter EffectGen::EqualizerProcessor::createPeakFilter(float frequency, float gain, float q) {
    const float A = std::pow(10.0f, gain / 40.0f);
    const float w0 = kTwoPi * std::clamp(frequency, 10.0f, m_sampleRate * 0.49f) / m_sampleRate;
    const float alpha = std::sin(w0) / (2.0f * q);
    const float c = std::cos(w0);
    const float a0 = 1 + alpha / A;
    BiquadFilter filter = {};
    filter.b0 = (1 + alpha * A) / a0;
    filter.b1 = -2 * c / a0;
    filter.b2 = (1 - alpha * A) / a0;
    filter.a1 = -2 * c / a0;
    filter.a2 = (1 - alpha / A) / a0;
    return filter;
}

float EffectGen::EqualizerProcessor::processBiquad(BiquadFilter& filter, float input) {
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
    const float omega = kTwoPi * std::clamp(cutoff, 10.0f, m_sampleRate * 0.49f) / m_sampleRate;
    const float alpha = std::sin(omega) / (2.0f * std::max(resonance, 0.05f));
    const float c = std::cos(omega);
    const int type = static_cast<int>(std::lround(filterType));

    if (type == 1) {        // high-pass
        b0 = (1.0f + c) / 2.0f;
        b1 = -(1.0f + c);
        b2 = (1.0f + c) / 2.0f;
    } else if (type == 2) { // band-pass (constant peak gain)
        b0 = alpha;
        b1 = 0.0f;
        b2 = -alpha;
    } else {                // low-pass
        b0 = (1.0f - c) / 2.0f;
        b1 = 1.0f - c;
        b2 = (1.0f - c) / 2.0f;
    }
    a1 = -2.0f * c;
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
    std::vector<float> output(std::max(dry.size(), wet.size()), 0.0f);
    for (size_t i = 0; i < output.size(); ++i) {
        const float d = i < dry.size() ? dry[i] : 0.0f;
        const float w = i < wet.size() ? wet[i] : 0.0f;
        output[i] = d * (1.0f - mix) + w * mix;
    }
    return output;
}

// Quality calculation functions
float EffectGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
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
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float EffectGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

} // namespace Audio
} // namespace MagiTech
