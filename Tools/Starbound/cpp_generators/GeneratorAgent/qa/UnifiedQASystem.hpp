#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <functional>
#include <variant>
#include <optional>
#include <chrono>
#include <filesystem>

// Forward declarations
namespace mt {
    class ThreadPoolManager;
}

namespace mt::qa {

// Data validation result types
struct ValidationError {
    std::string field;
    std::string message;
    std::string severity; // "error", "warning", "info"
    std::string assetPath;
    std::string assetType;
};

struct ValidationResult {
    bool isValid;
    std::vector<ValidationError> errors;
    std::vector<ValidationError> warnings;
    std::chrono::milliseconds duration;
    std::string assetPath;
    std::string assetType;
};

// Visual QA result types (from VisualQASystem)
struct ImageScore {
    double psnr;
    double ssim;
    double histogramCorrelation;
    double shapeDifference;
    double colorDistance;
    double edgeSimilarity;
    
    // Thresholds for pass/fail
    double psnrThreshold = 30.0;
    double ssimThreshold = 0.95;
    double histogramThreshold = 0.9;
    double shapeThreshold = 0.8;
    double colorThreshold = 0.85;
    double edgeThreshold = 0.8;
    
    bool passes() const;
    double overallScore() const;
};

struct VisualTestResult {
    bool passed;
    ImageScore score;
    std::string baselinePath;
    std::string testPath;
    std::string diffPath;
    std::string assetType;
    std::chrono::milliseconds duration;
};

// Unified test configuration
struct UnifiedTestConfig {
    // Data validation settings
    bool enableDataValidation = true;
    bool strictMode = false;
    std::vector<std::string> requiredFields;
    std::unordered_map<std::string, std::string> fieldValidators;
    
    // Visual QA settings
    bool enableVisualQA = true;
    std::string baselineDirectory;
    std::string outputDirectory;
    bool generateDiffs = true;
    bool generateReports = true;
    
    // General settings
    bool parallelExecution = true;
    int maxThreads = 4;
    std::chrono::milliseconds timeout{30000}; // 30 seconds
};

// Unified test result
struct UnifiedTestResult {
    std::string assetPath;
    std::string assetType;
    bool overallPassed;
    
    // Individual results
    std::optional<ValidationResult> dataValidation;
    std::optional<VisualTestResult> visualQA;
    
    // Metadata
    std::chrono::milliseconds totalDuration;
    std::string errorMessage;
    std::vector<std::string> warnings;
};

// Asset validator interface
class IAssetValidator {
public:
    virtual ~IAssetValidator() = default;
    virtual ValidationResult validate(const std::string& assetPath) = 0;
    virtual std::string getValidatorName() const = 0;
    virtual std::vector<std::string> getSupportedExtensions() const = 0;
};

// Main Unified QA System
class UnifiedQASystem {
public:
    UnifiedQASystem();
    ~UnifiedQASystem();
    
    // Configuration
    void configure(const UnifiedTestConfig& config);
    void setThreadPool(std::shared_ptr<mt::ThreadPoolManager> threadPool);
    
    // Asset validation registration
    void registerValidator(std::shared_ptr<IAssetValidator> validator);
    void unregisterValidator(const std::string& validatorName);
    
    // Test execution
    UnifiedTestResult testAsset(const std::string& assetPath);
    std::vector<UnifiedTestResult> testDirectory(const std::string& directoryPath);
    std::vector<UnifiedTestResult> testBatch(const std::vector<std::string>& assetPaths);
    
    // Baseline management
    void generateBaseline(const std::string& assetPath);
    void generateBaselines(const std::string& directoryPath);
    void updateBaseline(const std::string& assetPath);
    
    // Reporting
    void generateReport(const std::vector<UnifiedTestResult>& results, 
                       const std::string& outputPath);
    void generateSummary(const std::vector<UnifiedTestResult>& results);
    
    // Utility methods
    bool isInitialized() const;
    void clearCache();
    std::vector<std::string> getSupportedAssetTypes() const;
    std::vector<std::string> getRegisteredValidators() const;
    
    // Statistics
    struct Statistics {
        size_t totalTests;
        size_t passedTests;
        size_t failedTests;
        size_t skippedTests;
        std::chrono::milliseconds totalDuration;
        std::unordered_map<std::string, size_t> failuresByType;
        std::unordered_map<std::string, size_t> failuresByValidator;
    };
    
    Statistics getStatistics() const;
    void resetStatistics();

private:
    // Internal state
    UnifiedTestConfig m_config;
    std::shared_ptr<mt::ThreadPoolManager> m_threadPool;
    std::unordered_map<std::string, std::shared_ptr<IAssetValidator>> m_validators;
    std::unordered_map<std::string, std::string> m_assetTypeMap;
    
    // Statistics
    mutable Statistics m_stats;
    mutable std::mutex m_statsMutex;
    
    // Internal methods
    std::string determineAssetType(const std::string& assetPath) const;
    std::shared_ptr<IAssetValidator> findValidator(const std::string& assetPath) const;
    ValidationResult runDataValidation(const std::string& assetPath);
    VisualTestResult runVisualQA(const std::string& assetPath);
    
    // Helper methods
    bool shouldSkipAsset(const std::string& assetPath) const;
    void updateStatistics(const UnifiedTestResult& result);
    std::string generateReportHTML(const std::vector<UnifiedTestResult>& results) const;
    std::string generateSummaryText(const std::vector<UnifiedTestResult>& results) const;
};

// Built-in validators
class JsonAssetValidator : public IAssetValidator {
public:
    ValidationResult validate(const std::string& assetPath) override;
    std::string getValidatorName() const override { return "JSON"; }
    std::vector<std::string> getSupportedExtensions() const override;
};

class ImageAssetValidator : public IAssetValidator {
public:
    ValidationResult validate(const std::string& assetPath) override;
    std::string getValidatorName() const override { return "Image"; }
    std::vector<std::string> getSupportedExtensions() const override;
};

class AudioAssetValidator : public IAssetValidator {
public:
    ValidationResult validate(const std::string& assetPath) override;
    std::string getValidatorName() const override { return "Audio"; }
    std::vector<std::string> getSupportedExtensions() const override;
};

// Utility functions
namespace Utils {
    bool isValidJson(const std::string& content);
    bool isValidImage(const std::string& filePath);
    bool isValidAudio(const std::string& filePath);
    std::string getFileExtension(const std::string& filePath);
    std::string normalizePath(const std::string& path);
    std::vector<std::string> scanDirectory(const std::string& directoryPath, 
                                          const std::vector<std::string>& extensions);
}

} // namespace mt::qa 
