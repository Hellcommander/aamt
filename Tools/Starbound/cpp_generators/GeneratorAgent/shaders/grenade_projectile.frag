#version 450 core

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vTexCoord;
in vec3 vViewDir;
in float vFuseProgress;

uniform sampler2D uTexture;
uniform vec4 uLiquidColor;
uniform vec3 uGlowColor;
uniform float uNoiseScale;
uniform float uNoiseSpeed;
uniform float uGlowIntensity;
uniform float uFuseTime;
uniform float uTime;

out vec4 fragColor;

// Noise function for animated effects
float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

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
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewDir);
    
    // Sample base texture
    vec4 texColor = texture(uTexture, vTexCoord);
    
    // Calculate rim lighting
    float rim = 1.0 - max(dot(normal, viewDir), 0.0);
    rim = pow(rim, 2.0);
    
    // Base color from liquid
    vec3 baseColor = uLiquidColor.rgb;
    
    // Add animated noise for liquid movement
    float liquidNoise = smoothNoise(vTexCoord * uNoiseScale + uTime * uNoiseSpeed);
    baseColor *= 0.8 + liquidNoise * 0.4;
    
    // Add glow based on fuse progress
    float fuseGlow = sin(vFuseProgress * 20.0) * 0.5 + 0.5;
    baseColor += uGlowColor * fuseGlow * uGlowIntensity;
    
    // Add emission
    baseColor += uGlowColor * uGlowIntensity;
    
    // Add trail effect for projectile
    float trailIntensity = 1.0 - vFuseProgress;
    baseColor += uGlowColor * trailIntensity * 0.3;
    
    // Add pulsing effect as fuse runs out
    float pulse = sin(uTime * 10.0 + vFuseProgress * 50.0) * 0.3 + 0.7;
    baseColor *= pulse;
    
    // Apply transparency
    float alpha = uLiquidColor.a * (0.7 + liquidNoise * 0.3);
    
    // Add fade effect for trail
    if (vFuseProgress > 0.8) {
        alpha *= 1.0 - (vFuseProgress - 0.8) * 5.0;
    }
    
    fragColor = vec4(baseColor, alpha);
} 