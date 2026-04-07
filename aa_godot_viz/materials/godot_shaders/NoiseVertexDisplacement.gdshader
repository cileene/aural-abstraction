shader_type spatial;

uniform float height_scale = 0.5;
uniform float speed = 0.1;
uniform sampler2D displacement;
uniform vec4 albedo_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);

varying vec2 tex_position;

void fragment() {
	float height = texture(displacement, tex_position).r;
    ALBEDO = albedo_color.rgb * height;
}

void vertex() {
    tex_position = VERTEX.xz / 2.0 + 0.5;
    vec2 animated_uv = tex_position + vec2(TIME * speed, 0.0);
    float height = texture(displacement, animated_uv).r;
    VERTEX.y += height * height_scale;
}