using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Autofixes Mutations.xml XmlDataHelper MODWARNs confirmed against
/// <c>XRL.MutationFactory</c> / <c>MutationEntry</c> / <c>IPartEntry</c> (Managed):
/// <list type="bullet">
/// <item><c>Load=</c> on <c>mutations</c>/<c>category</c>/<c>mutation</c> — unused (merge is same-Name redeclare).</item>
/// <item><c>Code=</c> on <c>mutation</c> — unused (removed legacy char code).</item>
/// <item><c>Description=</c> attr on <c>mutation</c> → child <c>&lt;description&gt;&lt;p&gt;…&lt;/p&gt;&lt;/description&gt;</c>.</item>
/// <item><c>ExludeFromPool</c> typo → <c>ExcludeFromPool</c> (root / category / mutation).</item>
/// </list>
/// </summary>
public static class MutationsXmlFixer
{
    public const string LoadStripRuleName =
        "Mutations.xml Load= strip (unused on mutations/category/mutation)";

    public const string CodeStripRuleName =
        "Mutations.xml mutation Code= strip (unused)";

    public const string DescriptionAttrRuleName =
        "Mutations.xml mutation Description= → <description><p>…</p></description>";

    public const string ExcludeFromPoolTypoRuleName =
        "Mutations.xml ExludeFromPool → ExcludeFromPool";

    // Attrs may contain '/' inside quotes; never use [^>/]*.
    const string AttrsChunk = @"(?<attrs>(?:[^>""'/]|""[^""]*""|'[^']*')*)";

    static readonly Regex MutationsRootRx = new(
        @"<\s*mutations\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex MutationsOpenRx = new(
        @"<(?<tag>mutations)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex CategoryOpenRx = new(
        @"<(?<tag>category)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex MutationOpenRx = new(
        @"<(?<tag>mutation)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex LoadAttrRx = new(
        @"\s+Load\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex CodeAttrRx = new(
        @"\s+Code\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DescriptionAttrRx = new(
        @"\s+Description\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ExcludeTypoRx = new(
        @"\bExludeFromPool\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !MutationsRootRx.IsMatch(content))
            return (content, fixes);

        var load = 0;
        var code = 0;
        var desc = 0;
        var typo = 0;

        content = RewriteOpens(content, MutationsOpenRx, attrs =>
        {
            var changed = false;
            if (Strip(ref attrs, LoadAttrRx)) { load++; changed = true; }
            if (FixTypo(ref attrs)) { typo++; changed = true; }
            return changed ? attrs : null;
        });

        content = RewriteOpens(content, CategoryOpenRx, attrs =>
        {
            var changed = false;
            if (Strip(ref attrs, LoadAttrRx)) { load++; changed = true; }
            if (FixTypo(ref attrs)) { typo++; changed = true; }
            return changed ? attrs : null;
        });

        // Mutation opens: may insert description child — use match rebuild
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var anyMut = false;
        foreach (Match m in MutationOpenRx.Matches(content))
        {
            var attrs = m.Groups["attrs"].Value;
            var selfClose = m.Groups["slash"].Success && m.Groups["slash"].Value.IndexOf('/') >= 0;
            var changed = false;
            string? descText = null;

            if (Strip(ref attrs, LoadAttrRx)) { load++; changed = true; }
            if (Strip(ref attrs, CodeAttrRx)) { code++; changed = true; }
            if (FixTypo(ref attrs)) { typo++; changed = true; }

            var dm = DescriptionAttrRx.Match(attrs);
            if (dm.Success)
            {
                descText = UnescapeXmlAttr(dm.Groups["val"].Value);
                attrs = DescriptionAttrRx.Replace(attrs, "", 1);
                desc++;
                changed = true;
            }

            if (!changed) continue;

            anyMut = true;
            sb.Append(content, last, m.Index - last);
            if (descText != null)
            {
                // Insert description child. Self-closing → expand fully; open tag → keep
                // existing </mutation> closer.
                sb.Append("<mutation").Append(attrs).Append('>')
                    .Append("\n      <description>\n        <p>")
                    .Append(EscapeXmlText(descText))
                    .Append("</p>\n      </description>");
                if (selfClose)
                    sb.Append("\n    </mutation>");
            }
            else
            {
                sb.Append(RebuildOpenTag("mutation", attrs, selfClose));
            }
            last = m.Index + m.Length;
        }

        if (anyMut)
        {
            sb.Append(content, last, content.Length - last);
            content = sb.ToString();
        }

        if (load > 0)
            fixes.Add(new AppliedFix { RuleName = LoadStripRuleName, Count = load });
        if (code > 0)
            fixes.Add(new AppliedFix { RuleName = CodeStripRuleName, Count = code });
        if (desc > 0)
            fixes.Add(new AppliedFix { RuleName = DescriptionAttrRuleName, Count = desc });
        if (typo > 0)
            fixes.Add(new AppliedFix { RuleName = ExcludeFromPoolTypoRuleName, Count = typo });

        return (content, fixes);
    }

    static string RewriteOpens(string content, Regex openRx, Func<string, string?> transformAttrs)
    {
        return openRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            var next = transformAttrs(attrs);
            if (next == null) return m.Value;
            var selfClose = m.Groups["slash"].Success && m.Groups["slash"].Value.IndexOf('/') >= 0;
            return RebuildOpenTag(m.Groups["tag"].Value, next, selfClose);
        });
    }

    static bool Strip(ref string attrs, Regex attrRx)
    {
        if (!attrRx.IsMatch(attrs)) return false;
        attrs = attrRx.Replace(attrs, "");
        return true;
    }

    static bool FixTypo(ref string attrs)
    {
        if (!ExcludeTypoRx.IsMatch(attrs)) return false;
        attrs = ExcludeTypoRx.Replace(attrs, "ExcludeFromPool=");
        return true;
    }

    static string RebuildOpenTag(string tag, string attrs, bool selfClose) =>
        selfClose ? $"<{tag}{attrs} />" : $"<{tag}{attrs}>";

    static string EscapeXmlText(string value) =>
        value.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

    static string UnescapeXmlAttr(string value) =>
        value.Replace("&quot;", "\"").Replace("&lt;", "<").Replace("&gt;", ">").Replace("&amp;", "&");
}
