using Godot;

public partial class CardItem : PanelContainer
{
    private Label _label;
    private LineEdit _lineEdit;
    private bool _isEditable;

    public string CardText => _isEditable ? _lineEdit.Text : _label.Text;

    public override void _Ready()
    {
        _label = GetNode<Label>("CardLabel");
        _lineEdit = GetNode<LineEdit>("CardLineEdit");
        AddToGroup("cards");
    }

    public void Init(string text)
    {
        _label.Text = text;
    }

    public void InitEditable()
    {
        _isEditable = true;
        _label.Visible = false;
        _lineEdit.Visible = true;
        _lineEdit.MouseFilter = MouseFilterEnum.Ignore;
        _lineEdit.FocusMode = FocusModeEnum.None;
        _lineEdit.FocusExited += ExitEditMode;
        _lineEdit.TextSubmitted += _ => ExitEditMode();
    }

    public override void _GuiInput(InputEvent @event)
    {
        if (!_isEditable) return;
        if (@event is InputEventMouseButton mb && mb.Pressed
            && mb.ButtonIndex == MouseButton.Left && mb.DoubleClick)
        {
            _lineEdit.MouseFilter = MouseFilterEnum.Stop;
            _lineEdit.FocusMode = FocusModeEnum.Click;
            _lineEdit.GrabFocus();
            _lineEdit.CaretColumn = _lineEdit.Text.Length;
        }
    }

    private void ExitEditMode()
    {
        _lineEdit.ReleaseFocus();
        _lineEdit.MouseFilter = MouseFilterEnum.Ignore;
        _lineEdit.FocusMode = FocusModeEnum.None;
    }

    public override Variant _GetDragData(Vector2 atPosition)
    {
        if (_isEditable && string.IsNullOrWhiteSpace(_lineEdit.Text))
            return new Variant();
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