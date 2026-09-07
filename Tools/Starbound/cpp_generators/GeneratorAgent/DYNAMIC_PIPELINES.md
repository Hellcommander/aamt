# Dynamic Pipeline System

The enhanced image generator now supports dynamic pipeline loading, allowing you to work with any pipeline system without hardcoding dependencies. This makes the system more flexible and extensible.

## Overview

The dynamic pipeline system consists of three main components:

1. **IPipeline Interface** - Abstract base class for all pipelines
2. **PipelineFactory** - Factory pattern for creating pipeline instances
3. **PipelineManager** - Runtime management of pipeline loading and switching

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ImageGenerator│    │ PipelineManager  │    │ PipelineFactory │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │IPipeline*   │◄┼────┼►│Current Pipeline│ │    │ │Creators Map │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────────────────────────┐
                       │         Concrete Pipelines          │
                       │                                     │
                       │  MechPipeline    CharacterPipeline  │
                       │  VehiclePipeline  EffectPipeline    │
                       │  CustomPipeline   ...               │
                       └─────────────────────────────────────┘
```

## Creating a Custom Pipeline

### 1. Implement the IPipeline Interface

```cpp
class MyCustomPipeline : public IPipeline {
public:
    MyCustomPipeline() : m_initialized(false) {}
    
    // Core interface
    bool initialize() override {
        m_initialized = true;
        return true;
    }
    
    void shutdown() override {
        m_initialized = false;
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    // Animation interface
    void SetAnimTime(float time) override {
        m_animTime = time;
        // Apply to your pipeline
    }
    
    void SetMorphWeight(float weight) override {
        m_morphWeight = weight;
        // Apply to your pipeline
    }
    
    void SetModuleVisibility(float visibility) override {
        m_moduleVisibility = visibility;
        // Apply to your pipeline
    }
    
    void SetLODLevel(int level) override {
        m_lodLevel = level;
        // Apply to your pipeline
    }
    
    void SetWeaponFiring(bool firing) override {
        m_weaponFiring = firing;
        // Apply to your pipeline
    }
    
    void SetEffectsActive(bool active) override {
        m_effectsActive = active;
        // Apply to your pipeline
    }
    
    // Custom parameter interface
    void SetParameter(const std::string& name, const std::any& value) override {
        m_customParams[name] = value;
    }
    
    std::any GetParameter(const std::string& name) const override {
        auto it = m_customParams.find(name);
        return it != m_customParams.end() ? it->second : std::any{};
    }
    
    bool HasParameter(const std::string& name) const override {
        return m_customParams.find(name) != m_customParams.end();
    }
    
    // Metadata
    std::string GetName() const override {
        return "MyCustomPipeline";
    }
    
    std::string GetVersion() const override {
        return "1.0.0";
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {"custom_param1", "custom_param2", "custom_param3"};
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {"idle", "walk", "run", "custom_action"};
    }
    
private:
    bool m_initialized;
    float m_animTime;
    float m_morphWeight;
    float m_moduleVisibility;
    int m_lodLevel;
    bool m_weaponFiring;
    bool m_effectsActive;
    std::unordered_map<std::string, std::any> m_customParams;
};
```

### 2. Register Your Pipeline

```cpp
// In your initialization code
void registerMyCustomPipeline() {
    auto& factory = PipelineFactory::getInstance();
    
    factory.registerPipeline("my_custom", []() -> std::unique_ptr<IPipeline> {
        return std::make_unique<MyCustomPipeline>();
    });
}
```

### 3. Use Your Pipeline

```cpp
// Load your pipeline
imageGenerator.loadPipeline("my_custom");

// Switch to your pipeline
imageGenerator.switchPipeline("my_custom");

// Set custom parameters
imageGenerator.setPipelineParameter("custom_param1", 42.0f);
imageGenerator.setPipelineParameter("custom_param2", "hello");
```

## Built-in Pipelines

### MechPipeline

Designed for mechanical/robotic assets:

- **Parameters**: `anim_time`, `morph_weight`, `module_visibility`, `lod_level`, `weapon_firing`, `effects_active`
- **Animations**: `idle`, `walk`, `run`, `attack`, `defend`, `special`
- **Use Case**: Mechs, robots, vehicles, mechanical entities

### CharacterPipeline

Designed for character/npc assets:

- **Parameters**: `expression`, `pose`, `emotion`, `action`, `gesture`, `speech`
- **Animations**: `idle`, `walk`, `talk`, `gesture`, `emote`, `action`
- **Use Case**: Characters, NPCs, creatures, humanoid entities

## Pipeline Configuration

### JSON Configuration Format

```json
{
  "pipeline_type": "mech",
  "pipeline_name": "MechPipeline",
  "pipeline_version": "1.0.0",
  "parameters": {
    "morph_weight": 0.5,
    "module_visibility": 1.0,
    "lod_level": 2,
    "weapon_firing": false,
    "effects_active": true,
    "custom_param1": 42.0,
    "custom_param2": "hello"
  },
  "custom_config": {
    "additional_setting": "value"
  }
}
```

### Loading/Saving Configuration

```cpp
// Save current pipeline configuration
imageGenerator.savePipelineConfig("my_pipeline_config.json");

// Load pipeline from configuration
imageGenerator.loadPipelineConfig("my_pipeline_config.json");
```

## UI Integration

The enhanced UI includes a **Pipeline Management** section that provides:

- **Current Pipeline Info**: Shows loaded pipeline name, version, and capabilities
- **Pipeline Selection**: Dropdown to switch between available pipelines
- **Parameter Display**: Shows supported parameters and animations
- **Configuration Management**: Save/load pipeline configurations

### UI Features

1. **Pipeline Status**: Shows current pipeline with color coding
2. **Parameter Browser**: Tree view of supported parameters
3. **Animation Browser**: List of supported animations
4. **Configuration Tools**: Save/load pipeline settings
5. **Dynamic Switching**: Real-time pipeline switching

## Advanced Usage

### Custom Parameter Mapping

You can map the standard animation interface to your custom parameters:

```cpp
void SetMorphWeight(float weight) override {
    // Map to your custom parameter
    m_customParams["expression"] = weight;
    m_customParams["intensity"] = weight * 2.0f;
}
```

### Timeline Integration

The system automatically integrates with the timeline system:

```cpp
// Timeline evaluation automatically calls pipeline methods
float morphWeight = AnimationUtils::evaluateTimeline(timeline, time, "morph_weight");
pipeline->SetMorphWeight(morphWeight);
```

### Multi-Pipeline Support

You can create specialized pipelines for different asset types:

```cpp
// Mech assets
imageGenerator.loadPipeline("mech");
imageGenerator.setPipelineParameter("weapon_firing", true);

// Character assets  
imageGenerator.switchPipeline("character");
imageGenerator.setPipelineParameter("expression", 0.8f);

// Custom assets
imageGenerator.switchPipeline("my_custom");
imageGenerator.setPipelineParameter("custom_param1", 42.0f);
```

## Performance Considerations

### Pipeline Switching

- Pipeline switching is designed to be lightweight
- Only necessary state is preserved during switches
- Unused pipelines are automatically cleaned up

### Memory Management

- Pipelines are created on-demand
- Automatic cleanup when switching pipelines
- Configurable cache size for frequently used pipelines

### Thread Safety

- All pipeline operations are thread-safe
- Factory registration is protected by mutex
- Pipeline manager operations are atomic

## Extension Points

### Adding New Pipeline Types

1. Implement `IPipeline` interface
2. Register with `PipelineFactory`
3. Add UI support if needed
4. Create configuration templates

### Custom Animation Systems

1. Override animation interface methods
2. Map to your animation system
3. Implement parameter validation
4. Add custom metadata

### Integration with External Systems

1. Implement parameter translation
2. Add external system hooks
3. Create configuration adapters
4. Handle system-specific features

## Example: Vehicle Pipeline

```cpp
class VehiclePipeline : public IPipeline {
public:
    // Map standard interface to vehicle-specific parameters
    void SetMorphWeight(float weight) override {
        m_engineIntensity = weight;  // Engine RPM
    }
    
    void SetModuleVisibility(float visibility) override {
        m_gearPosition = visibility;  // Gear position
    }
    
    void SetLODLevel(int level) override {
        m_damageLevel = level;  // Damage state
    }
    
    void SetWeaponFiring(bool firing) override {
        m_weaponActive = firing;  // Weapon systems
    }
    
    std::vector<std::string> GetSupportedParameters() const override {
        return {"engine_intensity", "gear_position", "damage_level", 
                "weapon_active", "lights_on", "horn_active"};
    }
    
    std::vector<std::string> GetSupportedAnimations() const override {
        return {"idle", "drive", "reverse", "turn", "brake", "accelerate"};
    }
};
```

This dynamic pipeline system provides maximum flexibility while maintaining a consistent interface for animation generation and sprite sheet creation. 