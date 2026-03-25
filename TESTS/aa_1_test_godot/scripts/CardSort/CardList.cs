using Godot;

public partial class CardList : VBoxContainer
{
    public string ColumnName { get; set; }

    public override bool _CanDropData(Vector2 atPosition, Variant data)
    {
        return data.VariantType == Variant.Type.String;
    }

    public override void _DropData(Vector2 atPosition, Variant data)
    {
        string cardText = data.AsString();

        // Find the card in the tree and reparent it
        CardItem card = FindCard(cardText);
        if (card == null) return;

        card.Reparent(this);
        
        
    }

    private CardItem FindCard(string cardText)
    {
        foreach (Node node in GetTree().GetNodesInGroup("cards"))
        {
            if (node is CardItem card && card.CardText == cardText)
                return card;
        }
        return null;
    }
}