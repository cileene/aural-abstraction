using Godot;
using System.Linq;

public partial class AudioControl : Control
{
    [ExportCategory("Buttons")]
    [Export] public Button[] Buttons;

    [ExportCategory("Audio Players")]
    [Export] public AudioStreamPlayer2D[] Players;

    private int[] _mapping; // _mapping[buttonIndex] = playerIndex

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
    }
}