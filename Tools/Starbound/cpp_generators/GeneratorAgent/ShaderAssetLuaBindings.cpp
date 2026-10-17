#include "ShaderAssetLuaBindings.hpp"
#include "ShaderAssetFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace ShaderAssets {

static std::vector<std::pair<std::future<ShaderAssetBundle>, std::string>> pendingAssets;
static std::mutex pendingAssetsMutex;

static std::mutex factoryMutex;
static std::shared_ptr<ShaderAssetFactory> sharedFactory;

void ShaderAssetLuaBindings::setFactory(std::shared_ptr<ShaderAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<ShaderAssetFactory> ShaderAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<ShaderAssetFactory>();
        sharedFactory->initialize(128, 4);
    }
    return sharedFactory;
}

CompileTarget stringToCompileTarget(const std::string& s) {
    if (s == "SPIRV") return CompileTarget::SPIRV;
    if (s == "DXIL") return CompileTarget::DXIL;
    if (s == "MetalAIR") return CompileTarget::MetalAIR;
    return CompileTarget::SPIRV; // Default
}

void ShaderAssetLuaBindings::bind(sol::state& lua) {
    lua.new_enum("ShaderStage",
        "Vertex", ShaderStage::Vertex,
        "Fragment", ShaderStage::Fragment,
        "Compute", ShaderStage::Compute,
        "TessControl", ShaderStage::TessControl,
        "TessEval", ShaderStage::TessEval,
        "Geometry", ShaderStage::Geometry
    );

    lua.new_enum("ShaderLang",
        "GLSL", ShaderLang::GLSL,
        "HLSL", ShaderLang::HLSL,
        "MSL", ShaderLang::MSL,
        "ESSL", ShaderLang::ESSL
    );

    lua.new_usertype<ShaderParams>("ShaderParams",
        sol::constructors<ShaderParams()>(),
        "id", &ShaderParams::id,
        "stage", &ShaderParams::stage,
        "lang", &ShaderParams::lang,
        "sourceTemplate", &ShaderParams::sourceTemplate,
        "defines", &ShaderParams::defines,
        "includes", &ShaderParams::includes
    );

    lua.new_usertype<PipelineParams>("PipelineParams",
        sol::constructors<PipelineParams()>(),
        "id", &PipelineParams::id,
        "stages", &PipelineParams::stages
        // Descriptor/state fields are raw pointers or opaque descriptor types and are not exposed to Lua
    );

    lua.new_usertype<ShaderAssetBundle>("ShaderAssetBundle",
        sol::no_constructor,
        "shader", &ShaderAssetBundle::shader,
        "pipelineState", &ShaderAssetBundle::pipelineState
    );

    lua.set_function("spawn_shader_asset",
        [](const ShaderParams& sp, sol::optional<PipelineParams> pp, sol::optional<std::string> tgt) {
            auto target = tgt ? stringToCompileTarget(*tgt) : CompileTarget::SPIRV;
            std::optional<PipelineParams> pipeline;
            if (pp) pipeline = *pp;
            auto future = factory()->generateAsync(sp, std::move(pipeline), target);
            std::lock_guard<std::mutex> lock(pendingAssetsMutex);
            pendingAssets.emplace_back(std::move(future), sp.id);
        }
    );
}

void ShaderAssetLuaBindings::poll_assets(sol::state& lua) {
    std::lock_guard<std::mutex> lock(pendingAssetsMutex);
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Shader asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("ShaderAssets", "Shader asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace ShaderAssets
} // namespace MagiTech
