#version 450 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform float uTime;
uniform float uFuseTime;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vTexCoord;
out vec3 vViewDir;
out float vFuseProgress;

void main() {
    vWorldPos = vec3(uModel * vec4(aPos, 1.0));
    vNormal = mat3(transpose(inverse(uModel))) * aNormal;
    vTexCoord = aTexCoord;
    
    vec4 viewPos = uView * vec4(vWorldPos, 1.0);
    vViewDir = normalize(-viewPos.xyz);
    
    // Calculate fuse progress for trail effects
    vFuseProgress = mod(uTime, uFuseTime) / uFuseTime;
    
    gl_Position = uProjection * viewPos;
} 