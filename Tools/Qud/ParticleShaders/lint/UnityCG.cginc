// Minimal stand-in for Unity's UnityCG.cginc, enough to lint-compile a Qud Shader Library effect with fxc.
// Only what QudFX.cginc and the ShaderKit template use: the full-screen vertex pass-through. Unity itself still
// compiles the real thing when Build-QudShaderBundle.ps1 runs.
#ifndef UNITY_CG_INCLUDED
#define UNITY_CG_INCLUDED
struct appdata_img { float4 vertex : POSITION; half2 texcoord : TEXCOORD0; };
struct v2f_img { float4 pos : SV_POSITION; half2 uv : TEXCOORD0; };
v2f_img vert_img(appdata_img v) { v2f_img o; o.pos = v.vertex; o.uv = v.texcoord; return o; }
#endif
