using Godot;

[Tool]
public partial class TreeGenerator3D : Node3D
{
    [ExportGroup("Structure")]
    [Export] public int MaxDepth = 6;
    [Export] public int BranchCount = 3;
    [Export] public float BranchAngle = 28f;       // tilt from parent axis (degrees)
    [Export] public float LengthDecay = 0.65f;
    [Export] public float RadiusDecay = 0.60f;
    [Export] public float Randomness = 0.25f;      // 0 = symmetric, 1 = wild

    [ExportGroup("Dimensions")]
    [Export] public float TrunkLength = 2.5f;
    [Export] public float TrunkRadius = 0.18f;
    [Export] public float LeafRadius = 0.35f;

    [ExportGroup("Colors")]
    [Export] public Color WoodColor = new Color(0.38f, 0.22f, 0.09f);
    [Export] public Color LeafColor = new Color(0.18f, 0.65f, 0.28f);

    [ExportGroup("Generation")]
    [Export] public bool Regenerate
    {
        get => false;
        set { if (value) { _seed = GD.Randi(); Generate(); } }
    }

    private uint _seed = 42;

    public override void _Ready() => Generate();

    private void Generate()
    {
        foreach (var child in GetChildren())
            child.QueueFree();

        var rng = new RandomNumberGenerator { Seed = _seed };
        SpawnBranch(rng, this, TrunkLength, TrunkRadius, 0);
    }

    private void SpawnBranch(RandomNumberGenerator rng, Node3D parent, float length, float radius, int depth)
    {
        // --- Cylinder ---
        var meshInst = new MeshInstance3D();
        var cyl = new CylinderMesh
        {
            BottomRadius = radius,
            TopRadius    = Mathf.Max(0.01f, radius * 0.6f),
            Height       = length
        };
        meshInst.Mesh = cyl;
        meshInst.Position = new Vector3(0f, length / 2f, 0f); // center the cylinder
        meshInst.MaterialOverride = MakeMaterial(WoodColor);
        parent.AddChild(meshInst);

        // --- Leaf at terminal branches ---
        if (depth >= MaxDepth)
        {
            var leaf = new MeshInstance3D();
            var sphere = new SphereMesh();
            float r = LeafRadius * rng.RandfRange(0.75f, 1.35f);
            sphere.Radius = r;
            sphere.Height = r * 2f;
            leaf.Mesh = sphere;
            leaf.Position = new Vector3(0f, length, 0f);
            leaf.MaterialOverride = MakeMaterial(LeafColor);
            parent.AddChild(leaf);
            return;
        }

        // --- Child branches ---
        float azimuthStep = 360f / BranchCount;

        for (int i = 0; i < BranchCount; i++)
        {
            // Spread evenly around the axis, then jitter
            float azimuth = azimuthStep * i
                + rng.RandfRange(-azimuthStep * 0.4f, azimuthStep * 0.4f) * Randomness;

            float tilt = BranchAngle
                + rng.RandfRange(-BranchAngle * 0.5f, BranchAngle * 0.5f) * Randomness;

            float childLength = length * LengthDecay
                * rng.RandfRange(1f - Randomness * 0.25f, 1f + Randomness * 0.25f);

            // Pivot sits at the tip of the current branch
            var pivot = new Node3D();
            pivot.Position = new Vector3(0f, length, 0f);
            pivot.RotateY(Mathf.DegToRad(azimuth)); // spin around trunk axis
            pivot.RotateZ(Mathf.DegToRad(tilt));    // lean outward
            parent.AddChild(pivot);

            SpawnBranch(rng, pivot, childLength, radius * RadiusDecay, depth + 1);
        }
    }

    private static StandardMaterial3D MakeMaterial(Color color) => new()
    {
        AlbedoColor = color,
        RoughnessTexture = null,
        Roughness = 0.9f,
    };
}