using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Safe Worlds.xml autofixes. Only mechanically unambiguous edits —
/// currently: strip unused <c>DisableForcedConnections</c> from <c>&lt;cell&gt;</c>
/// opening tags (attribute is valid on <c>&lt;zone&gt;</c> only). Never deletes
/// <c>builder</c> nodes; never invents zone <c>Load=Merge|Replace</c>.
/// </summary>
public static class WorldsXmlFixer
{
    public const string CellDisableForcedRuleName =
        "Worlds.xml cell DisableForcedConnections → remove (zone-only attr)";

    static readonly Regex WorldsRootRx = new(
        @"<\s*worlds\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Opening <cell …> only (not </cell>). Attrs may span lines; DisableForcedConnections
    // is removed in-place so spacing / other attrs stay intact.
    static readonly Regex CellOpenRx = new(
        @"<\s*cell\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex DisableForcedAttrRx = new(
        @"\s+DisableForcedConnections\s*=\s*(?<q>['""])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>
    /// Removes <c>DisableForcedConnections="…"</c> from <c>&lt;cell&gt;</c> tags in Worlds.xml.
    /// No-op for non-worlds files or when the attribute is absent.
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !WorldsRootRx.IsMatch(content))
            return (content, fixes);

        if (content.IndexOf("DisableForcedConnections", StringComparison.OrdinalIgnoreCase) < 0)
            return (content, fixes);

        var count = 0;
        var next = CellOpenRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            if (!DisableForcedAttrRx.IsMatch(attrs))
                return m.Value;

            var newAttrs = DisableForcedAttrRx.Replace(attrs, "");
            count++;
            return "<cell" + newAttrs + ">";
        });

        if (count > 0)
        {
            fixes.Add(new AppliedFix { RuleName = CellDisableForcedRuleName, Count = count });
            return (next, fixes);
        }

        return (content, fixes);
    }
}
