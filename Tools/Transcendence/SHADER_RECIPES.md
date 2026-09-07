# Shield Shader Recipes

Production-ready shader code for shield visuals with rim, pulse, distortion, and hit feedback.

## Core Shield Shader (GLSL Pseudocode)

### Vertex Shader

```glsl
#version 330 core

in vec3 position;
in vec2 uv;

uniform mat4 modelViewProjection;
uniform vec3 shieldCenter;  // World position of shield center
uniform float time;

out vec2 fragUV;
out vec3 worldPos;
out vec3 viewDir;

void main() {
    vec4 worldPosition = vec4(position, 1.0);
    worldPos = worldPosition.xyz;
    
    fragUV = uv;
    viewDir = normalize(worldPosition.xyz - shieldCenter);
    
    gl_Position = modelViewProjection * worldPosition;
}
```

### Fragment Shader

```glsl
#version 330 core

in vec2 fragUV;
in vec3 worldPos;
in vec3 viewDir;

uniform vec3 shieldCenter;
uniform float radius;
uniform float thickness;
uniform vec3 baseColor;
uniform vec3 glowColor;
uniform float pulseFrequency;
uniform float pulseStrength;
uniform float distortionStrength;
uniform float waveFrequency;
uniform float waveSpeed;
uniform float time;
uniform float visualIntensity;  // 0.0-1.0 based on shield strength
uniform float hitFlashIntensity;  // 0.0-1.0 for hit flash
uniform vec3 hitPosition;  // World position of last hit
uniform float hitFlashDuration;
uniform float alpha;

out vec4 fragColor;

// Noise function for distortion
float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

// Smooth noise
float smoothNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = noise(i);
    float b = noise(i + vec2(1.0, 0.0));
    float c = noise(i + vec2(0.0, 1.0));
    float d = noise(i + vec2(1.0, 1.0));
    
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void main() {
    // Calculate distance from shield center
    float dist = length(worldPos - shieldCenter);
    
    // Rim mask (outer edge)
    float rim = smoothstep(radius, radius - thickness, dist);
    
    // Core mask (inner glow)
    float coreMask = smoothstep(radius - thickness * 0.6, 0.0, dist);
    
    // Pulse animation
    float pulse = 0.5 + 0.5 * sin(time * pulseFrequency * 6.28318);
    pulse = mix(1.0, pulse, pulseStrength);
    
    // Distortion effect
    float wave = sin(dist * waveFrequency - time * waveSpeed);
    float distortion = wave * distortionStrength * coreMask;
    vec2 uvOffset = fragUV + normalize(worldPos - shieldCenter).xy * distortion * 0.1;
    
    // Hit flash effect
    float hitDist = length(worldPos - hitPosition);
    float hitFlash = exp(-hitDist * 10.0) * hitFlashIntensity;
    
    // Combine colors
    vec3 color = mix(baseColor, glowColor, pulse * coreMask);
    color = mix(color, vec3(1.0, 1.0, 1.0), hitFlash);  // White flash on hit
    
    // Apply visual intensity (shield strength)
    color *= visualIntensity;
    
    // Final alpha
    float finalAlpha = rim * alpha * visualIntensity;
    
    fragColor = vec4(color, finalAlpha);
}
```

## Exposed Shader Parameters

### Visual Parameters
- `radius`: Shield radius (typically 1.0-2.0 relative to ship size)
- `thickness`: Rim thickness (0.0-1.0)
- `baseColor`: Base shield color (RGB)
- `glowColor`: Glow/core color (RGB)
- `alpha`: Overall transparency (0.0-1.0)

### Animation Parameters
- `pulseFrequency`: Pulse frequency in Hz (default: 0.9)
- `pulseStrength`: Pulse intensity (0.0-1.0, default: 0.5)
- `time`: Current time in seconds

### Distortion Parameters
- `distortionStrength`: Distortion intensity (0.0-1.0, 0.0 = none)
- `waveFrequency`: Distortion wave frequency (default: 4.0)
- `waveSpeed`: Distortion wave speed (default: 2.0)

### Runtime Parameters
- `visualIntensity`: Shield strength ratio (0.0-1.0)
- `hitFlashIntensity`: Hit flash intensity (0.0-1.0)
- `hitPosition`: World position of last hit (xyz)
- `hitFlashDuration`: Hit flash duration in seconds

## HLSL Version (DirectX)

```hlsl
// Shield.fx

float4x4 WorldViewProjection;
float3 ShieldCenter;
float Radius;
float Thickness;
float3 BaseColor;
float3 GlowColor;
float PulseFrequency;
float PulseStrength;
float DistortionStrength;
float WaveFrequency;
float WaveSpeed;
float Time;
float VisualIntensity;
float HitFlashIntensity;
float3 HitPosition;
float Alpha;

struct VS_INPUT {
    float3 Position : POSITION;
    float2 UV : TEXCOORD0;
};

struct PS_INPUT {
    float4 Position : SV_POSITION;
    float2 UV : TEXCOORD0;
    float3 WorldPos : TEXCOORD1;
    float3 ViewDir : TEXCOORD2;
};

PS_INPUT VS_Main(VS_INPUT input) {
    PS_INPUT output;
    float4 worldPos = float4(input.Position, 1.0);
    output.WorldPos = worldPos.xyz;
    output.UV = input.UV;
    output.ViewDir = normalize(worldPos.xyz - ShieldCenter);
    output.Position = mul(worldPos, WorldViewProjection);
    return output;
}

float Noise(float2 p) {
    return frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453);
}

float4 PS_Main(PS_INPUT input) : SV_Target {
    float dist = length(input.WorldPos - ShieldCenter);
    
    // Rim mask
    float rim = smoothstep(Radius, Radius - Thickness, dist);
    
    // Core mask
    float coreMask = smoothstep(Radius - Thickness * 0.6, 0.0, dist);
    
    // Pulse
    float pulse = 0.5 + 0.5 * sin(Time * PulseFrequency * 6.28318);
    pulse = lerp(1.0, pulse, PulseStrength);
    
    // Distortion
    float wave = sin(dist * WaveFrequency - Time * WaveSpeed);
    float distortion = wave * DistortionStrength * coreMask;
    float2 uvOffset = input.UV + normalize(input.WorldPos - ShieldCenter).xy * distortion * 0.1;
    
    // Hit flash
    float hitDist = length(input.WorldPos - HitPosition);
    float hitFlash = exp(-hitDist * 10.0) * HitFlashIntensity;
    
    // Color
    float3 color = lerp(BaseColor, GlowColor, pulse * coreMask);
    color = lerp(color, float3(1.0, 1.0, 1.0), hitFlash);
    color *= VisualIntensity;
    
    float finalAlpha = rim * Alpha * VisualIntensity;
    
    return float4(color, finalAlpha);
}

technique ShieldTechnique {
    pass Pass0 {
        VertexShader = compile vs_3_0 VS_Main();
        PixelShader = compile ps_3_0 PS_Main();
    }
}
```

## Sprite Strip Fallback

For engines that don't support shaders, bake shield animations into sprite strips:

### Generation Process
1. Render 8-16 frames of shield animation
2. Each frame shows rim + pulse at different phases
3. Use additive blending for glow effect
4. Export as PNG strip (horizontal or vertical)

### Usage
```glsl
// Simple sprite strip shader
uniform sampler2D shieldStrip;
uniform float frameCount;
uniform float time;
uniform float pulseSpeed;

void main() {
    float frame = mod(time * pulseSpeed, frameCount);
    float frameIndex = floor(frame);
    float2 uv = fragUV;
    uv.x = (uv.x + frameIndex) / frameCount;
    
    vec4 color = texture(shieldStrip, uv);
    color.a *= visualIntensity;
    fragColor = color;
}
```

## Performance Optimizations

### LOD (Level of Detail)
- **High**: Full shader with distortion, full particle count
- **Medium**: Simplified shader, reduced particles
- **Low**: Sprite strip only, minimal particles

### Batching
- Batch shields by shader/material
- Use instancing for multiple shields
- Pool particle systems

### Shader Optimizations
- Use lower precision where possible (`mediump` in GLSL)
- Simplify noise functions for mobile
- Disable distortion on low-end devices
- Use texture lookups instead of procedural noise if needed

## Integration Notes

### Unity Integration
```csharp
public class ShieldShaderController : MonoBehaviour {
    public Material shieldMaterial;
    public ShieldInstance shield;
    
    void Update() {
        shieldMaterial.SetFloat("_VisualIntensity", shield.visualIntensity);
        shieldMaterial.SetFloat("_HitFlashIntensity", shield.hitFlashIntensity);
        shieldMaterial.SetVector("_HitPosition", lastHitPosition);
        shieldMaterial.SetFloat("_Time", Time.time);
    }
}
```

### Unreal Integration
```cpp
// In shield actor
void AShieldActor::UpdateShaderParameters() {
    if (ShieldMaterialInstance) {
        ShieldMaterialInstance->SetScalarParameterValue("VisualIntensity", ShieldInstance->visualIntensity);
        ShieldMaterialInstance->SetScalarParameterValue("HitFlashIntensity", ShieldInstance->hitFlashIntensity);
        ShieldMaterialInstance->SetVectorParameterValue("HitPosition", LastHitPosition);
    }
}
```

## Testing Checklist

- [ ] Rim visible at all shield strengths
- [ ] Pulse animation smooth and visible
- [ ] Distortion effect works (if enabled)
- [ ] Hit flash appears at correct position
- [ ] Visual intensity scales with shield strength
- [ ] Alpha fades correctly when shield breaks
- [ ] Performance acceptable on target hardware
- [ ] LOD switching works correctly

