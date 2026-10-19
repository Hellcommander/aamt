#include "AudioAssetLuaBindings.hpp"
#include "AudioAssetFactory.hpp"
#include "GPUAudioInterface.hpp"
#include <algorithm>
#include <chrono>
#include <future>
#include <mutex>
#include <vector>
#include <memory>

namespace MagiTech {
namespace Audio {

static std::vector<std::pair<std::future<AudioBundle>, std::string>> pendingAudio;

namespace {

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}

std::shared_ptr<AudioAssetFactory>& factorySlot() {
    static std::shared_ptr<AudioAssetFactory> slot;
    return slot;
}

// Converts a Lua array of usertype values (e.g. SampleParams) to a vector.
template<typename T>
std::vector<T> tableToVector(const sol::table& table) {
    std::vector<T> out;
    const size_t n = table.size();
    out.reserve(n);
    for (size_t i = 1; i <= n; ++i) {
        sol::object item = table[i];
        if (item.is<T>()) out.push_back(item.as<T>());
    }
    return out;
}

sol::table futuresToTable(sol::this_state s, std::vector<std::future<AudioBundle>>&& futures) {
    sol::state_view lua(s);
    sol::table result = lua.create_table(static_cast<int>(futures.size()), 0);
    for (size_t i = 0; i < futures.size(); ++i) {
        result[i + 1] = std::move(futures[i]);
    }
    return result;
}

std::vector<std::future<AudioBundle>> batchFromTable(AudioAssetFactory& factory, const sol::table& params) {
    if (params.size() > 0) {
        sol::object first = params[1];
        if (first.is<SynthParams>()) {
            return factory.generateBatchAsync(tableToVector<SynthParams>(params));
        }
    }
    return factory.generateBatchAsync(tableToVector<SampleParams>(params));
}

} // namespace

void AudioAssetLuaBindings::setFactory(std::shared_ptr<AudioAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<AudioAssetFactory> AudioAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<AudioAssetFactory>();
        slot->initialize(16, 4);
    }
    return slot;
}

void AudioAssetLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum<AudioFormat>("AudioFormat", {
        {"WAV", AudioFormat::WAV},
        {"OGG", AudioFormat::OGG},
        {"FLAC", AudioFormat::FLAC},
        {"MP3", AudioFormat::MP3}
    });

    lua.new_enum<SampleRate>("SampleRate", {
        {"SR_8000", SampleRate::SR_8000},
        {"SR_11025", SampleRate::SR_11025},
        {"SR_16000", SampleRate::SR_16000},
        {"SR_22050", SampleRate::SR_22050},
        {"SR_44100", SampleRate::SR_44100},
        {"SR_48000", SampleRate::SR_48000},
        {"SR_96000", SampleRate::SR_96000},
        {"SR_192000", SampleRate::SR_192000}
    });

    lua.new_enum<BitDepth>("BitDepth", {
        {"BD_16", BitDepth::BD_16},
        {"BD_24", BitDepth::BD_24},
        {"BD_32", BitDepth::BD_32},
        {"BD_FLOAT", BitDepth::BD_FLOAT}
    });

    lua.new_enum<ChannelLayout>("ChannelLayout", {
        {"MONO", ChannelLayout::MONO},
        {"STEREO", ChannelLayout::STEREO},
        {"SURROUND_5_1", ChannelLayout::SURROUND_5_1},
        {"SURROUND_7_1", ChannelLayout::SURROUND_7_1}
    });

    lua.new_enum<WaveformType>("WaveformType", {
        {"SINE", WaveformType::SINE},
        {"SQUARE", WaveformType::SQUARE},
        {"SAW", WaveformType::SAW},
        {"TRIANGLE", WaveformType::TRIANGLE},
        {"NOISE", WaveformType::NOISE},
        {"CUSTOM", WaveformType::CUSTOM}
    });

    lua.new_enum<EffectType>("EffectType", {
        {"REVERB", EffectType::REVERB},
        {"DELAY", EffectType::DELAY},
        {"CHORUS", EffectType::CHORUS},
        {"FLANGER", EffectType::FLANGER},
        {"DISTORTION", EffectType::DISTORTION},
        {"COMPRESSOR", EffectType::COMPRESSOR},
        {"EQUALIZER", EffectType::EQUALIZER},
        {"FILTER", EffectType::FILTER}
    });

    lua.new_enum<MixerType>("MixerType", {
        {"LINEAR", MixerType::LINEAR},
        {"LOGARITHMIC", MixerType::LOGARITHMIC},
        {"CUSTOM", MixerType::CUSTOM}
    });

    lua.new_enum<LODLevel>("LODLevel", {
        {"HIGH", LODLevel::HIGH},
        {"MEDIUM", LODLevel::MEDIUM},
        {"LOW", LODLevel::LOW},
        {"ULTRA_LOW", LODLevel::ULTRA_LOW}
    });

    // Bind parameter structs
    lua.new_usertype<SoundParams>("SoundParams", sol::constructors<SoundParams()>(),
        "id", &SoundParams::id,
        "duration", &SoundParams::duration,
        "loop", &SoundParams::loop);

    lua.new_usertype<SampleParams>("SampleParams", sol::constructors<SampleParams()>(),
        "filePath", &SampleParams::filePath,
        "trimRange", &SampleParams::trimRange,
        "pitchShift", &SampleParams::pitchShift,
        "gain", &SampleParams::gain,
        "sampleDefinitionPath", &SampleParams::sampleDefinitionPath,
        "sampleRate", &SampleParams::sampleRate,
        "bitDepth", &SampleParams::bitDepth,
        "channels", &SampleParams::channels,
        "normalize", &SampleParams::normalize,
        "trimSilence", &SampleParams::trimSilence,
        "fadeInOut", &SampleParams::fadeInOut,
        "enableGPUAcceleration", &SampleParams::enableGPUAcceleration);

    lua.new_usertype<SynthParams>("SynthParams", sol::constructors<SynthParams()>(),
        "waveType", &SynthParams::waveType,
        "frequency", &SynthParams::frequency,
        "freqEnvelope", &SynthParams::freqEnvelope,
        "ampEnvelope", &SynthParams::ampEnvelope,
        "polyphonic", &SynthParams::polyphonic,
        "duration", &SynthParams::duration,
        "instrumentDefinitionPath", &SynthParams::instrumentDefinitionPath,
        "waveformType", &SynthParams::waveformType,
        "amplitude", &SynthParams::amplitude,
        "phase", &SynthParams::phase,
        "frequencyModulation", &SynthParams::frequencyModulation,
        "amplitudeModulation", &SynthParams::amplitudeModulation,
        "phaseModulation", &SynthParams::phaseModulation,
        "adsrEnvelope", &SynthParams::adsrEnvelope,
        "enableAntiAliasing", &SynthParams::enableAntiAliasing,
        "oversamplingFactor", &SynthParams::oversamplingFactor,
        "harmonicLimit", &SynthParams::harmonicLimit,
        "enableGPUAcceleration", &SynthParams::enableGPUAcceleration);

    // EffectParams::settings holds std::any values; numeric settings are exposed through
    // setSetting/getSetting.
    lua.new_usertype<EffectParams>("EffectParams", sol::constructors<EffectParams()>(),
        "chain", &EffectParams::chain,
        "effectTypes", &EffectParams::effectTypes,
        "inputBuffer", &EffectParams::inputBuffer,
        "sampleRate", &EffectParams::sampleRate,
        "processingQuality", &EffectParams::processingQuality,
        "oversamplingFactor", &EffectParams::oversamplingFactor,
        "enableAntiAliasing", &EffectParams::enableAntiAliasing,
        "enableGPUAcceleration", &EffectParams::enableGPUAcceleration,
        "setSetting", [](EffectParams& p, const std::string& key, double value) {
            p.settings[key] = static_cast<float>(value);
        },
        "getSetting", [](const EffectParams& p, const std::string& key) -> sol::optional<double> {
            auto it = p.settings.find(key);
            if (it == p.settings.end()) return sol::nullopt;
            if (const float* f = std::any_cast<float>(&it->second)) return static_cast<double>(*f);
            if (const double* d = std::any_cast<double>(&it->second)) return *d;
            if (const int* i = std::any_cast<int>(&it->second)) return static_cast<double>(*i);
            return sol::nullopt;
        });

    lua.new_usertype<MixerParams>("MixerParams", sol::constructors<MixerParams()>(),
        "channels", &MixerParams::channels,
        "masterGain", &MixerParams::masterGain,
        "trackGains", &MixerParams::trackGains,
        "mixerType", &MixerParams::mixerType,
        "realTimeProcessing", &MixerParams::realTimeProcessing,
        "bufferSize", &MixerParams::bufferSize,
        "enableGPUAcceleration", &MixerParams::enableGPUAcceleration,
        "panPositions", &MixerParams::panPositions,
        "automationCurves", &MixerParams::automationCurves);

    lua.new_usertype<ExportParams>("ExportParams", sol::constructors<ExportParams()>(),
        "format", &ExportParams::format,
        "sampleRate", &ExportParams::sampleRate,
        "bitDepth", &ExportParams::bitDepth,
        "exportDefinitionPath", &ExportParams::exportDefinitionPath,
        "sourceBuffer", &ExportParams::sourceBuffer,
        "audioFormat", &ExportParams::audioFormat,
        "exportSampleRate", &ExportParams::exportSampleRate,
        "exportBitDepth", &ExportParams::exportBitDepth,
        "exportChannels", &ExportParams::exportChannels,
        "compressionLevel", &ExportParams::compressionLevel,
        "enableDithering", &ExportParams::enableDithering,
        "enableNormalization", &ExportParams::enableNormalization,
        "metadata", &ExportParams::metadata,
        "enableGPUAcceleration", &ExportParams::enableGPUAcceleration);

    lua.new_usertype<LODParams>("AudioLODParams", sol::constructors<LODParams()>(),
        "sampleRates", &LODParams::sampleRates,
        "bitDepths", &LODParams::bitDepths,
        "lodLevels", &LODParams::lodLevels,
        "lodSampleRates", &LODParams::lodSampleRates,
        "lodBitDepths", &LODParams::lodBitDepths,
        "lodChannels", &LODParams::lodChannels,
        "enableGPUAcceleration", &LODParams::enableGPUAcceleration,
        "optimizationLevel", &LODParams::optimizationLevel,
        "sourceBuffer", &LODParams::sourceBuffer,
        "sourceSampleRate", &LODParams::sourceSampleRate);

    lua.new_usertype<AudioBundle>("AudioBundle", sol::no_constructor,
        "buffer", &AudioBundle::buffer,
        "lodBuffers", &AudioBundle::lodBuffers,
        "meta", &AudioBundle::meta,
        "gpuBuffer", &AudioBundle::gpuBuffer,
        "gpuTexture", &AudioBundle::gpuTexture,
        "gpuPipeline", &AudioBundle::gpuPipeline,
        "gpuDescriptorSet", &AudioBundle::gpuDescriptorSet,
        "creationTime", &AudioBundle::creationTime,
        "quality", &AudioBundle::quality,
        "gpuAccelerated", &AudioBundle::gpuAccelerated,
        "lodLevels", &AudioBundle::lodLevels,
        "lodSampleRates", &AudioBundle::lodSampleRates,
        "lodBitDepths", &AudioBundle::lodBitDepths,
        "lodChannels", &AudioBundle::lodChannels);

    lua.new_usertype<AudioMetadata>("AudioMetadata", sol::no_constructor,
        "id", &AudioMetadata::id,
        "duration", &AudioMetadata::duration,
        "loop", &AudioMetadata::loop,
        "artist", &AudioMetadata::artist,
        "title", &AudioMetadata::title,
        "album", &AudioMetadata::album,
        "genre", &AudioMetadata::genre,
        "year", &AudioMetadata::year,
        "comment", &AudioMetadata::comment,
        "copyright", &AudioMetadata::copyright,
        "composer", &AudioMetadata::composer,
        "publisher", &AudioMetadata::publisher,
        "tags", &AudioMetadata::tags,
        "quality", &AudioMetadata::quality,
        "creationTime", &AudioMetadata::creationTime);

    lua.new_usertype<AudioQualityMetrics>("AudioQualityMetrics", sol::no_constructor,
        "peakAmplitude", &AudioQualityMetrics::peakAmplitude,
        "rmsAmplitude", &AudioQualityMetrics::rmsAmplitude,
        "dynamicRange", &AudioQualityMetrics::dynamicRange,
        "signalToNoiseRatio", &AudioQualityMetrics::signalToNoiseRatio,
        "frequencyResponse", &AudioQualityMetrics::frequencyResponse,
        "distortion", &AudioQualityMetrics::distortion,
        "isHighQuality", &AudioQualityMetrics::isHighQuality);

    // Atomic counters are exposed as read-only snapshot values
    lua.new_usertype<AudioPerformanceMetrics>("AudioPerformanceMetrics", sol::no_constructor,
        "cacheHits", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.cacheHits.load(); }),
        "cacheMisses", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.cacheMisses.load(); }),
        "totalGenerations", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.totalGenerations.load(); }),
        "gpuGenerations", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.gpuGenerations.load(); }),
        "totalProcessingTime", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.totalProcessingTime.load(); }),
        "peakMemoryUsage", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.peakMemoryUsage.load(); }),
        "gpuMemoryUsage", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.gpuMemoryUsage.load(); }),
        "gpuUtilization", sol::readonly_property([](const AudioPerformanceMetrics& m) { return m.gpuUtilization.load(); }),
        "reset", &AudioPerformanceMetrics::reset,
        "getCacheHitRate", &AudioPerformanceMetrics::getCacheHitRate,
        "getAverageProcessingTime", &AudioPerformanceMetrics::getAverageProcessingTime);

    // Pending generation result (std::future is move-only and lives in Lua as userdata)
    lua.new_usertype<std::future<AudioBundle>>("AudioBundleFuture", sol::no_constructor,
        "valid", [](const std::future<AudioBundle>& f) { return f.valid(); },
        "ready", [](const std::future<AudioBundle>& f) {
            return f.valid() && f.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
        },
        "wait", [](const std::future<AudioBundle>& f) { if (f.valid()) f.wait(); },
        "get", [](std::future<AudioBundle>& f) { return f.get(); });

    // Bind AudioAssetFactory
    lua.new_usertype<AudioAssetFactory>("AudioAssetFactory", sol::no_constructor,
        "initialize", &AudioAssetFactory::initialize,
        "shutdown", &AudioAssetFactory::shutdown,
        "isInitialized", &AudioAssetFactory::isInitialized,
        "generateAsync", sol::overload(
            [](AudioAssetFactory& f, const SoundParams& sp, const sol::table& samples, const sol::table& synths,
               const EffectParams& ep, const MixerParams& mp, const ExportParams& xp, const LODParams& lp) {
                return f.generateAsync(sp, tableToVector<SampleParams>(samples), tableToVector<SynthParams>(synths),
                                       ep, mp, xp, lp);
            },
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const SampleParams&)>(&AudioAssetFactory::generateAsync),
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const SynthParams&)>(&AudioAssetFactory::generateAsync),
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const EffectParams&)>(&AudioAssetFactory::generateAsync),
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const MixerParams&)>(&AudioAssetFactory::generateAsync),
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const ExportParams&)>(&AudioAssetFactory::generateAsync)
        ),
        "generateSync", sol::overload(
            static_cast<AudioBundle(AudioAssetFactory::*)(const SampleParams&)>(&AudioAssetFactory::generateSync),
            static_cast<AudioBundle(AudioAssetFactory::*)(const SynthParams&)>(&AudioAssetFactory::generateSync),
            static_cast<AudioBundle(AudioAssetFactory::*)(const EffectParams&)>(&AudioAssetFactory::generateSync),
            static_cast<AudioBundle(AudioAssetFactory::*)(const MixerParams&)>(&AudioAssetFactory::generateSync),
            static_cast<AudioBundle(AudioAssetFactory::*)(const ExportParams&)>(&AudioAssetFactory::generateSync)
        ),
        // Accepts a table of SampleParams or of SynthParams; returns a table of AudioBundleFuture
        "generateBatchAsync", [](AudioAssetFactory& f, const sol::table& params, sol::this_state s) {
            return futuresToTable(s, batchFromTable(f, params));
        },
        "clearCache", &AudioAssetFactory::clearCache,
        "getCacheSize", &AudioAssetFactory::getCacheSize,
        "getCacheHitRate", &AudioAssetFactory::getCacheHitRate,
        "setCacheCapacity", &AudioAssetFactory::setCacheCapacity,
        "preloadCommonAudio", &AudioAssetFactory::preloadCommonAudio,
        "warmupCache", &AudioAssetFactory::warmupCache,
        "getPerformanceMetrics", &AudioAssetFactory::getPerformanceMetrics,
        "resetPerformanceMetrics", &AudioAssetFactory::resetPerformanceMetrics,
        "enableGPUAcceleration", &AudioAssetFactory::enableGPUAcceleration,
        "isGPUAccelerationEnabled", &AudioAssetFactory::isGPUAccelerationEnabled,
        // Ownership-transferring setters take their argument from C++; Lua can request fresh instances.
        "resetGPUDevice", [](AudioAssetFactory& f) { f.setGPUDevice(std::make_unique<GPUAudioInterface>()); },
        "setThreadPool", [](AudioAssetFactory& f, size_t threads) {
            f.setThreadPool(std::make_unique<GeneratorTaskPool>(std::max<size_t>(1, threads)));
        },
        "setMaxProcessingThreads", &AudioAssetFactory::setMaxProcessingThreads,
        "setQualitySettings", &AudioAssetFactory::setQualitySettings,
        "generateLOD", &AudioAssetFactory::generateLOD,
        "generateLODChain", &AudioAssetFactory::generateLODChain);

    // Create global AudioFactory table
    lua["AudioFactory"] = lua.create_table_with(
        "getInstance", []() -> std::shared_ptr<AudioAssetFactory> {
            return AudioAssetLuaBindings::factory();
        },
        "generateSample", [](const SampleParams& params) -> std::future<AudioBundle> {
            return AudioAssetLuaBindings::factory()->generateAsync(params);
        },
        "generateSynth", [](const SynthParams& params) -> std::future<AudioBundle> {
            return AudioAssetLuaBindings::factory()->generateAsync(params);
        },
        "generateEffect", [](const EffectParams& params) -> std::future<AudioBundle> {
            return AudioAssetLuaBindings::factory()->generateAsync(params);
        },
        "generateMixer", [](const MixerParams& params) -> std::future<AudioBundle> {
            return AudioAssetLuaBindings::factory()->generateAsync(params);
        },
        "generateExport", [](const ExportParams& params) -> std::future<AudioBundle> {
            return AudioAssetLuaBindings::factory()->generateAsync(params);
        },
        "generateSync", [](const SampleParams& params) -> AudioBundle {
            return AudioAssetLuaBindings::factory()->generateSync(params);
        },
        "generateSynthSync", [](const SynthParams& params) -> AudioBundle {
            return AudioAssetLuaBindings::factory()->generateSync(params);
        },
        "getPerformanceMetrics", []() -> AudioPerformanceMetrics {
            return AudioAssetLuaBindings::factory()->getPerformanceMetrics();
        },
        "clearCache", []() {
            AudioAssetLuaBindings::factory()->clearCache();
        },
        "warmupCache", []() {
            AudioAssetLuaBindings::factory()->warmupCache();
        }
    );

    // Legacy interface for backward compatibility
    lua.set_function("spawn_audio_asset",
        [](const SoundParams& sp, const sol::table& sam, const sol::table& syn,
           const EffectParams& ep, const MixerParams& mp, const ExportParams& xp, const LODParams& lp) {
            auto factory = AudioAssetLuaBindings::factory();
            pendingAudio.emplace_back(factory->generateAsync(sp, tableToVector<SampleParams>(sam),
                                                             tableToVector<SynthParams>(syn), ep, mp, xp, lp),
                                      sp.id);
        }
    );
}

void AudioAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAudio.begin(); it != pendingAudio.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Audio asset ready: " + it->second);
            } catch (const std::exception& e) {
                lua["print"]("Audio asset error: " + std::string(e.what()));
            }
            it = pendingAudio.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Audio
} // namespace MagiTech
