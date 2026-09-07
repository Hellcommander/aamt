using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Confidence-gated obsolete string <c>IInventoryActionsEvent.AddAction(...)</c>
/// → <c>AddAction(new InventoryAction { ... })</c> when args map to known fields.
/// Also strips CS8209 <c>_ = E.AddAction(...)</c> discards (AddAction returns void).
/// Static literal actions are handled by <see cref="InventoryActionsXmlFixer"/> (AddXMLAction + XML)
/// when that pre-pass runs; this fixer covers remaining dynamic calls.
/// Never rewrites <c>AddAction(new InventoryAction …)</c>.
/// Never rewrites mod-defined <c>AddAction</c> (e.g. vendor-action events) — only game
/// inventory-action receivers (<see cref="IsInventoryAddActionCall"/>).
/// </summary>
public static class AddActionFixer
{
    public const string FixRuleName =
        "AddAction(string,…) → AddAction(new InventoryAction { … }) [mapped args]";

    public const string DiscardFixRuleName =
        "_ = AddAction/AddXMLAction → statement (void discard CS8209)";

    /// <summary>Game inventory-action event / collector types whose string AddAction is obsolete.</summary>
    internal static readonly HashSet<string> InventoryEventTypeNames = new(StringComparer.Ordinal)
    {
        "IInventoryActionsEvent",
        "GetInventoryActionsEvent",
        "GetInventoryActionsAlwaysEvent",
        "OwnerGetInventoryActionsEvent",
        "EventParameterGetInventoryActions",
    };

    static readonly HashSet<string> TypeLookupSkip = new(StringComparer.Ordinal)
    {
        "var", "ref", "out", "in", "new", "return", "await", "using", "is", "as",
        "throw", "if", "else", "for", "foreach", "while", "switch", "case", "lock",
        "class", "struct", "enum", "interface", "record", "delegate", "const",
        "static", "public", "private", "protected", "internal", "this", "base",
        "true", "false", "null", "void",
    };

    // Receiver.AddAction( — first arg string literal or Name:
    internal static readonly Regex CallSite = new(
        @"\.(?<name>AddAction)\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex IdentTypeDecl = new(
        @"\b(?<type>[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\s+(?<id>[A-Za-z_][\w]*)\s*[,\)=\{\;]",
        RegexOptions.Compiled);

    static readonly HashSet<string> KnownFields = new(StringComparer.Ordinal)
    {
        "Name", "Display", "Command", "PreferToHighlight", "Key",
        "Default", "Priority", "FireOnActor",
        "WorksAtDistance", "WorksTelekinetically", "WorksTelepathically",
        "AsMinEvent", "FireOn", "ReturnToModernUI",
    };

    // Obsolete AddAction had Override; InventoryAction has no Override field — omit.
    static readonly HashSet<string> SkipFields = new(StringComparer.OrdinalIgnoreCase)
    {
        "Override",
    };

    static readonly string[] ModernPositional =
    {
        "Name", "Display", "Command", "PreferToHighlight", "Key",
        "FireOnActor", "Default", "Priority", "Override",
        "WorksAtDistance", "WorksTelekinetically", "WorksTelepathically",
        "AsMinEvent", "FireOn", "ReturnToModernUI",
    };

    // EventParameterGetInventoryActions obsolete: Name, Key, FireOnActor, Display, Command, …
    static readonly string[] ClassicPositional =
    {
        "Name", "Key", "FireOnActor", "Display", "Command",
        "PreferToHighlight", "Default", "Priority", "Override",
        "WorksAtDistance", "WorksTelekinetically", "WorksTelepathically",
        "AsMinEvent", "FireOn",
    };

    public static (string Content, int EditCount) Fix(string content)
    {
        var (next, n, _) = Rewrite(content, preferXml: false, resolveCommandConsts: false);
        return (next, n);
    }

    /// <summary>
    /// Rewrite string AddAction overloads. When <paramref name="preferXml"/>, literal Name/Display/Command/Key
    /// become <c>AddXMLAction("Name")</c> and are collected for InventoryActions.xml.
    /// </summary>
    public static (string Content, int EditCount, List<InventoryXmlAction> XmlActions) Rewrite(
        string content, bool preferXml, bool resolveCommandConsts)
    {
        var xml = new List<InventoryXmlAction>();
        if (string.IsNullOrEmpty(content))
            return (content, 0, xml);

        var matches = CallSite.Matches(content);
        if (matches.Count == 0)
        {
            var (onlyDiscard, dN) = StripVoidDiscards(content);
            return (onlyDiscard, dN, xml);
        }

        var sb = new StringBuilder(content.Length + 128);
        var last = 0;
        var edits = 0;

        foreach (Match m in matches)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            if (!IsInventoryAddActionCall(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count == 0)
                continue;

            var firstExpr = args[0].Expression.Trim();
            if (firstExpr.StartsWith("new ", StringComparison.Ordinal) ||
                firstExpr.Contains("InventoryAction", StringComparison.Ordinal))
                continue;

            if (args[0].Name is null)
            {
                if (!LooksLikeStringExpr(firstExpr))
                    continue;
            }
            else if (!string.Equals(args[0].Name, "Name", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (!TryMapFields(args, out var fields))
                continue;

            if (resolveCommandConsts)
                ResolveCommandConst(content, fields);

            string replacement;
            if (preferXml && TryBuildXmlAction(fields, out var xmlAction))
            {
                xml.Add(xmlAction);
                replacement = $"AddXMLAction(\"{EscapeCs(xmlAction.Name)}\")";
            }
            else
            {
                replacement = BuildInventoryActionCall(fields);
            }

            var callDot = m.Index;
            var spanStart = callDot;
            if (TryFindVoidDiscardStart(content, callDot, out var discardStart))
                spanStart = discardStart;

            sb.Append(content, last, spanStart - last);
            if (spanStart < callDot)
            {
                var eq = content.IndexOf('=', spanStart);
                var recvStart = eq >= 0 ? eq + 1 : callDot;
                while (recvStart < callDot && char.IsWhiteSpace(content[recvStart]))
                    recvStart++;
                sb.Append(content, recvStart, callDot - recvStart);
            }
            sb.Append('.');
            sb.Append(replacement);
            last = close + 1;
            edits++;
        }

        if (edits == 0)
        {
            var (onlyDiscard, dN) = StripVoidDiscards(content);
            return (onlyDiscard, dN, xml);
        }

        sb.Append(content, last, content.Length - last);
        var next = sb.ToString();
        var (stripped, discardN) = StripVoidDiscards(next);
        return (stripped, edits + discardN, xml);
    }

    /// <summary>
    /// CS8209: <c>_ = recv.AddAction(...)</c> / <c>_ = recv.AddXMLAction(...)</c> — both return void.
    /// </summary>
    public static (string Content, int EditCount) StripVoidDiscards(string content)
    {
        if (string.IsNullOrEmpty(content) || content.IndexOf("_ =", StringComparison.Ordinal) < 0)
            return (content, 0);

        var rx = new Regex(
            @"(?<pre>(?:^|[;\{\}])\s*)_\s*=\s*(?=[\w\.]*\.(?:AddAction|AddXMLAction)\s*\()",
            RegexOptions.Compiled | RegexOptions.Multiline);

        var n = 0;
        var next = rx.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            var addDot = content.IndexOf(".AddAction", m.Index, StringComparison.Ordinal);
            var xmlDot = content.IndexOf(".AddXMLAction", m.Index, StringComparison.Ordinal);
            if (xmlDot >= 0 && (addDot < 0 || xmlDot < addDot))
            {
                n++;
                return m.Groups["pre"].Value;
            }
            if (addDot >= 0)
            {
                var paren = content.IndexOf('(', addDot);
                if (paren > 0 && paren - addDot < 24)
                {
                    var invAt = content.IndexOf("new InventoryAction", paren, StringComparison.Ordinal);
                    if (invAt >= 0 && invAt < paren + 48)
                    {
                        n++;
                        return m.Groups["pre"].Value;
                    }
                }
                if (!IsInventoryAddActionCall(content, addDot))
                    return m.Value;
            }
            n++;
            return m.Groups["pre"].Value;
        });
        return (next, n);
    }

    /// <summary>
    /// True when <c>.AddAction(</c> at <paramref name="dotIndex"/> is the game inventory API
    /// (typed inventory-event receiver, or untyped in a file that mentions those types).
    /// False for mod-defined vendor/custom <c>AddAction</c> — do not rewrite or dump-flag those.
    /// </summary>
    public static bool IsInventoryAddActionCall(string content, int dotIndex)
    {
        if (string.IsNullOrEmpty(content) || dotIndex < 0 || dotIndex >= content.Length)
            return false;
        if (content[dotIndex] != '.')
            return false;

        if (!TryGetReceiverIdent(content, dotIndex, out var recv))
            return FileMentionsInventoryEventType(content);

        if (string.Equals(recv, "this", StringComparison.Ordinal))
            return FileMentionsInventoryEventType(content);

        if (TryFindIdentTypeBefore(content, dotIndex, recv, out var type))
            return LooksLikeInventoryEventType(type);

        return FileMentionsInventoryEventType(content);
    }

    internal static bool FileMentionsInventoryEventType(string content)
    {
        foreach (var t in InventoryEventTypeNames)
        {
            if (content.IndexOf(t, StringComparison.Ordinal) >= 0)
                return true;
        }
        return false;
    }

    internal static bool LooksLikeInventoryEventType(string type)
    {
        if (string.IsNullOrEmpty(type)) return false;
        var simple = type;
        var dot = type.LastIndexOf('.');
        if (dot >= 0)
            simple = type[(dot + 1)..];
        return InventoryEventTypeNames.Contains(simple);
    }

    static bool TryGetReceiverIdent(string content, int dotIndex, out string ident)
    {
        ident = "";
        var i = dotIndex - 1;
        while (i >= 0 && char.IsWhiteSpace(content[i])) i--;
        var end = i + 1;
        while (i >= 0 && (char.IsLetterOrDigit(content[i]) || content[i] == '_'))
            i--;
        if (end <= i + 1) return false;
        ident = content[(i + 1)..end];
        return ident.Length > 0;
    }

    static bool TryFindIdentTypeBefore(string content, int fromIndex, string ident, out string type)
    {
        type = "";
        var start = Math.Max(0, fromIndex - 5000);
        var window = content[start..fromIndex];
        Match? best = null;
        foreach (Match m in IdentTypeDecl.Matches(window))
        {
            if (!string.Equals(m.Groups["id"].Value, ident, StringComparison.Ordinal))
                continue;
            var typeName = m.Groups["type"].Value;
            if (TypeLookupSkip.Contains(typeName))
                continue;
            var abs = start + m.Index;
            if (HitFilter.IsInsideComment(content, abs) ||
                HitFilter.IsInsideStringLiteral(content, abs))
                continue;
            best = m;
        }
        if (best is null) return false;
        type = best.Groups["type"].Value;
        return type.Length > 0;
    }

    internal static bool TryMapFields(List<CallArgParser.Arg> args, out List<(string Name, string Expr)> fields)
    {
        fields = new List<(string, string)>();
        var used = new HashSet<string>(StringComparer.Ordinal);

        var classic = false;
        if (args.Count >= 2 && args[1].Name is null)
        {
            var second = args[1].Expression.Trim();
            if (LooksLikeCharExpr(second))
                classic = true;
            else if (!LooksLikeStringExpr(second) && args[1].Name is null)
                return false;
        }

        var positional = classic ? ClassicPositional : ModernPositional;
        var posIndex = 0;

        foreach (var a in args)
        {
            string field;
            string expr = a.Expression.Trim();

            if (a.Name is not null)
            {
                field = NormalizeFieldName(a.Name);
                if (SkipFields.Contains(field))
                    continue;
                if (!KnownFields.Contains(field))
                    return false;
            }
            else
            {
                while (posIndex < positional.Length && used.Contains(positional[posIndex]))
                    posIndex++;
                if (posIndex >= positional.Length)
                    return false;
                field = positional[posIndex++];
                if (SkipFields.Contains(field))
                    continue;
            }

            if (string.IsNullOrEmpty(expr))
                return false;

            if (!used.Add(field))
                return false;

            fields.Add((field, expr));
        }

        if (!fields.Any(f => f.Name == "Name"))
            return false;

        if (classic && !fields.Any(f => f.Name == "Key"))
            return false;

        return fields.Count >= 1;
    }

    static string NormalizeFieldName(string name)
    {
        foreach (var f in KnownFields)
        {
            if (string.Equals(f, name, StringComparison.OrdinalIgnoreCase))
                return f;
        }
        return name;
    }

    internal static string BuildInventoryActionCall(List<(string Name, string Expr)> fields)
    {
        var sb = new StringBuilder();
        sb.Append("AddAction(new InventoryAction { ");
        for (var i = 0; i < fields.Count; i++)
        {
            if (i > 0) sb.Append(", ");
            sb.Append(fields[i].Name);
            sb.Append(" = ");
            sb.Append(fields[i].Expr);
        }
        sb.Append(" })");
        return sb.ToString();
    }

    internal static bool LooksLikeStringExpr(string expr)
    {
        if (string.IsNullOrEmpty(expr)) return false;
        var t = expr.TrimStart();
        if (t.StartsWith("nameof(", StringComparison.Ordinal)) return true;
        if (t.StartsWith("\"")) return true;
        if (t.StartsWith("@\"")) return true;
        if (t.StartsWith("$\"")) return true;
        if (t.StartsWith("$@\"")) return true;
        return false;
    }

    internal static bool LooksLikeCharExpr(string expr)
    {
        var t = expr.Trim();
        return t.Length >= 3 && t[0] == '\'' && t[^1] == '\'';
    }

    internal static bool TryUnquoteString(string expr, out string lit)
    {
        lit = "";
        var e = expr.Trim();
        if (e.Length < 2 || e[0] != '"') return false;
        var i = 1;
        var sb = new StringBuilder();
        while (i < e.Length)
        {
            if (e[i] == '\\' && i + 1 < e.Length)
            {
                sb.Append(e[i + 1]);
                i += 2;
                continue;
            }
            if (e[i] == '"')
            {
                if (i != e.Length - 1) return false;
                lit = sb.ToString();
                return true;
            }
            sb.Append(e[i]);
            i++;
        }
        return false;
    }

    static bool TryUnquoteChar(string expr, out string ch)
    {
        ch = "";
        var t = expr.Trim();
        if (t.Length < 3 || t[0] != '\'' || t[^1] != '\'') return false;
        ch = t[1..^1];
        if (ch.StartsWith("\\", StringComparison.Ordinal) && ch.Length == 2)
            ch = ch[1].ToString();
        return ch.Length == 1;
    }

    static bool IsSimpleIdent(string expr) =>
        Regex.IsMatch(expr.Trim(), @"^[A-Za-z_][A-Za-z0-9_]*$");

    static void ResolveCommandConst(string content, List<(string Name, string Expr)> fields)
    {
        for (var i = 0; i < fields.Count; i++)
        {
            if (fields[i].Name != "Command") continue;
            if (LooksLikeStringExpr(fields[i].Expr)) return;
            if (!IsSimpleIdent(fields[i].Expr)) return;
            var ident = fields[i].Expr.Trim();
            var rx = new Regex(
                $@"\b(?:const\s+)?string\s+{Regex.Escape(ident)}\s*=\s*""(?<v>(?:[^""\\]|\\.)*)""",
                RegexOptions.Compiled);
            var m = rx.Match(content);
            if (!m.Success) return;
            fields[i] = ("Command", "\"" + m.Groups["v"].Value + "\"");
            return;
        }
    }

    internal static bool TryBuildXmlAction(List<(string Name, string Expr)> fields, out InventoryXmlAction action)
    {
        action = new InventoryXmlAction();
        string? name = null, display = null, command = null, key = null;
        bool? fireOnActor = null, worksAtDistance = null, worksTelekinetically = null,
            worksTelepathically = null, returnToModernUi = null;
        string? defaultVal = null, priority = null;

        foreach (var (n, expr) in fields)
        {
            switch (n)
            {
                case "Name":
                    if (!TryUnquoteString(expr, out name)) return false;
                    break;
                case "Display":
                    if (!TryUnquoteString(expr, out display)) return false;
                    break;
                case "Command":
                    if (!TryUnquoteString(expr, out command)) return false;
                    break;
                case "Key":
                    if (!TryUnquoteChar(expr, out key)) return false;
                    break;
                case "FireOnActor":
                    if (!TryBoolLit(expr, out var fa)) return false;
                    fireOnActor = fa;
                    break;
                case "WorksAtDistance":
                    if (!TryBoolLit(expr, out var wad)) return false;
                    worksAtDistance = wad;
                    break;
                case "WorksTelekinetically":
                    if (!TryBoolLit(expr, out var wtk)) return false;
                    worksTelekinetically = wtk;
                    break;
                case "WorksTelepathically":
                    if (!TryBoolLit(expr, out var wtp)) return false;
                    worksTelepathically = wtp;
                    break;
                case "ReturnToModernUI":
                    if (!TryBoolLit(expr, out var rui)) return false;
                    returnToModernUi = rui;
                    break;
                case "Default":
                    if (!Regex.IsMatch(expr.Trim(), @"^-?\d+$")) return false;
                    defaultVal = expr.Trim();
                    break;
                case "Priority":
                    if (!Regex.IsMatch(expr.Trim(), @"^-?\d+$")) return false;
                    priority = expr.Trim();
                    break;
                case "PreferToHighlight":
                    if (expr.Trim() is "null") break;
                    return false;
                case "AsMinEvent":
                    if (!TryBoolLit(expr, out _)) return false;
                    break;
                case "FireOn":
                    if (expr.Trim() is "null") break;
                    return false;
                default:
                    return false;
            }
        }

        if (string.IsNullOrEmpty(name))
            return false;

        action = new InventoryXmlAction
        {
            Name = name,
            Display = display,
            Command = command,
            Key = key,
            FireOnActor = fireOnActor,
            WorksAtDistance = worksAtDistance,
            WorksTelekinetically = worksTelekinetically,
            WorksTelepathically = worksTelepathically,
            ReturnToModernUI = returnToModernUi,
            Default = defaultVal,
            Priority = priority,
        };
        return true;
    }

    static bool TryBoolLit(string expr, out bool value)
    {
        value = false;
        var t = expr.Trim();
        if (t == "true") { value = true; return true; }
        if (t == "false") { value = false; return true; }
        return false;
    }

    static string EscapeCs(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");

    /// <summary>
    /// If the call is <c>_ = recv.AddAction(</c>, return the index of <c>_</c>.
    /// Used so the replacement span can drop the void discard.
    /// </summary>
    internal static bool TryFindVoidDiscardStart(string content, int dotIndex, out int discardStart)
    {
        discardStart = -1;
        var i = dotIndex - 1;
        while (i >= 0 && (char.IsLetterOrDigit(content[i]) || content[i] is '_' or '.'))
            i--;
        while (i >= 0 && char.IsWhiteSpace(content[i])) i--;
        if (i < 0 || content[i] != '=') return false;
        i--;
        while (i >= 0 && char.IsWhiteSpace(content[i])) i--;
        if (i < 0 || content[i] != '_') return false;
        if (i > 0 && (char.IsLetterOrDigit(content[i - 1]) || content[i - 1] == '_'))
            return false;
        discardStart = i;
        return true;
    }
}

public sealed class InventoryXmlAction
{
    public string Name { get; set; } = "";
    public string? Display { get; set; }
    public string? Command { get; set; }
    public string? Key { get; set; }
    public bool? FireOnActor { get; set; }
    public bool? WorksAtDistance { get; set; }
    public bool? WorksTelekinetically { get; set; }
    public bool? WorksTelepathically { get; set; }
    public bool? ReturnToModernUI { get; set; }
    public string? Default { get; set; }
    public string? Priority { get; set; }

    public string ToInnerXml()
    {
        var sb = new StringBuilder();
        void El(string tag, string? val)
        {
            if (val is null) return;
            sb.Append("    <").Append(tag).Append('>')
                .Append(XmlOverlayMerger.XmlEscape(val))
                .Append("</").Append(tag).Append(">\n");
        }
        void ElBool(string tag, bool? val)
        {
            if (val is null) return;
            El(tag, val.Value ? "true" : "false");
        }

        El("display", Display);
        El("key", Key);
        El("command", Command);
        El("default", Default);
        El("priority", Priority);
        ElBool("fireOnActor", FireOnActor);
        ElBool("worksAtDistance", WorksAtDistance);
        ElBool("worksTelekinetically", WorksTelekinetically);
        ElBool("worksTelepathically", WorksTelepathically);
        ElBool("returnToModernUI", ReturnToModernUI);
        return sb.ToString();
    }
}
