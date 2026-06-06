using Godot;
using System.Collections.Generic;

namespace aa_godot_viz.scripts;

/// <summary>
/// 1 - Receives parameters via the SetParameters event,
/// 2 - Rebuilds the tree by recursively collecting branches (CollectBranch),
/// 3 - Scatters sphere instances across each branch surface (SampleBranchSurface),
/// 4 - Assembles all instances into a MultiMesh for rendering (BuildMultiMesh).
/// </summary>

public partial class TreeGenerator3D : Node3D
{
    // ----- EXPORT VARIABLES, same as Unity Serialized Fields (shown in the editor) -----
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

    [ExportGroup("Point Cloud")]
    // Points per unit of cylinder lateral surface area (2π·r·h).
    [Export(PropertyHint.Range, "1, 500")] public float PointDensity = 80f;

    [Export(PropertyHint.Range, "0.005, 0.1")] public float PointRadius = 0.02f;

    [Export] public ShaderMaterial PointMaterial; // the shader material for our spheres

    [ExportGroup("Debug")]
    [Export] public bool ShowCylinderMesh;

    
    // ----- PRIVATE VARIABLES -----
    // Our random number generators
    private readonly RandomNumberGenerator _structureRng = new();
    private readonly RandomNumberGenerator _pointRng = new();

    // Accumulated point data before MultiMesh is built.
    private readonly List<Vector3> _positions = new();
    private readonly List<Color> _colors = new();
    private readonly List<(Transform3D Xform, float Length, float Radius, int Depth)> _branches = new();

    
    // ----- GODOT METHODS -----
    public override void _EnterTree() // godot version of unitys awake method
    {
        EventSystem.SetParameters += OnSetParameters;
        EventSystem.ToggleMesh += OnToggleMesh;
    }

    public override void _ExitTree() // godot version of unitys OnDestroy method
    {
        EventSystem.SetParameters -= OnSetParameters;
        EventSystem.ToggleMesh -= OnToggleMesh;
    }

    
    // ----- CUSTOM METHODS -----
    
    /// <summary>
    /// Called everytime the parameters change and maps the parameters to variables in the class
    /// </summary>
    /// <param name="parameters"></param>
    private void OnSetParameters(Parameters parameters) 
    {
        // Parameter 1 - COLOR
        PointMaterial?.SetShaderParameter("param1", parameters.Param1);
        PointMaterial?.SetShaderParameter("metallic", Mathf.Lerp(0.8f, 0.2f, parameters.Param1));
        PointMaterial?.SetShaderParameter("roughness", Mathf.Lerp(0.2f, 0.8f, parameters.Param1));
        
        // Parameter 2 - SPATIALITY
        MaxDepth = Mathf.RoundToInt(Mathf.Lerp(3, 9, parameters.Param2));
        LengthDecay = Mathf.Lerp(0.79f, 0.965f, parameters.Param2);

        // Parameter 3 - COMPOSITION
        PointDensity = Mathf.Lerp(10f, 300f, parameters.Param3);
        PointRadius = Mathf.Lerp(0.04f, 0.01f, parameters.Param3);
        
        // Parameter 4 - SHAPE
        BranchAngle = Mathf.Lerp(15f, 45f, parameters.Param4);
        Randomness = Mathf.Lerp(0.5f, 0.0f, parameters.Param4);
        
        // Parameter 5 - MATERIAL
        PointMaterial?.SetShaderParameter("speed", Mathf.Lerp(0.5f, 20.0f, parameters.Param5));
        PointMaterial?.SetShaderParameter("amplitude", Mathf.Lerp(0.25f, 1.0f, parameters.Param5));
        
        Generate();
    }

    
    /// <summary>
    /// 1 - Cleans up the old tree (if there is one),
    /// 2 - Seeds our random number generators (determinism)
    /// 3 - Starts the recursive branch collection,
    /// 4 - Then builds the multimesh from the collected points.
    /// </summary>
    private void Generate()
    {
        foreach (var child in GetChildren())
            child.QueueFree();

        _positions.Clear();
        _colors.Clear();
        _branches.Clear();

        _structureRng.Seed = 42;
        _pointRng.Seed = 7;
        CollectBranch(Transform3D.Identity, TrunkLength, TrunkRadius, 0);

        if (ShowCylinderMesh) // for debugging - and demo mode
            BuildCylinderMeshes();
        else
            BuildMultiMesh();
    }

    
    /// <summary>
    /// 1 - Records this branch and samples its surface points,
    /// 2 - Returns early if we've hit MaxDepth,
    /// 3 - Otherwise picks a child count using a depth-weighted binomial distribution,
    /// 4 - Then recurses for each child with azimuth, tilt, and length (with variable amount of randomization).
    /// </summary>
    private void CollectBranch(Transform3D worldXform, float length, float radius, int depth)
    {
        _branches.Add((worldXform, length, radius, depth));
        SampleBranchSurface(worldXform, length, radius, depth);

        if (depth >= MaxDepth)
            return;

        float t = (float)depth / MaxDepth;
        float r = _structureRng.Randf();
        int count;
        if (depth == 0) // the trunk
        {
            count = 1;
        }
        else
        {
            // Binomial(n=4) distribution: thresholds are cumulative probabilities of (1-t)^4 expansion.
            // t=depth/MaxDepth slides weight from high counts near the base to low counts near the tips.
            count =
                r < (1f - t) * (1f - t) * (1f - t) * (1f - t) ? 5 :
                r < (1f - t) * (1f - t) * (1f - t) * (1f + 3f * t) ? 4 :
                r < (1f - t) * (1f - t) * (1f + 2f * t + 3f * t * t) ? 3 :
                r < 1f - t * t * t * t ? 2 : 1;
        }
        float azimuthStep = 360f / count; // cylinder edge

        for (int i = 0; i < count; i++)
        {
            // azimuth = the angle around a vertical axis
            float azimuth = azimuthStep * i
                            + _structureRng.RandfRange(-azimuthStep * 0.4f, azimuthStep * 0.4f) * Randomness;

            float tiltBase = depth == 0 ? TrunkLean : BranchAngle;
            float tilt = tiltBase + _structureRng.RandfRange(-tiltBase * 0.5f, tiltBase * 0.5f) * Randomness;
            
            float childLength = length * LengthDecay
                                       * _structureRng.RandfRange(1f - (Randomness / 2) * 0.25f,
                                           1f + (Randomness / 2) * 0.25f);

            var childXform = worldXform
                .Translated(worldXform.Basis.Y * length)
                .RotatedLocal(Vector3.Up, Mathf.DegToRad(azimuth))
                .RotatedLocal(Vector3.Back, Mathf.DegToRad(tilt));

            CollectBranch(childXform, childLength, radius * RadiusDecay, depth + 1);
        }
    }

    
    /// <summary>
    /// 1 - Computes how many points to scatter based on surface area × PointDensity,
    /// 2 - Assigns each point a color where alpha encodes depth (root = 0, tip = 1),
    /// 3 - Places each point at a random height and angle on the cylinder surface.
    /// </summary>
    private void SampleBranchSurface(Transform3D worldXform, float length, float radius, int depth)
    {
        float area = 2f * Mathf.Pi * radius * length;
        int count = Mathf.Max(1, (int)(area * PointDensity));

        float t = (float)depth / MaxDepth;
        // RGB unused by shader; alpha carries depth for cold/warm palette lerp.
        var color = new Color(1f, 1f, 1f, t);

        for (int i = 0; i < count; i++)
        {
            float height = _pointRng.RandfRange(0f, length);
            float angle = _pointRng.RandfRange(0f, Mathf.Tau);

            var localPos = new Vector3(
                Mathf.Cos(angle) * radius,
                height,
                Mathf.Sin(angle) * radius
            );

            _positions.Add(worldXform * localPos);
            _colors.Add(color);
        }
    }
    
    
    /// <summary>
    /// 1 - Creates a MultiMesh with one sphere instance per collected point,
    /// 2 - Positions each sphere at its sampled world-space location,
    /// 3 - Passes depth-encoded color to the shader via instance color.
    /// </summary>
    private void BuildMultiMesh() // our active approach
    {
        int total = _positions.Count;
        GD.Print($"TreeGenerator: {total} points");

        var mm = new MultiMesh();
        mm.UseColors = true;
        mm.TransformFormat = MultiMesh.TransformFormatEnum.Transform3D;
        mm.InstanceCount = total;

        var sphere = new SphereMesh { Radius = PointRadius, Height = PointRadius * 2f, RadialSegments = 4, Rings = 2 };
        mm.Mesh = sphere;

        for (int i = 0; i < total; i++)
        {
            var t = Transform3D.Identity;
            t.Origin = _positions[i];
            mm.SetInstanceTransform(i, t);
            mm.SetInstanceColor(i, _colors[i]);
        }

        var mmInst = new MultiMeshInstance3D { Multimesh = mm };
        if (PointMaterial != null)
            mmInst.MaterialOverride = PointMaterial;
        AddChild(mmInst);
    }

    
    // ----- NOT IMPORTANT FOR MAIN TREE GENERATION -----
    
    /// <summary>
    /// NOT our main method, only used for debugging / demo mode
    /// </summary>
    private void BuildCylinderMeshes()
    {
        var mm = new MultiMesh();
        mm.UseColors = true;
        mm.TransformFormat = MultiMesh.TransformFormatEnum.Transform3D;
        mm.InstanceCount = _branches.Count;
        mm.Mesh = new CylinderMesh { TopRadius = 1f, BottomRadius = 1f, Height = 1f };

        for (int i = 0; i < _branches.Count; i++)
        {
            var (xform, length, radius, depth) = _branches[i];

            // Scale X/Z by radius and Y by length so the unit cylinder matches this branch.
            var basis = xform.Basis;
            var scaledBasis = new Basis(basis.X * radius, basis.Y * length, basis.Z * radius);
            var centeredOrigin = xform.Origin + basis.Y * (length * 0.5f);

            mm.SetInstanceTransform(i, new Transform3D(scaledBasis, centeredOrigin));
            mm.SetInstanceColor(i, new Color(1f, 1f, 1f, (float)depth / MaxDepth));
        }

        var mmInst = new MultiMeshInstance3D { Multimesh = mm };
        if (PointMaterial != null)
            mmInst.MaterialOverride = PointMaterial;
        AddChild(mmInst);
    }
    
    /// <summary>
    /// Demo method that allows us to se the cylinders
    /// </summary>
    private void OnToggleMesh()
    {
        ShowCylinderMesh = !ShowCylinderMesh;
        Generate();
    }
}