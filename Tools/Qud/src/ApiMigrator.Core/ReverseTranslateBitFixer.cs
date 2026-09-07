using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Confidence-gated <c>BitType.ReverseTranslateBit</c> / <c>ReverseCharTranslateBit</c>
/// → <c>FetchBitByCode(...)</c>. Auto only when usage clearly wants BitID vs DisplayColor.
/// Ambiguous sites stay for dump + <see cref="ManualAdvice"/>.
/// </summary>
/// <remarks>
/// Obsolete message says <c>.ID</c>; the live field is <c>BitID</c> (char). String contexts
/// use <c>.BitID.ToString()</c>. Historical ReverseTranslateBit returned the BitID string
/// (not data.xml DisplayColor).
/// </remarks>
public static class ReverseTranslateBitFixer
{
    public const string FixRuleNameId =
        "BitType.ReverseTranslateBit → FetchBitByCode(...).BitID (string ID context)";

    public const string FixRuleNameColor =
        "BitType.ReverseTranslateBit → FetchBitByCode(...).DisplayColor (color context)";

    public const string FixRuleNameChar =
        "BitType.ReverseCharTranslateBit → FetchBitByCode(...).BitID";

    static readonly Regex CallSite = new(
        @"\bBitType\.(?<name>ReverseTranslateBit|ReverseCharTranslateBit)\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex ColorCue = new(
        @"ColorString|DisplayColor|TileColor|DetailColor|ColorText|\{\{|Color\s*[=:]|color\s*[=:]",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    static readonly Regex IdCue = new(
        @"BitCost|TranslateBitString|rawBits|bitString|BitString|\bBitID\b|\+\s*=|\=\=\s*""\?""|\!\=\s*""\?""|string\s+\w+\s*=",
        RegexOptions.Compiled);

    public static (string Content, int IdFixes, int ColorFixes, int CharFixes) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0, 0, 0);

        var matches = CallSite.Matches(content);
        if (matches.Count == 0)
            return (content, 0, 0, 0);

        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var idFixes = 0;
        var colorFixes = 0;
        var charFixes = 0;

        foreach (Match m in matches)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count != 1)
                continue;

            var argExpr = args[0].Expression.Trim();
            if (string.IsNullOrEmpty(argExpr))
                continue;

            var name = m.Groups["name"].Value;
            string? replacement = null;

            if (name == "ReverseCharTranslateBit")
            {
                // Historical return was BitID char; DisplayColor is string — always BitID.
                replacement = $"(BitType.FetchBitByCode({argExpr})?.BitID ?? '?')";
                charFixes++;
            }
            else
            {
                var stmt = GetStatementSlice(content, m.Index, close);
                var wantsColor = ColorCue.IsMatch(stmt);
                var wantsId = IdCue.IsMatch(stmt);

                if (wantsColor && !wantsId)
                {
                    replacement = $"(BitType.FetchBitByCode({argExpr})?.DisplayColor ?? \"?\")";
                    colorFixes++;
                }
                else if (wantsId && !wantsColor)
                {
                    replacement = $"(BitType.FetchBitByCode({argExpr})?.BitID.ToString() ?? \"?\")";
                    idFixes++;
                }
                else if (wantsId && wantsColor)
                {
                    // Conflicting cues — leave for advice
                    continue;
                }
                else
                {
                    // No clear cue — leave for advice
                    continue;
                }
            }

            sb.Append(content, last, m.Index - last);
            sb.Append(replacement);
            last = close + 1;
        }

        if (idFixes + colorFixes + charFixes == 0)
            return (content, 0, 0, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), idFixes, colorFixes, charFixes);
    }

    /// <summary>Line containing the call — enough for local cues without cross-method bleed.</summary>
    static string GetStatementSlice(string content, int callStart, int closeParen)
    {
        var lineStart = callStart <= 0 ? 0 : content.LastIndexOf('\n', callStart - 1) + 1;
        var lineEnd = content.IndexOf('\n', closeParen);
        if (lineEnd < 0) lineEnd = content.Length;
        return content[lineStart..lineEnd];
    }
}
