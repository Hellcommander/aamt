// OllamaIntegrationExample.cpp
// Example showing how to integrate OllamaClient into C++ generators

#include "OllamaClient.hpp"
#include "ImageGenerator.hpp"
#include "ImageTypes.hpp"
#include <iostream>

namespace MagiTech {
namespace ImageGen {

/**
 * @brief Example: Enhanced ImageGenerator::generateImage with Ollama integration
 * 
 * This shows how to integrate OllamaClient into the existing ImageGenerator
 * to enhance descriptions before procedural generation.
 */
ImageBundle ImageGenerator::generateImageWithOllama(const ImageParams& params) {
    // Create Ollama client
    GeneratorAgent::OllamaClient ollama;
    
    // Configure Ollama (optional - uses defaults if not set)
    GeneratorAgent::OllamaClient::Config config;
    config.url = "http://localhost:11434";
    config.model = "llama3.2";
    config.enabled = true;
    ollama.setConfig(config);
    
    // Check if Ollama is available
    if (!ollama.isAvailable()) {
        std::cout << "Ollama not available, using standard generation" << std::endl;
        return generateImage(params);  // Fallback to standard generation
    }
    
    // Enhance description if provided
    ImageParams enhancedParams = params;
    
    // Note: Assuming ImageParams has a description field
    // If not, you would need to add it or pass it separately
    if (!params.description.empty()) {
        auto enhancement = ollama.enhance(params.description);
        
        if (enhancement && enhancement->description.wasEnhanced) {
            std::cout << "✓ Description enhanced by Ollama" << std::endl;
            std::cout << "  Original: " << enhancement->description.original << std::endl;
            std::cout << "  Enhanced: " << enhancement->description.enhanced << std::endl;
            
            // Use enhanced description
            enhancedParams.description = enhancement->description.enhanced;
            
            // Apply extracted parameters if available
            const auto& extracted = enhancement->parameters;
            
            // Example: Apply color palette if extracted
            if (!extracted.colorPalette.empty()) {
                std::cout << "  Extracted color palette with " 
                          << extracted.colorPalette.size() << " colors" << std::endl;
                // You would apply these colors to your procedural generation here
            }
            
            // Example: Apply style hints
            if (!extracted.style.empty()) {
                std::cout << "  Extracted style: " << extracted.style << std::endl;
                // Apply style to generation parameters
            }
            
            if (extracted.hasGradient) {
                std::cout << "  Style hint: Has gradient" << std::endl;
            }
            
            if (extracted.hasPattern) {
                std::cout << "  Style hint: Has pattern" << std::endl;
            }
            
            if (extracted.hasSparkles) {
                std::cout << "  Style hint: Has sparkles" << std::endl;
            }
        }
    }
    
    // Continue with enhanced parameters
    return generateImage(enhancedParams);
}

/**
 * @brief Example: Using Ollama in a standalone function
 */
void exampleStandaloneUsage() {
    GeneratorAgent::OllamaClient ollama;
    
    // Check availability
    if (!ollama.isAvailable()) {
        std::cout << "Ollama is not available" << std::endl;
        return;
    }
    
    // Enhance a description
    std::string original = "A magical sword";
    auto enhanced = ollama.enhanceDescription(original);
    
    if (enhanced && enhanced->wasEnhanced) {
        std::cout << "Enhanced: " << enhanced->enhanced << std::endl;
    }
    
    // Extract parameters
    auto params = ollama.extractParameters(original);
    if (params) {
        std::cout << "Style: " << params->style << std::endl;
        std::cout << "Color palette size: " << params->colorPalette.size() << std::endl;
    }
}

} // namespace ImageGen
} // namespace MagiTech
