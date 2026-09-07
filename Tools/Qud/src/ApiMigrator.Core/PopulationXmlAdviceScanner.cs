using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Report-only Populations.xml hygiene for Player.log XmlDataHelper MODWARNs that are
/// not safe to invent: required <c>Name</c> on <c>&lt;group&gt;</c> (and leftover wrong-case
/// attrs if Fixer was skipped). Gated on <c>&lt;populations</c> root.
/// </summary>
public static class PopulationXmlAdviceScanner
{
    public const string GroupNameMissingMember = "PopulationXml.GroupNameMissing";
    public const string AttrCaseMember = "PopulationXml.AttrCase";

    static readonly Regex PopulationsRootRx = new(
        @"<\s*populations\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex GroupOpenRx = new(
        @"<\s*group\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex NameAttrRx = new(
        @"\bName\s*=",
        RegexOptions.Compiled);

    // Leftover wrong-case after Fixer skipped / dry-run.
    static readonly Regex WrongCaseAttrRx = new(
        @"\b(?:(?!Name\b)[Nn][Aa][Mm][Ee]|(?!Load\b)[Ll][Oo][Aa][Dd]|(?!Style\b)[Ss][Tt][Yy][Ll][Ee])\s*=",
        RegexOptions.Compiled);

    static readonly Regex PopItemOpenRx = new(
        @"<\s*(?<tag>population|group|object|table)\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content) || !PopulationsRootRx.IsMatch(content))
            return hits;

        foreach (Match m in GroupOpenRx.Matches(content))
        {
            var attrs = m.Groups["attrs"].Value;
            if (NameAttrRx.IsMatch(attrs)) continue;

            hits.Add(new RemainingHit
            {
                Line = LineOf(content, m.Index),
                Member = GroupNameMissingMember,
                Message = "Required attribute Name missing on <group> (PopulationManager.LoadPopulationGroup)",
                Advice = ManualAdvice.PopulationGroupNameAdvice(),
                NeedsManual = true,
                Text = LineText(content, m.Index),
            });
        }

        foreach (Match m in PopItemOpenRx.Matches(content))
        {
            var attrs = m.Groups["attrs"].Value;
            if (!WrongCaseAttrRx.IsMatch(attrs)) continue;

            hits.Add(new RemainingHit
            {
                Line = LineOf(content, m.Index),
                Member = AttrCaseMember,
                Message = "Unused / wrong-case population attribute (XmlDataHelper is case-sensitive: Name, Load, Style)",
                Advice = ManualAdvice.PopulationAttrCaseAdvice(),
                NeedsManual = true,
                Text = LineText(content, m.Index),
            });
        }

        return hits;
    }

    static int LineOf(string text, int index)
    {
        var line = 1;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            if (text[i] == '\n') line++;
        }
        return line;
    }

    static string LineText(string text, int index)
    {
        var start = index;
        while (start > 0 && text[start - 1] != '\n') start--;
        var end = index;
        while (end < text.Length && text[end] != '\r' && text[end] != '\n') end++;
        return text.Substring(start, end - start).Trim();
    }
}
