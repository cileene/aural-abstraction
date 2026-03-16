using Godot;
using System.Linq;

public partial class AudioControl : Control
{
    [ExportCategory("Buttons")]
    [Export] public Button[] Buttons;

    [ExportCategory("Audio Players")]
    [Export] public AudioStreamPlayer2D[] Players;

    private int[] _mapping; // _mapping[buttonIndex] = playerIndex
    private FileAccess _logFile;
    private AudioEffectRecord _recorder;

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
        _logFile = FileAccess.Open("user://session_log.csv", FileAccess.ModeFlags.Write);
        string header = "mapping";
        for (int i = 0; i < _mapping.Length; i++)
            header += $", {i}>{_mapping[i]}";
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

        _logFile?.StoreLine($"{Time.GetTicksMsec()}, {buttonIndex}, {_mapping[buttonIndex]}");
    }

    public override void _Input(InputEvent @event)
    {
        if (@event is InputEventKey key && key.Pressed && key.Keycode == Key.Escape)
        {
            _recorder?.SetRecordingActive(false);
            var recording = _recorder?.GetRecording();
            if (recording != null)
                recording.SaveToWav($"user://session_{Time.GetTicksMsec()}.wav");
            _logFile?.Close();
            GetTree().Quit();
        }
    }
}