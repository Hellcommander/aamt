#include "StatusEffectFactory.hpp"
#include "StatusEffectGenerators.hpp"
#include "core/Log.hpp"
#include <fstream>

// Canonical StatusEffectFactory implementation (merged from the copy that was
// duplicated in StatusEffectGenerators.cpp; that copy must be removed there).

namespace MagiTech {
namespace StatusEffects {

// A simple hash combine function
template <class T>
inline void hash_combine(std::uint64_t& seed, const T& v) {
    std::hash<T> hasher;
    seed ^= static_cast<std::uint64_t>(hasher(v)) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

namespace {
    // Reads a JSON file; returns a null json when the file is missing or invalid.
    nlohmann::json loadJsonFile(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) {
            Log::warn("StatusEffectFactory", "Could not open JSON file: {}", path);
            return nlohmann::json();
        }
        nlohmann::json j = nlohmann::json::parse(file, nullptr, false);
        if (j.is_discarded()) {
            Log::warn("StatusEffectFactory", "Invalid JSON in file: {}", path);
            return nlohmann::json();
        }
        return j;
    }
}

StatusEffectFactory::StatusEffectFactory() {}

StatusEffectFactory::~StatusEffectFactory() {
    shutdown();
}

void StatusEffectFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
    Log::info("StatusEffectFactory", "initialized with cache_size={}, threads={}",
              cache_size, num_threads);
}

void StatusEffectFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
    Log::info("StatusEffectFactory shutdown");
}

std::future<EffectBundle> StatusEffectFactory::generateAsync(const StatusEffectParams& s, const UIParams& u) {
    std::uint64_t key = s.hashKey();
    hash_combine(key, u.hashKey());

    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([s, u, this, key] {
        EffectBundle b;
        b.shader    = ShaderGen::build(s);
        b.texture   = TextureGen::build(s);
        b.mesh      = MeshGen::build(s);
        b.particles = ParticleGen::build(s);
        b.icon      = IconGen::build(s, u);
        m_cache.insert(key, b);
        return b;
    });
}

EffectBundle StatusEffectFactory::generateSync(const StatusEffectParams& s, const UIParams& u) {
    return generateAsync(s, u).get();
}

std::future<EffectBundle> StatusEffectFactory::generateFromJson(const std::string& effectJsonPath, const std::string& uiJsonPath) {
    // Parse on the calling thread, then generate on the pool. (Waiting on the
    // pool from inside a pool task could deadlock a saturated pool.)
    StatusEffectParams effectParams;
    nlohmann::json effectJson = loadJsonFile(effectJsonPath);
    if (effectJson.is_object()) {
        Log::info("StatusEffectFactory", "Loading effect params from: {}", effectJsonPath);
        effectParams = ParamUtils::fromJson(effectJson);
    }

    UIParams uiParams;
    nlohmann::json uiJson = loadJsonFile(uiJsonPath);
    if (uiJson.is_object()) {
        Log::info("StatusEffectFactory", "Loading UI params from: {}", uiJsonPath);
        uiParams = ParamUtils::uiParamsFromJson(uiJson);
    }

    return generateAsync(effectParams, uiParams);
}

std::future<EffectBundle> StatusEffectFactory::generateFromParams(const StatusEffectParams& effectParams, const UIParams& uiParams) {
    return generateAsync(effectParams, uiParams);
}

std::vector<std::future<EffectBundle>> StatusEffectFactory::generateBatch(const std::vector<std::pair<StatusEffectParams, UIParams>>& params) {
    std::vector<std::future<EffectBundle>> futures;
    futures.reserve(params.size());
    for (const auto& param : params) {
        futures.push_back(generateAsync(param.first, param.second));
    }
    return futures;
}

void StatusEffectFactory::clearCache() {
    m_cache.clear();
    Log::info("StatusEffectFactory cache cleared");
}

size_t StatusEffectFactory::getCacheSize() const {
    return m_cache.size();
}

size_t StatusEffectFactory::getCacheCapacity() const {
    return m_cache.capacity();
}

bool StatusEffectFactory::validateEffectParams(const StatusEffectParams& params) {
    return params.duration > 0 && params.intensity >= 0 && params.intensity <= 1;
}

std::string StatusEffectFactory::getEffectValidationErrors(const StatusEffectParams& params) {
    std::string errors;
    if (params.duration <= 0) {
        errors += "Duration must be positive\n";
    }
    if (params.intensity < 0 || params.intensity > 1) {
        errors += "Intensity must be between 0 and 1\n";
    }
    if (params.particleCount < 0) {
        errors += "Particle count must be non-negative\n";
    }
    return errors;
}

bool StatusEffectFactory::validateUIParams(const UIParams& params) {
    return params.iconSize > 0 && params.iconSize <= 512;
}

std::string StatusEffectFactory::getUIValidationErrors(const UIParams& params) {
    std::string errors;
    if (params.iconSize <= 0 || params.iconSize > 512) {
        errors += "Icon size must be between 1 and 512\n";
    }
    return errors;
}

} // namespace StatusEffects
} // namespace MagiTech
