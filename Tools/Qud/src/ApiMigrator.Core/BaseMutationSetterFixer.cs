using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Removes obsolete <c>DisplayName = …</c> and <c>(base.)Type = "…"</c> assignments
/// inside classes that inherit <c>BaseMutation</c> (or common mutation bases). Entry data
/// belongs in Mutations.xml (PreferXML). Expression DisplayName setters (SetVariant concatenations)
/// are removed the same way as string literals.
/// </summary>
public static class BaseMutationSetterFixer
{
    public const string FixRuleName =
        "BaseMutation DisplayName/Type setter → remove (PreferXML Mutations.xml)";

    static readonly Regex ClassDecl = new(
        @"\b(?:public|internal|protected|private)?\s*(?:(?:abstract|sealed|partial|static)\s+)*class\s+(?<name>[A-Za-z_]\w*)\s*:\s*(?<bases>[^\{]+)",
        RegexOptions.Compiled);

    static readonly Regex MutationBase = new(
        @"\b(?:BaseMutation|BaseCore|IMutation)\b",
        RegexOptions.Compiled);

    static readonly Regex DisplayNameAssign = new(
        @"^[ \t]*(?:this\.)?DisplayName\s*=\s*[^;]+;[ \t]*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex TypeAssign = new(
        @"^[ \t]*(?:(?:base|this)\.)?Type\s*=\s*""(?:[^""\\]|\\.)*""\s*;[ \t]*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex ExpressionBodyTypeAssign = new(
        @"(?<ctor>\b[A-Za-z_]\w*\s*\(\s*\))\s*=>\s*(?:(?:base|this)\.)?Type\s*=\s*""(?:[^""\\]|\\.)*""\s*;",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);
        if (content.IndexOf("DisplayName", StringComparison.Ordinal) < 0 &&
            content.IndexOf("Type", StringComparison.Ordinal) < 0)
            return (content, 0);

        var edits = 0;
        var sb = new StringBuilder(content.Length);
        var last = 0;

        foreach (Match cm in ClassDecl.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, cm.Index) ||
                HitFilter.IsInsideStringLiteral(content, cm.Index))
                continue;
            if (!MutationBase.IsMatch(cm.Groups["bases"].Value))
                continue;

            var braceOpen = content.IndexOf('{', cm.Index + cm.Length - 1);
            if (braceOpen < 0) continue;
            if (!TryFindMatchingBrace(content, braceOpen, out var braceClose))
                continue;

            var body = content[(braceOpen + 1)..braceClose];
            var bodyEdits = 0;
            var nextBody = DisplayNameAssign.Replace(body, m =>
            {
                // Skip effect-style names with color markup if somehow in a non-mutation — still ok for BaseMutation
                bodyEdits++;
                return "";
            });
            nextBody = TypeAssign.Replace(nextBody, m =>
            {
                bodyEdits++;
                return "";
            });
            nextBody = ExpressionBodyTypeAssign.Replace(nextBody, m =>
            {
                var ctorName = Regex.Match(m.Groups["ctor"].Value, @"[A-Za-z_]\w*").Value;
                if (!ctorName.Equals(cm.Groups["name"].Value, StringComparison.Ordinal))
                    return m.Value;
                bodyEdits++;
                return m.Groups["ctor"].Value + " { }";
            });

            if (bodyEdits == 0) continue;

            sb.Append(content, last, braceOpen + 1 - last);
            sb.Append(nextBody);
            last = braceClose;
            edits += bodyEdits;
        }

        if (edits == 0)
            return (content, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits);
    }

    static bool TryFindMatchingBrace(string content, int openIndex, out int closeIndex)
    {
        closeIndex = -1;
        var depth = 0;
        var inStr = false;
        var inChr = false;
        var inLineComment = false;
        var inBlockComment = false;
        for (var i = openIndex; i < content.Length; i++)
        {
            var c = content[i];
            var next = i + 1 < content.Length ? content[i + 1] : '\0';

            if (inLineComment)
            {
                if (c == '\n') inLineComment = false;
                continue;
            }
            if (inBlockComment)
            {
                if (c == '*' && next == '/') { inBlockComment = false; i++; }
                continue;
            }
            if (inStr)
            {
                if (c == '\\') { i++; continue; }
                if (c == '"') inStr = false;
                continue;
            }
            if (inChr)
            {
                if (c == '\\') { i++; continue; }
                if (c == '\'') inChr = false;
                continue;
            }
            if (c == '/' && next == '/') { inLineComment = true; i++; continue; }
            if (c == '/' && next == '*') { inBlockComment = true; i++; continue; }
            if (c == '"') { inStr = true; continue; }
            if (c == '\'') { inChr = true; continue; }
            if (c == '{') depth++;
            else if (c == '}')
            {
                depth--;
                if (depth == 0)
                {
                    closeIndex = i;
                    return true;
                }
            }
        }
        return false;
    }
}
