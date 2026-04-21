using Godot;
using System.Collections.Generic;

namespace aa_godot_viz.scripts;

/// <summary>
/// Procedural tree generator.
/// </summary>

public partial class TreeGenerator3D : Node3D
{
    [ExportGroup("Structure")]
    [Export(PropertyHint.Range, "1, 7, prefer_slider")] public int MaxDepth = 6;
    [Export(PropertyHint.Range, "1, 3, prefer_slider")] public int BranchCount = 3;
    [Export(PropertyHint.Range, "-5.0, 20.0, degrees")] public float TrunkLean = 8f;
    [Export(PropertyHint.Range, "15.0, 90.0, degrees")] public float BranchAngle = 28f;
    [Export(PropertyHint.Range, "0.75, 0.99")] public float LengthDecay = 0.65f;
    [Export(PropertyHint.Range, "0.5, 0.99")] public float RadiusDecay = 0.60f;
    [Export(PropertyHint.Range, "0.0, 0.99")] public float Randomness = 0.25f;

    [ExportGroup("Dimensions")]
    [Export(PropertyHint.Range, "1.0, 2.5")] public float TrunkLength = 2.0f;
    [Export(PropertyHint.Range, "0.18, 0.9")] public float TrunkRadius = 0.18f;

    [ExportGroup("Leafs")]
    [Export] public bool ShowLeafs = false;
    [Export] public float LeafRadius = 0.35f;

    [ExportGroup("Materials")]
    [Export] public Material WoodMaterial;
    [Export] public Material LeafMaterial;

    [ExportGroup("Fallback Colors")]
    [Export] public Color WoodColor = new Color(0.38f, 0.22f, 0.09f);
    [Export] public Color LeafColor = new Color(0.18f, 0.65f, 0.28f);

    [ExportGroup("Growth Animation")]
    [Export] public bool AnimateGrowth = true;
    [Export(PropertyHint.Range, "1,5000,1")] public float PartsPerSecond = 120.0f;
    [Export] public bool AutoGrowOnGenerate = true;

    private const int MaxNodes = 50_000;
    private int _nodeCount = 0;
    private uint _seed = 42;

    private bool _isGrowing;
    private readonly Queue<BranchJob> _growthQueue = new();
    private RandomNumberGenerator _growthRng;
    private double _growthBudget = 0.0;

    private struct BranchJob
    {
        public Node3D Parent;
        public float Length;
        public float Radius;
        public int Depth;
    }

    public override void _EnterTree()
    {
        EventSystem.ImpulseSent += OnImpulseSent;
        EventSystem.SetParameters += OnSetParameters;
    }

    public override void _ExitTree()
    {
        EventSystem.ImpulseSent -= OnImpulseSent;
        EventSystem.SetParameters -= OnSetParameters;
    }

    private void OnImpulseSent()
    {
        _seed = GD.Randi();
        Generate();
    }

    private void OnSetParameters(Parameters parameters)
    {
        MaxDepth = Mathf.RoundToInt(Mathf.Lerp(3, 7, parameters.Param3));
        BranchCount = Mathf.RoundToInt(Mathf.Lerp(2, 3, parameters.Param3));
        LengthDecay = Mathf.Lerp(0.75f, 0.99f, parameters.Param2);
        BranchAngle = Mathf.Lerp(15f, 45f, parameters.Param4);
        Generate();
    }

    public override void _Ready() => Generate();

    public override void _Process(double delta)
    {
        if (!_isGrowing)
            return;

        float rate = Mathf.Max(1.0f, PartsPerSecond);
        _growthBudget += delta * rate;

        int steps = (int)_growthBudget;
        if (steps <= 0)
            return;

        _growthBudget -= steps;

        for (int i = 0; i < steps; i++)
        {
            if (_growthQueue.Count == 0)
            {
                _isGrowing = false;
                _growthBudget = 0.0;
                return;
            }

            SpawnBranchStep(_growthQueue.Dequeue());
        }
    }

    private void Generate()
    {
        long estimated = (long)Mathf.Pow(BranchCount, MaxDepth);
        GD.Print($"TreeGenerator: estimated ~{estimated:N0} leaf nodes");

        _isGrowing = false;
        _growthBudget = 0.0;
        _growthQueue.Clear();

        foreach (var child in GetChildren())
            child.QueueFree();

        _nodeCount = 0;

        if (AnimateGrowth && AutoGrowOnGenerate)
        {
            _growthRng = new RandomNumberGenerator { Seed = _seed };
            _growthQueue.Enqueue(new BranchJob
            {
                Parent = this,
                Length = TrunkLength,
                Radius = TrunkRadius,
                Depth = 0
            });
            _isGrowing = true;
            return;
        }

        var rng = new RandomNumberGenerator { Seed = _seed };
        SpawnBranch(rng, this, TrunkLength, TrunkRadius, 0);
    }

    private void SpawnBranchStep(BranchJob job)
    {
        if (job.Parent == null || !IsInstanceValid(job.Parent))
            return;

        if (_nodeCount > MaxNodes)
        {
            GD.PushWarning($"TreeGenerator: node limit ({MaxNodes}) reached - reduce BranchCount or MaxDepth.");
            _isGrowing = false;
            _growthQueue.Clear();
            return;
        }

        _nodeCount++;

        // Branch cylinder
        var meshInst = new MeshInstance3D();
        var cyl = new CylinderMesh
        {
            BottomRadius = job.Radius,
            TopRadius = Mathf.Max(0.01f, job.Radius * 0.6f),
            Height = job.Length
        };
        meshInst.Mesh = cyl;
        meshInst.Position = new Vector3(0f, job.Length / 2f, 0f);
        meshInst.MaterialOverride = WoodMaterial ?? MakeWoodMaterial(WoodColor);
        job.Parent.AddChild(meshInst);

        // Leaf at terminal branches
        if (job.Depth >= MaxDepth)
        {
            if (!ShowLeafs)
                return;

            var leaf = new MeshInstance3D();
            float r = LeafRadius * _growthRng.RandfRange(0.75f, 1.35f);

            var quad = new QuadMesh
            {
                Size = new Vector2(r * 2f, r * 2f)
            };

            leaf.Mesh = quad;
            leaf.Position = new Vector3(0f, job.Length, 0f);
            leaf.MaterialOverride = LeafMaterial ?? MakeLeafMaterial(LeafColor);

            job.Parent.AddChild(leaf);
            return;
        }

        // Child branches
        int count = job.Depth == 0 ? 1 : BranchCount;
        float azimuthStep = 360f / count;

        for (int i = 0; i < BranchCount; i++)
        {
            float azimuth = azimuthStep * i
                + _growthRng.RandfRange(-azimuthStep * 0.4f, azimuthStep * 0.4f) * Randomness;

            float tiltBase = job.Depth == 0 ? TrunkLean : BranchAngle;
            float tilt = tiltBase
                + _growthRng.RandfRange(-tiltBase * 0.5f, tiltBase * 0.5f) * Randomness;

            float childLength = job.Length * LengthDecay
                * _growthRng.RandfRange(1f - Randomness * 0.25f, 1f + Randomness * 0.25f);

            var pivot = new Node3D();
            pivot.Position = new Vector3(0f, job.Length, 0f);
            pivot.RotateY(Mathf.DegToRad(azimuth));
            pivot.RotateZ(Mathf.DegToRad(tilt));
            job.Parent.AddChild(pivot);

            _growthQueue.Enqueue(new BranchJob
            {
                Parent = pivot,
                Length = childLength,
                Radius = job.Radius * RadiusDecay,
                Depth = job.Depth + 1
            });
        }
    }

    // Instant path (used when AnimateGrowth is false)
    private void SpawnBranch(RandomNumberGenerator rng, Node3D parent, float length, float radius, int depth)
    {
        if (_nodeCount > MaxNodes)
        {
            GD.PushWarning($"TreeGenerator: node limit ({MaxNodes}) reached - reduce BranchCount or MaxDepth.");
            return;
        }

        _nodeCount++;

        // Branch cylinder
        var meshInst = new MeshInstance3D();
        var cyl = new CylinderMesh
        {
            BottomRadius = radius,
            TopRadius = Mathf.Max(0.01f, radius * 0.6f),
            Height = length
        };
        meshInst.Mesh = cyl;
        meshInst.Position = new Vector3(0f, length / 2f, 0f);
        meshInst.MaterialOverride = WoodMaterial ?? MakeWoodMaterial(WoodColor);
        parent.AddChild(meshInst);

        // Leaf at terminal branches
        if (depth >= MaxDepth)
        {
            if (!ShowLeafs)
                return;

            var leaf = new MeshInstance3D();
            float r = LeafRadius * rng.RandfRange(0.75f, 1.35f);

            var quad = new QuadMesh
            {
                Size = new Vector2(r * 2f, r * 2f)
            };

            leaf.Mesh = quad;
            leaf.Position = new Vector3(0f, length, 0f);
            leaf.MaterialOverride = LeafMaterial ?? MakeLeafMaterial(LeafColor);

            parent.AddChild(leaf);
            return;
        }

        // Child branches
        int count = depth == 0 ? 1 : BranchCount;
        float azimuthStep = 360f / count;

        for (int i = 0; i < BranchCount; i++)
        {
            float azimuth = azimuthStep * i
                + rng.RandfRange(-azimuthStep * 0.4f, azimuthStep * 0.4f) * Randomness;

            float tiltBase = depth == 0 ? TrunkLean : BranchAngle;
            float tilt = tiltBase
                + rng.RandfRange(-tiltBase * 0.5f, tiltBase * 0.5f) * Randomness;

            float childLength = length * LengthDecay
                * rng.RandfRange(1f - Randomness * 0.25f, 1f + Randomness * 0.25f);

            var pivot = new Node3D();
            pivot.Position = new Vector3(0f, length, 0f);
            pivot.RotateY(Mathf.DegToRad(azimuth));
            pivot.RotateZ(Mathf.DegToRad(tilt));
            parent.AddChild(pivot);

            SpawnBranch(rng, pivot, childLength, radius * RadiusDecay, depth + 1);
        }
    }

    private static StandardMaterial3D MakeWoodMaterial(Color color) => new()
    {
        AlbedoColor = color,
        Roughness = 0.9f
    };

    private static StandardMaterial3D MakeLeafMaterial(Color color) => new()
    {
        AlbedoColor = color,
        Roughness = 0.9f,
        BillboardMode = BaseMaterial3D.BillboardModeEnum.Enabled,
        Transparency = BaseMaterial3D.TransparencyEnum.Alpha
    };
}