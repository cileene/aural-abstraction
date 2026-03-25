using Godot;

public partial class CardSort : Node
{
    [Export] private PackedScene _cardItemScene;

    [Export] private string[] _vocabulary = new[]
    {
        "Bright", "Dark", "Warm", "Cold", "Large", "Small",
        "Distant", "Close", "Smooth", "Rough", "Open", "Enclosed",
        "morning", "evening", "sharp", "dull", "soft", "hard",
        "heavy", "light", "quiet", "loud", "fast", "slow",
        "better", "test", "any", "thing", "way", "Much"
    };

    public override void _Ready()
    {
        var unsortedA = GetNode<CardList>("UI/MainLayout/UnsortedColumn/UnsortedCards/UnsortedCards_A");
        var unsortedB = GetNode<CardList>("UI/MainLayout/UnsortedColumn/UnsortedCards/UnsortedCards_B");

        var columnA = GetNode<CardList>("UI/MainLayout/SortArea/CategoryColumn_A/ColLayout/CardList");
        var columnB = GetNode<CardList>("UI/MainLayout/SortArea/CategoryColumn_B/ColLayout/CardList");
        var columnC = GetNode<CardList>("UI/MainLayout/SortArea/CategoryColumn_C/ColLayout/CardList");

        unsortedA.ColumnName = "Unsorted";
        unsortedB.ColumnName = "Unsorted";
        columnA.ColumnName = "CategoryA";
        columnB.ColumnName = "CategoryB";
        columnC.ColumnName = "CategoryC";
        
        var logger = GetNode<Logger>("Logger");
        logger.RegisterColumn("Unsorted", unsortedA);
        logger.RegisterColumn("Unsorted", unsortedB);
        logger.RegisterColumn("CategoryA", columnA);
        logger.RegisterColumn("CategoryB", columnB);
        logger.RegisterColumn("CategoryC", columnC);

        // Shuffle
        var rng = new RandomNumberGenerator();
        rng.Randomize();
        for (int i = _vocabulary.Length - 1; i > 0; i--)
        {
            int j = (int)rng.RandiRange(0, i);
            (_vocabulary[i], _vocabulary[j]) = (_vocabulary[j], _vocabulary[i]);
        }

        // Populate
        int half = _vocabulary.Length / 2;
        for (int i = 0; i < _vocabulary.Length; i++)
        {
            var card = _cardItemScene.Instantiate<CardItem>();
            var target = i < half ? unsortedA : unsortedB;
            target.AddChild(card);
            card.Init(_vocabulary[i]);
        }
    }
    
    public override void _Input(InputEvent @event)
    {
        if (@event is InputEventKey key && key.Pressed && key.Keycode == Key.Escape)
        {
            GetNode<Logger>("Logger").WriteSnapshot();
            GetTree().Quit();
        }
    }
}