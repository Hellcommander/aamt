using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// CS1739: <c>BaseMutation.GetDisplayName(WithAnnotations:)</c> was renamed to
/// <c>Annotations:</c> (Direct/Base/Annotations/Variant). Named-arg only — do not
/// rewrite positional <c>GetDisplayName(false)</c> (that is now <c>Direct</c>).
/// </summary>
public static class GetDisplayNameArgFixer
{
    public const string FixRuleName =
        "GetDisplayName(WithAnnotations:) → Annotations: (BaseMutation)";

    static readonly Regex Named = new(
        @"GetDisplayName\s*\(\s*WithAnnotations\s*:",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);
        if (content.IndexOf("WithAnnotations", StringComparison.Ordinal) < 0)
            return (content, 0);

        var sb = new StringBuilder(content.Length);
        var last = 0;
        var edits = 0;
        foreach (Match m in Named.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            sb.Append(content, last, m.Index - last);
            sb.Append("GetDisplayName(Annotations:");
            last = m.Index + m.Length;
            edits++;
        }

        if (edits == 0)
            return (content, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits);
    }
}
