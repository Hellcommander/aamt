#pragma once

#include "LightTypes.hpp"
#include "LightLODGen.hpp"
#include "GPUDeviceInterface.hpp"
#include <algorithm>
#include <cstdint>
#include <string>

namespace mt::light {

// Clustered light culling grid: the view frustum is split into tilesX * tilesY screen tiles and
// depthSlices exponential depth slices; each cluster receives the list of lights whose sphere overlaps it.
struct ClusterGrid {
    uint32_t tilesX{16};
    uint32_t tilesY{9};
    uint32_t depthSlices{24};
    uint32_t maxLightsPerCluster{128};
    uint32_t workgroupSize{64};

    uint32_t clusterCount() const { return tilesX * tilesY * depthSlices; }
    uint32_t dispatchGroups() const { return (clusterCount() + workgroupSize - 1) / workgroupSize; }
};

// Builds the cluster-culling compute pipeline. Buffer bindings expected by the generated shader:
//   0: LightBuffer   (readonly)  vec4 per light: xyz view-space position, w radius (<= 0 => affects every cluster)
//   1: ClusterBuffer (readonly)  view-space AABB per cluster (minPoint, maxPoint)
//   2: LightIndexBuffer          compacted light indices
//   3: ClusterGridBuffer         uvec2 per cluster: (offset into LightIndexBuffer, count)
//   4: CounterBuffer             global atomic index counter (reset to 0 each frame)
//   5: CullParams (uniform)      lightCount
class GpuCullingGen {
public:
    static GpuComputePipeline buildClusterCuller(const LODData& lod) {
        const ClusterGrid grid = createClusterGrid(lod);
        return GPUDeviceInterface::getInstance().createComputePipeline(generateCullingShader(grid));
    }

    // Grid parameters for a LOD table: finer depth slicing when more LOD levels (distance bands) need to be
    // distinguished, so lights switching LOD do not share coarse clusters with distant geometry.
    static ClusterGrid createClusterGrid(const LODData& lod) {
        ClusterGrid grid;
        const auto levels = static_cast<uint32_t>(std::max<size_t>(lod.levels.size(), 1));
        grid.depthSlices = std::clamp(16u + 8u * (levels - 1u), 16u, 48u);
        return grid;
    }

    static std::string generateCullingShader(const ClusterGrid& grid) {
        std::string shader = "#version 450\n";
        shader += "#define CLUSTER_X " + std::to_string(grid.tilesX) + "u\n";
        shader += "#define CLUSTER_Y " + std::to_string(grid.tilesY) + "u\n";
        shader += "#define CLUSTER_Z " + std::to_string(grid.depthSlices) + "u\n";
        shader += "#define MAX_LIGHTS_PER_CLUSTER " + std::to_string(grid.maxLightsPerCluster) + "u\n";
        shader += "#define WORKGROUP_SIZE " + std::to_string(grid.workgroupSize) + "\n";
        shader += R"(
#define CLUSTER_COUNT (CLUSTER_X * CLUSTER_Y * CLUSTER_Z)
layout(local_size_x = WORKGROUP_SIZE) in;

struct ClusterAABB {
    vec4 minPoint;
    vec4 maxPoint;
};

layout(std430, binding = 0) readonly buffer LightBuffer { vec4 lightSpheres[]; };
layout(std430, binding = 1) readonly buffer ClusterBuffer { ClusterAABB clusters[]; };
layout(std430, binding = 2) writeonly buffer LightIndexBuffer { uint lightIndices[]; };
layout(std430, binding = 3) writeonly buffer ClusterGridBuffer { uvec2 clusterGrid[]; };
layout(std430, binding = 4) buffer CounterBuffer { uint globalIndexCount; };
layout(std140, binding = 5) uniform CullParams { uint lightCount; };

float sqDistancePointAABB(vec3 p, vec3 mn, vec3 mx) {
    vec3 d = max(max(mn - p, vec3(0.0)), p - mx);
    return dot(d, d);
}

void main() {
    uint clusterIndex = gl_GlobalInvocationID.x;
    if (clusterIndex >= CLUSTER_COUNT) return;

    ClusterAABB cluster = clusters[clusterIndex];
    uint visible[MAX_LIGHTS_PER_CLUSTER];
    uint count = 0u;

    for (uint i = 0u; i < lightCount && count < MAX_LIGHTS_PER_CLUSTER; ++i) {
        vec4 sphere = lightSpheres[i];
        bool affects = sphere.w <= 0.0 ||
            sqDistancePointAABB(sphere.xyz, cluster.minPoint.xyz, cluster.maxPoint.xyz) <= sphere.w * sphere.w;
        if (affects) {
            visible[count] = i;
            ++count;
        }
    }

    uint offset = atomicAdd(globalIndexCount, count);
    for (uint i = 0u; i < count; ++i) {
        lightIndices[offset + i] = visible[i];
    }
    clusterGrid[clusterIndex] = uvec2(offset, count);
}
)";
        return shader;
    }
};

} // namespace mt::light
