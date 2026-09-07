#include "ExportGen.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <cstring>
#include <filesystem>
#include <chrono>
#include <iomanip>
#include <random>

namespace MagiTech {
namespace Audio {

// Constants
constexpr uint32_t WAV_HEADER_SIZE = 44;
constexpr uint32_t WAV_FORMAT_PCM = 1;
constexpr uint32_t WAV_FORMAT_IEEE_FLOAT = 3;
constexpr size_t PREVIEW_DURATION_SECONDS = 30;
constexpr size_t FADE_DURATION_SECONDS = 2;

// ExportGen Implementation
ExportGen::ExportGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_oversamplingFactor(2)
    , m_antiAliasingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize with default settings
    m_sampleRate = 44100;
    m_bitDepth = 16;
    m_numChannels = 2;
    m_compressionLevel = 5;
    m_enableDithering = true;
    m_enableNormalization = false;
    
    // Initialize distribution settings
    m_enableRetryLogic = true;
    m_maxRetryAttempts = 3;
    m_retryDelayMs = 1000;
}

ExportGen::~ExportGen() = default;

AudioBundle ExportGen::process(const ExportParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "export_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        
        // Load export definition if provided
        ExportDefinition exportDef;
        if (!params.exportDefinitionPath.empty()) {
            exportDef = loadExportDefinition(params.exportDefinitionPath);
        } else {
            exportDef = createDefaultExportDefinition(params);
        }
        
        // Process export pipeline
        ExportResult result = processExportPipeline(exportDef, params);
        
        // Set the exported data
        bundle.buffer = result.audioData;
        bundle.meta.duration = static_cast<float>(result.audioData.size()) / (params.exportSampleRate * params.exportChannels);
        
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

// Export Definition Loading
ExportDefinition ExportGen::loadExportDefinition(const std::string& filePath) {
    ExportDefinition def;
    
    // TODO: Implement YAML/JSON parsing for export definitions
    // For now, create a basic definition
    def.name = "default_export";
    def.version = "1.0.0";
    def.sources.push_back("samplepack/default.samplepack");
    def.targets.audioFormats.push_back({AudioFormat::WAV, {24, 48000, true}});
    def.targets.audioFormats.push_back({AudioFormat::MP3, {192, 0, true}});
    def.targets.audioFormats.push_back({AudioFormat::FLAC, {0, 0, false}});
    def.metadata.artist = "MagiTech";
    def.metadata.album = "Audio Export";
    def.metadata.genre = "Electronic";
    def.metadata.year = 2025;
    
    return def;
}

ExportDefinition ExportGen::createDefaultExportDefinition(const ExportParams& params) {
    ExportDefinition def;
    def.name = "default_export";
    def.version = "1.0.0";
    def.sources.push_back("default_source");
    
    // Add target formats based on params
    if (params.audioFormat == AudioFormat::WAV) {
        def.targets.audioFormats.push_back({AudioFormat::WAV, {params.exportBitDepth, params.exportSampleRate, params.enableNormalization}});
    } else if (params.audioFormat == AudioFormat::MP3) {
        def.targets.audioFormats.push_back({AudioFormat::MP3, {192, 0, params.enableNormalization}});
    } else if (params.audioFormat == AudioFormat::FLAC) {
        def.targets.audioFormats.push_back({AudioFormat::FLAC, {0, 0, false}});
    }
    
    return def;
}

// Export Pipeline Processing
ExportResult ExportGen::processExportPipeline(const ExportDefinition& exportDef, const ExportParams& params) {
    ExportResult result;
    
    // Step 1: Load source audio
    std::vector<float> sourceAudio = loadSourceAudio(exportDef.sources);
    
    // Step 2: Format conversion
    for (const auto& formatTarget : exportDef.targets.audioFormats) {
        std::vector<uint8_t> convertedData = convertToFormat(sourceAudio, formatTarget, params);
        result.convertedFiles.push_back({formatTarget.format, convertedData});
    }
    
    // Step 3: Metadata embedding
    for (auto& convertedFile : result.convertedFiles) {
        embedMetadata(convertedFile.data, exportDef.metadata, convertedFile.format);
    }
    
    // Step 4: Preview generation
    if (exportDef.targets.preview.enabled) {
        result.previewData = generatePreview(sourceAudio, exportDef.targets.preview);
    }
    
    // Step 5: Waveform thumbnail generation
    if (exportDef.targets.preview.generateThumbnail) {
        result.thumbnailData = generateWaveformThumbnail(sourceAudio);
    }
    
    // Step 6: Versioning and manifest
    result.manifest = generateManifest(exportDef, result);
    
    // Step 7: Packaging
    result.packageData = createPackage(exportDef, result);
    
    // Step 8: Distribution
    distributePackage(exportDef, result);
    
    // Use the first converted file as the main result
    if (!result.convertedFiles.empty()) {
        result.audioData.resize(result.convertedFiles[0].data.size() / sizeof(float));
        std::memcpy(result.audioData.data(), result.convertedFiles[0].data.data(), result.convertedFiles[0].data.size());
    }
    
    return result;
}

// Source Audio Loading
std::vector<float> ExportGen::loadSourceAudio(const std::vector<std::string>& sources) {
    // TODO: Implement actual source pack loading
    // For now, generate test audio
    return generateTestAudio();
}

// Format Conversion
std::vector<uint8_t> ExportGen::convertToFormat(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    std::vector<uint8_t> convertedData;
    
    switch (target.format) {
        case AudioFormat::WAV:
            convertedData = convertToWAV(audio, target, params);
            break;
        case AudioFormat::MP3:
            convertedData = convertToMP3(audio, target, params);
            break;
        case AudioFormat::FLAC:
            convertedData = convertToFLAC(audio, target, params);
            break;
        case AudioFormat::OGG:
            convertedData = convertToOGG(audio, target, params);
            break;
    }
    
    return convertedData;
}

// WAV Conversion (Enhanced)
std::vector<uint8_t> ExportGen::convertToWAV(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    std::vector<uint8_t> wavData;
    
    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }
    
    // Apply dithering if enabled
    if (params.enableDithering) {
        applyDithering(processedAudio);
    }
    
    // Calculate sizes
    uint32_t numSamples = static_cast<uint32_t>(processedAudio.size());
    uint32_t bytesPerSample = target.bitDepth / 8;
    uint32_t dataSize = numSamples * bytesPerSample;
    uint32_t fileSize = WAV_HEADER_SIZE + dataSize - 8;
    
    // Reserve space for header + data
    wavData.resize(WAV_HEADER_SIZE + dataSize);
    
    // Write WAV header
    size_t offset = 0;
    
    // RIFF header
    writeString(wavData, offset, "RIFF");
    writeUint32LE(wavData, offset, fileSize);
    writeString(wavData, offset, "WAVE");
    
    // Format chunk
    writeString(wavData, offset, "fmt ");
    writeUint32LE(wavData, offset, 16);
    writeUint16LE(wavData, offset, target.bitDepth == 32 ? WAV_FORMAT_IEEE_FLOAT : WAV_FORMAT_PCM);
    writeUint16LE(wavData, offset, static_cast<uint16_t>(params.exportChannels));
    writeUint32LE(wavData, offset, target.sampleRate);
    writeUint32LE(wavData, offset, target.sampleRate * params.exportChannels * bytesPerSample);
    writeUint16LE(wavData, offset, static_cast<uint16_t>(params.exportChannels * bytesPerSample));
    writeUint16LE(wavData, offset, static_cast<uint16_t>(target.bitDepth));
    
    // Data chunk
    writeString(wavData, offset, "data");
    writeUint32LE(wavData, offset, dataSize);
    
    // Convert and write audio data
    convertAndWriteAudioData(wavData, offset, processedAudio, target, params);
    
    return wavData;
}

// MP3 Conversion (Enhanced)
std::vector<uint8_t> ExportGen::convertToMP3(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    // TODO: Implement proper MP3 encoding with libmp3lame
    // For now, create a placeholder MP3 structure
    std::vector<uint8_t> mp3Data;
    
    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }
    
    // Create basic MP3 container structure
    mp3Data.resize(1024); // Placeholder size
    
    // Add MP3 header
    std::string mp3Header = "ID3";
    std::memcpy(mp3Data.data(), mp3Header.c_str(), mp3Header.length());
    
    // TODO: Implement actual MP3 encoding
    // This would use libmp3lame or similar library
    
    return mp3Data;
}

// FLAC Conversion (Enhanced)
std::vector<uint8_t> ExportGen::convertToFLAC(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    // TODO: Implement proper FLAC encoding with libFLAC
    // For now, create a placeholder FLAC structure
    std::vector<uint8_t> flacData;
    
    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }
    
    // Create basic FLAC container structure
    flacData.resize(1024); // Placeholder size
    
    // Add FLAC header
    std::string flacHeader = "fLaC";
    std::memcpy(flacData.data(), flacHeader.c_str(), flacHeader.length());
    
    // TODO: Implement actual FLAC encoding
    // This would use libFLAC
    
    return flacData;
}

// OGG Conversion (Enhanced)
std::vector<uint8_t> ExportGen::convertToOGG(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    // TODO: Implement proper OGG encoding with libogg/libvorbis
    // For now, create a placeholder OGG structure
    std::vector<uint8_t> oggData;
    
    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }
    
    // Create basic OGG container structure
    oggData.resize(1024); // Placeholder size
    
    // Add OGG header
    std::string oggHeader = "OggS";
    std::memcpy(oggData.data(), oggHeader.c_str(), oggHeader.length());
    
    // TODO: Implement actual OGG encoding
    // This would use libogg/libvorbis
    
    return oggData;
}

// Audio Processing Functions
void ExportGen::normalizeAudio(std::vector<float>& audio) {
    if (audio.empty()) return;
    
    // Find peak amplitude
    float peak = 0.0f;
    for (float sample : audio) {
        peak = std::max(peak, std::abs(sample));
    }
    
    // Normalize to -1dB peak
    if (peak > 0.0f) {
        float normalizeGain = 0.89f / peak; // -1dB = 0.89
        for (float& sample : audio) {
            sample *= normalizeGain;
        }
    }
}

void ExportGen::applyDithering(std::vector<float>& audio) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
    
    for (float& sample : audio) {
        float dither = dis(gen) * 0.0001f; // Small dither amount
        sample += dither;
    }
}

// Metadata Embedding
void ExportGen::embedMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata, AudioFormat format) {
    switch (format) {
        case AudioFormat::WAV:
            embedWAVMetadata(audioData, metadata);
            break;
        case AudioFormat::MP3:
            embedMP3Metadata(audioData, metadata);
            break;
        case AudioFormat::FLAC:
            embedFLACMetadata(audioData, metadata);
            break;
        case AudioFormat::OGG:
            embedOGGMetadata(audioData, metadata);
            break;
    }
}

void ExportGen::embedWAVMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    // TODO: Implement WAV metadata embedding
    // This would add RIFF INFO chunks or broadcast WAV chunks
}

void ExportGen::embedMP3Metadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    // TODO: Implement MP3 metadata embedding
    // This would add ID3v2.4 frames
}

void ExportGen::embedFLACMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    // TODO: Implement FLAC metadata embedding
    // This would add VORBIS_COMMENT blocks
}

void ExportGen::embedOGGMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    // TODO: Implement OGG metadata embedding
    // This would add Vorbis comments
}

// Preview Generation
std::vector<uint8_t> ExportGen::generatePreview(const std::vector<float>& audio, const PreviewSettings& settings) {
    std::vector<float> previewAudio = audio;
    
    // Trim to preview duration
    size_t previewSamples = settings.duration * 44100; // Assume 44.1kHz
    if (previewAudio.size() > previewSamples) {
        previewAudio.resize(previewSamples);
    }
    
    // Apply fade in/out
    applyFadeInOut(previewAudio, settings.fadeDuration);
    
    // Convert to target format (OGG for preview)
    FormatTarget target;
    target.format = AudioFormat::OGG;
    target.bitDepth = 16;
    target.sampleRate = 44100;
    target.normalize = true;
    
    ExportParams params;
    params.exportBitDepth = 16;
    params.exportSampleRate = 44100;
    params.exportChannels = 2;
    params.enableDithering = true;
    params.enableNormalization = true;
    
    return convertToOGG(previewAudio, target, params);
}

void ExportGen::applyFadeInOut(std::vector<float>& audio, float fadeDuration) {
    size_t fadeSamples = static_cast<size_t>(fadeDuration * 44100);
    
    // Fade in
    for (size_t i = 0; i < std::min(fadeSamples, audio.size()); ++i) {
        float fadeFactor = static_cast<float>(i) / fadeSamples;
        audio[i] *= fadeFactor;
    }
    
    // Fade out
    for (size_t i = 0; i < std::min(fadeSamples, audio.size()); ++i) {
        float fadeFactor = static_cast<float>(i) / fadeSamples;
        size_t index = audio.size() - fadeSamples + i;
        if (index < audio.size()) {
            audio[index] *= fadeFactor;
        }
    }
}

// Waveform Thumbnail Generation
std::vector<uint8_t> ExportGen::generateWaveformThumbnail(const std::vector<float>& audio) {
    // TODO: Implement waveform thumbnail generation
    // This would create a PNG image showing the waveform
    
    // For now, create a placeholder PNG structure
    std::vector<uint8_t> thumbnailData;
    thumbnailData.resize(1024); // Placeholder size
    
    // Add PNG header
    std::string pngHeader = "\x89PNG\r\n\x1a\n";
    std::memcpy(thumbnailData.data(), pngHeader.c_str(), pngHeader.length());
    
    return thumbnailData;
}

// Manifest Generation
ExportManifest ExportGen::generateManifest(const ExportDefinition& exportDef, const ExportResult& result) {
    ExportManifest manifest;
    manifest.version = exportDef.version;
    manifest.date = std::chrono::system_clock::now();
    manifest.name = exportDef.name;
    
    // Add file entries
    for (const auto& convertedFile : result.convertedFiles) {
        FileEntry entry;
        entry.path = "audio/" + exportDef.name + "_" + getFormatString(convertedFile.format) + "." + getFormatExtension(convertedFile.format);
        entry.size = convertedFile.data.size();
        entry.checksum = calculateSHA256(convertedFile.data);
        manifest.files.push_back(entry);
    }
    
    // Add preview file
    if (!result.previewData.empty()) {
        FileEntry entry;
        entry.path = "preview/" + exportDef.name + "_preview.ogg";
        entry.size = result.previewData.size();
        entry.checksum = calculateSHA256(result.previewData);
        manifest.files.push_back(entry);
    }
    
    // Add thumbnail file
    if (!result.thumbnailData.empty()) {
        FileEntry entry;
        entry.path = "thumbs/" + exportDef.name + "_waveform.png";
        entry.size = result.thumbnailData.size();
        entry.checksum = calculateSHA256(result.thumbnailData);
        manifest.files.push_back(entry);
    }
    
    return manifest;
}

// Package Creation
std::vector<uint8_t> ExportGen::createPackage(const ExportDefinition& exportDef, const ExportResult& result) {
    // TODO: Implement actual package creation (ZIP, TAR.GZ, etc.)
    // For now, create a placeholder package
    
    std::vector<uint8_t> packageData;
    packageData.resize(2048); // Placeholder size
    
    // Add package header
    std::string packageHeader = "MAGITECH_PACKAGE";
    std::memcpy(packageData.data(), packageHeader.c_str(), packageHeader.length());
    
    return packageData;
}

// Distribution
void ExportGen::distributePackage(const ExportDefinition& exportDef, const ExportResult& result) {
    for (const auto& destination : exportDef.destinations) {
        try {
            uploadToDestination(destination, result);
        } catch (const std::exception& e) {
            // Log error and continue with other destinations
            m_lastError = "Distribution error: " + std::string(e.what());
        }
    }
}

void ExportGen::uploadToDestination(const DistributionDestination& destination, const ExportResult& result) {
    // TODO: Implement actual upload logic
    // This would handle filesystem, S3, Azure Blob, FTP, etc.
    
    switch (destination.type) {
        case DestinationType::FILESYSTEM:
            uploadToFilesystem(destination, result);
            break;
        case DestinationType::S3:
            uploadToS3(destination, result);
            break;
        case DestinationType::AZURE_BLOB:
            uploadToAzureBlob(destination, result);
            break;
        case DestinationType::FTP:
            uploadToFTP(destination, result);
            break;
    }
}

void ExportGen::uploadToFilesystem(const DistributionDestination& destination, const ExportResult& result) {
    // TODO: Implement filesystem upload
}

void ExportGen::uploadToS3(const DistributionDestination& destination, const ExportResult& result) {
    // TODO: Implement S3 upload
}

void ExportGen::uploadToAzureBlob(const DistributionDestination& destination, const ExportResult& result) {
    // TODO: Implement Azure Blob upload
}

void ExportGen::uploadToFTP(const DistributionDestination& destination, const ExportResult& result) {
    // TODO: Implement FTP upload
}

// Utility Functions
std::string ExportGen::calculateSHA256(const std::vector<uint8_t>& data) {
    // TODO: Implement actual SHA-256 calculation
    // For now, return a placeholder hash
    return "placeholder_sha256_hash";
}

std::string ExportGen::getFormatString(AudioFormat format) {
    switch (format) {
        case AudioFormat::WAV: return "WAV";
        case AudioFormat::OGG: return "OGG";
        case AudioFormat::FLAC: return "FLAC";
        case AudioFormat::MP3: return "MP3";
        default: return "UNKNOWN";
    }
}

std::string ExportGen::getFormatExtension(AudioFormat format) {
    switch (format) {
        case AudioFormat::WAV: return "wav";
        case AudioFormat::OGG: return "ogg";
        case AudioFormat::FLAC: return "flac";
        case AudioFormat::MP3: return "mp3";
        default: return "bin";
    }
}

// Enhanced Audio Data Conversion and Writing
void ExportGen::convertAndWriteAudioData(std::vector<uint8_t>& wavData, size_t& offset,
                                        const std::vector<float>& audioData, const FormatTarget& target, const ExportParams& params) {
    size_t dataOffset = offset;
    
    for (size_t i = 0; i < audioData.size(); ++i) {
        float sample = audioData[i];
        
        // Apply normalization if enabled
        if (target.normalize) {
            sample = normalizeSample(sample);
        }
        
        // Apply dithering if enabled
        if (params.enableDithering) {
            sample = applyDithering(sample);
        }
        
        // Convert to target bit depth
        switch (target.bitDepth) {
            case 16:
                writeInt16LE(wavData, dataOffset, static_cast<int16_t>(sample * 32767.0f));
                break;
            case 24:
                writeInt24LE(wavData, dataOffset, static_cast<int32_t>(sample * 8388607.0f));
                break;
            case 32:
                if (target.bitDepth == 32) {
                    writeFloat32LE(wavData, dataOffset, sample);
                } else {
                    writeInt32LE(wavData, dataOffset, static_cast<int32_t>(sample * 2147483647.0f));
                }
                break;
        }
    }
}

// Test Audio Generation
std::vector<float> ExportGen::generateTestAudio() {
    std::vector<float> audioData;
    size_t numSamples = 44100 * 5; // 5 seconds at 44.1kHz
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
float ExportGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float ExportGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float ExportGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float ExportGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void ExportGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void ExportGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = clamp(factor, 1, 8);
}

void ExportGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void ExportGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void ExportGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string ExportGen::getLastError() const {
    return m_lastError;
}

void ExportGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float ExportGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

// WAV Header Writing Functions
void ExportGen::writeString(std::vector<uint8_t>& data, size_t& offset, const std::string& str) {
    std::memcpy(data.data() + offset, str.c_str(), str.length());
    offset += str.length();
}

void ExportGen::writeUint16LE(std::vector<uint8_t>& data, size_t& offset, uint16_t value) {
    data[offset] = static_cast<uint8_t>(value & 0xFF);
    data[offset + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    offset += 2;
}

void ExportGen::writeUint32LE(std::vector<uint8_t>& data, size_t& offset, uint32_t value) {
    data[offset] = static_cast<uint8_t>(value & 0xFF);
    data[offset + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[offset + 2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[offset + 3] = static_cast<uint8_t>((value >> 24) & 0xFF);
    offset += 4;
}

void ExportGen::writeInt16LE(std::vector<uint8_t>& data, size_t& offset, int16_t value) {
    writeUint16LE(data, offset, static_cast<uint16_t>(value));
}

void ExportGen::writeInt24LE(std::vector<uint8_t>& data, size_t& offset, int32_t value) {
    data[offset] = static_cast<uint8_t>(value & 0xFF);
    data[offset + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[offset + 2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    offset += 3;
}

void ExportGen::writeInt32LE(std::vector<uint8_t>& data, size_t& offset, int32_t value) {
    writeUint32LE(data, offset, static_cast<uint32_t>(value));
}

void ExportGen::writeFloat32LE(std::vector<uint8_t>& data, size_t& offset, float value) {
    uint32_t intValue;
    std::memcpy(&intValue, &value, sizeof(float));
    writeUint32LE(data, offset, intValue);
}

// Sample Processing
float ExportGen::normalizeSample(float sample) {
    static float peakValue = 0.0f;
    peakValue = std::max(peakValue, std::abs(sample));
    
    if (peakValue > 0.0f) {
        return sample / peakValue * 0.95f; // Leave some headroom
    }
    return sample;
}

float ExportGen::applyDithering(float sample) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
    
    float dither = dis(gen) * 0.0001f; // Small dither amount
    return sample + dither;
}

} // namespace Audio
} // namespace MagiTech 
