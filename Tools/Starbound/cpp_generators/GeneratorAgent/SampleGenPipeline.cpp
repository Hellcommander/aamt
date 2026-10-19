#include "SampleGenPipeline.hpp"
#include "AudioFileIO.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cmath>
#include <complex>
#include <cstring>
#include <limits>
#include <filesystem>

namespace MagiTech {
namespace Audio {

namespace {

constexpr float kTwoPi = 6.28318530718f;
constexpr char kPackageMagic[4] = {'M', 'T', 'S', 'P'};
constexpr uint32_t kPackageVersion = 1;

void fftInPlace(std::vector<std::complex<float>>& a) {
    const size_t n = a.size();
    for (size_t i = 1, j = 0; i < n; ++i) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (size_t len = 2; len <= n; len <<= 1) {
        const float ang = -kTwoPi / static_cast<float>(len);
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

std::chrono::system_clock::time_point fileTime(const std::filesystem::path& p) {
    std::error_code ec;
    auto t = std::filesystem::last_write_time(p, ec);
    if (ec) return {};
    return std::chrono::clock_cast<std::chrono::system_clock>(t);
}

nlohmann::json loopToJson(const LoopRange& loop) {
    return {{"start", loop.start}, {"end", loop.end}, {"enabled", loop.enabled},
            {"type", loop.type}, {"autoDetect", loop.autoDetect}};
}

nlohmann::json sampleToJson(const SampleSourceDefinition& s) {
    return {{"id", s.id}, {"path", s.path}, {"trimSilence", s.trimSilence}, {"normalizeLUFS", s.normalizeLUFS},
            {"rootKey", s.rootKey}, {"bpm", s.bpm}, {"loop", loopToJson(s.loop)}, {"tags", s.tags}};
}

nlohmann::json zoneToJson(const VelocityZone& z) {
    return {{"sample", z.sampleId}, {"keyRange", {z.keyRange[0], z.keyRange[1]}},
            {"velocityRange", {z.velocityRange[0], z.velocityRange[1]}}};
}

nlohmann::json variationsToJson(const VariationSettings& v) {
    return {{"enabled", v.enableVariations}, {"pitchRange", {v.pitchRange.first, v.pitchRange.second}},
            {"enablePitchVariations", v.enablePitchVariations}, {"timeStretch", v.timeStretch.enabled},
            {"targetBPM", v.timeStretch.targetBPM}};
}

nlohmann::json definitionToJson(const SamplePackDefinition& d) {
    nlohmann::json j;
    j["name"] = d.name;
    j["samples"] = nlohmann::json::array();
    for (const auto& s : d.samples) j["samples"].push_back(sampleToJson(s));
    nlohmann::json zones = nlohmann::json::array();
    for (const auto& z : d.mappings.zones) zones.push_back(zoneToJson(z));
    j["mappings"] = {{"instrument", d.mappings.instrument}, {"zones", zones}};
    j["variations"] = variationsToJson(d.variations);
    j["outputPath"] = d.outputPath;
    j["audioFormat"] = d.audioFormat;
    j["quality"] = d.quality;
    return j;
}

// IMA ADPCM (mono, 512-byte blocks) WAV encoder.
std::vector<uint8_t> encodeImaAdpcmWav(const AudioBuffer& buffer, uint32_t sampleRate) {
    static const int stepTable[89] = {
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97,
        107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724,
        796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026,
        4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500,
        20350, 22385, 24623, 27086, 29794, 32767};
    static const int indexTable[16] = {-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8};
    constexpr uint32_t blockAlign = 512;
    constexpr uint32_t samplesPerBlock = (blockAlign - 4) * 2 + 1;

    auto toPcm = [&buffer](size_t i) -> int {
        if (i >= buffer.size()) return 0;
        return static_cast<int>(std::lround(std::clamp(buffer[i], -1.0f, 1.0f) * 32767.0f));
    };

    std::vector<uint8_t> data;
    int predictor = 0;
    int index = 0;
    for (size_t blockStart = 0; blockStart < buffer.size(); blockStart += samplesPerBlock) {
        predictor = toPcm(blockStart);
        data.push_back(static_cast<uint8_t>(predictor & 0xFF));
        data.push_back(static_cast<uint8_t>((predictor >> 8) & 0xFF));
        data.push_back(static_cast<uint8_t>(index));
        data.push_back(0);
        uint8_t pending = 0;
        bool low = true;
        for (uint32_t k = 1; k < samplesPerBlock; ++k) {
            const int sample = toPcm(blockStart + k);
            const int step = stepTable[index];
            int diff = sample - predictor;
            int nibble = 0;
            if (diff < 0) { nibble = 8; diff = -diff; }
            int tempStep = step;
            if (diff >= tempStep) { nibble |= 4; diff -= tempStep; }
            tempStep >>= 1;
            if (diff >= tempStep) { nibble |= 2; diff -= tempStep; }
            tempStep >>= 1;
            if (diff >= tempStep) { nibble |= 1; }
            int diffq = step >> 3;
            if (nibble & 4) diffq += step;
            if (nibble & 2) diffq += step >> 1;
            if (nibble & 1) diffq += step >> 2;
            predictor = std::clamp(predictor + ((nibble & 8) ? -diffq : diffq), -32768, 32767);
            index = std::clamp(index + indexTable[nibble], 0, 88);
            if (low) {
                pending = static_cast<uint8_t>(nibble);
            } else {
                data.push_back(static_cast<uint8_t>(pending | (nibble << 4)));
            }
            low = !low;
        }
    }

    std::vector<uint8_t> out;
    auto le16 = [&out](uint32_t v) { out.push_back(v & 0xFF); out.push_back((v >> 8) & 0xFF); };
    auto le32 = [&out](uint32_t v) { for (int i = 0; i < 4; ++i) out.push_back((v >> (8 * i)) & 0xFF); };
    auto tag = [&out](const char* t) { out.insert(out.end(), t, t + 4); };
    tag("RIFF");
    le32(static_cast<uint32_t>(4 + 28 + 12 + 8 + data.size()));
    tag("WAVE");
    tag("fmt ");
    le32(20);
    le16(0x11);                 // IMA ADPCM
    le16(1);                    // mono
    le32(sampleRate);
    le32(sampleRate * blockAlign / samplesPerBlock);
    le16(blockAlign);
    le16(4);                    // bits per sample
    le16(2);                    // cbSize
    le16(samplesPerBlock);
    tag("fact");
    le32(4);
    le32(static_cast<uint32_t>(buffer.size()));
    tag("data");
    le32(static_cast<uint32_t>(data.size()));
    out.insert(out.end(), data.begin(), data.end());
    return out;
}

} // namespace

SampleGenPipeline::SampleGenPipeline()
    : m_sampleGen(std::make_unique<SampleGen>()) {
}

SampleGenPipeline::~SampleGenPipeline() = default;

// Pipeline stages
bool SampleGenPipeline::importFromDefinition(const std::string& definitionPath) {
    clearLastError();
    m_progress.currentStage = "Loading definition";
    m_progress.percentage = 0.0f;
    m_progress.isComplete = false;

    try {
        SamplePackDefinition definition;
        if (!loadDefinition(definitionPath, definition)) {
            if (m_lastError.empty()) m_lastError = "Failed to load definition from: " + definitionPath;
            m_progress.errorMessage = m_lastError;
            return false;
        }
        m_definitions[definition.name] = definition;
        m_definitionPaths[definition.name] = definitionPath;
        m_definitionHashes[definition.name] = computeDefinitionHash(definition);

        if (m_hotReloadEnabled) {
            const std::string dir = std::filesystem::path(definitionPath).parent_path().string();
            setupFileWatcher(dir.empty() ? std::string(".") : dir);
        }

        m_progress.percentage = 20.0f;
        m_progress.currentStage = "Processing samples";

        if (!processSamples(definition)) {
            m_lastError = "Failed to process samples: " + m_lastError;
            m_progress.errorMessage = m_lastError;
            return false;
        }

        m_progress.percentage = 40.0f;
        m_progress.currentStage = "Analyzing samples";

        if (!analyzeSamples(definition.name, definition.samples)) {
            m_lastError = "Failed to analyze samples: " + m_lastError;
            m_progress.errorMessage = m_lastError;
            return false;
        }

        m_progress.percentage = 60.0f;
        m_progress.currentStage = "Generating variations";

        if (!generateVariations(definition)) {
            m_lastError = "Failed to generate variations: " + m_lastError;
            m_progress.errorMessage = m_lastError;
            return false;
        }

        m_progress.percentage = 80.0f;
        m_progress.currentStage = "Packaging samples";

        if (!packageSamples(definition)) {
            m_lastError = "Failed to package samples: " + m_lastError;
            m_progress.errorMessage = m_lastError;
            return false;
        }

        m_progress.percentage = 100.0f;
        m_progress.currentStage = "Complete";
        m_progress.isComplete = true;

        return true;

    } catch (const std::exception& e) {
        m_lastError = "Import error: " + std::string(e.what());
        m_progress.errorMessage = m_lastError;
        return false;
    }
}

bool SampleGenPipeline::processSample(const std::string& packageName, const SampleSourceDefinition& sampleDef) {
    // Load audio file
    AudioBuffer buffer;
    if (!decodeAudio(sampleDef.path, buffer)) {
        m_lastError = "Failed to decode audio: " + sampleDef.path + (m_lastError.empty() ? "" : " (" + m_lastError + ")");
        return false;
    }

    // Apply processing
    if (sampleDef.trimSilence) {
        buffer = trimSilence(buffer, SILENCE_THRESHOLD);
    }

    if (sampleDef.normalizeLUFS != 0.0f) {
        buffer = normalizeAudio(buffer, sampleDef.normalizeLUFS);
    }

    if (sampleDef.loop.enabled) {
        buffer = applyLoop(buffer, sampleDef.loop);
    }

    // Store processed sample
    RuntimeSampleEntry entry;
    entry.buffer = std::move(buffer);
    entry.id = sampleDef.id;
    entry.rootKey = sampleDef.rootKey;
    entry.bpm = sampleDef.bpm;
    entry.loop = sampleDef.loop;
    entry.tags = sampleDef.tags;
    entry.lastModified = std::chrono::system_clock::now();

    auto& package = m_packages[packageName];
    package.name = packageName;
    package.samples[sampleDef.id] = std::move(entry);
    return true;
}

bool SampleGenPipeline::processSamples(const SamplePackDefinition& definition) {
    clearLastError();

    try {
        m_definitions[definition.name] = definition;
        for (const auto& sampleDef : definition.samples) {
            if (!processSample(definition.name, sampleDef)) {
                return false;
            }
        }
        return true;

    } catch (const std::exception& e) {
        m_lastError = "Processing error: " + std::string(e.what());
        return false;
    }
}

bool SampleGenPipeline::analyzeSamples(const std::string& packageName, const std::vector<SampleSourceDefinition>& samples) {
    clearLastError();

    try {
        auto packageIt = m_packages.find(packageName);
        if (packageIt == m_packages.end()) {
            m_lastError = "Unknown package: " + packageName;
            return false;
        }
        for (const auto& sampleDef : samples) {
            auto sampleIt = packageIt->second.samples.find(sampleDef.id);
            if (sampleIt == packageIt->second.samples.end()) {
                m_lastError = "Sample not processed: " + sampleDef.id;
                return false;
            }
            RuntimeSampleEntry& sample = sampleIt->second;

            // Analyze the sample
            SampleAnalysis analysis = analyzeSample(sample.buffer, DEFAULT_SAMPLE_RATE);

            // Update sample with analysis results
            if (analysis.rootPitch > 0.0f) sample.rootKey = static_cast<int>(analysis.rootPitch);
            sample.bpm = analysis.bpm;
            if (sampleDef.loop.autoDetect && analysis.detectedLoop.enabled) {
                sample.loop = analysis.detectedLoop;
            }

            // Store analysis
            m_analyses[sampleDef.id] = analysis;
        }

        return true;

    } catch (const std::exception& e) {
        m_lastError = "Analysis error: " + std::string(e.what());
        return false;
    }
}

void SampleGenPipeline::generateVariationsForSample(const std::string& packageName, const SampleSourceDefinition& sampleDef,
                                                    const VariationSettings& variations) {
    auto& package = m_packages[packageName];
    auto originalIt = package.samples.find(sampleDef.id);
    if (originalIt == package.samples.end()) return;
    const RuntimeSampleEntry original = originalIt->second; // copy: the map grows below

    // Generate pitch variations
    if (variations.enablePitchVariations) {
        int generated = 0;
        for (int semitone = variations.pitchRange.first; semitone <= variations.pitchRange.second; semitone++) {
            if (semitone == 0) continue; // Skip original
            if (++generated > MAX_VARIATIONS) break;

            RuntimeSampleEntry variation;
            variation.buffer = pitchShift(original.buffer, static_cast<float>(semitone), DEFAULT_SAMPLE_RATE);
            variation.id = generateSampleId(sampleDef.id, semitone);
            variation.rootKey = original.rootKey + semitone;
            variation.bpm = original.bpm;
            variation.loop = original.loop;
            variation.tags = original.tags;
            variation.lastModified = std::chrono::system_clock::now();

            package.samples[variation.id] = std::move(variation);
        }
    }

    // Generate time-stretched variations if enabled
    if (variations.timeStretch.enabled) {
        RuntimeSampleEntry stretched;
        stretched.buffer = timeStretch(original.buffer, original.bpm, variations.timeStretch.targetBPM, DEFAULT_SAMPLE_RATE);
        stretched.id = generateSampleId(sampleDef.id + "_stretched", 0);
        stretched.rootKey = original.rootKey;
        stretched.bpm = variations.timeStretch.targetBPM;
        stretched.loop = original.loop;
        stretched.tags = original.tags;
        stretched.lastModified = std::chrono::system_clock::now();

        package.samples[stretched.id] = std::move(stretched);
    }
}

bool SampleGenPipeline::generateVariations(const SamplePackDefinition& definition) {
    clearLastError();

    if (!definition.variations.enableVariations) {
        return true; // Skip if variations are disabled
    }

    try {
        for (const auto& sampleDef : definition.samples) {
            generateVariationsForSample(definition.name, sampleDef, definition.variations);
        }
        return true;

    } catch (const std::exception& e) {
        m_lastError = "Variation generation error: " + std::string(e.what());
        return false;
    }
}

std::string SampleGenPipeline::packagePathFor(const SamplePackDefinition& definition) const {
    const std::filesystem::path dir = definition.outputPath.empty() ? std::filesystem::path(".") : std::filesystem::path(definition.outputPath);
    return (dir / (definition.name + ".samplepack")).string();
}

bool SampleGenPipeline::packageSamples(const SamplePackDefinition& definition) {
    clearLastError();

    try {
        auto& package = m_packages[definition.name];
        package.name = definition.name;
        package.mappings = definition.mappings;
        package.metadataHash = computeDefinitionHash(definition);
        package.created = std::chrono::system_clock::now();
        package.audioBuffers.clear();
        for (const auto& [id, entry] : package.samples) {
            package.audioBuffers[id] = entry.buffer;
        }

        // Create package file
        const std::string packagePath = packagePathFor(definition);
        if (!createPackage(packagePath, package)) {
            if (m_lastError.empty()) m_lastError = "Failed to create package: " + packagePath;
            return false;
        }

        // Export the individual samples in the definition's audio format
        if (!definition.outputPath.empty()) {
            const std::filesystem::path sampleDir = std::filesystem::path(definition.outputPath) / definition.name;
            std::filesystem::create_directories(sampleDir);
            for (const auto& [id, entry] : package.samples) {
                if (!encodeAudio(entry.buffer, definition.audioFormat, (sampleDir / (id + ".wav")).string(), definition.quality)) {
                    return false;
                }
            }
        }

        return true;

    } catch (const std::exception& e) {
        m_lastError = "Packaging error: " + std::string(e.what());
        return false;
    }
}

bool SampleGenPipeline::loadRuntime(const std::string& packagePath) {
    clearLastError();

    try {
        SamplePackage package;
        if (!loadPackage(packagePath, package)) {
            if (m_lastError.empty()) m_lastError = "Failed to load package: " + packagePath;
            return false;
        }

        // Create instrument from package
        SampleInstrument instrument;
        instrument.name = package.name;
        instrument.zones = package.mappings.zones;
        instrument.lastLoaded = std::chrono::system_clock::now();

        // Build key mapping
        for (const auto& zone : package.mappings.zones) {
            auto it = package.samples.find(zone.sampleId);
            if (it != package.samples.end()) {
                for (int key = std::max(0, zone.keyRange[0]); key <= std::min(127, zone.keyRange[1]); ++key) {
                    instrument.keyMap[key] = it->second;
                }
                instrument.sampleMap[zone.sampleId] = it->second;
            }
        }

        m_instruments[package.name] = std::move(instrument);
        m_packages[package.name] = std::move(package);
        setCacheCapacity(m_cacheCapacity);

        return true;

    } catch (const std::exception& e) {
        m_lastError = "Runtime loading error: " + std::string(e.what());
        return false;
    }
}

// Analysis methods
SampleAnalysis SampleGenPipeline::analyzeSample(const AudioBuffer& buffer, uint32_t sampleRate) {
    SampleAnalysis analysis;

    // Calculate basic metrics
    analysis.peakLevel = calculatePeakAmplitude(buffer);
    analysis.rmsLevel = calculateRMSAmplitude(buffer);
    analysis.lufsLevel = calculateLUFS(buffer, sampleRate);

    // Detect pitch
    analysis.rootPitch = detectRootPitch(buffer, sampleRate);

    // Estimate BPM
    analysis.bpm = estimateBPM(buffer, sampleRate);

    // Find spectral peaks
    analysis.spectralPeaks = findSpectralPeaks(buffer, sampleRate);

    // Detect loop points
    analysis.detectedLoop = detectLoopPoints(buffer, sampleRate);
    analysis.hasStableLoop = analysis.detectedLoop.enabled;

    // Detect silence
    auto silence = detectSilence(buffer);
    analysis.silenceStart = silence.first;
    analysis.silenceEnd = silence.second;

    return analysis;
}

// Autocorrelation pitch detection (50 Hz .. 2 kHz) over the first 0.25 s; returns a MIDI note.
float SampleGenPipeline::detectRootPitch(const AudioBuffer& buffer, uint32_t sampleRate) {
    const size_t maxLag = sampleRate / 50;   // Minimum frequency ~50Hz
    const size_t minLag = std::max<size_t>(2, sampleRate / 2000); // Maximum frequency ~2000Hz
    const size_t window = std::min<size_t>(buffer.size(), sampleRate / 4);
    if (window <= maxLag + 1) return 0.0f;

    size_t peakLag = 0;
    double peakValue = 0.0;
    for (size_t lag = minLag; lag < maxLag; ++lag) {
        double sum = 0.0;
        for (size_t i = 0; i + lag < window; ++i) {
            sum += static_cast<double>(buffer[i]) * buffer[i + lag];
        }
        sum /= static_cast<double>(window - lag);
        if (sum > peakValue) {
            peakValue = sum;
            peakLag = lag;
        }
    }
    if (peakLag == 0) return 0.0f;

    // Convert lag to frequency, then to a MIDI note number
    float frequency = static_cast<float>(sampleRate) / static_cast<float>(peakLag);
    float midiNote = 12.0f * std::log2(frequency / 440.0f) + 69.0f;

    return std::clamp(std::round(midiNote), 0.0f, 127.0f);
}

// Onset-energy based tempo estimate (10 ms frames).
float SampleGenPipeline::estimateBPM(const AudioBuffer& buffer, uint32_t sampleRate) {
    std::vector<float> onsetStrengths;
    const size_t windowSize = std::max<size_t>(1, sampleRate / 100); // 10ms windows

    float previous = 0.0f;
    for (size_t i = 0; i + windowSize <= buffer.size(); i += windowSize) {
        float energy = 0.0f;
        for (size_t j = 0; j < windowSize; ++j) {
            energy += buffer[i + j] * buffer[i + j];
        }
        onsetStrengths.push_back(std::max(0.0f, energy - previous));
        previous = energy;
    }
    if (onsetStrengths.size() < 3) return 120.0f;

    // Peaks in onset strength above a fraction of the strongest onset
    const float maxOnset = *std::max_element(onsetStrengths.begin(), onsetStrengths.end());
    if (maxOnset <= 0.0f) return 120.0f;
    std::vector<size_t> peaks;
    for (size_t i = 1; i + 1 < onsetStrengths.size(); ++i) {
        if (onsetStrengths[i] > onsetStrengths[i-1] &&
            onsetStrengths[i] >= onsetStrengths[i+1] &&
            onsetStrengths[i] > 0.3f * maxOnset) {
            peaks.push_back(i);
        }
    }

    if (peaks.size() < 2) {
        return 120.0f; // Default BPM
    }

    // Calculate average interval between peaks
    float totalInterval = 0.0f;
    for (size_t i = 1; i < peaks.size(); ++i) {
        totalInterval += static_cast<float>(peaks[i] - peaks[i-1]);
    }
    float avgInterval = totalInterval / (peaks.size() - 1);

    // Convert to BPM
    float windowTime = static_cast<float>(windowSize) / sampleRate;
    float beatTime = avgInterval * windowTime;
    if (beatTime <= 0.0f) return 120.0f;
    float bpm = 60.0f / beatTime;
    while (bpm > 200.0f) bpm *= 0.5f;
    while (bpm < 60.0f) bpm *= 2.0f;

    return bpm;
}

// Finds a sustain loop whose start/end windows correlate best (normalised cross-correlation).
LoopRange SampleGenPipeline::detectLoopPoints(const AudioBuffer& buffer, uint32_t sampleRate) {
    LoopRange loop;
    loop.enabled = false;

    const size_t windowSize = std::max<size_t>(64, sampleRate / 50); // 20ms comparison window
    const size_t step = std::max<size_t>(1, sampleRate / 100);
    const size_t searchStart = buffer.size() / 4;
    const size_t searchEnd = buffer.size() * 3 / 4;
    if (searchEnd <= searchStart + windowSize * 4 || searchEnd + windowSize >= buffer.size()) {
        return loop;
    }

    float bestCorrelation = 0.0f;
    size_t bestStart = 0;
    size_t bestEnd = 0;

    for (size_t start = searchStart; start + windowSize * 4 < searchEnd; start += step) {
        for (size_t end = start + windowSize * 4; end < searchEnd; end += step) {
            double dot = 0.0, ea = 0.0, eb = 0.0;
            for (size_t i = 0; i < windowSize; ++i) {
                const double a = buffer[start + i];
                const double b = buffer[end + i];
                dot += a * b;
                ea += a * a;
                eb += b * b;
            }
            if (ea <= 1e-12 || eb <= 1e-12) continue;
            const float correlation = static_cast<float>(dot / std::sqrt(ea * eb));
            if (correlation > bestCorrelation) {
                bestCorrelation = correlation;
                bestStart = start;
                bestEnd = end;
            }
        }
    }

    // If we found a good loop point
    if (bestCorrelation > 0.95f) {
        loop.enabled = true;
        loop.start = bestStart;
        loop.end = bestEnd;
        loop.type = "sustain";
        loop.autoDetect = true;
    }

    return loop;
}

// RMS-based loudness estimate (dB relative to full scale, offset to approximate LUFS).
float SampleGenPipeline::calculateLUFS(const AudioBuffer& buffer, uint32_t sampleRate) {
    if (buffer.empty()) return -std::numeric_limits<float>::infinity();
    double sum = 0.0;
    for (float sample : buffer) {
        sum += static_cast<double>(sample) * sample;
    }
    const double meanSquare = sum / buffer.size();
    if (meanSquare <= 1e-12) return -std::numeric_limits<float>::infinity();
    return static_cast<float>(10.0 * std::log10(meanSquare) - 0.691);
}

// Frequencies (Hz) of the strongest spectral peaks of the centre frame, strongest first.
std::vector<float> SampleGenPipeline::findSpectralPeaks(const AudioBuffer& buffer, uint32_t sampleRate) {
    std::vector<float> peaks;
    const size_t frameSize = 4096;
    if (buffer.size() < 64 || sampleRate == 0) return peaks;

    std::vector<std::complex<float>> frame(frameSize, {0.0f, 0.0f});
    const size_t start = buffer.size() > frameSize ? (buffer.size() - frameSize) / 2 : 0;
    for (size_t i = 0; i < frameSize && start + i < buffer.size(); ++i) {
        const float w = 0.5f * (1.0f - std::cos(kTwoPi * i / (frameSize - 1)));
        frame[i] = {buffer[start + i] * w, 0.0f};
    }
    fftInPlace(frame);

    std::vector<float> magnitude(frameSize / 2);
    for (size_t i = 0; i < magnitude.size(); ++i) magnitude[i] = std::abs(frame[i]);
    const float maxMag = *std::max_element(magnitude.begin(), magnitude.end());
    if (maxMag <= 0.0f) return peaks;

    std::vector<std::pair<float, size_t>> candidates;
    for (size_t i = 1; i + 1 < magnitude.size(); ++i) {
        if (magnitude[i] > magnitude[i - 1] && magnitude[i] >= magnitude[i + 1] && magnitude[i] > 0.01f * maxMag) {
            candidates.emplace_back(magnitude[i], i);
        }
    }
    std::sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
    const float binHz = static_cast<float>(sampleRate) / static_cast<float>(frameSize);
    for (size_t i = 0; i < candidates.size() && i < 8; ++i) {
        peaks.push_back(static_cast<float>(candidates[i].second) * binHz);
    }
    return peaks;
}

// Processing methods
AudioBuffer SampleGenPipeline::trimSilence(const AudioBuffer& buffer, float threshold) {
    if (buffer.empty()) return buffer;

    size_t start = 0;
    size_t end = buffer.size();

    // Find start of non-silence
    while (start < buffer.size() && std::abs(buffer[start]) < threshold) {
        start++;
    }

    // Find end of non-silence
    while (end > start && std::abs(buffer[end - 1]) < threshold) {
        end--;
    }

    if (start >= end) return AudioBuffer{};

    return AudioBuffer(buffer.begin() + start, buffer.begin() + end);
}

AudioBuffer SampleGenPipeline::normalizeAudio(const AudioBuffer& buffer, float targetLUFS) {
    if (buffer.empty()) return buffer;

    float currentLUFS = calculateLUFS(buffer, DEFAULT_SAMPLE_RATE);
    if (!std::isfinite(currentLUFS)) return buffer; // silence
    float gain = std::pow(10.0f, (targetLUFS - currentLUFS) / 20.0f);

    AudioBuffer result = buffer;
    for (auto& sample : result) {
        sample *= gain;
        sample = std::clamp(sample, -1.0f, 1.0f);
    }

    return result;
}

AudioBuffer SampleGenPipeline::applyLoop(const AudioBuffer& buffer, const LoopRange& loop) {
    if (!loop.enabled || loop.start >= loop.end || loop.end >= buffer.size()) {
        return buffer;
    }

    AudioBuffer result = buffer;

    // Crossfade the material after the loop end into the loop start
    const size_t crossfadeSize = std::min<size_t>({1024, buffer.size() - loop.end, loop.end - loop.start});
    for (size_t i = 0; i < crossfadeSize; ++i) {
        float fade = static_cast<float>(i) / crossfadeSize;
        result[loop.end + i] = result[loop.end + i] * (1.0f - fade) +
                               result[loop.start + i] * fade;
    }

    return result;
}

// Sampler-style pitch shift (resampling: duration changes with pitch).
AudioBuffer SampleGenPipeline::pitchShift(const AudioBuffer& buffer, float semitones, uint32_t sampleRate) {
    if (semitones == 0.0f || buffer.empty()) return buffer;

    const float ratio = std::pow(2.0f, semitones / 12.0f);
    const uint32_t virtualRate = static_cast<uint32_t>(std::lround(sampleRate * ratio));
    return FileIO::resampleLinear(buffer, 1, virtualRate, sampleRate);
}

// Tempo change without pitch change (overlap-add time stretching).
AudioBuffer SampleGenPipeline::timeStretch(const AudioBuffer& buffer, float sourceBPM, float targetBPM, uint32_t sampleRate) {
    if (sourceBPM == targetBPM || sourceBPM <= 0.0f || targetBPM <= 0.0f) return buffer;

    SampleGen::TimeStretcher stretcher;
    stretcher.initialize(sampleRate, 1);
    return stretcher.stretch(buffer, sourceBPM / targetBPM);
}

// Caching and hot-reload
void SampleGenPipeline::enableHotReload(bool enabled) {
    m_hotReloadEnabled = enabled;
    if (enabled) {
        // Watch the directories of all loaded definitions
        for (const auto& [name, path] : m_definitionPaths) {
            const std::string dir = std::filesystem::path(path).parent_path().string();
            setupFileWatcher(dir.empty() ? std::string(".") : dir);
        }
        for (const auto& dir : std::vector<std::string>(m_watchedDirectories)) {
            setupFileWatcher(dir);
        }
    }
}

void SampleGenPipeline::setCacheCapacity(size_t capacity) {
    m_cacheCapacity = std::max<size_t>(1, capacity);
    // Evict the oldest packages (and their runtime instruments) beyond capacity
    while (m_packages.size() > m_cacheCapacity) {
        auto oldest = std::min_element(m_packages.begin(), m_packages.end(),
                                       [](const auto& a, const auto& b) { return a.second.created < b.second.created; });
        m_instruments.erase(oldest->first);
        m_packages.erase(oldest);
    }
}

void SampleGenPipeline::clearCache() {
    m_packages.clear();
    m_instruments.clear();
    m_analyses.clear();
    m_fileHashes.clear();
    m_definitionHashes.clear();
}

bool SampleGenPipeline::isHotReloadEnabled() const {
    return m_hotReloadEnabled;
}

size_t SampleGenPipeline::getCacheSize() const {
    return m_packages.size();
}

void SampleGenPipeline::pollFileChanges() {
    if (!m_hotReloadEnabled) return;
    std::vector<std::string> changed;
    for (const auto& dir : m_watchedDirectories) {
        std::error_code ec;
        for (auto it = std::filesystem::recursive_directory_iterator(dir, ec);
             !ec && it != std::filesystem::recursive_directory_iterator(); it.increment(ec)) {
            if (!it->is_regular_file(ec)) continue;
            const std::string path = it->path().lexically_normal().string();
            const auto stamp = fileTime(it->path());
            auto known = m_fileHashes.find(path);
            if (known == m_fileHashes.end()) {
                m_fileHashes[path] = stamp;
            } else if (known->second != stamp) {
                known->second = stamp;
                changed.push_back(path);
            }
        }
    }
    for (const auto& path : changed) {
        onFileChanged(path);
    }
}

const SampleInstrument* SampleGenPipeline::getInstrument(const std::string& name) const {
    auto it = m_instruments.find(name);
    return it != m_instruments.end() ? &it->second : nullptr;
}

const SamplePackage* SampleGenPipeline::getPackage(const std::string& name) const {
    auto it = m_packages.find(name);
    return it != m_packages.end() ? &it->second : nullptr;
}

// Editor integration
std::string SampleGenPipeline::findPackageForSample(const std::string& sampleId) const {
    for (const auto& [name, definition] : m_definitions) {
        for (const auto& s : definition.samples) {
            if (s.id == sampleId) return name;
        }
    }
    return {};
}

void SampleGenPipeline::updateSampleDefinition(const std::string& sampleId, const SampleSourceDefinition& definition) {
    const std::string packageName = findPackageForSample(sampleId);
    if (packageName.empty()) {
        m_lastError = "Unknown sample: " + sampleId;
        return;
    }
    auto& packDef = m_definitions[packageName];
    for (auto& s : packDef.samples) {
        if (s.id == sampleId) s = definition;
    }
    for (auto& zone : packDef.mappings.zones) {
        if (zone.sampleId == sampleId) zone.sampleId = definition.id;
    }

    // Reprocess the edited sample and its variations, then refresh the package
    if (sampleId != definition.id) {
        m_packages[packageName].samples.erase(sampleId);
    }
    if (!processSample(packageName, definition)) return;
    if (!analyzeSamples(packageName, {definition})) return;
    regenerateVariations(definition.id);
    if (!m_lastError.empty()) return;
    packageSamples(packDef);
}

void SampleGenPipeline::regenerateVariations(const std::string& sampleId) {
    clearLastError();
    const std::string packageName = findPackageForSample(sampleId);
    if (packageName.empty()) {
        m_lastError = "Unknown sample: " + sampleId;
        return;
    }
    const auto& packDef = m_definitions[packageName];
    auto& samples = m_packages[packageName].samples;

    // Drop the previous variations of this sample
    for (int semitone = -MAX_VARIATIONS; semitone <= MAX_VARIATIONS; ++semitone) {
        if (semitone != 0) samples.erase(generateSampleId(sampleId, semitone));
    }
    samples.erase(generateSampleId(sampleId + "_stretched", 0));

    if (!packDef.variations.enableVariations) return;
    for (const auto& s : packDef.samples) {
        if (s.id == sampleId) {
            generateVariationsForSample(packageName, s, packDef.variations);
            break;
        }
    }
}

void SampleGenPipeline::rebuildPackage(const std::string& packageName) {
    auto it = m_definitions.find(packageName);
    if (it == m_definitions.end()) {
        m_lastError = "Unknown package: " + packageName;
        return;
    }
    const SamplePackDefinition definition = it->second;
    m_packages.erase(packageName);
    if (!processSamples(definition)) return;
    if (!analyzeSamples(definition.name, definition.samples)) return;
    if (!generateVariations(definition)) return;
    packageSamples(definition);
    m_definitionHashes[packageName] = computeDefinitionHash(definition);
}

// Error handling
std::string SampleGenPipeline::getLastError() const {
    return m_lastError;
}

void SampleGenPipeline::clearLastError() {
    m_lastError.clear();
}

// Private implementation methods
bool SampleGenPipeline::loadDefinition(const std::string& path, SamplePackDefinition& definition) {
    std::ifstream file(path);
    if (!file.is_open()) {
        m_lastError = "Cannot open definition: " + path;
        return false;
    }
    std::stringstream content;
    content << file.rdbuf();
    if (!SampleDefParser::parseDefinition(content.str(), definition)) {
        m_lastError = "Invalid sample pack definition: " + path;
        return false;
    }
    // Relative sample paths are resolved against the definition's directory
    const std::filesystem::path baseDir = std::filesystem::path(path).parent_path();
    for (auto& sample : definition.samples) {
        if (!sample.path.empty() && std::filesystem::path(sample.path).is_relative() && !baseDir.empty()) {
            sample.path = (baseDir / sample.path).lexically_normal().string();
        }
    }
    return true;
}

bool SampleGenPipeline::saveDefinition(const std::string& path, const SamplePackDefinition& definition) {
    std::ofstream file(path);
    if (!file.is_open()) {
        m_lastError = "Cannot write definition: " + path;
        return false;
    }
    file << SampleDefParser::serializeDefinition(definition);
    return static_cast<bool>(file);
}

// .samplepack layout: "MTSP", u32 version, u32 json length, JSON index, then for every
// sample listed in the index its mono float32 PCM (index gives the frame count).
bool SampleGenPipeline::createPackage(const std::string& path, const SamplePackage& package) {
    nlohmann::json index;
    index["name"] = package.name;
    index["metadataHash"] = package.metadataHash;
    index["created"] = std::chrono::duration_cast<std::chrono::seconds>(package.created.time_since_epoch()).count();
    index["sampleRate"] = DEFAULT_SAMPLE_RATE;
    nlohmann::json zones = nlohmann::json::array();
    for (const auto& z : package.mappings.zones) zones.push_back(zoneToJson(z));
    index["mappings"] = {{"instrument", package.mappings.instrument}, {"zones", zones}};
    index["samples"] = nlohmann::json::array();

    std::vector<std::string> order;
    for (const auto& [id, entry] : package.samples) order.push_back(id);
    std::sort(order.begin(), order.end());
    for (const auto& id : order) {
        const auto& entry = package.samples.at(id);
        index["samples"].push_back({{"id", entry.id}, {"rootKey", entry.rootKey}, {"bpm", entry.bpm},
                                    {"loop", loopToJson(entry.loop)}, {"tags", entry.tags},
                                    {"frames", entry.buffer.size()}});
    }
    const std::string indexText = index.dump();

    std::vector<uint8_t> bytes(kPackageMagic, kPackageMagic + 4);
    auto le32 = [&bytes](uint32_t v) { for (int i = 0; i < 4; ++i) bytes.push_back((v >> (8 * i)) & 0xFF); };
    le32(kPackageVersion);
    le32(static_cast<uint32_t>(indexText.size()));
    bytes.insert(bytes.end(), indexText.begin(), indexText.end());
    for (const auto& id : order) {
        const auto& buffer = package.samples.at(id).buffer;
        const auto* raw = reinterpret_cast<const uint8_t*>(buffer.data());
        bytes.insert(bytes.end(), raw, raw + buffer.size() * sizeof(float));
    }

    const std::filesystem::path out(path);
    if (out.has_parent_path()) std::filesystem::create_directories(out.parent_path());
    if (!FileIO::writeFileBytes(path, bytes)) {
        m_lastError = "Cannot write package: " + path;
        return false;
    }
    return true;
}

bool SampleGenPipeline::loadPackage(const std::string& path, SamplePackage& package) {
    std::vector<uint8_t> bytes;
    if (!FileIO::readFileBytes(path, bytes) || bytes.size() < 12 || std::memcmp(bytes.data(), kPackageMagic, 4) != 0) {
        m_lastError = "Not a sample package: " + path;
        return false;
    }
    auto le32 = [&bytes](size_t at) {
        return static_cast<uint32_t>(bytes[at]) | (static_cast<uint32_t>(bytes[at + 1]) << 8) |
               (static_cast<uint32_t>(bytes[at + 2]) << 16) | (static_cast<uint32_t>(bytes[at + 3]) << 24);
    };
    if (le32(4) != kPackageVersion) {
        m_lastError = "Unsupported sample package version in " + path;
        return false;
    }
    const size_t indexSize = le32(8);
    if (12 + indexSize > bytes.size()) {
        m_lastError = "Truncated sample package: " + path;
        return false;
    }
    nlohmann::json index = nlohmann::json::parse(bytes.begin() + 12, bytes.begin() + 12 + indexSize, nullptr, false);
    if (index.is_discarded() || !index.is_object()) {
        m_lastError = "Corrupt sample package index: " + path;
        return false;
    }

    package.name = index.value("name", std::string());
    package.metadataHash = index.value("metadataHash", std::string());
    package.created = std::chrono::system_clock::time_point(std::chrono::seconds(index.value("created", static_cast<int64_t>(0))));
    if (index.contains("mappings")) {
        package.mappings.instrument = index["mappings"].value("instrument", std::string());
        for (const auto& z : index["mappings"].value("zones", nlohmann::json::array())) {
            VelocityZone zone;
            SampleDefParser::parseVelocityZone(z, zone);
            package.mappings.zones.push_back(zone);
        }
    }

    size_t offset = 12 + indexSize;
    for (const auto& s : index.value("samples", nlohmann::json::array())) {
        RuntimeSampleEntry entry;
        entry.id = s.value("id", std::string());
        entry.rootKey = s.value("rootKey", 60);
        entry.bpm = s.value("bpm", 120.0f);
        if (s.contains("loop")) SampleDefParser::parseLoopRange(s["loop"], entry.loop);
        for (const auto& t : s.value("tags", nlohmann::json::array())) {
            if (t.is_string()) entry.tags.push_back(t.get<std::string>());
        }
        const size_t frames = s.value("frames", static_cast<size_t>(0));
        if (offset + frames * sizeof(float) > bytes.size()) {
            m_lastError = "Truncated sample data in package: " + path;
            return false;
        }
        entry.buffer.resize(frames);
        if (frames > 0) std::memcpy(entry.buffer.data(), bytes.data() + offset, frames * sizeof(float));
        offset += frames * sizeof(float);
        entry.lastModified = package.created;
        package.audioBuffers[entry.id] = entry.buffer;
        package.samples[entry.id] = std::move(entry);
    }
    return true;
}

bool SampleGenPipeline::encodeAudio(const AudioBuffer& buffer, const std::string& format,
                                  const std::string& outputPath, int quality) {
    std::string fmt = format;
    std::transform(fmt.begin(), fmt.end(), fmt.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });

    std::vector<uint8_t> encoded;
    if (fmt == "PCM" || fmt == "WAV") {
        // Quality above 5 keeps 24-bit resolution
        encoded = FileIO::encodeWav(buffer, DEFAULT_SAMPLE_RATE, 1, quality > 5 ? 24 : 16);
    } else if (fmt == "ADPCM") {
        encoded = encodeImaAdpcmWav(buffer, DEFAULT_SAMPLE_RATE);
    } else {
        m_lastError = "Unsupported sample encoding '" + format + "' (no " + format + " encoder is vendored; use PCM or ADPCM)";
        return false;
    }
    if (!FileIO::writeFileBytes(outputPath, encoded)) {
        m_lastError = "Cannot write encoded sample: " + outputPath;
        return false;
    }
    return true;
}

// Decodes through SampleGen's decoders and mixes down to the pipeline's mono format.
bool SampleGenPipeline::decodeAudio(const std::string& inputPath, AudioBuffer& buffer) {
    try {
        std::vector<float> stereo = m_sampleGen->decodeAudio(inputPath);
        buffer = FileIO::convertChannels(stereo, 2, 1);
        return !buffer.empty();
    } catch (const std::exception& e) {
        m_lastError = e.what();
        return false;
    }
}

std::string SampleGenPipeline::computeFileHash(const std::string& filePath) {
    std::vector<uint8_t> bytes;
    if (!FileIO::readFileBytes(filePath, bytes)) {
        m_lastError = "Cannot hash file: " + filePath;
        return {};
    }
    return FileIO::sha256Hex(bytes.data(), bytes.size());
}

std::string SampleGenPipeline::computeDefinitionHash(const SamplePackDefinition& definition) {
    const std::string text = SampleDefParser::serializeDefinition(definition);
    return FileIO::sha256Hex(reinterpret_cast<const uint8_t*>(text.data()), text.size());
}

void SampleGenPipeline::setupFileWatcher(const std::string& directory) {
    if (std::find(m_watchedDirectories.begin(), m_watchedDirectories.end(), directory) == m_watchedDirectories.end()) {
        m_watchedDirectories.push_back(directory);
    }
    // Snapshot the current modification times; pollFileChanges() reports later differences
    std::error_code ec;
    for (auto it = std::filesystem::recursive_directory_iterator(directory, ec);
         !ec && it != std::filesystem::recursive_directory_iterator(); it.increment(ec)) {
        if (it->is_regular_file(ec)) {
            m_fileHashes[it->path().lexically_normal().string()] = fileTime(it->path());
        }
    }
}

void SampleGenPipeline::onFileChanged(const std::string& filePath) {
    const std::filesystem::path changed = std::filesystem::path(filePath).lexically_normal();
    auto same = [&changed](const std::string& other) {
        std::error_code ec;
        return std::filesystem::equivalent(changed, std::filesystem::path(other), ec) ||
               changed == std::filesystem::path(other).lexically_normal();
    };

    // A changed definition re-runs the whole import (if its content really changed)
    for (const auto& [name, path] : std::unordered_map<std::string, std::string>(m_definitionPaths)) {
        if (same(path)) {
            SamplePackDefinition definition;
            if (loadDefinition(path, definition) && computeDefinitionHash(definition) != m_definitionHashes[name]) {
                importFromDefinition(path);
            }
            return;
        }
    }

    // A changed source sample is reprocessed together with its variations
    for (const auto& [name, definition] : std::unordered_map<std::string, SamplePackDefinition>(m_definitions)) {
        bool touched = false;
        for (const auto& sample : definition.samples) {
            if (!same(sample.path)) continue;
            if (processSample(name, sample) && analyzeSamples(name, {sample})) {
                regenerateVariations(sample.id);
                touched = true;
            }
        }
        if (touched) packageSamples(definition);
    }
}

std::string SampleGenPipeline::getFileExtension(const std::string& path) const {
    size_t dotPos = path.find_last_of('.');
    if (dotPos == std::string::npos) return "";
    return path.substr(dotPos);
}

bool SampleGenPipeline::fileExists(const std::string& path) const {
    return std::filesystem::exists(path);
}

std::string SampleGenPipeline::generateSampleId(const std::string& baseName, int variation) {
    if (variation == 0) return baseName;
    return baseName + "_" + std::to_string(variation);
}

// Helper functions
float SampleGenPipeline::calculatePeakAmplitude(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    float peak = 0.0f;
    for (float sample : buffer) {
        peak = std::max(peak, std::abs(sample));
    }
    return peak;
}

float SampleGenPipeline::calculateRMSAmplitude(const AudioBuffer& buffer) {
    if (buffer.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : buffer) {
        sum += sample * sample;
    }
    return std::sqrt(sum / buffer.size());
}

std::pair<size_t, size_t> SampleGenPipeline::detectSilence(const AudioBuffer& buffer) {
    if (buffer.empty()) return {0, 0};

    const float threshold = SILENCE_THRESHOLD;
    size_t start = 0;
    size_t end = buffer.size();

    // Find start of non-silence
    while (start < buffer.size() && std::abs(buffer[start]) < threshold) {
        start++;
    }

    // Find end of non-silence
    while (end > start && std::abs(buffer[end - 1]) < threshold) {
        end--;
    }

    return {start, end};
}

// ---------------------------------------------------------------------------
// SampleDefParser (JSON)
// ---------------------------------------------------------------------------
namespace SampleDefParser {

bool parseLoopRange(const nlohmann::json& node, LoopRange& loop) {
    if (!node.is_object()) return false;
    loop.start = node.value("start", static_cast<size_t>(0));
    loop.end = node.value("end", static_cast<size_t>(0));
    loop.type = node.value("type", std::string("none"));
    loop.enabled = node.value("enabled", loop.type != "none");
    loop.autoDetect = node.value("autoDetect", false);
    return true;
}

bool parseVelocityZone(const nlohmann::json& node, VelocityZone& zone) {
    if (!node.is_object()) return false;
    zone.sampleId = node.value("sample", node.value("sampleId", std::string()));
    if (node.contains("keyRange") && node["keyRange"].is_array() && node["keyRange"].size() >= 2) {
        zone.keyRange[0] = node["keyRange"][0].get<int>();
        zone.keyRange[1] = node["keyRange"][1].get<int>();
    }
    if (node.contains("velocityRange") && node["velocityRange"].is_array() && node["velocityRange"].size() >= 2) {
        zone.velocityRange[0] = node["velocityRange"][0].get<int>();
        zone.velocityRange[1] = node["velocityRange"][1].get<int>();
    }
    return !zone.sampleId.empty();
}

bool parseVariationSettings(const nlohmann::json& node, VariationSettings& settings) {
    if (!node.is_object()) return false;
    if (node.contains("pitchRange") && node["pitchRange"].is_array() && node["pitchRange"].size() >= 2) {
        settings.pitchRange = {node["pitchRange"][0].get<int>(), node["pitchRange"][1].get<int>()};
    }
    settings.enableVariations = node.value("enabled", node.value("enableVariations", true));
    settings.enablePitchVariations = node.value("enablePitchVariations", true);
    if (node.contains("timeStretch")) {
        if (node["timeStretch"].is_boolean()) {
            settings.timeStretch.enabled = node["timeStretch"].get<bool>();
        } else if (node["timeStretch"].is_object()) {
            settings.timeStretch.enabled = node["timeStretch"].value("enabled", false);
            settings.timeStretch.targetBPM = node["timeStretch"].value("targetBPM", 120.0f);
        }
    }
    settings.timeStretch.targetBPM = node.value("targetBPM", settings.timeStretch.targetBPM);
    settings.enableTimeVariations = settings.timeStretch.enabled;
    return true;
}

bool parseSampleDefinition(const nlohmann::json& node, SampleSourceDefinition& sample) {
    if (!node.is_object()) return false;
    sample.id = node.value("id", std::string());
    sample.path = node.value("path", std::string());
    sample.trimSilence = node.value("trimSilence", true);
    sample.normalizeLUFS = node.value("normalizeLUFS", -14.0f);
    sample.rootKey = node.value("rootKey", 60);
    sample.bpm = node.value("bpm", 120.0f);
    if (node.contains("loop")) parseLoopRange(node["loop"], sample.loop);
    for (const auto& t : node.value("tags", nlohmann::json::array())) {
        if (t.is_string()) sample.tags.push_back(t.get<std::string>());
    }
    return !sample.id.empty() && !sample.path.empty();
}

bool parseDefinition(const std::string& jsonContent, SamplePackDefinition& definition) {
    nlohmann::json root = nlohmann::json::parse(jsonContent, nullptr, false);
    if (root.is_discarded() || !root.is_object()) return false;

    definition.name = root.value("name", std::string());
    if (definition.name.empty()) return false;
    definition.outputPath = root.value("outputPath", std::string());
    definition.audioFormat = root.value("audioFormat", std::string("PCM"));
    definition.quality = std::clamp(root.value("quality", 5), 1, 10);

    definition.samples.clear();
    for (const auto& s : root.value("samples", nlohmann::json::array())) {
        SampleSourceDefinition sample;
        if (!parseSampleDefinition(s, sample)) return false;
        definition.samples.push_back(std::move(sample));
    }

    if (root.contains("mappings") && root["mappings"].is_object()) {
        definition.mappings.instrument = root["mappings"].value("instrument", definition.name);
        for (const auto& z : root["mappings"].value("zones", nlohmann::json::array())) {
            VelocityZone zone;
            if (parseVelocityZone(z, zone)) definition.mappings.zones.push_back(zone);
        }
    }
    if (root.contains("variations")) {
        parseVariationSettings(root["variations"], definition.variations);
    }
    return true;
}

std::string serializeDefinition(const SamplePackDefinition& definition) {
    return definitionToJson(definition).dump(2);
}

std::string serializeSampleDefinition(const SampleSourceDefinition& sample) {
    return sampleToJson(sample).dump(2);
}

std::string serializeLoopRange(const LoopRange& loop) {
    return loopToJson(loop).dump(2);
}

std::string serializeVelocityZone(const VelocityZone& zone) {
    return zoneToJson(zone).dump(2);
}

std::string serializeVariationSettings(const VariationSettings& settings) {
    return variationsToJson(settings).dump(2);
}

} // namespace SampleDefParser

} // namespace Audio
} // namespace MagiTech
