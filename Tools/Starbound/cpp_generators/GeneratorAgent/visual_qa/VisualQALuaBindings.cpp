#include "VisualQALuaBindings.hpp"
#include "VisualQASystem.hpp"
#include "core/Log.hpp"
#include <memory>

namespace MagiTech {

static std::unique_ptr<VisualQA::VisualQASystem> g_visualQA;

namespace {

VisualQA::VisualQASystem& visualQA() {
    if (!g_visualQA) {
        g_visualQA = std::make_unique<VisualQA::VisualQASystem>();
    }
    return *g_visualQA;
}

bool testAsset(const std::string& assetName, const std::string& category, int frameCount) {
    VisualQA::AssetTestConfig config;
    config.assetName = assetName;
    config.category = category;
    config.frameCount = frameCount;
    return visualQA().runAssetTest(config);
}

} // namespace

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

    // Bind VisualQASystem class (paths are passed as strings from Lua)
    lua.new_usertype<VisualQA::VisualQASystem>("VisualQASystem",
        sol::constructors<VisualQA::VisualQASystem()>(),

        // Configuration
        "setBaselineDir", [](VisualQA::VisualQASystem& self, const std::string& p) { self.setBaselineDir(p); },
        "setTestDir", [](VisualQA::VisualQASystem& self, const std::string& p) { self.setTestDir(p); },
        "setReportDir", [](VisualQA::VisualQASystem& self, const std::string& p) { self.setReportDir(p); },
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
    sol::table qa = lua.create_named_table("VisualQA");

    // Add convenience functions (optional arguments use the documented defaults)
    qa["getInstance"] = []() -> VisualQA::VisualQASystem& {
        return visualQA();
    };

    qa["testAsset"] = [](const std::string& assetName, const std::string& category, sol::optional<int> frameCount) {
        return testAsset(assetName, category, frameCount.value_or(1));
    };

    qa["testSpell"] = [](const std::string& spellName, sol::optional<int> frameCount) {
        return testAsset(spellName, "spell", frameCount.value_or(16));
    };

    qa["testMech"] = [](const std::string& mechName, sol::optional<int> frameCount) {
        return testAsset(mechName, "mech", frameCount.value_or(8));
    };

    qa["testTexture"] = [](const std::string& textureName) {
        return testAsset(textureName, "texture", 1);
    };

    qa["generateBaseline"] = [](const std::string& assetName, const std::string& category, sol::optional<int> frameCount) {
        VisualQA::AssetTestConfig config;
        config.assetName = assetName;
        config.category = category;
        config.frameCount = frameCount.value_or(1);
        config.generateBaseline = true;
        return visualQA().generateBaseline(config);
    };

    qa["runBatchTest"] = [](const sol::table& configs) {
        std::vector<VisualQA::AssetTestConfig> configList;

        for (const auto& [key, value] : configs) {
            if (value.is<VisualQA::AssetTestConfig>()) {
                configList.push_back(value.as<VisualQA::AssetTestConfig>());
            }
        }

        return visualQA().runBatchTest(configList);
    };

    qa["getResults"] = [&lua]() -> sol::table {
        sol::table results = lua.create_table();
        const auto& lastResults = visualQA().getLastResults();

        for (size_t i = 0; i < lastResults.size(); ++i) {
            results[i + 1] = lastResults[i];
        }

        return results;
    };

    qa["getPassRate"] = []() {
        return visualQA().getPassRate();
    };

    qa["configure"] = [](const std::string& baselineDir, const std::string& testDir, const std::string& reportDir) {
        auto& system = visualQA();
        system.setBaselineDir(baselineDir);
        system.setTestDir(testDir);
        system.setReportDir(reportDir);
    };

    // Quality threshold constants
    sol::table thresholds = lua.create_table();
    thresholds["PASS_PSNR"] = VisualQA::ImageScore::PASS_PSNR;
    thresholds["PASS_SSIM"] = VisualQA::ImageScore::PASS_SSIM;
    thresholds["PASS_HIST"] = VisualQA::ImageScore::PASS_HIST;
    thresholds["PASS_SHAPE"] = VisualQA::ImageScore::PASS_SHAPE;
    thresholds["PASS_COLOR"] = VisualQA::ImageScore::PASS_COLOR;
    thresholds["PASS_EDGE"] = VisualQA::ImageScore::PASS_EDGE;
    qa["THRESHOLDS"] = thresholds;

    Log::info("Visual QA Lua bindings initialized");
}

void VisualQALuaBindings::update(sol::state& lua) {
    // Visual QA runs synchronously (tests complete inside the Lua call), so there is no
    // per-frame work; publish the latest pass rate for scripts that poll it.
    sol::optional<sol::table> qa = lua["VisualQA"];
    if (qa && g_visualQA) {
        (*qa)["lastPassRate"] = g_visualQA->getPassRate();
    }
}

} // namespace MagiTech
