using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Confidence-gated: instance <c>recv.Capitalize()</c> / <c>recv.Capitalize(bool)</c>
/// → <c>Translator.InitUpper(recv)</c>. Chained receivers with balanced simple shapes only.
/// Leaves <c>CapitalizeExceptFormatting</c> to curated regex.
/// </summary>
public static class CapitalizeFixer
{
    public const string FixRuleName = "recv.Capitalize() → Translator.InitUpper(recv)";

    // Simple identifier or Member.Access chain ending in .Capitalize( [optional bool] )
    // Rejects calls that already look like Translator / Extensions.Capitalize (handled elsewhere).
    static readonly Regex InstanceCapitalize = new(
        @"(?<!\.)\b(?<recv>[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)\s*\.\s*Capitalize\s*\(\s*(?<arg>true|false)?\s*\)",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) || !content.Contains("Capitalize", StringComparison.Ordinal))
            return (content, 0);

        var edits = 0;
        var working = InstanceCapitalize.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;

            var recv = m.Groups["recv"].Value.Replace(" ", "");
            // Skip already-qualified static forms and false friends
            if (recv is "Extensions" or "Translator" or "ColorUtility" or "Grammar")
                return m.Value;
            if (recv.EndsWith("CapitalizeExceptFormatting", StringComparison.Ordinal))
                return m.Value;

            // Skip if receiver itself is a call chain with () — our regex doesn't allow that
            edits++;
            // InitUpper ignores the obsolete Capitalize(bool) culture flag; InitUpperInvariant by hand if needed
            return "Translator.InitUpper(" + recv + ")";
        });

        return (working, edits);
    }
}
