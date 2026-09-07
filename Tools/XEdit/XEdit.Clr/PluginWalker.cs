using System.IO.Compression;
using System.Text;

namespace XEdit.Clr;

public sealed class IndexedRecord
{
    public required string Signature { get; init; }
    public required uint FormId { get; init; }
    public string EditorId { get; init; } = "";
    public uint Flags { get; init; }
    public bool Compressed { get; init; }
    public string FormIdHex => FormId.ToString("X8");
}

public sealed class PluginIndex
{
    public required string Path { get; init; }
    public required PluginHeaderInfo Header { get; init; }
    public IReadOnlyList<string> TopGroups { get; init; } = [];
    public IReadOnlyList<IndexedRecord> Records { get; init; } = [];
}

public static class PluginWalker
{
    const uint CompressedFlag = 0x00040000;

    public static PluginIndex Index(string pluginPath, string? signature = null, int limit = 0)
    {
        var header = PluginHeader.Read(pluginPath);
        var groups = new List<string>();
        var records = new List<IndexedRecord>();

        using var fs = File.Open(pluginPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var br = new BinaryReader(fs, Encoding.Latin1, leaveOpen: true);

        Walk(br, fs.Length, groups, records, signature, limit, topLevel: true);

        return new PluginIndex
        {
            Path = Path.GetFullPath(pluginPath),
            Header = header,
            TopGroups = groups,
            Records = records
        };
    }

    static void Walk(BinaryReader br, long end, List<string> groups, List<IndexedRecord> records,
        string? signature, int limit, bool topLevel)
    {
        while (br.BaseStream.Position + 24 <= end)
        {
            if (limit > 0 && records.Count >= limit)
                return;

            var start = br.BaseStream.Position;
            var sig = Encoding.ASCII.GetString(br.ReadBytes(4));
            var size = br.ReadUInt32();

            if (sig == "GRUP")
            {
                var label = Encoding.ASCII.GetString(br.ReadBytes(4));
                var gtype = br.ReadInt32();
                br.ReadUInt32();
                br.ReadUInt32();
                if (topLevel && gtype == 0 && label.Length == 4)
                    groups.Add(label);
                var groupEnd = start + size;
                if (groupEnd > end) groupEnd = end;
                Walk(br, groupEnd, groups, records, signature, limit, topLevel: false);
                br.BaseStream.Position = groupEnd;
                continue;
            }

            var flags = br.ReadUInt32();
            var formId = br.ReadUInt32();
            br.ReadUInt32();
            br.ReadUInt16();
            br.ReadUInt16();

            var dataStart = br.BaseStream.Position;
            var dataEnd = dataStart + size;
            if (dataEnd > br.BaseStream.Length)
                break;

            var want = signature is null || sig.Equals(signature, StringComparison.OrdinalIgnoreCase);
            var edid = "";
            var compressed = (flags & CompressedFlag) != 0;
            if (want)
            {
                var data = br.ReadBytes((int)size);
                edid = TryReadEditorId(data, compressed);
                records.Add(new IndexedRecord
                {
                    Signature = sig,
                    FormId = formId,
                    EditorId = edid,
                    Flags = flags,
                    Compressed = compressed
                });
            }
            else
            {
                br.BaseStream.Position = dataEnd;
            }
        }
    }

    static string TryReadEditorId(byte[] data, bool compressed)
    {
        try
        {
            var payload = data;
            if (compressed)
            {
                if (data.Length < 6) return "";
                var uncompressed = BitConverter.ToInt32(data, 0);
                using var ms = new MemoryStream(data, 4, data.Length - 4);
                using var z = new ZLibStream(ms, CompressionMode.Decompress);
                using var outMs = new MemoryStream(Math.Max(uncompressed, 16));
                z.CopyTo(outMs);
                payload = outMs.ToArray();
            }

            var i = 0;
            while (i + 6 <= payload.Length)
            {
                var sub = Encoding.ASCII.GetString(payload, i, 4);
                var size = BitConverter.ToUInt16(payload, i + 4);
                i += 6;
                if (i + size > payload.Length) break;
                if (sub == "EDID")
                {
                    var n = size;
                    if (n > 0 && payload[i + n - 1] == 0) n--;
                    return Encoding.Latin1.GetString(payload, i, n);
                }
                i += size;
            }
        }
        catch
        {
            // lz4 or truncated — skip EDID
        }

        return "";
    }
}
