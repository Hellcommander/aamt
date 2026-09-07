#include "ShaderAssetLuaBindings.hpp"
#include "ShaderAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace ShaderAssets {

static std::vector<std::pair<std::future<ShaderAssetBundle>, std::string>> pendingAssets;

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
        // Other fields are pointers or complex types, omitted for this stub
    );

    lua.new_usertype<ShaderAssetBundle>("ShaderAssetBundle",
        sol::no_constructor,
        "shader", &ShaderAssetBundle::shader,
        "pipelineState", &ShaderAssetBundle::pipelineState
    );

    lua.set_function("spawn_shader_asset",
        [&](const ShaderParams& sp, sol::optional<PipelineParams> pp, sol::optional<std::string> tgt) {
            auto factory = MainPlugin::instance().getShaderAssetFactory();
            auto target = tgt ? stringToCompileTarget(*tgt) : CompileTarget::SPIRV;
            pendingAssets.emplace_back(factory->generateAsync(sp, pp, target), sp.id);
        }
    );
}

void ShaderAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Shader asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace ShaderAssets
} // namespace MagiTech
