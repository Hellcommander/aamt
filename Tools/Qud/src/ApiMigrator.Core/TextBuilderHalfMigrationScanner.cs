using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Report-only: half-migrations where a <c>TextBuilder</c> is used with
/// <c>StringBuilder</c>-only Extensions (AppendSigned/AppendArmor/…) or where
/// <c>AddsRep.AppendDescription</c> still uses the obsolete 7-arg form.
/// Never auto-rewrites — wrong choice breaks UI formatting.
/// </summary>
public static class TextBuilderHalfMigrationScanner
{
    public const string SbOnlyMember = "CS1929.TextBuilderStringBuilderOnly";
    public const string AddsRepMember = "AddsRep.AppendDescription.ObsoleteArity";
    public const string DefaultDisplayOrderMember = "InventoryAction.DefaultDisplayOrder";

    static readonly Regex SbOnlyAppend = new(
        @"\.(?<m>AppendSigned|AppendArmor|AppendPV|AppendDamage|AppendAttribute)\s*\(",
        RegexOptions.Compiled);

    static readonly Regex AddsRepObsolete = new(
        @"\.AppendDescription\s*\(\s*(?<args>[^;]{0,400})\)",
        RegexOptions.Compiled);

    static readonly Regex DefaultDisplayOrder = new(
        @"\bDefaultDisplayOrder\b",
        RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content))
            return hits;

        var seen = new HashSet<(int Line, string Member)>();

        foreach (Match m in SbOnlyAppend.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            // Only flag when the receiver is typed/assigned as TextBuilder (avoid SB locals
            // in files that also mention TextBuilder elsewhere).
            var lineText = GetLineText(content, m.Index);
            var recvMatch = Regex.Match(lineText, @"\b(?<recv>[A-Za-z_]\w*)\s*\.\s*" + m.Groups["m"].Value);
            if (!recvMatch.Success)
                continue;
            var recv = recvMatch.Groups["recv"].Value;
            if (!ReceiverLooksLikeTextBuilder(content, recv))
                continue;

            var line = GetLineNumber(content, m.Index);
            var member = SbOnlyMember + "." + m.Groups["m"].Value;
            if (!seen.Add((line, member)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = member,
                Message =
                    $"CS1929 risk — Extensions.{m.Groups["m"].Value} is StringBuilder-only; TextBuilder does not accept it",
                Advice = ManualAdvice.TextBuilderHalfMigrationAdvice(m.Groups["m"].Value),
                NeedsManual = true,
                Text = lineText.Trim(),
            });
        }

        foreach (Match m in AddsRepObsolete.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            // Obsolete 7-arg shape has Prefix/Postfix strings; current overload is (TB, Value, Faction, SignedRules)
            var args = m.Groups["args"].Value;
            var commaCount = CountTopLevelCommas(args);
            if (commaCount < 4)
                continue;

            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, AddsRepMember)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = AddsRepMember,
                Message =
                    "AddsRep.AppendDescription obsolete arity — use AppendDescription(TextBuilder, Value, Faction, SignedRules) or =addsRep#value#faction=",
                Advice = ManualAdvice.AddsRepAppendDescriptionAdvice(),
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        foreach (Match m in DefaultDisplayOrder.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, DefaultDisplayOrderMember)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = DefaultDisplayOrderMember,
                Message = "CS0117 — InventoryAction.DefaultDisplayOrder removed; use Priority (sort) or Default (default-action flag)",
                Advice = ManualAdvice.InventoryActionDefaultDisplayOrderAdvice(),
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        hits.Sort((a, b) => a.Line.CompareTo(b.Line));
        return hits;
    }

    static bool ReceiverLooksLikeTextBuilder(string content, string receiver)
    {
        if (string.IsNullOrEmpty(receiver))
            return false;
        // Typed local/param/field or TextBuilder.Get assignment
        var rx = new Regex(
            $@"\b(?:using\s+)?TextBuilder\s+{Regex.Escape(receiver)}\b|" +
            $@"\b{Regex.Escape(receiver)}\s*=\s*TextBuilder\.Get\b",
            RegexOptions.Compiled);
        return rx.IsMatch(content);
    }

    static int CountTopLevelCommas(string args)
    {
        var depth = 0;
        var count = 0;
        for (var i = 0; i < args.Length; i++)
        {
            var c = args[i];
            if (c is '"' or '\'')
            {
                var q = c;
                i++;
                while (i < args.Length)
                {
                    if (args[i] == '\\') { i += 2; continue; }
                    if (args[i] == q) break;
                    i++;
                }
                continue;
            }
            if (c is '(' or '[' or '{') depth++;
            else if (c is ')' or ']' or '}') depth = Math.Max(0, depth - 1);
            else if (c == ',' && depth == 0) count++;
        }
        return count;
    }

    static int GetLineNumber(string text, int index)
    {
        var count = 1;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            if (text[i] == '\n') count++;
        }
        return count;
    }

    static string GetLineText(string text, int index)
    {
        var start = index <= 0 ? -1 : text.LastIndexOf('\n', index - 1);
        var end = text.IndexOf('\n', index);
        if (end < 0) end = text.Length;
        var s = start + 1;
        return s <= end && s >= 0 && s <= text.Length ? text.Substring(s, Math.Max(end - s, 0)) : "";
    }
}
