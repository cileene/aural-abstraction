using Godot;

namespace aa_godot_viz.scripts.controllers;

public partial class LightColorController : OmniLight3D
{
	[Export] private Color _coldColor = new Color(0.5f, 0.5f, 1f);
	[Export] private Color _warmColor = new Color(1f, 0.5f, 0.5f);
	
	// Called when the node enters the scene tree for the first time
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
		LightColor = _coldColor.Lerp(_warmColor, parameters.Param1);
	}
}