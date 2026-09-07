using System.Text;

namespace XEdit.Clr;

/// <summary>TES4 header flags from wbDefinitionsSF1.pas (dev-4.1.6).</summary>
[Flags]
public enum Sf1HeaderFlags : uint
{
    Master = 1 << 0,
    Optimized = 1 << 4,
    Localized = 1 << 7,
    Small = 1 << 8,
    Update = 1 << 9,
    Medium = 1 << 10,
    Blueprint = 1 << 11
}

public sealed class PluginHeaderInfo
{
    public required string Path { get; init; }
    public uint Flags { get; init; }
    public IReadOnlyList<string> FlagNames { get; init; } = [];
    public float HedrVersion { get; init; }
    public int RecordCount { get; init; }
    public uint NextObjectId { get; init; }
    public string Author { get; init; } = "";
    public string Description { get; init; } = "";
    public IReadOnlyList<string> Masters { get; init; } = [];
    public bool IsEsm => (Flags & (uint)Sf1HeaderFlags.Master) != 0;
    public bool IsSmall => (Flags & (uint)Sf1HeaderFlags.Small) != 0;
    public bool IsMedium => (Flags & (uint)Sf1HeaderFlags.Medium) != 0;
    public bool IsBlueprint => (Flags & (uint)Sf1HeaderFlags.Blueprint) != 0;
    public bool IsLocalized => (Flags & (uint)Sf1HeaderFlags.Localized) != 0;
}

public static class PluginHeader
{
    public static PluginHeaderInfo Read(string pluginPath)
    {
        using var fs = File.Open(pluginPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var br = new BinaryReader(fs, Encoding.Latin1, leaveOpen: true);
        var sig = Encoding.ASCII.GetString(br.ReadBytes(4));
        if (sig != "TES4")
            throw new InvalidDataException($"{pluginPath} does not start with TES4 (got '{sig}').");

        var dataSize = br.ReadUInt32();
        var flags = br.ReadUInt32();
        br.ReadUInt32(); // form id
        br.ReadUInt32(); // vc
        br.ReadUInt16(); // version
        br.ReadUInt16(); // unknown

        var payload = br.ReadBytes((int)dataSize);
        float hedrVersion = 0;
        var recCount = 0;
        uint nextId = 0;
        var author = "";
        var desc = "";
        var masters = new List<string>();

        var i = 0;
        while (i + 6 <= payload.Length)
        {
            var sub = Encoding.ASCII.GetString(payload, i, 4);
            var size = BitConverter.ToUInt16(payload, i + 4);
            i += 6;
            if (i + size > payload.Length) break;
            var data = payload.AsSpan(i, size);
            i += size;

            switch (sub)
            {
                case "HEDR" when size >= 12:
                    hedrVersion = BitConverter.ToSingle(data);
                    recCount = BitConverter.ToInt32(data[4..]);
                    nextId = BitConverter.ToUInt32(data[8..]);
                    break;
                case "CNAM":
                    author = ReadZ(data);
                    break;
                case "SNAM":
                    desc = ReadZ(data);
                    break;
                case "MAST":
                    masters.Add(ReadZ(data));
                    break;
            }
        }

        var names = new List<string>();
        foreach (Sf1HeaderFlags bit in Enum.GetValues<Sf1HeaderFlags>())
        {
            if ((flags & (uint)bit) != 0)
                names.Add(bit.ToString());
        }

        return new PluginHeaderInfo
        {
            Path = Path.GetFullPath(pluginPath),
            Flags = flags,
            FlagNames = names,
            HedrVersion = hedrVersion,
            RecordCount = recCount,
            NextObjectId = nextId,
            Author = author,
            Description = desc,
            Masters = masters
        };
    }

    static string ReadZ(ReadOnlySpan<byte> data)
    {
        var end = data.IndexOf((byte)0);
        if (end < 0) end = data.Length;
        return Encoding.Latin1.GetString(data[..end]);
    }
}
