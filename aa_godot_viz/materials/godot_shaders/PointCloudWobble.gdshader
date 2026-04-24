shader_type spatial;
//render_mode unshaded, cull_disabled;

uniform float amplitude : hint_range(0.0, 0.15) = 0.016;
uniform float speed : hint_range(0.0, 100.0) = 1.2;

// Cold → Warm palette. COLOR.a carries depth (0 = root, 1 = tip).
uniform vec4 cold_root : source_color = vec4(0.15, 0.25, 0.50, 1.0);
uniform vec4 cold_tip  : source_color = vec4(0.25, 0.55, 0.65, 1.0);
uniform vec4 warm_root : source_color = vec4(0.38, 0.22, 0.09, 1.0);
uniform vec4 warm_tip  : source_color = vec4(0.18, 0.65, 0.28, 1.0);
uniform float param1 : hint_range(0.0, 1.0) = 0.5;
uniform float metallic  : hint_range(0.0, 1.0) = 0.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.8;

float hash(vec3 p) {
    // Nonlinear scramble — breaks the planar coherence of a plain dot product.
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

void vertex() {
	vec3 base = MODEL_MATRIX[3].xyz;
    float phase = hash(base) * 6.2832; // map [0,1] → [0, 2π]

    VERTEX += vec3(
        sin(TIME * speed       + phase)        * amplitude,
        sin(TIME * speed * 0.8 + phase * 1.3)  * amplitude * 0.6,
        cos(TIME * speed * 0.9 + phase)        * amplitude
    );
}

void fragment() {
    float depth = COLOR.a;
    vec3 cold = mix(cold_root.rgb, cold_tip.rgb, depth);
    vec3 warm = mix(warm_root.rgb, warm_tip.rgb, depth);
    ALBEDO     = mix(cold, warm, param1);
    METALLIC   = metallic;
    ROUGHNESS  = roughness;
}