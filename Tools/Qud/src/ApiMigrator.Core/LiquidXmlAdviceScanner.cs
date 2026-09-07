using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Report-only: liquid ctor/property setters, obsolete LiquidBlood/LiquidWarmStatic patterns,
/// and PreferXML guidance. Never auto-deletes.
/// </summary>
public static class LiquidXmlAdviceScanner
{
    public const string LiquidPropsMember = "PreferXML.LiquidProperties";
    public const string LiquidBloodMember = "PreferXML.LiquidBlood";
    public const string LiquidWarmStaticMember = "PreferXML.LiquidWarmStatic";

    static readonly Regex LiquidPropAssign = new(
        @"\b(?:this\.)?(?<prop>FlameTemperature|VaporTemperature|FreezeTemperature|Combustibility|Fluidity|Evaporativity|Staining|ThermalConductivity|CirculatoryLossTerm|CirculatoryLossNoun|ValuePerDram|Cooling|Heating|Cleansing|ConsiderDangerousToContact|ConsiderDangerousToDrink|InterruptAutowalk|PureElectricalConductivity|MixedElectricalConductivity|Weight|EnableCleaning|SlipperyWhenFrozen|SlipperySaveVs|SlipperySaveTargetScale|SlipperySaveTargetBase|SlipperyParticle|SlipperyMessage|VaporObject|Temperature)\s*=",
        RegexOptions.Compiled);

    static readonly Regex LiquidBloodRef = new(
        @"\bLiquidBlood\.(?<member>Colors|ID|GetColors)\b|\bLiquidBlood\b",
        RegexOptions.Compiled);

    static readonly Regex LiquidWarmStaticRef = new(
        @"\bLiquidWarmStatic\.(?<member>ApplyRandomEffectTo|GlitchObject|GlitchZone|ID)\b|\bLiquidWarmStatic\b",
        RegexOptions.Compiled);

    static readonly Regex NamespaceVsType = new(
        @"\b(?:new|:\s*|typeof\s*\()\s*(?<name>Telepathy|Telekinesis|Confusion|Clairvoyance)\b",
        RegexOptions.Compiled);

    static readonly Regex ConflictingUsing = new(
        @"(?m)^(?:global\s+)?using\s+(?<ns>[\w.]+)\s*;",
        RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content))
            return hits;

        var seen = new HashSet<(int Line, string Member)>();

        foreach (Match m in LiquidPropAssign.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, LiquidPropsMember)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = LiquidPropsMember,
                Message = "PreferXML — liquid temperature/physics fields belong in Liquids.xml; do not add [Obsolete]",
                Advice = ManualAdvice.LiquidPropertiesAdvice(m.Groups["prop"].Value),
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        foreach (Match m in LiquidBloodRef.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            // Skip class LiquidBlood declaration itself
            var lineText = GetLineText(content, m.Index);
            if (Regex.IsMatch(lineText, @"\bclass\s+LiquidBlood\b"))
                continue;

            var line = GetLineNumber(content, m.Index);
            var member = LiquidBloodMember + (m.Groups["member"].Success ? "." + m.Groups["member"].Value : "");
            if (!seen.Add((line, member)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = member,
                Message = "PreferXML — LiquidBlood back-compat; use Liquids.xml / LiquidID; do not add [Obsolete]",
                Advice = ManualAdvice.LiquidBloodAdvice(m.Groups["member"].Success ? m.Groups["member"].Value : null),
                NeedsManual = true,
                Text = lineText.Trim(),
            });
        }

        foreach (Match m in LiquidWarmStaticRef.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var lineText = GetLineText(content, m.Index);
            if (Regex.IsMatch(lineText, @"\bclass\s+LiquidWarmStatic\b"))
                continue;

            var line = GetLineNumber(content, m.Index);
            var member = LiquidWarmStaticMember +
                         (m.Groups["member"].Success ? "." + m.Groups["member"].Value : "");
            if (!seen.Add((line, member)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = member,
                Message =
                    "PreferXML — LiquidWarmStatic back-compat; behaviors live on BaseGlitchPart / GlitchOn* liquid parts",
                Advice = ManualAdvice.LiquidWarmStaticAdvice(
                    m.Groups["member"].Success ? m.Groups["member"].Value : null),
                NeedsManual = true,
                Text = lineText.Trim(),
            });
        }

        // CS0118-ish: mutation type name used while a using imports a namespace ending with that name
        var usings = new List<string>();
        foreach (Match u in ConflictingUsing.Matches(content))
            usings.Add(u.Groups["ns"].Value);

        foreach (Match m in NamespaceVsType.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var name = m.Groups["name"].Value;
            var conflict = usings.FirstOrDefault(ns =>
                ns.EndsWith("." + name, StringComparison.Ordinal) ||
                string.Equals(ns, name, StringComparison.Ordinal));
            if (conflict is null)
                continue;

            var line = GetLineNumber(content, m.Index);
            var member = "CS0118." + name;
            if (!seen.Add((line, member)))
                continue;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = member,
                Message = $"Possible CS0118 — '{name}' may be a namespace (from using {conflict})",
                Advice = ManualAdvice.NamespaceVsTypeAdvice(name),
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        hits.Sort((a, b) => a.Line.CompareTo(b.Line));
        return hits;
    }

    static int GetLineNumber(string text, int index)
    {
        var count = 1;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            if (text[i] == '\n') count++;
        }
        return count;
    }

    static string GetLineText(string text, int index)
    {
        var start = index <= 0 ? -1 : text.LastIndexOf('\n', index - 1);
        var end = text.IndexOf('\n', index);
        if (end < 0) end = text.Length;
        var s = start + 1;
        return s <= end && s >= 0 && s <= text.Length ? text.Substring(s, Math.Max(end - s, 0)) : "";
    }
}
