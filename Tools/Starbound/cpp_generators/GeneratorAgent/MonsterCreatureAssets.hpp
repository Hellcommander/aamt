#pragma once

/**
 * CPU-side asset data shared by the creature generator families
 * (MagiTech::Monsters and MagiTech::SegmentedCreatures).
 *
 *  - MeshData / TextureData / SkeletonData / AnimationData / BehaviorTreeData:
 *    plain data produced by the generators.
 *  - AssetStore: process-wide, thread-safe registry that owns generated assets
 *    and hands out the uint32 handles stored in the families' asset bundles
 *    (0 always means "no asset").
 *  - Geometry / Noise: small procedural helpers used by the mesh and texture
 *    generators.
 */

#include <glm/glm.hpp>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace MagiTech {
namespace CreatureAssets {

// ---------------------------------------------------------------- mesh
struct MeshVertex {
    glm::vec3 position{0.0f};
    glm::vec3 normal{0.0f, 1.0f, 0.0f};
    glm::vec2 uv{0.0f};
};

struct MeshData {
    std::vector<MeshVertex> vertices;
    std::vector<uint32_t> indices;

    bool empty() const { return vertices.empty(); }
    size_t triangleCount() const { return indices.size() / 3; }

    /** Appends another mesh, re-basing its indices. */
    void append(const MeshData& other);
    /** Applies an affine transform to positions and normals. */
    void transform(const glm::mat4& m);
    /** Recomputes smooth per-vertex normals from the triangles. */
    void recomputeNormals();
    /** Axis-aligned bounds; both zero for an empty mesh. */
    std::pair<glm::vec3, glm::vec3> bounds() const;
};

// ---------------------------------------------------------------- texture
struct TextureData {
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4, row-major
    float roughness = 0.5f;      // scalar PBR factors the texture was authored for
    float metallic = 0.0f;

    TextureData() = default;
    TextureData(uint32_t w, uint32_t h) { resize(w, h); }

    void resize(uint32_t w, uint32_t h);
    bool empty() const { return rgba.empty(); }
    glm::vec4 get(uint32_t x, uint32_t y) const;          // components in [0,1]
    void set(uint32_t x, uint32_t y, const glm::vec4& c);  // clamps to [0,1]
    /** Bilinear sample with wrapping UVs. */
    glm::vec4 sample(float u, float v) const;
};

// ---------------------------------------------------------------- skeleton
struct Bone {
    std::string name;
    int parent = -1;
    glm::vec3 head{0.0f};   // joint position (model space)
    glm::vec3 tail{0.0f};   // bone end position (model space)
    float minAngle = -3.14159265f;  // joint limits in radians
    float maxAngle = 3.14159265f;
    float stiffness = 0.5f;         // 0 = floppy, 1 = rigid
};

struct SkeletonData {
    std::vector<Bone> bones;

    int addBone(const std::string& name, int parent, const glm::vec3& head, const glm::vec3& tail);
    int find(const std::string& name) const;
    float length(int bone) const;
};

// ---------------------------------------------------------------- animation
struct BoneKey {
    glm::vec3 rotation{0.0f};     // euler angles in radians (pitch, yaw, roll)
    glm::vec3 translation{0.0f};  // offset from bind pose
};

struct AnimationFrame {
    float time = 0.0f;
    std::vector<BoneKey> bones;   // one entry per skeleton bone
};

struct AnimationClip {
    std::string name;
    float duration = 1.0f;
    bool loop = true;
    std::vector<AnimationFrame> frames;
};

struct AnimationData {
    std::vector<AnimationClip> clips;
    size_t boneCount = 0;
    // Optional track names. When set, frame.bones[i] animates the skeleton bone named
    // boneNames[i] (tracks for bones a skeleton lacks are ignored); when empty, keys are
    // indexed by skeleton bone index.
    std::vector<std::string> boneNames;

    const AnimationClip* find(const std::string& name) const;
    size_t frameCount() const;
    /**
     * Creates a clip with `frameCount` evenly spaced frames and fills each bone key with
     * `pose(boneIndex, phase)` where phase runs over [0,1).
     */
    template <typename PoseFn>
    AnimationClip& addSampledClip(const std::string& name, float duration, bool loop,
                                  size_t frameCount, PoseFn&& pose) {
        AnimationClip clip;
        clip.name = name;
        clip.duration = duration;
        clip.loop = loop;
        const size_t frames = frameCount == 0 ? 1 : frameCount;
        clip.frames.reserve(frames);
        for (size_t f = 0; f < frames; ++f) {
            const float phase = static_cast<float>(f) / static_cast<float>(loop ? frames : (frames > 1 ? frames - 1 : 1));
            AnimationFrame frame;
            frame.time = phase * duration;
            frame.bones.resize(boneCount);
            for (size_t b = 0; b < boneCount; ++b) {
                frame.bones[b] = pose(b, phase);
            }
            clip.frames.push_back(std::move(frame));
        }
        clips.push_back(std::move(clip));
        return clips.back();
    }
};

// ---------------------------------------------------------------- behaviour
enum class BehaviorNodeType : uint8_t { Selector, Sequence, Parallel, Condition, Action };

struct BehaviorNode {
    BehaviorNodeType type = BehaviorNodeType::Action;
    std::string name;
    std::map<std::string, float> params;
    std::vector<int> children;
};

struct BehaviorTransition {
    std::string condition;
    std::string target;
};

struct BehaviorState {
    std::string name;
    int treeRoot = -1;   // node evaluated while in this state
    std::vector<BehaviorTransition> transitions;
};

struct BehaviorTreeData {
    std::string name;
    std::vector<BehaviorNode> nodes;
    int root = -1;
    std::map<std::string, float> blackboard;
    std::vector<BehaviorState> states;
    std::string initialState;

    int addNode(BehaviorNodeType type, const std::string& name, std::map<std::string, float> params = {});
    void addChild(int parent, int child);
    /** Adds a node and attaches it to `parent` in one step. */
    int addChildNode(int parent, BehaviorNodeType type, const std::string& name, std::map<std::string, float> params = {});
    BehaviorState& addState(const std::string& name, int treeRoot);
    BehaviorState* findState(const std::string& name);
    int depth() const;
};

// ---------------------------------------------------------------- store
/** Thread-safe owner of generated assets; handles are unique per asset kind and never 0. */
class AssetStore {
public:
    static AssetStore& instance();

    uint32_t addMesh(MeshData mesh);
    uint32_t addTexture(TextureData texture);
    uint32_t addSkeleton(SkeletonData skeleton);
    uint32_t addAnimation(AnimationData animation);
    uint32_t addBehavior(BehaviorTreeData behavior);

    std::shared_ptr<const MeshData> mesh(uint32_t handle) const;
    std::shared_ptr<const TextureData> texture(uint32_t handle) const;
    std::shared_ptr<const SkeletonData> skeleton(uint32_t handle) const;
    std::shared_ptr<const AnimationData> animation(uint32_t handle) const;
    std::shared_ptr<const BehaviorTreeData> behavior(uint32_t handle) const;

    bool releaseMesh(uint32_t handle);
    bool releaseTexture(uint32_t handle);
    bool releaseSkeleton(uint32_t handle);
    bool releaseAnimation(uint32_t handle);
    bool releaseBehavior(uint32_t handle);

    struct Counts {
        size_t meshes = 0, textures = 0, skeletons = 0, animations = 0, behaviors = 0;
    };
    Counts counts() const;
    void clear();

private:
    template <typename T>
    struct Table {
        std::unordered_map<uint32_t, std::shared_ptr<const T>> items;
        uint32_t next = 1;
    };

    template <typename T>
    uint32_t add(Table<T>& table, T&& value);
    template <typename T>
    std::shared_ptr<const T> get(const Table<T>& table, uint32_t handle) const;
    template <typename T>
    bool release(Table<T>& table, uint32_t handle);

    mutable std::mutex m_mutex;
    Table<MeshData> m_meshes;
    Table<TextureData> m_textures;
    Table<SkeletonData> m_skeletons;
    Table<AnimationData> m_animations;
    Table<BehaviorTreeData> m_behaviors;
};

// ---------------------------------------------------------------- noise
namespace Noise {
    /** Deterministic integer hash -> [0,1). */
    float hash3(int x, int y, int z, uint32_t seed);
    /** Smooth value noise in [-1,1]. */
    float value3(const glm::vec3& p, uint32_t seed);
    /** Fractal sum of value noise in roughly [-1,1]. */
    float fbm3(const glm::vec3& p, int octaves, uint32_t seed);
    /** Distance to the nearest feature point of a cellular (Worley) grid, ~[0,1]. */
    float worley2(const glm::vec2& p, uint32_t seed);
    /** Stable 32-bit hash of a string (FNV-1a), handy for seeding from ids. */
    uint32_t seedFromString(const std::string& text);
}

// ---------------------------------------------------------------- geometry
namespace Geometry {
    /** Orthonormal frame (tangent, normal, binormal) with tangent along `forward`. */
    struct Frame {
        glm::vec3 origin{0.0f};
        glm::vec3 tangent{1.0f, 0.0f, 0.0f};
        glm::vec3 normal{0.0f, 1.0f, 0.0f};
        glm::vec3 binormal{0.0f, 0.0f, 1.0f};
    };
    Frame frameFromDirection(const glm::vec3& origin, const glm::vec3& forward);

    MeshData ellipsoid(const glm::vec3& center, const glm::vec3& radii, int rings, int sectors);
    MeshData sphere(const glm::vec3& center, float radius, int rings, int sectors);
    /** Closed cone from `base` along `direction` (normalised internally). */
    MeshData cone(const glm::vec3& base, const glm::vec3& direction, float radius, float length, int sides);
    /** Closed prism/cylinder with `sides` faces from `base` along `direction`. */
    MeshData prism(const glm::vec3& base, const glm::vec3& direction, float radius, float length, int sides,
                   float startAngle = 0.0f);
    MeshData box(const glm::vec3& center, const glm::vec3& halfExtents);
    /**
     * Swept tube through `path` with per-point `radii` (same size as path, >= 2 points),
     * `sides` faces around, optional end caps.
     */
    MeshData tube(const std::vector<glm::vec3>& path, const std::vector<float>& radii, int sides, bool capEnds);
    /** Partial cylindrical shell (arc of `arcRadians` centred on +normal of the frame). */
    MeshData shell(const Frame& frame, float radius, float thickness, float length, float arcRadians, int arcSegments);
    /** Flat double-sided quad fan (wings, fins) spanning the given corner points. */
    MeshData membrane(const glm::vec3& a, const glm::vec3& b, const glm::vec3& c, const glm::vec3& d);

    /** Moves each vertex along its normal by amplitude * fbm(position * frequency). */
    void displaceAlongNormals(MeshData& mesh, float amplitude, float frequency, uint32_t seed, int octaves = 3);
}

} // namespace CreatureAssets
} // namespace MagiTech
