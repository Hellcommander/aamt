using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Confidence-gated obsolete <c>Extensions.Things</c> / extension <c>.Things(</c>
/// → GameText <c>=number.things:what:whatPlural=</c> via <c>_T(...).SetArgument(...).ToString()</c>.
/// Auto only when <c>what</c> (and optional plural) are string literals (or plural null).
/// Ambiguous / non-literal noun args stay for dump + <see cref="ManualAdvice"/>.
/// </summary>
public static class ThingsFixer
{
    public const string FixRuleName =
        "Things(num, what[, plural]) → Strings._T(=number.things:…=).SetArgument (literal what)";

    // Extensions.Things(  OR  <receiver>.Things(
    static readonly Regex CallSite = new(
        @"(?:(?<static>Extensions)\.|\.)Things\s*(?<paren>\()",
        RegexOptions.Compiled);

    /// <summary>
    /// High-confidence rewrites only. Leaves non-literal <c>what</c> / unsafe tokens alone.
    /// </summary>
    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var matches = CallSite.Matches(content);
        if (matches.Count == 0)
            return (content, 0);

        var sb = new StringBuilder(content.Length + 128);
        var last = 0;
        var edits = 0;

        foreach (Match m in matches)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index) ||
                HitFilter.IsInsideGameTextToken(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;

            string numberExpr;
            string whatExpr;
            string? pluralExpr;
            int replaceStart;

            if (m.Groups["static"].Success)
            {
                // Extensions.Things(num, what[, plural])
                if (args.Count is < 2 or > 3)
                    continue;
                numberExpr = args[0].Expression.Trim();
                whatExpr = args[1].Expression.Trim();
                pluralExpr = args.Count == 3 ? args[2].Expression.Trim() : null;
                replaceStart = m.Index;
            }
            else
            {
                // recv.Things(what[, plural])
                if (args.Count is < 1 or > 2)
                    continue;
                if (!TryFindReceiver(content, m.Index, out var recvStart, out numberExpr))
                    continue;
                whatExpr = args[0].Expression.Trim();
                pluralExpr = args.Count == 2 ? args[1].Expression.Trim() : null;
                replaceStart = recvStart;
            }

            if (string.IsNullOrEmpty(numberExpr))
                continue;
            if (!TryGetStringLiteralContent(whatExpr, out var whatLit))
                continue;
            if (!IsSafeThingsTokenPart(whatLit))
                continue;

            string? pluralLit = null;
            if (pluralExpr != null)
            {
                if (IsNullLiteral(pluralExpr))
                    pluralLit = null;
                else if (TryGetStringLiteralContent(pluralExpr, out var p) && IsSafeThingsTokenPart(p))
                    pluralLit = p;
                else
                    continue; // non-literal / unsafe plural — advice only
            }

            var token = pluralLit == null
                ? $"=number.things:{whatLit}="
                : $"=number.things:{whatLit}:{pluralLit}=";

            // Stable-ish localization key from the noun; migrator-generated, not author prose.
            // FQN Strings._T — bare _T requires IComponent / using static and caused CS0103
            // outside those contexts (Sacred Well Hole world-builder timing log).
            var key = EscapeCSharpString($"Things:{whatLit}");
            var tokenEsc = EscapeCSharpString(token);
            var numberArg = WrapNumberArgIfFloating(numberExpr);
            var replacement =
                $"XRL.Language.Strings._T(\"{key}\", \"{tokenEsc}\").SetArgument(\"number\", {numberArg}).ToString()";

            sb.Append(content, last, replaceStart - last);
            sb.Append(replacement);
            last = close + 1;
            edits++;
        }

        if (edits == 0)
            return (content, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits);
    }

    /// <summary>
    /// Walk left from the <c>.</c> of <c>.Things</c> to capture a simple receiver expression
    /// (identifier / member access / call / indexer / parenthesized / numeric literal).
    /// </summary>
    internal static bool TryFindReceiver(
        string content, int thingsDotIndex, out int start, out string expression)
    {
        start = -1;
        expression = "";
        if (thingsDotIndex <= 0 || content[thingsDotIndex] != '.')
            return false;

        var i = thingsDotIndex - 1;
        while (i >= 0 && char.IsWhiteSpace(content[i]))
            i--;
        if (i < 0)
            return false;

        var end = i + 1; // exclusive end of receiver (at the '.')

        if (!TryScanPrimaryBackward(content, ref i))
            return false;

        // Optional member/call chain: .Ident(...) / .Ident[...] / .Ident
        while (true)
        {
            var save = i;
            while (i >= 0 && char.IsWhiteSpace(content[i]))
                i--;
            if (i < 0 || content[i] != '.')
            {
                i = save;
                break;
            }

            i--; // before '.'
            while (i >= 0 && char.IsWhiteSpace(content[i]))
                i--;
            if (i < 0 || !TryScanPrimaryBackward(content, ref i))
            {
                i = save;
                break;
            }
        }

        start = i + 1;
        while (start < end && char.IsWhiteSpace(content[start]))
            start++;
        if (start >= end)
            return false;

        expression = content[start..end].Trim();
        return expression.Length > 0;
    }

    /// <summary>
    /// Scan one primary ending at <paramref name="i"/> (inclusive), moving <paramref name="i"/>
    /// to the char before the primary. Handles Ident, number, (...), [...], and Ident(...)/Ident[...]
    /// when the suffix was already consumed as nested.
    /// </summary>
    static bool TryScanPrimaryBackward(string content, ref int i)
    {
        if (i < 0)
            return false;

        // Trailing ) or ] — match pair, then optional identifier before it (method/indexer).
        if (content[i] is ')' or ']')
        {
            var close = content[i];
            var open = close == ')' ? '(' : '[';
            var depth = 1;
            i--;
            while (i >= 0 && depth > 0)
            {
                var c = content[i];
                if (c is '"' or '\'')
                {
                    // Walking backward through strings is best-effort; reject if we hit one.
                    return false;
                }
                if (c == close) depth++;
                else if (c == open) depth--;
                i--;
            }
            if (depth != 0)
                return false;

            // i is now at char before '(' / '['; optional method/indexer name
            var afterNest = i;
            while (i >= 0 && char.IsWhiteSpace(content[i]))
                i--;
            if (i >= 0 && (char.IsLetterOrDigit(content[i]) || content[i] == '_'))
            {
                while (i >= 0 && (char.IsLetterOrDigit(content[i]) || content[i] == '_'))
                    i--;
                return true;
            }

            // Bare (expr) or [expr] — keep nest only
            i = afterNest;
            return true;
        }

        // Identifier
        if (char.IsLetter(content[i]) || content[i] == '_')
        {
            while (i >= 0 && (char.IsLetterOrDigit(content[i]) || content[i] == '_'))
                i--;
            return true;
        }

        // Numeric literal (int / float / suffix)
        if (char.IsDigit(content[i]) || content[i] == '.')
        {
            while (i >= 0 && (char.IsDigit(content[i]) || content[i] is '.' or '_' or 'f' or 'F' or 'd' or 'D' or 'm' or 'M' or 'l' or 'L' or 'u' or 'U'))
                i--;
            return true;
        }

        return false;
    }

    static bool TryGetStringLiteralContent(string expr, out string content)
    {
        content = "";
        if (string.IsNullOrEmpty(expr))
            return false;
        expr = expr.Trim();
        // Only regular "..." (no $@ / $ / @) — keeps token embedding trivial.
        if (expr.Length < 2 || expr[0] != '"' || expr[^1] != '"')
            return false;
        var inner = expr[1..^1];
        // Reject escapes that would confuse GameText embedding or our quoting.
        if (inner.Contains('\\', StringComparison.Ordinal) ||
            inner.Contains('"', StringComparison.Ordinal))
            return false;
        content = inner;
        return true;
    }

    static bool IsNullLiteral(string expr)
    {
        expr = expr.Trim();
        return expr == "null" ||
               expr == "(string)null" ||
               expr == "(String)null" ||
               expr.Equals("default", StringComparison.Ordinal) ||
               expr.Equals("default(string)", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>GameText token parts must not contain <c>:</c> or <c>=</c>.</summary>
    static bool IsSafeThingsTokenPart(string part) =>
        part.Length > 0 &&
        !part.Contains(':', StringComparison.Ordinal) &&
        !part.Contains('=', StringComparison.Ordinal);

    static string EscapeCSharpString(string s) =>
        s.Replace("\\", "\\\\", StringComparison.Ordinal)
         .Replace("\"", "\\\"", StringComparison.Ordinal);

    /// <summary>
    /// NumberReplacers.Things is looked up as =Int32.things= — wrap floating receivers
    /// (<c>TotalSeconds</c>, <c>1.5</c>, etc.) as <c>(int)System.Math.Round(...)</c>
    /// (not long — GameText keys by runtime type and =Int64.things= does not exist).
    /// </summary>
    static string WrapNumberArgIfFloating(string numberExpr)
    {
        var t = numberExpr.Trim();
        if (t.Length == 0) return numberExpr;
        if (t.Contains("TotalSeconds", StringComparison.Ordinal) ||
            t.Contains("TotalMilliseconds", StringComparison.Ordinal) ||
            t.Contains("TotalMinutes", StringComparison.Ordinal) ||
            t.Contains("TotalHours", StringComparison.Ordinal) ||
            Regex.IsMatch(t, @"\d+\.\d+") ||
            t.EndsWith("f", StringComparison.OrdinalIgnoreCase) ||
            (t.EndsWith("d", StringComparison.OrdinalIgnoreCase) &&
             t.Length > 1 && char.IsDigit(t[^2])))
        {
            return $"(int)System.Math.Round({t})";
        }
        return numberExpr;
    }
}
