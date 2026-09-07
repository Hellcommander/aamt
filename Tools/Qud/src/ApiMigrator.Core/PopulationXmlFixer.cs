using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Safe PopulationTables / Populations.xml autofixes for XmlDataHelper MODWARNs
/// confirmed against <c>XRL.PopulationManager</c> (Managed):
/// <list type="bullet">
/// <item><c>name=</c> / wrong-case → <c>Name=</c> on population/group/object/table (ParseAttribute required on population + group).</item>
/// <item><c>load=</c> / wrong-case → <c>Load=</c>; value Merge|Replace|Remove title-cased (<c>Load == "Merge"</c> is case-sensitive).</item>
/// <item><c>style=</c> / wrong-case → <c>Style=</c> on population/group.</item>
/// </list>
/// Does not invent missing group <c>Name</c> values (report-only via <see cref="PopulationXmlAdviceScanner"/>).
/// </summary>
public static class PopulationXmlFixer
{
    public const string NameCaseRuleName =
        "Populations.xml name= → Name= (population/group/object/table)";

    public const string LoadCaseRuleName =
        "Populations.xml load= → Load= + Merge|Replace|Remove casing";

    public const string StyleCaseRuleName =
        "Populations.xml style= → Style= (population/group)";

    static readonly Regex PopulationsRootRx = new(
        @"<\s*populations\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Opening tags that PopulationManager reads attrs from (attrs may span lines).
    static readonly Regex PopItemOpenRx = new(
        @"<\s*(?<tag>population|group|object|table)\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // XmlDataHelper is case-sensitive; only Name= / Load= / Style= are parsed.
    static readonly Regex WrongNameAttrRx = new(
        @"\b(?!Name\b)[Nn][Aa][Mm][Ee]\s*=",
        RegexOptions.Compiled);

    static readonly Regex WrongLoadAttrRx = new(
        @"\b(?!Load\b)[Ll][Oo][Aa][Dd]\s*=",
        RegexOptions.Compiled);

    static readonly Regex WrongStyleAttrRx = new(
        @"\b(?!Style\b)[Ss][Tt][Yy][Ll][Ee]\s*=",
        RegexOptions.Compiled);

    // Load value must match PopulationItem Merge/Remove/Replace (== "Merge" etc.).
    static readonly Regex LoadValueRx = new(
        @"(\bLoad\s*=\s*)(?<q>['""])(?<val>merge|replace|remove)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>
    /// Applies safe Populations.xml attribute casing. No-op for non-populations files.
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !PopulationsRootRx.IsMatch(content))
            return (content, fixes);

        var nameCount = 0;
        var loadCount = 0;
        var styleCount = 0;

        var next = PopItemOpenRx.Replace(content, m =>
        {
            var tag = m.Groups["tag"].Value;
            var attrs = m.Groups["attrs"].Value;
            var changed = false;

            if (WrongNameAttrRx.IsMatch(attrs))
            {
                attrs = WrongNameAttrRx.Replace(attrs, "Name=");
                nameCount++;
                changed = true;
            }

            if (WrongLoadAttrRx.IsMatch(attrs))
            {
                attrs = WrongLoadAttrRx.Replace(attrs, "Load=");
                loadCount++;
                changed = true;
            }

            // Style only on population/group (object/table ignore Style).
            if ((tag.Equals("population", StringComparison.OrdinalIgnoreCase) ||
                 tag.Equals("group", StringComparison.OrdinalIgnoreCase)) &&
                WrongStyleAttrRx.IsMatch(attrs))
            {
                attrs = WrongStyleAttrRx.Replace(attrs, "Style=");
                styleCount++;
                changed = true;
            }

            if (LoadValueRx.IsMatch(attrs))
            {
                attrs = LoadValueRx.Replace(attrs, mv =>
                {
                    var q = mv.Groups["q"].Value;
                    var raw = mv.Groups["val"].Value;
                    var title = TitleCaseLoad(raw);
                    if (string.Equals(raw, title, StringComparison.Ordinal))
                        return mv.Value;
                    loadCount++;
                    changed = true;
                    return mv.Groups[1].Value + q + title + q;
                });
            }

            return changed ? "<" + tag + attrs + ">" : m.Value;
        });

        if (nameCount > 0)
            fixes.Add(new AppliedFix { RuleName = NameCaseRuleName, Count = nameCount });
        if (loadCount > 0)
            fixes.Add(new AppliedFix { RuleName = LoadCaseRuleName, Count = loadCount });
        if (styleCount > 0)
            fixes.Add(new AppliedFix { RuleName = StyleCaseRuleName, Count = styleCount });

        return (next, fixes);
    }

    static string TitleCaseLoad(string value) => value.ToLowerInvariant() switch
    {
        "merge" => "Merge",
        "replace" => "Replace",
        "remove" => "Remove",
        _ => value,
    };
}
