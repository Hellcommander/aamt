#include "ImageGenerator.hpp"
#include <imgui.h>
#include <imgui_internal.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <future>
#include <cmath>
#include <cstring>
#include <cctype>
#include <numeric>
#include <typeinfo>
#include <stb_image.h>        // implementation compiled once in core/StbImageImpl.cpp
#include <stb_image_write.h>  // implementation compiled once in core/StbImageImpl.cpp
#include <nlohmann/json.hpp>
#include "core/Log.hpp"

namespace MagiTech {
namespace ImageGen {

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------
namespace {

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f));
}

std::string checksumHex(const ImageBuffer& data) {
    const uint64_t h = XXH64(data.data(), data.size(), 0);
    std::ostringstream oss;
    oss << std::hex << std::setw(16) << std::setfill('0') << h;
    return oss.str();
}

bool ensureParentDirectory(const std::string& path) {
    std::error_code ec;
    const std::filesystem::path parent = std::filesystem::path(path).parent_path();
    if (parent.empty() || std::filesystem::exists(parent, ec)) {
        return true;
    }
    return std::filesystem::create_directories(parent, ec) || std::filesystem::exists(parent, ec);
}

bool writeTextFile(const std::string& path, const std::string& content, std::string& error) {
    if (!ensureParentDirectory(path)) {
        error = "Failed to create directory for: " + path;
        return false;
    }
    std::ofstream out(path, std::ios::binary);
    if (!out.is_open()) {
        error = "Failed to open output file: " + path;
        return false;
    }
    out << content;
    if (!out.good()) {
        error = "Failed to write output file: " + path;
        return false;
    }
    return true;
}

nlohmann::json anyToJson(const std::any& value) {
    if (!value.has_value()) return nullptr;
    const std::type_info& t = value.type();
    if (t == typeid(float)) return std::any_cast<float>(value);
    if (t == typeid(double)) return std::any_cast<double>(value);
    if (t == typeid(int)) return std::any_cast<int>(value);
    if (t == typeid(int64_t)) return std::any_cast<int64_t>(value);
    if (t == typeid(uint32_t)) return std::any_cast<uint32_t>(value);
    if (t == typeid(bool)) return std::any_cast<bool>(value);
    if (t == typeid(std::string)) return std::any_cast<std::string>(value);
    if (t == typeid(const char*)) return std::string(std::any_cast<const char*>(value));
    return nullptr;
}

std::any jsonToAny(const nlohmann::json& value) {
    if (value.is_boolean()) return value.get<bool>();
    if (value.is_number_integer()) return value.get<int>();
    if (value.is_number()) return value.get<float>();
    if (value.is_string()) return value.get<std::string>();
    return std::any{};
}

float anyToFloat(const std::any& value, float fallback = 0.0f) {
    if (!value.has_value()) return fallback;
    const std::type_info& t = value.type();
    if (t == typeid(float)) return std::any_cast<float>(value);
    if (t == typeid(double)) return static_cast<float>(std::any_cast<double>(value));
    if (t == typeid(int)) return static_cast<float>(std::any_cast<int>(value));
    if (t == typeid(bool)) return std::any_cast<bool>(value) ? 1.0f : 0.0f;
    return fallback;
}

nlohmann::json timelineToJson(const AnimationTimeline& timeline) {
    nlohmann::json timelineJson;
    timelineJson["id"] = timeline.id;
    timelineJson["duration"] = timeline.duration;
    timelineJson["looping"] = timeline.looping;
    timelineJson["frameRate"] = timeline.frameRate;
    timelineJson["tracks"] = timeline.trackNames;
    timelineJson["keyframes"] = nlohmann::json::array();
    for (const auto& keyframe : timeline.keyframes) {
        nlohmann::json kfJson;
        kfJson["time"] = keyframe.time;
        kfJson["trackName"] = keyframe.trackName;
        kfJson["trackType"] = static_cast<int>(keyframe.trackType);
        kfJson["interpolation"] = keyframe.interpolation;
        nlohmann::json value = anyToJson(keyframe.value);
        if (!value.is_null()) {
            kfJson["value"] = value;
        }
        timelineJson["keyframes"].push_back(kfJson);
    }
    return timelineJson;
}

AnimationTimeline timelineFromJson(const nlohmann::json& j) {
    AnimationTimeline timeline;
    timeline.id = j.value("id", std::string());
    timeline.duration = j.value("duration", 0.0f);
    timeline.looping = j.value("looping", true);
    timeline.frameRate = j.value("frameRate", 30.0f);
    if (j.contains("keyframes") && j["keyframes"].is_array()) {
        for (const auto& kfJson : j["keyframes"]) {
            TimelineKeyframe kf;
            kf.time = kfJson.value("time", 0.0f);
            kf.trackName = kfJson.value("trackName", std::string());
            kf.trackType = static_cast<TimelineTrackType>(kfJson.value("trackType", static_cast<int>(TimelineTrackType::CUSTOM)));
            kf.interpolation = kfJson.value("interpolation", std::string("linear"));
            if (kfJson.contains("value")) {
                kf.value = jsonToAny(kfJson["value"]);
            }
            timeline.keyframes.push_back(kf);
            timeline.tracks[kf.trackName].push_back(kf);
            if (std::find(timeline.trackNames.begin(), timeline.trackNames.end(), kf.trackName) == timeline.trackNames.end()) {
                timeline.trackNames.push_back(kf.trackName);
            }
        }
    }
    return timeline;
}

// Square-ish grid used for animation sheets: cols = floor(sqrt(n)), rows = ceil(n / cols).
void animationGrid(int frameCount, int& cols, int& rows) {
    const int n = std::max(1, frameCount);
    cols = std::max(1, static_cast<int>(std::sqrt(static_cast<double>(n))));
    rows = (n + cols - 1) / cols;
}

nlohmann::json atlasToJson(const SpritesheetBundle& bundle, const std::string& imageName) {
    nlohmann::json j;
    j["image"] = imageName;
    j["size"] = { bundle.combinedImage.width, bundle.combinedImage.height };
    // Starbound ".frames" compatible grid description
    j["frameGrid"] = {
        {"size", { bundle.tileWidth, bundle.tileHeight }},
        {"dimensions", { bundle.columns, bundle.rows }}
    };
    j["padding"] = bundle.padding;
    j["frameCount"] = bundle.atlasMetadata.frameCount;
    j["frameRate"] = bundle.atlasMetadata.frameRate;
    j["looping"] = bundle.atlasMetadata.looping;
    j["frames"] = nlohmann::json::array();
    for (const auto& frame : bundle.atlasMetadata.frames) {
        nlohmann::json f;
        f["name"] = frame.name;
        f["x"] = frame.x;
        f["y"] = frame.y;
        f["width"] = frame.width;
        f["height"] = frame.height;
        f["duration"] = frame.duration;
        if (!frame.properties.empty()) {
            f["properties"] = frame.properties;
        }
        j["frames"].push_back(f);
    }
    j["animations"] = nlohmann::json::array();
    for (const auto& anim : bundle.atlasMetadata.animations) {
        j["animations"].push_back({
            {"name", anim.name},
            {"frames", anim.frameIndices},
            {"frameRate", anim.frameRate},
            {"looping", anim.looping}
        });
    }
    return j;
}

void atlasFromJson(const nlohmann::json& j, SpritesheetBundle& bundle) {
    if (j.contains("frameGrid")) {
        const auto& grid = j["frameGrid"];
        if (grid.contains("size") && grid["size"].is_array() && grid["size"].size() == 2) {
            bundle.tileWidth = grid["size"][0].get<int>();
            bundle.tileHeight = grid["size"][1].get<int>();
        }
        if (grid.contains("dimensions") && grid["dimensions"].is_array() && grid["dimensions"].size() == 2) {
            bundle.columns = grid["dimensions"][0].get<int>();
            bundle.rows = grid["dimensions"][1].get<int>();
        }
    }
    bundle.padding = j.value("padding", 0);
    bundle.atlasMetadata.frameCount = j.value("frameCount", 0);
    bundle.atlasMetadata.frameRate = j.value("frameRate", 30.0f);
    bundle.atlasMetadata.looping = j.value("looping", true);
    bundle.atlasMetadata.frames.clear();
    bundle.frameBounds.clear();
    if (j.contains("frames") && j["frames"].is_array()) {
        for (const auto& f : j["frames"]) {
            AtlasMetadata::FrameInfo info;
            info.name = f.value("name", std::string());
            info.x = f.value("x", 0);
            info.y = f.value("y", 0);
            info.width = f.value("width", 0);
            info.height = f.value("height", 0);
            info.duration = f.value("duration", 0.0f);
            if (f.contains("properties") && f["properties"].is_object()) {
                info.properties = f["properties"].get<std::map<std::string, std::string>>();
            }
            bundle.atlasMetadata.frames.push_back(info);
            bundle.frameBounds.emplace_back(info.x, info.y, info.width, info.height);
        }
    }
    bundle.atlasMetadata.animations.clear();
    if (j.contains("animations") && j["animations"].is_array()) {
        for (const auto& a : j["animations"]) {
            AtlasMetadata::AnimationInfo anim;
            anim.name = a.value("name", std::string());
            anim.frameIndices = a.value("frames", std::vector<int>{});
            anim.frameRate = a.value("frameRate", 30.0f);
            anim.looping = a.value("looping", true);
            bundle.atlasMetadata.animations.push_back(anim);
        }
    }
    if (bundle.atlasMetadata.frameCount == 0) {
        bundle.atlasMetadata.frameCount = static_cast<int>(bundle.atlasMetadata.frames.size());
    }
}

// Draws the (srcX, srcY, srcW, srcH) region of `image` into the draw list without a GPU texture:
// the region is sampled onto a grid of at most 128x128 filled cells, fitted into `areaSize`.
void drawImagePreview(ImDrawList* drawList, const ImageData& image, ImVec2 areaMin, ImVec2 areaSize,
                      float scale, int srcX, int srcY, int srcW, int srcH) {
    if (!drawList || image.empty() || srcW <= 0 || srcH <= 0) {
        return;
    }
    const float fit = std::min(areaSize.x / static_cast<float>(srcW), areaSize.y / static_cast<float>(srcH)) * scale;
    const float drawW = srcW * fit;
    const float drawH = srcH * fit;
    const ImVec2 origin(areaMin.x + (areaSize.x - drawW) * 0.5f, areaMin.y + (areaSize.y - drawH) * 0.5f);
    const int cellsX = std::min(srcW, 128);
    const int cellsY = std::min(srcH, 128);
    const float cellW = drawW / cellsX;
    const float cellH = drawH / cellsY;
    const int c = image.channels;
    for (int cy = 0; cy < cellsY; ++cy) {
        const int sy = std::clamp(srcY + (cy * srcH) / cellsY, 0, image.height - 1);
        for (int cx = 0; cx < cellsX; ++cx) {
            const int sx = std::clamp(srcX + (cx * srcW) / cellsX, 0, image.width - 1);
            const uint8_t* px = &image.data[(static_cast<size_t>(sy) * image.width + sx) * c];
            const uint8_t r = px[0];
            const uint8_t g = c >= 3 ? px[1] : px[0];
            const uint8_t b = c >= 3 ? px[2] : px[0];
            const uint8_t a = c == 4 ? px[3] : (c == 2 ? px[1] : 255);
            if (a == 0) continue;
            const ImVec2 p0(origin.x + cx * cellW, origin.y + cy * cellH);
            drawList->AddRectFilled(p0, ImVec2(p0.x + cellW, p0.y + cellH), IM_COL32(r, g, b, a));
        }
    }
}

std::string replaceExtension(const std::string& path, const std::string& newExtWithDot) {
    std::filesystem::path p(path);
    p.replace_extension(newExtWithDot);
    return p.string();
}

} // namespace

// ---------------------------------------------------------------------------
// Handles / RenderContext / ImageAssembler / ImageWriter / SpritesheetAssembler
// ---------------------------------------------------------------------------
ImageHandle allocateImageHandle() {
    static std::atomic<ImageHandle> nextHandle{1};
    ImageHandle h = nextHandle.fetch_add(1, std::memory_order_relaxed);
    if (h == 0) {  // wrapped around: 0 is reserved for "no handle"
        h = nextHandle.fetch_add(1, std::memory_order_relaxed);
    }
    return h;
}

void RenderContext::resize(int width, int height) {
    if (width == m_color.width && height == m_color.height && !m_color.data.empty()) {
        return;
    }
    m_color.allocate(std::max(0, width), std::max(0, height), 4);
}

void RenderContext::clear(const glm::vec4& color) {
    const uint8_t rgba[4] = { toByte(color.r), toByte(color.g), toByte(color.b), toByte(color.a) };
    for (size_t i = 0; i + 3 < m_color.data.size(); i += 4) {
        std::memcpy(&m_color.data[i], rgba, 4);
    }
}

ImageData RenderContext::readPixels() const {
    ImageData copy = m_color;
    copy.handle = allocateImageHandle();
    return copy;
}

ImageData ImageAssembler::toRGBA(const ImageData& src) const {
    if (src.channels == 4) {
        return src;
    }
    ImageData out;
    out.handle = src.handle;
    out.allocate(src.width, src.height, 4);
    const size_t pixels = static_cast<size_t>(src.width) * static_cast<size_t>(src.height);
    for (size_t p = 0; p < pixels; ++p) {
        const uint8_t* s = &src.data[p * src.channels];
        uint8_t* d = &out.data[p * 4];
        switch (src.channels) {
            case 1: d[0] = d[1] = d[2] = s[0]; d[3] = 255; break;
            case 2: d[0] = d[1] = d[2] = s[0]; d[3] = s[1]; break;
            case 3: d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = 255; break;
            default: d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3]; break;
        }
    }
    return out;
}

ImageData ImageAssembler::resize(const ImageData& src, int newWidth, int newHeight) const {
    ImageData out;
    out.handle = src.handle;
    out.allocate(newWidth, newHeight, src.channels);
    if (src.empty() || newWidth <= 0 || newHeight <= 0) {
        return out;
    }
    if (newWidth == src.width && newHeight == src.height) {
        out.data = src.data;
        return out;
    }
    const int c = src.channels;
    const float sx = static_cast<float>(src.width) / static_cast<float>(newWidth);
    const float sy = static_cast<float>(src.height) / static_cast<float>(newHeight);
    for (int y = 0; y < newHeight; ++y) {
        const float fy = std::clamp((y + 0.5f) * sy - 0.5f, 0.0f, static_cast<float>(src.height - 1));
        const int y0 = static_cast<int>(fy);
        const int y1 = std::min(y0 + 1, src.height - 1);
        const float ty = fy - static_cast<float>(y0);
        for (int x = 0; x < newWidth; ++x) {
            const float fx = std::clamp((x + 0.5f) * sx - 0.5f, 0.0f, static_cast<float>(src.width - 1));
            const int x0 = static_cast<int>(fx);
            const int x1 = std::min(x0 + 1, src.width - 1);
            const float tx = fx - static_cast<float>(x0);
            for (int ch = 0; ch < c; ++ch) {
                const float a = src.data[(static_cast<size_t>(y0) * src.width + x0) * c + ch];
                const float b = src.data[(static_cast<size_t>(y0) * src.width + x1) * c + ch];
                const float d = src.data[(static_cast<size_t>(y1) * src.width + x0) * c + ch];
                const float e = src.data[(static_cast<size_t>(y1) * src.width + x1) * c + ch];
                const float top = a + (b - a) * tx;
                const float bottom = d + (e - d) * tx;
                out.data[(static_cast<size_t>(y) * newWidth + x) * c + ch] =
                    static_cast<uint8_t>(std::lround(std::clamp(top + (bottom - top) * ty, 0.0f, 255.0f)));
            }
        }
    }
    return out;
}

void ImageAssembler::fill(ImageData& image, const glm::vec4& color) const {
    const uint8_t rgba[4] = { toByte(color.r), toByte(color.g), toByte(color.b), toByte(color.a) };
    const int c = std::max(1, image.channels);
    for (size_t i = 0; i + c <= image.data.size(); i += c) {
        for (int ch = 0; ch < c; ++ch) {
            image.data[i + ch] = (c == 1 || c == 2) ? (ch == 0 ? rgba[0] : rgba[3]) : rgba[std::min(ch, 3)];
        }
    }
}

void ImageAssembler::blit(ImageData& dst, const ImageData& src, int x, int y) const {
    if (src.empty() || dst.empty()) {
        return;
    }
    const ImageData converted = (src.channels == dst.channels) ? ImageData{} : toRGBA(src);
    const ImageData& s = (src.channels == dst.channels) ? src : converted;
    const int c = dst.channels;
    if (s.channels != c) {
        // dst is not RGBA and src differs: convert per pixel through RGBA.
        for (int sy = 0; sy < s.height; ++sy) {
            const int dy = y + sy;
            if (dy < 0 || dy >= dst.height) continue;
            for (int sx = 0; sx < s.width; ++sx) {
                const int dx = x + sx;
                if (dx < 0 || dx >= dst.width) continue;
                const uint8_t* sp = &s.data[(static_cast<size_t>(sy) * s.width + sx) * s.channels];
                uint8_t* dp = &dst.data[(static_cast<size_t>(dy) * dst.width + dx) * c];
                const uint8_t gray = static_cast<uint8_t>((sp[0] * 77 + sp[1] * 150 + sp[2] * 29) >> 8);
                if (c == 1) { dp[0] = gray; }
                else if (c == 2) { dp[0] = gray; dp[1] = sp[3]; }
                else { dp[0] = sp[0]; dp[1] = sp[1]; dp[2] = sp[2]; }
            }
        }
        return;
    }
    for (int sy = 0; sy < s.height; ++sy) {
        const int dy = y + sy;
        if (dy < 0 || dy >= dst.height) continue;
        const int startX = std::max(0, -x);
        const int endX = std::min(s.width, dst.width - x);
        if (endX <= startX) continue;
        std::memcpy(&dst.data[(static_cast<size_t>(dy) * dst.width + (x + startX)) * c],
                    &s.data[(static_cast<size_t>(sy) * s.width + startX) * c],
                    static_cast<size_t>(endX - startX) * c);
    }
}

ImageData ImageAssembler::addPadding(const ImageData& src, int padding, const glm::vec4& paddingColor) const {
    if (padding <= 0) {
        return src;
    }
    ImageData out;
    out.handle = allocateImageHandle();
    out.allocate(src.width + padding * 2, src.height + padding * 2, src.channels);
    fill(out, paddingColor);
    blit(out, src, padding, padding);
    return out;
}

ImageData ImageAssembler::crop(const ImageData& src, int x, int y, int w, int h) const {
    ImageData out;
    out.handle = allocateImageHandle();
    out.allocate(w, h, src.channels);
    if (src.empty() || w <= 0 || h <= 0) {
        return out;
    }
    const int c = src.channels;
    for (int row = 0; row < h; ++row) {
        const int sy = y + row;
        if (sy < 0 || sy >= src.height) continue;
        const int startX = std::max(0, -x);
        const int endX = std::min(w, src.width - x);
        if (endX <= startX) continue;
        std::memcpy(&out.data[(static_cast<size_t>(row) * w + startX) * c],
                    &src.data[(static_cast<size_t>(sy) * src.width + (x + startX)) * c],
                    static_cast<size_t>(endX - startX) * c);
    }
    return out;
}

ImageFormat ImageWriter::formatFromPath(const std::string& path) {
    std::string ext = std::filesystem::path(path).extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    if (ext == ".jpg" || ext == ".jpeg") return ImageFormat::JPG;
    if (ext == ".bmp") return ImageFormat::BMP;
    if (ext == ".tga") return ImageFormat::TGA;
    if (ext == ".hdr") return ImageFormat::HDR;
    return ImageFormat::PNG;
}

bool ImageWriter::write(const ImageData& image, const std::string& path) const {
    return write(image, path, formatFromPath(path));
}

bool ImageWriter::write(const ImageData& image, const std::string& path, ImageFormat format, float quality) const {
    if (image.empty()) {
        m_lastError = "Cannot write empty image: " + path;
        return false;
    }
    if (image.channels < 1 || image.channels > 4 ||
        image.data.size() < static_cast<size_t>(image.width) * image.height * image.channels) {
        m_lastError = "Image buffer does not match its dimensions: " + path;
        return false;
    }
    if (!ensureParentDirectory(path)) {
        m_lastError = "Failed to create directory for: " + path;
        return false;
    }
    int ok = 0;
    switch (format) {
        case ImageFormat::PNG:
            ok = stbi_write_png(path.c_str(), image.width, image.height, image.channels,
                                image.data.data(), image.width * image.channels);
            break;
        case ImageFormat::JPG: {
            const int q = std::clamp(static_cast<int>(std::lround(quality * 100.0f)), 1, 100);
            ok = stbi_write_jpg(path.c_str(), image.width, image.height, image.channels, image.data.data(), q);
            break;
        }
        case ImageFormat::BMP:
            ok = stbi_write_bmp(path.c_str(), image.width, image.height, image.channels, image.data.data());
            break;
        case ImageFormat::TGA:
            ok = stbi_write_tga(path.c_str(), image.width, image.height, image.channels, image.data.data());
            break;
        case ImageFormat::HDR: {
            std::vector<float> linear(image.data.size());
            for (size_t i = 0; i < image.data.size(); ++i) {
                linear[i] = static_cast<float>(image.data[i]) / 255.0f;
            }
            ok = stbi_write_hdr(path.c_str(), image.width, image.height, image.channels, linear.data());
            break;
        }
    }
    if (!ok) {
        m_lastError = "Failed to write image: " + path;
        return false;
    }
    return true;
}

bool ImageWriter::read(const std::string& path, ImageData& out, int desiredChannels) const {
    int w = 0, h = 0, fileChannels = 0;
    stbi_uc* pixels = stbi_load(path.c_str(), &w, &h, &fileChannels, desiredChannels);
    if (!pixels) {
        const char* reason = stbi_failure_reason();
        m_lastError = "Failed to load image " + path + (reason ? (": " + std::string(reason)) : std::string());
        return false;
    }
    const int channels = desiredChannels > 0 ? desiredChannels : fileChannels;
    out.handle = allocateImageHandle();
    out.width = w;
    out.height = h;
    out.channels = channels;
    out.data.assign(pixels, pixels + static_cast<size_t>(w) * h * channels);
    stbi_image_free(pixels);
    return true;
}

SpritesheetBundle SpritesheetAssembler::assemble(const std::vector<ImageBundle>& tiles,
                                                 int cols, int rows, int tileW, int tileH, int padding,
                                                 const glm::vec4& backgroundColor,
                                                 float frameRate, bool looping,
                                                 const std::string& animationName) const {
    SpritesheetBundle sheet;
    cols = std::max(1, cols);
    rows = std::max(1, rows);
    padding = std::max(0, padding);
    if (tileW <= 0 || tileH <= 0) {
        // Derive the tile size from the first non-empty tile.
        for (const auto& t : tiles) {
            if (!t.image.empty()) { tileW = t.image.width; tileH = t.image.height; break; }
        }
    }
    tileW = std::max(1, tileW);
    tileH = std::max(1, tileH);

    const int sheetWidth = cols * (tileW + padding) - padding;
    const int sheetHeight = rows * (tileH + padding) - padding;

    sheet.combinedImage.handle = allocateImageHandle();
    sheet.combinedImage.allocate(sheetWidth, sheetHeight, 4);
    m_images.fill(sheet.combinedImage, backgroundColor);
    sheet.spritesheet = sheet.combinedImage.handle;
    sheet.spritesheetTexture = allocateImageHandle();
    sheet.columns = cols;
    sheet.rows = rows;
    sheet.tileWidth = tileW;
    sheet.tileHeight = tileH;
    sheet.padding = padding;

    const int capacity = cols * rows;
    const int count = std::min(static_cast<int>(tiles.size()), capacity);
    const float frameDuration = frameRate > 0.0f ? 1.0f / frameRate : 0.0f;

    AtlasMetadata::AnimationInfo animInfo;
    animInfo.name = animationName;
    animInfo.frameRate = frameRate;
    animInfo.looping = looping;

    for (int i = 0; i < count; ++i) {
        const int col = i % cols;
        const int row = i / cols;
        const int x = col * (tileW + padding);
        const int y = row * (tileH + padding);

        const ImageBundle& tile = tiles[static_cast<size_t>(i)];
        if (!tile.image.empty()) {
            ImageData rgba = m_images.toRGBA(tile.image);
            if (rgba.width != tileW || rgba.height != tileH) {
                rgba = m_images.resize(rgba, tileW, tileH);
            }
            m_images.blit(sheet.combinedImage, rgba, x, y);
        }

        sheet.individualFrames.push_back(tile.image.handle != 0 ? tile.image.handle : allocateImageHandle());
        sheet.individualTextures.push_back(tile.texture != 0 ? tile.texture : allocateImageHandle());
        sheet.frameBounds.emplace_back(static_cast<float>(x), static_cast<float>(y),
                                       static_cast<float>(tileW), static_cast<float>(tileH));

        AtlasMetadata::FrameInfo info;
        info.name = tile.metadata.id.empty() ? ("frame_" + std::to_string(i)) : tile.metadata.id;
        info.x = x;
        info.y = y;
        info.width = tileW;
        info.height = tileH;
        info.duration = frameDuration;
        if (tile.metadata.frameIndex >= 0) {
            info.properties["frameIndex"] = std::to_string(tile.metadata.frameIndex);
            info.properties["timestamp"] = std::to_string(tile.metadata.timestamp);
        }
        sheet.atlasMetadata.frames.push_back(info);
        animInfo.frameIndices.push_back(i);
    }

    sheet.atlasMetadata.id = animationName + "_sheet";
    sheet.atlasMetadata.name = animationName;
    sheet.atlasMetadata.description = "Sprite sheet assembled from " + std::to_string(count) + " frames";
    sheet.atlasMetadata.frameCount = count;
    sheet.atlasMetadata.frameRate = frameRate;
    sheet.atlasMetadata.looping = looping;
    sheet.atlasMetadata.animations.push_back(animInfo);

    sheet.memoryUsage = sheet.combinedImage.byteSize();
    sheet.creationTime = std::chrono::system_clock::now();
    return sheet;
}

// ImageGenerator Implementation
ImageGenerator::ImageGenerator()
    : m_processingQuality(DEFAULT_PROCESSING_QUALITY)
    , m_compressionQuality(DEFAULT_COMPRESSION_QUALITY)
    , m_gpuAccelerationEnabled(false)
    , m_asyncProcessingEnabled(true)
    , m_maxProcessingThreads(4)
    , m_cachingEnabled(true)
    , m_hotReloadEnabled(false)
{
    // Initialize default state
    m_state.id = "image_generator";
    m_state.imageParams.id = "default_image";
    m_state.imageParams.width = 512;
    m_state.imageParams.height = 512;
    m_state.imageParams.format = ImageFormat::PNG;
    m_state.imageParams.quality = ImageQuality::HIGH;
    
    m_state.spritesheetParams.id = "default_spritesheet";
    m_state.spritesheetParams.columns = 4;
    m_state.spritesheetParams.rows = 3;
    m_state.spritesheetParams.tileWidth = 256;
    m_state.spritesheetParams.tileHeight = 256;
    m_state.spritesheetParams.padding = 2;
    m_state.spritesheetParams.layout = SpritesheetLayout::GRID;
    m_state.spritesheetParams.paddingStyle = PaddingStyle::TRANSPARENT;
    
    m_state.captureParams.id = "default_capture";
    m_state.captureParams.width = 512;
    m_state.captureParams.height = 512;
    
    m_state.uiParams.showWindow = true;
    m_state.uiParams.showPreview = true;
    m_state.uiParams.showControls = true;
    
    // Initialize animation state
    m_animationState.id = "animation_generator";
    m_animationState.animationParams.id = "default_animation";
    m_animationState.animationParams.mode = AnimationMode::ANIMATED_SEQUENCE;
    m_animationState.animationParams.frameCount = DEFAULT_ANIMATION_FRAME_COUNT;
    m_animationState.animationParams.frameDuration = DEFAULT_ANIMATION_FRAME_DURATION;
    m_animationState.animationParams.frameOrder = FrameOrder::ROW_MAJOR;
    m_animationState.animationParams.looping = true;
    m_animationState.animationParams.frameRate = DEFAULT_ANIMATION_FRAME_RATE;
    m_animationState.animationParams.useTimeline = false;
    m_animationState.animationParams.timelineDuration = 1.0f;
    m_animationState.animationParams.exportFormat = AnimationExportFormat::STARBOUND_ANIMATION;
    m_animationState.animationParams.generateAnimationJSON = true;
    m_animationState.animationParams.generateAtlasJSON = true;
    m_animationState.animationParams.animationName = "default";
    m_animationState.animationParams.starboundCompatible = true;
    m_animationState.animationParams.starboundCategory = "mech";
    m_animationState.animationParams.starboundType = "animation";
    
    m_animationState.spritesheetParams = m_state.spritesheetParams;
    m_animationState.captureParams = m_state.captureParams;
    m_animationState.uiParams = m_state.uiParams;
    
    m_animationState.showAnimationGenerator = true;
    m_animationState.showTimelineEditor = true;
    m_animationState.showPreview = true;
    m_animationState.showControls = true;
    
    // Initialize pipeline manager
    m_pipelineManager = std::make_unique<PipelineManager>();
}

ImageGenerator::~ImageGenerator() {
    shutdown();
}

void ImageGenerator::ensureProcessingObjects() {
    if (!m_renderContext) m_renderContext = std::make_unique<RenderContext>();
    if (!m_imageAssembler) m_imageAssembler = std::make_unique<ImageAssembler>();
    if (!m_imageWriter) m_imageWriter = std::make_unique<ImageWriter>();
    if (!m_spritesheetAssembler) m_spritesheetAssembler = std::make_unique<SpritesheetAssembler>();
    if (!m_animationAssembler) m_animationAssembler = std::make_unique<AnimationAssembler>();
    if (!m_pipelineManager) m_pipelineManager = std::make_unique<PipelineManager>();
}

bool ImageGenerator::initialize() {
    try {
        // Register default pipelines
        registerDefaultPipelines();

        // Initialize external dependencies
        ensureProcessingObjects();

        // Try to load default pipeline if available
        if (!m_pipelineManager->isPipelineLoaded()) {
            auto availablePipelines = m_pipelineManager->getAvailablePipelines();
            std::sort(availablePipelines.begin(), availablePipelines.end());
            const auto mech = std::find(availablePipelines.begin(), availablePipelines.end(), "mech");
            if (mech != availablePipelines.end()) {
                m_pipelineManager->loadPipeline(*mech);
            } else if (!availablePipelines.empty()) {
                m_pipelineManager->loadPipeline(availablePipelines[0]);
            }
        }

        // Initialize UI
        initializeUI();

        // Background workers that service startGeneration()/startCapture()/startAnimation*()
        if (m_asyncProcessingEnabled) {
            if (!m_generationThreadRunning.exchange(true)) {
                m_generationThread = std::thread(&ImageGenerator::generationThreadFunction, this);
            }
            if (!m_animationThreadRunning.exchange(true)) {
                m_animationThread = std::thread(&ImageGenerator::animationThreadFunction, this);
            }
        }

        return true;

    } catch (const std::exception& e) {
        m_lastError = "Initialization failed: " + std::string(e.what());
        return false;
    }
}

void ImageGenerator::shutdown() {
    // Stop generation threads (stop any running job so the workers can observe the flag)
    m_state.isGenerating = false;
    m_state.isCapturing = false;
    m_animationState.isGenerating = false;
    m_animationState.isPreviewing = false;
    {
        std::lock_guard<std::mutex> lock(m_generationMutex);
        m_generationThreadRunning = false;
    }
    {
        std::lock_guard<std::mutex> lock(m_animationMutex);
        m_animationThreadRunning = false;
    }
    m_generationCV.notify_all();
    m_animationCV.notify_all();
    
    if (m_generationThread.joinable()) {
        m_generationThread.join();
    }
    
    if (m_animationThread.joinable()) {
        m_animationThread.join();
    }
    
    // Shutdown UI
    shutdownUI();
    
    // Clear caches
    clearCache();
}

// Main UI Functions
void ImageGenerator::showImageGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Image Generator", &m_state.uiParams.showWindow, 
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            const std::string imagePath = sanitizeFilename(m_state.imageParams.id) + "." +
                                          getFormatExtension(m_state.imageParams.format);
            if (ImGui::MenuItem("Save Image", "Ctrl+S")) {
                if (m_state.currentImage.image.empty()) {
                    m_state.currentImage = generateImage(m_state.imageParams);
                }
                saveImage(m_state.currentImage, imagePath);
            }
            if (ImGui::MenuItem("Load Image", "Ctrl+O")) {
                ImageBundle loaded;
                if (loadImage(imagePath, loaded)) {
                    m_state.currentImage = loaded;
                }
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_state.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Preview", nullptr, &m_state.uiParams.showPreview);
            ImGui::MenuItem("Controls", nullptr, &m_state.uiParams.showControls);
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderImageGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showSpritesheetGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Spritesheet Generator", &m_state.uiParams.showWindow,
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            const std::string sheetBase = sanitizeFilename(m_state.spritesheetParams.id) + "_sheet";
            if (ImGui::MenuItem("Save Spritesheet", "Ctrl+Shift+S")) {
                if (m_state.currentSpritesheet.combinedImage.empty()) {
                    m_state.currentSpritesheet = generateSpritesheet(m_state.spritesheetParams);
                }
                saveSpritesheet(m_state.currentSpritesheet,
                                sheetBase + "." + getFormatExtension(m_state.spritesheetParams.exportFormat));
            }
            if (ImGui::MenuItem("Export Atlas JSON", "Ctrl+E")) {
                exportAtlasJSON(m_state.currentSpritesheet, sheetBase + ".json");
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_state.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderSpritesheetGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showPreviewWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showPreview) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Preview", &m_state.uiParams.showPreview,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderPreviewUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showControlsWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_state.uiParams.showControls) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Controls", &m_state.uiParams.showControls,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderControlsUI(imgui);
    
    ImGui::End();
}

// NEW: Animation UI Functions
void ImageGenerator::showAnimationGeneratorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_animationState.uiParams.showWindow) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Animation Generator", &m_animationState.uiParams.showWindow,
                 ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_MenuBar);
    
    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            const std::string animBase = sanitizeAnimationFilename(m_animationState.animationParams.id);
            if (ImGui::MenuItem("Save Animation", "Ctrl+Shift+A")) {
                saveAnimation(m_animationState.currentAnimation, animBase + ".animation");
            }
            if (ImGui::MenuItem("Export Starbound Animation", "Ctrl+E")) {
                exportStarboundAnimation(m_animationState.animationParams, animBase + ".animation");
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                m_animationState.uiParams.showWindow = false;
            }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Timeline Editor", nullptr, &m_animationState.showTimelineEditor);
            ImGui::MenuItem("Preview", nullptr, &m_animationState.showPreview);
            ImGui::MenuItem("Controls", nullptr, &m_animationState.showControls);
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }
    
    // Main content
    renderAnimationGeneratorUI(imgui);
    
    ImGui::End();
}

void ImageGenerator::showTimelineEditorWindow(ImGuiContext* imgui, RenderContext& renderCtx) {
    if (!m_animationState.showTimelineEditor) return;
    
    ImGui::SetCurrentContext(imgui);
    
    ImGui::Begin("Timeline Editor", &m_animationState.showTimelineEditor,
                 ImGuiWindowFlags_AlwaysAutoResize);
    
    renderTimelineEditorUI(imgui);
    
    ImGui::End();
}

// UI Rendering Functions
void ImageGenerator::renderImageGeneratorUI(ImGuiContext* imgui) {
    // Shared between the configuration and spritesheet sections
    static char filename[64] = "mech_snapshot";
    static int formatIdx = 0;
    const char* formats[] = { "PNG", "JPG", "BMP", "TGA", "HDR" };
    static bool lastSaveOk = true;

    // Configuration section
    if (ImGui::CollapsingHeader("Configuration", ImGuiTreeNodeFlags_DefaultOpen)) {
        // Image parameters
        ImGui::Text("Image Settings");
        ImGui::Separator();

        ImGui::InputText("Filename", filename, sizeof(filename));

        static int resX = 512, resY = 512;
        ImGui::InputInt("Resolution X", &resX);
        ImGui::InputInt("Resolution Y", &resY);

        ImGui::Combo("Format", &formatIdx, formats, IM_ARRAYSIZE(formats));
        
        static int qualityIdx = 3; // HIGH
        const char* qualities[] = { "Ultra Low", "Low", "Medium", "High", "Ultra High" };
        ImGui::Combo("Quality", &qualityIdx, qualities, IM_ARRAYSIZE(qualities));
        
        // Update state
        m_state.imageParams.id = filename;
        m_state.imageParams.width = resX;
        m_state.imageParams.height = resY;
        m_state.imageParams.format = static_cast<ImageFormat>(formatIdx);
        m_state.imageParams.quality = static_cast<ImageQuality>(qualityIdx);
        
        // Export controls
        ImGui::Text("Export Controls");
        ImGui::Separator();
        
        if (ImGui::Button("Save Image")) {
            m_state.currentImage = generateImage(m_state.imageParams);
            const std::string path = sanitizeFilename(filename) + "." + getFormatExtension(m_state.imageParams.format);
            lastSaveOk = saveImage(m_state.currentImage, path);
            ImGui::OpenPopup("Save Image");
        }

        if (ImGui::BeginPopupModal("Save Image", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
            if (lastSaveOk) {
                ImGui::Text("Image saved successfully!");
            } else {
                ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "Save failed: %s", m_lastError.c_str());
            }
            if (ImGui::Button("OK")) {
                ImGui::CloseCurrentPopup();
            }
            ImGui::EndPopup();
        }
    }
    
    // Spritesheet section
    if (ImGui::CollapsingHeader("Spritesheet", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Spritesheet Settings");
        ImGui::Separator();
        
        static int cols = 4, rows = 3;
        ImGui::InputInt("Columns", &cols);
        ImGui::InputInt("Rows", &rows);
        
        static int tileW = 256, tileH = 256;
        ImGui::InputInt("Tile Width", &tileW);
        ImGui::InputInt("Tile Height", &tileH);
        
        static int padding = 2;
        ImGui::InputInt("Padding", &padding);
        
        // Update state
        m_state.spritesheetParams.columns = cols;
        m_state.spritesheetParams.rows = rows;
        m_state.spritesheetParams.tileWidth = tileW;
        m_state.spritesheetParams.tileHeight = tileH;
        m_state.spritesheetParams.padding = padding;
        
        if (ImGui::Button("Generate Spritesheet")) {
            startGeneration();
        }
        
        // Status display
        if (m_state.isGenerating) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Generating spritesheet... %.1f%%", 
                              m_state.generationProgress * 100.0f);
            
            ImGui::ProgressBar(m_state.generationProgress);
        } else if (!m_lastError.empty()) {
            ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), 
                              "Error: %s", m_lastError.c_str());
        } else if (!m_state.currentSpritesheet.combinedImage.empty()) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f),
                              "Spritesheet ready (%dx%d) - save as %s_sheet.%s",
                              m_state.currentSpritesheet.combinedImage.width,
                              m_state.currentSpritesheet.combinedImage.height,
                              filename, getFormatExtension(static_cast<ImageFormat>(formatIdx)).c_str());
            if (ImGui::Button("Save Spritesheet")) {
                saveSpritesheet(m_state.currentSpritesheet,
                                sanitizeFilename(filename) + "_sheet." + getFormatExtension(static_cast<ImageFormat>(formatIdx)));
            }
        }
    }
    
    // Status bar
    renderStatusBar(imgui);
}

void ImageGenerator::renderSpritesheetGeneratorUI(ImGuiContext* imgui) {
    // Spritesheet configuration
    ImGui::Text("Spritesheet Configuration");
    ImGui::Separator();
    
    static int cols = 4, rows = 3;
    ImGui::InputInt("Columns", &cols);
    ImGui::InputInt("Rows", &rows);
    
    static int tileW = 256, tileH = 256;
    ImGui::InputInt("Tile Width", &tileW);
    ImGui::InputInt("Tile Height", &tileH);
    
    static int padding = 2;
    ImGui::InputInt("Padding", &padding);
    
    // Layout options
    static int layoutIdx = 0;
    const char* layouts[] = { "Grid", "Horizontal", "Vertical", "Custom" };
    ImGui::Combo("Layout", &layoutIdx, layouts, IM_ARRAYSIZE(layouts));
    
    // Padding style
    static int paddingStyleIdx = 2; // TRANSPARENT
    const char* paddingStyles[] = { "None", "Solid", "Transparent", "Pattern", "Gradient" };
    ImGui::Combo("Padding Style", &paddingStyleIdx, paddingStyles, IM_ARRAYSIZE(paddingStyles));
    
    // Update state
    m_state.spritesheetParams.columns = cols;
    m_state.spritesheetParams.rows = rows;
    m_state.spritesheetParams.tileWidth = tileW;
    m_state.spritesheetParams.tileHeight = tileH;
    m_state.spritesheetParams.padding = padding;
    m_state.spritesheetParams.layout = static_cast<SpritesheetLayout>(layoutIdx);
    m_state.spritesheetParams.paddingStyle = static_cast<PaddingStyle>(paddingStyleIdx);
    
    // Generate button
    if (ImGui::Button("Generate Spritesheet", ImVec2(200, 30))) {
        startGeneration();
    }
    
    // Progress and status
    if (m_state.isGenerating) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                          "Generating spritesheet... %.1f%%", 
                          m_state.generationProgress * 100.0f);
        
        ImGui::ProgressBar(m_state.generationProgress);
    }
    
    // Results
    if (!m_state.currentSpritesheet.individualFrames.empty()) {
        ImGui::Text("Generated %zu frames", m_state.currentSpritesheet.individualFrames.size());
        ImGui::Text("Spritesheet size: %dx%d", 
                   m_state.spritesheetParams.columns * m_state.spritesheetParams.tileWidth + 
                   (m_state.spritesheetParams.columns + 1) * m_state.spritesheetParams.padding,
                   m_state.spritesheetParams.rows * m_state.spritesheetParams.tileHeight + 
                   (m_state.spritesheetParams.rows + 1) * m_state.spritesheetParams.padding);
    }
}

void ImageGenerator::renderPreviewUI(ImGuiContext* imgui) {
    // Preview area
    ImGui::Text("Preview");
    ImGui::Separator();
    
    static float previewScale = 1.0f;

    // Preview of the current image (or the current spritesheet when no image exists)
    ImVec2 previewSize(400, 300);
    ImGui::BeginChild("PreviewArea", previewSize, true, ImGuiWindowFlags_NoScrollbar);

    ImVec2 minPos = ImGui::GetWindowPos();
    ImVec2 maxPos = ImVec2(minPos.x + previewSize.x, minPos.y + previewSize.y);
    ImDrawList* drawList = ImGui::GetWindowDrawList();
    drawList->AddRectFilled(minPos, maxPos, IM_COL32(50, 50, 50, 255));

    const ImageData& shown = !m_state.currentImage.image.empty() ? m_state.currentImage.image
                                                                 : m_state.currentSpritesheet.combinedImage;
    if (!shown.empty()) {
        drawImagePreview(drawList, shown, minPos, previewSize, previewScale, 0, 0, shown.width, shown.height);
        const std::string info = std::to_string(shown.width) + "x" + std::to_string(shown.height);
        drawList->AddText(ImVec2(minPos.x + 10, minPos.y + 10), IM_COL32(255, 255, 255, 255), info.c_str());
    } else {
        drawList->AddText(ImVec2(minPos.x + 10, minPos.y + 10), IM_COL32(255, 255, 255, 255),
                          "Nothing generated yet");
    }

    ImGui::EndChild();

    // Preview controls
    ImGui::Text("Preview Controls");
    ImGui::Separator();

    ImGui::SliderFloat("Scale", &previewScale, 0.1f, 3.0f, "%.2f");
    m_state.uiParams.previewScale = previewScale;
    
    static bool enableZoom = true;
    ImGui::Checkbox("Enable Zoom", &enableZoom);
    
    static bool enablePan = true;
    ImGui::Checkbox("Enable Pan", &enablePan);
}

void ImageGenerator::renderControlsUI(ImGuiContext* imgui) {
    // Generation controls
    ImGui::Text("Generation Controls");
    ImGui::Separator();
    
    if (ImGui::Button("Start Generation")) {
        startGeneration();
    }
    
    if (ImGui::Button("Stop Generation")) {
        stopGeneration();
    }
    
    ImGui::SameLine();
    
    if (ImGui::Button("Clear Cache")) {
        clearCache();
    }
    
    // Processing settings
    ImGui::Text("Processing Settings");
    ImGui::Separator();
    
    static int processingQuality = m_processingQuality;
    if (ImGui::SliderInt("Processing Quality", &processingQuality, 1, 5)) {
        setProcessingQuality(processingQuality);
    }
    
    static float compressionQuality = m_compressionQuality;
    if (ImGui::SliderFloat("Compression Quality", &compressionQuality, 0.0f, 1.0f, "%.2f")) {
        setCompressionQuality(compressionQuality);
    }
    
    static bool gpuAcceleration = m_gpuAccelerationEnabled;
    if (ImGui::Checkbox("GPU Acceleration", &gpuAcceleration)) {
        setGPUAcceleration(gpuAcceleration);
    }
    
    static bool asyncProcessing = m_asyncProcessingEnabled;
    if (ImGui::Checkbox("Async Processing", &asyncProcessing)) {
        setAsyncProcessing(asyncProcessing);
    }
    
    // Performance metrics
    ImGui::Text("Performance Metrics");
    ImGui::Separator();
    
    ImGui::Text("Total Generations: %llu", m_performanceMetrics.totalGenerations.load());
    ImGui::Text("Cache Hit Rate: %.2f%%", m_performanceMetrics.getCacheHitRate() * 100.0);
    ImGui::Text("Average Generation Time: %.2f ms", m_performanceMetrics.getAverageGenerationTime());
    ImGui::Text("Peak Memory Usage: %llu MB", m_performanceMetrics.peakMemoryUsage.load() / (1024 * 1024));
    ImGui::Text("Active Generators: %llu", m_performanceMetrics.activeGenerators.load());
}

void ImageGenerator::renderStatusBar(ImGuiContext* imgui) {
    ImGui::Separator();
    
    // Status information
    std::string statusText;
    if (m_state.isGenerating) {
        statusText = "Generating...";
    } else if (m_state.isCapturing) {
        statusText = "Capturing...";
    } else if (!m_lastError.empty()) {
        statusText = "Error: " + m_lastError;
    } else {
        statusText = "Ready";
    }
    
    ImGui::TextColored(ImVec4(0.8f, 0.8f, 0.8f, 1.0f), "%s", statusText.c_str());
    
    // Performance info
    ImGui::SameLine(ImGui::GetWindowWidth() - 200);
    ImGui::Text("Cache: %zu items", getCacheSize());
}

// Generation Control Functions
void ImageGenerator::startGeneration() {
    if (m_state.isGenerating) return;
    
    m_state.isGenerating = true;
    m_state.generationProgress = 0.0f;
    m_generationCV.notify_one();
}

void ImageGenerator::stopGeneration() {
    m_state.isGenerating = false;
    m_state.generationProgress = 0.0f;
}

void ImageGenerator::startCapture() {
    if (m_state.isCapturing) return;
    
    m_state.isCapturing = true;
    m_generationCV.notify_one();
}

void ImageGenerator::stopCapture() {
    m_state.isCapturing = false;
}

// Main Processing Functions
ImageBundle ImageGenerator::generateImage(const ImageParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        ImageBundle cachedBundle;
        if (m_cachingEnabled && getCachedImage(hash, cachedBundle)) {
            m_performanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_performanceMetrics.cacheMisses++;
        m_performanceMetrics.activeGenerators++;
        
        // Generate image
        ImageBundle bundle = processImageGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheImage(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return ImageBundle{};
    }
}

SpritesheetBundle ImageGenerator::generateSpritesheet(const SpritesheetParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        SpritesheetBundle cachedBundle;
        if (m_cachingEnabled && getCachedSpritesheet(hash, cachedBundle)) {
            m_performanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_performanceMetrics.cacheMisses++;
        m_performanceMetrics.activeGenerators++;
        
        // Generate spritesheet
        SpritesheetBundle bundle = processSpritesheetGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheSpritesheet(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return SpritesheetBundle{};
    }
}

ImageBundle ImageGenerator::captureFrame(const CaptureParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        m_performanceMetrics.activeGenerators++;
        
        // Capture frame
        ImageBundle bundle = processFrameCapture(params);
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_performanceMetrics.totalGenerations++;
        m_performanceMetrics.totalGenerationTime += duration.count();
        m_performanceMetrics.activeGenerators--;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_performanceMetrics.activeGenerators--;
        return ImageBundle{};
    }
}

// Processing Helper Functions
ImageBundle ImageGenerator::processImageGeneration(const ImageParams& params) {
    ensureProcessingObjects();

    // Render the current pipeline state into an offscreen target of the requested size.
    CaptureParams capture;
    capture.id = params.id;
    capture.width = params.width;
    capture.height = params.height;
    capture.enableHDR = params.enableHDR;
    capture.exposure = params.exposure;
    capture.gamma = params.gamma;
    capture.gpuAccelerated = params.enableGPUAcceleration && m_gpuAccelerationEnabled;
    capture.clearColor = params.enableAlpha ? glm::vec4(0.0f) : glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);

    ImageBundle bundle = captureWithContext(*m_renderContext, capture);

    // Exposure / gamma for HDR output
    if (params.enableHDR && (params.exposure != 1.0f || params.gamma != 2.2f)) {
        const float invGamma = params.gamma > 0.0f ? (2.2f / params.gamma) : 1.0f;
        const int c = bundle.image.channels;
        for (size_t i = 0; i < bundle.image.data.size(); ++i) {
            if (c == 4 && (i % 4) == 3) continue;  // leave alpha untouched
            const float v = static_cast<float>(bundle.image.data[i]) / 255.0f;
            bundle.image.data[i] = toByte(std::pow(std::clamp(v * params.exposure, 0.0f, 1.0f), invGamma));
        }
    }

    // Drop the alpha channel when it is not wanted
    if (!params.enableAlpha && bundle.image.channels == 4) {
        ImageData rgb;
        rgb.handle = bundle.image.handle;
        rgb.allocate(bundle.image.width, bundle.image.height, 3);
        const size_t pixels = static_cast<size_t>(rgb.width) * rgb.height;
        for (size_t p = 0; p < pixels; ++p) {
            rgb.data[p * 3 + 0] = bundle.image.data[p * 4 + 0];
            rgb.data[p * 3 + 1] = bundle.image.data[p * 4 + 1];
            rgb.data[p * 3 + 2] = bundle.image.data[p * 4 + 2];
        }
        bundle.image = std::move(rgb);
    }

    // Create metadata
    bundle.metadata.id = params.id;
    bundle.metadata.title = "Generated Image";
    bundle.metadata.description = "Generated by MagiTech Image Generator";
    bundle.metadata.author = "MagiTech";
    bundle.metadata.version = "1.0.0";
    bundle.metadata.creationTime = std::chrono::system_clock::now();
    bundle.metadata.width = bundle.image.width;
    bundle.metadata.height = bundle.image.height;
    bundle.metadata.format = params.format;
    bundle.metadata.compression = params.compressionType;
    bundle.metadata.fileSize = bundle.image.byteSize();
    bundle.metadata.checksum = checksumHex(bundle.image.data);
    bundle.memoryUsage = bundle.image.byteSize();

    return bundle;
}

SpritesheetBundle ImageGenerator::processSpritesheetGeneration(const SpritesheetParams& params) {
    ensureProcessingObjects();

    int cols = std::max(1, params.columns);
    int rows = std::max(1, params.rows);
    const int totalFrames = cols * rows;
    switch (params.layout) {
        case SpritesheetLayout::HORIZONTAL: cols = totalFrames; rows = 1; break;
        case SpritesheetLayout::VERTICAL:   cols = 1; rows = totalFrames; break;
        case SpritesheetLayout::GRID:
        case SpritesheetLayout::CUSTOM:     break;
    }

    int padding = std::max(0, params.padding);
    glm::vec4 background = params.backgroundColor;
    switch (params.paddingStyle) {
        case PaddingStyle::NONE:        padding = 0; break;
        case PaddingStyle::TRANSPARENT: background = glm::vec4(0.0f); break;
        case PaddingStyle::SOLID:       background = params.paddingColor; break;
        case PaddingStyle::PATTERN:
        case PaddingStyle::GRADIENT:    break;
    }

    // Capture one tile per cell from the active pipeline, stepping its animation clock.
    IPipeline* pipeline = m_pipelineManager ? m_pipelineManager->getCurrentPipeline() : nullptr;
    const float frameDuration = params.frameRate > 0.0f ? 1.0f / params.frameRate : 0.0f;
    std::vector<ImageBundle> tiles;
    tiles.reserve(static_cast<size_t>(totalFrames));
    for (int i = 0; i < totalFrames; ++i) {
        if (pipeline) {
            pipeline->SetAnimTime(i * frameDuration);
        }
        CaptureParams capture = m_state.captureParams;
        capture.id = params.id + "_frame_" + std::to_string(i);
        capture.width = std::max(1, params.tileWidth);
        capture.height = std::max(1, params.tileHeight);
        capture.padding = 0;
        capture.clearColor = glm::vec4(0.0f);
        ImageBundle tile = captureWithContext(*m_renderContext, capture);
        tile.metadata.frameIndex = i;
        tile.metadata.timestamp = i * frameDuration;
        tiles.push_back(std::move(tile));
        updateGenerationProgress(static_cast<float>(i + 1) / static_cast<float>(totalFrames));
    }

    SpritesheetBundle bundle = m_spritesheetAssembler->assemble(
        tiles, cols, rows, params.tileWidth, params.tileHeight, padding, background,
        params.frameRate, params.enableLooping, params.animationName);

    // Patterned / gradient padding: paint the gutters between cells
    if (padding > 0 && (params.paddingStyle == PaddingStyle::PATTERN || params.paddingStyle == PaddingStyle::GRADIENT)) {
        ImageData& img = bundle.combinedImage;
        const int cellW = bundle.tileWidth + padding;
        const int cellH = bundle.tileHeight + padding;
        for (int y = 0; y < img.height; ++y) {
            for (int x = 0; x < img.width; ++x) {
                const bool inGutter = (x % cellW) >= bundle.tileWidth || (y % cellH) >= bundle.tileHeight;
                if (!inGutter) continue;
                glm::vec4 color;
                if (params.paddingStyle == PaddingStyle::PATTERN) {
                    color = (((x / 2) + (y / 2)) % 2 == 0) ? params.paddingColor : params.backgroundColor;
                } else {
                    const float t = img.height > 1 ? static_cast<float>(y) / static_cast<float>(img.height - 1) : 0.0f;
                    color = params.paddingColor + (params.backgroundColor - params.paddingColor) * t;
                }
                uint8_t* px = &img.data[(static_cast<size_t>(y) * img.width + x) * 4];
                px[0] = toByte(color.r); px[1] = toByte(color.g); px[2] = toByte(color.b); px[3] = toByte(color.a);
            }
        }
    }

    // Create atlas metadata
    bundle.atlasMetadata.id = params.id;
    bundle.atlasMetadata.name = "Generated Spritesheet";
    bundle.atlasMetadata.description = "Generated by MagiTech Image Generator";

    return bundle;
}

ImageBundle ImageGenerator::processFrameCapture(const CaptureParams& params) {
    ensureProcessingObjects();
    return captureWithContext(*m_renderContext, params);
}

ImageBundle ImageGenerator::captureWithContext(RenderContext& ctx, const CaptureParams& params) {
    ensureProcessingObjects();

    const int width = std::max(1, params.width);
    const int height = std::max(1, params.height);

    // Prepare the render target and read it back
    ctx.resize(width, height);
    ctx.clear(params.clearColor);

    ImageBundle bundle;
    bundle.image = ctx.readPixels();
    if (params.padding > 0) {
        bundle.image = m_imageAssembler->addPadding(bundle.image, params.padding, glm::vec4(0.0f));
    }
    bundle.texture = allocateImageHandle();
    bundle.framebuffer = ctx.framebufferHandle();
    bundle.gpuAccelerated = params.gpuAccelerated && m_gpuAccelerationEnabled;
    if (bundle.gpuAccelerated) {
        m_performanceMetrics.gpuGenerations++;
    }

    // Create metadata
    bundle.metadata.id = params.id;
    bundle.metadata.title = "Captured Frame";
    bundle.metadata.description = "Captured by MagiTech Image Generator";
    bundle.metadata.author = "MagiTech";
    bundle.metadata.version = "1.0.0";
    bundle.metadata.creationTime = std::chrono::system_clock::now();
    bundle.metadata.width = bundle.image.width;
    bundle.metadata.height = bundle.image.height;
    bundle.metadata.format = ImageFormat::PNG;
    bundle.metadata.compression = ImageCompression::NONE;
    bundle.metadata.fileSize = bundle.image.byteSize();
    bundle.metadata.checksum = checksumHex(bundle.image.data);
    bundle.memoryUsage = bundle.image.byteSize();

    return bundle;
}

// Threading Functions
void ImageGenerator::generationThreadFunction() {
    while (m_generationThreadRunning) {
        std::unique_lock<std::mutex> lock(m_generationMutex);
        m_generationCV.wait(lock, [this] { 
            return !m_generationThreadRunning || m_state.isGenerating || m_state.isCapturing; 
        });
        
        if (!m_generationThreadRunning) break;
        
        if (m_state.isGenerating) {
            processAsyncGeneration();
        }
        
        if (m_state.isCapturing) {
            processAsyncCapture();
        }
    }
}

void ImageGenerator::processAsyncGeneration() {
    try {
        // Simulate generation progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_state.isGenerating) break;
            
            m_state.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
        
        // Generate spritesheet
        SpritesheetBundle bundle = generateSpritesheet(m_state.spritesheetParams);
        m_state.currentSpritesheet = bundle;
        
        m_state.isGenerating = false;
        m_state.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_state.isGenerating = false;
        m_state.generationProgress = 0.0f;
    }
}

void ImageGenerator::processAsyncCapture() {
    try {
        // Simulate capture progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_state.isCapturing) break;
            
            m_state.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        
        // Capture frame
        ImageBundle bundle = captureFrame(m_state.captureParams);
        m_state.currentImage = bundle;
        
        m_state.isCapturing = false;
        m_state.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleGenerationError(e.what());
        m_state.isCapturing = false;
        m_state.generationProgress = 0.0f;
    }
}

// Cache Functions
bool ImageGenerator::getCachedImage(uint64_t hash, ImageBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_imageCache.find(hash);
    if (it != m_imageCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

bool ImageGenerator::getCachedSpritesheet(uint64_t hash, SpritesheetBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_spritesheetCache.find(hash);
    if (it != m_spritesheetCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

void ImageGenerator::cacheImage(uint64_t hash, const ImageBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_imageCache.size() >= MAX_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_imageCache.erase(m_imageCache.begin());
    }
    
    m_imageCache[hash] = bundle;
}

void ImageGenerator::cacheSpritesheet(uint64_t hash, const SpritesheetBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_spritesheetCache.size() >= MAX_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_spritesheetCache.erase(m_spritesheetCache.begin());
    }
    
    m_spritesheetCache[hash] = bundle;
}

// Configuration Functions
void ImageGenerator::setProcessingQuality(int quality) {
    m_processingQuality = std::clamp(quality, 1, 5);
}

void ImageGenerator::setCompressionQuality(float quality) {
    m_compressionQuality = std::clamp(quality, 0.0f, 1.0f);
}

void ImageGenerator::setGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void ImageGenerator::setAsyncProcessing(bool enable) {
    m_asyncProcessingEnabled = enable;
}

void ImageGenerator::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = std::clamp(threads, 1, static_cast<int>(MAX_THREADS));
}

void ImageGenerator::enableCaching(bool enable) {
    m_cachingEnabled = enable;
}

void ImageGenerator::clearCache() {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    m_imageCache.clear();
    m_spritesheetCache.clear();
}

size_t ImageGenerator::getCacheSize() const {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    return m_imageCache.size() + m_spritesheetCache.size();
}

void ImageGenerator::enableHotReload(bool enable) {
    m_hotReloadEnabled = enable;
}

void ImageGenerator::reloadConfiguration() {
    // Re-apply the last pipeline configuration file that was saved or loaded.
    if (m_pipelineConfigPath.empty()) {
        return;
    }
    std::error_code ec;
    if (!std::filesystem::exists(m_pipelineConfigPath, ec)) {
        m_lastError = "Pipeline configuration not found: " + m_pipelineConfigPath;
        return;
    }
    if (!loadPipelineConfig(m_pipelineConfigPath)) {
        m_lastError = "Failed to reload pipeline configuration: " + m_pipelineConfigPath;
        return;
    }
    clearCache();  // cached results were produced with the old configuration
    MagiTech::Log::info("ImageGenerator", "Reloaded pipeline configuration from {}", m_pipelineConfigPath);
}

// Utility Functions
std::string ImageGenerator::getFormatExtension(ImageFormat format) const {
    switch (format) {
        case ImageFormat::PNG: return "png";
        case ImageFormat::JPG: return "jpg";
        case ImageFormat::BMP: return "bmp";
        case ImageFormat::TGA: return "tga";
        case ImageFormat::HDR: return "hdr";
        default: return "png";
    }
}

std::string ImageGenerator::getCompressionName(ImageCompression compression) const {
    switch (compression) {
        case ImageCompression::NONE: return "None";
        case ImageCompression::LOSSY: return "Lossy";
        case ImageCompression::LOSSLESS: return "Lossless";
        case ImageCompression::BC1: return "BC1";
        case ImageCompression::BC3: return "BC3";
        case ImageCompression::BC7: return "BC7";
        case ImageCompression::ASTC_4x4: return "ASTC 4x4";
        case ImageCompression::ASTC_8x8: return "ASTC 8x8";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getQualityName(ImageQuality quality) const {
    switch (quality) {
        case ImageQuality::ULTRA_LOW: return "Ultra Low";
        case ImageQuality::LOW: return "Low";
        case ImageQuality::MEDIUM: return "Medium";
        case ImageQuality::HIGH: return "High";
        case ImageQuality::ULTRA_HIGH: return "Ultra High";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getLayoutName(SpritesheetLayout layout) const {
    switch (layout) {
        case SpritesheetLayout::GRID: return "Grid";
        case SpritesheetLayout::HORIZONTAL: return "Horizontal";
        case SpritesheetLayout::VERTICAL: return "Vertical";
        case SpritesheetLayout::CUSTOM: return "Custom";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getPaddingStyleName(PaddingStyle style) const {
    switch (style) {
        case PaddingStyle::NONE: return "None";
        case PaddingStyle::SOLID: return "Solid";
        case PaddingStyle::TRANSPARENT: return "Transparent";
        case PaddingStyle::PATTERN: return "Pattern";
        case PaddingStyle::GRADIENT: return "Gradient";
        default: return "Unknown";
    }
}

// Error Handling Functions
void ImageGenerator::handleGenerationError(const std::string& error) {
    m_lastError = error;
    m_state.isGenerating = false;
    m_state.isCapturing = false;
    m_state.generationProgress = 0.0f;
}

// UI Helper Functions
void ImageGenerator::initializeUI() {
    // The ImGui context is owned by the host and passed into each show*Window call;
    // here we only reset the generator's own window/progress state.
    m_state.uiParams.showWindow = true;
    m_state.showImageGenerator = true;
    m_state.showSpritesheetGenerator = true;
    m_state.showPreview = m_state.uiParams.showPreview;
    m_state.showControls = m_state.uiParams.showControls;
    m_state.generationProgress = 0.0f;
    m_state.lastUpdate = std::chrono::system_clock::now();

    m_animationState.uiParams.showWindow = true;
    m_animationState.generationProgress = 0.0f;
    m_animationState.previewTime = 0.0f;
    m_animationState.lastUpdate = std::chrono::system_clock::now();
}

void ImageGenerator::shutdownUI() {
    // Close all generator windows so nothing is drawn after shutdown.
    m_state.uiParams.showWindow = false;
    m_state.uiParams.showPreview = false;
    m_state.uiParams.showControls = false;
    m_state.showImageGenerator = false;
    m_state.showSpritesheetGenerator = false;
    m_animationState.uiParams.showWindow = false;
    m_animationState.showTimelineEditor = false;
    m_animationState.showPreview = false;
    m_animationState.showControls = false;
}

void ImageGenerator::updateGenerationProgress(float progress) {
    m_state.generationProgress = std::clamp(progress, 0.0f, 1.0f);
}

// Validation Functions
bool ImageGenerator::validateImageDimensions(int width, int height) {
    return width > 0 && height > 0 && width <= 8192 && height <= 8192;
}

bool ImageGenerator::validateSpritesheetDimensions(int cols, int rows, int tileW, int tileH) {
    return cols > 0 && rows > 0 && tileW > 0 && tileH > 0 &&
           cols * tileW <= 8192 && rows * tileH <= 8192;
}

bool ImageGenerator::validateFilePaths(const std::string& filePath) {
    return !filePath.empty() && filePath.length() < 1024;
}

// Utility Helper Functions
std::string ImageGenerator::generateUniqueID() const {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    return "img_" + std::to_string(millis);
}

std::string ImageGenerator::sanitizeFilename(const std::string& filename) const {
    std::string sanitized = filename;
    const std::string invalidChars = "<>:\"|?*";
    
    for (char& c : sanitized) {
        if (invalidChars.find(c) != std::string::npos) {
            c = '_';
        }
    }
    
    return sanitized;
}

std::string ImageGenerator::getTimestampString() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
    return oss.str();
}

// Performance Helper Functions
void ImageGenerator::updatePerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage) {
    m_performanceMetrics.totalGenerationTime += generationTime;
    m_performanceMetrics.peakMemoryUsage = std::max(m_performanceMetrics.peakMemoryUsage.load(), memoryUsage);
}

void ImageGenerator::logPerformanceMetrics() {
    MagiTech::Log::info("ImageGenerator",
                        "generations={} cacheHitRate={:.2f}% avgTime={:.2f}us peakMemory={}B active={} gpu={}",
                        m_performanceMetrics.totalGenerations.load(),
                        m_performanceMetrics.getCacheHitRate() * 100.0,
                        m_performanceMetrics.getAverageGenerationTime(),
                        m_performanceMetrics.peakMemoryUsage.load(),
                        m_performanceMetrics.activeGenerators.load(),
                        m_performanceMetrics.gpuGenerations.load());
}

// Quality Assessment Functions
ImageQualityMetrics ImageGenerator::assessImageQuality(const ImageBundle& bundle) {
    ImageQualityMetrics metrics;
    const ImageData& img = bundle.image;
    if (img.empty() || img.channels < 1) {
        return metrics;
    }

    // Luminance plane (0..1)
    const int w = img.width;
    const int h = img.height;
    const int c = img.channels;
    std::vector<float> lum(static_cast<size_t>(w) * h);
    for (size_t p = 0; p < lum.size(); ++p) {
        const uint8_t* px = &img.data[p * c];
        const float l = (c >= 3) ? (0.2126f * px[0] + 0.7152f * px[1] + 0.0722f * px[2]) : static_cast<float>(px[0]);
        lum[p] = l / 255.0f;
    }

    double sum = 0.0, sumSq = 0.0;
    float peak = 0.0f;
    for (float l : lum) {
        sum += l;
        sumSq += static_cast<double>(l) * l;
        peak = std::max(peak, l);
    }
    const double n = static_cast<double>(lum.size());
    const double mean = sum / n;
    const double variance = std::max(0.0, sumSq / n - mean * mean);
    metrics.peakBrightness = peak;
    metrics.averageBrightness = static_cast<float>(mean);
    metrics.contrast = static_cast<float>(std::min(1.0, 2.0 * std::sqrt(variance)));

    if (w >= 3 && h >= 3) {
        // Sharpness: mean gradient magnitude; noise: mean |Laplacian| residual
        double gradSum = 0.0, lapSum = 0.0;
        // Blockiness at 8x8 boundaries vs. inside blocks (JPEG-style artifacts)
        double blockEdge = 0.0, blockInner = 0.0;
        size_t blockEdgeCount = 0, blockInnerCount = 0;
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                const size_t i = static_cast<size_t>(y) * w + x;
                const float gx = lum[i + 1] - lum[i - 1];
                const float gy = lum[i + w] - lum[i - w];
                gradSum += std::sqrt(gx * gx + gy * gy);
                const float lap = lum[i - 1] + lum[i + 1] + lum[i - w] + lum[i + w] - 4.0f * lum[i];
                lapSum += std::fabs(lap);
                const float dx = std::fabs(lum[i + 1] - lum[i]);
                if ((x % 8) == 7) { blockEdge += dx; ++blockEdgeCount; }
                else { blockInner += dx; ++blockInnerCount; }
            }
        }
        const double interior = static_cast<double>(w - 2) * (h - 2);
        metrics.sharpness = static_cast<float>(std::min(1.0, (gradSum / interior) * 4.0));
        metrics.noise = static_cast<float>(std::min(1.0, lapSum / interior));
        if (blockEdgeCount > 0 && blockInnerCount > 0) {
            const double edgeMean = blockEdge / blockEdgeCount;
            const double innerMean = blockInner / blockInnerCount;
            metrics.compressionArtifacts = static_cast<float>(std::clamp(edgeMean - innerMean, 0.0, 1.0));
        }
    }
    return metrics;
}

bool ImageGenerator::validateImageParams(const ImageParams& params, std::string& errorMessage) {
    if (!validateImageDimensions(params.width, params.height)) {
        errorMessage = "Invalid image dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Image ID cannot be empty";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateSpritesheetParams(const SpritesheetParams& params, std::string& errorMessage) {
    if (!validateSpritesheetDimensions(params.columns, params.rows, params.tileWidth, params.tileHeight)) {
        errorMessage = "Invalid spritesheet dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Spritesheet ID cannot be empty";
        return false;
    }
    
    if (params.padding < 0) {
        errorMessage = "Padding cannot be negative";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateCaptureParams(const CaptureParams& params, std::string& errorMessage) {
    if (!validateImageDimensions(params.width, params.height)) {
        errorMessage = "Invalid capture dimensions";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Capture ID cannot be empty";
        return false;
    }
    
    return true;
}

// File Operation Functions
bool ImageGenerator::saveImage(const ImageBundle& bundle, const std::string& filePath) {
    ensureProcessingObjects();
    if (!validateFilePaths(filePath)) {
        m_lastError = "Invalid image path: " + filePath;
        return false;
    }
    const ImageFormat format = ImageWriter::formatFromPath(filePath);
    if (!m_imageWriter->write(bundle.image, filePath, format, m_compressionQuality)) {
        m_lastError = m_imageWriter->lastError();
        return false;
    }
    return true;
}

bool ImageGenerator::saveSpritesheet(const SpritesheetBundle& bundle, const std::string& filePath) {
    ensureProcessingObjects();
    if (!validateFilePaths(filePath)) {
        m_lastError = "Invalid spritesheet path: " + filePath;
        return false;
    }
    const ImageFormat format = ImageWriter::formatFromPath(filePath);
    if (!m_imageWriter->write(bundle.combinedImage, filePath, format, m_compressionQuality)) {
        m_lastError = m_imageWriter->lastError();
        return false;
    }
    return true;
}

bool ImageGenerator::loadImage(const std::string& filePath, ImageBundle& bundle) {
    ensureProcessingObjects();
    ImageData image;
    if (!m_imageWriter->read(filePath, image, 4)) {
        m_lastError = m_imageWriter->lastError();
        return false;
    }
    bundle = ImageBundle{};
    bundle.image = std::move(image);
    bundle.texture = allocateImageHandle();
    bundle.metadata.id = std::filesystem::path(filePath).stem().string();
    bundle.metadata.title = bundle.metadata.id;
    bundle.metadata.source = filePath;
    bundle.metadata.creationTime = std::chrono::system_clock::now();
    bundle.metadata.width = bundle.image.width;
    bundle.metadata.height = bundle.image.height;
    bundle.metadata.format = ImageWriter::formatFromPath(filePath);
    bundle.metadata.compression = ImageCompression::NONE;
    std::error_code ec;
    const auto size = std::filesystem::file_size(filePath, ec);
    bundle.metadata.fileSize = ec ? bundle.image.byteSize() : static_cast<size_t>(size);
    bundle.metadata.checksum = checksumHex(bundle.image.data);
    bundle.memoryUsage = bundle.image.byteSize();
    bundle.creationTime = std::chrono::system_clock::now();
    return true;
}

bool ImageGenerator::loadSpritesheet(const std::string& filePath, SpritesheetBundle& bundle) {
    ensureProcessingObjects();
    ImageData image;
    if (!m_imageWriter->read(filePath, image, 4)) {
        m_lastError = m_imageWriter->lastError();
        return false;
    }
    bundle = SpritesheetBundle{};
    bundle.combinedImage = std::move(image);
    bundle.spritesheet = bundle.combinedImage.handle;
    bundle.spritesheetTexture = allocateImageHandle();
    bundle.creationTime = std::chrono::system_clock::now();
    bundle.memoryUsage = bundle.combinedImage.byteSize();

    // Atlas data written by exportAtlasJSON (same name, .json extension)
    const std::string atlasPath = replaceExtension(filePath, ".json");
    std::error_code ec;
    if (std::filesystem::exists(atlasPath, ec)) {
        try {
            std::ifstream in(atlasPath);
            nlohmann::json j;
            in >> j;
            atlasFromJson(j, bundle);
        } catch (const std::exception& e) {
            m_lastError = "Failed to parse atlas " + atlasPath + ": " + e.what();
            return false;
        }
    } else {
        // No atlas: treat the whole image as a single frame
        bundle.columns = 1;
        bundle.rows = 1;
        bundle.tileWidth = bundle.combinedImage.width;
        bundle.tileHeight = bundle.combinedImage.height;
        bundle.frameBounds.emplace_back(0.0f, 0.0f, static_cast<float>(bundle.tileWidth), static_cast<float>(bundle.tileHeight));
        AtlasMetadata::FrameInfo info;
        info.name = "frame_0";
        info.x = 0;
        info.y = 0;
        info.width = bundle.tileWidth;
        info.height = bundle.tileHeight;
        info.duration = 0.0f;
        bundle.atlasMetadata.frames.push_back(info);
        bundle.atlasMetadata.frameCount = 1;
        bundle.atlasMetadata.frameRate = 0.0f;
        bundle.atlasMetadata.looping = false;
    }
    bundle.atlasMetadata.id = std::filesystem::path(filePath).stem().string();
    if (bundle.atlasMetadata.name.empty()) {
        bundle.atlasMetadata.name = bundle.atlasMetadata.id;
    }
    for (size_t i = 0; i < bundle.frameBounds.size(); ++i) {
        bundle.individualFrames.push_back(allocateImageHandle());
        bundle.individualTextures.push_back(allocateImageHandle());
    }
    return true;
}

// Export Functions
bool ImageGenerator::exportSpritesheet(const SpritesheetParams& params, const std::string& outputPath) {
    ensureProcessingObjects();
    std::string error;
    if (!validateSpritesheetParams(params, error)) {
        m_lastError = error;
        return false;
    }
    SpritesheetBundle bundle = generateSpritesheet(params);
    if (bundle.combinedImage.empty()) {
        if (m_lastError.empty()) m_lastError = "Spritesheet generation produced no image";
        return false;
    }
    if (!m_imageWriter->write(bundle.combinedImage, outputPath, params.exportFormat, params.exportQuality)) {
        m_lastError = m_imageWriter->lastError();
        return false;
    }
    if (params.enableAtlasJSON || params.enableMetadata) {
        return exportAtlasJSON(bundle, replaceExtension(outputPath, ".json"));
    }
    return true;
}

bool ImageGenerator::exportAtlasJSON(const SpritesheetBundle& bundle, const std::string& outputPath) {
    try {
        const std::string imageName = std::filesystem::path(replaceExtension(outputPath, ".png")).filename().string();
        const nlohmann::json j = atlasToJson(bundle, imageName);
        std::string error;
        if (!writeTextFile(outputPath, j.dump(2), error)) {
            m_lastError = error;
            return false;
        }
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Atlas export failed: " + std::string(e.what());
        return false;
    }
}

bool ImageGenerator::exportIndividualFrames(const SpritesheetBundle& bundle, const std::string& outputDir) {
    ensureProcessingObjects();
    if (bundle.combinedImage.empty()) {
        m_lastError = "Spritesheet has no image data to export";
        return false;
    }
    std::error_code ec;
    std::filesystem::create_directories(outputDir, ec);
    const std::string baseName = sanitizeFilename(bundle.atlasMetadata.id.empty() ? std::string("frame") : bundle.atlasMetadata.id);
    for (size_t i = 0; i < bundle.frameBounds.size(); ++i) {
        const glm::vec4& b = bundle.frameBounds[i];
        const ImageData frame = m_imageAssembler->crop(bundle.combinedImage,
                                                       static_cast<int>(b.x), static_cast<int>(b.y),
                                                       static_cast<int>(b.z), static_cast<int>(b.w));
        const std::string name = (i < bundle.atlasMetadata.frames.size() && !bundle.atlasMetadata.frames[i].name.empty())
                                     ? sanitizeFilename(bundle.atlasMetadata.frames[i].name)
                                     : baseName + "_" + std::to_string(i);
        const std::string path = (std::filesystem::path(outputDir) / (name + ".png")).string();
        if (!m_imageWriter->write(frame, path, ImageFormat::PNG)) {
            m_lastError = m_imageWriter->lastError();
            return false;
        }
    }
    return true;
}

// NEW: Animation UI Rendering Functions
void ImageGenerator::renderAnimationGeneratorUI(ImGuiContext* imgui) {
    // Enhanced Animation UI with requested layout
    ImGui::Columns(3, "AnimationLayout", true);
    
    // Configuration Panel
    ImGui::BeginChild("Configuration", ImVec2(0, 0), true);
    ImGui::Text("Configuration");
    ImGui::Separator();
    
    // Mode Selector
    static int modeIdx = 1; // ANIMATED_SEQUENCE
    const char* modes[] = { "Single Frame", "Animated Sequence" };
    ImGui::Text("Mode Selector");
    ImGui::Combo("Mode", &modeIdx, modes, IM_ARRAYSIZE(modes));
    
    // Frame Settings
    ImGui::Text("Frame Settings");
    static int frameCount = DEFAULT_ANIMATION_FRAME_COUNT;
    ImGui::InputInt("Frame Count", &frameCount);
    
    static float frameDuration = DEFAULT_ANIMATION_FRAME_DURATION;
    ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
    
    static int orderIdx = 0; // ROW_MAJOR
    const char* orders[] = { "Row-Major", "Column-Major" };
    ImGui::Combo("Frame Order", &orderIdx, orders, IM_ARRAYSIZE(orders));
    
    // Timeline Editor
    ImGui::Text("Timeline Editor");
    static bool useTimeline = false;
    ImGui::Checkbox("Use Timeline", &useTimeline);
    
    if (useTimeline) {
        static float timelineDuration = 1.0f;
        ImGui::InputFloat("Timeline Duration", &timelineDuration, 0.1f, 1.0f, "%.2f");
        
        // Timeline scrubber
        static float animTime = 0.0f;
        ImGui::SliderFloat("Time", &animTime, 0.0f, timelineDuration, "%.3f");
        
        // Update preview time
        m_animationState.previewTime = animTime;
        
        m_animationState.animationParams.useTimeline = true;
        m_animationState.animationParams.timelineDuration = timelineDuration;
    } else {
        m_animationState.animationParams.useTimeline = false;
    }
    
    // Update state
    m_animationState.animationParams.mode = static_cast<AnimationMode>(modeIdx);
    m_animationState.animationParams.frameCount = frameCount;
    m_animationState.animationParams.frameDuration = frameDuration;
    m_animationState.animationParams.frameOrder = static_cast<FrameOrder>(orderIdx);
    
    ImGui::EndChild();
    ImGui::NextColumn();
    
    // Preview Panel
    ImGui::BeginChild("Preview", ImVec2(0, 0), true);
    ImGui::Text("Preview");
    ImGui::Separator();
    
    // 3D Viewport placeholder
    ImGui::BeginChild("3DViewport", ImVec2(0, 200), true, ImGuiWindowFlags_NoScrollbar);
    ImGui::TextColored(ImVec4(0.7f, 0.7f, 0.7f, 1.0f), "[3D Viewport]");
    ImGui::Text("Animation Preview");
    
    // Preview controls
    if (ImGui::Button("Play", ImVec2(60, 25))) {
        startAnimationPreview();
    }
    ImGui::SameLine();
    if (ImGui::Button("Stop", ImVec2(60, 25))) {
        stopAnimationPreview();
    }
    ImGui::SameLine();
    if (ImGui::Button("Reset", ImVec2(60, 25))) {
        m_animationState.previewTime = 0.0f;
    }
    
    // Preview time display
    ImGui::Text("Time: %.3f", m_animationState.previewTime);
    
    ImGui::EndChild();
    
    // Status display
    if (m_animationState.isPreviewing) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), "Previewing...");
    }
    
    ImGui::EndChild();
    ImGui::NextColumn();
    
    // Export & Animation Panel
    ImGui::BeginChild("Export", ImVec2(0, 0), true);
    ImGui::Text("Export & Animation");
    ImGui::Separator();
    
    // Filename
    static char filename[64] = "mech_animation";
    ImGui::Text("Filename");
    ImGui::InputText("##Filename", filename, sizeof(filename));
    
    // Format options
    ImGui::Text("Format");
    static int formatIdx = 0; // PNG
    const char* formats[] = { "PNG", "JPG", "BMP", "TGA" };
    ImGui::Combo("##Format", &formatIdx, formats, IM_ARRAYSIZE(formats));
    
    // Sheet Layout
    ImGui::Text("Sheet Layout");
    static int cols = 4, rows = 3;
    ImGui::InputInt("Cols", &cols);
    ImGui::InputInt("Rows", &rows);
    
    // Tile dimensions
    ImGui::Text("Tile Dimensions");
    static int tileW = 256, tileH = 256;
    ImGui::InputInt("W", &tileW);
    ImGui::InputInt("H", &tileH);
    
    // Padding
    static int padding = 2;
    ImGui::InputInt("Padding", &padding);
    
    // Frame settings
    ImGui::Text("Frame Settings");
    ImGui::InputInt("Frame Count", &frameCount);
    ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
    
    // Mode
    ImGui::Combo("Mode", &modeIdx, modes, IM_ARRAYSIZE(modes));
    
    // Generate options
    static bool generateSheet = true;
    static bool generateJSON = true;
    ImGui::Checkbox("Generate Sheet+JSON", &generateSheet);
    ImGui::Checkbox("Generate JSON", &generateJSON);
    
    // Generate button
    if (ImGui::Button("Generate Animation Sheet", ImVec2(200, 30))) {
        // Update spritesheet params
        m_animationState.spritesheetParams.columns = cols;
        m_animationState.spritesheetParams.rows = rows;
        m_animationState.spritesheetParams.tileWidth = tileW;
        m_animationState.spritesheetParams.tileHeight = tileH;
        m_animationState.spritesheetParams.padding = padding;
        
        // Update animation params
        m_animationState.animationParams.id = filename;
        m_animationState.animationParams.frameCount = frameCount;
        m_animationState.animationParams.frameDuration = frameDuration;
        m_animationState.animationParams.mode = static_cast<AnimationMode>(modeIdx);
        m_animationState.animationParams.generateAnimationJSON = generateJSON;
        
        startAnimationGeneration();
    }
    
    // Enhanced ImGui snippet for animation controls
    if (ImGui::CollapsingHeader("Animation Controls", ImGuiTreeNodeFlags_DefaultOpen)) {
        static bool animMode = true;       // true = sequence, false = single
        ImGui::Checkbox("Sequence Mode", &animMode);
        
        if (animMode) {
            ImGui::InputInt("Frame Count", &frameCount);
            ImGui::InputFloat("Frame Duration", &frameDuration, 0.01f, 0.1f, "%.3f");
            ImGui::Combo("Order", &orderIdx, orders, IM_ARRAYSIZE(orders));
            
            // Simple timeline scrubber
            static float animTime = 0.0f;
            ImGui::SliderFloat("Time", &animTime, 0.0f, (frameCount-1)*frameDuration, "%.3f");
            m_animationState.previewTime = animTime;
            
            // Update pipeline with animation time
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline()) {
                m_pipelineManager->getCurrentPipeline()->SetAnimTime(animTime);
            }
        }
        
        if (ImGui::Button(animMode ? "Generate Animation Sheet" : "Capture Frame")) {
            // Capture tiles using enhanced function
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline() && m_renderContext) {
                auto tiles = CaptureTiles(*m_pipelineManager->getCurrentPipeline(), *m_renderContext,
                                       animMode, frameCount, frameDuration,
                                       tileW, tileH, padding, orderIdx);
                
                // Create spritesheet
                auto sheet = MakeSheet(tiles, cols, rows, tileW, tileH, padding);
                
                // Generate output filename
                const std::string baseName = sanitizeAnimationFilename(filename);
                std::string outPng = baseName + (animMode ? "_anim.png" : ".png");
                std::string outJson = baseName + ".animation";
                
                // Save spritesheet
                if (saveSpritesheet(sheet, outPng)) {
                    // Generate Starbound animation JSON
                    if (animMode && generateJSON) {
                        WriteStarboundAnimationJSON(outJson, frameCount, frameDuration, cols, rows, orderIdx);
                        
                        // Update status message
                        m_animationState.currentAnimation.spritesheet = sheet;
                        m_animationState.currentAnimation.animationJsonPath = outJson;
                        m_animationState.currentAnimation.spritesheetPath = outPng;
                    }
                }
            }
        }
    }
    
    // NEW: Pipeline Management UI
    if (ImGui::CollapsingHeader("Pipeline Management", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Dynamic Pipeline System");
        ImGui::Separator();
        
        // Current pipeline info
        std::string currentPipeline = getCurrentPipelineName();
        if (currentPipeline.empty()) {
            ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "No pipeline loaded");
        } else {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), "Current: %s", currentPipeline.c_str());
            
            // Pipeline info
            if (m_pipelineManager && m_pipelineManager->getCurrentPipeline()) {
                auto pipeline = m_pipelineManager->getCurrentPipeline();
                ImGui::Text("Name: %s", pipeline->GetName().c_str());
                ImGui::Text("Version: %s", pipeline->GetVersion().c_str());
                
                // Supported parameters
                auto params = pipeline->GetSupportedParameters();
                if (!params.empty()) {
                    if (ImGui::TreeNode("Supported Parameters")) {
                        for (const auto& param : params) {
                            ImGui::Text("• %s", param.c_str());
                        }
                        ImGui::TreePop();
                    }
                }
                
                // Supported animations
                auto animations = pipeline->GetSupportedAnimations();
                if (!animations.empty()) {
                    if (ImGui::TreeNode("Supported Animations")) {
                        for (const auto& anim : animations) {
                            ImGui::Text("• %s", anim.c_str());
                        }
                        ImGui::TreePop();
                    }
                }
            }
        }
        
        ImGui::Separator();
        
        // Pipeline selection
        auto availablePipelines = getAvailablePipelines();
        if (!availablePipelines.empty()) {
            static int selectedPipeline = 0;
            std::vector<const char*> pipelineNames;
            for (const auto& name : availablePipelines) {
                pipelineNames.push_back(name.c_str());
            }
            
            ImGui::Text("Available Pipelines:");
            if (ImGui::Combo("##PipelineSelect", &selectedPipeline, pipelineNames.data(), pipelineNames.size())) {
                if (selectedPipeline < availablePipelines.size()) {
                    switchPipeline(availablePipelines[selectedPipeline]);
                }
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Load")) {
                if (selectedPipeline < availablePipelines.size()) {
                    loadPipeline(availablePipelines[selectedPipeline]);
                }
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Unload")) {
                unloadCurrentPipeline();
            }
        } else {
            ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No pipelines available");
        }
        
        // Pipeline configuration
        if (isPipelineLoaded()) {
            ImGui::Separator();
            ImGui::Text("Pipeline Configuration");
            
            static char configPath[256] = "pipeline_config.json";
            ImGui::InputText("Config Path", configPath, sizeof(configPath));
            
            if (ImGui::Button("Save Config")) {
                savePipelineConfig(configPath);
            }
            
            ImGui::SameLine();
            if (ImGui::Button("Load Config")) {
                loadPipelineConfig(configPath);
            }
        }
    }
    
    // Progress and status
    if (m_animationState.isGenerating) {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                          "Generating animation... %.1f%%", 
                          m_animationState.generationProgress * 100.0f);
        
        ImGui::ProgressBar(m_animationState.generationProgress);
    }
    
    // Results
    if (!m_animationState.currentAnimation.spritesheet.individualFrames.empty()) {
        ImGui::Text("Generated %zu frames", m_animationState.currentAnimation.spritesheet.individualFrames.size());
        ImGui::Text("Animation duration: %.3f seconds", 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration);
        
        // Show saved files
        if (!m_animationState.currentAnimation.spritesheetPath.empty()) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Saved: %s", m_animationState.currentAnimation.spritesheetPath.c_str());
        }
        
        if (!m_animationState.currentAnimation.animationJsonPath.empty()) {
            ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                              "Saved: %s", m_animationState.currentAnimation.animationJsonPath.c_str());
        }
    }
    
    ImGui::EndChild();
    ImGui::Columns(1);
    
    // Timeline scrubber at bottom
    ImGui::Text("Timeline: ");
    ImGui::SameLine();
    static float timelineTime = 0.0f;
    float maxTime = m_animationState.animationParams.useTimeline ? 
                   m_animationState.animationParams.timelineDuration : 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
    
    if (ImGui::SliderFloat("##Timeline", &timelineTime, 0.0f, maxTime, "%.3f")) {
        m_animationState.previewTime = timelineTime;
    }
    
    // Status bar
    renderAnimationStatusBar(imgui);
}

void ImageGenerator::renderTimelineEditorUI(ImGuiContext* imgui) {
    ImGui::Text("Timeline Editor");
    ImGui::Separator();
    
    // Timeline tracks
    if (ImGui::CollapsingHeader("Tracks", ImGuiTreeNodeFlags_DefaultOpen)) {
        // Morph weight track
        if (ImGui::TreeNode("Morph Weight")) {
            static float morphWeight = 0.0f;
            ImGui::SliderFloat("Weight", &morphWeight, 0.0f, 1.0f, "%.3f");
            ImGui::TreePop();
        }
        
        // Module visibility track
        if (ImGui::TreeNode("Module Visibility")) {
            static bool weaponVisible = true;
            static bool shieldVisible = true;
            static bool effectsVisible = true;
            
            ImGui::Checkbox("Weapon", &weaponVisible);
            ImGui::Checkbox("Shield", &shieldVisible);
            ImGui::Checkbox("Effects", &effectsVisible);
            
            ImGui::TreePop();
        }
        
        // LOD change track
        if (ImGui::TreeNode("LOD Changes")) {
            static int currentLOD = 0;
            ImGui::SliderInt("LOD Level", &currentLOD, 0, 3);
            ImGui::TreePop();
        }
        
        // Weapon fire track
        if (ImGui::TreeNode("Weapon Fire")) {
            static bool weaponFiring = false;
            ImGui::Checkbox("Firing", &weaponFiring);
            ImGui::TreePop();
        }
        
        // Effects track
        if (ImGui::TreeNode("Effects")) {
            static bool effectsActive = false;
            ImGui::Checkbox("Active", &effectsActive);
            ImGui::TreePop();
        }
    }
    
    // Keyframe editor
    if (ImGui::CollapsingHeader("Keyframes", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Keyframe Editor");
        AnimationTimeline& timeline = m_animationState.animationParams.timeline;

        // New keyframe input
        static float newTime = 0.0f;
        static int newTrackIdx = 0;
        static float newValue = 0.0f;
        static int newInterpIdx = 0;
        const char* trackNames[] = { "morph_weight", "module_visibility", "lod_change", "weapon_fire", "effects", "custom" };
        const char* interpNames[] = { "linear", "ease", "step" };
        ImGui::InputFloat("Key Time", &newTime, 0.01f, 0.1f, "%.3f");
        ImGui::Combo("Key Track", &newTrackIdx, trackNames, IM_ARRAYSIZE(trackNames));
        ImGui::InputFloat("Key Value", &newValue, 0.01f, 0.1f, "%.3f");
        ImGui::Combo("Interpolation", &newInterpIdx, interpNames, IM_ARRAYSIZE(interpNames));
        if (ImGui::Button("Add Keyframe")) {
            TimelineKeyframe kf;
            kf.time = std::max(0.0f, newTime);
            kf.trackName = trackNames[newTrackIdx];
            kf.trackType = static_cast<TimelineTrackType>(newTrackIdx);
            kf.value = newValue;
            kf.interpolation = interpNames[newInterpIdx];
            timeline.keyframes.push_back(kf);
            std::stable_sort(timeline.keyframes.begin(), timeline.keyframes.end(),
                             [](const TimelineKeyframe& a, const TimelineKeyframe& b) { return a.time < b.time; });
            timeline.duration = std::max(timeline.duration, kf.time);
            m_animationState.animationParams.useTimeline = true;
        }

        // Existing keyframes
        int removeIndex = -1;
        for (size_t i = 0; i < timeline.keyframes.size(); ++i) {
            TimelineKeyframe& kf = timeline.keyframes[i];
            ImGui::PushID(static_cast<int>(i));
            float value = anyToFloat(kf.value);
            ImGui::Text("%.3fs  %s  (%s)", kf.time, kf.trackName.c_str(), kf.interpolation.c_str());
            ImGui::SameLine();
            if (ImGui::DragFloat("##value", &value, 0.01f)) {
                kf.value = value;
            }
            ImGui::SameLine();
            if (ImGui::Button("Remove")) {
                removeIndex = static_cast<int>(i);
            }
            ImGui::PopID();
        }
        if (removeIndex >= 0) {
            timeline.keyframes.erase(timeline.keyframes.begin() + removeIndex);
        }

        // Keep per-track views in sync with the flat keyframe list
        timeline.tracks.clear();
        timeline.trackNames.clear();
        for (const auto& kf : timeline.keyframes) {
            if (timeline.tracks.find(kf.trackName) == timeline.tracks.end()) {
                timeline.trackNames.push_back(kf.trackName);
            }
            timeline.tracks[kf.trackName].push_back(kf);
        }
    }
    
    // Timeline scrubber
    ImGui::Text("Timeline");
    ImGui::Separator();
    
    static float timelineTime = 0.0f;
    float maxTime = m_animationState.animationParams.useTimeline ? 
                   m_animationState.animationParams.timelineDuration : 
                   m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
    
    if (ImGui::SliderFloat("Time", &timelineTime, 0.0f, maxTime, "%.3f")) {
        m_animationState.previewTime = timelineTime;
    }
    
    // Playback controls
    ImGui::SameLine();
    if (ImGui::Button("Play")) {
        startAnimationPreview();
    }
    
    ImGui::SameLine();
    if (ImGui::Button("Stop")) {
        stopAnimationPreview();
    }
    
    ImGui::SameLine();
    if (ImGui::Button("Reset")) {
        timelineTime = 0.0f;
        m_animationState.previewTime = 0.0f;
    }
}

void ImageGenerator::renderAnimationPreviewUI(ImGuiContext* imgui) {
    // Preview area
    ImGui::Text("Animation Preview");
    ImGui::Separator();
    
    static float previewScale = 1.0f;

    // Current frame of the generated animation, picked from the sheet by preview time
    ImVec2 previewSize(400, 300);
    ImGui::BeginChild("AnimationPreviewArea", previewSize, true, ImGuiWindowFlags_NoScrollbar);

    ImVec2 minPos = ImGui::GetWindowPos();
    ImVec2 maxPos = ImVec2(minPos.x + previewSize.x, minPos.y + previewSize.y);
    ImDrawList* drawList = ImGui::GetWindowDrawList();
    drawList->AddRectFilled(minPos, maxPos, IM_COL32(50, 50, 50, 255));

    const AnimationBundle& anim = m_animationState.currentAnimation;
    const int frameCount = anim.frameIndices.empty() ? static_cast<int>(anim.spritesheet.frameBounds.size())
                                                     : static_cast<int>(anim.frameIndices.size());
    const int frame = AnimationUtils::calculateFrameIndex(m_animationState.previewTime,
                                                          m_animationState.animationParams.frameDuration,
                                                          std::max(1, frameCount));
    const size_t cell = anim.frameIndices.empty() ? static_cast<size_t>(frame)
                                                  : static_cast<size_t>(anim.frameIndices[static_cast<size_t>(frame)]);
    if (!anim.spritesheet.combinedImage.empty() && cell < anim.spritesheet.frameBounds.size()) {
        const glm::vec4& b = anim.spritesheet.frameBounds[cell];
        drawImagePreview(drawList, anim.spritesheet.combinedImage, minPos, previewSize, previewScale,
                         static_cast<int>(b.x), static_cast<int>(b.y), static_cast<int>(b.z), static_cast<int>(b.w));
    } else {
        drawList->AddText(ImVec2(minPos.x + 10, minPos.y + 10), IM_COL32(255, 255, 255, 255),
                          "No animation generated yet");
    }

    // Draw current frame info
    std::string frameInfo = "Frame: " + std::to_string(frame) + " / " + std::to_string(frameCount);
    ImVec2 frameTextPos = ImVec2(minPos.x + 10, minPos.y + 30);
    drawList->AddText(frameTextPos, IM_COL32(255, 255, 0, 255), frameInfo.c_str());

    ImGui::EndChild();

    // Preview controls
    ImGui::Text("Preview Controls");
    ImGui::Separator();

    ImGui::SliderFloat("Scale", &previewScale, 0.1f, 3.0f, "%.2f");

    ImGui::Checkbox("Loop Preview", &m_animationState.animationParams.looping);

    static float previewSpeed = 1.0f;
    if (ImGui::SliderFloat("Speed", &previewSpeed, 0.1f, 5.0f, "%.2f")) {
        // Speed scales playback by changing the per-frame duration used by the preview clock
        m_animationState.animationParams.frameRate = DEFAULT_ANIMATION_FRAME_RATE * previewSpeed;
    }
}

void ImageGenerator::renderAnimationControlsUI(ImGuiContext* imgui) {
    // Animation generation controls
    ImGui::Text("Animation Generation Controls");
    ImGui::Separator();
    
    if (ImGui::Button("Start Animation Generation")) {
        startAnimationGeneration();
    }
    
    if (ImGui::Button("Stop Animation Generation")) {
        stopAnimationGeneration();
    }
    
    ImGui::SameLine();
    
    if (ImGui::Button("Clear Animation Cache")) {
        clearCache();
    }
    
    // Animation processing settings
    ImGui::Text("Animation Processing Settings");
    ImGui::Separator();
    
    static int animationProcessingQuality = m_processingQuality;
    if (ImGui::SliderInt("Processing Quality", &animationProcessingQuality, 1, 5)) {
        setProcessingQuality(animationProcessingQuality);
    }
    
    static float animationCompressionQuality = m_compressionQuality;
    if (ImGui::SliderFloat("Compression Quality", &animationCompressionQuality, 0.0f, 1.0f, "%.2f")) {
        setCompressionQuality(animationCompressionQuality);
    }
    
    static bool animationGPUAcceleration = m_gpuAccelerationEnabled;
    if (ImGui::Checkbox("GPU Acceleration", &animationGPUAcceleration)) {
        setGPUAcceleration(animationGPUAcceleration);
    }
    
    static bool animationAsyncProcessing = m_asyncProcessingEnabled;
    if (ImGui::Checkbox("Async Processing", &animationAsyncProcessing)) {
        setAsyncProcessing(animationAsyncProcessing);
    }
    
    // Animation performance metrics
    ImGui::Text("Animation Performance Metrics");
    ImGui::Separator();
    
    ImGui::Text("Total Animations: %llu", m_animationPerformanceMetrics.totalGenerations.load());
    ImGui::Text("Animation Cache Hit Rate: %.2f%%", m_animationPerformanceMetrics.getCacheHitRate() * 100.0);
    ImGui::Text("Average Animation Time: %.2f ms", m_animationPerformanceMetrics.getAverageGenerationTime());
    ImGui::Text("Animation Exports: %llu", m_animationPerformanceMetrics.animationExports.load());
    ImGui::Text("Active Animations: %llu", m_animationPerformanceMetrics.activeGenerators.load());
}

void ImageGenerator::renderAnimationStatusBar(ImGuiContext* imgui) {
    ImGui::Separator();
    
    // Status information
    std::string statusText;
    if (m_animationState.isGenerating) {
        statusText = "Generating Animation...";
    } else if (m_animationState.isPreviewing) {
        statusText = "Previewing Animation...";
    } else if (!m_lastError.empty()) {
        statusText = "Error: " + m_lastError;
    } else {
        statusText = "Animation Ready";
    }
    
    ImGui::TextColored(ImVec4(0.8f, 0.8f, 0.8f, 1.0f), "%s", statusText.c_str());
    
    // Performance info
    ImGui::SameLine(ImGui::GetWindowWidth() - 200);
    ImGui::Text("Animation Cache: %zu items", getCacheSize());
}

// NEW: Animation Generation Control Functions
void ImageGenerator::startAnimationGeneration() {
    if (m_animationState.isGenerating) return;
    
    m_animationState.isGenerating = true;
    m_animationState.generationProgress = 0.0f;
    m_animationCV.notify_one();
}

void ImageGenerator::stopAnimationGeneration() {
    m_animationState.isGenerating = false;
    m_animationState.generationProgress = 0.0f;
}

void ImageGenerator::startAnimationPreview() {
    if (m_animationState.isPreviewing) return;
    
    m_animationState.isPreviewing = true;
    m_animationCV.notify_one();
}

void ImageGenerator::stopAnimationPreview() {
    m_animationState.isPreviewing = false;
}

// NEW: Animation Processing Functions
AnimationBundle ImageGenerator::generateAnimation(const AnimationParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t hash = params.hashKey();
        AnimationBundle cachedBundle;
        if (m_cachingEnabled && getCachedAnimation(hash, cachedBundle)) {
            m_animationPerformanceMetrics.cacheHits++;
            return cachedBundle;
        }
        
        m_animationPerformanceMetrics.cacheMisses++;
        m_animationPerformanceMetrics.activeGenerators++;
        
        // Generate animation
        AnimationBundle bundle = processAnimationGeneration(params);
        
        // Cache result
        if (m_cachingEnabled) {
            cacheAnimation(hash, bundle);
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        bundle.generationTime = duration.count();
        bundle.creationTime = std::chrono::system_clock::now();
        
        m_animationPerformanceMetrics.totalGenerations++;
        m_animationPerformanceMetrics.totalGenerationTime += duration.count();
        m_animationPerformanceMetrics.activeGenerators--;
        m_animationPerformanceMetrics.animationExports++;
        
        return bundle;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationPerformanceMetrics.activeGenerators--;
        return AnimationBundle{};
    }
}

std::vector<ImageBundle> ImageGenerator::captureAnimationFrames(const AnimationParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        m_animationPerformanceMetrics.activeGenerators++;
        
        // Capture animation frames
        std::vector<ImageBundle> frames = processAnimationFrameCapture(params);
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        m_animationPerformanceMetrics.totalGenerations++;
        m_animationPerformanceMetrics.totalGenerationTime += duration.count();
        m_animationPerformanceMetrics.activeGenerators--;
        
        return frames;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationPerformanceMetrics.activeGenerators--;
        return std::vector<ImageBundle>{};
    }
}

// NEW: Animation Processing Helper Functions
AnimationBundle ImageGenerator::processAnimationGeneration(const AnimationParams& params) {
    // Capture animation frames
    std::vector<ImageBundle> frames = processAnimationFrameCapture(params);
    
    ensureProcessingObjects();

    // Create spritesheet from the captured frames
    SpritesheetParams spParams = m_animationState.spritesheetParams;
    animationGrid(params.frameCount, spParams.columns, spParams.rows);

    // Lay frames out in the requested order (column-major fills columns first)
    const std::vector<int> cellIndices =
        AnimationUtils::generateFrameIndices(static_cast<int>(frames.size()), params.frameOrder, spParams.columns, spParams.rows);
    std::vector<ImageBundle> orderedFrames(static_cast<size_t>(spParams.columns) * spParams.rows);
    for (size_t i = 0; i < frames.size() && i < cellIndices.size(); ++i) {
        const int cell = cellIndices[i];
        if (cell >= 0 && static_cast<size_t>(cell) < orderedFrames.size()) {
            orderedFrames[static_cast<size_t>(cell)] = frames[i];
        }
    }

    const float frameRate = params.frameDuration > 0.0f ? 1.0f / params.frameDuration : params.frameRate;
    SpritesheetBundle spritesheet = m_spritesheetAssembler->assemble(
        orderedFrames, spParams.columns, spParams.rows, spParams.tileWidth, spParams.tileHeight,
        spParams.padding, glm::vec4(0.0f), frameRate, params.looping,
        params.animationName.empty() ? params.id : params.animationName);

    // Create animation bundle
    AnimationBundle bundle;
    bundle.spritesheet = spritesheet;
    bundle.starboundMetadata = processStarboundMetadata(params);
    bundle.timeline = params.timeline;

    // Generate frame data
    bundle.frameTimes = AnimationUtils::generateFrameTimes(params.frameCount, params.frameDuration);
    bundle.frameIndices = cellIndices;
    bundle.memoryUsage = spritesheet.memoryUsage;
    
    // Set file paths
    bundle.animationJsonPath = params.id + ".animation";
    bundle.spritesheetPath = params.id + "_anim.png";
    
    return bundle;
}

std::vector<ImageBundle> ImageGenerator::processAnimationFrameCapture(const AnimationParams& params) {
    std::vector<ImageBundle> frames;
    frames.reserve(params.frameCount);
    
    // Get current pipeline
    IPipeline* pipeline = m_pipelineManager ? m_pipelineManager->getCurrentPipeline() : nullptr;
    if (!pipeline) {
        m_lastError = "No pipeline loaded for animation capture";
        return frames;
    }
    
    // Enhanced tile capture for animations
    for (int i = 0; i < params.frameCount; ++i) {
        // Set animation time
        float time = i * params.frameDuration;
        
        // Update pipeline with animation time
        pipeline->SetAnimTime(time);
        
        // Evaluate timeline if enabled
        if (params.useTimeline) {
            // Evaluate timeline at this time
            float morphWeight = AnimationUtils::evaluateTimeline(params.timeline, time, "morph_weight");
            float moduleVisibility = AnimationUtils::evaluateTimeline(params.timeline, time, "module_visibility");
            float lodLevel = AnimationUtils::evaluateTimeline(params.timeline, time, "lod_change");
            
            // Apply timeline values to pipeline
            pipeline->SetMorphWeight(morphWeight);
            pipeline->SetModuleVisibility(moduleVisibility);
            pipeline->SetLODLevel(static_cast<int>(lodLevel));
        }
        
        // Capture frame with enhanced parameters
        CaptureParams captureParams = m_animationState.captureParams;
        captureParams.width = m_animationState.spritesheetParams.tileWidth;
        captureParams.height = m_animationState.spritesheetParams.tileHeight;
        
        // Use GPU acceleration if enabled
        if (m_gpuAccelerationEnabled) {
            captureParams.gpuAccelerated = true;
        }
        
        ImageBundle frame = processFrameCapture(captureParams);
        
        // Set enhanced frame metadata
        frame.metadata.id = params.id + "_frame_" + std::to_string(i);
        frame.metadata.title = "Animation Frame " + std::to_string(i);
        frame.metadata.description = "Generated animation frame at time " + std::to_string(time);
        frame.metadata.timestamp = time;
        frame.metadata.frameIndex = i;
        
        // Add animation-specific metadata
        frame.metadata.customData["animation_time"] = time;
        frame.metadata.customData["frame_index"] = i;
        frame.metadata.customData["frame_duration"] = params.frameDuration;
        
        frames.push_back(frame);
        
        // Update progress
        float progress = static_cast<float>(i + 1) / params.frameCount;
        updateAnimationGenerationProgress(progress);
    }
    
    return frames;
}

StarboundAnimationMetadata ImageGenerator::processStarboundMetadata(const AnimationParams& params) {
    return AnimationUtils::createStarboundMetadata(params);
}

// NEW: Animation Threading Functions
void ImageGenerator::animationThreadFunction() {
    while (m_animationThreadRunning) {
        std::unique_lock<std::mutex> lock(m_animationMutex);
        m_animationCV.wait(lock, [this] { 
            return !m_animationThreadRunning || m_animationState.isGenerating || m_animationState.isPreviewing; 
        });
        
        if (!m_animationThreadRunning) break;
        
        if (m_animationState.isGenerating) {
            processAsyncAnimationGeneration();
        }
        
        if (m_animationState.isPreviewing) {
            processAsyncAnimationPreview();
        }
    }
}

void ImageGenerator::processAsyncAnimationGeneration() {
    try {
        // Simulate animation generation progress
        for (int i = 0; i <= 100; ++i) {
            if (!m_animationState.isGenerating) break;
            
            m_animationState.generationProgress = i / 100.0f;
            std::this_thread::sleep_for(std::chrono::milliseconds(30));
        }
        
        // Generate animation
        AnimationBundle bundle = generateAnimation(m_animationState.animationParams);
        m_animationState.currentAnimation = bundle;
        
        m_animationState.isGenerating = false;
        m_animationState.generationProgress = 0.0f;
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationState.isGenerating = false;
        m_animationState.generationProgress = 0.0f;
    }
}

void ImageGenerator::processAsyncAnimationPreview() {
    try {
        // Simulate animation preview
        float maxTime = m_animationState.animationParams.useTimeline ? 
                       m_animationState.animationParams.timelineDuration : 
                       m_animationState.animationParams.frameCount * m_animationState.animationParams.frameDuration;
        
        while (m_animationState.isPreviewing) {
            // ~60 FPS clock, scaled by the preview speed (frameRate relative to the default rate)
            const float speed = m_animationState.animationParams.frameRate > 0.0f
                                    ? m_animationState.animationParams.frameRate / DEFAULT_ANIMATION_FRAME_RATE
                                    : 1.0f;
            m_animationState.previewTime += 0.016f * speed;
            if (m_animationState.previewTime >= maxTime) {
                if (m_animationState.animationParams.looping) {
                    m_animationState.previewTime = 0.0f;
                } else {
                    m_animationState.isPreviewing = false;
                    break;
                }
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(16));
        }
        
    } catch (const std::exception& e) {
        handleAnimationGenerationError(e.what());
        m_animationState.isPreviewing = false;
    }
}

// NEW: Animation Cache Functions
bool ImageGenerator::getCachedAnimation(uint64_t hash, AnimationBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    auto it = m_animationCache.find(hash);
    if (it != m_animationCache.end()) {
        bundle = it->second;
        return true;
    }
    return false;
}

void ImageGenerator::cacheAnimation(uint64_t hash, const AnimationBundle& bundle) {
    std::lock_guard<std::mutex> lock(m_cacheMutex);
    
    // Limit cache size
    if (m_animationCache.size() >= MAX_ANIMATION_CACHE_SIZE) {
        // Remove oldest entry (simple FIFO)
        m_animationCache.erase(m_animationCache.begin());
    }
    
    m_animationCache[hash] = bundle;
}

// NEW: Animation Helper Functions
void ImageGenerator::updateAnimationGenerationProgress(float progress) {
    m_animationState.generationProgress = std::clamp(progress, 0.0f, 1.0f);
}

void ImageGenerator::updateAnimationPreviewTime(float time) {
    m_animationState.previewTime = time;
}

void ImageGenerator::handleAnimationGenerationError(const std::string& error) {
    m_lastError = "Animation Error: " + error;
    m_animationState.isGenerating = false;
    m_animationState.isPreviewing = false;
    m_animationState.generationProgress = 0.0f;
}

// NEW: Animation Validation Functions
bool ImageGenerator::validateAnimationFrameCount(int frameCount) {
    return frameCount > 0 && frameCount <= 1000;
}

bool ImageGenerator::validateAnimationDuration(float duration) {
    return duration > 0.0f && duration <= 60.0f;
}

bool ImageGenerator::validateTimelineKeyframes(const std::vector<TimelineKeyframe>& keyframes) {
    if (keyframes.empty()) return true;
    
    // Check for valid time ordering
    for (size_t i = 1; i < keyframes.size(); ++i) {
        if (keyframes[i].time < keyframes[i-1].time) {
            return false;
        }
    }
    
    return true;
}

// NEW: Animation Utility Functions
std::string ImageGenerator::getAnimationModeString(AnimationMode mode) const {
    switch (mode) {
        case AnimationMode::SINGLE_FRAME: return "Single Frame";
        case AnimationMode::ANIMATED_SEQUENCE: return "Animated Sequence";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getFrameOrderString(FrameOrder order) const {
    switch (order) {
        case FrameOrder::ROW_MAJOR: return "Row-Major";
        case FrameOrder::COLUMN_MAJOR: return "Column-Major";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getTimelineTrackTypeString(TimelineTrackType type) const {
    switch (type) {
        case TimelineTrackType::MORPH_WEIGHT: return "Morph Weight";
        case TimelineTrackType::MODULE_VISIBILITY: return "Module Visibility";
        case TimelineTrackType::LOD_CHANGE: return "LOD Change";
        case TimelineTrackType::WEAPON_FIRE: return "Weapon Fire";
        case TimelineTrackType::EFFECTS: return "Effects";
        case TimelineTrackType::CUSTOM: return "Custom";
        default: return "Unknown";
    }
}

std::string ImageGenerator::getAnimationExportFormatString(AnimationExportFormat format) const {
    switch (format) {
        case AnimationExportFormat::STARBOUND_ANIMATION: return "Starbound Animation";
        case AnimationExportFormat::GENERIC_JSON: return "Generic JSON";
        case AnimationExportFormat::CUSTOM_FORMAT: return "Custom Format";
        default: return "Unknown";
    }
}

// NEW: Animation Performance Helper Functions
void ImageGenerator::updateAnimationPerformanceMetrics(uint64_t generationTime, uint64_t memoryUsage) {
    m_animationPerformanceMetrics.totalGenerationTime += generationTime;
    m_animationPerformanceMetrics.peakMemoryUsage = std::max(m_animationPerformanceMetrics.peakMemoryUsage.load(), memoryUsage);
}

void ImageGenerator::logAnimationPerformanceMetrics() {
    MagiTech::Log::info("ImageGenerator",
                        "animations={} cacheHitRate={:.2f}% avgTime={:.2f}us exports={} peakMemory={}B active={}",
                        m_animationPerformanceMetrics.totalGenerations.load(),
                        m_animationPerformanceMetrics.getCacheHitRate() * 100.0,
                        m_animationPerformanceMetrics.getAverageGenerationTime(),
                        m_animationPerformanceMetrics.animationExports.load(),
                        m_animationPerformanceMetrics.peakMemoryUsage.load(),
                        m_animationPerformanceMetrics.activeGenerators.load());
}

// NEW: Animation Quality Assessment Functions
AnimationQualityMetrics ImageGenerator::assessAnimationQuality(const AnimationBundle& bundle) {
    AnimationQualityMetrics metrics;
    const auto& times = bundle.frameTimes;

    // Frame durations from the per-frame start times
    std::vector<float> durations;
    for (size_t i = 1; i < times.size(); ++i) {
        durations.push_back(times[i] - times[i - 1]);
    }
    if (durations.empty() && bundle.starboundMetadata.frameTime > 0.0f) {
        durations.push_back(bundle.starboundMetadata.frameTime);
    }
    if (!durations.empty()) {
        const double mean = std::accumulate(durations.begin(), durations.end(), 0.0) / durations.size();
        double var = 0.0;
        for (float d : durations) var += (d - mean) * (d - mean);
        var /= durations.size();
        metrics.averageFrameTime = static_cast<float>(mean);
        metrics.frameTimeVariance = static_cast<float>(var);

        // Consistency: share of frames within 10% of the mean duration
        size_t consistent = 0;
        for (float d : durations) {
            if (mean > 0.0 && std::fabs(d - mean) <= 0.1 * mean) ++consistent;
        }
        metrics.consistency = static_cast<float>(consistent) / static_cast<float>(durations.size());
        // Smoothness: 1 for perfectly even timing, falling off with the coefficient of variation
        const double cv = mean > 0.0 ? std::sqrt(var) / mean : 1.0;
        metrics.smoothness = static_cast<float>(1.0 / (1.0 + cv * 10.0));
    }

    // Dropped frames: requested frames that never made it into the sheet
    const int expected = bundle.starboundMetadata.frameCount;
    const int produced = static_cast<int>(bundle.frameIndices.size());
    metrics.droppedFrames = std::max(0, expected - produced);

    // Compression ratio: packed sheet bytes vs. the raw RGBA frames it contains
    const auto& sheet = bundle.spritesheet;
    const size_t rawBytes = static_cast<size_t>(std::max(0, produced)) *
                            static_cast<size_t>(std::max(0, sheet.tileWidth)) *
                            static_cast<size_t>(std::max(0, sheet.tileHeight)) * 4;
    if (rawBytes > 0) {
        metrics.compressionRatio = static_cast<float>(sheet.combinedImage.byteSize()) / static_cast<float>(rawBytes);
    }
    return metrics;
}

bool ImageGenerator::validateAnimationParams(const AnimationParams& params, std::string& errorMessage) {
    if (!validateAnimationFrameCount(params.frameCount)) {
        errorMessage = "Invalid animation frame count";
        return false;
    }
    
    if (!validateAnimationDuration(params.frameDuration)) {
        errorMessage = "Invalid animation frame duration";
        return false;
    }
    
    if (params.id.empty()) {
        errorMessage = "Animation ID cannot be empty";
        return false;
    }
    
    return true;
}

bool ImageGenerator::validateTimelineData(const AnimationTimeline& timeline, std::string& errorMessage) {
    if (!validateTimelineKeyframes(timeline.keyframes)) {
        errorMessage = "Invalid timeline keyframes";
        return false;
    }
    
    if (timeline.duration <= 0.0f) {
        errorMessage = "Invalid timeline duration";
        return false;
    }
    
    return true;
}

// NEW: Animation File Operation Functions
bool ImageGenerator::saveAnimation(const AnimationBundle& bundle, const std::string& filePath) {
    if (!validateFilePaths(filePath)) {
        m_lastError = "Invalid animation path: " + filePath;
        return false;
    }
    AnimationBundle toSave = bundle;
    // The sheet image is written next to the animation file
    if (!bundle.spritesheet.combinedImage.empty()) {
        const std::string sheetPath = replaceExtension(filePath, ".png");
        if (!saveSpritesheet(bundle.spritesheet, sheetPath)) {
            return false;
        }
        if (!exportAtlasJSON(bundle.spritesheet, replaceExtension(filePath, ".json"))) {
            return false;
        }
        toSave.spritesheetPath = sheetPath;
    }
    toSave.animationJsonPath = filePath;
    return exportAnimationJSON(toSave, filePath);
}

bool ImageGenerator::loadAnimation(const std::string& filePath, AnimationBundle& bundle) {
    try {
        std::ifstream in(filePath);
        if (!in.is_open()) {
            m_lastError = "Failed to open animation file: " + filePath;
            return false;
        }
        nlohmann::json j;
        in >> j;

        AnimationBundle loaded;
        StarboundAnimationMetadata& meta = loaded.starboundMetadata;
        meta.name = j.value("name", std::string());
        meta.category = j.value("category", std::string());
        meta.type = j.value("type", std::string());
        meta.frameTime = j.value("frameTime", 0.0f);
        meta.loop = j.value("loop", true);
        meta.sheetCols = j.value("sheetCols", 1);
        meta.sheetRows = j.value("sheetRows", 1);
        meta.order = j.value("order", std::string("row-major"));
        meta.description = j.value("description", std::string());
        meta.author = j.value("author", std::string());
        meta.version = j.value("version", std::string());
        meta.creationTime = std::chrono::system_clock::now();
        if (j.contains("frames") && j["frames"].is_array()) {
            loaded.frameIndices = j["frames"].get<std::vector<int>>();
        }
        meta.frameCount = static_cast<int>(loaded.frameIndices.size());
        loaded.frameTimes = AnimationUtils::generateFrameTimes(meta.frameCount, meta.frameTime);
        if (j.contains("timeline")) {
            loaded.timeline = timelineFromJson(j["timeline"]);
        }
        loaded.animationJsonPath = filePath;

        // Sheet image: explicit reference, else <name>.png next to the file
        std::string sheetPath = j.value("spritesheet", std::string());
        if (!sheetPath.empty() && std::filesystem::path(sheetPath).is_relative()) {
            sheetPath = (std::filesystem::path(filePath).parent_path() / sheetPath).string();
        }
        if (sheetPath.empty()) {
            sheetPath = replaceExtension(filePath, ".png");
        }
        std::error_code ec;
        if (std::filesystem::exists(sheetPath, ec)) {
            if (!loadSpritesheet(sheetPath, loaded.spritesheet)) {
                return false;
            }
            loaded.spritesheetPath = sheetPath;
        }
        loaded.creationTime = std::chrono::system_clock::now();
        loaded.memoryUsage = loaded.spritesheet.combinedImage.byteSize();
        bundle = std::move(loaded);
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Failed to load animation " + filePath + ": " + e.what();
        return false;
    }
}

bool ImageGenerator::exportAnimationJSON(const AnimationBundle& bundle, const std::string& outputPath) {
    try {
        // Create output directory if it doesn't exist
        std::filesystem::path outputDir = std::filesystem::path(outputPath).parent_path();
        if (!std::filesystem::exists(outputDir)) {
            std::filesystem::create_directories(outputDir);
        }
        
        // Generate Starbound animation JSON
        nlohmann::json animationJson;
        
        // Frame indices array
        animationJson["frames"] = nlohmann::json::array();
        if (!bundle.frameIndices.empty()) {
            for (int index : bundle.frameIndices) {
                animationJson["frames"].push_back(index);
            }
        } else {
            for (int i = 0; i < bundle.starboundMetadata.frameCount; ++i) {
                animationJson["frames"].push_back(i);
            }
        }
        
        // Frame timing
        animationJson["frameTime"] = bundle.starboundMetadata.frameTime;
        animationJson["loop"] = bundle.starboundMetadata.loop;
        
        // Optional sheet layout information for mod tools
        animationJson["sheetCols"] = bundle.starboundMetadata.sheetCols;
        animationJson["sheetRows"] = bundle.starboundMetadata.sheetRows;
        animationJson["order"] = bundle.starboundMetadata.order;
        
        // Additional metadata
        animationJson["name"] = bundle.starboundMetadata.name;
        animationJson["category"] = bundle.starboundMetadata.category;
        animationJson["type"] = bundle.starboundMetadata.type;
        animationJson["description"] = bundle.starboundMetadata.description;
        animationJson["author"] = bundle.starboundMetadata.author;
        animationJson["version"] = bundle.starboundMetadata.version;
        
        // Sheet image reference (relative to the animation file when possible)
        if (!bundle.spritesheetPath.empty()) {
            const std::filesystem::path sheet(bundle.spritesheetPath);
            const std::filesystem::path base = std::filesystem::path(outputPath).parent_path();
            animationJson["spritesheet"] = (sheet.parent_path() == base) ? sheet.filename().string() : sheet.string();
        }

        // Timeline data if available
        if (!bundle.timeline.keyframes.empty()) {
            animationJson["timeline"] = timelineToJson(bundle.timeline);
        }
        
        // Write JSON file
        std::ofstream jsonFile(outputPath);
        if (!jsonFile.is_open()) {
            m_lastError = "Failed to open output file: " + outputPath;
            return false;
        }
        
        jsonFile << animationJson.dump(2);
        jsonFile.close();
        
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Export failed: " + std::string(e.what());
        return false;
    }
}

// NEW: Animation Export Functions
bool ImageGenerator::exportStarboundAnimation(const AnimationParams& params, const std::string& outputPath) {
    try {
        // Generate animation bundle
        AnimationBundle bundle = generateAnimation(params);
        
        // Create output directory if it doesn't exist
        std::filesystem::path outputDir = std::filesystem::path(outputPath).parent_path();
        if (!std::filesystem::exists(outputDir)) {
            std::filesystem::create_directories(outputDir);
        }
        
        // Generate Starbound animation JSON
        nlohmann::json animationJson;
        
        // Frame indices array
        animationJson["frames"] = nlohmann::json::array();
        for (int i = 0; i < params.frameCount; ++i) {
            animationJson["frames"].push_back(i);
        }
        
        // Frame timing
        animationJson["frameTime"] = params.frameDuration;
        animationJson["loop"] = params.looping;
        
        // Optional sheet layout information for mod tools
        animationJson["sheetCols"] = bundle.starboundMetadata.sheetCols;
        animationJson["sheetRows"] = bundle.starboundMetadata.sheetRows;
        animationJson["order"] = bundle.starboundMetadata.order;
        
        // Additional metadata
        animationJson["name"] = params.animationName;
        animationJson["category"] = params.starboundCategory;
        animationJson["type"] = params.starboundType;
        animationJson["description"] = bundle.starboundMetadata.description;
        animationJson["author"] = bundle.starboundMetadata.author;
        animationJson["version"] = bundle.starboundMetadata.version;
        
        // Write JSON file
        std::ofstream jsonFile(outputPath);
        if (!jsonFile.is_open()) {
            m_lastError = "Failed to open output file: " + outputPath;
            return false;
        }
        
        jsonFile << animationJson.dump(2);
        jsonFile.close();
        
        // Save the spritesheet assembled from the captured frames
        if (!bundle.spritesheet.combinedImage.empty()) {
            const std::string sheetPath = outputPath.substr(0, outputPath.find_last_of('.')) + "_sheet.png";
            if (!saveSpritesheet(bundle.spritesheet, sheetPath)) {
                m_lastError = "Failed to save spritesheet: " + sheetPath + " (" + m_lastError + ")";
                return false;
            }
            if (params.generateAtlasJSON &&
                !exportAtlasJSON(bundle.spritesheet, outputPath.substr(0, outputPath.find_last_of('.')) + "_sheet.json")) {
                return false;
            }
        }

        m_animationPerformanceMetrics.animationExports++;
        return true;
        
    } catch (const std::exception& e) {
        m_lastError = "Export failed: " + std::string(e.what());
        return false;
    }
}

bool ImageGenerator::exportAnimationFrames(const AnimationBundle& bundle, const std::string& outputDir) {
    ensureProcessingObjects();
    const SpritesheetBundle& sheet = bundle.spritesheet;
    if (sheet.combinedImage.empty()) {
        m_lastError = "Animation has no spritesheet image to export frames from";
        return false;
    }
    std::error_code ec;
    std::filesystem::create_directories(outputDir, ec);
    const std::string baseName = sanitizeAnimationFilename(
        bundle.starboundMetadata.name.empty() ? std::string("frame") : bundle.starboundMetadata.name);

    // Export in playback order: frameIndices maps sequence position -> sheet cell
    const size_t count = bundle.frameIndices.empty() ? sheet.frameBounds.size() : bundle.frameIndices.size();
    for (size_t i = 0; i < count; ++i) {
        const size_t cell = bundle.frameIndices.empty() ? i : static_cast<size_t>(bundle.frameIndices[i]);
        if (cell >= sheet.frameBounds.size()) {
            continue;
        }
        const glm::vec4& b = sheet.frameBounds[cell];
        const ImageData frame = m_imageAssembler->crop(sheet.combinedImage,
                                                       static_cast<int>(b.x), static_cast<int>(b.y),
                                                       static_cast<int>(b.z), static_cast<int>(b.w));
        std::ostringstream name;
        name << baseName << "_" << std::setw(3) << std::setfill('0') << i << ".png";
        const std::string path = (std::filesystem::path(outputDir) / name.str()).string();
        if (!m_imageWriter->write(frame, path, ImageFormat::PNG)) {
            m_lastError = m_imageWriter->lastError();
            return false;
        }
    }
    m_animationPerformanceMetrics.animationExports++;
    return true;
}

bool ImageGenerator::exportTimelineData(const AnimationBundle& bundle, const std::string& outputPath) {
    try {
        nlohmann::json j = timelineToJson(bundle.timeline);
        j["frameTimes"] = bundle.frameTimes;
        j["frameIndices"] = bundle.frameIndices;
        std::string error;
        if (!writeTextFile(outputPath, j.dump(2), error)) {
            m_lastError = error;
            return false;
        }
        return true;
    } catch (const std::exception& e) {
        m_lastError = "Timeline export failed: " + std::string(e.what());
        return false;
    }
}

// NEW: Animation Utility Helper Functions
std::string ImageGenerator::generateAnimationID() const {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    return "anim_" + std::to_string(millis);
}

std::string ImageGenerator::sanitizeAnimationFilename(const std::string& filename) const {
    std::string sanitized = filename;
    const std::string invalidChars = "<>:\"|?*";
    
    for (char& c : sanitized) {
        if (invalidChars.find(c) != std::string::npos) {
            c = '_';
        }
    }
    
    return sanitized;
}

std::string ImageGenerator::getAnimationTimestampString() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
    return oss.str();
}

// NEW: Enhanced Tile Capture & Assembly Function
std::vector<ImageBundle> ImageGenerator::CaptureTiles(
    IPipeline& pipeline, RenderContext& ctx,
    bool animMode, int frameCount, float frameDuration,
    int tileW, int tileH, int pad, int orderIdx
) {
    std::vector<ImageBundle> tiles;
    int total = animMode ? frameCount : 1;
    
    for (int i = 0; i < total; ++i) {
        if (animMode) {
            float t = i * frameDuration;
            pipeline.SetAnimTime(t);
        }
        
        // Capture frame with specified dimensions (padding is applied when the sheet is assembled)
        CaptureParams captureParams = m_animationState.captureParams;
        captureParams.id = "tile_" + std::to_string(i);
        captureParams.width = tileW;
        captureParams.height = tileH;
        captureParams.padding = 0;
        captureParams.gpuAccelerated = m_gpuAccelerationEnabled;

        ImageBundle tile = captureWithContext(ctx, captureParams);
        
        // Set tile metadata
        tile.metadata.id = "tile_" + std::to_string(i);
        tile.metadata.title = "Animation Tile " + std::to_string(i);
        tile.metadata.description = "Generated animation tile";
        tile.metadata.frameIndex = i;
        
        if (animMode) {
            tile.metadata.timestamp = i * frameDuration;
            tile.metadata.customData["animation_time"] = i * frameDuration;
        }
        
        tiles.push_back(tile);
        
        // Update progress
        float progress = static_cast<float>(i + 1) / total;
        updateAnimationGenerationProgress(progress);
    }
    
    return tiles;
}

// NEW: Image Assembly Function for Sprite Sheets
SpritesheetBundle ImageGenerator::MakeSheet(
    const std::vector<ImageBundle>& tiles,
    int cols, int rows, int tileW, int tileH, int padding
) {
    ensureProcessingObjects();
    SpritesheetBundle sheet = m_spritesheetAssembler->assemble(
        tiles, cols, rows, tileW, tileH, padding, glm::vec4(0.0f),
        m_animationState.animationParams.frameDuration > 0.0f ? 1.0f / m_animationState.animationParams.frameDuration
                                                              : m_animationState.animationParams.frameRate,
        m_animationState.animationParams.looping, "animation_sheet");
    
    // Set sheet metadata
    sheet.atlasMetadata.id = "animation_sheet";
    sheet.atlasMetadata.name = "Animation Sprite Sheet";
    sheet.atlasMetadata.description = "Generated animation sprite sheet";
    
    return sheet;
}

// NEW: Starbound Animation JSON Generator
void ImageGenerator::WriteStarboundAnimationJSON(
    const std::string& path,
    int frameCount,
    float frameDuration,
    int cols, int rows,
    int orderIdx
) {
    nlohmann::json j;
    
    // Frame indices array
    j["frames"] = nlohmann::json::array();
    for (int i = 0; i < frameCount; ++i) {
        j["frames"].push_back(i);
    }
    
    // Frame timing
    j["frameTime"] = frameDuration;
    j["loop"] = true;
    
    // Optional sheet layout information for mod tools
    j["sheetCols"] = cols;
    j["sheetRows"] = rows;
    j["order"] = orderIdx == 0 ? "row-major" : "column-major";
    
    // Additional metadata
    j["name"] = "Generated Animation";
    j["category"] = "mech";
    j["type"] = "animation";
    j["description"] = "Generated by MagiTech Animation Generator";
    j["author"] = "MagiTech";
    j["version"] = "1.0.0";
    
    // Write JSON file
    std::ofstream out(path);
    if (out.is_open()) {
        out << j.dump(2);
        out.close();
    }
}

// NEW: PipelineFactory Implementation
PipelineFactory& PipelineFactory::getInstance() {
    static PipelineFactory instance;
    return instance;
}

void PipelineFactory::registerPipeline(const std::string& name, PipelineCreator creator) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators[name] = creator;
}

void PipelineFactory::unregisterPipeline(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators.erase(name);
}

std::unique_ptr<IPipeline> PipelineFactory::createPipeline(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_creators.find(name);
    if (it != m_creators.end()) {
        return it->second();
    }
    return nullptr;
}

std::vector<std::string> PipelineFactory::getAvailablePipelines() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    std::vector<std::string> names;
    for (const auto& pair : m_creators) {
        names.push_back(pair.first);
    }
    return names;
}

std::unique_ptr<IPipeline> PipelineFactory::loadPipelineFromConfig(const std::string& configPath) {
    try {
        std::ifstream file(configPath);
        if (!file.is_open()) {
            return nullptr;
        }
        
        nlohmann::json config;
        file >> config;
        
        std::string pipelineType = config.value("pipeline_type", "");
        if (pipelineType.empty()) {
            return nullptr;
        }
        
        auto pipeline = createPipeline(pipelineType);
        if (pipeline) {
            // Load pipeline-specific configuration
            if (config.contains("parameters")) {
                for (const auto& [key, value] : config["parameters"].items()) {
                    if (value.is_number()) {
                        pipeline->SetParameter(key, value.get<double>());
                    } else if (value.is_string()) {
                        pipeline->SetParameter(key, value.get<std::string>());
                    } else if (value.is_boolean()) {
                        pipeline->SetParameter(key, value.get<bool>());
                    }
                }
            }
        }
        
        return pipeline;
        
    } catch (const std::exception& e) {
        return nullptr;
    }
}

// NEW: PipelineManager Implementation
PipelineManager::PipelineManager() {
    // Initialize with default pipeline if available
}

PipelineManager::~PipelineManager() {
    unloadCurrentPipeline();
}

bool PipelineManager::loadPipeline(const std::string& name) {
    auto pipeline = PipelineFactory::getInstance().createPipeline(name);
    if (pipeline && pipeline->initialize()) {
        m_currentPipeline = std::move(pipeline);
        m_currentPipelineName = name;
        return true;
    }
    return false;
}

bool PipelineManager::switchPipeline(const std::string& name) {
    if (m_currentPipelineName == name) {
        return true; // Already loaded
    }
    
    unloadCurrentPipeline();
    return loadPipeline(name);
}

void PipelineManager::unloadCurrentPipeline() {
    if (m_currentPipeline) {
        m_currentPipeline->shutdown();
        m_currentPipeline.reset();
        m_currentPipelineName.clear();
    }
}

std::vector<std::string> PipelineManager::getAvailablePipelines() const {
    return PipelineFactory::getInstance().getAvailablePipelines();
}

bool PipelineManager::savePipelineConfig(const std::string& configPath) const {
    try {
        nlohmann::json config;
        config["pipeline_type"] = m_currentPipelineName;
        config["pipeline_name"] = m_currentPipeline ? m_currentPipeline->GetName() : "";
        config["pipeline_version"] = m_currentPipeline ? m_currentPipeline->GetVersion() : "";
        
        // Save pipeline parameters
        if (m_currentPipeline) {
            nlohmann::json params;
            for (const auto& paramName : m_currentPipeline->GetSupportedParameters()) {
                nlohmann::json value = anyToJson(m_currentPipeline->GetParameter(paramName));
                if (!value.is_null()) {
                    params[paramName] = value;
                }
            }
            config["parameters"] = params;
        }

        // Save custom configuration
        nlohmann::json custom = nlohmann::json::object();
        for (const auto& [key, value] : m_pipelineConfig) {
            nlohmann::json v = anyToJson(value);
            if (!v.is_null()) {
                custom[key] = v;
            }
        }
        config["custom_config"] = custom;

        std::string error;
        return writeTextFile(configPath, config.dump(2), error);
        
    } catch (const std::exception& e) {
        return false;
    }
}

bool PipelineManager::loadPipelineConfig(const std::string& configPath) {
    nlohmann::json config;
    try {
        std::ifstream file(configPath);
        if (!file.is_open()) {
            return false;
        }
        file >> config;
    } catch (const std::exception&) {
        return false;
    }

    auto pipeline = PipelineFactory::getInstance().loadPipelineFromConfig(configPath);
    if (!pipeline || !pipeline->initialize()) {
        return false;
    }

    // Restore the configured parameters again after initialize() (which may reset state)
    if (config.contains("parameters") && config["parameters"].is_object()) {
        for (const auto& [key, value] : config["parameters"].items()) {
            std::any v = jsonToAny(value);
            if (v.has_value()) {
                pipeline->SetParameter(key, v);
            }
        }
    }

    unloadCurrentPipeline();
    m_currentPipeline = std::move(pipeline);
    m_currentPipelineName = config.value("pipeline_type", std::string());

    m_pipelineConfig.clear();
    if (config.contains("custom_config") && config["custom_config"].is_object()) {
        for (const auto& [key, value] : config["custom_config"].items()) {
            std::any v = jsonToAny(value);
            if (v.has_value()) {
                m_pipelineConfig[key] = v;
            }
        }
    }
    return true;
}

// NEW: Dynamic Pipeline Management Functions
bool ImageGenerator::loadPipeline(const std::string& pipelineName) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->loadPipeline(pipelineName);
}

bool ImageGenerator::switchPipeline(const std::string& pipelineName) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    return m_pipelineManager->switchPipeline(pipelineName);
}

void ImageGenerator::unloadCurrentPipeline() {
    if (m_pipelineManager) {
        m_pipelineManager->unloadCurrentPipeline();
    }
}

std::vector<std::string> ImageGenerator::getAvailablePipelines() const {
    if (!m_pipelineManager) {
        return {};
    }
    return m_pipelineManager->getAvailablePipelines();
}

std::string ImageGenerator::getCurrentPipelineName() const {
    if (!m_pipelineManager) {
        return "";
    }
    return m_pipelineManager->getCurrentPipelineName();
}

bool ImageGenerator::isPipelineLoaded() const {
    if (!m_pipelineManager) {
        return false;
    }
    return m_pipelineManager->isPipelineLoaded();
}

bool ImageGenerator::savePipelineConfig(const std::string& configPath) const {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    if (!m_pipelineManager->savePipelineConfig(configPath)) {
        m_lastError = "Failed to save pipeline configuration: " + configPath;
        return false;
    }
    m_pipelineConfigPath = configPath;
    return true;
}

bool ImageGenerator::loadPipelineConfig(const std::string& configPath) {
    if (!m_pipelineManager) {
        m_lastError = "Pipeline manager not initialized";
        return false;
    }
    
    if (!m_pipelineManager->loadPipelineConfig(configPath)) {
        m_lastError = "Failed to load pipeline configuration: " + configPath;
        return false;
    }
    m_pipelineConfigPath = configPath;
    return true;
}

bool ImageGenerator::setPipelineParameter(const std::string& name, const std::any& value) {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        m_lastError = "No pipeline loaded";
        return false;
    }
    
    m_pipelineManager->getCurrentPipeline()->SetParameter(name, value);
    return true;
}

std::any ImageGenerator::getPipelineParameter(const std::string& name) const {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        return std::any{};
    }
    
    return m_pipelineManager->getCurrentPipeline()->GetParameter(name);
}

std::vector<std::string> ImageGenerator::getPipelineSupportedParameters() const {
    if (!m_pipelineManager || !m_pipelineManager->getCurrentPipeline()) {
        return {};
    }
    
    return m_pipelineManager->getCurrentPipeline()->GetSupportedParameters();
}

// NEW: Example MechPipeline Implementation
class MechPipeline : public IPipeline {
public:
    MechPipeline() : m_initialized(false), m_animTime(0.0f), m_morphWeight(0.0f), 
                    m_moduleVisibility(1.0f), m_lodLevel(0), m_weaponFiring(false), 
                    m_effectsActive(false) {}
    
    ~MechPipeline() {
        shutdown();
    }
    
    // Core pipeline interface
    bool initialize() override {
        m_initialized = true;
        return true;
    }
    
    void shutdown() override {
        m_initialized = false;
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    // Animation interface
    void SetAnimTime(float time) override {
        m_animTime = time;
    }
    
    void SetMorphWeight(float weight) override {
        m_morphWeight = std::clamp(weight, 0.0f, 1.0f);
    }
    
    void SetModuleVisibility(float visibility) override {
        m_moduleVisibility = std::clamp(visibility, 0.0f, 1.0f);
    }
    
    void SetLODLevel(int level) override {
        m_lodLevel = std::clamp(level, 0, 3);
    }
    
    void SetWeaponFiring(bool firing) override {
        m_weaponFiring = firing;
    }
    
    void SetEffectsActive(bool active) override {
        m_effectsActive = active;
    }
    
    // Custom parameter interface
    void SetParameter(const std::string& name, const std::any& value) override {
        m_customParams[name] = value;
    }
    
    std::any GetParameter(const std::string& name) const override {
        auto it = m_customParams.find(name);
        if (it != m_customParams.end()) {
            return it->second;
        }
        return std::any{};
    }
    
    bool HasParameter(const std::string& name) const override {
        return m_customParams.find(name) != m_customParams.end();
    }
    
    // Pipeline metadata
    std::string GetName() const override {
        return "MechPipeline";
    }
    
    std::string GetVersion() const override {
        return "1.0.0";
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {
            "anim_time", "morph_weight", "module_visibility", "lod_level",
            "weapon_firing", "effects_active", "custom_param1", "custom_param2"
        };
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {
            "idle", "walk", "run", "attack", "defend", "special"
        };
    }
    
private:
    bool m_initialized;
    float m_animTime;
    float m_morphWeight;
    float m_moduleVisibility;
    int m_lodLevel;
    bool m_weaponFiring;
    bool m_effectsActive;
    std::unordered_map<std::string, std::any> m_customParams;
};

// NEW: Example CharacterPipeline Implementation
class CharacterPipeline : public IPipeline {
public:
    CharacterPipeline() : m_initialized(false), m_animTime(0.0f), m_expression(0.0f),
                        m_pose(0.0f), m_emotion(0.0f), m_action(0.0f) {}
    
    ~CharacterPipeline() {
        shutdown();
    }
    
    // Core pipeline interface
    bool initialize() override {
        m_initialized = true;
        return true;
    }
    
    void shutdown() override {
        m_initialized = false;
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    // Animation interface (mapped to character-specific parameters)
    void SetAnimTime(float time) override {
        m_animTime = time;
    }
    
    void SetMorphWeight(float weight) override {
        m_expression = std::clamp(weight, 0.0f, 1.0f);
    }
    
    void SetModuleVisibility(float visibility) override {
        m_pose = std::clamp(visibility, 0.0f, 1.0f);
    }
    
    void SetLODLevel(int level) override {
        m_emotion = static_cast<float>(std::clamp(level, 0, 3)) / 3.0f;
    }
    
    void SetWeaponFiring(bool firing) override {
        m_action = firing ? 1.0f : 0.0f;
    }
    
    void SetEffectsActive(bool active) override {
        // Character-specific effect handling
    }
    
    // Custom parameter interface
    void SetParameter(const std::string& name, const std::any& value) override {
        m_customParams[name] = value;
    }
    
    std::any GetParameter(const std::string& name) const override {
        auto it = m_customParams.find(name);
        if (it != m_customParams.end()) {
            return it->second;
        }
        return std::any{};
    }
    
    bool HasParameter(const std::string& name) const override {
        return m_customParams.find(name) != m_customParams.end();
    }
    
    // Pipeline metadata
    std::string GetName() const override {
        return "CharacterPipeline";
    }
    
    std::string GetVersion() const override {
        return "1.0.0";
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {
            "expression", "pose", "emotion", "action", "gesture", "speech"
        };
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {
            "idle", "walk", "talk", "gesture", "emote", "action"
        };
    }
    
private:
    bool m_initialized;
    float m_animTime;
    float m_expression;
    float m_pose;
    float m_emotion;
    float m_action;
    std::unordered_map<std::string, std::any> m_customParams;
};

// NEW: Pipeline Registration Function
void registerDefaultPipelines() {
    auto& factory = PipelineFactory::getInstance();
    
    // Register MechPipeline
    factory.registerPipeline("mech", []() -> std::unique_ptr<IPipeline> {
        return std::make_unique<MechPipeline>();
    });
    
    // Register CharacterPipeline
    factory.registerPipeline("character", []() -> std::unique_ptr<IPipeline> {
        return std::make_unique<CharacterPipeline>();
    });
}

// ---------------------------------------------------------------------------
// AnimationAssembler
// ---------------------------------------------------------------------------
AnimationAssembler::AnimationAssembler()
    : m_initialized(false)
    , m_enableOptimization(true)
    , m_enableCompression(false)
    , m_compressionQuality(0.8f)
    , m_enableStarboundCompatibility(true)
{
    initialize();
}

AnimationAssembler::~AnimationAssembler() {
    shutdown();
}

void AnimationAssembler::initialize() {
    m_lastError.clear();
    m_initialized = true;
}

void AnimationAssembler::shutdown() {
    m_initialized = false;
}

AnimationBundle AnimationAssembler::assembleAnimation(const std::vector<ImageBundle>& frames,
                                                      const AnimationParams& params) {
    AnimationBundle bundle;
    if (!validateAnimationFrames(frames, params)) {
        return bundle;
    }
    if (m_enableStarboundCompatibility && params.starboundCompatible && !validateStarboundCompatibility(params)) {
        m_lastError = "Animation parameters are not Starbound compatible";
        return bundle;
    }

    const std::vector<ImageBundle> processed = processAnimationFrames(frames, params);
    int cols = 1, rows = 1;
    animationGrid(static_cast<int>(processed.size()), cols, rows);

    // Place frames into their sheet cells according to the frame order
    const std::vector<int> cells = AnimationUtils::generateFrameIndices(
        static_cast<int>(processed.size()), params.frameOrder, cols, rows);
    std::vector<ImageBundle> ordered(static_cast<size_t>(cols) * rows);
    for (size_t i = 0; i < processed.size() && i < cells.size(); ++i) {
        ordered[static_cast<size_t>(cells[i])] = processed[i];
    }

    const int tileW = processed.empty() ? 0 : processed.front().image.width;
    const int tileH = processed.empty() ? 0 : processed.front().image.height;
    const float frameRate = params.frameDuration > 0.0f ? 1.0f / params.frameDuration : params.frameRate;
    SpritesheetAssembler sheets;
    bundle.spritesheet = sheets.assemble(ordered, cols, rows, tileW, tileH, 0, glm::vec4(0.0f), frameRate,
                                         params.looping, params.animationName.empty() ? params.id : params.animationName);

    bundle.starboundMetadata = generateStarboundMetadata(params);
    bundle.starboundMetadata.sheetCols = cols;
    bundle.starboundMetadata.sheetRows = rows;
    bundle.starboundMetadata.frameCount = static_cast<int>(processed.size());
    bundle.timeline = processTimeline(params);
    bundle.frameTimes = AnimationUtils::generateFrameTimes(static_cast<int>(processed.size()), params.frameDuration);
    bundle.frameIndices = cells;
    bundle.creationTime = std::chrono::system_clock::now();
    bundle.memoryUsage = bundle.spritesheet.combinedImage.byteSize();
    return bundle;
}

std::vector<ImageBundle> AnimationAssembler::processAnimationFrames(const std::vector<ImageBundle>& frames,
                                                                    const AnimationParams& params) {
    std::vector<ImageBundle> out;
    const size_t count = (params.frameCount > 0) ? std::min(frames.size(), static_cast<size_t>(params.frameCount))
                                                 : frames.size();
    out.reserve(count);
    ImageAssembler images;
    int tileW = 0, tileH = 0;
    for (size_t i = 0; i < count; ++i) {
        ImageBundle frame = frames[i];
        if (!frame.image.empty()) {
            frame.image = images.toRGBA(frame.image);
            if (tileW == 0) { tileW = frame.image.width; tileH = frame.image.height; }
            // Normalise every frame to the size of the first one
            if (frame.image.width != tileW || frame.image.height != tileH) {
                frame.image = images.resize(frame.image, tileW, tileH);
            }
        }
        frame.metadata.frameIndex = static_cast<int>(i);
        frame.metadata.timestamp = static_cast<float>(i) * params.frameDuration;
        frame.metadata.customData["animation_time"] = frame.metadata.timestamp;
        frame.metadata.customData["frame_index"] = static_cast<double>(i);
        frame.metadata.customData["frame_duration"] = params.frameDuration;
        out.push_back(std::move(frame));
    }
    if (m_enableOptimization && params.mode == AnimationMode::SINGLE_FRAME && out.size() > 1) {
        out.resize(1);
    }
    return out;
}

std::vector<int> AnimationAssembler::generateFrameIndices(const AnimationParams& params) {
    int cols = 1, rows = 1;
    animationGrid(params.frameCount, cols, rows);
    return AnimationUtils::generateFrameIndices(params.frameCount, params.frameOrder, cols, rows);
}

std::vector<float> AnimationAssembler::generateFrameTimes(const AnimationParams& params) {
    return AnimationUtils::generateFrameTimes(params.frameCount, params.frameDuration);
}

AnimationTimeline AnimationAssembler::processTimeline(const AnimationParams& params) {
    AnimationTimeline timeline = params.timeline;
    timeline.keyframes = sortKeyframesByTime(timeline.keyframes);
    timeline.tracks.clear();
    timeline.trackNames.clear();
    for (const auto& kf : timeline.keyframes) {
        if (timeline.tracks.find(kf.trackName) == timeline.tracks.end()) {
            timeline.trackNames.push_back(kf.trackName);
        }
        timeline.tracks[kf.trackName].push_back(kf);
    }
    if (timeline.duration <= 0.0f) {
        timeline.duration = params.useTimeline ? params.timelineDuration
                                               : static_cast<float>(params.frameCount) * params.frameDuration;
    }
    if (timeline.frameRate <= 0.0f) {
        timeline.frameRate = params.frameRate;
    }
    if (timeline.id.empty()) {
        timeline.id = params.id + "_timeline";
    }
    if (!validateTimelineData(timeline)) {
        m_lastError = "Timeline contains keyframes outside its duration";
    }
    return timeline;
}

float AnimationAssembler::evaluateTimelineAtTime(const AnimationTimeline& timeline, float time, const std::string& trackName) {
    return AnimationUtils::evaluateTimeline(timeline, time, trackName);
}

TimelineKeyframe AnimationAssembler::interpolateKeyframes(const TimelineKeyframe& k1, const TimelineKeyframe& k2, float t) {
    return AnimationUtils::interpolateKeyframes(k1, k2, t);
}

StarboundAnimationMetadata AnimationAssembler::generateStarboundMetadata(const AnimationParams& params) {
    return AnimationUtils::createStarboundMetadata(params);
}

std::string AnimationAssembler::generateStarboundAnimationJSON(const StarboundAnimationMetadata& metadata) {
    return AnimationUtils::generateStarboundAnimationJSON(metadata);
}

bool AnimationAssembler::validateStarboundCompatibility(const AnimationParams& params) {
    return AnimationUtils::validateStarboundCompatibility(params);
}

bool AnimationAssembler::exportAnimationJSON(const AnimationBundle& bundle, const std::string& outputPath) {
    nlohmann::json j = nlohmann::json::parse(AnimationUtils::generateStarboundAnimationJSON(bundle.starboundMetadata));
    if (!bundle.frameIndices.empty()) {
        j["frames"] = bundle.frameIndices;
    }
    if (!bundle.spritesheetPath.empty()) {
        j["spritesheet"] = std::filesystem::path(bundle.spritesheetPath).filename().string();
    }
    if (!bundle.timeline.keyframes.empty()) {
        j["timeline"] = timelineToJson(bundle.timeline);
    }
    return writeTextFile(outputPath, j.dump(2), m_lastError);
}

bool AnimationAssembler::exportTimelineData(const AnimationBundle& bundle, const std::string& outputPath) {
    nlohmann::json j = timelineToJson(bundle.timeline);
    j["frameTimes"] = bundle.frameTimes;
    j["frameIndices"] = bundle.frameIndices;
    return writeTextFile(outputPath, j.dump(2), m_lastError);
}

bool AnimationAssembler::exportIndividualFrames(const AnimationBundle& bundle, const std::string& outputDir) {
    const SpritesheetBundle& sheet = bundle.spritesheet;
    if (sheet.combinedImage.empty()) {
        m_lastError = "Animation has no spritesheet image";
        return false;
    }
    std::error_code ec;
    std::filesystem::create_directories(outputDir, ec);
    ImageAssembler images;
    ImageWriter writer;
    const std::string base = bundle.starboundMetadata.name.empty() ? std::string("frame") : bundle.starboundMetadata.name;
    for (size_t i = 0; i < sheet.frameBounds.size(); ++i) {
        const glm::vec4& b = sheet.frameBounds[i];
        const ImageData frame = images.crop(sheet.combinedImage, static_cast<int>(b.x), static_cast<int>(b.y),
                                            static_cast<int>(b.z), static_cast<int>(b.w));
        const std::string path = (std::filesystem::path(outputDir) / (base + "_" + std::to_string(i) + ".png")).string();
        if (!writer.write(frame, path, ImageFormat::PNG)) {
            m_lastError = writer.lastError();
            return false;
        }
    }
    return true;
}

bool AnimationAssembler::validateAnimationFrames(const std::vector<ImageBundle>& frames, const AnimationParams& params) {
    if (frames.empty()) {
        m_lastError = "No frames to assemble";
        return false;
    }
    if (params.frameCount > 0 && static_cast<int>(frames.size()) < params.frameCount &&
        params.mode == AnimationMode::ANIMATED_SEQUENCE) {
        m_lastError = "Expected " + std::to_string(params.frameCount) + " frames but got " + std::to_string(frames.size());
        return false;
    }
    if (params.frameDuration <= 0.0f && params.mode == AnimationMode::ANIMATED_SEQUENCE) {
        m_lastError = "Frame duration must be positive";
        return false;
    }
    return true;
}

bool AnimationAssembler::validateTimelineData(const AnimationTimeline& timeline) {
    float previous = -1.0f;
    for (const auto& kf : timeline.keyframes) {
        if (kf.time < 0.0f || kf.time < previous) return false;
        if (timeline.duration > 0.0f && kf.time > timeline.duration + 1e-4f) return false;
        previous = kf.time;
    }
    return true;
}

std::vector<TimelineKeyframe> AnimationAssembler::sortKeyframesByTime(const std::vector<TimelineKeyframe>& keyframes) {
    std::vector<TimelineKeyframe> sorted = keyframes;
    std::stable_sort(sorted.begin(), sorted.end(),
                     [](const TimelineKeyframe& a, const TimelineKeyframe& b) { return a.time < b.time; });
    return sorted;
}

// ---------------------------------------------------------------------------
// AnimationUtils
// ---------------------------------------------------------------------------
namespace AnimationUtils {

std::vector<TimelineKeyframe> getKeyframesForTrack(const AnimationTimeline& timeline, const std::string& trackName) {
    std::vector<TimelineKeyframe> result;
    auto it = timeline.tracks.find(trackName);
    if (it != timeline.tracks.end() && !it->second.empty()) {
        result = it->second;
    } else {
        for (const auto& kf : timeline.keyframes) {
            if (kf.trackName == trackName) result.push_back(kf);
        }
    }
    std::stable_sort(result.begin(), result.end(),
                     [](const TimelineKeyframe& a, const TimelineKeyframe& b) { return a.time < b.time; });
    return result;
}

TimelineKeyframe interpolateKeyframes(const TimelineKeyframe& k1, const TimelineKeyframe& k2, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    TimelineKeyframe out = k1;
    out.time = k1.time + (k2.time - k1.time) * t;
    if (k1.interpolation == "step") {
        out.value = (t < 1.0f) ? k1.value : k2.value;
        return out;
    }
    const float eased = (k1.interpolation == "ease") ? t * t * (3.0f - 2.0f * t) : t;
    const bool numeric1 = k1.value.has_value() && (k1.value.type() == typeid(float) || k1.value.type() == typeid(double) ||
                                                   k1.value.type() == typeid(int) || k1.value.type() == typeid(bool));
    const bool numeric2 = k2.value.has_value() && (k2.value.type() == typeid(float) || k2.value.type() == typeid(double) ||
                                                   k2.value.type() == typeid(int) || k2.value.type() == typeid(bool));
    if (numeric1 && numeric2) {
        const float a = anyToFloat(k1.value);
        const float b = anyToFloat(k2.value);
        out.value = a + (b - a) * eased;
    } else {
        out.value = (eased < 0.5f) ? k1.value : k2.value;
    }
    return out;
}

float evaluateTimeline(const AnimationTimeline& timeline, float time, const std::string& trackName) {
    const std::vector<TimelineKeyframe> keys = getKeyframesForTrack(timeline, trackName);
    if (keys.empty()) {
        return 0.0f;
    }
    if (timeline.looping && timeline.duration > 0.0f) {
        time = std::fmod(time, timeline.duration);
        if (time < 0.0f) time += timeline.duration;
    }
    if (time <= keys.front().time) return anyToFloat(keys.front().value);
    if (time >= keys.back().time) return anyToFloat(keys.back().value);
    for (size_t i = 1; i < keys.size(); ++i) {
        if (time <= keys[i].time) {
            const TimelineKeyframe& k1 = keys[i - 1];
            const TimelineKeyframe& k2 = keys[i];
            const float span = k2.time - k1.time;
            const float t = span > 0.0f ? (time - k1.time) / span : 1.0f;
            return anyToFloat(interpolateKeyframes(k1, k2, t).value);
        }
    }
    return anyToFloat(keys.back().value);
}

std::vector<int> generateFrameIndices(int frameCount, FrameOrder order, int cols, int rows) {
    std::vector<int> indices;
    if (frameCount <= 0) return indices;
    cols = std::max(1, cols);
    rows = std::max(1, rows);
    const int capacity = cols * rows;
    indices.reserve(static_cast<size_t>(std::min(frameCount, capacity)));
    for (int i = 0; i < frameCount && i < capacity; ++i) {
        if (order == FrameOrder::COLUMN_MAJOR) {
            const int col = i / rows;
            const int row = i % rows;
            indices.push_back(row * cols + col);
        } else {
            indices.push_back(i);
        }
    }
    return indices;
}

std::vector<float> generateFrameTimes(int frameCount, float frameDuration) {
    std::vector<float> times;
    if (frameCount <= 0) return times;
    times.reserve(static_cast<size_t>(frameCount));
    for (int i = 0; i < frameCount; ++i) {
        times.push_back(static_cast<float>(i) * frameDuration);
    }
    return times;
}

int calculateFrameIndex(float time, float frameDuration, int frameCount) {
    if (frameDuration <= 0.0f || frameCount <= 0) return 0;
    int index = static_cast<int>(std::floor(time / frameDuration)) % frameCount;
    if (index < 0) index += frameCount;
    return index;
}

std::string generateStarboundAnimationJSON(const StarboundAnimationMetadata& metadata) {
    nlohmann::json j;
    j["frames"] = nlohmann::json::array();
    for (int i = 0; i < metadata.frameCount; ++i) {
        j["frames"].push_back(i);
    }
    j["frameTime"] = metadata.frameTime;
    j["loop"] = metadata.loop;
    j["sheetCols"] = metadata.sheetCols;
    j["sheetRows"] = metadata.sheetRows;
    j["order"] = metadata.order;
    j["name"] = metadata.name;
    j["category"] = metadata.category;
    j["type"] = metadata.type;
    j["description"] = metadata.description;
    j["author"] = metadata.author;
    j["version"] = metadata.version;
    return j.dump(2);
}

StarboundAnimationMetadata createStarboundMetadata(const AnimationParams& params) {
    StarboundAnimationMetadata metadata;
    metadata.name = params.animationName;
    metadata.category = params.starboundCategory;
    metadata.type = params.starboundType;
    metadata.frameCount = params.frameCount;
    metadata.frameTime = params.frameDuration;
    metadata.loop = params.looping;
    animationGrid(params.frameCount, metadata.sheetCols, metadata.sheetRows);
    metadata.order = (params.frameOrder == FrameOrder::ROW_MAJOR) ? "row-major" : "column-major";
    metadata.description = "Generated by MagiTech Animation Generator";
    metadata.author = "MagiTech";
    metadata.version = "1.0.0";
    metadata.creationTime = std::chrono::system_clock::now();
    return metadata;
}

bool validateStarboundCompatibility(const AnimationParams& params) {
    if (params.frameCount <= 0 || params.frameCount > 1000) return false;
    if (params.mode == AnimationMode::ANIMATED_SEQUENCE && params.frameDuration <= 0.0f) return false;
    if (params.animationName.empty()) return false;
    // Starbound state / frame names: no whitespace or path separators
    for (char ch : params.animationName) {
        if (std::isspace(static_cast<unsigned char>(ch)) || ch == '/' || ch == '\\' || ch == ':') return false;
    }
    return true;
}

std::string getAnimationModeString(AnimationMode mode) {
    switch (mode) {
        case AnimationMode::SINGLE_FRAME: return "single_frame";
        case AnimationMode::ANIMATED_SEQUENCE: return "animated_sequence";
    }
    return "animated_sequence";
}

AnimationMode getAnimationModeFromString(const std::string& str) {
    const std::string s = Utils::toLower(str);
    if (s == "single_frame" || s == "single frame" || s == "single") return AnimationMode::SINGLE_FRAME;
    return AnimationMode::ANIMATED_SEQUENCE;
}

std::string getFrameOrderString(FrameOrder order) {
    return order == FrameOrder::COLUMN_MAJOR ? "column-major" : "row-major";
}

FrameOrder getFrameOrderFromString(const std::string& str) {
    const std::string s = Utils::toLower(str);
    if (s == "column-major" || s == "column_major" || s == "column major" || s == "columns") return FrameOrder::COLUMN_MAJOR;
    return FrameOrder::ROW_MAJOR;
}

std::string getTimelineTrackTypeString(TimelineTrackType type) {
    switch (type) {
        case TimelineTrackType::MORPH_WEIGHT: return "morph_weight";
        case TimelineTrackType::MODULE_VISIBILITY: return "module_visibility";
        case TimelineTrackType::LOD_CHANGE: return "lod_change";
        case TimelineTrackType::WEAPON_FIRE: return "weapon_fire";
        case TimelineTrackType::EFFECTS: return "effects";
        case TimelineTrackType::CUSTOM: return "custom";
    }
    return "custom";
}

TimelineTrackType getTimelineTrackTypeFromString(const std::string& str) {
    const std::string s = Utils::toLower(str);
    if (s == "morph_weight") return TimelineTrackType::MORPH_WEIGHT;
    if (s == "module_visibility") return TimelineTrackType::MODULE_VISIBILITY;
    if (s == "lod_change") return TimelineTrackType::LOD_CHANGE;
    if (s == "weapon_fire") return TimelineTrackType::WEAPON_FIRE;
    if (s == "effects") return TimelineTrackType::EFFECTS;
    return TimelineTrackType::CUSTOM;
}

std::string getAnimationExportFormatString(AnimationExportFormat format) {
    switch (format) {
        case AnimationExportFormat::STARBOUND_ANIMATION: return "starbound_animation";
        case AnimationExportFormat::GENERIC_JSON: return "generic_json";
        case AnimationExportFormat::CUSTOM_FORMAT: return "custom_format";
    }
    return "starbound_animation";
}

AnimationExportFormat getAnimationExportFormatFromString(const std::string& str) {
    const std::string s = Utils::toLower(str);
    if (s == "generic_json" || s == "json") return AnimationExportFormat::GENERIC_JSON;
    if (s == "custom_format" || s == "custom") return AnimationExportFormat::CUSTOM_FORMAT;
    return AnimationExportFormat::STARBOUND_ANIMATION;
}

} // namespace AnimationUtils

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------
namespace Utils {

std::string formatToString(ImageFormat format) {
    switch (format) {
        case ImageFormat::PNG: return "png";
        case ImageFormat::JPG: return "jpg";
        case ImageFormat::BMP: return "bmp";
        case ImageFormat::TGA: return "tga";
        case ImageFormat::HDR: return "hdr";
    }
    return "png";
}

ImageFormat stringToFormat(const std::string& str) {
    std::string s = toLower(trim(str));
    if (!s.empty() && s[0] == '.') s.erase(0, 1);
    if (s == "jpg" || s == "jpeg") return ImageFormat::JPG;
    if (s == "bmp") return ImageFormat::BMP;
    if (s == "tga") return ImageFormat::TGA;
    if (s == "hdr") return ImageFormat::HDR;
    return ImageFormat::PNG;
}

std::string qualityToString(ImageQuality quality) {
    switch (quality) {
        case ImageQuality::ULTRA_LOW: return "ultra_low";
        case ImageQuality::LOW: return "low";
        case ImageQuality::MEDIUM: return "medium";
        case ImageQuality::HIGH: return "high";
        case ImageQuality::ULTRA_HIGH: return "ultra_high";
    }
    return "high";
}

ImageQuality stringToQuality(const std::string& str) {
    const std::string s = toLower(trim(str));
    if (s == "ultra_low" || s == "ultra low") return ImageQuality::ULTRA_LOW;
    if (s == "low") return ImageQuality::LOW;
    if (s == "medium") return ImageQuality::MEDIUM;
    if (s == "ultra_high" || s == "ultra high") return ImageQuality::ULTRA_HIGH;
    return ImageQuality::HIGH;
}

std::string layoutToString(SpritesheetLayout layout) {
    switch (layout) {
        case SpritesheetLayout::GRID: return "grid";
        case SpritesheetLayout::HORIZONTAL: return "horizontal";
        case SpritesheetLayout::VERTICAL: return "vertical";
        case SpritesheetLayout::CUSTOM: return "custom";
    }
    return "grid";
}

SpritesheetLayout stringToLayout(const std::string& str) {
    const std::string s = toLower(trim(str));
    if (s == "horizontal") return SpritesheetLayout::HORIZONTAL;
    if (s == "vertical") return SpritesheetLayout::VERTICAL;
    if (s == "custom") return SpritesheetLayout::CUSTOM;
    return SpritesheetLayout::GRID;
}

std::string paddingStyleToString(PaddingStyle style) {
    switch (style) {
        case PaddingStyle::NONE: return "none";
        case PaddingStyle::SOLID: return "solid";
        case PaddingStyle::TRANSPARENT: return "transparent";
        case PaddingStyle::PATTERN: return "pattern";
        case PaddingStyle::GRADIENT: return "gradient";
    }
    return "transparent";
}

PaddingStyle stringToPaddingStyle(const std::string& str) {
    const std::string s = toLower(trim(str));
    if (s == "none") return PaddingStyle::NONE;
    if (s == "solid") return PaddingStyle::SOLID;
    if (s == "pattern") return PaddingStyle::PATTERN;
    if (s == "gradient") return PaddingStyle::GRADIENT;
    return PaddingStyle::TRANSPARENT;
}

std::string animationModeToString(AnimationMode mode) { return AnimationUtils::getAnimationModeString(mode); }
AnimationMode stringToAnimationMode(const std::string& str) { return AnimationUtils::getAnimationModeFromString(str); }
std::string frameOrderToString(FrameOrder order) { return AnimationUtils::getFrameOrderString(order); }
FrameOrder stringToFrameOrder(const std::string& str) { return AnimationUtils::getFrameOrderFromString(str); }
std::string timelineTrackTypeToString(TimelineTrackType type) { return AnimationUtils::getTimelineTrackTypeString(type); }
TimelineTrackType stringToTimelineTrackType(const std::string& str) { return AnimationUtils::getTimelineTrackTypeFromString(str); }
std::string animationExportFormatToString(AnimationExportFormat format) { return AnimationUtils::getAnimationExportFormatString(format); }
AnimationExportFormat stringToAnimationExportFormat(const std::string& str) { return AnimationUtils::getAnimationExportFormatFromString(str); }

bool fileExists(const std::string& filePath) {
    std::error_code ec;
    return std::filesystem::is_regular_file(filePath, ec);
}

bool createDirectory(const std::string& dirPath) {
    std::error_code ec;
    if (std::filesystem::is_directory(dirPath, ec)) return true;
    return std::filesystem::create_directories(dirPath, ec);
}

std::string getFileExtension(const std::string& filePath) {
    return std::filesystem::path(filePath).extension().string();
}

std::string getFileName(const std::string& filePath) {
    return std::filesystem::path(filePath).filename().string();
}

std::string getDirectory(const std::string& filePath) {
    return std::filesystem::path(filePath).parent_path().string();
}

bool isValidImageSize(int width, int height) {
    return width > 0 && height > 0 && width <= 8192 && height <= 8192;
}

bool isValidSpritesheetSize(int cols, int rows, int tileW, int tileH) {
    return cols > 0 && rows > 0 && tileW > 0 && tileH > 0 &&
           static_cast<long long>(cols) * tileW <= 8192 && static_cast<long long>(rows) * tileH <= 8192;
}

glm::vec2 calculateAspectRatio(int width, int height) {
    if (width <= 0 || height <= 0) return glm::vec2(0.0f);
    const int g = std::gcd(width, height);
    return glm::vec2(static_cast<float>(width / g), static_cast<float>(height / g));
}

float calculateAspectRatioFloat(int width, int height) {
    return height > 0 ? static_cast<float>(width) / static_cast<float>(height) : 0.0f;
}

bool isValidAnimationFrameCount(int frameCount) { return frameCount > 0 && frameCount <= 1000; }
bool isValidAnimationDuration(float duration) { return duration > 0.0f && duration <= 60.0f; }
bool isValidAnimationFrameRate(float frameRate) { return frameRate > 0.0f && frameRate <= 240.0f; }

int calculateOptimalFrameCount(float duration, float frameRate) {
    if (duration <= 0.0f || frameRate <= 0.0f) return 1;
    return std::clamp(static_cast<int>(std::lround(duration * frameRate)), 1, 1000);
}

glm::vec4 hexToColor(const std::string& hex) {
    std::string s = trim(hex);
    if (!s.empty() && s[0] == '#') s.erase(0, 1);
    if (s.size() == 3 || s.size() == 4) {  // short form #rgb / #rgba
        std::string expanded;
        for (char ch : s) { expanded += ch; expanded += ch; }
        s = expanded;
    }
    if (s.size() != 6 && s.size() != 8) return glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    auto component = [&](size_t i) -> float {
        try { return static_cast<float>(std::stoi(s.substr(i, 2), nullptr, 16)) / 255.0f; }
        catch (const std::exception&) { return 0.0f; }
    };
    return glm::vec4(component(0), component(2), component(4), s.size() == 8 ? component(6) : 1.0f);
}

std::string colorToHex(const glm::vec4& color) {
    std::ostringstream oss;
    oss << '#' << std::hex << std::setfill('0')
        << std::setw(2) << static_cast<int>(toByte(color.r))
        << std::setw(2) << static_cast<int>(toByte(color.g))
        << std::setw(2) << static_cast<int>(toByte(color.b))
        << std::setw(2) << static_cast<int>(toByte(color.a));
    return oss.str();
}

glm::vec4 blendColors(const glm::vec4& color1, const glm::vec4& color2, float factor) {
    return color1 + (color2 - color1) * std::clamp(factor, 0.0f, 1.0f);
}

std::string toLower(const std::string& str) {
    std::string out = str;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return out;
}

std::string toUpper(const std::string& str) {
    std::string out = str;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
    return out;
}

std::string trim(const std::string& str) {
    const auto first = std::find_if_not(str.begin(), str.end(), [](unsigned char ch) { return std::isspace(ch) != 0; });
    const auto last = std::find_if_not(str.rbegin(), str.rend(), [](unsigned char ch) { return std::isspace(ch) != 0; }).base();
    return (first < last) ? std::string(first, last) : std::string();
}

std::vector<std::string> split(const std::string& str, char delimiter) {
    std::vector<std::string> parts;
    std::string current;
    std::istringstream iss(str);
    while (std::getline(iss, current, delimiter)) {
        parts.push_back(current);
    }
    if (!str.empty() && str.back() == delimiter) {
        parts.emplace_back();
    }
    return parts;
}

std::string join(const std::vector<std::string>& strings, const std::string& delimiter) {
    std::string out;
    for (size_t i = 0; i < strings.size(); ++i) {
        if (i > 0) out += delimiter;
        out += strings[i];
    }
    return out;
}

std::string getCurrentTimestamp() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
#ifdef _WIN32
    localtime_s(&tm, &t);
#else
    localtime_r(&t, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

std::string formatDuration(std::chrono::milliseconds duration) {
    const long long ms = duration.count();
    std::ostringstream oss;
    if (ms < 1000) {
        oss << ms << "ms";
    } else if (ms < 60000) {
        oss << std::fixed << std::setprecision(2) << (ms / 1000.0) << "s";
    } else {
        oss << (ms / 60000) << "m " << ((ms % 60000) / 1000) << "s";
    }
    return oss.str();
}

std::string formatFileSize(size_t bytes) {
    const char* units[] = { "B", "KB", "MB", "GB", "TB" };
    double size = static_cast<double>(bytes);
    int unit = 0;
    while (size >= 1024.0 && unit < 4) {
        size /= 1024.0;
        ++unit;
    }
    std::ostringstream oss;
    if (unit == 0) oss << bytes << " B";
    else oss << std::fixed << std::setprecision(2) << size << " " << units[unit];
    return oss.str();
}

bool isValidFilename(const std::string& filename) {
    if (filename.empty() || filename.size() > 255) return false;
    const std::string invalid = "<>:\"/\\|?*";
    for (char ch : filename) {
        if (invalid.find(ch) != std::string::npos || static_cast<unsigned char>(ch) < 32) return false;
    }
    return filename != "." && filename != "..";
}

bool isValidPath(const std::string& path) {
    if (path.empty() || path.size() >= 1024) return false;
    const std::string invalid = "<>\"|?*";
    for (char ch : path) {
        if (invalid.find(ch) != std::string::npos || static_cast<unsigned char>(ch) < 32) return false;
    }
    return true;
}

bool isSupportedFormat(const std::string& extension) {
    std::string s = toLower(extension);
    if (!s.empty() && s[0] == '.') s.erase(0, 1);
    return s == "png" || s == "jpg" || s == "jpeg" || s == "bmp" || s == "tga" || s == "hdr";
}

bool isValidAnimationFilename(const std::string& filename) {
    return isValidFilename(filename) && std::filesystem::path(filename).extension() == ".animation";
}

bool isValidAnimationPath(const std::string& path) {
    return isValidPath(path) && std::filesystem::path(path).extension() == ".animation";
}

bool isSupportedAnimationFormat(const std::string& extension) {
    std::string s = toLower(extension);
    if (!s.empty() && s[0] == '.') s.erase(0, 1);
    return s == "animation" || s == "json" || s == "frames";
}

} // namespace Utils

} // namespace ImageGen
} // namespace MagiTech 
