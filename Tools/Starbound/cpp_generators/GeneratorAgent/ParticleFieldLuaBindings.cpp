#include "ParticleFieldLuaBindings.hpp"
#include "ParticleFieldAssetFactory.hpp"
#include "ParticleFieldTypes.hpp"
#include <sol/sol.hpp>
#include <memory>
#include <future>

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

    lua.new_usertype<NoiseParams>("NoiseParams",
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

    lua.new_usertype<ParticleParams>("ParticleParams",
        sol::constructors<ParticleParams()>(),
        "sizeRange", &ParticleParams::sizeRange,
        "lifeTimeRange", &ParticleParams::lifeTimeRange,
        "speedRange", &ParticleParams::speedRange,
        "alignToCamera", &ParticleParams::alignToCamera
    );

    lua.new_usertype<LODParams>("LODParams",
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

    // Bind particle system management
    lua.set_function("get_particle_count", 
        [&](ParticleSystemHandle handle) {
            // TODO: Implement particle count retrieval
            return 0;
        });

    lua.set_function("update_particle_system", 
        [&](ParticleSystemHandle handle, float deltaTime) {
            // TODO: Implement particle system update
        });

    lua.set_function("enable_particle_compute_update", 
        [&](ParticleSystemHandle handle, const std::string& shaderPath) {
            // TODO: Implement compute shader enablement
        });

    lua.set_function("enable_particle_cpu_update", 
        [&](ParticleSystemHandle handle) {
            // TODO: Implement CPU update enablement
        });

    // Bind performance monitoring
    lua.set_function("get_particle_update_time", 
        [&](ParticleSystemHandle handle) {
            // TODO: Implement update time retrieval
            return 0.0f;
        });

    lua.set_function("get_particle_render_time", 
        [&](ParticleSystemHandle handle) {
            // TODO: Implement render time retrieval
            return 0.0f;
        });

    // Bind LOD management
    lua.set_function("select_lod_level", 
        [&](const LODData& lodData, float screenSize) {
            // TODO: Implement LOD selection
            return 0;
        });

    lua.set_function("get_density_scale", 
        [&](const LODData& lodData, int lodLevel) {
            // TODO: Implement density scale retrieval
            return 1.0f;
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
    lua.set_function("set_particle_gravity", 
        [&](ParticleSystemHandle handle, const glm::vec3& gravity) {
            // TODO: Implement gravity setting
        });

    lua.set_function("set_particle_wind", 
        [&](ParticleSystemHandle handle, const glm::vec3& wind) {
            // TODO: Implement wind setting
        });

    lua.set_function("set_particle_turbulence", 
        [&](ParticleSystemHandle handle, float intensity) {
            // TODO: Implement turbulence setting
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

} // namespace ParticleFields
} // namespace MagiTech
