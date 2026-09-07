#pragma once
#include <string>
#include <vector>
#include <optional>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ShaderAssets {

using ShaderHandle = uint32_t;
using PipelineStateHandle = uint32_t;

// Forward declarations for complex descriptor types
struct ReflectionData;
struct DescriptorSetLayoutDesc;
struct VertexAttribDesc;
struct RasterStateDesc;
struct BlendStateDesc;
struct DepthStateDesc;

enum class ShaderStage   { Vertex, Fragment, Compute, TessControl, TessEval, Geometry };
enum class ShaderLang    { GLSL, HLSL, MSL, ESSL };
enum class CompileTarget { SPIRV, DXIL, MetalAIR };

struct ShaderParams {
    std::string id = "default_shader";
    ShaderStage stage = ShaderStage::Vertex;
    ShaderLang lang = ShaderLang::GLSL;
    std::string sourceTemplate;
    std::vector<std::string> defines;
    std::vector<std::string> includes;

    uint64_t hashKey() const;
};

struct PipelineParams {
    std::string id = "default_pipeline";
    std::vector<ShaderParams> stages;
    std::vector<DescriptorSetLayoutDesc> descriptorSets;
    std::vector<VertexAttribDesc> vertexLayout;
    RasterStateDesc* rasterState = nullptr;
    BlendStateDesc* blendState = nullptr;
    DepthStateDesc* depthState = nullptr;

    uint64_t hashKey() const;
};

struct ShaderAssetBundle {
    ShaderHandle shader;
    std::optional<ReflectionData> reflection;
    PipelineStateHandle pipelineState;
};

// --- Placeholder Descriptor Structs ---
struct ReflectionData {};
struct DescriptorSetLayoutDesc {};
struct VertexAttribDesc {};
struct RasterStateDesc {};
struct BlendStateDesc {};
struct DepthStateDesc {};

} // namespace ShaderAssets
} // namespace MagiTech
