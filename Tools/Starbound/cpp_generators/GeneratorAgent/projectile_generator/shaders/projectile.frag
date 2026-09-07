#version 450 core

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vTexCoord;
in vec3 vViewDir;

uniform sampler2D uTexture;
uniform vec3 uCoreCol;
uniform vec3 uEdgeCol;
uniform float uTime;

#ifdef USE_ADDITIVE
layout(blend_support_add_amd) out vec4 fragColor;
#else
out vec4 fragColor;
#endif

void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewDir);
    
    // Sample texture
    vec4 texColor = texture(uTexture, vTexCoord);
    
    // Calculate rim lighting for better visibility
    float rim = 1.0 - max(dot(normal, viewDir), 0.0);
    rim = pow(rim, 3.0);
    
    // Mix core and edge colors based on rim
    vec3 baseColor = mix(uCoreCol, uEdgeCol, rim);
    
    #ifdef USE_EMISSION
    // Add emission for fireballs and magical projectiles
    float emission = sin(uTime * 5.0) * 0.3 + 0.7;
    baseColor *= emission;
    #endif
    
    #ifdef USE_ADDITIVE
    // Additive blending for lasers
    fragColor = vec4(baseColor * texColor.rgb, texColor.a * 0.8);
    #else
    // Standard blending
    fragColor = vec4(baseColor * texColor.rgb, texColor.a);
    #endif
} 