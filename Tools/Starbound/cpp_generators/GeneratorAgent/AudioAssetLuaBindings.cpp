#include "AudioAssetLuaBindings.hpp"
#include "AudioAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>
#include <memory>

namespace MagiTech {
namespace Audio {

static std::vector<std::pair<std::future<AudioBundle>, std::string>> pendingAudio;
static std::shared_ptr<AudioAssetFactory> g_audioFactory;

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

    // Note: Binding std::any directly to Lua is complex. This is a simplified binding.
    lua.new_usertype<EffectParams>("EffectParams", sol::constructors<EffectParams()>(),
        "chain", &EffectParams::chain,
        "effectTypes", &EffectParams::effectTypes,
        "processingQuality", &EffectParams::processingQuality,
        "oversamplingFactor", &EffectParams::oversamplingFactor,
        "enableAntiAliasing", &EffectParams::enableAntiAliasing,
        "enableGPUAcceleration", &EffectParams::enableGPUAcceleration);

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
        "audioFormat", &ExportParams::audioFormat,
        "exportSampleRate", &ExportParams::exportSampleRate,
        "exportBitDepth", &ExportParams::exportBitDepth,
        "exportChannels", &ExportParams::exportChannels,
        "compressionLevel", &ExportParams::compressionLevel,
        "enableDithering", &ExportParams::enableDithering,
        "enableNormalization", &ExportParams::enableNormalization,
        "metadata", &ExportParams::metadata,
        "enableGPUAcceleration", &ExportParams::enableGPUAcceleration);

    lua.new_usertype<LODParams>("LODParams", sol::constructors<LODParams()>(),
        "sampleRates", &LODParams::sampleRates, 
        "bitDepths", &LODParams::bitDepths,
        "lodLevels", &LODParams::lodLevels,
        "lodSampleRates", &LODParams::lodSampleRates,
        "lodBitDepths", &LODParams::lodBitDepths,
        "lodChannels", &LODParams::lodChannels,
        "enableGPUAcceleration", &LODParams::enableGPUAcceleration,
        "optimizationLevel", &LODParams::optimizationLevel);

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

    lua.new_usertype<AudioPerformanceMetrics>("AudioPerformanceMetrics", sol::no_constructor,
        "cacheHits", &AudioPerformanceMetrics::cacheHits,
        "cacheMisses", &AudioPerformanceMetrics::cacheMisses,
        "totalGenerations", &AudioPerformanceMetrics::totalGenerations,
        "gpuGenerations", &AudioPerformanceMetrics::gpuGenerations,
        "totalProcessingTime", &AudioPerformanceMetrics::totalProcessingTime,
        "peakMemoryUsage", &AudioPerformanceMetrics::peakMemoryUsage,
        "gpuMemoryUsage", &AudioPerformanceMetrics::gpuMemoryUsage,
        "gpuUtilization", &AudioPerformanceMetrics::gpuUtilization,
        "reset", &AudioPerformanceMetrics::reset,
        "getCacheHitRate", &AudioPerformanceMetrics::getCacheHitRate,
        "getAverageProcessingTime", &AudioPerformanceMetrics::getAverageProcessingTime);

    // Bind AudioAssetFactory
    lua.new_usertype<AudioAssetFactory>("AudioAssetFactory", sol::no_constructor,
        "initialize", &AudioAssetFactory::initialize,
        "shutdown", &AudioAssetFactory::shutdown,
        "isInitialized", &AudioAssetFactory::isInitialized,
        "generateAsync", sol::overload(
            static_cast<std::future<AudioBundle>(AudioAssetFactory::*)(const SoundParams&, const std::vector<SampleParams>&, const std::vector<SynthParams>&, const EffectParams&, const MixerParams&, const ExportParams&, const LODParams&)>(&AudioAssetFactory::generateAsync),
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
        "generateBatchAsync", sol::overload(
            static_cast<std::vector<std::future<AudioBundle>>(AudioAssetFactory::*)(const std::vector<SampleParams>&)>(&AudioAssetFactory::generateBatchAsync),
            static_cast<std::vector<std::future<AudioBundle>>(AudioAssetFactory::*)(const std::vector<SynthParams>&)>(&AudioAssetFactory::generateBatchAsync)
        ),
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
        "setGPUDevice", &AudioAssetFactory::setGPUDevice,
        "setThreadPool", &AudioAssetFactory::setThreadPool,
        "setMaxProcessingThreads", &AudioAssetFactory::setMaxProcessingThreads,
        "setQualitySettings", &AudioAssetFactory::setQualitySettings,
        "generateLOD", &AudioAssetFactory::generateLOD,
        "generateLODChain", &AudioAssetFactory::generateLODChain);

    // Create global AudioFactory table
    lua["AudioFactory"] = lua.create_table_with(
        "getInstance", [&]() -> std::shared_ptr<AudioAssetFactory> {
            if (!g_audioFactory) {
                g_audioFactory = std::make_shared<AudioAssetFactory>();
                g_audioFactory->initialize(1000, 4);
            }
            return g_audioFactory;
        },
        "generateSample", [&](const SampleParams& params) -> std::future<AudioBundle> {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateAsync(params);
        },
        "generateSynth", [&](const SynthParams& params) -> std::future<AudioBundle> {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateAsync(params);
        },
        "generateEffect", [&](const EffectParams& params) -> std::future<AudioBundle> {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateAsync(params);
        },
        "generateMixer", [&](const MixerParams& params) -> std::future<AudioBundle> {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateAsync(params);
        },
        "generateExport", [&](const ExportParams& params) -> std::future<AudioBundle> {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateAsync(params);
        },
        "generateSync", [&](const SampleParams& params) -> AudioBundle {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateSync(params);
        },
        "generateSynthSync", [&](const SynthParams& params) -> AudioBundle {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->generateSync(params);
        },
        "getPerformanceMetrics", [&]() -> AudioPerformanceMetrics {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            return factory->getPerformanceMetrics();
        },
        "clearCache", [&]() {
            if (g_audioFactory) {
                g_audioFactory->clearCache();
            }
        },
        "warmupCache", [&]() {
            if (g_audioFactory) {
                g_audioFactory->warmupCache();
            }
        }
    );

    // Legacy interface for backward compatibility
    lua.set_function("spawn_audio_asset",
        [&](const SoundParams& sp, const std::vector<SampleParams>& sam, const std::vector<SynthParams>& syn,
            const EffectParams& ep, const MixerParams& mp, const ExportParams& xp, const LODParams& lp) {
            auto factory = g_audioFactory ? g_audioFactory : std::make_shared<AudioAssetFactory>();
            pendingAudio.emplace_back(factory->generateAsync(sp, sam, syn, ep, mp, xp, lp), sp.id);
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
