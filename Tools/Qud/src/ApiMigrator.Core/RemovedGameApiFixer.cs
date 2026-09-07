using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Strips <c>if (Options.Sifrah*)</c> / <c>if (Options.AnySifrah)</c> blocks (minigames are gone)
/// and remaining <c>Options.Sifrah*</c> accesses. Leftover removed-type identifiers are
/// report-only (<see cref="Scan"/>).
/// </summary>
public static class RemovedGameApiFixer
{
    public const string FixRuleName = "Options.Sifrah* / AnySifrah minigame branches removed";
    public const string HitMember = "RemovedType";
    public const string OptionHitMember = "RemovedMember.Options.Sifrah";

    static readonly Regex SifrahIf = new(
        @"\bif\s*\(\s*Options\.(?:AnySifrah|Sifrah\w+)\s*\)",
        RegexOptions.Compiled);

    static readonly Regex SifrahOption = new(
        @"\bOptions\.(?:AnySifrah|Sifrah\w+)\b",
        RegexOptions.Compiled);

    static readonly Regex FalseTernary = new(
        @"\bfalse\s*\?(?:[^?:]|\((?:[^()]|\([^()]*\))*\))*:",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);
        if (content.IndexOf("Sifrah", StringComparison.Ordinal) < 0 &&
            content.IndexOf("HackingGame", StringComparison.Ordinal) < 0 &&
            content.IndexOf("HagglingGame", StringComparison.Ordinal) < 0)
            return (content, 0);

        var working = content;
        var edits = 0;

        var ifs = SifrahIf.Matches(working).Cast<Match>().OrderByDescending(m => m.Index).ToList();
        foreach (var m in ifs)
        {
            if (HitFilter.IsInsideComment(working, m.Index) ||
                HitFilter.IsInsideStringLiteral(working, m.Index))
                continue;

            var i = CsText.SkipWsAndComments(working, m.Index + m.Length);
            if (i >= working.Length || working[i] != '{')
                continue;
            if (!CsText.TryFindMatchingBrace(working, i, out var braceClose))
                continue;

            var end = braceClose + 1;
            var after = CsText.SkipWsAndComments(working, end);
            if (after + 4 <= working.Length &&
                string.Compare(working, after, "else", 0, 4, StringComparison.Ordinal) == 0 &&
                (after + 4 == working.Length || !char.IsLetterOrDigit(working[after + 4])))
            {
                var elseKwEnd = after + 4;
                var elseBody = CsText.SkipWsAndComments(working, elseKwEnd);
                if (elseBody < working.Length && working[elseBody] == '{')
                {
                    if (!CsText.TryFindMatchingBrace(working, elseBody, out var elseClose))
                        continue;
                    var inner = working[(elseBody + 1)..elseClose];
                    working = working[..m.Index] + inner.Trim() + working[(elseClose + 1)..];
                    edits++;
                    continue;
                }
                // else-if / statement else: too ambiguous
                continue;
            }

            working = working[..m.Index] + working[end..];
            edits++;
        }

        var optionEdits = 0;
        var optionMatches = SifrahOption.Matches(working).Cast<Match>()
            .Where(m => !HitFilter.IsInsideComment(working, m.Index) &&
                        !HitFilter.IsInsideStringLiteral(working, m.Index))
            .OrderByDescending(m => m.Index)
            .ToList();
        foreach (var m in optionMatches)
        {
            working = working[..m.Index] + "false" + working[(m.Index + m.Length)..];
            optionEdits++;
            working = TryUnwrapTernaryAt(working, m.Index, ref edits);
        }
        edits += optionEdits;

        return (working, edits);
    }

    /// <summary>
    /// Unwrap only a <c>false ? … : …</c> whose <c>false</c> starts at <paramref name="falseIndex"/>
    /// (the token we just substituted for <c>Options.Sifrah*</c>). Other dead ternaries stay put.
    /// </summary>
    static string TryUnwrapTernaryAt(string working, int falseIndex, ref int edits)
    {
        var m = FalseTernary.Match(working, falseIndex);
        if (!m.Success || m.Index != falseIndex)
            return working;

        var colon = m.Index + m.Length - 1;
        var falseStart = CsText.SkipWsAndComments(working, colon + 1);
        var falseEnd = ScanExpressionEnd(working, falseStart);
        if (falseEnd <= falseStart) return working;
        var falseExpr = working[falseStart..falseEnd].Trim();
        edits++;
        return working[..m.Index] + falseExpr + working[falseEnd..];
    }

    static int ScanExpressionEnd(string s, int start)
    {
        var depthParen = 0;
        var depthBrace = 0;
        for (var i = start; i < s.Length; i++)
        {
            var c = s[i];
            if (c is '"' or '\'')
            {
                i = CsText.SkipStringLite(s, i);
                continue;
            }
            if (c == '(') depthParen++;
            else if (c == ')')
            {
                if (depthParen == 0) return i;
                depthParen--;
            }
            else if (c == '{') depthBrace++;
            else if (c == '}')
            {
                if (depthBrace == 0) return i;
                depthBrace--;
            }
            else if (depthParen == 0 && depthBrace == 0 && (c == ';' || c == ',' || c == '}' ))
                return i;
        }
        return s.Length;
    }

    public static IEnumerable<RemainingHit> Scan(string content)
    {
        if (string.IsNullOrEmpty(content))
            yield break;

        RemovedGameApiCatalog.Load();
        var file = RemovedGameApiCatalog.Load();
        var seen = new HashSet<(int Line, string Member)>();

        foreach (var type in file.Types)
        {
            if (string.IsNullOrWhiteSpace(type.Name))
                continue;
            var rx = new Regex(@"\b" + Regex.Escape(type.Name) + @"\b", RegexOptions.Compiled);
            foreach (Match m in rx.Matches(content))
            {
                if (HitFilter.IsInsideComment(content, m.Index) ||
                    HitFilter.IsInsideStringLiteral(content, m.Index))
                    continue;
                // TypeByName("SifrahGame") / comments already skipped; skip catalog-only string leftovers in AccessTools
                var line = CsText.GetLineNumber(content, m.Index);
                var member = HitMember + "." + type.Name;
                if (!seen.Add((line, member))) continue;
                var text = CsText.GetLineText(content, m.Index).Trim();
                if (text.Contains("TypeByName", StringComparison.Ordinal) ||
                    text.Contains("GetType(\"", StringComparison.Ordinal))
                    continue;
                yield return new RemainingHit
                {
                    Line = line,
                    Member = member,
                    Message = "Removed game type (minigame / deleted API) — does not compile",
                    NeedsManual = true,
                    Text = text,
                    Advice = ManualAdvice.RemovedGameTypeAdvice(type.Name, type.Kind),
                };
            }
        }

        foreach (Match m in SifrahOption.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var line = CsText.GetLineNumber(content, m.Index);
            if (!seen.Add((line, OptionHitMember))) continue;
            yield return new RemainingHit
            {
                Line = line,
                Member = OptionHitMember,
                Message = "Options.Sifrah* / AnySifrah was removed with minigames",
                NeedsManual = true,
                Text = CsText.GetLineText(content, m.Index).Trim(),
                Advice = ManualAdvice.RemovedSifrahOptionAdvice(),
            };
        }
    }
}
