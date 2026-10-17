#pragma once

#include "AudioAssetTypes.hpp"
#include <cstdint>
#include <map>
#include <vector>
#include <string>
#include <memory>
#include <chrono>

namespace MagiTech {
namespace Audio {

// Forward declarations
struct ExportDefinition;
struct ExportResult;
struct ExportManifest;
struct FormatTarget;
struct PreviewSettings;
struct DistributionDestination;
struct FileEntry;

// AudioMetadata (tag fields embedded on export) is defined in AudioAssetTypes.hpp.

// Format Target Structure
struct FormatTarget {
    AudioFormat format = AudioFormat::WAV;
    int bitDepth = 16;          // 8, 16, 24, 32 (32 / 0 = IEEE float for WAV)
    int sampleRate = 44100;
    bool normalize = false;
    int bitrate = 192;          // For MP3/AAC (kbps)
    int compressionLevel = 5;   // For FLAC/OGG
    bool enableDithering = true;
    bool enableAntiAliasing = true;
    std::map<std::string, std::string> codecOptions;
};

struct PreviewSettings {
    bool enabled = true;
    float duration = 30.0f; // seconds
    float fadeDuration = 2.0f; // seconds
    bool generateThumbnail = true;
    int thumbnailWidth = 800;
    int thumbnailHeight = 200;
};

struct ExportTargets {
    std::vector<FormatTarget> audioFormats;
    PreviewSettings preview;
    bool generateManifest = true;
    bool createPackage = true;
    bool enableDistribution = false;
};

struct DistributionDestination {
    enum class Type {
        FILESYSTEM,
        S3,
        AZURE_BLOB,
        FTP,
        SFTP,
        HTTP,
        CUSTOM
    };

    Type type = Type::FILESYSTEM;
    std::string path;
    std::string bucket; // For S3
    std::string prefix; // For S3/Azure
    std::string endpoint; // For custom endpoints
    std::string accessKey; // For cloud services
    std::string secretKey; // For cloud services
    bool enableRetry = true;
    int maxRetries = 3;
    int retryDelayMs = 1000;
};

struct ArchiveSettings {
    enum class Format {
        ZIP,
        TAR_GZ,
        SEVEN_ZIP,
        RAR,
        CUSTOM
    };

    Format format = Format::ZIP;
    int compressionLevel = 6;
    size_t splitSizeMB = 100;
    bool encrypt = false;
    std::string password;
    bool createInstaller = false;
    std::string installerTemplate;
};

struct ExportDefinition {
    std::string name;
    std::string version;
    std::vector<std::string> sources;
    ExportTargets targets;
    AudioMetadata metadata;
    std::vector<DistributionDestination> destinations;
    ArchiveSettings archive;
    std::string notes;
    std::string changelog;
    std::vector<std::string> tags;
    bool enableHotReload = true;
    bool enableIncrementalBuild = true;
    bool enableParallelProcessing = true;
    int maxConcurrentExports = 4;
};

// Export Result Structures
struct ConvertedFile {
    AudioFormat format = AudioFormat::WAV;
    std::vector<uint8_t> data;
    std::string filename;
    size_t originalSize = 0;
    size_t compressedSize = 0;
    float compressionRatio = 1.0f;
    std::string checksum;
};

// Manifest Structures
struct FileEntry {
    std::string path;
    size_t size = 0;
    std::string checksum;
    std::string format;
    std::chrono::system_clock::time_point modifiedTime;
    std::map<std::string, std::string> metadata;
};

struct ExportManifest {
    std::string version;
    std::chrono::system_clock::time_point date;
    std::string name;
    std::vector<FileEntry> files;
    std::string totalSize;
    std::string totalFiles;
    std::map<std::string, std::string> metadata;
    std::string notes;
    std::string changelog;
    std::vector<std::string> tags;
};

struct ExportResult {
    std::vector<ConvertedFile> convertedFiles;
    std::vector<uint8_t> previewData;
    std::vector<uint8_t> thumbnailData;
    ExportManifest manifest;
    std::vector<uint8_t> packageData;
    std::vector<float> audioData; // Exported (processed) PCM, interleaved
    std::chrono::system_clock::time_point exportTime;
    std::string exportPath;
    bool success = true;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

// ExportGen Class
class ExportGen {
public:
    ExportGen();
    ~ExportGen();

    // Main processing function
    AudioBundle process(const ExportParams& params);

    // Export definition management (JSON)
    ExportDefinition loadExportDefinition(const std::string& filePath);
    ExportDefinition createDefaultExportDefinition(const ExportParams& params);
    bool saveExportDefinition(const ExportDefinition& def, const std::string& filePath);

    // Export pipeline processing
    ExportResult processExportPipeline(const ExportDefinition& exportDef, const ExportParams& params);

    // Source audio loading (decoded to the export's working rate / channel count)
    std::vector<float> loadSourceAudio(const std::vector<std::string>& sources);

    // Format conversion. MP3 and OGG need encoder libraries that are not vendored and
    // throw std::runtime_error; the pipeline reports them as warnings.
    std::vector<uint8_t> convertToFormat(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params);
    std::vector<uint8_t> convertToWAV(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params);
    std::vector<uint8_t> convertToMP3(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params);
    std::vector<uint8_t> convertToFLAC(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params);
    std::vector<uint8_t> convertToOGG(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params);

    // Audio processing
    void normalizeAudio(std::vector<float>& audio);
    void applyDithering(std::vector<float>& audio);
    void applyFadeInOut(std::vector<float>& audio, float fadeDuration);

    // Metadata embedding
    void embedMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata, AudioFormat format);
    void embedWAVMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata);
    void embedMP3Metadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata);
    void embedFLACMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata);
    void embedOGGMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata);

    // Preview generation (WAV preview + PNG waveform thumbnail)
    std::vector<uint8_t> generatePreview(const std::vector<float>& audio, const PreviewSettings& settings);
    std::vector<uint8_t> generateWaveformThumbnail(const std::vector<float>& audio);
    std::vector<uint8_t> generateWaveformThumbnail(const std::vector<float>& audio, int width, int height);

    // Manifest generation
    ExportManifest generateManifest(const ExportDefinition& exportDef, const ExportResult& result);

    // Package creation (ZIP archive of all exported files plus manifest.json)
    std::vector<uint8_t> createPackage(const ExportDefinition& exportDef, const ExportResult& result);

    // Distribution
    void distributePackage(const ExportDefinition& exportDef, const ExportResult& result);
    void uploadToDestination(const DistributionDestination& destination, const ExportResult& result);
    void uploadToFilesystem(const DistributionDestination& destination, const ExportResult& result);
    void uploadToS3(const DistributionDestination& destination, const ExportResult& result);
    void uploadToAzureBlob(const DistributionDestination& destination, const ExportResult& result);
    void uploadToFTP(const DistributionDestination& destination, const ExportResult& result);

    // Utility functions
    std::string calculateSHA256(const std::vector<uint8_t>& data);
    std::string getFormatString(AudioFormat format);
    std::string getFormatExtension(AudioFormat format);

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

    // Utility functions
    float clamp(float value, float min, float max);

    // WAV header writing functions
    void writeString(std::vector<uint8_t>& data, size_t& offset, const std::string& str);
    void writeUint16LE(std::vector<uint8_t>& data, size_t& offset, uint16_t value);
    void writeUint32LE(std::vector<uint8_t>& data, size_t& offset, uint32_t value);
    void writeInt16LE(std::vector<uint8_t>& data, size_t& offset, int16_t value);
    void writeInt24LE(std::vector<uint8_t>& data, size_t& offset, int32_t value);
    void writeInt32LE(std::vector<uint8_t>& data, size_t& offset, int32_t value);
    void writeFloat32LE(std::vector<uint8_t>& data, size_t& offset, float value);

    // Enhanced audio data conversion and writing
    void convertAndWriteAudioData(std::vector<uint8_t>& wavData, size_t& offset,
                                 const std::vector<float>& audioData, const FormatTarget& target, const ExportParams& params);

    // Sample processing
    float normalizeSample(float sample);
    float applyDithering(float sample);

    // Reference test signal (used when no source audio can be loaded)
    std::vector<float> generateTestAudio();

    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);

private:
    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    int m_maxProcessingThreads;
    std::string m_lastError;

    // Export settings (working format of the pipeline)
    uint32_t m_sampleRate;
    uint32_t m_bitDepth;
    uint32_t m_numChannels;
    int m_compressionLevel;
    bool m_enableDithering;
    bool m_enableNormalization;

    // Distribution settings
    bool m_enableRetryLogic;
    int m_maxRetryAttempts;
    int m_retryDelayMs;

    // Warnings collected while running the pipeline
    std::vector<std::string> m_warnings;

    // Constants
    static constexpr float PI = 3.14159265359f;
    static constexpr float TWO_PI = 2.0f * PI;
};

} // namespace Audio
} // namespace MagiTech
