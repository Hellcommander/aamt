#pragma once

// Ollama prompt enhancement on top of the procedural ImageGenerator
// (OllamaIntegrationExample.cpp). Compiled into the backend, so the demonstration is
// exposed as runOllamaIntegrationExample() instead of main().

#include "ImageTypes.hpp"
#include "OllamaClient.hpp"

#include <string>
#include <vector>

namespace MagiTech {
namespace ImageGen {

class ImageGenerator;

namespace Examples {

// Result of running a text description through Ollama. When Ollama is unreachable or
// returns nothing usable, `description` is the original text and `wasEnhanced` is false.
struct PromptEnhancement {
    std::string originalDescription;
    std::string description;
    bool ollamaAvailable = false;
    bool wasEnhanced = false;
    std::string model;                 // Ollama model that produced the enhancement
    std::vector<glm::vec4> palette;    // extracted colours, RGBA in 0..1
    std::string style;
    bool hasGradient = false;
    bool hasPattern = false;
    bool hasSparkles = false;
};

// Prompt-enhancement step: asks `client` to rewrite `description` and extract palette /
// style hints from it.
PromptEnhancement enhancePromptWithOllama(const GeneratorAgent::OllamaClient& client,
                                          const std::string& description);

// Writes the enhancement into `bundle`: metadata (description, title, tags, source,
// custom fields, checksum) and, when a palette was extracted, a palette tint over the
// covered pixels (a vertical blend through the palette when a gradient was requested).
void applyPromptEnhancement(ImageBundle& bundle, const PromptEnhancement& enhancement);

// Enhance `description` with Ollama, generate the image with `generator`, then apply
// the enhancement to the result. Falls back to plain generation when Ollama is offline.
// When `appliedEnhancement` is non-null it receives the enhancement that was used.
ImageBundle generateImageWithOllama(ImageGenerator& generator,
                                    const GeneratorAgent::OllamaClient& client,
                                    const ImageParams& params,
                                    const std::string& description,
                                    PromptEnhancement* appliedEnhancement = nullptr);

// Runs the full demonstration (standalone enhancement + generation of a few described
// images, saved as PNG with a JSON sidecar under `outputDirectory`).
// Returns 0 on success and 1 if generation failed or threw.
int runOllamaIntegrationExample(const std::string& outputDirectory = "./ollama_output");

} // namespace Examples
} // namespace ImageGen
} // namespace MagiTech
