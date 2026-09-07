using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Detects and (when safe) fixes CS0019 method-group mistakes of the form
/// <c>.Count &gt; N</c> / <c>.Count == N</c> etc. where <c>Count</c> is the LINQ
/// extension method group rather than an <c>ICollection.Count</c> property.
/// </summary>
/// <remarks>
/// <para>
/// Auto-fixes (high confidence only):
/// </para>
/// <list type="bullet">
/// <item><c>.Where(...).Count &gt; 0</c> → <c>.Where(...).Count() &gt; 0</c> (and other LINQ chain tails)</item>
/// <item><c>IEnumerable&lt;T&gt; xs; … xs.Count &gt; 0</c> → <c>xs.Count()</c> (also IQueryable / IOrdered*)</item>
/// </list>
/// <para>
/// Never rewrites <c>list.Count</c> / <c>dict.Count</c> / <c>ToList().Count</c> property uses.
/// Ambiguous bare <c>foo.Count &gt; N</c> (untyped / <c>var</c> / collection interfaces with a
/// real <c>Count</c> property) is left alone — no auto-fix and no report spam.
/// </para>
/// <para>
/// Name collisions: if the same identifier is declared as <c>IEnumerable&lt;T&gt;</c> in one
/// method and <c>List&lt;T&gt;</c> / <c>var x = new List&lt;…&gt;</c> elsewhere in the file
/// (Broodmother <c>defects</c>), the IEnumerable-typed path is skipped for that name so
/// List property uses are not turned into illegal <c>.Count()</c> (CS1955).
/// </para>
/// <para>
/// Also flags <c>?? Enumerable.Empty&lt;(...)&gt;</c> as a possible CS0019 named-vs-unnamed
/// tuple mismatch (report only; do not auto-rename tuple elements).
/// </para>
/// </remarks>
public static class CountMethodGroupFixer
{
    /// <summary>LINQ operators that return <c>IEnumerable</c>/<c>IQueryable</c> (Count is an extension).</summary>
    static readonly HashSet<string> LinqChainMethods = new(StringComparer.Ordinal)
    {
        "Where", "Select", "SelectMany", "OfType", "Cast",
        "Concat", "Union", "Intersect", "Except", "Zip", "Join", "GroupJoin",
        "Skip", "Take", "SkipWhile", "TakeWhile", "Distinct",
        "OrderBy", "OrderByDescending", "ThenBy", "ThenByDescending",
        "GroupBy", "Reverse", "AsEnumerable", "AsQueryable", "DefaultIfEmpty",
        "Append", "Prepend",
    };

    /// <summary>Materializers whose result has a <c>Count</c>/<c>Length</c> property — do not add <c>()</c>.</summary>
    static readonly HashSet<string> Materializers = new(StringComparer.Ordinal)
    {
        "ToList", "ToArray", "ToHashSet", "ToDictionary", "ToLookup",
    };

    // .Count compared to something, but not already .Count(
    static readonly Regex CountCompare = new(
        @"\.Count(?!\s*\()(?=\s*(?:==|!=|<=|>=|<|>))",
        RegexOptions.Compiled);

    // IEnumerable<T> name  (one nesting level of generics)
    static readonly Regex EnumerableTypedName = new(
        @"\b(?<type>IEnumerable|IQueryable|IOrderedEnumerable|IOrderedQueryable)\s*(?<generic><(?:[^<>]|<[^<>]*>)*>)\s+(?<name>[A-Za-z_]\w*)\b",
        RegexOptions.Compiled);

    // Types with a real Count property — never treat as LINQ Count() via name lookup.
    static readonly Regex CollectionTypedName = new(
        @"\b(?<type>List|Dictionary|HashSet|Queue|Stack|SortedList|SortedDictionary|SortedSet|LinkedList|ConcurrentDictionary|ConcurrentBag|ConcurrentQueue|ConcurrentStack|BlockingCollection|IList|ICollection|IReadOnlyList|IReadOnlyCollection|IDictionary|IReadOnlyDictionary)\s*(?<generic><(?:[^<>]|<[^<>]*>)*>)?\s+(?<name>[A-Za-z_]\w*)\b",
        RegexOptions.Compiled);

    // var name = new List<...> / new Dictionary<...> etc.
    static readonly Regex VarNewCollection = new(
        @"\bvar\s+(?<name>[A-Za-z_]\w*)\s*=\s*new\s+(?:List|Dictionary|HashSet|Queue|Stack|SortedList|SortedDictionary|SortedSet|LinkedList|ConcurrentDictionary|ConcurrentBag|ConcurrentQueue|ConcurrentStack|BlockingCollection)\s*<",
        RegexOptions.Compiled);

    // ?? Enumerable.Empty<(...)>  — common CS0019 when left side has named tuple elements
    static readonly Regex TupleEmptyCoalesce = new(
        @"\?\?\s*Enumerable\.Empty\s*<\s*\(",
        RegexOptions.Compiled);

    public const string CountHitMember = "CS0019.CountMethodGroup";
    public const string CountHitMessage =
        "CS0019 method-group Count — use .Count() or .Count property";

    public const string TupleHitMember = "CS0019.TupleEmptyCoalesce";
    public const string TupleHitMessage =
        "CS0019 possible incompatible ?? with Enumerable.Empty<(...)> — named vs unnamed tuple element names often differ; align tuple types by hand";

    /// <summary>
    /// High-confidence rewrites: LINQ-chain <c>.Count</c> comparisons and
    /// <c>IEnumerable</c>-typed name <c>.Count</c> comparisons → <c>.Count()</c>.
    /// </summary>
    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var enumerableNames = CollectEnumerableTypedNames(content);
        var collectionNames = CollectCollectionTypedNames(content);
        // Same identifier used as List in one place and IEnumerable in another → do not
        // auto-fix via the typed-name path (LINQ-chain .Where().Count still fixed).
        enumerableNames.ExceptWith(collectionNames);
        var edits = 0;

        // Right-to-left so indices stay valid while inserting "()".
        var matches = CountCompare.Matches(content);
        if (matches.Count == 0)
            return (content, 0);

        var sb = new StringBuilder(content);
        for (var i = matches.Count - 1; i >= 0; i--)
        {
            var m = matches[i];
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            // m.Index points at '.' of ".Count"
            if (!ShouldAutoFixCountAt(content, m.Index, enumerableNames))
                continue;

            // Insert () after "Count" (match length is ".Count" → 6 chars; Count starts at +1)
            var insertAt = m.Index + m.Length; // after "Count"
            sb.Insert(insertAt, "()");
            edits++;
        }

        return (sb.ToString(), edits);
    }

    /// <summary>
    /// Flag leftover suspicious patterns for migrate reports (manual review).
    /// Call on post-fix content. Does not spam valid <c>List.Count</c> property uses.
    /// </summary>
    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content))
            return hits;

        // After Fix, LINQ-chain / IEnumerable-typed cases should already be .Count().
        // Flag any remaining LINQ-chain .Count compares that Fix skipped (edge parse failures).
        foreach (Match m in CountCompare.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            if (IsLinqChainCount(content, m.Index))
            {
                hits.Add(MakeHit(content, m.Index, CountHitMember, CountHitMessage));
            }
        }

        foreach (Match m in TupleEmptyCoalesce.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            hits.Add(MakeHit(content, m.Index, TupleHitMember, TupleHitMessage));
        }

        hits.Sort((a, b) => a.Line.CompareTo(b.Line));
        return hits;
    }

    static RemainingHit MakeHit(string content, int index, string member, string message) => new()
    {
        Line = GetLineNumber(content, index),
        Member = member,
        Message = message,
        NeedsManual = true,
        Text = GetLineText(content, index).Trim(),
    };

    static HashSet<string> CollectEnumerableTypedNames(string content)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in EnumerableTypedName.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            // Skip method return-type false positives slightly: "IEnumerable<T> Name(" is a method.
            // If the next non-ws char after the name is '(', it's a method decl — still harmless
            // to track (Name.Count is rare), but prefer locals/params/fields.
            var name = m.Groups["name"].Value;
            var afterName = m.Index + m.Length;
            while (afterName < content.Length && char.IsWhiteSpace(content[afterName]))
                afterName++;
            if (afterName < content.Length && content[afterName] == '(')
                continue; // method returning IEnumerable — not a variable
            names.Add(name);
        }
        return names;
    }

    static HashSet<string> CollectCollectionTypedNames(string content)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in CollectionTypedName.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var name = m.Groups["name"].Value;
            var afterName = m.Index + m.Length;
            while (afterName < content.Length && char.IsWhiteSpace(content[afterName]))
                afterName++;
            if (afterName < content.Length && content[afterName] == '(')
                continue; // method returning List<T> etc.
            names.Add(name);
        }

        foreach (Match m in VarNewCollection.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            names.Add(m.Groups["name"].Value);
        }

        return names;
    }

    static bool ShouldAutoFixCountAt(string content, int countDotIndex, HashSet<string> enumerableNames)
    {
        if (IsLinqChainCount(content, countDotIndex))
            return true;

        // name.Count or name?.Count where name is IEnumerable-typed in this file
        var name = ReadReceiverNameBeforeCount(content, countDotIndex);
        return name != null && enumerableNames.Contains(name);
    }

    /// <summary>
    /// True when <c>.Count</c> at <paramref name="countDotIndex"/> is immediately after a
    /// non-materializing LINQ call: <c>.Where(...).Count</c> / <c>Enumerable.Range(...).Count</c>.
    /// </summary>
    public static bool IsLinqChainCount(string content, int countDotIndex)
    {
        if (countDotIndex <= 0 || countDotIndex >= content.Length || content[countDotIndex] != '.')
            return false;

        var i = countDotIndex - 1;
        while (i >= 0 && char.IsWhiteSpace(content[i]))
            i--;

        if (i < 0 || content[i] != ')')
            return false;

        // Walk back over balanced (...)
        var depth = 0;
        for (; i >= 0; i--)
        {
            var c = content[i];
            if (c == ')')
            {
                depth++;
                continue;
            }
            if (c == '(')
            {
                depth--;
                if (depth == 0)
                    break;
                continue;
            }
            // Bail if we hit statement boundary inside the walk (shouldn't for well-formed code)
            if (depth > 0 && c == ';' && !HitFilter.IsInsideStringLiteral(content, i))
                return false;
        }
        if (i < 0 || content[i] != '(' || depth != 0)
            return false;

        // Before '(': optional generic args, then method name
        var beforeCall = i - 1;
        while (beforeCall >= 0 && char.IsWhiteSpace(content[beforeCall]))
            beforeCall--;

        if (beforeCall >= 0 && content[beforeCall] == '>')
        {
            // Skip <...> generic
            var gDepth = 0;
            for (; beforeCall >= 0; beforeCall--)
            {
                var c = content[beforeCall];
                if (c == '>') { gDepth++; continue; }
                if (c == '<')
                {
                    gDepth--;
                    if (gDepth == 0)
                    {
                        beforeCall--;
                        break;
                    }
                }
            }
            while (beforeCall >= 0 && char.IsWhiteSpace(content[beforeCall]))
                beforeCall--;
        }

        var methodEnd = beforeCall;
        if (methodEnd < 0 || !IsIdentChar(content[methodEnd]))
            return false;
        while (methodEnd >= 0 && IsIdentChar(content[methodEnd]))
            methodEnd--;
        var methodStart = methodEnd + 1;
        var method = content.Substring(methodStart, beforeCall - methodStart + 1);

        if (Materializers.Contains(method))
            return false;
        if (!LinqChainMethods.Contains(method))
            return false;

        // Prefer instance .Method( or Enumerable.Method(
        while (methodEnd >= 0 && char.IsWhiteSpace(content[methodEnd]))
            methodEnd--;
        if (methodEnd >= 0 && content[methodEnd] == '.')
            return true;

        // Bare Where( without receiver is uncommon; still treat as LINQ if name matches
        return LinqChainMethods.Contains(method);
    }

    /// <summary>
    /// Reads <c>name</c> from <c>name.Count</c> or <c>name?.Count</c> immediately before the dot.
    /// </summary>
    static string? ReadReceiverNameBeforeCount(string content, int countDotIndex)
    {
        var i = countDotIndex - 1;
        while (i >= 0 && char.IsWhiteSpace(content[i]))
            i--;
        if (i >= 0 && content[i] == '?')
            i--; // null-conditional ?.
        while (i >= 0 && char.IsWhiteSpace(content[i]))
            i--;
        if (i < 0 || !IsIdentChar(content[i]))
            return null;
        var end = i;
        while (i >= 0 && IsIdentChar(content[i]))
            i--;
        return content.Substring(i + 1, end - i);
    }

    static bool IsIdentChar(char c) => char.IsLetterOrDigit(c) || c == '_';

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
