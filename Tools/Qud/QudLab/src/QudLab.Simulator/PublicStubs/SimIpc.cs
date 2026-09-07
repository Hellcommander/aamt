using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;

namespace QudLab.Simulator;

/// <summary>
/// MIT TCP client for a privately built SimHost. Does not contain the simulator.
/// </summary>
public static class SimIpc
{
    public const int DefaultPort = 47822;

    public static async Task<SimSnapshot> CallRemoteAsync(
        SimRequest request,
        string host = "127.0.0.1",
        int port = DefaultPort,
        CancellationToken ct = default)
    {
        using var client = new TcpClient();
        await client.ConnectAsync(host, port, ct);
        await using var stream = client.GetStream();
        var json = JsonSerializer.Serialize(request, CacheIO.JsonOptions);
        var bytes = Encoding.UTF8.GetBytes(json + "\n");
        await stream.WriteAsync(bytes, ct);
        using var reader = new StreamReader(stream, Encoding.UTF8);
        var line = await reader.ReadLineAsync(ct) ?? "{}";
        return JsonSerializer.Deserialize<SimSnapshot>(line, CacheIO.JsonOptions) ?? new SimSnapshot();
    }

    public static async Task<bool> IsReachableAsync(
        string host = "127.0.0.1",
        int port = DefaultPort,
        int timeoutMs = 400)
    {
        try
        {
            using var cts = new CancellationTokenSource(timeoutMs);
            using var client = new TcpClient();
            await client.ConnectAsync(host, port, cts.Token);
            return client.Connected;
        }
        catch
        {
            return false;
        }
    }
}
