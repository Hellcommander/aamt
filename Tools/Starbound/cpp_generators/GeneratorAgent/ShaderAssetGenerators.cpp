#include "ShaderAssetFactory.hpp"
#include "core/Log.hpp"
#include <fstream>
#include <sstream>
#include <atomic>

namespace MagiTech {
namespace ShaderAssets {

#define LOG_SHADER_GEN(Action, Id) Log::info("ShaderGen", "{}: {}", #Action, Id)

namespace {
    // Field-wise hashing (raw struct bytes would include padding and heap pointers).
    void hashBytes(XXH64_state_t& s, const void* data, size_t len) { XXH64_update(&s, data, len); }
    template <typename T>
    void hashPod(XXH64_state_t& s, const T& v) { hashBytes(s, &v, sizeof(T)); }
    void hashString(XXH64_state_t& s, const std::string& v) {
        hashPod(s, static_cast<uint64_t>(v.size()));
        hashBytes(s, v.data(), v.size());
    }
    void hashStrings(XXH64_state_t& s, const std::vector<std::string>& v) {
        hashPod(s, static_cast<uint64_t>(v.size()));
        for (const auto& str : v) hashString(s, str);
    }
}

// Hash function implementations
uint64_t ShaderParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    hashString(hash_state, id);
    hashPod(hash_state, stage);
    hashPod(hash_state, lang);
    hashString(hash_state, sourceTemplate);
    hashStrings(hash_state, defines);
    hashStrings(hash_state, includes);
    return XXH64_digest(&hash_state);
}

uint64_t PipelineParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    // Hash basic members, then iterate through vectors
    hashString(hash_state, id);
    hashPod(hash_state, static_cast<uint64_t>(stages.size()));
    for (const auto& stageParams : stages) hashPod(hash_state, stageParams.hashKey());
    // Descriptor structs carry no data yet; their counts and presence still distinguish layouts.
    hashPod(hash_state, static_cast<uint64_t>(descriptorSets.size()));
    hashPod(hash_state, static_cast<uint64_t>(vertexLayout.size()));
    hashPod(hash_state, rasterState != nullptr);
    hashPod(hash_state, blendState != nullptr);
    hashPod(hash_state, depthState != nullptr);
    return XXH64_digest(&hash_state);
}


namespace TemplateGen {
    std::string expand(const std::string& t, const std::vector<std::string>& d, const std::vector<std::string>& i) {
        LOG_SHADER_GEN(Expanding, t);
        // In a real implementation, this would load from a file path
        // For now, we'll treat the template as the source itself
        std::string src = t; 
        std::string defines_str;
        for(const auto& def : d) { defines_str += "#define " + def + "\n"; }
        std::string includes_str;
        for(const auto& inc : i) { includes_str += "#include \"" + inc + "\"\n"; }
        return includes_str + defines_str + src;
    }
} // namespace TemplateGen

namespace CompileGen {
    ShaderHandle compile(const std::string& src, ShaderStage s, ShaderLang l, CompileTarget t) {
        LOG_SHADER_GEN(Compiling, "Shader");
        // Implement shader compilation (glslang, DXC, SPIRV-Cross)
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace CompileGen

namespace ReflectionGen {
    ReflectionData inspect(const ShaderHandle& module) {
        LOG_SHADER_GEN(Reflecting, module);
        // Implement SPIR-V parsing for reflection data
        return ReflectionData{};
    }
} // namespace ReflectionGen

namespace PipelineGen {
    PipelineStateHandle create(const PipelineParams& pp, const ReflectionData& r) {
        LOG_SHADER_GEN(Creating PSO, pp.id);
        // Implement pipeline state object creation
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace PipelineGen

} // namespace ShaderAssets
} // namespace MagiTech
