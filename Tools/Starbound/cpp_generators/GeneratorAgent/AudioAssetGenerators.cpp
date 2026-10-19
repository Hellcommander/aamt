#include "AudioAssetGenerators.hpp"
#include "AudioFileIO.hpp"
#include "SampleGen.hpp"
#include "SynthGen.hpp"
#include "EffectGen.hpp"
#include "MixerGen.hpp"
#include "ExportGen.hpp"
#include "AudioLODGen.hpp"
#include "core/Log.hpp"
#include "core/utils/HashCombine.hpp"
#include <algorithm>
#include <filesystem>
#include <typeinfo>

namespace MagiTech {
namespace Audio {

#define LOG_AUDIO_GEN(Action, Id) Log::info("Audio", "AudioGenerator - {}: {}", #Action, Id)

namespace {

template<typename... Ts>
uint64_t combine(uint64_t seed, const Ts&... values) {
    return static_cast<uint64_t>(ud::hash::hash_combine(static_cast<size_t>(seed), values...));
}

uint64_t hashVec2(const glm::vec2& v) { return combine(0x2u, v.x, v.y); }
uint64_t hashVec4(const glm::vec4& v) { return combine(0x4u, v.x, v.y, v.z, v.w); }

uint64_t hashBuffer(const std::vector<float>& buffer) {
    return FileIO::fnv1a64(buffer.data(), buffer.size() * sizeof(float), 1469598103934665603ULL ^ buffer.size());
}

template<typename T>
uint64_t hashList(const std::vector<T>& values) {
    uint64_t h = combine(0x51u, values.size());
    for (const auto& v : values) h = combine(h, v);
    return h;
}

uint64_t hashAny(const std::any& value) {
    if (const float* f = std::any_cast<float>(&value)) return combine(1u, *f);
    if (const double* d = std::any_cast<double>(&value)) return combine(2u, *d);
    if (const int* i = std::any_cast<int>(&value)) return combine(3u, *i);
    if (const bool* b = std::any_cast<bool>(&value)) return combine(4u, *b);
    if (const std::string* s = std::any_cast<std::string>(&value)) return combine(5u, *s);
    if (const auto* v = std::any_cast<std::vector<float>>(&value)) return combine(6u, hashBuffer(*v));
    // Values of other types only contribute their type
    return combine(7u, std::string(value.type().name()));
}

} // namespace

// ---------------------------------------------------------------------------
// Parameter hashing (cache keys of AudioAssetFactory)
// ---------------------------------------------------------------------------
uint64_t SoundParams::hashKey() const {
    return combine(0x50u, id, duration, loop);
}

uint64_t SampleParams::hashKey() const {
    return combine(0x51u, filePath, hashVec2(trimRange), pitchShift, gain, sampleDefinitionPath,
                   sampleRate, bitDepth, channels, normalize, trimSilence, hashVec2(fadeInOut),
                   enableGPUAcceleration);
}

uint64_t SynthParams::hashKey() const {
    return combine(0x52u, waveType, frequency, hashVec2(freqEnvelope), hashVec2(ampEnvelope), polyphonic,
                   duration, instrumentDefinitionPath, waveformType, amplitude, phase,
                   hashVec2(frequencyModulation), hashVec2(amplitudeModulation), hashVec2(phaseModulation),
                   hashVec4(adsrEnvelope), enableAntiAliasing, oversamplingFactor, harmonicLimit,
                   enableGPUAcceleration);
}

uint64_t EffectParams::ReverbSettings::hashKey() const {
    return combine(0x60u, roomSize, damping, wetLevel, dryLevel, width);
}

uint64_t EffectParams::DelaySettings::hashKey() const {
    return combine(0x61u, delayTime, feedback, wetLevel);
}

uint64_t EffectParams::DistortionSettings::hashKey() const {
    return combine(0x62u, drive, range, blend);
}

uint64_t EffectParams::CompressorSettings::hashKey() const {
    return combine(0x63u, threshold, ratio, attack, release);
}

uint64_t EffectParams::hashKey() const {
    uint64_t h = combine(0x53u, hashList(chain), effectTypes.size(), hashBuffer(inputBuffer), sampleRate,
                         processingQuality, oversamplingFactor, enableAntiAliasing, enableGPUAcceleration,
                         reverb.hashKey(), delay.hashKey(), distortion.hashKey(), compressor.hashKey());
    for (EffectType type : effectTypes) h = combine(h, type);
    // Settings in key order so the hash does not depend on map iteration order
    std::vector<std::string> keys;
    keys.reserve(settings.size());
    for (const auto& [key, value] : settings) keys.push_back(key);
    std::sort(keys.begin(), keys.end());
    for (const auto& key : keys) h = combine(h, key, hashAny(settings.at(key)));
    return h;
}

uint64_t MixerParams::hashKey() const {
    uint64_t h = combine(0x54u, channels, masterGain, hashList(trackGains), mixerType, realTimeProcessing,
                         bufferSize, enableGPUAcceleration, hashList(automationCurves));
    for (const auto& pan : panPositions) h = combine(h, hashVec2(pan));
    return h;
}

uint64_t ExportParams::hashKey() const {
    return combine(0x55u, format, sampleRate, bitDepth, exportDefinitionPath, hashBuffer(sourceBuffer),
                   audioFormat, exportSampleRate, exportBitDepth, exportChannels, compressionLevel,
                   enableDithering, enableNormalization, metadata, enableGPUAcceleration);
}

uint64_t LODParams::hashKey() const {
    uint64_t h = combine(0x56u, hashList(sampleRates), hashList(bitDepths), enableGPUAcceleration,
                         optimizationLevel, hashBuffer(sourceBuffer), sourceSampleRate);
    for (LODLevel level : lodLevels) h = combine(h, level);
    for (SampleRate rate : lodSampleRates) h = combine(h, rate);
    for (BitDepth depth : lodBitDepths) h = combine(h, depth);
    for (ChannelLayout layout : lodChannels) h = combine(h, layout);
    return h;
}

uint64_t AudioMetadata::hashKey() const {
    return combine(0x57u, id, duration, loop, artist, title, album, genre, year, comment,
                   copyright, composer, producer, engineer, publisher, isrc, upc, catalog, bpm, key, mood, tags);
}

uint64_t AudioBundle::hashKey() const {
    uint64_t h = combine(0x58u, hashBuffer(buffer), meta.hashKey(), lodBuffers.size(), gpuAccelerated);
    for (const auto& lod : lodBuffers) h = combine(h, hashBuffer(lod));
    for (LODLevel level : lodLevels) h = combine(h, level);
    return h;
}

// ---------------------------------------------------------------------------
// Batch helpers
// ---------------------------------------------------------------------------
namespace AudioGenerators {

std::vector<AudioBuffer> processSamples(SampleGen& generator, const std::vector<SampleParams>& params) {
    LOG_AUDIO_GEN(ProcessingSamples, params.size());
    std::vector<AudioBuffer> buffers;
    buffers.reserve(params.size());
    for (const auto& p : params) {
        AudioBundle bundle = generator.process(p);
        if (!bundle.buffer.empty()) buffers.push_back(std::move(bundle.buffer));
    }
    return buffers;
}

std::vector<AudioBuffer> generateSynths(SynthGen& generator, const std::vector<SynthParams>& params, float duration) {
    LOG_AUDIO_GEN(GeneratingSynths, params.size());
    std::vector<AudioBuffer> buffers;
    buffers.reserve(params.size());
    for (const auto& p : params) {
        SynthParams request = p;
        if (duration > 0.0f) request.duration = duration;
        AudioBundle bundle = generator.process(request);
        if (!bundle.buffer.empty()) buffers.push_back(std::move(bundle.buffer));
    }
    return buffers;
}

AudioBuffer applyEffects(EffectGen& generator, const AudioBuffer& input, const EffectParams& ep) {
    LOG_AUDIO_GEN(ApplyingEffects, ep.chain.size() + ep.effectTypes.size());
    if (EffectGen::resolveChain(ep).empty() || input.empty()) return input;
    return generator.processChain(input, ep);
}

AudioBuffer mixTracks(MixerGen& generator, const std::vector<AudioBuffer>& samples,
                      const std::vector<AudioBuffer>& synths, const MixerParams& mp) {
    LOG_AUDIO_GEN(MixingTracks, samples.size() + synths.size());
    std::vector<AudioBuffer> tracks;
    tracks.reserve(samples.size() + synths.size());
    tracks.insert(tracks.end(), samples.begin(), samples.end());
    tracks.insert(tracks.end(), synths.begin(), synths.end());
    if (tracks.empty()) return {};
    return generator.mixChannels(tracks, mp);
}

bool exportAudio(ExportGen& generator, const AudioBuffer& buf, const ExportParams& xp, const std::string& outPath) {
    LOG_AUDIO_GEN(ExportingAudio, outPath);
    ExportResult result = generator.exportAudio(xp, buf);
    if (result.convertedFiles.empty()) {
        Log::warn("Audio", "Export to {} produced no file: {}", outPath, result.errorMessage);
        return false;
    }
    const std::filesystem::path out(outPath);
    std::error_code ec;
    if (out.has_parent_path()) std::filesystem::create_directories(out.parent_path(), ec);
    if (!FileIO::writeFileBytes(outPath, result.convertedFiles.front().data)) {
        Log::warn("Audio", "Could not write exported audio to {}", outPath);
        return false;
    }
    return true;
}

std::vector<AudioBuffer> resampleLODs(LODGen& generator, const AudioBuffer& master, const LODParams& lp) {
    LOG_AUDIO_GEN(ResamplingForLOD, lp.lodLevels.size());
    LODParams request = lp;
    request.sourceBuffer = master;
    if (request.sourceSampleRate == 0) request.sourceSampleRate = 44100;
    AudioBundle bundle = generator.process(request);
    return bundle.lodBuffers;
}

} // namespace AudioGenerators

} // namespace Audio
} // namespace MagiTech
