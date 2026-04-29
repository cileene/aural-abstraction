using Godot;

namespace aa_godot_viz.scripts;

public partial class _ObjectPlacer : Node
{
    private FastNoiseLite _noise;
    private PackedScene _cube;
    private int _gridSize;
    private float _spacing, _threshold;

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
        _noise = config.Noise;
        _cube = config.Cube;
        _gridSize = 10; //TODO: get from config
        _spacing = 2f; //TODO: get from config
        _threshold = 0.5f; //TODO: get from config
    }

    private void OnImpulseSent()
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
            float value = (_noise.GetNoise3D(x, y, z) + 1f) / 2f;

            if (value > _threshold)
            {
                var instance = _cube.Instantiate<Node3D>();
                instance.Position = new Vector3(x, y, z) * _spacing;
                AddChild(instance);
            }
        }
    }
}