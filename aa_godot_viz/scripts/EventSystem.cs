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
    public static event Action<_SceneConfig> SetSceneConfig;
    public static event Action ImpulseSent;
    public static event Action PlaySound;
    public static event Action<bool> NextSound;

    // EVENT METHODS
    public static void RaiseSetParameters(Parameters parameters)
    {
        SetParameters?.Invoke(parameters);
        GD.Print($"EventSystem: Raised SetParameters | Color:{parameters.Param1:F3} Spatiality:{parameters.Param2:F3} Composition:{parameters.Param3:F3} Shape:{parameters.Param4:F3} Material:{parameters.Param5:F3}");
    }

    public static void RaiseSetSceneConfig(_SceneConfig config)
    {
        SetSceneConfig?.Invoke(config);
        GD.Print("EventSystem: Raised SetSceneConfig");
    }

    public static void RaiseImpulseSent()
    {
        ImpulseSent?.Invoke();
        GD.Print("EventSystem: Raised ImpulseSent");
    }
    
    public static void RaisePlaySound()
    {
        PlaySound?.Invoke();
        GD.Print("EventSystem: Raised PlaySound");
    }
    
    public static void RaiseNextSound(bool forward)
    {
        NextSound?.Invoke(forward);
        GD.Print(forward ? "EventSystem: Raised NextSound (forward)" : "EventSystem: Raised NextSound (backward)");
    }
}