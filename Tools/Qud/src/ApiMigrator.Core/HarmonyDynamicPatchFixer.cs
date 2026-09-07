using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Converts <c>[HarmonyPatch(typeof(RemovedType)…)]</c> (and string type-name forms) into
/// Harmony <c>Prepare</c> + <c>TargetMethod</c> that resolve via
/// <c>AccessTools.TypeByName</c>. Missing types then skip at PatchAll instead of CS0246 /
/// a Harmony exception. Catalog: <see cref="RemovedGameApiCatalog"/>.
/// </summary>
public static class HarmonyDynamicPatchFixer
{
    public const string FixRuleName =
        "HarmonyPatch typeof(removed) → Prepare/TargetMethod (AccessTools.TypeByName)";

    static readonly Regex HarmonyPatchOpen = new(
        @"\[HarmonyPatch\s*\(",
        RegexOptions.Compiled);

    static readonly Regex Typeof = new(
        @"typeof\s*\(\s*(?<t>[\w.]+)\s*\)",
        RegexOptions.Compiled);

    static readonly Regex StringLit = new(
        @"""(?<s>(?:[^""\\]|\\.)*)""",
        RegexOptions.Compiled);

    static readonly Regex Nameof = new(
        @"nameof\s*\(\s*(?<t>[\w.]+)\s*\)",
        RegexOptions.Compiled);

    static readonly Regex HasTargetMethod = new(
        @"\bstatic\s+(?:MethodBase|IEnumerable\s*<\s*MethodBase\s*>)\s+TargetMethods?\s*\(",
        RegexOptions.Compiled);

    static readonly Regex HasPrepare = new(
        @"\bstatic\s+bool\s+Prepare\s*\(",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) ||
            content.IndexOf("HarmonyPatch", StringComparison.Ordinal) < 0)
            return (content, 0);

        RemovedGameApiCatalog.Load();

        var sites = FindClassPatches(content);
        if (sites.Count == 0)
            return (content, 0);

        sites.Sort((a, b) => b.ClassOpen.CompareTo(a.ClassOpen));
        var working = content;
        var edits = 0;

        foreach (var site in sites)
        {
            if (site.ClassOpen < 0 || site.ClassClose < 0 || site.AttrStart < 0)
                continue;
            if (site.ClassOpen >= working.Length || site.ClassClose >= working.Length)
                continue;

            var body = working.Substring(site.ClassOpen + 1, site.ClassClose - site.ClassOpen - 1);
            var alreadyDynamic = HasTargetMethod.IsMatch(body);
            var hasPrepare = HasPrepare.IsMatch(body);

            var methodName = site.MethodName;
            if (string.IsNullOrEmpty(methodName))
                methodName = InferMethodNameFromBody(body);
            if (string.IsNullOrEmpty(methodName))
                continue;

            var typeExpr = site.PreferredFullName;
            var indent = DetectIndent(working, site.ClassOpen + 1);
            var nl = working.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";

            // Rewrite leading HarmonyPatch(typeof/string) attributes to bare [HarmonyPatch].
            var attrBlock = working[site.AttrStart..site.ClassKeyword];
            var newAttrBlock = RewriteAttributeBlock(attrBlock);
            if (newAttrBlock is null)
                continue;

            var insert = "";
            if (!alreadyDynamic)
            {
                insert = nl + indent + "static bool Prepare() => TargetMethod() != null;" + nl + nl +
                         indent + "static MethodBase TargetMethod()" + nl +
                         indent + "{" + nl +
                         indent + "    var t = AccessTools.TypeByName(\"" + typeExpr + "\");" + nl +
                         indent + "    return t == null ? null : AccessTools.Method(t, \"" + methodName + "\"" +
                         (string.IsNullOrEmpty(site.TypeArrayLiteral) ? "" : ", " + site.TypeArrayLiteral) +
                         ");" + nl +
                         indent + "}" + nl;
            }
            else if (!hasPrepare)
            {
                insert = nl + indent + "static bool Prepare() => TargetMethod() != null;" + nl;
            }

            working = working[..site.AttrStart] + newAttrBlock +
                      working[site.ClassKeyword..(site.ClassOpen + 1)] +
                      insert +
                      working[(site.ClassOpen + 1)..];
            edits++;
        }

        if (edits == 0)
            return (working, 0);

        var (withUsings, _) = UsingInserter.EnsureUsings(working, new[] { "HarmonyLib", "System.Reflection" });
        return (withUsings, edits);
    }

    sealed class PatchSite
    {
        public int AttrStart;
        public int ClassKeyword;
        public int ClassOpen;
        public int ClassClose;
        public string PreferredFullName = "";
        public string MethodName = "";
        public string TypeArrayLiteral = "";
        public List<string> RemovedTypeTokens { get; } = new();
    }

    static List<PatchSite> FindClassPatches(string content)
    {
        var result = new List<PatchSite>();
        foreach (Match m in HarmonyPatchOpen.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var parenOpen = m.Index + m.Length - 1;
            if (!CsText.TryFindMatchingParen(content, parenOpen, out var parenClose))
                continue;
            var bracketClose = content.IndexOf(']', parenClose);
            if (bracketClose < 0) continue;

            var args = content[(parenOpen + 1)..parenClose];
            var removed = new List<string>();
            string? preferred = null;
            foreach (Match t in Typeof.Matches(args))
            {
                var token = t.Groups["t"].Value;
                if (!RemovedGameApiCatalog.TryGet(token, out var entry))
                    continue;
                removed.Add(token);
                preferred ??= RemovedGameApiCatalog.PreferredFullName(entry);
            }

            if (removed.Count == 0)
            {
                foreach (Match s in StringLit.Matches(args))
                {
                    var token = Regex.Unescape(s.Groups["s"].Value);
                    if (!RemovedGameApiCatalog.TryGet(token, out var entry))
                        continue;
                    removed.Add(token);
                    preferred ??= RemovedGameApiCatalog.PreferredFullName(entry);
                }
            }

            if (removed.Count == 0 || preferred is null)
                continue;

            if (args.IndexOf("MethodType", StringComparison.Ordinal) >= 0)
                continue;

            if (!TryFindClassAfterAttribute(content, bracketClose, out var classKw, out var classOpen, out var classClose))
                continue;

            var attrStart = FindAttributeClusterStart(content, m.Index);

            var methodName = ExtractMethodName(args, removed);
            var typeArray = ExtractTypeArrayLiteral(args);

            // One site per class (first HarmonyPatch that mentions a removed type).
            if (result.Any(s => s.ClassOpen == classOpen))
                continue;

            result.Add(new PatchSite
            {
                AttrStart = attrStart,
                ClassKeyword = classKw,
                ClassOpen = classOpen,
                ClassClose = classClose,
                PreferredFullName = preferred,
                MethodName = methodName,
                TypeArrayLiteral = typeArray,
            });
            result[^1].RemovedTypeTokens.AddRange(removed);
        }
        return result;
    }

    static string ExtractMethodName(string args, List<string> removedTokens)
    {
        foreach (Match n in Nameof.Matches(args))
        {
            var token = n.Groups["t"].Value;
            var simple = RemovedGameApiCatalog.SimpleName(token);
            if (removedTokens.Any(t => simple.Equals(RemovedGameApiCatalog.SimpleName(t), StringComparison.Ordinal)))
                continue;
            return simple;
        }

        var strings = StringLit.Matches(args);
        foreach (Match s in strings)
        {
            var v = Regex.Unescape(s.Groups["s"].Value);
            if (RemovedGameApiCatalog.IsRemovedTypeToken(v) || v.Contains('.', StringComparison.Ordinal))
                continue;
            if (v.Length > 0 && (char.IsLetter(v[0]) || v[0] == '_'))
                return v;
        }
        return "";
    }

    static string ExtractTypeArrayLiteral(string args)
    {
        var i = args.IndexOf("new Type[]", StringComparison.Ordinal);
        if (i < 0) i = args.IndexOf("new[]", StringComparison.Ordinal);
        if (i < 0) return "";
        var brace = args.IndexOf('{', i);
        if (brace < 0) return "";
        if (!CsText.TryFindMatchingBrace(args, brace, out var close))
            return "";
        var inner = args[brace..(close + 1)];
        foreach (Match t in Typeof.Matches(inner))
        {
            if (RemovedGameApiCatalog.IsRemovedTypeToken(t.Groups["t"].Value))
                return "";
        }
        return "new Type[] " + inner;
    }

    static string? RewriteAttributeBlock(string attrBlock)
    {
        var working = attrBlock;
        var matches = HarmonyPatchOpen.Matches(working).Cast<Match>().ToList();
        for (var k = matches.Count - 1; k >= 0; k--)
        {
            var m = matches[k];
            var parenOpen = m.Index + m.Length - 1;
            if (!CsText.TryFindMatchingParen(working, parenOpen, out var parenClose))
                continue;
            var args = working[(parenOpen + 1)..parenClose];
            var mentionsRemoved = Typeof.Matches(args).Cast<Match>()
                    .Any(t => RemovedGameApiCatalog.IsRemovedTypeToken(t.Groups["t"].Value)) ||
                StringLit.Matches(args).Cast<Match>()
                    .Any(s => RemovedGameApiCatalog.IsRemovedTypeToken(Regex.Unescape(s.Groups["s"].Value)));
            if (!mentionsRemoved)
                continue;

            var bracketClose = working.IndexOf(']', parenClose);
            if (bracketClose < 0) continue;
            working = working[..m.Index] + "[HarmonyPatch]" + working[(bracketClose + 1)..];
        }
        return working;
    }

    static string InferMethodNameFromBody(string body)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in HarmonyPatchOpen.Matches(body))
        {
            var parenOpen = m.Index + m.Length - 1;
            if (!CsText.TryFindMatchingParen(body, parenOpen, out var parenClose))
                continue;
            var args = body[(parenOpen + 1)..parenClose];
            var n = ExtractMethodName(args, new List<string>());
            if (!string.IsNullOrEmpty(n))
                names.Add(n);
        }
        return names.Count == 1 ? names.First() : "";
    }

    static bool TryFindClassAfterAttribute(
        string content, int attrEnd,
        out int classKeyword, out int classOpen, out int classClose)
    {
        classKeyword = -1;
        classOpen = -1;
        classClose = -1;
        var i = attrEnd + 1;
        i = CsText.SkipWsAndComments(content, i);
        while (i < content.Length && content[i] == '[')
        {
            var close = content.IndexOf(']', i);
            if (close < 0) return false;
            i = CsText.SkipWsAndComments(content, close + 1);
        }

        while (i < content.Length)
        {
            i = CsText.SkipWsAndComments(content, i);
            if (StartsWithKeyword(content, i, "public") || StartsWithKeyword(content, i, "private") ||
                StartsWithKeyword(content, i, "internal") || StartsWithKeyword(content, i, "protected") ||
                StartsWithKeyword(content, i, "static") || StartsWithKeyword(content, i, "sealed") ||
                StartsWithKeyword(content, i, "partial") || StartsWithKeyword(content, i, "abstract") ||
                StartsWithKeyword(content, i, "unsafe"))
            {
                while (i < content.Length && (char.IsLetter(content[i]) || content[i] == '_')) i++;
                continue;
            }
            break;
        }

        i = CsText.SkipWsAndComments(content, i);
        if (!StartsWithKeyword(content, i, "class") && !StartsWithKeyword(content, i, "struct"))
            return false;
        classKeyword = i;
        while (i < content.Length && content[i] != '{' && content[i] != ';') i++;
        if (i >= content.Length || content[i] != '{')
            return false;
        classOpen = i;
        return CsText.TryFindMatchingBrace(content, classOpen, out classClose);
    }

    static bool StartsWithKeyword(string content, int i, string kw)
    {
        if (i + kw.Length > content.Length) return false;
        if (string.Compare(content, i, kw, 0, kw.Length, StringComparison.Ordinal) != 0)
            return false;
        var after = i + kw.Length;
        if (after < content.Length && (char.IsLetterOrDigit(content[after]) || content[after] == '_'))
            return false;
        return true;
    }

    static int FindAttributeClusterStart(string content, int patchAttrStart)
    {
        var start = patchAttrStart;
        var i = patchAttrStart;
        while (i > 0)
        {
            i--;
            while (i > 0 && char.IsWhiteSpace(content[i])) i--;
            if (content[i] != ']')
                break;
            var open = content.LastIndexOf('[', i);
            if (open < 0) break;
            start = open;
            i = open;
        }
        return start;
    }

    static string DetectIndent(string content, int afterOpenBrace)
    {
        var i = afterOpenBrace;
        while (i < content.Length && (content[i] == '\r' || content[i] == '\n')) i++;
        var start = i;
        while (i < content.Length && (content[i] == ' ' || content[i] == '\t')) i++;
        if (i > start)
            return content[start..i];
        return "    ";
    }
}
