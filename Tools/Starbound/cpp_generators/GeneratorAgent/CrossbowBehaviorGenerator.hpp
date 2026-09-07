#pragma once

#include "CrossbowAssetFactory.hpp"
#include "core/Log.hpp"
#include "core/behavior/BehaviorTree.hpp"
#include "core/behavior/BehaviorNode.hpp"
#include <string>
#include <memory>
#include <vector>

namespace MagiTech {
namespace Crossbows {

// Crossbow Behavior Generator for C++ Backend
class CrossbowBehaviorGenerator {
public:
    struct BehaviorConfig {
        std::string behaviorName;
        bool useAutoReload;
        bool useDrawProgression;
        bool useMaterialEffects;
        bool useProjectileTracking;
        float drawSpeed;
        float reloadSpeed;
        float accuracyBonus;
        std::vector<std::string> specialAbilities;
    };

    struct BehaviorOutput {
        std::string behaviorFile;      // .behavior JSON
        std::string scriptFile;        // .cpp behavior implementation
        std::string headerFile;        // .hpp behavior interface
        std::string configFile;        // .json behavior config
    };

    CrossbowBehaviorGenerator();
    ~CrossbowBehaviorGenerator() = default;

    // Generate C++ behavior modules
    BehaviorOutput generateCrossbowBehavior(const CrossbowParams& params, const BehaviorConfig& config);
    BehaviorOutput generateBoltBehavior(const BoltParams& params, const BehaviorConfig& config);
    BehaviorOutput generateArrowBehavior(const ArrowParams& params, const BehaviorConfig& config);

    // Behavior tree generation
    std::string generateBehaviorTree(const CrossbowParams& params, const BehaviorConfig& config);
    std::string generateProjectileBehaviorTree(const BoltParams& params, const BehaviorConfig& config);
    std::string generateProjectileBehaviorTree(const ArrowParams& params, const BehaviorConfig& config);

    // C++ code generation
    std::string generateBehaviorHeader(const std::string& className, const CrossbowParams& params);
    std::string generateBehaviorImplementation(const std::string& className, const CrossbowParams& params, const BehaviorConfig& config);
    std::string generateProjectileBehaviorHeader(const std::string& className, const BoltParams& params);
    std::string generateProjectileBehaviorImplementation(const std::string& className, const BoltParams& params, const BehaviorConfig& config);

    // Behavior node generation
    std::string generateDrawNode(const CrossbowParams& params);
    std::string generateReleaseNode(const CrossbowParams& params);
    std::string generateReloadNode(const CrossbowParams& params);
    std::string generateProjectileNode(const BoltParams& params);
    std::string generateProjectileNode(const ArrowParams& params);

    // File system helpers
    bool createDirectory(const std::string& path);
    bool writeFile(const std::string& path, const std::string& content);
    std::string sanitizeClassName(const std::string& name);

private:
    std::string outputBasePath;
    
    // Template helpers
    std::string getBehaviorTreeTemplate();
    std::string getBehaviorHeaderTemplate();
    std::string getBehaviorImplementationTemplate();
    std::string getProjectileBehaviorTemplate();
    
    // Behavior logic generation
    std::string generateDrawLogic(const CrossbowParams& params, const BehaviorConfig& config);
    std::string generateReleaseLogic(const CrossbowParams& params, const BehaviorConfig& config);
    std::string generateReloadLogic(const CrossbowParams& params, const BehaviorConfig& config);
    std::string generateProjectileLogic(const BoltParams& params, const BehaviorConfig& config);
    std::string generateProjectileLogic(const ArrowParams& params, const BehaviorConfig& config);
    
    // Material effects
    std::string generateMaterialEffects(const CrossbowParams& params);
    std::string generateProjectileEffects(const BoltParams& params);
    std::string generateProjectileEffects(const ArrowParams& params);
    
    // Special abilities
    std::string generateSpecialAbilities(const std::vector<std::string>& abilities);
};

// Global behavior generator instance
extern std::unique_ptr<CrossbowBehaviorGenerator> g_behaviorGenerator;

} // namespace Crossbows
} // namespace MagiTech 
