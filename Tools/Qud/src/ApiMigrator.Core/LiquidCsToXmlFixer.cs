using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// PreferXML: <c>[IsLiquid]</c> / ctor setters / literal name-color-value-stain-render
/// overrides on a <c>BaseLiquid</c> subclass → merged <c>Liquids.xml</c>, strip those C# sites.
/// Drink behavior is <see cref="LiquidDrankToPartFixer"/>. Requires <c>namespace XRL.Liquids</c>
/// for <c>&lt;class&gt;</c> resolve.
/// </summary>
public static class LiquidCsToXmlFixer
{
    public const string FixRuleName =
        "BaseLiquid [IsLiquid]/ctor setters → Liquids.xml";

    static readonly Regex ClassDecl = new(
        @"\b(?:public|internal|protected|private)?\s*(?:(?:abstract|sealed|partial|static)\s+)*class\s+(?<name>[A-Za-z_]\w*)\s*:\s*(?<bases>[^\{]+)",
        RegexOptions.Compiled);

    static readonly Dictionary<string, string> PropToXml = new(StringComparer.Ordinal)
    {
        ["FlameTemperature"] = "flameTemperature",
        ["VaporTemperature"] = "vaporTemperature",
        ["FreezeTemperature"] = "freezeTemperature",
        ["Combustibility"] = "combustibility",
        ["Fluidity"] = "fluidity",
        ["Evaporativity"] = "evaporativity",
        ["Staining"] = "staining",
        ["ThermalConductivity"] = "thermalConductivity",
        ["CirculatoryLossTerm"] = "circulatoryLossTerm",
        ["CirculatoryLossNoun"] = "circulatoryLossNoun",
        ["ValuePerDram"] = "valuePerDram",
        ["Cooling"] = "cooling",
        ["Heating"] = "heating",
        ["Cleansing"] = "cleansing",
        ["ConsiderDangerousToContact"] = "considerDangerousToContact",
        ["ConsiderDangerousToDrink"] = "considerDangerousToDrink",
        ["InterruptAutowalk"] = "interruptAutowalk",
        ["PureElectricalConductivity"] = "pureElectricalConductivity",
        ["MixedElectricalConductivity"] = "mixedElectricalConductivity",
        ["EnableCleaning"] = "enableCleaning",
        ["SlipperyWhenFrozen"] = "slipperyWhenFrozen",
        ["SlipperySaveVs"] = "slipperySaveVs",
        ["SlipperySaveTargetScale"] = "slipperySaveTargetScale",
        ["SlipperySaveTargetBase"] = "slipperySaveTargetBase",
        ["SlipperyParticle"] = "slipperyParticle",
        ["SlipperyMessage"] = "slipperyMessage",
        ["VaporObject"] = "vaporObject",
    };

    static readonly Regex PropAssign = new(
        @"^[ \t]*(?:this\.)?(?<prop>FlameTemperature|VaporTemperature|FreezeTemperature|Combustibility|Fluidity|Evaporativity|Staining|ThermalConductivity|CirculatoryLossTerm|CirculatoryLossNoun|ValuePerDram|Cooling|Heating|Cleansing|ConsiderDangerousToContact|ConsiderDangerousToDrink|InterruptAutowalk|PureElectricalConductivity|MixedElectricalConductivity|EnableCleaning|SlipperyWhenFrozen|SlipperySaveVs|SlipperySaveTargetScale|SlipperySaveTargetBase|SlipperyParticle|SlipperyMessage|VaporObject)\s*=\s*(?<val>[^;]+);\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex IsLiquidAttr = new(
        @"^[ \t]*\[IsLiquid(?:Attribute)?\]\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex IsLiquidOverride = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+bool\s+IsLiquid\s*(?:=>\s*true\s*;|{\s*get\s*(?:=>\s*true\s*;|{\s*return\s+true\s*;\s*})\s*})\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex BaseSlug = new(
        @":\s*base\s*\(\s*""(?<slug>(?:[^""\\]|\\.)*)""\s*\)",
        RegexOptions.Compiled);

    static readonly Regex StringOverride = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+string\s+(?<meth>GetSmearedAdjective|GetSmearedName|GetStainedName|GetName|GetWaterRitualName|GetAdjective|GetColor)\s*\([^)]*\)\s*(?:=>\s*""(?<val>(?:[^""\\]|\\.)*)""\s*;|{\s*return\s*""(?<val2>(?:[^""\\]|\\.)*)""\s*;\s*})\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex ValueOverride = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+float\s+GetValuePerDram\s*\(\s*\)\s*(?:=>\s*(?<val>-?\d+(?:\.\d+)?f?)\s*;|{\s*return\s*(?<val2>-?\d+(?:\.\d+)?f?)\s*;\s*})\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex GetColorsOverride = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+List\s*<\s*string\s*>\s+GetColors\s*\(\s*\)\s*=>\s*(?<src>LiquidBlood\.Colors|Colors)\s*;\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex ColorsField = new(
        @"^[ \t]*(?:\[NonSerialized\]\s*)?(?:public|internal)\s+static\s+List\s*<\s*string\s*>\s+Colors\s*=\s*new\s+List\s*<\s*string\s*>\s*(?:\([^)]*\))?\s*\{(?<items>[^}]+)\}\s*;\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex StainElementsOverride = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+StainElements\s*\(\s*LiquidVolume\s+\w+\s*,\s*GetItemElementsEvent\s+\w+\s*\)\s*\{\s*\w+\.Add\s*\(\s*""(?<el>[^""]+)""\s*,\s*(?<w>\d+)\s*\)\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex BaseRenderPrimary = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+BaseRenderPrimary\s*\(\s*LiquidVolume\s+(?<liq>\w+)\s*\)\s*\{\s*\k<liq>\.ParentObject\.Render\.ColorString\s*=\s*""(?<cs>(?:[^""\\]|\\.)*)""\s*;\s*\k<liq>\.ParentObject\.Render\.TileColor\s*=\s*""(?<tile>(?:[^""\\]|\\.)*)""\s*;\s*\k<liq>\.ParentObject\.Render\.DetailColor\s*=\s*""(?<detail>(?:[^""\\]|\\.)*)""\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex RenderBackgroundPrimary = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+RenderBackgroundPrimary\s*\(\s*LiquidVolume\s+\w+\s*,\s*RenderEvent\s+(?<ev>\w+)\s*\)\s*\{\s*if\s*\(\s*!\k<ev>\.ColorsVisible\s*\)\s*return\s*;\s*\k<ev>\.ColorString\s*=\s*""(?<bg>(?:[^""\\]|\\.)*)""\s*\+\s*\k<ev>\.ColorString\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex RenderSmearPrimary = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+RenderSmearPrimary\s*\(\s*LiquidVolume\s+\w+\s*,\s*RenderEvent\s+(?<ev>\w+)\s*,\s*GameObject\s+\w+\s*\)\s*\{\s*if\s*\(\s*\k<ev>\.ColorsVisible\s*\)\s*\k<ev>\.ColorString\s*=\s*""(?<smear>(?:[^""\\]|\\.)*)""\s*;\s*base\.RenderSmearPrimary\s*\([^;]+;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex BaseRenderSecondaryAlgae = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+BaseRenderSecondary\s*\(\s*LiquidVolume\s+(?<liq>\w+)\s*\)\s*\{\s*\k<liq>\.ParentObject\.Render\.ColorString\s*\+=\s*""(?<sec>(?:[^""\\]|\\.)*)""\s*;\s*if\s*\(\s*!\k<liq>\.ContainsLiquid\s*\(\s*""algae""\s*\)\s*\)\s*return\s*;\s*\k<liq>\.ParentObject\.Render\.ColorString\s*\+=\s*""(?<algae>(?:[^""\\]|\\.)*)""\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex RenderSecondaryAlgae = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+RenderSecondary\s*\(\s*LiquidVolume\s+(?<liq>\w+)\s*,\s*RenderEvent\s+(?<ev>\w+)\s*\)\s*\{\s*if\s*\(\s*!\k<ev>\.ColorsVisible\s*\)\s*return\s*;\s*\k<ev>\.ColorString\s*\+=\s*""(?<sec>(?:[^""\\]|\\.)*)""\s*;\s*if\s*\(\s*!\k<liq>\.ContainsLiquid\s*\(\s*""algae""\s*\)\s*\)\s*return\s*;\s*\k<ev>\.DetailColor\s*\+=\s*""(?<detail>(?:[^""\\]|\\.)*)""\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Regex RenderPrimary = new(
        @"^[ \t]*(?:public|protected|internal)\s+override\s+void\s+RenderPrimary\s*\(\s*LiquidVolume\s+\w+\s*,\s*RenderEvent\s+(?<ev>\w+)\s*\)\s*\{\s*if\s*\(\s*!\k<ev>\.ColorsVisible\s*\)\s*return\s*;\s*\k<ev>\.ColorString\s*=\s*""(?<col>(?:[^""\\]|\\.)*)""\s*;\s*\}\s*\r?\n?",
        RegexOptions.Compiled | RegexOptions.Multiline);

    static readonly Dictionary<string, string> StringMethToXml = new(StringComparer.Ordinal)
    {
        ["GetSmearedAdjective"] = "smearedAdjective",
        ["GetSmearedName"] = "smearedName",
        ["GetStainedName"] = "stainedName",
        ["GetName"] = "displayName",
        ["GetWaterRitualName"] = "waterRitualName",
        ["GetAdjective"] = "adjective",
        ["GetColor"] = "color",
    };

    public static SidecarModFixResult FixMod(string modRoot, IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new SidecarModFixResult();
        if (string.IsNullOrEmpty(modRoot) || pathToContent == null)
            return result;

        var liquids = new List<(string Name, string InnerXml)>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("BaseLiquid", StringComparison.Ordinal) < 0)
                continue;

            var (next, edits, extracted) = FixContent(content);
            if (edits == 0)
                continue;

            var addedHere = 0;
            foreach (var liq in extracted)
            {
                if (!seen.Add(liq.Name))
                {
                    result.Warnings.Add(
                        $"Duplicate liquid '{liq.Name}' in {Path.GetFileName(path)} — XML already collected; C# not rewritten for this file.");
                    continue;
                }
                liquids.Add(liq);
                addedHere++;
            }

            if (addedHere == 0)
                continue;

            result.UpdatedContents[path] = next;
            result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleName, Count = edits }));
        }

        if (liquids.Count == 0)
            return result;

        var xmlPath = Path.Combine(modRoot, "Liquids.xml");
        string existing = "";
        if (pathToContent.TryGetValue(xmlPath, out var fromMap))
            existing = fromMap;
        else if (File.Exists(xmlPath))
            existing = File.ReadAllText(xmlPath);

        var merged = XmlOverlayMerger.MergeNamedChildren(existing, "liquids", "liquid", liquids);
        foreach (var liq in liquids)
            merged = XmlOverlayMerger.MergeMissingInner(merged, "liquid", liq.Name, liq.InnerXml);

        result.SidecarFiles[xmlPath] = merged;
        result.Fixes.Add((xmlPath, new AppliedFix
        {
            RuleName = FixRuleName + " (write Liquids.xml)",
            Count = liquids.Count,
        }));
        return result;
    }

    public static (string Content, int EditCount, List<(string Name, string InnerXml)> Liquids) FixContent(string content)
    {
        var liquids = new List<(string Name, string InnerXml)>();
        if (string.IsNullOrEmpty(content))
            return (content, 0, liquids);

        var edits = 0;
        var sb = new StringBuilder(content.Length);
        var last = 0;

        foreach (Match cm in ClassDecl.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, cm.Index) ||
                HitFilter.IsInsideStringLiteral(content, cm.Index))
                continue;
            if (!Regex.IsMatch(cm.Groups["bases"].Value, @"\bBaseLiquid\b"))
                continue;

            var className = cm.Groups["name"].Value;
            var braceOpen = content.IndexOf('{', cm.Index + cm.Length - 1);
            if (braceOpen < 0) continue;
            if (!CsText.TryFindMatchingBrace(content, braceOpen, out var braceClose))
                continue;

            var classSpan = content[cm.Index..braceClose];
            var slugMatch = BaseSlug.Match(classSpan);
            var slug = slugMatch.Success ? slugMatch.Groups["slug"].Value : XmlNameFromClass(className).ToLowerInvariant();

            var body = content[(braceOpen + 1)..braceClose];
            var props = new Dictionary<string, string>(StringComparer.Ordinal);
            var bodyEdits = 0;
            var nextBody = PropAssign.Replace(body, m =>
            {
                if (!TryLiteralValue(m.Groups["val"].Value.Trim(), out var val))
                    return m.Value;
                var prop = m.Groups["prop"].Value;
                if (!PropToXml.TryGetValue(prop, out var xmlName))
                    return m.Value;
                props[xmlName] = val;
                bodyEdits++;
                return "";
            });
            nextBody = IsLiquidOverride.Replace(nextBody, _ =>
            {
                bodyEdits++;
                return "";
            });

            string? colors = null;
            nextBody = ColorsField.Replace(nextBody, m =>
            {
                if (!TryColorsFromItems(m.Groups["items"].Value, out colors))
                    return m.Value;
                bodyEdits++;
                return "";
            });
            nextBody = GetColorsOverride.Replace(nextBody, m =>
            {
                var src = m.Groups["src"].Value;
                if (src == "LiquidBlood.Colors" && colors is null)
                    colors = "rK";
                bodyEdits++;
                return "";
            });
            nextBody = StringOverride.Replace(nextBody, m =>
            {
                var meth = m.Groups["meth"].Value;
                var val = m.Groups["val"].Success ? m.Groups["val"].Value : m.Groups["val2"].Value;
                if (!StringMethToXml.TryGetValue(meth, out var xmlName))
                    return m.Value;
                if (xmlName == "color")
                {
                    colors ??= UnescapeCs(val);
                    bodyEdits++;
                    return "";
                }
                props[xmlName] = UnescapeCs(val);
                bodyEdits++;
                return "";
            });
            nextBody = ValueOverride.Replace(nextBody, m =>
            {
                var raw = m.Groups["val"].Success ? m.Groups["val"].Value : m.Groups["val2"].Value;
                props["valuePerDram"] = raw.TrimEnd('f', 'F');
                bodyEdits++;
                return "";
            });
            string? stainEl = null;
            string? stainW = null;
            nextBody = StainElementsOverride.Replace(nextBody, m =>
            {
                stainEl = m.Groups["el"].Value;
                stainW = m.Groups["w"].Value;
                bodyEdits++;
                return "";
            });

            string? baseColor = null, baseTile = null, baseDetail = null, baseBg = null, smear = null;
            string? secColor = null, algaeText = null, algaeDetail = null;
            nextBody = BaseRenderPrimary.Replace(nextBody, m =>
            {
                baseColor = UnescapeCs(m.Groups["cs"].Value);
                baseTile = UnescapeCs(m.Groups["tile"].Value);
                baseDetail = UnescapeCs(m.Groups["detail"].Value);
                bodyEdits++;
                return "";
            });
            nextBody = RenderBackgroundPrimary.Replace(nextBody, m =>
            {
                baseBg = UnescapeCs(m.Groups["bg"].Value);
                bodyEdits++;
                return "";
            });
            nextBody = RenderSmearPrimary.Replace(nextBody, m =>
            {
                smear = UnescapeCs(m.Groups["smear"].Value);
                bodyEdits++;
                return "";
            });
            nextBody = BaseRenderSecondaryAlgae.Replace(nextBody, m =>
            {
                secColor = UnescapeCs(m.Groups["sec"].Value);
                algaeText = UnescapeCs(m.Groups["algae"].Value);
                bodyEdits++;
                return "";
            });
            nextBody = RenderSecondaryAlgae.Replace(nextBody, m =>
            {
                secColor ??= UnescapeCs(m.Groups["sec"].Value);
                algaeDetail = UnescapeCs(m.Groups["detail"].Value);
                bodyEdits++;
                return "";
            });
            nextBody = RenderPrimary.Replace(nextBody, m =>
            {
                secColor ??= UnescapeCs(m.Groups["col"].Value);
                bodyEdits++;
                return "";
            });

            var beforeClass = content[last..cm.Index];
            var nextBefore = IsLiquidAttr.Replace(beforeClass, _ =>
            {
                bodyEdits++;
                return "";
            });

            if (bodyEdits == 0)
                continue;

            var xmlName = slug;
            var inner = new StringBuilder();
            inner.Append("    <slug>").Append(XmlOverlayMerger.XmlEscape(slug)).Append("</slug>\n");
            inner.Append("    <class>").Append(XmlOverlayMerger.XmlEscape(className)).Append("</class>\n");
            foreach (var kv in props)
            {
                inner.Append("    <").Append(kv.Key).Append('>')
                    .Append(XmlOverlayMerger.XmlEscape(kv.Value))
                    .Append("</").Append(kv.Key).Append(">\n");
            }
            if (!string.IsNullOrEmpty(colors))
                inner.Append("    <colors>").Append(XmlOverlayMerger.XmlEscape(colors)).Append("</colors>\n");
            if (!string.IsNullOrEmpty(stainEl))
            {
                inner.Append("    <stainElement Name=\"").Append(XmlOverlayMerger.XmlEscape(stainEl)).Append('"');
                if (stainW is not null && stainW != "1")
                    inner.Append('>').Append(stainW).Append("</stainElement>\n");
                else
                    inner.Append(" />\n");
            }

            var hasRenderBits = baseColor is not null || baseTile is not null || baseDetail is not null ||
                                baseBg is not null || smear is not null || secColor is not null ||
                                algaeText is not null || algaeDetail is not null;
            if (hasRenderBits)
            {
                inner.Append("    <render>\n");
                if (algaeText is not null || algaeDetail is not null)
                {
                    inner.Append("      <part Name=\"RenderSecondToAlgae\" Class=\"RenderSecondToAlgae\">\n");
                    if (algaeText is not null)
                        inner.Append("        <colorText>").Append(XmlOverlayMerger.XmlEscape(secColor + algaeText)).Append("</colorText>\n");
                    if (algaeDetail is not null)
                        inner.Append("        <colorDetail>").Append(XmlOverlayMerger.XmlEscape(algaeDetail)).Append("</colorDetail>\n");
                    inner.Append("      </part>\n");
                }
                if (baseColor is not null)
                    inner.Append("      <baseColor>").Append(XmlOverlayMerger.XmlEscape(baseColor)).Append("</baseColor>\n");
                if (baseTile is not null)
                    inner.Append("      <baseColorTile>").Append(XmlOverlayMerger.XmlEscape(baseTile)).Append("</baseColorTile>\n");
                if (baseDetail is not null)
                    inner.Append("      <baseColorDetail>").Append(XmlOverlayMerger.XmlEscape(baseDetail)).Append("</baseColorDetail>\n");
                if (baseBg is not null)
                    inner.Append("      <baseColorBackground>").Append(XmlOverlayMerger.XmlEscape(baseBg)).Append("</baseColorBackground>\n");
                if (secColor is not null)
                    inner.Append("      <secondaryColorText>").Append(XmlOverlayMerger.XmlEscape(secColor)).Append("</secondaryColorText>\n");
                if (smear is not null)
                {
                    inner.Append("      <smear>\n        <color>")
                        .Append(XmlOverlayMerger.XmlEscape(smear))
                        .Append("</color>\n      </smear>\n");
                }
                inner.Append("    </render>\n");
            }
            else
                inner.Append("    <render />\n");

            liquids.Add((xmlName, inner.ToString()));

            sb.Append(nextBefore);
            sb.Append(content, cm.Index, braceOpen + 1 - cm.Index);
            sb.Append(nextBody);
            last = braceClose;
            edits += bodyEdits;
        }

        if (edits == 0)
            return (content, 0, liquids);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), edits, liquids);
    }

    public static string XmlNameFromClass(string className)
    {
        if (className.StartsWith("Liquid", StringComparison.Ordinal) && className.Length > 6)
            return className[6..];
        return className;
    }

    /// <summary>
    /// Liquids.xml <c>Name</c> is the ctor slug when present (<c>ctor : base("ichor")</c> →
    /// <c>ichor</c>), matching vanilla. Otherwise the class stem without a <c>Liquid</c> prefix.
    /// Search <paramref name="searchText"/> should include the class header and ctor.
    /// </summary>
    public static string LiquidXmlName(string className, string classHeader)
    {
        var slugMatch = BaseSlug.Match(classHeader ?? "");
        if (slugMatch.Success)
            return slugMatch.Groups["slug"].Value;
        return XmlNameFromClass(className);
    }

    static bool TryColorsFromItems(string items, out string colors)
    {
        colors = "";
        var sb = new StringBuilder();
        foreach (Match m in Regex.Matches(items, @"""(?<c>(?:[^""\\]|\\.)*)"""))
        {
            var c = UnescapeCs(m.Groups["c"].Value);
            if (c.Length == 0) return false;
            sb.Append(c);
        }
        if (sb.Length == 0) return false;
        colors = sb.ToString();
        return true;
    }

    static bool TryLiteralValue(string expr, out string val)
    {
        val = "";
        var t = expr.Trim();
        if (t is "true" or "false")
        {
            val = t;
            return true;
        }
        if (Regex.IsMatch(t, @"^-?\d+$"))
        {
            val = t;
            return true;
        }
        if (t.Length >= 2 && t[0] == '"' && t[^1] == '"')
        {
            val = UnescapeCs(t[1..^1]);
            return true;
        }
        return false;
    }

    static string UnescapeCs(string s) =>
        s.Replace("\\\"", "\"").Replace("\\\\", "\\");
}
