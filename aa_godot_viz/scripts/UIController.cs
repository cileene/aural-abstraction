using Godot;

namespace aa_godot_viz.scripts;

public partial class UIController : VBoxContainer
{
	[Export] private HSlider _colorSlider;
	[Export] private HSlider _spatialitySlider;
	[Export] private HSlider _compositionSlider;
	[Export] private HSlider _shapeSlider;
	[Export] private HSlider _materialSlider;
	
	private float _color, _spatiality, _composition, _shape, _material;

	public override void _Ready()
	{
		_colorSlider.DragEnded += _ => { _color = (float)_colorSlider.Value; RaiseParameters(); };
		_spatialitySlider.DragEnded += _ => { _spatiality = (float)_spatialitySlider.Value; RaiseParameters(); };
		_compositionSlider.DragEnded += _ => { _composition = (float)_compositionSlider.Value; RaiseParameters(); };
		_shapeSlider.DragEnded += _ => { _shape = (float)_shapeSlider.Value; RaiseParameters(); };
		_materialSlider.DragEnded += _ => { _material = (float)_materialSlider.Value; RaiseParameters(); };

		RaiseParameters();
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
