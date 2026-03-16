using Godot;
using System.Linq;

public partial class AudioControl : Control
{
    [ExportCategory("Buttons")]
    [Export] public Button[] Buttons;

    [ExportCategory("Audio Players")]
    [Export] public AudioStreamPlayer2D[] Players;

    private int[] _mapping; // _mapping[buttonIndex] = playerIndex
    private static readonly string[] PlayerNames = { "CLEAN", "SMALL", "MEDIUM", "LARGE" };
    private FileAccess _logFile;
    private AudioEffectRecord _recorder;
    private string _sessionPrefix;

    public override void _EnterTree()
    {
        for (int i = 0; i < Buttons.Length; i++)
        {
            int index = i;
            Buttons[i].Pressed += () => OnPressed(index);
        }
    }

    public override void _Ready()
    {
        _mapping = BuildMapping();

        // Session log
        _sessionPrefix = $"{NextSessionNumber():D3}";
        _logFile = FileAccess.Open($"user://{_sessionPrefix}_log.csv", FileAccess.ModeFlags.Write);
        string header = "mapping";
        for (int i = 0; i < _mapping.Length; i++)
            header += $", {i}>{PlayerNames[_mapping[i]]}";
        _logFile.StoreLine(header);

        // Microphone recording — route mic through the Record bus so AudioEffectRecord captures it
        var micPlayer = new AudioStreamPlayer();
        micPlayer.Stream = new AudioStreamMicrophone();
        micPlayer.Bus = "Record";
        AddChild(micPlayer);
        micPlayer.Play();

        int busIdx = AudioServer.GetBusIndex("Record");
        _recorder = (AudioEffectRecord)AudioServer.GetBusEffect(busIdx, 0);
        _recorder.SetRecordingActive(true);

        Buttons[0].ButtonPressed = true;
        foreach (var player in Players)
            player.Play();

        OnPressed(0);
    }

    private int NextSessionNumber()
    {
        int max = 0;
        using var dir = DirAccess.Open("user://");
        if (dir != null)
        {
            dir.ListDirBegin();
            string name;
            while ((name = dir.GetNext()) != "")
            {
                if (name.EndsWith("_recording.wav") || name.EndsWith("_log.csv"))
                {
                    var parts = name.Split('_');
                    if (parts.Length > 0 && int.TryParse(parts[0], out int n))
                        max = Mathf.Max(max, n);
                }
            }
            dir.ListDirEnd();
        }
        return max + 1;
    }

    // Godot records mono mic input into only the left channel of a stereo stream.
    // Copy the left channel bytes to the right channel so the file plays back centred.
    private void FixMonoRecording(AudioStreamWav wav)
    {
        if (!wav.Stereo) return;
        int bytesPerSample = wav.Format == AudioStreamWav.FormatEnum.Format8Bits ? 1 : 2;
        int stride = bytesPerSample * 2;
        var data = wav.Data;
        for (int i = 0; i < data.Length; i += stride)
            for (int b = 0; b < bytesPerSample; b++)
                data[i + bytesPerSample + b] = data[i + b];
        wav.Data = data;
    }

    private int[] BuildMapping()
    {
        var shuffled = Enumerable.Range(1, Players.Length - 1)
            .OrderBy(_ => GD.Randi())
            .ToArray();

        return new[] { 0 }.Concat(shuffled).ToArray();
    }

    private void OnPressed(int buttonIndex)
    {
        int activePlayer = _mapping[buttonIndex];
        for (int i = 0; i < Players.Length; i++)
            Players[i].VolumeDb = i == activePlayer ? 0f : -80f;

        _logFile?.StoreLine($"{Time.GetTicksMsec()}, {buttonIndex}, {PlayerNames[_mapping[buttonIndex]]}");
    }

    public override void _Input(InputEvent @event)
    {
        if (@event != null && @event is InputEventKey key && key.Pressed && key.Keycode == Key.Escape)
        {
            _recorder?.SetRecordingActive(false);
            var recording = _recorder?.GetRecording();
            if (recording != null)
            {
                FixMonoRecording(recording);
                recording.SaveToWav($"user://{_sessionPrefix}_recording.wav");
            }
            _logFile?.Close();
            GetTree().Quit();
        }
    }
}