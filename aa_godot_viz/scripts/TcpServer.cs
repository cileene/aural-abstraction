using Godot;
using System;

namespace aa_godot_viz.scripts;

public partial class TcpServer : Node
{
    private const int Port = 5001;
    private const int PacketSize = 20; // 5 floats × 4 bytes

    private Godot.TcpServer _server;
    private StreamPeerTcp _peer;

    public override void _Ready()
    {
        _server = new Godot.TcpServer();
        var err = _server.Listen(Port);
        if (err != Error.Ok)
            GD.PrintErr($"TcpServer: Failed to listen on port {Port} — {err}");
        else
            GD.Print($"TcpServer: Listening on port {Port}");
    }

    public override void _ExitTree()
    {
        _peer?.DisconnectFromHost();
        _server.Stop();
    }

    public override void _Process(double delta)
    {
        if (_peer == null && _server.IsConnectionAvailable())
        {
            _peer = _server.TakeConnection();
            GD.Print("TcpServer: Client connected");
        }

        if (_peer == null) return;

        if (_peer.GetStatus() != StreamPeerTcp.Status.Connected)
        {
            _peer = null;
            return;
        }

        if (_peer.GetAvailableBytes() < PacketSize) return;

        var result = _peer.GetData(PacketSize);
        if ((Error)(long)result[0] != Error.Ok) return;

        var bytes = (byte[])result[1];
        var p = new Parameters
        {
            Param1 = BitConverter.ToSingle(bytes, 0),
            Param2 = BitConverter.ToSingle(bytes, 4),
            Param3 = BitConverter.ToSingle(bytes, 8),
            Param4 = BitConverter.ToSingle(bytes, 12),
            Param5 = BitConverter.ToSingle(bytes, 16),
        };

        GD.Print($"TcpServer: Received — {p.Param1:F3} {p.Param2:F3} {p.Param3:F3} {p.Param4:F3} {p.Param5:F3}");
        EventSystem.RaiseSetParameters(p);
        _peer.DisconnectFromHost();
        _peer = null;
    }
}
