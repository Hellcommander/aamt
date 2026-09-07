using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// <c>CachedDoubleSemicolonExpansion()</c> now returns <c>IReadOnlyList&lt;string&gt;</c>
/// (CS0266 if assigned to <c>List&lt;string&gt;</c>).
/// </summary>
public static class CachedDoubleSemicolonExpansionFixer
{
    public const string FixRuleName =
        "List<string> x = …CachedDoubleSemicolonExpansion() → IReadOnlyList<string>";

    static readonly Regex ListAssign = new(
        @"\bList\s*<\s*string\s*>\s+(?<id>[A-Za-z_]\w*)\s*=\s*(?<rhs>[^;]*CachedDoubleSemicolonExpansion\s*\(\s*\))",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) ||
            content.IndexOf("CachedDoubleSemicolonExpansion", StringComparison.Ordinal) < 0)
            return (content, 0);

        var edits = 0;
        var working = ListAssign.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            edits++;
            return "IReadOnlyList<string> " + m.Groups["id"].Value + " = " + m.Groups["rhs"].Value;
        });
        return (working, edits);
    }
}
