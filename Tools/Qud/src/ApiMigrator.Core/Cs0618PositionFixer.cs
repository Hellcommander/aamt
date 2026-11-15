using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Rewrites that are only safe when the compiler has said which overload a call binds to. A CS0618 warning
/// carries the file, line and column of the call and the full obsolete signature, so these fixes run from the
/// harvested warnings (<see cref="Cs0618Resolver"/>), never from a text scan.
///
/// <c>Grammar.MakeAndList(words)</c> / <c>MakeOrList(words)</c>: only the string-list overloads are obsolete
/// (the GameObject-list ones are not), and a text scan can't tell them apart. The replacement,
/// <c>Translator.MakeAndList(List, SerialComma)</c>, sits in the same namespace but has no default for its
/// second parameter, so a one-argument call gains an explicit <c>true</c> (the old default).
/// </summary>
public static class Cs0618PositionFixer
{
    public const string FixRuleName = "Grammar.MakeAndList/MakeOrList(strings) → Translator (from CS0618 position)";

    static readonly Regex ListSymbol = new(
        @"^Grammar\.(?<method>MakeAndList|MakeOrList)\(IReadOnlyList<string>",
        RegexOptions.Compiled);

    /// <summary>
    /// Applies the position-driven fixes for one file. <paramref name="warnings"/> are that file's warnings,
    /// with the line and column the compiler reported. A warning whose line no longer holds the call (the
    /// file changed since the log was written) is skipped.
    /// </summary>
    public static (string Content, int EditCount) Apply(string content, IEnumerable<Cs0618Warning> warnings)
    {
        var targets = new List<(int Line, int Column, string Method)>();
        foreach (var w in warnings)
        {
            var m = ListSymbol.Match(w.ObsoleteSymbol.Trim());
            if (m.Success && w.Line > 0)
                targets.Add((w.Line, Math.Max(1, w.Column), m.Groups["method"].Value));
        }
        if (targets.Count == 0)
            return (content, 0);

        // Offsets of each line start, so (line, column) maps to an index. Work bottom-up: an edit never
        // moves a target that is still to come.
        var lineStarts = new List<int> { 0 };
        for (var i = 0; i < content.Length; i++)
            if (content[i] == '\n') lineStarts.Add(i + 1);

        var edits = 0;
        foreach (var (line, column, method) in targets
                     .Distinct()
                     .OrderByDescending(t => t.Line)
                     .ThenByDescending(t => t.Column))
        {
            if (line > lineStarts.Count) continue;
            var lineStart = lineStarts[line - 1];
            var lineEnd = line < lineStarts.Count ? lineStarts[line] : content.Length;
            var call = "Grammar." + method;
            // The column points at the start of the call expression; a qualified XRL.Language.Grammar
            // starts a little earlier, so look from the column to the end of the line.
            // Some compilers report the member name's column instead; step back over "Grammar." to cover both.
            var from = Math.Clamp(lineStart + column - 1 - "Grammar.".Length, lineStart, lineEnd);
            var at = content.IndexOf(call, from, lineEnd - from, StringComparison.Ordinal);
            if (at < 0) continue;
            var open = at + call.Length;
            while (open < content.Length && char.IsWhiteSpace(content[open])) open++;
            if (open >= content.Length || content[open] != '(') continue;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close)) continue;
            // Named arguments use the old parameter names (Words, Serial); the new ones differ.
            if (args.Any(a => a.Name != null)) continue;
            var count = LogicalArgumentCount(args);
            if (count is < 1 or > 2) continue;

            if (count == 1)
                content = content.Insert(close, ", true");
            content = content.Remove(at, "Grammar".Length).Insert(at, "Translator");
            edits++;
        }
        return (content, edits);
    }

    static readonly Regex StringLiteral = new(@"""(?:[^""\\]|\\.)*""", RegexOptions.Compiled);

    /// <summary>
    /// The argument parser splits on every top-level comma, including the one inside a generic argument list
    /// (<c>xs.Select&lt;GameObject, string&gt;(...)</c> came back as two arguments, so a one-argument call was
    /// taken for a two-argument one and got no <c>, true</c>). Pieces are glued back together while their
    /// angle brackets don't balance; <c>=&gt;</c> arrows and brackets inside string literals don't count.
    /// </summary>
    static int LogicalArgumentCount(List<CallArgParser.Arg> args)
    {
        var count = 0;
        var open = 0;
        foreach (var arg in args)
        {
            var text = StringLiteral.Replace(arg.Expression, "\"\"").Replace("=>", "", StringComparison.Ordinal);
            open += text.Count(c => c == '<') - text.Count(c => c == '>');
            if (open <= 0)
            {
                count++;
                open = 0;
            }
        }
        // Still open at the end: the pieces were one unfinished argument.
        return open > 0 ? count + 1 : count;
    }
}
