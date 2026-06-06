using Godot;

namespace aa_godot_viz.scripts.demo;

public partial class LightToggle : DirectionalLight3D
{

	public override void _Ready()
	{
		EventSystem.ToggleLight += OnToggleLight;
	}

	public override void _ExitTree()
	{
		EventSystem.ToggleLight -= OnToggleLight;
	}

	private void OnToggleLight()
	{
		Visible = !Visible;
	}
}