using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Inserts missing <c>using Namespace;</c> directives into C# source. Shared by the curated-rule
/// engine so PowerShell and C# paths stay behaviorally aligned (PS mirrors this regex logic).
/// </summary>
public static class UsingInserter
{
    private static readonly Regex FileScopedUsing = new(
        @"(?m)^(?:global\s+)?using\s+[^;]+;\r?\n",
        RegexOptions.Compiled);

    private static readonly Regex NamespaceStart = new(
        @"(?m)^(?:(?:public|internal|file)\s+)?namespace\s",
        RegexOptions.Compiled);

    private static readonly Regex NamespaceDecl = new(
        @"(?m)^(?:(?:public|internal|file)\s+)?namespace\s+([A-Za-z_][\w.]*)",
        RegexOptions.Compiled);

    /// <summary>
    /// True when the file already has <c>using ns;</c> or <c>global using ns;</c>.
    /// Does not detect alias usings (<c>using X = ns;</c>).
    /// </summary>
    public static bool HasUsing(string content, string ns)
    {
        if (string.IsNullOrWhiteSpace(ns)) return true;
        var pattern = $@"(?m)^(?:global\s+)?using\s+{Regex.Escape(ns)}\s*;";
        return Regex.IsMatch(content, pattern);
    }

    /// <summary>
    /// Ensures each namespace appears as a file-scoped using. Returns the (possibly unchanged)
    /// content and the list of namespaces that were actually inserted.
    /// </summary>
    public static (string Content, List<string> Inserted) EnsureUsings(
        string content, IEnumerable<string> namespaces)
    {
        var needed = namespaces
            .Where(n => !string.IsNullOrWhiteSpace(n))
            .Distinct(StringComparer.Ordinal)
            .Where(n => !HasUsing(content, n) && !FileNamespaceIsOrUnder(content, n))
            .OrderBy(n => n, StringComparer.Ordinal)
            .ToList();

        if (needed.Count == 0)
            return (content, needed);

        var nl = content.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
        var block = string.Concat(needed.Select(n => $"using {n};{nl}"));

        var usingMatches = FileScopedUsing.Matches(content);
        if (usingMatches.Count > 0)
        {
            var last = usingMatches[^1];
            var insertAt = last.Index + last.Length;
            return (content.Insert(insertAt, block), needed);
        }

        var nsMatch = NamespaceStart.Match(content);
        if (nsMatch.Success)
        {
            // Blank line between usings and namespace when we invent the using block.
            return (content.Insert(nsMatch.Index, block + nl), needed);
        }

        return (block + nl + content, needed);
    }

    /// <summary>
    /// True when every namespace in the file is <paramref name="ns"/> or nested under it
    /// (<c>namespace XRL.World.Parts</c> has <c>XRL</c> extension methods in scope).
    /// False when the file has no namespace, or mixed namespaces (a split helper + IPart file
    /// still needs the helper's using in the <c>XRL.World.Parts</c> block).
    /// </summary>
    public static bool FileNamespaceIsOrUnder(string content, string ns)
    {
        if (string.IsNullOrWhiteSpace(ns) || string.IsNullOrEmpty(content))
            return false;
        var matches = NamespaceDecl.Matches(content);
        if (matches.Count == 0)
            return false;
        foreach (Match m in matches)
        {
            var fileNs = m.Groups[1].Value;
            if (!fileNs.Equals(ns, StringComparison.Ordinal) &&
                !fileNs.StartsWith(ns + ".", StringComparison.Ordinal))
                return false;
        }
        return true;
    }

    /// <summary>
    /// Usings required for GameText <c>StartReplace</c> chains: always
    /// <c>XRL.World.Text</c>; also <c>XRL</c> when the file is not already under that namespace
    /// (extension methods live in <c>XRL</c>, not only <c>XRL.World.Text</c>).
    /// </summary>
    public static IEnumerable<string> UsingsForStartReplace(string content)
    {
        yield return "XRL.World.Text";
        if (content.Contains("StartReplace", StringComparison.Ordinal))
            yield return "XRL";
    }
}
