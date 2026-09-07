using System.Text;

namespace ApiMigrator.Core;

/// <summary>
/// Best-effort C# call-argument splitter (strings, nested parens/brackets, named args).
/// </summary>
public static class CallArgParser
{
    public readonly record struct Arg(string? Name, string Expression);

    /// <summary>
    /// Parse the argument list starting at <paramref name="openParenIndex"/> (must point at '(').
    /// </summary>
    public static bool TryParseArgumentList(
        string content, int openParenIndex, out List<Arg> args, out int closeParenIndex)
    {
        args = new List<Arg>();
        closeParenIndex = -1;
        if (openParenIndex < 0 || openParenIndex >= content.Length || content[openParenIndex] != '(')
            return false;

        var i = openParenIndex + 1;
        var depth = 1;
        var argStart = i;
        while (i < content.Length)
        {
            var c = content[i];

            if (c is '"' or '\'' or '@')
            {
                i = SkipString(content, i);
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
                    i = Math.Min(i + 2, content.Length);
                    continue;
                }
            }

            if (c is '(' or '[' or '{')
            {
                depth++;
                i++;
                continue;
            }

            if (c is ')' or ']' or '}')
            {
                depth--;
                if (depth == 0 && c == ')')
                {
                    AddArg(content, argStart, i, args);
                    closeParenIndex = i;
                    return true;
                }
                i++;
                continue;
            }

            if (c == ',' && depth == 1)
            {
                AddArg(content, argStart, i, args);
                i++;
                argStart = i;
                continue;
            }

            i++;
        }

        args.Clear();
        closeParenIndex = -1;
        return false;
    }

    static void AddArg(string content, int start, int end, List<Arg> args)
    {
        if (end < start) return;
        var raw = content.Substring(start, end - start).Trim();
        if (raw.Length == 0 && args.Count == 0) return; // empty () 
        if (raw.Length == 0) { args.Add(new Arg(null, "")); return; }

        // Named arg: Identifier : expr  (not ternary — require identifier then colon with no ? before)
        var colon = IndexOfTopLevelColon(raw);
        if (colon > 0)
        {
            var name = raw[..colon].Trim();
            if (IsSimpleIdentifier(name))
            {
                args.Add(new Arg(name, raw[(colon + 1)..].Trim()));
                return;
            }
        }

        args.Add(new Arg(null, raw));
    }

    static int IndexOfTopLevelColon(string raw)
    {
        var depth = 0;
        for (var i = 0; i < raw.Length; i++)
        {
            var c = raw[i];
            if (c is '"' or '\'')
            {
                i = SkipString(raw, i) - 1;
                continue;
            }
            if (c is '(' or '[' or '{') depth++;
            else if (c is ')' or ']' or '}') depth--;
            else if (c == ':' && depth == 0)
            {
                // skip :: and labels in strings already handled; reject ?: ternary left of ?
                var before = raw[..i].TrimEnd();
                if (before.EndsWith('?')) continue;
                return i;
            }
        }
        return -1;
    }

    static bool IsSimpleIdentifier(string s)
    {
        if (string.IsNullOrEmpty(s)) return false;
        if (!(char.IsLetter(s[0]) || s[0] == '_')) return false;
        for (var i = 1; i < s.Length; i++)
        {
            if (!(char.IsLetterOrDigit(s[i]) || s[i] == '_')) return false;
        }
        return true;
    }

    static int SkipString(string content, int i)
    {
        if (i >= content.Length) return i;
        // verbatim @"..." or $@"..." / $"..."
        var start = i;
        if (content[i] == '@')
        {
            i++;
            if (i < content.Length && content[i] == '"')
            {
                i++;
                while (i < content.Length)
                {
                    if (content[i] == '"' && i + 1 < content.Length && content[i + 1] == '"')
                    {
                        i += 2;
                        continue;
                    }
                    if (content[i] == '"') return i + 1;
                    i++;
                }
                return content.Length;
            }
            return start + 1;
        }

        if (content[i] == '$' && i + 1 < content.Length && content[i + 1] == '"')
        {
            // interpolated — treat braces at depth for arg parser already; skip string with escapes
            i += 2;
            while (i < content.Length)
            {
                if (content[i] == '\\') { i += 2; continue; }
                if (content[i] == '"') return i + 1;
                // skip interpolated holes roughly
                if (content[i] == '{')
                {
                    if (i + 1 < content.Length && content[i + 1] == '{') { i += 2; continue; }
                    var d = 1;
                    i++;
                    while (i < content.Length && d > 0)
                    {
                        if (content[i] == '{') d++;
                        else if (content[i] == '}') d--;
                        else if (content[i] is '"' or '\'') i = SkipString(content, i) - 1;
                        i++;
                    }
                    continue;
                }
                i++;
            }
            return content.Length;
        }

        if (content[i] is '"' or '\'')
        {
            var quote = content[i++];
            while (i < content.Length)
            {
                if (content[i] == '\\') { i += 2; continue; }
                if (content[i] == quote) return i + 1;
                i++;
            }
            return content.Length;
        }

        return i + 1;
    }

    /// <summary>
    /// Find the opening '(' of a method call ending at <paramref name="nameEnd"/> (index after method name).
    /// </summary>
    public static int FindCallOpenParen(string content, int nameEnd)
    {
        var i = nameEnd;
        while (i < content.Length && char.IsWhiteSpace(content[i])) i++;
        return i < content.Length && content[i] == '(' ? i : -1;
    }

    public static string JoinNamedArgs(IEnumerable<(string Name, string Expr)> named, string indent = "    ")
    {
        var sb = new StringBuilder();
        var first = true;
        foreach (var (name, expr) in named)
        {
            if (!first) sb.Append(',').AppendLine();
            first = false;
            sb.Append(indent).Append(name).Append(": ").Append(expr);
        }
        return sb.ToString();
    }
}
