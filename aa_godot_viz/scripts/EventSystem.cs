using System;
using Godot;

namespace aa_godot_viz.scripts;

/// <summary>
/// Centralized event system for that sweet sweet decoupling.
/// </summary>

public static class EventSystem
{
    // EVENTS
    public static event Action<Parameters> SetParameters;
    
    // EVENT METHODS
    public static void RaiseSetParameters(Parameters parameters)
    {
        SetParameters?.Invoke(parameters);
        GD.Print($"EventSystem: Raised SetParameters with values: " +
                 $"{parameters.Param1}, " +
                 $"{parameters.Param2}, " +
                 $"{parameters.Param3}, " +
                 $"{parameters.Param4}, " +
                 $"{parameters.Param5}");
    }
}