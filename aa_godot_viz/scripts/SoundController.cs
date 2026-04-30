using Godot;

namespace aa_godot_viz.scripts;

public partial class SoundController : AudioStreamPlayer3D
{
    [ExportCategory("Sounds")] [Export] private AudioStream[] _audioStreams;

    private int _currentSoundIndex = 0;
    private int _minIndex = 0;
    private int _maxIndex = 0;

    public override void _Ready()
    {
        EventSystem.SetParameters += OnSetParameters;
        EventSystem.PlaySound += OnPlaySound;
        EventSystem.NextSound += OnNextSound;
        EventSystem.SoundRangeChanged += OnSoundRangeChanged;

        if (_audioStreams is { Length: > 0 })
        {
            _maxIndex = _audioStreams.Length - 1;
            Stream = _audioStreams[_currentSoundIndex];
            EventSystem.RaiseSoundsInitialized(_audioStreams.Length);
            EventSystem.RaiseCurrentSoundIndexChanged(_currentSoundIndex);
        }
    }

    public override void _ExitTree()
    {
        EventSystem.SetParameters -= OnSetParameters;
        EventSystem.PlaySound -= OnPlaySound;
        EventSystem.NextSound -= OnNextSound;
        EventSystem.SoundRangeChanged -= OnSoundRangeChanged;
    }

    private void OnSoundRangeChanged(int min, int max)
    {
        _minIndex = Mathf.Clamp(min, 0, _audioStreams.Length - 1);
        _maxIndex = Mathf.Clamp(max, _minIndex, _audioStreams.Length - 1);
        _currentSoundIndex = _minIndex;
        bool wasPlaying = Playing;
        Stop();
        Stream = _audioStreams[_currentSoundIndex];
        EventSystem.RaiseCurrentSoundIndexChanged(_currentSoundIndex);
        if (wasPlaying) Play();
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

        int rangeSize = _maxIndex - _minIndex + 1;
        if (next)
            _currentSoundIndex = _minIndex + (_currentSoundIndex - _minIndex + 1) % rangeSize;
        else
            _currentSoundIndex = _minIndex + (_currentSoundIndex - _minIndex - 1 + rangeSize) % rangeSize;

        float pos = GetPlaybackPosition();
        bool wasPlaying = Playing;
        Stop();
        Stream = _audioStreams[_currentSoundIndex];
        EventSystem.RaiseCurrentSoundIndexChanged(_currentSoundIndex);
        if (wasPlaying) Play(pos);
    }
}