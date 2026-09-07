using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Migrates obsolete GameText variable replacer shapes:
/// <list type="bullet">
/// <item><c>[VariableObjectReplacer(…)]</c> → <c>[VariableReplacer(…, Capitalization = true)]</c></item>
/// <item><c>DelegateContext</c> first param under <c>[VariableReplacer]</c>/<c>[VariableObjectReplacer]</c>
/// → <c>VariableContext</c></item>
/// <item>When the body uses <c>Context.Target</c>/<c>Pronouns</c>/<c>Explicit</c>, add
/// <c>GameObject Object</c> and rewrite those accesses (vanilla <c>GameObjectReplacers</c> pattern).</item>
/// </list>
/// Conversation <c>DelegateContext</c> (no VariableReplacer attribute) is left untouched.
/// </summary>
public static class VariableReplacerFixer
{
    public const string FixRuleNameAttr =
        "[VariableObjectReplacer] → [VariableReplacer(Capitalization = true)]";

    public const string FixRuleNameSignature =
        "[VariableReplacer] DelegateContext/Target → VariableContext (+ GameObject Object)";

    // Attribute on its own line(s), then method signature with DelegateContext or VariableContext first param.
    static readonly Regex ReplacerMethod = new(
        @"\[(?<attr>Variable(?:Object)?Replacer)\b(?<attrTail>[^\]]*)\](?<between>\s*)" +
        @"(?<sig>(?:(?:public|private|internal|protected|static|unsafe|new|partial)\s+)+)" +
        @"(?<ret>[A-Za-z_][\w.<>,\[\]\s\?]*?)\s+" +
        @"(?<name>[A-Za-z_]\w*)\s*" +
        @"\((?<params>[^)]*)\)",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex DelegateFirstParam = new(
        @"^\s*DelegateContext\s+(?<ctx>[A-Za-z_]\w*)\b",
        RegexOptions.Compiled);

    static readonly Regex VariableFirstParam = new(
        @"^\s*VariableContext\s+(?<ctx>[A-Za-z_]\w*)\b",
        RegexOptions.Compiled);

    public static (string Content, int AttributeEdits, int SignatureEdits) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0, 0);
        if (content.IndexOf("VariableReplacer", StringComparison.Ordinal) < 0 &&
            content.IndexOf("VariableObjectReplacer", StringComparison.Ordinal) < 0)
            return (content, 0, 0);

        var matches = ReplacerMethod.Matches(content);
        if (matches.Count == 0)
            return (content, 0, 0);

        var attrEdits = 0;
        var sigEdits = 0;
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;

        foreach (Match m in matches)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var attrName = m.Groups["attr"].Value;
            var attrTail = m.Groups["attrTail"].Value; // includes leading '(' … or empty / whitespace
            var between = m.Groups["between"].Value;
            var sigMods = m.Groups["sig"].Value;
            var ret = m.Groups["ret"].Value.TrimEnd();
            var name = m.Groups["name"].Value;
            var parameters = m.Groups["params"].Value;

            var newAttr = RewriteAttribute(attrName, attrTail, out var attrChanged);
            var newParams = parameters;
            var bodyRewrite = false;
            string? ctxName = null;

            var del = DelegateFirstParam.Match(parameters);
            var varCtx = VariableFirstParam.Match(parameters);
            if (del.Success)
                ctxName = del.Groups["ctx"].Value;
            else if (varCtx.Success)
                ctxName = varCtx.Groups["ctx"].Value;

            // Find method body (expression-bodied `=>` or `{ … }`).
            var afterSig = m.Index + m.Length;
            afterSig = CsText.SkipWsAndComments(content, afterSig);
            string? body = null;
            var bodyStart = -1;
            var bodyEnd = -1; // index of closing `}` or `;` (not included in body)

            if (afterSig < content.Length && content[afterSig] == '{')
            {
                if (CsText.TryFindMatchingBrace(content, afterSig, out var close))
                {
                    bodyStart = afterSig + 1;
                    bodyEnd = close;
                    body = content[bodyStart..bodyEnd];
                }
            }
            else if (afterSig + 1 < content.Length && content[afterSig] == '=' && content[afterSig + 1] == '>')
            {
                var semi = content.IndexOf(';', afterSig);
                if (semi >= 0)
                {
                    bodyStart = afterSig + 2;
                    bodyEnd = semi;
                    body = content[bodyStart..bodyEnd];
                }
            }

            var needsObject = false;
            if (ctxName is not null && body is not null)
            {
                // Explicit is GenderedNoun-only legacy; leave for ManualAdvice.
                needsObject =
                    UsesContextMember(body, ctxName, "Target") ||
                    UsesContextMember(body, ctxName, "Pronouns");
            }

            var hasGameObjectParam = Regex.IsMatch(
                parameters, @"\bGameObject\b", RegexOptions.CultureInvariant);

            var paramChanged = false;
            if (del.Success)
            {
                // DelegateContext Context → VariableContext Context[, GameObject Object]
                var rest = parameters[del.Length..];
                newParams = "VariableContext " + ctxName +
                            (needsObject && !hasGameObjectParam ? ", GameObject Object" : "") +
                            rest;
                paramChanged = true;
            }
            else if (needsObject && !hasGameObjectParam && varCtx.Success)
            {
                // Already VariableContext but still uses Target/Pronouns — add GameObject Object.
                var rest = parameters[varCtx.Length..];
                newParams = "VariableContext " + ctxName + ", GameObject Object" + rest;
                paramChanged = true;
            }

            string? newBody = body;
            if (needsObject && body is not null && ctxName is not null)
            {
                newBody = RewriteBody(body, ctxName);
                bodyRewrite = !string.Equals(newBody, body, StringComparison.Ordinal);
            }

            if (!attrChanged && !paramChanged && !bodyRewrite)
                continue;

            sb.Append(content, last, m.Index - last);
            sb.Append(newAttr);
            sb.Append(between);
            sb.Append(sigMods);
            sb.Append(ret);
            sb.Append(' ');
            sb.Append(name);
            sb.Append('(');
            sb.Append(newParams);
            sb.Append(')');

            if (body is not null && bodyStart >= 0)
            {
                // Emit up through opening of body, then new body, then leave last at bodyEnd.
                sb.Append(content, m.Index + m.Length, bodyStart - (m.Index + m.Length));
                sb.Append(newBody);
                last = bodyEnd;
            }
            else
            {
                last = m.Index + m.Length;
            }

            if (attrChanged) attrEdits++;
            if (paramChanged || bodyRewrite) sigEdits++;
        }

        if (attrEdits + sigEdits == 0)
            return (content, 0, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), attrEdits, sigEdits);
    }

    static string RewriteAttribute(string attrName, string attrTail, out bool changed)
    {
        changed = false;
        if (!attrName.Equals("VariableObjectReplacer", StringComparison.Ordinal))
            return "[" + attrName + attrTail + "]";

        changed = true;
        // attrTail is everything after the attribute name inside [...] — e.g. "" or "(…)" or " (…)"
        var trimmed = attrTail.Trim();
        if (trimmed.Length == 0)
            return "[VariableReplacer(Capitalization = true)]";

        if (!trimmed.StartsWith('(') || !trimmed.EndsWith(')'))
            return "[VariableReplacer(Capitalization = true)]";

        var inner = trimmed[1..^1].Trim();
        if (inner.Length == 0)
            return "[VariableReplacer(Capitalization = true)]";

        if (inner.Contains("Capitalization", StringComparison.Ordinal))
            return "[VariableReplacer(" + inner + ")]";

        return "[VariableReplacer(" + inner + ", Capitalization = true)]";
    }

    static bool UsesContextMember(string body, string ctxName, string member) =>
        Regex.IsMatch(
            body,
            @"\b" + Regex.Escape(ctxName) + @"\." + Regex.Escape(member) + @"\b",
            RegexOptions.CultureInvariant);

    static string RewriteBody(string body, string ctxName)
    {
        var escaped = Regex.Escape(ctxName);
        // Target / Pronouns — Object is the typed second arg (vanilla GameObjectReplacers).
        body = Regex.Replace(
            body,
            @"\b" + escaped + @"\.Target\b",
            "Object",
            RegexOptions.CultureInvariant);
        body = Regex.Replace(
            body,
            @"\b" + escaped + @"\.Pronouns\b",
            "Object.GetPronounProvider()",
            RegexOptions.CultureInvariant);
        return body;
    }
}
