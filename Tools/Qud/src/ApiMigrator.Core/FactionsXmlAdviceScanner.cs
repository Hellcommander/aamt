using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Report-only Factions.xml hygiene for Player.log XmlDataHelper MODWARNs.
/// Bare <c>&lt;interest&gt;</c> under <c>&lt;faction&gt;</c> (must be under <c>&lt;interests&gt;</c>)
/// is never auto-wrapped. Leftover <c>Load=Merge</c> / wrong-case <c>skill=</c> /
/// <c>EEmblemTileColor</c> are flagged if still present after <see cref="FactionsXmlFixer"/>.
/// </summary>
public static class FactionsXmlAdviceScanner
{
    public const string BareInterestMember = "FactionsXml.BareInterest";
    public const string LoadMergeMember = "FactionsXml.LoadMerge";
    public const string WaterRitualSkillCaseMember = "FactionsXml.WaterRitualSkillCase";
    public const string EmblemTileColorTypoMember = "FactionsXml.EEmblemTileColor";

    static readonly Regex FactionsRootRx = new(
        @"<\s*factions\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex TagRx = new(
        @"<!--[\s\S]*?-->|</(?<close>faction|interests|waterritual)\s*>|<(?<open>faction|interests|interest|waterritual|factions)\b(?<attrs>[^>]*?)(?<self>/?)\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex LoadMergeAttrRx = new(
        @"\bLoad\s*=\s*(['""])Merge\1",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex WrongSkillAttrRx = new(
        @"\b(?!Skill\b)[Ss][Kk][Ii][Ll][Ll]\s*=",
        RegexOptions.Compiled);

    static readonly Regex EmblemTypoRx = new(
        @"\bEEmblemTileColor\s*=",
        RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content) || !FactionsRootRx.IsMatch(content))
            return hits;

        var seen = new HashSet<(int Line, string Member)>();
        var stack = new Stack<string>();

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
                    if (top == closeName)
                        break;
                }
                continue;
            }

            var open = m.Groups["open"].Value.ToLowerInvariant();
            var attrs = m.Groups["attrs"].Value;
            var selfClose = m.Groups["self"].Value.Contains('/');

            if (open is "factions" or "faction")
            {
                if (LoadMergeAttrRx.IsMatch(attrs))
                {
                    var line = GetLineNumber(content, m.Index);
                    if (seen.Add((line, LoadMergeMember)))
                    {
                        hits.Add(new RemainingHit
                        {
                            Line = line,
                            Member = LoadMergeMember,
                            Message =
                                "Unused attribute 'Load' on <" + open + "> (Merge unused; Replace only when name exists)",
                            Advice = ManualAdvice.FactionsLoadMergeAdvice(),
                            NeedsManual = true,
                            Text = GetLineText(content, m.Index).Trim(),
                        });
                    }
                }

                if (!selfClose && open == "faction")
                    stack.Push("faction");
                continue;
            }

            if (open == "interests")
            {
                if (!selfClose)
                    stack.Push("interests");
                continue;
            }

            if (open == "interest")
            {
                var parent = stack.Count > 0 ? stack.Peek() : "";
                if (parent == "faction")
                {
                    var line = GetLineNumber(content, m.Index);
                    if (seen.Add((line, BareInterestMember)))
                    {
                        hits.Add(new RemainingHit
                        {
                            Line = line,
                            Member = BareInterestMember,
                            Message =
                                "Unexpected 'interest' element (XmlDataHelper — wrap under <interests>)",
                            Advice = ManualAdvice.FactionsBareInterestAdvice(),
                            NeedsManual = true,
                            Text = GetLineText(content, m.Index).Trim(),
                        });
                    }
                }
                continue;
            }

            if (open == "waterritual")
            {
                if (WrongSkillAttrRx.IsMatch(attrs))
                {
                    var line = GetLineNumber(content, m.Index);
                    if (seen.Add((line, WaterRitualSkillCaseMember)))
                    {
                        hits.Add(new RemainingHit
                        {
                            Line = line,
                            Member = WaterRitualSkillCaseMember,
                            Message = "Unused attribute 'skill' on <waterritual> (attribute is Skill, case-sensitive)",
                            Advice = ManualAdvice.FactionsWaterRitualSkillAdvice(),
                            NeedsManual = true,
                            Text = GetLineText(content, m.Index).Trim(),
                        });
                    }
                }
            }
        }

        foreach (Match m in EmblemTypoRx.Matches(content))
        {
            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, EmblemTileColorTypoMember)))
                continue;
            hits.Add(new RemainingHit
            {
                Line = line,
                Member = EmblemTileColorTypoMember,
                Message = "Unused attribute 'EEmblemTileColor' (typo — use EmblemTileColor)",
                Advice = ManualAdvice.FactionsEmblemTileColorAdvice(),
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
