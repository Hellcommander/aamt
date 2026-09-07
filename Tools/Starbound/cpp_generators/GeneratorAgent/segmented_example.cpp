#include "MechFactory.hpp"
#include "MechGenerators.hpp"
#include "MechLuaBindings.hpp"
#include <iostream>
#include <chrono>
#include <thread>
#include <future>
#include <vector>
#include <memory>

// Example: Segmented Mech Asset Generation Pipeline
// This demonstrates the integration of snake and worm mech capabilities
// with the existing hybrid C++23/26 + Lua mech generator system.

class SegmentedMechGameSystem {
private:
    std::unique_ptr<MechFactory> mechFactory_;
    std::vector<SegmentedMechInstanceState> activeSegmentedInstances_;
    std::chrono::high_resolution_clock::time_point lastUpdate_;
    lua_State* luaState_;
    
public:
    SegmentedMechGameSystem() {
        // Initialize the enhanced mech factory
        mechFactory_ = std::make_unique<MechFactory>();
        mechFactory_->initialize(100, 4); // 100 cache entries, 4 threads
        mechFactory_->setGPUAcceleration(true);
        
        // Initialize Lua state
        luaState_ = luaL_newstate();
        luaL_openlibs(luaState_);
        
        // Register enhanced Lua bindings
        registerMechLuaBindings(luaState_);
        
        lastUpdate_ = std::chrono::high_resolution_clock::now();
        
        std::cout << "SegmentedMechGameSystem: Initialized enhanced pipeline" << std::endl;
    }
    
    ~SegmentedMechGameSystem() {
        // Clean up instances
        for (auto& instance : activeSegmentedInstances_) {
            mechFactory_->destroySegmentedInstance(instance);
        }
        activeSegmentedInstances_.clear();
        
        // Clean up Lua
        if (luaState_) {
            lua_close(luaState_);
        }
        
        std::cout << "SegmentedMechGameSystem: Cleaned up all resources" << std::endl;
    }
    
    // Demonstrate snake mech generation
    void demonstrateSnakeMechGeneration() {
        std::cout << "\n=== Snake Mech Generation Demo ===" << std::endl;
        
        // Create snake mech parameters
        SegmentedMechParams snakeParams;
        snakeParams.id = "viper_mk1";
        snakeParams.mechType = "snake";
        snakeParams.segmentCount = 15;
        snakeParams.segmentLength = 1.0f;
        snakeParams.segmentRadius = 0.4f;
        snakeParams.connectorGap = 0.1f;
        snakeParams.maxBendAngleDeg = 45.0f;
        snakeParams.bendStiffness = 100.0f;
        snakeParams.enablePlating = true;
        snakeParams.platesPerSegment = 6;
        snakeParams.plateThickness = 0.05f;
        snakeParams.platingColor = glm::vec4(0.3f, 0.3f, 0.35f, 1.0f);
        snakeParams.stripeCount = 2;
        snakeParams.stripeWidth = 0.02f;
        snakeParams.stripeColor = glm::vec4(1.0f, 0.2f, 0.2f, 1.0f);
        snakeParams.stripeGlowIntensity = 3.0f;
        snakeParams.enableJointSparks = true;
        snakeParams.sparkRate = 20.0f;
        snakeParams.sparkLifetime = 0.4f;
        snakeParams.sparkColor = glm::vec4(1.0f, 0.8f, 0.5f, 1.0f);
        snakeParams.segmentMass = 10.0f;
        snakeParams.jointDamping = 0.7f;
        snakeParams.waveAmplitude = 1.5f;
        snakeParams.waveFrequency = 1.0f;
        snakeParams.animationProfile = "mech_slither";
        snakeParams.cockpitType = "internal";
        snakeParams.cockpitSegmentIndex = 5;
        snakeParams.cockpitRadius = 0.8f;
        snakeParams.colorPrimary = glm::vec3(0.2f, 0.3f, 0.35f);
        snakeParams.colorSecondary = glm::vec3(0.8f, 0.6f, 0.4f);
        
        // Create cockpit parameters
        CockpitParams cockpitParams;
        cockpitParams.seatWidth = 0.8f;
        cockpitParams.seatDepth = 1.2f;
        cockpitParams.seatHeight = 0.5f;
        cockpitParams.canopyRadius = 1.0f;
        cockpitParams.canopyHeight = 0.8f;
        cockpitParams.displayCount = 3;
        cockpitParams.gaugeCount = 6;
        cockpitParams.cockpitLight = true;
        cockpitParams.lightColor = glm::vec4(0.8f, 0.8f, 1.0f, 1.0f);
        cockpitParams.lightIntensity = 1.0f;
        
        // Create UI parameters
        UIParams uiParams;
        uiParams.iconSize = 64;
        uiParams.borderColor = glm::vec4(1.0f, 0.8f, 0.2f, 0.9f);
        uiParams.backgroundShape = "hexagon";
        uiParams.flashOnSelect = true;
        
        // Generate snake mech
        std::cout << "Generating snake mech..." << std::endl;
        auto future = mechFactory_->generateSegmentedAsync(snakeParams, cockpitParams, uiParams);
        
        try {
            SegmentedMechBundle bundle = future.get();
            SegmentedMechInstanceState instance = mechFactory_->createSegmentedInstance(snakeParams, cockpitParams);
            instance.bundle = bundle;
            activeSegmentedInstances_.push_back(instance);
            
            std::cout << "Snake mech generated successfully!" << std::endl;
            std::cout << "  Segment mesh: " << bundle.segmentMesh << std::endl;
            std::cout << "  Skeleton: " << bundle.skeleton << std::endl;
            std::cout << "  Animation: " << bundle.proceduralAnimation << std::endl;
            std::cout << "  Material: " << bundle.materialShader << std::endl;
            std::cout << "  Particles: " << bundle.sparkParticles << std::endl;
            std::cout << "  Physics: " << bundle.physicsAsset << std::endl;
            std::cout << "  Cockpit mesh: " << bundle.cockpitMesh << std::endl;
            std::cout << "  Icon: " << bundle.icon << std::endl;
            
        } catch (const std::exception& e) {
            std::cerr << "Failed to generate snake mech: " << e.what() << std::endl;
        }
    }
    
    // Demonstrate worm mech generation
    void demonstrateWormMechGeneration() {
        std::cout << "\n=== Worm Mech Generation Demo ===" << std::endl;
        
        // Create worm mech parameters
        SegmentedMechParams wormParams;
        wormParams.id = "sand_serpent_mkI";
        wormParams.mechType = "worm";
        wormParams.segmentCount = 25;
        wormParams.segmentLength = 1.2f;
        wormParams.segmentRadius = 0.5f;
        wormParams.taperProfile = "linear";
        wormParams.segmentShape = "cylinder";
        wormParams.jointFlexibility = 0.7f;
        wormParams.armorPlating = true;
        wormParams.platingDetailLevel = 2;
        wormParams.colorPrimary = glm::vec3(0.2f, 0.3f, 0.35f);
        wormParams.colorSecondary = glm::vec3(0.8f, 0.6f, 0.4f);
        wormParams.noiseDetail = 0.3f;
        wormParams.textureScale = 1.5f;
        wormParams.cockpitType = "external";
        wormParams.cockpitSegmentIndex = 5;
        wormParams.cockpitRadius = 0.8f;
        wormParams.cockpitOrientation = glm::vec3(0.0f, 1.0f, 0.0f);
        wormParams.animationProfile = "mech_slither";
        wormParams.aiProfile = "patrol";
        
        // Create external cockpit parameters
        CockpitParams externalCockpit;
        externalCockpit.seatWidth = 1.0f;
        externalCockpit.seatDepth = 1.5f;
        externalCockpit.seatHeight = 0.6f;
        externalCockpit.canopyRadius = 1.2f;
        externalCockpit.canopyHeight = 1.0f;
        externalCockpit.displayCount = 4;
        externalCockpit.gaugeCount = 8;
        externalCockpit.cockpitLight = true;
        externalCockpit.lightColor = glm::vec4(1.0f, 0.9f, 0.8f, 1.0f);
        externalCockpit.lightIntensity = 1.2f;
        externalCockpit.canopyAnimEnabled = true;
        externalCockpit.canopyOpenAngleDeg = 90.0f;
        externalCockpit.canopyOpenDuration = 2.0f;
        
        // Create UI parameters
        UIParams wormUI;
        wormUI.iconSize = 128;
        wormUI.borderColor = glm::vec4(0.8f, 0.4f, 0.2f, 0.9f);
        wormUI.backgroundShape = "hexagon";
        wormUI.flashOnSelect = true;
        
        // Generate worm mech
        std::cout << "Generating worm mech..." << std::endl;
        auto future = mechFactory_->generateSegmentedAsync(wormParams, externalCockpit, wormUI);
        
        try {
            SegmentedMechBundle bundle = future.get();
            SegmentedMechInstanceState instance = mechFactory_->createSegmentedInstance(wormParams, externalCockpit);
            instance.bundle = bundle;
            activeSegmentedInstances_.push_back(instance);
            
            std::cout << "Worm mech generated successfully!" << std::endl;
            std::cout << "  Segment mesh: " << bundle.segmentMesh << std::endl;
            std::cout << "  Skeleton: " << bundle.skeleton << std::endl;
            std::cout << "  Animation: " << bundle.proceduralAnimation << std::endl;
            std::cout << "  Material: " << bundle.materialShader << std::endl;
            std::cout << "  Particles: " << bundle.sparkParticles << std::endl;
            std::cout << "  Physics: " << bundle.physicsAsset << std::endl;
            std::cout << "  Cockpit mesh: " << bundle.cockpitMesh << std::endl;
            std::cout << "  Icon: " << bundle.icon << std::endl;
            
        } catch (const std::exception& e) {
            std::cerr << "Failed to generate worm mech: " << e.what() << std::endl;
        }
    }
    
    // Demonstrate dynamic segment management
    void demonstrateDynamicSegmentManagement() {
        std::cout << "\n=== Dynamic Segment Management Demo ===" << std::endl;
        
        if (activeSegmentedInstances_.empty()) {
            std::cout << "No instances available for dynamic management demo" << std::endl;
            return;
        }
        
        // Get first instance
        SegmentedMechInstanceState& instance = activeSegmentedInstances_[0];
        
        std::cout << "Initial segment count: " << instance.currentSegmentCount << std::endl;
        
        // Add segments
        std::cout << "Adding segments..." << std::endl;
        for (int i = 0; i < 5; ++i) {
            if (mechFactory_->addSegment(instance, instance.currentSegmentCount)) {
                std::cout << "  Added segment " << (instance.currentSegmentCount - 1) << std::endl;
            }
        }
        
        // Update segment properties
        std::cout << "Updating segment properties..." << std::endl;
        std::unordered_map<std::string, float> properties;
        properties["segmentRadius"] = 0.6f;
        properties["segmentLength"] = 1.3f;
        properties["maxBendAngleDeg"] = 60.0f;
        
        if (mechFactory_->updateSegmentProperties(instance, 3, properties)) {
            std::cout << "  Updated segment 3 properties" << std::endl;
        }
        
        // Remove segments
        std::cout << "Removing segments..." << std::endl;
        for (int i = 0; i < 2; ++i) {
            if (mechFactory_->removeSegment(instance, instance.currentSegmentCount - 1)) {
                std::cout << "  Removed segment " << (instance.currentSegmentCount + 1) << std::endl;
            }
        }
        
        std::cout << "Final segment count: " << instance.currentSegmentCount << std::endl;
    }
    
    // Demonstrate segmented mech animation
    void demonstrateSegmentedAnimation() {
        std::cout << "\n=== Segmented Mech Animation Demo ===" << std::endl;
        
        if (activeSegmentedInstances_.empty()) {
            std::cout << "No instances available for animation demo" << std::endl;
            return;
        }
        
        // Get first instance
        SegmentedMechInstanceState& instance = activeSegmentedInstances_[0];
        
        // Demonstrate different animation profiles
        std::vector<std::string> animations = {"mech_slither", "coil", "undulate"};
        
        for (const auto& animation : animations) {
            std::cout << "Starting animation: " << animation << std::endl;
            
            if (mechFactory_->startSegmentedAnimation(instance, animation)) {
                // Simulate animation playback
                for (int frame = 0; frame < 60; ++frame) {
                    float progress = frame / 60.0f;
                    mechFactory_->setSegmentedAnimationProgress(instance, progress);
                    
                    // Update instance
                    mechFactory_->updateSegmentedInstance(instance, 1.0f / 60.0f);
                    
                    if (frame % 20 == 0) {
                        std::cout << "  Animation progress: " << (progress * 100.0f) << "%" << std::endl;
                    }
                    
                    std::this_thread::sleep_for(std::chrono::milliseconds(16));
                }
            }
            
            // Pause between animations
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }
    
    // Demonstrate cockpit integration
    void demonstrateCockpitIntegration() {
        std::cout << "\n=== Cockpit Integration Demo ===" << std::endl;
        
        if (activeSegmentedInstances_.empty()) {
            std::cout << "No instances available for cockpit demo" << std::endl;
            return;
        }
        
        // Get first instance
        SegmentedMechInstanceState& instance = activeSegmentedInstances_[0];
        
        // Create new cockpit parameters
        CockpitParams newCockpit;
        newCockpit.seatWidth = 1.2f;
        newCockpit.seatDepth = 1.8f;
        newCockpit.seatHeight = 0.7f;
        newCockpit.canopyRadius = 1.5f;
        newCockpit.canopyHeight = 1.2f;
        newCockpit.displayCount = 6;
        newCockpit.gaugeCount = 12;
        newCockpit.cockpitLight = true;
        newCockpit.lightColor = glm::vec4(0.9f, 0.9f, 1.0f, 1.0f);
        newCockpit.lightIntensity = 1.5f;
        newCockpit.holographicHUD = true;
        newCockpit.canopyAnimEnabled = true;
        newCockpit.canopyOpenAngleDeg = 120.0f;
        newCockpit.canopyOpenDuration = 1.5f;
        
        std::cout << "Attaching new cockpit..." << std::endl;
        if (mechFactory_->attachCockpit(instance, newCockpit)) {
            std::cout << "  Cockpit attached successfully" << std::endl;
        }
        
        // Update cockpit parameters
        std::cout << "Updating cockpit parameters..." << std::endl;
        newCockpit.lightIntensity = 2.0f;
        newCockpit.displayCount = 8;
        
        if (mechFactory_->updateCockpitParams(instance, newCockpit)) {
            std::cout << "  Cockpit parameters updated" << std::endl;
        }
        
        // Detach cockpit
        std::cout << "Detaching cockpit..." << std::endl;
        if (mechFactory_->detachCockpit(instance)) {
            std::cout << "  Cockpit detached successfully" << std::endl;
        }
    }
    
    // Demonstrate Lua integration for segmented mechs
    void demonstrateLuaIntegration() {
        std::cout << "\n=== Lua Integration Demo ===" << std::endl;
        
        // Lua script for segmented mech generation
        const char* luaScript = R"(
            -- Create snake mech parameters in Lua
            local snakeParams = {
                id = "lua_viper",
                mechType = "snake",
                segmentCount = 20,
                segmentLength = 1.1,
                segmentRadius = 0.45,
                connectorGap = 0.12,
                maxBendAngleDeg = 50.0,
                bendStiffness = 120.0,
                enablePlating = true,
                platesPerSegment = 8,
                plateThickness = 0.06,
                platingColor = {0.3, 0.3, 0.35, 1.0},
                stripeCount = 3,
                stripeWidth = 0.025,
                stripeColor = {1.0, 0.3, 0.3, 1.0},
                stripeGlowIntensity = 4.0,
                enableJointSparks = true,
                sparkRate = 25.0,
                sparkLifetime = 0.5,
                sparkColor = {1.0, 0.9, 0.6, 1.0},
                segmentMass = 12.0,
                jointDamping = 0.8,
                waveAmplitude = 1.8,
                waveFrequency = 1.2,
                animationProfile = "mech_slither",
                cockpitType = "internal",
                cockpitSegmentIndex = 6,
                cockpitRadius = 0.9,
                colorPrimary = {0.25, 0.35, 0.4},
                colorSecondary = {0.9, 0.7, 0.5}
            }
            
            -- Create cockpit parameters
            local cockpitParams = {
                seatWidth = 0.9,
                seatDepth = 1.3,
                seatHeight = 0.55,
                canopyRadius = 1.1,
                canopyHeight = 0.9,
                displayCount = 4,
                gaugeCount = 7,
                cockpitLight = true,
                lightColor = {0.85, 0.85, 1.0, 1.0},
                lightIntensity = 1.1,
                holographicHUD = true,
                canopyAnimEnabled = true,
                canopyOpenAngleDeg = 95.0,
                canopyOpenDuration = 1.8
            }
            
            -- Create UI parameters
            local uiParams = {
                iconSize = 96,
                borderColor = {1.0, 0.9, 0.3, 0.9},
                backgroundShape = "hexagon",
                flashOnSelect = true
            }
            
            -- Generate segmented mech
            print("Generating segmented mech from Lua...")
            local future = mt_mech.generateSegmentedAsync(snakeParams, cockpitParams, uiParams)
            local bundle = future:get()
            
            -- Create instance
            local instance = mt_mech.createSegmentedInstance(snakeParams, cockpitParams)
            
            -- Start animation
            mt_mech.startSegmentedAnimation(instance, "mech_slither")
            
            -- Update instance
            mt_mech.updateSegmentedInstance(instance, 0.016)
            
            print("Lua segmented mech generation completed!")
            print("Segment mesh: " .. bundle.segmentMesh)
            print("Skeleton: " .. bundle.skeleton)
            print("Animation: " .. bundle.proceduralAnimation)
            print("Material: " .. bundle.materialShader)
            print("Particles: " .. bundle.sparkParticles)
            print("Physics: " .. bundle.physicsAsset)
            print("Cockpit mesh: " .. bundle.cockpitMesh)
            print("Icon: " .. bundle.icon)
        )";
        
        // Execute Lua script
        if (luaL_dostring(luaState_, luaScript) != LUA_OK) {
            std::cerr << "Lua script error: " << lua_tostring(luaState_, -1) << std::endl;
            lua_pop(luaState_, 1);
            return;
        }
        
        std::cout << "Lua script executed successfully!" << std::endl;
    }
    
    // Demonstrate batch generation
    void demonstrateBatchGeneration() {
        std::cout << "\n=== Batch Generation Demo ===" << std::endl;
        
        // Create multiple segmented mech configurations
        std::vector<std::pair<SegmentedMechParams, CockpitParams>> mechConfigs;
        
        // Configuration 1: Small snake
        SegmentedMechParams smallSnake;
        smallSnake.id = "small_snake";
        smallSnake.mechType = "snake";
        smallSnake.segmentCount = 10;
        smallSnake.segmentLength = 0.8f;
        smallSnake.segmentRadius = 0.3f;
        smallSnake.animationProfile = "mech_slither";
        
        CockpitParams smallCockpit;
        smallCockpit.seatWidth = 0.6f;
        smallCockpit.seatDepth = 1.0f;
        smallCockpit.canopyRadius = 0.8f;
        
        mechConfigs.push_back({smallSnake, smallCockpit});
        
        // Configuration 2: Large worm
        SegmentedMechParams largeWorm;
        largeWorm.id = "large_worm";
        largeWorm.mechType = "worm";
        largeWorm.segmentCount = 35;
        largeWorm.segmentLength = 1.5f;
        largeWorm.segmentRadius = 0.7f;
        largeWorm.animationProfile = "coil";
        
        CockpitParams largeCockpit;
        largeCockpit.seatWidth = 1.5f;
        largeCockpit.seatDepth = 2.0f;
        largeCockpit.canopyRadius = 1.8f;
        
        mechConfigs.push_back({largeWorm, largeCockpit});
        
        // Configuration 3: Fast serpent
        SegmentedMechParams fastSerpent;
        fastSerpent.id = "fast_serpent";
        fastSerpent.mechType = "serpent";
        fastSerpent.segmentCount = 18;
        fastSerpent.segmentLength = 1.2f;
        fastSerpent.segmentRadius = 0.4f;
        fastSerpent.animationProfile = "undulate";
        
        CockpitParams fastCockpit;
        fastCockpit.seatWidth = 0.9f;
        fastCockpit.seatDepth = 1.4f;
        fastCockpit.canopyRadius = 1.1f;
        
        mechConfigs.push_back({fastSerpent, fastCockpit});
        
        // Generate batch
        std::cout << "Generating batch of " << mechConfigs.size() << " segmented mechs..." << std::endl;
        auto futures = mechFactory_->generateSegmentedBatch(mechConfigs);
        
        // Wait for completion
        for (size_t i = 0; i < futures.size(); ++i) {
            try {
                SegmentedMechBundle bundle = futures[i].get();
                std::cout << "Generated mech " << (i + 1) << ": " << mechConfigs[i].first.id << std::endl;
                std::cout << "  Segment mesh: " << bundle.segmentMesh << std::endl;
                std::cout << "  Skeleton: " << bundle.skeleton << std::endl;
                std::cout << "  Animation: " << bundle.proceduralAnimation << std::endl;
                
                // Create instance
                SegmentedMechInstanceState instance = mechFactory_->createSegmentedInstance(
                    mechConfigs[i].first, mechConfigs[i].second);
                instance.bundle = bundle;
                activeSegmentedInstances_.push_back(instance);
                
            } catch (const std::exception& e) {
                std::cerr << "Failed to generate mech " << (i + 1) << ": " << e.what() << std::endl;
            }
        }
        
        std::cout << "Batch generation completed!" << std::endl;
    }
    
    // Demonstrate performance monitoring
    void demonstratePerformanceMonitoring() {
        std::cout << "\n=== Performance Monitoring Demo ===" << std::endl;
        
        const MechPerformanceMetrics& metrics = mechFactory_->getPerformanceMetrics();
        
        std::cout << "Performance Metrics:" << std::endl;
        std::cout << "  Total generations: " << metrics.totalGenerations.load() << std::endl;
        std::cout << "  Cache hits: " << metrics.cacheHits.load() << std::endl;
        std::cout << "  Cache misses: " << metrics.cacheMisses.load() << std::endl;
        std::cout << "  Cache hit rate: " << (metrics.getCacheHitRate() * 100.0) << "%" << std::endl;
        std::cout << "  Average generation time: " << metrics.getAverageGenerationTime() << " ms" << std::endl;
        std::cout << "  Active instances: " << metrics.activeInstances.load() << std::endl;
        std::cout << "  Morphing instances: " << metrics.morphingInstances.load() << std::endl;
        std::cout << "  Peak memory usage: " << metrics.peakMemoryUsage.load() << " bytes" << std::endl;
        
        // Segmented mech specific metrics
        std::cout << "\nSegmented Mech Metrics:" << std::endl;
        std::cout << "  Segmented cache size: " << mechFactory_->getSegmentedCacheSize() << std::endl;
        std::cout << "  Active segmented instances: " << activeSegmentedInstances_.size() << std::endl;
    }
    
    // Main demonstration
    void runFullDemonstration() {
        std::cout << "=== Segmented Mech Asset Generation Pipeline Full Demo ===" << std::endl;
        
        // 1. Snake mech generation
        demonstrateSnakeMechGeneration();
        
        // 2. Worm mech generation
        demonstrateWormMechGeneration();
        
        // 3. Dynamic segment management
        demonstrateDynamicSegmentManagement();
        
        // 4. Segmented mech animation
        demonstrateSegmentedAnimation();
        
        // 5. Cockpit integration
        demonstrateCockpitIntegration();
        
        // 6. Lua integration
        demonstrateLuaIntegration();
        
        // 7. Batch generation
        demonstrateBatchGeneration();
        
        // 8. Performance monitoring
        demonstratePerformanceMonitoring();
        
        std::cout << "\n=== Full demonstration completed! ===" << std::endl;
    }
};

// Main function to run the demonstration
int main() {
    try {
        SegmentedMechGameSystem gameSystem;
        gameSystem.runFullDemonstration();
        
        std::cout << "\nSegmented mech generator demonstration completed successfully!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception in main: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
} 
