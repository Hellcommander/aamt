using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Last-resort auto-fix: simple obsolete <c>Register(GameObject)</c> overrides whose bodies only
/// register/unregister part events on the Object parameter + optional <c>base.Register</c>.
/// Complex bodies (FireEvent-only parts, extra logic) are left for PreferHarmonyPatch advice.
/// Never adds <c>[Obsolete]</c>. Never deletes overrides.
/// </summary>
public static class RegisterOverrideFixer
{
    public const string FixRuleName =
        "Register(GameObject) → Register(GameObject, IEventRegistrar) [last-resort simple body]";

    // override void Register(GameObject Name)  — no second parameter yet
    static readonly Regex Signature = new(
        @"\b(?<sig>(?:public|protected|internal|private)\s+(?:(?:new|sealed|unsafe|async)\s+)*override\s+void\s+Register\s*\(\s*GameObject\s+(?<obj>[A-Za-z_]\w*)\s*\))",
        RegexOptions.Compiled);

    static readonly Regex SignatureBare = new(
        @"(?<=^|[\{\};])\s*(?<sig>override\s+void\s+Register\s*\(\s*GameObject\s+(?<obj>[A-Za-z_]\w*)\s*\))",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var sites = new List<(int SigStart, int SigEnd, string ObjName, string SigText)>();
        Collect(content, Signature, sites);
        Collect(content, SignatureBare, sites);
        if (sites.Count == 0)
            return (content, 0);

        // Process from end so indices stay valid
        sites.Sort((a, b) => b.SigStart.CompareTo(a.SigStart));
        var working = content;
        var edits = 0;

        foreach (var site in sites)
        {
            if (HitFilter.IsInsideComment(working, site.SigStart) ||
                HitFilter.IsInsideStringLiteral(working, site.SigStart))
                continue;

            // Already has IEventRegistrar? (defensive — regex shouldn't match)
            if (site.SigText.Contains("IEventRegistrar", StringComparison.Ordinal))
                continue;

            var braceOpen = FindMethodBodyOpen(working, site.SigEnd);
            if (braceOpen < 0) continue;
            if (!TryFindMatchingBrace(working, braceOpen, out var braceClose))
                continue;

            var body = working.Substring(braceOpen + 1, braceClose - braceOpen - 1);
            if (!TryRewriteSimpleBody(body, site.ObjName, out var newBody))
                continue;

            var newSig = site.SigText.TrimEnd();
            // Insert registrar param before closing paren of signature
            var closeParen = newSig.LastIndexOf(')');
            if (closeParen < 0) continue;
            newSig = newSig[..closeParen] + ", IEventRegistrar Registrar)";

            var replacement = newSig + working.Substring(site.SigEnd, braceOpen - site.SigEnd) +
                              "{" + newBody + "}";

            working = working[..site.SigStart] + replacement + working[(braceClose + 1)..];
            edits++;
        }

        return (working, edits);
    }

    static void Collect(
        string content,
        Regex rx,
        List<(int SigStart, int SigEnd, string ObjName, string SigText)> sites)
    {
        foreach (Match m in rx.Matches(content))
        {
            var start = m.Groups["sig"].Index;
            var end = m.Groups["sig"].Index + m.Groups["sig"].Length;
            // de-dupe overlapping
            if (sites.Any(s => s.SigStart == start))
                continue;
            sites.Add((start, end, m.Groups["obj"].Value, m.Groups["sig"].Value));
        }
    }

    static int FindMethodBodyOpen(string content, int afterSig)
    {
        var i = afterSig;
        while (i < content.Length)
        {
            var c = content[i];
            if (char.IsWhiteSpace(c)) { i++; continue; }
            if (c == '{') return i;
            // expression-bodied not supported for this fixer
            if (c == '=' && i + 1 < content.Length && content[i + 1] == '>')
                return -1;
            // attributes / unexpected
            if (c == ';') return -1;
            // allow nothing else before {
            return -1;
        }
        return -1;
    }

    static bool TryFindMatchingBrace(string content, int open, out int close)
    {
        close = -1;
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
            if (c == '{') depth++;
            else if (c == '}')
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

    /// <summary>Returns the index of the last character of the string literal (the closing quote).</summary>
    static int SkipStringLite(string content, int i)
    {
        if (i >= content.Length) return i;
        var q = content[i++];
        if (q is not ('"' or '\'')) return i - 1;
        while (i < content.Length)
        {
            if (content[i] == '\\') { i += 2; continue; }
            if (content[i] == q) return i;
            i++;
        }
        return content.Length - 1;
    }

    /// <summary>
    /// Body is "simple" if every non-comment statement is RegisterPartEvent / UnregisterPartEvent
    /// on the Object parameter (with this / (IPart)this) or base.Register(Object).
    /// </summary>
    static bool TryRewriteSimpleBody(string body, string objName, out string newBody)
    {
        newBody = body;
        var obj = Regex.Escape(objName);

        // Strip comments for validation (keep original for rewrite via regex on original)
        var stripped = StripComments(body);

        // Reject if anything other than allowed patterns remain
        var remainder = stripped;

        // Remove allowed statements
        var registerPart = new Regex(
            $@"\b{obj}\s*\.\s*RegisterPartEvent\s*\(\s*(?:\(IPart\)\s*)?this\s*,\s*[^;]+?\)\s*;",
            RegexOptions.None);
        var unregisterPart = new Regex(
            $@"\b{obj}\s*\.\s*UnregisterPartEvent\s*\(\s*(?:\(IPart\)\s*)?this\s*,\s*[^;]+?\)\s*;",
            RegexOptions.None);
        var baseRegister = new Regex(
            $@"\bbase\s*\.\s*Register\s*\(\s*{obj}\s*\)\s*;",
            RegexOptions.None);

        remainder = registerPart.Replace(remainder, " ");
        remainder = unregisterPart.Replace(remainder, " ");
        remainder = baseRegister.Replace(remainder, " ");

        // Only whitespace left?
        if (!string.IsNullOrWhiteSpace(remainder))
            return false;

        // Must have at least one RegisterPartEvent (or only base.Register — still OK for CS0672 bump)
        var hadEvents = registerPart.IsMatch(body) || unregisterPart.IsMatch(body);
        var hadBase = baseRegister.IsMatch(body);
        if (!hadEvents && !hadBase)
            return false;

        // Rewrite on original body (preserve comments / formatting)
        var rewritten = body;
        rewritten = Regex.Replace(
            rewritten,
            $@"\b{obj}\s*\.\s*RegisterPartEvent\s*\(\s*(?:\(IPart\)\s*)?this\s*,\s*(?<ev>[^;]+?)\s*\)",
            "Registrar.Register(${ev})",
            RegexOptions.None);
        rewritten = Regex.Replace(
            rewritten,
            $@"\b{obj}\s*\.\s*UnregisterPartEvent\s*\(\s*(?:\(IPart\)\s*)?this\s*,\s*(?<ev>[^;]+?)\s*\)",
            "Registrar.Unregister(${ev})",
            RegexOptions.None);
        rewritten = Regex.Replace(
            rewritten,
            $@"\bbase\s*\.\s*Register\s*\(\s*{obj}\s*\)",
            $"base.Register({objName}, Registrar)",
            RegexOptions.None);

        // If there was no base.Register, append one (game expects it)
        if (!hadBase)
        {
            var trimmed = rewritten.TrimEnd();
            var nl = rewritten.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
            // Detect indent from first non-empty line
            var indent = "            ";
            foreach (var line in rewritten.Split('\n'))
            {
                var t = line.TrimEnd('\r');
                if (string.IsNullOrWhiteSpace(t)) continue;
                var lead = t.Length - t.TrimStart().Length;
                if (lead > 0)
                {
                    indent = t[..lead];
                    break;
                }
            }
            rewritten = trimmed + nl + indent + $"base.Register({objName}, Registrar);" + nl;
        }

        newBody = rewritten;
        return true;
    }

    static string StripComments(string body)
    {
        var sb = new StringBuilder(body.Length);
        for (var i = 0; i < body.Length; i++)
        {
            var c = body[i];
            if (c is '"' or '\'')
            {
                var start = i;
                i = SkipStringLite(body, i);
                sb.Append(body, start, i - start + 1);
                continue;
            }
            if (c == '/' && i + 1 < body.Length && body[i + 1] == '/')
            {
                while (i < body.Length && body[i] != '\n') i++;
                if (i < body.Length) sb.Append('\n');
                continue;
            }
            if (c == '/' && i + 1 < body.Length && body[i + 1] == '*')
            {
                i += 2;
                while (i + 1 < body.Length && !(body[i] == '*' && body[i + 1] == '/')) i++;
                i++;
                continue;
            }
            sb.Append(c);
        }
        return sb.ToString();
    }
}
