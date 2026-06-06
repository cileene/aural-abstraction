using Godot;

namespace aa_godot_viz.scripts;

/// <summary>
/// Sets the initial parameters and translates godot input events into calls to the event system.
/// </summary>
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

    /// <summary>
    /// Here all of our godot input events are handled and translated into calls to the event system.
    /// </summary>
    /// <param name="event"></param>
    public override void _Input(InputEvent @event)
    {
        if (@event.IsActionPressed("Play")) EventSystem.RaisePlaySound();
        
        else if (@event.IsActionPressed("Next")) EventSystem.RaiseNextSound(true);
        
        else if (@event.IsActionPressed("Previous")) EventSystem.RaiseNextSound(false);
        
        else if (@event.IsActionPressed("Randomize")) EventSystem.RaiseRandomize();
        
        else if (@event.IsActionPressed("Demo")) EventSystem.RaiseStartDemoMode();
        
        else if (@event.IsActionPressed("UI")) EventSystem.RaiseToggleUI();
        
        else if (@event.IsActionPressed("Mesh")) EventSystem.RaiseToggleMesh();
        
        else if (@event.IsActionPressed("Light")) EventSystem.RaiseToggleLight();
    }
}