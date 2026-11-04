#pragma once

// Audio level-of-detail generator (MagiTech::Audio::LODGen).
// Note: GeneratorAgent/LODGen.hpp is the unrelated Trail-family ::LODGen namespace; the audio
// LOD generator (implemented in LODGen.cpp) is declared here.

#include "AudioAssetTypes.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace MagiTech {
namespace Audio {

class LODGen {
public:
    LODGen();
    ~LODGen();

    // Builds the LOD chain described by params from params.sourceBuffer (interleaved stereo
    // at params.sourceSampleRate), or from a reference signal when no source is given.
    AudioBundle process(const LODParams& params);

    // Derives one LOD level from interleaved stereo audio at sourceSampleRate. The result is
    // resampled to sampleRate, quantised to bitDepth and laid out as `channels`.
    std::vector<float> generateLODLevel(const std::vector<float>& originalAudio, LODLevel level,
                                        SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels,
                                        uint32_t sourceSampleRate = 44100);

    // Reference signal used when no source audio is supplied
    std::vector<float> generateTestAudio();

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
    // Quality reduction stages per level
    void applyHighQualityReduction(std::vector<float>& audio, SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels);
    void applyMediumQualityReduction(std::vector<float>& audio, SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels);
    void applyLowQualityReduction(std::vector<float>& audio, SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels);
    void applyUltraLowQualityReduction(std::vector<float>& audio, SampleRate sampleRate, BitDepth bitDepth, ChannelLayout channels);

    // Audio processing (interleaved stereo unless noted)
    void applyLowPassFilter(std::vector<float>& audio, float cutoffFreq, float resonance);
    void applyDynamicRangeCompression(std::vector<float>& audio, float threshold, float ratio);
    void applyBitDepthReduction(std::vector<float>& audio, float effectiveBits);
    void maintainStereoWidth(std::vector<float>& audio);
    void reduceStereoWidth(std::vector<float>& audio, float widthFactor);
    void convertToMono(std::vector<float>& audio);
    void downsample(std::vector<float>& audio, int factor);

    float clamp(float value, float min, float max);

    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    int m_maxProcessingThreads;
    std::string m_lastError;

    int m_optimizationLevel;
    float m_targetQuality;
    size_t m_maxFileSize;

    // Sample rate / channel count of the buffer currently being processed
    uint32_t m_workingSampleRate = 44100;
    uint32_t m_workingChannels = 2;
};

} // namespace Audio
} // namespace MagiTech
