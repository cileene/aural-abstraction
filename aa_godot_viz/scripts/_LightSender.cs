using Godot;

namespace aa_godot_viz.scripts;

public partial class _LightSender : Node
{
    private Camera3D _camera;
    private float _speed, _lifetime, _intensity, _range;
    private Color _color;
    private bool _lightInFlight;

    public override void _EnterTree()
    {
        EventSystem.SetSceneConfig += OnSetSceneConfig;
        EventSystem.ImpulseSent += OnImpulseSent;
    }

    public override void _ExitTree()
    {
        EventSystem.SetSceneConfig -= OnSetSceneConfig;
        EventSystem.ImpulseSent -= OnImpulseSent;
    }

    private void OnSetSceneConfig(_SceneConfig config)
    {
        _camera = config.Camera;
        _speed = config.LightSpeed;
        _lifetime = config.LightLifetime;
        _intensity = config.LightIntensity;
        _range = config.LightRange;
        _color = config.LightColor;
    }

    private void OnImpulseSent()
    {
        if (_lightInFlight) return;
        _lightInFlight = true;
        SendLight(_camera, _speed, _lifetime, _intensity, _range, _color);
    }

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