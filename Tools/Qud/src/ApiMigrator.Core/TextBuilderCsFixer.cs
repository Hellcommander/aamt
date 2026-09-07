using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// High-confidence TextBuilder follow-ups after <c>Event.NewStringBuilder → TextBuilder.Get</c>:
/// <c>Event.FinalizeString(tb)</c> still takes StringBuilder (CS1503);
/// <c>tb.AppendSigned(n, "rules")</c> is StringBuilder-only (CS1503) — vanilla uses
/// <c>AppendModifier</c>; obsolete 7-arg <c>AddsRep.AppendDescription</c> swaps Value/Faction.
/// Locals from <c>Event.NewStringBuilder → TextBuilder.Get</c> that are still passed to
/// StringBuilder APIs (<c>AppendName</c>/<c>Substitute</c>) are reverted to <c>new StringBuilder()</c>.
/// Same-file <c>ref StringBuilder</c> parameters that receive a TextBuilder.Get local are
/// retargeted to <c>ref TextBuilder</c> (CS1503).
/// </summary>
public static class TextBuilderCsFixer
{
    public const string FinalizeRuleName = "Event.FinalizeString(TextBuilder) → ToString()";
    public const string AppendSignedRuleName = "TextBuilder.AppendSigned → AppendModifier / Append(signed)";
    public const string AddsRepRuleName = "AddsRep.AppendDescription 7-arg → (TB, Value, Faction, SignedRules)";
    public const string StringBuilderConsumerRuleName =
        "TextBuilder.Get → new StringBuilder when passed to AppendName/Substitute";
    public const string RefStringBuilderParamRuleName =
        "ref StringBuilder param → ref TextBuilder (TextBuilder.Get local)";

    static readonly Regex GetAssign = new(
        @"(?:(?<kw>using)\s+)?(?:(?<typ>(?:System\.Text\.)?StringBuilder|TextBuilder|var)\s+)?(?<id>[A-Za-z_]\w*)\s*=\s*TextBuilder\.Get\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex FinalizeCall = new(
        @"Event\.FinalizeString\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex AppendSignedCall = new(
        @"(?<recv>(?:this\.)?[A-Za-z_]\w*)\.AppendSigned\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex AddsRepCall = new(
        @"(?:AddsRep\s*\.)?AppendDescription\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex MethodCall = new(
        @"\b(?<method>[A-Za-z_]\w*)\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex MethodDef = new(
        @"(?:public|private|protected|internal|static|virtual|override|new|async|extern|sealed|partial)(?:\s+(?:public|private|protected|internal|static|virtual|override|new|async|extern|sealed|partial))*\s+[\w.<>,\[\]?]+\s+(?<name>[A-Za-z_]\w*)\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly HashSet<string> CallKeywords = new(StringComparer.Ordinal)
    {
        "if", "while", "for", "foreach", "switch", "catch", "using", "lock", "return",
        "sizeof", "typeof", "default", "new", "stackalloc", "checked", "unchecked",
        "nameof", "await", "switch",
    };

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content))
            return (content, fixes);

        var working = content;
        var n = 0;
        working = FixStringBuilderConsumers(working, ref n);
        if (n > 0)
            fixes.Add(new AppliedFix { RuleName = StringBuilderConsumerRuleName, Count = n });

        n = 0;
        working = FixRefStringBuilderParams(working, ref n);
        if (n > 0)
            fixes.Add(new AppliedFix { RuleName = RefStringBuilderParamRuleName, Count = n });

        n = 0;
        working = FixFinalizeString(working, ref n);
        if (n > 0)
            fixes.Add(new AppliedFix { RuleName = FinalizeRuleName, Count = n });

        n = 0;
        working = FixAppendSigned(working, ref n);
        if (n > 0)
            fixes.Add(new AppliedFix { RuleName = AppendSignedRuleName, Count = n });

        n = 0;
        working = FixAddsRepArity(working, ref n);
        if (n > 0)
            fixes.Add(new AppliedFix { RuleName = AddsRepRuleName, Count = n });

        if (fixes.Count == 0)
            return (content, fixes);

        var usings = new List<string> { "XRL.World.Text" };
        if (fixes.Any(f => f.RuleName == StringBuilderConsumerRuleName))
            usings.Add("System.Text");
        var (withUsing, inserted) = UsingInserter.EnsureUsings(working, usings);
        working = withUsing;
        if (inserted.Count > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "ensure using: " + string.Join(", ", inserted),
                Count = inserted.Count,
            });
        }

        return (working, fixes);
    }

    static string FixStringBuilderConsumers(string content, ref int edits)
    {
        if (content.IndexOf("TextBuilder.Get", StringComparison.Ordinal) < 0)
            return content;
        if (content.IndexOf("AppendName", StringComparison.Ordinal) < 0 &&
            content.IndexOf("Substitute", StringComparison.Ordinal) < 0)
            return content;

        var sb = new StringBuilder(content.Length);
        var last = 0;
        var local = 0;
        foreach (Match m in GetAssign.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var id = m.Groups["id"].Value;
            if (!LocalPassedToStringBuilderApi(content, id))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count > 1)
                continue;
            if (args.Count == 1)
            {
                var a = args[0].Expression.Trim();
                if (a is not "null" && !(a.Length >= 2 && a[0] == '"'))
                    continue;
            }

            sb.Append(content, last, m.Index - last);
            var kw = m.Groups["kw"].Success ? m.Groups["kw"].Value : "";
            var typ = m.Groups["typ"].Success ? m.Groups["typ"].Value : "";
            if (kw == "using" || typ is "TextBuilder")
                sb.Append("StringBuilder ").Append(id).Append(" = new StringBuilder");
            else if (!string.IsNullOrEmpty(typ))
                sb.Append(typ).Append(' ').Append(id).Append(" = new StringBuilder");
            else
                sb.Append(id).Append(" = new StringBuilder");
            sb.Append(content, open, close - open + 1);
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static bool LocalPassedToStringBuilderApi(string content, string id)
    {
        var rx = new Regex(
            $@"\b(?:AppendName|Substitute)\s*\(\s*{Regex.Escape(id)}\b",
            RegexOptions.Compiled);
        return rx.IsMatch(content);
    }

    static string FixFinalizeString(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length);
        var last = 0;
        var local = 0;
        foreach (Match m in FinalizeCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count != 1)
                continue;
            var recv = args[0].Expression.Trim();
            if (!IsIdent(recv) || !ReceiverLooksLikeTextBuilder(content, recv))
                continue;
            sb.Append(content, last, m.Index - last);
            sb.Append(recv).Append(".ToString()");
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixAppendSigned(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length);
        var last = 0;
        var local = 0;
        foreach (Match m in AppendSignedCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var recv = m.Groups["recv"].Value;
            if (!ReceiverLooksLikeTextBuilder(content, recv))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count == 0)
                continue;

            string replacement;
            if (args.Count == 1)
            {
                replacement = $"{recv}.Append({args[0].Expression.Trim()}, true)";
            }
            else if (args.Count == 2 && LooksLikeColorLiteral(args[1].Expression.Trim()))
            {
                replacement = $"{recv}.AppendModifier({args[0].Expression.Trim()}, {args[1].Expression.Trim()})";
            }
            else
                continue;

            sb.Append(content, last, m.Index - last);
            sb.Append(replacement);
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixAddsRepArity(string content, ref int edits)
    {
        if (content.IndexOf("AppendDescription", StringComparison.Ordinal) < 0)
            return content;

        var sb = new StringBuilder(content.Length);
        var last = 0;
        var local = 0;
        foreach (Match m in AddsRepCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            // Only rewrite AddsRep.AppendDescription or a call whose preceding ident is AddsRep
            var prefixStart = m.Index;
            var looksAddsRep = m.Value.StartsWith("AddsRep", StringComparison.Ordinal);
            if (!looksAddsRep)
            {
                var before = content[Math.Max(0, m.Index - 12)..m.Index];
                if (!before.Contains("AddsRep", StringComparison.Ordinal))
                    continue;
            }

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            // Obsolete: (TB, Faction, Value, Prefix, Postfix, Rules, SignedRules)
            if (args.Count < 5)
                continue;

            var store = args[0].Expression.Trim();
            var faction = args[1].Expression.Trim();
            var value = args[2].Expression.Trim();
            var signed = args.Count >= 7 ? args[6].Expression.Trim() : "false";
            if (signed is "null")
                signed = "false";

            var call = looksAddsRep
                ? $"AddsRep.AppendDescription({store}, {value}, {faction}, {signed})"
                : $"AppendDescription({store}, {value}, {faction}, {signed})";

            sb.Append(content, last, prefixStart - last);
            sb.Append(call);
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    /// <summary>
    /// After NewStringBuilder → TextBuilder.Get, same-file helpers still taking
    /// <c>ref StringBuilder</c> fail CS1503. Retarget those parameters when a caller
    /// passes <c>ref</c> a TextBuilder.Get local. Skips <c>override</c> (game virtuals).
    /// </summary>
    static string FixRefStringBuilderParams(string content, ref int edits)
    {
        if (content.IndexOf("TextBuilder.Get", StringComparison.Ordinal) < 0)
            return content;
        if (content.IndexOf("ref StringBuilder", StringComparison.Ordinal) < 0 &&
            content.IndexOf("ref System.Text.StringBuilder", StringComparison.Ordinal) < 0)
            return content;

        var tbLocals = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in GetAssign.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            tbLocals.Add(m.Groups["id"].Value);
        }
        if (tbLocals.Count == 0)
            return content;

        var indexesByMethod = new Dictionary<string, HashSet<int>>(StringComparer.Ordinal);
        foreach (Match m in MethodCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var method = m.Groups["method"].Value;
            if (CallKeywords.Contains(method))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out _))
                continue;
            for (var i = 0; i < args.Count; i++)
            {
                var e = args[i].Expression.Trim();
                if (!e.StartsWith("ref ", StringComparison.Ordinal))
                    continue;
                var id = e[4..].Trim();
                if (!tbLocals.Contains(id))
                    continue;
                if (!indexesByMethod.TryGetValue(method, out var set))
                {
                    set = new HashSet<int>();
                    indexesByMethod[method] = set;
                }
                set.Add(i);
            }
        }
        if (indexesByMethod.Count == 0)
            return content;

        var sb = new StringBuilder(content.Length);
        var last = 0;
        var local = 0;
        foreach (Match m in MethodDef.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            if (m.Value.Contains("override", StringComparison.Ordinal))
                continue;
            var name = m.Groups["name"].Value;
            if (!indexesByMethod.TryGetValue(name, out var indexes))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var parms, out var close))
                continue;

            var changed = false;
            var parts = new string[parms.Count];
            for (var i = 0; i < parms.Count; i++)
            {
                var expr = parms[i].Expression;
                if (indexes.Contains(i) && IsRefStringBuilderParam(expr))
                {
                    parts[i] = RefStringBuilderToTextBuilder(expr);
                    changed = true;
                }
                else
                {
                    parts[i] = expr;
                }
            }
            if (!changed)
                continue;

            sb.Append(content, last, open + 1 - last);
            sb.Append(string.Join(",", parts));
            last = close;
            local++;
        }
        if (local == 0)
            return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static bool IsRefStringBuilderParam(string paramExpr) =>
        Regex.IsMatch(paramExpr.Trim(), @"^ref\s+(?:System\.Text\.)?StringBuilder\b");

    static string RefStringBuilderToTextBuilder(string paramExpr) =>
        Regex.Replace(paramExpr, @"\bref\s+(?:System\.Text\.)?StringBuilder\b", "ref TextBuilder");

    static bool LooksLikeColorLiteral(string expr)
    {
        var t = expr.Trim();
        return t.Length >= 2 && t[0] == '"' && t[^1] == '"' && t.Length <= 24;
    }

    static bool IsIdent(string expr) =>
        Regex.IsMatch(expr, @"^(?:this\.)?[A-Za-z_]\w*$");

    internal static bool ReceiverLooksLikeTextBuilder(string content, string receiver)
    {
        if (string.IsNullOrEmpty(receiver))
            return false;
        var leaf = receiver.StartsWith("this.", StringComparison.Ordinal) ? receiver[5..] : receiver;
        var rx = new Regex(
            $@"\b(?:using\s+)?TextBuilder\s+{Regex.Escape(leaf)}\b|" +
            $@"\b{Regex.Escape(leaf)}\s*=\s*TextBuilder\.Get\b",
            RegexOptions.Compiled);
        return rx.IsMatch(content);
    }
}
