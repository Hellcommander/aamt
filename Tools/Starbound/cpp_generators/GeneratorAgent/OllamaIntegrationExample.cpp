// OllamaIntegrationExample.cpp
// Shows how OllamaClient plugs into the procedural ImageGenerator: a text description is
// enhanced by Ollama (rewritten prompt + extracted palette / style hints) and the result
// is applied to an image produced by ImageGenerator::generateImage.

#include "OllamaIntegrationExample.hpp"
#include "ImageGenerator.hpp"
#include "core/Log.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <format>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

namespace MagiTech {
namespace ImageGen {
namespace Examples {

namespace {

constexpr const char* kLogCategory = "OllamaExample";

// How strongly the extracted palette tints covered pixels.
constexpr float kPaletteTintStrength = 0.35f;

std::uint8_t toChannelByte(float value) {
    return static_cast<std::uint8_t>(std::clamp(value, 0.0f, 1.0f) * 255.0f + 0.5f);
}

glm::vec4 paletteColorAt(const std::vector<glm::vec4>& palette, float t) {
    if (palette.size() == 1) {
        return palette.front();
    }
    const float scaled = std::clamp(t, 0.0f, 1.0f) * static_cast<float>(palette.size() - 1);
    const size_t index = std::min(static_cast<size_t>(scaled), palette.size() - 2);
    return Utils::blendColors(palette[index], palette[index + 1], scaled - static_cast<float>(index));
}

std::string joinHex(const std::vector<glm::vec4>& palette) {
    std::vector<std::string> hex;
    hex.reserve(palette.size());
    for (const auto& color : palette) {
        hex.push_back(Utils::colorToHex(color));
    }
    return Utils::join(hex, ",");
}

bool writeSidecarJson(const std::filesystem::path& path, const ImageBundle& bundle,
                      const PromptEnhancement& enhancement) {
    nlohmann::json palette = nlohmann::json::array();
    for (const auto& color : enhancement.palette) {
        palette.push_back(Utils::colorToHex(color));
    }

    const nlohmann::json sidecar = {
        {"id", bundle.metadata.id},
        {"width", bundle.image.width},
        {"height", bundle.image.height},
        {"checksum", bundle.metadata.checksum},
        {"source", bundle.metadata.source},
        {"originalDescription", enhancement.originalDescription},
        {"description", enhancement.description},
        {"enhanced", enhancement.wasEnhanced},
        {"model", enhancement.model},
        {"style", enhancement.style},
        {"palette", palette},
        {"hasGradient", enhancement.hasGradient},
        {"hasPattern", enhancement.hasPattern},
        {"hasSparkles", enhancement.hasSparkles},
    };

    std::ofstream file(path, std::ios::trunc);
    if (!file) {
        return false;
    }
    file << sidecar.dump(2) << '\n';
    return static_cast<bool>(file);
}

} // namespace

PromptEnhancement enhancePromptWithOllama(const GeneratorAgent::OllamaClient& client,
                                          const std::string& description) {
    PromptEnhancement result;
    result.originalDescription = description;
    result.description = description;
    result.model = client.getConfig().model;

    if (description.empty()) {
        return result;
    }

    result.ollamaAvailable = client.isAvailable();
    if (!result.ollamaAvailable) {
        Log::warn(kLogCategory, "Ollama not reachable at {}; using the description as written",
                  client.getConfig().url);
        return result;
    }

    const auto enhancement = client.enhance(description);
    if (!enhancement) {
        Log::warn(kLogCategory, "Ollama returned no enhancement for \"{}\"", description);
        return result;
    }

    if (enhancement->description.wasEnhanced && !enhancement->description.enhanced.empty()) {
        result.description = enhancement->description.enhanced;
        result.wasEnhanced = true;
    }

    const auto& extracted = enhancement->parameters;
    for (const auto& rgb : extracted.colorPalette) {
        if (rgb.size() >= 3) {
            result.palette.emplace_back(std::clamp(rgb[0], 0, 255) / 255.0f,
                                        std::clamp(rgb[1], 0, 255) / 255.0f,
                                        std::clamp(rgb[2], 0, 255) / 255.0f, 1.0f);
        }
    }
    result.style = extracted.style;
    result.hasGradient = extracted.hasGradient;
    result.hasPattern = extracted.hasPattern;
    result.hasSparkles = extracted.hasSparkles;

    Log::info(kLogCategory, "Enhanced \"{}\" -> \"{}\"", result.originalDescription, result.description);
    if (!result.palette.empty()) {
        Log::info(kLogCategory, "  palette: {}", joinHex(result.palette));
    }
    if (!result.style.empty()) {
        Log::info(kLogCategory, "  style: {} (gradient {}, pattern {}, sparkles {})", result.style,
                  result.hasGradient, result.hasPattern, result.hasSparkles);
    }
    return result;
}

void applyPromptEnhancement(ImageBundle& bundle, const PromptEnhancement& enhancement) {
    // Palette tint over every covered pixel
    ImageData& image = bundle.image;
    if (!enhancement.palette.empty() && !image.empty() && image.channels >= 3) {
        const int channels = image.channels;
        for (int y = 0; y < image.height; ++y) {
            const float t = image.height > 1 ? static_cast<float>(y) / static_cast<float>(image.height - 1) : 0.0f;
            const glm::vec4 tint = enhancement.hasGradient ? paletteColorAt(enhancement.palette, t)
                                                           : enhancement.palette.front();
            for (int x = 0; x < image.width; ++x) {
                const size_t offset = static_cast<size_t>(y) * image.stride() + static_cast<size_t>(x) * channels;
                if (channels == 4 && image.data[offset + 3] == 0) {
                    continue;  // leave transparent background untouched
                }
                const glm::vec4 source(image.data[offset] / 255.0f, image.data[offset + 1] / 255.0f,
                                       image.data[offset + 2] / 255.0f, 1.0f);
                const glm::vec4 tinted = Utils::blendColors(source, tint, kPaletteTintStrength);
                image.data[offset] = toChannelByte(tinted.r);
                image.data[offset + 1] = toChannelByte(tinted.g);
                image.data[offset + 2] = toChannelByte(tinted.b);
            }
        }
    }

    // Metadata
    ImageMetadata& meta = bundle.metadata;
    meta.title = enhancement.originalDescription;
    meta.description = enhancement.description;
    meta.source = enhancement.wasEnhanced ? "ollama:" + enhancement.model : "procedural";

    std::vector<std::string> tags;
    if (!enhancement.style.empty()) tags.push_back(enhancement.style);
    if (enhancement.hasGradient) tags.push_back("gradient");
    if (enhancement.hasPattern) tags.push_back("pattern");
    if (enhancement.hasSparkles) tags.push_back("sparkles");
    meta.tags = Utils::join(tags, ",");

    meta.customFields["original_description"] = enhancement.originalDescription;
    meta.customFields["ollama_available"] = enhancement.ollamaAvailable ? "true" : "false";
    meta.customFields["ollama_enhanced"] = enhancement.wasEnhanced ? "true" : "false";
    if (!enhancement.style.empty()) meta.customFields["style"] = enhancement.style;
    if (!enhancement.palette.empty()) meta.customFields["palette"] = joinHex(enhancement.palette);

    // Pixels may have changed: keep the checksum in step with the data
    meta.fileSize = image.byteSize();
    meta.checksum = std::format("{:016x}", static_cast<std::uint64_t>(XXH64(image.data.data(), image.data.size(), 0)));
}

ImageBundle generateImageWithOllama(ImageGenerator& generator,
                                    const GeneratorAgent::OllamaClient& client,
                                    const ImageParams& params,
                                    const std::string& description,
                                    PromptEnhancement* appliedEnhancement) {
    PromptEnhancement enhancement = enhancePromptWithOllama(client, description);

    ImageBundle bundle = generator.generateImage(params);
    if (!bundle.image.empty()) {
        applyPromptEnhancement(bundle, enhancement);
    }

    if (appliedEnhancement) {
        *appliedEnhancement = std::move(enhancement);
    }
    return bundle;
}

int runOllamaIntegrationExample(const std::string& outputDirectory) {
    try {
        GeneratorAgent::OllamaClient::Config config;
        config.url = "http://localhost:11434";
        config.model = "llama3.2";
        config.enabled = true;
        const GeneratorAgent::OllamaClient client(config);

        const bool available = client.isAvailable();
        Log::info(kLogCategory, "Ollama at {} (model {}): {}", config.url, config.model,
                  available ? "available" : "not available, procedural fallback");

        // Standalone use of the client: the two calls that enhance() combines
        if (available) {
            const std::string sample = "A magical sword";
            if (const auto enhanced = client.enhanceDescription(sample); enhanced && enhanced->wasEnhanced) {
                Log::info(kLogCategory, "enhanceDescription: \"{}\" -> \"{}\"", enhanced->original, enhanced->enhanced);
            }
            if (const auto extracted = client.extractParameters(sample)) {
                Log::info(kLogCategory, "extractParameters: style \"{}\", {} palette colours", extracted->style,
                          extracted->colorPalette.size());
            }
        }

        // Generation through the real ImageGenerator
        ImageGenerator generator;
        generator.setAsyncProcessing(false);
        if (!generator.initialize()) {
            Log::error(kLogCategory, "ImageGenerator failed to initialize: {}", generator.getLastError());
            return 1;
        }

        const std::filesystem::path outputDir(outputDirectory);
        if (!Utils::createDirectory(outputDir.string())) {
            Log::error(kLogCategory, "Cannot create output directory {}", outputDir.string());
            generator.shutdown();
            return 1;
        }

        struct DescribedImage {
            std::string id;
            std::string description;
        };
        const std::vector<DescribedImage> requests = {
            {"ollama_arcane_mech", "A heavy arcane mech with glowing blue runes"},
            {"ollama_ember_core", "A molten ember reactor core with orange to red heat"},
            {"ollama_frost_drone", "A small frost scout drone with crystalline wings"},
        };

        bool ok = true;
        for (const auto& request : requests) {
            ImageParams params;
            params.id = request.id;
            params.width = 128;
            params.height = 128;
            params.format = ImageFormat::PNG;
            params.quality = ImageQuality::HIGH;
            params.enableAlpha = true;

            std::string validationError;
            if (!generator.validateImageParams(params, validationError)) {
                Log::error(kLogCategory, "Invalid parameters for {}: {}", request.id, validationError);
                ok = false;
                continue;
            }

            PromptEnhancement enhancement;
            const ImageBundle bundle =
                generateImageWithOllama(generator, client, params, request.description, &enhancement);
            if (bundle.image.empty()) {
                Log::error(kLogCategory, "Generation of {} failed: {}", request.id, generator.getLastError());
                ok = false;
                continue;
            }

            const std::filesystem::path imagePath = outputDir / (request.id + ".png");
            const std::filesystem::path sidecarPath = outputDir / (request.id + ".json");
            if (!generator.saveImage(bundle, imagePath.string())) {
                Log::error(kLogCategory, "Saving {} failed: {}", imagePath.string(), generator.getLastError());
                ok = false;
                continue;
            }
            if (!writeSidecarJson(sidecarPath, bundle, enhancement)) {
                Log::error(kLogCategory, "Writing {} failed", sidecarPath.string());
                ok = false;
                continue;
            }
            Log::info(kLogCategory, "Wrote {} ({}x{}, source {}) and {}", imagePath.filename().string(),
                      bundle.image.width, bundle.image.height, bundle.metadata.source,
                      sidecarPath.filename().string());
        }

        generator.shutdown();
        return ok ? 0 : 1;
    } catch (const std::exception& e) {
        Log::error(kLogCategory, "Ollama integration example threw: {}", e.what());
        return 1;
    }
}

} // namespace Examples
} // namespace ImageGen
} // namespace MagiTech
