using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Safe Liquids.xml autofixes from Quiet Age PreferXML learnings:
/// <list type="bullet">
/// <item>Insert empty <c>&lt;render /&gt;</c> on liquids that declare <c>&lt;class&gt;</c>
/// (without it, <c>Part.Class</c> stays null → <c>BaseLiquid.Initialize</c> NRE).
/// Merge-only overlays without <c>&lt;class&gt;</c> are left alone (report-only).</item>
/// <item>Rename obsolete default-render colors <c>colorText</c>/<c>colorTile</c>/<c>colorDetail</c>
/// → <c>baseColorText</c>/<c>baseColorTile</c>/<c>baseColorDetail</c> on <c>&lt;render&gt;</c>
/// attrs/children and unnamed / <c>BaseLiquidRenderPart</c> parts. Never touches
/// <c>RenderSecondTo*</c> part children (those still use colorText).</item>
/// <item>Move <c>BrighterWithVolume</c>/<c>LightLevel</c> off <c>&lt;render&gt;</c> /
/// default render part onto a <c>Glows</c> part when mechanically clear.</item>
/// <item>Add <c>Class="Name"</c> on named <c>&lt;render&gt;</c> parts that only set
/// <c>Name</c>. <c>ModuleBlueprint.Read</c> resolves Name→type after Namespace state is
/// popped, so Name-only parts fall through to <c>BaseLiquidRenderPart</c> and warn
/// Extraneous for <c>colorText</c>/<c>BrighterWithVolume</c>/etc. Explicit <c>Class</c>
/// is applied during attribute read while Namespace is still <c>XRL.Liquids.Parts</c>.</item>
/// </list>
/// </summary>
public static class LiquidXmlFixer
{
    public const string MissingRenderRuleName =
        "Liquids.xml insert empty <render /> for <class> liquids";

    public const string RenderColorRenameRuleName =
        "Liquids.xml colorText/Tile/Detail → baseColor* (default render)";

    public const string RenderGlowMoveRuleName =
        "Liquids.xml BrighterWithVolume/LightLevel → Glows part";

    public const string RenderPartClassRuleName =
        "Liquids.xml render <part Name> → also Class= (ResolveType)";

    static readonly Regex LiquidsRootRx = new(
        @"<\s*liquids\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Non-nested liquid blocks (vanilla/mod liquids never nest).
    static readonly Regex LiquidBlockRx = new(
        @"<(?<open>liquid)\b(?<openAttrs>[^>]*)>(?<body>[\s\S]*?)</liquid\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ClassChildRx = new(
        @"<\s*class\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ClassAttrRx = new(
        @"\bClass\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex RenderChildRx = new(
        @"<\s*render\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex RenderOpenRx = new(
        @"<\s*render\b(?<attrs>[^>]*?)(?<self>/?)\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ColorAttrRx = new(
        @"\b(?<name>colorText|colorTile|colorDetail)\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex GlowAttrRx = new(
        @"\s+(?<name>BrighterWithVolume|LightLevel)\s*=\s*(?<q>['""])(?<val>[^'""]*)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex PartNameRx = new(
        @"\bName\s*=\s*(?<q>['""])(?<val>[^'""]*)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex GlowsPartRx = new(
        @"<\s*part\b(?<attrs>[^>]*?\bName\s*=\s*(?<q>['""])Glows\k<q>[^>]*)(?<self>/?)\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content) || !LiquidsRootRx.IsMatch(content))
            return (content, fixes);

        var working = content;
        var missingCount = 0;
        var colorCount = 0;
        var glowCount = 0;
        var partClassCount = 0;

        working = LiquidBlockRx.Replace(working, m =>
        {
            var openAttrs = m.Groups["openAttrs"].Value;
            var body = m.Groups["body"].Value;
            var nextBody = body;
            var changed = false;

            var hasClass = ClassChildRx.IsMatch(body) || ClassAttrRx.IsMatch(openAttrs);
            var hasRender = RenderChildRx.IsMatch(body);

            if (hasClass && !hasRender)
            {
                var indent = GuessChildIndent(body);
                nextBody = nextBody.TrimEnd() + "\n" + indent + "<render />\n";
                missingCount++;
                changed = true;
                hasRender = true;
            }

            if (hasRender || RenderChildRx.IsMatch(nextBody))
            {
                var (body2, c, g, pc) = FixRenderRegions(nextBody);
                if (c > 0 || g > 0 || pc > 0)
                {
                    nextBody = body2;
                    colorCount += c;
                    glowCount += g;
                    partClassCount += pc;
                    changed = true;
                }
            }

            if (!changed)
                return m.Value;

            return "<liquid" + openAttrs + ">" + nextBody + "</liquid>";
        });

        if (missingCount > 0)
            fixes.Add(new AppliedFix { RuleName = MissingRenderRuleName, Count = missingCount });
        if (colorCount > 0)
            fixes.Add(new AppliedFix { RuleName = RenderColorRenameRuleName, Count = colorCount });
        if (glowCount > 0)
            fixes.Add(new AppliedFix { RuleName = RenderGlowMoveRuleName, Count = glowCount });
        if (partClassCount > 0)
            fixes.Add(new AppliedFix { RuleName = RenderPartClassRuleName, Count = partClassCount });

        return (working, fixes);
    }

    static (string Body, int ColorEdits, int GlowEdits, int PartClassEdits) FixRenderRegions(string body)
    {
        var colorEdits = 0;
        var glowEdits = 0;
        var partClassEdits = 0;
        var sb = new StringBuilder(body.Length + 64);
        var pos = 0;

        foreach (Match m in RenderOpenRx.Matches(body))
        {
            sb.Append(body, pos, m.Index - pos);
            var attrs = m.Groups["attrs"].Value;
            var self = m.Groups["self"].Value.Contains('/');

            // Rename obsolete color attrs on <render …>
            var (attrs2, c1) = RenameColorAttrs(attrs);
            colorEdits += c1;

            // Harvest glow attrs from <render …> for Glows part.
            var glowPairs = new List<(string Name, string Quote, string Val)>();
            attrs2 = GlowAttrRx.Replace(attrs2, gm =>
            {
                glowPairs.Add((gm.Groups["name"].Value, gm.Groups["q"].Value, gm.Groups["val"].Value));
                glowEdits++;
                return "";
            });

            if (self)
            {
                // Self-closing: convert color attrs → child elements (LiquidRenderBlueprint
                // reads nodes). Expand when glows or colors need children.
                var colorKids = new List<(string Name, string Quote, string Val)>();
                attrs2 = Regex.Replace(attrs2,
                    @"\s+\b(?<name>baseColorText|baseColorTile|baseColorDetail|baseColor)\s*=\s*(?<q>['""])(?<val>[^'""]*)\k<q>",
                    gm =>
                    {
                        colorKids.Add((gm.Groups["name"].Value, gm.Groups["q"].Value, gm.Groups["val"].Value));
                        return "";
                    },
                    RegexOptions.IgnoreCase);

                if (glowPairs.Count == 0 && colorKids.Count == 0)
                {
                    sb.Append("<render").Append(attrs2).Append(" />");
                }
                else
                {
                    var indent = "      ";
                    sb.Append("<render").Append(attrs2).Append(">\n");
                    if (glowPairs.Count > 0)
                    {
                        sb.Append(indent).Append(BuildGlowsPart(glowPairs)).Append('\n');
                        partClassEdits++; // BuildGlowsPart always emits Class="Glows"
                    }
                    foreach (var (name, _, val) in colorKids)
                        sb.Append(indent).Append('<').Append(name).Append('>')
                          .Append(val).Append("</").Append(name).Append(">\n");
                    sb.Append("    </render>");
                }
                pos = m.Index + m.Length;
                continue;
            }

            // Find matching </render>
            var closeIdx = FindCloseTag(body, m.Index + m.Length, "render");
            if (closeIdx < 0)
            {
                sb.Append(m.Value);
                pos = m.Index + m.Length;
                continue;
            }

            var inner = body.Substring(m.Index + m.Length, closeIdx - (m.Index + m.Length));
            var (inner2, c2, g2, pc2) = FixRenderInner(inner, glowPairs);
            colorEdits += c2;
            glowEdits += g2;
            partClassEdits += pc2;

            sb.Append("<render").Append(attrs2).Append('>')
              .Append(inner2)
              .Append("</render>");
            pos = closeIdx + IndexOfCloseEnd(body, closeIdx);
        }

        sb.Append(body, pos, body.Length - pos);
        return (sb.ToString(), colorEdits, glowEdits, partClassEdits);
    }

    static (string Inner, int ColorEdits, int GlowEdits, int PartClassEdits)
        FixRenderInner(string inner, List<(string Name, string Quote, string Val)> pendingGlows)
    {
        var colorEdits = 0;
        var glowEdits = 0;
        var partClassEdits = 0;
        var sb = new StringBuilder(inner.Length + 64);
        var pos = 0;
        var depth = 0; // part nesting; 0 = direct child of render

        // Walk tags roughly: part opens/closes + color children at depth 0.
        var tagRx = new Regex(
            @"<!--[\s\S]*?-->|</(?<close>part)\s*>|<(?<open>part)\b(?<attrs>[^>]*?)(?<self>/?)\s*>|</(?<colorClose>colorText|colorTile|colorDetail)\s*>|<(?<colorOpen>colorText|colorTile|colorDetail)\b(?<colorAttrs>[^>]*?)(?<colorSelf>/?)\s*>",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        foreach (Match m in tagRx.Matches(inner))
        {
            sb.Append(inner, pos, m.Index - pos);

            if (m.Value.StartsWith("<!--", StringComparison.Ordinal))
            {
                sb.Append(m.Value);
                pos = m.Index + m.Length;
                continue;
            }

            if (m.Groups["close"].Success)
            {
                if (depth > 0) depth--;
                sb.Append(m.Value);
                pos = m.Index + m.Length;
                continue;
            }

            if (m.Groups["colorClose"].Success)
            {
                if (depth == 0)
                {
                    var ren = MapColorName(m.Groups["colorClose"].Value);
                    sb.Append("</").Append(ren).Append('>');
                    colorEdits++;
                }
                else sb.Append(m.Value);
                pos = m.Index + m.Length;
                continue;
            }

            if (m.Groups["colorOpen"].Success)
            {
                if (depth == 0)
                {
                    var ren = MapColorName(m.Groups["colorOpen"].Value);
                    var cAttrs = m.Groups["colorAttrs"].Value;
                    var cSelf = m.Groups["colorSelf"].Value.Contains('/') ? " /" : "";
                    sb.Append('<').Append(ren).Append(cAttrs).Append(cSelf).Append('>');
                    colorEdits++;
                }
                else sb.Append(m.Value);
                pos = m.Index + m.Length;
                continue;
            }

            if (m.Groups["open"].Success)
            {
                var attrs = m.Groups["attrs"].Value;
                var self = m.Groups["self"].Value.Contains('/');
                var nameMatch = PartNameRx.Match(attrs);
                var partName = nameMatch.Success ? nameMatch.Groups["val"].Value : "";
                var isDefaultRenderPart = string.IsNullOrEmpty(partName) ||
                    partName.Equals("BaseLiquidRenderPart", StringComparison.OrdinalIgnoreCase);

                if (isDefaultRenderPart)
                {
                    var (a2, c) = RenameColorAttrs(attrs);
                    colorEdits += c;
                    var harvested = new List<(string Name, string Quote, string Val)>();
                    a2 = GlowAttrRx.Replace(a2, gm =>
                    {
                        harvested.Add((gm.Groups["name"].Value, gm.Groups["q"].Value, gm.Groups["val"].Value));
                        glowEdits++;
                        return "";
                    });
                    pendingGlows.AddRange(harvested);
                    attrs = a2;
                }
                // Glows / RenderSecondTo*: leave colorText + glow attrs alone.

                // Name-only parts need Class= so ResolveType runs during attribute read
                // (Namespace still pushed). Skip BaseLiquidRenderPart / empty Name.
                if (!string.IsNullOrEmpty(partName) &&
                    !partName.Equals("BaseLiquidRenderPart", StringComparison.OrdinalIgnoreCase) &&
                    !ClassAttrRx.IsMatch(attrs))
                {
                    attrs += $" Class=\"{partName}\"";
                    partClassEdits++;
                }

                sb.Append("<part").Append(attrs);
                if (self) sb.Append(" /");
                sb.Append('>');
                if (!self) depth++;
                pos = m.Index + m.Length;
                continue;
            }

            sb.Append(m.Value);
            pos = m.Index + m.Length;
        }

        sb.Append(inner, pos, inner.Length - pos);
        var result = sb.ToString();

        if (pendingGlows.Count > 0)
        {
            // Glow attrs were already counted when stripped from render/default part.
            result = MergeGlowsIntoInner(result, pendingGlows, out var mergedNew);
            if (mergedNew && !GlowsPartRx.IsMatch(inner))
                partClassEdits++; // newly inserted Glows part includes Class=
            pendingGlows.Clear();
        }

        return (result, colorEdits, glowEdits, partClassEdits);
    }

    static string MergeGlowsIntoInner(string inner, List<(string Name, string Quote, string Val)> glows,
        out bool merged)
    {
        merged = false;
        if (glows.Count == 0) return inner;

        var m = GlowsPartRx.Match(inner);
        if (m.Success)
        {
            var attrs = m.Groups["attrs"].Value;
            var self = m.Groups["self"].Value.Contains('/');
            var nextAttrs = attrs;
            if (!ClassAttrRx.IsMatch(nextAttrs))
            {
                nextAttrs += " Class=\"Glows\"";
                merged = true;
            }
            foreach (var (name, q, val) in glows)
            {
                if (Regex.IsMatch(nextAttrs, $@"\b{Regex.Escape(name)}\s*=", RegexOptions.IgnoreCase))
                    continue;
                nextAttrs += $" {name}={q}{val}{q}";
                merged = true;
            }
            if (!merged) return inner;
            var repl = "<part" + nextAttrs + (self ? " /" : "") + ">";
            return GlowsPartRx.Replace(inner, repl, 1);
        }

        var indent = GuessChildIndent(inner);
        if (string.IsNullOrEmpty(indent)) indent = "      ";
        var insert = indent + BuildGlowsPart(glows) + "\n";
        merged = true;
        // Prefer inserting after leading whitespace at start of render inner.
        if (inner.Length > 0 && (inner[0] == '\n' || inner[0] == '\r'))
            return inner[..1] + insert + inner[1..];
        return "\n" + insert + inner;
    }

    static string BuildGlowsPart(List<(string Name, string Quote, string Val)> glows)
    {
        var attrs = " Name=\"Glows\" Class=\"Glows\"";
        foreach (var (name, q, val) in glows)
            attrs += $" {name}={q}{val}{q}";
        return "<part" + attrs + " />";
    }

    static (string Attrs, int Count) RenameColorAttrs(string attrs)
    {
        var count = 0;
        var next = ColorAttrRx.Replace(attrs, m =>
        {
            count++;
            return MapColorName(m.Groups["name"].Value) + "=";
        });
        return (next, count);
    }

    static string MapColorName(string name) => name.ToLowerInvariant() switch
    {
        "colortext" => "baseColorText",
        "colortile" => "baseColorTile",
        "colordetail" => "baseColorDetail",
        _ => name,
    };

    static string GuessChildIndent(string body)
    {
        var m = Regex.Match(body, @"\r?\n([ \t]+)<");
        return m.Success ? m.Groups[1].Value : "    ";
    }

    static int FindCloseTag(string text, int from, string name)
    {
        var close = new Regex(@"</\s*" + Regex.Escape(name) + @"\s*>",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);
        var open = new Regex(@"<\s*" + Regex.Escape(name) + @"\b",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);
        var depth = 1;
        var i = from;
        while (i < text.Length)
        {
            var nextOpen = open.Match(text, i);
            var nextClose = close.Match(text, i);
            if (!nextClose.Success) return -1;
            if (nextOpen.Success && nextOpen.Index < nextClose.Index)
            {
                // self-closing open?
                var end = text.IndexOf('>', nextOpen.Index);
                if (end >= 0 && text[end - 1] != '/')
                    depth++;
                i = (end >= 0 ? end : nextOpen.Index) + 1;
                continue;
            }
            depth--;
            if (depth == 0) return nextClose.Index;
            i = nextClose.Index + nextClose.Length;
        }
        return -1;
    }

    static int IndexOfCloseEnd(string text, int closeIdx)
    {
        var end = text.IndexOf('>', closeIdx);
        return end >= 0 ? end + 1 - closeIdx : 0;
    }
}
