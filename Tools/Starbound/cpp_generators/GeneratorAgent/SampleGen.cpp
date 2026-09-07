#include "SampleGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;
constexpr float SEMITONE_RATIO = 1.059463094359f;
constexpr size_t DEFAULT_SAMPLE_RATE = 44100;
constexpr size_t DEFAULT_BUFFER_SIZE = 1024;
constexpr float SILENCE_THRESHOLD = 0.01f;
constexpr float LOOP_CROSSFADE_DURATION = 0.1f; // seconds

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
        
        // Set the processed data
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

// Sample Definition Loading
SampleDefinition SampleGen::loadSampleDefinition(const std::string& filePath) {
    SampleDefinition def;
    
    // TODO: Implement YAML/JSON parsing for sample definitions
    // For now, create a basic definition
    def.name = "default_sample_pack";
    def.category = "drum_kit";
    def.description = "Default sample pack";
    
    // Add sample entries
    SampleEntry kickSample;
    kickSample.id = "kick";
    kickSample.path = "src/audio/kick_raw.wav";
    kickSample.trimSilence = true;
    kickSample.normalizeLUFS = -14.0f;
    kickSample.loop.type = LoopType::NONE;
    kickSample.loop.autoDetect = false;
    def.samples.push_back(kickSample);
    
    SampleEntry snareSample;
    snareSample.id = "snare";
    snareSample.path = "src/audio/snare_raw.wav";
    snareSample.trimSilence = true;
    snareSample.normalizeLUFS = -14.0f;
    snareSample.loop.type = LoopType::NONE;
    snareSample.loop.autoDetect = false;
    def.samples.push_back(snareSample);
    
    SampleEntry hatSample;
    hatSample.id = "hat_open";
    hatSample.path = "src/audio/hat_open_raw.wav";
    hatSample.trimSilence = true;
    hatSample.normalizeLUFS = -18.0f;
    hatSample.loop.type = LoopType::SUSTAIN;
    hatSample.loop.autoDetect = true;
    def.samples.push_back(hatSample);
    
    // Add mappings
    def.mappings.instrument = "drum_kit";
    
    MappingZone kickZone;
    kickZone.sampleId = "kick";
    kickZone.keyRange = {36, 36};
    kickZone.velocityRange = {1, 127};
    def.mappings.zones.push_back(kickZone);
    
    MappingZone snareZone;
    snareZone.sampleId = "snare";
    snareZone.keyRange = {38, 38};
    snareZone.velocityRange = {1, 127};
    def.mappings.zones.push_back(snareZone);
    
    MappingZone hatZone;
    hatZone.sampleId = "hat_open";
    hatZone.keyRange = {42, 46};
    hatZone.velocityRange = {1, 127};
    def.mappings.zones.push_back(hatZone);
    
    // Add variations
    def.variations.pitchRange = {-12, 12};
    def.variations.timeStretch.enabled = true;
    def.variations.timeStretch.targetBPM = 120.0f;
    
    return def;
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
    
    return def;
}

// Sample Pipeline Processing
SampleResult SampleGen::processSamplePipeline(const SampleDefinition& sampleDef, const SampleParams& params) {
    SampleResult result;
    
    // Step 1: Import and decode samples
    std::vector<ProcessedSample> processedSamples;
    for (const auto& sampleEntry : sampleDef.samples) {
        ProcessedSample processed = importSample(sampleEntry, params);
        processedSamples.push_back(processed);
    }
    
    // Step 2: Generate variations
    std::vector<SampleVariation> variations = generateVariations(processedSamples, sampleDef.variations);
    
    // Step 3: Generate metadata
    result.metadata = generateMetadata(sampleDef, processedSamples, variations);
    
    // Step 4: Create sample pack
    result.samplePack = createSamplePack(sampleDef, processedSamples, variations);
    
    // Step 5: Set main result (use first sample for compatibility)
    if (!processedSamples.empty()) {
        result.audioData = processedSamples[0].audioData;
    }
    
    result.processedSamples = processedSamples;
    result.variations = variations;
    result.sampleDef = sampleDef;
    
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
}

// Sample Import
ProcessedSample SampleGen::importSample(const SampleEntry& sampleEntry, const SampleParams& params) {
    ProcessedSample processed;
    processed.id = sampleEntry.id;
    processed.originalPath = sampleEntry.path;
    
    // Step 1: Decode audio
    std::vector<float> rawAudio = decodeAudio(sampleEntry.path);
    
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

// Audio Decoding
std::vector<float> SampleGen::decodeAudio(const std::string& filePath) {
    // TODO: Implement actual audio file decoding
    // For now, generate test audio
    return generateTestAudio();
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
    if (audio.empty()) return audio;
    
    // Find start of audio (first non-silent sample)
    size_t startIndex = 0;
    for (size_t i = 0; i < audio.size(); ++i) {
        if (std::abs(audio[i]) > SILENCE_THRESHOLD) {
            startIndex = i;
            break;
        }
    }
    
    // Find end of audio (last non-silent sample)
    size_t endIndex = audio.size() - 1;
    for (size_t i = audio.size() - 1; i > startIndex; --i) {
        if (std::abs(audio[i]) > SILENCE_THRESHOLD) {
            endIndex = i;
            break;
        }
    }
    
    // Extract trimmed audio
    std::vector<float> trimmedAudio;
    trimmedAudio.reserve(endIndex - startIndex + 1);
    for (size_t i = startIndex; i <= endIndex; ++i) {
        trimmedAudio.push_back(audio[i]);
    }
    
    return trimmedAudio;
}

// Loudness Normalization
std::vector<float> SampleGen::normalizeLoudness(const std::vector<float>& audio, float targetLUFS) {
    if (audio.empty()) return audio;
    
    // Calculate current LUFS
    float currentLUFS = m_loudnessAnalyzer->analyzeLUFS(audio, m_sampleRate);
    
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
    }
    
    return loopInfo;
}

// Loop Creation
std::vector<float> SampleGen::createLoop(const std::vector<float>& audio, const LoopInfo& loopInfo) {
    if (!loopInfo.isValid) return audio;
    
    std::vector<float> loopedAudio = audio;
    
    // Add crossfade at loop points
    size_t crossfadeSamples = static_cast<size_t>(LOOP_CROSSFADE_DURATION * m_sampleRate);
    
    // Create crossfade at the end
    for (size_t i = 0; i < crossfadeSamples && i < (audio.size() - loopInfo.endSample); ++i) {
        float fadeOut = 1.0f - static_cast<float>(i) / crossfadeSamples;
        size_t endIndex = loopInfo.endSample + i;
        if (endIndex < audio.size()) {
            loopedAudio[endIndex] *= fadeOut;
        }
    }
    
    // Create crossfade at the start
    for (size_t i = 0; i < crossfadeSamples && i < loopInfo.startSample; ++i) {
        float fadeIn = static_cast<float>(i) / crossfadeSamples;
        size_t startIndex = loopInfo.startSample - crossfadeSamples + i;
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
            
            allVariations.push_back(variation);
        }
        
        // Generate time-stretched variations if enabled
        if (variations.timeStretch.enabled) {
            SampleVariation timeVariation;
            timeVariation.sampleId = sample.id;
            timeVariation.timeStretch = true;
            timeVariation.targetBPM = variations.timeStretch.targetBPM;
            
            // Apply time stretching
            timeVariation.audioData = timeStretch(sample.audioData, variations.timeStretch);
            timeVariation.sampleRate = sample.sampleRate;
            timeVariation.numChannels = sample.numChannels;
            timeVariation.duration = static_cast<float>(timeVariation.audioData.size()) / (sample.sampleRate * sample.numChannels);
            
            allVariations.push_back(timeVariation);
        }
    }
    
    return allVariations;
}

// Pitch Shifting
std::vector<float> SampleGen::pitchShift(const std::vector<float>& input, int semitones) {
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
std::vector<float> SampleGen::timeStretch(const std::vector<float>& input, const TimeStretchSettings& settings) {
    // Simple time stretching using overlap-add method
    std::vector<float> output;
    size_t windowSize = 1024; // Default window size
    size_t hopSize = static_cast<size_t>(windowSize * 0.5f); // 50% overlap
    
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

// Metadata Generation
SampleMetadata SampleGen::generateMetadata(const SampleDefinition& sampleDef, const std::vector<ProcessedSample>& samples, const std::vector<SampleVariation>& variations) {
    SampleMetadata metadata;
    
    metadata.packName = sampleDef.name;
    metadata.category = sampleDef.category;
    metadata.description = sampleDef.description;
    metadata.sampleRate = m_sampleRate;
    metadata.bitDepth = 24; // Assume 24-bit
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
        
        metadata.variations.push_back(entry);
    }
    
    // Mapping information
    metadata.mappings = sampleDef.mappings;
    
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
    
    // TODO: Implement actual pack creation with audio encoding and file bundling
    // This would create the .samplepack archive with audio files and metadata
    
    return pack;
}

// Decoder Implementations
std::vector<float> SampleGen::WAVDecoder::decode(const std::string& filePath) {
    // TODO: Implement WAV decoding
    // For now, return empty vector
    return std::vector<float>();
}

std::vector<float> SampleGen::MP3Decoder::decode(const std::string& filePath) {
    // TODO: Implement MP3 decoding
    // For now, return empty vector
    return std::vector<float>();
}

std::vector<float> SampleGen::OGGDecoder::decode(const std::string& filePath) {
    // TODO: Implement OGG decoding
    // For now, return empty vector
    return std::vector<float>();
}

// Analysis Engine Implementations
int SampleGen::PitchDetector::detectPitch(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement pitch detection
    // For now, return middle C (60)
    return 60;
}

float SampleGen::TempoDetector::detectTempo(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement tempo detection
    // For now, return 120 BPM
    return 120.0f;
}

float SampleGen::LoudnessAnalyzer::analyzeLUFS(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement LUFS analysis
    // For now, calculate RMS and convert to LUFS approximation
    float rms = 0.0f;
    for (float sample : audio) {
        rms += sample * sample;
    }
    rms = std::sqrt(rms / audio.size());
    return 20.0f * std::log10(rms) + 3.0f; // Rough LUFS approximation
}

float SampleGen::LoudnessAnalyzer::analyzePeak(const std::vector<float>& audio) {
    if (audio.empty()) return 0.0f;
    return *std::max_element(audio.begin(), audio.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float SampleGen::LoudnessAnalyzer::analyzeRMS(const std::vector<float>& audio) {
    if (audio.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : audio) {
        sum += sample * sample;
    }
    return std::sqrt(sum / audio.size());
}

float SampleGen::SpectralAnalyzer::analyzeCentroid(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement spectral centroid analysis
    // For now, return 1000 Hz
    return 1000.0f;
}

float SampleGen::SpectralAnalyzer::analyzeRolloff(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement spectral rolloff analysis
    // For now, return 8000 Hz
    return 8000.0f;
}

float SampleGen::SpectralAnalyzer::analyzeFlatness(const std::vector<float>& audio) {
    // TODO: Implement spectral flatness analysis
    // For now, return 0.5
    return 0.5f;
}

// Processing Engine Implementations
std::vector<float> SampleGen::SilenceTrimmer::trim(const std::vector<float>& audio, float threshold) {
    // Implementation already provided in main class
    return audio;
}

std::vector<float> SampleGen::Normalizer::normalize(const std::vector<float>& audio, float targetLevel) {
    // Implementation already provided in main class
    return audio;
}

LoopInfo SampleGen::LoopDetector::detectLoop(const std::vector<float>& audio, uint32_t sampleRate) {
    // TODO: Implement automatic loop detection
    // For now, return invalid loop
    return LoopInfo{};
}

std::vector<float> SampleGen::PitchShifter::shift(const std::vector<float>& audio, int semitones) {
    // Implementation already provided in main class
    return audio;
}

std::vector<float> SampleGen::TimeStretcher::stretch(const std::vector<float>& audio, float stretchFactor) {
    // Implementation already provided in main class
    return audio;
}

// Utility Functions
float SampleGen::midiToFrequency(int midiNote) {
    return 440.0f * std::pow(2.0f, (midiNote - 69) / 12.0f);
}

int SampleGen::frequencyToMidi(float frequency) {
    return static_cast<int>(12.0f * std::log2(frequency / 440.0f) + 69);
}

// Test Audio Generation
std::vector<float> SampleGen::generateTestAudio() {
    std::vector<float> audioData;
    size_t numSamples = 44100 * 2; // 2 seconds at 44.1kHz
    size_t numChannels = 2; // Stereo
    
    audioData.resize(numSamples * numChannels);
    
    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / 44100.0f;
        
        // Generate a test tone
        float frequency = 440.0f; // A4 note
        float amplitude = 0.3f;
        float sample = amplitude * std::sin(2.0f * PI * frequency * time);
        
        // Add some harmonics
        sample += 0.1f * amplitude * std::sin(2.0f * PI * frequency * 2.0f * time);
        sample += 0.05f * amplitude * std::sin(2.0f * PI * frequency * 3.0f * time);
        
        // Write to all channels
        for (uint32_t ch = 0; ch < numChannels; ++ch) {
            size_t index = i * numChannels + ch;
            if (index < audioData.size()) {
                audioData[index] = sample;
            }
        }
    }
    
    return audioData;
}

// Quality calculation functions
float SampleGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
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
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float SampleGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void SampleGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void SampleGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void SampleGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void SampleGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void SampleGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
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
