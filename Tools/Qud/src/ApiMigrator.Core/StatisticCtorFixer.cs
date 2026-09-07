using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// CS1729: removed 5-arg <c>new Statistic(...)</c> → <c>new Statistic(blueprint)</c>
/// plus a merged <c>Statistics.xml</c> overlay (<see cref="XRL.Blueprints.StatisticBlueprint"/>).
/// </summary>
public static class StatisticCtorFixer
{
    public const string FixRuleName =
        "new Statistic(5 args) → StatisticBlueprint + Statistics.xml";

    static readonly Regex NewStat = new(
        @"\bnew\s+Statistic\s*(?<paren>\()",
        RegexOptions.Compiled);

    public static SidecarModFixResult FixMod(string modRoot, IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new SidecarModFixResult();
        if (string.IsNullOrEmpty(modRoot) || pathToContent == null)
            return result;

        var xmlKids = new List<(string Name, string InnerXml)>();
        var seenXml = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("new Statistic", StringComparison.Ordinal) < 0)
                continue;

            var (next, edits, stats) = FixContent(content);
            if (edits == 0)
                continue;

            foreach (var s in stats)
            {
                if (!seenXml.Add(s.Name)) continue;
                xmlKids.Add((s.Name, s.InnerXml));
            }

            var (withUsing, _) = UsingInserter.EnsureUsings(next, new[] { "XRL.Blueprints" });
            result.UpdatedContents[path] = withUsing;
            result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleName, Count = edits }));
        }

        if (xmlKids.Count == 0)
            return result;

        var xmlPath = Path.Combine(modRoot, "Statistics.xml");
        string existing = "";
        if (pathToContent.TryGetValue(xmlPath, out var fromMap))
            existing = fromMap;
        else if (File.Exists(xmlPath))
            existing = File.ReadAllText(xmlPath);

        result.SidecarFiles[xmlPath] =
            XmlOverlayMerger.MergeNamedChildren(existing, "statistics", "statistic", xmlKids);
        result.Fixes.Add((xmlPath, new AppliedFix
        {
            RuleName = FixRuleName + " (write Statistics.xml)",
            Count = xmlKids.Count,
        }));
        return result;
    }

    public static (string Content, int EditCount, List<(string Name, string InnerXml)> Stats) FixContent(string content)
    {
        var stats = new List<(string Name, string InnerXml)>();
        if (string.IsNullOrEmpty(content))
            return (content, 0, stats);

        var sb = new StringBuilder(content.Length + 128);
        var last = 0;
        var edits = 0;

        foreach (Match m in NewStat.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count != 5)
                continue;

            var a0 = args[0].Expression.Trim();
            var a1 = args[1].Expression.Trim();
            var a2 = args[2].Expression.Trim();
            var a3 = args[3].Expression.Trim();
            var a4 = args[4].Expression.Trim();
            if (!TryUnquote(a0, out var name) || string.IsNullOrEmpty(name))
                continue;
            if (!IsSafeIdent(name))
                continue;

            string? display = null;
            string minExpr, maxExpr, valueExpr, ownerExpr;
            // Form2: (name, displayName, min, max, value)
            // Form1: (name, min, max, value, owner)
            if (TryUnquote(a1, out var disp))
            {
                display = disp;
                minExpr = a2;
                maxExpr = a3;
                valueExpr = a4;
                ownerExpr = "";
            }
            else if (LooksNumeric(a1) && LooksNumeric(a2))
            {
                minExpr = a1;
                maxExpr = a2;
                valueExpr = a3;
                ownerExpr = a4;
            }
            else
            {
                continue;
            }

            var bpVar = "__statBp_" + SanitizeIdent(name);
            var bpInit = new StringBuilder();
            bpInit.Append("new StatisticBlueprint { Name = \"").Append(EscapeCs(name)).Append('"');
            if (TryIntLit(minExpr, out _))
                bpInit.Append(", Minimum = ").Append(minExpr.Trim());
            if (TryIntLit(maxExpr, out _))
                bpInit.Append(", Maximum = ").Append(maxExpr.Trim());
            if (display != null)
                bpInit.Append(", DisplayName = \"").Append(EscapeCs(display)).Append('"');
            bpInit.Append(" }");

            var ctor = new StringBuilder();
            ctor.Append("new Statistic(StatisticBlueprint.TryGet(\"")
                .Append(EscapeCs(name))
                .Append("\", out var ")
                .Append(bpVar)
                .Append(") && ")
                .Append(bpVar)
                .Append(" != null ? ")
                .Append(bpVar)
                .Append(" : ")
                .Append(bpInit)
                .Append(") { BaseValue = ")
                .Append(valueExpr);
            if (!string.IsNullOrEmpty(ownerExpr))
                ctor.Append(", Owner = ").Append(ownerExpr);
            ctor.Append(" }");

            sb.Append(content, last, m.Index - last);
            sb.Append(ctor);
            last = close + 1;
            edits++;

            var inner = new StringBuilder();
            if (display != null)
                inner.Append("    <displayName>").Append(XmlOverlayMerger.XmlEscape(display)).Append("</displayName>\n");
            if (TryIntLit(minExpr, out var minLit))
                inner.Append("    <minimum>").Append(minLit).Append("</minimum>\n");
            if (TryIntLit(maxExpr, out var maxLit))
                inner.Append("    <maximum>").Append(maxLit).Append("</maximum>\n");
            stats.Add((name, inner.ToString()));
        }

        if (edits == 0)
            return (content, 0, stats);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits, stats);
    }

    static bool TryUnquote(string expr, out string lit)
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

    static bool LooksNumeric(string expr)
    {
        var t = expr.Trim();
        if (TryIntLit(t, out _)) return true;
        // simple calls like maximumPsiCharge() still OK as value, not as min for form-detect
        return false;
    }

    static bool TryIntLit(string expr, out string lit)
    {
        lit = "";
        var t = expr.Trim();
        if (!Regex.IsMatch(t, @"^-?\d+$")) return false;
        lit = t;
        return true;
    }

    static bool IsSafeIdent(string name) =>
        Regex.IsMatch(name, @"^[A-Za-z_][A-Za-z0-9_]*$");

    static string SanitizeIdent(string name)
    {
        var sb = new StringBuilder(name.Length);
        foreach (var c in name)
        {
            if (char.IsLetterOrDigit(c) || c == '_')
                sb.Append(c);
        }
        return sb.Length == 0 ? "Stat" : sb.ToString();
    }

    static string EscapeCs(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");
}
