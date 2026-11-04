#pragma once

#include "AudioAssetTypes.hpp"
#include <memory>
#include <string>
#include <vector>

namespace MagiTech {
namespace Audio {

// Audio mixing and channel processing.
// Tracks are the registered input channels (addInputChannel); when none are registered,
// MixerGen renders one procedural reference track per entry of MixerParams::trackGains.
class MixerGen {
public:
    MixerGen();
    ~MixerGen();

    // Core processing
    AudioBundle process(const MixerParams& params);

    // Channel mixing: mixes the given interleaved tracks with params (mixer type,
    // per-track gains, automation and master processing).
    std::vector<float> mixChannels(const std::vector<std::vector<float>>& channels, const MixerParams& params);

    // Automation
    void applyAutomation(std::vector<float>& samples, const std::vector<float>& automationCurves);

    // Master processing (master gain + soft limiting)
    void applyMasterProcessing(std::vector<float>& samples, const MixerParams& params);

    // Channel management
    void addInputChannel(const std::string& name, const std::vector<float>& samples);
    void removeInputChannel(const std::string& name);
    void clearInputChannels();
    size_t getInputChannelCount() const { return m_inputChannels.size(); }

    // Quality settings
    void setMixingQuality(int quality);
    void setRealTimeProcessing(bool enabled);
    void setBufferSize(int size);
    void setProcessingQuality(int quality);
    void setOversamplingFactor(int factor);
    void setAntiAliasingEnabled(bool enable);

    // Processing options
    void enableGPUAcceleration(bool enable);
    void setMaxProcessingThreads(int threads);

    // Error handling
    std::string getLastError() const;
    void clearLastError();

    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);

private:
    // Channel data structure
    struct ChannelData {
        std::string name;
        std::vector<float> samples;
        float gain = 1.0f;
        glm::vec2 pan = glm::vec2(0.5f, 0.5f);
        bool muted = false;
        bool solo = false;
    };

    // Automation point structure
    struct AutomationPoint {
        float time;
        float value;
        float curve; // 0 = linear, 1 = exponential, etc.
    };

    // Mixer-type specific processing of MixerParams tracks
    std::vector<float> processLinearMix(const MixerParams& params);
    std::vector<float> processLogarithmicMix(const MixerParams& params);
    std::vector<float> processCustomMix(const MixerParams& params);

    // Mixing algorithms over prepared tracks
    std::vector<float> linearMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains);
    std::vector<float> logarithmicMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains);
    std::vector<float> customMix(const std::vector<std::vector<float>>& channels, const MixerParams& params);

    // Track processing
    std::vector<float> getTrackSamples(size_t trackIndex, size_t bufferSize);
    std::vector<float> generateTrackSamples(size_t trackIndex, size_t bufferSize);
    size_t trackLength() const;
    void applyTrackProcessing(std::vector<float>& trackSamples, float gain, size_t trackIndex, const MixerParams& params);
    void applyTrackEffects(std::vector<float>& samples, size_t trackIndex, const MixerParams& params);
    void applyCustomProcessing(std::vector<float>& samples, float gain, size_t trackIndex, const MixerParams& params);

    // Panning algorithms
    void applyPanning(std::vector<float>& samples, const glm::vec2& panPosition);
    void applyStereoPanning(std::vector<float>& samples, const glm::vec2& pan);
    void applySurroundPanning(std::vector<float>& samples, const glm::vec2& pan, uint32_t channels);

    // Filters / dynamics
    void applyLowPassFilter(std::vector<float>& samples, float cutoffFreq, float resonance);
    void applyHighPassFilter(std::vector<float>& samples, float cutoffFreq, float resonance);
    void applyBandPassFilter(std::vector<float>& samples, float centerFreq, float q);
    void applyCompression(std::vector<float>& samples, float threshold, float ratio, float attack, float release);

    // Custom effects
    void applyTransientEnhancement(std::vector<float>& samples);
    void applyHarmonicEnhancement(std::vector<float>& samples);
    void applyDeEsser(std::vector<float>& samples);
    void applyStereoEnhancement(std::vector<float>& samples);
    void applySaturation(std::vector<float>& samples);
    void applyMasterGain(std::vector<float>& samples, float masterGain);

    // Utility functions
    float clamp(float value, float min, float max);
    float lerp(float a, float b, float t);
    float smoothstep(float edge0, float edge1, float x);
    float calculateRMS(const std::vector<float>& samples);
    float calculatePeak(const std::vector<float>& samples);

    // Member variables
    std::vector<ChannelData> m_inputChannels;
    std::vector<AutomationPoint> m_automationPoints;

    bool m_gpuAccelerationEnabled;
    int m_mixingQuality;
    bool m_realTimeProcessing;
    int m_bufferSize;
    int m_maxProcessingThreads;
    std::string m_lastError;

    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    float m_masterGain;
    uint32_t m_sampleRate;
    uint32_t m_numChannels;

    // Constants
    static constexpr float MIN_GAIN = -60.0f; // -60 dB
    static constexpr float MAX_GAIN = 20.0f;  // +20 dB
    static constexpr float DEFAULT_GAIN = 0.0f; // 0 dB
};

} // namespace Audio
} // namespace MagiTech
