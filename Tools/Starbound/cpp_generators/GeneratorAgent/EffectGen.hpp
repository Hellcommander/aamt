#pragma once

#include "AudioAssetTypes.hpp"
#include <memory>
#include <string>
#include <vector>
#include <deque>

namespace MagiTech {
namespace Audio {

// Audio effects processing
class EffectGen {
public:
    EffectGen();
    ~EffectGen();

    // Core processing: runs the effect chain over params.inputBuffer (mono/interleaved
    // samples at params.sampleRate). With an empty input the chain's impulse response
    // (1 second) is rendered instead.
    AudioBundle process(const EffectParams& params);

    // Applies the chain described by params (effectTypes, or the names in params.chain)
    // to the given samples.
    std::vector<float> processChain(const std::vector<float>& samples, const EffectParams& params);

    // Resolves the effect chain: effectTypes when set, otherwise the names in chain.
    static std::vector<EffectType> resolveChain(const EffectParams& params);
    static bool effectTypeFromString(const std::string& name, EffectType& out);

    // Effect implementations
    std::vector<float> applyReverb(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyDelay(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyChorus(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyFlanger(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyDistortion(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyCompressor(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyEqualizer(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);
    std::vector<float> applyFilter(const std::vector<float>& samples, const EffectParams& params, uint32_t sampleRate);

    // Quality settings
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
    // Reverb implementation
    class ReverbProcessor {
    public:
        ReverbProcessor(uint32_t sampleRate);
        std::vector<float> process(const std::vector<float>& input, float roomSize, float damping,
                                 float wetLevel, float dryLevel, float width);
    private:
        std::vector<std::deque<float>> m_delayLines;
        std::vector<float> m_feedbackGains;
        uint32_t m_sampleRate;
    };

    // Delay implementation
    class DelayProcessor {
    public:
        DelayProcessor(uint32_t sampleRate);
        std::vector<float> process(const std::vector<float>& input, float delayTime, float feedback, float mix);
    private:
        std::deque<float> m_delayBuffer;
        size_t m_writeIndex = 0;
        uint32_t m_sampleRate;
    };

    // Chorus/Flanger implementation
    class ChorusProcessor {
    public:
        ChorusProcessor(uint32_t sampleRate);
        std::vector<float> process(const std::vector<float>& input, float rate, float depth, float feedback);
    private:
        std::vector<std::deque<float>> m_delayBuffers;
        std::vector<float> m_lfoPhases;
        size_t m_writeIndex = 0;
        uint32_t m_sampleRate;
    };

    // Distortion implementation
    class DistortionProcessor {
    public:
        DistortionProcessor();
        std::vector<float> process(const std::vector<float>& input, float drive, float range, float blend);
    private:
        float softClip(float sample, float drive);
        float hardClip(float sample, float threshold);
    };

    // Compressor implementation (threshold in dBFS, attack/release in seconds)
    class CompressorProcessor {
    public:
        explicit CompressorProcessor(uint32_t sampleRate = 44100);
        std::vector<float> process(const std::vector<float>& input, float threshold, float ratio,
                                 float attack, float release);
    private:
        float m_envelope;
        uint32_t m_sampleRate;
        float calculateGain(float inputLevel, float threshold, float ratio);
    };

    // Equalizer implementation
    class EqualizerProcessor {
    public:
        EqualizerProcessor(uint32_t sampleRate);
        std::vector<float> process(const std::vector<float>& input, const std::vector<float>& frequencies,
                                 const std::vector<float>& gains, const std::vector<float>& qFactors);
    private:
        struct BiquadFilter {
            float b0, b1, b2, a1, a2;
            float x1, x2, y1, y2;
        };

        std::vector<BiquadFilter> m_filters;
        uint32_t m_sampleRate;

        BiquadFilter createLowShelfFilter(float frequency, float gain, float q);
        BiquadFilter createHighShelfFilter(float frequency, float gain, float q);
        BiquadFilter createPeakFilter(float frequency, float gain, float q);
        float processBiquad(BiquadFilter& filter, float input);
    };

    // Filter implementation (filterType: 0 = low-pass, 1 = high-pass, 2 = band-pass)
    class FilterProcessor {
    public:
        FilterProcessor(uint32_t sampleRate);
        std::vector<float> process(const std::vector<float>& input, float cutoffFrequency,
                                 float resonance, float filterType);
    private:
        struct FilterState {
            float x1, x2, y1, y2;
        };

        FilterState m_state;
        uint32_t m_sampleRate;

        void calculateCoefficients(float cutoff, float resonance, float filterType,
                                float& b0, float& b1, float& b2, float& a1, float& a2);
        float processSample(float input, float b0, float b1, float b2, float a1, float a2);
    };

    // (Re)creates the processors for the given sample rate.
    void prepare(uint32_t sampleRate);

    // Utility functions
    float clamp(float value, float min, float max);
    float lerp(float a, float b, float t);
    float smoothstep(float edge0, float edge1, float x);
    std::vector<float> mixSignals(const std::vector<float>& dry, const std::vector<float>& wet, float mix);

    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    int m_maxProcessingThreads;
    std::string m_lastError;
    uint32_t m_sampleRate = 0;

    // Effect processors
    std::unique_ptr<ReverbProcessor> m_reverbProcessor;
    std::unique_ptr<DelayProcessor> m_delayProcessor;
    std::unique_ptr<ChorusProcessor> m_chorusProcessor;
    std::unique_ptr<DistortionProcessor> m_distortionProcessor;
    std::unique_ptr<CompressorProcessor> m_compressorProcessor;
    std::unique_ptr<EqualizerProcessor> m_equalizerProcessor;
    std::unique_ptr<FilterProcessor> m_filterProcessor;

    // Constants
    static constexpr float PI = 3.14159265359f;
    static constexpr float TWO_PI = 2.0f * PI;
};

} // namespace Audio
} // namespace MagiTech
