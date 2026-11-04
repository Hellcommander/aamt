#pragma once

#include "LightTypes.hpp"
#include "GPUDeviceInterface.hpp"
#include <string>

namespace mt::light {

// Generates the deferred lighting shader variant for a light (type, cookie, volumetric) and registers it
// with GPUDeviceInterface (identical variants share one pipeline handle).
//
// Bindings: 0 = LightBlock (std140, matches mt::light::LightUBO), 1 = shadow map (sampler2DArrayShadow),
//           2 = cookie (sampler2D), 3 = volumetric noise (sampler3D),
//           4..6 = G-buffer world position / normal / albedo, 7 = FrameBlock (camera data).
class LightShaderGen {
public:
    static GpuPipeline compileLightingPipeline(LightType type, bool useCookie, float volumetricDensity) {
        const bool volumetric = volumetricDensity > 0.0f;
        return GPUDeviceInterface::getInstance().createGraphicsPipeline(vertexShader(),
                                                                        fragmentShader(type, useCookie, volumetric));
    }

    static std::string vertexShader() {
        return R"(#version 450
// Fullscreen triangle; the light is evaluated per pixel against the G-buffer.
layout(location = 0) out vec2 vUV;
void main() {
    vec2 pos = vec2((gl_VertexIndex << 1) & 2, gl_VertexIndex & 2);
    vUV = pos;
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
}
)";
    }

    static std::string fragmentShader(LightType type, bool useCookie, bool volumetric) {
        std::string src = "#version 450\n";
        src += "#define LIGHT_TYPE " + std::to_string(static_cast<uint32_t>(type)) + "\n";
        src += "#define USE_COOKIE " + std::string(useCookie ? "1" : "0") + "\n";
        src += "#define USE_VOLUMETRIC " + std::string(volumetric ? "1" : "0") + "\n";
        src += R"(
#define LIGHT_DIRECTIONAL 0
#define LIGHT_POINT 1
#define LIGHT_SPOT 2
#define LIGHT_AREA 3

layout(location = 0) in vec2 vUV;
layout(location = 0) out vec4 outColor;

layout(std140, binding = 0) uniform LightBlock {
    vec4  positionType;
    vec4  directionRange;
    vec4  colorIntensity;
    vec4  spotArea;
    vec4  shadowParams;
    vec4  cookieUV;
    vec4  volumetricParams;
    vec4  scatterColor;
    vec4  flickerParams;
    uvec4 extra;
} light;

layout(binding = 1) uniform sampler2DArrayShadow shadowMap;
layout(binding = 2) uniform sampler2D cookieTex;
layout(binding = 3) uniform sampler3D volumeNoise;
layout(binding = 4) uniform sampler2D gPosition;
layout(binding = 5) uniform sampler2D gNormal;
layout(binding = 6) uniform sampler2D gAlbedo;

layout(std140, binding = 7) uniform FrameBlock {
    mat4  lightViewProj[6];
    vec4  cameraPosTime; // xyz camera position, w time (s)
    float flickerScale;  // evaluated on the CPU with FlickerGen::evaluate
} frame;

float rangeAttenuation(float dist, float range) {
    if (range <= 0.0) return 1.0;
    float x = clamp(1.0 - pow(dist / range, 4.0), 0.0, 1.0);
    return x * x / (dist * dist + 1.0);
}

float shadowFactor(vec3 worldPos, vec3 N, vec3 L) {
    if (light.shadowParams.x < 0.5) return 1.0;
    int layer = 0;
#if LIGHT_TYPE == LIGHT_POINT
    vec3 d = worldPos - light.positionType.xyz;
    vec3 a = abs(d);
    layer = a.x > a.y && a.x > a.z ? (d.x > 0.0 ? 0 : 1) : (a.y > a.z ? (d.y > 0.0 ? 2 : 3) : (d.z > 0.0 ? 4 : 5));
#elif LIGHT_TYPE == LIGHT_DIRECTIONAL
    float viewDist = length(worldPos - frame.cameraPosTime.xyz);
    float cascades = max(light.volumetricParams.w, 1.0);
    layer = int(min(floor(log2(max(viewDist, 1.0)) / 3.0), cascades - 1.0));
#endif
    vec3 biased = worldPos + N * light.shadowParams.w;
    vec4 clip = frame.lightViewProj[layer] * vec4(biased, 1.0);
    vec3 ndc = clip.xyz / clip.w;
    vec2 uv = ndc.xy * 0.5 + 0.5;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 1.0;
    float bias = light.shadowParams.z * (1.0 - max(dot(N, L), 0.0)) + light.shadowParams.z * 0.1;
    float texel = 1.0 / max(light.shadowParams.y, 1.0);
    float sum = 0.0;
    for (int y = -1; y <= 1; ++y)
        for (int x = -1; x <= 1; ++x)
            sum += texture(shadowMap, vec4(uv + vec2(x, y) * texel, float(layer), ndc.z - bias));
    return sum / 9.0;
}

void main() {
    vec3 worldPos = texture(gPosition, vUV).xyz;
    vec3 N = normalize(texture(gNormal, vUV).xyz);
    vec3 albedo = texture(gAlbedo, vUV).rgb;

    vec3 L;
    float attenuation = 1.0;
#if LIGHT_TYPE == LIGHT_DIRECTIONAL
    L = -normalize(light.directionRange.xyz);
#else
    vec3 toLight = light.positionType.xyz - worldPos;
    float dist = length(toLight);
    L = toLight / max(dist, 1e-4);
    attenuation = rangeAttenuation(dist, light.directionRange.w);
#endif

#if LIGHT_TYPE == LIGHT_SPOT
    float cosAngle = dot(-L, normalize(light.directionRange.xyz));
    attenuation *= smoothstep(light.spotArea.y, light.spotArea.x, cosAngle);
#elif LIGHT_TYPE == LIGHT_AREA
    // Rectangular area light approximated by its facing term and projected area.
    float facing = max(dot(-L, normalize(light.directionRange.xyz)), 0.0);
    attenuation *= facing * light.spotArea.z * light.spotArea.w;
#endif

#if USE_COOKIE
    if (light.scatterColor.a > 0.5) {
        vec3 fwd = normalize(light.directionRange.xyz);
        vec3 up = abs(fwd.y) > 0.99 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
        vec3 right = normalize(cross(up, fwd));
        up = cross(fwd, right);
        vec3 rel = worldPos - light.positionType.xyz;
        float depth = max(dot(rel, fwd), 1e-4);
        vec2 proj = vec2(dot(rel, right), dot(rel, up)) / depth;
        vec2 cookieUV = proj * 0.5 * light.cookieUV.xy + 0.5 + light.cookieUV.zw;
        attenuation *= texture(cookieTex, cookieUV).r;
    }
#endif

    float NdotL = max(dot(N, L), 0.0);
    float shadow = shadowFactor(worldPos, N, L);
    float intensity = light.colorIntensity.a * (light.flickerParams.x > 0.5 ? frame.flickerScale : 1.0);
    vec3 radiance = light.colorIntensity.rgb * intensity * attenuation;
    vec3 color = albedo * radiance * NdotL * shadow;

#if USE_VOLUMETRIC
    if (light.volumetricParams.z > 0.5) {
        // Single-scattering ray march from the camera to the surface.
        vec3 camPos = frame.cameraPosTime.xyz;
        vec3 rayDir = worldPos - camPos;
        float rayLen = length(rayDir);
        rayDir /= max(rayLen, 1e-4);
        const int STEPS = 16;
        float stepLen = rayLen / float(STEPS);
        float g = light.volumetricParams.y;
        vec3 inScatter = vec3(0.0);
        for (int i = 0; i < STEPS; ++i) {
            vec3 p = camPos + rayDir * (float(i) + 0.5) * stepLen;
            vec3 toL = light.positionType.xyz - p;
            float d = length(toL);
#if LIGHT_TYPE == LIGHT_DIRECTIONAL
            vec3 lDir = -normalize(light.directionRange.xyz);
            float att = 1.0;
#else
            vec3 lDir = toL / max(d, 1e-4);
            float att = rangeAttenuation(d, light.directionRange.w);
#endif
            float cosTheta = dot(rayDir, lDir);
            float phase = (1.0 - g * g) / (12.5663706 * pow(max(1.0 + g * g - 2.0 * g * cosTheta, 1e-4), 1.5));
            float density = light.volumetricParams.x * texture(volumeNoise, p * 0.05 + frame.cameraPosTime.w * 0.01).r;
            inScatter += density * phase * att * stepLen;
        }
        color += inScatter * light.scatterColor.rgb * light.colorIntensity.rgb * intensity;
    }
#endif

    outColor = vec4(color, 1.0);
}
)";
        return src;
    }
};

} // namespace mt::light
