using Godot;

namespace aa_godot_viz.scripts;

public partial class TreeRotator : Node3D
{
    [Export(PropertyHint.Range, "0.01, 2.0")] public float RotationSpeed = 0.3f;

    private bool _demoMode;

    public override void _Ready()
    {
        EventSystem.ToggleDemoMode += OnToggleDemoMode;
    }

    public override void _ExitTree()
    {
        EventSystem.ToggleDemoMode -= OnToggleDemoMode;
    }

    public override void _Process(double delta)
    {
        if (_demoMode)
            RotateY(RotationSpeed * (float)delta);
    }

    private void OnToggleDemoMode()
    {
        _demoMode = !_demoMode;
    }
}
