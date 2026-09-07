using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

namespace ApiMigrator.Core;

/// <summary>
/// Auto-fixes truncated / EOF-unclosed XML that the game reports as
/// <c>Unexpected end of file has occurred. The following elements are not closed: …</c>
/// (e.g. ChooseYourFighter expansions missing <c>&lt;/group&gt;&lt;/KernelmethodChooseYourFighter&gt;</c>).
/// Only applies when appending the missing closers yields a well-formed document.
/// </summary>
public static class XmlUnclosedElementFixer
{
    public const string FixRuleName = "XML append missing closing tags (EOF unclosed)";

    static readonly Regex XmlDeclOrCommentLead = new(
        @"^\s*(?:<\?xml\b[^>]*\?>\s*|<!--.*?-->\s*)*",
        RegexOptions.Compiled | RegexOptions.Singleline | RegexOptions.IgnoreCase);

    static readonly Regex NameToken = new(
        @"[A-Za-z_][\w.\-]*",
        RegexOptions.Compiled);

    /// <summary>
    /// If the document is already well-formed, returns unchanged.
    /// Otherwise tries to close the open-element stack (after stripping a trailing
    /// mistaken re-open of the root tag) and keeps the result only if it parses.
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrWhiteSpace(content)) return (content, fixes);
        if (IsWellFormed(content)) return (content, fixes);

        var working = content;
        var stripped = StripTrailingBogusRootReopen(working);
        var didStrip = !ReferenceEquals(stripped, working) && stripped != working;
        working = stripped;

        var stack = BuildOpenElementStack(working);
        if (stack == null || stack.Count == 0)
            return (content, fixes);

        var nl = working.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
        var sb = new StringBuilder(working.TrimEnd());
        foreach (var name in Enumerable.Reverse(stack))
            sb.Append(nl).Append("</").Append(name).Append('>');
        if (working.EndsWith('\n') || working.EndsWith("\r\n", StringComparison.Ordinal))
            sb.Append(nl);

        var candidate = sb.ToString();
        if (!IsWellFormed(candidate))
            return (content, fixes);

        fixes.Add(new AppliedFix
        {
            RuleName = FixRuleName,
            Count = stack.Count + (didStrip ? 1 : 0),
        });
        return (candidate, fixes);
    }

    public static bool IsWellFormed(string content)
    {
        if (string.IsNullOrWhiteSpace(content)) return false;
        try
        {
            var settings = new XmlReaderSettings
            {
                DtdProcessing = DtdProcessing.Prohibit,
                XmlResolver = null,
                CheckCharacters = false,
            };
            using var reader = XmlReader.Create(new StringReader(content), settings);
            while (reader.Read()) { }
            return true;
        }
        catch (XmlException)
        {
            return false;
        }
    }

    /// <summary>
    /// Some truncated CYF files end with a bare <c>&lt;Root&gt;</c> instead of closers.
    /// Strip that trailing reopen when the root was already opened earlier.
    /// </summary>
    static string StripTrailingBogusRootReopen(string content)
    {
        var root = PeekRootElementName(content);
        if (root == null) return content;

        var trimmed = content.TrimEnd();
        var rx = new Regex(
            $@"<\s*{Regex.Escape(root)}\s*>\s*$",
            RegexOptions.CultureInvariant);
        if (!rx.IsMatch(trimmed)) return content;

        // Require the root to appear as a real open earlier (not only this trailing tag).
        var earlier = trimmed[..rx.Match(trimmed).Index];
        if (!Regex.IsMatch(earlier, $@"<\s*{Regex.Escape(root)}\b", RegexOptions.CultureInvariant))
            return content;

        return rx.Replace(trimmed, "").TrimEnd() +
               (content.EndsWith('\n') || content.EndsWith("\r\n", StringComparison.Ordinal)
                   ? (content.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n")
                   : "");
    }

    static string? PeekRootElementName(string content)
    {
        var m = XmlDeclOrCommentLead.Match(content);
        var i = m.Success ? m.Length : 0;
        while (i < content.Length && char.IsWhiteSpace(content[i])) i++;
        if (i >= content.Length || content[i] != '<') return null;
        if (i + 1 < content.Length && content[i + 1] == '/') return null;
        i++;
        var nameMatch = NameToken.Match(content, i);
        return nameMatch.Success ? nameMatch.Value : null;
    }

    /// <summary>
    /// Lightweight open-element stack. Returns null when the scan hits mismatched
    /// closers or unrecoverable structure (do not auto-fix).
    /// </summary>
    static List<string>? BuildOpenElementStack(string content)
    {
        var stack = new List<string>();
        var i = 0;
        while (i < content.Length)
        {
            if (content[i] != '<')
            {
                i++;
                continue;
            }

            // Comment
            if (i + 3 < content.Length && content.AsSpan(i).StartsWith("<!--"))
            {
                var end = content.IndexOf("-->", i + 4, StringComparison.Ordinal);
                if (end < 0) return null;
                i = end + 3;
                continue;
            }

            // PI
            if (i + 1 < content.Length && content[i + 1] == '?')
            {
                var end = content.IndexOf("?>", i + 2, StringComparison.Ordinal);
                if (end < 0) return null;
                i = end + 2;
                continue;
            }

            // CDATA
            if (i + 8 < content.Length && content.AsSpan(i).StartsWith("<![CDATA["))
            {
                var end = content.IndexOf("]]>", i + 9, StringComparison.Ordinal);
                if (end < 0) return null;
                i = end + 3;
                continue;
            }

            var tagEnd = content.IndexOf('>', i + 1);
            if (tagEnd < 0) return null; // truncated mid-tag — don't guess

            var inner = content.Substring(i + 1, tagEnd - i - 1).Trim();
            if (inner.Length == 0) { i = tagEnd + 1; continue; }

            if (inner[0] == '/')
            {
                var closeName = NameToken.Match(inner, 1);
                if (!closeName.Success) return null;
                if (stack.Count == 0) return null;
                if (!stack[^1].Equals(closeName.Value, StringComparison.Ordinal))
                    return null; // mismatched — unsafe
                stack.RemoveAt(stack.Count - 1);
                i = tagEnd + 1;
                continue;
            }

            if (inner[0] is '!' or '?')
            {
                i = tagEnd + 1;
                continue;
            }

            var openName = NameToken.Match(inner);
            if (!openName.Success) return null;

            var selfClose = inner.EndsWith('/');
            if (!selfClose)
                stack.Add(openName.Value);

            i = tagEnd + 1;
        }

        return stack;
    }
}
