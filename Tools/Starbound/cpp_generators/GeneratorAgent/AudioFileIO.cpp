#include "AudioFileIO.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>

// Declarations only; the implementation is compiled once in AudioStbVorbis.cpp.
#define STB_VORBIS_HEADER_ONLY
#include "vendor/stb/stb_vorbis.c"

namespace MagiTech {
namespace Audio {
namespace FileIO {

namespace {

uint16_t readLE16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
uint32_t readLE32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

void putLE16(std::vector<uint8_t>& out, uint16_t v) {
    out.push_back(static_cast<uint8_t>(v & 0xFF));
    out.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
}
void putLE32(std::vector<uint8_t>& out, uint32_t v) {
    for (int i = 0; i < 4; ++i) out.push_back(static_cast<uint8_t>((v >> (8 * i)) & 0xFF));
}
void putTag(std::vector<uint8_t>& out, const char* tag) {
    out.insert(out.end(), tag, tag + 4);
}

} // namespace

bool readFileBytes(const std::string& path, std::vector<uint8_t>& out) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    file.seekg(0, std::ios::end);
    std::streamoff size = file.tellg();
    if (size < 0) return false;
    file.seekg(0, std::ios::beg);
    out.resize(static_cast<size_t>(size));
    if (size > 0) file.read(reinterpret_cast<char*>(out.data()), size);
    return static_cast<bool>(file) || file.eof();
}

bool writeFileBytes(const std::string& path, const std::vector<uint8_t>& data) {
    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    if (!file) return false;
    if (!data.empty()) file.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
    return static_cast<bool>(file);
}

std::string lowerExtension(const std::string& path) {
    size_t dot = path.find_last_of('.');
    size_t slash = path.find_last_of("/\\");
    if (dot == std::string::npos || (slash != std::string::npos && dot < slash)) return {};
    std::string ext = path.substr(dot);
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return ext;
}

bool decodeWavMemory(const uint8_t* data, size_t size, DecodedAudio& out, std::string& error) {
    if (size < 12 || std::memcmp(data, "RIFF", 4) != 0 || std::memcmp(data + 8, "WAVE", 4) != 0) {
        error = "not a RIFF/WAVE file";
        return false;
    }

    uint16_t format = 0, channels = 0, bits = 0;
    uint32_t rate = 0;
    const uint8_t* pcm = nullptr;
    size_t pcmSize = 0;

    size_t pos = 12;
    while (pos + 8 <= size) {
        uint32_t chunkSize = readLE32(data + pos + 4);
        const uint8_t* body = data + pos + 8;
        size_t available = std::min<size_t>(chunkSize, size - (pos + 8));
        if (std::memcmp(data + pos, "fmt ", 4) == 0 && available >= 16) {
            format = readLE16(body);
            channels = readLE16(body + 2);
            rate = readLE32(body + 4);
            bits = readLE16(body + 14);
            if (format == 0xFFFE && available >= 26) {
                format = readLE16(body + 24); // WAVE_FORMAT_EXTENSIBLE sub-format
            }
        } else if (std::memcmp(data + pos, "data", 4) == 0) {
            pcm = body;
            pcmSize = available;
        }
        pos += 8 + static_cast<size_t>(chunkSize) + (chunkSize & 1u);
    }

    if (!pcm || channels == 0 || rate == 0) {
        error = "WAVE file has no fmt/data chunk";
        return false;
    }
    if (format != 1 && format != 3) {
        error = "unsupported WAVE encoding (only PCM and IEEE float are supported)";
        return false;
    }

    const size_t bytesPerSample = bits / 8;
    if (bytesPerSample == 0 || (format == 3 && bits != 32 && bits != 64)) {
        error = "unsupported WAVE bit depth";
        return false;
    }

    const size_t count = pcmSize / bytesPerSample;
    out.samples.resize(count);
    out.sampleRate = rate;
    out.channels = channels;

    for (size_t i = 0; i < count; ++i) {
        const uint8_t* s = pcm + i * bytesPerSample;
        float v = 0.0f;
        if (format == 3) {
            if (bits == 32) {
                std::memcpy(&v, s, 4);
            } else {
                double d;
                std::memcpy(&d, s, 8);
                v = static_cast<float>(d);
            }
        } else {
            switch (bits) {
                case 8: v = (static_cast<int>(s[0]) - 128) / 128.0f; break;
                case 16: v = static_cast<int16_t>(readLE16(s)) / 32768.0f; break;
                case 24: {
                    int32_t x = static_cast<int32_t>(s[0] | (s[1] << 8) | (s[2] << 16));
                    if (x & 0x800000) x |= ~0xFFFFFF;
                    v = x / 8388608.0f;
                    break;
                }
                case 32: v = static_cast<float>(static_cast<int32_t>(readLE32(s)) / 2147483648.0); break;
                default:
                    error = "unsupported PCM bit depth";
                    return false;
            }
        }
        out.samples[i] = v;
    }
    return true;
}

bool decodeOggMemory(const uint8_t* data, size_t size, DecodedAudio& out, std::string& error) {
    int channels = 0;
    int rate = 0;
    short* decoded = nullptr;
    int frames = stb_vorbis_decode_memory(data, static_cast<int>(size), &channels, &rate, &decoded);
    if (frames < 0 || !decoded || channels <= 0) {
        if (decoded) std::free(decoded);
        error = "failed to decode Ogg Vorbis stream";
        return false;
    }
    const size_t count = static_cast<size_t>(frames) * static_cast<size_t>(channels);
    out.samples.resize(count);
    for (size_t i = 0; i < count; ++i) out.samples[i] = decoded[i] / 32768.0f;
    out.sampleRate = static_cast<uint32_t>(rate);
    out.channels = static_cast<uint32_t>(channels);
    std::free(decoded);
    return true;
}

bool decodeFile(const std::string& path, DecodedAudio& out, std::string& error) {
    std::vector<uint8_t> bytes;
    if (!readFileBytes(path, bytes)) {
        error = "cannot read audio file: " + path;
        return false;
    }
    const std::string ext = lowerExtension(path);
    bool ok = false;
    if (ext == ".ogg" || ext == ".oga") {
        ok = decodeOggMemory(bytes.data(), bytes.size(), out, error);
    } else if (ext == ".mp3") {
        error = "MP3 decoding is not available (no MP3 decoder is vendored): " + path;
        return false;
    } else {
        ok = decodeWavMemory(bytes.data(), bytes.size(), out, error);
    }
    if (!ok) error += " (" + path + ")";
    return ok;
}

std::vector<float> convertChannels(const std::vector<float>& interleaved, uint32_t fromChannels, uint32_t toChannels) {
    if (fromChannels == 0 || toChannels == 0 || fromChannels == toChannels) return interleaved;
    const size_t frames = interleaved.size() / fromChannels;
    std::vector<float> out(frames * toChannels);
    for (size_t f = 0; f < frames; ++f) {
        const float* in = &interleaved[f * fromChannels];
        float* dst = &out[f * toChannels];
        if (toChannels == 1) {
            float sum = 0.0f;
            for (uint32_t c = 0; c < fromChannels; ++c) sum += in[c];
            dst[0] = sum / static_cast<float>(fromChannels);
        } else if (fromChannels == 1) {
            for (uint32_t c = 0; c < toChannels; ++c) dst[c] = in[0];
        } else {
            for (uint32_t c = 0; c < toChannels; ++c) dst[c] = in[c % fromChannels];
        }
    }
    return out;
}

std::vector<float> resampleLinear(const std::vector<float>& interleaved, uint32_t channels,
                                  uint32_t fromRate, uint32_t toRate) {
    if (channels == 0 || fromRate == 0 || toRate == 0 || fromRate == toRate || interleaved.empty()) return interleaved;
    const size_t inFrames = interleaved.size() / channels;
    const size_t outFrames = static_cast<size_t>(std::llround(static_cast<double>(inFrames) * toRate / fromRate));
    std::vector<float> out(outFrames * channels);
    const double step = static_cast<double>(fromRate) / static_cast<double>(toRate);
    for (size_t f = 0; f < outFrames; ++f) {
        double src = f * step;
        size_t i0 = static_cast<size_t>(src);
        size_t i1 = std::min(i0 + 1, inFrames - 1);
        i0 = std::min(i0, inFrames - 1);
        float frac = static_cast<float>(src - static_cast<double>(i0));
        for (uint32_t c = 0; c < channels; ++c) {
            float a = interleaved[i0 * channels + c];
            float b = interleaved[i1 * channels + c];
            out[f * channels + c] = a + (b - a) * frac;
        }
    }
    return out;
}

bool decodeFileAs(const std::string& path, uint32_t sampleRate, uint32_t channels,
                  std::vector<float>& out, std::string& error) {
    DecodedAudio decoded;
    if (!decodeFile(path, decoded, error)) return false;
    std::vector<float> converted = convertChannels(decoded.samples, decoded.channels, channels);
    out = resampleLinear(converted, channels, decoded.sampleRate, sampleRate);
    return true;
}

std::vector<uint8_t> encodeWav(const std::vector<float>& interleaved, uint32_t sampleRate,
                               uint16_t channels, uint16_t bitsPerSample, bool floatFormat) {
    if (channels == 0) channels = 1;
    if (bitsPerSample != 8 && bitsPerSample != 16 && bitsPerSample != 24 && bitsPerSample != 32) bitsPerSample = 16;
    if (floatFormat) bitsPerSample = 32;

    const uint32_t bytesPerSample = bitsPerSample / 8u;
    const uint32_t dataSize = static_cast<uint32_t>(interleaved.size() * bytesPerSample);

    std::vector<uint8_t> out;
    out.reserve(44 + dataSize);
    putTag(out, "RIFF");
    putLE32(out, 36 + dataSize);
    putTag(out, "WAVE");
    putTag(out, "fmt ");
    putLE32(out, 16);
    putLE16(out, floatFormat ? 3 : 1);
    putLE16(out, channels);
    putLE32(out, sampleRate);
    putLE32(out, sampleRate * channels * bytesPerSample);
    putLE16(out, static_cast<uint16_t>(channels * bytesPerSample));
    putLE16(out, bitsPerSample);
    putTag(out, "data");
    putLE32(out, dataSize);

    for (float s : interleaved) {
        float v = std::clamp(s, -1.0f, 1.0f);
        if (floatFormat) {
            uint32_t bits;
            std::memcpy(&bits, &v, 4);
            putLE32(out, bits);
            continue;
        }
        switch (bitsPerSample) {
            case 8: out.push_back(static_cast<uint8_t>(std::lround(v * 127.0f) + 128)); break;
            case 16: putLE16(out, static_cast<uint16_t>(static_cast<int16_t>(std::lround(v * 32767.0f)))); break;
            case 24: {
                int32_t x = static_cast<int32_t>(std::lround(v * 8388607.0f));
                out.push_back(static_cast<uint8_t>(x & 0xFF));
                out.push_back(static_cast<uint8_t>((x >> 8) & 0xFF));
                out.push_back(static_cast<uint8_t>((x >> 16) & 0xFF));
                break;
            }
            default: putLE32(out, static_cast<uint32_t>(static_cast<int32_t>(std::llround(v * 2147483647.0)))); break;
        }
    }
    return out;
}

uint32_t crc32(const uint8_t* data, size_t size, uint32_t previous) {
    static const std::array<uint32_t, 256> table = [] {
        std::array<uint32_t, 256> t{};
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t c = i;
            for (int k = 0; k < 8; ++k) c = (c & 1u) ? 0xEDB88320u ^ (c >> 1) : (c >> 1);
            t[i] = c;
        }
        return t;
    }();
    uint32_t crc = previous ^ 0xFFFFFFFFu;
    for (size_t i = 0; i < size; ++i) crc = table[(crc ^ data[i]) & 0xFFu] ^ (crc >> 8);
    return crc ^ 0xFFFFFFFFu;
}

std::string sha256Hex(const uint8_t* data, size_t size) {
    static const uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};

    auto rotr = [](uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };

    std::vector<uint8_t> msg(data, data + size);
    const uint64_t bitLen = static_cast<uint64_t>(size) * 8u;
    msg.push_back(0x80);
    while (msg.size() % 64 != 56) msg.push_back(0);
    for (int i = 7; i >= 0; --i) msg.push_back(static_cast<uint8_t>((bitLen >> (8 * i)) & 0xFF));

    for (size_t chunk = 0; chunk < msg.size(); chunk += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; ++i) {
            const uint8_t* p = &msg[chunk + i * 4];
            w[i] = (static_cast<uint32_t>(p[0]) << 24) | (static_cast<uint32_t>(p[1]) << 16) |
                   (static_cast<uint32_t>(p[2]) << 8) | static_cast<uint32_t>(p[3]);
        }
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            uint32_t ch = (e & f) ^ (~e & g);
            uint32_t t1 = hh + S1 + ch + k[i] + w[i];
            uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + maj;
            hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (uint32_t v : h) oss << std::setw(8) << v;
    return oss.str();
}

uint64_t fnv1a64(const void* data, size_t size, uint64_t seed) {
    const uint8_t* p = static_cast<const uint8_t*>(data);
    uint64_t hash = seed;
    for (size_t i = 0; i < size; ++i) {
        hash ^= p[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::vector<uint8_t> createZipArchive(const std::vector<ZipEntry>& entries) {
    std::vector<uint8_t> out;
    std::vector<uint8_t> central;
    for (const auto& entry : entries) {
        const uint32_t offset = static_cast<uint32_t>(out.size());
        const uint32_t crc = crc32(entry.data.data(), entry.data.size());
        const uint32_t size = static_cast<uint32_t>(entry.data.size());
        const uint16_t nameLen = static_cast<uint16_t>(entry.name.size());

        // Local file header (stored, no compression)
        putLE32(out, 0x04034b50);
        putLE16(out, 20);      // version needed
        putLE16(out, 0x0800);  // UTF-8 names
        putLE16(out, 0);       // method: stored
        putLE16(out, 0);       // mod time
        putLE16(out, 0x21);    // mod date (1980-01-01)
        putLE32(out, crc);
        putLE32(out, size);
        putLE32(out, size);
        putLE16(out, nameLen);
        putLE16(out, 0);
        out.insert(out.end(), entry.name.begin(), entry.name.end());
        out.insert(out.end(), entry.data.begin(), entry.data.end());

        // Central directory record
        putLE32(central, 0x02014b50);
        putLE16(central, 20);
        putLE16(central, 20);
        putLE16(central, 0x0800);
        putLE16(central, 0);
        putLE16(central, 0);
        putLE16(central, 0x21);
        putLE32(central, crc);
        putLE32(central, size);
        putLE32(central, size);
        putLE16(central, nameLen);
        putLE16(central, 0);   // extra
        putLE16(central, 0);   // comment
        putLE16(central, 0);   // disk
        putLE16(central, 0);   // internal attrs
        putLE32(central, 0);   // external attrs
        putLE32(central, offset);
        central.insert(central.end(), entry.name.begin(), entry.name.end());
    }

    const uint32_t centralOffset = static_cast<uint32_t>(out.size());
    out.insert(out.end(), central.begin(), central.end());
    putLE32(out, 0x06054b50);
    putLE16(out, 0);
    putLE16(out, 0);
    putLE16(out, static_cast<uint16_t>(entries.size()));
    putLE16(out, static_cast<uint16_t>(entries.size()));
    putLE32(out, static_cast<uint32_t>(central.size()));
    putLE32(out, centralOffset);
    putLE16(out, 0);
    return out;
}

} // namespace FileIO
} // namespace Audio
} // namespace MagiTech
