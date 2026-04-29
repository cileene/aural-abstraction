using Godot;

namespace aa_godot_viz.scripts;

public class _SceneConfig
{
        public TreeGenerator3D TreeGenerator;
        public Node3D Bubble;
        public VBoxContainer UI;
        public Camera3D Camera;
        public WorldEnvironment WorldEnvironment;
        public FastNoiseLite Noise;
        public PackedScene Cube;
        public float LightSpeed, LightLifetime, LightIntensity, LightRange;
        public Color LightColor;
}