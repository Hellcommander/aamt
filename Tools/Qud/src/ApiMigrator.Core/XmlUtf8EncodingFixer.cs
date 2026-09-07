using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Stamps or upgrades the game-data XML root attribute <c>Encoding="utf-8"</c>.
/// Missing Encoding makes <c>XmlDataHelper</c> default to CP437 and emit ParseWarnings
/// ("not specifying Encoding, defaulting to Encoding=cp437" / "Found CP437 Characters").
/// </summary>
public static class XmlUtf8EncodingFixer
{
    public const string FixRuleName = "XML root Encoding=\"utf-8\"";

    // Matches xml decl / leading comments, then the first element open tag.
    private static readonly Regex XmlRootOpenRx = new(
        @"(?is)(?<prefix>^\s*(<\?xml[^>]*\?>\s*)?(?:<!--.*?-->\s*)*)<(?<name>[A-Za-z_][\w.\-]*)(?<attrs>(?:\s+[\w:.\-]+\s*=\s*(?:""[^""]*""|'[^']*'))*)\s*(?<selfclose>/?)>",
        RegexOptions.Compiled | RegexOptions.Singleline);

    /// <summary>
    /// Inserts or upgrades root <c>Encoding="utf-8"</c>. No-op when already utf-8
    /// or when no root open tag is found.
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes) Ensure(string content)
    {
        var fixes = new List<AppliedFix>();
        var (next, changed, _) = TryEnsure(content);
        if (changed)
        {
            fixes.Add(new AppliedFix { RuleName = FixRuleName, Count = 1 });
            return (next, fixes);
        }
        return (content, fixes);
    }

    /// <summary>
    /// Same as <see cref="Ensure"/> but returns a one-line description for CP437 reports.
    /// </summary>
    public static (string Content, bool Changed, string? From) TryEnsure(string content)
    {
        if (string.IsNullOrEmpty(content)) return (content, false, null);

        var m = XmlRootOpenRx.Match(content);
        if (!m.Success) return (content, false, null);

        var attrs = m.Groups["attrs"].Value;
        if (Regex.IsMatch(attrs, @"(?i)\bEncoding\s*=\s*[""']utf-8[""']"))
            return (content, false, null);

        string newAttrs;
        string from;
        if (Regex.IsMatch(attrs, @"(?i)\bEncoding\s*="))
        {
            newAttrs = Regex.Replace(attrs, @"(?i)\bEncoding\s*=\s*(?:""[^""]*""|'[^']*')",
                " Encoding=\"utf-8\"");
            from = "Encoding=…";
        }
        else
        {
            newAttrs = " Encoding=\"utf-8\"" + attrs;
            from = "(missing)";
        }

        var newTag = $"<{m.Groups["name"].Value}{newAttrs}{m.Groups["selfclose"].Value}>";
        var rebuilt = m.Groups["prefix"].Value + newTag;
        var text2 = content[..m.Index] + rebuilt + content[(m.Index + m.Length)..];
        return (text2, true, from);
    }
}
