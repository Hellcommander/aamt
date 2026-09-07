using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// One CS0618 (obsolete API) diagnostic harvested from a compiler log or an offline paste.
/// </summary>
public sealed class Cs0618Warning
{
    public string FilePath { get; set; } = "";
    public int Line { get; set; }
    public int Column { get; set; }
    public string ObsoleteSymbol { get; set; } = "";
    public string ObsoleteMessage { get; set; } = "";
    public string Raw { get; set; } = "";
}

/// <summary>
/// Parses C# compiler CS0618 lines such as:
/// <c>C:\mod\Foo.cs(12,34): warning CS0618: 'GameObject.the' is obsolete: 'Use =GameObject.the='</c>
/// Also accepts Player.log-style MODWARN wrappers that embed the same diagnostic text.
/// </summary>
public static class Cs0618Parser
{
    // path(line,col): warning CS0618: 'Symbol' is obsolete: 'Message'
    // Message may use doubled single-quotes inside.
    private static readonly Regex WarningRegex = new(
        @"(?<file>(?:[A-Za-z]:)?[^:\r\n]+?)\((?<line>\d+),(?<col>\d+)\):\s*warning\s+CS0618:\s*'(?<symbol>[^']+)'\s+is\s+obsolete:\s*'(?<msg>(?:[^']|'')*)'",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    // Fallback when the obsolete message is missing: '... is obsolete'
    private static readonly Regex WarningNoMsgRegex = new(
        @"(?<file>(?:[A-Za-z]:)?[^:\r\n]+?)\((?<line>\d+),(?<col>\d+)\):\s*warning\s+CS0618:\s*'(?<symbol>[^']+)'\s+is\s+obsolete",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public static List<Cs0618Warning> Parse(string text)
    {
        var results = new List<Cs0618Warning>();
        if (string.IsNullOrWhiteSpace(text)) return results;

        foreach (Match m in WarningRegex.Matches(text))
        {
            results.Add(FromMatch(m, hasMessage: true));
        }

        // Only use no-message form for lines that didn't already match.
        var seen = new HashSet<string>(results.Select(KeyOf), StringComparer.OrdinalIgnoreCase);
        foreach (Match m in WarningNoMsgRegex.Matches(text))
        {
            var w = FromMatch(m, hasMessage: false);
            if (seen.Add(KeyOf(w))) results.Add(w);
        }

        return results;
    }

    public static List<Cs0618Warning> ParseFile(string path) =>
        Parse(File.ReadAllText(path));

    private static Cs0618Warning FromMatch(Match m, bool hasMessage)
    {
        var file = m.Groups["file"].Value.Trim();
        // Strip MODWARN prefixes like "<...>/steamapps/..." — keep as-is; resolver resolves later.
        file = file.Replace("<...>", "", StringComparison.Ordinal);
        return new Cs0618Warning
        {
            FilePath = file,
            Line = int.Parse(m.Groups["line"].Value),
            Column = int.Parse(m.Groups["col"].Value),
            ObsoleteSymbol = m.Groups["symbol"].Value,
            ObsoleteMessage = hasMessage
                ? m.Groups["msg"].Value.Replace("''", "'", StringComparison.Ordinal)
                : "",
            Raw = m.Value,
        };
    }

    private static string KeyOf(Cs0618Warning w) =>
        $"{w.FilePath}|{w.Line}|{w.Column}|{w.ObsoleteSymbol}";
}
