using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// PreferXML: a mod's own <c>BaseLiquid.Drank</c> override → <c>XRL.Liquids.Parts.*OnDrink</c>
/// plus a Liquids.xml <c>&lt;part&gt;</c>. Static <c>Message.Compound("…"); return true;</c>
/// becomes vanilla <c>MessageOnDrink</c>. Vanilla liquid class names are left alone
/// (PreferHarmony / overlay parts).
/// </summary>
public static class LiquidDrankToPartFixer
{
    public const string FixRuleName =
        "BaseLiquid.Drank → Liquids.xml OnDrink part";

    static readonly HashSet<string> VanillaLiquidClasses = new(StringComparer.Ordinal)
    {
        "LiquidAcid", "LiquidAlgae", "LiquidAsphalt", "LiquidBlood", "LiquidBrainBrine",
        "LiquidCider", "LiquidCloning", "LiquidConvalessence", "LiquidGel", "LiquidGoo",
        "LiquidHoney", "LiquidInk", "LiquidLava", "LiquidNeutronFlux", "LiquidOil",
        "LiquidOoze", "LiquidProteanGunk", "LiquidPutrescence", "LiquidSalt", "LiquidSap",
        "LiquidSlime", "LiquidSludge", "LiquidSunSlag", "LiquidWater", "LiquidWax",
        "LiquidWine", "LiquidWarmStatic",
    };

    static readonly Regex ClassDecl = new(
        @"\b(?:public|internal|protected|private)?\s*(?:(?:abstract|sealed|partial|static)\s+)*class\s+(?<name>[A-Za-z_]\w*)\s*:\s*(?<bases>[^\{]+)",
        RegexOptions.Compiled);

    static readonly Regex DrankSig = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+bool\s+Drank\s*\(",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex StaticDrinkBody = new(
        @"^\s*Message\.Compound\s*\(\s*""(?<msg>(?:[^""\\]|\\.)*)""\s*\)\s*;\s*return\s+true\s*;\s*$",
        RegexOptions.Compiled | RegexOptions.Singleline);

    public static SidecarModFixResult FixMod(string modRoot, IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new SidecarModFixResult();
        if (string.IsNullOrEmpty(modRoot) || pathToContent == null)
            return result;

        var parts = new List<(string LiquidName, string InnerXml)>();
        var xmlPath = Path.Combine(modRoot, "Liquids.xml");

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("Drank", StringComparison.Ordinal) < 0)
                continue;

            var (next, edits, extracted) = FixContent(content);
            if (edits == 0)
                continue;

            parts.AddRange(extracted);
            result.UpdatedContents[path] = next;
            result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleName, Count = edits }));
        }

        if (parts.Count == 0)
            return result;

        string existing = "";
        if (pathToContent.TryGetValue(xmlPath, out var fromMap))
            existing = fromMap;
        else if (File.Exists(xmlPath))
            existing = File.ReadAllText(xmlPath);

        // Prefer sidecar already produced this run (LiquidCsToXmlFixer) if the caller
        // chained via workingMap; FixMod itself only sees pathToContent.
        var merged = existing;
        merged = XmlOverlayMerger.MergeNamedChildren(merged, "liquids", "liquid",
            parts.Select(p => (p.LiquidName, p.InnerXml)).ToList());
        foreach (var p in parts)
            merged = XmlOverlayMerger.MergeMissingInner(merged, "liquid", p.LiquidName, p.InnerXml);

        result.SidecarFiles[xmlPath] = merged;
        result.Fixes.Add((xmlPath, new AppliedFix
        {
            RuleName = FixRuleName + " (write Liquids.xml part)",
            Count = parts.Count,
        }));
        return result;
    }

    public static (string Content, int EditCount, List<(string LiquidName, string InnerXml)> Parts)
        FixContent(string content)
    {
        var parts = new List<(string LiquidName, string InnerXml)>();
        if (string.IsNullOrEmpty(content))
            return (content, 0, parts);

        var working = content;
        var edits = 0;

        foreach (Match cm in ClassDecl.Matches(content).Cast<Match>().Reverse())
        {
            if (HitFilter.IsInsideComment(working, cm.Index) ||
                HitFilter.IsInsideStringLiteral(working, cm.Index))
                continue;
            if (!Regex.IsMatch(cm.Groups["bases"].Value, @"\bBaseLiquid\b"))
                continue;

            var className = cm.Groups["name"].Value;
            if (VanillaLiquidClasses.Contains(className))
                continue;
            if (!InNamespace(working, cm.Index, "XRL.Liquids"))
                continue;

            var braceOpen = working.IndexOf('{', cm.Index + cm.Length - 1);
            if (braceOpen < 0) continue;
            if (!CsText.TryFindMatchingBrace(working, braceOpen, out var braceClose))
                continue;

            var body = working[(braceOpen + 1)..braceClose];
            var drank = DrankSig.Match(body);
            if (!drank.Success) continue;

            var sigAbs = braceOpen + 1 + drank.Index;
            var parenOpen = working.IndexOf('(', sigAbs);
            if (parenOpen < 0 || !CsText.TryFindMatchingParen(working, parenOpen, out var parenClose))
                continue;
            var paramList = working[(parenOpen + 1)..parenClose];
            if (paramList.IndexOf("LiquidVolume", StringComparison.Ordinal) < 0 ||
                paramList.IndexOf("GameObject", StringComparison.Ordinal) < 0)
                continue;

            var after = CsText.SkipWsAndComments(working, parenClose + 1);
            string methodText;
            int methodEnd;
            string drankBody;
            if (after < working.Length && working[after] == '{')
            {
                if (!CsText.TryFindMatchingBrace(working, after, out methodEnd))
                    continue;
                drankBody = working[(after + 1)..methodEnd];
                methodText = working[sigAbs..(methodEnd + 1)];
            }
            else if (after + 1 < working.Length && working[after] == '=' && working[after + 1] == '>')
            {
                var semi = working.IndexOf(';', after);
                if (semi < 0 || semi > braceClose) continue;
                methodEnd = semi;
                drankBody = working[(after + 2)..semi];
                methodText = working[sigAbs..(semi + 1)];
            }
            else
                continue;

            var partName = PartNameFromClass(className);
            if (working.IndexOf("class " + partName, StringComparison.Ordinal) >= 0)
                continue;

            var xmlName = LiquidCsToXmlFixer.LiquidXmlName(className, working[cm.Index..braceClose]);
            string innerXml;
            string? partClassSource = null;

            var trimmedBody = drankBody.Trim();
            var staticM = StaticDrinkBody.Match(trimmedBody);
            if (staticM.Success)
            {
                var msg = staticM.Groups["msg"].Value.Replace("\\\"", "\"").Replace("\\\\", "\\");
                innerXml = $"    <part Name=\"MessageOnDrink\" Message=\"{XmlOverlayMerger.XmlEscape(msg)}\" />\n";
            }
            else
            {
                partClassSource = BuildPartClass(partName, paramList, drankBody);
                innerXml = $"    <part Name=\"{XmlOverlayMerger.XmlEscape(partName)}\" Class=\"{XmlOverlayMerger.XmlEscape(partName)}\" />\n";
            }

            working = working[..sigAbs] + working[(methodEnd + 1)..];
            edits++;

            if (partClassSource is not null)
                working = InsertPartClass(working, partClassSource);

            parts.Add((xmlName, innerXml));
        }

        return (working, edits, parts);
    }

    public static bool IsVanillaLiquidClass(string className) =>
        !string.IsNullOrEmpty(className) && VanillaLiquidClasses.Contains(className);

    /// <summary>
    /// Own <c>BaseLiquid</c> subclass (not a vanilla liquid type). Convert via OnDrink XML/part
    /// instead of bumping the obsolete <c>Drank(..., StringBuilder)</c> signature.
    /// </summary>
    public static bool ShouldConvertOwnLiquidDrank(string content, int index)
    {
        if (!TryEnclosingClass(content, index, out var className, out var bases))
            return false;
        if (!Regex.IsMatch(bases, @"\bBaseLiquid\b"))
            return false;
        return !VanillaLiquidClasses.Contains(className);
    }

    public static bool TryEnclosingClass(string content, int index, out string className, out string bases)
    {
        className = "";
        bases = "";
        Match? last = null;
        foreach (Match m in ClassDecl.Matches(content))
        {
            if (m.Index >= index) break;
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            last = m;
        }
        if (last is null) return false;
        className = last.Groups["name"].Value;
        bases = last.Groups["bases"].Value;
        return className.Length > 0;
    }

    public static string PartNameFromClass(string className)
    {
        var stem = LiquidCsToXmlFixer.XmlNameFromClass(className);
        if (string.IsNullOrEmpty(stem))
            stem = className;
        return stem + "OnDrink";
    }

    static string BuildPartClass(string partName, string paramList, string body)
    {
        var liquidId = FirstParamName(paramList, "LiquidVolume") ?? "Liquid";
        var amountId = FirstParamName(paramList, "int") ?? "Volume";
        var targetId = FirstParamName(paramList, "GameObject") ?? "Target";
        var messageId = Regex.Match(paramList, @"(?:StringBuilder|TextBuilder)\s+(?<n>[A-Za-z_]\w*)").Groups["n"].Value;
        if (string.IsNullOrEmpty(messageId)) messageId = "Message";
        var exitId = Regex.Match(paramList, @"ref\s+bool\s+(?<n>[A-Za-z_]\w*)").Groups["n"].Value;
        if (string.IsNullOrEmpty(exitId)) exitId = "ExitInterface";

        var indentedBody = Indent(body.Trim('\r', '\n'), "            ");
        var sb = new StringBuilder();
        sb.AppendLine("namespace XRL.Liquids.Parts");
        sb.AppendLine("{");
        sb.AppendLine("\tpublic class " + partName + " : BaseLiquidPart");
        sb.AppendLine("\t{");
        sb.AppendLine("\t\tpublic override bool Drank(ref DrankEvent E)");
        sb.AppendLine("\t\t{");
        sb.AppendLine("\t\t\tvar " + liquidId + " = E.Volume;");
        sb.AppendLine("\t\t\tint " + amountId + " = E.Amount;");
        sb.AppendLine("\t\t\tvar " + targetId + " = E.Target;");
        sb.AppendLine("\t\t\tvar " + messageId + " = E.Message;");
        sb.AppendLine("\t\t\tbool " + exitId + " = E.ExitInterface;");
        sb.AppendLine("\t\t\tbool __result = " + partName + "Body();");
        sb.AppendLine("\t\t\tE.ExitInterface = " + exitId + ";");
        sb.AppendLine("\t\t\treturn __result;");
        sb.AppendLine();
        sb.AppendLine("\t\t\tbool " + partName + "Body()");
        sb.AppendLine("\t\t\t{");
        sb.AppendLine(indentedBody);
        sb.AppendLine("\t\t\t}");
        sb.AppendLine("\t\t}");
        sb.AppendLine("\t}");
        sb.AppendLine("}");
        return sb.ToString();
    }

    static string InsertPartClass(string content, string partSource)
    {
        var nsRx = new Regex(@"namespace\s+XRL\.Liquids\.Parts\s*\{", RegexOptions.Compiled);
        var m = nsRx.Match(content);
        if (m.Success && CsText.TryFindMatchingBrace(content, m.Index + m.Length - 1, out var close))
        {
            var classOnly = partSource;
            var innerStart = classOnly.IndexOf('{');
            var innerEnd = classOnly.LastIndexOf('}');
            if (innerStart >= 0 && innerEnd > innerStart)
            {
                var inner = classOnly[(innerStart + 1)..innerEnd].TrimEnd() + "\n";
                return content[..close] + inner + content[close..];
            }
        }

        var trimmed = content.TrimEnd();
        return trimmed + "\n\n" + partSource;
    }

    static string? FirstParamName(string paramList, string typeName)
    {
        var m = Regex.Match(paramList, @"\b" + Regex.Escape(typeName) + @"\s+(?<n>[A-Za-z_]\w*)");
        return m.Success ? m.Groups["n"].Value : null;
    }

    static string Indent(string text, string prefix)
    {
        var lines = text.Replace("\r\n", "\n").Split('\n');
        var min = int.MaxValue;
        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var n = 0;
            while (n < line.Length && line[n] is ' ' or '\t') n++;
            if (n < min) min = n;
        }
        if (min == int.MaxValue) min = 0;
        var sb = new StringBuilder();
        foreach (var line in lines)
        {
            var stripped = line.Length >= min ? line[min..] : line.TrimStart();
            sb.Append(prefix).Append(stripped).Append('\n');
        }
        if (sb.Length > 0 && sb[^1] == '\n')
            sb.Length--;
        return sb.ToString();
    }

    static bool InNamespace(string content, int index, string ns)
    {
        var fileScoped = Regex.Match(content, @"^namespace\s+([\w.]+)\s*;", RegexOptions.Multiline);
        if (fileScoped.Success)
            return string.Equals(fileScoped.Groups[1].Value, ns, StringComparison.Ordinal);

        Match? last = null;
        foreach (Match m in Regex.Matches(content, @"\bnamespace\s+(?<ns>[\w.]+)\s*\{"))
        {
            if (m.Index >= index) break;
            last = m;
        }
        return last is not null &&
               string.Equals(last.Groups["ns"].Value, ns, StringComparison.Ordinal);
    }
}
