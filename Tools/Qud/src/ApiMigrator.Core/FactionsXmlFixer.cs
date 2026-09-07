using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Safe Factions.xml autofixes for XmlDataHelper MODWARNs confirmed against
/// <c>XRL.World.Factions</c> (Managed): unused root/nested <c>Load="Merge"</c>,
/// <c>waterritual skill=</c> case, and typo <c>EEmblemTileColor</c>.
/// Keeps <c>Load="Replace"</c> on <c>&lt;faction&gt;</c> (only value the loader checks).
/// Does not wrap bare <c>&lt;interest&gt;</c> (report-only via <see cref="FactionsXmlAdviceScanner"/>).
/// </summary>
public static class FactionsXmlFixer
{
    public const string LoadMergeRuleName =
        "Factions.xml Load=Merge → remove (unused on factions / Merge no-op on faction)";

    public const string WaterRitualSkillCaseRuleName =
        "Factions.xml waterritual skill= → Skill=";

    public const string EmblemTileColorTypoRuleName =
        "Factions.xml EEmblemTileColor → EmblemTileColor";

    static readonly Regex FactionsRootRx = new(
        @"<\s*factions\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Opening <factions …> or <faction …> (not closes). Attrs may span lines.
    static readonly Regex FactionsOrFactionOpenRx = new(
        @"<\s*(?<tag>factions|faction)\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Only Merge — Replace on <faction> is meaningful when the name already exists.
    static readonly Regex LoadMergeAttrRx = new(
        @"\s+Load\s*=\s*(?<q>['""])Merge\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex WaterRitualOpenRx = new(
        @"<\s*waterritual\b(?<attrs>[^>]*)(?<self>/?)\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // XmlDataHelper is case-sensitive; only Skill= is parsed. Rewrite any other casing.
    static readonly Regex WrongSkillAttrNameRx = new(
        @"\b(?!Skill\b)[Ss][Kk][Ii][Ll][Ll]\s*=",
        RegexOptions.Compiled);

    static readonly Regex EmblemTypoRx = new(
        @"\bEEmblemTileColor\s*=",
        RegexOptions.Compiled);

    /// <summary>
    /// Applies safe Factions.xml hygiene. No-op for non-factions files.
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !FactionsRootRx.IsMatch(content))
            return (content, fixes);

        var working = content;

        var loadCount = 0;
        working = FactionsOrFactionOpenRx.Replace(working, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            if (!LoadMergeAttrRx.IsMatch(attrs))
                return m.Value;

            var newAttrs = LoadMergeAttrRx.Replace(attrs, "");
            loadCount++;
            return "<" + m.Groups["tag"].Value + newAttrs + ">";
        });
        if (loadCount > 0)
            fixes.Add(new AppliedFix { RuleName = LoadMergeRuleName, Count = loadCount });

        var skillCount = 0;
        working = WaterRitualOpenRx.Replace(working, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            if (!WrongSkillAttrNameRx.IsMatch(attrs))
                return m.Value;

            var newAttrs = WrongSkillAttrNameRx.Replace(attrs, "Skill=");
            skillCount++;
            return "<waterritual" + newAttrs + m.Groups["self"].Value + ">";
        });
        if (skillCount > 0)
            fixes.Add(new AppliedFix { RuleName = WaterRitualSkillCaseRuleName, Count = skillCount });

        var emblemCount = 0;
        working = EmblemTypoRx.Replace(working, _ =>
        {
            emblemCount++;
            return "EmblemTileColor=";
        });
        if (emblemCount > 0)
            fixes.Add(new AppliedFix { RuleName = EmblemTileColorTypoRuleName, Count = emblemCount });

        return (working, fixes);
    }
}
