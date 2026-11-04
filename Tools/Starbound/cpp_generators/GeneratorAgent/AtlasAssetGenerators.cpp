#include "AtlasAssetFactory.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <atomic>
#include <type_traits>

namespace MagiTech {
namespace AtlasAssets {

#define LOG_ATLAS_GEN(Action, Id) Log::info("AtlasAssetGen", "{}: {}", #Action, Id)

namespace {
    // Field-wise hashing (raw struct bytes would include padding and heap pointers).
    struct Hasher {
        XXH64_state_t state;
        Hasher() { XXH64_reset(&state, 0); }
        template <typename T>
        Hasher& pod(const T& v) {
            static_assert(std::is_trivially_copyable_v<T>);
            XXH64_update(&state, &v, sizeof(T));
            return *this;
        }
        Hasher& str(const std::string& v) {
            pod(static_cast<uint64_t>(v.size()));
            XXH64_update(&state, v.data(), v.size());
            return *this;
        }
        template <typename T>
        Hasher& vec(const std::vector<T>& v) {
            pod(static_cast<uint64_t>(v.size()));
            for (const auto& e : v) pod(e);
            return *this;
        }
        uint64_t digest() { return XXH64_digest(&state); }
    };
}

// Hash function implementations
uint64_t SpriteParams::hashKey() const {
    return Hasher().str(id).str(path).pod(trim).pod(border).digest();
}
uint64_t AtlasParams::hashKey() const {
    return Hasher().str(id).pod(maxWidth).pod(maxHeight).pod(padding).pod(allowRotation)
                   .pod(generateMipmaps).pod(mipLevels).digest();
}
uint64_t MaterialParams::hashKey() const {
    return Hasher().str(shader).pod(alphaTest).pod(alphaThreshold).digest();
}
uint64_t LODParams::hashKey() const {
    return Hasher().vec(screenSizes).vec(atlasResolutions).digest();
}

// Generator stubs
namespace SpriteImportGen {
    std::vector<ImportedSprite> import(const std::vector<SpriteParams>& sprites) {
        LOG_ATLAS_GEN(ImportingSprites, sprites.size());
        std::vector<ImportedSprite> imported;
        for(const auto& p : sprites) {
            imported.push_back({p.id, {}, 128, 128});
        }
        return imported;
    }
}
namespace LayoutGen {
    AtlasLayout createLayout(const std::vector<ImportedSprite>& sprites, const AtlasParams& ap) {
        LOG_ATLAS_GEN(CreatingLayout, ap.id);
        AtlasLayout layout;
        layout.atlasWidth = ap.maxWidth;
        layout.atlasHeight = ap.maxHeight;
        int x = 0, y = 0, rowHeight = 0;
        for(const auto& s : sprites) {
            // Wrap to the next row before placing a sprite that would overflow the atlas width.
            if (x > 0 && x + s.width > ap.maxWidth) { x = 0; y += rowHeight + ap.padding; rowHeight = 0; }
            layout.uvMap[s.id] = UVRect(x, y, s.width, s.height);
            x += s.width + ap.padding;
            rowHeight = std::max(rowHeight, s.height);
        }
        return layout;
    }
}
namespace PackingGen {
    TextureHandle packSprites(const std::vector<ImportedSprite>& sprites, const AtlasLayout& layout, const AtlasParams& ap) {
        LOG_ATLAS_GEN(PackingSprites, ap.id);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}
namespace MipGen {
    void generate(const TextureHandle& atlas, int levels) {
        LOG_ATLAS_GEN(GeneratingMips, atlas);
    }
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const MaterialParams& mp, const TextureHandle& atlas) {
        LOG_ATLAS_GEN(BuildingMaterial, mp.shader);
        static std::atomic<uint32_t> nextHandle{100}; return nextHandle++;
    }
}
namespace LODGen {
    LODData compute(const LODParams& lp, const TextureHandle& base) {
        LOG_ATLAS_GEN(ComputingLODs, lp.screenSizes.size());
        LODData data;
        data.screenSizes = lp.screenSizes;
        return data;
    }
}

} // namespace AtlasAssets
} // namespace MagiTech
