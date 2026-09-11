using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// High-confidence repairs for current Qud compiler diagnostics that are not obsolete-member
/// warnings. These rules also heal a few malformed outputs produced by older migrator builds.
/// </summary>
public static class ModernCompilerFixer
{
    public const string FixRuleName = "current Qud compiler compatibility repairs";

    static readonly Regex BoolRender = new(
        @"\b(?<sig>(?:public|protected|internal)\s+(?:(?:sealed|unsafe)\s+)*override\s+)bool(?<tail>\s+Render\s*\(\s*RenderEvent\s+(?<event>[A-Za-z_]\w*)\s*\))",
        RegexOptions.Compiled);

    static readonly Regex TakeDamageBuilder = new(
        @"\.TakeDamage\(\s*(?<amount>[A-Za-z_]\w*)\s*,\s*(?<builder>[A-Za-z_]\w*)\s*,",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var working = content;
        var edits = 0;
        working = FixRenderOverrides(working, ref edits);
        working = FixTakeDamageTextBuilder(working, ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\.(?<name>WantTurnTick)\(\s*(?:this|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\)", RegexOptions.Compiled),
            m => "." + m.Groups["name"].Value + "()", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\breturn\s+base\.Does\s*=\s*TurnTick\s*;", RegexOptions.Compiled),
            _ => "return base.WantTurnTick();", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\.HasGoal\(\s*""(?<goal>[A-Za-z_]\w*)""\s*\)", RegexOptions.Compiled),
            m => ".HasGoal<" + m.Groups["goal"].Value + ">()", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\.GiveDramsEvent\s*\(", RegexOptions.Compiled),
            _ => ".GiveDrams(", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"(?<![.\w])FetchBitById\s*\(", RegexOptions.Compiled),
            _ => "BitType.FetchBitByCode(", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\bBuildZone\s*\(\s*ZoneRequest\s+(?<name>[A-Za-z_]\w*)\s*\)", RegexOptions.Compiled),
            m => "BuildZone(Zone " + m.Groups["name"].Value + ")", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\bbase\.Object\.Render\s*\(", RegexOptions.Compiled),
            _ => "base.Render(", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\bpublic\s+static\s+readonly\s+int\s+ICON_COLOR_PRIORITY\b", RegexOptions.Compiled),
            _ => "public new static readonly int ICON_COLOR_PRIORITY", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\bcell\.(?<coord>X|Y)\s*!=\s*null\s*&&\s*", RegexOptions.Compiled),
            _ => "", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"\s*&&\s*cell\.(?:X|Y)\s*!=\s*null", RegexOptions.Compiled),
            _ => "", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"(?<start>""(?:[^""\\]|\\.)*=subject\.(?:possessive|[^""\\]*)""\.StartReplace\(\))\s*\.AddObject\(\s*(?<subject>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\)", RegexOptions.Compiled),
            m => m.Groups["start"].Value + ".SetSubject(" + m.Groups["subject"].Value + ")", ref edits);
        working = ReplaceOutsideComments(working,
            new Regex(@"(?<recv>[A-Za-z_]\w*)\.SetZoneMusicOverride\(\s*(?<zone>[^,;]+)\s*,\s*(?<track>[^);]+)\s*\)\s*;", RegexOptions.Compiled),
            m => m.Groups["recv"].Value + ".AddZoneBuilderOverride(" + m.Groups["zone"].Value.Trim() +
                 ", ZoneBuilderBlueprint.Get(nameof(Music), \"Track\", " + m.Groups["track"].Value.Trim() + "));",
            ref edits);
        working = FixDeepCopyConstructors(working, ref edits);
        working = FixLegacyZoneBuilderWrappers(working, ref edits);
        working = RemoveUnusedLiteralLocals(working, ref edits);
        working = InitializeReadOnlyDefaultFields(working, ref edits);
        return (working, edits);
    }

    static string FixRenderOverrides(string content, ref int edits)
    {
        var working = content;
        foreach (Match m in BoolRender.Matches(content).Cast<Match>().Reverse())
        {
            if (HitFilter.IsInsideComment(content, m.Index) || HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var open = CsText.SkipWsAndComments(working, m.Index + m.Length);
            if (open >= working.Length || working[open] != '{' ||
                !CsText.TryFindMatchingBrace(working, open, out var close))
                continue;
            var body = working[(open + 1)..close];
            var eventName = m.Groups["event"].Value;
            var unsupportedReturn = Regex.Matches(body, @"\breturn\s+(?<expr>[^;]+);")
                .Cast<Match>()
                .Any(r =>
                {
                    var expr = r.Groups["expr"].Value.Trim();
                    return expr is not "true" and not "false" &&
                           !Regex.IsMatch(expr, @"^base\.Render\(\s*" + Regex.Escape(eventName) + @"\s*\)$");
                });
            if (unsupportedReturn)
                continue;

            body = Regex.Replace(body,
                @"\breturn\s+base\.Render\(\s*" + Regex.Escape(eventName) + @"\s*\)\s*;",
                "base.Render(" + eventName + ");");
            body = Regex.Replace(body, @"\breturn\s+(?:true|false)\s*;", "return;");
            var newSig = m.Groups["sig"].Value + "void" + m.Groups["tail"].Value;
            working = working[..m.Index] + newSig + working[(m.Index + m.Length)..(open + 1)] +
                      body + working[close..];
            edits++;
        }
        return working;
    }

    static string FixTakeDamageTextBuilder(string content, ref int edits)
    {
        var local = 0;
        var next = TakeDamageBuilder.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) || HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            var builder = m.Groups["builder"].Value;
            var amount = m.Groups["amount"].Value;
            if (!Regex.IsMatch(content, @"\bint\s+" + Regex.Escape(amount) + @"\b") ||
                !Regex.IsMatch(content,
                    @"\b(?:TextBuilder|var)\s+" + Regex.Escape(builder) + @"\s*=\s*TextBuilder\.Get\s*\("))
                return m.Value;
            local++;
            return ".TakeDamage(ref " + amount + ", " + builder + ".ToString(),";
        });
        edits += local;
        return next;
    }

    static string FixDeepCopyConstructors(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?<head>override\s+IPart\s+DeepCopy\s*\(\s*GameObject\s+(?<parent>[A-Za-z_]\w*)\s*\)[^{]*\{(?:(?!\}).){0,300}?\b(?<type>[A-Za-z_]\w*)\s+(?<local>[A-Za-z_]\w*)\s*=\s*)new\s+\k<type>\s*\(\s*\k<parent>\s*\)",
            RegexOptions.Compiled | RegexOptions.Singleline);
        var localEdits = 0;
        var next = rx.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) || HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            localEdits++;
            return m.Groups["head"].Value + "base.DeepCopy(" + m.Groups["parent"].Value + ") as " +
                   m.Groups["type"].Value;
        });
        edits += localEdits;
        return next;
    }

    static string FixLegacyZoneBuilderWrappers(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?<recv>[A-Za-z_]\w*)\.AddZoneBuilderOverride\(\s*new\s+ZoneBuilderOverride\s*\((?<args>[^;]+)\)\s*\)\s*;",
            RegexOptions.Compiled);
        return ReplaceOutsideComments(content, rx,
            m => m.Groups["recv"].Value + ".AddZoneBuilderOverride(" + m.Groups["args"].Value + ");",
            ref edits);
    }

    static string RemoveUnusedLiteralLocals(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?m)^[ \t]*(?:bool|int|string|char)\s+(?<name>flag\d*)\s*=\s*(?:true|false|null|-?\d+(?:\.\d+)?|""(?:[^""\\]|\\.)*""|'(?:[^'\\]|\\.)')\s*;[ \t]*(?<eol>\r?\n|$)",
            RegexOptions.Compiled | RegexOptions.IgnoreCase);
        var local = 0;
        var next = rx.Replace(content, m =>
        {
            var name = m.Groups["name"].Value;
            if (Regex.Matches(content, @"\b" + Regex.Escape(name) + @"\b").Count != 1)
                return m.Value;
            local++;
            return m.Groups["eol"].Value;
        });
        edits += local;
        return next;
    }

    static string InitializeReadOnlyDefaultFields(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?m)^(?<prefix>[ \t]*private\s+(?:int|long|float|double|bool|char)\s+(?<name>[A-Za-z_]\w*))\s*;",
            RegexOptions.Compiled);
        var local = 0;
        var next = rx.Replace(content, m =>
        {
            var name = m.Groups["name"].Value;
            if (Regex.Matches(content, @"\b" + Regex.Escape(name) + @"\b").Count < 2 ||
                Regex.IsMatch(content, @"\b" + Regex.Escape(name) + @"\s*(?:[+\-*/%]?=|\+\+|--)", RegexOptions.Multiline))
                return m.Value;
            var type = Regex.Match(m.Groups["prefix"].Value,
                @"\b(?<type>int|long|float|double|bool|char)\s+" + Regex.Escape(name) + @"$").Groups["type"].Value;
            var value = type == "bool" ? "false" : type == "char" ? "'\\0'" : "0";
            local++;
            return m.Groups["prefix"].Value + " = " + value + ";";
        });
        edits += local;
        return next;
    }

    static string ReplaceOutsideComments(
        string content, Regex regex, Func<Match, string> replacement, ref int edits)
    {
        var local = 0;
        var next = regex.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) || HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            local++;
            return replacement(m);
        });
        edits += local;
        return next;
    }
}
