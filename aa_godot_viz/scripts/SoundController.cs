using Godot;

namespace aa_godot_viz.scripts;

public partial class SoundController : AudioStreamPlayer3D
{
    [ExportCategory("Sounds")] [Export] private AudioStream[] _audioStreams;

    private int _currentSoundIndex = 0;

    public override void _Ready()
    {
        EventSystem.SetParameters += OnSetParameters;
        EventSystem.PlaySound += OnPlaySound;
        EventSystem.NextSound += OnNextSound;

        if (_audioStreams is { Length: > 0 })
        {
            Stream = _audioStreams[0];
            EventSystem.RaiseSoundsInitialized(_audioStreams.Length);
            EventSystem.RaiseCurrentSoundIndexChanged(_currentSoundIndex);
        }
    }

    public override void _ExitTree()
    {
        EventSystem.SetParameters -= OnSetParameters;
        EventSystem.PlaySound -= OnPlaySound;
        EventSystem.NextSound -= OnNextSound;
    }

    private void OnSetParameters(Parameters parameters)
    {
    }

    private void OnPlaySound()
    {
        if (Playing) Stop();
        else Play();
    }

    private void OnNextSound(bool next)
    {
        if (_audioStreams == null || _audioStreams.Length == 0)
        {
            GD.PrintErr("SoundController: No audio streams assigned!");
            return;
        }

        int n = _audioStreams.Length;
        if (next)
            _currentSoundIndex = (_currentSoundIndex + 1) % n;
        else
            _currentSoundIndex = (_currentSoundIndex - 1 + n) % n;

        bool wasPlaying = Playing;
        Stop();
        Stream = _audioStreams[_currentSoundIndex];
        EventSystem.RaiseCurrentSoundIndexChanged(_currentSoundIndex);
        if (wasPlaying) Play();
    }
}