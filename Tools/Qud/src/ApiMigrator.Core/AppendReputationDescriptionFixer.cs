using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Rewrites the common <c>StringBuilder sb = new(); … AppendReputationDescription(sb)</c>
/// pattern to <c>using TextBuilder sb = TextBuilder.Get();</c>.
/// Programmatic (not curated regex) — the old multi-line backref rule ReDoS-hung on any
/// empty <c>new StringBuilder()</c> / <c>new()</c> even when AppendReputation was absent.
/// </summary>
public static class AppendReputationDescriptionFixer
{
    public const string FixRuleName =
        "StringBuilder local + AppendReputationDescription → TextBuilder.Get";

    /// <summary>Max chars to look back from a call site for the matching alloc.</summary>
    const int LookbackChars = 1200;

    static readonly Regex CallSite = new(
        @"((?:[\w\.]+\.)?)AppendReputationDescription\s*\(\s*(?<arg>[A-Za-z_]\w*)\s*\)",
        RegexOptions.Compiled);

    // StringBuilder|var name = new [StringBuilder]();
    static readonly Regex Alloc = new(
        @"(?:(?:System\.Text\.)?StringBuilder|var)\s+(?<name>[A-Za-z_]\w*)\s*=\s*new\s*(?:(?:System\.Text\.)?StringBuilder)?\s*\(\s*\)\s*;",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) ||
            content.IndexOf("AppendReputationDescription", StringComparison.Ordinal) < 0)
            return (content, 0);

        var calls = CallSite.Matches(content);
        if (calls.Count == 0)
            return (content, 0);

        // Collect alloc spans to rewrite (index → length), latest match wins per span.
        var rewrites = new SortedDictionary<int, (int Length, string Name)>();

        foreach (Match call in calls)
        {
            if (HitFilter.IsInsideComment(content, call.Index) ||
                HitFilter.IsInsideStringLiteral(content, call.Index))
                continue;

            var arg = call.Groups["arg"].Value;
            var lookStart = Math.Max(0, call.Index - LookbackChars);
            var window = content.Substring(lookStart, call.Index - lookStart);

            Match? best = null;
            foreach (Match alloc in Alloc.Matches(window))
            {
                if (!string.Equals(alloc.Groups["name"].Value, arg, StringComparison.Ordinal))
                    continue;
                if (HitFilter.IsInsideComment(content, lookStart + alloc.Index) ||
                    HitFilter.IsInsideStringLiteral(content, lookStart + alloc.Index))
                    continue;
                // Prefer the alloc closest to the call.
                best = alloc;
            }

            if (best is null)
                continue;

            var absIndex = lookStart + best.Index;
            rewrites[absIndex] = (best.Length, arg);
        }

        if (rewrites.Count == 0)
            return (content, 0);

        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var edits = 0;
        foreach (var (index, pair) in rewrites)
        {
            var (length, name) = pair;
            if (index < last)
                continue;
            sb.Append(content, last, index - last);
            sb.Append("using TextBuilder ").Append(name).Append(" = TextBuilder.Get();");
            last = index + length;
            edits++;
        }

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits);
    }
}
