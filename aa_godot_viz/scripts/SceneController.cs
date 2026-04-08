using Godot;

public partial class SceneController : Node
{
	[Export] private WorldEnvironment _worldEnvironment;
	[Export] private Light3D _light;
	[Export] private FastNoiseLite _noise;
	[Export] private PackedScene _cube;
	[Export] private int _gridSize = 10;
	[Export] private float _spacing = 2f;
	[Export] private float _threshold = 0.5f;
	[Export] private Camera3D _camera;
	[Export] private float _lightSpeed = 1f;
	[Export] private float _lightLifetime = 5f;
	[Export] private float _lightIntensity = 1f;
	[Export] private Color _lightColor = Colors.White;
	
	private bool _sendLightRequested = false;
	private bool _lightSent = false;
	
	public override void _Ready()
	{
		PlaceObjectsWithNoise();
	}
	
	public override void _Process(double delta)
	{
		if (_sendLightRequested)
		{
			_lightSent = true;
			SendLight(_camera, _lightSpeed, _lightLifetime, _lightIntensity, _lightColor);
			_sendLightRequested = false;
			_lightSent = false;
		}
	}
	
	public override void _Input(InputEvent @event)
	{
		if (@event.IsActionPressed("Step") && !_lightSent)
		{
			_sendLightRequested = true;
		}
	}

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
			float value = (_noise.GetNoise3D(x, y, z) + 1f) / 2f; // normalize to [0, 1]

			if (value > _threshold)
			{
				var instance = _cube.Instantiate<Node3D>();
				instance.Position = new Vector3(x, y, z) * _spacing;
				AddChild(instance);
			}
		}
	}
	
	private void SendLight(Camera3D camera, float speed, float lifetime, float intensity, Color color)
	{
		var lightInstance = new OmniLight3D
		{
			Position = camera.GlobalPosition,
			LightColor = color,
			LightEnergy = intensity,
		};

		AddChild(lightInstance);

		var direction = -camera.GlobalTransform.Basis.Z.Normalized();
		var endPosition = lightInstance.Position + direction * speed * lifetime;

		var tween = CreateTween();
		tween.TweenProperty(lightInstance, "position", endPosition, lifetime).SetTrans(Tween.TransitionType.Linear);
		
		tween.Parallel().TweenProperty(lightInstance, "light_energy", 0.0f, lifetime);

		var timer = new Timer { WaitTime = lifetime, OneShot = true };
		timer.Timeout += () =>
		{
			lightInstance.QueueFree();
			timer.QueueFree();
		};
		AddChild(timer);
		timer.Start();
	}
}
