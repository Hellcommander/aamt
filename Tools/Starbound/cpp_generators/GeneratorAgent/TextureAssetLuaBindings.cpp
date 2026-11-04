#include "TextureAssetLuaBindings.hpp"
#include "TextureAssetFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace TextureAssets {

static std::vector<std::pair<std::future<TextureAssetBundle>, std::string>> pendingAssets;
static std::mutex pendingAssetsMutex;

static std::mutex factoryMutex;
static std::shared_ptr<TextureAssetFactory> sharedFactory;

void TextureAssetLuaBindings::setFactory(std::shared_ptr<TextureAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<TextureAssetFactory> TextureAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<TextureAssetFactory>();
        sharedFactory->initialize(128, 4);
    }
    return sharedFactory;
}

namespace {
    template <typename T>
    std::optional<T> toStd(const sol::optional<T>& v) {
        if (v) return *v;
        return std::nullopt;
    }
}

void TextureAssetLuaBindings::bind(sol::state& lua) {
    lua.new_enum("TextureType",
        "Noise", TextureType::Noise,
        "Mask", TextureType::Mask,
        "PBR", TextureType::PBR,
        "Atlas", TextureType::Atlas,
        "TrimSheet", TextureType::TrimSheet
    );

    lua.new_usertype<TextureParams>("TextureParams",
        sol::constructors<TextureParams()>(),
        "id", &TextureParams::id,
        "type", &TextureParams::type,
        "resolution", &TextureParams::resolution,
        "uvScale", &TextureParams::uvScale,
        "seed", &TextureParams::seed,
        "seamless", &TextureParams::seamless
    );

    lua.new_usertype<NoiseParams>("TextureNoiseParams",
        sol::constructors<NoiseParams()>(),
        "noiseType", &NoiseParams::noiseType,
        "octaves", &NoiseParams::octaves,
        "frequency", &NoiseParams::frequency,
        "lacunarity", &NoiseParams::lacunarity,
        "gain", &NoiseParams::gain
    );

    lua.new_usertype<MaskParams>("MaskParams",
        sol::constructors<MaskParams()>(),
        "stops", &MaskParams::stops,
        "invert", &MaskParams::invert,
        "gaussianBlur", &MaskParams::gaussianBlur,
        "blurRadius", &MaskParams::blurRadius
    );

    lua.new_usertype<PBRParams>("PBRParams",
        sol::constructors<PBRParams()>(),
        "baseColorTint", &PBRParams::baseColorTint,
        "metallic", &PBRParams::metallic,
        "roughness", &PBRParams::roughness,
        "ambientOcclusion", &PBRParams::ambientOcclusion,
        "bakeHeight", &PBRParams::bakeHeight,
        "heightScale", &PBRParams::heightScale
    );

    lua.new_usertype<AtlasParams>("TextureAtlasParams",
        sol::constructors<AtlasParams()>(),
        "sources", &AtlasParams::sources,
        "padding", &AtlasParams::padding,
        "maxWidth", &AtlasParams::maxWidth,
        "maxHeight", &AtlasParams::maxHeight,
        "generateUDIM", &AtlasParams::generateUDIM
    );

    lua.new_usertype<CompressionParams>("CompressionParams",
        sol::constructors<CompressionParams()>(),
        "format", &CompressionParams::format,
        "quality", &CompressionParams::quality,
        "generateMipmaps", &CompressionParams::generateMipmaps,
        "sRGB", &CompressionParams::sRGB
    );

    lua.new_usertype<TextureAssetBundle>("TextureAssetBundle",
        sol::no_constructor,
        "texture", &TextureAssetBundle::texture,
        "mipmaps", &TextureAssetBundle::mipmaps,
        "udim", &TextureAssetBundle::udim,
        "hasUDIM", sol::readonly_property([](const TextureAssetBundle& b) { return b.udim.has_value(); })
    );

    lua.set_function("spawn_texture_asset",
        [](const TextureParams& t, sol::optional<NoiseParams> n,
           sol::optional<MaskParams> m, sol::optional<PBRParams> p,
           sol::optional<AtlasParams> a, sol::optional<CompressionParams> c) {
            auto future = factory()->generateAsync(t, toStd(n), toStd(m), toStd(p), toStd(a), toStd(c));
            std::lock_guard<std::mutex> lock(pendingAssetsMutex);
            pendingAssets.emplace_back(std::move(future), t.id);
        }
    );
}

void TextureAssetLuaBindings::poll_assets(sol::state& lua) {
    std::lock_guard<std::mutex> lock(pendingAssetsMutex);
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Texture asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("TextureAssets", "Texture asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace TextureAssets
} // namespace MagiTech
