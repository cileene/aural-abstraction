using Godot;

namespace aa_godot_viz.scripts;

//TODO: Split into multiple classes via the event system. Just take the inputs here.

public partial class SceneController : Node
{
    [Export] private TreeGenerator3D _treeGenerator; //TODO: not hooked up
    [Export] private Node3D _bubble; //TODO: not hooked up
    [Export] private VBoxContainer _uI; //TODO: not hooked up
    [Export] private Camera3D _camera; //TODO: not hooked up
    [Export] private WorldEnvironment _worldEnvironment; //TODO: not hooked up
    [Export] private FastNoiseLite _noise; //TODO: not hooked up
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
    [Export(PropertyHint.Range, "0,1")] private float _color;
    [Export(PropertyHint.Range, "0,1")] private float _spatiality;
    [Export(PropertyHint.Range, "0,1")] private float _composition;
    [Export(PropertyHint.Range, "0,1")] private float _shape;
    [Export(PropertyHint.Range, "0,1")] private float _material;
    

    private bool _sendLightRequested, _lightInFlight;

    public override void _Ready()
    {
        //PlaceObjectsWithNoise();
    }

    public override void _Process(double delta)
    {
        if (_sendLightRequested)
        {
            _sendLightRequested = false;
            _lightInFlight = true;
            SendLight(_camera, _lightSpeed, _lightLifetime, _lightIntensity, _lightRange, _lightColor);
        }
    }

    public override void _Input(InputEvent @event)
    {
        if (@event.IsActionPressed("Step") && !_lightInFlight)
        {
            EventSystem.RaiseImpulseSent();
            _sendLightRequested = true;
        }
    }

    //TODO: Move to separate RoomBuilder class
    private void PlaceObjectsWithNoise()
    {
        if (_noise == null || _cube == null)
        {
            GD.PrintErr("SceneController: missing exports.");
            return;
        }

        for (int x = 0; x < _gridSize; x++)
        for (int y = 0; y < _gridSize; y++)
        for (int z = 0; z < _gridSize; z++)
        {
            float value = (_noise.GetNoise3D(x, y, z) + 1f) / 2f;

            if (value > _threshold)
            {
                var instance = _cube.Instantiate<Node3D>();
                instance.Position = new Vector3(x, y, z) * _spacing;
                AddChild(instance);
            }
        }
    }

    //TODO: Move to separate LightImpulse class
    private void SendLight(Camera3D camera, float speed, float lifetime, float intensity, float range, Color color)
    {
        var lightInstance = new OmniLight3D
        {
            LightColor = color,
            LightEnergy = intensity,
            ShadowEnabled = true,
            OmniRange = range,
            OmniAttenuation = 2f
        };

        AddChild(lightInstance);

        lightInstance.GlobalPosition = camera.GlobalPosition;

        var direction = -camera.GlobalTransform.Basis.Z.Normalized();
        var endPosition = lightInstance.GlobalPosition + direction * speed * lifetime;

        var tween = CreateTween();
        tween.TweenProperty(lightInstance, "global_position", endPosition, lifetime)
            .SetTrans(Tween.TransitionType.Linear);
        tween.Parallel().TweenProperty(lightInstance, "light_energy", 0.0f, lifetime);
        tween.Finished += () =>
        {
            lightInstance.QueueFree();
            _lightInFlight = false;
        };
    }
}