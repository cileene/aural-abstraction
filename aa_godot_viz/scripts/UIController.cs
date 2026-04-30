using Godot;

namespace aa_godot_viz.scripts;

public partial class UIController : VBoxContainer
{
	[Export] private Label _soundLabel;
	[Export] private SpinBox _minSoundSpinBox;
	[Export] private SpinBox _maxSoundSpinBox;
	[Export] private SpinBox _testerSpinBox;
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

	public override void _EnterTree()
	{
		EventSystem.CurrentSoundIndexChanged += OnCurrentSoundIndexChanged;
		EventSystem.ParametersRestored += OnParametersRestored;
		EventSystem.Randomize += OnRandomize;
		EventSystem.SoundsInitialized += OnSoundsInitialized;
	}

	public override void _Ready()
	{
		_minSoundSpinBox.Step = 1;
		_maxSoundSpinBox.Step = 1;
		_minSoundSpinBox.ValueChanged += _ => RaiseActiveSounds();
		_maxSoundSpinBox.ValueChanged += _ => RaiseActiveSounds();

		_testerSpinBox.Step = 1;
		_testerSpinBox.MinValue = 0;
		_testerSpinBox.MaxValue = 5;
		_testerSpinBox.ValueChanged += _ => RaiseActiveSounds();

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
		spinBox.Step = slider.Step > 0 ? slider.Step : 0.1;
		spinBox.Value = slider.Value;

		slider.ValueChanged += v =>
		{
			onChange((float)v);
			spinBox.SetValueNoSignal(v);
		};

		slider.DragEnded += _ => EventSystem.RaiseSliderReleased();

		spinBox.ValueChanged += v =>
		{
			slider.SetValueNoSignal(v);
			onChange((float)v);
		};
	}

	public override void _ExitTree()
	{
		EventSystem.CurrentSoundIndexChanged -= OnCurrentSoundIndexChanged;
		EventSystem.ParametersRestored -= OnParametersRestored;
		EventSystem.Randomize -= OnRandomize;
		EventSystem.SoundsInitialized -= OnSoundsInitialized;
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

	private void RaiseActiveSounds()
	{
		int min = (int)_minSoundSpinBox.Value;
		int max = (int)_maxSoundSpinBox.Value;
		if (min > max) return;

		int tester = (int)_testerSpinBox.Value;
		int size = max - min + 1;
		int[] sounds;

		if (tester == 0)
		{
			sounds = new int[size];
			for (int i = 0; i < size; i++)
				sounds[i] = min + i;
		}
		else
		{
			sounds = new int[4];
			for (int k = 0; k < 4; k++)
				sounds[k] = min + ((tester - 1) * 2 + k) % size;
		}

		EventSystem.RaiseActiveSoundsChanged(sounds);
	}

	private void OnRandomize()
	{
		_colorSlider.Value       = GD.Randf();
		_spatialitySlider.Value  = GD.Randf();
		_compositionSlider.Value = GD.Randf();
		_shapeSlider.Value       = GD.Randf();
		_materialSlider.Value    = GD.Randf();
		EventSystem.RaiseSliderReleased();
	}

	private void OnSoundsInitialized(int count)
	{
		_minSoundSpinBox.MaxValue = count - 1;
		_maxSoundSpinBox.MaxValue = count - 1;
		_maxSoundSpinBox.SetValueNoSignal(count - 1);
		RaiseActiveSounds();
	}

	private void OnCurrentSoundIndexChanged(int index)
	{
		_soundLabel.Text = $"{index:D2}";
	}

	private void OnParametersRestored(Parameters p)
	{
		_color       = p.Param1;
		_spatiality  = p.Param2;
		_composition = p.Param3;
		_shape       = p.Param4;
		_material    = p.Param5;

		_colorSlider.SetValueNoSignal(_color);             _colorValue.SetValueNoSignal(_color);
		_spatialitySlider.SetValueNoSignal(_spatiality);   _spatialityValue.SetValueNoSignal(_spatiality);
		_compositionSlider.SetValueNoSignal(_composition); _compositionValue.SetValueNoSignal(_composition);
		_shapeSlider.SetValueNoSignal(_shape);             _shapeValue.SetValueNoSignal(_shape);
		_materialSlider.SetValueNoSignal(_material);       _materialValue.SetValueNoSignal(_material);

		RaiseParameters();
	}
}