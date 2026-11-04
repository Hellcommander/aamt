#include "MixerGen.hpp"
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
constexpr float kHalfPi = 0.5f * kPi;

// Logarithmic (audio taper) mapping of a 0..1+ linear fader value.
float logTaper(float gain) {
    return gain > 0.0f ? std::log10(1.0f + 9.0f * gain) : 0.0f;
}
} // namespace

// MixerGen Implementation
MixerGen::MixerGen()
    : m_gpuAccelerationEnabled(false)
    , m_mixingQuality(1)
    , m_realTimeProcessing(false)
    , m_bufferSize(1024)
    , m_maxProcessingThreads(4)
    , m_lastError("")
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_masterGain(1.0f)
    , m_sampleRate(44100)
    , m_numChannels(2) {
}

MixerGen::~MixerGen() = default;

AudioBundle MixerGen::process(const MixerParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "mixer_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f; // Will be calculated
        bundle.meta.loop = false;

        m_numChannels = static_cast<uint32_t>(std::clamp(params.channels, 1, 8));
        if (params.bufferSize > 0) m_bufferSize = params.bufferSize;
        m_realTimeProcessing = params.realTimeProcessing;
        m_masterGain = params.masterGain;

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
        applyMasterProcessing(mixedSamples, params);

        // Set the mixed samples
        bundle.buffer = mixedSamples;
        bundle.meta.duration = static_cast<float>(mixedSamples.size()) / (m_sampleRate * m_numChannels);
        bundle.meta.creationTime = std::chrono::system_clock::now();
        bundle.creationTime = bundle.meta.creationTime;

        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(mixedSamples);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(mixedSamples);
        bundle.quality.dynamicRange = calculateDynamicRange(mixedSamples);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(mixedSamples);
        bundle.meta.quality = bundle.quality;

        return bundle;

    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

std::vector<float> MixerGen::mixChannels(const std::vector<std::vector<float>>& channels, const MixerParams& params) {
    m_numChannels = static_cast<uint32_t>(std::clamp(params.channels, 1, 8));
    std::vector<float> gains(channels.size(), 1.0f);
    for (size_t i = 0; i < gains.size() && i < params.trackGains.size(); ++i) gains[i] = params.trackGains[i];

    std::vector<std::vector<float>> panned = channels;
    for (size_t i = 0; i < panned.size() && i < params.panPositions.size(); ++i) {
        applyPanning(panned[i], params.panPositions[i]);
    }

    std::vector<float> mixed;
    switch (params.mixerType) {
        case MixerType::LINEAR: mixed = linearMix(panned, gains); break;
        case MixerType::LOGARITHMIC: mixed = logarithmicMix(panned, gains); break;
        case MixerType::CUSTOM: mixed = customMix(panned, params); break;
    }
    if (!params.automationCurves.empty()) {
        applyAutomation(mixed, params.automationCurves);
    }
    applyMasterProcessing(mixed, params);
    return mixed;
}

// Number of interleaved samples of each track in the current mix.
size_t MixerGen::trackLength() const {
    size_t length = 0;
    for (const auto& ch : m_inputChannels) length = std::max(length, ch.samples.size());
    if (length == 0) length = static_cast<size_t>(std::max(1, m_bufferSize)) * m_numChannels;
    return length;
}

std::vector<float> MixerGen::getTrackSamples(size_t trackIndex, size_t bufferSize) {
    if (m_inputChannels.empty()) {
        return generateTrackSamples(trackIndex, bufferSize / std::max<uint32_t>(1, m_numChannels));
    }
    std::vector<float> samples(bufferSize, 0.0f);
    if (trackIndex >= m_inputChannels.size()) return samples;

    const bool anySolo = std::any_of(m_inputChannels.begin(), m_inputChannels.end(), [](const ChannelData& c) { return c.solo; });
    const ChannelData& channel = m_inputChannels[trackIndex];
    if (channel.muted || (anySolo && !channel.solo)) return samples;

    std::copy_n(channel.samples.begin(), std::min(bufferSize, channel.samples.size()), samples.begin());
    for (float& s : samples) s *= channel.gain;
    if (channel.pan != glm::vec2(0.5f, 0.5f)) applyPanning(samples, channel.pan);
    return samples;
}

// Linear Mixing Implementation
std::vector<float> MixerGen::processLinearMix(const MixerParams& params) {
    const size_t trackCount = m_inputChannels.empty() ? params.trackGains.size() : m_inputChannels.size();
    const size_t length = trackLength();
    if (trackCount == 0) {
        return std::vector<float>(length, 0.0f);
    }

    std::vector<std::vector<float>> tracks;
    for (size_t trackIndex = 0; trackIndex < trackCount; ++trackIndex) {
        float trackGain = trackIndex < params.trackGains.size() ? params.trackGains[trackIndex] : 1.0f;
        std::vector<float> trackSamples = getTrackSamples(trackIndex, length);
        applyTrackProcessing(trackSamples, trackGain, trackIndex, params);
        tracks.push_back(std::move(trackSamples));
    }

    std::vector<float> mixedSamples = linearMix(tracks, std::vector<float>(tracks.size(), 1.0f));

    // Apply automation curves if available
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }

    return mixedSamples;
}

// Logarithmic Mixing Implementation
std::vector<float> MixerGen::processLogarithmicMix(const MixerParams& params) {
    const size_t trackCount = m_inputChannels.empty() ? params.trackGains.size() : m_inputChannels.size();
    const size_t length = trackLength();
    if (trackCount == 0) {
        return std::vector<float>(length, 0.0f);
    }

    std::vector<std::vector<float>> tracks;
    for (size_t trackIndex = 0; trackIndex < trackCount; ++trackIndex) {
        float trackGain = trackIndex < params.trackGains.size() ? params.trackGains[trackIndex] : 1.0f;

        // Convert to logarithmic scale
        float logGain = logTaper(trackGain);

        std::vector<float> trackSamples = getTrackSamples(trackIndex, length);
        applyTrackProcessing(trackSamples, logGain, trackIndex, params);
        tracks.push_back(std::move(trackSamples));
    }

    std::vector<float> mixedSamples = linearMix(tracks, std::vector<float>(tracks.size(), 1.0f));

    // Apply automation curves
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }

    return mixedSamples;
}

// Custom Mixing Implementation
std::vector<float> MixerGen::processCustomMix(const MixerParams& params) {
    const size_t trackCount = m_inputChannels.empty() ? params.trackGains.size() : m_inputChannels.size();
    const size_t length = trackLength();
    if (trackCount == 0) {
        return std::vector<float>(length, 0.0f);
    }

    std::vector<std::vector<float>> tracks;
    for (size_t trackIndex = 0; trackIndex < trackCount; ++trackIndex) {
        float trackGain = trackIndex < params.trackGains.size() ? params.trackGains[trackIndex] : 1.0f;
        std::vector<float> trackSamples = getTrackSamples(trackIndex, length);

        // Apply custom processing
        applyCustomProcessing(trackSamples, trackGain, trackIndex, params);
        tracks.push_back(std::move(trackSamples));
    }

    std::vector<float> mixedSamples = customMix(tracks, params);

    // Apply automation curves
    if (!params.automationCurves.empty()) {
        applyAutomation(mixedSamples, params.automationCurves);
    }

    return mixedSamples;
}

std::vector<float> MixerGen::linearMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains) {
    size_t length = 0;
    for (const auto& ch : channels) length = std::max(length, ch.size());
    std::vector<float> out(length, 0.0f);
    for (size_t c = 0; c < channels.size(); ++c) {
        const float g = c < gains.size() ? gains[c] : 1.0f;
        for (size_t i = 0; i < channels[c].size(); ++i) out[i] += channels[c][i] * g;
    }
    return out;
}

std::vector<float> MixerGen::logarithmicMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains) {
    std::vector<float> logGains(channels.size(), 1.0f);
    for (size_t i = 0; i < logGains.size(); ++i) logGains[i] = logTaper(i < gains.size() ? gains[i] : 1.0f);
    return linearMix(channels, logGains);
}

// Constant-power mix: the sum is normalised by sqrt(N) so the combined RMS level stays
// comparable to a single track regardless of how many tracks are summed.
std::vector<float> MixerGen::customMix(const std::vector<std::vector<float>>& channels, const MixerParams& params) {
    std::vector<float> gains(channels.size(), 1.0f);
    for (size_t i = 0; i < gains.size() && i < params.trackGains.size() && !m_inputChannels.empty(); ++i) {
        gains[i] = params.trackGains[i];
    }
    std::vector<float> out = linearMix(channels, gains);
    if (channels.size() > 1) {
        const float norm = 1.0f / std::sqrt(static_cast<float>(channels.size()));
        for (float& s : out) s *= norm;
    }
    return out;
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

    // Procedural reference tracks get role-specific processing
    if (m_inputChannels.empty()) {
        applyTrackEffects(trackSamples, trackIndex, params);
    }
}

// Panning Implementation
void MixerGen::applyPanning(std::vector<float>& samples, const glm::vec2& panPosition) {
    if (m_numChannels == 2) {
        applyStereoPanning(samples, panPosition);
    } else if (m_numChannels > 2) {
        applySurroundPanning(samples, panPosition, m_numChannels);
    }
}

// Equal-power stereo panning: pan.x 0 = hard left, 0.5 = centre, 1 = hard right.
void MixerGen::applyStereoPanning(std::vector<float>& samples, const glm::vec2& pan) {
    const float x = std::clamp(pan.x, 0.0f, 1.0f);
    const float panLeft = std::cos(x * kHalfPi) * std::sqrt(2.0f);
    const float panRight = std::sin(x * kHalfPi) * std::sqrt(2.0f);
    for (size_t i = 0; i + 1 < samples.size(); i += 2) {
        samples[i] *= panLeft;
        samples[i + 1] *= panRight;
    }
}

// Surround panning for 5.1 (FL FR C LFE RL RR) and 7.1 (+ SL SR): pan.x = left/right,
// pan.y = front (0) / back (1). The LFE channel is left untouched.
void MixerGen::applySurroundPanning(std::vector<float>& samples, const glm::vec2& pan, uint32_t channels) {
    if (channels < 6) return;
    const float x = std::clamp(pan.x, 0.0f, 1.0f);
    const float y = std::clamp(pan.y, 0.0f, 1.0f);
    const float left = std::cos(x * kHalfPi), right = std::sin(x * kHalfPi);
    const float front = std::cos(y * kHalfPi), back = std::sin(y * kHalfPi);
    const float centre = front * (1.0f - std::abs(x - 0.5f) * 2.0f);
    std::vector<float> gains(channels, 1.0f);
    gains[0] = left * front;
    gains[1] = right * front;
    gains[2] = centre;
    gains[3] = 1.0f;
    gains[4] = left * back;
    gains[5] = right * back;
    if (channels >= 8) {
        const float side = std::sin(y * kPi); // strongest at the middle of the front/back axis
        gains[6] = left * side;
        gains[7] = right * side;
    }
    for (size_t i = 0; i < samples.size(); ++i) {
        samples[i] *= gains[i % channels];
    }
}

// Automation Implementation: the curve is stretched over the whole buffer and
// linearly interpolated between its points.
void MixerGen::applyAutomation(std::vector<float>& samples, const std::vector<float>& automationCurves) {
    if (automationCurves.empty() || samples.empty()) return;

    const size_t channels = std::max<uint32_t>(1, m_numChannels);
    const size_t frames = samples.size() / channels;
    for (size_t f = 0; f < frames; ++f) {
        float value = automationCurves.front();
        if (automationCurves.size() > 1 && frames > 1) {
            const float pos = static_cast<float>(f) / static_cast<float>(frames - 1) * (automationCurves.size() - 1);
            const size_t i0 = static_cast<size_t>(pos);
            const size_t i1 = std::min(i0 + 1, automationCurves.size() - 1);
            value = lerp(automationCurves[i0], automationCurves[i1], pos - static_cast<float>(i0));
        }
        for (size_t c = 0; c < channels; ++c) samples[f * channels + c] *= value;
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
    float omega = kTwoPi * cutoffFreq / m_sampleRate;
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
    float omega = kTwoPi * cutoffFreq / m_sampleRate;
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
    float omega = kTwoPi * centerFreq / m_sampleRate;
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

// Compression Implementation (threshold in dBFS, attack/release in seconds)
void MixerGen::applyCompression(std::vector<float>& samples, float threshold, float ratio, float attack, float release) {
    float envelope = 1.0f;
    const float attackCoeff = std::exp(-1.0f / (std::max(attack, 1e-5f) * m_sampleRate));
    const float releaseCoeff = std::exp(-1.0f / (std::max(release, 1e-5f) * m_sampleRate));

    for (float& sample : samples) {
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

// Custom Processing
void MixerGen::applyCustomProcessing(std::vector<float>& samples, float gain, size_t trackIndex, const MixerParams& params) {
    // Apply gain
    for (float& sample : samples) {
        sample *= gain;
    }

    // Apply panning if available
    if (trackIndex < params.panPositions.size()) {
        applyPanning(samples, params.panPositions[trackIndex]);
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
    // Emphasise transients by adding back the high-passed (attack) content
    std::vector<float> transients = samples;
    applyHighPassFilter(transients, 5000.0f, 0.5f);
    for (size_t i = 0; i < samples.size(); ++i) {
        samples[i] += transients[i] * 0.5f;
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

void MixerGen::applyMasterProcessing(std::vector<float>& samples, const MixerParams& params) {
    applyMasterGain(samples, params.masterGain);

    // Soft-knee limiter above -1 dBFS keeps the bus from clipping
    const float knee = 0.89f;
    for (float& s : samples) {
        const float a = std::abs(s);
        if (a > knee) {
            const float over = (a - knee) / (1.0f - knee);
            s = std::copysign(knee + (1.0f - knee) * std::tanh(over), s);
        }
    }
}

// Channel management
void MixerGen::addInputChannel(const std::string& name, const std::vector<float>& samples) {
    for (auto& ch : m_inputChannels) {
        if (ch.name == name) {
            ch.samples = samples;
            return;
        }
    }
    ChannelData channel;
    channel.name = name;
    channel.samples = samples;
    m_inputChannels.push_back(std::move(channel));
}

void MixerGen::removeInputChannel(const std::string& name) {
    m_inputChannels.erase(std::remove_if(m_inputChannels.begin(), m_inputChannels.end(),
                                         [&](const ChannelData& c) { return c.name == name; }),
                          m_inputChannels.end());
}

void MixerGen::clearInputChannels() {
    m_inputChannels.clear();
}

// Procedural reference track (sine / square / saw / noise) used when no inputs are registered.
std::vector<float> MixerGen::generateTrackSamples(size_t trackIndex, size_t bufferSize) {
    const uint32_t channels = std::max<uint32_t>(1, m_numChannels);
    std::vector<float> samples(bufferSize * channels);
    std::mt19937 noise(static_cast<uint32_t>(trackIndex * 7919u + 17u));
    std::uniform_real_distribution<float> dist(-0.5f, 0.5f);
    const float frequency = 100.0f + trackIndex * 200.0f;

    // Generate different content for each track
    for (size_t frame = 0; frame < bufferSize; ++frame) {
        float time = static_cast<float>(frame) / m_sampleRate;
        float value = 0.0f;

        switch (trackIndex % 4) {
            case 0: // Sine wave
                value = std::sin(kTwoPi * frequency * time) * 0.3f;
                break;
            case 1: // Square wave
                value = (std::sin(kTwoPi * frequency * time) > 0.0f ? 1.0f : -1.0f) * 0.2f;
                break;
            case 2: // Saw wave
                value = (2.0f * (frequency * time - std::floor(frequency * time + 0.5f))) * 0.15f;
                break;
            case 3: // Noise
                value = dist(noise) * 0.2f;
                break;
        }
        for (uint32_t c = 0; c < channels; ++c) samples[frame * channels + c] = value;
    }

    return samples;
}

// Quality calculation functions
float MixerGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    return calculatePeak(samples);
}

float MixerGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    return calculateRMS(samples);
}

float MixerGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float MixerGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

float MixerGen::calculateRMS(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    double sum = 0.0;
    for (float s : samples) sum += static_cast<double>(s) * s;
    return static_cast<float>(std::sqrt(sum / samples.size()));
}

float MixerGen::calculatePeak(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
}

// Quality Settings
void MixerGen::setMixingQuality(int quality) {
    m_mixingQuality = std::clamp(quality, 1, 10);
}

void MixerGen::setRealTimeProcessing(bool enabled) {
    m_realTimeProcessing = enabled;
}

void MixerGen::setBufferSize(int size) {
    m_bufferSize = std::max(1, size);
}

void MixerGen::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 10);
}

void MixerGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = std::clamp(factor, 1, 8);
}

void MixerGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void MixerGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void MixerGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 16);
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

float MixerGen::lerp(float a, float b, float t) {
    return a + (b - a) * t;
}

float MixerGen::smoothstep(float edge0, float edge1, float x) {
    float t = clamp((x - edge0) / (edge1 - edge0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

} // namespace Audio
} // namespace MagiTech
