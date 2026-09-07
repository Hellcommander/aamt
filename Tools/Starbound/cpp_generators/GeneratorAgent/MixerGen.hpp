#pragma once

#include "AudioAssetTypes.hpp"
#include <memory>
#include <vector>

namespace MagiTech {
namespace Audio {

// Audio mixing and channel processing
class MixerGen {
public:
    MixerGen();
    ~MixerGen();
    
    // Core processing
    AudioBundle process(const MixerParams& params);
    
    // Channel mixing
    std::vector<float> mixChannels(const std::vector<std::vector<float>>& channels, const MixerParams& params);
    
    // Automation
    void applyAutomation(std::vector<float>& samples, const std::vector<float>& automationCurves);
    
    // Master processing
    void applyMasterProcessing(std::vector<float>& samples, const MixerParams& params);
    
    // Channel management
    void addInputChannel(const std::string& name, const std::vector<float>& samples);
    void removeInputChannel(const std::string& name);
    void clearInputChannels();
    
    // Quality settings
    void setMixingQuality(int quality);
    void setRealTimeProcessing(bool enabled);
    void setBufferSize(int size);
    
    // Processing options
    void enableGPUAcceleration(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Error handling
    std::string getLastError() const;
    void clearLastError();

private:
    // Channel data structure
    struct ChannelData {
        std::string name;
        std::vector<float> samples;
        float gain;
        glm::vec2 pan;
        bool muted;
        bool solo;
    };
    
    // Automation point structure
    struct AutomationPoint {
        float time;
        float value;
        float curve; // 0 = linear, 1 = exponential, etc.
    };
    
    // Mixing algorithms
    std::vector<float> linearMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains);
    std::vector<float> logarithmicMix(const std::vector<std::vector<float>>& channels, const std::vector<float>& gains);
    std::vector<float> customMix(const std::vector<std::vector<float>>& channels, const MixerParams& params);
    
    // Panning algorithms
    void applyStereoPanning(std::vector<float>& samples, const glm::vec2& pan);
    void applySurroundPanning(std::vector<float>& samples, const glm::vec2& pan, uint32_t channels);
    
    // Utility functions
    float clamp(float value, float min, float max);
    float lerp(float a, float b, float t);
    float smoothstep(float edge0, float edge1, float x);
    float calculateRMS(const std::vector<float>& samples);
    float calculatePeak(const std::vector<float>& samples);
    
    // Member variables
    std::vector<ChannelData> m_inputChannels;
    std::vector<AutomationPoint> m_automationPoints;
    
    bool m_gpuAccelerationEnabled;
    int m_mixingQuality;
    bool m_realTimeProcessing;
    int m_bufferSize;
    int m_maxProcessingThreads;
    std::string m_lastError;
    
    // Constants
    static constexpr float MIN_GAIN = -60.0f; // -60 dB
    static constexpr float MAX_GAIN = 20.0f;  // +20 dB
    static constexpr float DEFAULT_GAIN = 0.0f; // 0 dB
};

} // namespace Audio
} // namespace MagiTech 
