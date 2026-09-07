using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Auto-fix: <c>override bool FinalRender(RenderEvent E, bool Alt)</c> →
/// <c>FinalRender(RenderEvent E)</c> when the bool parameter is unused in the body.
/// PreferHarmonyPatch.FinalRender advice still applies for extension policy.
/// Never adds <c>[Obsolete]</c>.
/// </summary>
public static class FinalRenderOverrideFixer
{
    public const string FixRuleName =
        "FinalRender(RenderEvent, bool) → FinalRender(RenderEvent) [unused Alt]";

    static readonly Regex Signature = new(
        @"\b(?<sig>(?:public|protected|internal|private)\s+(?:(?:new|sealed|unsafe|async)\s+)*override\s+bool\s+FinalRender\s*\(\s*RenderEvent\s+(?<ev>[A-Za-z_]\w*)\s*,\s*bool\s+(?<alt>[A-Za-z_]\w*)\s*\))",
        RegexOptions.Compiled);

    static readonly Regex SignatureBare = new(
        @"(?<=^|[\{\};])\s*(?<sig>override\s+bool\s+FinalRender\s*\(\s*RenderEvent\s+(?<ev>[A-Za-z_]\w*)\s*,\s*bool\s+(?<alt>[A-Za-z_]\w*)\s*\))",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) || !content.Contains("FinalRender", StringComparison.Ordinal))
            return (content, 0);

        var sites = new List<(int SigStart, int SigEnd, string Ev, string Alt, string SigText)>();
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

            var braceOpen = FindMethodBodyOpen(working, site.SigEnd);
            if (braceOpen < 0) continue;
            if (!TryFindMatchingBrace(working, braceOpen, out var braceClose))
                continue;

            var body = working.Substring(braceOpen + 1, braceClose - braceOpen - 1);
            // If Alt/bAlt is referenced as an identifier, leave for manual
            if (Regex.IsMatch(body, $@"\b{Regex.Escape(site.Alt)}\b"))
                continue;

            var newSig = Regex.Replace(
                site.SigText,
                @"\bFinalRender\s*\(\s*RenderEvent\s+" + Regex.Escape(site.Ev) +
                @"\s*,\s*bool\s+" + Regex.Escape(site.Alt) + @"\s*\)",
                $"FinalRender(RenderEvent {site.Ev})");

            var replacement = newSig + working.Substring(site.SigEnd, braceOpen - site.SigEnd) +
                              "{" + body + "}";
            working = working[..site.SigStart] + replacement + working[(braceClose + 1)..];
            edits++;
        }

        return (working, edits);
    }

    static void Collect(
        string content,
        Regex rx,
        List<(int SigStart, int SigEnd, string Ev, string Alt, string SigText)> sites)
    {
        foreach (Match m in rx.Matches(content))
        {
            var start = m.Groups["sig"].Index;
            if (sites.Any(s => s.SigStart == start))
                continue;
            sites.Add((
                start,
                m.Groups["sig"].Index + m.Groups["sig"].Length,
                m.Groups["ev"].Value,
                m.Groups["alt"].Value,
                m.Groups["sig"].Value));
        }
    }

    static int FindMethodBodyOpen(string content, int afterSig)
    {
        var i = afterSig;
        while (i < content.Length)
        {
            var c = content[i];
            if (char.IsWhiteSpace(c)) { i++; continue; }
            if (c == '{') return i;
            if (c == '=' && i + 1 < content.Length && content[i + 1] == '>')
                return -1;
            if (c == ';') return -1;
            return -1;
        }
        return -1;
    }

    static bool TryFindMatchingBrace(string content, int open, out int close)
    {
        close = -1;
        var depth = 0;
        for (var i = open; i < content.Length; i++)
        {
            var c = content[i];
            if (c is '"' or '\'')
            {
                i = SkipStringLite(content, i);
                continue;
            }
            if (c == '/' && i + 1 < content.Length)
            {
                if (content[i + 1] == '/')
                {
                    while (i < content.Length && content[i] != '\n') i++;
                    continue;
                }
                if (content[i + 1] == '*')
                {
                    i += 2;
                    while (i + 1 < content.Length && !(content[i] == '*' && content[i + 1] == '/')) i++;
                    i++;
                    continue;
                }
            }
            if (c == '{') depth++;
            else if (c == '}')
            {
                depth--;
                if (depth == 0)
                {
                    close = i;
                    return true;
                }
            }
        }
        return false;
    }

    static int SkipStringLite(string content, int i)
    {
        if (i >= content.Length) return i;
        var q = content[i++];
        if (q is not ('"' or '\'')) return i - 1;
        while (i < content.Length)
        {
            if (content[i] == '\\') { i += 2; continue; }
            if (content[i] == q) return i;
            i++;
        }
        return content.Length - 1;
    }
}
