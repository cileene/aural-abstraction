shader_type spatial;
render_mode cull_back;

uniform sampler2D grow_texture;
uniform sampler2D albedo_texture;
uniform sampler2D normal_texture;
uniform sampler2D ems_texture;
uniform sampler2D noise_texture;
uniform sampler2D rounghess_texture;
uniform float ems;

uniform float distortionVertex : hint_range(0.0, 0.3, 0.005) = 0.03;
uniform float speedVertex : hint_range(0.0, 1.0, 0.005) = 0.5;
uniform sampler2D noiseVertex;
uniform vec3 offset_direction = vec3(1.0, 0.0, 0.0); // 偏移方向
uniform float offset_strength = 0.1; // 偏移强度
uniform float shrink_strength = 0.5; // 缩小强度
uniform sampler2D add_texture;
uniform sampler2D add_ems_texture;
uniform bool alpha_apply;

void vertex() {
    // 顶点位移（使用顶点噪声）
    float noiseVal = (texture(noiseVertex, UV + (TIME * speedVertex)).r * 2.0) - 1.0;
    vec3 displacement = NORMAL * noiseVal * distortionVertex;
    VERTEX += displacement;

    // 采样生长纹理（UV2）
    float grow_val = texture(grow_texture, UV2).r;

    // 对生长值小于0.03的部分进行偏移和缩放
    if (grow_val < 0.03) {
        float offset_factor = (0.3 - grow_val) / 0.3;
        VERTEX.x += offset_direction.x * offset_strength * offset_factor;
        VERTEX.y += offset_direction.y * offset_strength * offset_factor;
        VERTEX *= (0.8 - shrink_strength * offset_factor);
    }
}

void fragment() {
    // --- 修改点：将视图空间顶点转换为世界空间，用于噪声采样 ---
    vec4 world_pos = INV_VIEW_MATRIX * vec4(VERTEX, 1.0);
    // 使用世界空间的 xz 平面作为噪声纹理坐标（可根据需要改为 xy 或 yz）
    vec2 uv = world_pos.xz;
    // 保留原有的时间动画效果
    uv += TIME * 0.5 * offset_direction.xy;
    float noise = texture(noise_texture, uv).r;

    // 生长纹理处理（基于UV）
    vec4 grow_color = texture(grow_texture, UV);
    grow_color.r += noise * 0.3;

    if (grow_color.r < 0.3) {
        grow_color.r -= noise;
        if (grow_color.r < 0.01) {
            discard;
        }
    }

    // 基础纹理采样
    vec4 albedo_color = texture(albedo_texture, UV);
    vec4 normal_color = texture(normal_texture, UV);
    NORMAL_MAP = normal_color.rgb;

    vec4 ems_color = texture(ems_texture, UV);
    vec4 add_color = texture(add_texture, UV);
    vec4 add_ems = texture(add_ems_texture, UV);

    albedo_color *= add_color;
    ems_color *= add_ems;

    // 根据生长值混合颜色与自发光
    ALBEDO = mix(albedo_color.rgb, ems_color.rgb, 1.0 - smoothstep(0.3, 0.4, grow_color.r));
    EMISSION = mix(ems_color.rgb * ems, vec3(0.0), smoothstep(0.3, 0.4, grow_color.r));

    // 粗糙度
    vec4 rou_color = texture(rounghess_texture, UV);
    ROUGHNESS = rou_color.r;

    if (alpha_apply) {
        ALPHA = albedo_color.a;
    }
}