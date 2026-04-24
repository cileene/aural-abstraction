using Godot;

namespace aa_godot_viz.scripts;

public partial class UIController : VBoxContainer
{
	[Export] private HSlider _colorSlider;
	[Export] private SpinBox _colorValue;
	[Export] private HSlider _spatialitySlider;
	[Export] private SpinBox _spatialityValue;
	[Export] private HSlider _compositionSlider;
	[Export] private SpinBox _compositionValue;
	[Export] private HSlider _shapeSlider;
	[Export] private SpinBox _shapeValue;
	[Export] private HSlider _materialSlider;
	[Export] private SpinBox _materialValue;

	[Export] public bool ShowFps = true;

	private float _color = 0.5f, _spatiality = 0.5f, _composition = 0.5f, _shape = 0.5f, _material = 0.5f;
	private Label _fpsLabel;

	public override void _Ready()
	{
		BindSlider(_colorSlider,      _colorValue,      v => { _color = v;       RaiseParameters(); });
		BindSlider(_spatialitySlider, _spatialityValue, v => { _spatiality = v;  RaiseParameters(); });
		BindSlider(_compositionSlider,_compositionValue,v => { _composition = v; RaiseParameters(); });
		BindSlider(_shapeSlider,      _shapeValue,      v => { _shape = v;       RaiseParameters(); });
		BindSlider(_materialSlider,   _materialValue,   v => { _material = v;    RaiseParameters(); });

		_fpsLabel = new Label();
		_fpsLabel.SetAnchorsPreset(LayoutPreset.TopRight);
		_fpsLabel.GrowHorizontal = GrowDirection.Begin;
		_fpsLabel.OffsetRight = -10;
		_fpsLabel.OffsetTop = 10;
		GetParent().CallDeferred("add_child", _fpsLabel);

		RaiseParameters();
	}

	private void BindSlider(HSlider slider, SpinBox spinBox, System.Action<float> onChange)
	{
		spinBox.MinValue = slider.MinValue;
		spinBox.MaxValue = slider.MaxValue;
		spinBox.Step = slider.Step > 0 ? slider.Step : 0.01;
		spinBox.Value = slider.Value;

		slider.ValueChanged += v =>
		{
			onChange((float)v);
			spinBox.SetValueNoSignal(v);
		};

		spinBox.ValueChanged += v =>
		{
			slider.SetValueNoSignal(v);
			onChange((float)v);
		};
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
