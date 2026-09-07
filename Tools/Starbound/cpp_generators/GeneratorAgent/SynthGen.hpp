#pragma once

#include "AudioAssetTypes.hpp"
#include <vector>
#include <string>
#include <memory>
#include <map>
#include <chrono>

namespace MagiTech {
namespace Audio {

// Forward declarations
struct InstrumentDefinition;
struct SynthResult;
struct SynthMetadata;
struct SynthPack;
struct VoiceDefinition;
struct OscillatorDefinition;
struct ADSR;
struct FilterDefinition;
struct LFODefinition;
struct EffectDefinition;
struct VariationSettings;
struct VariationSample;
struct TimeStretchSettings;
struct RandomizationSettings;

// Oscillator Types
enum class OscillatorType {
    SINE,
    SQUARE,
    SAW,
    TRIANGLE,
    WAVETABLE,
    FM,
    GRANULAR
};

// Filter Types
enum class FilterType {
    LOWPASS,
    HIGHPASS,
    BANDPASS,
    NOTCH
};

// Modulation Targets
enum class ModulationTarget {
    FREQUENCY,
    AMPLITUDE,
    CUTOFF,
    PHASE
};

// Effect Types
enum class EffectType {
    REVERB,
    DELAY,
    CHORUS,
    DISTORTION,
    COMPRESSOR,
    EQUALIZER
};

// Instrument Definition Structures
struct OscillatorDefinition {
    OscillatorType type = OscillatorType::SINE;
    float frequency = 440.0f;
    float amplitude = 0.8f;
    float phase = 0.0f;
    float detune = 0.0f;
    std::string wavetablePath;
    std::map<std::string, float> parameters;
};

struct ADSR {
    float attack = 0.1f;
    float decay = 0.1f;
    float sustain = 0.7f;
    float release = 0.2f;
};

struct FilterDefinition {
    FilterType type = FilterType::LOWPASS;
    float cutoff = 2000.0f;
    float resonance = 0.3f;
    float envelopeAmount = 0.5f;
    std::map<std::string, float> parameters;
};

struct LFODefinition {
    ModulationTarget target = ModulationTarget::CUTOFF;
    WaveformType waveform = WaveformType::SINE;
    float rate = 0.5f;
    float depth = 100.0f;
    float phase = 0.0f;
    std::map<std::string, float> parameters;
};

struct VoiceDefinition {
    OscillatorDefinition oscillator;
    ADSR ampEnvelope;
    ADSR filterEnvelope;
    FilterDefinition filter;
    LFODefinition lfo;
    std::map<std::string, float> parameters;
};

struct EffectDefinition {
    EffectType type;
    std::map<std::string, float> parameters;
    bool enabled = true;
    float wetLevel = 0.5f;
    float dryLevel = 0.5f;
};

struct TimeStretchSettings {
    bool enabled = false;
    size_t windowSize = 1024;
    float overlap = 0.5f;
    float stretchFactor = 1.0f;
};

struct RandomizationSettings {
    bool enabled = false;
    float amount = 0.1f;
    std::map<std::string, float> ranges;
};

struct VariationSettings {
    std::pair<int, int> pitchRange = {-12, 12};
    TimeStretchSettings timeStretch;
    RandomizationSettings randomization;
    bool enablePitchVariations = true;
    bool enableTimeVariations = false;
    bool enableRandomVariations = false;
};

struct InstrumentDefinition {
    std::string name;
    std::string category;
    std::string description;
    VoiceDefinition voice;
    std::vector<EffectDefinition> effects;
    VariationSettings variations;
    std::map<std::string, std::string> metadata;
    std::vector<std::string> tags;
    bool enableHotReload = true;
    bool enableCaching = true;
    bool enableParallelProcessing = true;
    int maxConcurrentVoices = 8;
};

// Synthesis Result Structures
struct VariationSample {
    int midiNote;
    int pitchShift;
    std::vector<float> audioData;
    std::vector<float> stretchedData;
    std::map<std::string, float> parameters;
    std::chrono::system_clock::time_point generationTime;
    std::string filename;
    size_t fileSize;
    std::string checksum;
};

struct SynthResult {
    std::vector<float> audioData;
    std::vector<VariationSample> variations;
    SynthMetadata metadata;
    SynthPack synthPack;
    InstrumentDefinition instrumentDef;
    std::chrono::system_clock::time_point synthesisTime;
    bool success = true;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

// Metadata Structures
struct VoiceParameters {
    OscillatorType oscillatorType;
    float frequency;
    float amplitude;
    ADSR ampEnvelope;
    ADSR filterEnvelope;
    FilterType filterType;
    float filterCutoff;
    float filterResonance;
    std::map<std::string, float> additionalParams;
};

struct SynthMetadata {
    std::string instrumentName;
    std::string category;
    std::string description;
    uint32_t sampleRate;
    uint32_t bitDepth;
    uint32_t channels;
    float duration;
    VoiceParameters voiceParams;
    std::pair<int, int> pitchRange;
    int numVariations;
    bool timeStretchEnabled;
    bool randomizationEnabled;
    std::vector<EffectDefinition> effects;
    std::vector<std::string> timbreTags;
    std::map<std::string, std::string> additionalMetadata;
};

struct SynthPack {
    std::string name;
    std::string version;
    SynthMetadata metadata;
    std::vector<VariationSample> variations;
    InstrumentDefinition instrumentDef;
    std::chrono::system_clock::time_point creationTime;
    std::string filePath;
    size_t totalSize;
    std::string checksum;
};

// SynthGen Class
class SynthGen {
public:
    SynthGen();
    ~SynthGen();
    
    // Main processing function
    AudioBundle process(const SynthParams& params);
    
    // Instrument definition management
    InstrumentDefinition loadInstrumentDefinition(const std::string& filePath);
    InstrumentDefinition createDefaultInstrumentDefinition(const SynthParams& params);
    bool saveInstrumentDefinition(const InstrumentDefinition& def, const std::string& filePath);
    
    // Synthesis pipeline processing
    SynthResult processSynthesisPipeline(const InstrumentDefinition& instrumentDef, const SynthParams& params);
    
    // Synthesis engine initialization
    void initializeSynthesisEngines();
    void initializeSynthesisEngine(const InstrumentDefinition& instrumentDef);
    
    // Voice synthesis
    std::vector<float> synthesizeVoice(const VoiceDefinition& voice, const SynthParams& params);
    
    // Oscillator generation
    std::vector<float> generateOscillatorOutput(const OscillatorDefinition& osc, size_t numSamples);
    
    // Envelope application
    std::vector<float> applyEnvelope(const std::vector<float>& input, const ADSR& envelope);
    
    // Filter application
    std::vector<float> applyFilter(const std::vector<float>& input, const FilterDefinition& filter);
    
    // LFO application
    std::vector<float> applyLFO(const std::vector<float>& input, const LFODefinition& lfo);
    float generateLFOValue(WaveformType waveform, float rate, float depth, float phase, float time);
    
    // Effect chain application
    std::vector<float> applyEffectChain(const std::vector<float>& input, const std::vector<EffectDefinition>& effects);
    std::vector<float> applyEffect(const std::vector<float>& input, const EffectDefinition& effect);
    
    // Variation generation
    std::vector<VariationSample> generateVariations(const std::vector<float>& baseVoice, const VariationSettings& variations);
    std::vector<float> pitchShift(const std::vector<float>& input, int semitones);
    std::vector<float> timeStretch(const std::vector<float>& input, const TimeStretchSettings& settings);
    void applyRandomization(std::vector<float>& audio, const RandomizationSettings& settings);
    
    // Metadata generation
    SynthMetadata generateMetadata(const InstrumentDefinition& instrumentDef, const std::vector<VariationSample>& variations);
    std::vector<std::string> generateTimbreTags(const InstrumentDefinition& instrumentDef);
    
    // Synth pack creation
    SynthPack createSynthPack(const InstrumentDefinition& instrumentDef, const SynthResult& result);
    
    // Oscillator implementations
    class SineOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class SquareOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class SawOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class TriangleOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class WavetableOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples, const std::string& wavetablePath);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class FMOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class GranularOscillator {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> generate(float frequency, float amplitude, float phase, size_t numSamples);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    // Filter implementations
    class LowpassFilter {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, float cutoff, float resonance);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class HighpassFilter {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, float cutoff, float resonance);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class BandpassFilter {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, float cutoff, float resonance);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class NotchFilter {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, float cutoff, float resonance);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    // Effect implementations
    class ReverbEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class DelayEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class ChorusEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class DistortionEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class CompressorEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class EqualizerEffect {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> process(const std::vector<float>& input, const std::map<std::string, float>& parameters);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
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
    
    // Utility functions
    float clamp(float value, float min, float max);
    
    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);

private:
    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    int m_maxProcessingThreads;
    std::string m_lastError;
    
    // Synthesis settings
    uint32_t m_sampleRate;
    uint32_t m_bufferSize;
    uint32_t m_numChannels;
    bool m_enableAntiAliasing;
    bool m_enableOversampling;
    
    // Synthesis engines
    std::unique_ptr<SineOscillator> m_sineOscillator;
    std::unique_ptr<SquareOscillator> m_squareOscillator;
    std::unique_ptr<SawOscillator> m_sawOscillator;
    std::unique_ptr<TriangleOscillator> m_triangleOscillator;
    std::unique_ptr<WavetableOscillator> m_wavetableOscillator;
    std::unique_ptr<FMOscillator> m_fmOscillator;
    std::unique_ptr<GranularOscillator> m_granularOscillator;
    
    // Filters
    std::unique_ptr<LowpassFilter> m_lowpassFilter;
    std::unique_ptr<HighpassFilter> m_highpassFilter;
    std::unique_ptr<BandpassFilter> m_bandpassFilter;
    std::unique_ptr<NotchFilter> m_notchFilter;
    
    // Effects
    std::unique_ptr<ReverbEffect> m_reverbEffect;
    std::unique_ptr<DelayEffect> m_delayEffect;
    std::unique_ptr<ChorusEffect> m_chorusEffect;
    std::unique_ptr<DistortionEffect> m_distortionEffect;
    std::unique_ptr<CompressorEffect> m_compressorEffect;
    std::unique_ptr<EqualizerEffect> m_equalizerEffect;
    
    // Current synthesis state
    uint32_t m_currentSampleRate;
    uint32_t m_currentBufferSize;
    
    // Constants
    static constexpr float PI = 3.14159265359f;
    static constexpr float TWO_PI = 2.0f * PI;
    static constexpr float SEMITONE_RATIO = 1.059463094359f;
};

} // namespace Audio
} // namespace MagiTech 
