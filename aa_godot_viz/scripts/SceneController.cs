using Godot;

namespace aa_godot_viz.scripts;

public partial class SceneController : Node
{
    [Export] private TreeGenerator3D _treeGenerator;
    [Export] private Node3D _bubble;
    [Export] private VBoxContainer _uI;
    [Export] private Camera3D _camera;
    [Export] private WorldEnvironment _worldEnvironment;
    [Export] private FastNoiseLite _noise;
    [Export] private PackedScene _cube; // is this needed?
    [Export] private int _gridSize = 10; // leftover
    [Export] private float _spacing = 2f; // leftover
    [Export] private float _threshold = 0.5f; // leftover
    [Export] private float _lightSpeed = 1f;
    [Export] private float _lightLifetime = 5f;
    [Export] private float _lightIntensity = 1f;
    [Export] private float _lightRange = 30f;
    [Export] private Color _lightColor = Colors.White;

    [ExportCategory("Parameters")]
    [Export(PropertyHint.Range, "0,1")] private float _color = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _spatiality = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _composition = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _shape = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _material = 0.5f; //TODO: Not hooked up
    

    private bool _sendLightRequested, _lightInFlight;

    public override void _Ready()
    {
        HandleSceneConfig();
    }

    public override void _Input(InputEvent @event)
    {
        if (@event.IsActionPressed("Step"))
        {
            EventSystem.RaiseImpulseSent();
        }
    }
    
    private void HandleSceneConfig()
    {
        var config = new SceneConfig
        {
            TreeGenerator = _treeGenerator,
            Bubble = _bubble,
            UI = _uI,
            Camera = _camera,
            WorldEnvironment = _worldEnvironment,
            Noise = _noise,
            Cube = _cube,
            LightSpeed = _lightSpeed,
            LightLifetime = _lightLifetime,
            LightIntensity = _lightIntensity,
            LightRange = _lightRange,
            LightColor = _lightColor
        };
        EventSystem.RaiseSetSceneConfig(config);
    }
}