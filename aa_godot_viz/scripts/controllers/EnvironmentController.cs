using Godot;

namespace aa_godot_viz.scripts.controllers;

public partial class EnvironmentController : WorldEnvironment
{
	// Called when the node enters the scene tree for the first time.
	public override void _Ready()
	{
		EventSystem.SetParameters += OnSetParameters;
	}
	
	public override void _ExitTree()
	{
		EventSystem.SetParameters -= OnSetParameters;
	}
	
	private void OnSetParameters(Parameters parameters)
	{

		Environment.VolumetricFogDensity = Mathf.Lerp(0.02f, 0.08f, parameters.Param1);
	}
}