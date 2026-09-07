#include "SampleGenPipeline.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <thread>
#include <future>
#include <filesystem>

// Include YAML and JSON libraries (placeholders)
// #include <yaml-cpp/yaml.h>
// #include <nlohmann/json.hpp>

namespace MagiTech {
namespace Audio {

SampleGenPipeline::SampleGenPipeline()
    : m_sampleGen(std::make_unique<SampleGen>()) {
}

SampleGenPipeline::~SampleGenPipeline() = default;

// Pipeline stages
bool SampleGenPipeline::importFromDefinition(const std::string& definitionPath) {
    clearLastError();
    m_progress.currentStage = "Loading definition";
    m_progress.percentage = 0.0f;
    
    try {
        SamplePackDefinition definition;
        if (!loadDefinition(definitionPath, definition)) {
            m_lastError = "Failed to load definition from: " + definitionPath;
            return false;
        }
        
        m_progress.percentage = 20.0f;
        m_progress.currentStage = "Processing samples";
        
        if (!processSamples(definition)) {
            m_lastError = "Failed to process samples";
            return false;
        }
        
        m_progress.percentage = 40.0f;
        m_progress.currentStage = "Analyzing samples";
        
        if (!analyzeSamples(definition.samples)) {
            m_lastError = "Failed to analyze samples";
            return false;
        }
        
        m_progress.percentage = 60.0f;
        m_progress.currentStage = "Generating variations";
        
        if (!generateVariations(definition)) {
            m_lastError = "Failed to generate variations";
            return false;
        }
        
        m_progress.percentage = 80.0f;
        m_progress.currentStage = "Packaging samples";
        
        if (!packageSamples(definition)) {
            m_lastError = "Failed to package samples";
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

bool SampleGenPipeline::processSamples(const SamplePackDefinition& definition) {
    clearLastError();
    
    try {
        for (const auto& sampleDef : definition.samples) {
            // Load audio file
            AudioBuffer buffer;
            if (!decodeAudio(sampleDef.path, buffer)) {
                m_lastError = "Failed to decode audio: " + sampleDef.path;
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
            SampleEntry entry;
            entry.buffer = std::move(buffer);
            entry.id = sampleDef.id;
            entry.rootKey = sampleDef.rootKey;
            entry.bpm = sampleDef.bpm;
            entry.loop = sampleDef.loop;
            entry.tags = sampleDef.tags;
            entry.lastModified = std::chrono::system_clock::now();
            
            // Store in package
            auto& package = m_packages[definition.name];
            package.samples[sampleDef.id] = std::move(entry);
        }
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Processing error: " + std::string(e.what());
        return false;
    }
}

bool SampleGenPipeline::analyzeSamples(const std::vector<SampleDefinition>& samples) {
    clearLastError();
    
    try {
        for (const auto& sampleDef : samples) {
            auto& package = m_packages[sampleDef.name];
            auto& sample = package.samples[sampleDef.id];
            
            // Analyze the sample
            SampleAnalysis analysis = analyzeSample(sample.buffer, DEFAULT_SAMPLE_RATE);
            
            // Update sample with analysis results
            sample.rootKey = static_cast<int>(analysis.rootPitch);
            sample.bpm = analysis.bpm;
            sample.loop = analysis.detectedLoop;
            
            // Store analysis
            m_analyses[sampleDef.id] = analysis;
        }
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Analysis error: " + std::string(e.what());
        return false;
    }
}

bool SampleGenPipeline::generateVariations(const SamplePackDefinition& definition) {
    clearLastError();
    
    if (!definition.variations.enableVariations) {
        return true; // Skip if variations are disabled
    }
    
    try {
        for (const auto& sampleDef : definition.samples) {
            auto& package = m_packages[definition.name];
            auto& originalSample = package.samples[sampleDef.id];
            
            // Generate pitch variations
            for (int semitone = definition.variations.pitchRange[0]; 
                 semitone <= definition.variations.pitchRange[1]; 
                 semitone++) {
                
                if (semitone == 0) continue; // Skip original
                
                AudioBuffer pitchedBuffer = pitchShift(originalSample.buffer, 
                                                     static_cast<float>(semitone), 
                                                     DEFAULT_SAMPLE_RATE);
                
                // Create variation sample
                SampleEntry variation;
                variation.buffer = std::move(pitchedBuffer);
                variation.id = generateSampleId(sampleDef.id, semitone);
                variation.rootKey = originalSample.rootKey + semitone;
                variation.bpm = originalSample.bpm;
                variation.loop = originalSample.loop;
                variation.tags = originalSample.tags;
                variation.lastModified = std::chrono::system_clock::now();
                
                package.samples[variation.id] = std::move(variation);
            }
            
            // Generate time-stretched variations if enabled
            if (definition.variations.timeStretch) {
                AudioBuffer stretchedBuffer = timeStretch(originalSample.buffer,
                                                       originalSample.bpm,
                                                       definition.variations.targetBPM,
                                                       DEFAULT_SAMPLE_RATE);
                
                SampleEntry stretched;
                stretched.buffer = std::move(stretchedBuffer);
                stretched.id = generateSampleId(sampleDef.id + "_stretched", 0);
                stretched.rootKey = originalSample.rootKey;
                stretched.bpm = definition.variations.targetBPM;
                stretched.loop = originalSample.loop;
                stretched.tags = originalSample.tags;
                stretched.lastModified = std::chrono::system_clock::now();
                
                package.samples[stretched.id] = std::move(stretched);
            }
        }
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Variation generation error: " + std::string(e.what());
        return false;
    }
}

bool SampleGenPipeline::packageSamples(const SamplePackDefinition& definition) {
    clearLastError();
    
    try {
        auto& package = m_packages[definition.name];
        package.name = definition.name;
        package.mappings = definition.mappings;
        package.metadataHash = computeDefinitionHash(definition);
        package.created = std::chrono::system_clock::now();
        
        // Create package file
        std::string packagePath = definition.outputPath + "/" + definition.name + ".samplepack";
        if (!createPackage(packagePath, package)) {
            m_lastError = "Failed to create package: " + packagePath;
            return false;
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
            m_lastError = "Failed to load package: " + packagePath;
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
                for (int key = zone.keyRange[0]; key <= zone.keyRange[1]; ++key) {
                    instrument.keyMap[key] = it->second;
                }
                instrument.sampleMap[zone.sampleId] = it->second;
            }
        }
        
        m_instruments[package.name] = std::move(instrument);
        
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

float SampleGenPipeline::detectRootPitch(const AudioBuffer& buffer, uint32_t sampleRate) {
    // Simple pitch detection using autocorrelation
    // In a real implementation, this would use more sophisticated algorithms
    
    const size_t maxLag = sampleRate / 50; // Minimum frequency ~50Hz
    const size_t minLag = sampleRate / 2000; // Maximum frequency ~2000Hz
    
    std::vector<float> autocorr(maxLag);
    
    // Compute autocorrelation
    for (size_t lag = minLag; lag < maxLag; ++lag) {
        float sum = 0.0f;
        for (size_t i = 0; i < buffer.size() - lag; ++i) {
            sum += buffer[i] * buffer[i + lag];
        }
        autocorr[lag] = sum;
    }
    
    // Find the peak (excluding the first few lags)
    size_t peakLag = minLag;
    float peakValue = autocorr[minLag];
    
    for (size_t lag = minLag + 1; lag < maxLag; ++lag) {
        if (autocorr[lag] > peakValue) {
            peakValue = autocorr[lag];
            peakLag = lag;
        }
    }
    
    // Convert lag to frequency
    float frequency = static_cast<float>(sampleRate) / static_cast<float>(peakLag);
    
    // Convert frequency to MIDI note number
    float midiNote = 12.0f * std::log2(frequency / 440.0f) + 69.0f;
    
    return std::round(midiNote);
}

float SampleGenPipeline::estimateBPM(const AudioBuffer& buffer, uint32_t sampleRate) {
    // Simple BPM estimation using onset detection
    // In a real implementation, this would use more sophisticated algorithms
    
    std::vector<float> onsetStrengths;
    const size_t windowSize = sampleRate / 100; // 10ms windows
    
    for (size_t i = windowSize; i < buffer.size(); i += windowSize) {
        float energy = 0.0f;
        for (size_t j = 0; j < windowSize && i + j < buffer.size(); ++j) {
            energy += buffer[i + j] * buffer[i + j];
        }
        onsetStrengths.push_back(energy);
    }
    
    // Find peaks in onset strengths
    std::vector<size_t> peaks;
    for (size_t i = 1; i < onsetStrengths.size() - 1; ++i) {
        if (onsetStrengths[i] > onsetStrengths[i-1] && 
            onsetStrengths[i] > onsetStrengths[i+1] &&
            onsetStrengths[i] > 0.1f) { // Threshold
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
    float bpm = 60.0f / beatTime;
    
    return std::clamp(bpm, 60.0f, 200.0f);
}

LoopRange SampleGenPipeline::detectLoopPoints(const AudioBuffer& buffer, uint32_t sampleRate) {
    LoopRange loop;
    loop.enabled = false;
    
    // Simple loop detection using cross-correlation
    // In a real implementation, this would use more sophisticated algorithms
    
    const size_t searchStart = buffer.size() / 4;
    const size_t searchEnd = buffer.size() * 3 / 4;
    const size_t windowSize = sampleRate / 10; // 100ms window
    
    float bestCorrelation = 0.0f;
    size_t bestStart = 0;
    size_t bestEnd = 0;
    
    for (size_t start = searchStart; start < searchEnd - windowSize; start += sampleRate / 100) {
        for (size_t end = start + windowSize; end < searchEnd; end += sampleRate / 100) {
            float correlation = 0.0f;
            size_t overlapSize = end - start;
            
            if (end + overlapSize < buffer.size()) {
                for (size_t i = 0; i < overlapSize; ++i) {
                    correlation += buffer[start + i] * buffer[end + i];
                }
                correlation /= overlapSize;
                
                if (correlation > bestCorrelation) {
                    bestCorrelation = correlation;
                    bestStart = start;
                    bestEnd = end;
                }
            }
        }
    }
    
    // If we found a good loop point
    if (bestCorrelation > 0.8f) {
        loop.enabled = true;
        loop.start = bestStart;
        loop.end = bestEnd;
        loop.type = "sustain";
        loop.autoDetect = true;
    }
    
    return loop;
}

float SampleGenPipeline::calculateLUFS(const AudioBuffer& buffer, uint32_t sampleRate) {
    // Simplified LUFS calculation
    // In a real implementation, this would use the full EBU R128 algorithm
    
    float sum = 0.0f;
    for (float sample : buffer) {
        sum += sample * sample;
    }
    
    float rms = std::sqrt(sum / buffer.size());
    float lufs = 20.0f * std::log10(rms) + 3.0f; // Approximate LUFS
    
    return lufs;
}

std::vector<float> SampleGenPipeline::findSpectralPeaks(const AudioBuffer& buffer, uint32_t sampleRate) {
    // Simplified spectral peak detection
    // In a real implementation, this would use FFT
    
    std::vector<float> peaks;
    const size_t windowSize = 1024;
    
    for (size_t i = 0; i < buffer.size() - windowSize; i += windowSize / 2) {
        float maxVal = 0.0f;
        for (size_t j = 0; j < windowSize; ++j) {
            maxVal = std::max(maxVal, std::abs(buffer[i + j]));
        }
        peaks.push_back(maxVal);
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
    
    // Apply crossfade at loop points
    const size_t crossfadeSize = 1024; // 23ms at 44.1kHz
    
    if (loop.end + crossfadeSize < buffer.size()) {
        for (size_t i = 0; i < crossfadeSize; ++i) {
            float fade = static_cast<float>(i) / crossfadeSize;
            result[loop.end + i] = result[loop.end + i] * (1.0f - fade) + 
                                  result[loop.start + i] * fade;
        }
    }
    
    return result;
}

AudioBuffer SampleGenPipeline::pitchShift(const AudioBuffer& buffer, float semitones, uint32_t sampleRate) {
    if (semitones == 0.0f) return buffer;
    
    // Simple pitch shifting using resampling
    // In a real implementation, this would use more sophisticated algorithms
    
    float ratio = std::pow(2.0f, semitones / 12.0f);
    size_t newSize = static_cast<size_t>(buffer.size() * ratio);
    
    AudioBuffer result(newSize);
    
    for (size_t i = 0; i < newSize; ++i) {
        float srcIndex = i / ratio;
        size_t srcIndex1 = static_cast<size_t>(srcIndex);
        size_t srcIndex2 = std::min(srcIndex1 + 1, buffer.size() - 1);
        float fraction = srcIndex - srcIndex1;
        
        if (srcIndex1 < buffer.size()) {
            float sample1 = buffer[srcIndex1];
            float sample2 = buffer[srcIndex2];
            result[i] = sample1 + fraction * (sample2 - sample1);
        } else {
            result[i] = 0.0f;
        }
    }
    
    return result;
}

AudioBuffer SampleGenPipeline::timeStretch(const AudioBuffer& buffer, float sourceBPM, float targetBPM, uint32_t sampleRate) {
    if (sourceBPM == targetBPM) return buffer;
    
    float ratio = sourceBPM / targetBPM;
    size_t newSize = static_cast<size_t>(buffer.size() * ratio);
    
    AudioBuffer result(newSize);
    
    for (size_t i = 0; i < newSize; ++i) {
        float srcIndex = i / ratio;
        size_t srcIndex1 = static_cast<size_t>(srcIndex);
        size_t srcIndex2 = std::min(srcIndex1 + 1, buffer.size() - 1);
        float fraction = srcIndex - srcIndex1;
        
        if (srcIndex1 < buffer.size()) {
            float sample1 = buffer[srcIndex1];
            float sample2 = buffer[srcIndex2];
            result[i] = sample1 + fraction * (sample2 - sample1);
        } else {
            result[i] = 0.0f;
        }
    }
    
    return result;
}

// Caching and hot-reload
void SampleGenPipeline::enableHotReload(bool enabled) {
    m_hotReloadEnabled = enabled;
    if (enabled) {
        // Setup file watchers for watched directories
        for (const auto& dir : m_watchedDirectories) {
            setupFileWatcher(dir);
        }
    }
}

void SampleGenPipeline::setCacheCapacity(size_t capacity) {
    m_cacheCapacity = capacity;
    // Trim cache if necessary
    if (m_packages.size() > capacity) {
        // Remove oldest packages
        // Implementation would depend on specific caching strategy
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

// Editor integration
void SampleGenPipeline::updateSampleDefinition(const std::string& sampleId, const SampleDefinition& definition) {
    // Update the definition and trigger reprocessing
    // This would typically be called from the editor UI
}

void SampleGenPipeline::regenerateVariations(const std::string& sampleId) {
    // Regenerate variations for a specific sample
    // This would typically be called from the editor UI
}

void SampleGenPipeline::rebuildPackage(const std::string& packageName) {
    // Rebuild a specific package
    // This would typically be called from the editor UI
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
    // Placeholder for YAML/JSON loading
    // In a real implementation, this would parse the YAML/JSON file
    return true;
}

bool SampleGenPipeline::saveDefinition(const std::string& path, const SamplePackDefinition& definition) {
    // Placeholder for YAML/JSON saving
    return true;
}

bool SampleGenPipeline::createPackage(const std::string& path, const SamplePackage& package) {
    // Placeholder for package creation
    return true;
}

bool SampleGenPipeline::loadPackage(const std::string& path, SamplePackage& package) {
    // Placeholder for package loading
    return true;
}

bool SampleGenPipeline::encodeAudio(const AudioBuffer& buffer, const std::string& format, 
                                  const std::string& outputPath, int quality) {
    // Placeholder for audio encoding
    return true;
}

bool SampleGenPipeline::decodeAudio(const std::string& inputPath, AudioBuffer& buffer) {
    // Use the existing SampleGen to decode audio
    SampleParams params;
    params.filePath = inputPath;
    
    AudioBundle bundle = m_sampleGen->process(params);
    if (bundle.buffer.empty()) {
        return false;
    }
    
    buffer = std::move(bundle.buffer);
    return true;
}

std::string SampleGenPipeline::computeFileHash(const std::string& filePath) {
    // Placeholder for file hash computation
    return std::to_string(std::hash<std::string>{}(filePath));
}

std::string SampleGenPipeline::computeDefinitionHash(const SamplePackDefinition& definition) {
    // Placeholder for definition hash computation
    return std::to_string(std::hash<std::string>{}(definition.name));
}

void SampleGenPipeline::setupFileWatcher(const std::string& directory) {
    // Placeholder for file watching setup
    // In a real implementation, this would use a library like efsw or libuv
}

void SampleGenPipeline::onFileChanged(const std::string& filePath) {
    // Handle file change events
    // This would trigger reprocessing of affected samples
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
    
    const float threshold = 0.01f;
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

} // namespace Audio
} // namespace MagiTech 
