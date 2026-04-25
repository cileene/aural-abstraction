using System;
using System.IO;
using Godot;

namespace aa_godot_viz.scripts;

public partial class DataManager : Node
{
    private string _filePath;

    public override void _Ready()
    {
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string dir = ProjectSettings.GlobalizePath("user://");
        _filePath = Path.Combine(dir, $"{timestamp}.csv");

        File.WriteAllText(_filePath, "");
        GD.Print($"DataManager: logging to {_filePath}");
    }
}
