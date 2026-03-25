using Godot;

public partial class CardItem : PanelContainer
{
    private Label _label;

    public string CardText { get; private set; }

    public override void _Ready()
    {
        _label = GetNode<Label>("CardLabel");
        AddToGroup("cards");
    }

    public void Init(string text)
    {
        CardText = text;
        _label.Text = text;
    }

    public override Variant _GetDragData(Vector2 atPosition)
    {
        SetDragPreview(BuildPreview());
        return CardText;
    }

    private Control BuildPreview()
    {
        var preview = (CardItem)Duplicate();
        preview.Modulate = new Color(1, 1, 1, 0.7f);
        return preview;
    }
}