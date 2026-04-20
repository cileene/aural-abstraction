shader_type spatial;

// --- Material A ---
uniform sampler2D albedo_a    : source_color, hint_default_white;
uniform sampler2D normal_a    : hint_normal;
uniform sampler2D roughness_a : hint_default_white;
uniform sampler2D metallic_a  : hint_default_black;
uniform vec2 uv_scale_a       = vec2(1.0, 1.0);

// --- Material B ---
uniform sampler2D albedo_b    : source_color, hint_default_white;
uniform sampler2D normal_b    : hint_normal;
uniform sampler2D roughness_b : hint_default_white;
uniform sampler2D metallic_b  : hint_default_black;
uniform vec2 uv_scale_b       = vec2(1.0, 1.0);

// --- Material C ---
uniform sampler2D albedo_c    : source_color, hint_default_white;
uniform sampler2D normal_c    : hint_normal;
uniform sampler2D roughness_c : hint_default_white;
uniform sampler2D metallic_c  : hint_default_black;
uniform vec2 uv_scale_c       = vec2(1.0, 1.0);

// 0.0 = A, 0.5 = B, 1.0 = C
uniform float blend           : hint_range(0.0, 1.0) = 0.0;
uniform float normal_strength : hint_range(0.0, 2.0) = 1.0;
uniform vec4 tint             : source_color = vec4(1.0, 1.0, 1.0, 1.0);

void fragment() {
    float wa = clamp(1.0 - blend * 2.0,        0.0, 1.0);
    float wb = 1.0 - min(abs(blend - 0.5) * 2.0, 1.0);
    float wc = clamp((blend - 0.5) * 2.0,      0.0, 1.0);

    vec2 uv_a = UV * uv_scale_a;
    vec2 uv_b = UV * uv_scale_b;
    vec2 uv_c = UV * uv_scale_c;

    // Albedo — tint applied after blend
    vec3 blended_albedo = texture(albedo_a, uv_a).rgb * wa
                        + texture(albedo_b, uv_b).rgb * wb
                        + texture(albedo_c, uv_c).rgb * wc;
    ALBEDO = blended_albedo * tint.rgb;

    // Normals
    vec3 n_a = texture(normal_a, uv_a).rgb * 2.0 - 1.0;
    vec3 n_b = texture(normal_b, uv_b).rgb * 2.0 - 1.0;
    vec3 n_c = texture(normal_c, uv_c).rgb * 2.0 - 1.0;
    NORMAL_MAP = normalize(n_a * wa + n_b * wb + n_c * wc) * 0.5 + 0.5;
    NORMAL_MAP_DEPTH = normal_strength;

    // Roughness & Metallic
    ROUGHNESS = texture(roughness_a, uv_a).r * wa
              + texture(roughness_b, uv_b).r * wb
              + texture(roughness_c, uv_c).r * wc;

    METALLIC  = texture(metallic_a,  uv_a).r * wa
              + texture(metallic_b,  uv_b).r * wb
              + texture(metallic_c,  uv_c).r * wc;
}