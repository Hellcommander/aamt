#version 450 core

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vTexCoord;
in vec3 vViewDir;

uniform sampler2D uTexture;
uniform vec3 uCasingColorPrimary;
uniform vec3 uCasingColorSecondary;
uniform vec4 uLiquidColor;
uniform vec3 uGlowColor;
uniform float uNoiseScale;
uniform float uNoiseSpeed;
uniform float uGlowIntensity;
uniform float uEmissivePower;
uniform float uTransparency;
uniform float uRefractionIndex;
uniform float uMetallicness;
uniform float uRoughness;
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
    rim = pow(rim, 3.0);
    
    // Base color from casing
    vec3 baseColor = mix(uCasingColorPrimary, uCasingColorSecondary, rim);
    
    #ifdef USE_GLASS
    // Glass material with refraction
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 5.0);
    baseColor = mix(baseColor, vec3(1.0), fresnel * 0.3);
    
    // Add refraction distortion
    vec2 refractedUV = vTexCoord + normal.xy * 0.1;
    vec4 refractedColor = texture(uTexture, refractedUV);
    baseColor = mix(baseColor, refractedColor.rgb, 0.2);
    #endif
    
    #ifdef USE_METAL
    // Metal material with reflection
    float metallic = uMetallicness;
    float roughness = uRoughness;
    
    // Simulate metallic reflection
    vec3 reflection = reflect(-viewDir, normal);
    float reflectionIntensity = 1.0 - roughness;
    baseColor = mix(baseColor, vec3(0.8), reflectionIntensity * metallic);
    #endif
    
    #ifdef USE_CERAMIC
    // Ceramic material with subtle texture
    float ceramicNoise = smoothNoise(vTexCoord * uNoiseScale);
    baseColor *= 0.9 + ceramicNoise * 0.2;
    #endif
    
    // Add liquid color for transparent areas
    float liquidMask = texColor.a;
    baseColor = mix(baseColor, uLiquidColor.rgb, liquidMask * uLiquidColor.a);
    
    // Add glow effects based on grenade type
    #ifdef GRENADE_FIRE
    float fireGlow = sin(uTime * 3.0) * 0.3 + 0.7;
    baseColor += uGlowColor * fireGlow * uGlowIntensity;
    #endif
    
    #ifdef GRENADE_ACID
    float acidGlow = sin(uTime * 2.0) * 0.2 + 0.8;
    baseColor += uGlowColor * acidGlow * uGlowIntensity;
    #endif
    
    #ifdef GRENADE_FROST
    float frostGlow = sin(uTime * 1.5) * 0.4 + 0.6;
    baseColor += uGlowColor * frostGlow * uGlowIntensity;
    #endif
    
    #ifdef GRENADE_SHOCK
    float shockGlow = sin(uTime * 8.0) * 0.5 + 0.5;
    baseColor += uGlowColor * shockGlow * uGlowIntensity;
    #endif
    
    #ifdef GRENADE_HEALING
    float healingGlow = sin(uTime * 2.5) * 0.3 + 0.7;
    baseColor += uGlowColor * healingGlow * uGlowIntensity;
    #endif
    
    // Add emission
    baseColor += uGlowColor * uEmissivePower;
    
    // Apply transparency
    float alpha = 1.0 - (liquidMask * uTransparency);
    
    fragColor = vec4(baseColor, alpha);
} 