#include "VisualQALuaBindings.hpp"
#include "VisualQASystem.hpp"
#include "core/Log.hpp"
#include <memory>

namespace MagiTech {

static std::unique_ptr<VisualQA::VisualQASystem> g_visualQA;

void VisualQALuaBindings::bind(sol::state& lua) {
    // Create global Visual QA instance
    g_visualQA = std::make_unique<VisualQA::VisualQASystem>();
    
    // Bind ImageScore struct
    lua.new_usertype<VisualQA::ImageScore>("ImageScore",
        sol::constructors<VisualQA::ImageScore()>(),
        "psnr", &VisualQA::ImageScore::psnr,
        "ssim", &VisualQA::ImageScore::ssim,
        "histCorr", &VisualQA::ImageScore::histCorr,
        "shapeDiff", &VisualQA::ImageScore::shapeDiff,
        "colorDistance", &VisualQA::ImageScore::colorDistance,
        "edgeSimilarity", &VisualQA::ImageScore::edgeSimilarity,
        "qualityScore", &VisualQA::ImageScore::qualityScore,
        "passes", &VisualQA::ImageScore::passes,
        "getReport", &VisualQA::ImageScore::getReport
    );
    
    // Bind AssetTestConfig struct
    lua.new_usertype<VisualQA::AssetTestConfig>("AssetTestConfig",
        sol::constructors<VisualQA::AssetTestConfig()>(),
        "assetName", &VisualQA::AssetTestConfig::assetName,
        "category", &VisualQA::AssetTestConfig::category,
        "frameCount", &VisualQA::AssetTestConfig::frameCount,
        "seeds", &VisualQA::AssetTestConfig::seeds,
        "generateBaseline", &VisualQA::AssetTestConfig::generateBaseline,
        "tolerance", &VisualQA::AssetTestConfig::tolerance,
        "minPSNR", &VisualQA::AssetTestConfig::minPSNR,
        "minSSIM", &VisualQA::AssetTestConfig::minSSIM,
        "minHistCorr", &VisualQA::AssetTestConfig::minHistCorr,
        "maxShapeDiff", &VisualQA::AssetTestConfig::maxShapeDiff,
        "maxColorDistance", &VisualQA::AssetTestConfig::maxColorDistance,
        "minEdgeSimilarity", &VisualQA::AssetTestConfig::minEdgeSimilarity
    );
    
    // Bind TestResult struct
    lua.new_usertype<VisualQA::TestResult>("TestResult",
        sol::no_constructor,
        "assetName", &VisualQA::TestResult::assetName,
        "frameIndex", &VisualQA::TestResult::frameIndex,
        "baselinePath", &VisualQA::TestResult::baselinePath,
        "testPath", &VisualQA::TestResult::testPath,
        "diffPath", &VisualQA::TestResult::diffPath,
        "score", &VisualQA::TestResult::score,
        "passed", &VisualQA::TestResult::passed,
        "failureReason", &VisualQA::TestResult::failureReason,
        "getReport", &VisualQA::TestResult::getReport
    );
    
    // Bind VisualQASystem class
    lua.new_usertype<VisualQA::VisualQASystem>("VisualQASystem",
        sol::constructors<VisualQA::VisualQASystem()>(),
        
        // Configuration
        "setBaselineDir", &VisualQA::VisualQASystem::setBaselineDir,
        "setTestDir", &VisualQA::VisualQASystem::setTestDir,
        "setReportDir", &VisualQA::VisualQASystem::setReportDir,
        "setTolerance", &VisualQA::VisualQASystem::setTolerance,
        
        // Core functionality
        "runAssetTest", &VisualQA::VisualQASystem::runAssetTest,
        "runBatchTest", &VisualQA::VisualQASystem::runBatchTest,
        "generateBaseline", &VisualQA::VisualQASystem::generateBaseline,
        
        // Getters
        "getLastResults", &VisualQA::VisualQASystem::getLastResults,
        "getPassRate", &VisualQA::VisualQASystem::getPassRate
    );
    
    // Create global VisualQA namespace
    lua["VisualQA"] = lua.create_table();
    
    // Add convenience functions
    lua["VisualQA"]["getInstance"] = []() -> VisualQA::VisualQASystem& {
        return *g_visualQA;
    };
    
    lua["VisualQA"]["testAsset"] = [](const std::string& assetName, const std::string& category, int frameCount = 1) {
        VisualQA::AssetTestConfig config;
        config.assetName = assetName;
        config.category = category;
        config.frameCount = frameCount;
        return g_visualQA->runAssetTest(config);
    };
    
    lua["VisualQA"]["testSpell"] = [](const std::string& spellName, int frameCount = 16) {
        return lua["VisualQA"]["testAsset"](spellName, "spell", frameCount);
    };
    
    lua["VisualQA"]["testMech"] = [](const std::string& mechName, int frameCount = 8) {
        return lua["VisualQA"]["testAsset"](mechName, "mech", frameCount);
    };
    
    lua["VisualQA"]["testTexture"] = [](const std::string& textureName) {
        return lua["VisualQA"]["testAsset"](textureName, "texture", 1);
    };
    
    lua["VisualQA"]["generateBaseline"] = [](const std::string& assetName, const std::string& category, int frameCount = 1) {
        VisualQA::AssetTestConfig config;
        config.assetName = assetName;
        config.category = category;
        config.frameCount = frameCount;
        config.generateBaseline = true;
        return g_visualQA->generateBaseline(config);
    };
    
    lua["VisualQA"]["runBatchTest"] = [](const sol::table& configs) {
        std::vector<VisualQA::AssetTestConfig> configList;
        
        for (const auto& [key, value] : configs) {
            if (value.is<VisualQA::AssetTestConfig>()) {
                configList.push_back(value.as<VisualQA::AssetTestConfig>());
            }
        }
        
        return g_visualQA->runBatchTest(configList);
    };
    
    lua["VisualQA"]["getResults"] = []() -> sol::table {
        sol::table results = lua.create_table();
        const auto& lastResults = g_visualQA->getLastResults();
        
        for (size_t i = 0; i < lastResults.size(); ++i) {
            results[i + 1] = lastResults[i];
        }
        
        return results;
    };
    
    lua["VisualQA"]["getPassRate"] = []() {
        return g_visualQA->getPassRate();
    };
    
    lua["VisualQA"]["configure"] = [](const std::string& baselineDir, const std::string& testDir, const std::string& reportDir) {
        g_visualQA->setBaselineDir(baselineDir);
        g_visualQA->setTestDir(testDir);
        g_visualQA->setReportDir(reportDir);
    };
    
    // Quality threshold constants
    lua["VisualQA"]["THRESHOLDS"] = lua.create_table();
    lua["VisualQA"]["THRESHOLDS"]["PASS_PSNR"] = VisualQA::ImageScore::PASS_PSNR;
    lua["VisualQA"]["THRESHOLDS"]["PASS_SSIM"] = VisualQA::ImageScore::PASS_SSIM;
    lua["VisualQA"]["THRESHOLDS"]["PASS_HIST"] = VisualQA::ImageScore::PASS_HIST;
    lua["VisualQA"]["THRESHOLDS"]["PASS_SHAPE"] = VisualQA::ImageScore::PASS_SHAPE;
    lua["VisualQA"]["THRESHOLDS"]["PASS_COLOR"] = VisualQA::ImageScore::PASS_COLOR;
    lua["VisualQA"]["THRESHOLDS"]["PASS_EDGE"] = VisualQA::ImageScore::PASS_EDGE;
    
    Log::info("Visual QA Lua bindings initialized");
}

void VisualQALuaBindings::update(sol::state& lua) {
    // Update function for any per-frame operations
    // Currently empty, but could be used for async operations
}

} // namespace MagiTech 
