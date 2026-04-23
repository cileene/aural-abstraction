using Godot;

namespace aa_godot_viz.scripts;

// Renders a point cloud using MultiMesh — all instances share one draw call,
// so this scales to tens of thousands of points without per-object overhead.
public partial class PointCloudDemo : Node3D
{
    [Export] public int PointCount = 10000;
    [Export] public float Spread = 5f;
    // Assign a ShaderMaterial in the inspector; it must read INSTANCE_COLOR
    // to pick up the per-point color set below.
    [Export(PropertyHint.Range, "1, 20")] private float _sizeMultiply = 1f;
    [Export] public ShaderMaterial PointMaterial;

    public override void _Ready()
    {
        // MultiMeshInstance3D is the scene node; MultiMesh holds the data.
        var mmInstance = new MultiMeshInstance3D();
        AddChild(mmInstance);

        var mm = new MultiMesh();
        mm.UseColors = true;                                        // allocates per-instance color buffer
        mm.TransformFormat = MultiMesh.TransformFormatEnum.Transform3D;
        mm.InstanceCount = PointCount;

        // One shared sphere mesh — geometry is uploaded once, instanced N times.
        var sphere = new SphereMesh();
        sphere.Radius = 0.02f * _sizeMultiply;
        sphere.Height = 0.04f * _sizeMultiply;
        mm.Mesh = sphere;

        var rng = new RandomNumberGenerator();

        for (int i = 0; i < PointCount; i++)
        {
            // Random position within a cube of side 2*Spread centred at origin.
            var pos = new Vector3(
                rng.RandfRange(-Spread, Spread),
                rng.RandfRange(-Spread, Spread),
                rng.RandfRange(-Spread, Spread)
            );

            // Translation-only transform — no rotation or scale needed for spheres.
            var t = Transform3D.Identity;
            t.Origin = pos;
            mm.SetInstanceTransform(i, t);

            // Map XYZ position to RGB so spatial structure is visible as color.
            var col = new Color(
                (pos.X + Spread) / (Spread * 2f),
                (pos.Y + Spread) / (Spread * 2f),
                (pos.Z + Spread) / (Spread * 2f)
            );
            mm.SetInstanceColor(i, col);
        }

        mmInstance.Multimesh = mm;

        // Apply the inspector-assigned shader material to all instances at once.
        var mat = PointMaterial;
        mmInstance.MaterialOverride = mat;
    }
}
