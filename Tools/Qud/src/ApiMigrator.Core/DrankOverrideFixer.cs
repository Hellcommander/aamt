using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Signature-only bump: obsolete <c>Drank(..., StringBuilder Message, ...)</c> override
/// → <c>Drank(..., TextBuilder Message, ...)</c>. Last resort for leftover vanilla-liquid
/// patches. Own <c>BaseLiquid</c> subclasses convert via <see cref="LiquidDrankToPartFixer"/>.
/// </summary>
public static class DrankOverrideFixer
{
    public const string FixRuleName =
        "Drank(..., StringBuilder, ...) → Drank(..., TextBuilder, ...) [signature bump]";

    // override bool Drank(… StringBuilder Name …)
    static readonly Regex Signature = new(
        @"\b(?<sig>(?:public|protected|internal|private)\s+(?:(?:new|sealed|unsafe|async)\s+)*override\s+bool\s+Drank\s*\((?<params>[^)]*)\))",
        RegexOptions.Compiled);

    static readonly Regex SignatureBare = new(
        @"(?<=^|[\{\};])\s*(?<sig>override\s+bool\s+Drank\s*\((?<params>[^)]*)\))",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex StringBuilderMessage = new(
        @"(?<pre>(?:^|,)\s*)(?:System\.Text\.)?StringBuilder\s+(?<name>[A-Za-z_]\w*)",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var sites = new List<(int SigStart, int SigEnd, string Params)>();
        Collect(content, Signature, sites);
        Collect(content, SignatureBare, sites);
        if (sites.Count == 0)
            return (content, 0);

        sites.Sort((a, b) => b.SigStart.CompareTo(a.SigStart));
        var working = content;
        var edits = 0;

        foreach (var site in sites)
        {
            if (HitFilter.IsInsideComment(working, site.SigStart) ||
                HitFilter.IsInsideStringLiteral(working, site.SigStart))
                continue;

            if (!StringBuilderMessage.IsMatch(site.Params))
                continue;

            // Must look like the liquid Drank shape (LiquidVolume + GameObject + ref bool) for confidence
            if (!site.Params.Contains("LiquidVolume", StringComparison.Ordinal) ||
                !site.Params.Contains("GameObject", StringComparison.Ordinal))
                continue;

            if (LiquidDrankToPartFixer.ShouldConvertOwnLiquidDrank(working, site.SigStart))
                continue;

            var newParams = StringBuilderMessage.Replace(site.Params, "${pre}TextBuilder ${name}");
            if (newParams == site.Params)
                continue;

            var oldSig = working.Substring(site.SigStart, site.SigEnd - site.SigStart);
            var openParen = oldSig.IndexOf('(');
            if (openParen < 0) continue;
            var newSig = oldSig[..(openParen + 1)] + newParams + ")";

            working = working[..site.SigStart] + newSig + working[site.SigEnd..];
            edits++;
        }

        return (working, edits);
    }

    static void Collect(string content, Regex rx, List<(int SigStart, int SigEnd, string Params)> sites)
    {
        foreach (Match m in rx.Matches(content))
        {
            var start = m.Groups["sig"].Index;
            var end = m.Groups["sig"].Index + m.Groups["sig"].Length;
            if (sites.Any(s => s.SigStart == start))
                continue;
            sites.Add((start, end, m.Groups["params"].Value));
        }
    }
}
