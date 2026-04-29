using Godot;

namespace aa_godot_viz.scripts;

public partial class SceneController : Node
{
    [ExportCategory("Parameters")] 
    [Export(PropertyHint.Range, "0,1")] private float _color = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _spatiality = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _composition = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _shape = 0.5f;
    [Export(PropertyHint.Range, "0,1")] private float _material = 0.5f;

    public override void _Ready()
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

    public override void _Input(InputEvent @event)
    {
        if (@event.IsActionPressed("Play"))
        {
            EventSystem.RaisePlaySound();
        }
        else if (@event.IsActionPressed("Next"))
        {
            EventSystem.RaiseNextSound(true);
        }
        else if (@event.IsActionPressed("Previous"))
        {
            EventSystem.RaiseNextSound(false);
        }
        else if (@event.IsActionPressed("Randomize"))
        {
            EventSystem.RaiseRandomize();
        }
    }
}