#include "MeshAssetGenerator.hpp"
#include <algorithm>

namespace MagiTech::GeneratorAgent {

// Primitive presets

MeshAssetParams MeshAssetPresets::cube(const glm::vec3& dimensions) {
    MeshAssetParams params;
    params.id = "cube";
    params.type = "primitive";
    params.meshParams.type = "Cube";
    params.meshParams.dimensions = dimensions;
    params.meshParams.subdivisions = 1;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    return params;
}

MeshAssetParams MeshAssetPresets::sphere(float radius, uint32_t subdivisions) {
    MeshAssetParams params;
    params.id = "sphere";
    params.type = "primitive";
    params.meshParams.type = "Sphere";
    params.meshParams.dimensions = glm::vec3(radius * 2.0f);
    params.meshParams.subdivisions = subdivisions;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    return params;
}

MeshAssetParams MeshAssetPresets::cylinder(float radius, float height, uint32_t subdivisions) {
    MeshAssetParams params;
    params.id = "cylinder";
    params.type = "primitive";
    params.meshParams.type = "Cylinder";
    params.meshParams.dimensions = glm::vec3(radius * 2.0f, height, radius * 2.0f);
    params.meshParams.subdivisions = subdivisions;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    return params;
}

MeshAssetParams MeshAssetPresets::torus(float majorRadius, float minorRadius) {
    MeshAssetParams params;
    params.id = "torus";
    params.type = "primitive";
    params.meshParams.type = "Torus";
    params.meshParams.dimensions = glm::vec3(majorRadius * 2.0f, minorRadius * 2.0f, majorRadius * 2.0f);
    params.meshParams.subdivisions = 32;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    return params;
}

MeshAssetParams MeshAssetPresets::plane(const glm::vec2& size) {
    MeshAssetParams params;
    params.id = "plane";
    params.type = "primitive";
    params.meshParams.type = "Plane";
    params.meshParams.dimensions = glm::vec3(size.x, 0.0f, size.y);
    params.meshParams.subdivisions = 1;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    return params;
}

// Terrain presets

MeshAssetParams MeshAssetPresets::terrain(const glm::vec2& size, uint32_t resolution) {
    MeshAssetParams params;
    params.id = "terrain";
    params.type = "terrain";
    params.meshParams.type = "Terrain";
    params.meshParams.dimensions = glm::vec3(size.x, 10.0f, size.y);
    params.meshParams.subdivisions = resolution;
    params.meshParams.noiseFrequency = 0.01f;
    params.meshParams.seed = 42.0f;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    
    // Set up UV generation for terrain
    params.uvParams.unwrapMethod = UVGenParams::UnwrapMethod::Planar;
    params.uvParams.packingMethod = UVGenParams::PackingMethod::MaxRects;
    params.uvParams.atlasSize = glm::vec2(2048, 2048);
    params.uvParams.padding = 4.0f;
    params.uvParams.texelDensity = 1.0f;
    params.uvParams.preserveSeams = true;
    params.uvParams.optimizeCharts = true;
    params.uvParams.maxCharts = 8;
    
    return params;
}

MeshAssetParams MeshAssetPresets::mountain(const glm::vec2& size, uint32_t resolution) {
    MeshAssetParams params;
    params.id = "mountain";
    params.type = "terrain";
    params.meshParams.type = "Terrain";
    params.meshParams.dimensions = glm::vec3(size.x, 20.0f, size.y);
    params.meshParams.subdivisions = resolution;
    params.meshParams.noiseFrequency = 0.005f;
    params.meshParams.seed = 123.0f;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    
    // Set up UV generation for mountain
    params.uvParams.unwrapMethod = UVGenParams::UnwrapMethod::Planar;
    params.uvParams.packingMethod = UVGenParams::PackingMethod::MaxRects;
    params.uvParams.atlasSize = glm::vec2(4096, 4096);
    params.uvParams.padding = 8.0f;
    params.uvParams.texelDensity = 2.0f;
    params.uvParams.preserveSeams = true;
    params.uvParams.optimizeCharts = true;
    params.uvParams.maxCharts = 16;
    
    return params;
}

MeshAssetParams MeshAssetPresets::valley(const glm::vec2& size, uint32_t resolution) {
    MeshAssetParams params;
    params.id = "valley";
    params.type = "terrain";
    params.meshParams.type = "Terrain";
    params.meshParams.dimensions = glm::vec3(size.x, 15.0f, size.y);
    params.meshParams.subdivisions = resolution;
    params.meshParams.noiseFrequency = 0.008f;
    params.meshParams.seed = 456.0f;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    
    // Set up UV generation for valley
    params.uvParams.unwrapMethod = UVGenParams::UnwrapMethod::Planar;
    params.uvParams.packingMethod = UVGenParams::PackingMethod::MaxRects;
    params.uvParams.atlasSize = glm::vec2(2048, 2048);
    params.uvParams.padding = 4.0f;
    params.uvParams.texelDensity = 1.5f;
    params.uvParams.preserveSeams = true;
    params.uvParams.optimizeCharts = true;
    params.uvParams.maxCharts = 12;
    
    return params;
}

// Procedural presets

MeshAssetParams MeshAssetPresets::proceduralSphere(float radius, uint32_t subdivisions) {
    MeshAssetParams params;
    params.id = "procedural_sphere";
    params.type = "procedural";
    params.meshParams.type = "Sphere";
    params.meshParams.dimensions = glm::vec3(radius * 2.0f);
    params.meshParams.subdivisions = subdivisions;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    params.meshParams.seed = 789.0f;
    return params;
}

MeshAssetParams MeshAssetPresets::proceduralCube(const glm::vec3& dimensions) {
    MeshAssetParams params;
    params.id = "procedural_cube";
    params.type = "procedural";
    params.meshParams.type = "Cube";
    params.meshParams.dimensions = dimensions;
    params.meshParams.subdivisions = 1;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    params.meshParams.seed = 101.0f;
    return params;
}

MeshAssetParams MeshAssetPresets::proceduralCylinder(float radius, float height) {
    MeshAssetParams params;
    params.id = "procedural_cylinder";
    params.type = "procedural";
    params.meshParams.type = "Cylinder";
    params.meshParams.dimensions = glm::vec3(radius * 2.0f, height, radius * 2.0f);
    params.meshParams.subdivisions = 16;
    params.meshParams.generateNormals = true;
    params.meshParams.generateTangents = true;
    params.meshParams.generateUVs = true;
    params.meshParams.weldVertices = true;
    params.meshParams.seed = 202.0f;
    return params;
}

// Material presets

MaterialParams MeshAssetPresets::pbrMetal() {
    MaterialParams params;
    params.id = "pbr_metal";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.8f, 0.8f, 0.8f, 1.0f);
    params.emissive = glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    params.metallic = 1.0f;
    params.roughness = 0.2f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = false;
    return params;
}

MaterialParams MeshAssetPresets::pbrPlastic() {
    MaterialParams params;
    params.id = "pbr_plastic";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.9f, 0.9f, 0.9f, 1.0f);
    params.emissive = glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    params.metallic = 0.0f;
    params.roughness = 0.8f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = false;
    return params;
}

MaterialParams MeshAssetPresets::pbrWood() {
    MaterialParams params;
    params.id = "pbr_wood";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.6f, 0.4f, 0.2f, 1.0f);
    params.emissive = glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    params.metallic = 0.0f;
    params.roughness = 0.9f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = true;
    return params;
}

MaterialParams MeshAssetPresets::pbrStone() {
    MaterialParams params;
    params.id = "pbr_stone";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.5f, 0.5f, 0.5f, 1.0f);
    params.emissive = glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    params.metallic = 0.0f;
    params.roughness = 0.7f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = true;
    return params;
}

MaterialParams MeshAssetPresets::emissive() {
    MaterialParams params;
    params.id = "emissive";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.2f, 0.2f, 0.2f, 1.0f);
    params.emissive = glm::vec4(1.0f, 1.0f, 1.0f, 1.0f);
    params.metallic = 0.0f;
    params.roughness = 0.5f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = false;
    return params;
}

MaterialParams MeshAssetPresets::transparent() {
    MaterialParams params;
    params.id = "transparent";
    params.shaderType = "PBR";
    params.albedo = glm::vec4(0.8f, 0.8f, 0.8f, 0.5f);
    params.emissive = glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    params.metallic = 0.0f;
    params.roughness = 0.1f;
    params.ao = 1.0f;
    params.normalScale = 1.0f;
    params.usePBR = true;
    params.generateProcedural = false;
    return params;
}

// LOD presets

LODParams MeshAssetPresets::standardLOD() {
    LODParams params;
    params.baseMeshId = "";
    params.screenSizes = {0.4f, 0.15f, 0.03f};
    params.targetRatios = {1.0f, 0.4f, 0.15f};
    params.preserveBorders = true;
    params.preserveUVSeams = false;
    params.maxTriangles = 15000;
    params.errorThreshold = 0.08f;
    return params;
}

LODParams MeshAssetPresets::aggressiveLOD() {
    LODParams params;
    params.baseMeshId = "";
    params.screenSizes = {0.6f, 0.25f, 0.05f};
    params.targetRatios = {1.0f, 0.25f, 0.1f};
    params.preserveBorders = false;
    params.preserveUVSeams = false;
    params.maxTriangles = 8000;
    params.errorThreshold = 0.15f;
    return params;
}

LODParams MeshAssetPresets::conservativeLOD() {
    LODParams params;
    params.baseMeshId = "";
    params.screenSizes = {0.2f, 0.08f, 0.02f};
    params.targetRatios = {1.0f, 0.6f, 0.25f};
    params.preserveBorders = true;
    params.preserveUVSeams = true;
    params.maxTriangles = 25000;
    params.errorThreshold = 0.05f;
    return params;
}

// UV presets

UVGenParams MeshAssetPresets::standardUV() {
    UVGenParams params;
    params.unwrapMethod = UVGenParams::UnwrapMethod::Auto;
    params.packingMethod = UVGenParams::PackingMethod::MaxRects;
    params.atlasSize = glm::vec2(1024, 1024);
    params.padding = 2.0f;
    params.texelDensity = 1.0f;
    params.preserveSeams = true;
    params.optimizeCharts = true;
    params.generateUDIM = false;
    params.maxCharts = 8;
    return params;
}

UVGenParams MeshAssetPresets::optimizedUV() {
    UVGenParams params;
    params.unwrapMethod = UVGenParams::UnwrapMethod::LSCM;
    params.packingMethod = UVGenParams::PackingMethod::Guillotine;
    params.atlasSize = glm::vec2(2048, 2048);
    params.padding = 4.0f;
    params.texelDensity = 1.5f;
    params.preserveSeams = true;
    params.optimizeCharts = true;
    params.generateUDIM = false;
    params.maxCharts = 16;
    return params;
}

UVGenParams MeshAssetPresets::seamlessUV() {
    UVGenParams params;
    params.unwrapMethod = UVGenParams::UnwrapMethod::Planar;
    params.packingMethod = UVGenParams::PackingMethod::Skyline;
    params.atlasSize = glm::vec2(1024, 1024);
    params.padding = 8.0f;
    params.texelDensity = 1.0f;
    params.preserveSeams = false;
    params.optimizeCharts = true;
    params.generateUDIM = false;
    params.maxCharts = 4;
    return params;
}

} // namespace MagiTech::GeneratorAgent 
