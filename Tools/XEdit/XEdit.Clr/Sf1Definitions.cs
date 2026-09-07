using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace XEdit.Clr;

public sealed class Sf1RecordDef
{
    public required string Signature { get; init; }
    public required string Name { get; init; }
    public int Line { get; init; }
}

public sealed class Sf1DefinitionCatalog
{
    public string Source { get; init; } = "";
    public string ForkCommit { get; init; } = "";
    public IReadOnlyList<Sf1RecordDef> Records { get; init; } = [];
    public IReadOnlyList<string> GroupOrder { get; init; } = [];
    public IReadOnlyList<string> OfficialDlc { get; init; } = [];
    public IReadOnlyList<string> StarfieldSignatures { get; init; } = [];

    [JsonIgnore] public int RecordCount => Records.Count;
}

/// <summary>
/// Reads TES5Edit Core/wbDefinitionsSF1.pas so the AI knows current Starfield
/// record types without launching xEdit.
/// </summary>
public static class Sf1Definitions
{
    static readonly Regex RecordRx = new(@"wbRecord\(\s*([A-Z0-9_]{4})\s*,\s*'([^']*)'", RegexOptions.Compiled);
    static readonly Regex GroupRx = new(@"wbAddGroupOrder\(\s*([A-Z0-9_]{4})\s*\)", RegexOptions.Compiled);
    static readonly Regex DlcRx = new(@"wbOfficialDLC\[\d+\]\s*:=\s*'([^']+)'", RegexOptions.Compiled);
    static readonly Regex SigCommentRx = new(@"^\s+([A-Z0-9]{4})\s*:\s*TwbSignature\s*=\s*'[^']+'\s*;\s*\{\s*New To Starfield", RegexOptions.Compiled | RegexOptions.Multiline);

    public static Sf1DefinitionCatalog Load()
    {
        var fork = XEditFork.Load();
        var path = fork.DefinitionsPath;
        if (!File.Exists(path))
            throw new FileNotFoundException("TES5Edit Starfield definitions missing. Run xedit-assist sync.", path);

        var text = File.ReadAllText(path);
        var records = new List<Sf1RecordDef>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var lineNo = 1;
        using (var reader = new StringReader(text))
        {
            string? line;
            while ((line = reader.ReadLine()) is not null)
            {
                var m = RecordRx.Match(line);
                if (m.Success)
                {
                    var sig = m.Groups[1].Value;
                    if (seen.Add(sig))
                    {
                        records.Add(new Sf1RecordDef
                        {
                            Signature = sig,
                            Name = m.Groups[2].Value,
                            Line = lineNo
                        });
                    }
                }
                lineNo++;
            }
        }

        var groups = GroupRx.Matches(text).Select(m => m.Groups[1].Value).Distinct().ToList();
        var dlc = DlcRx.Matches(text).Select(m => m.Groups[1].Value).ToList();

        var sigFile = Path.Combine(XEditPaths.Tes5EditDir, "Core", "wbDefinitionsSignatures.pas");
        var starfieldSigs = new List<string>();
        if (File.Exists(sigFile))
        {
            starfieldSigs = SigCommentRx.Matches(File.ReadAllText(sigFile))
                .Select(m => m.Groups[1].Value)
                .Distinct()
                .OrderBy(s => s)
                .ToList();
        }

        return new Sf1DefinitionCatalog
        {
            Source = path,
            ForkCommit = fork.LocalCommit,
            Records = records,
            GroupOrder = groups,
            OfficialDlc = dlc,
            StarfieldSignatures = starfieldSigs
        };
    }

    public static Sf1RecordDef? Find(string signature)
    {
        var cat = Load();
        return cat.Records.FirstOrDefault(r => r.Signature.Equals(signature, StringComparison.OrdinalIgnoreCase));
    }
}
