#include "UnifiedQASystem.hpp"
#include "VisualQASystem.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <thread>
#include <future>
#include <nlohmann/json.hpp>
#include <opencv2/opencv.hpp"

namespace mt::qa {

// ImageScore implementation
bool ImageScore::passes() const {
    return psnr >= psnrThreshold &&
           ssim >= ssimThreshold &&
           histogramCorrelation >= histogramThreshold &&
           shapeDifference >= shapeThreshold &&
           colorDistance >= colorThreshold &&
           edgeSimilarity >= edgeThreshold;
}

double ImageScore::overallScore() const {
    // Weighted average of all metrics
    return (psnr / psnrThreshold * 0.2 +
            ssim / ssimThreshold * 0.25 +
            histogramCorrelation / histogramThreshold * 0.15 +
            shapeDifference / shapeThreshold * 0.2 +
            colorDistance / colorThreshold * 0.1 +
            edgeSimilarity / edgeThreshold * 0.1);
}

// UnifiedQASystem implementation
UnifiedQASystem::UnifiedQASystem() {
    // Register built-in validators
    registerValidator(std::make_shared<JsonAssetValidator>());
    registerValidator(std::make_shared<ImageAssetValidator>());
    registerValidator(std::make_shared<AudioAssetValidator>());
    
    // Initialize asset type mapping
    m_assetTypeMap = {
        {".json", "JSON"},
        {".png", "Image"},
        {".jpg", "Image"},
        {".jpeg", "Image"},
        {".bmp", "Image"},
        {".tga", "Image"},
        {".wav", "Audio"},
        {".mp3", "Audio"},
        {".ogg", "Audio"},
        {".flac", "Audio"}
    };
    
    resetStatistics();
}

UnifiedQASystem::~UnifiedQASystem() = default;

void UnifiedQASystem::configure(const UnifiedTestConfig& config) {
    m_config = config;
}

void UnifiedQASystem::setThreadPool(std::shared_ptr<mt::ThreadPoolManager> threadPool) {
    m_threadPool = threadPool;
}

void UnifiedQASystem::registerValidator(std::shared_ptr<IAssetValidator> validator) {
    if (validator) {
        m_validators[validator->getValidatorName()] = validator;
    }
}

void UnifiedQASystem::unregisterValidator(const std::string& validatorName) {
    m_validators.erase(validatorName);
}

UnifiedTestResult UnifiedQASystem::testAsset(const std::string& assetPath) {
    UnifiedTestResult result;
    result.assetPath = assetPath;
    result.assetType = determineAssetType(assetPath);
    result.overallPassed = true;
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Run data validation if enabled
        if (m_config.enableDataValidation) {
            result.dataValidation = runDataValidation(assetPath);
            if (!result.dataValidation->isValid) {
                result.overallPassed = false;
                result.errorMessage = "Data validation failed";
            }
        }
        
        // Run visual QA if enabled and asset is visual
        if (m_config.enableVisualQA && isVisualAsset(result.assetType)) {
            result.visualQA = runVisualQA(assetPath);
            if (!result.visualQA->passed) {
                result.overallPassed = false;
                if (!result.errorMessage.empty()) {
                    result.errorMessage += "; ";
                }
                result.errorMessage += "Visual QA failed";
            }
        }
        
    } catch (const std::exception& e) {
        result.overallPassed = false;
        result.errorMessage = std::string("Exception: ") + e.what();
    }
    
    auto endTime = std::chrono::high_resolution_clock::now();
    result.totalDuration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    
    updateStatistics(result);
    return result;
}

std::vector<UnifiedTestResult> UnifiedQASystem::testDirectory(const std::string& directoryPath) {
    std::vector<std::string> assetPaths;
    
    for (const auto& entry : std::filesystem::recursive_directory_iterator(directoryPath)) {
        if (entry.is_regular_file()) {
            std::string extension = Utils::getFileExtension(entry.path().string());
            if (m_assetTypeMap.find(extension) != m_assetTypeMap.end()) {
                assetPaths.push_back(entry.path().string());
            }
        }
    }
    
    return testBatch(assetPaths);
}

std::vector<UnifiedTestResult> UnifiedQASystem::testBatch(const std::vector<std::string>& assetPaths) {
    std::vector<UnifiedTestResult> results;
    
    if (m_config.parallelExecution && m_threadPool) {
        // Parallel execution
        std::vector<std::future<UnifiedTestResult>> futures;
        
        for (const auto& assetPath : assetPaths) {
            if (!shouldSkipAsset(assetPath)) {
                futures.push_back(m_threadPool->enqueue([this, assetPath]() {
                    return testAsset(assetPath);
                }));
            }
        }
        
        for (auto& future : futures) {
            results.push_back(future.get());
        }
    } else {
        // Sequential execution
        for (const auto& assetPath : assetPaths) {
            if (!shouldSkipAsset(assetPath)) {
                results.push_back(testAsset(assetPath));
            }
        }
    }
    
    return results;
}

void UnifiedQASystem::generateBaseline(const std::string& assetPath) {
    if (!m_config.enableVisualQA) return;
    
    // This would integrate with the VisualQASystem
    // For now, we'll create a placeholder baseline
    std::filesystem::path baselineDir(m_config.baselineDirectory);
    std::filesystem::path assetPathObj(assetPath);
    std::filesystem::path baselinePath = baselineDir / assetPathObj.filename();
    
    if (std::filesystem::exists(assetPath)) {
        std::filesystem::create_directories(baselinePath.parent_path());
        std::filesystem::copy_file(assetPath, baselinePath, 
                                  std::filesystem::copy_options::overwrite_existing);
    }
}

void UnifiedQASystem::generateBaselines(const std::string& directoryPath) {
    for (const auto& entry : std::filesystem::recursive_directory_iterator(directoryPath)) {
        if (entry.is_regular_file()) {
            std::string extension = Utils::getFileExtension(entry.path().string());
            if (isVisualAsset(m_assetTypeMap[extension])) {
                generateBaseline(entry.path().string());
            }
        }
    }
}

void UnifiedQASystem::updateBaseline(const std::string& assetPath) {
    generateBaseline(assetPath);
}

void UnifiedQASystem::generateReport(const std::vector<UnifiedTestResult>& results, 
                                    const std::string& outputPath) {
    std::string htmlContent = generateReportHTML(results);
    
    std::ofstream file(outputPath);
    if (file.is_open()) {
        file << htmlContent;
        file.close();
    }
}

void UnifiedQASystem::generateSummary(const std::vector<UnifiedTestResult>& results) {
    std::string summary = generateSummaryText(results);
    std::cout << summary << std::endl;
}

bool UnifiedQASystem::isInitialized() const {
    return !m_validators.empty();
}

void UnifiedQASystem::clearCache() {
    // Clear any cached data
}

std::vector<std::string> UnifiedQASystem::getSupportedAssetTypes() const {
    std::vector<std::string> types;
    for (const auto& pair : m_assetTypeMap) {
        types.push_back(pair.second);
    }
    return types;
}

std::vector<std::string> UnifiedQASystem::getRegisteredValidators() const {
    std::vector<std::string> validators;
    for (const auto& pair : m_validators) {
        validators.push_back(pair.first);
    }
    return validators;
}

UnifiedQASystem::Statistics UnifiedQASystem::getStatistics() const {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    return m_stats;
}

void UnifiedQASystem::resetStatistics() {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    m_stats = Statistics{};
}

// Private methods
std::string UnifiedQASystem::determineAssetType(const std::string& assetPath) const {
    std::string extension = Utils::getFileExtension(assetPath);
    auto it = m_assetTypeMap.find(extension);
    return (it != m_assetTypeMap.end()) ? it->second : "Unknown";
}

std::shared_ptr<IAssetValidator> UnifiedQASystem::findValidator(const std::string& assetPath) const {
    std::string assetType = determineAssetType(assetPath);
    
    for (const auto& pair : m_validators) {
        const auto& extensions = pair.second->getSupportedExtensions();
        std::string extension = Utils::getFileExtension(assetPath);
        
        if (std::find(extensions.begin(), extensions.end(), extension) != extensions.end()) {
            return pair.second;
        }
    }
    
    return nullptr;
}

ValidationResult UnifiedQASystem::runDataValidation(const std::string& assetPath) {
    auto validator = findValidator(assetPath);
    if (!validator) {
        ValidationResult result;
        result.isValid = false;
        result.assetPath = assetPath;
        result.assetType = determineAssetType(assetPath);
        result.errors.push_back({"validator", "No suitable validator found", "error", assetPath, result.assetType});
        return result;
    }
    
    return validator->validate(assetPath);
}

VisualTestResult UnifiedQASystem::runVisualQA(const std::string& assetPath) {
    // This would integrate with the VisualQASystem
    // For now, return a placeholder result
    VisualTestResult result;
    result.passed = true;
    result.assetType = determineAssetType(assetPath);
    result.testPath = assetPath;
    result.baselinePath = m_config.baselineDirectory + "/" + std::filesystem::path(assetPath).filename().string();
    result.diffPath = m_config.outputDirectory + "/diff_" + std::filesystem::path(assetPath).filename().string();
    
    // Placeholder score
    result.score.psnr = 35.0;
    result.score.ssim = 0.98;
    result.score.histogramCorrelation = 0.95;
    result.score.shapeDifference = 0.9;
    result.score.colorDistance = 0.92;
    result.score.edgeSimilarity = 0.88;
    
    return result;
}

bool UnifiedQASystem::shouldSkipAsset(const std::string& assetPath) const {
    // Skip hidden files and temporary files
    std::string filename = std::filesystem::path(assetPath).filename().string();
    return filename.empty() || filename[0] == '.' || filename.find("~") != std::string::npos;
}

void UnifiedQASystem::updateStatistics(const UnifiedTestResult& result) {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    
    m_stats.totalTests++;
    m_stats.totalDuration += result.totalDuration;
    
    if (result.overallPassed) {
        m_stats.passedTests++;
    } else {
        m_stats.failedTests++;
        m_stats.failuresByType[result.assetType]++;
        
        if (result.dataValidation && !result.dataValidation->isValid) {
            m_stats.failuresByValidator["DataValidation"]++;
        }
        if (result.visualQA && !result.visualQA->passed) {
            m_stats.failuresByValidator["VisualQA"]++;
        }
    }
}

std::string UnifiedQASystem::generateReportHTML(const std::vector<UnifiedTestResult>& results) const {
    std::ostringstream html;
    
    html << "<!DOCTYPE html>\n<html>\n<head>\n";
    html << "<title>Unified QA Report</title>\n";
    html << "<style>\n";
    html << "body { font-family: Arial, sans-serif; margin: 20px; }\n";
    html << ".header { background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }\n";
    html << ".result { border: 1px solid #ddd; margin: 10px 0; padding: 10px; }\n";
    html << ".passed { background-color: #d4edda; }\n";
    html << ".failed { background-color: #f8d7da; }\n";
    html << ".warning { background-color: #fff3cd; }\n";
    html << "</style>\n</head>\n<body>\n";
    
    html << "<div class='header'>\n";
    html << "<h1>Unified QA Report</h1>\n";
    html << "<p>Generated: " << std::chrono::system_clock::now().time_since_epoch().count() << "</p>\n";
    html << "<p>Total Assets: " << results.size() << "</p>\n";
    
    size_t passed = 0, failed = 0;
    for (const auto& result : results) {
        if (result.overallPassed) passed++;
        else failed++;
    }
    
    html << "<p>Passed: " << passed << " | Failed: " << failed << "</p>\n";
    html << "</div>\n";
    
    for (const auto& result : results) {
        html << "<div class='result " << (result.overallPassed ? "passed" : "failed") << "'>\n";
        html << "<h3>" << result.assetPath << "</h3>\n";
        html << "<p>Type: " << result.assetType << " | Duration: " << result.totalDuration.count() << "ms</p>\n";
        
        if (!result.overallPassed) {
            html << "<p><strong>Error:</strong> " << result.errorMessage << "</p>\n";
        }
        
        if (result.dataValidation) {
            html << "<h4>Data Validation:</h4>\n";
            html << "<p>Valid: " << (result.dataValidation->isValid ? "Yes" : "No") << "</p>\n";
            if (!result.dataValidation->errors.empty()) {
                html << "<ul>\n";
                for (const auto& error : result.dataValidation->errors) {
                    html << "<li>" << error.message << "</li>\n";
                }
                html << "</ul>\n";
            }
        }
        
        if (result.visualQA) {
            html << "<h4>Visual QA:</h4>\n";
            html << "<p>Passed: " << (result.visualQA->passed ? "Yes" : "No") << "</p>\n";
            html << "<p>Overall Score: " << result.visualQA->score.overallScore() << "</p>\n";
        }
        
        html << "</div>\n";
    }
    
    html << "</body>\n</html>";
    return html.str();
}

std::string UnifiedQASystem::generateSummaryText(const std::vector<UnifiedTestResult>& results) const {
    std::ostringstream summary;
    
    size_t passed = 0, failed = 0;
    std::unordered_map<std::string, size_t> failuresByType;
    
    for (const auto& result : results) {
        if (result.overallPassed) {
            passed++;
        } else {
            failed++;
            failuresByType[result.assetType]++;
        }
    }
    
    summary << "=== Unified QA Summary ===\n";
    summary << "Total Assets: " << results.size() << "\n";
    summary << "Passed: " << passed << "\n";
    summary << "Failed: " << failed << "\n";
    summary << "Success Rate: " << (results.size() > 0 ? (passed * 100.0 / results.size()) : 0) << "%\n\n";
    
    if (!failuresByType.empty()) {
        summary << "Failures by Type:\n";
        for (const auto& pair : failuresByType) {
            summary << "  " << pair.first << ": " << pair.second << "\n";
        }
    }
    
    return summary.str();
}

bool UnifiedQASystem::isVisualAsset(const std::string& assetType) const {
    return assetType == "Image";
}

// Built-in validators implementation
ValidationResult JsonAssetValidator::validate(const std::string& assetPath) {
    ValidationResult result;
    result.assetPath = assetPath;
    result.assetType = "JSON";
    result.isValid = true;
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        std::ifstream file(assetPath);
        if (!file.is_open()) {
            result.isValid = false;
            result.errors.push_back({"file", "Cannot open file", "error", assetPath, "JSON"});
            return result;
        }
        
        std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        
        if (!Utils::isValidJson(content)) {
            result.isValid = false;
            result.errors.push_back({"json", "Invalid JSON format", "error", assetPath, "JSON"});
        }
        
    } catch (const std::exception& e) {
        result.isValid = false;
        result.errors.push_back({"exception", e.what(), "error", assetPath, "JSON"});
    }
    
    auto endTime = std::chrono::high_resolution_clock::now();
    result.duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    
    return result;
}

std::vector<std::string> JsonAssetValidator::getSupportedExtensions() const {
    return {".json"};
}

ValidationResult ImageAssetValidator::validate(const std::string& assetPath) {
    ValidationResult result;
    result.assetPath = assetPath;
    result.assetType = "Image";
    result.isValid = true;
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    if (!Utils::isValidImage(assetPath)) {
        result.isValid = false;
        result.errors.push_back({"image", "Invalid or corrupted image file", "error", assetPath, "Image"});
    }
    
    auto endTime = std::chrono::high_resolution_clock::now();
    result.duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    
    return result;
}

std::vector<std::string> ImageAssetValidator::getSupportedExtensions() const {
    return {".png", ".jpg", ".jpeg", ".bmp", ".tga"};
}

ValidationResult AudioAssetValidator::validate(const std::string& assetPath) {
    ValidationResult result;
    result.assetPath = assetPath;
    result.assetType = "Audio";
    result.isValid = true;
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    if (!Utils::isValidAudio(assetPath)) {
        result.isValid = false;
        result.errors.push_back({"audio", "Invalid or corrupted audio file", "error", assetPath, "Audio"});
    }
    
    auto endTime = std::chrono::high_resolution_clock::now();
    result.duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    
    return result;
}

std::vector<std::string> AudioAssetValidator::getSupportedExtensions() const {
    return {".wav", ".mp3", ".ogg", ".flac"};
}

// Utility functions implementation
namespace Utils {
    
bool isValidJson(const std::string& content) {
    try {
        nlohmann::json::parse(content);
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

bool isValidImage(const std::string& filePath) {
    try {
        cv::Mat image = cv::imread(filePath);
        return !image.empty();
    } catch (const std::exception&) {
        return false;
    }
}

bool isValidAudio(const std::string& filePath) {
    // This is a simplified check - in a real implementation,
    // you'd use a proper audio library like libsndfile or similar
    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) return false;
    
    // Check file header for common audio formats
    char header[12];
    file.read(header, 12);
    
    // WAV header check
    if (std::string(header, 4) == "RIFF" && std::string(header + 8, 4) == "WAVE") {
        return true;
    }
    
    // MP3 header check (simplified)
    if ((header[0] & 0xFF) == 0xFF && (header[1] & 0xE0) == 0xE0) {
        return true;
    }
    
    return false;
}

std::string getFileExtension(const std::string& filePath) {
    std::filesystem::path path(filePath);
    return path.extension().string();
}

std::string normalizePath(const std::string& path) {
    return std::filesystem::path(path).lexically_normal().string();
}

std::vector<std::string> scanDirectory(const std::string& directoryPath, 
                                      const std::vector<std::string>& extensions) {
    std::vector<std::string> files;
    
    for (const auto& entry : std::filesystem::recursive_directory_iterator(directoryPath)) {
        if (entry.is_regular_file()) {
            std::string extension = getFileExtension(entry.path().string());
            if (std::find(extensions.begin(), extensions.end(), extension) != extensions.end()) {
                files.push_back(entry.path().string());
            }
        }
    }
    
    return files;
}

} // namespace Utils

} // namespace mt::qa 
