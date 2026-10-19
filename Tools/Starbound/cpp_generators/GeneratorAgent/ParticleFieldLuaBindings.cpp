#include "ParticleFieldLuaBindings.hpp"
#include "ParticleFieldAssetFactory.hpp"
#include "ParticleFieldTypes.hpp"
#include "core/Log.hpp"
#include <sol/sol.hpp>
#include <chrono>
#include <memory>
#include <mutex>
#include <future>
#include <utility>
#include <vector>

namespace MagiTech {
namespace ParticleFields {

void bindParticleFieldToLua(sol::state& lua) {
    // Bind parameter structures
    lua.new_usertype<ParticleFieldParams>("ParticleFieldParams",
        sol::constructors<ParticleFieldParams()>(),
        "id", &ParticleFieldParams::id,
        "boundsMin", &ParticleFieldParams::boundsMin,
        "boundsMax", &ParticleFieldParams::boundsMax,
        "density", &ParticleFieldParams::density,
        "useVolume", &ParticleFieldParams::useVolume,
        "gpuDriven", &ParticleFieldParams::gpuDriven,
        "seed", &ParticleFieldParams::seed,
        "lod", &ParticleFieldParams::lod
    );

    lua.new_usertype<NoiseParams>("ParticleFieldNoiseParams",
        sol::constructors<NoiseParams()>(),
        "noiseType", &NoiseParams::noiseType,
        "octaves", &NoiseParams::octaves,
        "frequency", &NoiseParams::frequency,
        "lacunarity", &NoiseParams::lacunarity,
        "gain", &NoiseParams::gain,
        "warp", &NoiseParams::warp
    );

    lua.new_usertype<ColorRampParams>("ColorRampParams",
        sol::constructors<ColorRampParams()>(),
        "stops", &ColorRampParams::stops,
        "cyclic", &ColorRampParams::cyclic,
        "resolution", &ColorRampParams::resolution
    );

    lua.new_usertype<ParticleParams>("ParticleFieldParticleParams",
        sol::constructors<ParticleParams()>(),
        "sizeRange", &ParticleParams::sizeRange,
        "lifeTimeRange", &ParticleParams::lifeTimeRange,
        "speedRange", &ParticleParams::speedRange,
        "alignToCamera", &ParticleParams::alignToCamera
    );

    lua.new_usertype<LODParams>("ParticleFieldLODParams",
        sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes,
        "densityScales", &LODParams::densityScales
    );

    lua.new_usertype<ParticleFieldBundle>("ParticleFieldBundle",
        sol::constructors<ParticleFieldBundle()>(),
        "particles", &ParticleFieldBundle::particles,
        "noiseVolume", &ParticleFieldBundle::noiseVolume,
        "colorRampTex", &ParticleFieldBundle::colorRampTex,
        "fieldShader", &ParticleFieldBundle::fieldShader,
        "lodData", &ParticleFieldBundle::lodData
    );

    lua.new_usertype<LODData>("LODData",
        sol::constructors<LODData()>(),
        "thresholds", &LODData::thresholds,
        "scales", &LODData::scales
    );

    // Bind factory functions
    lua.set_function("spawn_field_asset", 
        [&](const ParticleFieldParams& fp, 
            const NoiseParams& np,
            const ColorRampParams& cr, 
            const ParticleParams& pp) {
            return fieldFactory.generateAsync(fp, np, cr, pp).get();
        });

    lua.set_function("spawn_field_asset_sync", 
        [&](const ParticleFieldParams& fp, 
            const NoiseParams& np,
            const ColorRampParams& cr, 
            const ParticleParams& pp) {
            return fieldFactory.generate(fp, np, cr, pp);
        });

    // Bind factory management functions
    lua.set_function("clear_particle_field_cache", 
        [&]() { fieldFactory.clearCache(); });

    lua.set_function("set_particle_field_cache_size", 
        [&](size_t size) { fieldFactory.setCacheSize(size); });

    lua.set_function("get_particle_field_cache_size", 
        [&]() { return fieldFactory.getCacheSize(); });

    lua.set_function("get_particle_field_cache_hits", 
        [&]() { return fieldFactory.getCacheHits(); });

    lua.set_function("get_particle_field_cache_misses", 
        [&]() { return fieldFactory.getCacheMisses(); });

    // Bind thread pool management
    lua.set_function("set_particle_field_max_threads", 
        [&](int threads) { fieldFactory.setMaxThreads(threads); });

    lua.set_function("get_particle_field_max_threads", 
        [&]() { return fieldFactory.getMaxThreads(); });

    // Bind GPU acceleration
    lua.set_function("enable_particle_field_gpu_acceleration", 
        [&](bool enable) { fieldFactory.enableGPUAcceleration(enable); });

    lua.set_function("is_particle_field_gpu_acceleration_enabled", 
        [&]() { return fieldFactory.isGPUAccelerationEnabled(); });

    // Bind generation status
    lua.set_function("is_particle_field_generating", 
        [&]() { return fieldFactory.isGenerating(); });

    lua.set_function("get_particle_field_generation_progress", 
        [&]() { return fieldFactory.getGenerationProgress(); });

    // Bind error handling
    lua.set_function("get_particle_field_last_error", 
        [&]() { return fieldFactory.getLastError(); });

    lua.set_function("clear_particle_field_last_error", 
        [&]() { fieldFactory.clearLastError(); });

    // Bind parameter validation
    lua.set_function("validate_particle_field_params", 
        [&](const ParticleFieldParams& fp, 
            const NoiseParams& np,
            const ColorRampParams& cr, 
            const ParticleParams& pp) {
            return fieldFactory.validateParams(fp, np, cr, pp);
        });

    // Bind noise generation functions
    lua.set_function("generate_noise_volume", 
        [&](const NoiseParams& np, const glm::vec3& min, const glm::vec3& max) {
            return NoiseGen::buildVolume(np, min, max);
        });

    // Bind color ramp generation
    lua.set_function("generate_color_ramp", 
        [&](const ColorRampParams& cr) {
            return ColorGen::buildRamp(cr);
        });

    // Bind LOD computation
    lua.set_function("compute_lod_data", 
        [&](const LODParams& lp) {
            return LODGen::compute(lp);
        });

    // Bind shader generation
    lua.set_function("build_field_shader", 
        [&](const ParticleFieldParams& fp, 
            const NoiseParams& np,
            const ColorRampParams& cr, 
            const ParticleParams& pp) {
            return ShaderGen::buildFieldShader(fp, np, cr, pp);
        });

    // Bind simulation functions
    lua.set_function("attach_particle_simulation", 
        [&](ParticleSystemHandle ps, bool gpu) {
            SimGen::attachSim(ps, gpu);
        });

    // Bind field generation
    lua.set_function("spawn_particle_field", 
        [&](const ParticleFieldParams& fp, 
            const NoiseParams& np,
            const ParticleParams& pp, 
            const TextureHandle& ramp) {
            return FieldGen::spawnField(fp, np, pp, ramp);
        });

    // Bind utility functions for creating parameter structures
    lua.set_function("create_particle_field_params", 
        [](const std::string& id, 
           const glm::vec3& boundsMin, 
           const glm::vec3& boundsMax,
           float density, 
           bool useVolume, 
           bool gpuDriven, 
           float seed) {
            ParticleFieldParams params;
            params.id = id;
            params.boundsMin = boundsMin;
            params.boundsMax = boundsMax;
            params.density = density;
            params.useVolume = useVolume;
            params.gpuDriven = gpuDriven;
            params.seed = seed;
            return params;
        });

    lua.set_function("create_noise_params", 
        [](const std::string& noiseType, 
           int octaves, 
           float frequency, 
           float lacunarity, 
           float gain, 
           const glm::vec3& warp) {
            NoiseParams params;
            params.noiseType = noiseType;
            params.octaves = octaves;
            params.frequency = frequency;
            params.lacunarity = lacunarity;
            params.gain = gain;
            params.warp = warp;
            return params;
        });

    lua.set_function("create_color_ramp_params", 
        [](const std::vector<std::pair<float, glm::vec4>>& stops, 
           bool cyclic, 
           int resolution) {
            ColorRampParams params;
            params.stops = stops;
            params.cyclic = cyclic;
            params.resolution = resolution;
            return params;
        });

    lua.set_function("create_particle_params", 
        [](const glm::vec2& sizeRange, 
           const glm::vec2& lifeTimeRange, 
           const glm::vec2& speedRange, 
           bool alignToCamera) {
            ParticleParams params;
            params.sizeRange = sizeRange;
            params.lifeTimeRange = lifeTimeRange;
            params.speedRange = speedRange;
            params.alignToCamera = alignToCamera;
            return params;
        });

    lua.set_function("create_lod_params", 
        [](const std::vector<float>& screenSizes, 
           const std::vector<float>& densityScales) {
            LODParams params;
            params.screenSizes = screenSizes;
            params.densityScales = densityScales;
            return params;
        });

    // Bind particle system management (systems registered by spawnField)
    lua.set_function("get_particle_count",
        [](ParticleSystemHandle handle) -> size_t {
            auto system = FieldGen::getSystem(handle);
            return system ? system->getActiveParticleCount() : 0;
        });

    lua.set_function("update_particle_system",
        [](ParticleSystemHandle handle, float deltaTime) -> bool {
            auto system = FieldGen::getSystem(handle);
            if (!system) return false;
            system->update(deltaTime);
            if (auto sim = SimGen::getSimulation(handle)) {
                sim->update(system->getParticles(), deltaTime);
            }
            return true;
        });

    lua.set_function("enable_particle_compute_update",
        [](ParticleSystemHandle handle, const std::string& shaderPath) -> bool {
            auto system = FieldGen::getSystem(handle);
            if (!system) return false;
            system->enableComputeUpdate(shaderPath);
            if (auto sim = SimGen::getSimulation(handle)) {
                sim->enableComputeUpdate(shaderPath);
            }
            return true;
        });

    // Optional Lua callback(particle_table, dt) run per active particle on update;
    // without a callback the built-in force integration (SimGen) drives the system.
    lua.set_function("enable_particle_cpu_update",
        [](ParticleSystemHandle handle, sol::optional<sol::protected_function> callback) -> bool {
            auto system = FieldGen::getSystem(handle);
            if (!system) return false;
            if (!SimGen::getSimulation(handle)) {
                SimGen::attachSim(handle, false);
            }
            if (callback && callback->valid()) {
                sol::protected_function fn = *callback;
                system->enableCPUUpdate([fn](Particle& particle, float dt) {
                    sol::state_view lua(fn.lua_state());
                    sol::table p = lua.create_table();
                    p["position"] = particle.position;
                    p["velocity"] = particle.velocity;
                    p["color"] = particle.color;
                    p["size"] = particle.size;
                    p["age"] = particle.age;
                    p["lifetime"] = particle.lifetime;
                    p["active"] = particle.active;
                    auto result = fn(p, dt);
                    if (!result.valid()) return;
                    particle.position = p.get_or("position", particle.position);
                    particle.velocity = p.get_or("velocity", particle.velocity);
                    particle.color = p.get_or("color", particle.color);
                    particle.size = p.get_or("size", particle.size);
                    particle.active = p.get_or("active", particle.active);
                });
            } else {
                system->enableCPUUpdate(nullptr);
            }
            return true;
        });

    // Bind performance monitoring
    lua.set_function("get_particle_update_time",
        [](ParticleSystemHandle handle) -> float {
            auto system = FieldGen::getSystem(handle);
            float time = system ? system->getUpdateTime() : 0.0f;
            if (auto sim = SimGen::getSimulation(handle)) time += sim->getUpdateTime();
            return time;
        });

    lua.set_function("get_particle_render_time",
        [](ParticleSystemHandle handle) -> float {
            auto system = FieldGen::getSystem(handle);
            return system ? system->getRenderTime() : 0.0f;
        });

    // Bind LOD management
    lua.set_function("select_lod_level",
        [](const LODData& lodData, float screenSize) {
            return LODGen::LODManager(lodData).selectLOD(screenSize);
        });

    lua.set_function("get_density_scale",
        [](const LODData& lodData, int lodLevel) {
            return LODGen::LODManager(lodData).getDensityScale(lodLevel);
        });

    // Bind shader compilation
    lua.set_function("set_shader_optimization_level", 
        [&](int level) {
            ShaderGen::CompileGen::setOptimizationLevel(level);
        });

    lua.set_function("enable_shader_debug_info", 
        [&](bool enable) {
            ShaderGen::CompileGen::enableDebugInfo(enable);
        });

    lua.set_function("get_shader_compilation_errors", 
        [&]() {
            return ShaderGen::CompileGen::getCompilationErrors();
        });

    lua.set_function("has_shader_compilation_errors", 
        [&]() {
            return ShaderGen::CompileGen::hasCompilationErrors();
        });

    // Bind simulation parameters
    // (attaches a CPU simulation module when the system has none yet)
    auto simulationFor = [](ParticleSystemHandle handle) -> std::shared_ptr<SimGen::SimulationModule> {
        if (!FieldGen::getSystem(handle)) return nullptr;
        if (!SimGen::getSimulation(handle)) SimGen::attachSim(handle, false);
        return SimGen::getSimulation(handle);
    };

    lua.set_function("set_particle_gravity",
        [simulationFor](ParticleSystemHandle handle, const glm::vec3& gravity) -> bool {
            auto sim = simulationFor(handle);
            if (!sim) return false;
            sim->setGravity(gravity);
            return true;
        });

    lua.set_function("set_particle_wind",
        [simulationFor](ParticleSystemHandle handle, const glm::vec3& wind) -> bool {
            auto sim = simulationFor(handle);
            if (!sim) return false;
            sim->setWind(wind);
            return true;
        });

    lua.set_function("set_particle_turbulence",
        [simulationFor](ParticleSystemHandle handle, float intensity) -> bool {
            auto sim = simulationFor(handle);
            if (!sim) return false;
            sim->setTurbulence(intensity);
            return true;
        });

    lua.set_function("destroy_particle_system",
        [](ParticleSystemHandle handle) {
            FieldGen::destroySystem(handle);
        });

    // Asynchronous generation: results are delivered by ParticleFieldLuaBindings::poll_assets
    // through the global Lua function on_particle_field_ready(id, bundle).
    lua.set_function("spawn_field_asset_async",
        [](const ParticleFieldParams& fp,
           const NoiseParams& np,
           const ColorRampParams& cr,
           const ParticleParams& pp) -> bool {
            try {
                ParticleFieldLuaBindings::queue(fieldFactory.generateAsync(fp, np, cr, pp), fp.id);
                return true;
            } catch (const std::exception&) {
                return false; // details via get_particle_field_last_error()
            }
        });

    // Bind noise type constants
    lua["NOISE_TYPE_PERLIN"] = "Perlin";
    lua["NOISE_TYPE_SIMPLEX"] = "Simplex";
    lua["NOISE_TYPE_WORLEY"] = "Worley";
    lua["NOISE_TYPE_FBM"] = "FBM";

    // Bind quality constants
    lua["LOD_QUALITY_HIGH"] = 0;
    lua["LOD_QUALITY_MEDIUM"] = 1;
    lua["LOD_QUALITY_LOW"] = 2;

    // Bind shader stage constants
    lua["SHADER_STAGE_VERTEX"] = static_cast<int>(ShaderStage::Vertex);
    lua["SHADER_STAGE_FRAGMENT"] = static_cast<int>(ShaderStage::Fragment);
    lua["SHADER_STAGE_COMPUTE"] = static_cast<int>(ShaderStage::Compute);
    lua["SHADER_STAGE_GEOMETRY"] = static_cast<int>(ShaderStage::Geometry);

    // Register example usage
    lua.script(R"(
        -- Example: Create a starfield particle system
        function create_starfield()
            local fieldParams = create_particle_field_params(
                "starfield",
                {-50, -50, -50},  -- boundsMin
                {50, 50, 50},     -- boundsMax
                0.1,               -- density
                true,              -- useVolume
                true,              -- gpuDriven
                1234               -- seed
            )
            
            local noiseParams = create_noise_params(
                "FBM",            -- noiseType
                5,                -- octaves
                0.02,             -- frequency
                2.0,              -- lacunarity
                0.5,              -- gain
                {0.1, 0.2, 0.3}  -- warp
            )
            
            local colorStops = {
                {0.0, {0, 0, 0, 0}},      -- transparent at start
                {0.5, {1, 1, 1, 1}},      -- white at middle
                {1.0, {1, 1, 0.8, 1}}     -- slightly yellow at end
            }
            
            local colorParams = create_color_ramp_params(
                colorStops,
                false,  -- cyclic
                256     -- resolution
            )
            
            local particleParams = create_particle_params(
                {2, 5},    -- sizeRange
                {3, 8},    -- lifeTimeRange
                {1, 3},    -- speedRange
                true       -- alignToCamera
            )
            
            local lodParams = create_lod_params(
                {0.5, 0.2, 0.0},  -- screenSizes
                {1.0, 0.5, 0.2}   -- densityScales
            )
            
            fieldParams.lod = lodParams
            
            local field = spawn_field_asset(fieldParams, noiseParams, colorParams, particleParams)
            return field
        end
        
        -- Example: Create a dust swarm
        function create_dust_swarm()
            local fieldParams = create_particle_field_params(
                "dust_swarm",
                {-10, -10, -10},
                {10, 10, 10},
                0.5,
                true,
                false,
                5678
            )
            
            local noiseParams = create_noise_params(
                "Perlin",
                3,
                0.1,
                2.0,
                0.7,
                {0.05, 0.05, 0.05}
            )
            
            local colorStops = {
                {0.0, {0.8, 0.6, 0.4, 0.3}},
                {1.0, {0.9, 0.7, 0.5, 0.1}}
            }
            
            local colorParams = create_color_ramp_params(colorStops, false, 128)
            local particleParams = create_particle_params({1, 3}, {5, 10}, {0.5, 1.5}, true)
            
            local field = spawn_field_asset(fieldParams, noiseParams, colorParams, particleParams)
            return field
        end
        
        -- Example: Create a magical glow effect
        function create_magical_glow()
            local fieldParams = create_particle_field_params(
                "magical_glow",
                {-5, -5, -5},
                {5, 5, 5},
                0.3,
                true,
                true,
                9999
            )
            
            local noiseParams = create_noise_params(
                "Worley",
                4,
                0.05,
                2.5,
                0.6,
                {0.2, 0.1, 0.3}
            )
            
            local colorStops = {
                {0.0, {0.2, 0.8, 1.0, 0.0}},
                {0.3, {0.5, 0.9, 1.0, 0.8}},
                {0.7, {0.8, 0.4, 1.0, 0.6}},
                {1.0, {1.0, 0.2, 0.8, 0.0}}
            }
            
            local colorParams = create_color_ramp_params(colorStops, true, 512)
            local particleParams = create_particle_params({3, 8}, {2, 6}, {0.2, 0.8}, true)
            
            local field = spawn_field_asset(fieldParams, noiseParams, colorParams, particleParams)
            return field
        end
    )");
}

namespace {
struct PendingFields {
    std::mutex mutex;
    std::vector<std::pair<std::future<ParticleFieldBundle>, std::string>> jobs;
};
PendingFields& pendingFields() {
    static PendingFields pending;
    return pending;
}
} // namespace

void ParticleFieldLuaBindings::bind(sol::state& lua) {
    bindParticleFieldToLua(lua);
}

void ParticleFieldLuaBindings::queue(std::future<ParticleFieldBundle> future, const std::string& id) {
    std::lock_guard<std::mutex> lock(pendingFields().mutex);
    pendingFields().jobs.emplace_back(std::move(future), id);
}

void ParticleFieldLuaBindings::poll_assets(sol::state& lua) {
    std::vector<std::pair<std::future<ParticleFieldBundle>, std::string>> ready;
    {
        std::lock_guard<std::mutex> lock(pendingFields().mutex);
        auto& jobs = pendingFields().jobs;
        for (auto it = jobs.begin(); it != jobs.end();) {
            if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                ready.push_back(std::move(*it));
                it = jobs.erase(it);
            } else {
                ++it;
            }
        }
    }
    for (auto& [future, id] : ready) {
        try {
            ParticleFieldBundle bundle = future.get();
            sol::protected_function onReady = lua["on_particle_field_ready"];
            if (onReady.valid()) {
                auto result = onReady(id, bundle);
                if (!result.valid()) {
                    sol::error err = result;
                    Log::error("ParticleField", "on_particle_field_ready failed for {}: {}", id, err.what());
                }
            }
        } catch (const std::exception& e) {
            Log::error("ParticleField", "Particle field generation failed for {}: {}", id, e.what());
            sol::protected_function onError = lua["on_particle_field_error"];
            if (onError.valid()) {
                onError(id, std::string(e.what()));
            }
        }
    }
}

} // namespace ParticleFields
} // namespace MagiTech
