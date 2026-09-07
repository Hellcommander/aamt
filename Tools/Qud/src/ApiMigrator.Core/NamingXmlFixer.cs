using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Autofixes Naming.xml XmlDataHelper MODWARNs confirmed against <c>XRL.Names.NameStyles</c>:
/// <list type="bullet">
/// <item>Deprecated <c>*Var*</c> template placeholders → <c>=var=</c> (first letter lowercased).</item>
/// <item><c>templatevar Name</c> PascalCase → camelCase (first letter lowercased).</item>
/// <item>Unused <c>Load=</c> on <c>templatevar</c> — strip.</item>
/// </list>
/// </summary>
public static class NamingXmlFixer
{
    public const string StarVarRuleName =
        "Naming.xml template *Var* → =var= (deprecated Variables Format)";

    public const string TemplateVarCaseRuleName =
        "Naming.xml templatevar Name PascalCase → camelCase";

    public const string TemplateVarLoadRuleName =
        "Naming.xml templatevar Load= strip (unused)";

    // Attrs may contain '/' inside quotes.
    const string AttrsChunk = @"(?<attrs>(?:[^>""'/]|""[^""]*""|'[^']*')*)";

    static readonly Regex NamingRootRx = new(
        @"<\s*naming\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex TemplateOpenRx = new(
        @"<(?<tag>template)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex TemplateVarOpenRx = new(
        @"<(?<tag>templatevar)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex NameAttrRx = new(
        @"\bName\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex StarVarRx = new(
        @"\*(?<name>[A-Za-z][A-Za-z0-9_]*)\*",
        RegexOptions.Compiled);

    static readonly Regex LoadAttrRx = new(
        @"\s+Load\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !NamingRootRx.IsMatch(content))
            return (content, fixes);

        var star = 0;
        var camel = 0;
        var load = 0;

        content = TemplateOpenRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            var nameMatch = NameAttrRx.Match(attrs);
            if (!nameMatch.Success) return m.Value;

            var val = nameMatch.Groups["val"].Value;
            var q = nameMatch.Groups["q"].Value;
            var replaced = StarVarRx.Replace(val, sm =>
            {
                star++;
                return "=" + ToCamel(sm.Groups["name"].Value) + "=";
            });
            if (replaced == val) return m.Value;

            var newAttrs = NameAttrRx.Replace(attrs,
                $" Name={q}{replaced}{q}", 1);
            return RebuildOpenTag(m.Groups["tag"].Value, newAttrs, IsSelfClose(m));
        });

        content = TemplateVarOpenRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            var orig = attrs;
            var changed = false;

            var nameMatch = NameAttrRx.Match(attrs);
            if (nameMatch.Success)
            {
                var val = nameMatch.Groups["val"].Value;
                var camelized = ToCamel(val);
                if (camelized != val)
                {
                    var q = nameMatch.Groups["q"].Value;
                    attrs = NameAttrRx.Replace(attrs, $" Name={q}{camelized}{q}", 1);
                    camel++;
                    changed = true;
                }
            }

            if (LoadAttrRx.IsMatch(attrs))
            {
                attrs = LoadAttrRx.Replace(attrs, "");
                load++;
                changed = true;
            }

            if (!changed) return m.Value;
            return RebuildOpenTag(m.Groups["tag"].Value, attrs, IsSelfClose(m));
        });

        if (star > 0)
            fixes.Add(new AppliedFix { RuleName = StarVarRuleName, Count = star });
        if (camel > 0)
            fixes.Add(new AppliedFix { RuleName = TemplateVarCaseRuleName, Count = camel });
        if (load > 0)
            fixes.Add(new AppliedFix { RuleName = TemplateVarLoadRuleName, Count = load });

        return (content, fixes);
    }

    /// <summary>PascalCase / ALLCAPS token → camelCase (first letter lower).</summary>
    public static string ToCamel(string name)
    {
        if (string.IsNullOrEmpty(name)) return name;
        if (char.IsLower(name[0])) return name;
        if (name.Length == 1) return name.ToLowerInvariant();
        return char.ToLowerInvariant(name[0]) + name[1..];
    }

    static bool IsSelfClose(Match m) =>
        m.Groups["slash"].Success && m.Groups["slash"].Value.IndexOf('/') >= 0;

    static string RebuildOpenTag(string tag, string attrs, bool selfClose) =>
        selfClose ? $"<{tag}{attrs} />" : $"<{tag}{attrs}>";
}
