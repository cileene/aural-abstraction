using System;
using Godot;

namespace aa_godot_viz.scripts;

/// <summary>
/// Centralized event system for that sweet sweet decoupling.
/// </summary>
public static class EventSystem
{
    // THIS is our main event, all other are related to tests, data collection or ui events
    public static event Action<Parameters> SetParameters; // The event
    public static void RaiseSetParameters(Parameters parameters) // The static helper method to raise the event
    {
        SetParameters?.Invoke(parameters);
        GD.Print($"EventSystem: Raised SetParameters | Color:{parameters.Param1:F3} Spatiality:{parameters.Param2:F3} Composition:{parameters.Param3:F3} Shape:{parameters.Param4:F3} Material:{parameters.Param5:F3}");
    }
    

    
    // BELOW THIS POINT NOT IMPORTANT for the system
    public static event Action PlaySound;
    public static void RaisePlaySound()
    {
        PlaySound?.Invoke();
        GD.Print("EventSystem: Raised PlaySound");
    }

    public static event Action<bool> NextSound;
    public static void RaiseNextSound(bool forward)
    {
        NextSound?.Invoke(forward);
        GD.Print(forward ? "EventSystem: Raised NextSound (forward)" : "EventSystem: Raised NextSound (backward)");
    }

    public static event Action<int> CurrentSoundIndexChanged;
    public static void RaiseCurrentSoundIndexChanged(int index)
    {
        CurrentSoundIndexChanged?.Invoke(index);
        GD.Print($"EventSystem: Raised CurrentSoundIndexChanged | New Index: {index}");
    }

    public static event Action<int> SoundsInitialized;
    public static void RaiseSoundsInitialized(int count)
    {
        SoundsInitialized?.Invoke(count);
        GD.Print($"EventSystem: Raised SoundsInitialized | Count: {count}");
    }

    public static event Action<Parameters> ParametersRestored;
    public static void RaiseParametersRestored(Parameters parameters)
    {
        ParametersRestored?.Invoke(parameters);
        GD.Print($"EventSystem: Raised ParametersRestored | Color:{parameters.Param1:F3} Spatiality:{parameters.Param2:F3} Composition:{parameters.Param3:F3} Shape:{parameters.Param4:F3} Material:{parameters.Param5:F3}");
    }

    public static event Action SliderReleased;
    public static void RaiseSliderReleased()
    {
        SliderReleased?.Invoke();
    }

    public static event Action Randomize;
    public static void RaiseRandomize()
    {
        Randomize?.Invoke();
        GD.Print("EventSystem: Raised Randomize");
    }

    public static event Action<int[]> ActiveSoundsChanged;
    public static void RaiseActiveSoundsChanged(int[] sounds)
    {
        ActiveSoundsChanged?.Invoke(sounds);
        GD.Print($"EventSystem: Raised ActiveSoundsChanged | [{string.Join(", ", sounds)}]");
    }

    public static event Action ToggleDemoMode;
    public static void RaiseStartDemoMode()
    {
        ToggleDemoMode?.Invoke();
        GD.Print("EventSystem: Raised ToggleDemoMode");
    }

    public static event Action ToggleUI;
    public static void RaiseToggleUI()
    {
        ToggleUI?.Invoke();
        GD.Print("EventSystem: Raised ToggleUI");
    }

    public static event Action ToggleMesh;
    public static void RaiseToggleMesh()
    {
        ToggleMesh?.Invoke();
        GD.Print("EventSystem: Raised ToggleMesh");
    }
    
    public static event Action ToggleLight;
    public static void RaiseToggleLight()
    {
        ToggleLight?.Invoke();
        GD.Print("EventSystem: Raised ToggleLight");
    }
}
