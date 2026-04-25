using Godot;

namespace aa_godot_viz.scripts;

public partial class AudioAnalyzer : Node
{
    [Export] public ShaderMaterial PointMaterial;
    [Export(PropertyHint.Range, "0.0, 20.0")] public float Gain = 8.0f;
    [Export(PropertyHint.Range, "0.01, 1.0")] public float Smoothing = 0.15f;

    private AudioEffectCapture _capture;
    private float _smoothedRms;
    private int _effectIndex;

    public override void _Ready()
    {
        _capture = new AudioEffectCapture();
        _effectIndex = AudioServer.GetBusEffectCount(0);
        AudioServer.AddBusEffect(0, _capture);
    }

    public override void _ExitTree()
    {
        AudioServer.RemoveBusEffect(0, _effectIndex);
    }

    public override void _Process(double delta)
    {
        if (_capture == null || PointMaterial == null) return;

        int available = _capture.GetFramesAvailable();
        if (available == 0) return;

        var frames = _capture.GetBuffer(available);

        float sumSq = 0f;
        foreach (var frame in frames)
            sumSq += frame.X * frame.X + frame.Y * frame.Y;
        float rms = Mathf.Sqrt(sumSq / (frames.Length * 2f));

        _smoothedRms = Mathf.Lerp(_smoothedRms, rms * Gain, Smoothing);
        PointMaterial.SetShaderParameter("audio_amplitude", _smoothedRms);
    }
}
