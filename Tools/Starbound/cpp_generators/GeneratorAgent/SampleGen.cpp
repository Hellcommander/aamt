#include "SampleGen.hpp"
#include "AudioFileIO.hpp"
#include "core/Log.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <algorithm>
#include <cmath>
#include <complex>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>

namespace MagiTech {
namespace Audio {

namespace {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;
constexpr float SEMITONE_RATIO = 1.059463094359f;
constexpr size_t DEFAULT_SAMPLE_RATE = 44100;
constexpr size_t DEFAULT_BUFFER_SIZE = 1024;
constexpr float SILENCE_THRESHOLD = 0.01f;
constexpr float LOOP_CROSSFADE_DURATION = 0.1f; // seconds

// Mixes interleaved audio down to mono.
std::vector<float> toMono(const std::vector<float>& audio, uint32_t channels) {
    if (channels <= 1) return audio;
    return FileIO::convertChannels(audio, channels, 1);
}

// In-place iterative radix-2 FFT (size must be a power of two).
void fft(std::vector<std::complex<float>>& a) {
    const size_t n = a.size();
    for (size_t i = 1, j = 0; i < n; ++i) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (size_t len = 2; len <= n; len <<= 1) {
        const float ang = -TWO_PI / static_cast<float>(len);
        const std::complex<float> wlen(std::cos(ang), std::sin(ang));
        for (size_t i = 0; i < n; i += len) {
            std::complex<float> w(1.0f, 0.0f);
            for (size_t k = 0; k < len / 2; ++k) {
                const std::complex<float> u = a[i + k];
                const std::complex<float> v = a[i + k + len / 2] * w;
                a[i + k] = u + v;
                a[i + k + len / 2] = u - v;
                w *= wlen;
            }
        }
    }
}

// Power spectrum of a Hann-windowed frame taken from the middle of the signal.
std::vector<float> powerSpectrum(const std::vector<float>& mono, size_t frameSize = 2048) {
    std::vector<std::complex<float>> frame(frameSize, {0.0f, 0.0f});
    const size_t start = mono.size() > frameSize ? (mono.size() - frameSize) / 2 : 0;
    for (size_t i = 0; i < frameSize && start + i < mono.size(); ++i) {
        const float w = 0.5f * (1.0f - std::cos(TWO_PI * i / (frameSize - 1)));
        frame[i] = {mono[start + i] * w, 0.0f};
    }
    fft(frame);
    std::vector<float> power(frameSize / 2 + 1);
    for (size_t i = 0; i < power.size(); ++i) power[i] = std::norm(frame[i]);
    return power;
}

// RBJ biquad used for the K-weighting pre-filter.
struct Biquad {
    double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    double z1 = 0, z2 = 0;
    double process(double x) {
        const double y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        return y;
    }
};

Biquad makeHighShelf(double fs, double f0, double gainDb, double q) {
    const double A = std::pow(10.0, gainDb / 40.0);
    const double w0 = 2.0 * 3.14159265358979 * f0 / fs;
    const double alpha = std::sin(w0) / (2.0 * q);
    const double c = std::cos(w0);
    const double a0 = (A + 1) - (A - 1) * c + 2 * std::sqrt(A) * alpha;
    Biquad f;
    f.b0 = A * ((A + 1) + (A - 1) * c + 2 * std::sqrt(A) * alpha) / a0;
    f.b1 = -2 * A * ((A - 1) + (A + 1) * c) / a0;
    f.b2 = A * ((A + 1) + (A - 1) * c - 2 * std::sqrt(A) * alpha) / a0;
    f.a1 = 2 * ((A - 1) - (A + 1) * c) / a0;
    f.a2 = ((A + 1) - (A - 1) * c - 2 * std::sqrt(A) * alpha) / a0;
    return f;
}

Biquad makeHighPass(double fs, double f0, double q) {
    const double w0 = 2.0 * 3.14159265358979 * f0 / fs;
    const double alpha = std::sin(w0) / (2.0 * q);
    const double c = std::cos(w0);
    const double a0 = 1 + alpha;
    Biquad f;
    f.b0 = (1 + c) / 2 / a0;
    f.b1 = -(1 + c) / a0;
    f.b2 = (1 + c) / 2 / a0;
    f.a1 = -2 * c / a0;
    f.a2 = (1 - alpha) / a0;
    return f;
}

const char* loopTypeToString(LoopType type) {
    switch (type) {
        case LoopType::SUSTAIN: return "sustain";
        case LoopType::LOOP: return "loop";
        case LoopType::PING_PONG: return "ping_pong";
        default: return "none";
    }
}

LoopType loopTypeFromString(const std::string& s) {
    if (s == "sustain") return LoopType::SUSTAIN;
    if (s == "loop") return LoopType::LOOP;
    if (s == "ping_pong" || s == "pingpong") return LoopType::PING_PONG;
    return LoopType::NONE;
}

std::map<std::string, float> floatMapFromJson(const nlohmann::json& j) {
    std::map<std::string, float> out;
    if (j.is_object()) {
        for (auto it = j.begin(); it != j.end(); ++it) {
            if (it.value().is_number()) out[it.key()] = it.value().get<float>();
        }
    }
    return out;
}

std::map<std::string, std::string> stringMapFromJson(const nlohmann::json& j) {
    std::map<std::string, std::string> out;
    if (j.is_object()) {
        for (auto it = j.begin(); it != j.end(); ++it) {
            if (it.value().is_string()) out[it.key()] = it.value().get<std::string>();
        }
    }
    return out;
}

std::pair<int, int> rangeFromJson(const nlohmann::json& j, std::pair<int, int> fallback) {
    if (j.is_array() && j.size() >= 2 && j[0].is_number() && j[1].is_number()) {
        return {j[0].get<int>(), j[1].get<int>()};
    }
    return fallback;
}

} // namespace

// SampleGen Implementation
SampleGen::SampleGen()
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

    // Initialize processing engines
    initializeProcessingEngines();
}

SampleGen::~SampleGen() = default;

AudioBundle SampleGen::process(const SampleParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "sample_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;

        // Load sample definition if provided
        SampleDefinition sampleDef;
        if (!params.sampleDefinitionPath.empty()) {
            sampleDef = loadSampleDefinition(params.sampleDefinitionPath);
        } else {
            sampleDef = createDefaultSampleDefinition(params);
        }

        // Process sample pipeline
        SampleResult result = processSamplePipeline(sampleDef, params);

        // Apply the per-request parameters to the primary sample
        std::vector<float> audio = result.audioData;
        applySampleParams(audio, params);

        // Set the processed data
        bundle.buffer = std::move(audio);
        bundle.meta.duration = static_cast<float>(bundle.buffer.size()) / (m_sampleRate * m_numChannels);
        bundle.meta.loop = !result.processedSamples.empty() && result.processedSamples[0].loopInfo.isValid;
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

void SampleGen::applySampleParams(std::vector<float>& audio, const SampleParams& params) {
    const uint32_t channels = std::max<uint32_t>(1, m_numChannels);

    // Trim range in seconds (x = start, y = end); ignored when end <= start.
    if (params.trimRange.y > params.trimRange.x && params.trimRange.x >= 0.0f) {
        const size_t frames = audio.size() / channels;
        const size_t startFrame = std::min(frames, static_cast<size_t>(params.trimRange.x * m_sampleRate));
        const size_t endFrame = std::min(frames, static_cast<size_t>(params.trimRange.y * m_sampleRate));
        audio = std::vector<float>(audio.begin() + startFrame * channels, audio.begin() + endFrame * channels);
    }

    // Pitch shift in semitones
    if (std::abs(params.pitchShift) > 1e-3f) {
        const float ratio = std::pow(2.0f, params.pitchShift / 12.0f);
        const uint32_t virtualRate = static_cast<uint32_t>(std::lround(m_sampleRate * ratio));
        audio = FileIO::resampleLinear(audio, channels, virtualRate, m_sampleRate);
    }

    // Gain
    if (params.gain != 1.0f) {
        for (float& s : audio) s *= params.gain;
    }

    // Fade in / out (seconds)
    const size_t frames = audio.size() / channels;
    const size_t fadeIn = std::min(frames, static_cast<size_t>(std::max(0.0f, params.fadeInOut.x) * m_sampleRate));
    const size_t fadeOut = std::min(frames, static_cast<size_t>(std::max(0.0f, params.fadeInOut.y) * m_sampleRate));
    for (size_t f = 0; f < fadeIn; ++f) {
        const float g = static_cast<float>(f) / static_cast<float>(fadeIn);
        for (uint32_t c = 0; c < channels; ++c) audio[f * channels + c] *= g;
    }
    for (size_t f = 0; f < fadeOut; ++f) {
        const float g = static_cast<float>(f) / static_cast<float>(fadeOut);
        const size_t frame = frames - 1 - f;
        for (uint32_t c = 0; c < channels; ++c) audio[frame * channels + c] *= g;
    }

    if (params.normalize && !audio.empty()) {
        audio = m_normalizer->normalize(audio, 0.95f);
    }
}

// Sample Definition Loading (JSON)
SampleDefinition SampleGen::loadSampleDefinition(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open sample definition: " + filePath);
    }

    nlohmann::json j;
    try {
        file >> j;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("Failed to parse sample definition " + filePath + ": " + e.what());
    }

    SampleDefinition def;
    def.name = j.value("name", std::string("sample_pack"));
    def.category = j.value("category", std::string("one_shot"));
    def.description = j.value("description", std::string());
    def.metadata = stringMapFromJson(j.value("metadata", nlohmann::json::object()));
    if (j.contains("tags") && j["tags"].is_array()) {
        for (const auto& t : j["tags"]) if (t.is_string()) def.tags.push_back(t.get<std::string>());
    }
    def.enableHotReload = j.value("enableHotReload", true);
    def.enableCaching = j.value("enableCaching", true);
    def.enableParallelProcessing = j.value("enableParallelProcessing", true);
    def.maxConcurrentSamples = j.value("maxConcurrentSamples", 8);

    // Relative sample paths are resolved against the definition file's directory.
    const std::filesystem::path baseDir = std::filesystem::path(filePath).parent_path();

    if (j.contains("samples") && j["samples"].is_array()) {
        for (const auto& s : j["samples"]) {
            SampleEntry entry;
            entry.id = s.value("id", std::string("sample_") + std::to_string(def.samples.size()));
            std::string path = s.value("path", std::string());
            if (!path.empty() && std::filesystem::path(path).is_relative() && !baseDir.empty()) {
                path = (baseDir / path).string();
            }
            entry.path = path;
            entry.trimSilence = s.value("trimSilence", true);
            entry.normalizeLUFS = s.value("normalizeLUFS", -14.0f);
            entry.parameters = floatMapFromJson(s.value("parameters", nlohmann::json::object()));
            if (s.contains("loop") && s["loop"].is_object()) {
                const auto& l = s["loop"];
                entry.loop.type = loopTypeFromString(l.value("type", std::string("none")));
                entry.loop.autoDetect = l.value("autoDetect", false);
                entry.loop.startSample = l.value("start", static_cast<size_t>(0));
                entry.loop.endSample = l.value("end", static_cast<size_t>(0));
                entry.loop.crossfadeDuration = l.value("crossfade", LOOP_CROSSFADE_DURATION);
                entry.loop.parameters = floatMapFromJson(l.value("parameters", nlohmann::json::object()));
            }
            def.samples.push_back(entry);
        }
    }

    if (j.contains("mappings") && j["mappings"].is_object()) {
        const auto& m = j["mappings"];
        def.mappings.instrument = m.value("instrument", def.name);
        def.mappings.metadata = stringMapFromJson(m.value("metadata", nlohmann::json::object()));
        if (m.contains("zones") && m["zones"].is_array()) {
            for (const auto& z : m["zones"]) {
                MappingZone zone;
                zone.sampleId = z.value("sample", z.value("sampleId", std::string()));
                zone.keyRange = rangeFromJson(z.value("keyRange", nlohmann::json()), {60, 60});
                zone.velocityRange = rangeFromJson(z.value("velocityRange", nlohmann::json()), {1, 127});
                zone.parameters = floatMapFromJson(z.value("parameters", nlohmann::json::object()));
                def.mappings.zones.push_back(zone);
            }
        }
    }

    if (j.contains("variations") && j["variations"].is_object()) {
        const auto& v = j["variations"];
        def.variations.pitchRange = rangeFromJson(v.value("pitchRange", nlohmann::json()), {-12, 12});
        def.variations.enableVariations = v.value("enabled", true);
        def.variations.enablePitchVariations = v.value("enablePitchVariations", true);
        if (v.contains("timeStretch")) {
            const auto& ts = v["timeStretch"];
            if (ts.is_boolean()) {
                def.variations.timeStretch.enabled = ts.get<bool>();
            } else if (ts.is_object()) {
                def.variations.timeStretch.enabled = ts.value("enabled", false);
                def.variations.timeStretch.targetBPM = ts.value("targetBPM", 120.0f);
                def.variations.timeStretch.stretchFactor = ts.value("stretchFactor", 1.0f);
            }
        }
        if (v.contains("targetBPM")) def.variations.timeStretch.targetBPM = v.value("targetBPM", 120.0f);
        def.variations.enableTimeVariations = def.variations.timeStretch.enabled;
    }

    return def;
}

bool SampleGen::saveSampleDefinition(const SampleDefinition& def, const std::string& filePath) {
    try {
        nlohmann::json j;
        j["name"] = def.name;
        j["category"] = def.category;
        j["description"] = def.description;
        j["metadata"] = def.metadata;
        j["tags"] = def.tags;
        j["enableHotReload"] = def.enableHotReload;
        j["enableCaching"] = def.enableCaching;
        j["enableParallelProcessing"] = def.enableParallelProcessing;
        j["maxConcurrentSamples"] = def.maxConcurrentSamples;

        j["samples"] = nlohmann::json::array();
        for (const auto& s : def.samples) {
            nlohmann::json e;
            e["id"] = s.id;
            e["path"] = s.path;
            e["trimSilence"] = s.trimSilence;
            e["normalizeLUFS"] = s.normalizeLUFS;
            e["parameters"] = s.parameters;
            e["loop"] = {
                {"type", loopTypeToString(s.loop.type)},
                {"autoDetect", s.loop.autoDetect},
                {"start", s.loop.startSample},
                {"end", s.loop.endSample},
                {"crossfade", s.loop.crossfadeDuration},
                {"parameters", s.loop.parameters}};
            j["samples"].push_back(e);
        }

        nlohmann::json zones = nlohmann::json::array();
        for (const auto& z : def.mappings.zones) {
            zones.push_back({{"sample", z.sampleId},
                             {"keyRange", {z.keyRange.first, z.keyRange.second}},
                             {"velocityRange", {z.velocityRange.first, z.velocityRange.second}},
                             {"parameters", z.parameters}});
        }
        j["mappings"] = {{"instrument", def.mappings.instrument}, {"zones", zones}, {"metadata", def.mappings.metadata}};

        j["variations"] = {
            {"enabled", def.variations.enableVariations},
            {"enablePitchVariations", def.variations.enablePitchVariations},
            {"pitchRange", {def.variations.pitchRange.first, def.variations.pitchRange.second}},
            {"timeStretch", {{"enabled", def.variations.timeStretch.enabled},
                             {"targetBPM", def.variations.timeStretch.targetBPM},
                             {"stretchFactor", def.variations.timeStretch.stretchFactor}}}};

        std::ofstream file(filePath);
        if (!file.is_open()) {
            m_lastError = "Could not open file for writing: " + filePath;
            return false;
        }
        file << j.dump(2);
        return static_cast<bool>(file);
    } catch (const std::exception& e) {
        m_lastError = "Failed to save sample definition: " + std::string(e.what());
        return false;
    }
}

SampleDefinition SampleGen::createDefaultSampleDefinition(const SampleParams& params) {
    SampleDefinition def;
    def.name = "default_sample";
    def.category = "one_shot";
    def.description = "Default sample";

    // Create a single sample entry
    SampleEntry sample;
    sample.id = "default";
    sample.path = params.filePath;
    sample.trimSilence = params.trimSilence;
    sample.normalizeLUFS = -14.0f;
    sample.loop.type = LoopType::NONE;
    sample.loop.autoDetect = false;
    def.samples.push_back(sample);

    // Add mapping
    def.mappings.instrument = "default";

    MappingZone zone;
    zone.sampleId = "default";
    zone.keyRange = {60, 60}; // Middle C
    zone.velocityRange = {1, 127};
    def.mappings.zones.push_back(zone);

    // A one-shot request only needs the sample itself.
    def.variations.enableVariations = false;

    return def;
}

// Sample Pipeline Processing
SampleResult SampleGen::processSamplePipeline(const SampleDefinition& sampleDef, const SampleParams& params) {
    SampleResult result;
    result.processingTime = std::chrono::system_clock::now();

    // Step 1: Import and decode samples
    std::vector<ProcessedSample> processedSamples;
    for (const auto& sampleEntry : sampleDef.samples) {
        ProcessedSample processed = importSample(sampleEntry, params);
        auto warn = processed.metadata.find("warning");
        if (warn != processed.metadata.end()) result.warnings.push_back(warn->second);
        processedSamples.push_back(std::move(processed));
    }

    // Step 2: Generate variations
    std::vector<SampleVariation> variations;
    if (sampleDef.variations.enableVariations) {
        variations = generateVariations(processedSamples, sampleDef.variations);
    }

    // Step 3: Generate metadata
    result.metadata = generateMetadata(sampleDef, processedSamples, variations);

    // Step 4: Create sample pack
    result.samplePack = createSamplePack(sampleDef, processedSamples, variations);

    // Step 5: Set main result (use first sample for compatibility)
    if (!processedSamples.empty()) {
        result.audioData = processedSamples[0].audioData;
    }

    result.processedSamples = std::move(processedSamples);
    result.variations = std::move(variations);
    result.sampleDef = sampleDef;
    result.extraMetadata["sampleCount"] = std::to_string(result.processedSamples.size());
    result.extraMetadata["variationCount"] = std::to_string(result.variations.size());

    return result;
}

// Processing Engine Initialization
void SampleGen::initializeProcessingEngines() {
    // Initialize audio decoders
    m_wavDecoder = std::make_unique<WAVDecoder>();
    m_mp3Decoder = std::make_unique<MP3Decoder>();
    m_oggDecoder = std::make_unique<OGGDecoder>();

    // Initialize analysis engines
    m_pitchDetector = std::make_unique<PitchDetector>();
    m_tempoDetector = std::make_unique<TempoDetector>();
    m_loudnessAnalyzer = std::make_unique<LoudnessAnalyzer>();
    m_spectralAnalyzer = std::make_unique<SpectralAnalyzer>();

    // Initialize processing engines
    m_silenceTrimmer = std::make_unique<SilenceTrimmer>();
    m_normalizer = std::make_unique<Normalizer>();
    m_loopDetector = std::make_unique<LoopDetector>();
    m_pitchShifter = std::make_unique<PitchShifter>();
    m_timeStretcher = std::make_unique<TimeStretcher>();

    m_wavDecoder->initialize(m_sampleRate, m_numChannels);
    m_mp3Decoder->initialize(m_sampleRate, m_numChannels);
    m_oggDecoder->initialize(m_sampleRate, m_numChannels);
    m_pitchDetector->initialize(m_sampleRate, m_numChannels);
    m_tempoDetector->initialize(m_sampleRate, m_numChannels);
    m_loudnessAnalyzer->initialize(m_sampleRate, m_numChannels);
    m_spectralAnalyzer->initialize(m_sampleRate, m_numChannels);
    m_silenceTrimmer->initialize(m_sampleRate, m_numChannels);
    m_normalizer->initialize(m_sampleRate, m_numChannels);
    m_loopDetector->initialize(m_sampleRate, m_numChannels);
    m_pitchShifter->initialize(m_sampleRate, m_numChannels);
    m_timeStretcher->initialize(m_sampleRate, m_numChannels);
}

// Sample Import
ProcessedSample SampleGen::importSample(const SampleEntry& sampleEntry, const SampleParams& params) {
    ProcessedSample processed;
    processed.id = sampleEntry.id;
    processed.originalPath = sampleEntry.path;

    // Step 1: Decode audio
    std::vector<float> rawAudio;
    try {
        rawAudio = decodeAudio(sampleEntry.path);
    } catch (const std::exception& e) {
        // Missing/undecodable sources fall back to the reference tone so a pack can
        // still be previewed; the problem is reported through the warnings.
        m_lastError = e.what();
        processed.metadata["warning"] = e.what();
        processed.metadata["source"] = "reference_tone";
        Log::warn("Audio", "SampleGen: {} - using reference tone", e.what());
        rawAudio = generateTestAudio();
    }

    // Step 2: Analyze audio
    AudioAnalysis analysis = analyzeAudio(rawAudio);
    processed.analysis = analysis;

    // Step 3: Trim silence
    if (sampleEntry.trimSilence) {
        rawAudio = trimSilence(rawAudio);
    }

    // Step 4: Normalize
    if (sampleEntry.normalizeLUFS != 0.0f) {
        rawAudio = normalizeLoudness(rawAudio, sampleEntry.normalizeLUFS);
    }

    // Step 5: Detect/create loop points
    if (sampleEntry.loop.type != LoopType::NONE) {
        LoopInfo loopInfo = detectLoop(rawAudio, sampleEntry.loop);
        processed.loopInfo = loopInfo;

        if (loopInfo.isValid) {
            rawAudio = createLoop(rawAudio, loopInfo);
        }
    }

    // Step 6: Set processed audio
    processed.audioData = rawAudio;
    processed.sampleRate = m_sampleRate;
    processed.numChannels = m_numChannels;
    processed.duration = static_cast<float>(rawAudio.size()) / (m_sampleRate * m_numChannels);

    return processed;
}

// Audio Decoding: dispatch on the file extension.
std::vector<float> SampleGen::decodeAudio(const std::string& filePath) {
    if (filePath.empty()) {
        throw std::runtime_error("No sample file specified");
    }
    const std::string ext = FileIO::lowerExtension(filePath);
    if (ext == ".mp3") return m_mp3Decoder->decode(filePath);
    if (ext == ".ogg" || ext == ".oga") return m_oggDecoder->decode(filePath);
    return m_wavDecoder->decode(filePath);
}

// Audio Analysis
AudioAnalysis SampleGen::analyzeAudio(const std::vector<float>& audio) {
    AudioAnalysis analysis;

    // Pitch detection
    analysis.rootKey = m_pitchDetector->detectPitch(audio, m_sampleRate);
    analysis.frequency = midiToFrequency(analysis.rootKey);

    // Tempo detection
    analysis.bpm = m_tempoDetector->detectTempo(audio, m_sampleRate);

    // Loudness analysis
    analysis.lufs = m_loudnessAnalyzer->analyzeLUFS(audio, m_sampleRate);
    analysis.peak = m_loudnessAnalyzer->analyzePeak(audio);
    analysis.rms = m_loudnessAnalyzer->analyzeRMS(audio);

    // Spectral analysis
    analysis.spectralCentroid = m_spectralAnalyzer->analyzeCentroid(audio, m_sampleRate);
    analysis.spectralRolloff = m_spectralAnalyzer->analyzeRolloff(audio, m_sampleRate);
    analysis.spectralFlatness = m_spectralAnalyzer->analyzeFlatness(audio);

    return analysis;
}

// Silence Trimming
std::vector<float> SampleGen::trimSilence(const std::vector<float>& audio) {
    return m_silenceTrimmer->trim(audio, SILENCE_THRESHOLD);
}

// Loudness Normalization
std::vector<float> SampleGen::normalizeLoudness(const std::vector<float>& audio, float targetLUFS) {
    if (audio.empty()) return audio;

    // Calculate current LUFS
    float currentLUFS = m_loudnessAnalyzer->analyzeLUFS(audio, m_sampleRate);
    if (!std::isfinite(currentLUFS)) return audio; // digital silence

    // Calculate gain adjustment
    float gainAdjustment = std::pow(10.0f, (targetLUFS - currentLUFS) / 20.0f);

    // Apply gain
    std::vector<float> normalizedAudio = audio;
    for (float& sample : normalizedAudio) {
        sample *= gainAdjustment;
        sample = clamp(sample, -1.0f, 1.0f);
    }

    return normalizedAudio;
}

// Loop Detection
LoopInfo SampleGen::detectLoop(const std::vector<float>& audio, const LoopSettings& settings) {
    LoopInfo loopInfo;

    if (settings.autoDetect) {
        // Auto-detect loop points
        loopInfo = m_loopDetector->detectLoop(audio, m_sampleRate);
    } else {
        // Use manual loop points if provided
        loopInfo.startSample = settings.startSample;
        loopInfo.endSample = settings.endSample;
        loopInfo.isValid = (loopInfo.startSample < loopInfo.endSample && loopInfo.endSample < audio.size());
        loopInfo.confidence = loopInfo.isValid ? 1.0f : 0.0f;
    }
    loopInfo.parameters["crossfadeDuration"] = settings.crossfadeDuration;

    return loopInfo;
}

// Loop Creation
std::vector<float> SampleGen::createLoop(const std::vector<float>& audio, const LoopInfo& loopInfo) {
    if (!loopInfo.isValid) return audio;

    std::vector<float> loopedAudio = audio;

    // Add crossfade at loop points
    auto cf = loopInfo.parameters.find("crossfadeDuration");
    const float crossfadeSeconds = cf != loopInfo.parameters.end() ? cf->second : LOOP_CROSSFADE_DURATION;
    size_t crossfadeSamples = static_cast<size_t>(crossfadeSeconds * m_sampleRate);
    if (crossfadeSamples == 0) return loopedAudio;

    // Create crossfade at the end
    for (size_t i = 0; i < crossfadeSamples && i < (audio.size() - loopInfo.endSample); ++i) {
        float fadeOut = 1.0f - static_cast<float>(i) / crossfadeSamples;
        size_t endIndex = loopInfo.endSample + i;
        if (endIndex < audio.size()) {
            loopedAudio[endIndex] *= fadeOut;
        }
    }

    // Create crossfade at the start
    const size_t startFade = std::min(crossfadeSamples, loopInfo.startSample);
    for (size_t i = 0; i < startFade; ++i) {
        float fadeIn = static_cast<float>(i) / startFade;
        size_t startIndex = loopInfo.startSample - startFade + i;
        if (startIndex < audio.size()) {
            loopedAudio[startIndex] *= fadeIn;
        }
    }

    return loopedAudio;
}

// Variation Generation
std::vector<SampleVariation> SampleGen::generateVariations(const std::vector<ProcessedSample>& samples, const VariationSettings& variations) {
    std::vector<SampleVariation> allVariations;

    for (const auto& sample : samples) {
        // Generate pitch variations
        if (variations.enablePitchVariations) {
            for (int semitone = variations.pitchRange.first; semitone <= variations.pitchRange.second; ++semitone) {
                SampleVariation variation;
                variation.sampleId = sample.id;
                variation.pitchShift = semitone;
                variation.midiNote = sample.analysis.rootKey + semitone;

                // Apply pitch shifting
                variation.audioData = pitchShift(sample.audioData, semitone);
                variation.sampleRate = sample.sampleRate;
                variation.numChannels = sample.numChannels;
                variation.duration = static_cast<float>(variation.audioData.size()) / (sample.sampleRate * sample.numChannels);

                allVariations.push_back(std::move(variation));
            }
        }

        // Generate time-stretched variations if enabled
        if (variations.timeStretch.enabled) {
            SampleVariation timeVariation;
            timeVariation.sampleId = sample.id;
            timeVariation.timeStretch = true;
            timeVariation.targetBPM = variations.timeStretch.targetBPM;

            // Derive the stretch factor from the detected tempo when none is given.
            TimeStretchSettings settings = variations.timeStretch;
            if (settings.stretchFactor == 1.0f && settings.targetBPM > 0.0f && sample.analysis.bpm > 0.0f) {
                settings.stretchFactor = sample.analysis.bpm / settings.targetBPM;
            }
            timeVariation.parameters["stretchFactor"] = settings.stretchFactor;

            // Apply time stretching
            timeVariation.audioData = timeStretch(sample.audioData, settings);
            timeVariation.sampleRate = sample.sampleRate;
            timeVariation.numChannels = sample.numChannels;
            timeVariation.duration = static_cast<float>(timeVariation.audioData.size()) / (sample.sampleRate * sample.numChannels);

            allVariations.push_back(std::move(timeVariation));
        }
    }

    return allVariations;
}

// Pitch Shifting
std::vector<float> SampleGen::pitchShift(const std::vector<float>& input, int semitones) {
    return m_pitchShifter->shift(input, semitones);
}

// Time Stretching
std::vector<float> SampleGen::timeStretch(const std::vector<float>& input, const TimeStretchSettings& settings) {
    return m_timeStretcher->stretch(input, settings.stretchFactor);
}

// Metadata Generation
SampleMetadata SampleGen::generateMetadata(const SampleDefinition& sampleDef, const std::vector<ProcessedSample>& samples, const std::vector<SampleVariation>& variations) {
    SampleMetadata metadata;

    metadata.packName = sampleDef.name;
    metadata.category = sampleDef.category;
    metadata.description = sampleDef.description;
    metadata.sampleRate = m_sampleRate;
    metadata.bitDepth = 24; // Packs are written as 24-bit PCM
    metadata.channels = m_numChannels;
    metadata.numSamples = static_cast<int>(samples.size());
    metadata.numVariations = static_cast<int>(variations.size());

    // Sample entries
    for (const auto& sample : samples) {
        SampleMetadataEntry entry;
        entry.id = sample.id;
        entry.originalPath = sample.originalPath;
        entry.rootKey = sample.analysis.rootKey;
        entry.frequency = sample.analysis.frequency;
        entry.bpm = sample.analysis.bpm;
        entry.lufs = sample.analysis.lufs;
        entry.peak = sample.analysis.peak;
        entry.rms = sample.analysis.rms;
        entry.duration = sample.duration;
        entry.loopInfo = sample.loopInfo;
        entry.spectralCentroid = sample.analysis.spectralCentroid;
        entry.spectralRolloff = sample.analysis.spectralRolloff;
        entry.spectralFlatness = sample.analysis.spectralFlatness;
        entry.additionalMetadata = sample.metadata;

        metadata.samples.push_back(entry);
    }

    // Variation entries
    for (const auto& variation : variations) {
        VariationMetadataEntry entry;
        entry.sampleId = variation.sampleId;
        entry.pitchShift = variation.pitchShift;
        entry.midiNote = variation.midiNote;
        entry.timeStretch = variation.timeStretch;
        entry.targetBPM = variation.targetBPM;
        entry.duration = variation.duration;
        entry.parameters = variation.parameters;

        metadata.variations.push_back(entry);
    }

    // Mapping information
    metadata.mappings = sampleDef.mappings;
    metadata.additionalMetadata = sampleDef.metadata;

    return metadata;
}

// Sample Pack Creation
SamplePack SampleGen::createSamplePack(const SampleDefinition& sampleDef, const std::vector<ProcessedSample>& samples, const std::vector<SampleVariation>& variations) {
    SamplePack pack;

    pack.name = sampleDef.name;
    pack.version = "1.0.0";
    pack.metadata = generateMetadata(sampleDef, samples, variations);
    pack.samples = samples;
    pack.variations = variations;
    pack.sampleDef = sampleDef;
    pack.creationTime = std::chrono::system_clock::now();

    // Size and checksum over all PCM content
    std::vector<uint8_t> pcm;
    auto append = [&pcm](const std::vector<float>& audio) {
        const auto* bytes = reinterpret_cast<const uint8_t*>(audio.data());
        pcm.insert(pcm.end(), bytes, bytes + audio.size() * sizeof(float));
    };
    for (const auto& s : samples) append(s.audioData);
    for (const auto& v : variations) append(v.audioData);
    pack.totalSize = pcm.size();
    pack.checksum = FileIO::sha256Hex(pcm.data(), pcm.size());

    return pack;
}

bool SampleGen::writeSamplePack(const SamplePack& pack, const std::string& filePath) {
    try {
        std::vector<FileIO::ZipEntry> entries;
        nlohmann::json meta;
        meta["name"] = pack.name;
        meta["version"] = pack.version;
        meta["category"] = pack.metadata.category;
        meta["description"] = pack.metadata.description;
        meta["sampleRate"] = pack.metadata.sampleRate;
        meta["bitDepth"] = pack.metadata.bitDepth;
        meta["channels"] = pack.metadata.channels;
        meta["checksum"] = pack.checksum;
        meta["samples"] = nlohmann::json::array();
        for (const auto& s : pack.metadata.samples) {
            meta["samples"].push_back({{"id", s.id}, {"file", "samples/" + s.id + ".wav"},
                                       {"rootKey", s.rootKey}, {"bpm", s.bpm}, {"lufs", s.lufs},
                                       {"duration", s.duration},
                                       {"loop", {{"valid", s.loopInfo.isValid}, {"start", s.loopInfo.startSample}, {"end", s.loopInfo.endSample}}}});
        }
        meta["variations"] = nlohmann::json::array();
        nlohmann::json zones = nlohmann::json::array();
        for (const auto& z : pack.metadata.mappings.zones) {
            zones.push_back({{"sample", z.sampleId}, {"keyRange", {z.keyRange.first, z.keyRange.second}},
                             {"velocityRange", {z.velocityRange.first, z.velocityRange.second}}});
        }
        meta["mappings"] = {{"instrument", pack.metadata.mappings.instrument}, {"zones", zones}};

        for (const auto& s : pack.samples) {
            entries.push_back({"samples/" + s.id + ".wav",
                               FileIO::encodeWav(s.audioData, s.sampleRate, static_cast<uint16_t>(s.numChannels), 24)});
        }
        for (size_t i = 0; i < pack.variations.size(); ++i) {
            const auto& v = pack.variations[i];
            std::string name = "variations/" + v.sampleId + (v.timeStretch ? "_stretch" : "_p" + std::to_string(v.pitchShift)) + ".wav";
            entries.push_back({name, FileIO::encodeWav(v.audioData, v.sampleRate, static_cast<uint16_t>(v.numChannels), 24)});
            meta["variations"].push_back({{"sample", v.sampleId}, {"file", name}, {"pitchShift", v.pitchShift},
                                          {"midiNote", v.midiNote}, {"timeStretch", v.timeStretch}});
        }
        const std::string metaText = meta.dump(2);
        entries.insert(entries.begin(), FileIO::ZipEntry{"metadata.json", std::vector<uint8_t>(metaText.begin(), metaText.end())});

        const std::filesystem::path out(filePath);
        if (out.has_parent_path()) std::filesystem::create_directories(out.parent_path());
        if (!FileIO::writeFileBytes(filePath, FileIO::createZipArchive(entries))) {
            m_lastError = "Could not write sample pack: " + filePath;
            return false;
        }
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Failed to write sample pack: " + std::string(e.what());
        return false;
    }
}

// Decoder Implementations
std::vector<float> SampleGen::WAVDecoder::decode(const std::string& filePath) {
    std::vector<float> out;
    std::string error;
    if (!FileIO::decodeFileAs(filePath, m_sampleRate, m_channels, out, error)) {
        throw std::runtime_error("WAV decode failed: " + error);
    }
    return out;
}

std::vector<float> SampleGen::MP3Decoder::decode(const std::string& filePath) {
    // No MP3 decoder library is vendored with the backend; FileIO reports this explicitly.
    std::vector<float> out;
    std::string error;
    if (!FileIO::decodeFileAs(filePath, m_sampleRate, m_channels, out, error)) {
        throw std::runtime_error("MP3 decode failed: " + error);
    }
    return out;
}

std::vector<float> SampleGen::OGGDecoder::decode(const std::string& filePath) {
    std::vector<float> out;
    std::string error;
    if (!FileIO::decodeFileAs(filePath, m_sampleRate, m_channels, out, error)) {
        throw std::runtime_error("OGG decode failed: " + error);
    }
    return out;
}

// Analysis Engine Implementations

// Autocorrelation pitch detection over the first ~0.25 s of the mono mix.
int SampleGen::PitchDetector::detectPitch(const std::vector<float>& audio, uint32_t sampleRate) {
    std::vector<float> mono = toMono(audio, m_channels);
    if (mono.empty() || sampleRate == 0) return 60;

    const size_t window = std::min<size_t>(mono.size(), sampleRate / 4);
    const size_t minLag = std::max<size_t>(2, sampleRate / 2000); // up to 2 kHz
    const size_t maxLag = std::min<size_t>(window / 2, sampleRate / 40); // down to 40 Hz
    if (maxLag <= minLag) return 60;

    double energy = 0.0;
    for (size_t i = 0; i < window; ++i) energy += static_cast<double>(mono[i]) * mono[i];
    if (energy <= 1e-9) return 60;

    size_t bestLag = 0;
    double best = 0.0;
    for (size_t lag = minLag; lag <= maxLag; ++lag) {
        double sum = 0.0;
        for (size_t i = 0; i + lag < window; ++i) sum += static_cast<double>(mono[i]) * mono[i + lag];
        sum /= static_cast<double>(window - lag);
        if (sum > best) {
            best = sum;
            bestLag = lag;
        }
    }
    if (bestLag == 0) return 60;

    const float frequency = static_cast<float>(sampleRate) / static_cast<float>(bestLag);
    const int midi = static_cast<int>(std::lround(12.0f * std::log2(frequency / 440.0f) + 69.0f));
    return std::clamp(midi, 0, 127);
}

// Tempo from the autocorrelation of the onset-strength envelope (60..200 BPM).
float SampleGen::TempoDetector::detectTempo(const std::vector<float>& audio, uint32_t sampleRate) {
    std::vector<float> mono = toMono(audio, m_channels);
    if (sampleRate == 0) return 120.0f;
    const size_t hop = std::max<size_t>(1, sampleRate / 100); // 10 ms frames
    if (mono.size() < hop * 8) return 120.0f;

    std::vector<float> energy;
    for (size_t i = 0; i + hop <= mono.size(); i += hop) {
        float e = 0.0f;
        for (size_t j = 0; j < hop; ++j) e += mono[i + j] * mono[i + j];
        energy.push_back(e);
    }
    std::vector<float> onset(energy.size(), 0.0f);
    for (size_t i = 1; i < energy.size(); ++i) onset[i] = std::max(0.0f, energy[i] - energy[i - 1]);

    const float framesPerSecond = static_cast<float>(sampleRate) / static_cast<float>(hop);
    const size_t minLag = static_cast<size_t>(framesPerSecond * 60.0f / 200.0f);
    const size_t maxLag = static_cast<size_t>(framesPerSecond * 60.0f / 60.0f);
    if (onset.size() <= maxLag + 1) return 120.0f;

    size_t bestLag = 0;
    double best = 0.0;
    for (size_t lag = std::max<size_t>(1, minLag); lag <= maxLag; ++lag) {
        double sum = 0.0;
        for (size_t i = 0; i + lag < onset.size(); ++i) sum += static_cast<double>(onset[i]) * onset[i + lag];
        if (sum > best) {
            best = sum;
            bestLag = lag;
        }
    }
    if (bestLag == 0 || best <= 1e-12) return 120.0f;
    return std::clamp(60.0f * framesPerSecond / static_cast<float>(bestLag), 60.0f, 200.0f);
}

// Integrated loudness (ITU-R BS.1770 K-weighting, ungated) in LUFS.
float SampleGen::LoudnessAnalyzer::analyzeLUFS(const std::vector<float>& audio, uint32_t sampleRate) {
    if (audio.empty() || sampleRate == 0) return -std::numeric_limits<float>::infinity();
    const uint32_t channels = std::max<uint32_t>(1, m_channels);
    const size_t frames = audio.size() / channels;
    if (frames == 0) return -std::numeric_limits<float>::infinity();

    double total = 0.0;
    for (uint32_t c = 0; c < channels; ++c) {
        Biquad shelf = makeHighShelf(sampleRate, 1681.97, 4.0, 0.7071);
        Biquad highPass = makeHighPass(sampleRate, 38.13, 0.5003);
        double sum = 0.0;
        for (size_t f = 0; f < frames; ++f) {
            const double y = highPass.process(shelf.process(audio[f * channels + c]));
            sum += y * y;
        }
        total += sum / static_cast<double>(frames);
    }
    if (total <= 1e-12) return -std::numeric_limits<float>::infinity();
    return static_cast<float>(-0.691 + 10.0 * std::log10(total));
}

float SampleGen::LoudnessAnalyzer::analyzePeak(const std::vector<float>& audio) {
    float peak = 0.0f;
    for (float s : audio) peak = std::max(peak, std::abs(s));
    return peak;
}

float SampleGen::LoudnessAnalyzer::analyzeRMS(const std::vector<float>& audio) {
    if (audio.empty()) return 0.0f;
    double sum = 0.0;
    for (float sample : audio) {
        sum += static_cast<double>(sample) * sample;
    }
    return static_cast<float>(std::sqrt(sum / audio.size()));
}

float SampleGen::SpectralAnalyzer::analyzeCentroid(const std::vector<float>& audio, uint32_t sampleRate) {
    const std::vector<float> power = powerSpectrum(toMono(audio, m_channels));
    const float binHz = static_cast<float>(sampleRate) / static_cast<float>((power.size() - 1) * 2);
    double weighted = 0.0, total = 0.0;
    for (size_t i = 0; i < power.size(); ++i) {
        const double mag = std::sqrt(power[i]);
        weighted += mag * i * binHz;
        total += mag;
    }
    return total > 0.0 ? static_cast<float>(weighted / total) : 0.0f;
}

float SampleGen::SpectralAnalyzer::analyzeRolloff(const std::vector<float>& audio, uint32_t sampleRate) {
    const std::vector<float> power = powerSpectrum(toMono(audio, m_channels));
    const float binHz = static_cast<float>(sampleRate) / static_cast<float>((power.size() - 1) * 2);
    const double total = std::accumulate(power.begin(), power.end(), 0.0);
    if (total <= 0.0) return 0.0f;
    double cumulative = 0.0;
    for (size_t i = 0; i < power.size(); ++i) {
        cumulative += power[i];
        if (cumulative >= 0.85 * total) return static_cast<float>(i) * binHz;
    }
    return static_cast<float>(power.size() - 1) * binHz;
}

float SampleGen::SpectralAnalyzer::analyzeFlatness(const std::vector<float>& audio) {
    const std::vector<float> power = powerSpectrum(toMono(audio, m_channels));
    double logSum = 0.0, sum = 0.0;
    for (float p : power) {
        const double v = static_cast<double>(p) + 1e-12;
        logSum += std::log(v);
        sum += v;
    }
    const double n = static_cast<double>(power.size());
    const double arithmetic = sum / n;
    return arithmetic > 0.0 ? static_cast<float>(std::exp(logSum / n) / arithmetic) : 0.0f;
}

// Processing Engine Implementations

// Removes leading/trailing frames whose absolute level is below the threshold.
std::vector<float> SampleGen::SilenceTrimmer::trim(const std::vector<float>& audio, float threshold) {
    const uint32_t channels = std::max<uint32_t>(1, m_channels);
    const size_t frames = audio.size() / channels;
    auto loud = [&](size_t f) {
        for (uint32_t c = 0; c < channels; ++c) {
            if (std::abs(audio[f * channels + c]) > threshold) return true;
        }
        return false;
    };
    size_t start = 0;
    while (start < frames && !loud(start)) ++start;
    if (start == frames) return {};
    size_t end = frames;
    while (end > start && !loud(end - 1)) --end;
    return std::vector<float>(audio.begin() + start * channels, audio.begin() + end * channels);
}

// Peak normalisation to the given linear level.
std::vector<float> SampleGen::Normalizer::normalize(const std::vector<float>& audio, float targetLevel) {
    float peak = 0.0f;
    for (float s : audio) peak = std::max(peak, std::abs(s));
    if (peak <= 1e-9f) return audio;
    const float gain = targetLevel / peak;
    std::vector<float> out = audio;
    for (float& s : out) s *= gain;
    return out;
}

// Finds a loop start/end pair whose surrounding windows correlate best.
LoopInfo SampleGen::LoopDetector::detectLoop(const std::vector<float>& audio, uint32_t sampleRate) {
    LoopInfo info;
    const uint32_t channels = std::max<uint32_t>(1, m_channels);
    std::vector<float> mono = toMono(audio, channels);
    const size_t window = std::max<size_t>(64, sampleRate / 50); // 20 ms comparison window
    if (mono.size() < window * 8) return info;

    const size_t step = std::max<size_t>(1, sampleRate / 200);
    const size_t endCandidate = mono.size() - window - 1;
    float bestScore = -1.0f;
    size_t bestStart = 0;
    for (size_t start = mono.size() / 8; start + window * 4 < endCandidate; start += step) {
        double dot = 0.0, ea = 0.0, eb = 0.0;
        for (size_t i = 0; i < window; ++i) {
            const double a = mono[start + i];
            const double b = mono[endCandidate + i];
            dot += a * b;
            ea += a * a;
            eb += b * b;
        }
        if (ea <= 1e-12 || eb <= 1e-12) continue;
        const float score = static_cast<float>(dot / std::sqrt(ea * eb));
        if (score > bestScore) {
            bestScore = score;
            bestStart = start;
        }
    }

    if (bestScore > 0.9f) {
        info.startSample = bestStart * channels;
        info.endSample = endCandidate * channels;
        info.isValid = true;
        info.confidence = bestScore;
    }
    return info;
}

// Resampling pitch shifter (changes duration with pitch, like a sampler).
std::vector<float> SampleGen::PitchShifter::shift(const std::vector<float>& audio, int semitones) {
    if (semitones == 0 || audio.empty()) return audio;
    const float ratio = std::pow(SEMITONE_RATIO, static_cast<float>(semitones));
    const uint32_t virtualRate = static_cast<uint32_t>(std::lround(m_sampleRate * ratio));
    return FileIO::resampleLinear(audio, std::max<uint32_t>(1, m_channels), virtualRate, m_sampleRate);
}

// Overlap-add time stretcher: output length = input length * stretchFactor, pitch preserved.
std::vector<float> SampleGen::TimeStretcher::stretch(const std::vector<float>& audio, float stretchFactor) {
    const uint32_t channels = std::max<uint32_t>(1, m_channels);
    const size_t frames = audio.size() / channels;
    if (frames == 0 || stretchFactor <= 0.0f || std::abs(stretchFactor - 1.0f) < 1e-4f) return audio;

    const size_t windowSize = 2048;
    const size_t synthesisHop = windowSize / 4;
    const double analysisHop = synthesisHop / static_cast<double>(stretchFactor);
    const size_t outFrames = static_cast<size_t>(frames * stretchFactor);

    std::vector<float> window(windowSize);
    for (size_t i = 0; i < windowSize; ++i) window[i] = 0.5f * (1.0f - std::cos(TWO_PI * i / (windowSize - 1)));

    std::vector<float> out(outFrames * channels, 0.0f);
    std::vector<float> norm(outFrames, 0.0f);
    for (size_t k = 0;; ++k) {
        const size_t outPos = k * synthesisHop;
        const size_t inPos = static_cast<size_t>(k * analysisHop);
        if (outPos >= outFrames || inPos >= frames) break;
        for (size_t i = 0; i < windowSize && outPos + i < outFrames && inPos + i < frames; ++i) {
            const float w = window[i];
            for (uint32_t c = 0; c < channels; ++c) {
                out[(outPos + i) * channels + c] += audio[(inPos + i) * channels + c] * w;
            }
            norm[outPos + i] += w;
        }
    }
    for (size_t f = 0; f < outFrames; ++f) {
        if (norm[f] > 1e-3f) {
            for (uint32_t c = 0; c < channels; ++c) out[f * channels + c] /= norm[f];
        }
    }
    return out;
}

// Utility Functions
float SampleGen::midiToFrequency(int midiNote) {
    return 440.0f * std::pow(2.0f, (midiNote - 69) / 12.0f);
}

int SampleGen::frequencyToMidi(float frequency) {
    return static_cast<int>(12.0f * std::log2(frequency / 440.0f) + 69);
}

// Reference tone (A4 with harmonics) used when a source cannot be decoded.
std::vector<float> SampleGen::generateTestAudio() {
    std::vector<float> audioData;
    const size_t numSamples = m_sampleRate * 2; // 2 seconds
    const size_t numChannels = m_numChannels;

    audioData.resize(numSamples * numChannels);

    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / static_cast<float>(m_sampleRate);

        // Generate a test tone
        float frequency = 440.0f; // A4 note
        float amplitude = 0.3f;
        float sample = amplitude * std::sin(2.0f * PI * frequency * time);

        // Add some harmonics
        sample += 0.1f * amplitude * std::sin(2.0f * PI * frequency * 2.0f * time);
        sample += 0.05f * amplitude * std::sin(2.0f * PI * frequency * 3.0f * time);

        // Write to all channels
        for (size_t ch = 0; ch < numChannels; ++ch) {
            audioData[i * numChannels + ch] = sample;
        }
    }

    return audioData;
}

// Quality calculation functions
float SampleGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
}

float SampleGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float SampleGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float SampleGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void SampleGen::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 10);
}

void SampleGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = std::clamp(factor, 1, 8);
}

void SampleGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void SampleGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void SampleGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 16);
}

// Error Handling
std::string SampleGen::getLastError() const {
    return m_lastError;
}

void SampleGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float SampleGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech
