using System;
using System.Globalization;
using System.IO;
using System.Text;
using Godot;

namespace aa_godot_viz.scripts;

public partial class DataManager : Node
{
    private string _filePath;
    private float[,] _grid; // [soundIndex, paramIndex]
    private int[] _activeSounds;
    private int _currentSoundIndex;
    private Parameters _currentParams = new() { Param1 = 0.5f, Param2 = 0.5f, Param3 = 0.5f, Param4 = 0.5f, Param5 = 0.5f };

    private static readonly string[] ParamNames = { "Color", "Spatiality", "Composition", "Shape", "Material" };

    public override void _EnterTree()
    {
        EventSystem.SoundsInitialized += OnSoundsInitialized;
        EventSystem.SetParameters += OnSetParameters;
        EventSystem.CurrentSoundIndexChanged += OnCurrentSoundIndexChanged;
        EventSystem.SliderReleased += OnSliderReleased;
        EventSystem.ActiveSoundsChanged += OnActiveSoundsChanged;
    }

    public override void _ExitTree()
    {
        EventSystem.SoundsInitialized -= OnSoundsInitialized;
        EventSystem.SetParameters -= OnSetParameters;
        EventSystem.CurrentSoundIndexChanged -= OnCurrentSoundIndexChanged;
        EventSystem.SliderReleased -= OnSliderReleased;
        EventSystem.ActiveSoundsChanged -= OnActiveSoundsChanged;
    }

    public override void _Ready()
    {
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string dir = OS.GetUserDataDir();
        _filePath = Path.Combine(dir, $"{timestamp}.csv");
        GD.Print($"DataManager: will log to {_filePath}");
    }

    private void OnSoundsInitialized(int count)
    {
        _grid = new float[count, 5];
        for (int s = 0; s < count; s++)
            for (int p = 0; p < 5; p++)
                _grid[s, p] = 0.5f;
    }

    private void OnActiveSoundsChanged(int[] sounds)
    {
        _activeSounds = sounds;
        WriteCSV();
    }

    private void OnSetParameters(Parameters parameters)
    {
        _currentParams = parameters;
    }

    private void OnCurrentSoundIndexChanged(int newIndex)
    {
        if (_grid == null) return;

        SaveParams(_currentSoundIndex);

        _currentSoundIndex = newIndex;

        var restored = new Parameters
        {
            Param1 = _grid[newIndex, 0],
            Param2 = _grid[newIndex, 1],
            Param3 = _grid[newIndex, 2],
            Param4 = _grid[newIndex, 3],
            Param5 = _grid[newIndex, 4]
        };

        EventSystem.RaiseParametersRestored(restored);
        WriteCSV();
    }

    private void OnSliderReleased()
    {
        SaveParams(_currentSoundIndex);
        WriteCSV();
    }

    private void SaveParams(int soundIndex)
    {
        _grid[soundIndex, 0] = _currentParams.Param1;
        _grid[soundIndex, 1] = _currentParams.Param2;
        _grid[soundIndex, 2] = _currentParams.Param3;
        _grid[soundIndex, 3] = _currentParams.Param4;
        _grid[soundIndex, 4] = _currentParams.Param5;
    }

    private void WriteCSV()
    {
        if (_grid == null || _filePath == null || _activeSounds == null) return;

        var sb = new StringBuilder();

        sb.Append("Sound");
        foreach (string name in ParamNames)
            sb.Append($",{name}");
        sb.AppendLine();

        foreach (int s in _activeSounds)
        {
            sb.Append(s.ToString("D2"));
            for (int p = 0; p < 5; p++)
                sb.Append($",{_grid[s, p].ToString("F3", CultureInfo.InvariantCulture)}");
            sb.AppendLine();
        }

        File.WriteAllText(_filePath, sb.ToString());
    }
}