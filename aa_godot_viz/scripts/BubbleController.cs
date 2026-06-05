using Godot;

namespace aa_godot_viz.scripts;

public partial class BubbleController : Node3D
{
    [Export(PropertyHint.Range, "0.01, 1.0")] public float DemoLerpSpeed = 0.5f;

    private static readonly Vector3 DemoTargetRotation = new(
        Mathf.DegToRad(110f), 0f, Mathf.DegToRad(-26f)
    );

    private bool _demoMode;

    public override void _Ready()
    {
        EventSystem.SetParameters += OnSetParameters;
        EventSystem.ToggleDemoMode += OnToggleDemoMode;
    }

    public override void _ExitTree()
    {
        EventSystem.SetParameters -= OnSetParameters;
        EventSystem.ToggleDemoMode -= OnToggleDemoMode;
    }

    public override void _Process(double delta)
    {
        if (_demoMode)
            Rotation = Rotation.Lerp(DemoTargetRotation, DemoLerpSpeed * (float)delta);
    }

    private void OnSetParameters(Parameters parameters)
    {
        if (_demoMode) return;
        GlobalRotation = GlobalRotation with { Y = Mathf.Lerp(0.0f, Mathf.Pi * 2.0f, parameters.Param2) };
    }

    private void OnToggleDemoMode()
    {
        _demoMode = !_demoMode;
    }
}
