using Godot;
using System.Collections.Generic;
using System.IO;
using System.Linq;

public partial class Logger : Node
{
    private string _filePath;
    private StreamWriter _writer;

    private readonly Dictionary<string, List<CardList>> _columns = new();

    public override void _Ready()
    {
        string dir = OS.GetUserDataDir();
        int index = 1;

        while (File.Exists(Path.Combine(dir, $"cardsort_{index}.csv")))
            index++;

        _filePath = Path.Combine(dir, $"cardsort_{index}.csv");
        _writer = new StreamWriter(_filePath, append: false);

        GD.Print($"Logger ready: {_filePath}");
    }

    public void RegisterColumn(string name, CardList list)
    {
        if (!_columns.ContainsKey(name))
            _columns[name] = new List<CardList>();
        _columns[name].Add(list);
    }

    public void WriteSnapshot()
    {
        var columnOrder = new[] { "Unsorted", "CategoryA", "CategoryB", "CategoryC" };
        var columns = columnOrder.Select(GetColumnCards).ToArray();
        int maxRows = columns.Max(c => c.Count);

        _writer.WriteLine("Unsorted,CategoryA,CategoryB,CategoryC");
        for (int i = 0; i < maxRows; i++)
        {
            var row = columns.Select(c => i < c.Count ? c[i] : "");
            _writer.WriteLine(string.Join(",", row));
        }

        _writer.Flush();
        _writer.Close();
    }

    private List<string> GetColumnCards(string name)
    {
        var cards = new List<string>();
        if (!_columns.TryGetValue(name, out var lists))
            return cards;

        foreach (var list in lists)
        foreach (Node child in list.GetChildren())
            if (child is CardItem card)
                cards.Add(card.CardText);

        return cards;
    }
}