#include "MechAssetFactory.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <iostream>
#include <chrono>
#include <thread>
#include <filesystem>
#include "vendor/yaml-cpp/yaml.h"
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace MechAssets {

// MechAssetFactory Implementation
MechAssetFactory::MechAssetFactory() {
    // Initialize core components
    generator_ = std::make_unique<MechGenerator>();
    assembler_ = std::make_unique<ModuleAssembler>();
    morphGen_ = std::make_unique<MorphGenerator>();
    physicsBuilder_ = std::make_unique<PhysicsRigBuilder>();
    lodBuilder_ = std::make_unique<LODBuilder>();
    packWriter_ = std::make_unique<PackageWriter>();
    loader_ = std::make_unique<MechLoader>();
    
    // Start hot reload thread if enabled
    if (hotReloadEnabled_) {
        hotReloadRunning_ = true;
        hotReloadThread_ = std::thread(&MechAssetFactory::hotReloadWorker, this);
    }
    
    lastMetricsUpdate_ = std::chrono::system_clock::now();
}

MechAssetFactory::~MechAssetFactory() {
    // Stop hot reload thread
    if (hotReloadRunning_) {
        hotReloadRunning_ = false;
        if (hotReloadThread_.joinable()) {
            hotReloadThread_.join();
        }
    }
    
    // Clear cache and instances
    clearCache();
    {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        activeInstances_.clear();
    }
}

MechHandle MechAssetFactory::createMech(const MechDefinitionParams& params) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Validate parameters
        if (!generator_->validateDefinition(params)) {
            std::cerr << "MechAssetFactory: Invalid mech definition for " << params.name << std::endl;
            return 0;
        }
        
        // Build asset
        auto asset = buildAsset(params);
        if (!asset) {
            std::cerr << "MechAssetFactory: Failed to build mech asset for " << params.name << std::endl;
            return 0;
        }
        
        // Cache the asset
        uint64_t cacheKey = asset->hashKey();
        {
            std::lock_guard<std::mutex> lock(cacheMutex_);
            assetCache_[cacheKey] = asset;
            handleToAsset_[asset->handle] = asset;
            
            // Enforce cache size limit
            if (assetCache_.size() > maxCacheSize_) {
                auto oldest = assetCache_.begin();
                handleToAsset_.erase(oldest->second->handle);
                assetCache_.erase(oldest);
            }
        }
        
        // Save to pack file
        std::string packPath = "assets/mechs/" + params.name + ".mechpack";
        if (!saveToPack(*asset, packPath)) {
            std::cerr << "MechAssetFactory: Failed to save mech pack for " << params.name << std::endl;
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        metrics_.totalProcessingTime.fetch_add(duration.count());
        metrics_.totalInstances.fetch_add(1);
        
        return asset->handle;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during mech creation: " << e.what() << std::endl;
        return 0;
    }
}

MechHandle MechAssetFactory::loadMech(const std::string& name, LODQuality quality) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        // Check cache first
        uint64_t cacheKey = generateCacheKey(name, quality);
        {
            std::lock_guard<std::mutex> lock(cacheMutex_);
            auto it = assetCache_.find(cacheKey);
            if (it != assetCache_.end()) {
                metrics_.cacheHits.fetch_add(1);
                return it->second->handle;
            }
        }
        
        metrics_.cacheMisses.fetch_add(1);
        
        // Load from pack file
        auto asset = loadFromPack(name, quality);
        if (!asset) {
            std::cerr << "MechAssetFactory: Failed to load mech from pack: " << name << std::endl;
            return 0;
        }
        
        // Cache the asset
        {
            std::lock_guard<std::mutex> lock(cacheMutex_);
            assetCache_[cacheKey] = asset;
            handleToAsset_[asset->handle] = asset;
        }
        
        // Update metrics
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        metrics_.totalProcessingTime.fetch_add(duration.count());
        
        return asset->handle;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during mech loading: " << e.what() << std::endl;
        return 0;
    }
}

bool MechAssetFactory::unloadMech(MechHandle handle) {
    try {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        
        auto it = handleToAsset_.find(handle);
        if (it == handleToAsset_.end()) {
            return false;
        }
        
        // Remove from both caches
        uint64_t assetHash = it->second->hashKey();
        assetCache_.erase(assetHash);
        handleToAsset_.erase(it);
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during mech unloading: " << e.what() << std::endl;
        return false;
    }
}

MechInstanceState MechAssetFactory::createInstance(MechHandle mechHandle) {
    MechInstanceState instance;
    
    try {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        auto it = handleToAsset_.find(mechHandle);
        if (it == handleToAsset_.end()) {
            return instance; // Return default instance
        }
        
        // Initialize instance with mech data
        instance.isActive = true;
        instance.currentForm = FormType::WALKER;
        instance.targetForm = FormType::WALKER;
        instance.morphProgress = 0.0f;
        instance.morphDuration = 1.0f;
        instance.isMorphing = false;
        
        // Generate unique instance ID
        uint64_t instanceId = std::hash<std::string>{}(it->second->name + std::to_string(mechHandle) + 
                                                      std::to_string(std::chrono::system_clock::now().time_since_epoch().count()));
        
        // Store instance
        {
            std::lock_guard<std::mutex> instanceLock(instanceMutex_);
            activeInstances_[instanceId] = instance;
        }
        
        metrics_.activeInstances.fetch_add(1);
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during instance creation: " << e.what() << std::endl;
    }
    
    return instance;
}

bool MechAssetFactory::destroyInstance(const MechInstanceState& instance) {
    try {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        
        // Find and remove instance
        for (auto it = activeInstances_.begin(); it != activeInstances_.end(); ++it) {
            if (it->second.hashKey() == instance.hashKey()) {
                activeInstances_.erase(it);
                metrics_.activeInstances.fetch_sub(1);
                return true;
            }
        }
        
        return false;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during instance destruction: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::updateInstance(MechInstanceState& instance, float deltaTime) {
    try {
        if (!instance.isActive) {
            return false;
        }
        
        // Update morph progress if morphing
        if (instance.isMorphing) {
            instance.morphProgress += deltaTime / instance.morphDuration;
            
            if (instance.morphProgress >= 1.0f) {
                instance.morphProgress = 1.0f;
                instance.isMorphing = false;
                instance.currentForm = instance.targetForm;
                metrics_.morphingInstances.fetch_sub(1);
            }
        }
        
        // Update physics (simplified - would integrate with physics engine)
        // instance.velocity += acceleration * deltaTime;
        // instance.position += instance.velocity * deltaTime;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during instance update: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::startMorph(MechInstanceState& instance, const std::string& profileName) {
    try {
        // Find the morph profile
        std::lock_guard<std::mutex> lock(cacheMutex_);
        for (const auto& pair : handleToAsset_) {
            const auto& asset = pair.second;
            for (const auto& profile : asset->morphProfiles) {
                if (profile.name == profileName) {
                    instance.targetForm = profile.toForm;
                    instance.morphDuration = profile.duration;
                    instance.morphProgress = 0.0f;
                    instance.isMorphing = true;
                    metrics_.morphingInstances.fetch_add(1);
                    return true;
                }
            }
        }
        
        return false;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during morph start: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::setMorphProgress(MechInstanceState& instance, float progress) {
    try {
        progress = std::clamp(progress, 0.0f, 1.0f);
        instance.morphProgress = progress;
        
        if (progress >= 1.0f) {
            instance.isMorphing = false;
            instance.currentForm = instance.targetForm;
            metrics_.morphingInstances.fetch_sub(1);
        }
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during morph progress set: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::pauseMorph(MechInstanceState& instance) {
    try {
        instance.isMorphing = false;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during morph pause: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::resumeMorph(MechInstanceState& instance) {
    try {
        if (instance.currentForm != instance.targetForm) {
            instance.isMorphing = true;
            metrics_.morphingInstances.fetch_add(1);
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during morph resume: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::watchDefinition(const std::string& mechName) {
    try {
        std::string defPath = "assets/mechs/" + mechName + ".mechdef";
        std::filesystem::path path(defPath);
        
        if (!std::filesystem::exists(path)) {
            std::cerr << "MechAssetFactory: Definition file not found: " << defPath << std::endl;
            return false;
        }
        
        std::lock_guard<std::mutex> lock(watcherMutex_);
        
        // Check if already watching
        for (const auto& watcher : fileWatchers_) {
            if (watcher.mechName == mechName) {
                return true;
            }
        }
        
        // Add new watcher
        FileWatcher watcher;
        watcher.mechName = mechName;
        watcher.definitionPath = path;
        watcher.lastModified = std::filesystem::last_write_time(path);
        watcher.lastHash = computeFileHash(path);
        
        fileWatchers_.push_back(watcher);
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during watch setup: " << e.what() << std::endl;
        return false;
    }
}

bool MechAssetFactory::unwatchDefinition(const std::string& mechName) {
    try {
        std::lock_guard<std::mutex> lock(watcherMutex_);
        
        fileWatchers_.erase(
            std::remove_if(fileWatchers_.begin(), fileWatchers_.end(),
                          [&mechName](const FileWatcher& w) { return w.mechName == mechName; }),
            fileWatchers_.end()
        );
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during watch removal: " << e.what() << std::endl;
        return false;
    }
}

void MechAssetFactory::processHotReloads() {
    checkFileChanges();
}

void MechAssetFactory::clearCache() {
    try {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        assetCache_.clear();
        handleToAsset_.clear();
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during cache clear: " << e.what() << std::endl;
    }
}

size_t MechAssetFactory::getCacheSize() const {
    try {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        return assetCache_.size();
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during cache size query: " << e.what() << std::endl;
        return 0;
    }
}

bool MechAssetFactory::isCached(const std::string& name) const {
    try {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        for (const auto& pair : assetCache_) {
            if (pair.second->name == name) {
                return true;
            }
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during cache check: " << e.what() << std::endl;
        return false;
    }
}

// Private implementation methods
uint64_t MechAssetFactory::generateCacheKey(const std::string& name, LODQuality quality) const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, name.c_str(), name.length());
    XXH64_update(&hash_state, &quality, sizeof(quality));
    return XXH64_digest(&hash_state);
}

std::shared_ptr<MechAsset> MechAssetFactory::buildAsset(const MechDefinitionParams& params) {
    try {
        auto asset = std::make_shared<MechAsset>();
        asset->name = params.name;
        asset->creationTime = std::chrono::system_clock::now();
        asset->gpuAccelerated = gpuAccelerationEnabled_;
        
        // Generate unique handle
        static MechHandle nextHandle = 1;
        asset->handle = nextHandle++;
        
        // Assemble modules
        if (!assembler_->assembleModules(params.modules, params.skeletonTemplate, *asset)) {
            std::cerr << "MechAssetFactory: Failed to assemble modules for " << params.name << std::endl;
            return nullptr;
        }
        
        // Generate morph targets
        if (!morphGen_->generateMorphTargets(params.morphProfiles, asset->modules, *asset)) {
            std::cerr << "MechAssetFactory: Failed to generate morph targets for " << params.name << std::endl;
            return nullptr;
        }
        
        // Build physics rig
        if (!physicsBuilder_->buildPhysicsRig(params.physicsRig, asset->modules, *asset)) {
            std::cerr << "MechAssetFactory: Failed to build physics rig for " << params.name << std::endl;
            return nullptr;
        }
        
        // Generate LODs
        if (!lodBuilder_->generateLODs(params.lods, asset->modules, *asset)) {
            std::cerr << "MechAssetFactory: Failed to generate LODs for " << params.name << std::endl;
            return nullptr;
        }
        
        // Copy profiles and LODs
        asset->morphProfiles = params.morphProfiles;
        asset->lods = params.lods;
        
        return asset;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during asset build: " << e.what() << std::endl;
        return nullptr;
    }
}

std::shared_ptr<MechAsset> MechAssetFactory::loadFromPack(const std::string& name, LODQuality quality) {
    try {
        std::string packPath = "assets/mechs/" + name + ".mechpack";
        auto asset = std::make_shared<MechAsset>();
        
        if (!packWriter_->readPackage(packPath, *asset)) {
            std::cerr << "MechAssetFactory: Failed to read mech pack: " << packPath << std::endl;
            return nullptr;
        }
        
        // Filter LODs based on quality
        asset->lods.erase(
            std::remove_if(asset->lods.begin(), asset->lods.end(),
                          [quality](const LODDefinition& lod) { return lod.quality != quality; }),
            asset->lods.end()
        );
        
        return asset;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during pack loading: " << e.what() << std::endl;
        return nullptr;
    }
}

bool MechAssetFactory::saveToPack(const MechAsset& asset, const std::string& name) {
    try {
        return packWriter_->writePackage(asset, name);
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during pack saving: " << e.what() << std::endl;
        return false;
    }
}

void MechAssetFactory::updateMetrics() {
    auto now = std::chrono::system_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(now - lastMetricsUpdate_);
    
    if (duration.count() >= 1) { // Update every second
        // Update memory usage (simplified)
        size_t cacheSize = getCacheSize();
        metrics_.peakMemoryUsage.store(std::max(metrics_.peakMemoryUsage.load(), 
                                               static_cast<uint64_t>(cacheSize * sizeof(MechAsset))));
        
        lastMetricsUpdate_ = now;
    }
}

void MechAssetFactory::checkFileChanges() {
    try {
        std::lock_guard<std::mutex> lock(watcherMutex_);
        
        for (auto& watcher : fileWatchers_) {
            if (!std::filesystem::exists(watcher.definitionPath)) {
                continue;
            }
            
            auto lastModified = std::filesystem::last_write_time(watcher.definitionPath);
            uint64_t currentHash = computeFileHash(watcher.definitionPath);
            
            if (lastModified > watcher.lastModified || currentHash != watcher.lastHash) {
                // File changed, rebuild asset
                if (rebuildAsset(watcher.mechName)) {
                    watcher.lastModified = lastModified;
                    watcher.lastHash = currentHash;
                    std::cout << "MechAssetFactory: Hot reloaded " << watcher.mechName << std::endl;
                }
            }
        }
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during file change check: " << e.what() << std::endl;
    }
}

bool MechAssetFactory::rebuildAsset(const std::string& mechName) {
    try {
        // Parse definition
        MechDefinitionParams params = generator_->parseDefinition("assets/mechs/" + mechName + ".mechdef");
        
        // Build new asset
        auto newAsset = buildAsset(params);
        if (!newAsset) {
            return false;
        }
        
        // Update cache
        std::lock_guard<std::mutex> lock(cacheMutex_);
        for (auto& pair : assetCache_) {
            if (pair.second->name == mechName) {
                // Update existing asset
                *pair.second = *newAsset;
                pair.second->creationTime = std::chrono::system_clock::now();
                return true;
            }
        }
        
        return false;
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during asset rebuild: " << e.what() << std::endl;
        return false;
    }
}

uint64_t MechAssetFactory::computeFileHash(const std::filesystem::path& path) const {
    try {
        std::ifstream file(path, std::ios::binary);
        if (!file) {
            return 0;
        }
        
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        
        char buffer[4096];
        while (file.read(buffer, sizeof(buffer))) {
            XXH64_update(&hash_state, buffer, file.gcount());
        }
        
        return XXH64_digest(&hash_state);
        
    } catch (const std::exception& e) {
        std::cerr << "MechAssetFactory: Exception during file hash computation: " << e.what() << std::endl;
        return 0;
    }
}

void MechAssetFactory::hotReloadWorker() {
    while (hotReloadRunning_) {
        processHotReloads();
        std::this_thread::sleep_for(std::chrono::milliseconds(100)); // Check every 100ms
    }
}

} // namespace MechAssets
} // namespace MagiTech 
