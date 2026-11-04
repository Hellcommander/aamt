#include "ProceduralAssetModule.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <atomic>
#include <fstream>
#include <mutex>
#include <string>
#include <system_error>
#include <type_traits>

namespace MagiTech {
namespace Procedural {

namespace {
    constexpr uint32_t kRecordMagic = 0x4150544D; // "MTPA"
    constexpr uint32_t kRecordVersion = 1;
    constexpr const char* kRecordPrefix = "proc_asset_";
    constexpr const char* kRecordExtension = ".bin";

    template <typename T>
    void writePod(std::ofstream& os, const T& v) {
        static_assert(std::is_trivially_copyable_v<T>);
        os.write(reinterpret_cast<const char*>(&v), sizeof(T));
    }

    template <typename T>
    bool readPod(std::ifstream& is, T& v) {
        static_assert(std::is_trivially_copyable_v<T>);
        is.read(reinterpret_cast<char*>(&v), sizeof(T));
        return static_cast<bool>(is);
    }

    void writeParams(std::ofstream& os, const SpellAssetParams& p) {
        writePod(os, p.seed);
        writePod(os, static_cast<int32_t>(p.type));
        writePod(os, p.durationFrames);
        writePod(os, p.texWidth);
        writePod(os, p.texHeight);
        writePod(os, p.colorStart.x); writePod(os, p.colorStart.y); writePod(os, p.colorStart.z);
        writePod(os, p.colorEnd.x);   writePod(os, p.colorEnd.y);   writePod(os, p.colorEnd.z);
        writePod(os, p.noiseScale);
        writePod(os, p.swirlStrength);
        writePod(os, p.meshRadius);
        writePod(os, p.meshThickness);
        writePod(os, p.meshDetail);
        writePod(os, p.curlNoiseIntensity);
        writePod(os, p.fractalDepth);
        writePod(os, p.emissionRate);
    }

    bool readParams(std::ifstream& is, SpellAssetParams& p) {
        int32_t type = 0;
        bool ok = readPod(is, p.seed) && readPod(is, type) && readPod(is, p.durationFrames)
               && readPod(is, p.texWidth) && readPod(is, p.texHeight)
               && readPod(is, p.colorStart.x) && readPod(is, p.colorStart.y) && readPod(is, p.colorStart.z)
               && readPod(is, p.colorEnd.x) && readPod(is, p.colorEnd.y) && readPod(is, p.colorEnd.z)
               && readPod(is, p.noiseScale) && readPod(is, p.swirlStrength)
               && readPod(is, p.meshRadius) && readPod(is, p.meshThickness) && readPod(is, p.meshDetail)
               && readPod(is, p.curlNoiseIntensity) && readPod(is, p.fractalDepth) && readPod(is, p.emissionRate);
        if (!ok || type < static_cast<int32_t>(SpellType::Projectile) || type > static_cast<int32_t>(SpellType::Aura)) {
            return false;
        }
        p.type = static_cast<SpellType>(type);
        return true;
    }

    // Until the renderer exposes resource creation, generated resources get
    // unique process-wide handles (0 stays the invalid handle).
    uint32_t nextResourceHandle() {
        static std::atomic<uint32_t> next{1};
        return next++;
    }
}

ProceduralAssetModule::ProceduralAssetModule() {
}

ProceduralAssetModule::~ProceduralAssetModule() {
    shutdown();
}

bool ProceduralAssetModule::initialize() {
    if (m_initialized) {
        return true;
    }

    Log::info("ProceduralAssetModule: Initializing...");

    // Restore previously generated assets from the save directory
    deserializeAssets();

    m_initialized = true;
    Log::info("ProceduralAssetModule: Initialized successfully.");
    return true;
}

void ProceduralAssetModule::shutdown() {
    if (!m_initialized) {
        return;
    }

    Log::info("ProceduralAssetModule: Shutting down...");

    // Assets are persisted as they are generated (see getOrCreateSpellAsset),
    // so only the in-memory cache needs releasing here.
    {
        std::unique_lock lock(m_cacheMutex);
        m_cache.clear();
        m_lruQueue.clear();
    }

    m_initialized = false;
    Log::info("ProceduralAssetModule: Shutdown complete.");
}

void ProceduralAssetModule::registerBindings(sol::state_view lua) {
    Log::info("ProceduralAssetModule: Registering Lua bindings...");

    lua.new_enum("ProceduralSpellType",
        "Projectile", SpellType::Projectile,
        "AOE", SpellType::AOE,
        "Beam", SpellType::Beam,
        "Aura", SpellType::Aura
    );

    lua.new_usertype<SpellAssetParams>("SpellAssetParams",
        sol::constructors<SpellAssetParams()>(),
        "seed", &SpellAssetParams::seed,
        "type", &SpellAssetParams::type,
        "durationFrames", &SpellAssetParams::durationFrames,
        "texWidth", &SpellAssetParams::texWidth,
        "texHeight", &SpellAssetParams::texHeight,
        "colorStart", &SpellAssetParams::colorStart,
        "colorEnd", &SpellAssetParams::colorEnd,
        "noiseScale", &SpellAssetParams::noiseScale,
        "swirlStrength", &SpellAssetParams::swirlStrength,
        "meshRadius", &SpellAssetParams::meshRadius,
        "meshThickness", &SpellAssetParams::meshThickness,
        "meshDetail", &SpellAssetParams::meshDetail,
        "curlNoiseIntensity", &SpellAssetParams::curlNoiseIntensity,
        "fractalDepth", &SpellAssetParams::fractalDepth,
        "emissionRate", &SpellAssetParams::emissionRate,
        "getHash", &SpellAssetParams::getHash
    );

    lua.new_usertype<AssetBundle>("ProceduralAssetBundle",
        sol::no_constructor,
        "texHandle", &AssetBundle::texHandle,
        "meshHandle", &AssetBundle::meshHandle,
        "lastUsedFrame", &AssetBundle::lastUsedFrame
    );

    auto proceduralNs = lua.create_named_table("procedural");
    proceduralNs["generate"] = [this](const SpellAssetParams& params) {
        return getOrCreateSpellAsset(params);
    };
    proceduralNs["isInitialized"] = [this]() { return m_initialized; };

    Log::info("ProceduralAssetModule: Lua bindings registered.");
}

AssetBundle ProceduralAssetModule::getOrCreateSpellAsset(const SpellAssetParams& params) {
    uint64_t key = params.getHash();

    if (auto cached = cacheLookup(key)) {
        return *cached;
    }

    AssetBundle newBundle = generateAsset(params);
    cacheInsert(key, newBundle);
    serializeAsset(key, params);

    return newBundle;
}

void ProceduralAssetModule::setRenderer(EnhancedRenderer* renderer) {
    m_renderer = renderer;
}

std::optional<AssetBundle> ProceduralAssetModule::cacheLookup(uint64_t key) {
    // Exclusive lock: a hit also refreshes the key's LRU position.
    std::unique_lock lock(m_cacheMutex);
    auto it = m_cache.find(key);
    if (it == m_cache.end()) {
        return std::nullopt;
    }
    auto pos = std::find(m_lruQueue.begin(), m_lruQueue.end(), key);
    if (pos != m_lruQueue.end()) {
        m_lruQueue.erase(pos);
    }
    m_lruQueue.push_back(key);
    return it->second;
}

void ProceduralAssetModule::cacheInsert(uint64_t key, const AssetBundle& bundle) {
    std::unique_lock lock(m_cacheMutex);
    auto [it, inserted] = m_cache.insert_or_assign(key, bundle);
    if (!inserted) {
        auto pos = std::find(m_lruQueue.begin(), m_lruQueue.end(), key);
        if (pos != m_lruQueue.end()) {
            m_lruQueue.erase(pos);
        }
    }
    m_lruQueue.push_back(key);

    while (m_cache.size() > m_cacheCapacity && !m_lruQueue.empty()) {
        m_cache.erase(m_lruQueue.front());
        m_lruQueue.pop_front();
    }
}

AssetBundle ProceduralAssetModule::generateAsset(const SpellAssetParams& params) {
    // This is the core of the pipeline: texture and mesh generation, then upload.
    Log::info("ProceduralAsset", "Generating new procedural asset with seed {}.", params.seed);

    AssetBundle bundle;
    bundle.texHandle = generateTexture(params);
    bundle.meshHandle = generateMesh(params);
    bundle.lastUsedFrame = 0;

    uploadToGpu();
    return bundle;
}

TextureHandle ProceduralAssetModule::generateTexture(const SpellAssetParams& params) {
    Log::info("ProceduralAsset", "...Generating texture ({}x{})", params.texWidth, params.texHeight);
    // The texture would be produced by a compute kernel and registered with the
    // renderer; EnhancedRenderer has no resource-creation API yet, so the module
    // allocates the handle itself.
    return nextResourceHandle();
}

MeshHandle ProceduralAssetModule::generateMesh(const SpellAssetParams& params) {
    Log::info("ProceduralAsset", "...Generating mesh (detail: {})", params.meshDetail);
    // Vertex/index data would be generated (CPU or GPU) and registered with the
    // renderer; see generateTexture for the handle allocation.
    return nextResourceHandle();
}

void ProceduralAssetModule::uploadToGpu() {
    // Transfers generated data to the rendering API once a renderer is attached.
    if (!m_renderer) {
        return;
    }
    Log::debug("ProceduralAssetModule: renderer attached, generated data is ready for upload.");
}

void ProceduralAssetModule::serializeAsset(uint64_t key, const SpellAssetParams& params) {
    Log::info("ProceduralAsset", "Serializing asset with key {}.", key);

    std::error_code ec;
    std::filesystem::create_directories(m_storageDir, ec);
    if (ec) {
        Log::error("ProceduralAsset", "Cannot create asset directory {}: {}", m_storageDir.string(), ec.message());
        return;
    }

    const auto path = m_storageDir / (std::string(kRecordPrefix) + std::to_string(key) + kRecordExtension);
    std::ofstream ofs(path, std::ios::binary | std::ios::trunc);
    if (!ofs) {
        Log::error("ProceduralAsset", "Cannot write asset record {}", path.string());
        return;
    }
    // Header, then the generation parameters (assets are regenerated from them on load).
    writePod(ofs, kRecordMagic);
    writePod(ofs, kRecordVersion);
    writePod(ofs, key);
    writeParams(ofs, params);
}

void ProceduralAssetModule::deserializeAssets() {
    Log::info("Deserializing procedural assets from storage...");

    std::error_code ec;
    if (!std::filesystem::is_directory(m_storageDir, ec)) {
        return;
    }

    size_t restored = 0;
    for (const auto& entry : std::filesystem::directory_iterator(m_storageDir, ec)) {
        const auto name = entry.path().filename().string();
        if (!entry.is_regular_file() || !name.starts_with(kRecordPrefix) || !name.ends_with(kRecordExtension)) {
            continue;
        }

        std::ifstream ifs(entry.path(), std::ios::binary);
        uint32_t magic = 0, version = 0;
        uint64_t key = 0;
        SpellAssetParams params;
        if (!readPod(ifs, magic) || !readPod(ifs, version) || !readPod(ifs, key)
            || magic != kRecordMagic || version != kRecordVersion || !readParams(ifs, params)
            || params.getHash() != key) {
            Log::warn("ProceduralAsset", "Skipping invalid asset record {}", entry.path().string());
            continue;
        }

        cacheInsert(key, generateAsset(params));
        ++restored;
    }

    Log::info("ProceduralAsset", "Restored {} procedural assets.", restored);
}


} // namespace Procedural
} // namespace MagiTech
