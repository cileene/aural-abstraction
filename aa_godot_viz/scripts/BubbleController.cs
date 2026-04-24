using Godot;

namespace aa_godot_viz.scripts;

public partial class BubbleController : Node3D
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
		GlobalRotation = new Vector3(
			0.0f,
			Mathf.Lerp(0.0f, Mathf.Pi * 2.0f, parameters.Param2),
			0.0f
		);
	}
}