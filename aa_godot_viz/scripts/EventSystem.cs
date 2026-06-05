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
    //public static event Action<_SceneConfig> SetSceneConfig;
    public static event Action ImpulseSent;
    public static event Action PlaySound;
    public static event Action<bool> NextSound;
    public static event Action<int> CurrentSoundIndexChanged;
    public static event Action<int> SoundsInitialized;
    public static event Action<Parameters> ParametersRestored;
    public static event Action SliderReleased;
    public static event Action Randomize;
    public static event Action<int[]> ActiveSoundsChanged;
    public static event Action StartDemoMode;
    public static event Action ToggleUI;
    public static event Action ToggleMesh;
    public static event Action ParametersReceived;

    // EVENT METHODS
    public static void RaiseSetParameters(Parameters parameters)
    {
        SetParameters?.Invoke(parameters);
        GD.Print($"EventSystem: Raised SetParameters | Color:{parameters.Param1:F3} Spatiality:{parameters.Param2:F3} Composition:{parameters.Param3:F3} Shape:{parameters.Param4:F3} Material:{parameters.Param5:F3}");
    }

    // public static void RaiseSetSceneConfig(_SceneConfig config)
    // {
    //     SetSceneConfig?.Invoke(config);
    //     GD.Print("EventSystem: Raised SetSceneConfig");
    // }

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

    public static void RaiseCurrentSoundIndexChanged(int index)
    {
        CurrentSoundIndexChanged?.Invoke(index);
        GD.Print($"EventSystem: Raised CurrentSoundIndexChanged | New Index: {index}");
    }

    public static void RaiseSoundsInitialized(int count)
    {
        SoundsInitialized?.Invoke(count);
        GD.Print($"EventSystem: Raised SoundsInitialized | Count: {count}");
    }

    public static void RaiseSliderReleased()
    {
        SliderReleased?.Invoke();
    }

    public static void RaiseParametersRestored(Parameters parameters)
    {
        ParametersRestored?.Invoke(parameters);
        GD.Print($"EventSystem: Raised ParametersRestored | Color:{parameters.Param1:F3} Spatiality:{parameters.Param2:F3} Composition:{parameters.Param3:F3} Shape:{parameters.Param4:F3} Material:{parameters.Param5:F3}");
    }

    public static void RaiseRandomize()
    {
        Randomize?.Invoke();
        GD.Print("EventSystem: Raised Randomize");
    }

    public static void RaiseActiveSoundsChanged(int[] sounds)
    {
        ActiveSoundsChanged?.Invoke(sounds);
        GD.Print($"EventSystem: Raised ActiveSoundsChanged | [{string.Join(", ", sounds)}]");
    }

    public static void RaiseStartDemoMode()
    {
        StartDemoMode?.Invoke();
        GD.Print("EventSystem: Raised StartDemoMode");
    }

    public static void RaiseToggleUI()
    {
        ToggleUI?.Invoke();
        GD.Print("EventSystem: Raised ToggleUI");
    }

    public static void RaiseToggleMesh()
    {
        ToggleMesh?.Invoke();
        GD.Print("EventSystem: Raised ToggleMesh");
    }
    
    public static void RaiseParametersReceived()
    {
        ParametersReceived?.Invoke();
        GD.Print("EventSystem: Raised ParametersReceived");
    }
}
