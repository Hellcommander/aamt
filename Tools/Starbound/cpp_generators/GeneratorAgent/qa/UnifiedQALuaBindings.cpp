#include "UnifiedQALuaBindings.hpp"
#include "UnifiedQASystem.hpp"
#include <memory>

namespace mt::qa {

namespace {
// The QA.system instance currently stored in Lua (scripts may replace it)
std::shared_ptr<UnifiedQASystem> currentSystem(sol::this_state ts) {
    sol::state_view lua(ts);
    return lua["QA"]["system"].get<std::shared_ptr<UnifiedQASystem>>();
}
} // namespace

void UnifiedQALuaBindings::bind(sol::state& lua) {
    // Global QA table with convenience functions. ImageScore lives in it (QA.ImageScore)
    // because VisualQA binds a different ImageScore type.
    sol::table qaTable = lua.create_table();
    lua["QA"] = qaTable;

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
    
    qaTable.new_usertype<ImageScore>("ImageScore",
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
        // Plain Lua table copied in/out: the vendored sol2 container usertype cannot iterate string maps
        "fieldValidators", sol::property(
            [](const UnifiedTestConfig& config) { return sol::as_table(config.fieldValidators); },
            [](UnifiedTestConfig& config, sol::table table) {
                config.fieldValidators.clear();
                for (const auto& [key, value] : table) {
                    config.fieldValidators[key.as<std::string>()] = value.as<std::string>();
                }
            }),
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
    
    // Global QA instance
    lua["QA"]["system"] = std::make_shared<UnifiedQASystem>();
    
    // Convenience functions
    lua["QA"]["testAsset"] = [](sol::this_state ts, const std::string& assetPath) {
        auto system = currentSystem(ts);
        return system->testAsset(assetPath);
    };
    
    lua["QA"]["testDirectory"] = [](sol::this_state ts, const std::string& directoryPath) {
        auto system = currentSystem(ts);
        return system->testDirectory(directoryPath);
    };
    
    lua["QA"]["testBatch"] = [](sol::this_state ts, const std::vector<std::string>& assetPaths) {
        auto system = currentSystem(ts);
        return system->testBatch(assetPaths);
    };
    
    lua["QA"]["configure"] = [](sol::this_state ts, const UnifiedTestConfig& config) {
        auto system = currentSystem(ts);
        system->configure(config);
    };
    
    lua["QA"]["generateBaseline"] = [](sol::this_state ts, const std::string& assetPath) {
        auto system = currentSystem(ts);
        system->generateBaseline(assetPath);
    };
    
    lua["QA"]["generateBaselines"] = [](sol::this_state ts, const std::string& directoryPath) {
        auto system = currentSystem(ts);
        system->generateBaselines(directoryPath);
    };
    
    lua["QA"]["generateReport"] = [](sol::this_state ts, const std::vector<UnifiedTestResult>& results, const std::string& outputPath) {
        auto system = currentSystem(ts);
        system->generateReport(results, outputPath);
    };
    
    lua["QA"]["generateSummary"] = [](sol::this_state ts, const std::vector<UnifiedTestResult>& results) {
        auto system = currentSystem(ts);
        system->generateSummary(results);
    };
    
    lua["QA"]["getStatistics"] = [](sol::this_state ts) {
        auto system = currentSystem(ts);
        return system->getStatistics();
    };
    
    lua["QA"]["resetStatistics"] = [](sol::this_state ts) {
        auto system = currentSystem(ts);
        system->resetStatistics();
    };
    
    lua["QA"]["getSupportedAssetTypes"] = [](sol::this_state ts) {
        auto system = currentSystem(ts);
        return system->getSupportedAssetTypes();
    };
    
    lua["QA"]["getRegisteredValidators"] = [](sol::this_state ts) {
        auto system = currentSystem(ts);
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
    // Scripts may clear or replace QA.system; the convenience functions need a valid instance
    sol::object qa = lua["QA"];
    if (!qa.is<sol::table>()) {
        bind(lua);
        return;
    }
    sol::object system = lua["QA"]["system"];
    if (!system.is<std::shared_ptr<UnifiedQASystem>>()) {
        lua["QA"]["system"] = std::make_shared<UnifiedQASystem>();
    }
}

} // namespace mt::qa 
