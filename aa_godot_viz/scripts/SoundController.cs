using Godot;

namespace aa_godot_viz.scripts;

public partial class SoundController : AudioStreamPlayer3D
{
    [ExportCategory("Selected Sounds")] [Export] private int[] _selectedSounds;
    [ExportCategory("Sounds")] [Export] private AudioStream[] _audioStreams;

    private int[] _activeSounds;
    private int _pos;

    public override void _Ready()
    {
        EventSystem.PlaySound += OnPlaySound;
        EventSystem.NextSound += OnNextSound;
        EventSystem.ActiveSoundsChanged += OnActiveSoundsChanged;

        if (_audioStreams is { Length: > 0 })
        {
            if (_selectedSounds is { Length: > 0 })
                _activeSounds = _selectedSounds;

            int initialIndex = _activeSounds is { Length: > 0 } ? _activeSounds[0] : 0;
            Stream = _audioStreams[initialIndex];
            EventSystem.RaiseSoundsInitialized(_audioStreams.Length);
            EventSystem.RaiseCurrentSoundIndexChanged(initialIndex);
        }
    }

    public override void _ExitTree()
    {
        EventSystem.PlaySound -= OnPlaySound;
        EventSystem.NextSound -= OnNextSound;
        EventSystem.ActiveSoundsChanged -= OnActiveSoundsChanged;
    }

    private void OnActiveSoundsChanged(int[] sounds)
    {
        if (sounds == null || sounds.Length == 0) return;

        int[] next = _selectedSounds is { Length: > 0 }
            ? System.Array.FindAll(sounds, s => System.Array.IndexOf(_selectedSounds, s) >= 0)
            : sounds;

        if (next.Length == 0) return;

        _activeSounds = next;
        _pos = 0;
        bool wasPlaying = Playing;
        Stop();
        Stream = _audioStreams[_activeSounds[_pos]];
        EventSystem.RaiseCurrentSoundIndexChanged(_activeSounds[_pos]);
        if (wasPlaying) Play();
    }

    private void OnPlaySound()
    {
        if (Playing) Stop();
        else Play();
    }

    private void OnNextSound(bool next)
    {
        if (_activeSounds == null || _activeSounds.Length == 0)
        {
            GD.PrintErr("SoundController: No active sounds!");
            return;
        }

        int n = _activeSounds.Length;
        _pos = next ? (_pos + 1) % n : (_pos - 1 + n) % n;

        float pos = GetPlaybackPosition();
        bool wasPlaying = Playing;
        Stop();
        Stream = _audioStreams[_activeSounds[_pos]];
        EventSystem.RaiseCurrentSoundIndexChanged(_activeSounds[_pos]);
        if (wasPlaying) Play(pos);
    }
}