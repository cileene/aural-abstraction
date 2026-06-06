using Godot;

namespace aa_godot_viz.scripts.controllers;

public partial class CameraController : Camera3D
{
	public override void _Ready() => EventSystem.SetParameters += OnSetParameters;

	public override void _ExitTree() => EventSystem.SetParameters -= OnSetParameters;

	private void OnSetParameters(Parameters parameters)
	{
		Fov = Mathf.Lerp(40f, 110f, parameters.Param2);
	}
}