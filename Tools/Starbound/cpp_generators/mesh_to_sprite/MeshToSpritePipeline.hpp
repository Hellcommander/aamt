#pragma once

#include <vector>
#include <memory>
#include <unordered_map>
#include <string>
#include <functional>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <chrono>

// Graphics API headers (simplified for cross-platform)
#ifdef _WIN32
#include <d3d11.h>
#elif defined(__linux__) || defined(__APPLE__)
#include <GL/gl.h>
#endif

namespace MagiTech {
namespace Animation {

/**
 * @brief Comprehensive mesh-to-sprite pipeline for converting 3D animations to 2D sprites
 * 
 * Renders 3D mesh animations offscreen and bakes them into sprite sheets with
 * accompanying animation metadata for use in 2D engines like Starbound.
 */
class MeshToSpritePipeline {
public:
    enum class RenderBackend {
        OPENGL,
        DIRECTX11,
        VULKAN,
        SOFTWARE_RASTERIZER
    };

    enum class CameraType {
        ORTHOGRAPHIC,
        PERSPECTIVE,
        ISOMETRIC
    };

    enum class LightingMode {
        NONE,
        AMBIENT_ONLY,
        DIRECTIONAL,
        POINT_LIGHT,
        FULL_PBR
    };

    enum class OutputFormat {
        PNG,
        WEBP,
        TGA,
        BMP
    };

    struct CameraConfig {
        CameraType type = CameraType::ORTHOGRAPHIC;
        glm::vec3 position = glm::vec3(0, 0, 5);
        glm::vec3 target = glm::vec3(0, 0, 0);
        glm::vec3 up = glm::vec3(0, 1, 0);
        float fov = 45.0f;
        float near_plane = 0.1f;
        float far_plane = 100.0f;
        float ortho_size = 5.0f;
        bool auto_fit_bounds = true;
    };

    struct LightingConfig {
        LightingMode mode = LightingMode::DIRECTIONAL;
        glm::vec3 ambient_color = glm::vec3(0.2f, 0.2f, 0.2f);
        glm::vec3 directional_direction = glm::vec3(-1, -1, -1);
        glm::vec3 directional_color = glm::vec3(1.0f, 1.0f, 1.0f);
        float directional_intensity = 1.0f;
        std::vector<glm::vec3> point_light_positions;
        std::vector<glm::vec3> point_light_colors;
        std::vector<float> point_light_intensities;
        bool cast_shadows = false;
        float shadow_bias = 0.001f;
    };

    struct RenderConfig {
        uint32_t frame_width = 128;
        uint32_t frame_height = 128;
        uint32_t samples = 4; // MSAA samples
        bool enable_alpha = true;
        bool enable_depth_test = true;
        glm::vec4 background_color = glm::vec4(0, 0, 0, 0); // Transparent background
        bool render_wireframe = false;
        bool render_normals = false;
        bool render_bounds = false;
    };

    struct AnimationCapture {
        std::string animation_name;
        float start_time = 0.0f;
        float end_time = 1.0f;
        float fps = 24.0f;
        bool loop = true;
        std::vector<std::string> captured_angles; // ["front", "back", "left", "right", etc.]
    };

    struct DirectionalCapture {
        std::string direction_name;
        glm::vec3 camera_offset;
        float yaw_rotation = 0.0f;
        float pitch_rotation = 0.0f;
    };

    struct SpriteFrame {
        uint32_t frame_index;
        std::string filename;
        glm::ivec2 position; // Position in sprite sheet
        glm::ivec2 size;     // Frame size
        glm::vec2 pivot;     // Pivot point (normalized 0-1)
        float timestamp;     // Time in animation
        bool is_key_frame;
        std::vector<uint8_t> pixel_data; // RGBA pixel data
    };

    struct SpriteSheet {
        std::string name;
        uint32_t width;
        uint32_t height;
        std::vector<SpriteFrame> frames;
        std::vector<uint8_t> packed_data; // Final sprite sheet data
        std::string texture_filename;
    };

    struct AnimationDefinition {
        std::string animation_name;
        float duration;
        float fps;
        bool loop;
        std::vector<uint32_t> frame_sequence;
        std::vector<float> frame_times;
        std::unordered_map<std::string, std::vector<uint32_t>> directional_sequences;
    };

    struct PipelineConfig {
        RenderBackend backend = RenderBackend::OPENGL;
        CameraConfig camera;
        LightingConfig lighting;
        RenderConfig render;
        OutputFormat output_format = OutputFormat::PNG;
        std::string output_directory = "./output";
        std::string asset_prefix = "mech";
        bool generate_sprite_sheets = true;
        bool generate_individual_frames = false;
        bool generate_animation_json = true;
        bool generate_starbound_files = true;
        bool enable_multithreading = true;
        bool enable_progressive_capture = false;
        uint32_t max_sheet_width = 2048;
        uint32_t max_sheet_height = 2048;
        float sprite_padding = 2.0f;
        bool power_of_two_sheets = true;
        bool optimize_empty_space = true;
    };

    struct PerformanceStats {
        uint64_t frames_rendered = 0;
        uint64_t sprites_packed = 0;
        uint64_t animations_generated = 0;
        double total_render_time = 0.0;
        double total_packing_time = 0.0;
        double avg_frame_render_time = 0.0;
        double avg_packing_time = 0.0;
        size_t total_output_size = 0;
        size_t compressed_size = 0;
        float compression_ratio = 1.0f;
    };

    MeshToSpritePipeline();
    ~MeshToSpritePipeline();

    // Initialization and configuration
    bool initialize(const PipelineConfig& config = PipelineConfig{});
    void shutdown();
    void set_config(const PipelineConfig& config);
    const PipelineConfig& get_config() const { return config_; }

    // Mesh and animation setup
    bool load_mesh(const std::string& mesh_file);
    bool load_animation_clip(const std::string& animation_name, const std::string& clip_file);
    void set_mesh_transform(const glm::mat4& transform);
    void add_material_override(const std::string& material_name, const std::string& texture_path);

    // Camera and lighting setup
    void setup_camera(const CameraConfig& camera_config);
    void setup_lighting(const LightingConfig& lighting_config);
    void add_directional_capture(const std::string& name, const glm::vec3& camera_offset, 
                                 float yaw = 0.0f, float pitch = 0.0f);

    // Animation capture
    bool capture_animation(const AnimationCapture& capture_config);
    bool capture_all_animations();
    bool capture_directional_set(const std::string& animation_name, 
                                const std::vector<DirectionalCapture>& directions);

    // Frame processing
    std::vector<SpriteFrame> render_animation_frames(const std::string& animation_name);
    SpriteFrame render_single_frame(const std::string& animation_name, float time, 
                                   const std::string& direction = "");

    // Sprite sheet generation
    SpriteSheet pack_frames_to_sheet(const std::vector<SpriteFrame>& frames, 
                                    const std::string& sheet_name);
    std::vector<SpriteSheet> pack_all_animations();
    bool optimize_sprite_sheet(SpriteSheet& sheet);

    // Output generation
    bool export_sprite_sheet(const SpriteSheet& sheet);
    bool export_frames_json(const SpriteSheet& sheet);
    bool export_animation_definition(const AnimationDefinition& animation);
    bool export_starbound_animation(const AnimationDefinition& animation);
    bool export_starbound_projectile(const std::string& projectile_name, 
                                   const std::vector<AnimationDefinition>& animations);

    // Batch processing
    bool process_batch(const std::vector<std::string>& mesh_files,
                      const std::vector<AnimationCapture>& captures);
    void set_progress_callback(std::function<void(float, const std::string&)> callback);

    // Utility and inspection
    std::vector<std::string> get_available_animations() const;
    std::vector<std::string> get_loaded_meshes() const;
    glm::vec3 calculate_mesh_bounds() const;
    void auto_fit_camera_to_mesh();

    // Performance monitoring
    void reset_performance_stats();
    const PerformanceStats& get_performance_stats() const { return performance_stats_; }

    // Advanced features
    bool enable_normal_mapping(bool enable);
    bool enable_ambient_occlusion(bool enable);
    void set_custom_shader(const std::string& vertex_shader, const std::string& fragment_shader);
    void add_post_process_effect(const std::string& effect_name, const std::string& shader);

private:
    struct MeshData {
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        std::vector<glm::vec4> bone_weights;
        std::vector<glm::uvec4> bone_indices;
        glm::mat4 transform = glm::mat4(1.0f);
        std::string material_name;
    };

    struct AnimationClip {
        std::string name;
        float duration;
        std::vector<glm::mat4> bone_matrices;
        std::vector<float> keyframe_times;
        bool loop;
    };

    struct RenderContext {
        void* device;
        void* context;
        void* framebuffer;
        void* color_texture;
        void* depth_texture;
        void* render_target_view;
        void* depth_stencil_view;
        uint32_t viewport_width;
        uint32_t viewport_height;
    };

    // Core state
    bool is_initialized_;
    PipelineConfig config_;
    RenderContext render_context_;
    PerformanceStats performance_stats_;

    // Mesh and animation data
    std::vector<MeshData> loaded_meshes_;
    std::unordered_map<std::string, AnimationClip> animation_clips_;
    std::unordered_map<std::string, std::string> material_overrides_;
    std::vector<DirectionalCapture> directional_captures_;

    // Camera and lighting state
    CameraConfig current_camera_;
    LightingConfig current_lighting_;
    glm::mat4 view_matrix_;
    glm::mat4 projection_matrix_;

    // Progress tracking
    std::function<void(float, const std::string&)> progress_callback_;
    std::atomic<bool> is_processing_;

    // Render backend implementations
    bool initialize_opengl();
    bool initialize_directx11();
    void cleanup_opengl();
    void cleanup_directx11();

    // Mesh loading
    bool load_mesh_obj(const std::string& filename);
    bool load_mesh_fbx(const std::string& filename);
    bool load_mesh_gltf(const std::string& filename);

    // Animation loading
    bool load_animation_bvh(const std::string& filename);
    bool load_animation_fbx(const std::string& filename);
    bool load_animation_gltf(const std::string& filename);

    // Rendering pipeline
    void setup_render_target();
    void clear_render_target();
    void render_mesh_with_animation(const MeshData& mesh, const AnimationClip& clip, float time);
    void apply_lighting();
    void capture_framebuffer(std::vector<uint8_t>& pixel_data);

    // Camera and view calculations
    void update_view_matrix();
    void update_projection_matrix();
    glm::mat4 calculate_model_matrix(const AnimationClip& clip, float time);

    // Sprite packing algorithms
    struct PackingNode {
        glm::ivec2 position;
        glm::ivec2 size;
        bool occupied;
        std::unique_ptr<PackingNode> left;
        std::unique_ptr<PackingNode> right;
    };

    PackingNode* pack_rectangle(PackingNode* node, glm::ivec2 size);
    bool fits_in_sheet(const std::vector<SpriteFrame>& frames, uint32_t width, uint32_t height);
    void optimize_packing_order(std::vector<SpriteFrame>& frames);

    // Image processing
    bool save_image_png(const std::string& filename, const std::vector<uint8_t>& data, 
                       uint32_t width, uint32_t height);
    bool save_image_webp(const std::string& filename, const std::vector<uint8_t>& data, 
                        uint32_t width, uint32_t height);
    std::vector<uint8_t> compress_image_data(const std::vector<uint8_t>& data);

    // JSON generation
    std::string generate_frames_json(const SpriteSheet& sheet);
    std::string generate_animation_json(const AnimationDefinition& animation);
    std::string generate_starbound_animation_json(const AnimationDefinition& animation);
    std::string generate_starbound_projectile_json(const std::string& projectile_name,
                                                  const std::vector<AnimationDefinition>& animations);

    // Utility functions
    std::string get_timestamp_string();
    std::string sanitize_filename(const std::string& name);
    bool create_directory_if_not_exists(const std::string& path);
    glm::vec3 calculate_bounds_center(const MeshData& mesh);
    float calculate_bounds_radius(const MeshData& mesh);

    // Performance tracking
    void update_performance_stats(const std::string& operation, double time_taken);
    std::chrono::high_resolution_clock::time_point get_current_time();
};

// Utility functions for common use cases
namespace MeshToSpriteUtils {
    // Preset camera configurations
    CameraConfig CreateIsometricCamera(float distance = 5.0f);
    CameraConfig CreateTopDownCamera(float distance = 10.0f);
    CameraConfig CreateSideViewCamera(float distance = 5.0f);

    // Preset lighting configurations
    LightingConfig CreateBasicLighting();
    LightingConfig CreateDramaticLighting();
    LightingConfig CreateSoftLighting();

    // Common directional capture sets
    std::vector<DirectionalCapture> Create8DirectionalSet(float distance = 5.0f);
    std::vector<DirectionalCapture> Create4DirectionalSet(float distance = 5.0f);
    std::vector<DirectionalCapture> CreateSingleDirectionSet(float distance = 5.0f);

    // Animation processing helpers
    AnimationCapture CreateBasicCapture(const std::string& name, float duration, float fps = 24.0f);
    std::vector<AnimationCapture> CreateCaptureSet(const std::vector<std::string>& animation_names);

    // Starbound-specific helpers
    std::string GenerateStarboundProjectileConfig(const std::string& projectile_name,
                                                 const std::string& sprite_sheet,
                                                 const AnimationDefinition& animation);
}

} // namespace Animation
} // namespace MagiTech