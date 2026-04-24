using Godot;

namespace aa_godot_viz.scripts;

public partial class UIController : VBoxContainer
{
	[Export] private HSlider _colorSlider;
	[Export] private HSlider _spatialitySlider;
	[Export] private HSlider _compositionSlider;
	[Export] private HSlider _shapeSlider;
	[Export] private HSlider _materialSlider;

	[Export] public bool ShowFps = true;

	private float _color = 0.5f, _spatiality = 0.5f, _composition = 0.5f, _shape = 0.5f, _material = 0.5f;
	private Label _fpsLabel;

	public override void _Ready()
	{
		_colorSlider.ValueChanged += v => { _color = (float)v; RaiseParameters(); };
		_spatialitySlider.ValueChanged += v => { _spatiality = (float)v; RaiseParameters(); };
		_compositionSlider.ValueChanged += v => { _composition = (float)v; RaiseParameters(); };
		_shapeSlider.ValueChanged += v => { _shape = (float)v; RaiseParameters(); };
		_materialSlider.ValueChanged += v => { _material = (float)v; RaiseParameters(); };

		_fpsLabel = new Label();
		_fpsLabel.SetAnchorsPreset(LayoutPreset.TopRight);
		_fpsLabel.GrowHorizontal = GrowDirection.Begin;
		_fpsLabel.OffsetRight = -10;
		_fpsLabel.OffsetTop = 10;
		GetParent().CallDeferred("add_child", _fpsLabel);

		RaiseParameters();
	}

	public override void _ExitTree()
	{
		_fpsLabel?.QueueFree();
	}

	public override void _Process(double delta)
	{
		if (_fpsLabel == null) return;
		_fpsLabel.Visible = ShowFps;
		if (ShowFps)
			_fpsLabel.Text = $"{Engine.GetFramesPerSecond()} FPS";
	}

	private void RaiseParameters()
	{
		EventSystem.RaiseSetParameters(new Parameters
		{
			Param1 = _color,
			Param2 = _spatiality,
			Param3 = _composition,
			Param4 = _shape,
			Param5 = _material
		});
	}
}
