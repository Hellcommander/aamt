#include "MeshToSpritePipeline.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <cmath>
#include <thread>
#include <iomanip>
#include <cfloat>
#include <cstring>
#include <cstdlib>
#include <limits>
#include <iterator>
#include <glm/gtc/quaternion.hpp>

// Image I/O: stb_image / stb_image_write. Their implementations are compiled exactly once
// in core/StbImageImpl.cpp, so no *_IMPLEMENTATION defines here.
#include <stb_image.h>
#include <stb_image_write.h>

// stb_image_write defines this zlib encoder (used for its PNG writer) but does not declare it
// in the header section; STBIWDEF is extern "C" when compiled as C++.
extern "C" unsigned char* stbi_zlib_compress(unsigned char* data, int data_len, int* out_len, int quality);

namespace MagiTech {
namespace Animation {

MeshToSpritePipeline::MeshToSpritePipeline() 
    : is_initialized_(false)
    , is_processing_(false)
{
    config_ = PipelineConfig{};
    performance_stats_ = PerformanceStats{};
    current_camera_ = CameraConfig{};
    current_lighting_ = LightingConfig{};
    view_matrix_ = glm::mat4(1.0f);
    projection_matrix_ = glm::mat4(1.0f);
}

MeshToSpritePipeline::~MeshToSpritePipeline() {
    shutdown();
}

bool MeshToSpritePipeline::initialize(const PipelineConfig& config) {
    if (is_initialized_) {
        return true;
    }
    
    config_ = config;
    
    // Initialize render backend
    bool backend_success = false;
    switch (config_.backend) {
        case RenderBackend::OPENGL:
            backend_success = initialize_opengl();
            break;
        case RenderBackend::DIRECTX11:
            backend_success = initialize_directx11();
            break;
        case RenderBackend::VULKAN:
            std::cout << "Vulkan backend requested: rendering with the software rasterizer" << std::endl;
            render_context_ = RenderContext{};
            backend_success = true;
            break;
        case RenderBackend::SOFTWARE_RASTERIZER:
            render_context_ = RenderContext{};
            backend_success = true;
            break;
    }
    
    if (!backend_success) {
        std::cerr << "Failed to initialize render backend" << std::endl;
        return false;
    }
    
    // Setup render target
    setup_render_target();
    
    // Initialize camera and lighting
    setup_camera(config_.camera);
    setup_lighting(config_.lighting);
    
    // Create output directory
    create_directory_if_not_exists(config_.output_directory);
    
    is_initialized_ = true;
    
    std::cout << "Mesh-to-Sprite Pipeline initialized successfully" << std::endl;
    static const char* backend_names[] = { "OpenGL", "DirectX11", "Vulkan", "Software" };
    std::cout << "Backend: " << backend_names[static_cast<int>(config_.backend)] << " (software rasterizer)" << std::endl;
    std::cout << "Output resolution: " << config_.render.frame_width << "x" << config_.render.frame_height << std::endl;
    
    return true;
}

void MeshToSpritePipeline::shutdown() {
    if (!is_initialized_) {
        return;
    }
    
    // Clean up render backend
    switch (config_.backend) {
        case RenderBackend::OPENGL:
            cleanup_opengl();
            break;
        case RenderBackend::DIRECTX11:
            cleanup_directx11();
            break;
        case RenderBackend::VULKAN:
        case RenderBackend::SOFTWARE_RASTERIZER:
            cleanup_opengl();  // releases the shared software render target
            break;
    }
    
    // Clear data
    loaded_meshes_.clear();
    animation_clips_.clear();
    material_overrides_.clear();
    directional_captures_.clear();
    
    is_initialized_ = false;
    
    std::cout << "Mesh-to-Sprite Pipeline shutdown complete" << std::endl;
}

void MeshToSpritePipeline::set_config(const PipelineConfig& config) {
    config_ = config;
    
    if (is_initialized_) {
        setup_camera(config_.camera);
        setup_lighting(config_.lighting);
    }
}

bool MeshToSpritePipeline::load_mesh(const std::string& mesh_file) {
    if (!is_initialized_) {
        return false;
    }
    
    std::string extension = std::filesystem::path(mesh_file).extension().string();
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    
    bool success = false;
    if (extension == ".obj") {
        success = load_mesh_obj(mesh_file);
    } else if (extension == ".fbx") {
        success = load_mesh_fbx(mesh_file);
    } else if (extension == ".gltf" || extension == ".glb") {
        success = load_mesh_gltf(mesh_file);
    } else {
        std::cerr << "Unsupported mesh format: " << extension << std::endl;
        return false;
    }
    
    if (success) {
        std::cout << "Successfully loaded mesh: " << mesh_file << std::endl;
        
        // Auto-fit camera if enabled
        if (config_.camera.auto_fit_bounds) {
            auto_fit_camera_to_mesh();
        }
    }
    
    return success;
}

bool MeshToSpritePipeline::load_animation_clip(const std::string& animation_name, const std::string& clip_file) {
    if (!is_initialized_) {
        return false;
    }
    
    std::string extension = std::filesystem::path(clip_file).extension().string();
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });

    bool success = false;
    if (extension == ".bvh") {
        success = load_animation_bvh(clip_file, animation_name);
    } else if (extension == ".fbx") {
        success = load_animation_fbx(clip_file, animation_name);
    } else if (extension == ".gltf" || extension == ".glb") {
        success = load_animation_gltf(clip_file, animation_name);
    } else {
        std::cerr << "Unsupported animation format: " << extension << std::endl;
        return false;
    }
    
    if (success) {
        std::cout << "Successfully loaded animation: " << animation_name << " from " << clip_file << std::endl;
    }
    
    return success;
}

void MeshToSpritePipeline::set_mesh_transform(const glm::mat4& transform) {
    for (auto& mesh : loaded_meshes_) {
        mesh.transform = transform;
    }
}

void MeshToSpritePipeline::add_material_override(const std::string& material_name, const std::string& texture_path) {
    material_overrides_[material_name] = texture_path;
}

void MeshToSpritePipeline::setup_camera(const CameraConfig& camera_config) {
    current_camera_ = camera_config;
    update_view_matrix();
    update_projection_matrix();
}

void MeshToSpritePipeline::setup_lighting(const LightingConfig& lighting_config) {
    current_lighting_ = lighting_config;
    apply_lighting();
}

void MeshToSpritePipeline::add_directional_capture(const std::string& name, const glm::vec3& camera_offset, 
                                                  float yaw, float pitch) {
    DirectionalCapture capture;
    capture.direction_name = name;
    capture.camera_offset = camera_offset;
    capture.yaw_rotation = yaw;
    capture.pitch_rotation = pitch;
    
    directional_captures_.push_back(capture);
}

bool MeshToSpritePipeline::capture_animation(const AnimationCapture& capture_config) {
    return capture_animation_as(capture_config, capture_config.animation_name);
}

bool MeshToSpritePipeline::capture_animation_as(const AnimationCapture& capture_config, const std::string& output_name) {
    if (!is_initialized_ || loaded_meshes_.empty()) {
        std::cerr << "Pipeline not initialized or no meshes loaded" << std::endl;
        return false;
    }
    
    auto clip_it = animation_clips_.find(capture_config.animation_name);
    if (clip_it == animation_clips_.end()) {
        std::cerr << "Animation not found: " << capture_config.animation_name << std::endl;
        return false;
    }
    
    is_processing_ = true;
    auto start_time = get_current_time();
    
    // Calculate total frames
    float duration = capture_config.end_time - capture_config.start_time;
    int total_frames = std::max(1, static_cast<int>(std::lround(duration * capture_config.fps)));
    if (duration <= 0.0f || capture_config.fps <= 0.0f) {
        std::cerr << "Invalid capture range for " << capture_config.animation_name << std::endl;
        is_processing_ = false;
        return false;
    }

    std::cout << "Capturing animation: " << capture_config.animation_name << " -> " << output_name << std::endl;
    std::cout << "Duration: " << duration << "s, FPS: " << capture_config.fps 
              << ", Total frames: " << total_frames << std::endl;
    
    std::vector<SpriteFrame> captured_frames;
    
    // Capture frames
    for (int frame = 0; frame < total_frames; ++frame) {
        float time = capture_config.start_time + (frame / capture_config.fps);
        
        // Update progress
        float progress = static_cast<float>(frame) / total_frames;
        if (progress_callback_) {
            progress_callback_(progress, "Rendering frame " + std::to_string(frame + 1) + "/" + std::to_string(total_frames));
        }
        
        // Render frame
        SpriteFrame sprite_frame = render_single_frame(capture_config.animation_name, time);
        sprite_frame.frame_index = frame;
        sprite_frame.timestamp = time;
        sprite_frame.is_key_frame = (frame % 8 == 0); // Every 8th frame is a keyframe
        
        captured_frames.push_back(sprite_frame);
        
        performance_stats_.frames_rendered++;
    }
    
    // Generate sprite sheet if enabled
    if (config_.generate_sprite_sheets) {
        SpriteSheet sheet = pack_frames_to_sheet(captured_frames, output_name);
        export_sprite_sheet(sheet);
        export_frames_json(sheet);
        
        performance_stats_.sprites_packed++;
    }
    
    // Generate animation definition
    if (config_.generate_animation_json) {
        AnimationDefinition anim_def;
        anim_def.animation_name = output_name;
        anim_def.duration = duration;
        anim_def.fps = capture_config.fps;
        anim_def.loop = capture_config.loop;
        
        for (size_t i = 0; i < captured_frames.size(); ++i) {
            anim_def.frame_sequence.push_back(static_cast<uint32_t>(i));
            anim_def.frame_times.push_back(captured_frames[i].timestamp);
        }
        
        export_animation_definition(anim_def);
        
        if (config_.generate_starbound_files) {
            export_starbound_animation(anim_def);
        }
        
        performance_stats_.animations_generated++;
    }
    
    is_processing_ = false;
    
    auto end_time = get_current_time();
    auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
    performance_stats_.total_render_time += duration_ms.count() / 1000.0;
    performance_stats_.avg_frame_render_time = performance_stats_.total_render_time / performance_stats_.frames_rendered;
    
    std::cout << "Animation capture completed in " << duration_ms.count() << "ms" << std::endl;
    std::cout << "Average frame time: " << std::fixed << std::setprecision(2) 
              << (duration_ms.count() / static_cast<double>(total_frames)) << "ms" << std::endl;
    
    return true;
}

bool MeshToSpritePipeline::capture_all_animations() {
    bool all_success = true;
    
    for (const auto& [anim_name, clip] : animation_clips_) {
        AnimationCapture capture_config;
        capture_config.animation_name = anim_name;
        capture_config.start_time = 0.0f;
        capture_config.end_time = clip.duration;
        capture_config.fps = 24.0f;
        capture_config.loop = clip.loop;
        
        if (!capture_animation(capture_config)) {
            all_success = false;
            std::cerr << "Failed to capture animation: " << anim_name << std::endl;
        }
    }
    
    return all_success;
}

bool MeshToSpritePipeline::capture_directional_set(const std::string& animation_name, 
                                                   const std::vector<DirectionalCapture>& directions) {
    auto clip_it = animation_clips_.find(animation_name);
    if (clip_it == animation_clips_.end()) {
        std::cerr << "Animation not found: " << animation_name << std::endl;
        return false;
    }
    const float clip_duration = clip_it->second.duration > 0.0f ? clip_it->second.duration : 1.0f;
    const bool clip_loop = clip_it->second.loop;

    if (directions.empty()) {
        AnimationCapture capture;
        capture.animation_name = animation_name;
        capture.start_time = 0.0f;
        capture.end_time = clip_duration;
        capture.fps = 24.0f;
        capture.loop = clip_loop;
        return capture_animation(capture);
    }

    // Save original camera configuration
    CameraConfig original_camera = current_camera_;
    
    bool all_success = true;
    
    for (const auto& direction : directions) {
        // Modify camera for this direction
        CameraConfig directional_camera = original_camera;
        directional_camera.position = original_camera.position + direction.camera_offset;
        
        // Apply yaw and pitch rotations
        glm::mat4 rotation = glm::rotate(glm::mat4(1.0f), glm::radians(direction.yaw_rotation), glm::vec3(0, 1, 0));
        rotation = glm::rotate(rotation, glm::radians(direction.pitch_rotation), glm::vec3(1, 0, 0));
        
        glm::vec4 rotated_pos = rotation * glm::vec4(directional_camera.position, 1.0f);
        directional_camera.position = glm::vec3(rotated_pos);
        
        setup_camera(directional_camera);
        
        // Capture animation for this direction
        AnimationCapture capture_config;
        capture_config.animation_name = animation_name;
        capture_config.start_time = 0.0f;
        capture_config.end_time = clip_duration;
        capture_config.fps = 24.0f;
        capture_config.loop = clip_loop;
        capture_config.captured_angles.push_back(direction.direction_name);

        const std::string output_name = animation_name + "_" + direction.direction_name;
        if (!capture_animation_as(capture_config, output_name)) {
            all_success = false;
            std::cerr << "Failed to capture directional animation: " << output_name << std::endl;
        }
    }
    
    // Restore original camera
    setup_camera(original_camera);
    
    return all_success;
}

std::vector<MeshToSpritePipeline::SpriteFrame> MeshToSpritePipeline::render_animation_frames(const std::string& animation_name) {
    std::vector<SpriteFrame> frames;
    
    auto clip_it = animation_clips_.find(animation_name);
    if (clip_it == animation_clips_.end()) {
        return frames;
    }
    
    const auto& clip = clip_it->second;
    
    // Render frames at 24 FPS
    float fps = 24.0f;
    int total_frames = static_cast<int>(clip.duration * fps);
    
    for (int frame = 0; frame < total_frames; ++frame) {
        float time = frame / fps;
        SpriteFrame sprite_frame = render_single_frame(animation_name, time);
        sprite_frame.frame_index = frame;
        sprite_frame.timestamp = time;
        frames.push_back(sprite_frame);
    }
    
    return frames;
}

MeshToSpritePipeline::SpriteFrame MeshToSpritePipeline::render_single_frame(const std::string& animation_name, 
                                                                           float time, const std::string& direction) {
    SpriteFrame frame;
    frame.size = glm::ivec2(config_.render.frame_width, config_.render.frame_height);
    frame.pivot = glm::vec2(0.5f, 0.5f); // Center pivot
    
    auto clip_it = animation_clips_.find(animation_name);
    if (clip_it == animation_clips_.end() || loaded_meshes_.empty()) {
        // Return empty frame
        frame.pixel_data.resize(config_.render.frame_width * config_.render.frame_height * 4, 0);
        return frame;
    }
    
    // Clear render target
    clear_render_target();
    
    // Render every loaded mesh with the clip's transform at this time
    const auto& clip = clip_it->second;
    for (const auto& mesh : loaded_meshes_) {
        render_mesh_with_animation(mesh, clip, time);
    }

    // Capture framebuffer
    capture_framebuffer(frame.pixel_data);

    // Generate filename
    frame.filename = sanitize_filename(animation_name) + (direction.empty() ? "" : "_" + sanitize_filename(direction)) +
                     "_" + std::to_string(static_cast<int>(time * 1000)) + ".png";
    
    return frame;
}

MeshToSpritePipeline::SpriteSheet MeshToSpritePipeline::pack_frames_to_sheet(const std::vector<SpriteFrame>& frames, 
                                                                            const std::string& sheet_name) {
    if (frames.empty()) {
        return SpriteSheet{};
    }
    
    auto start_time = get_current_time();
    
    SpriteSheet sheet;
    sheet.name = sheet_name;
    sheet.texture_filename = sanitize_filename(sheet_name) + ".png";

    const uint32_t padding = static_cast<uint32_t>(std::max(0.0f, config_.sprite_padding));
    const bool uniform = std::all_of(frames.begin(), frames.end(),
                                     [&](const SpriteFrame& f) { return f.size == frames[0].size; });

    // Uniform frames keep animation order (Starbound frame grids are read in order);
    // mixed sizes are packed largest-first.
    std::vector<SpriteFrame> ordered = frames;
    if (!uniform) {
        optimize_packing_order(ordered);
    }

    // Candidate sheet sizes, smallest area first
    std::vector<std::pair<uint32_t, uint32_t>> size_candidates;
    const uint32_t frame_width = static_cast<uint32_t>(std::max(1, frames[0].size.x));
    const uint32_t frame_height = static_cast<uint32_t>(std::max(1, frames[0].size.y));
    if (uniform && !config_.power_of_two_sheets) {
        // Exact grids: every column count, trimmed to the space actually used
        const uint32_t n = static_cast<uint32_t>(ordered.size());
        for (uint32_t cols = 1; cols <= n; ++cols) {
            const uint32_t rows = (n + cols - 1) / cols;
            const uint32_t w = cols * (frame_width + padding);
            const uint32_t h = rows * (frame_height + padding);
            if (w <= config_.max_sheet_width && h <= config_.max_sheet_height) {
                size_candidates.emplace_back(w, h);
            }
        }
    } else {
        for (uint32_t w = 64; w <= config_.max_sheet_width; w *= 2) {
            for (uint32_t h = 64; h <= config_.max_sheet_height; h *= 2) {
                size_candidates.emplace_back(w, h);
            }
        }
    }
    std::stable_sort(size_candidates.begin(), size_candidates.end(), [](const auto& a, const auto& b) {
        const uint64_t area_a = static_cast<uint64_t>(a.first) * a.second;
        const uint64_t area_b = static_cast<uint64_t>(b.first) * b.second;
        if (area_a != area_b) return area_a < area_b;
        // Prefer wider-than-tall sheets at equal area
        return a.first > b.first;
    });

    bool packed_successfully = false;
    for (const auto& [width, height] : size_candidates) {
        if (fits_in_sheet(ordered, width, height)) {
            sheet.width = width;
            sheet.height = height;
            sheet.frames = ordered;
            packed_successfully = true;
            break;
        }
    }

    if (!packed_successfully) {
        std::cerr << "Failed to pack " << frames.size() << " frames into a sheet of at most "
                  << config_.max_sheet_width << "x" << config_.max_sheet_height << std::endl;
        return sheet;
    }

    if (uniform) {
        // Grid layout
        const uint32_t frames_per_row = std::max<uint32_t>(1, sheet.width / (frame_width + padding));
        uint32_t current_row = 0;
        uint32_t current_col = 0;
        for (auto& frame : sheet.frames) {
            frame.position.x = static_cast<int>(current_col * (frame_width + padding));
            frame.position.y = static_cast<int>(current_row * (frame_height + padding));
            if (++current_col >= frames_per_row) {
                current_col = 0;
                current_row++;
            }
        }
    } else {
        // Binary-tree packing for mixed frame sizes
        PackingNode root;
        root.position = glm::ivec2(0);
        root.size = glm::ivec2(static_cast<int>(sheet.width), static_cast<int>(sheet.height));
        root.occupied = false;
        for (auto& frame : sheet.frames) {
            PackingNode* node = pack_rectangle(&root, frame.size + glm::ivec2(static_cast<int>(padding)));
            frame.position = node ? node->position : glm::ivec2(0);
        }
    }

    if (config_.optimize_empty_space && !config_.power_of_two_sheets) {
        // Trim unused space on the right / bottom
        int used_w = 0, used_h = 0;
        for (const auto& frame : sheet.frames) {
            used_w = std::max(used_w, frame.position.x + frame.size.x);
            used_h = std::max(used_h, frame.position.y + frame.size.y);
        }
        sheet.width = static_cast<uint32_t>(std::max(1, used_w));
        sheet.height = static_cast<uint32_t>(std::max(1, used_h));
    }
    
    // Create final packed texture
    sheet.packed_data.resize(sheet.width * sheet.height * 4, 0); // RGBA
    
    for (const auto& frame : sheet.frames) {
        // Copy frame data to sheet
        for (uint32_t y = 0; y < frame.size.y; ++y) {
            for (uint32_t x = 0; x < frame.size.x; ++x) {
                uint32_t src_index = (y * frame.size.x + x) * 4;
                uint32_t dst_x = frame.position.x + x;
                uint32_t dst_y = frame.position.y + y;
                uint32_t dst_index = (dst_y * sheet.width + dst_x) * 4;
                
                if (src_index + 3 < frame.pixel_data.size() && dst_index + 3 < sheet.packed_data.size()) {
                    sheet.packed_data[dst_index + 0] = frame.pixel_data[src_index + 0]; // R
                    sheet.packed_data[dst_index + 1] = frame.pixel_data[src_index + 1]; // G
                    sheet.packed_data[dst_index + 2] = frame.pixel_data[src_index + 2]; // B
                    sheet.packed_data[dst_index + 3] = frame.pixel_data[src_index + 3]; // A
                }
            }
        }
    }
    
    auto end_time = get_current_time();
    auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
    performance_stats_.total_packing_time += duration_ms.count() / 1000.0;
    performance_stats_.avg_packing_time = performance_stats_.total_packing_time / std::max(1ULL, performance_stats_.sprites_packed);
    
    std::cout << "Packed " << frames.size() << " frames into " << sheet.width << "x" << sheet.height 
              << " sprite sheet in " << duration_ms.count() << "ms" << std::endl;
    
    return sheet;
}

std::vector<MeshToSpritePipeline::SpriteSheet> MeshToSpritePipeline::pack_all_animations() {
    std::vector<SpriteSheet> sheets;
    
    for (const auto& [anim_name, clip] : animation_clips_) {
        auto frames = render_animation_frames(anim_name);
        if (!frames.empty()) {
            auto sheet = pack_frames_to_sheet(frames, anim_name);
            sheets.push_back(sheet);
        }
    }
    
    return sheets;
}

bool MeshToSpritePipeline::optimize_sprite_sheet(SpriteSheet& sheet) {
    // Remove duplicate frames
    std::vector<SpriteFrame> unique_frames;
    
    for (const auto& frame : sheet.frames) {
        bool is_duplicate = false;
        
        for (const auto& unique_frame : unique_frames) {
            if (frame.pixel_data == unique_frame.pixel_data) {
                is_duplicate = true;
                break;
            }
        }
        
        if (!is_duplicate) {
            unique_frames.push_back(frame);
        }
    }
    
    if (unique_frames.size() < sheet.frames.size()) {
        std::cout << "Removed " << (sheet.frames.size() - unique_frames.size()) 
                  << " duplicate frames" << std::endl;
        sheet.frames = unique_frames;
        return true;
    }
    
    return false;
}

bool MeshToSpritePipeline::export_sprite_sheet(const SpriteSheet& sheet) {
    if (sheet.packed_data.empty()) {
        return false;
    }
    
    std::string filepath = config_.output_directory + "/" + sheet.texture_filename;
    
    bool success = false;
    switch (config_.output_format) {
        case OutputFormat::PNG:
            success = save_image_png(filepath, sheet.packed_data, sheet.width, sheet.height);
            break;
        case OutputFormat::WEBP:
            success = save_image_webp(filepath, sheet.packed_data, sheet.width, sheet.height);
            break;
        case OutputFormat::TGA: {
            std::filesystem::path path(filepath);
            path.replace_extension(".tga");
            filepath = path.string();
            success = stbi_write_tga(filepath.c_str(), static_cast<int>(sheet.width), static_cast<int>(sheet.height),
                                     4, sheet.packed_data.data()) != 0;
            break;
        }
        case OutputFormat::BMP: {
            std::filesystem::path path(filepath);
            path.replace_extension(".bmp");
            filepath = path.string();
            success = stbi_write_bmp(filepath.c_str(), static_cast<int>(sheet.width), static_cast<int>(sheet.height),
                                     4, sheet.packed_data.data()) != 0;
            break;
        }
        default:
            success = save_image_png(filepath, sheet.packed_data, sheet.width, sheet.height);
            break;
    }
    
    if (success) {
        std::error_code ec;
        const auto written = std::filesystem::file_size(filepath, ec);
        performance_stats_.total_output_size += sheet.packed_data.size();
        performance_stats_.compressed_size += ec ? compress_image_data(sheet.packed_data).size()
                                                 : static_cast<size_t>(written);
        if (performance_stats_.total_output_size > 0) {
            performance_stats_.compression_ratio = static_cast<float>(performance_stats_.compressed_size) /
                                                   static_cast<float>(performance_stats_.total_output_size);
        }
        std::cout << "Exported sprite sheet: " << filepath << std::endl;
    }
    
    return success;
}

bool MeshToSpritePipeline::export_frames_json(const SpriteSheet& sheet) {
    std::string json_content = generate_frames_json(sheet);
    std::string filepath = config_.output_directory + "/" + sheet.name + ".frames";
    
    std::ofstream file(filepath);
    if (file.is_open()) {
        file << json_content;
        file.close();
        std::cout << "Exported frames JSON: " << filepath << std::endl;
        return true;
    }
    
    return false;
}

bool MeshToSpritePipeline::export_animation_definition(const AnimationDefinition& animation) {
    std::string json_content = generate_animation_json(animation);
    std::string filepath = config_.output_directory + "/" + animation.animation_name + ".animation";
    
    std::ofstream file(filepath);
    if (file.is_open()) {
        file << json_content;
        file.close();
        std::cout << "Exported animation definition: " << filepath << std::endl;
        return true;
    }
    
    return false;
}

bool MeshToSpritePipeline::export_starbound_animation(const AnimationDefinition& animation) {
    std::string json_content = generate_starbound_animation_json(animation);
    std::string filepath = config_.output_directory + "/" + animation.animation_name + ".animation";
    
    std::ofstream file(filepath);
    if (file.is_open()) {
        file << json_content;
        file.close();
        std::cout << "Exported Starbound animation: " << filepath << std::endl;
        return true;
    }
    
    return false;
}

bool MeshToSpritePipeline::export_starbound_projectile(const std::string& projectile_name, 
                                                      const std::vector<AnimationDefinition>& animations) {
    std::string json_content = generate_starbound_projectile_json(projectile_name, animations);
    std::string filepath = config_.output_directory + "/" + projectile_name + ".projectile";
    
    std::ofstream file(filepath);
    if (file.is_open()) {
        file << json_content;
        file.close();
        std::cout << "Exported Starbound projectile: " << filepath << std::endl;
        return true;
    }
    
    return false;
}

bool MeshToSpritePipeline::process_batch(const std::vector<std::string>& mesh_files,
                                        const std::vector<AnimationCapture>& captures) {
    bool all_success = true;
    
    for (const auto& mesh_file : mesh_files) {
        if (!load_mesh(mesh_file)) {
            all_success = false;
            continue;
        }
        
        for (const auto& capture : captures) {
            if (!capture_animation(capture)) {
                all_success = false;
            }
        }
        
        // Clear meshes for next iteration
        loaded_meshes_.clear();
    }
    
    return all_success;
}

void MeshToSpritePipeline::set_progress_callback(std::function<void(float, const std::string&)> callback) {
    progress_callback_ = callback;
}

std::vector<std::string> MeshToSpritePipeline::get_available_animations() const {
    std::vector<std::string> names;
    for (const auto& [name, clip] : animation_clips_) {
        names.push_back(name);
    }
    return names;
}

std::vector<std::string> MeshToSpritePipeline::get_loaded_meshes() const {
    std::vector<std::string> names;
    for (size_t i = 0; i < loaded_meshes_.size(); ++i) {
        names.push_back("mesh_" + std::to_string(i));
    }
    return names;
}

glm::vec3 MeshToSpritePipeline::calculate_mesh_bounds() const {
    if (loaded_meshes_.empty()) {
        return glm::vec3(0);
    }
    
    glm::vec3 min_bounds(FLT_MAX);
    glm::vec3 max_bounds(-FLT_MAX);
    
    for (const auto& mesh : loaded_meshes_) {
        for (const auto& vertex : mesh.vertices) {
            min_bounds = glm::min(min_bounds, vertex);
            max_bounds = glm::max(max_bounds, vertex);
        }
    }
    
    return max_bounds - min_bounds;
}

void MeshToSpritePipeline::auto_fit_camera_to_mesh() {
    glm::vec3 bounds = calculate_mesh_bounds();
    float max_dimension = std::max({bounds.x, bounds.y, bounds.z});
    
    if (current_camera_.type == CameraType::ORTHOGRAPHIC) {
        current_camera_.ortho_size = max_dimension * 1.2f; // 20% padding
    } else {
        // Adjust distance for perspective camera
        float distance = max_dimension * 2.0f;
        glm::vec3 direction = glm::normalize(current_camera_.target - current_camera_.position);
        current_camera_.position = current_camera_.target - direction * distance;
    }
    
    update_view_matrix();
    update_projection_matrix();
}

void MeshToSpritePipeline::reset_performance_stats() {
    performance_stats_ = PerformanceStats{};
}

// Private helper implementations

namespace {

// Supersampling factor used to honour RenderConfig::samples (4 samples -> 2x2).
uint32_t supersample_factor(uint32_t samples) {
    if (samples <= 1) return 1;
    return std::max<uint32_t>(1, static_cast<uint32_t>(std::lround(std::sqrt(static_cast<double>(samples)))));
}

uint8_t to_byte(float v) {
    return static_cast<uint8_t>(std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f));
}

void plot_line(std::vector<uint8_t>& color, uint32_t width, uint32_t height,
               glm::vec2 a, glm::vec2 b, const glm::u8vec4& rgba) {
    int x0 = static_cast<int>(std::floor(a.x)), y0 = static_cast<int>(std::floor(a.y));
    const int x1 = static_cast<int>(std::floor(b.x)), y1 = static_cast<int>(std::floor(b.y));
    const int dx = std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    const int dy = -std::abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (int guard = 0; guard < 1 << 16; ++guard) {
        if (x0 >= 0 && y0 >= 0 && x0 < static_cast<int>(width) && y0 < static_cast<int>(height)) {
            const size_t i = (static_cast<size_t>(y0) * width + x0) * 4;
            color[i + 0] = rgba.r; color[i + 1] = rgba.g; color[i + 2] = rgba.b; color[i + 3] = rgba.a;
        }
        if (x0 == x1 && y0 == y1) break;
        const int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

} // namespace

bool MeshToSpritePipeline::initialize_opengl() {
    // No GL context is available to the plugin offscreen: OpenGL captures are produced by the
    // built-in software rasterizer, which follows the same GL conventions (RH, CCW, [0,1] depth).
    std::cout << "OpenGL backend requested: rendering with the software rasterizer" << std::endl;
    render_context_ = RenderContext{};
    return true;
}

bool MeshToSpritePipeline::initialize_directx11() {
    std::cout << "DirectX11 backend requested: rendering with the software rasterizer" << std::endl;
    render_context_ = RenderContext{};
    return true;
}

void MeshToSpritePipeline::cleanup_opengl() {
    render_context_.color_buffer.clear();
    render_context_.color_buffer.shrink_to_fit();
    render_context_.depth_buffer.clear();
    render_context_.depth_buffer.shrink_to_fit();
    texture_cache_.clear();
}

void MeshToSpritePipeline::cleanup_directx11() {
    cleanup_opengl();
}

bool MeshToSpritePipeline::load_mesh_obj(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        return false;
    }

    // Raw OBJ streams
    std::vector<glm::vec3> positions;
    std::vector<glm::vec3> normals;
    std::vector<glm::vec2> uvs;

    MeshData mesh;
    // Unique (position, uv, normal) corners -> output vertex index
    std::unordered_map<std::string, uint32_t> corner_lookup;

    auto resolve = [](int index, size_t count) -> int {
        // OBJ indices are 1-based; negative indices count back from the end
        if (index > 0) return index - 1;
        if (index < 0) return static_cast<int>(count) + index;
        return -1;
    };

    std::string line;
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string type;
        iss >> type;

        if (type == "v") {
            float x = 0, y = 0, z = 0;
            iss >> x >> y >> z;
            positions.emplace_back(x, y, z);
        } else if (type == "vn") {
            float x = 0, y = 0, z = 0;
            iss >> x >> y >> z;
            normals.emplace_back(x, y, z);
        } else if (type == "vt") {
            float u = 0, v = 0;
            iss >> u >> v;
            uvs.emplace_back(u, v);
        } else if (type == "usemtl") {
            iss >> mesh.material_name;
        } else if (type == "f") {
            std::vector<uint32_t> polygon;
            std::string corner;
            while (iss >> corner) {
                int vi = 0, ti = 0, ni = 0;
                const size_t s1 = corner.find('/');
                try {
                    vi = std::stoi(corner.substr(0, s1));
                    if (s1 != std::string::npos) {
                        const size_t s2 = corner.find('/', s1 + 1);
                        const std::string t = corner.substr(s1 + 1, s2 == std::string::npos ? std::string::npos : s2 - s1 - 1);
                        if (!t.empty()) ti = std::stoi(t);
                        if (s2 != std::string::npos && s2 + 1 < corner.size()) ni = std::stoi(corner.substr(s2 + 1));
                    }
                } catch (const std::exception&) {
                    continue;
                }
                const int p = resolve(vi, positions.size());
                if (p < 0 || p >= static_cast<int>(positions.size())) continue;
                const int t = resolve(ti, uvs.size());
                const int n = resolve(ni, normals.size());

                const std::string key = std::to_string(p) + "/" + std::to_string(t) + "/" + std::to_string(n);
                auto it = corner_lookup.find(key);
                if (it == corner_lookup.end()) {
                    const uint32_t index = static_cast<uint32_t>(mesh.vertices.size());
                    mesh.vertices.push_back(positions[static_cast<size_t>(p)]);
                    mesh.uvs.push_back((t >= 0 && t < static_cast<int>(uvs.size())) ? uvs[static_cast<size_t>(t)] : glm::vec2(0.0f));
                    mesh.normals.push_back((n >= 0 && n < static_cast<int>(normals.size())) ? normals[static_cast<size_t>(n)] : glm::vec3(0.0f));
                    it = corner_lookup.emplace(key, index).first;
                }
                polygon.push_back(it->second);
            }
            // Fan-triangulate polygons
            for (size_t i = 1; i + 1 < polygon.size(); ++i) {
                mesh.indices.push_back(polygon[0]);
                mesh.indices.push_back(polygon[i]);
                mesh.indices.push_back(polygon[i + 1]);
            }
        }
    }

    file.close();

    if (mesh.vertices.empty() || mesh.indices.empty()) {
        std::cerr << "OBJ file contains no faces: " << filename << std::endl;
        return false;
    }

    // Generate smooth normals for vertices that had none
    bool missing_normals = false;
    for (const auto& n : mesh.normals) {
        if (glm::dot(n, n) < 1e-12f) { missing_normals = true; break; }
    }
    if (missing_normals) {
        std::vector<glm::vec3> accum(mesh.vertices.size(), glm::vec3(0.0f));
        for (size_t i = 0; i + 2 < mesh.indices.size(); i += 3) {
            const glm::vec3& a = mesh.vertices[mesh.indices[i]];
            const glm::vec3& b = mesh.vertices[mesh.indices[i + 1]];
            const glm::vec3& c = mesh.vertices[mesh.indices[i + 2]];
            const glm::vec3 face = glm::cross(b - a, c - a);  // area weighted
            accum[mesh.indices[i]] += face;
            accum[mesh.indices[i + 1]] += face;
            accum[mesh.indices[i + 2]] += face;
        }
        for (size_t i = 0; i < mesh.normals.size(); ++i) {
            if (glm::dot(mesh.normals[i], mesh.normals[i]) < 1e-12f) {
                const float len = glm::length(accum[i]);
                mesh.normals[i] = len > 0.0f ? accum[i] / len : glm::vec3(0, 1, 0);
            }
        }
    }

    loaded_meshes_.push_back(std::move(mesh));
    return true;
}

bool MeshToSpritePipeline::load_mesh_fbx(const std::string& filename) {
    // FBX needs the Autodesk SDK or Assimp, neither of which is vendored in this build.
    std::cerr << "FBX meshes are not supported in this build (convert to .obj): " << filename << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_mesh_gltf(const std::string& filename) {
    // glTF needs a glTF/Assimp importer, which is not vendored in this build.
    std::cerr << "glTF meshes are not supported in this build (convert to .obj): " << filename << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_animation_bvh(const std::string& filename, const std::string& animation_name) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Failed to open BVH file: " << filename << std::endl;
        return false;
    }

    // HIERARCHY: collect the channel layout; only the root joint's channels drive the
    // model matrix (the pipeline animates the mesh as a rigid body).
    std::vector<std::string> root_channels;
    size_t total_channels = 0;
    bool seen_root = false;
    std::string token;
    while (file >> token) {
        if (token == "ROOT") {
            seen_root = true;
        } else if (token == "CHANNELS") {
            size_t count = 0;
            file >> count;
            const bool is_root_channels = seen_root && root_channels.empty() && total_channels == 0;
            for (size_t i = 0; i < count; ++i) {
                std::string channel;
                file >> channel;
                if (is_root_channels) root_channels.push_back(channel);
            }
            total_channels += count;
        } else if (token == "MOTION") {
            break;
        }
    }
    if (!seen_root || total_channels == 0) {
        std::cerr << "BVH file has no ROOT joint / channels: " << filename << std::endl;
        return false;
    }

    // MOTION header
    size_t frame_count = 0;
    float frame_time = 1.0f / 24.0f;
    std::string line;
    while (std::getline(file, line)) {
        if (line.find("Frames:") != std::string::npos) {
            frame_count = static_cast<size_t>(std::stoul(line.substr(line.find(':') + 1)));
        } else if (line.find("Frame Time:") != std::string::npos) {
            frame_time = std::stof(line.substr(line.find(':') + 1));
            break;
        }
    }
    if (frame_count == 0 || frame_time <= 0.0f) {
        std::cerr << "BVH file has no motion frames: " << filename << std::endl;
        return false;
    }

    AnimationClip clip;
    clip.name = animation_name;
    clip.loop = true;
    clip.bone_matrices.reserve(frame_count);
    clip.keyframe_times.reserve(frame_count);

    glm::vec3 first_position(0.0f);
    std::vector<float> values(total_channels);
    for (size_t frame = 0; frame < frame_count; ++frame) {
        for (size_t c = 0; c < total_channels; ++c) {
            if (!(file >> values[c])) {
                std::cerr << "BVH motion data truncated at frame " << frame << ": " << filename << std::endl;
                if (frame == 0) return false;
                frame_count = frame;
                break;
            }
        }
        if (clip.bone_matrices.size() == frame_count) break;

        glm::vec3 position(0.0f);
        glm::mat4 rotation(1.0f);
        for (size_t c = 0; c < root_channels.size(); ++c) {
            const std::string& ch = root_channels[c];
            const float v = values[c];
            if (ch == "Xposition") position.x = v;
            else if (ch == "Yposition") position.y = v;
            else if (ch == "Zposition") position.z = v;
            else if (ch == "Xrotation") rotation = rotation * glm::rotate(glm::mat4(1.0f), glm::radians(v), glm::vec3(1, 0, 0));
            else if (ch == "Yrotation") rotation = rotation * glm::rotate(glm::mat4(1.0f), glm::radians(v), glm::vec3(0, 1, 0));
            else if (ch == "Zrotation") rotation = rotation * glm::rotate(glm::mat4(1.0f), glm::radians(v), glm::vec3(0, 0, 1));
        }
        if (frame == 0) first_position = position;
        // Root motion relative to the first frame keeps the mesh centred in the capture
        clip.bone_matrices.push_back(glm::translate(glm::mat4(1.0f), position - first_position) * rotation);
        clip.keyframe_times.push_back(static_cast<float>(frame) * frame_time);
    }
    clip.duration = static_cast<float>(clip.bone_matrices.size()) * frame_time;

    animation_clips_[clip.name] = std::move(clip);
    return true;
}

bool MeshToSpritePipeline::load_animation_fbx(const std::string& filename, const std::string& animation_name) {
    std::cerr << "FBX animations are not supported in this build (convert to .bvh): "
              << filename << " (" << animation_name << ")" << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_animation_gltf(const std::string& filename, const std::string& animation_name) {
    std::cerr << "glTF animations are not supported in this build (convert to .bvh): "
              << filename << " (" << animation_name << ")" << std::endl;
    return false;
}

void MeshToSpritePipeline::setup_render_target() {
    const uint32_t ss = supersample_factor(config_.render.samples);
    render_context_.viewport_width = std::max<uint32_t>(1, config_.render.frame_width) * ss;
    render_context_.viewport_height = std::max<uint32_t>(1, config_.render.frame_height) * ss;
    const size_t pixels = static_cast<size_t>(render_context_.viewport_width) * render_context_.viewport_height;
    render_context_.color_buffer.assign(pixels * 4, 0);
    render_context_.depth_buffer.assign(pixels, std::numeric_limits<float>::infinity());
}

void MeshToSpritePipeline::clear_render_target() {
    const uint32_t ss = supersample_factor(config_.render.samples);
    if (render_context_.viewport_width != config_.render.frame_width * ss ||
        render_context_.viewport_height != config_.render.frame_height * ss ||
        render_context_.color_buffer.empty()) {
        setup_render_target();
    }
    const glm::vec4& bg = config_.render.background_color;
    const uint8_t rgba[4] = { to_byte(bg.r), to_byte(bg.g), to_byte(bg.b),
                              config_.render.enable_alpha ? to_byte(bg.a) : static_cast<uint8_t>(255) };
    for (size_t i = 0; i + 3 < render_context_.color_buffer.size(); i += 4) {
        std::memcpy(&render_context_.color_buffer[i], rgba, 4);
    }
    std::fill(render_context_.depth_buffer.begin(), render_context_.depth_buffer.end(),
              std::numeric_limits<float>::infinity());
}

const MeshToSpritePipeline::TextureData* MeshToSpritePipeline::get_material_texture(const std::string& material_name) {
    auto override_it = material_overrides_.find(material_name);
    if (override_it == material_overrides_.end()) {
        return nullptr;
    }
    auto cached = texture_cache_.find(override_it->second);
    if (cached != texture_cache_.end()) {
        return cached->second.pixels.empty() ? nullptr : &cached->second;
    }
    TextureData tex;
    int channels = 0;
    stbi_uc* data = stbi_load(override_it->second.c_str(), &tex.width, &tex.height, &channels, 4);
    if (data) {
        tex.pixels.assign(data, data + static_cast<size_t>(tex.width) * tex.height * 4);
        stbi_image_free(data);
    } else {
        std::cerr << "Failed to load material texture: " << override_it->second << std::endl;
    }
    auto inserted = texture_cache_.emplace(override_it->second, std::move(tex)).first;
    return inserted->second.pixels.empty() ? nullptr : &inserted->second;
}

void MeshToSpritePipeline::render_mesh_with_animation(const MeshData& mesh, const AnimationClip& clip, float time) {
    const uint32_t W = render_context_.viewport_width;
    const uint32_t H = render_context_.viewport_height;
    if (W == 0 || H == 0 || mesh.vertices.empty()) {
        return;
    }

    const glm::mat4 model = calculate_model_matrix(clip, time) * mesh.transform;
    const glm::mat4 mvp = projection_matrix_ * view_matrix_ * model;
    const glm::mat3 normal_matrix = glm::transpose(glm::inverse(glm::mat3(model)));
    const glm::vec3 eye = current_camera_.position;
    const TextureData* texture = get_material_texture(mesh.material_name);
    const LightingConfig& L = current_lighting_;

    // Transform all vertices once
    struct ScreenVertex { glm::vec3 screen; float inv_w; glm::vec3 world; glm::vec3 normal; glm::vec2 uv; bool valid; };
    std::vector<ScreenVertex> sv(mesh.vertices.size());
    for (size_t i = 0; i < mesh.vertices.size(); ++i) {
        const glm::vec4 clip_pos = mvp * glm::vec4(mesh.vertices[i], 1.0f);
        ScreenVertex& v = sv[i];
        v.valid = clip_pos.w > 1e-6f;
        const float inv_w = v.valid ? 1.0f / clip_pos.w : 0.0f;
        const glm::vec3 ndc = glm::vec3(clip_pos) * inv_w;
        v.screen = glm::vec3((ndc.x * 0.5f + 0.5f) * W, (1.0f - (ndc.y * 0.5f + 0.5f)) * H, ndc.z);
        v.inv_w = inv_w;
        v.world = glm::vec3(model * glm::vec4(mesh.vertices[i], 1.0f));
        v.normal = i < mesh.normals.size() ? glm::normalize(normal_matrix * mesh.normals[i]) : glm::vec3(0, 1, 0);
        v.uv = i < mesh.uvs.size() ? mesh.uvs[i] : glm::vec2(0.0f);
    }

    auto shade = [&](const glm::vec3& world, glm::vec3 n, const glm::vec2& uv) -> glm::vec4 {
        glm::vec4 base(0.8f, 0.8f, 0.8f, 1.0f);
        if (texture) {
            const float u = uv.x - std::floor(uv.x);
            const float v = 1.0f - (uv.y - std::floor(uv.y));  // OBJ UV origin is bottom-left
            const int tx = std::clamp(static_cast<int>(u * texture->width), 0, texture->width - 1);
            const int ty = std::clamp(static_cast<int>(v * texture->height), 0, texture->height - 1);
            const uint8_t* p = &texture->pixels[(static_cast<size_t>(ty) * texture->width + tx) * 4];
            base = glm::vec4(p[0], p[1], p[2], p[3]) / 255.0f;
        }
        if (L.mode == LightingMode::NONE) {
            return base;
        }
        const glm::vec3 to_eye = glm::normalize(eye - world);
        if (glm::dot(n, to_eye) < 0.0f) n = -n;  // two-sided lighting
        glm::vec3 light = L.ambient_color;
        if (L.mode == LightingMode::DIRECTIONAL || L.mode == LightingMode::FULL_PBR) {
            const glm::vec3 ldir = -L.directional_direction;  // normalised by apply_lighting()
            const float ndl = std::max(glm::dot(n, ldir), 0.0f);
            light += L.directional_color * (L.directional_intensity * ndl);
            if (L.mode == LightingMode::FULL_PBR && ndl > 0.0f) {
                const glm::vec3 h = glm::normalize(ldir + to_eye);
                light += L.directional_color * (L.directional_intensity * 0.25f * std::pow(std::max(glm::dot(n, h), 0.0f), 32.0f));
            }
        }
        if (L.mode == LightingMode::POINT_LIGHT || L.mode == LightingMode::FULL_PBR) {
            for (size_t i = 0; i < L.point_light_positions.size(); ++i) {
                const glm::vec3 d = L.point_light_positions[i] - world;
                const float dist2 = glm::dot(d, d);
                const glm::vec3 ldir = dist2 > 0.0f ? d / std::sqrt(dist2) : glm::vec3(0, 1, 0);
                const float ndl = std::max(glm::dot(n, ldir), 0.0f);
                const float atten = 1.0f / (1.0f + 0.1f * dist2);
                light += L.point_light_colors[i] * (L.point_light_intensities[i] * ndl * atten);
            }
        }
        return glm::vec4(glm::vec3(base) * light, base.a);
    };

    auto& color = render_context_.color_buffer;
    auto& depth = render_context_.depth_buffer;
    const bool depth_test = config_.render.enable_depth_test;
    const size_t index_count = mesh.indices.empty() ? mesh.vertices.size() : mesh.indices.size();
    auto vertex_index = [&](size_t i) -> size_t { return mesh.indices.empty() ? i : mesh.indices[i]; };

    for (size_t t = 0; t + 2 < index_count; t += 3) {
        const size_t i0 = vertex_index(t), i1 = vertex_index(t + 1), i2 = vertex_index(t + 2);
        if (i0 >= sv.size() || i1 >= sv.size() || i2 >= sv.size()) continue;
        const ScreenVertex& a = sv[i0];
        const ScreenVertex& b = sv[i1];
        const ScreenVertex& c = sv[i2];
        if (!a.valid || !b.valid || !c.valid) continue;  // behind the camera
        if ((a.screen.z < 0.0f && b.screen.z < 0.0f && c.screen.z < 0.0f) ||
            (a.screen.z > 1.0f && b.screen.z > 1.0f && c.screen.z > 1.0f)) continue;  // outside depth range

        const glm::vec3 face_normal = glm::normalize(glm::cross(b.world - a.world, c.world - a.world));

        if (config_.render.render_wireframe) {
            const glm::vec4 shaded = shade((a.world + b.world + c.world) / 3.0f, face_normal, a.uv);
            const glm::u8vec4 rgba(to_byte(shaded.r), to_byte(shaded.g), to_byte(shaded.b), 255);
            plot_line(color, W, H, glm::vec2(a.screen), glm::vec2(b.screen), rgba);
            plot_line(color, W, H, glm::vec2(b.screen), glm::vec2(c.screen), rgba);
            plot_line(color, W, H, glm::vec2(c.screen), glm::vec2(a.screen), rgba);
            continue;
        }

        const float area = (b.screen.x - a.screen.x) * (c.screen.y - a.screen.y) -
                           (b.screen.y - a.screen.y) * (c.screen.x - a.screen.x);
        if (std::fabs(area) < 1e-8f) continue;

        const int min_x = std::max(0, static_cast<int>(std::floor(std::min({a.screen.x, b.screen.x, c.screen.x}))));
        const int max_x = std::min(static_cast<int>(W) - 1, static_cast<int>(std::ceil(std::max({a.screen.x, b.screen.x, c.screen.x}))));
        const int min_y = std::max(0, static_cast<int>(std::floor(std::min({a.screen.y, b.screen.y, c.screen.y}))));
        const int max_y = std::min(static_cast<int>(H) - 1, static_cast<int>(std::ceil(std::max({a.screen.y, b.screen.y, c.screen.y}))));

        for (int y = min_y; y <= max_y; ++y) {
            for (int x = min_x; x <= max_x; ++x) {
                const float px = x + 0.5f, py = y + 0.5f;
                float w0 = (b.screen.x - px) * (c.screen.y - py) - (b.screen.y - py) * (c.screen.x - px);
                float w1 = (c.screen.x - px) * (a.screen.y - py) - (c.screen.y - py) * (a.screen.x - px);
                float w2 = (a.screen.x - px) * (b.screen.y - py) - (a.screen.y - py) * (b.screen.x - px);
                w0 /= area; w1 /= area; w2 /= area;
                if (w0 < 0.0f || w1 < 0.0f || w2 < 0.0f) continue;

                const float z = w0 * a.screen.z + w1 * b.screen.z + w2 * c.screen.z;
                if (z < 0.0f || z > 1.0f) continue;
                const size_t pixel = static_cast<size_t>(y) * W + x;
                if (depth_test && z >= depth[pixel]) continue;

                // Perspective-correct attribute interpolation
                const float pw0 = w0 * a.inv_w, pw1 = w1 * b.inv_w, pw2 = w2 * c.inv_w;
                const float psum = pw0 + pw1 + pw2;
                if (psum <= 0.0f) continue;
                const glm::vec3 world = (a.world * pw0 + b.world * pw1 + c.world * pw2) / psum;
                const glm::vec2 uv = (a.uv * pw0 + b.uv * pw1 + c.uv * pw2) / psum;
                glm::vec3 n = face_normal;
                if (normal_mapping_enabled_) {
                    const glm::vec3 interpolated = (a.normal * pw0 + b.normal * pw1 + c.normal * pw2) / psum;
                    const float len = glm::length(interpolated);
                    if (len > 0.0f) n = interpolated / len;
                }

                const glm::vec4 shaded = shade(world, n, uv);
                if (shaded.a <= 0.0f) continue;  // alpha-tested texels
                depth[pixel] = z;
                uint8_t* dst = &color[pixel * 4];
                dst[0] = to_byte(shaded.r);
                dst[1] = to_byte(shaded.g);
                dst[2] = to_byte(shaded.b);
                dst[3] = to_byte(shaded.a);
            }
        }
    }

    // Debug overlays
    if (config_.render.render_normals) {
        const float length = std::max(0.05f, calculate_bounds_radius(mesh) * 0.1f);
        const glm::mat4 vp = projection_matrix_ * view_matrix_;
        for (size_t i = 0; i < sv.size(); ++i) {
            const glm::vec4 tip = vp * glm::vec4(sv[i].world + sv[i].normal * length, 1.0f);
            if (!sv[i].valid || tip.w <= 1e-6f) continue;
            const glm::vec3 ndc = glm::vec3(tip) / tip.w;
            const glm::vec2 tip_screen((ndc.x * 0.5f + 0.5f) * W, (1.0f - (ndc.y * 0.5f + 0.5f)) * H);
            plot_line(color, W, H, glm::vec2(sv[i].screen), tip_screen, glm::u8vec4(0, 128, 255, 255));
        }
    }
    if (config_.render.render_bounds) {
        glm::vec3 mn(FLT_MAX), mx(-FLT_MAX);
        for (const auto& v : mesh.vertices) { mn = glm::min(mn, v); mx = glm::max(mx, v); }
        glm::vec2 corners[8];
        bool ok = true;
        for (int i = 0; i < 8; ++i) {
            const glm::vec3 p((i & 1) ? mx.x : mn.x, (i & 2) ? mx.y : mn.y, (i & 4) ? mx.z : mn.z);
            const glm::vec4 cp = mvp * glm::vec4(p, 1.0f);
            if (cp.w <= 1e-6f) { ok = false; break; }
            const glm::vec3 ndc = glm::vec3(cp) / cp.w;
            corners[i] = glm::vec2((ndc.x * 0.5f + 0.5f) * W, (1.0f - (ndc.y * 0.5f + 0.5f)) * H);
        }
        if (ok) {
            const int edges[12][2] = { {0,1},{2,3},{4,5},{6,7},{0,2},{1,3},{4,6},{5,7},{0,4},{1,5},{2,6},{3,7} };
            for (const auto& e : edges) {
                plot_line(color, W, H, corners[e[0]], corners[e[1]], glm::u8vec4(255, 255, 0, 255));
            }
        }
    }
}

void MeshToSpritePipeline::apply_lighting() {
    // Normalise the lighting configuration once so the rasterizer can use it directly.
    LightingConfig& L = current_lighting_;
    const float len = glm::length(L.directional_direction);
    L.directional_direction = len > 0.0f ? L.directional_direction / len : glm::vec3(0, -1, 0);
    const size_t lights = L.point_light_positions.size();
    L.point_light_colors.resize(lights, glm::vec3(1.0f));
    L.point_light_intensities.resize(lights, 1.0f);
}

void MeshToSpritePipeline::apply_post_process() {
    const uint32_t W = render_context_.viewport_width;
    const uint32_t H = render_context_.viewport_height;
    auto& color = render_context_.color_buffer;
    auto& depth = render_context_.depth_buffer;
    if (W == 0 || H == 0 || color.empty()) return;

    if (ambient_occlusion_enabled_) {
        // Screen-space AO: darken pixels whose neighbours are noticeably closer to the camera
        const std::vector<float> d = depth;
        const int radius = static_cast<int>(std::max<uint32_t>(1, W / 64));
        for (uint32_t y = 0; y < H; ++y) {
            for (uint32_t x = 0; x < W; ++x) {
                const size_t i = static_cast<size_t>(y) * W + x;
                if (!std::isfinite(d[i])) continue;
                int occluders = 0, samples = 0;
                for (int oy = -radius; oy <= radius; oy += radius) {
                    for (int ox = -radius; ox <= radius; ox += radius) {
                        if (ox == 0 && oy == 0) continue;
                        const int sx = static_cast<int>(x) + ox, sy = static_cast<int>(y) + oy;
                        if (sx < 0 || sy < 0 || sx >= static_cast<int>(W) || sy >= static_cast<int>(H)) continue;
                        ++samples;
                        const float nd = d[static_cast<size_t>(sy) * W + sx];
                        if (std::isfinite(nd) && nd < d[i] - 0.002f) ++occluders;
                    }
                }
                if (samples > 0 && occluders > 0) {
                    const float factor = 1.0f - 0.5f * static_cast<float>(occluders) / samples;
                    for (int ch = 0; ch < 3; ++ch) {
                        color[i * 4 + ch] = static_cast<uint8_t>(color[i * 4 + ch] * factor);
                    }
                }
            }
        }
    }

    for (const auto& [effect, shader] : post_process_effects_) {
        if (effect == "grayscale") {
            for (size_t i = 0; i + 3 < color.size(); i += 4) {
                const uint8_t g = static_cast<uint8_t>((color[i] * 77 + color[i + 1] * 150 + color[i + 2] * 29) >> 8);
                color[i] = color[i + 1] = color[i + 2] = g;
            }
        } else if (effect == "invert") {
            for (size_t i = 0; i + 3 < color.size(); i += 4) {
                color[i] = 255 - color[i]; color[i + 1] = 255 - color[i + 1]; color[i + 2] = 255 - color[i + 2];
            }
        } else if (effect == "outline") {
            // 1px dark outline around opaque coverage (classic sprite look)
            const std::vector<uint8_t> src = color;
            for (uint32_t y = 0; y < H; ++y) {
                for (uint32_t x = 0; x < W; ++x) {
                    const size_t i = (static_cast<size_t>(y) * W + x) * 4;
                    if (src[i + 3] != 0) continue;
                    bool edge = false;
                    for (int oy = -1; oy <= 1 && !edge; ++oy) {
                        for (int ox = -1; ox <= 1 && !edge; ++ox) {
                            const int sx = static_cast<int>(x) + ox, sy = static_cast<int>(y) + oy;
                            if (sx < 0 || sy < 0 || sx >= static_cast<int>(W) || sy >= static_cast<int>(H)) continue;
                            edge = src[(static_cast<size_t>(sy) * W + sx) * 4 + 3] != 0;
                        }
                    }
                    if (edge) { color[i] = 16; color[i + 1] = 16; color[i + 2] = 24; color[i + 3] = 255; }
                }
            }
        }
    }
}

void MeshToSpritePipeline::capture_framebuffer(std::vector<uint8_t>& pixel_data) {
    apply_post_process();

    // Resolve the supersampled colour target down to the output frame size (box filter)
    const uint32_t width = config_.render.frame_width;
    const uint32_t height = config_.render.frame_height;
    const uint32_t ss = supersample_factor(config_.render.samples);
    const uint32_t W = render_context_.viewport_width;
    pixel_data.assign(static_cast<size_t>(width) * height * 4, 0);
    if (render_context_.color_buffer.empty() || W != width * ss) {
        return;
    }
    const auto& src = render_context_.color_buffer;
    const float inv = 1.0f / static_cast<float>(ss * ss);
    for (uint32_t y = 0; y < height; ++y) {
        for (uint32_t x = 0; x < width; ++x) {
            float acc[4] = { 0, 0, 0, 0 };
            for (uint32_t sy = 0; sy < ss; ++sy) {
                for (uint32_t sx = 0; sx < ss; ++sx) {
                    const size_t i = ((static_cast<size_t>(y) * ss + sy) * W + (static_cast<size_t>(x) * ss + sx)) * 4;
                    const float a = src[i + 3];
                    // Premultiply so transparent samples do not darken edges
                    acc[0] += src[i] * a; acc[1] += src[i + 1] * a; acc[2] += src[i + 2] * a; acc[3] += a;
                }
            }
            const size_t o = (static_cast<size_t>(y) * width + x) * 4;
            const float alpha = acc[3] * inv;
            if (acc[3] > 0.0f) {
                pixel_data[o + 0] = static_cast<uint8_t>(std::lround(acc[0] / acc[3]));
                pixel_data[o + 1] = static_cast<uint8_t>(std::lround(acc[1] / acc[3]));
                pixel_data[o + 2] = static_cast<uint8_t>(std::lround(acc[2] / acc[3]));
            }
            pixel_data[o + 3] = static_cast<uint8_t>(std::lround(alpha));
        }
    }
}

void MeshToSpritePipeline::update_view_matrix() {
    view_matrix_ = glm::lookAt(current_camera_.position, current_camera_.target, current_camera_.up);
}

void MeshToSpritePipeline::update_projection_matrix() {
    float aspect = static_cast<float>(config_.render.frame_width) / std::max<uint32_t>(1, config_.render.frame_height);

    if (current_camera_.type == CameraType::ORTHOGRAPHIC) {
        float size = current_camera_.ortho_size;
        projection_matrix_ = glm::ortho(-size * aspect, size * aspect, -size, size,
                                       current_camera_.near_plane, current_camera_.far_plane);
    } else if (current_camera_.type == CameraType::PERSPECTIVE) {
        projection_matrix_ = glm::perspective(glm::radians(current_camera_.fov), aspect,
                                             current_camera_.near_plane, current_camera_.far_plane);
    } else if (current_camera_.type == CameraType::ISOMETRIC) {
        // Isometric projection (special case of orthographic)
        float size = current_camera_.ortho_size;
        projection_matrix_ = glm::ortho(-size * aspect, size * aspect, -size, size,
                                       current_camera_.near_plane, current_camera_.far_plane);
    }
}

glm::mat4 MeshToSpritePipeline::calculate_model_matrix(const AnimationClip& clip, float time) {
    if (clip.bone_matrices.empty()) {
        return glm::mat4(1.0f);
    }
    if (clip.bone_matrices.size() == 1 || clip.duration <= 0.0f) {
        return clip.bone_matrices.front();
    }

    float t = clip.loop ? std::fmod(time, clip.duration) : std::clamp(time, 0.0f, clip.duration);
    if (t < 0.0f) t += clip.duration;

    // Keyframe times (evenly spaced when the clip does not provide them)
    const size_t count = clip.bone_matrices.size();
    auto key_time = [&](size_t i) -> float {
        return i < clip.keyframe_times.size() ? clip.keyframe_times[i]
                                              : clip.duration * static_cast<float>(i) / static_cast<float>(count);
    };
    size_t next = 0;
    while (next < count && key_time(next) <= t) ++next;
    if (next == 0) return clip.bone_matrices.front();
    const size_t prev = next - 1;
    if (next >= count) {
        if (!clip.loop) return clip.bone_matrices.back();
        next = 0;  // wrap: blend the last key towards the first
    }
    const float t0 = key_time(prev);
    const float t1 = next == 0 ? clip.duration : key_time(next);
    const float alpha = t1 > t0 ? std::clamp((t - t0) / (t1 - t0), 0.0f, 1.0f) : 0.0f;

    // Interpolate rigid transforms: lerp translation, slerp rotation
    const glm::mat4& a = clip.bone_matrices[prev];
    const glm::mat4& b = clip.bone_matrices[next];
    const glm::vec3 ta(a[3]), tb(b[3]);
    const glm::quat qa = glm::quat_cast(glm::mat3(a));
    const glm::quat qb = glm::quat_cast(glm::mat3(b));
    glm::mat4 result = glm::mat4_cast(glm::slerp(qa, qb, alpha));
    result[3] = glm::vec4(glm::mix(ta, tb, alpha), 1.0f);
    return result;
}

MeshToSpritePipeline::PackingNode* MeshToSpritePipeline::pack_rectangle(PackingNode* node, glm::ivec2 size) {
    if (!node) return nullptr;
    if (node->left || node->right) {
        // Internal node: try both children
        if (PackingNode* placed = pack_rectangle(node->left.get(), size)) return placed;
        return pack_rectangle(node->right.get(), size);
    }
    if (node->occupied || size.x > node->size.x || size.y > node->size.y) {
        return nullptr;
    }
    if (size.x == node->size.x && size.y == node->size.y) {
        node->occupied = true;
        return node;
    }
    // Split along the axis with the most leftover space
    node->left = std::make_unique<PackingNode>();
    node->right = std::make_unique<PackingNode>();
    const int dw = node->size.x - size.x;
    const int dh = node->size.y - size.y;
    if (dw > dh) {
        node->left->position = node->position;
        node->left->size = glm::ivec2(size.x, node->size.y);
        node->right->position = glm::ivec2(node->position.x + size.x, node->position.y);
        node->right->size = glm::ivec2(dw, node->size.y);
    } else {
        node->left->position = node->position;
        node->left->size = glm::ivec2(node->size.x, size.y);
        node->right->position = glm::ivec2(node->position.x, node->position.y + size.y);
        node->right->size = glm::ivec2(node->size.x, dh);
    }
    node->left->occupied = false;
    node->right->occupied = false;
    return pack_rectangle(node->left.get(), size);
}

bool MeshToSpritePipeline::fits_in_sheet(const std::vector<SpriteFrame>& frames, uint32_t width, uint32_t height) {
    if (frames.empty()) return true;

    const uint32_t padding = static_cast<uint32_t>(config_.sprite_padding);
    const bool uniform = std::all_of(frames.begin(), frames.end(),
                                     [&](const SpriteFrame& f) { return f.size == frames[0].size; });
    if (!uniform) {
        // Mixed sizes: try the binary-tree packer
        PackingNode root;
        root.position = glm::ivec2(0);
        root.size = glm::ivec2(static_cast<int>(width), static_cast<int>(height));
        root.occupied = false;
        for (const auto& f : frames) {
            if (!pack_rectangle(&root, f.size + glm::ivec2(static_cast<int>(padding)))) return false;
        }
        return true;
    }

    uint32_t frame_width = frames[0].size.x;
    uint32_t frame_height = frames[0].size.y;

    uint32_t frames_per_row = width / (frame_width + padding);
    if (frames_per_row == 0) return false;
    uint32_t required_rows = static_cast<uint32_t>((frames.size() + frames_per_row - 1) / frames_per_row);
    uint32_t required_height = required_rows * (frame_height + padding);

    return required_height <= height;
}

void MeshToSpritePipeline::optimize_packing_order(std::vector<SpriteFrame>& frames) {
    // Sort frames by area (largest first) for better packing; stable so equal-size
    // frames keep their animation order
    std::stable_sort(frames.begin(), frames.end(), [](const SpriteFrame& a, const SpriteFrame& b) {
        return (a.size.x * a.size.y) > (b.size.x * b.size.y);
    });
}

bool MeshToSpritePipeline::save_image_png(const std::string& filename, const std::vector<uint8_t>& data,
                                         uint32_t width, uint32_t height) {
    if (data.size() < static_cast<size_t>(width) * height * 4) {
        std::cerr << "Image buffer too small for " << width << "x" << height << ": " << filename << std::endl;
        return false;
    }
    return stbi_write_png(filename.c_str(), static_cast<int>(width), static_cast<int>(height), 4,
                          data.data(), static_cast<int>(width * 4)) != 0;
}

bool MeshToSpritePipeline::save_image_webp(const std::string& filename, const std::vector<uint8_t>& data,
                                          uint32_t width, uint32_t height) {
    // No WebP encoder is vendored (libwebp); the sheet is written losslessly as PNG instead,
    // using the .png name so the file contents match its extension.
    std::filesystem::path path(filename);
    path.replace_extension(".png");
    std::cerr << "WebP encoder unavailable, writing PNG: " << path.string() << std::endl;
    return save_image_png(path.string(), data, width, height);
}

std::vector<uint8_t> MeshToSpritePipeline::compress_image_data(const std::vector<uint8_t>& data) {
    if (data.empty()) return {};
    int out_len = 0;
    unsigned char* compressed = stbi_zlib_compress(const_cast<unsigned char*>(data.data()),
                                                   static_cast<int>(data.size()), &out_len, 8);
    if (!compressed) return {};
    std::vector<uint8_t> result(compressed, compressed + out_len);
    std::free(compressed);  // stb_image_write allocates with STBIW_MALLOC (malloc)
    return result;
}

void MeshToSpritePipeline::update_performance_stats(const std::string& operation, double time_taken) {
    if (operation == "render") {
        performance_stats_.frames_rendered++;
        performance_stats_.total_render_time += time_taken;
        performance_stats_.avg_frame_render_time =
            performance_stats_.total_render_time / static_cast<double>(std::max<uint64_t>(1, performance_stats_.frames_rendered));
    } else if (operation == "pack") {
        performance_stats_.sprites_packed++;
        performance_stats_.total_packing_time += time_taken;
        performance_stats_.avg_packing_time =
            performance_stats_.total_packing_time / static_cast<double>(std::max<uint64_t>(1, performance_stats_.sprites_packed));
    } else if (operation == "animation") {
        performance_stats_.animations_generated++;
    }
}

bool MeshToSpritePipeline::enable_normal_mapping(bool enable) {
    // Shades with the mesh's interpolated vertex normals instead of flat face normals.
    normal_mapping_enabled_ = enable;
    return true;
}

bool MeshToSpritePipeline::enable_ambient_occlusion(bool enable) {
    // Screen-space AO computed from the software depth buffer (see apply_post_process).
    ambient_occlusion_enabled_ = enable;
    return true;
}

void MeshToSpritePipeline::set_custom_shader(const std::string& vertex_shader, const std::string& fragment_shader) {
    // Kept for GPU backends; the software rasterizer uses its fixed lighting model.
    custom_vertex_shader_ = vertex_shader;
    custom_fragment_shader_ = fragment_shader;
    std::cerr << "Custom shaders are stored but not executed by the software rasterizer" << std::endl;
}

void MeshToSpritePipeline::add_post_process_effect(const std::string& effect_name, const std::string& shader) {
    static const char* builtin[] = { "outline", "grayscale", "invert" };
    if (std::find(std::begin(builtin), std::end(builtin), effect_name) == std::end(builtin)) {
        std::cerr << "Unknown post-process effect '" << effect_name
                  << "' (built-in: outline, grayscale, invert)" << std::endl;
        return;
    }
    post_process_effects_.emplace_back(effect_name, shader);
}

std::string MeshToSpritePipeline::generate_frames_json(const SpriteSheet& sheet) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"frameCount\": " << sheet.frames.size() << ",\n";
    json << "  \"frameWidth\": " << (sheet.frames.empty() ? 0 : sheet.frames[0].size.x) << ",\n";
    json << "  \"frameHeight\": " << (sheet.frames.empty() ? 0 : sheet.frames[0].size.y) << ",\n";
    json << "  \"sheetWidth\": " << sheet.width << ",\n";
    json << "  \"sheetHeight\": " << sheet.height << ",\n";
    json << "  \"texture\": \"" << sheet.texture_filename << "\",\n";
    json << "  \"frames\": [\n";
    
    for (size_t i = 0; i < sheet.frames.size(); ++i) {
        const auto& frame = sheet.frames[i];
        json << "    {\n";
        json << "      \"index\": " << frame.frame_index << ",\n";
        json << "      \"x\": " << frame.position.x << ",\n";
        json << "      \"y\": " << frame.position.y << ",\n";
        json << "      \"width\": " << frame.size.x << ",\n";
        json << "      \"height\": " << frame.size.y << ",\n";
        json << "      \"pivotX\": " << frame.pivot.x << ",\n";
        json << "      \"pivotY\": " << frame.pivot.y << ",\n";
        json << "      \"timestamp\": " << frame.timestamp << "\n";
        json << "    }";
        if (i < sheet.frames.size() - 1) {
            json << ",";
        }
        json << "\n";
    }
    
    json << "  ]\n";
    json << "}";
    
    return json.str();
}

std::string MeshToSpritePipeline::generate_animation_json(const AnimationDefinition& animation) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"animationName\": \"" << animation.animation_name << "\",\n";
    json << "  \"duration\": " << animation.duration << ",\n";
    json << "  \"fps\": " << animation.fps << ",\n";
    json << "  \"loop\": " << (animation.loop ? "true" : "false") << ",\n";
    json << "  \"frameSequence\": [";
    
    for (size_t i = 0; i < animation.frame_sequence.size(); ++i) {
        json << animation.frame_sequence[i];
        if (i < animation.frame_sequence.size() - 1) {
            json << ", ";
        }
    }
    
    json << "],\n";
    json << "  \"frameTimes\": [";
    
    for (size_t i = 0; i < animation.frame_times.size(); ++i) {
        json << animation.frame_times[i];
        if (i < animation.frame_times.size() - 1) {
            json << ", ";
        }
    }
    
    json << "]\n";
    json << "}";
    
    return json.str();
}

std::string MeshToSpritePipeline::generate_starbound_animation_json(const AnimationDefinition& animation) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"animatedParts\": {\n";
    json << "    \"parts\": {\n";
    json << "      \"sprite\": {\n";
    json << "        \"partStates\": {\n";
    json << "          \"" << animation.animation_name << "\": {\n";
    json << "            \"frames\": " << animation.frame_sequence.size() << ",\n";
    json << "            \"frameTime\": " << (1.0f / animation.fps) << ",\n";
    json << "            \"loop\": " << (animation.loop ? "true" : "false") << "\n";
    json << "          }\n";
    json << "        }\n";
    json << "      }\n";
    json << "    }\n";
    json << "  },\n";
    json << "  \"globalTagDefaults\": {\n";
    json << "    \"sprite\": \"" << animation.animation_name << "\"\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

std::string MeshToSpritePipeline::generate_starbound_projectile_json(const std::string& projectile_name,
                                                                    const std::vector<AnimationDefinition>& animations) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"projectileName\": \"" << projectile_name << "\",\n";
    json << "  \"image\": \"" << projectile_name << ".png\",\n";
    json << "  \"animationCycle\": " << (animations.empty() ? 1.0f : animations[0].duration) << ",\n";
    json << "  \"frameNumber\": " << (animations.empty() ? 1 : static_cast<int>(animations[0].frame_sequence.size())) << ",\n";
    json << "  \"windupFrames\": 0,\n";
    json << "  \"winddownFrames\": 0,\n";
    json << "  \"speed\": 50,\n";
    json << "  \"timeToLive\": 5,\n";
    json << "  \"power\": 10,\n";
    json << "  \"damageType\": \"energy\",\n";
    json << "  \"damageKind\": \"default\"\n";
    json << "}";
    
    return json.str();
}

std::string MeshToSpritePipeline::get_timestamp_string() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time_t), "%Y%m%d_%H%M%S");
    return oss.str();
}

std::string MeshToSpritePipeline::sanitize_filename(const std::string& name) {
    std::string sanitized = name;
    
    // Replace invalid filename characters
    std::replace_if(sanitized.begin(), sanitized.end(), [](char c) {
        return c == '/' || c == '\\' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|';
    }, '_');
    
    return sanitized;
}

bool MeshToSpritePipeline::create_directory_if_not_exists(const std::string& path) {
    try {
        std::filesystem::create_directories(path);
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to create directory: " << path << " - " << e.what() << std::endl;
        return false;
    }
}

glm::vec3 MeshToSpritePipeline::calculate_bounds_center(const MeshData& mesh) {
    if (mesh.vertices.empty()) {
        return glm::vec3(0);
    }
    
    glm::vec3 min_bounds(FLT_MAX);
    glm::vec3 max_bounds(-FLT_MAX);
    
    for (const auto& vertex : mesh.vertices) {
        min_bounds = glm::min(min_bounds, vertex);
        max_bounds = glm::max(max_bounds, vertex);
    }
    
    return (min_bounds + max_bounds) * 0.5f;
}

float MeshToSpritePipeline::calculate_bounds_radius(const MeshData& mesh) {
    glm::vec3 center = calculate_bounds_center(mesh);
    float max_distance = 0.0f;
    
    for (const auto& vertex : mesh.vertices) {
        float distance = glm::distance(vertex, center);
        max_distance = std::max(max_distance, distance);
    }
    
    return max_distance;
}

std::chrono::high_resolution_clock::time_point MeshToSpritePipeline::get_current_time() {
    return std::chrono::high_resolution_clock::now();
}

// Utility function implementations

namespace MeshToSpriteUtils {

CameraConfig CreateIsometricCamera(float distance) {
    CameraConfig config;
    config.type = CameraType::ISOMETRIC;
    config.position = glm::vec3(distance * 0.707f, distance * 0.707f, distance * 0.707f);
    config.target = glm::vec3(0, 0, 0);
    config.up = glm::vec3(0, 1, 0);
    config.ortho_size = distance * 0.5f;
    return config;
}

CameraConfig CreateTopDownCamera(float distance) {
    CameraConfig config;
    config.type = CameraType::ORTHOGRAPHIC;
    config.position = glm::vec3(0, distance, 0);
    config.target = glm::vec3(0, 0, 0);
    config.up = glm::vec3(0, 0, -1);
    config.ortho_size = distance * 0.4f;
    return config;
}

CameraConfig CreateSideViewCamera(float distance) {
    CameraConfig config;
    config.type = CameraType::ORTHOGRAPHIC;
    config.position = glm::vec3(distance, 0, 0);
    config.target = glm::vec3(0, 0, 0);
    config.up = glm::vec3(0, 1, 0);
    config.ortho_size = distance * 0.4f;
    return config;
}

LightingConfig CreateBasicLighting() {
    LightingConfig config;
    config.mode = LightingMode::DIRECTIONAL;
    config.ambient_color = glm::vec3(0.3f, 0.3f, 0.3f);
    config.directional_direction = glm::vec3(-1, -1, -1);
    config.directional_color = glm::vec3(1.0f, 1.0f, 1.0f);
    config.directional_intensity = 1.0f;
    return config;
}

LightingConfig CreateDramaticLighting() {
    LightingConfig config;
    config.mode = LightingMode::DIRECTIONAL;
    config.ambient_color = glm::vec3(0.1f, 0.1f, 0.2f);
    config.directional_direction = glm::vec3(-2, -1, -1);
    config.directional_color = glm::vec3(1.2f, 1.0f, 0.8f);
    config.directional_intensity = 1.5f;
    config.cast_shadows = true;
    return config;
}

LightingConfig CreateSoftLighting() {
    LightingConfig config;
    config.mode = LightingMode::DIRECTIONAL;
    config.ambient_color = glm::vec3(0.4f, 0.4f, 0.4f);
    config.directional_direction = glm::vec3(-0.5f, -1, -0.5f);
    config.directional_color = glm::vec3(0.8f, 0.8f, 0.8f);
    config.directional_intensity = 0.8f;
    return config;
}

std::vector<DirectionalCapture> Create8DirectionalSet(float distance) {
    std::vector<DirectionalCapture> captures;
    
    std::vector<std::pair<std::string, float>> directions = {
        {"front", 0.0f}, {"front_right", 45.0f}, {"right", 90.0f}, {"back_right", 135.0f},
        {"back", 180.0f}, {"back_left", 225.0f}, {"left", 270.0f}, {"front_left", 315.0f}
    };
    
    for (const auto& [name, yaw] : directions) {
        DirectionalCapture capture;
        capture.direction_name = name;
        capture.yaw_rotation = yaw;
        capture.pitch_rotation = 0.0f;
        
        float rad = glm::radians(yaw);
        capture.camera_offset = glm::vec3(std::sin(rad) * distance, 0, std::cos(rad) * distance);
        
        captures.push_back(capture);
    }
    
    return captures;
}

std::vector<DirectionalCapture> Create4DirectionalSet(float distance) {
    std::vector<DirectionalCapture> captures;
    
    std::vector<std::pair<std::string, float>> directions = {
        {"front", 0.0f}, {"right", 90.0f}, {"back", 180.0f}, {"left", 270.0f}
    };
    
    for (const auto& [name, yaw] : directions) {
        DirectionalCapture capture;
        capture.direction_name = name;
        capture.yaw_rotation = yaw;
        capture.pitch_rotation = 0.0f;
        
        float rad = glm::radians(yaw);
        capture.camera_offset = glm::vec3(std::sin(rad) * distance, 0, std::cos(rad) * distance);
        
        captures.push_back(capture);
    }
    
    return captures;
}

std::vector<DirectionalCapture> CreateSingleDirectionSet(float distance) {
    std::vector<DirectionalCapture> captures;
    
    DirectionalCapture capture;
    capture.direction_name = "default";
    capture.yaw_rotation = 0.0f;
    capture.pitch_rotation = 0.0f;
    capture.camera_offset = glm::vec3(0, 0, distance);
    
    captures.push_back(capture);
    return captures;
}

AnimationCapture CreateBasicCapture(const std::string& name, float duration, float fps) {
    AnimationCapture capture;
    capture.animation_name = name;
    capture.start_time = 0.0f;
    capture.end_time = duration;
    capture.fps = fps;
    capture.loop = true;
    return capture;
}

std::vector<AnimationCapture> CreateCaptureSet(const std::vector<std::string>& animation_names) {
    std::vector<AnimationCapture> captures;
    
    for (const auto& name : animation_names) {
        captures.push_back(CreateBasicCapture(name, 2.0f, 24.0f));
    }
    
    return captures;
}

std::string GenerateStarboundProjectileConfig(const std::string& projectile_name,
                                             const std::string& sprite_sheet,
                                             const AnimationDefinition& animation) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"projectileName\": \"" << projectile_name << "\",\n";
    json << "  \"image\": \"" << sprite_sheet << "\",\n";
    json << "  \"animationCycle\": " << animation.duration << ",\n";
    json << "  \"frameNumber\": " << animation.frame_sequence.size() << ",\n";
    json << "  \"windupFrames\": 0,\n";
    json << "  \"winddownFrames\": 0,\n";
    json << "  \"speed\": 50,\n";
    json << "  \"timeToLive\": 5,\n";
    json << "  \"power\": 10,\n";
    json << "  \"damageType\": \"energy\",\n";
    json << "  \"damageKind\": \"default\",\n";
    json << "  \"physics\": \"laser\",\n";
    json << "  \"bounces\": 0,\n";
    json << "  \"piercing\": false,\n";
    json << "  \"fullbright\": true\n";
    json << "}";
    
    return json.str();
}

} // namespace MeshToSpriteUtils

} // namespace Animation
} // namespace MagiTech
