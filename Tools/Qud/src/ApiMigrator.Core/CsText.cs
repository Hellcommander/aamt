namespace ApiMigrator.Core;

/// <summary>Small C# scan helpers (strings / comments / balanced braces) for programmatic fixers.</summary>
public static class CsText
{
    /// <summary>Returns the index of the last character of the string/char literal (the closing quote).</summary>
    public static int SkipStringLite(string content, int i)
    {
        if (i >= content.Length) return i;
        var q = content[i++];
        if (q is not ('"' or '\'')) return i - 1;
        var verbatim = q == '"' && i >= 2 && content[i - 2] == '@';
        while (i < content.Length)
        {
            var c = content[i];
            if (!verbatim && c == '\\' && i + 1 < content.Length)
            {
                i += 2;
                continue;
            }
            if (c == q) return i;
            i++;
        }
        return content.Length - 1;
    }

    public static bool TryFindMatching(string content, int open, char openCh, char closeCh, out int close)
    {
        close = -1;
        if (open < 0 || open >= content.Length || content[open] != openCh)
            return false;
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
            if (c == openCh) depth++;
            else if (c == closeCh)
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

    public static bool TryFindMatchingBrace(string content, int open, out int close) =>
        TryFindMatching(content, open, '{', '}', out close);

    public static bool TryFindMatchingParen(string content, int open, out int close) =>
        TryFindMatching(content, open, '(', ')', out close);

    public static int SkipWsAndComments(string content, int i)
    {
        while (i < content.Length)
        {
            var c = content[i];
            if (char.IsWhiteSpace(c)) { i++; continue; }
            if (c == '/' && i + 1 < content.Length && content[i + 1] == '/')
            {
                while (i < content.Length && content[i] != '\n') i++;
                continue;
            }
            if (c == '/' && i + 1 < content.Length && content[i + 1] == '*')
            {
                i += 2;
                while (i + 1 < content.Length && !(content[i] == '*' && content[i + 1] == '/')) i++;
                i = Math.Min(i + 2, content.Length);
                continue;
            }
            break;
        }
        return i;
    }

    public static int GetLineNumber(string text, int index)
    {
        var line = 1;
        var lim = Math.Min(index, text.Length);
        for (var i = 0; i < lim; i++)
        {
            if (text[i] == '\n') line++;
        }
        return line;
    }

    public static string GetLineText(string text, int index)
    {
        var start = index;
        while (start > 0 && text[start - 1] != '\n') start--;
        var end = index;
        while (end < text.Length && text[end] != '\n' && text[end] != '\r') end++;
        return text[start..end];
    }
}
