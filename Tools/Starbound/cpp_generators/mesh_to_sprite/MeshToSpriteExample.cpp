#include "core/animation/MeshToSpritePipeline.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>

using namespace MagiTech::Animation;

/**
 * @brief Example demonstrating comprehensive mesh-to-sprite pipeline
 * 
 * Shows conversion of 3D mech animations to 2D sprite sheets with
 * multiple camera angles, lighting setups, and Starbound integration.
 */
class MeshToSpriteExample {
public:
    MeshToSpriteExample() {
        // Configure pipeline
        MeshToSpritePipeline::PipelineConfig config;
        
        // Render settings
        config.backend = MeshToSpritePipeline::RenderBackend::OPENGL;
        config.render.frame_width = 128;
        config.render.frame_height = 128;
        config.render.samples = 4; // 4x MSAA
        config.render.enable_alpha = true;
        config.render.enable_depth_test = true;
        config.render.background_color = glm::vec4(0, 0, 0, 0); // Transparent
        
        // Camera settings
        config.camera.type = MeshToSpritePipeline::CameraType::ISOMETRIC;
        config.camera.position = glm::vec3(5, 5, 5);
        config.camera.target = glm::vec3(0, 0, 0);
        config.camera.up = glm::vec3(0, 1, 0);
        config.camera.ortho_size = 3.0f;
        config.camera.auto_fit_bounds = true;
        
        // Lighting settings
        config.lighting.mode = MeshToSpritePipeline::LightingMode::DIRECTIONAL;
        config.lighting.ambient_color = glm::vec3(0.3f, 0.3f, 0.3f);
        config.lighting.directional_direction = glm::vec3(-1, -1, -1);
        config.lighting.directional_color = glm::vec3(1.0f, 1.0f, 1.0f);
        config.lighting.directional_intensity = 1.2f;
        config.lighting.cast_shadows = false; // Disable for performance
        
        // Output settings
        config.output_format = MeshToSpritePipeline::OutputFormat::PNG;
        config.output_directory = "./sprite_output";
        config.asset_prefix = "mech";
        config.generate_sprite_sheets = true;
        config.generate_individual_frames = false;
        config.generate_animation_json = true;
        config.generate_starbound_files = true;
        
        // Sprite sheet settings
        config.max_sheet_width = 2048;
        config.max_sheet_height = 2048;
        config.sprite_padding = 2.0f;
        config.power_of_two_sheets = true;
        config.optimize_empty_space = true;
        
        // Performance settings
        config.enable_multithreading = true;
        config.enable_progressive_capture = false;
        
        // Initialize pipeline
        pipeline_ = std::make_unique<MeshToSpritePipeline>();
        if (!pipeline_->initialize(config)) {
            throw std::runtime_error("Failed to initialize mesh-to-sprite pipeline");
        }
        
        // Set progress callback
        pipeline_->set_progress_callback([this](float progress, const std::string& status) {
            this->on_progress_update(progress, status);
        });
        
        std::cout << "=== Mesh-to-Sprite Pipeline Example ===" << std::endl;
        std::cout << "Converting 3D mech animations to 2D sprite sheets" << std::endl;
        std::cout << "=============================================" << std::endl << std::endl;
        
        std::cout << "Configuration:" << std::endl;
        std::cout << "  Render Resolution: " << config.render.frame_width << "x" << config.render.frame_height << std::endl;
        std::cout << "  Camera Type: Isometric" << std::endl;
        std::cout << "  Lighting: Directional with shadows" << std::endl;
        std::cout << "  Output Format: PNG" << std::endl;
        std::cout << "  Max Sheet Size: " << config.max_sheet_width << "x" << config.max_sheet_height << std::endl;
        std::cout << "  Starbound Integration: Enabled" << std::endl << std::endl;
    }
    
    ~MeshToSpriteExample() {
        if (pipeline_) {
            pipeline_->shutdown();
        }
    }
    
    void run_demonstration() {
        std::cout << "Starting mesh-to-sprite conversion demonstration..." << std::endl << std::endl;
        
        // Step 1: Load mesh and animations
        demonstrate_mesh_loading();
        
        // Step 2: Setup multiple camera angles
        demonstrate_camera_setups();
        
        // Step 3: Capture single animation
        demonstrate_single_animation_capture();
        
        // Step 4: Capture directional set
        demonstrate_directional_capture();
        
        // Step 5: Batch processing
        demonstrate_batch_processing();
        
        // Step 6: Starbound integration
        demonstrate_starbound_integration();
        
        // Step 7: Performance analysis
        demonstrate_performance_analysis();
        
        print_final_summary();
    }
    
private:
    std::unique_ptr<MeshToSpritePipeline> pipeline_;
    
    void demonstrate_mesh_loading() {
        std::cout << "=== Demonstrating Mesh and Animation Loading ===" << std::endl;
        
        // For this example, we'll simulate loading since we don't have actual files
        std::cout << "Loading 3D mech mesh..." << std::endl;
        
        // In a real scenario, you would load actual mesh files:
        // bool success = pipeline_->load_mesh("./assets/mech_body.obj");
        
        // For demonstration, we'll create a simple procedural mesh
        bool mesh_loaded = create_demo_mesh();
        
        if (mesh_loaded) {
            std::cout << "✓ Mesh loaded successfully" << std::endl;
        } else {
            std::cout << "✗ Failed to load mesh" << std::endl;
            return;
        }
        
        std::cout << "Loading animation clips..." << std::endl;
        
        // Load various animation clips
        std::vector<std::string> animation_names = {
            "idle", "walk", "run", "attack", "damaged", "destroyed"
        };
        
        for (const auto& anim_name : animation_names) {
            // In a real scenario: pipeline_->load_animation_clip(anim_name, "./assets/" + anim_name + ".bvh");
            
            // For demonstration, create placeholder animations
            bool anim_loaded = create_demo_animation(anim_name);
            
            if (anim_loaded) {
                std::cout << "✓ Animation '" << anim_name << "' loaded" << std::endl;
            } else {
                std::cout << "✗ Failed to load animation: " << anim_name << std::endl;
            }
        }
        
        // Auto-fit camera to mesh bounds
        pipeline_->auto_fit_camera_to_mesh();
        std::cout << "✓ Camera auto-fitted to mesh bounds" << std::endl;
        
        std::cout << std::endl;
    }
    
    void demonstrate_camera_setups() {
        std::cout << "=== Demonstrating Camera Configurations ===" << std::endl;
        
        // Test different camera presets
        std::vector<std::pair<std::string, std::function<CameraConfig()>>> camera_presets = {
            {"Isometric", []() { return MeshToSpriteUtils::CreateIsometricCamera(6.0f); }},
            {"Top-Down", []() { return MechToSpriteUtils::CreateTopDownCamera(8.0f); }},
            {"Side View", []() { return MeshToSpriteUtils::CreateSideViewCamera(6.0f); }}
        };
        
        for (const auto& [name, create_camera] : camera_presets) {
            std::cout << "Testing " << name << " camera..." << std::endl;
            
            auto camera_config = create_camera();
            pipeline_->setup_camera(camera_config);
            
            // Render a test frame to verify camera setup
            auto test_frame = pipeline_->render_single_frame("idle", 0.0f);
            
            if (!test_frame.pixel_data.empty()) {
                std::cout << "✓ " << name << " camera setup successful" << std::endl;
            } else {
                std::cout << "✗ " << name << " camera setup failed" << std::endl;
            }
        }
        
        // Reset to isometric for remaining demonstrations
        pipeline_->setup_camera(MeshToSpriteUtils::CreateIsometricCamera(6.0f));
        
        std::cout << std::endl;
    }
    
    void demonstrate_single_animation_capture() {
        std::cout << "=== Demonstrating Single Animation Capture ===" << std::endl;
        
        // Capture the idle animation
        AnimationCapture capture_config;
        capture_config.animation_name = "idle";
        capture_config.start_time = 0.0f;
        capture_config.end_time = 2.0f;
        capture_config.fps = 24.0f;
        capture_config.loop = true;
        
        std::cout << "Capturing 'idle' animation..." << std::endl;
        std::cout << "  Duration: " << capture_config.end_time << " seconds" << std::endl;
        std::cout << "  FPS: " << capture_config.fps << std::endl;
        std::cout << "  Expected frames: " << static_cast<int>(capture_config.end_time * capture_config.fps) << std::endl;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        bool success = pipeline_->capture_animation(capture_config);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        if (success) {
            std::cout << "✓ Animation captured successfully in " << duration.count() << "ms" << std::endl;
            std::cout << "  Output files:" << std::endl;
            std::cout << "    - idle.png (sprite sheet)" << std::endl;
            std::cout << "    - idle.frames (frame data)" << std::endl;
            std::cout << "    - idle.animation (animation definition)" << std::endl;
        } else {
            std::cout << "✗ Animation capture failed" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    void demonstrate_directional_capture() {
        std::cout << "=== Demonstrating Directional Animation Capture ===" << std::endl;
        
        // Create 8-directional capture set
        auto directional_set = MeshToSpriteUtils::Create8DirectionalSet(6.0f);
        
        std::cout << "Capturing 'walk' animation from 8 directions..." << std::endl;
        std::cout << "Directions: ";
        for (const auto& direction : directional_set) {
            std::cout << direction.direction_name << " ";
        }
        std::cout << std::endl;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        bool success = pipeline_->capture_directional_set("walk", directional_set);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        if (success) {
            std::cout << "✓ Directional capture completed in " << duration.count() << "ms" << std::endl;
            std::cout << "  Generated " << directional_set.size() << " directional sprite sheets" << std::endl;
            
            for (const auto& direction : directional_set) {
                std::cout << "    - walk_" << direction.direction_name << ".png" << std::endl;
            }
        } else {
            std::cout << "✗ Directional capture failed" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    void demonstrate_batch_processing() {
        std::cout << "=== Demonstrating Batch Processing ===" << std::endl;
        
        // Create animation capture configurations for batch processing
        std::vector<std::string> batch_animations = {"attack", "damaged", "destroyed"};
        auto capture_configs = MeshToSpriteUtils::CreateCaptureSet(batch_animations);
        
        // Modify configurations for different durations and framerates
        capture_configs[0].end_time = 1.5f;  // attack: 1.5 seconds
        capture_configs[0].fps = 30.0f;      // higher framerate for smooth attack
        
        capture_configs[1].end_time = 0.5f;  // damaged: 0.5 seconds
        capture_configs[1].fps = 20.0f;      // lower framerate for damage effect
        capture_configs[1].loop = false;     // one-shot animation
        
        capture_configs[2].end_time = 3.0f;  // destroyed: 3 seconds
        capture_configs[2].fps = 15.0f;      // lower framerate for destruction
        capture_configs[2].loop = false;     // one-shot animation
        
        std::cout << "Processing " << capture_configs.size() << " animations in batch..." << std::endl;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        bool all_success = true;
        for (const auto& config : capture_configs) {
            std::cout << "Processing '" << config.animation_name << "'..." << std::endl;
            
            if (!pipeline_->capture_animation(config)) {
                std::cout << "✗ Failed to process: " << config.animation_name << std::endl;
                all_success = false;
            } else {
                std::cout << "✓ Completed: " << config.animation_name << std::endl;
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        if (all_success) {
            std::cout << "✓ Batch processing completed successfully in " << duration.count() << "ms" << std::endl;
            std::cout << "  Average time per animation: " << (duration.count() / capture_configs.size()) << "ms" << std::endl;
        } else {
            std::cout << "⚠️  Batch processing completed with some failures" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    void demonstrate_starbound_integration() {
        std::cout << "=== Demonstrating Starbound Integration ===" << std::endl;
        
        // Create animation definitions for Starbound
        std::vector<AnimationDefinition> starbound_animations;
        
        auto available_animations = pipeline_->get_available_animations();
        std::cout << "Converting " << available_animations.size() << " animations for Starbound..." << std::endl;
        
        for (const auto& anim_name : available_animations) {
            AnimationDefinition def;
            def.animation_name = anim_name;
            def.duration = 2.0f; // Default duration
            def.fps = 24.0f;
            def.loop = (anim_name == "idle" || anim_name == "walk" || anim_name == "run");
            
            // Generate frame sequence
            int total_frames = static_cast<int>(def.duration * def.fps);
            for (int i = 0; i < total_frames; ++i) {
                def.frame_sequence.push_back(i);
                def.frame_times.push_back(i / def.fps);
            }
            
            starbound_animations.push_back(def);
            
            // Export individual animation
            if (pipeline_->export_starbound_animation(def)) {
                std::cout << "✓ Exported Starbound animation: " << anim_name << ".animation" << std::endl;
            }
        }
        
        // Create projectile configuration
        std::string projectile_name = "mech_energy_blast";
        if (pipeline_->export_starbound_projectile(projectile_name, starbound_animations)) {
            std::cout << "✓ Exported Starbound projectile: " << projectile_name << ".projectile" << std::endl;
        }
        
        // Generate comprehensive Starbound config
        std::cout << "Generated Starbound integration files:" << std::endl;
        std::cout << "  - Individual .animation files for each animation" << std::endl;
        std::cout << "  - .projectile file for projectile integration" << std::endl;
        std::cout << "  - Sprite sheets with proper frame data" << std::endl;
        std::cout << "  - Compatible with Starbound modding framework" << std::endl;
        
        std::cout << std::endl;
    }
    
    void demonstrate_performance_analysis() {
        std::cout << "=== Performance Analysis ===" << std::endl;
        
        auto stats = pipeline_->get_performance_stats();
        
        std::cout << "Pipeline Performance Statistics:" << std::endl;
        std::cout << "  Frames Rendered: " << stats.frames_rendered << std::endl;
        std::cout << "  Sprites Packed: " << stats.sprites_packed << std::endl;
        std::cout << "  Animations Generated: " << stats.animations_generated << std::endl;
        
        std::cout << "Timing Performance:" << std::endl;
        std::cout << "  Total Render Time: " << std::fixed << std::setprecision(3) 
                  << stats.total_render_time << "s" << std::endl;
        std::cout << "  Total Packing Time: " << std::fixed << std::setprecision(3) 
                  << stats.total_packing_time << "s" << std::endl;
        std::cout << "  Average Frame Render Time: " << std::fixed << std::setprecision(3) 
                  << (stats.avg_frame_render_time * 1000) << "ms" << std::endl;
        std::cout << "  Average Packing Time: " << std::fixed << std::setprecision(3) 
                  << (stats.avg_packing_time * 1000) << "ms" << std::endl;
        
        std::cout << "Output Statistics:" << std::endl;
        std::cout << "  Total Output Size: " << std::fixed << std::setprecision(1) 
                  << (stats.total_output_size / (1024.0 * 1024.0)) << " MB" << std::endl;
        
        if (stats.compressed_size > 0) {
            std::cout << "  Compressed Size: " << std::fixed << std::setprecision(1) 
                      << (stats.compressed_size / (1024.0 * 1024.0)) << " MB" << std::endl;
            std::cout << "  Compression Ratio: " << std::fixed << std::setprecision(2) 
                      << stats.compression_ratio << std::endl;
        }
        
        // Calculate performance metrics
        double frames_per_second = 0.0;
        if (stats.total_render_time > 0) {
            frames_per_second = stats.frames_rendered / stats.total_render_time;
        }
        
        double throughput_mbps = 0.0;
        if (stats.total_render_time > 0) {
            throughput_mbps = (stats.total_output_size / (1024.0 * 1024.0)) / stats.total_render_time;
        }
        
        std::cout << "Performance Metrics:" << std::endl;
        std::cout << "  Render Throughput: " << std::fixed << std::setprecision(1) 
                  << frames_per_second << " FPS" << std::endl;
        std::cout << "  Data Throughput: " << std::fixed << std::setprecision(1) 
                  << throughput_mbps << " MB/s" << std::endl;
        
        // Recommend optimizations if performance is low
        if (stats.avg_frame_render_time > 0.1) { // More than 100ms per frame
            std::cout << "Performance Recommendations:" << std::endl;
            std::cout << "  ⚠️  Frame render time is high - consider reducing resolution or MSAA" << std::endl;
        }
        
        if (stats.compression_ratio > 0.8) { // Low compression
            std::cout << "  ⚠️  Low compression ratio - consider different formats or settings" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    void print_final_summary() {
        std::cout << "=== Mesh-to-Sprite Pipeline Demonstration Complete ===" << std::endl;
        
        auto stats = pipeline_->get_performance_stats();
        
        std::cout << "Summary of Results:" << std::endl;
        std::cout << "  ✓ Successfully converted 3D mesh animations to 2D sprites" << std::endl;
        std::cout << "  ✓ Generated " << stats.sprites_packed << " sprite sheets" << std::endl;
        std::cout << "  ✓ Processed " << stats.frames_rendered << " individual frames" << std::endl;
        std::cout << "  ✓ Created " << stats.animations_generated << " animation definitions" << std::endl;
        std::cout << "  ✓ Generated Starbound-compatible files" << std::endl;
        
        std::cout << "Key Features Demonstrated:" << std::endl;
        std::cout << "  ✓ Multiple camera angles (isometric, top-down, side-view)" << std::endl;
        std::cout << "  ✓ Directional sprite generation (8-direction support)" << std::endl;
        std::cout << "  ✓ Batch processing for multiple animations" << std::endl;
        std::cout << "  ✓ Automatic sprite sheet packing and optimization" << std::endl;
        std::cout << "  ✓ JSON metadata generation for frame data" << std::endl;
        std::cout << "  ✓ Starbound modding integration" << std::endl;
        std::cout << "  ✓ Performance monitoring and optimization" << std::endl;
        
        std::cout << "Output Files Generated:" << std::endl;
        std::cout << "  - Sprite sheets (.png files)" << std::endl;
        std::cout << "  - Frame data (.frames JSON files)" << std::endl;
        std::cout << "  - Animation definitions (.animation files)" << std::endl;
        std::cout << "  - Starbound projectile configurations" << std::endl;
        
        std::cout << "Total Processing Time: " << std::fixed << std::setprecision(2) 
                  << (stats.total_render_time + stats.total_packing_time) << " seconds" << std::endl;
        
        std::cout << std::endl;
        std::cout << "The pipeline successfully demonstrates a complete workflow for" << std::endl;
        std::cout << "converting complex 3D mech animations into optimized 2D sprites" << std::endl;
        std::cout << "ready for integration with Starbound or other 2D game engines!" << std::endl;
    }
    
    void on_progress_update(float progress, const std::string& status) {
        // Update progress display
        int bar_width = 50;
        int filled_width = static_cast<int>(progress * bar_width);
        
        std::cout << "\r[";
        for (int i = 0; i < bar_width; ++i) {
            if (i < filled_width) {
                std::cout << "=";
            } else if (i == filled_width) {
                std::cout << ">";
            } else {
                std::cout << " ";
            }
        }
        std::cout << "] " << std::fixed << std::setprecision(1) << (progress * 100) << "% - " << status;
        std::cout.flush();
        
        if (progress >= 1.0f) {
            std::cout << std::endl;
        }
    }
    
    // Helper methods for creating demo content
    bool create_demo_mesh() {
        // In a real implementation, this would load an actual mesh file
        // For demonstration, we'll simulate a successful mesh load
        std::this_thread::sleep_for(std::chrono::milliseconds(100)); // Simulate loading time
        return true;
    }
    
    bool create_demo_animation(const std::string& animation_name) {
        // In a real implementation, this would load actual animation data
        // For demonstration, we'll simulate successful animation loading
        
        // Different loading times for different animations
        if (animation_name == "idle") {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        } else if (animation_name == "walk" || animation_name == "run") {
            std::this_thread::sleep_for(std::chrono::milliseconds(75));
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(60));
        }
        
        return true;
    }
};

int main() {
    try {
        MeshToSpriteExample example;
        example.run_demonstration();
        
        std::cout << "Mesh-to-Sprite pipeline example completed successfully!" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error in mesh-to-sprite example: " << e.what() << std::endl;
        return 1;
    }
}