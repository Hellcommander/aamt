# Shield Aura Shader Recipes

Production-ready shader code for solar wind shield aura: alpha noise, wind streams, distortion, and orbital particles.

## Core Aura Shader (GLSL)

### Vertex Shader

```glsl
#version 330 core

in vec3 position;
in vec2 uv;

uniform mat4 modelViewProjection;
uniform vec3 auraCenter;  // World position of aura center
uniform float time;
uniform float shieldHP;  // 0.0-1.0 shield strength

out vec2 fragUV;
out vec3 worldPos;
out float shieldStrength;

void main() {
    vec4 worldPosition = vec4(position, 1.0);
    worldPos = worldPosition.xyz;
    fragUV = uv;
    shieldStrength = shieldHP;
    
    gl_Position = modelViewProjection * worldPosition;
}
```

### Fragment Shader - Alpha Noise Layer

```glsl
#version 330 core

in vec2 fragUV;
in vec3 worldPos;
in float shieldStrength;

uniform vec3 auraCenter;
uniform float radiusMin;
uniform float radiusMax;
uniform float alphaNoiseSpeed;
uniform float alphaNoiseScale;
uniform float alphaNoiseStrength;
uniform float time;
uniform vec3 baseColor;
uniform float distortionStrength;
uniform float distortionFrequency;
uniform sampler2D noiseTexture;

out vec4 fragColor;

// Noise function
float noise(vec2 p) {
    return texture(noiseTexture, p).r;
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

// Radial falloff
float radialFalloff(float dist, float radius, float curve) {
    float t = dist / radius;
    if (curve == 0.0) {  // linear
        return 1.0 - t;
    } else if (curve == 1.0) {  // exponential
        return exp(-t * 3.0);
    } else if (curve == 2.0) {  // smooth
        return 1.0 - smoothstep(0.0, 1.0, t);
    } else {  // step
        return step(t, 0.8);
    }
}

void main() {
    // Calculate distance from center
    float dist = length(worldPos.xy - auraCenter.xy);
    
    // Scale radius with shield HP
    float currentRadius = mix(radiusMin, radiusMax, shieldStrength);
    
    // Alpha noise - animated
    vec2 noiseUV = fragUV * alphaNoiseScale + vec2(time * alphaNoiseSpeed * 0.1, time * alphaNoiseSpeed * 0.15);
    float alphaNoise = smoothNoise(noiseUV);
    alphaNoise = alphaNoise * 2.0 - 1.0;  // -1 to 1
    alphaNoise = alphaNoise * alphaNoiseStrength;
    
    // Base alpha from radial falloff
    float baseAlpha = radialFalloff(dist, currentRadius, 2.0);  // smooth curve
    
    // Combine with noise
    float finalAlpha = baseAlpha * (1.0 + alphaNoise);
    finalAlpha = clamp(finalAlpha, 0.0, 1.0);
    
    // Scale alpha with shield HP
    finalAlpha *= shieldStrength;
    
    // Color
    vec3 color = baseColor;
    
    // Distortion effect (subtle)
    float distortion = sin(dist * distortionFrequency - time * 2.0) * distortionStrength;
    vec2 uvOffset = fragUV + normalize(worldPos.xy - auraCenter.xy) * distortion * 0.05;
    
    fragColor = vec4(color, finalAlpha);
}
```

## Solar Wind Streams Shader

```glsl
// Additional layer for wind streaks
void main() {
    float dist = length(worldPos.xy - auraCenter.xy);
    float currentRadius = mix(radiusMin, radiusMax, shieldStrength);
    
    // Wind direction (outward)
    vec2 windDir = normalize(worldPos.xy - auraCenter.xy);
    
    // Wind noise - directional
    vec2 windUV = fragUV + windDir * time * windSpeed;
    float windNoise = smoothNoise(windUV * windNoiseScale);
    
    // Wind mask - radial gradient
    float windMask = radialFalloff(dist, currentRadius, 2.0);
    windMask = pow(windMask, 0.5);  // Sharper falloff
    
    // Wind alpha
    float windAlpha = windNoise * windMask * shieldStrength;
    
    // Wind color
    vec3 windColor = windColor * windAlpha;
    
    fragColor = vec4(windColor, windAlpha);
}
```

## Distortion Field Shader

```glsl
// Screen-space distortion pass
void main() {
    float dist = length(worldPos.xy - auraCenter.xy);
    float currentRadius = mix(radiusMin, radiusMax, shieldStrength);
    
    // Distortion mask - stronger near edge
    float distMask = 1.0 - radialFalloff(dist, currentRadius, 2.0);
    distMask = pow(distMask, 2.0);  // Stronger at edge
    
    // Distortion offset
    vec2 dir = normalize(worldPos.xy - auraCenter.xy);
    float wave = sin(dist * distortionFrequency - time * 2.0);
    vec2 offset = dir * wave * distortionStrength * distMask;
    
    // Sample background with offset
    vec2 screenUV = fragUV + offset * 0.1;
    vec4 background = texture(screenSampler, screenUV);
    
    // Apply distortion alpha
    float distAlpha = distMask * shieldStrength * 0.3;
    
    fragColor = mix(background, vec4(distortionColor, 1.0), distAlpha);
}
```

## Orbital Particles Shader

```glsl
// Particle system for orbital particles
struct Particle {
    vec2 position;
    float angle;
    float radius;
    float speed;
    float lifetime;
};

void main() {
    // Calculate particle position in orbit
    float angle = particleAngle + time * particleSpeed;
    vec2 particlePos = auraCenter.xy + vec2(cos(angle), sin(angle)) * particleRadius;
    
    // Add turbulence
    float turb = smoothNoise(vec2(angle * 2.0, time * 0.5)) * turbulence;
    particlePos += vec2(cos(angle + 1.57), sin(angle + 1.57)) * turb;
    
    // Distance from fragment to particle
    float dist = length(worldPos.xy - particlePos);
    
    // Particle alpha (fade with distance)
    float particleAlpha = exp(-dist * 20.0) * particleAlpha * shieldStrength;
    
    // Particle color
    vec3 color = baseColor;
    
    fragColor = vec4(color, particleAlpha);
}
```

## Projectile Orbit Behavior (Runtime)

```glsl
// In game engine or script
void UpdateProjectileInAura(Projectile proj, Aura aura, float dt) {
    vec2 dir = proj.position - aura.center;
    float dist = length(dir);
    
    // Check if in influence radius
    if (dist > aura.influenceRadius) {
        return;  // Not influenced
    }
    
    // Compute tangential vector (perpendicular to radial)
    vec2 radial = normalize(dir);
    vec2 tangent = vec2(-radial.y, radial.x);  // 90 degree rotation
    
    // Blend velocity toward tangential (orbit)
    float blend = aura.tangentialBlend * aura.gravityStrength * dt;
    proj.velocity = mix(proj.velocity, tangent * aura.orbitSpeed, blend);
    
    // Add inward pull (gravity well)
    vec2 inwardPull = -radial * aura.inwardPull * dt;
    proj.velocity += inwardPull;
    
    // Limit orbit time
    if (aura.orbitTime > 0.0) {
        proj.orbitTime += dt;
        if (proj.orbitTime > aura.orbitTime) {
            // Release projectile
            proj.inOrbit = false;
        }
    }
}
```

## Shield HP Scaling

```glsl
// Scale all properties with shield HP
uniform float shieldHP;  // 0.0-1.0

// Radius scaling
float currentRadius = mix(radiusMin, radiusMax, shieldHP);

// Alpha scaling
float alpha = baseAlpha * shieldHP;

// Speed scaling
float currentSpeed = mix(orbitSpeedMin, orbitSpeedMax, shieldHP);

// Distortion scaling
float currentDistortion = distortionStrength * shieldHP;
```

## HLSL Version (DirectX)

```hlsl
// ShieldAura.fx

float4x4 WorldViewProjection;
float3 AuraCenter;
float RadiusMin;
float RadiusMax;
float AlphaNoiseSpeed;
float AlphaNoiseScale;
float AlphaNoiseStrength;
float Time;
float ShieldHP;
float3 BaseColor;
float DistortionStrength;
float DistortionFrequency;
Texture2D NoiseTexture;
SamplerState NoiseSampler;

struct VS_INPUT {
    float3 Position : POSITION;
    float2 UV : TEXCOORD0;
};

struct PS_INPUT {
    float4 Position : SV_POSITION;
    float2 UV : TEXCOORD0;
    float3 WorldPos : TEXCOORD1;
    float ShieldStrength : TEXCOORD2;
};

PS_INPUT VS_Main(VS_INPUT input) {
    PS_INPUT output;
    float4 worldPos = float4(input.Position, 1.0);
    output.WorldPos = worldPos.xyz;
    output.UV = input.UV;
    output.ShieldStrength = ShieldHP;
    output.Position = mul(worldPos, WorldViewProjection);
    return output;
}

float Noise(float2 p) {
    return NoiseTexture.Sample(NoiseSampler, p).r;
}

float RadialFalloff(float dist, float radius) {
    float t = dist / radius;
    return 1.0 - smoothstep(0.0, 1.0, t);
}

float4 PS_Main(PS_INPUT input) : SV_Target {
    float dist = length(input.WorldPos.xy - AuraCenter.xy);
    float currentRadius = lerp(RadiusMin, RadiusMax, input.ShieldStrength);
    
    // Alpha noise
    float2 noiseUV = input.UV * AlphaNoiseScale + float2(Time * AlphaNoiseSpeed * 0.1, Time * AlphaNoiseSpeed * 0.15);
    float alphaNoise = Noise(noiseUV);
    alphaNoise = alphaNoise * 2.0 - 1.0;
    alphaNoise *= AlphaNoiseStrength;
    
    // Base alpha
    float baseAlpha = RadialFalloff(dist, currentRadius);
    float finalAlpha = baseAlpha * (1.0 + alphaNoise);
    finalAlpha = saturate(finalAlpha);
    finalAlpha *= input.ShieldStrength;
    
    float3 color = BaseColor;
    
    return float4(color, finalAlpha);
}

technique AuraTechnique {
    pass Pass0 {
        VertexShader = compile vs_3_0 VS_Main();
        PixelShader = compile ps_3_0 PS_Main();
    }
}
```

## Performance Optimizations

### LOD System
- **High**: Full shader with all layers, high particle count
- **Medium**: Simplified shader, reduced particles
- **Low**: Sprite strip only, minimal particles

### Batching
- Batch auras by shader/material
- Use instancing for multiple auras
- Pool particle systems

### Shader Optimizations
- Use lower precision where possible
- Simplify noise functions for mobile
- Disable distortion on low-end devices
- Use texture lookups instead of procedural noise if needed

## Integration Notes

### Unity

```csharp
public class ShieldAuraController : MonoBehaviour {
    public Material auraMaterial;
    public ShieldInstance shield;
    
    void Update() {
        float shieldHP = shield.currentStrength / shield.maxStrength;
        auraMaterial.SetFloat("_ShieldHP", shieldHP);
        auraMaterial.SetFloat("_Time", Time.time);
        auraMaterial.SetVector("_AuraCenter", transform.position);
        
        // Update radius
        float radius = Mathf.Lerp(radiusMin, radiusMax, shieldHP);
        auraMaterial.SetFloat("_CurrentRadius", radius);
    }
}
```

### Projectile Orbit Integration

```csharp
void OnTriggerEnter(Collider other) {
    if (other.CompareTag("Projectile")) {
        Projectile proj = other.GetComponent<Projectile>();
        if (proj != null) {
            proj.EnterAura(this);
        }
    }
}

void UpdateProjectile(Projectile proj, float dt) {
    Vector2 dir = proj.position - transform.position;
    float dist = dir.magnitude;
    
    if (dist > influenceRadius) return;
    
    // Tangential vector
    Vector2 radial = dir.normalized;
    Vector2 tangent = new Vector2(-radial.y, radial.x);
    
    // Blend toward orbit
    float blend = tangentialBlend * gravityStrength * dt;
    proj.velocity = Vector2.Lerp(proj.velocity, tangent * orbitSpeed, blend);
    
    // Inward pull
    proj.velocity -= radial * inwardPull * dt;
}
```

