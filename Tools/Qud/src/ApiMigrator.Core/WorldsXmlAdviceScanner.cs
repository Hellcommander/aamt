using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Report-only Worlds.xml hygiene for Player.log XmlDataHelper MODWARNs:
/// zone Load create conflicts, unexpected cell-level <c>builder</c>, and
/// (when not already stripped) cell <c>DisableForcedConnections</c>.
/// Never auto-sets Merge vs Replace; never auto-deletes builders.
/// </summary>
public static class WorldsXmlAdviceScanner
{
    public const string ZoneLoadMember = "WorldsXml.ZoneLoadCreate";
    public const string CellBuilderMember = "WorldsXml.CellBuilder";
    public const string CellDisableForcedMember = "WorldsXml.CellDisableForcedConnections";

    static readonly Regex WorldsRootRx = new(
        @"<\s*worlds\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Comments, closes, and opens for the Worlds.xml element set we care about.
    static readonly Regex TagRx = new(
        @"<!--[\s\S]*?-->|</(?<close>world|cell|zone)\s*>|<(?<open>world|cell|zone|builder|postbuilder|music|map|properties)\b(?<attrs>[^>]*?)(?<self>/?)\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex LoadMergeOrReplaceRx = new(
        @"\bLoad\s*=\s*(['""])(?:Merge|Replace)\1",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex AnyLoadAttrRx = new(
        @"\bLoad\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DisableForcedOnCellOpenRx = new(
        @"<\s*cell\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DisableForcedAttrRx = new(
        @"\bDisableForcedConnections\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content) || !WorldsRootRx.IsMatch(content))
            return hits;

        var seen = new HashSet<(int Line, string Member)>();
        var stack = new Stack<(string Name, bool CellMergeContext)>();

        foreach (Match m in TagRx.Matches(content))
        {
            if (m.Value.StartsWith("<!--", StringComparison.Ordinal))
                continue;

            if (m.Groups["close"].Success)
            {
                var closeName = m.Groups["close"].Value.ToLowerInvariant();
                while (stack.Count > 0)
                {
                    var top = stack.Pop();
                    if (top.Name == closeName)
                        break;
                }
                continue;
            }

            var open = m.Groups["open"].Value.ToLowerInvariant();
            var attrs = m.Groups["attrs"].Value;
            var selfClose = m.Groups["self"].Value.Contains('/');

            if (open is "world" or "cell" or "zone")
            {
                var cellMerge = open == "cell" && LoadMergeOrReplaceRx.IsMatch(attrs);
                // Inherit merge context from ancestor cell when pushing nested zone.
                var inherit = stack.Count > 0 && stack.Peek().CellMergeContext;
                var mergeCtx = open == "cell" ? cellMerge : (open == "zone" ? inherit : false);

                if (open == "zone" && mergeCtx && !AnyLoadAttrRx.IsMatch(attrs))
                {
                    var line = GetLineNumber(content, m.Index);
                    if (seen.Add((line, ZoneLoadMember)))
                    {
                        hits.Add(new RemainingHit
                        {
                            Line = line,
                            Member = ZoneLoadMember,
                            Message =
                                "Found existing zone … load mode create doesn't indicate replace or merge (XmlDataHelper)",
                            Advice = ManualAdvice.WorldsZoneLoadAdvice(),
                            NeedsManual = true,
                            Text = GetLineText(content, m.Index).Trim(),
                        });
                    }
                }

                if (!selfClose)
                    stack.Push((open, open == "cell" ? cellMerge : mergeCtx));
                continue;
            }

            if (open == "builder")
            {
                var parent = stack.Count > 0 ? stack.Peek().Name : "";
                if (parent == "cell")
                {
                    var line = GetLineNumber(content, m.Index);
                    if (seen.Add((line, CellBuilderMember)))
                    {
                        hits.Add(new RemainingHit
                        {
                            Line = line,
                            Member = CellBuilderMember,
                            Message = "Unexpected 'builder' element (XmlDataHelper — cells allow zone/properties only)",
                            Advice = ManualAdvice.WorldsCellBuilderAdvice(),
                            NeedsManual = true,
                            Text = GetLineText(content, m.Index).Trim(),
                        });
                    }
                }
            }
        }

        // Leftover cell DisableForcedConnections (Fixer should strip under migrate; flag if still present).
        foreach (Match m in DisableForcedOnCellOpenRx.Matches(content))
        {
            if (!DisableForcedAttrRx.IsMatch(m.Groups["attrs"].Value))
                continue;
            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, CellDisableForcedMember)))
                continue;
            hits.Add(new RemainingHit
            {
                Line = line,
                Member = CellDisableForcedMember,
                Message = "Unused attribute 'DisableForcedConnections' on <cell> (valid on <zone> only)",
                Advice = ManualAdvice.WorldsCellDisableForcedAdvice(),
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        return hits;
    }

    static int GetLineNumber(string text, int index)
    {
        var count = 1;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            if (text[i] == '\n') count++;
        }
        return count;
    }

    static string GetLineText(string text, int index)
    {
        var start = index <= 0 ? -1 : text.LastIndexOf('\n', index - 1);
        var end = text.IndexOf('\n', index);
        if (end < 0) end = text.Length;
        var s = start + 1;
        return s <= end && s >= 0 && s <= text.Length ? text.Substring(s, Math.Max(end - s, 0)) : "";
    }
}
