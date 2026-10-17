#include "ExportGen.hpp"
#include "AudioFileIO.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <stb_image_write.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <cstring>
#include <filesystem>
#include <chrono>
#include <iomanip>
#include <random>
#include <thread>

namespace MagiTech {
namespace Audio {

namespace {

// Constants
constexpr uint32_t WAV_HEADER_SIZE = 44;
constexpr uint32_t WAV_FORMAT_PCM = 1;
constexpr uint32_t WAV_FORMAT_IEEE_FLOAT = 3;
constexpr float kPi = 3.14159265359f;
constexpr size_t FLAC_BLOCK_SIZE = 4096;

FormatTarget makeTarget(AudioFormat format, int bitDepth, int sampleRate, bool normalize) {
    FormatTarget target;
    target.format = format;
    target.bitDepth = bitDepth;
    target.sampleRate = sampleRate;
    target.normalize = normalize;
    return target;
}

std::string toLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

AudioFormat formatFromString(const std::string& name) {
    const std::string n = toLower(name);
    if (n == "mp3") return AudioFormat::MP3;
    if (n == "flac") return AudioFormat::FLAC;
    if (n == "ogg" || n == "vorbis") return AudioFormat::OGG;
    return AudioFormat::WAV;
}

DistributionDestination::Type destinationFromString(const std::string& name) {
    const std::string n = toLower(name);
    if (n == "s3") return DistributionDestination::Type::S3;
    if (n == "azure" || n == "azure_blob") return DistributionDestination::Type::AZURE_BLOB;
    if (n == "ftp") return DistributionDestination::Type::FTP;
    if (n == "sftp") return DistributionDestination::Type::SFTP;
    if (n == "http" || n == "https") return DistributionDestination::Type::HTTP;
    if (n == "custom") return DistributionDestination::Type::CUSTOM;
    return DistributionDestination::Type::FILESYSTEM;
}

std::string destinationToString(DistributionDestination::Type type) {
    switch (type) {
        case DistributionDestination::Type::S3: return "s3";
        case DistributionDestination::Type::AZURE_BLOB: return "azure_blob";
        case DistributionDestination::Type::FTP: return "ftp";
        case DistributionDestination::Type::SFTP: return "sftp";
        case DistributionDestination::Type::HTTP: return "http";
        case DistributionDestination::Type::CUSTOM: return "custom";
        default: return "filesystem";
    }
}

// The non-empty tag fields of an AudioMetadata as (key, value) pairs.
std::vector<std::pair<std::string, std::string>> metadataFields(const AudioMetadata& m) {
    std::vector<std::pair<std::string, std::string>> fields = {
        {"TITLE", m.title}, {"ARTIST", m.artist}, {"ALBUM", m.album}, {"GENRE", m.genre},
        {"DATE", m.year > 0 ? std::to_string(m.year) : std::string()}, {"COMMENT", m.comment},
        {"COPYRIGHT", m.copyright}, {"COMPOSER", m.composer}, {"PRODUCER", m.producer},
        {"ENGINEER", m.engineer}, {"PUBLISHER", m.publisher}, {"ISRC", m.isrc}, {"UPC", m.upc},
        {"CATALOG", m.catalog}, {"BPM", m.bpm}, {"KEY", m.key}, {"MOOD", m.mood}, {"TAGS", m.tags}};
    fields.erase(std::remove_if(fields.begin(), fields.end(), [](const auto& f) { return f.second.empty(); }), fields.end());
    return fields;
}

void readMetadataJson(const nlohmann::json& j, AudioMetadata& m) {
    if (!j.is_object()) return;
    auto str = [&j](const char* key, std::string& out) {
        if (j.contains(key) && j[key].is_string()) out = j[key].get<std::string>();
    };
    str("artist", m.artist); str("album", m.album); str("genre", m.genre); str("title", m.title);
    str("comment", m.comment); str("copyright", m.copyright); str("composer", m.composer);
    str("producer", m.producer); str("engineer", m.engineer); str("publisher", m.publisher);
    str("isrc", m.isrc); str("upc", m.upc); str("catalog", m.catalog); str("bpm", m.bpm);
    str("key", m.key); str("mood", m.mood); str("tags", m.tags);
    if (j.contains("year") && j["year"].is_number_integer()) m.year = j["year"].get<int>();
}

nlohmann::json metadataToJson(const AudioMetadata& m) {
    nlohmann::json j;
    j["artist"] = m.artist; j["album"] = m.album; j["genre"] = m.genre; j["year"] = m.year;
    j["title"] = m.title; j["comment"] = m.comment; j["copyright"] = m.copyright;
    j["composer"] = m.composer; j["producer"] = m.producer; j["engineer"] = m.engineer;
    j["publisher"] = m.publisher; j["isrc"] = m.isrc; j["upc"] = m.upc; j["catalog"] = m.catalog;
    j["bpm"] = m.bpm; j["key"] = m.key; j["mood"] = m.mood; j["tags"] = m.tags;
    return j;
}

nlohmann::json manifestToJson(const ExportManifest& manifest) {
    nlohmann::json j;
    j["name"] = manifest.name;
    j["version"] = manifest.version;
    j["date"] = std::chrono::duration_cast<std::chrono::seconds>(manifest.date.time_since_epoch()).count();
    j["totalSize"] = manifest.totalSize;
    j["totalFiles"] = manifest.totalFiles;
    j["metadata"] = manifest.metadata;
    j["notes"] = manifest.notes;
    j["changelog"] = manifest.changelog;
    j["tags"] = manifest.tags;
    j["files"] = nlohmann::json::array();
    for (const auto& f : manifest.files) {
        j["files"].push_back({{"path", f.path}, {"size", f.size}, {"sha256", f.checksum},
                              {"format", f.format}, {"metadata", f.metadata}});
    }
    return j;
}

// CRC-8 (poly 0x07) and CRC-16 (poly 0x8005) as required by FLAC frames.
uint8_t flacCrc8(const uint8_t* data, size_t size) {
    uint8_t crc = 0;
    for (size_t i = 0; i < size; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x07) : static_cast<uint8_t>(crc << 1);
    }
    return crc;
}

uint16_t flacCrc16(const uint8_t* data, size_t size) {
    uint16_t crc = 0;
    for (size_t i = 0; i < size; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (int b = 0; b < 8; ++b) crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x8005) : static_cast<uint16_t>(crc << 1);
    }
    return crc;
}

// FLAC "UTF-8" coding of the frame number.
void putFlacUtf8(std::vector<uint8_t>& out, uint32_t value) {
    if (value < 0x80) {
        out.push_back(static_cast<uint8_t>(value));
        return;
    }
    int bytes = value < 0x800 ? 2 : value < 0x10000 ? 3 : value < 0x200000 ? 4 : value < 0x4000000 ? 5 : 6;
    const uint8_t prefix = static_cast<uint8_t>(0xFF00 >> bytes);
    out.push_back(static_cast<uint8_t>(prefix | (value >> (6 * (bytes - 1)))));
    for (int i = bytes - 2; i >= 0; --i) out.push_back(static_cast<uint8_t>(0x80 | ((value >> (6 * i)) & 0x3F)));
}

void putBE(std::vector<uint8_t>& out, uint64_t value, int bytes) {
    for (int i = bytes - 1; i >= 0; --i) out.push_back(static_cast<uint8_t>((value >> (8 * i)) & 0xFF));
}

void putLE32(std::vector<uint8_t>& out, uint32_t v) {
    for (int i = 0; i < 4; ++i) out.push_back(static_cast<uint8_t>((v >> (8 * i)) & 0xFF));
}

} // namespace

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

        // Working format of this export
        m_sampleRate = static_cast<uint32_t>(params.exportSampleRate);
        m_numChannels = std::max<uint32_t>(1, static_cast<uint32_t>(params.exportChannels));
        m_bitDepth = params.exportBitDepth == BitDepth::BD_FLOAT ? 32u : static_cast<uint32_t>(params.exportBitDepth);
        m_compressionLevel = params.compressionLevel;
        m_enableDithering = params.enableDithering;
        m_enableNormalization = params.enableNormalization;

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
        bundle.meta.duration = static_cast<float>(result.audioData.size()) / (static_cast<float>(m_sampleRate) * m_numChannels);
        bundle.meta.title = exportDef.metadata.title;
        bundle.meta.artist = exportDef.metadata.artist;
        bundle.meta.album = exportDef.metadata.album;
        bundle.meta.genre = exportDef.metadata.genre;
        bundle.meta.year = exportDef.metadata.year;
        bundle.meta.comment = exportDef.metadata.comment;
        bundle.meta.creationTime = result.exportTime;
        bundle.creationTime = result.exportTime;

        // Calculate quality metrics
        bundle.quality.peakAmplitude = calculatePeakAmplitude(result.audioData);
        bundle.quality.rmsAmplitude = calculateRMSAmplitude(result.audioData);
        bundle.quality.dynamicRange = calculateDynamicRange(result.audioData);
        bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(result.audioData);
        bundle.meta.quality = bundle.quality;

        return bundle;

    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Export Definition Loading (JSON)
ExportDefinition ExportGen::loadExportDefinition(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open export definition: " + filePath);
    }
    nlohmann::json j;
    try {
        file >> j;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("Failed to parse export definition " + filePath + ": " + e.what());
    }

    ExportDefinition def;
    def.name = j.value("name", std::string("export"));
    def.version = j.value("version", std::string("1.0.0"));
    def.notes = j.value("notes", std::string());
    def.changelog = j.value("changelog", std::string());
    if (j.contains("tags") && j["tags"].is_array()) {
        for (const auto& t : j["tags"]) if (t.is_string()) def.tags.push_back(t.get<std::string>());
    }
    def.enableHotReload = j.value("enableHotReload", true);
    def.enableIncrementalBuild = j.value("enableIncrementalBuild", true);
    def.enableParallelProcessing = j.value("enableParallelProcessing", true);
    def.maxConcurrentExports = j.value("maxConcurrentExports", 4);

    const std::filesystem::path baseDir = std::filesystem::path(filePath).parent_path();
    if (j.contains("sources") && j["sources"].is_array()) {
        for (const auto& s : j["sources"]) {
            if (!s.is_string()) continue;
            std::filesystem::path p = s.get<std::string>();
            if (p.is_relative() && !baseDir.empty()) p = baseDir / p;
            def.sources.push_back(p.string());
        }
    }

    if (j.contains("targets") && j["targets"].is_object()) {
        const auto& t = j["targets"];
        if (t.contains("formats") && t["formats"].is_array()) {
            for (const auto& f : t["formats"]) {
                FormatTarget target;
                target.format = formatFromString(f.value("format", std::string("wav")));
                target.bitDepth = f.value("bitDepth", 16);
                target.sampleRate = f.value("sampleRate", static_cast<int>(m_sampleRate));
                target.normalize = f.value("normalize", false);
                target.bitrate = f.value("bitrate", 192);
                target.compressionLevel = f.value("compressionLevel", 5);
                target.enableDithering = f.value("dithering", true);
                target.enableAntiAliasing = f.value("antiAliasing", true);
                if (f.contains("codecOptions") && f["codecOptions"].is_object()) {
                    for (auto it = f["codecOptions"].begin(); it != f["codecOptions"].end(); ++it) {
                        if (it.value().is_string()) target.codecOptions[it.key()] = it.value().get<std::string>();
                    }
                }
                def.targets.audioFormats.push_back(target);
            }
        }
        if (t.contains("preview") && t["preview"].is_object()) {
            const auto& p = t["preview"];
            def.targets.preview.enabled = p.value("enabled", true);
            def.targets.preview.duration = p.value("duration", 30.0f);
            def.targets.preview.fadeDuration = p.value("fadeDuration", 2.0f);
            def.targets.preview.generateThumbnail = p.value("thumbnail", true);
            def.targets.preview.thumbnailWidth = p.value("thumbnailWidth", 800);
            def.targets.preview.thumbnailHeight = p.value("thumbnailHeight", 200);
        }
        def.targets.generateManifest = t.value("generateManifest", true);
        def.targets.createPackage = t.value("createPackage", true);
        def.targets.enableDistribution = t.value("enableDistribution", false);
    }
    if (def.targets.audioFormats.empty()) {
        def.targets.audioFormats.push_back(makeTarget(AudioFormat::WAV, 16, static_cast<int>(m_sampleRate), false));
    }

    readMetadataJson(j.value("metadata", nlohmann::json::object()), def.metadata);

    if (j.contains("destinations") && j["destinations"].is_array()) {
        for (const auto& d : j["destinations"]) {
            DistributionDestination dest;
            dest.type = destinationFromString(d.value("type", std::string("filesystem")));
            dest.path = d.value("path", std::string());
            dest.bucket = d.value("bucket", std::string());
            dest.prefix = d.value("prefix", std::string());
            dest.endpoint = d.value("endpoint", std::string());
            dest.enableRetry = d.value("retry", true);
            dest.maxRetries = d.value("maxRetries", 3);
            dest.retryDelayMs = d.value("retryDelayMs", 1000);
            def.destinations.push_back(dest);
        }
    }

    if (j.contains("archive") && j["archive"].is_object()) {
        const auto& a = j["archive"];
        const std::string fmt = toLower(a.value("format", std::string("zip")));
        def.archive.format = fmt == "tar.gz" || fmt == "tar_gz" ? ArchiveSettings::Format::TAR_GZ
                           : fmt == "7z" ? ArchiveSettings::Format::SEVEN_ZIP
                           : fmt == "rar" ? ArchiveSettings::Format::RAR
                           : ArchiveSettings::Format::ZIP;
        def.archive.compressionLevel = a.value("compressionLevel", 6);
        def.archive.splitSizeMB = a.value("splitSizeMB", static_cast<size_t>(100));
    }

    return def;
}

bool ExportGen::saveExportDefinition(const ExportDefinition& def, const std::string& filePath) {
    try {
        nlohmann::json j;
        j["name"] = def.name;
        j["version"] = def.version;
        j["sources"] = def.sources;
        j["notes"] = def.notes;
        j["changelog"] = def.changelog;
        j["tags"] = def.tags;
        j["metadata"] = metadataToJson(def.metadata);
        nlohmann::json formats = nlohmann::json::array();
        for (const auto& t : def.targets.audioFormats) {
            formats.push_back({{"format", getFormatExtension(t.format)}, {"bitDepth", t.bitDepth},
                               {"sampleRate", t.sampleRate}, {"normalize", t.normalize}, {"bitrate", t.bitrate},
                               {"compressionLevel", t.compressionLevel}, {"dithering", t.enableDithering},
                               {"antiAliasing", t.enableAntiAliasing}, {"codecOptions", t.codecOptions}});
        }
        const auto& p = def.targets.preview;
        j["targets"] = {{"formats", formats},
                        {"preview", {{"enabled", p.enabled}, {"duration", p.duration}, {"fadeDuration", p.fadeDuration},
                                     {"thumbnail", p.generateThumbnail}, {"thumbnailWidth", p.thumbnailWidth},
                                     {"thumbnailHeight", p.thumbnailHeight}}},
                        {"generateManifest", def.targets.generateManifest},
                        {"createPackage", def.targets.createPackage},
                        {"enableDistribution", def.targets.enableDistribution}};
        nlohmann::json destinations = nlohmann::json::array();
        for (const auto& d : def.destinations) {
            destinations.push_back({{"type", destinationToString(d.type)}, {"path", d.path}, {"bucket", d.bucket},
                                    {"prefix", d.prefix}, {"endpoint", d.endpoint}, {"retry", d.enableRetry},
                                    {"maxRetries", d.maxRetries}, {"retryDelayMs", d.retryDelayMs}});
        }
        j["destinations"] = destinations;
        j["archive"] = {{"format", "zip"}, {"compressionLevel", def.archive.compressionLevel},
                        {"splitSizeMB", def.archive.splitSizeMB}};

        std::ofstream file(filePath);
        if (!file.is_open()) {
            m_lastError = "Could not open file for writing: " + filePath;
            return false;
        }
        file << j.dump(2);
        return static_cast<bool>(file);
    } catch (const std::exception& e) {
        m_lastError = "Failed to save export definition: " + std::string(e.what());
        return false;
    }
}

ExportDefinition ExportGen::createDefaultExportDefinition(const ExportParams& params) {
    ExportDefinition def;
    def.name = "default_export";
    def.version = "1.0.0";

    const int sampleRate = static_cast<int>(params.exportSampleRate);
    const int bitDepth = params.exportBitDepth == BitDepth::BD_FLOAT ? 32 : static_cast<int>(params.exportBitDepth);

    // Add target formats based on params
    FormatTarget target;
    switch (params.audioFormat) {
        case AudioFormat::WAV:
            target = makeTarget(AudioFormat::WAV, bitDepth, sampleRate, params.enableNormalization);
            break;
        case AudioFormat::MP3:
            target = makeTarget(AudioFormat::MP3, 16, sampleRate, params.enableNormalization);
            target.bitrate = 192;
            break;
        case AudioFormat::FLAC:
            target = makeTarget(AudioFormat::FLAC, bitDepth == 24 ? 24 : 16, sampleRate, params.enableNormalization);
            target.compressionLevel = params.compressionLevel;
            break;
        case AudioFormat::OGG:
            target = makeTarget(AudioFormat::OGG, 16, sampleRate, params.enableNormalization);
            break;
    }
    target.enableDithering = params.enableDithering;
    def.targets.audioFormats.push_back(target);

    // ExportParams::metadata is either a JSON object of tag fields or a free-text comment
    if (!params.metadata.empty()) {
        nlohmann::json meta = nlohmann::json::parse(params.metadata, nullptr, false);
        if (!meta.is_discarded() && meta.is_object()) {
            readMetadataJson(meta, def.metadata);
        } else {
            def.metadata.comment = params.metadata;
        }
    }

    return def;
}

// Export Pipeline Processing
ExportResult ExportGen::processExportPipeline(const ExportDefinition& exportDef, const ExportParams& params) {
    ExportResult result;
    m_warnings.clear();

    // Step 1: Source audio (explicit buffer, else the definition's sources)
    std::vector<float> sourceAudio = !params.sourceBuffer.empty() ? params.sourceBuffer : loadSourceAudio(exportDef.sources);
    if (params.enableNormalization) {
        normalizeAudio(sourceAudio);
    }

    // Step 2: Format conversion
    for (const auto& formatTarget : exportDef.targets.audioFormats) {
        try {
            ConvertedFile file;
            file.format = formatTarget.format;
            file.data = convertToFormat(sourceAudio, formatTarget, params);
            file.filename = exportDef.name + "_" + getFormatString(formatTarget.format) + "." + getFormatExtension(formatTarget.format);
            file.originalSize = sourceAudio.size() * sizeof(float);
            file.compressedSize = file.data.size();
            file.compressionRatio = file.compressedSize > 0 ? static_cast<float>(file.originalSize) / file.compressedSize : 0.0f;
            result.convertedFiles.push_back(std::move(file));
        } catch (const std::exception& e) {
            m_warnings.push_back(std::string("Skipped ") + getFormatString(formatTarget.format) + " target: " + e.what());
        }
    }

    // Step 3: Metadata embedding
    for (auto& convertedFile : result.convertedFiles) {
        embedMetadata(convertedFile.data, exportDef.metadata, convertedFile.format);
        convertedFile.compressedSize = convertedFile.data.size();
        convertedFile.checksum = calculateSHA256(convertedFile.data);
    }

    // Step 4: Preview generation
    if (exportDef.targets.preview.enabled) {
        result.previewData = generatePreview(sourceAudio, exportDef.targets.preview);
    }

    // Step 5: Waveform thumbnail generation
    if (exportDef.targets.preview.generateThumbnail) {
        result.thumbnailData = generateWaveformThumbnail(sourceAudio, exportDef.targets.preview.thumbnailWidth,
                                                         exportDef.targets.preview.thumbnailHeight);
    }

    // Step 6: Versioning and manifest
    result.exportTime = std::chrono::system_clock::now();
    if (exportDef.targets.generateManifest) {
        result.manifest = generateManifest(exportDef, result);
    }

    // Step 7: Packaging
    if (exportDef.targets.createPackage) {
        result.packageData = createPackage(exportDef, result);
    }

    // Step 8: Distribution
    if (exportDef.targets.enableDistribution || !exportDef.destinations.empty()) {
        distributePackage(exportDef, result);
    }

    // The exported PCM (after normalisation) is the main result
    result.audioData = std::move(sourceAudio);
    result.warnings = m_warnings;
    result.success = !result.convertedFiles.empty();
    if (!result.success) {
        result.errorMessage = "No export target could be produced";
    }
    result.metadata["name"] = exportDef.name;
    result.metadata["version"] = exportDef.version;
    result.metadata["files"] = std::to_string(result.convertedFiles.size());

    return result;
}

// Source Audio Loading
std::vector<float> ExportGen::loadSourceAudio(const std::vector<std::string>& sources) {
    std::vector<float> combined;
    for (const auto& source : sources) {
        std::vector<float> decoded;
        std::string error;
        if (FileIO::decodeFileAs(source, m_sampleRate, m_numChannels, decoded, error)) {
            combined.insert(combined.end(), decoded.begin(), decoded.end());
        } else {
            m_warnings.push_back("Source not loaded: " + error);
        }
    }
    if (combined.empty()) {
        // Nothing decodable: export the reference signal so the pipeline output stays verifiable.
        m_warnings.push_back("No decodable source audio; exporting reference signal");
        return generateTestAudio();
    }
    return combined;
}

// Format Conversion
std::vector<uint8_t> ExportGen::convertToFormat(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    // Resample from the working rate to the target rate if needed
    const uint32_t targetRate = target.sampleRate > 0 ? static_cast<uint32_t>(target.sampleRate) : m_sampleRate;
    const std::vector<float> resampled = FileIO::resampleLinear(audio, m_numChannels, m_sampleRate, targetRate);

    switch (target.format) {
        case AudioFormat::WAV: return convertToWAV(resampled, target, params);
        case AudioFormat::MP3: return convertToMP3(resampled, target, params);
        case AudioFormat::FLAC: return convertToFLAC(resampled, target, params);
        case AudioFormat::OGG: return convertToOGG(resampled, target, params);
    }
    return {};
}

// WAV Conversion
std::vector<uint8_t> ExportGen::convertToWAV(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    std::vector<uint8_t> wavData;
    const bool isFloat = target.bitDepth == 32 || target.bitDepth == 0;
    const uint16_t bitDepth = static_cast<uint16_t>(isFloat ? 32 : (target.bitDepth == 8 || target.bitDepth == 24 ? target.bitDepth : 16));
    const uint32_t sampleRate = target.sampleRate > 0 ? static_cast<uint32_t>(target.sampleRate) : m_sampleRate;
    const uint16_t channels = static_cast<uint16_t>(m_numChannels);

    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }

    // Apply dithering for integer formats
    if (params.enableDithering && target.enableDithering && !isFloat) {
        applyDithering(processedAudio);
    }

    // Calculate sizes
    uint32_t numSamples = static_cast<uint32_t>(processedAudio.size());
    uint32_t bytesPerSample = bitDepth / 8;
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
    writeUint16LE(wavData, offset, static_cast<uint16_t>(isFloat ? WAV_FORMAT_IEEE_FLOAT : WAV_FORMAT_PCM));
    writeUint16LE(wavData, offset, channels);
    writeUint32LE(wavData, offset, sampleRate);
    writeUint32LE(wavData, offset, sampleRate * channels * bytesPerSample);
    writeUint16LE(wavData, offset, static_cast<uint16_t>(channels * bytesPerSample));
    writeUint16LE(wavData, offset, bitDepth);

    // Data chunk
    writeString(wavData, offset, "data");
    writeUint32LE(wavData, offset, dataSize);

    // Convert and write audio data
    FormatTarget effective = target;
    effective.bitDepth = bitDepth;
    convertAndWriteAudioData(wavData, offset, processedAudio, effective, params);

    return wavData;
}

// MP3 Conversion: requires an MP3 encoder (e.g. LAME), which is not vendored with the backend.
std::vector<uint8_t> ExportGen::convertToMP3(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    throw std::runtime_error("MP3 encoding is unavailable: no MP3 encoder library is vendored (export WAV or FLAC instead)");
}

// FLAC Conversion: valid FLAC stream (STREAMINFO + fixed-blocksize frames with VERBATIM subframes).
std::vector<uint8_t> ExportGen::convertToFLAC(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    const uint32_t channels = std::clamp<uint32_t>(m_numChannels, 1, 8);
    const uint32_t bitsPerSample = target.bitDepth == 24 || target.bitDepth == 32 || target.bitDepth == 0 ? 24 : (target.bitDepth == 8 ? 8 : 16);
    const uint32_t sampleRate = target.sampleRate > 0 ? static_cast<uint32_t>(target.sampleRate) : m_sampleRate;

    // Apply normalization if requested
    std::vector<float> processedAudio = audio;
    if (target.normalize) {
        normalizeAudio(processedAudio);
    }
    if (params.enableDithering && target.enableDithering) {
        applyDithering(processedAudio);
    }

    const uint64_t totalFrames = processedAudio.size() / channels;
    const double scale = static_cast<double>((1u << (bitsPerSample - 1)) - 1);

    std::vector<uint8_t> flacData = {'f', 'L', 'a', 'C'};

    // STREAMINFO (last metadata block)
    const uint32_t blockSize = static_cast<uint32_t>(std::max<uint64_t>(16, std::min<uint64_t>(FLAC_BLOCK_SIZE, std::max<uint64_t>(totalFrames, 16))));
    flacData.push_back(0x80); // last block, type 0
    putBE(flacData, 34, 3);
    putBE(flacData, blockSize, 2);   // min block size
    putBE(flacData, blockSize, 2);   // max block size
    putBE(flacData, 0, 3);           // min frame size (unknown)
    putBE(flacData, 0, 3);           // max frame size (unknown)
    // sample rate (20) | channels-1 (3) | bps-1 (5) | total samples (36)
    const uint64_t packed = (static_cast<uint64_t>(sampleRate & 0xFFFFF) << 44) |
                            (static_cast<uint64_t>(channels - 1) << 41) |
                            (static_cast<uint64_t>(bitsPerSample - 1) << 36) |
                            (totalFrames & 0xFFFFFFFFFULL);
    putBE(flacData, packed, 8);
    for (int i = 0; i < 16; ++i) flacData.push_back(0); // MD5 unknown

    const uint8_t sampleSizeCode = bitsPerSample == 8 ? 0x1 : bitsPerSample == 16 ? 0x4 : 0x6;
    const int bytesPerSample = static_cast<int>(bitsPerSample / 8);

    uint32_t frameNumber = 0;
    for (uint64_t start = 0; start < totalFrames; start += blockSize, ++frameNumber) {
        const uint32_t frames = static_cast<uint32_t>(std::min<uint64_t>(blockSize, totalFrames - start));
        std::vector<uint8_t> frame = {0xFF, 0xF8};
        frame.push_back(static_cast<uint8_t>((0x7 << 4) | 0x0));                         // 16-bit block size follows; rate from STREAMINFO
        frame.push_back(static_cast<uint8_t>(((channels - 1) << 4) | (sampleSizeCode << 1)));
        putFlacUtf8(frame, frameNumber);
        putBE(frame, frames - 1, 2);
        frame.push_back(flacCrc8(frame.data(), frame.size()));

        for (uint32_t c = 0; c < channels; ++c) {
            frame.push_back(0x02); // VERBATIM subframe, no wasted bits
            for (uint32_t f = 0; f < frames; ++f) {
                const float s = std::clamp(processedAudio[(start + f) * channels + c], -1.0f, 1.0f);
                const int32_t v = static_cast<int32_t>(std::lround(s * scale));
                putBE(frame, static_cast<uint32_t>(v), bytesPerSample);
            }
        }
        const uint16_t crc = flacCrc16(frame.data(), frame.size());
        putBE(frame, crc, 2);
        flacData.insert(flacData.end(), frame.begin(), frame.end());
    }

    return flacData;
}

// OGG Conversion: requires a Vorbis encoder (libvorbis), which is not vendored (only the stb_vorbis decoder is).
std::vector<uint8_t> ExportGen::convertToOGG(const std::vector<float>& audio, const FormatTarget& target, const ExportParams& params) {
    throw std::runtime_error("Ogg Vorbis encoding is unavailable: no Vorbis encoder library is vendored (export WAV or FLAC instead)");
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
    for (float& sample : audio) {
        sample = applyDithering(sample);
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

// Appends a RIFF LIST/INFO chunk and fixes up the RIFF size.
void ExportGen::embedWAVMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    if (audioData.size() < 12 || std::memcmp(audioData.data(), "RIFF", 4) != 0) return;
    static const std::map<std::string, std::string> infoIds = {
        {"TITLE", "INAM"}, {"ARTIST", "IART"}, {"ALBUM", "IPRD"}, {"GENRE", "IGNR"}, {"DATE", "ICRD"},
        {"COMMENT", "ICMT"}, {"COPYRIGHT", "ICOP"}, {"COMPOSER", "IMUS"}, {"ENGINEER", "IENG"},
        {"PUBLISHER", "IPUB"}, {"TAGS", "IKEY"}};

    std::vector<uint8_t> info = {'I', 'N', 'F', 'O'};
    for (const auto& [key, value] : metadataFields(metadata)) {
        auto id = infoIds.find(key);
        if (id == infoIds.end()) continue;
        info.insert(info.end(), id->second.begin(), id->second.end());
        putLE32(info, static_cast<uint32_t>(value.size() + 1));
        info.insert(info.end(), value.begin(), value.end());
        info.push_back(0);
        if ((value.size() + 1) & 1u) info.push_back(0); // word alignment
    }
    if (info.size() == 4) return; // nothing to embed

    if (audioData.size() & 1u) audioData.push_back(0);
    const char listTag[4] = {'L', 'I', 'S', 'T'};
    audioData.insert(audioData.end(), listTag, listTag + 4);
    putLE32(audioData, static_cast<uint32_t>(info.size()));
    audioData.insert(audioData.end(), info.begin(), info.end());

    const uint32_t riffSize = static_cast<uint32_t>(audioData.size() - 8);
    for (int i = 0; i < 4; ++i) audioData[4 + i] = static_cast<uint8_t>((riffSize >> (8 * i)) & 0xFF);
}

// Prepends an ID3v2.4 tag (UTF-8 text frames).
void ExportGen::embedMP3Metadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    static const std::map<std::string, std::string> frameIds = {
        {"TITLE", "TIT2"}, {"ARTIST", "TPE1"}, {"ALBUM", "TALB"}, {"GENRE", "TCON"}, {"DATE", "TDRC"},
        {"COPYRIGHT", "TCOP"}, {"COMPOSER", "TCOM"}, {"PUBLISHER", "TPUB"}, {"ISRC", "TSRC"},
        {"BPM", "TBPM"}, {"KEY", "TKEY"}, {"MOOD", "TMOO"}};
    auto syncsafe = [](std::vector<uint8_t>& out, uint32_t v) {
        out.push_back(static_cast<uint8_t>((v >> 21) & 0x7F));
        out.push_back(static_cast<uint8_t>((v >> 14) & 0x7F));
        out.push_back(static_cast<uint8_t>((v >> 7) & 0x7F));
        out.push_back(static_cast<uint8_t>(v & 0x7F));
    };

    std::vector<uint8_t> frames;
    for (const auto& [key, value] : metadataFields(metadata)) {
        std::vector<uint8_t> body;
        std::string id;
        if (key == "COMMENT") {
            id = "COMM";
            body = {0x03, 'e', 'n', 'g', 0x00}; // UTF-8, language, empty description
        } else {
            auto it = frameIds.find(key);
            if (it == frameIds.end()) continue;
            id = it->second;
            body = {0x03}; // UTF-8
        }
        body.insert(body.end(), value.begin(), value.end());
        frames.insert(frames.end(), id.begin(), id.end());
        syncsafe(frames, static_cast<uint32_t>(body.size()));
        frames.push_back(0);
        frames.push_back(0);
        frames.insert(frames.end(), body.begin(), body.end());
    }
    if (frames.empty()) return;

    std::vector<uint8_t> tag = {'I', 'D', '3', 0x04, 0x00, 0x00};
    syncsafe(tag, static_cast<uint32_t>(frames.size()));
    tag.insert(tag.end(), frames.begin(), frames.end());
    audioData.insert(audioData.begin(), tag.begin(), tag.end());
}

// Inserts a VORBIS_COMMENT metadata block after STREAMINFO.
void ExportGen::embedFLACMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    if (audioData.size() < 42 || std::memcmp(audioData.data(), "fLaC", 4) != 0) return;
    const auto fields = metadataFields(metadata);
    if (fields.empty()) return;

    std::vector<uint8_t> body;
    const std::string vendor = "MagiTech ExportGen";
    putLE32(body, static_cast<uint32_t>(vendor.size()));
    body.insert(body.end(), vendor.begin(), vendor.end());
    putLE32(body, static_cast<uint32_t>(fields.size()));
    for (const auto& [key, value] : fields) {
        const std::string comment = key + "=" + value;
        putLE32(body, static_cast<uint32_t>(comment.size()));
        body.insert(body.end(), comment.begin(), comment.end());
    }

    const bool streamInfoWasLast = (audioData[4] & 0x80) != 0;
    audioData[4] &= 0x7F; // STREAMINFO is no longer the last block
    std::vector<uint8_t> block;
    block.push_back(static_cast<uint8_t>((streamInfoWasLast ? 0x80 : 0x00) | 4));
    putBE(block, body.size(), 3);
    block.insert(block.end(), body.begin(), body.end());
    audioData.insert(audioData.begin() + 42, block.begin(), block.end());
}

// Ogg streams are never produced by this exporter (no Vorbis encoder); rewriting the comment
// header of a foreign Ogg stream would require re-paginating it, which is not supported.
void ExportGen::embedOGGMetadata(std::vector<uint8_t>& audioData, const AudioMetadata& metadata) {
    if (!audioData.empty() && !metadataFields(metadata).empty()) {
        m_warnings.push_back("Metadata was not embedded into the Ogg stream (re-pagination not supported)");
    }
}

// Preview Generation: faded excerpt encoded as 16-bit WAV
std::vector<uint8_t> ExportGen::generatePreview(const std::vector<float>& audio, const PreviewSettings& settings) {
    std::vector<float> previewAudio = audio;

    // Trim to preview duration
    size_t previewSamples = static_cast<size_t>(settings.duration * m_sampleRate) * m_numChannels;
    if (previewAudio.size() > previewSamples) {
        previewAudio.resize(previewSamples);
    }

    // Apply fade in/out
    applyFadeInOut(previewAudio, settings.fadeDuration);
    normalizeAudio(previewAudio);

    return FileIO::encodeWav(previewAudio, m_sampleRate, static_cast<uint16_t>(m_numChannels), 16);
}

void ExportGen::applyFadeInOut(std::vector<float>& audio, float fadeDuration) {
    const size_t channels = std::max<uint32_t>(1, m_numChannels);
    const size_t frames = audio.size() / channels;
    size_t fadeFrames = std::min(frames / 2, static_cast<size_t>(fadeDuration * m_sampleRate));
    if (fadeFrames == 0) return;

    for (size_t f = 0; f < fadeFrames; ++f) {
        const float fadeFactor = static_cast<float>(f) / fadeFrames;
        for (size_t c = 0; c < channels; ++c) {
            audio[f * channels + c] *= fadeFactor;                       // fade in
            audio[(frames - 1 - f) * channels + c] *= fadeFactor;        // fade out
        }
    }
}

// Waveform Thumbnail Generation (PNG)
std::vector<uint8_t> ExportGen::generateWaveformThumbnail(const std::vector<float>& audio) {
    return generateWaveformThumbnail(audio, 800, 200);
}

std::vector<uint8_t> ExportGen::generateWaveformThumbnail(const std::vector<float>& audio, int width, int height) {
    width = std::clamp(width, 16, 4096);
    height = std::clamp(height, 16, 2048);
    std::vector<uint8_t> pixels(static_cast<size_t>(width) * height * 4);

    // Background
    for (size_t i = 0; i < pixels.size(); i += 4) {
        pixels[i] = 24; pixels[i + 1] = 26; pixels[i + 2] = 33; pixels[i + 3] = 255;
    }

    const std::vector<float> mono = FileIO::convertChannels(audio, std::max<uint32_t>(1, m_numChannels), 1);
    const float mid = (height - 1) * 0.5f;
    for (int x = 0; x < width; ++x) {
        float lo = 0.0f, hi = 0.0f;
        if (!mono.empty()) {
            const size_t begin = mono.size() * x / width;
            const size_t end = std::max(begin + 1, mono.size() * (x + 1) / width);
            for (size_t i = begin; i < end && i < mono.size(); ++i) {
                lo = std::min(lo, mono[i]);
                hi = std::max(hi, mono[i]);
            }
        }
        const int y0 = static_cast<int>(std::lround(mid - std::clamp(hi, -1.0f, 1.0f) * mid));
        const int y1 = static_cast<int>(std::lround(mid - std::clamp(lo, -1.0f, 1.0f) * mid));
        for (int y = std::max(0, y0); y <= std::min(height - 1, y1); ++y) {
            uint8_t* p = &pixels[(static_cast<size_t>(y) * width + x) * 4];
            p[0] = 96; p[1] = 196; p[2] = 255; p[3] = 255;
        }
        uint8_t* centre = &pixels[(static_cast<size_t>(mid) * width + x) * 4];
        centre[0] = std::max<uint8_t>(centre[0], 70); centre[1] = std::max<uint8_t>(centre[1], 70); centre[2] = std::max<uint8_t>(centre[2], 80);
    }

    std::vector<uint8_t> png;
    auto writer = [](void* context, void* data, int size) {
        auto* out = static_cast<std::vector<uint8_t>*>(context);
        const auto* bytes = static_cast<const uint8_t*>(data);
        out->insert(out->end(), bytes, bytes + size);
    };
    if (!stbi_write_png_to_func(writer, &png, width, height, 4, pixels.data(), width * 4)) {
        m_warnings.push_back("Waveform thumbnail PNG encoding failed");
        png.clear();
    }
    return png;
}

// Manifest Generation
ExportManifest ExportGen::generateManifest(const ExportDefinition& exportDef, const ExportResult& result) {
    ExportManifest manifest;
    manifest.version = exportDef.version;
    manifest.date = std::chrono::system_clock::now();
    manifest.name = exportDef.name;
    manifest.notes = exportDef.notes;
    manifest.changelog = exportDef.changelog;
    manifest.tags = exportDef.tags;
    for (const auto& [key, value] : metadataFields(exportDef.metadata)) {
        manifest.metadata[key] = value;
    }

    // Add file entries
    for (const auto& convertedFile : result.convertedFiles) {
        FileEntry entry;
        entry.path = "audio/" + (convertedFile.filename.empty()
            ? exportDef.name + "_" + getFormatString(convertedFile.format) + "." + getFormatExtension(convertedFile.format)
            : convertedFile.filename);
        entry.size = convertedFile.data.size();
        entry.checksum = convertedFile.checksum.empty() ? calculateSHA256(convertedFile.data) : convertedFile.checksum;
        entry.format = getFormatString(convertedFile.format);
        entry.modifiedTime = manifest.date;
        manifest.files.push_back(entry);
    }

    // Add preview file
    if (!result.previewData.empty()) {
        FileEntry entry;
        entry.path = "preview/" + exportDef.name + "_preview.wav";
        entry.size = result.previewData.size();
        entry.checksum = calculateSHA256(result.previewData);
        entry.format = "WAV";
        entry.modifiedTime = manifest.date;
        manifest.files.push_back(entry);
    }

    // Add thumbnail file
    if (!result.thumbnailData.empty()) {
        FileEntry entry;
        entry.path = "thumbs/" + exportDef.name + "_waveform.png";
        entry.size = result.thumbnailData.size();
        entry.checksum = calculateSHA256(result.thumbnailData);
        entry.format = "PNG";
        entry.modifiedTime = manifest.date;
        manifest.files.push_back(entry);
    }

    size_t total = 0;
    for (const auto& f : manifest.files) total += f.size;
    manifest.totalSize = std::to_string(total);
    manifest.totalFiles = std::to_string(manifest.files.size());

    return manifest;
}

// Package Creation: stored ZIP with the exported audio, preview, thumbnail and manifest.json
std::vector<uint8_t> ExportGen::createPackage(const ExportDefinition& exportDef, const ExportResult& result) {
    if (exportDef.archive.format != ArchiveSettings::Format::ZIP) {
        m_warnings.push_back("Only ZIP packages are supported; packaging as ZIP");
    }
    if (exportDef.archive.encrypt) {
        m_warnings.push_back("Package encryption is not supported; package written unencrypted");
    }

    std::vector<FileIO::ZipEntry> entries;
    size_t fileIndex = 0;
    for (const auto& convertedFile : result.convertedFiles) {
        const std::string path = fileIndex < result.manifest.files.size()
            ? result.manifest.files[fileIndex].path
            : "audio/" + convertedFile.filename;
        entries.push_back({path, convertedFile.data});
        ++fileIndex;
    }
    if (!result.previewData.empty()) {
        entries.push_back({"preview/" + exportDef.name + "_preview.wav", result.previewData});
    }
    if (!result.thumbnailData.empty()) {
        entries.push_back({"thumbs/" + exportDef.name + "_waveform.png", result.thumbnailData});
    }
    const std::string manifestText = manifestToJson(result.manifest).dump(2);
    entries.push_back({"manifest.json", std::vector<uint8_t>(manifestText.begin(), manifestText.end())});

    return FileIO::createZipArchive(entries);
}

// Distribution
void ExportGen::distributePackage(const ExportDefinition& exportDef, const ExportResult& result) {
    for (const auto& destination : exportDef.destinations) {
        const int attempts = destination.enableRetry && m_enableRetryLogic ? std::max(1, destination.maxRetries) : 1;
        for (int attempt = 1; attempt <= attempts; ++attempt) {
            try {
                ExportResult named = result;
                named.exportPath = exportDef.name + "-" + exportDef.version + ".zip";
                uploadToDestination(destination, named);
                break;
            } catch (const std::exception& e) {
                m_lastError = "Distribution error: " + std::string(e.what());
                if (attempt == attempts) {
                    m_warnings.push_back(m_lastError);
                } else {
                    std::this_thread::sleep_for(std::chrono::milliseconds(std::max(0, destination.retryDelayMs)));
                }
            }
        }
    }
}

void ExportGen::uploadToDestination(const DistributionDestination& destination, const ExportResult& result) {
    switch (destination.type) {
        case DistributionDestination::Type::FILESYSTEM:
            uploadToFilesystem(destination, result);
            break;
        case DistributionDestination::Type::S3:
            uploadToS3(destination, result);
            break;
        case DistributionDestination::Type::AZURE_BLOB:
            uploadToAzureBlob(destination, result);
            break;
        case DistributionDestination::Type::FTP:
            uploadToFTP(destination, result);
            break;
        case DistributionDestination::Type::SFTP:
        case DistributionDestination::Type::HTTP:
        case DistributionDestination::Type::CUSTOM:
            throw std::runtime_error("Unsupported distribution destination type: " + destinationToString(destination.type));
    }
}

void ExportGen::uploadToFilesystem(const DistributionDestination& destination, const ExportResult& result) {
    const std::filesystem::path dir = destination.path.empty() ? std::filesystem::path("exports") : std::filesystem::path(destination.path);
    std::filesystem::create_directories(dir);
    const std::string packageName = result.exportPath.empty() ? "export.zip" : result.exportPath;
    if (!result.packageData.empty()) {
        if (!FileIO::writeFileBytes((dir / packageName).string(), result.packageData)) {
            throw std::runtime_error("Could not write package to " + (dir / packageName).string());
        }
    } else {
        // No package requested: copy the converted files individually
        for (const auto& file : result.convertedFiles) {
            if (!FileIO::writeFileBytes((dir / file.filename).string(), file.data)) {
                throw std::runtime_error("Could not write " + (dir / file.filename).string());
            }
        }
    }
    const std::string manifestText = manifestToJson(result.manifest).dump(2);
    if (!FileIO::writeFileBytes((dir / "manifest.json").string(), std::vector<uint8_t>(manifestText.begin(), manifestText.end()))) {
        throw std::runtime_error("Could not write manifest to " + dir.string());
    }
}

void ExportGen::uploadToS3(const DistributionDestination& destination, const ExportResult& result) {
    throw std::runtime_error("S3 distribution requires an AWS client which is not available in this build (bucket '" +
                             destination.bucket + "')");
}

void ExportGen::uploadToAzureBlob(const DistributionDestination& destination, const ExportResult& result) {
    throw std::runtime_error("Azure Blob distribution requires an Azure storage client which is not available in this build (endpoint '" +
                             destination.endpoint + "')");
}

void ExportGen::uploadToFTP(const DistributionDestination& destination, const ExportResult& result) {
    throw std::runtime_error("FTP distribution requires a network transfer client which is not available in this build (endpoint '" +
                             destination.endpoint + "')");
}

// Utility Functions
std::string ExportGen::calculateSHA256(const std::vector<uint8_t>& data) {
    return FileIO::sha256Hex(data.data(), data.size());
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

// Quantises the (already normalised / dithered) samples to the target sample format.
void ExportGen::convertAndWriteAudioData(std::vector<uint8_t>& wavData, size_t& offset,
                                        const std::vector<float>& audioData, const FormatTarget& target, const ExportParams& params) {
    for (size_t i = 0; i < audioData.size(); ++i) {
        const float sample = normalizeSample(audioData[i]);

        // Convert to target bit depth
        switch (target.bitDepth) {
            case 8:
                wavData[offset++] = static_cast<uint8_t>(std::lround(sample * 127.0f) + 128);
                break;
            case 24:
                writeInt24LE(wavData, offset, static_cast<int32_t>(std::lround(sample * 8388607.0f)));
                break;
            case 32:
            case 0:
                writeFloat32LE(wavData, offset, sample);
                break;
            default:
                writeInt16LE(wavData, offset, static_cast<int16_t>(std::lround(sample * 32767.0f)));
                break;
        }
    }
}

// Reference signal (A4 with harmonics, 5 s) in the working format
std::vector<float> ExportGen::generateTestAudio() {
    std::vector<float> audioData;
    const size_t numSamples = static_cast<size_t>(m_sampleRate) * 5;
    const size_t numChannels = std::max<uint32_t>(1, m_numChannels);

    audioData.resize(numSamples * numChannels);

    for (size_t i = 0; i < numSamples; ++i) {
        float time = static_cast<float>(i) / static_cast<float>(m_sampleRate);

        // Generate a test tone
        float frequency = 440.0f; // A4 note
        float amplitude = 0.3f;
        float sample = amplitude * std::sin(2.0f * kPi * frequency * time);

        // Add some harmonics
        sample += 0.1f * amplitude * std::sin(2.0f * kPi * frequency * 2.0f * time);
        sample += 0.05f * amplitude * std::sin(2.0f * kPi * frequency * 3.0f * time);

        // Write to all channels
        for (size_t ch = 0; ch < numChannels; ++ch) {
            audioData[i * numChannels + ch] = sample;
        }
    }

    return audioData;
}

// Quality calculation functions
float ExportGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
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
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float ExportGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void ExportGen::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 10);
}

void ExportGen::setOversamplingFactor(int factor) {
    m_oversamplingFactor = std::clamp(factor, 1, 8);
}

void ExportGen::setAntiAliasingEnabled(bool enable) {
    m_antiAliasingEnabled = enable;
}

// Processing Options
void ExportGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void ExportGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, 16);
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

// Sample Processing: keeps a sample inside the representable range before quantisation.
float ExportGen::normalizeSample(float sample) {
    if (!std::isfinite(sample)) return 0.0f;
    return std::clamp(sample, -1.0f, 1.0f);
}

// TPDF dither at the 16-bit LSB level.
float ExportGen::applyDithering(float sample) {
    thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_real_distribution<float> dis(-0.5f, 0.5f);

    const float dither = (dis(gen) + dis(gen)) / 32768.0f;
    return sample + dither;
}

} // namespace Audio
} // namespace MagiTech
