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
	
	public override void _Ready()
	{
		PlaceObjectsWithNoise();
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
}
