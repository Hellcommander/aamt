#include "MeshAssetGenerator.hpp"
#include <random>
#include <sstream>
#include <algorithm>

namespace MagiTech::GeneratorAgent {

// Parameter creation

MeshAssetParams MeshAssetUtils::createMeshParams(const nlohmann::json& data) {
    MeshAssetParams params;
    
    if (data.contains("id")) {
        params.id = data["id"].get<std::string>();
    }
    if (data.contains("type")) {
        params.type = data["type"].get<std::string>();
    }
    if (data.contains("generateAsync")) {
        params.generateAsync = data["generateAsync"].get<bool>();
    }
    if (data.contains("cacheResult")) {
        params.cacheResult = data["cacheResult"].get<bool>();
    }
    if (data.contains("validateResult")) {
        params.validateResult = data["validateResult"].get<bool>();
    }
    if (data.contains("optimizeMesh")) {
        params.optimizeMesh = data["optimizeMesh"].get<bool>();
    }
    if (data.contains("maxGenerationTime")) {
        params.maxGenerationTime = data["maxGenerationTime"].get<float>();
    }
    if (data.contains("maxMemoryUsage")) {
        params.maxMemoryUsage = data["maxMemoryUsage"].get<size_t>();
    }
    
    // Mesh parameters
    if (data.contains("meshParams")) {
        auto meshData = data["meshParams"];
        if (meshData.contains("type")) {
            params.meshParams.type = meshData["type"].get<std::string>();
        }
        if (meshData.contains("dimensions")) {
            auto dims = meshData["dimensions"];
            params.meshParams.dimensions = glm::vec3(
                dims[0].get<float>(),
                dims[1].get<float>(),
                dims[2].get<float>()
            );
        }
        if (meshData.contains("subdivisions")) {
            params.meshParams.subdivisions = meshData["subdivisions"].get<int>();
        }
        if (meshData.contains("noiseFrequency")) {
            params.meshParams.noiseFrequency = meshData["noiseFrequency"].get<float>();
        }
        if (meshData.contains("isoThreshold")) {
            params.meshParams.isoThreshold = meshData["isoThreshold"].get<float>();
        }
        if (meshData.contains("generateNormals")) {
            params.meshParams.generateNormals = meshData["generateNormals"].get<bool>();
        }
        if (meshData.contains("generateTangents")) {
            params.meshParams.generateTangents = meshData["generateTangents"].get<bool>();
        }
        if (meshData.contains("generateUVs")) {
            params.meshParams.generateUVs = meshData["generateUVs"].get<bool>();
        }
        if (meshData.contains("weldVertices")) {
            params.meshParams.weldVertices = meshData["weldVertices"].get<bool>();
        }
        if (meshData.contains("seed")) {
            params.meshParams.seed = meshData["seed"].get<float>();
        }
    }
    
    // LOD parameters
    if (data.contains("lodParams")) {
        auto lodData = data["lodParams"];
        if (lodData.contains("baseMeshId")) {
            params.lodParams.baseMeshId = lodData["baseMeshId"].get<std::string>();
        }
        if (lodData.contains("screenSizes")) {
            params.lodParams.screenSizes = lodData["screenSizes"].get<std::vector<float>>();
        }
        if (lodData.contains("targetRatios")) {
            params.lodParams.targetRatios = lodData["targetRatios"].get<std::vector<float>>();
        }
        if (lodData.contains("preserveBorders")) {
            params.lodParams.preserveBorders = lodData["preserveBorders"].get<bool>();
        }
        if (lodData.contains("preserveUVSeams")) {
            params.lodParams.preserveUVSeams = lodData["preserveUVSeams"].get<bool>();
        }
        if (lodData.contains("maxTriangles")) {
            params.lodParams.maxTriangles = lodData["maxTriangles"].get<int>();
        }
        if (lodData.contains("errorThreshold")) {
            params.lodParams.errorThreshold = lodData["errorThreshold"].get<float>();
        }
    }
    
    // Material parameters
    if (data.contains("materialParams")) {
        auto matData = data["materialParams"];
        if (matData.contains("id")) {
            params.materialParams.id = matData["id"].get<std::string>();
        }
        if (matData.contains("shaderType")) {
            params.materialParams.shaderType = matData["shaderType"].get<std::string>();
        }
        if (matData.contains("albedo")) {
            auto albedo = matData["albedo"];
            params.materialParams.albedo = glm::vec4(
                albedo[0].get<float>(),
                albedo[1].get<float>(),
                albedo[2].get<float>(),
                albedo[3].get<float>()
            );
        }
        if (matData.contains("emissive")) {
            auto emissive = matData["emissive"];
            params.materialParams.emissive = glm::vec4(
                emissive[0].get<float>(),
                emissive[1].get<float>(),
                emissive[2].get<float>(),
                emissive[3].get<float>()
            );
        }
        if (matData.contains("metallic")) {
            params.materialParams.metallic = matData["metallic"].get<float>();
        }
        if (matData.contains("roughness")) {
            params.materialParams.roughness = matData["roughness"].get<float>();
        }
        if (matData.contains("usePBR")) {
            params.materialParams.usePBR = matData["usePBR"].get<bool>();
        }
        if (matData.contains("generateProcedural")) {
            params.materialParams.generateProcedural = matData["generateProcedural"].get<bool>();
        }
    }
    
    // UV parameters
    if (data.contains("uvParams")) {
        auto uvData = data["uvParams"];
        if (uvData.contains("atlasSize")) {
            auto size = uvData["atlasSize"];
            params.uvParams.atlasSize = glm::vec2(
                size[0].get<float>(),
                size[1].get<float>()
            );
        }
        if (uvData.contains("padding")) {
            params.uvParams.padding = uvData["padding"].get<float>();
        }
        if (uvData.contains("texelDensity")) {
            params.uvParams.texelDensity = uvData["texelDensity"].get<float>();
        }
        if (uvData.contains("preserveSeams")) {
            params.uvParams.preserveSeams = uvData["preserveSeams"].get<bool>();
        }
        if (uvData.contains("optimizeCharts")) {
            params.uvParams.optimizeCharts = uvData["optimizeCharts"].get<bool>();
        }
        if (uvData.contains("generateUDIM")) {
            params.uvParams.generateUDIM = uvData["generateUDIM"].get<bool>();
        }
        if (uvData.contains("maxCharts")) {
            params.uvParams.maxCharts = uvData["maxCharts"].get<uint32_t>();
        }
    }
    
    return params;
}

MeshAssetParams MeshAssetUtils::createMeshParams(const std::string& id, const std::string& type) {
    MeshAssetParams params;
    params.id = id;
    params.type = type;
    return params;
}

// Validation

bool MeshAssetUtils::validateMeshParams(const MeshAssetParams& params) {
    if (params.id.empty()) return false;
    if (params.type.empty()) return false;
    if (params.maxMemoryUsage == 0) return false;
    if (params.maxGenerationTime <= 0.0f) return false;
    
    // Validate mesh parameters
    if (params.meshParams.dimensions.x <= 0.0f || 
        params.meshParams.dimensions.y <= 0.0f || 
        params.meshParams.dimensions.z <= 0.0f) {
        return false;
    }
    if (params.meshParams.subdivisions <= 0) return false;
    if (params.meshParams.noiseFrequency < 0.0f) return false;
    if (params.meshParams.isoThreshold < 0.0f || params.meshParams.isoThreshold > 1.0f) return false;
    
    return true;
}

bool MeshAssetUtils::validateLODParams(const LODParams& params) {
    if (params.screenSizes.empty()) return false;
    if (params.targetRatios.empty()) return false;
    if (params.screenSizes.size() != params.targetRatios.size()) return false;
    if (params.maxTriangles <= 0) return false;
    if (params.errorThreshold < 0.0f) return false;
    
    // Validate screen sizes are in descending order
    for (size_t i = 1; i < params.screenSizes.size(); ++i) {
        if (params.screenSizes[i] >= params.screenSizes[i-1]) return false;
    }
    
    // Validate target ratios are in descending order
    for (size_t i = 1; i < params.targetRatios.size(); ++i) {
        if (params.targetRatios[i] >= params.targetRatios[i-1]) return false;
    }
    
    return true;
}

bool MeshAssetUtils::validateMaterialParams(const MaterialParams& params) {
    if (params.id.empty()) return false;
    if (params.shaderType.empty()) return false;
    if (params.metallic < 0.0f || params.metallic > 1.0f) return false;
    if (params.roughness < 0.0f || params.roughness > 1.0f) return false;
    if (params.ao < 0.0f || params.ao > 1.0f) return false;
    if (params.normalScale < 0.0f) return false;
    
    return true;
}

bool MeshAssetUtils::validateUVParams(const UVGenParams& params) {
    if (params.atlasSize.x <= 0.0f || params.atlasSize.y <= 0.0f) return false;
    if (params.padding < 0.0f) return false;
    if (params.texelDensity <= 0.0f) return false;
    if (params.maxCharts == 0) return false;
    
    return true;
}

// Conversion utilities

nlohmann::json MeshAssetUtils::paramsToJson(const MeshAssetParams& params) {
    nlohmann::json data;
    
    data["id"] = params.id;
    data["type"] = params.type;
    data["generateAsync"] = params.generateAsync;
    data["cacheResult"] = params.cacheResult;
    data["validateResult"] = params.validateResult;
    data["optimizeMesh"] = params.optimizeMesh;
    data["maxGenerationTime"] = params.maxGenerationTime;
    data["maxMemoryUsage"] = params.maxMemoryUsage;
    
    // Mesh parameters
    nlohmann::json meshData;
    meshData["type"] = params.meshParams.type;
    meshData["dimensions"] = {
        params.meshParams.dimensions.x,
        params.meshParams.dimensions.y,
        params.meshParams.dimensions.z
    };
    meshData["subdivisions"] = params.meshParams.subdivisions;
    meshData["noiseFrequency"] = params.meshParams.noiseFrequency;
    meshData["isoThreshold"] = params.meshParams.isoThreshold;
    meshData["generateNormals"] = params.meshParams.generateNormals;
    meshData["generateTangents"] = params.meshParams.generateTangents;
    meshData["generateUVs"] = params.meshParams.generateUVs;
    meshData["weldVertices"] = params.meshParams.weldVertices;
    meshData["seed"] = params.meshParams.seed;
    data["meshParams"] = meshData;
    
    // LOD parameters
    nlohmann::json lodData;
    lodData["baseMeshId"] = params.lodParams.baseMeshId;
    lodData["screenSizes"] = params.lodParams.screenSizes;
    lodData["targetRatios"] = params.lodParams.targetRatios;
    lodData["preserveBorders"] = params.lodParams.preserveBorders;
    lodData["preserveUVSeams"] = params.lodParams.preserveUVSeams;
    lodData["maxTriangles"] = params.lodParams.maxTriangles;
    lodData["errorThreshold"] = params.lodParams.errorThreshold;
    data["lodParams"] = lodData;
    
    // Material parameters
    nlohmann::json matData;
    matData["id"] = params.materialParams.id;
    matData["shaderType"] = params.materialParams.shaderType;
    matData["albedo"] = {
        params.materialParams.albedo.x,
        params.materialParams.albedo.y,
        params.materialParams.albedo.z,
        params.materialParams.albedo.w
    };
    matData["emissive"] = {
        params.materialParams.emissive.x,
        params.materialParams.emissive.y,
        params.materialParams.emissive.z,
        params.materialParams.emissive.w
    };
    matData["metallic"] = params.materialParams.metallic;
    matData["roughness"] = params.materialParams.roughness;
    matData["ao"] = params.materialParams.ao;
    matData["normalScale"] = params.materialParams.normalScale;
    matData["usePBR"] = params.materialParams.usePBR;
    matData["generateProcedural"] = params.materialParams.generateProcedural;
    data["materialParams"] = matData;
    
    // UV parameters
    nlohmann::json uvData;
    uvData["atlasSize"] = {
        params.uvParams.atlasSize.x,
        params.uvParams.atlasSize.y
    };
    uvData["padding"] = params.uvParams.padding;
    uvData["texelDensity"] = params.uvParams.texelDensity;
    uvData["preserveSeams"] = params.uvParams.preserveSeams;
    uvData["optimizeCharts"] = params.uvParams.optimizeCharts;
    uvData["generateUDIM"] = params.uvParams.generateUDIM;
    uvData["maxCharts"] = params.uvParams.maxCharts;
    data["uvParams"] = uvData;
    
    return data;
}

MeshAssetParams MeshAssetUtils::jsonToParams(const nlohmann::json& data) {
    return createMeshParams(data);
}

// Utility functions

std::string MeshAssetUtils::generateAssetId(const std::string& prefix) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(1000, 9999);
    
    std::stringstream ss;
    ss << prefix << "_" << dis(gen);
    return ss.str();
}

size_t MeshAssetUtils::estimateMemoryUsage(const MeshAssetParams& params) {
    size_t usage = 0;
    
    // Estimate based on mesh complexity
    size_t vertexCount = params.meshParams.subdivisions * params.meshParams.subdivisions;
    if (params.meshParams.type == "Cube") {
        vertexCount = 8; // 8 vertices for cube
    } else if (params.meshParams.type == "Sphere") {
        vertexCount = params.meshParams.subdivisions * params.meshParams.subdivisions * 2;
    } else if (params.meshParams.type == "Terrain") {
        vertexCount = params.meshParams.subdivisions * params.meshParams.subdivisions;
    }
    
    // Estimate memory per vertex (position, normal, tangent, UV, color, bone weights)
    size_t bytesPerVertex = 3 * 4 + 3 * 4 + 3 * 4 + 2 * 4 + 4 * 4 + 4 * 4 + 4 * 4; // 88 bytes
    usage += vertexCount * bytesPerVertex;
    
    // Estimate index buffer
    size_t indexCount = vertexCount * 3; // Rough estimate
    usage += indexCount * 4; // 4 bytes per index
    
    // Estimate LOD memory
    if (!params.lodParams.targetRatios.empty()) {
        for (float ratio : params.lodParams.targetRatios) {
            usage += static_cast<size_t>(usage * ratio);
        }
    }
    
    // Estimate material memory
    if (!params.materialParams.id.empty()) {
        usage += 1024; // Rough estimate for material
    }
    
    // Estimate UV atlas memory
    if (params.uvParams.atlasSize.x > 0 && params.uvParams.atlasSize.y > 0) {
        usage += static_cast<size_t>(params.uvParams.atlasSize.x * params.uvParams.atlasSize.y * 4); // RGBA
    }
    
    return usage;
}

double MeshAssetUtils::estimateGenerationTime(const MeshAssetParams& params) {
    double time = 0.0;
    
    // Base time for mesh generation
    if (params.meshParams.type == "Cube") {
        time = 0.001; // Very fast
    } else if (params.meshParams.type == "Sphere") {
        time = 0.01 * params.meshParams.subdivisions / 16.0; // Linear with subdivisions
    } else if (params.meshParams.type == "Terrain") {
        time = 0.1 * params.meshParams.subdivisions / 256.0; // Linear with resolution
    } else {
        time = 0.01; // Default
    }
    
    // Add time for optimizations
    if (params.optimizeMesh) {
        time *= 1.5;
    }
    
    // Add time for UV generation
    if (params.uvParams.atlasSize.x > 0 && params.uvParams.atlasSize.y > 0) {
        time += 0.05; // UV generation takes time
    }
    
    // Add time for material generation
    if (!params.materialParams.id.empty()) {
        time += 0.01;
    }
    
    // Add time for LOD generation
    if (!params.lodParams.targetRatios.empty()) {
        time += 0.02 * params.lodParams.targetRatios.size();
    }
    
    return time;
}

// Asset comparison

bool MeshAssetUtils::compareAssets(const MeshAssetBundle& a, const MeshAssetBundle& b) {
    if (a.isValid != b.isValid) return false;
    if (a.assetId != b.assetId) return false;
    if (a.assetType != b.assetType) return false;
    if (a.memoryUsage != b.memoryUsage) return false;
    
    // Compare meshes if both are valid
    if (a.isValid && b.isValid) {
        if (!a.mesh || !b.mesh) return false;
        if (a.mesh->vertexCount != b.mesh->vertexCount) return false;
        if (a.mesh->indexCount != b.mesh->indexCount) return false;
        if (a.mesh->triangleCount != b.mesh->triangleCount) return false;
    }
    
    return true;
}

float MeshAssetUtils::calculateSimilarity(const MeshAssetBundle& a, const MeshAssetBundle& b) {
    if (!a.isValid || !b.isValid) return 0.0f;
    if (!a.mesh || !b.mesh) return 0.0f;
    
    float similarity = 0.0f;
    int factors = 0;
    
    // Compare vertex counts
    float vertexSimilarity = 1.0f - std::abs(static_cast<float>(a.mesh->vertexCount - b.mesh->vertexCount)) / 
                              std::max(static_cast<float>(a.mesh->vertexCount), static_cast<float>(b.mesh->vertexCount));
    similarity += vertexSimilarity;
    factors++;
    
    // Compare index counts
    float indexSimilarity = 1.0f - std::abs(static_cast<float>(a.mesh->indexCount - b.mesh->indexCount)) / 
                             std::max(static_cast<float>(a.mesh->indexCount), static_cast<float>(b.mesh->indexCount));
    similarity += indexSimilarity;
    factors++;
    
    // Compare memory usage
    float memorySimilarity = 1.0f - std::abs(static_cast<float>(a.memoryUsage - b.memoryUsage)) / 
                             std::max(static_cast<float>(a.memoryUsage), static_cast<float>(b.memoryUsage));
    similarity += memorySimilarity;
    factors++;
    
    // Compare asset types
    if (a.assetType == b.assetType) {
        similarity += 1.0f;
        factors++;
    }
    
    return factors > 0 ? similarity / factors : 0.0f;
}

} // namespace MagiTech::GeneratorAgent 
