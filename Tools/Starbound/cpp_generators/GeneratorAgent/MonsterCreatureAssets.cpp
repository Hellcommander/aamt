#include "MonsterCreatureAssets.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace MagiTech {
namespace CreatureAssets {

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 2.0f * kPi;

glm::vec3 safeNormalize(const glm::vec3& v, const glm::vec3& fallback) {
    const float len = glm::length(v);
    return len > 1e-6f ? v / len : fallback;
}

void addTriangle(MeshData& mesh, uint32_t a, uint32_t b, uint32_t c) {
    mesh.indices.push_back(a);
    mesh.indices.push_back(b);
    mesh.indices.push_back(c);
}
} // namespace

// ================================================================ MeshData
void MeshData::append(const MeshData& other) {
    const uint32_t base = static_cast<uint32_t>(vertices.size());
    vertices.insert(vertices.end(), other.vertices.begin(), other.vertices.end());
    indices.reserve(indices.size() + other.indices.size());
    for (uint32_t index : other.indices) {
        indices.push_back(base + index);
    }
}

void MeshData::transform(const glm::mat4& m) {
    const glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(m)));
    for (auto& v : vertices) {
        v.position = glm::vec3(m * glm::vec4(v.position, 1.0f));
        v.normal = safeNormalize(normalMatrix * v.normal, v.normal);
    }
}

void MeshData::recomputeNormals() {
    for (auto& v : vertices) v.normal = glm::vec3(0.0f);
    for (size_t i = 0; i + 2 < indices.size(); i += 3) {
        auto& a = vertices[indices[i]];
        auto& b = vertices[indices[i + 1]];
        auto& c = vertices[indices[i + 2]];
        const glm::vec3 n = glm::cross(b.position - a.position, c.position - a.position);
        a.normal += n;
        b.normal += n;
        c.normal += n;
    }
    for (auto& v : vertices) v.normal = safeNormalize(v.normal, glm::vec3(0.0f, 1.0f, 0.0f));
}

std::pair<glm::vec3, glm::vec3> MeshData::bounds() const {
    if (vertices.empty()) return {glm::vec3(0.0f), glm::vec3(0.0f)};
    glm::vec3 lo(std::numeric_limits<float>::max());
    glm::vec3 hi(std::numeric_limits<float>::lowest());
    for (const auto& v : vertices) {
        lo = glm::min(lo, v.position);
        hi = glm::max(hi, v.position);
    }
    return {lo, hi};
}

// ================================================================ TextureData
void TextureData::resize(uint32_t w, uint32_t h) {
    width = w;
    height = h;
    rgba.assign(static_cast<size_t>(w) * h * 4, 0);
}

glm::vec4 TextureData::get(uint32_t x, uint32_t y) const {
    if (x >= width || y >= height) return glm::vec4(0.0f);
    const size_t i = (static_cast<size_t>(y) * width + x) * 4;
    return glm::vec4(rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]) / 255.0f;
}

void TextureData::set(uint32_t x, uint32_t y, const glm::vec4& c) {
    if (x >= width || y >= height) return;
    const size_t i = (static_cast<size_t>(y) * width + x) * 4;
    const glm::vec4 clamped = glm::clamp(c, 0.0f, 1.0f);
    for (int k = 0; k < 4; ++k) {
        rgba[i + k] = static_cast<uint8_t>(std::lround(clamped[k] * 255.0f));
    }
}

glm::vec4 TextureData::sample(float u, float v) const {
    if (width == 0 || height == 0) return glm::vec4(0.0f);
    const float fx = (u - std::floor(u)) * width - 0.5f;
    const float fy = (v - std::floor(v)) * height - 0.5f;
    const int x0 = static_cast<int>(std::floor(fx));
    const int y0 = static_cast<int>(std::floor(fy));
    const float tx = fx - x0;
    const float ty = fy - y0;
    auto wrap = [](int value, uint32_t size) {
        const int s = static_cast<int>(size);
        return static_cast<uint32_t>(((value % s) + s) % s);
    };
    const glm::vec4 c00 = get(wrap(x0, width), wrap(y0, height));
    const glm::vec4 c10 = get(wrap(x0 + 1, width), wrap(y0, height));
    const glm::vec4 c01 = get(wrap(x0, width), wrap(y0 + 1, height));
    const glm::vec4 c11 = get(wrap(x0 + 1, width), wrap(y0 + 1, height));
    return glm::mix(glm::mix(c00, c10, tx), glm::mix(c01, c11, tx), ty);
}

// ================================================================ SkeletonData
int SkeletonData::addBone(const std::string& name, int parent, const glm::vec3& head, const glm::vec3& tail) {
    Bone bone;
    bone.name = name;
    bone.parent = (parent >= 0 && parent < static_cast<int>(bones.size())) ? parent : -1;
    bone.head = head;
    bone.tail = tail;
    bones.push_back(std::move(bone));
    return static_cast<int>(bones.size()) - 1;
}

int SkeletonData::find(const std::string& name) const {
    for (size_t i = 0; i < bones.size(); ++i) {
        if (bones[i].name == name) return static_cast<int>(i);
    }
    return -1;
}

float SkeletonData::length(int bone) const {
    if (bone < 0 || bone >= static_cast<int>(bones.size())) return 0.0f;
    return glm::length(bones[bone].tail - bones[bone].head);
}

// ================================================================ AnimationData
const AnimationClip* AnimationData::find(const std::string& name) const {
    for (const auto& clip : clips) {
        if (clip.name == name) return &clip;
    }
    return nullptr;
}

size_t AnimationData::frameCount() const {
    size_t total = 0;
    for (const auto& clip : clips) total += clip.frames.size();
    return total;
}

// ================================================================ BehaviorTreeData
int BehaviorTreeData::addNode(BehaviorNodeType type, const std::string& nodeName, std::map<std::string, float> params) {
    BehaviorNode node;
    node.type = type;
    node.name = nodeName;
    node.params = std::move(params);
    nodes.push_back(std::move(node));
    const int index = static_cast<int>(nodes.size()) - 1;
    if (root < 0) root = index;
    return index;
}

void BehaviorTreeData::addChild(int parent, int child) {
    if (parent < 0 || parent >= static_cast<int>(nodes.size())) return;
    if (child < 0 || child >= static_cast<int>(nodes.size()) || child == parent) return;
    nodes[parent].children.push_back(child);
}

int BehaviorTreeData::addChildNode(int parent, BehaviorNodeType type, const std::string& nodeName,
                                   std::map<std::string, float> params) {
    const int child = addNode(type, nodeName, std::move(params));
    addChild(parent, child);
    return child;
}

BehaviorState& BehaviorTreeData::addState(const std::string& stateName, int treeRoot) {
    if (BehaviorState* existing = findState(stateName)) {
        existing->treeRoot = treeRoot;
        return *existing;
    }
    BehaviorState state;
    state.name = stateName;
    state.treeRoot = treeRoot;
    states.push_back(std::move(state));
    if (initialState.empty()) initialState = stateName;
    return states.back();
}

BehaviorState* BehaviorTreeData::findState(const std::string& stateName) {
    for (auto& state : states) {
        if (state.name == stateName) return &state;
    }
    return nullptr;
}

int BehaviorTreeData::depth() const {
    if (root < 0 || nodes.empty()) return 0;
    // Iterative DFS guarding against cycles.
    int best = 0;
    std::vector<std::pair<int, int>> stack{{root, 1}};
    std::vector<int> visits(nodes.size(), 0);
    while (!stack.empty()) {
        auto [node, d] = stack.back();
        stack.pop_back();
        if (node < 0 || node >= static_cast<int>(nodes.size())) continue;
        if (visits[node]++ > static_cast<int>(nodes.size())) continue;
        best = std::max(best, d);
        for (int child : nodes[node].children) stack.emplace_back(child, d + 1);
    }
    return best;
}

// ================================================================ AssetStore
AssetStore& AssetStore::instance() {
    static AssetStore store;
    return store;
}

template <typename T>
uint32_t AssetStore::add(Table<T>& table, T&& value) {
    std::lock_guard<std::mutex> lock(m_mutex);
    uint32_t handle = table.next++;
    if (handle == 0) handle = table.next++;   // skip 0 after wrap-around
    table.items[handle] = std::make_shared<const T>(std::move(value));
    return handle;
}

template <typename T>
std::shared_ptr<const T> AssetStore::get(const Table<T>& table, uint32_t handle) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = table.items.find(handle);
    return it == table.items.end() ? nullptr : it->second;
}

template <typename T>
bool AssetStore::release(Table<T>& table, uint32_t handle) {
    std::lock_guard<std::mutex> lock(m_mutex);
    return table.items.erase(handle) > 0;
}

uint32_t AssetStore::addMesh(MeshData mesh) { return add(m_meshes, std::move(mesh)); }
uint32_t AssetStore::addTexture(TextureData texture) { return add(m_textures, std::move(texture)); }
uint32_t AssetStore::addSkeleton(SkeletonData skeleton) { return add(m_skeletons, std::move(skeleton)); }
uint32_t AssetStore::addAnimation(AnimationData animation) { return add(m_animations, std::move(animation)); }
uint32_t AssetStore::addBehavior(BehaviorTreeData behavior) { return add(m_behaviors, std::move(behavior)); }

std::shared_ptr<const MeshData> AssetStore::mesh(uint32_t handle) const { return get(m_meshes, handle); }
std::shared_ptr<const TextureData> AssetStore::texture(uint32_t handle) const { return get(m_textures, handle); }
std::shared_ptr<const SkeletonData> AssetStore::skeleton(uint32_t handle) const { return get(m_skeletons, handle); }
std::shared_ptr<const AnimationData> AssetStore::animation(uint32_t handle) const { return get(m_animations, handle); }
std::shared_ptr<const BehaviorTreeData> AssetStore::behavior(uint32_t handle) const { return get(m_behaviors, handle); }

bool AssetStore::releaseMesh(uint32_t handle) { return release(m_meshes, handle); }
bool AssetStore::releaseTexture(uint32_t handle) { return release(m_textures, handle); }
bool AssetStore::releaseSkeleton(uint32_t handle) { return release(m_skeletons, handle); }
bool AssetStore::releaseAnimation(uint32_t handle) { return release(m_animations, handle); }
bool AssetStore::releaseBehavior(uint32_t handle) { return release(m_behaviors, handle); }

AssetStore::Counts AssetStore::counts() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    Counts c;
    c.meshes = m_meshes.items.size();
    c.textures = m_textures.items.size();
    c.skeletons = m_skeletons.items.size();
    c.animations = m_animations.items.size();
    c.behaviors = m_behaviors.items.size();
    return c;
}

void AssetStore::clear() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_meshes.items.clear();
    m_textures.items.clear();
    m_skeletons.items.clear();
    m_animations.items.clear();
    m_behaviors.items.clear();
}

// ================================================================ Noise
namespace Noise {

float hash3(int x, int y, int z, uint32_t seed) {
    uint32_t h = seed * 0x9E3779B1u;
    h ^= static_cast<uint32_t>(x) * 0x85EBCA6Bu;
    h = (h << 13) | (h >> 19);
    h ^= static_cast<uint32_t>(y) * 0xC2B2AE35u;
    h = (h << 17) | (h >> 15);
    h ^= static_cast<uint32_t>(z) * 0x27D4EB2Fu;
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return static_cast<float>(h & 0x00FFFFFFu) / 16777216.0f;
}

float value3(const glm::vec3& p, uint32_t seed) {
    const glm::vec3 cell = glm::floor(p);
    const glm::vec3 f = p - cell;
    const glm::vec3 s = f * f * (3.0f - 2.0f * f);
    const int x = static_cast<int>(cell.x), y = static_cast<int>(cell.y), z = static_cast<int>(cell.z);
    auto h = [&](int dx, int dy, int dz) { return hash3(x + dx, y + dy, z + dz, seed); };
    const float x00 = glm::mix(h(0, 0, 0), h(1, 0, 0), s.x);
    const float x10 = glm::mix(h(0, 1, 0), h(1, 1, 0), s.x);
    const float x01 = glm::mix(h(0, 0, 1), h(1, 0, 1), s.x);
    const float x11 = glm::mix(h(0, 1, 1), h(1, 1, 1), s.x);
    const float v = glm::mix(glm::mix(x00, x10, s.y), glm::mix(x01, x11, s.y), s.z);
    return v * 2.0f - 1.0f;
}

float fbm3(const glm::vec3& p, int octaves, uint32_t seed) {
    float sum = 0.0f, amplitude = 0.5f, norm = 0.0f;
    glm::vec3 q = p;
    for (int i = 0; i < std::max(1, octaves); ++i) {
        sum += amplitude * value3(q, seed + static_cast<uint32_t>(i) * 1013u);
        norm += amplitude;
        amplitude *= 0.5f;
        q *= 2.03f;
    }
    return norm > 0.0f ? sum / norm : 0.0f;
}

float worley2(const glm::vec2& p, uint32_t seed) {
    const glm::vec2 cell = glm::floor(p);
    float best = 2.0f;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            const int cx = static_cast<int>(cell.x) + dx;
            const int cy = static_cast<int>(cell.y) + dy;
            const glm::vec2 feature(cx + hash3(cx, cy, 0, seed), cy + hash3(cx, cy, 1, seed));
            best = std::min(best, glm::length(feature - p));
        }
    }
    return std::min(best, 1.0f);
}

uint32_t seedFromString(const std::string& text) {
    uint32_t h = 2166136261u;
    for (unsigned char c : text) {
        h ^= c;
        h *= 16777619u;
    }
    return h;
}

} // namespace Noise

// ================================================================ Geometry
namespace Geometry {

Frame frameFromDirection(const glm::vec3& origin, const glm::vec3& forward) {
    Frame f;
    f.origin = origin;
    f.tangent = safeNormalize(forward, glm::vec3(1.0f, 0.0f, 0.0f));
    const glm::vec3 up = std::abs(f.tangent.y) > 0.95f ? glm::vec3(1.0f, 0.0f, 0.0f) : glm::vec3(0.0f, 1.0f, 0.0f);
    f.binormal = safeNormalize(glm::cross(f.tangent, up), glm::vec3(0.0f, 0.0f, 1.0f));
    f.normal = glm::cross(f.binormal, f.tangent);
    return f;
}

MeshData ellipsoid(const glm::vec3& center, const glm::vec3& radii, int rings, int sectors) {
    MeshData mesh;
    rings = std::max(rings, 3);
    sectors = std::max(sectors, 3);
    for (int r = 0; r <= rings; ++r) {
        const float v = static_cast<float>(r) / rings;
        const float theta = v * kPi;
        for (int s = 0; s <= sectors; ++s) {
            const float u = static_cast<float>(s) / sectors;
            const float phi = u * kTwoPi;
            const glm::vec3 unit(std::sin(theta) * std::cos(phi), std::cos(theta), std::sin(theta) * std::sin(phi));
            MeshVertex vert;
            vert.position = center + unit * radii;
            vert.normal = safeNormalize(unit / glm::max(radii, glm::vec3(1e-6f)), unit);
            vert.uv = glm::vec2(u, v);
            mesh.vertices.push_back(vert);
        }
    }
    const uint32_t stride = static_cast<uint32_t>(sectors + 1);
    for (int r = 0; r < rings; ++r) {
        for (int s = 0; s < sectors; ++s) {
            const uint32_t a = r * stride + s, b = a + stride;
            addTriangle(mesh, a, a + 1, b);
            addTriangle(mesh, a + 1, b + 1, b);
        }
    }
    return mesh;
}

MeshData sphere(const glm::vec3& center, float radius, int rings, int sectors) {
    return ellipsoid(center, glm::vec3(radius), rings, sectors);
}

MeshData cone(const glm::vec3& base, const glm::vec3& direction, float radius, float length, int sides) {
    MeshData mesh;
    sides = std::max(sides, 3);
    const Frame f = frameFromDirection(base, direction);
    const glm::vec3 apex = base + f.tangent * length;
    const float slope = radius / std::max(length, 1e-4f);
    // side
    for (int i = 0; i <= sides; ++i) {
        const float a = kTwoPi * i / sides;
        const glm::vec3 radial = std::cos(a) * f.normal + std::sin(a) * f.binormal;
        MeshVertex rim;
        rim.position = base + radial * radius;
        rim.normal = safeNormalize(radial + f.tangent * slope, radial);
        rim.uv = glm::vec2(static_cast<float>(i) / sides, 0.0f);
        MeshVertex tip = rim;
        tip.position = apex;
        tip.uv.y = 1.0f;
        mesh.vertices.push_back(rim);
        mesh.vertices.push_back(tip);
    }
    for (int i = 0; i < sides; ++i) {
        const uint32_t r0 = i * 2, t0 = r0 + 1, r1 = r0 + 2;
        addTriangle(mesh, r0, r1, t0);
    }
    // base cap
    const uint32_t centerIndex = static_cast<uint32_t>(mesh.vertices.size());
    mesh.vertices.push_back({base, -f.tangent, glm::vec2(0.5f)});
    for (int i = 0; i <= sides; ++i) {
        const float a = kTwoPi * i / sides;
        const glm::vec3 radial = std::cos(a) * f.normal + std::sin(a) * f.binormal;
        mesh.vertices.push_back({base + radial * radius, -f.tangent,
                                 glm::vec2(0.5f + 0.5f * std::cos(a), 0.5f + 0.5f * std::sin(a))});
    }
    for (int i = 0; i < sides; ++i) {
        addTriangle(mesh, centerIndex, centerIndex + 2 + i, centerIndex + 1 + i);
    }
    return mesh;
}

MeshData prism(const glm::vec3& base, const glm::vec3& direction, float radius, float length, int sides, float startAngle) {
    MeshData mesh;
    sides = std::max(sides, 3);
    const Frame f = frameFromDirection(base, direction);
    const glm::vec3 top = base + f.tangent * length;
    // Flat-shaded sides: 4 unique vertices per face.
    for (int i = 0; i < sides; ++i) {
        const float a0 = startAngle + kTwoPi * i / sides;
        const float a1 = startAngle + kTwoPi * (i + 1) / sides;
        const glm::vec3 r0 = std::cos(a0) * f.normal + std::sin(a0) * f.binormal;
        const glm::vec3 r1 = std::cos(a1) * f.normal + std::sin(a1) * f.binormal;
        const glm::vec3 n = safeNormalize(r0 + r1, r0);
        const uint32_t start = static_cast<uint32_t>(mesh.vertices.size());
        const float u0 = static_cast<float>(i) / sides, u1 = static_cast<float>(i + 1) / sides;
        mesh.vertices.push_back({base + r0 * radius, n, {u0, 0.0f}});
        mesh.vertices.push_back({base + r1 * radius, n, {u1, 0.0f}});
        mesh.vertices.push_back({top + r1 * radius, n, {u1, 1.0f}});
        mesh.vertices.push_back({top + r0 * radius, n, {u0, 1.0f}});
        addTriangle(mesh, start, start + 2, start + 1);
        addTriangle(mesh, start, start + 3, start + 2);
    }
    // caps
    for (int cap = 0; cap < 2; ++cap) {
        const glm::vec3 c = cap == 0 ? base : top;
        const glm::vec3 n = cap == 0 ? -f.tangent : f.tangent;
        const uint32_t centerIndex = static_cast<uint32_t>(mesh.vertices.size());
        mesh.vertices.push_back({c, n, glm::vec2(0.5f)});
        for (int i = 0; i <= sides; ++i) {
            const float a = startAngle + kTwoPi * i / sides;
            const glm::vec3 radial = std::cos(a) * f.normal + std::sin(a) * f.binormal;
            mesh.vertices.push_back({c + radial * radius, n, glm::vec2(0.5f + 0.5f * std::cos(a), 0.5f + 0.5f * std::sin(a))});
        }
        for (int i = 0; i < sides; ++i) {
            if (cap == 0) addTriangle(mesh, centerIndex, centerIndex + 1 + i, centerIndex + 2 + i);
            else addTriangle(mesh, centerIndex, centerIndex + 2 + i, centerIndex + 1 + i);
        }
    }
    return mesh;
}

MeshData box(const glm::vec3& center, const glm::vec3& h) {
    MeshData mesh;
    const glm::vec3 axes[3] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
    for (int axis = 0; axis < 3; ++axis) {
        for (int sign = -1; sign <= 1; sign += 2) {
            const glm::vec3 n = axes[axis] * static_cast<float>(sign);
            const glm::vec3 u = axes[(axis + 1) % 3];
            const glm::vec3 v = axes[(axis + 2) % 3];
            const glm::vec3 faceCenter = center + n * h[axis];
            const float hu = h[(axis + 1) % 3], hv = h[(axis + 2) % 3];
            const uint32_t start = static_cast<uint32_t>(mesh.vertices.size());
            mesh.vertices.push_back({faceCenter - u * hu - v * hv, n, {0, 0}});
            mesh.vertices.push_back({faceCenter + u * hu - v * hv, n, {1, 0}});
            mesh.vertices.push_back({faceCenter + u * hu + v * hv, n, {1, 1}});
            mesh.vertices.push_back({faceCenter - u * hu + v * hv, n, {0, 1}});
            if (sign > 0) {
                addTriangle(mesh, start, start + 1, start + 2);
                addTriangle(mesh, start, start + 2, start + 3);
            } else {
                addTriangle(mesh, start, start + 2, start + 1);
                addTriangle(mesh, start, start + 3, start + 2);
            }
        }
    }
    return mesh;
}

MeshData tube(const std::vector<glm::vec3>& path, const std::vector<float>& radii, int sides, bool capEnds) {
    MeshData mesh;
    if (path.size() < 2) return mesh;
    sides = std::max(sides, 3);
    const size_t count = path.size();
    // Parallel-transport frames keep the rings from twisting.
    std::vector<Frame> frames(count);
    frames[0] = frameFromDirection(path[0], path[1] - path[0]);
    for (size_t i = 1; i < count; ++i) {
        const glm::vec3 forward = i + 1 < count ? path[i + 1] - path[i - 1] : path[i] - path[i - 1];
        const glm::vec3 t = safeNormalize(forward, frames[i - 1].tangent);
        glm::vec3 n = frames[i - 1].normal - t * glm::dot(frames[i - 1].normal, t);
        n = safeNormalize(n, frameFromDirection(path[i], t).normal);
        frames[i].origin = path[i];
        frames[i].tangent = t;
        frames[i].normal = n;
        frames[i].binormal = glm::cross(t, n);
    }
    float travelled = 0.0f;
    for (size_t i = 0; i < count; ++i) {
        if (i > 0) travelled += glm::length(path[i] - path[i - 1]);
        const float radius = i < radii.size() ? radii[i] : (radii.empty() ? 0.1f : radii.back());
        for (int s = 0; s <= sides; ++s) {
            const float a = kTwoPi * s / sides;
            const glm::vec3 radial = std::cos(a) * frames[i].normal + std::sin(a) * frames[i].binormal;
            mesh.vertices.push_back({path[i] + radial * radius, radial, {static_cast<float>(s) / sides, travelled}});
        }
    }
    const uint32_t stride = static_cast<uint32_t>(sides + 1);
    for (size_t i = 0; i + 1 < count; ++i) {
        for (int s = 0; s < sides; ++s) {
            const uint32_t a = static_cast<uint32_t>(i) * stride + s, b = a + stride;
            addTriangle(mesh, a, b, a + 1);
            addTriangle(mesh, a + 1, b, b + 1);
        }
    }
    if (capEnds) {
        for (int end = 0; end < 2; ++end) {
            const size_t i = end == 0 ? 0 : count - 1;
            const float radius = i < radii.size() ? radii[i] : (radii.empty() ? 0.1f : radii.back());
            const glm::vec3 n = end == 0 ? -frames[i].tangent : frames[i].tangent;
            const uint32_t centerIndex = static_cast<uint32_t>(mesh.vertices.size());
            mesh.vertices.push_back({path[i], n, glm::vec2(0.5f)});
            for (int s = 0; s <= sides; ++s) {
                const float a = kTwoPi * s / sides;
                const glm::vec3 radial = std::cos(a) * frames[i].normal + std::sin(a) * frames[i].binormal;
                mesh.vertices.push_back({path[i] + radial * radius, n, glm::vec2(0.5f + 0.5f * std::cos(a), 0.5f + 0.5f * std::sin(a))});
            }
            for (int s = 0; s < sides; ++s) {
                if (end == 0) addTriangle(mesh, centerIndex, centerIndex + 1 + s, centerIndex + 2 + s);
                else addTriangle(mesh, centerIndex, centerIndex + 2 + s, centerIndex + 1 + s);
            }
        }
    }
    return mesh;
}

MeshData shell(const Frame& frame, float radius, float thickness, float length, float arcRadians, int arcSegments) {
    MeshData mesh;
    arcSegments = std::max(arcSegments, 1);
    const float start = -0.5f * arcRadians;
    // outer and inner surfaces
    for (int layer = 0; layer < 2; ++layer) {
        const float r = layer == 0 ? radius + thickness : radius;
        const uint32_t base = static_cast<uint32_t>(mesh.vertices.size());
        for (int s = 0; s <= arcSegments; ++s) {
            const float a = start + arcRadians * s / arcSegments;
            const glm::vec3 radial = std::cos(a) * frame.normal + std::sin(a) * frame.binormal;
            const glm::vec3 n = layer == 0 ? radial : -radial;
            const float u = static_cast<float>(s) / arcSegments;
            mesh.vertices.push_back({frame.origin + radial * r, n, {u, 0.0f}});
            mesh.vertices.push_back({frame.origin + radial * r + frame.tangent * length, n, {u, 1.0f}});
        }
        for (int s = 0; s < arcSegments; ++s) {
            const uint32_t a = base + s * 2;
            if (layer == 0) {
                addTriangle(mesh, a, a + 1, a + 2);
                addTriangle(mesh, a + 1, a + 3, a + 2);
            } else {
                addTriangle(mesh, a, a + 2, a + 1);
                addTriangle(mesh, a + 1, a + 2, a + 3);
            }
        }
    }
    // front/back rims
    const uint32_t outerBase = 0;
    const uint32_t innerBase = static_cast<uint32_t>((arcSegments + 1) * 2);
    for (int s = 0; s < arcSegments; ++s) {
        for (int end = 0; end < 2; ++end) {
            const uint32_t o0 = outerBase + s * 2 + end, o1 = o0 + 2;
            const uint32_t i0 = innerBase + s * 2 + end, i1 = i0 + 2;
            if (end == 0) {
                addTriangle(mesh, o0, o1, i0);
                addTriangle(mesh, o1, i1, i0);
            } else {
                addTriangle(mesh, o0, i0, o1);
                addTriangle(mesh, o1, i0, i1);
            }
        }
    }
    return mesh;
}

MeshData membrane(const glm::vec3& a, const glm::vec3& b, const glm::vec3& c, const glm::vec3& d) {
    MeshData mesh;
    const glm::vec3 n = safeNormalize(glm::cross(b - a, d - a), glm::vec3(0.0f, 1.0f, 0.0f));
    for (int side = 0; side < 2; ++side) {
        const glm::vec3 sn = side == 0 ? n : -n;
        const uint32_t start = static_cast<uint32_t>(mesh.vertices.size());
        mesh.vertices.push_back({a, sn, {0, 0}});
        mesh.vertices.push_back({b, sn, {1, 0}});
        mesh.vertices.push_back({c, sn, {1, 1}});
        mesh.vertices.push_back({d, sn, {0, 1}});
        if (side == 0) {
            addTriangle(mesh, start, start + 1, start + 2);
            addTriangle(mesh, start, start + 2, start + 3);
        } else {
            addTriangle(mesh, start, start + 2, start + 1);
            addTriangle(mesh, start, start + 3, start + 2);
        }
    }
    return mesh;
}

void displaceAlongNormals(MeshData& mesh, float amplitude, float frequency, uint32_t seed, int octaves) {
    if (amplitude == 0.0f) return;
    for (auto& v : mesh.vertices) {
        const float n = Noise::fbm3(v.position * frequency, octaves, seed);
        v.position += v.normal * (n * amplitude);
    }
    mesh.recomputeNormals();
}

} // namespace Geometry

} // namespace CreatureAssets
} // namespace MagiTech
