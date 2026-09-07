#include "IconAssetFactory.hpp"
#include <stdexcept>

namespace MagiTech {
namespace IconAssets {

void IconAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_atlasCache.set_capacity(cache_size / 4); // Atlases are larger, so smaller cache
    m_pool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized = true;
}

void IconAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.reset();
    m_initialized = false;
}


std::future<IconAsset> IconAssetFactory::generateIconAsync(const IconParams& p) {
    uint64_t key = p.hashKey();
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool->enqueue([=]() {
        IconAsset asset;
        switch (p.type) {
            case IconType::Primitive:
                asset.bitmap = PrimitiveGen::build(p.shape, p.size, p.fillColor, p.strokeColor, p.strokeWidth);
                break;
            case IconType::SVG:
                asset.bitmap = SVGGen::render(p.svgPath, p.size, p.fillColor, p.strokeColor, p.strokeWidth);
                break;
            case IconType::Bitmap:
                asset.bitmap = TextureLoader::load(p.id);
                break;
            case IconType::SDF: // SDF is generated from another type, typically primitive
                 asset.bitmap = PrimitiveGen::build(p.shape, p.size, p.fillColor, p.strokeColor, p.strokeWidth);
                 break;
        }

        if (p.generateSDF && asset.bitmap != 0) {
            asset.sdf = SDFGen::generate(asset.bitmap, p.sdfPadding);
        }

        m_cache.insert(key, asset);
        return asset;
    });
}

std::future<IconAtlas> IconAssetFactory::generateAtlasAsync(const std::vector<IconParams>& icons, const AtlasParams& ap) {
    uint64_t key = hashCombine(ap.hashKey(), hashVector(icons));
    if (auto hit = m_atlasCache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool->enqueue([=, this]() {
        std::vector<std::future<IconAsset>> futures;
        futures.reserve(icons.size());
        for (const auto& ip : icons) {
            futures.push_back(this->generateIconAsync(ip));
        }

        std::vector<TextureHandle> textures;
        textures.reserve(icons.size());
        for (auto& f : futures) {
            textures.push_back(f.get().bitmap);
        }
        
        IconAtlas atlas;
        atlas.atlasTexture = AtlasGen::packIcons(textures, ap, ap.iconSize);
        int atlasWidth = ap.columns * (ap.iconSize.x + ap.padding);
        int atlasHeight = ap.rows * (ap.iconSize.y + ap.padding);

        atlas.uvRects = AtlasGen::computeUVs(textures.size(), ap.columns, ap.rows, {atlasWidth, atlasHeight}, ap.iconSize, ap.padding);
        
        m_atlasCache.insert(key, atlas);
        return atlas;
    });
}


} // namespace IconAssets
} // namespace MagiTech
