using Godot;

namespace aa_godot_viz.scripts.controllers;

public partial class SpotLightController : SpotLight3D
{
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
		LightEnergy = Mathf.Lerp(4.0f, 25.0f, parameters.Param1);
		ShadowBlur = Mathf.Lerp(5.0f, 0.0f, parameters.Param4);
	}
}