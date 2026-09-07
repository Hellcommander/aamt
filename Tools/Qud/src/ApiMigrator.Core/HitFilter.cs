using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Post-match suppressions for dump scan hits that are structurally obsolete-shaped but are
/// not real CS0618 call sites (GameText templates, comments, known cross-type collisions).
/// Pattern tightenings in the dump handle most cases; this covers cross-cutting context.
/// </summary>
public static class HitFilter
{
    private static readonly HashSet<string> ShortGameObjectMembers = new(StringComparer.Ordinal)
    {
        "a", "A", "an", "An", "the", "The", "them", "Them", "they", "They",
        "their", "Their", "its", "Its", "itself", "Itself", "it", "It",
        "tis", "Tis", "itis", "Is", "are",
    };

    /// <summary>
    /// Per-file precomputed comment/string membership so dump scans do not re-walk the
    /// whole file from index 0 for every match (catastrophic on short patterns like .a / .the).
    /// </summary>
    public sealed class FileContext
    {
        private readonly bool[] _inComment;
        private readonly bool[] _inString;

        internal FileContext(bool[] inComment, bool[] inString)
        {
            _inComment = inComment;
            _inString = inString;
        }

        public bool IsInsideComment(int index) =>
            index >= 0 && index < _inComment.Length && _inComment[index];

        public bool IsInsideStringLiteral(int index) =>
            index >= 0 && index < _inString.Length && _inString[index];
    }

    /// <summary>Build once per file before scanning dump matches.</summary>
    public static FileContext BuildContext(string content)
    {
        var n = content?.Length ?? 0;
        var inComment = new bool[n];
        var inString = new bool[n];
        if (n == 0) return new FileContext(inComment, inString);

        var i = 0;
        while (i < n)
        {
            var c = content![i];

            // Line comment
            if (c == '/' && i + 1 < n && content[i + 1] == '/')
            {
                var start = i;
                var eol = content.IndexOf('\n', i + 2);
                if (eol < 0) eol = n;
                for (var k = start; k < eol; k++) inComment[k] = true;
                i = eol;
                continue;
            }

            // Block comment
            if (c == '/' && i + 1 < n && content[i + 1] == '*')
            {
                var start = i;
                var end = content.IndexOf("*/", i + 2, StringComparison.Ordinal);
                var stop = end < 0 ? n : end + 2;
                for (var k = start; k < stop; k++) inComment[k] = true;
                i = stop;
                continue;
            }

            // Strings: ", @", $", $@"
            if (c == '"' || c == '@' || c == '$')
            {
                var start = i;
                var next = SkipStringLiteral(content, i);
                if (next > start + 1 || (c == '"' && next > start))
                {
                    for (var k = start; k < next && k < n; k++) inString[k] = true;
                    i = Math.Max(next, start + 1);
                    continue;
                }
            }

            i++;
        }

        return new FileContext(inComment, inString);
    }

    /// <summary>
    /// Returns false when <paramref name="match"/> should not be reported as an obsolete hit.
    /// Pass <paramref name="ctx"/> from <see cref="BuildContext"/> for O(1) comment/string checks.
    /// </summary>
    public static bool ShouldReport(ObsoleteEntry entry, string content, Match match, FileContext? ctx = null)
    {
        if (match is null || !match.Success) return false;
        var index = match.Index;

        if (ctx is not null)
        {
            if (ctx.IsInsideComment(index))
                return false;
        }
        else if (IsInsideComment(content, index))
        {
            return false;
        }

        if (IsInsideGameTextToken(content, index))
            return false;

        if (IsShortGameObjectPronoun(entry))
        {
            var inStr = ctx is not null
                ? ctx.IsInsideStringLiteral(index)
                : IsInsideStringLiteral(content, index);
            if (inStr) return false;
            if (IsCaseLabelOrAssignment(content, index, index + match.Length))
                return false;
            if (IsPronounEnumReceiver(content, index))
                return false;
        }

        // Body/Inventory.DeepCopy dump patterns use bare .DeepCopy( and false-positive on
        // GameObject.DeepCopy(… MapInv …) which is the current non-obsolete API.
        if (entry.Member.Equals("DeepCopy", StringComparison.Ordinal) &&
            (entry.Type.Contains("Body", StringComparison.Ordinal) ||
             entry.Type.Contains("Inventory", StringComparison.Ordinal)))
        {
            var start = Math.Max(0, index - 48);
            var window = content[start..Math.Min(content.Length, index + 80)];
            if (window.Contains("MapInv", StringComparison.Ordinal) ||
                Regex.IsMatch(window, @"\b(?:ParentObject|gameObject|GO|Object|transmitter)\s*\.DeepCopy\s*\("))
                return false;
        }

        // Mod-defined AddAction (vendor events, etc.) is not IInventoryActionsEvent.AddAction.
        if (entry.Member.Equals("AddAction", StringComparison.Ordinal) &&
            (entry.Type.Contains("InventoryActions", StringComparison.Ordinal) ||
             entry.Type.Contains("GetInventoryActions", StringComparison.Ordinal)))
        {
            if (!AddActionFixer.IsInventoryAddActionCall(content, index))
                return false;
        }

        return true;
    }

    static readonly HashSet<string> PronounEnumReceivers = new(StringComparer.Ordinal)
    {
        "Keys", "KeyCode", "ConsoleKey",
    };

    /// <summary>
    /// <c>case Keys.A:</c> / <c>go.A = …</c> — not GameObject pronoun access.
    /// </summary>
    public static bool IsCaseLabelOrAssignment(string content, int exprStart, int exprEnd)
    {
        if (string.IsNullOrEmpty(content) || exprStart < 0 || exprStart > content.Length)
            return false;

        var i = exprStart;
        while (i > 0 && char.IsWhiteSpace(content[i - 1])) i--;
        if (i >= 4)
        {
            var from = Math.Max(0, i - 5);
            var before = content[from..i];
            if (Regex.IsMatch(before, @"\bcase\s*$"))
                return true;
        }

        var j = Math.Min(content.Length, Math.Max(exprStart, exprEnd));
        while (j < content.Length && char.IsWhiteSpace(content[j])) j++;
        if (j >= content.Length) return false;
        if (content[j] == ':') return true;
        if (content[j] == '=' && (j + 1 >= content.Length || content[j + 1] != '='))
            return true;
        return false;
    }

    /// <summary>
    /// Receiver immediately before <c>.A</c>/<c>.a</c>/… is a key/enum type, not a GameObject.
    /// </summary>
    public static bool IsPronounEnumReceiver(string content, int matchIndex)
    {
        if (string.IsNullOrEmpty(content) || matchIndex < 0)
            return false;
        var searchTo = Math.Min(content.Length - 1, matchIndex + 64);
        var dot = -1;
        for (var k = matchIndex; k <= searchTo; k++)
        {
            if (content[k] == '.')
            {
                dot = k;
                break;
            }
        }
        if (dot < 1) return false;
        var end = dot;
        var start = end;
        while (start > 0 && (char.IsLetterOrDigit(content[start - 1]) || content[start - 1] == '_'))
            start--;
        if (start >= end) return false;
        var recv = content[start..end];
        return PronounEnumReceivers.Contains(recv);
    }

    public static bool IsPronounEnumName(string recv)
    {
        if (string.IsNullOrEmpty(recv)) return false;
        var leaf = recv.Contains('.') ? recv[(recv.LastIndexOf('.') + 1)..] : recv;
        return PronounEnumReceivers.Contains(recv) || PronounEnumReceivers.Contains(leaf);
    }

    private static bool IsShortGameObjectPronoun(ObsoleteEntry entry)
    {
        if (!entry.Type.EndsWith("GameObject", StringComparison.Ordinal))
            return false;
        return ShortGameObjectMembers.Contains(entry.Member);
    }

    /// <summary>
    /// True when index sits in a <c>//</c> line comment or <c>/* */</c> block comment
    /// (best-effort; ignores comment markers inside strings).
    /// </summary>
    public static bool IsInsideComment(string content, int index)
    {
        if (index < 0 || index > content.Length) return false;

        var i = 0;
        var blockDepth = 0;
        while (i < index)
        {
            var c = content[i];

            if (c is '"' or '\'')
            {
                i = SkipStringLiteral(content, i);
                continue;
            }

            if (c == '/' && i + 1 < content.Length)
            {
                var n = content[i + 1];
                if (n == '/' && blockDepth == 0)
                {
                    var eol = content.IndexOf('\n', i + 2);
                    if (eol < 0) eol = content.Length;
                    if (index > i && index < eol)
                        return true;
                    i = eol;
                    continue;
                }
                if (n == '*')
                {
                    blockDepth++;
                    i += 2;
                    continue;
                }
            }

            if (blockDepth > 0 && c == '*' && i + 1 < content.Length && content[i + 1] == '/')
            {
                blockDepth--;
                i += 2;
                continue;
            }

            i++;
        }

        return blockDepth > 0;
    }

    public static bool IsInsideGameTextToken(string content, int index)
    {
        if (index <= 0 || index >= content.Length) return false;

        var lineStart = index == 0 ? 0 : content.LastIndexOf('\n', index - 1) + 1;
        var lineEnd = content.IndexOf('\n', index);
        if (lineEnd < 0) lineEnd = content.Length;

        for (var open = index - 1; open >= lineStart; open--)
        {
            if (content[open] != '=') continue;
            if (open + 1 >= lineEnd || !char.IsLetter(content[open + 1]))
                continue;

            var close = content.IndexOf('=', index);
            if (close < 0 || close >= lineEnd) return false;

            for (var k = open + 1; k < close; k++)
            {
                var ch = content[k];
                if (char.IsLetterOrDigit(ch) || ch is '.' or '_' or ':' or '#' or '\'' or '-')
                    continue;
                return false;
            }
            return close > open + 1;
        }
        return false;
    }

    public static bool IsInsideStringLiteral(string content, int index)
    {
        if (index < 0 || index >= content.Length) return false;
        var i = 0;
        while (i < index)
        {
            var c = content[i];
            if (c is '"' or '@' or '$')
            {
                if (c == '@' && i + 1 < content.Length && content[i + 1] == '"')
                {
                    var start = i;
                    i = SkipStringLiteral(content, i);
                    if (index > start && index < i) return true;
                    continue;
                }
                if (c == '$' && i + 1 < content.Length && content[i + 1] == '"')
                {
                    var start = i;
                    i = SkipStringLiteral(content, i);
                    if (index > start && index < i) return true;
                    continue;
                }
                if (c == '$' && i + 2 < content.Length && content[i + 1] == '@' && content[i + 2] == '"')
                {
                    var start = i;
                    i = SkipStringLiteral(content, i);
                    if (index > start && index < i) return true;
                    continue;
                }
                if (c == '"')
                {
                    var start = i;
                    i = SkipStringLiteral(content, i);
                    if (index > start && index < i) return true;
                    continue;
                }
            }
            if (c == '/' && i + 1 < content.Length)
            {
                var n = content[i + 1];
                if (n == '/')
                {
                    var eol = content.IndexOf('\n', i + 2);
                    i = eol < 0 ? content.Length : eol;
                    continue;
                }
                if (n == '*')
                {
                    var end = content.IndexOf("*/", i + 2, StringComparison.Ordinal);
                    i = end < 0 ? content.Length : end + 2;
                    continue;
                }
            }
            i++;
        }
        return false;
    }

    private static int SkipStringLiteral(string content, int start)
    {
        var i = start;
        var verbatim = false;
        var interpolated = false;

        if (content[i] == '$')
        {
            interpolated = true;
            i++;
            if (i < content.Length && content[i] == '@')
            {
                verbatim = true;
                i++;
            }
        }
        else if (content[i] == '@')
        {
            verbatim = true;
            i++;
        }

        if (i >= content.Length || content[i] != '"')
            return start + 1;

        i++;
        while (i < content.Length)
        {
            var c = content[i];
            if (verbatim)
            {
                if (c == '"')
                {
                    if (i + 1 < content.Length && content[i + 1] == '"')
                    {
                        i += 2;
                        continue;
                    }
                    return i + 1;
                }
                i++;
                continue;
            }

            if (c == '\\')
            {
                i += 2;
                continue;
            }
            if (c == '"')
                return i + 1;

            if (interpolated && c == '{')
            {
                i++;
                var depth = 1;
                while (i < content.Length && depth > 0)
                {
                    if (content[i] == '{') depth++;
                    else if (content[i] == '}') depth--;
                    else if (content[i] == '"' || content[i] == '\'')
                    {
                        i = SkipStringLiteral(content, i);
                        continue;
                    }
                    i++;
                }
                continue;
            }
            i++;
        }
        return content.Length;
    }
}
