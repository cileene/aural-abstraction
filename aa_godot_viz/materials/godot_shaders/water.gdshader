shader_type spatial;

render_mode unshaded, cull_disabled, depth_draw_always;

uniform sampler2D screen_texture : hint_screen_texture;

uniform sampler2D normal1tex : hint_normal;
uniform sampler2D normal2tex : hint_normal;

uniform vec2 speed1 = vec2(0.01, 0.0);
uniform vec2 speed2 = vec2(0.0, 0.01);

uniform float strength = 0.1;
uniform float distortion = 0.2;

uniform vec3 water_color : source_color = vec3(0.0, 0.05, 0.08);

varying vec2 uv1;
varying vec2 uv2;

void vertex() {
	uv1 = UV + speed1 * TIME;
	uv2 = UV + speed2 * TIME;

	float wave = sin(VERTEX.x * 1.0 + TIME * 1.0) * 0.1;
	wave += cos(VERTEX.z * 1.0 + TIME * 1.0) * 0.1;

	VERTEX.y += wave;
}

void fragment() {

	vec3 normal1 = texture(normal1tex, uv1).rgb;
	vec3 normal2 = texture(normal2tex, uv2).rgb;

	vec2 distortion_uv = SCREEN_UV + ((normal1.xy + normal2.xy - 1.0) * distortion);

	vec3 screen_color = texture(screen_texture, distortion_uv).rgb;

	
	vec3 final_color = mix(screen_color, water_color,0.6);

	ALBEDO = final_color;
	ALPHA = 0.8;
}