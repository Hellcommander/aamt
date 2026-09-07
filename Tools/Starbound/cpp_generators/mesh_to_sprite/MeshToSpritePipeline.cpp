#include "MeshToSpritePipeline.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <cmath>
#include <thread>

// Image processing libraries (simplified implementations)
#ifdef USE_STBI
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include <stb_image_write.h>
#endif

#ifdef USE_LIBPNG
#include <png.h>
#endif

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
        default:
            std::cerr << "Unsupported render backend" << std::endl;
            return false;
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
    std::cout << "Backend: " << (config_.backend == RenderBackend::OPENGL ? "OpenGL" : "DirectX11") << std::endl;
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
        default:
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
    
    std::string extension = mesh_file.substr(mesh_file.find_last_of('.'));
    std::transform(extension.begin(), extension.end(), extension.begin(), ::tolower);
    
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
    
    std::string extension = clip_file.substr(clip_file.find_last_of('.'));
    std::transform(extension.begin(), extension.end(), extension.begin(), ::tolower);
    
    bool success = false;
    if (extension == ".bvh") {
        success = load_animation_bvh(clip_file);
    } else if (extension == ".fbx") {
        success = load_animation_fbx(clip_file);
    } else if (extension == ".gltf" || extension == ".glb") {
        success = load_animation_gltf(clip_file);
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
    int total_frames = static_cast<int>(duration * capture_config.fps);
    
    std::cout << "Capturing animation: " << capture_config.animation_name << std::endl;
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
        SpriteSheet sheet = pack_frames_to_sheet(captured_frames, capture_config.animation_name);
        export_sprite_sheet(sheet);
        export_frames_json(sheet);
        
        performance_stats_.sprites_packed++;
    }
    
    // Generate animation definition
    if (config_.generate_animation_json) {
        AnimationDefinition anim_def;
        anim_def.animation_name = capture_config.animation_name;
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
    if (directions.empty()) {
        return capture_animation(AnimationCapture{animation_name, 0.0f, 1.0f, 24.0f, true});
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
        capture_config.animation_name = animation_name + "_" + direction.direction_name;
        capture_config.start_time = 0.0f;
        capture_config.end_time = 1.0f;
        capture_config.fps = 24.0f;
        capture_config.loop = true;
        
        if (!capture_animation(capture_config)) {
            all_success = false;
            std::cerr << "Failed to capture directional animation: " << capture_config.animation_name << std::endl;
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
    
    // Render mesh with animation
    const auto& mesh = loaded_meshes_[0]; // Use first mesh for now
    const auto& clip = clip_it->second;
    
    render_mesh_with_animation(mesh, clip, time);
    
    // Capture framebuffer
    capture_framebuffer(frame.pixel_data);
    
    // Generate filename
    frame.filename = sanitize_filename(animation_name) + "_" + 
                    std::to_string(static_cast<int>(time * 1000)) + ".png";
    
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
    
    // Calculate required sheet size
    uint32_t frame_width = frames[0].size.x;
    uint32_t frame_height = frames[0].size.y;
    uint32_t padding = static_cast<uint32_t>(config_.sprite_padding);
    
    // Try different sheet sizes
    std::vector<std::pair<uint32_t, uint32_t>> size_candidates = {
        {512, 512}, {1024, 512}, {1024, 1024}, {2048, 1024}, {2048, 2048}
    };
    
    bool packed_successfully = false;
    
    for (const auto& [width, height] : size_candidates) {
        if (width > config_.max_sheet_width || height > config_.max_sheet_height) {
            continue;
        }
        
        // Try packing with this size
        std::vector<SpriteFrame> temp_frames = frames;
        optimize_packing_order(temp_frames);
        
        if (fits_in_sheet(temp_frames, width, height)) {
            sheet.width = width;
            sheet.height = height;
            sheet.frames = temp_frames;
            packed_successfully = true;
            break;
        }
    }
    
    if (!packed_successfully) {
        std::cerr << "Failed to pack frames into sprite sheet" << std::endl;
        return sheet;
    }
    
    // Pack frames using simple grid layout for now
    uint32_t frames_per_row = sheet.width / (frame_width + padding);
    uint32_t current_row = 0;
    uint32_t current_col = 0;
    
    for (auto& frame : sheet.frames) {
        frame.position.x = current_col * (frame_width + padding);
        frame.position.y = current_row * (frame_height + padding);
        
        current_col++;
        if (current_col >= frames_per_row) {
            current_col = 0;
            current_row++;
        }
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
        default:
            success = save_image_png(filepath, sheet.packed_data, sheet.width, sheet.height);
            break;
    }
    
    if (success) {
        performance_stats_.total_output_size += sheet.packed_data.size();
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

bool MeshToSpritePipeline::initialize_opengl() {
    // Simplified OpenGL initialization
    // In production, this would create a proper OpenGL context
    std::cout << "Initializing OpenGL renderer (simplified)" << std::endl;
    
    render_context_.viewport_width = config_.render.frame_width;
    render_context_.viewport_height = config_.render.frame_height;
    
    return true;
}

bool MeshToSpritePipeline::initialize_directx11() {
    // Simplified DirectX11 initialization
    // In production, this would create D3D11 device and context
    std::cout << "Initializing DirectX11 renderer (simplified)" << std::endl;
    
    render_context_.viewport_width = config_.render.frame_width;
    render_context_.viewport_height = config_.render.frame_height;
    
    return true;
}

void MeshToSpritePipeline::cleanup_opengl() {
    // OpenGL cleanup
}

void MeshToSpritePipeline::cleanup_directx11() {
    // DirectX11 cleanup
}

bool MeshToSpritePipeline::load_mesh_obj(const std::string& filename) {
    // Simplified OBJ loading
    MeshData mesh;
    
    std::ifstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string type;
        iss >> type;
        
        if (type == "v") {
            float x, y, z;
            iss >> x >> y >> z;
            mesh.vertices.emplace_back(x, y, z);
        } else if (type == "vn") {
            float x, y, z;
            iss >> x >> y >> z;
            mesh.normals.emplace_back(x, y, z);
        } else if (type == "vt") {
            float u, v;
            iss >> u >> v;
            mesh.uvs.emplace_back(u, v);
        } else if (type == "f") {
            // Simple face parsing (vertex indices only)
            std::string vertex_data;
            while (iss >> vertex_data) {
                size_t slash_pos = vertex_data.find('/');
                uint32_t vertex_index = std::stoi(vertex_data.substr(0, slash_pos)) - 1;
                mesh.indices.push_back(vertex_index);
            }
        }
    }
    
    file.close();
    
    // Generate normals if not present
    if (mesh.normals.empty()) {
        mesh.normals.resize(mesh.vertices.size(), glm::vec3(0, 1, 0));
    }
    
    // Generate UVs if not present
    if (mesh.uvs.empty()) {
        mesh.uvs.resize(mesh.vertices.size(), glm::vec2(0, 0));
    }
    
    loaded_meshes_.push_back(mesh);
    return true;
}

bool MeshToSpritePipeline::load_mesh_fbx(const std::string& filename) {
    // Placeholder for FBX loading
    std::cout << "FBX loading not implemented (placeholder)" << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_mesh_gltf(const std::string& filename) {
    // Placeholder for glTF loading
    std::cout << "glTF loading not implemented (placeholder)" << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_animation_bvh(const std::string& filename) {
    // Placeholder for BVH loading
    AnimationClip clip;
    clip.name = "default";
    clip.duration = 2.0f;
    clip.loop = true;
    
    // Generate dummy keyframes
    int num_keyframes = 48; // 24 FPS * 2 seconds
    clip.keyframe_times.resize(num_keyframes);
    clip.bone_matrices.resize(num_keyframes);
    
    for (int i = 0; i < num_keyframes; ++i) {
        clip.keyframe_times[i] = i / 24.0f;
        
        // Simple rotation animation
        float angle = (i / 24.0f) * 2.0f * 3.14159f;
        clip.bone_matrices[i] = glm::rotate(glm::mat4(1.0f), angle, glm::vec3(0, 1, 0));
    }
    
    animation_clips_[clip.name] = clip;
    return true;
}

bool MeshToSpritePipeline::load_animation_fbx(const std::string& filename) {
    // Placeholder for FBX animation loading
    std::cout << "FBX animation loading not implemented (placeholder)" << std::endl;
    return false;
}

bool MeshToSpritePipeline::load_animation_gltf(const std::string& filename) {
    // Placeholder for glTF animation loading
    std::cout << "glTF animation loading not implemented (placeholder)" << std::endl;
    return false;
}

void MeshToSpritePipeline::setup_render_target() {
    // Setup render target for offscreen rendering
    // This would create framebuffer objects in a real implementation
}

void MeshToSpritePipeline::clear_render_target() {
    // Clear render target with background color
    // In a real implementation, this would clear the framebuffer
}

void MeshToSpritePipeline::render_mesh_with_animation(const MeshData& mesh, const AnimationClip& clip, float time) {
    // Simplified mesh rendering with animation
    // In a real implementation, this would:
    // 1. Set up vertex/index buffers
    // 2. Apply bone transformations based on time
    // 3. Set up shaders and render state
    // 4. Draw the mesh
}

void MeshToSpritePipeline::apply_lighting() {
    // Apply lighting configuration
    // In a real implementation, this would set shader uniforms for lighting
}

void MeshToSpritePipeline::capture_framebuffer(std::vector<uint8_t>& pixel_data) {
    // Capture framebuffer contents
    // For now, generate a simple test pattern
    uint32_t width = config_.render.frame_width;
    uint32_t height = config_.render.frame_height;
    
    pixel_data.resize(width * height * 4);
    
    for (uint32_t y = 0; y < height; ++y) {
        for (uint32_t x = 0; x < width; ++x) {
            uint32_t index = (y * width + x) * 4;
            
            // Generate a simple test pattern
            pixel_data[index + 0] = static_cast<uint8_t>((x * 255) / width);       // R
            pixel_data[index + 1] = static_cast<uint8_t>((y * 255) / height);      // G
            pixel_data[index + 2] = 128;                                           // B
            pixel_data[index + 3] = 255;                                           // A
        }
    }
}

void MeshToSpritePipeline::update_view_matrix() {
    view_matrix_ = glm::lookAt(current_camera_.position, current_camera_.target, current_camera_.up);
}

void MeshToSpritePipeline::update_projection_matrix() {
    float aspect = static_cast<float>(config_.render.frame_width) / config_.render.frame_height;
    
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
    // Interpolate between keyframes
    float normalized_time = fmod(time, clip.duration) / clip.duration;
    size_t keyframe_index = static_cast<size_t>(normalized_time * clip.bone_matrices.size());
    keyframe_index = std::min(keyframe_index, clip.bone_matrices.size() - 1);
    
    return clip.bone_matrices[keyframe_index];
}

bool MeshToSpritePipeline::fits_in_sheet(const std::vector<SpriteFrame>& frames, uint32_t width, uint32_t height) {
    if (frames.empty()) return true;
    
    uint32_t frame_width = frames[0].size.x;
    uint32_t frame_height = frames[0].size.y;
    uint32_t padding = static_cast<uint32_t>(config_.sprite_padding);
    
    uint32_t frames_per_row = width / (frame_width + padding);
    uint32_t required_rows = (frames.size() + frames_per_row - 1) / frames_per_row;
    uint32_t required_height = required_rows * (frame_height + padding);
    
    return required_height <= height;
}

void MeshToSpritePipeline::optimize_packing_order(std::vector<SpriteFrame>& frames) {
    // Sort frames by area (largest first) for better packing
    std::sort(frames.begin(), frames.end(), [](const SpriteFrame& a, const SpriteFrame& b) {
        return (a.size.x * a.size.y) > (b.size.x * b.size.y);
    });
}

bool MeshToSpritePipeline::save_image_png(const std::string& filename, const std::vector<uint8_t>& data, 
                                         uint32_t width, uint32_t height) {
#ifdef USE_STBI
    return stbi_write_png(filename.c_str(), width, height, 4, data.data(), width * 4) != 0;
#else
    // Simplified PNG saving (placeholder)
    std::ofstream file(filename, std::ios::binary);
    if (file.is_open()) {
        // Write a simple header (not real PNG format)
        file.write(reinterpret_cast<const char*>(&width), sizeof(width));
        file.write(reinterpret_cast<const char*>(&height), sizeof(height));
        file.write(reinterpret_cast<const char*>(data.data()), data.size());
        file.close();
        return true;
    }
    return false;
#endif
}

bool MeshToSpritePipeline::save_image_webp(const std::string& filename, const std::vector<uint8_t>& data, 
                                          uint32_t width, uint32_t height) {
    // Placeholder for WebP saving
    return save_image_png(filename, data, width, height);
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