using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Autofixes Genotypes.xml XmlDataHelper MODWARNs confirmed against
/// <c>XRL.GenotypeFactory.LoadGenotypeNode</c> (Managed): same-Name redeclare merges;
/// <c>Load=</c> is never parsed.
/// </summary>
public static class GenotypesXmlFixer
{
    public const string LoadStripRuleName =
        "Genotypes.xml genotype Load= strip (unused; merge is same-Name redeclare)";

    // Attrs may contain '/' inside quotes; never use [^>/]*.
    const string AttrsChunk = @"(?<attrs>(?:[^>""'/]|""[^""]*""|'[^']*')*)";

    static readonly Regex GenotypesRootRx = new(
        @"<\s*genotypes\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex GenotypeOpenRx = new(
        @"<(?<tag>genotype)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex LoadAttrRx = new(
        @"\s+Load\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !GenotypesRootRx.IsMatch(content))
            return (content, fixes);

        var load = 0;
        content = GenotypeOpenRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            if (!LoadAttrRx.IsMatch(attrs)) return m.Value;
            attrs = LoadAttrRx.Replace(attrs, "");
            load++;
            var selfClose = m.Groups["slash"].Success && m.Groups["slash"].Value.IndexOf('/') >= 0;
            return RebuildOpenTag(m.Groups["tag"].Value, attrs, selfClose);
        });

        if (load > 0)
            fixes.Add(new AppliedFix { RuleName = LoadStripRuleName, Count = load });

        return (content, fixes);
    }

    static string RebuildOpenTag(string tag, string attrs, bool selfClose) =>
        selfClose ? $"<{tag}{attrs} />" : $"<{tag}{attrs}>";
}
