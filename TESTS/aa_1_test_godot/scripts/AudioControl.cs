using Godot;
using System.Linq;

public partial class AudioControl : Node
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
        int count = Mathf.Min(Buttons.Length, Players.Length);
        int[] map = Enumerable.Range(0, count).ToArray();
        
        var rng = new RandomNumberGenerator();
        rng.Randomize();

        for (int i = map.Length - 1; i > 0; i--)
        {
            int j = rng.RandiRange(0, i);
            (map[i], map[j]) = (map[j], map[i]);
        }

        return map;
    }

    private void OnPressed(int buttonIndex)
    {
        if (_mapping == null || buttonIndex < 0 || buttonIndex >= _mapping.Length)
            return;

        int activePlayer = _mapping[buttonIndex];
        for (int i = 0; i < Players.Length; i++)
            Players[i].VolumeDb = i == activePlayer ? 0f : -80f;
    }
    
    public string GetPlayerNameForButton(int buttonIndex)
    {
        if (_mapping == null || buttonIndex < 0 || buttonIndex >= _mapping.Length)
            return $"Button_{buttonIndex}";

        int playerIndex = _mapping[buttonIndex];
        if (playerIndex < 0 || playerIndex >= Players.Length)
            return $"Player_{playerIndex}";

        return Players[playerIndex]?.Name ?? $"Player_{playerIndex}";
    }
}