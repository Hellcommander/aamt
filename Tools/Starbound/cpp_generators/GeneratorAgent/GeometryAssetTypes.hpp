#pragma once
#include <string>
#include <vector>
#include <variant>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Geometry {

using MeshHandle = uint32_t;

enum class GeometryType { Primitive, Extrusion, LSystem, Surface, Boolean };

struct PrimitiveParams {
    GeometryType type = GeometryType::Primitive;
    std::string shape;
    glm::vec3 dimensions;
    int subdivisions;
    uint64_t hashKey() const;
};

struct ExtrusionParams {
    GeometryType type = GeometryType::Extrusion;
    std::vector<glm::vec2> profile;
    std::vector<glm::vec3> path;
    int segments;
    float twist;
    bool capEnds;
    uint64_t hashKey() const;
};

struct LSystemParams {
    GeometryType type = GeometryType::LSystem;
    std::string axiom;
    std::vector<std::pair<char, std::string>> rules;
    int iterations;
    float angle;
    float step;
    uint64_t hashKey() const;
};

struct SurfaceParams {
    GeometryType type = GeometryType::Surface;
    std::string func;
    glm::vec2 uRange;
    glm::vec2 vRange;
    glm::ivec2 resolution;
    uint64_t hashKey() const;
};

struct BooleanParams {
    GeometryType type = GeometryType::Boolean;
    std::string op;
    MeshHandle meshA;
    MeshHandle meshB;
    uint64_t hashKey() const;
};

using GeometryRequest = std::variant<
    PrimitiveParams,
    ExtrusionParams,
    LSystemParams,
    SurfaceParams,
    BooleanParams
>;

struct LODParams {
    std::vector<float> screenSizes;
    std::vector<float> simplificationFactors; // e.g. 1.0, 0.5, 0.25
    uint64_t hashKey() const;
};

struct LODData {
    std::vector<float> thresholds;
    std::vector<std::vector<MeshHandle>> lodMeshes;
};

struct GeometryBundle {
    std::vector<MeshHandle> meshes;
    LODData lod;
};

} // namespace Geometry
} // namespace MagiTech
