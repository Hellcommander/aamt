#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "UIAssetTypes.hpp"

namespace MagiTech {
namespace UIAssets {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildUIElement(const UIElementParams& p, const UIThemeParams& t);
}
namespace TextureGen {
    TextureHandle buildUITexture(const UIElementParams& p, const UIThemeParams& t);
}
namespace ShaderGen {
    ShaderHandle buildUIShader(const UIElementParams& p, const UIThemeParams& t);
}
namespace AnimGen {
    AnimationHandle buildUIAnimations(const UIElementParams& p);
}
namespace FontGen {
    FontHandle buildFontAtlas(const std::string& fontName, int fontSize, TextAlign align);
}
namespace IconGen {
    TextureHandle buildUIIcon(const std::string& shape, const glm::vec4& color, const glm::vec2& size);
}

inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class UIAssetFactory {
    ConcurrentLRUCache<uint64_t, UIAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    UIAssetFactory() = default;
    ~UIAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    std::future<UIAssetBundle> generateAsync(const UIElementParams& p, const UIThemeParams& t) {
        uint64_t key = hashCombine(p.hashKey(), t.hashKey());
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }

        return m_pool.enqueue([=]() {
            UIAssetBundle b;
            b.mesh = MeshGen::buildUIElement(p, t);
            b.texture = TextureGen::buildUITexture(p, t);
            b.shader = ShaderGen::buildUIShader(p, t);
            b.animations = AnimGen::buildUIAnimations(p);
            b.fontAtlas = (p.type == UIElementType::Text)
                          ? FontGen::buildFontAtlas(p.fontName, p.fontSize, p.textAlign)
                          : FontHandle{};
            b.iconTexture = (p.type == UIElementType::Icon)
                            ? IconGen::buildUIIcon(p.iconShape, p.iconColor, p.size)
                            : TextureHandle{};
            m_cache.insert(key, b);
            return b;
        });
    }
};

} // namespace UIAssets
} // namespace MagiTech
