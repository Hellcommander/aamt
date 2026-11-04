#pragma once

#include "LightTypes.hpp"
#include "core/GPULightingSystem.hpp"
#include <cstring>
#include <functional>
#include <mutex>
#include <glm/geometric.hpp>

namespace mt::light {

// Bits stored in GPULight::params.w (as an exactly representable float).
namespace LightFlags {
inline constexpr uint32_t Dynamic      = 1u << 0;
inline constexpr uint32_t Volumetric   = 1u << 1;
inline constexpr uint32_t CastsShadows = 1u << 2;
inline constexpr uint32_t Cookie       = 1u << 3;
inline constexpr uint32_t Flicker      = 1u << 4;
} // namespace LightFlags

// LightGen bridges the light param structs to the backend's WorldExLighting::GPULightingSystem.
//
// GPULight layout (see core/GPULightingSystem.hpp):
//   position  = xyz position,  w = WorldExLighting::LightType
//   direction = xyz direction, w = spot outer angle (degrees)
//   color     = rgb colour,    a = intensity
//   params    = x radius, y falloff, z blend mode, w flags (LightFlags)
//   transform = x/y area size, z rotation, w spot inner angle (degrees)
class LightGen {
public:
    // The process-wide lighting system, created on first use (thread-safe).
    static WorldExLighting::GPULightingSystem& system() {
        static std::mutex initMutex;
        std::lock_guard<std::mutex> lock(initMutex);
        if (!WorldExLighting::g_gpu_lighting_system) {
            WorldExLighting::initializeGPULightingSystem();
        }
        return *WorldExLighting::g_gpu_lighting_system;
    }

    static WorldExLighting::LightType toSystemType(LightType type) {
        switch (type) {
            case LightType::Directional: return WorldExLighting::LightType::DIRECTIONAL;
            case LightType::Spot:        return WorldExLighting::LightType::SPOT;
            case LightType::Area:        return WorldExLighting::LightType::AREA;
            case LightType::Point:
            default:                     return WorldExLighting::LightType::POINT;
        }
    }

    static WorldExLighting::GPULight makeGPULight(const LightParams& p) {
        WorldExLighting::GPULight light;
        const float typeValue = static_cast<float>(static_cast<int>(toSystemType(p.type)));
        const Vec3 dir = glm::length(p.direction) > 1e-6f ? glm::normalize(p.direction) : Vec3(0.0f, -1.0f, 0.0f);

        light.position = glm::vec4(p.type == LightType::Directional ? Vec3(0.0f) : p.position, typeValue);
        light.direction = glm::vec4(dir, p.type == LightType::Spot ? p.outerAngle : 0.0f);
        light.color = glm::vec4(p.color, p.intensity);

        uint32_t flags = 0;
        if (p.dynamic) flags |= LightFlags::Dynamic;
        if (p.volumetric) flags |= LightFlags::Volumetric;
        light.params = glm::vec4(p.type == LightType::Directional ? 0.0f : p.range,
                                 static_cast<float>(static_cast<int>(WorldExLighting::LightFalloff::QUADRATIC)),
                                 static_cast<float>(static_cast<int>(WorldExLighting::LightBlendMode::ADDITIVE)),
                                 static_cast<float>(flags));
        light.animation = glm::vec4(0.0f);
        light.transform = glm::vec4(p.type == LightType::Area ? p.areaSize : Vec2(1.0f, 1.0f), 0.0f,
                                    p.type == LightType::Spot ? p.innerAngle : 0.0f);
        light.is_active = true;
        light.needs_update = true;
        return light;
    }

    // Registers the light with the GPU lighting system and returns its handle.
    static LightHandle build(const LightParams& p) { return system().addLight(makeGPULight(p)); }

    // Applies `fn` to a copy of the registered light and writes it back. False when the handle is unknown.
    static bool modify(LightHandle handle, const std::function<void(WorldExLighting::GPULight&)>& fn) {
        if (handle == 0) return false;
        auto& sys = system();
        WorldExLighting::GPULight* current = sys.getLight(handle);
        if (!current) return false;
        WorldExLighting::GPULight copy = *current;
        fn(copy);
        copy.needs_update = true;
        sys.updateLight(handle, copy);
        return true;
    }

    static uint32_t flagsOf(const WorldExLighting::GPULight& light) { return static_cast<uint32_t>(light.params.w); }

    static bool setFlag(LightHandle handle, uint32_t flag, bool enabled) {
        return modify(handle, [flag, enabled](WorldExLighting::GPULight& light) {
            uint32_t flags = flagsOf(light);
            flags = enabled ? (flags | flag) : (flags & ~flag);
            light.params.w = static_cast<float>(flags);
        });
    }

    static void destroy(LightHandle handle) {
        if (handle != 0) system().removeLight(handle);
    }
};

} // namespace mt::light
