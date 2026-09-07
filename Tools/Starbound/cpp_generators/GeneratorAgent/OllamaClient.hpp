#pragma once

#include <string>
#include <optional>
#include <vector>
#include <memory>
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace GeneratorAgent {

/**
 * @brief Client for interacting with Ollama AI service
 * 
 * Provides methods to enhance descriptions and extract parameters
 * for improved procedural asset generation.
 */
class OllamaClient {
public:
    struct Config {
        std::string url = "http://localhost:11434";
        std::string model = "llama3.2";
        int timeoutSeconds = 30;
        bool enabled = true;
    };

    struct EnhancedDescription {
        std::string original;
        std::string enhanced;
        bool wasEnhanced = false;
    };

    struct ExtractedParameters {
        std::vector<std::vector<int>> colorPalette;  // RGB values
        std::string style;
        bool hasGradient = false;
        bool hasPattern = false;
        bool hasSparkles = false;
    };

    OllamaClient();
    explicit OllamaClient(const Config& config);
    ~OllamaClient();

    // Configuration
    void setConfig(const Config& config);
    const Config& getConfig() const { return m_config; }

    // Connection
    bool isAvailable() const;
    bool checkConnection() const;

    // Description enhancement
    std::optional<EnhancedDescription> enhanceDescription(const std::string& description) const;
    
    // Parameter extraction
    std::optional<ExtractedParameters> extractParameters(const std::string& description) const;
    
    // Combined enhancement (description + parameters)
    struct EnhancementResult {
        EnhancedDescription description;
        ExtractedParameters parameters;
    };
    std::optional<EnhancementResult> enhance(const std::string& description) const;

private:
    Config m_config;
    
    // HTTP request helpers
    std::optional<nlohmann::json> makeRequest(
        const std::string& endpoint,
        const nlohmann::json& body
    ) const;
    
    std::string httpPost(const std::string& url, const std::string& body) const;
    bool httpGet(const std::string& url) const;
    
    // JSON parsing helpers
    ExtractedParameters parseExtractedParameters(const nlohmann::json& json) const;
};

} // namespace GeneratorAgent
} // namespace MagiTech
