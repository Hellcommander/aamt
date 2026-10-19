#pragma once

#include "ParticleFieldTypes.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/rendering/Shaders.hpp"
#include <atomic>
#include <cstdint>
#include <functional>
#include <future>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace MagiTech {
namespace ParticleFields {

// Shader stages come from the shared rendering layer (core/rendering/Shaders.hpp).
using MagiTech::ShaderStage;

// Particle data structure
struct Particle {
    glm::vec3 position;
    glm::vec3 velocity;
    glm::vec4 color;
    float size;
    float age;
    float lifetime;
    bool active;

    Particle() : position(0), velocity(0), color(1), size(1), age(0), lifetime(1), active(true) {}
};

// CPU-side texture data produced by the generators (noise volumes, colour ramps).
struct FieldTextureData {
    int width = 0;
    int height = 0;
    int depth = 0;                  // 1 for 1D/2D textures
    std::vector<uint8_t> rgba;      // width * height * depth * 4 bytes
};

/** Store for generated field textures, keyed by the handle the generators return. */
TextureHandle storeFieldTexture(FieldTextureData data);
std::optional<FieldTextureData> getFieldTexture(TextureHandle handle);

// Particle Field Asset Factory
class ParticleFieldAssetFactory {
public:
    ParticleFieldAssetFactory();
    ~ParticleFieldAssetFactory();

    // Main async generation function
    std::future<ParticleFieldBundle> generateAsync(
        const ParticleFieldParams& fp,
        const NoiseParams& np,
        const ColorRampParams& cr,
        const ParticleParams& pp);

    // Synchronous generation for immediate use
    ParticleFieldBundle generate(
        const ParticleFieldParams& fp,
        const NoiseParams& np,
        const ColorRampParams& cr,
        const ParticleParams& pp);

    // Cache management
    void clearCache();
    void setCacheSize(size_t maxEntries);
    size_t getCacheSize() const;
    size_t getCacheHits() const;
    size_t getCacheMisses() const;

    // Thread pool management
    void setMaxThreads(int threads);
    int getMaxThreads() const;

    // GPU acceleration
    void enableGPUAcceleration(bool enable);
    bool isGPUAccelerationEnabled() const;

    // Error handling
    std::string getLastError() const;
    void clearLastError();

    // Utility functions
    uint64_t hashCombine(const ParticleFieldParams& fp,
                        const NoiseParams& np,
                        const ColorRampParams& cr,
                        const ParticleParams& pp) const;

    // Field generation status
    bool isGenerating() const;
    float getGenerationProgress() const;

    // Asset validation
    bool validateParams(const ParticleFieldParams& fp,
                       const NoiseParams& np,
                       const ColorRampParams& cr,
                       const ParticleParams& pp) const;

private:
    // Core components
    std::unique_ptr<ConcurrentLRUCache<uint64_t, ParticleFieldBundle>> m_cache;
    std::unique_ptr<GeneratorTaskPool> m_pool;

    // Settings
    std::atomic<bool> m_gpuAccelerationEnabled;
    int m_maxThreads;
    mutable std::mutex m_errorMutex;
    mutable std::string m_lastError;

    // Generation tracking
    std::atomic<int> m_activeGenerations;
    std::atomic<float> m_generationProgress;

    // Statistics
    std::atomic<size_t> m_cacheHits;
    std::atomic<size_t> m_cacheMisses;

    // Internal methods
    void initializeComponents();
    void setLastError(const std::string& error) const;
    ParticleFieldBundle generateInternal(
        const ParticleFieldParams& fp,
        const NoiseParams& np,
        const ColorRampParams& cr,
        const ParticleParams& pp);

    // Validation helpers
    bool validateFieldParams(const ParticleFieldParams& fp) const;
    bool validateNoiseParams(const NoiseParams& np) const;
    bool validateColorRampParams(const ColorRampParams& cr) const;
    bool validateParticleParams(const ParticleParams& pp) const;
};

// Field Generation Namespace
namespace FieldGen {
    ParticleSystemHandle spawnField(
        const ParticleFieldParams& fp,
        const NoiseParams& np,
        const ParticleParams& pp,
        const TextureHandle& ramp);

    class ParticleSystem {
    public:
        ParticleSystem(bool gpuDriven);
        ~ParticleSystem();

        void configure(const glm::vec2& lifeTimeRange,
                      const glm::vec2& sizeRange,
                      bool alignToCamera);
        void setSpeedRange(const glm::vec2& speedRange);

        void emitVolume(const glm::vec3& boundsMin,
                       const glm::vec3& boundsMax,
                       float density,
                       float seed,
                       const NoiseParams& noiseParams);

        void emitSurface(const glm::vec3& boundsMin,
                        const glm::vec3& boundsMax,
                        float density,
                        float seed = 0.0f);

        void setColorRamp(const TextureHandle& ramp);
        /** Registers a copy of this system in the field registry and returns its handle. */
        ParticleSystemHandle create();

        // GPU/CPU mode management
        void enableComputeUpdate(const std::string& shaderPath);
        void enableCPUUpdate(std::function<void(Particle&, float)> updateFunc);
        bool isGPUDriven() const { return m_gpuDriven; }
        const std::string& getComputeShaderPath() const { return m_computeShaderPath; }

        /** Advances the particles by deltaTime (custom CPU update, then ageing). */
        void update(float deltaTime);

        // Particle data access
        size_t getParticleCount() const;
        size_t getActiveParticleCount() const;
        const std::vector<Particle>& getParticles() const;
        std::vector<Particle>& getParticles();

        // Performance monitoring
        float getUpdateTime() const;
        float getRenderTime() const;

    private:
        bool m_gpuDriven;
        glm::vec2 m_lifeTimeRange;
        glm::vec2 m_sizeRange;
        glm::vec2 m_speedRange;
        bool m_alignToCamera;
        TextureHandle m_colorRamp;
        std::vector<Particle> m_particles;
        std::function<void(Particle&, float)> m_cpuUpdateFunc;
        std::string m_computeShaderPath;

        // Performance tracking
        float m_updateTime;
        float m_renderTime;

        // Internal methods
        void initializeGPU();
        void initializeCPU();
        void updateParticles(float deltaTime);
        void applyColorRamp();
    };

    /** Registered particle systems (from spawnField / ParticleSystem::create). */
    std::shared_ptr<ParticleSystem> getSystem(ParticleSystemHandle handle);
    void destroySystem(ParticleSystemHandle handle);
}

// Noise Generation Namespace
namespace NoiseGen {
    TextureHandle buildVolume(const NoiseParams& np,
                             const glm::vec3& min,
                             const glm::vec3& max);

    class VolumeNoise {
    public:
        /** Resolution (per axis) of generated noise volumes. */
        static constexpr int kVolumeResolution = 32;

        static TextureHandle generate3D(const std::string& noiseType,
                                       int octaves,
                                       float frequency,
                                       float lacunarity,
                                       float gain,
                                       const glm::vec3& min,
                                       const glm::vec3& max,
                                       const glm::vec3& warp);

        // Noise type implementations (results in [0, 1])
        static float perlin3D(const glm::vec3& pos, float frequency);
        static float simplex3D(const glm::vec3& pos, float frequency);
        static float worley3D(const glm::vec3& pos, float frequency);
        static float fbm3D(const glm::vec3& pos,
                          int octaves,
                          float frequency,
                          float lacunarity,
                          float gain);
        /** Sample by noise type name ("Perlin", "Simplex", "Worley", "FBM"). */
        static float sample(const std::string& noiseType, const glm::vec3& pos, int octaves,
                            float frequency, float lacunarity, float gain);

        // Domain warping
        static glm::vec3 domainWarp(const glm::vec3& pos,
                                   const glm::vec3& warp,
                                   const std::string& noiseType);

        /** Uniform random value in [0, 1) from the shared generator (thread-safe). */
        static float random01();

    private:
        static std::mutex m_randomMutex;
        static std::mt19937 m_generator;
        static std::uniform_real_distribution<float> m_distribution;
    };
}

// Color Generation Namespace
namespace ColorGen {
    TextureHandle buildRamp(const ColorRampParams& cr);

    class RampBuilder {
    public:
        static TextureHandle create1DRamp(const std::vector<std::pair<float, glm::vec4>>& stops,
                                         int resolution,
                                         bool cyclic);

        // Color interpolation
        static glm::vec4 interpolateColors(const glm::vec4& color1,
                                          const glm::vec4& color2,
                                          float t);

        // Ramp validation
        static bool validateStops(const std::vector<std::pair<float, glm::vec4>>& stops);

        /** Colour of the ramp at t in [0, 1] (wraps around when cyclic). */
        static glm::vec4 evaluate(const std::vector<std::pair<float, glm::vec4>>& stops, float t, bool cyclic);

    private:
        static std::vector<uint8_t> generateRampTexture(const std::vector<std::pair<float, glm::vec4>>& stops,
                                                       int resolution,
                                                       bool cyclic);
    };
}

// Simulation Generation Namespace
namespace SimGen {
    class SimulationModule;

    /** Attaches a simulation module to a registered particle system. */
    void attachSim(ParticleSystemHandle ps, bool gpu);
    std::shared_ptr<SimulationModule> getSimulation(ParticleSystemHandle ps);

    class SimulationModule {
    public:
        SimulationModule(bool gpuDriven);
        ~SimulationModule();

        void enableComputeUpdate(const std::string& shaderPath);
        void enableCPUUpdate(std::function<void(Particle&, float)> updateFunc);

        /** Integrates forces (gravity, wind, turbulence) and ages the particles. */
        void update(std::vector<Particle>& particles, float deltaTime);

        // Physics parameters
        void setGravity(const glm::vec3& gravity);
        void setWind(const glm::vec3& wind);
        void setTurbulence(float intensity);

        // Performance monitoring
        float getUpdateTime() const;
        int getActiveParticles() const;
        bool isGPUDriven() const { return m_gpuDriven; }

    private:
        bool m_gpuDriven;
        std::string m_computeShaderPath;
        std::function<void(Particle&, float)> m_cpuUpdateFunc;

        // Physics parameters
        glm::vec3 m_gravity;
        glm::vec3 m_wind;
        float m_turbulence;
        float m_time;

        // Performance tracking
        float m_updateTime;
        int m_activeParticles;
    };
}

// LOD Generation Namespace
namespace LODGen {
    LODData compute(const LODParams& lp);

    class LODManager {
    public:
        LODManager(const LODParams& params);
        LODManager(const LODData& data);

        int selectLOD(float screenSize) const;
        float getDensityScale(int lodLevel) const;

        // LOD statistics
        int getLODCount() const;
        float getScreenThreshold(int lodLevel) const;

    private:
        std::vector<float> m_thresholds;
        std::vector<float> m_scales;
    };
}

// Shader Generation Namespace
namespace ShaderGen {
    ShaderHandle buildFieldShader(const ParticleFieldParams& fp,
                                 const NoiseParams& np,
                                 const ColorRampParams& cr,
                                 const ParticleParams& pp);

    class TemplateGen {
    public:
        /** Loads the template file (built-in field shader when missing), injects the
            defines after #version and substitutes {{KEY}} placeholders from defines + includes. */
        static std::string expand(const std::string& templatePath,
                                 const std::map<std::string, std::string>& defines,
                                 const std::map<std::string, std::string>& includes);

        // Template variables
        static std::string toString(bool value);
        static std::string toString(int value);
        static std::string toString(float value);
        static std::string toString(const std::string& value);

    private:
        static std::string replaceVariables(const std::string& templateStr,
                                          const std::map<std::string, std::string>& variables);
    };

    class CompileGen {
    public:
        static ShaderHandle compile(const std::string& source, ShaderStage stage);

        // Compilation options
        static void setOptimizationLevel(int level);
        static void enableDebugInfo(bool enable);

        // Error handling
        static std::string getCompilationErrors();
        static bool hasCompilationErrors();

    private:
        static std::mutex m_mutex;
        static int m_optimizationLevel;
        static bool m_debugInfoEnabled;
        static std::string m_compilationErrors;
    };
}

// Global factory instance
extern ParticleFieldAssetFactory fieldFactory;

} // namespace ParticleFields
} // namespace MagiTech
