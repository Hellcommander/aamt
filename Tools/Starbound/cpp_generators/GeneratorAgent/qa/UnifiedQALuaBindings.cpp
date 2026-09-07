#include "UnifiedQALuaBindings.hpp"
#include "UnifiedQASystem.hpp"
#include <memory>

namespace mt::qa {

void UnifiedQALuaBindings::bind(sol::state& lua) {
    // Bind result types
    lua.new_usertype<ValidationError>("ValidationError",
        "field", &ValidationError::field,
        "message", &ValidationError::message,
        "severity", &ValidationError::severity,
        "assetPath", &ValidationError::assetPath,
        "assetType", &ValidationError::assetType
    );
    
    lua.new_usertype<ValidationResult>("ValidationResult",
        "isValid", &ValidationResult::isValid,
        "errors", &ValidationResult::errors,
        "warnings", &ValidationResult::warnings,
        "duration", &ValidationResult::duration,
        "assetPath", &ValidationResult::assetPath,
        "assetType", &ValidationResult::assetType
    );
    
    lua.new_usertype<ImageScore>("ImageScore",
        "psnr", &ImageScore::psnr,
        "ssim", &ImageScore::ssim,
        "histogramCorrelation", &ImageScore::histogramCorrelation,
        "shapeDifference", &ImageScore::shapeDifference,
        "colorDistance", &ImageScore::colorDistance,
        "edgeSimilarity", &ImageScore::edgeSimilarity,
        "psnrThreshold", &ImageScore::psnrThreshold,
        "ssimThreshold", &ImageScore::ssimThreshold,
        "histogramThreshold", &ImageScore::histogramThreshold,
        "shapeThreshold", &ImageScore::shapeThreshold,
        "colorThreshold", &ImageScore::colorThreshold,
        "edgeThreshold", &ImageScore::edgeThreshold,
        "passes", &ImageScore::passes,
        "overallScore", &ImageScore::overallScore
    );
    
    lua.new_usertype<VisualTestResult>("VisualTestResult",
        "passed", &VisualTestResult::passed,
        "score", &VisualTestResult::score,
        "baselinePath", &VisualTestResult::baselinePath,
        "testPath", &VisualTestResult::testPath,
        "diffPath", &VisualTestResult::diffPath,
        "assetType", &VisualTestResult::assetType,
        "duration", &VisualTestResult::duration
    );
    
    lua.new_usertype<UnifiedTestConfig>("UnifiedTestConfig",
        "enableDataValidation", &UnifiedTestConfig::enableDataValidation,
        "strictMode", &UnifiedTestConfig::strictMode,
        "requiredFields", &UnifiedTestConfig::requiredFields,
        "fieldValidators", &UnifiedTestConfig::fieldValidators,
        "enableVisualQA", &UnifiedTestConfig::enableVisualQA,
        "baselineDirectory", &UnifiedTestConfig::baselineDirectory,
        "outputDirectory", &UnifiedTestConfig::outputDirectory,
        "generateDiffs", &UnifiedTestConfig::generateDiffs,
        "generateReports", &UnifiedTestConfig::generateReports,
        "parallelExecution", &UnifiedTestConfig::parallelExecution,
        "maxThreads", &UnifiedTestConfig::maxThreads,
        "timeout", &UnifiedTestConfig::timeout
    );
    
    lua.new_usertype<UnifiedTestResult>("UnifiedTestResult",
        "assetPath", &UnifiedTestResult::assetPath,
        "assetType", &UnifiedTestResult::assetType,
        "overallPassed", &UnifiedTestResult::overallPassed,
        "dataValidation", &UnifiedTestResult::dataValidation,
        "visualQA", &UnifiedTestResult::visualQA,
        "totalDuration", &UnifiedTestResult::totalDuration,
        "errorMessage", &UnifiedTestResult::errorMessage,
        "warnings", &UnifiedTestResult::warnings
    );
    
    // Bind the main UnifiedQASystem class
    lua.new_usertype<UnifiedQASystem>("UnifiedQASystem",
        sol::constructors<UnifiedQASystem()>(),
        "configure", &UnifiedQASystem::configure,
        "setThreadPool", &UnifiedQASystem::setThreadPool,
        "registerValidator", &UnifiedQASystem::registerValidator,
        "unregisterValidator", &UnifiedQASystem::unregisterValidator,
        "testAsset", &UnifiedQASystem::testAsset,
        "testDirectory", &UnifiedQASystem::testDirectory,
        "testBatch", &UnifiedQASystem::testBatch,
        "generateBaseline", &UnifiedQASystem::generateBaseline,
        "generateBaselines", &UnifiedQASystem::generateBaselines,
        "updateBaseline", &UnifiedQASystem::updateBaseline,
        "generateReport", &UnifiedQASystem::generateReport,
        "generateSummary", &UnifiedQASystem::generateSummary,
        "isInitialized", &UnifiedQASystem::isInitialized,
        "clearCache", &UnifiedQASystem::clearCache,
        "getSupportedAssetTypes", &UnifiedQASystem::getSupportedAssetTypes,
        "getRegisteredValidators", &UnifiedQASystem::getRegisteredValidators,
        "getStatistics", &UnifiedQASystem::getStatistics,
        "resetStatistics", &UnifiedQASystem::resetStatistics
    );
    
    // Create global QA table with convenience functions
    lua["QA"] = lua.create_table();
    
    // Global QA instance
    lua["QA"]["system"] = std::make_shared<UnifiedQASystem>();
    
    // Convenience functions
    lua["QA"]["testAsset"] = [](const std::string& assetPath) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->testAsset(assetPath);
    };
    
    lua["QA"]["testDirectory"] = [](const std::string& directoryPath) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->testDirectory(directoryPath);
    };
    
    lua["QA"]["testBatch"] = [](const std::vector<std::string>& assetPaths) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->testBatch(assetPaths);
    };
    
    lua["QA"]["configure"] = [](const UnifiedTestConfig& config) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->configure(config);
    };
    
    lua["QA"]["generateBaseline"] = [](const std::string& assetPath) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->generateBaseline(assetPath);
    };
    
    lua["QA"]["generateBaselines"] = [](const std::string& directoryPath) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->generateBaselines(directoryPath);
    };
    
    lua["QA"]["generateReport"] = [](const std::vector<UnifiedTestResult>& results, const std::string& outputPath) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->generateReport(results, outputPath);
    };
    
    lua["QA"]["generateSummary"] = [](const std::vector<UnifiedTestResult>& results) {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->generateSummary(results);
    };
    
    lua["QA"]["getStatistics"] = []() {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->getStatistics();
    };
    
    lua["QA"]["resetStatistics"] = []() {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        system->resetStatistics();
    };
    
    lua["QA"]["getSupportedAssetTypes"] = []() {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->getSupportedAssetTypes();
    };
    
    lua["QA"]["getRegisteredValidators"] = []() {
        auto system = lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
        return system->getRegisteredValidators();
    };
    
    // Utility functions
    lua["QA"]["isValidJson"] = [](const std::string& content) {
        return Utils::isValidJson(content);
    };
    
    lua["QA"]["isValidImage"] = [](const std::string& filePath) {
        return Utils::isValidImage(filePath);
    };
    
    lua["QA"]["isValidAudio"] = [](const std::string& filePath) {
        return Utils::isValidAudio(filePath);
    };
    
    lua["QA"]["getFileExtension"] = [](const std::string& filePath) {
        return Utils::getFileExtension(filePath);
    };
    
    lua["QA"]["scanDirectory"] = [](const std::string& directoryPath, const std::vector<std::string>& extensions) {
        return Utils::scanDirectory(directoryPath, extensions);
    };
    
    // Constants
    lua["QA"]["SEVERITY_ERROR"] = "error";
    lua["QA"]["SEVERITY_WARNING"] = "warning";
    lua["QA"]["SEVERITY_INFO"] = "info";
    
    lua["QA"]["ASSET_TYPE_JSON"] = "JSON";
    lua["QA"]["ASSET_TYPE_IMAGE"] = "Image";
    lua["QA"]["ASSET_TYPE_AUDIO"] = "Audio";
}

void UnifiedQALuaBindings::update(sol::state& lua) {
    // Update any dynamic bindings if needed
    // This could be used for runtime configuration updates
}

} // namespace mt::qa 
