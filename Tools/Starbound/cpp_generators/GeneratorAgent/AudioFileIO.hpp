#pragma once

// Shared audio file / codec helpers for the audio generator family
// (SampleGen, SampleGenPipeline, ExportGen, SynthGen).

#include <cstdint>
#include <string>
#include <vector>

namespace MagiTech {
namespace Audio {
namespace FileIO {

// Decoded PCM audio, interleaved float samples in [-1, 1].
struct DecodedAudio {
    std::vector<float> samples;
    uint32_t sampleRate = 0;
    uint32_t channels = 0;

    size_t frameCount() const { return channels ? samples.size() / channels : 0; }
};

// Raw file access
bool readFileBytes(const std::string& path, std::vector<uint8_t>& out);
bool writeFileBytes(const std::string& path, const std::vector<uint8_t>& data);
std::string lowerExtension(const std::string& path); // ".wav", ".ogg", ...

// Decoders. Return false and fill `error` on failure.
bool decodeWavMemory(const uint8_t* data, size_t size, DecodedAudio& out, std::string& error);
bool decodeOggMemory(const uint8_t* data, size_t size, DecodedAudio& out, std::string& error);
// Dispatches on the file extension (.wav/.wave, .ogg). MP3 is reported as unsupported
// because no MP3 decoder is vendored.
bool decodeFile(const std::string& path, DecodedAudio& out, std::string& error);

// Sample conversion
std::vector<float> convertChannels(const std::vector<float>& interleaved, uint32_t fromChannels, uint32_t toChannels);
std::vector<float> resampleLinear(const std::vector<float>& interleaved, uint32_t channels,
                                  uint32_t fromRate, uint32_t toRate);
// Decode a file and convert it to the requested rate / channel count.
bool decodeFileAs(const std::string& path, uint32_t sampleRate, uint32_t channels,
                  std::vector<float>& out, std::string& error);

// RIFF/WAVE encoder. bitsPerSample: 8, 16, 24, 32 (32 => IEEE float when floatFormat).
std::vector<uint8_t> encodeWav(const std::vector<float>& interleaved, uint32_t sampleRate,
                               uint16_t channels, uint16_t bitsPerSample, bool floatFormat = false);

// Checksums / hashes
uint32_t crc32(const uint8_t* data, size_t size, uint32_t previous = 0);
std::string sha256Hex(const uint8_t* data, size_t size);
uint64_t fnv1a64(const void* data, size_t size, uint64_t seed = 1469598103934665603ULL);

// Uncompressed ("stored") ZIP archive writer.
struct ZipEntry {
    std::string name;
    std::vector<uint8_t> data;
};
std::vector<uint8_t> createZipArchive(const std::vector<ZipEntry>& entries);

} // namespace FileIO
} // namespace Audio
} // namespace MagiTech
