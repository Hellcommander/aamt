using System.Text.RegularExpressions;



namespace ApiMigrator.Core;



/// <summary>

/// Report-only Liquids.xml hygiene that LiquidXmlFixer does not auto-apply:

/// merge-only liquids missing <c>&lt;render&gt;</c> (ambiguous — may inherit vanilla render),

/// leftover obsolete default-render color names, glow fields still on non-Glows parts,

/// and named render parts still missing <c>Class=</c> (Name-only → BaseLiquidRenderPart Extraneous).

/// </summary>

public static class LiquidXmlRenderAdviceScanner

{

    public const string MissingRenderMergeMember = "PreferXML.LiquidMissingRender.Merge";

    public const string ObsoleteRenderColorMember = "PreferXML.LiquidRender.ObsoleteColor";

    public const string MisplacedGlowMember = "PreferXML.LiquidRender.MisplacedGlow";

    public const string MissingPartClassMember = "PreferXML.LiquidRender.MissingPartClass";



    static readonly Regex LiquidsRootRx = new(

        @"<\s*liquids\b",

        RegexOptions.IgnoreCase | RegexOptions.Compiled);



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



    static readonly Regex ObsoleteColorRx = new(

        @"\b(?<name>colorText|colorTile|colorDetail)\b",

        RegexOptions.IgnoreCase | RegexOptions.Compiled);



    static readonly Regex MisplacedGlowRx = new(

        @"<\s*(?:render|part)\b(?![^>]*\bName\s*=\s*['""]Glows['""])[^>]*(?:BrighterWithVolume|LightLevel)\s*=",

        RegexOptions.IgnoreCase | RegexOptions.Compiled);



    // Named render <part> without Class= (skip BaseLiquidRenderPart / empty Name).

    static readonly Regex NamedPartWithoutClassRx = new(

        @"<\s*part\b(?![^>]*\bClass\s*=)(?=[^>]*\bName\s*=\s*(?<q>['""])(?<name>(?!BaseLiquidRenderPart\b)[^'""]+)\k<q>)[^>]*/?\s*>",

        RegexOptions.IgnoreCase | RegexOptions.Compiled);



    static readonly Regex RenderOpenRx = new(

        @"<\s*render\b(?<attrs>[^>]*?)(?<self>/?)\s*>",

        RegexOptions.IgnoreCase | RegexOptions.Compiled);



    public static List<RemainingHit> Scan(string content)

    {

        var hits = new List<RemainingHit>();

        if (string.IsNullOrEmpty(content) || !LiquidsRootRx.IsMatch(content))

            return hits;



        var seen = new HashSet<(int Line, string Member)>();



        foreach (Match m in LiquidBlockRx.Matches(content))

        {

            var openAttrs = m.Groups["openAttrs"].Value;

            var body = m.Groups["body"].Value;

            var hasClass = ClassChildRx.IsMatch(body) || ClassAttrRx.IsMatch(openAttrs);

            var hasRender = RenderChildRx.IsMatch(body);



            if (hasClass && !hasRender)

            {

                var line = GetLineNumber(content, m.Index);

                if (seen.Add((line, MissingRenderMergeMember)))

                {

                    hits.Add(new RemainingHit

                    {

                        Line = line,

                        Member = MissingRenderMergeMember,

                        Message =

                            "PreferXML — liquid with <class> has no <render>; BaseLiquid.Initialize NREs without one (even empty)",

                        Advice = ManualAdvice.LiquidXmlRenderAdvice +

                                 " LiquidXmlFixer inserts <render /> under -Apply for class liquids. Merge-only overlays without <class> inherit vanilla render and are not flagged.",

                        NeedsManual = true,

                        Text = GetLineText(content, m.Index).Trim(),

                    });

                }

            }

        }



        // Leftover obsolete colors on default render (not inside a named RenderSecondTo* / custom part).

        // Cheap heuristic: flag colorText/Tile/Detail that appear as attrs on <render or as

        // elements/attrs not preceded by Name="RenderSecond… on the same tag line.

        foreach (Match m in ObsoleteColorRx.Matches(content))

        {

            if (IsInsideRenderSecondToPart(content, m.Index))

                continue;



            var line = GetLineNumber(content, m.Index);

            if (!seen.Add((line, ObsoleteRenderColorMember)))

                continue;



            hits.Add(new RemainingHit

            {

                Line = line,

                Member = ObsoleteRenderColorMember,

                Message =

                    "PreferXML — obsolete liquid render color name (use baseColor / baseColorText / baseColorTile / baseColorDetail)",

                Advice = ManualAdvice.LiquidXmlRenderAdvice,

                NeedsManual = true,

                Text = GetLineText(content, m.Index).Trim(),

            });

        }



        foreach (Match m in MisplacedGlowRx.Matches(content))

        {

            var line = GetLineNumber(content, m.Index);

            if (!seen.Add((line, MisplacedGlowMember)))

                continue;



            hits.Add(new RemainingHit

            {

                Line = line,

                Member = MisplacedGlowMember,

                Message =

                    "PreferXML — BrighterWithVolume / LightLevel belong on <part Name=\"Glows\" Class=\"Glows\" … />, not BaseLiquidRenderPart / bare <render>",

                Advice = ManualAdvice.LiquidXmlRenderAdvice,

                NeedsManual = true,

                Text = GetLineText(content, m.Index).Trim(),

            });

        }



        foreach (Match m in FindNamedPartsWithoutClassInRender(content))

        {

            var line = GetLineNumber(content, m.Index);

            if (!seen.Add((line, MissingPartClassMember)))

                continue;



            var partName = m.Groups["name"].Value;

            hits.Add(new RemainingHit

            {

                Line = line,

                Member = MissingPartClassMember,

                Message =

                    $"PreferXML — render <part Name=\"{partName}\"> needs Class=\"{partName}\" " +

                    "(Name-only → BaseLiquidRenderPart Extraneous for colorText/BrighterWithVolume/etc.)",

                Advice = ManualAdvice.LiquidXmlRenderAdvice +

                         " LiquidXmlFixer adds Class= under -Apply when safe.",

                NeedsManual = true,

                Text = GetLineText(content, m.Index).Trim(),

            });

        }



        hits.Sort((a, b) => a.Line.CompareTo(b.Line));

        return hits;

    }



    /// <summary>

    /// Yields named <c>&lt;part&gt;</c> opens that sit directly under a <c>&lt;render&gt;</c>

    /// and lack <c>Class=</c>.

    /// </summary>

    static IEnumerable<Match> FindNamedPartsWithoutClassInRender(string content)

    {

        foreach (Match render in RenderOpenRx.Matches(content))

        {

            if (render.Groups["self"].Value.Contains('/'))

                continue;



            var innerStart = render.Index + render.Length;

            var closeIdx = FindCloseTag(content, innerStart, "render");

            if (closeIdx < 0)

                continue;



            var inner = content.Substring(innerStart, closeIdx - innerStart);

            foreach (Match part in NamedPartWithoutClassRx.Matches(inner))

            {

                // Re-anchor match index to full content for line numbers.

                yield return NamedPartWithoutClassRx.Match(content, innerStart + part.Index);

            }

        }

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



    /// <summary>

    /// True when the match sits inside a <c>&lt;part Name="RenderSecond…"&gt;…&lt;/part&gt;</c>

    /// (those parts still use colorText/colorTile/colorDetail).

    /// </summary>

    static bool IsInsideRenderSecondToPart(string content, int index)

    {

        // Search backwards for nearest <part …> open.

        var before = content.AsSpan(0, Math.Min(index, content.Length));

        var lastPart = before.LastIndexOf("<part".AsSpan(), StringComparison.OrdinalIgnoreCase);

        if (lastPart < 0) return false;

        var slice = content.AsSpan(lastPart, Math.Min(200, content.Length - lastPart));

        var end = slice.IndexOf('>');

        if (end < 0) return false;

        var openTag = slice[..(end + 1)].ToString();

        if (!Regex.IsMatch(openTag, @"\bName\s*=\s*['""]RenderSecond", RegexOptions.IgnoreCase))

            return false;

        // Ensure we haven't closed that part yet.

        var afterOpen = content.AsSpan(lastPart);

        var close = afterOpen.IndexOf("</part".AsSpan(), StringComparison.OrdinalIgnoreCase);

        if (close < 0) return true;

        return index < lastPart + close;

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


