using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Autofixes Subtypes.xml XmlDataHelper MODWARNs confirmed against
/// <c>XRL.SubtypeFactory</c> (Managed):
/// <list type="bullet">
/// <item><c>Load=</c> unused on class/category/subtype/skills/reputations/savemodifiers (merge is same-Name/ID).</item>
/// <item><c>Code=</c> unused on subtype (legacy char code removed).</item>
/// <item><c>DisplayName=</c> on class → <c>ChargenTitle=</c> (UI field); strip if ChargenTitle already set.</item>
/// <item><c>Class=</c>/<c>Tile=</c> unused on class (those attrs belong on subtype/genotype).</item>
/// <item><c>Foreground=</c> unused on subtype; <c>ForegroundColor=</c> → <c>DetailColor=</c> when missing else strip.</item>
/// <item>Root-level orphan <c>&lt;subtype&gt;</c> (XMLNodes only accepts class) → wrap under <c>&lt;class ID="Callings"&gt;</c>
/// or expand a preceding empty/self-closing class.</item>
/// </list>
/// </summary>
public static class SubtypesXmlFixer
{
    public const string LoadStripRuleName =
        "Subtypes.xml Load= strip (unused on class/category/subtype/skills/…)";

    public const string CodeStripRuleName =
        "Subtypes.xml subtype Code= strip (unused)";

    public const string ClassDisplayNameRuleName =
        "Subtypes.xml class DisplayName= → ChargenTitle=";

    public const string ClassUnusedAttrRuleName =
        "Subtypes.xml class Class=/Tile= strip (unused on class)";

    public const string ForegroundRuleName =
        "Subtypes.xml subtype Foreground=/ForegroundColor= → DetailColor or strip";

    public const string OrphanSubtypeWrapRuleName =
        "Subtypes.xml orphan root <subtype> wrap under <class>";

    // Attrs may contain '/' inside quotes; never use [^>/]*.
    const string AttrsChunk = @"(?<attrs>(?:[^>""'/]|""[^""]*""|'[^']*')*)";

    static readonly Regex SubtypesRootRx = new(
        @"<\s*subtypes\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ClassOpenRx = new(
        @"<(?<tag>class)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex CategoryOpenRx = new(
        @"<(?<tag>category)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex SubtypeOpenRx = new(
        @"<(?<tag>subtype)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex SkillsOpenRx = new(
        @"<(?<tag>skills)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ReputationsOpenRx = new(
        @"<(?<tag>reputations)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex SaveModifiersOpenRx = new(
        @"<(?<tag>savemodifiers)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex LoadAttrRx = new(
        @"\s+Load\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex CodeAttrRx = new(
        @"\s+Code\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DisplayNameAttrRx = new(
        @"\bDisplayName\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ChargenTitleAttrRx = new(
        @"\bChargenTitle\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ClassAttrOnClassRx = new(
        @"\s+Class\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex TileAttrRx = new(
        @"\s+Tile\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ForegroundAttrRx = new(
        @"\s+Foreground\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ForegroundColorAttrRx = new(
        @"\s+ForegroundColor\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DetailColorAttrRx = new(
        @"\bDetailColor\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Self-closing empty class, then one or more sibling root subtypes.
    static readonly Regex SelfCloseClassThenOrphansRx = new(
        @"(?is)<class\b" + AttrsChunk + @"\s*/\s*>\s*(?<orphans>(?:(?:\s|<!--.*?-->)*<subtype\b(?:[^>""'/]|""[^""]*""|'[^']*')*(?:\s*/\s*)?>(?:.*?</\s*subtype\s*>)?)+)",
        RegexOptions.Compiled);

    // Empty open/close class, then sibling root subtypes.
    static readonly Regex EmptyClassThenOrphansRx = new(
        @"(?is)<class\b" + AttrsChunk + @">\s*</\s*class\s*>\s*(?<orphans>(?:(?:\s|<!--.*?-->)*<subtype\b(?:[^>""'/]|""[^""]*""|'[^']*')*(?:\s*/\s*)?>(?:.*?</\s*subtype\s*>)?)+)",
        RegexOptions.Compiled);

    // Root subtypes body that starts with orphan subtype(s) and has no preceding class.
    static readonly Regex RootOrphanSubtypesRx = new(
        @"(?is)(?<open><subtypes\b" + AttrsChunk + @">)(?<pre>(?:\s|<!--.*?-->)*)(?<orphans>(?:(?:\s|<!--.*?-->)*<subtype\b(?:[^>""'/]|""[^""]*""|'[^']*')*(?:\s*/\s*)?>(?:.*?</\s*subtype\s*>)?)+)(?<post>\s*)(?<close></\s*subtypes\s*>)",
        RegexOptions.Compiled);

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !SubtypesRootRx.IsMatch(content))
            return (content, fixes);

        var load = 0;
        var code = 0;
        var displayName = 0;
        var classUnused = 0;
        var foreground = 0;
        var wrap = 0;

        // Structural wrap first so subsequent attr rewrites see nested subtypes.
        var wrapCount = 0;
        content = ExpandEmptyClassAroundOrphans(content, ref wrapCount);
        content = WrapBareRootOrphans(content, ref wrapCount);
        wrap = wrapCount;

        content = RewriteOpens(content, ClassOpenRx, attrs =>
        {
            var changed = false;
            if (Strip(ref attrs, LoadAttrRx)) { load++; changed = true; }
            if (Strip(ref attrs, ClassAttrOnClassRx)) { classUnused++; changed = true; }
            if (Strip(ref attrs, TileAttrRx)) { classUnused++; changed = true; }

            var dm = DisplayNameAttrRx.Match(attrs);
            if (dm.Success)
            {
                if (ChargenTitleAttrRx.IsMatch(attrs))
                {
                    attrs = DisplayNameAttrRx.Replace(attrs, "", 1);
                    displayName++;
                    changed = true;
                }
                else
                {
                    attrs = DisplayNameAttrRx.Replace(attrs,
                        $" ChargenTitle={dm.Groups["q"].Value}{dm.Groups["val"].Value}{dm.Groups["q"].Value}", 1);
                    // Keep spacing tidy: DisplayName was \b match without leading space capture —
                    // if we introduced " ChargenTitle" after another attr it's fine; if at start, trim.
                    attrs = Regex.Replace(attrs, @"^\s+", " ");
                    displayName++;
                    changed = true;
                }
            }

            return changed ? attrs : null;
        });

        content = RewriteOpens(content, CategoryOpenRx, attrs =>
        {
            if (!Strip(ref attrs, LoadAttrRx)) return null;
            load++;
            return attrs;
        });

        content = RewriteOpens(content, SubtypeOpenRx, attrs =>
        {
            var changed = false;
            if (Strip(ref attrs, LoadAttrRx)) { load++; changed = true; }
            if (Strip(ref attrs, CodeAttrRx)) { code++; changed = true; }

            if (FixForeground(ref attrs)) { foreground++; changed = true; }

            return changed ? attrs : null;
        });

        foreach (var rx in new[] { SkillsOpenRx, ReputationsOpenRx, SaveModifiersOpenRx })
        {
            content = RewriteOpens(content, rx, attrs =>
            {
                if (!Strip(ref attrs, LoadAttrRx)) return null;
                load++;
                return attrs;
            });
        }

        if (load > 0)
            fixes.Add(new AppliedFix { RuleName = LoadStripRuleName, Count = load });
        if (code > 0)
            fixes.Add(new AppliedFix { RuleName = CodeStripRuleName, Count = code });
        if (displayName > 0)
            fixes.Add(new AppliedFix { RuleName = ClassDisplayNameRuleName, Count = displayName });
        if (classUnused > 0)
            fixes.Add(new AppliedFix { RuleName = ClassUnusedAttrRuleName, Count = classUnused });
        if (foreground > 0)
            fixes.Add(new AppliedFix { RuleName = ForegroundRuleName, Count = foreground });
        if (wrap > 0)
            fixes.Add(new AppliedFix { RuleName = OrphanSubtypeWrapRuleName, Count = wrap });

        return (content, fixes);
    }

    static string ExpandEmptyClassAroundOrphans(string content, ref int wrap)
    {
        var n = wrap;
        content = SelfCloseClassThenOrphansRx.Replace(content, m =>
        {
            n++;
            return $"<class{m.Groups["attrs"].Value}>{m.Groups["orphans"].Value}\n</class>";
        });

        content = EmptyClassThenOrphansRx.Replace(content, m =>
        {
            n++;
            return $"<class{m.Groups["attrs"].Value}>{m.Groups["orphans"].Value}\n</class>";
        });

        wrap = n;
        return content;
    }

    static string WrapBareRootOrphans(string content, ref int wrap)
    {
        var n = wrap;
        content = RootOrphanSubtypesRx.Replace(content, m =>
        {
            // Only when the orphans are the whole body (no trailing class/category after).
            var orphans = m.Groups["orphans"].Value;
            var post = m.Groups["post"].Value;
            if (Regex.IsMatch(orphans + post, @"(?is)<\s*class\b") ||
                Regex.IsMatch(orphans + post, @"(?is)<\s*category\b"))
                return m.Value;

            n++;
            return m.Groups["open"].Value
                   + m.Groups["pre"].Value
                   + "<class ID=\"Callings\">"
                   + orphans
                   + "\n</class>"
                   + post
                   + m.Groups["close"].Value;
        });
        wrap = n;
        return content;
    }

    static bool FixForeground(ref string attrs)
    {
        var changed = false;
        string? color = null;

        var fg = ForegroundAttrRx.Match(attrs);
        if (fg.Success)
        {
            color = fg.Groups["val"].Value;
            attrs = ForegroundAttrRx.Replace(attrs, "", 1);
            changed = true;
        }

        var fgc = ForegroundColorAttrRx.Match(attrs);
        if (fgc.Success)
        {
            color ??= fgc.Groups["val"].Value;
            attrs = ForegroundColorAttrRx.Replace(attrs, "", 1);
            changed = true;
        }

        if (!changed) return false;

        if (color != null && !DetailColorAttrRx.IsMatch(attrs))
            attrs += $" DetailColor=\"{color}\"";

        return true;
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

    static string RebuildOpenTag(string tag, string attrs, bool selfClose) =>
        selfClose ? $"<{tag}{attrs} />" : $"<{tag}{attrs}>";
}
