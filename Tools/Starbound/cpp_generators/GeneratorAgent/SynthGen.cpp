#include "SynthGen.hpp"
#include "AudioFileIO.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <mutex>
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;
constexpr float SEMITONE_RATIO = 1.059463094359f;
constexpr size_t DEFAULT_SAMPLE_RATE = 44100;
constexpr size_t DEFAULT_BUFFER_SIZE = 1024;

// JSON/YAML Parsing Implementation
namespace {
    // Helper function to safely get JSON values with defaults
    template<typename T>
    T getJsonValue(const nlohmann::json& j, const std::string& key, const T& defaultValue) {
        try {
            if (j.contains(key) && !j[key].is_null()) {
                return j[key].get<T>();
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get string with default
    std::string getJsonString(const nlohmann::json& j, const std::string& key, const std::string& defaultValue = "") {
        try {
            if (j.contains(key) && !j[key].is_null()) {
                return j[key].get<std::string>();
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get float with default
    float getJsonFloat(const nlohmann::json& j, const std::string& key, float defaultValue = 0.0f) {
        try {
            if (j.contains(key) && !j[key].is_null()) {
                return j[key].get<float>();
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get boolean with default
    bool getJsonBool(const nlohmann::json& j, const std::string& key, bool defaultValue = false) {
        try {
            if (j.contains(key) && !j[key].is_null()) {
                return j[key].get<bool>();
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get vector with default
    template<typename T>
    std::vector<T> getJsonVector(const nlohmann::json& j, const std::string& key, const std::vector<T>& defaultValue = {}) {
        try {
            if (j.contains(key) && j[key].is_array()) {
                return j[key].get<std::vector<T>>();
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get map with default
    std::map<std::string, float> getJsonMap(const nlohmann::json& j, const std::string& key, const std::map<std::string, float>& defaultValue = {}) {
        try {
            if (j.contains(key) && j[key].is_object()) {
                std::map<std::string, float> result;
                for (auto it = j[key].begin(); it != j[key].end(); ++it) {
                    if (it.value().is_number()) {
                        result[it.key()] = it.value().get<float>();
                    }
                }
                return result;
            }
        } catch (const std::exception& e) {
            // Log error if needed
        }
        return defaultValue;
    }
    
    // Helper function to get parameter from map with default
    float getParameter(const std::map<std::string, float>& parameters, const std::string& key, float defaultValue) {
        auto it = parameters.find(key);
        return (it != parameters.end()) ? it->second : defaultValue;
    }
    
    // Parse oscillator type from string
    OscillatorType parseOscillatorType(const std::string& typeStr) {
        if (typeStr == "sine") return OscillatorType::SINE;
        if (typeStr == "square") return OscillatorType::SQUARE;
        if (typeStr == "saw") return OscillatorType::SAW;
        if (typeStr == "triangle") return OscillatorType::TRIANGLE;
        if (typeStr == "wavetable") return OscillatorType::WAVETABLE;
        if (typeStr == "fm") return OscillatorType::FM;
        if (typeStr == "granular") return OscillatorType::GRANULAR;
        return OscillatorType::SINE; // Default
    }
    
    // Parse filter type from string
    FilterType parseFilterType(const std::string& typeStr) {
        if (typeStr == "lowpass") return FilterType::LOWPASS;
        if (typeStr == "highpass") return FilterType::HIGHPASS;
        if (typeStr == "bandpass") return FilterType::BANDPASS;
        if (typeStr == "notch") return FilterType::NOTCH;
        return FilterType::LOWPASS; // Default
    }
    
    // Parse modulation target from string
    ModulationTarget parseModulationTarget(const std::string& targetStr) {
        if (targetStr == "frequency") return ModulationTarget::FREQUENCY;
        if (targetStr == "amplitude") return ModulationTarget::AMPLITUDE;
        if (targetStr == "cutoff") return ModulationTarget::CUTOFF;
        if (targetStr == "phase") return ModulationTarget::PHASE;
        return ModulationTarget::CUTOFF; // Default
    }
    
    // Parse effect type from string
    EffectType parseEffectType(const std::string& typeStr) {
        if (typeStr == "reverb") return EffectType::REVERB;
        if (typeStr == "delay") return EffectType::DELAY;
        if (typeStr == "chorus") return EffectType::CHORUS;
        if (typeStr == "flanger") return EffectType::FLANGER;
        if (typeStr == "filter") return EffectType::FILTER;
        if (typeStr == "distortion") return EffectType::DISTORTION;
        if (typeStr == "compressor") return EffectType::COMPRESSOR;
        if (typeStr == "equalizer") return EffectType::EQUALIZER;
        return EffectType::REVERB; // Default
    }
    
    // Parse waveform type from string
    WaveformType parseWaveformType(const std::string& typeStr) {
        if (typeStr == "sine") return WaveformType::SINE;
        if (typeStr == "square") return WaveformType::SQUARE;
        if (typeStr == "saw") return WaveformType::SAW;
        if (typeStr == "triangle") return WaveformType::TRIANGLE;
        if (typeStr == "noise") return WaveformType::NOISE;
        if (typeStr == "custom") return WaveformType::CUSTOM;
        return WaveformType::SINE; // Default
    }
    
    // Parse oscillator definition from JSON
    OscillatorDefinition parseOscillatorDefinition(const nlohmann::json& j) {
        OscillatorDefinition osc;
        
        if (j.contains("oscillator")) {
            const auto& oscJson = j["oscillator"];
            osc.type = parseOscillatorType(getJsonString(oscJson, "type", "sine"));
            osc.frequency = getJsonFloat(oscJson, "frequency", 440.0f);
            osc.amplitude = getJsonFloat(oscJson, "amplitude", 0.8f);
            osc.phase = getJsonFloat(oscJson, "phase", 0.0f);
            osc.detune = getJsonFloat(oscJson, "detune", 0.0f);
            osc.wavetablePath = getJsonString(oscJson, "wavetablePath", "");
            osc.parameters = getJsonMap(oscJson, "parameters");
        }
        
        return osc;
    }
    
    // Parse ADSR envelope from JSON
    ADSR parseADSR(const nlohmann::json& j, const std::string& prefix = "") {
        ADSR adsr;
        
        std::string attackKey = prefix.empty() ? "attack" : prefix + "Attack";
        std::string decayKey = prefix.empty() ? "decay" : prefix + "Decay";
        std::string sustainKey = prefix.empty() ? "sustain" : prefix + "Sustain";
        std::string releaseKey = prefix.empty() ? "release" : prefix + "Release";
        
        adsr.attack = getJsonFloat(j, attackKey, 0.1f);
        adsr.decay = getJsonFloat(j, decayKey, 0.1f);
        adsr.sustain = getJsonFloat(j, sustainKey, 0.7f);
        adsr.release = getJsonFloat(j, releaseKey, 0.2f);
        
        return adsr;
    }
    
    // Parse filter definition from JSON
    FilterDefinition parseFilterDefinition(const nlohmann::json& j) {
        FilterDefinition filter;
        
        if (j.contains("filter")) {
            const auto& filterJson = j["filter"];
            filter.type = parseFilterType(getJsonString(filterJson, "type", "lowpass"));
            filter.cutoff = getJsonFloat(filterJson, "cutoff", 2000.0f);
            filter.resonance = getJsonFloat(filterJson, "resonance", 0.3f);
            filter.envelopeAmount = getJsonFloat(filterJson, "envelopeAmount", 0.5f);
            filter.parameters = getJsonMap(filterJson, "parameters");
        }
        
        return filter;
    }
    
    // Parse LFO definition from JSON
    LFODefinition parseLFODefinition(const nlohmann::json& j) {
        LFODefinition lfo;
        
        if (j.contains("lfo")) {
            const auto& lfoJson = j["lfo"];
            lfo.target = parseModulationTarget(getJsonString(lfoJson, "target", "cutoff"));
            lfo.waveform = parseWaveformType(getJsonString(lfoJson, "waveform", "sine"));
            lfo.rate = getJsonFloat(lfoJson, "rate", 0.5f);
            lfo.depth = getJsonFloat(lfoJson, "depth", 100.0f);
            lfo.phase = getJsonFloat(lfoJson, "phase", 0.0f);
            lfo.parameters = getJsonMap(lfoJson, "parameters");
        }
        
        return lfo;
    }
    
    // Parse voice definition from JSON
    VoiceDefinition parseVoiceDefinition(const nlohmann::json& j) {
        VoiceDefinition voice;
        
        voice.oscillator = parseOscillatorDefinition(j);
        voice.ampEnvelope = parseADSR(j, "amp");
        voice.filterEnvelope = parseADSR(j, "filter");
        voice.filter = parseFilterDefinition(j);
        voice.lfo = parseLFODefinition(j);
        voice.parameters = getJsonMap(j, "parameters");
        
        return voice;
    }
    
    // Parse effect definition from JSON
    EffectDefinition parseEffectDefinition(const nlohmann::json& j) {
        EffectDefinition effect;
        
        effect.type = parseEffectType(getJsonString(j, "type", "reverb"));
        effect.parameters = getJsonMap(j, "parameters");
        effect.enabled = getJsonBool(j, "enabled", true);
        effect.wetLevel = getJsonFloat(j, "wetLevel", 0.5f);
        effect.dryLevel = getJsonFloat(j, "dryLevel", 0.5f);
        
        return effect;
    }
    
    // Parse variation settings from JSON
    VariationSettings parseVariationSettings(const nlohmann::json& j) {
        VariationSettings variations;
        
        if (j.contains("variations")) {
            const auto& varJson = j["variations"];
            
            // Parse pitch range
            if (varJson.contains("pitchRange") && varJson["pitchRange"].is_array()) {
                auto pitchRange = varJson["pitchRange"].get<std::vector<int>>();
                if (pitchRange.size() >= 2) {
                    variations.pitchRange = {pitchRange[0], pitchRange[1]};
                }
            }
            
            // Parse time stretch settings
            if (varJson.contains("timeStretch")) {
                const auto& tsJson = varJson["timeStretch"];
                variations.timeStretch.enabled = getJsonBool(tsJson, "enabled", false);
                variations.timeStretch.windowSize = getJsonValue(tsJson, "windowSize", size_t(1024));
                variations.timeStretch.overlap = getJsonFloat(tsJson, "overlap", 0.5f);
                variations.timeStretch.stretchFactor = getJsonFloat(tsJson, "stretchFactor", 1.0f);
            }
            
            // Parse randomization settings
            if (varJson.contains("randomization")) {
                const auto& randJson = varJson["randomization"];
                variations.randomization.enabled = getJsonBool(randJson, "enabled", false);
                variations.randomization.amount = getJsonFloat(randJson, "amount", 0.1f);
                variations.randomization.ranges = getJsonMap(randJson, "ranges");
            }
            
            variations.enablePitchVariations = getJsonBool(varJson, "enablePitchVariations", true);
            variations.enableTimeVariations = getJsonBool(varJson, "enableTimeVariations", false);
            variations.enableRandomVariations = getJsonBool(varJson, "enableRandomVariations", false);
        }
        
        return variations;
    }
    
    // Parse instrument definition from JSON
    InstrumentDefinition parseInstrumentDefinition(const nlohmann::json& j) {
        InstrumentDefinition instrument;
        
        instrument.name = getJsonString(j, "name", "default_instrument");
        instrument.category = getJsonString(j, "category", "pad");
        instrument.description = getJsonString(j, "description", "Default synthesized instrument");
        
        // Parse voice definition
        instrument.voice = parseVoiceDefinition(j);
        
        // Parse effects
        if (j.contains("effects") && j["effects"].is_array()) {
            for (const auto& effectJson : j["effects"]) {
                instrument.effects.push_back(parseEffectDefinition(effectJson));
            }
        }
        
        // Parse variation settings
        instrument.variations = parseVariationSettings(j);
        
        // Parse metadata
        if (j.contains("metadata") && j["metadata"].is_object()) {
            for (auto it = j["metadata"].begin(); it != j["metadata"].end(); ++it) {
                if (it.value().is_string()) {
                    instrument.metadata[it.key()] = it.value().get<std::string>();
                }
            }
        }
        
        // Parse tags
        instrument.tags = getJsonVector<std::string>(j, "tags");
        
        // Parse settings
        instrument.enableHotReload = getJsonBool(j, "enableHotReload", true);
        instrument.enableCaching = getJsonBool(j, "enableCaching", true);
        instrument.enableParallelProcessing = getJsonBool(j, "enableParallelProcessing", true);
        instrument.maxConcurrentVoices = getJsonValue(j, "maxConcurrentVoices", 8);
        
        return instrument;
    }
    
    // Try to parse as JSON first, then YAML
    InstrumentDefinition parseInstrumentFile(const std::string& filePath) {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            throw std::runtime_error("Could not open instrument file: " + filePath);
        }
        
        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();
        
        // Instrument definitions are JSON documents (yaml-cpp is not vendored with the backend)
        try {
            nlohmann::json j = nlohmann::json::parse(content);
            return parseInstrumentDefinition(j);
        } catch (const nlohmann::json::exception& e) {
            throw std::runtime_error("Failed to parse instrument file as JSON: " + std::string(e.what()));
        }
    }
}

// SynthGen Implementation
SynthGen::SynthGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize with default settings
    m_sampleRate = DEFAULT_SAMPLE_RATE;
    m_bufferSize = DEFAULT_BUFFER_SIZE;
    m_numChannels = 2; // Stereo
    m_enableAntiAliasing = true;
    m_enableOversampling = true;
    
    // Initialize synthesis engines
    initializeSynthesisEngines();
}

SynthGen::~SynthGen() = default;

AudioBundle SynthGen::process(const SynthParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "synth_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        
        // Load instrument definition if provided
        InstrumentDefinition instrumentDef;
        if (!params.instrumentDefinitionPath.empty()) {
            instrumentDef = loadInstrumentDefinition(params.instrumentDefinitionPath);
        } else {
            instrumentDef = createDefaultInstrumentDefinition(params);
        }
        
        // Process synthesis pipeline
        SynthResult result = processSynthesisPipeline(instrumentDef, params);
        
        // Set the synthesized data
        bundle.buffer = result.audioData;
        bundle.meta.duration = static_cast<float>(result.audioData.size()) / (m_sampleRate * m_numChannels);
        
        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(result.audioData);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(result.audioData);
        bundle.quality.dynamicRange = calculateDynamicRange(result.audioData);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(result.audioData);
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Instrument Definition Loading - IMPLEMENTED
InstrumentDefinition SynthGen::loadInstrumentDefinition(const std::string& filePath) {
    try {
        return parseInstrumentFile(filePath);
    } catch (const std::exception& e) {
        m_lastError = "Failed to load instrument definition: " + std::string(e.what());
        // Return a default definition if loading fails
        return createDefaultInstrumentDefinition(SynthParams{});
    }
}

// Instrument Definition Saving - IMPLEMENTED
bool SynthGen::saveInstrumentDefinition(const InstrumentDefinition& def, const std::string& filePath) {
    try {
        nlohmann::json j;
        
        // Basic instrument properties
        j["name"] = def.name;
        j["category"] = def.category;
        j["description"] = def.description;
        
        // Voice definition
        j["oscillator"]["type"] = [](OscillatorType type) -> std::string {
            switch (type) {
                case OscillatorType::SINE: return "sine";
                case OscillatorType::SQUARE: return "square";
                case OscillatorType::SAW: return "saw";
                case OscillatorType::TRIANGLE: return "triangle";
                case OscillatorType::WAVETABLE: return "wavetable";
                case OscillatorType::FM: return "fm";
                case OscillatorType::GRANULAR: return "granular";
                default: return "sine";
            }
        }(def.voice.oscillator.type);
        
        j["oscillator"]["frequency"] = def.voice.oscillator.frequency;
        j["oscillator"]["amplitude"] = def.voice.oscillator.amplitude;
        j["oscillator"]["phase"] = def.voice.oscillator.phase;
        j["oscillator"]["detune"] = def.voice.oscillator.detune;
        j["oscillator"]["wavetablePath"] = def.voice.oscillator.wavetablePath;
        
        // ADSR envelopes
        j["ampAttack"] = def.voice.ampEnvelope.attack;
        j["ampDecay"] = def.voice.ampEnvelope.decay;
        j["ampSustain"] = def.voice.ampEnvelope.sustain;
        j["ampRelease"] = def.voice.ampEnvelope.release;
        
        j["filterAttack"] = def.voice.filterEnvelope.attack;
        j["filterDecay"] = def.voice.filterEnvelope.decay;
        j["filterSustain"] = def.voice.filterEnvelope.sustain;
        j["filterRelease"] = def.voice.filterEnvelope.release;
        
        // Filter
        j["filter"]["type"] = [](FilterType type) -> std::string {
            switch (type) {
                case FilterType::LOWPASS: return "lowpass";
                case FilterType::HIGHPASS: return "highpass";
                case FilterType::BANDPASS: return "bandpass";
                case FilterType::NOTCH: return "notch";
                default: return "lowpass";
            }
        }(def.voice.filter.type);
        
        j["filter"]["cutoff"] = def.voice.filter.cutoff;
        j["filter"]["resonance"] = def.voice.filter.resonance;
        j["filter"]["envelopeAmount"] = def.voice.filter.envelopeAmount;
        
        // LFO
        j["lfo"]["target"] = [](ModulationTarget target) -> std::string {
            switch (target) {
                case ModulationTarget::FREQUENCY: return "frequency";
                case ModulationTarget::AMPLITUDE: return "amplitude";
                case ModulationTarget::CUTOFF: return "cutoff";
                case ModulationTarget::PHASE: return "phase";
                default: return "cutoff";
            }
        }(def.voice.lfo.target);
        
        j["lfo"]["waveform"] = [](WaveformType type) -> std::string {
            switch (type) {
                case WaveformType::SINE: return "sine";
                case WaveformType::SQUARE: return "square";
                case WaveformType::SAW: return "saw";
                case WaveformType::TRIANGLE: return "triangle";
                case WaveformType::NOISE: return "noise";
                case WaveformType::CUSTOM: return "custom";
                default: return "sine";
            }
        }(def.voice.lfo.waveform);
        
        j["lfo"]["rate"] = def.voice.lfo.rate;
        j["lfo"]["depth"] = def.voice.lfo.depth;
        j["lfo"]["phase"] = def.voice.lfo.phase;
        
        // Effects
        j["effects"] = nlohmann::json::array();
        for (const auto& effect : def.effects) {
            nlohmann::json effectJson;
            effectJson["type"] = [](EffectType type) -> std::string {
                switch (type) {
                    case EffectType::REVERB: return "reverb";
                    case EffectType::DELAY: return "delay";
                    case EffectType::CHORUS: return "chorus";
                    case EffectType::DISTORTION: return "distortion";
                    case EffectType::COMPRESSOR: return "compressor";
                    case EffectType::EQUALIZER: return "equalizer";
                    case EffectType::FLANGER: return "flanger";
                    case EffectType::FILTER: return "filter";
                    default: return "reverb";
                }
            }(effect.type);
            
            effectJson["enabled"] = effect.enabled;
            effectJson["wetLevel"] = effect.wetLevel;
            effectJson["dryLevel"] = effect.dryLevel;
            
            // Parameters
            effectJson["parameters"] = nlohmann::json::object();
            for (const auto& param : effect.parameters) {
                effectJson["parameters"][param.first] = param.second;
            }
            
            j["effects"].push_back(effectJson);
        }
        
        // Variations
        j["variations"]["pitchRange"] = {def.variations.pitchRange.first, def.variations.pitchRange.second};
        j["variations"]["enablePitchVariations"] = def.variations.enablePitchVariations;
        j["variations"]["enableTimeVariations"] = def.variations.enableTimeVariations;
        j["variations"]["enableRandomVariations"] = def.variations.enableRandomVariations;
        
        // Time stretch
        j["variations"]["timeStretch"]["enabled"] = def.variations.timeStretch.enabled;
        j["variations"]["timeStretch"]["windowSize"] = def.variations.timeStretch.windowSize;
        j["variations"]["timeStretch"]["overlap"] = def.variations.timeStretch.overlap;
        j["variations"]["timeStretch"]["stretchFactor"] = def.variations.timeStretch.stretchFactor;
        
        // Randomization
        j["variations"]["randomization"]["enabled"] = def.variations.randomization.enabled;
        j["variations"]["randomization"]["amount"] = def.variations.randomization.amount;
        j["variations"]["randomization"]["ranges"] = nlohmann::json::object();
        for (const auto& range : def.variations.randomization.ranges) {
            j["variations"]["randomization"]["ranges"][range.first] = range.second;
        }
        
        // Metadata
        j["metadata"] = nlohmann::json::object();
        for (const auto& meta : def.metadata) {
            j["metadata"][meta.first] = meta.second;
        }
        
        // Tags
        j["tags"] = def.tags;
        
        // Settings
        j["enableHotReload"] = def.enableHotReload;
        j["enableCaching"] = def.enableCaching;
        j["enableParallelProcessing"] = def.enableParallelProcessing;
        j["maxConcurrentVoices"] = def.maxConcurrentVoices;
        
        // Write to file
        std::ofstream file(filePath);
        if (!file.is_open()) {
            m_lastError = "Could not open file for writing: " + filePath;
            return false;
        }
        
        file << j.dump(2); // Pretty print with 2-space indentation
        file.close();
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Failed to save instrument definition: " + std::string(e.what());
        return false;
    }
}

InstrumentDefinition SynthGen::createDefaultInstrumentDefinition(const SynthParams& params) {
    InstrumentDefinition def;
    def.name = "default_instrument";
    def.category = "synth";
    def.description = "Default synthesized instrument";
    
    // Configure based on params
    switch (params.waveformType) {
        case WaveformType::SINE: def.voice.oscillator.type = OscillatorType::SINE; break;
        case WaveformType::SQUARE: def.voice.oscillator.type = OscillatorType::SQUARE; break;
        case WaveformType::SAW: def.voice.oscillator.type = OscillatorType::SAW; break;
        case WaveformType::TRIANGLE: def.voice.oscillator.type = OscillatorType::TRIANGLE; break;
        case WaveformType::NOISE: def.voice.oscillator.type = OscillatorType::GRANULAR; break;
        case WaveformType::CUSTOM: def.voice.oscillator.type = OscillatorType::WAVETABLE; break;
    }
    def.voice.oscillator.frequency = params.frequency;
    def.voice.oscillator.amplitude = params.amplitude;
    def.voice.oscillator.phase = params.phase;
    
    // Set envelopes from params
    def.voice.ampEnvelope.attack = params.adsrEnvelope.x;
    def.voice.ampEnvelope.decay = params.adsrEnvelope.y;
    def.voice.ampEnvelope.sustain = params.adsrEnvelope.z;
    def.voice.ampEnvelope.release = params.adsrEnvelope.w;

    // Modulation from the request (x = rate Hz, y = depth 0..1)
    if (params.amplitudeModulation.y > 0.0f) {
        def.voice.lfo.target = ModulationTarget::AMPLITUDE;
        def.voice.lfo.rate = params.amplitudeModulation.x;
        def.voice.lfo.depth = params.amplitudeModulation.y;
    } else if (params.frequencyModulation.y > 0.0f) {
        def.voice.lfo.target = ModulationTarget::FREQUENCY;
        def.voice.lfo.rate = params.frequencyModulation.x;
        def.voice.lfo.depth = params.frequencyModulation.y;
    } else if (params.phaseModulation.y > 0.0f) {
        def.voice.lfo.target = ModulationTarget::PHASE;
        def.voice.lfo.rate = params.phaseModulation.x;
        def.voice.lfo.depth = params.phaseModulation.y;
    } else {
        def.voice.lfo.depth = 0.0f; // no modulation requested
    }
    // Keep the filter open so the requested waveform is heard as specified.
    def.voice.filter.cutoff = std::min(18000.0f, static_cast<float>(m_sampleRate) * 0.45f);
    def.voice.filter.resonance = 0.7071f;

    // A single parameterised note does not produce a variation pack.
    def.variations.enableVariations = false;
    def.variations.enablePitchVariations = false;

    return def;
}

// Synthesis Pipeline Processing
SynthResult SynthGen::processSynthesisPipeline(const InstrumentDefinition& instrumentDef, const SynthParams& params) {
    SynthResult result;
    
    // Step 1: Initialize synthesis engine
    initializeSynthesisEngine(instrumentDef);
    
    // Step 2: Generate base voice
    std::vector<float> baseVoice = synthesizeVoice(instrumentDef.voice, params);
    
    // Step 3: Apply effects chain
    std::vector<float> processedVoice = applyEffectChain(baseVoice, instrumentDef.effects);
    
    // Step 4: Generate variations
    std::vector<VariationSample> variations;
    if (instrumentDef.variations.enableVariations) {
        variations = generateVariations(processedVoice, instrumentDef.variations);
    }

    // Step 5: Generate metadata
    result.synthesisTime = std::chrono::system_clock::now();
    result.metadata = generateMetadata(instrumentDef, variations);
    result.metadata.duration = m_numChannels > 0
        ? static_cast<float>(processedVoice.size()) / (static_cast<float>(m_sampleRate) * m_numChannels)
        : 0.0f;
    
    // Step 6: Package synthesis results
    result.audioData = processedVoice;
    result.variations = variations;
    result.instrumentDef = instrumentDef;
    
    // Step 7: Create synth pack
    result.synthPack = createSynthPack(instrumentDef, result);
    
    return result;
}

// Synthesis Engine Initialization
void SynthGen::initializeSynthesisEngines() {
    // Initialize oscillators
    m_sineOscillator = std::make_unique<SineOscillator>();
    m_squareOscillator = std::make_unique<SquareOscillator>();
    m_sawOscillator = std::make_unique<SawOscillator>();
    m_triangleOscillator = std::make_unique<TriangleOscillator>();
    m_wavetableOscillator = std::make_unique<WavetableOscillator>();
    m_fmOscillator = std::make_unique<FMOscillator>();
    m_granularOscillator = std::make_unique<GranularOscillator>();
    
    // Initialize filters
    m_lowpassFilter = std::make_unique<LowpassFilter>();
    m_highpassFilter = std::make_unique<HighpassFilter>();
    m_bandpassFilter = std::make_unique<BandpassFilter>();
    m_notchFilter = std::make_unique<NotchFilter>();
    
    // Initialize effects
    m_reverbEffect = std::make_unique<ReverbEffect>();
    m_delayEffect = std::make_unique<DelayEffect>();
    m_chorusEffect = std::make_unique<ChorusEffect>();
    m_distortionEffect = std::make_unique<DistortionEffect>();
    m_compressorEffect = std::make_unique<CompressorEffect>();
    m_equalizerEffect = std::make_unique<EqualizerEffect>();
}

void SynthGen::initializeSynthesisEngine(const InstrumentDefinition& instrumentDef) {
    // Set up synthesis parameters
    m_currentSampleRate = m_sampleRate;
    m_currentBufferSize = m_bufferSize;
    
    // Initialize oscillators with instrument settings
    if (m_sineOscillator) m_sineOscillator->initialize(m_currentSampleRate);
    if (m_squareOscillator) m_squareOscillator->initialize(m_currentSampleRate);
    if (m_sawOscillator) m_sawOscillator->initialize(m_currentSampleRate);
    if (m_triangleOscillator) m_triangleOscillator->initialize(m_currentSampleRate);
    if (m_wavetableOscillator) m_wavetableOscillator->initialize(m_currentSampleRate);
    if (m_fmOscillator) m_fmOscillator->initialize(m_currentSampleRate);
    if (m_granularOscillator) m_granularOscillator->initialize(m_currentSampleRate);
    
    // Initialize filters
    if (m_lowpassFilter) m_lowpassFilter->initialize(m_currentSampleRate);
    if (m_highpassFilter) m_highpassFilter->initialize(m_currentSampleRate);
    if (m_bandpassFilter) m_bandpassFilter->initialize(m_currentSampleRate);
    if (m_notchFilter) m_notchFilter->initialize(m_currentSampleRate);
    
    // Initialize effects
    if (m_reverbEffect) m_reverbEffect->initialize(m_currentSampleRate);
    if (m_delayEffect) m_delayEffect->initialize(m_currentSampleRate);
    if (m_chorusEffect) m_chorusEffect->initialize(m_currentSampleRate);
    if (m_distortionEffect) m_distortionEffect->initialize(m_currentSampleRate);
    if (m_compressorEffect) m_compressorEffect->initialize(m_currentSampleRate);
    if (m_equalizerEffect) m_equalizerEffect->initialize(m_currentSampleRate);
}

// Voice Synthesis
std::vector<float> SynthGen::synthesizeVoice(const VoiceDefinition& voice, const SynthParams& params) {
    std::vector<float> audioData;
    size_t numSamples = static_cast<size_t>(params.duration * m_sampleRate);
    audioData.resize(numSamples * m_numChannels);
    
    // Generate oscillator output
    std::vector<float> oscillatorOutput = generateOscillatorOutput(voice.oscillator, numSamples);
    
    // Apply envelope
    std::vector<float> envelopedOutput = applyEnvelope(oscillatorOutput, voice.ampEnvelope);
    
    // Apply filter
    std::vector<float> filteredOutput = applyFilter(envelopedOutput, voice.filter);

    // Apply LFO modulation (cutoff modulation is centred on the voice's filter cutoff)
    LFODefinition lfo = voice.lfo;
    lfo.parameters.emplace("baseCutoff", voice.filter.cutoff);
    std::vector<float> modulatedOutput = applyLFO(filteredOutput, lfo);
    
    // Convert to stereo if needed
    if (m_numChannels == 2) {
        for (size_t i = 0; i < modulatedOutput.size(); ++i) {
            audioData[i * 2] = modulatedOutput[i];     // Left channel
            audioData[i * 2 + 1] = modulatedOutput[i]; // Right channel
        }
    } else {
        audioData = modulatedOutput;
    }
    
    return audioData;
}

// Oscillator Generation
std::vector<float> SynthGen::generateOscillatorOutput(const OscillatorDefinition& osc, size_t numSamples) {
    std::vector<float> output(numSamples);
    
    switch (osc.type) {
        case OscillatorType::SINE:
            output = m_sineOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
        case OscillatorType::SQUARE:
            output = m_squareOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
        case OscillatorType::SAW:
            output = m_sawOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
        case OscillatorType::TRIANGLE:
            output = m_triangleOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
        case OscillatorType::WAVETABLE:
            output = m_wavetableOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples, osc.wavetablePath);
            break;
        case OscillatorType::FM:
            output = m_fmOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
        case OscillatorType::GRANULAR:
            output = m_granularOscillator->generate(osc.frequency, osc.amplitude, osc.phase, numSamples);
            break;
    }
    
    return output;
}

// Envelope Application
std::vector<float> SynthGen::applyEnvelope(const std::vector<float>& input, const ADSR& envelope) {
    std::vector<float> output(input.size());
    
    // Envelope stages are scaled down proportionally when the note is shorter than A+D+R.
    double attackSamples = std::max(0.0f, envelope.attack) * m_sampleRate;
    double decaySamples = std::max(0.0f, envelope.decay) * m_sampleRate;
    double releaseSamples = std::max(0.0f, envelope.release) * m_sampleRate;
    const double envelopeTotal = attackSamples + decaySamples + releaseSamples;
    if (envelopeTotal > static_cast<double>(input.size()) && envelopeTotal > 0.0) {
        const double scale = static_cast<double>(input.size()) / envelopeTotal;
        attackSamples *= scale;
        decaySamples *= scale;
        releaseSamples *= scale;
    }
    const size_t aS = static_cast<size_t>(attackSamples);
    const size_t dS = static_cast<size_t>(decaySamples);
    const size_t rS = static_cast<size_t>(releaseSamples);
    const size_t sustainSamples = input.size() > aS + dS + rS ? input.size() - aS - dS - rS : 0;
    const size_t attackLen = aS;
    const size_t decayLen = dS;
    const size_t releaseLen = std::max<size_t>(1, rS);
    
    for (size_t i = 0; i < input.size(); ++i) {
        float envelopeValue = 0.0f;
        
        if (i < attackLen) {
            // Attack phase
            envelopeValue = static_cast<float>(i) / static_cast<float>(attackLen);
        } else if (i < attackLen + decayLen) {
            // Decay phase
            float decayProgress = static_cast<float>(i - attackLen) / static_cast<float>(decayLen);
            envelopeValue = 1.0f - (1.0f - envelope.sustain) * decayProgress;
        } else if (i < attackLen + decayLen + sustainSamples) {
            // Sustain phase
            envelopeValue = envelope.sustain;
        } else {
            // Release phase
            float releaseProgress = static_cast<float>(i - (attackLen + decayLen + sustainSamples)) / static_cast<float>(releaseLen);
            envelopeValue = envelope.sustain * std::max(0.0f, 1.0f - releaseProgress);
        }
        
        output[i] = input[i] * envelopeValue;
    }
    
    return output;
}

// Filter Application
std::vector<float> SynthGen::applyFilter(const std::vector<float>& input, const FilterDefinition& filter) {
    std::vector<float> output(input.size());
    
    switch (filter.type) {
        case FilterType::LOWPASS:
            output = m_lowpassFilter->process(input, filter.cutoff, filter.resonance);
            break;
        case FilterType::HIGHPASS:
            output = m_highpassFilter->process(input, filter.cutoff, filter.resonance);
            break;
        case FilterType::BANDPASS:
            output = m_bandpassFilter->process(input, filter.cutoff, filter.resonance);
            break;
        case FilterType::NOTCH:
            output = m_notchFilter->process(input, filter.cutoff, filter.resonance);
            break;
    }
    
    return output;
}

// LFO Application (operates on the mono voice signal)
std::vector<float> SynthGen::applyLFO(const std::vector<float>& input, const LFODefinition& lfo) {
    if (lfo.depth == 0.0f || lfo.rate <= 0.0f || input.empty()) {
        return input;
    }
    std::vector<float> output(input.size());
    const float sr = static_cast<float>(m_sampleRate);
    
    switch (lfo.target) {
        case ModulationTarget::AMPLITUDE: {
            // Tremolo: depth is a 0..1 modulation index (values > 1 are treated as percent)
            const float index = std::clamp(lfo.depth > 1.0f ? lfo.depth / 100.0f : lfo.depth, 0.0f, 1.0f);
            for (size_t i = 0; i < input.size(); ++i) {
                const float l = generateLFOValue(lfo.waveform, lfo.rate, 1.0f, lfo.phase, i / sr);
                output[i] = input[i] * (1.0f - index * 0.5f * (1.0f - l));
            }
            break;
        }
        case ModulationTarget::FREQUENCY:
        case ModulationTarget::PHASE: {
            // Vibrato / phase modulation through a modulated fractional delay line.
            // depth: 0..1 (or percent) of a 5 ms maximum excursion.
            const float index = std::clamp(lfo.depth > 1.0f ? lfo.depth / 100.0f : lfo.depth, 0.0f, 1.0f);
            const float maxDelay = 0.005f * sr * index;
            for (size_t i = 0; i < input.size(); ++i) {
                const float l = generateLFOValue(lfo.waveform, lfo.rate, 1.0f, lfo.phase, i / sr);
                const float delay = maxDelay * 0.5f * (1.0f + l);
                const float readPos = static_cast<float>(i) - delay;
                if (readPos <= 0.0f) {
                    output[i] = input[0];
                    continue;
                }
                const size_t i0 = static_cast<size_t>(readPos);
                const size_t i1 = std::min(i0 + 1, input.size() - 1);
                const float frac = readPos - static_cast<float>(i0);
                output[i] = input[i0] + (input[i1] - input[i0]) * frac;
            }
            break;
        }
        case ModulationTarget::CUTOFF: {
            // Time-varying one-pole low-pass; depth is the cutoff swing in Hz.
            auto base = lfo.parameters.find("baseCutoff");
            const float baseCutoff = base != lfo.parameters.end() ? base->second : 2000.0f;
            float state = 0.0f;
            for (size_t i = 0; i < input.size(); ++i) {
                const float l = generateLFOValue(lfo.waveform, lfo.rate, 1.0f, lfo.phase, i / sr);
                const float cutoff = std::clamp(baseCutoff + lfo.depth * l, 20.0f, sr * 0.45f);
                const float alpha = 1.0f - std::exp(-TWO_PI * cutoff / sr);
                state += alpha * (input[i] - state);
                output[i] = state;
            }
            break;
        }
    }
    
    return output;
}

// LFO Value Generation
float SynthGen::generateLFOValue(WaveformType waveform, float rate, float depth, float phase, float time) {
    float lfoPhase = TWO_PI * rate * time + phase;
    float lfoValue = 0.0f;
    
    switch (waveform) {
        case WaveformType::SINE:
        case WaveformType::CUSTOM:
            lfoValue = std::sin(lfoPhase);
            break;
        case WaveformType::SQUARE:
            lfoValue = std::sin(lfoPhase) > 0.0f ? 1.0f : -1.0f;
            break;
        case WaveformType::SAW:
            lfoValue = 2.0f * (lfoPhase / TWO_PI - std::floor(lfoPhase / TWO_PI + 0.5f));
            break;
        case WaveformType::TRIANGLE:
            lfoValue = 2.0f * std::abs(2.0f * (lfoPhase / TWO_PI - std::floor(lfoPhase / TWO_PI + 0.5f))) - 1.0f;
            break;
        case WaveformType::NOISE: {
            // Sample-and-hold noise: a new deterministic random value every LFO cycle
            const uint64_t cycle = static_cast<uint64_t>(std::max(0.0f, lfoPhase / TWO_PI));
            uint64_t x = cycle * 0x9E3779B97F4A7C15ULL + 0x632BE59BD9B4E019ULL;
            x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33;
            lfoValue = static_cast<float>(x % 20001ULL) / 10000.0f - 1.0f;
            break;
        }
    }
    
    return lfoValue * depth;
}

// Effect Chain Application
std::vector<float> SynthGen::applyEffectChain(const std::vector<float>& input, const std::vector<EffectDefinition>& effects) {
    std::vector<float> output = input;
    
    for (const auto& effect : effects) {
        if (!effect.enabled) continue;
        output = applyEffect(output, effect);
    }
    
    return output;
}

std::vector<float> SynthGen::applyEffect(const std::vector<float>& input, const EffectDefinition& effect) {
    switch (effect.type) {
        case EffectType::REVERB:
            return m_reverbEffect->process(input, effect.parameters);
        case EffectType::DELAY:
            return m_delayEffect->process(input, effect.parameters);
        case EffectType::CHORUS:
            return m_chorusEffect->process(input, effect.parameters);
        case EffectType::FLANGER: {
            // Flanger = short, fast-modulated chorus
            std::map<std::string, float> p = effect.parameters;
            p.emplace("rate", 0.25f);
            p.emplace("depth", 0.001f);
            p.emplace("mix", 0.7f);
            return m_chorusEffect->process(input, p);
        }
        case EffectType::DISTORTION:
            return m_distortionEffect->process(input, effect.parameters);
        case EffectType::COMPRESSOR:
            return m_compressorEffect->process(input, effect.parameters);
        case EffectType::EQUALIZER:
            return m_equalizerEffect->process(input, effect.parameters);
        case EffectType::FILTER: {
            auto get = [&](const char* k, float d) {
                auto it = effect.parameters.find(k);
                return it != effect.parameters.end() ? it->second : d;
            };
            return m_lowpassFilter->process(input, get("cutoff", 2000.0f), get("resonance", 0.7071f));
        }
    }
    return input;
}
// Variation Generation
std::vector<VariationSample> SynthGen::generateVariations(const std::vector<float>& baseVoice, const VariationSettings& variations) {
    std::vector<VariationSample> samples;
    
    // Generate pitch variations (only the unshifted voice when pitch variations are off)
    const int first = variations.enablePitchVariations ? variations.pitchRange.first : 0;
    const int last = variations.enablePitchVariations ? variations.pitchRange.second : 0;
    for (int semitone = first; semitone <= last; ++semitone) {
        VariationSample sample;
        sample.midiNote = 60 + semitone; // C4 = 60
        sample.pitchShift = semitone;
        sample.name = "note_" + std::to_string(sample.midiNote) + (semitone < 0 ? "_m" : "_p") + std::to_string(std::abs(semitone));
        sample.description = "Pitch variation " + std::string(semitone < 0 ? "" : "+") + std::to_string(semitone) +
                             " semitones (MIDI " + std::to_string(sample.midiNote) + ")";
        sample.generationTime = std::chrono::system_clock::now();
        sample.parameters["pitchShift"] = static_cast<float>(semitone);
        
        // Apply pitch shifting
        sample.audioData = pitchShift(baseVoice, semitone);
        
        // Apply time stretching if enabled
        if (variations.timeStretch.enabled) {
            sample.stretchedData = timeStretch(sample.audioData, variations.timeStretch);
        }
        
        // Apply randomization if enabled
        if (variations.randomization.enabled && (variations.enableRandomVariations || variations.randomization.amount > 0.0f)) {
            applyRandomization(sample.audioData, variations.randomization);
        }
        
        samples.push_back(std::move(sample));
    }
    
    return samples;
}

// Pitch Shifting
std::vector<float> SynthGen::pitchShift(const std::vector<float>& input, int semitones) {
    float pitchRatio = std::pow(SEMITONE_RATIO, semitones);
    
    std::vector<float> output;
    output.reserve(static_cast<size_t>(input.size() * pitchRatio));
    
    for (size_t i = 0; i < input.size(); ++i) {
        float readIndex = i / pitchRatio;
        size_t readIndexInt = static_cast<size_t>(readIndex);
        
        if (readIndexInt < input.size() - 1) {
            float fraction = readIndex - readIndexInt;
            float interpolated = input[readIndexInt] * (1.0f - fraction) + input[readIndexInt + 1] * fraction;
            output.push_back(interpolated);
        }
    }
    
    return output;
}

// Time Stretching
std::vector<float> SynthGen::timeStretch(const std::vector<float>& input, const TimeStretchSettings& settings) {
    // Simple time stretching using overlap-add method
    std::vector<float> output;
    size_t windowSize = settings.windowSize;
    size_t hopSize = static_cast<size_t>(windowSize * (1.0f - settings.overlap));
    
    for (size_t i = 0; i < input.size(); i += hopSize) {
        std::vector<float> window(windowSize);
        
        // Extract window
        for (size_t j = 0; j < windowSize && i + j < input.size(); ++j) {
            window[j] = input[i + j];
        }
        
        // Apply window function (Hann window)
        for (size_t j = 0; j < windowSize; ++j) {
            float windowValue = 0.5f * (1.0f - std::cos(TWO_PI * j / (windowSize - 1)));
            window[j] *= windowValue;
        }
        
        // Add to output
        for (size_t j = 0; j < windowSize && output.size() + j < input.size(); ++j) {
            if (output.size() <= i + j) {
                output.resize(i + j + 1);
            }
            output[i + j] += window[j];
        }
    }
    
    return output;
}

// Randomization
void SynthGen::applyRandomization(std::vector<float>& audio, const RandomizationSettings& settings) {
    thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
    
    for (float& sample : audio) {
        float randomValue = dis(gen) * settings.amount;
        sample += randomValue;
        sample = clamp(sample, -1.0f, 1.0f);
    }
}

// Metadata Generation
SynthMetadata SynthGen::generateMetadata(const InstrumentDefinition& instrumentDef, const std::vector<VariationSample>& variations) {
    SynthMetadata metadata;
    
    metadata.instrumentName = instrumentDef.name;
    metadata.category = instrumentDef.category;
    metadata.description = instrumentDef.description;
    metadata.sampleRate = m_sampleRate;
    metadata.bitDepth = 24; // Assume 24-bit
    metadata.channels = m_numChannels;
    metadata.duration = 5.0f; // Default duration
    
    // Voice parameters
    metadata.voiceParams.oscillatorType = instrumentDef.voice.oscillator.type;
    metadata.voiceParams.frequency = instrumentDef.voice.oscillator.frequency;
    metadata.voiceParams.amplitude = instrumentDef.voice.oscillator.amplitude;
    metadata.voiceParams.ampEnvelope = instrumentDef.voice.ampEnvelope;
    metadata.voiceParams.filterEnvelope = instrumentDef.voice.filterEnvelope;
    metadata.voiceParams.filterType = instrumentDef.voice.filter.type;
    metadata.voiceParams.filterCutoff = instrumentDef.voice.filter.cutoff;
    metadata.voiceParams.filterResonance = instrumentDef.voice.filter.resonance;
    
    // Variation information
    metadata.pitchRange = instrumentDef.variations.pitchRange;
    metadata.numVariations = static_cast<int>(variations.size());
    metadata.timeStretchEnabled = instrumentDef.variations.timeStretch.enabled;
    metadata.randomizationEnabled = instrumentDef.variations.randomization.enabled;
    
    // Effect chain
    metadata.effects = instrumentDef.effects;
    
    // Timbre tags
    metadata.timbreTags = generateTimbreTags(instrumentDef);
    
    return metadata;
}

// Timbre Tag Generation
std::vector<std::string> SynthGen::generateTimbreTags(const InstrumentDefinition& instrumentDef) {
    std::vector<std::string> tags;
    
    // Add oscillator type tags
    switch (instrumentDef.voice.oscillator.type) {
        case OscillatorType::SINE:
            tags.push_back("sine");
            tags.push_back("pure");
            break;
        case OscillatorType::SQUARE:
            tags.push_back("square");
            tags.push_back("harsh");
            break;
        case OscillatorType::SAW:
            tags.push_back("saw");
            tags.push_back("bright");
            break;
        case OscillatorType::TRIANGLE:
            tags.push_back("triangle");
            tags.push_back("warm");
            break;
        case OscillatorType::WAVETABLE:
            tags.push_back("wavetable");
            tags.push_back("complex");
            break;
        case OscillatorType::FM:
            tags.push_back("fm");
            tags.push_back("metallic");
            break;
        case OscillatorType::GRANULAR:
            tags.push_back("granular");
            tags.push_back("textural");
            break;
    }
    
    // Add filter type tags
    switch (instrumentDef.voice.filter.type) {
        case FilterType::LOWPASS:
            tags.push_back("lowpass");
            tags.push_back("dark");
            break;
        case FilterType::HIGHPASS:
            tags.push_back("highpass");
            tags.push_back("bright");
            break;
        case FilterType::BANDPASS:
            tags.push_back("bandpass");
            tags.push_back("focused");
            break;
        case FilterType::NOTCH:
            tags.push_back("notch");
            tags.push_back("hollow");
            break;
    }
    
    // Add effect tags
    for (const auto& effect : instrumentDef.effects) {
        switch (effect.type) {
            case EffectType::REVERB:
                tags.push_back("reverb");
                tags.push_back("spatial");
                break;
            case EffectType::DELAY:
                tags.push_back("delay");
                tags.push_back("echo");
                break;
            case EffectType::CHORUS:
                tags.push_back("chorus");
                tags.push_back("thick");
                break;
            case EffectType::DISTORTION:
                tags.push_back("distortion");
                tags.push_back("aggressive");
                break;
            case EffectType::COMPRESSOR:
                tags.push_back("compressed");
                break;
            case EffectType::EQUALIZER:
                tags.push_back("eq");
                break;
            case EffectType::FLANGER:
                tags.push_back("flanger");
                tags.push_back("swirling");
                break;
            case EffectType::FILTER:
                tags.push_back("filtered");
                break;
        }
    }
    
    // Add category tags
    tags.push_back(instrumentDef.category);
    
    return tags;
}

// Synth Pack Creation
// Writes packs/<instrument>.synthpack.json, one WAV per variation (packs/<instrument>_<variation>.wav)
// and the packs/<instrument>.synthpack archive ("SYNTHPACK" + metadata + [name, size, wav]...).
SynthPack SynthGen::createSynthPack(const InstrumentDefinition& instrumentDef, const SynthResult& result) {
    SynthPack pack;
    
    pack.name = instrumentDef.name;
    pack.version = "1.0.0";
    pack.metadata = result.metadata;
    pack.variations = result.variations;
    pack.instrumentDef = instrumentDef;
    pack.creationTime = std::chrono::system_clock::now();
    
    // Encode every variation as PCM WAV (interleaved, m_numChannels channels)
    std::vector<std::vector<uint8_t>> wavFiles;
    std::vector<uint8_t> allAudio;
    for (auto& variation : pack.variations) {
        std::vector<uint8_t> wav = FileIO::encodeWav(variation.audioData, m_sampleRate,
                                                     static_cast<uint16_t>(m_numChannels), 16);
        variation.filename = instrumentDef.name + "_" + variation.name + ".wav";
        variation.fileSize = wav.size();
        variation.checksum = FileIO::sha256Hex(wav.data(), wav.size());
        allAudio.insert(allAudio.end(), wav.begin(), wav.end());
        wavFiles.push_back(std::move(wav));
    }
    pack.totalSize = allAudio.size();
    pack.checksum = FileIO::sha256Hex(allAudio.data(), allAudio.size());
    
    // A pack is the set of rendered variations; nothing to write without any.
    if (pack.variations.empty()) {
        return pack;
    }
    
    const std::filesystem::path packDir = "packs";
    std::error_code ec;
    std::filesystem::create_directories(packDir, ec);
    if (ec) {
        m_lastError = "Could not create pack directory: " + ec.message();
        return pack;
    }
    const std::string packFilename = (packDir / (instrumentDef.name + ".synthpack")).string();
    pack.filePath = packFilename;
    
    // Pack metadata
    nlohmann::json packJson;
    packJson["name"] = instrumentDef.name;
    packJson["version"] = pack.version;
    packJson["description"] = instrumentDef.description;
    packJson["category"] = instrumentDef.category;
    packJson["author"] = "MagiTech Audio Generator";
    packJson["created"] = pack.creationTime.time_since_epoch().count();
    packJson["sampleRate"] = m_sampleRate;
    packJson["channels"] = m_numChannels;
    packJson["checksum"] = pack.checksum;
    packJson["timbreTags"] = pack.metadata.timbreTags;
    packJson["variations"] = nlohmann::json::array();
    for (const auto& variation : pack.variations) {
        nlohmann::json varJson;
        varJson["name"] = variation.name;
        varJson["description"] = variation.description;
        varJson["midiNote"] = variation.midiNote;
        varJson["pitchShift"] = variation.pitchShift;
        varJson["audioFile"] = variation.filename;
        varJson["size"] = variation.fileSize;
        varJson["sha256"] = variation.checksum;
        packJson["variations"].push_back(varJson);
    }
    const std::string metadataStr = packJson.dump(2);
    
    std::ofstream metadataFile(packFilename + ".json");
    if (metadataFile.is_open()) {
        metadataFile << metadataStr;
    } else {
        m_lastError = "Could not write pack metadata: " + packFilename + ".json";
    }
    
    // Individual WAV files
    for (size_t i = 0; i < pack.variations.size(); ++i) {
        const std::string audioFilename = (packDir / pack.variations[i].filename).string();
        if (!FileIO::writeFileBytes(audioFilename, wavFiles[i])) {
            m_lastError = "Could not write variation audio: " + audioFilename;
        }
    }
    
    // Archive: header, metadata block, then [name length, name, size, data] per variation
    std::vector<uint8_t> archive;
    auto putU32 = [&archive](uint32_t v) {
        for (int b = 0; b < 4; ++b) archive.push_back(static_cast<uint8_t>((v >> (8 * b)) & 0xFF));
    };
    const std::string header = "SYNTHPACK";
    archive.insert(archive.end(), header.begin(), header.end());
    const std::string compactMeta = packJson.dump();
    putU32(static_cast<uint32_t>(compactMeta.size()));
    archive.insert(archive.end(), compactMeta.begin(), compactMeta.end());
    for (size_t i = 0; i < pack.variations.size(); ++i) {
        const std::string& name = pack.variations[i].name;
        putU32(static_cast<uint32_t>(name.size()));
        archive.insert(archive.end(), name.begin(), name.end());
        putU32(static_cast<uint32_t>(wavFiles[i].size()));
        archive.insert(archive.end(), wavFiles[i].begin(), wavFiles[i].end());
    }
    if (!FileIO::writeFileBytes(packFilename, archive)) {
        m_lastError = "Could not write synth pack: " + packFilename;
    }
    
    return pack;
}
// Oscillator Implementations
std::vector<float> SynthGen::SineOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    std::vector<float> output(numSamples);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        output[i] = amplitude * std::sin(TWO_PI * frequency * time + phase);
    }
    
    return output;
}

std::vector<float> SynthGen::SquareOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    std::vector<float> output(numSamples);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        float value = std::sin(TWO_PI * frequency * time + phase);
        output[i] = amplitude * (value > 0.0f ? 1.0f : -1.0f);
    }
    
    return output;
}

std::vector<float> SynthGen::SawOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    std::vector<float> output(numSamples);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        float value = 2.0f * (frequency * time + phase / TWO_PI - std::floor(frequency * time + phase / TWO_PI + 0.5f));
        output[i] = amplitude * value;
    }
    
    return output;
}

std::vector<float> SynthGen::TriangleOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    std::vector<float> output(numSamples);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        float value = 2.0f * std::abs(2.0f * (frequency * time + phase / TWO_PI - std::floor(frequency * time + phase / TWO_PI + 0.5f))) - 1.0f;
        output[i] = amplitude * value;
    }
    
    return output;
}

std::vector<float> SynthGen::WavetableOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples, const std::string& wavetablePath) {
    // Wavetables are loaded once per path (one cycle = up to the first 1024 mono frames of the file)
    static std::mutex cacheMutex;
    static std::map<std::string, std::vector<float>> wavetableCache;

    std::vector<float> wavetable;
    {
        std::lock_guard<std::mutex> lock(cacheMutex);
        auto cached = wavetableCache.find(wavetablePath);
        if (cached != wavetableCache.end()) {
            wavetable = cached->second;
        }
    }

    if (wavetable.empty()) {
        if (!wavetablePath.empty()) {
            FileIO::DecodedAudio decoded;
            std::string error;
            if (FileIO::decodeFile(wavetablePath, decoded, error)) {
                std::vector<float> mono = FileIO::convertChannels(decoded.samples, decoded.channels, 1);
                if (mono.size() > 1024) mono.resize(1024);
                wavetable = std::move(mono);
            }
        }

        // If loading failed, generate a default wavetable
        if (wavetable.empty()) {
            wavetable.resize(1024);
            for (size_t i = 0; i < wavetable.size(); ++i) {
                float t = static_cast<float>(i) / wavetable.size();
                // Generate a complex waveform
                wavetable[i] = 0.5f * std::sin(TWO_PI * t) +
                              0.25f * std::sin(TWO_PI * 3.0f * t) +
                              0.125f * std::sin(TWO_PI * 5.0f * t);
            }
        }

        std::lock_guard<std::mutex> lock(cacheMutex);
        wavetableCache[wavetablePath] = wavetable;
    }

    std::vector<float> output(numSamples);
    
    // Generate wavetable output with interpolation
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        float phaseOffset = phase + frequency * time;
        
        // Calculate wavetable position
        float tablePos = (phaseOffset - std::floor(phaseOffset)) * wavetable.size();
        size_t index1 = static_cast<size_t>(tablePos) % wavetable.size();
        size_t index2 = (index1 + 1) % wavetable.size();
        float frac = tablePos - std::floor(tablePos);
        
        // Linear interpolation
        float sample = wavetable[index1] * (1.0f - frac) + wavetable[index2] * frac;
        output[i] = amplitude * sample;
    }
    
    return output;
}

std::vector<float> SynthGen::FMOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    // Implement FM synthesis with modulation index
    float modulationIndex = 5.0f; // Default modulation depth
    float carrierFreq = frequency;
    float modulatorFreq = frequency * 2.0f; // Default modulator frequency
    
    std::vector<float> output(numSamples);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        
        // Generate modulator signal
        float modulator = std::sin(TWO_PI * modulatorFreq * time);
        
        // Apply frequency modulation
        float modulatedFreq = carrierFreq + modulationIndex * modulator;
        
        // Generate carrier signal with modulated frequency
        float carrier = std::sin(TWO_PI * modulatedFreq * time + phase);
        
        output[i] = amplitude * carrier;
    }
    
    return output;
}

std::vector<float> SynthGen::GranularOscillator::generate(float frequency, float amplitude, float phase, size_t numSamples) {
    // Implement granular synthesis
    size_t grainSize = 512; // Default grain size in samples
    size_t grainOverlap = 256; // Overlap between grains
    float grainRate = frequency / 100.0f; // Grains per second
    
    std::vector<float> output(numSamples, 0.0f);
    
    // Generate source signal (sine wave for simplicity)
    std::vector<float> sourceSignal(numSamples);
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / m_sampleRate;
        sourceSignal[i] = std::sin(TWO_PI * frequency * time + phase);
    }
    
    // Generate grains
    size_t grainSpacing = static_cast<size_t>(m_sampleRate / grainRate);
    size_t numGrains = (numSamples + grainSpacing - 1) / grainSpacing;
    
    for (size_t grain = 0; grain < numGrains; ++grain) {
        size_t grainStart = grain * grainSpacing;
        
        // Generate window function (Hanning window)
        std::vector<float> window(grainSize);
        for (size_t i = 0; i < grainSize; ++i) {
            float windowPos = static_cast<float>(i) / grainSize;
            window[i] = 0.5f * (1.0f - std::cos(TWO_PI * windowPos));
        }
        
        // Apply grain to output
        for (size_t i = 0; i < grainSize && (grainStart + i) < numSamples; ++i) {
            size_t outputIndex = grainStart + i;
            size_t sourceIndex = (grainStart + i) % sourceSignal.size();
            
            float grainSample = sourceSignal[sourceIndex] * window[i];
            output[outputIndex] += grainSample;
        }
    }
    
    // Normalize and apply amplitude
    float maxAmplitude = 0.0f;
    for (float sample : output) {
        maxAmplitude = std::max(maxAmplitude, std::abs(sample));
    }
    
    if (maxAmplitude > 0.0f) {
        for (size_t i = 0; i < output.size(); ++i) {
            output[i] = amplitude * (output[i] / maxAmplitude);
        }
    }
    
    return output;
}

// Filter Implementations
std::vector<float> SynthGen::LowpassFilter::process(const std::vector<float>& input, float cutoff, float resonance) {
    std::vector<float> output(input.size());
    
    float omega = TWO_PI * cutoff / m_sampleRate;
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
    for (size_t i = 0; i < input.size(); ++i) {
        float outputSample = b0 * input[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = input[i]; y2 = y1; y1 = outputSample;
        output[i] = outputSample;
    }
    
    return output;
}

std::vector<float> SynthGen::HighpassFilter::process(const std::vector<float>& input, float cutoff, float resonance) {
    std::vector<float> output(input.size());
    
    float omega = TWO_PI * cutoff / m_sampleRate;
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
    for (size_t i = 0; i < input.size(); ++i) {
        float outputSample = b0 * input[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = input[i]; y2 = y1; y1 = outputSample;
        output[i] = outputSample;
    }
    
    return output;
}

std::vector<float> SynthGen::BandpassFilter::process(const std::vector<float>& input, float cutoff, float resonance) {
    std::vector<float> output(input.size());
    
    float omega = TWO_PI * cutoff / m_sampleRate;
    float alpha = std::sin(omega) / (2.0f * resonance);
    
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
    for (size_t i = 0; i < input.size(); ++i) {
        float outputSample = b0 * input[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = input[i]; y2 = y1; y1 = outputSample;
        output[i] = outputSample;
    }
    
    return output;
}

std::vector<float> SynthGen::NotchFilter::process(const std::vector<float>& input, float cutoff, float resonance) {
    std::vector<float> output(input.size());
    
    float omega = TWO_PI * cutoff / m_sampleRate;
    float alpha = std::sin(omega) / (2.0f * resonance);
    
    float b0 = 1.0f;
    float b1 = -2.0f * std::cos(omega);
    float b2 = 1.0f;
    float a1 = -2.0f * std::cos(omega);
    float a2 = 1.0f - alpha;
    
    // Normalize
    float norm = 1.0f + alpha;
    b0 /= norm; b1 /= norm; b2 /= norm; a1 /= norm; a2 /= norm;
    
    // Apply filter
    float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;
    for (size_t i = 0; i < input.size(); ++i) {
        float outputSample = b0 * input[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = input[i]; y2 = y1; y1 = outputSample;
        output[i] = outputSample;
    }
    
    return output;
}

// Effect Implementations
std::vector<float> SynthGen::ReverbEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement Schroeder reverb algorithm
    float roomSize = getParameter(parameters, "roomSize", 0.5f);
    float damping = getParameter(parameters, "damping", 0.5f);
    float wetLevel = getParameter(parameters, "wetLevel", 0.33f);
    float dryLevel = getParameter(parameters, "dryLevel", 0.4f);
    float width = getParameter(parameters, "width", 1.0f);
    
    std::vector<float> output(input.size());
    
    // Initialize delay lines for reverb
    static const size_t numCombs = 4;
    static const size_t numAllpasses = 2;
    
    // Comb filter delay times (in samples)
    static const size_t combDelays[numCombs] = {1116, 1188, 1277, 1356};
    // Allpass filter delay times
    static const size_t allpassDelays[numAllpasses] = {556, 441};
    
    // Initialize delay lines (static to persist between calls)
    std::vector<std::vector<float>> combBuffers(numCombs);
    std::vector<std::vector<float>> allpassBuffers(numAllpasses);
    std::vector<size_t> combIndices(numCombs, 0);
    std::vector<size_t> allpassIndices(numAllpasses, 0);
    
    // Initialize buffers if needed
    for (size_t i = 0; i < numCombs; ++i) {
        if (combBuffers[i].size() != combDelays[i]) {
            combBuffers[i].resize(combDelays[i], 0.0f);
        }
    }
    for (size_t i = 0; i < numAllpasses; ++i) {
        if (allpassBuffers[i].size() != allpassDelays[i]) {
            allpassBuffers[i].resize(allpassDelays[i], 0.0f);
        }
    }
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Apply comb filters
        float combOutput = 0.0f;
        for (size_t j = 0; j < numCombs; ++j) {
            float delayed = combBuffers[j][combIndices[j]];
            combBuffers[j][combIndices[j]] = inputSample + roomSize * delayed;
            combOutput += delayed;
            combIndices[j] = (combIndices[j] + 1) % combDelays[j];
        }
        combOutput /= numCombs;
        
        // Apply allpass filters
        float allpassOutput = combOutput;
        for (size_t j = 0; j < numAllpasses; ++j) {
            float delayed = allpassBuffers[j][allpassIndices[j]];
            allpassBuffers[j][allpassIndices[j]] = allpassOutput + roomSize * delayed;
            allpassOutput = delayed - roomSize * allpassBuffers[j][allpassIndices[j]];
            allpassIndices[j] = (allpassIndices[j] + 1) % allpassDelays[j];
        }
        
        // Mix dry and wet signals
        output[i] = dryLevel * inputSample + wetLevel * allpassOutput;
    }
    
    return output;
}

std::vector<float> SynthGen::DelayEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement delay effect with feedback
    float delayTime = getParameter(parameters, "delayTime", 0.5f);
    float feedback = getParameter(parameters, "feedback", 0.3f);
    float wetLevel = getParameter(parameters, "wetLevel", 0.5f);
    
    size_t delaySamples = std::max<size_t>(1, static_cast<size_t>(delayTime * m_sampleRate));
    std::vector<float> output(input.size());
    
    // Initialize delay buffer
    std::vector<float> delayBuffer;
    size_t delayIndex = 0;
    
    if (delayBuffer.size() != delaySamples) {
        delayBuffer.resize(delaySamples, 0.0f);
        delayIndex = 0;
    }
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        float delayedSample = delayBuffer[delayIndex];
        
        // Mix input with feedback
        delayBuffer[delayIndex] = inputSample + feedback * delayedSample;
        delayIndex = (delayIndex + 1) % delaySamples;
        
        // Mix dry and wet signals
        output[i] = inputSample + wetLevel * delayedSample;
    }
    
    return output;
}

std::vector<float> SynthGen::ChorusEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement chorus effect with LFO modulation
    float rate = getParameter(parameters, "rate", 1.5f);
    float depth = getParameter(parameters, "depth", 0.002f);
    float mix = getParameter(parameters, "mix", 0.5f);
    
    std::vector<float> output(input.size());
    
    // Initialize delay buffer for chorus
    std::vector<float> chorusBuffer(std::max<size_t>(2, static_cast<size_t>(0.03f * m_sampleRate)), 0.0f);
    size_t chorusIndex = 0;
    float lfoPhase = 0.0f;
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Generate LFO for modulation
        float lfoValue = std::sin(TWO_PI * rate * i / m_sampleRate + lfoPhase);
        float modulatedDelay = 0.01f + depth * lfoValue; // Base delay + modulation
        size_t delaySamples = static_cast<size_t>(modulatedDelay * m_sampleRate);
        
        // Get delayed sample with interpolation
        size_t readIndex = (chorusIndex + chorusBuffer.size() - delaySamples) % chorusBuffer.size();
        float delayedSample = chorusBuffer[readIndex];
        
        // Update delay buffer
        chorusBuffer[chorusIndex] = inputSample;
        chorusIndex = (chorusIndex + 1) % chorusBuffer.size();
        
        // Mix dry and wet signals
        output[i] = inputSample + mix * delayedSample;
    }
    
    lfoPhase += TWO_PI * rate / m_sampleRate;
    return output;
}

std::vector<float> SynthGen::DistortionEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement soft clipping distortion
    float drive = getParameter(parameters, "drive", 0.5f);
    float range = getParameter(parameters, "range", 2400.0f);
    float blend = getParameter(parameters, "blend", 0.5f);
    
    std::vector<float> output(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Apply drive
        float driven = inputSample * (1.0f + drive * 10.0f);
        
        // Soft clipping using tanh
        float clipped = std::tanh(driven / range);
        
        // Blend between original and distorted
        output[i] = (1.0f - blend) * inputSample + blend * clipped;
    }
    
    return output;
}

std::vector<float> SynthGen::CompressorEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement dynamic range compression
    float threshold = getParameter(parameters, "threshold", -20.0f);
    float ratio = getParameter(parameters, "ratio", 4.0f);
    float attack = getParameter(parameters, "attack", 0.003f);
    float release = getParameter(parameters, "release", 0.25f);
    
    std::vector<float> output(input.size());
    
    float attackCoeff = std::exp(-1.0f / (attack * m_sampleRate));
    float releaseCoeff = std::exp(-1.0f / (release * m_sampleRate));
    float envelope = 0.0f;
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Calculate input level in dB
        float inputLevel = 20.0f * std::log10(std::abs(inputSample) + 1e-6f);
        
        // Calculate gain reduction
        float gainReduction = 0.0f;
        if (inputLevel > threshold) {
            gainReduction = (inputLevel - threshold) * (1.0f - 1.0f / ratio);
        }
        
        // Smooth the gain reduction
        if (gainReduction > envelope) {
            envelope = attackCoeff * (envelope - gainReduction) + gainReduction;
        } else {
            envelope = releaseCoeff * (envelope - gainReduction) + gainReduction;
        }
        
        // Apply gain reduction
        float gain = std::pow(10.0f, -envelope / 20.0f);
        output[i] = inputSample * gain;
    }
    
    return output;
}

std::vector<float> SynthGen::EqualizerEffect::process(const std::vector<float>& input, const std::map<std::string, float>& parameters) {
    // Implement 3-band equalizer (low, mid, high)
    float lowGain = getParameter(parameters, "lowGain", 0.0f);
    float midGain = getParameter(parameters, "midGain", 0.0f);
    float highGain = getParameter(parameters, "highGain", 0.0f);
    float lowFreq = getParameter(parameters, "lowFreq", 250.0f);
    float highFreq = getParameter(parameters, "highFreq", 4000.0f);
    
    std::vector<float> output(input.size());
    
    // Simple IIR filter implementation for 3 bands
    float lowState[2] = {0.0f, 0.0f};
    float highState[2] = {0.0f, 0.0f};
    
    // Calculate filter coefficients
    float lowOmega = TWO_PI * lowFreq / m_sampleRate;
    float highOmega = TWO_PI * highFreq / m_sampleRate;
    
    float lowAlpha = std::sin(lowOmega) / (2.0f * 0.707f);
    float highAlpha = std::sin(highOmega) / (2.0f * 0.707f);
    
    for (size_t i = 0; i < input.size(); ++i) {
        float inputSample = input[i];
        
        // Low-pass filter for low band
        float lowOutput = lowAlpha * (inputSample + 2.0f * lowState[0] + lowState[1]);
        lowState[1] = lowState[0];
        lowState[0] = inputSample;
        
        // High-pass filter for high band
        float highOutput = highAlpha * (inputSample - 2.0f * highState[0] + highState[1]);
        highState[1] = highState[0];
        highState[0] = inputSample;
        
        // Mid band is input minus low and high
        float midOutput = inputSample - lowOutput - highOutput;
        
        // Apply gains and sum
        output[i] = std::pow(10.0f, lowGain / 20.0f) * lowOutput +
                   std::pow(10.0f, midGain / 20.0f) * midOutput +
                   std::pow(10.0f, highGain / 20.0f) * highOutput;
    }
    
    return output;
}

// Quality calculation functions
float SynthGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float SynthGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float SynthGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float SynthGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void SynthGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void SynthGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void SynthGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void SynthGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void SynthGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string SynthGen::getLastError() const {
    return m_lastError;
}

void SynthGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float SynthGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech 
