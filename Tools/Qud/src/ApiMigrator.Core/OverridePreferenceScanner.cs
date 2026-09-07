using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Flags mod <c>override</c> members that extend/replace game virtuals or entry data,
/// with tiered guidance: PreferXML → PreferHarmonyPatch → C# override only when there is no other option.
/// Report-only for complex cases; never deletes overrides. Simple <c>Register(GameObject)</c> bodies
/// may be auto-bumped by <see cref="RegisterOverrideFixer"/> (last resort under Apply).
/// </summary>
/// <remarks>
/// Never advise adding <c>[Obsolete]</c> to silence CS0672.
/// Carve-out: direct fixes inside the mod’s own methods are normal in-place edits.
/// WantEvent/HandleEvent/Register/FireEvent on the mod’s own IPart/Effect/BaseMutation/…
/// subclasses are the part’s event pipeline — not a vanilla-class replacement — so they
/// are not PreferHarmonyPatch noise. Overrides on a concrete vanilla type (Stomach, Brain, …)
/// are still flagged.
/// </remarks>
public static class OverridePreferenceScanner
{
    public const string PreferXmlMember = "PreferXML";
    public const string PreferHarmonyMember = "PreferHarmonyPatch";

    static readonly HashSet<string> PreferXmlNames = new(StringComparer.Ordinal)
    {
        "DisplayName", "GetDisplayName", "Type", "IsLiquid", "GetLiquidDescription",
    };

    static readonly HashSet<string> PreferHarmonyNames = new(StringComparer.Ordinal)
    {
        "Register", "Unregister", "FireEvent", "HandleEvent", "WantEvent",
        "Render", "FinalRender", "Drank", "Apply", "Remove", "Write", "Read", "FinalizeRead",
        "GetDescription", "Mutate", "Unmutate", "ChangeLevel", "CollectStats",
        // CS0672 tick hooks (WantHundred/Ten → WantTurnTick; Hundred/TenTurnTick → TurnTick)
        "WantHundredTurnTick", "WantTenTurnTick", "HundredTurnTick", "TenTurnTick",
        "WantTurnTick", "TurnTick",
        // IGameSystem: LoadGame→Read, SaveGame→Write (also listed as Write/Read above)
        "LoadGame", "SaveGame",
        "Vaporized", "BeforeRender",
    };

    /// <summary>
    /// Event-pipeline methods that are the correct C# extension point on a mod’s own part/effect.
    /// Still PreferHarmony when the class replaces a concrete vanilla type.
    /// </summary>
    static readonly HashSet<string> HarmonySkipOnExtensionBase = new(StringComparer.Ordinal)
    {
        "WantEvent", "HandleEvent", "Register", "Unregister", "FireEvent",
        "Drank",
    };

    static readonly HashSet<string> ExtensionBases = new(StringComparer.Ordinal)
    {
        "IPart", "IScribedPart", "IModPart", "IComposite",
        "Effect", "IEffect",
        "BaseMutation", "BaseCore", "IMutation",
        "IGameSystem", "IObjectBuilder", "IPlayerMutator",
        "BaseLiquidPart", "IObjectGasBehavior", "IBuilder",
    };

    static readonly HashSet<string> CuratedNames = new(StringComparer.Ordinal);

    static readonly Regex ClassDecl = new(
        @"\bclass\s+(?<cname>\w+)\s*(?::\s*(?<bases>[^{]+))?",
        RegexOptions.Compiled);

    static OverridePreferenceScanner()
    {
        foreach (var k in PreferXmlNames) CuratedNames.Add(k);
        foreach (var k in PreferHarmonyNames) CuratedNames.Add(k);
    }

    static readonly Regex OverrideDecl = new(
        @"\b(?:public|protected|internal|private)\s+(?:(?:new|sealed|unsafe|async)\s+)*override\s+(?:(?:async|unsafe)\s+)*(?:[\w.<>,\[\]\?]+\s+)+(?<name>[A-Za-z_]\w*)\s*(?<kind>[\(\{]|=>)",
        RegexOptions.Compiled);

    static readonly Regex OverrideDeclBare = new(
        @"(?<=^|[\{\};])\s*override\s+(?:(?:async|unsafe)\s+)*(?:[\w.<>,\[\]\?]+\s+)+(?<name>[A-Za-z_]\w*)\s*(?<kind>[\(\{]|=>)",
        RegexOptions.Compiled | RegexOptions.Multiline);

    // PreferXML report for remaining BaseMutation DisplayName/Type assigns (after autofix).
    static readonly Regex BaseMutationSetterAssign = new(
        @"\b(?:(?:this|base)\.)?(?<name>DisplayName|Type)\s*=\s*",
        RegexOptions.Compiled);

    static readonly Regex MutationClassHint = new(
        @"\bclass\s+\w+\s*:\s*[^{]*\b(?:BaseMutation|BaseCore|IMutation)\b",
        RegexOptions.Compiled);

    public static List<RemainingHit> Scan(string content)
    {
        var hits = new List<RemainingHit>();
        if (string.IsNullOrEmpty(content))
            return hits;

        var seen = new HashSet<(int Line, string Kind, string Name)>();

        void Consider(Match m)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return;

            var name = m.Groups["name"].Value;
            if (string.IsNullOrEmpty(name) || !CuratedNames.Contains(name))
                return;

            if (name == "Drank")
            {
                if (ClassIsExtensionBase(content, m.Index))
                    return;

                string drankKind;
                string drankMessage;
                string drankAdvice;
                if (ClassHasBase(content, m.Index, "BaseLiquid") &&
                    TryEnclosingClassName(content, m.Index, out var liqClass) &&
                    !LiquidDrankToPartFixer.IsVanillaLiquidClass(liqClass))
                {
                    drankKind = PreferXmlMember;
                    drankMessage = "PreferXML — own BaseLiquid.Drank belongs in Liquids.xml OnDrink / MessageOnDrink; do not add [Obsolete]";
                    drankAdvice = ManualAdvice.PreferXmlAdvice("Drank");
                }
                else
                {
                    drankKind = PreferHarmonyMember;
                    drankMessage = "PreferHarmonyPatch — prefer Prefix/Postfix; do not add [Obsolete]";
                    drankAdvice = ManualAdvice.PreferHarmonyAdvice("Drank");
                }

                var drankLine = GetLineNumber(content, m.Index);
                if (!seen.Add((drankLine, drankKind, name)))
                    return;
                hits.Add(new RemainingHit
                {
                    Line = drankLine,
                    Member = drankKind + "." + name,
                    Message = drankMessage,
                    Advice = drankAdvice,
                    NeedsManual = true,
                    Text = GetLineText(content, m.Index).Trim(),
                });
                return;
            }

            if (PreferHarmonyNames.Contains(name) &&
                HarmonySkipOnExtensionBase.Contains(name) &&
                ClassIsExtensionBase(content, m.Index))
                return;

            string kind;
            string message;
            string advice;
            if (PreferXmlNames.Contains(name))
            {
                kind = PreferXmlMember;
                message = "PreferXML — use game XML overlay/merge; do not add [Obsolete]";
                advice = ManualAdvice.PreferXmlAdvice(name);
            }
            else
            {
                kind = PreferHarmonyMember;
                message = "PreferHarmonyPatch — prefer Prefix/Postfix; do not add [Obsolete]";
                advice = ManualAdvice.PreferHarmonyAdvice(name);
            }

            var line = GetLineNumber(content, m.Index);
            if (!seen.Add((line, kind, name)))
                return;

            hits.Add(new RemainingHit
            {
                Line = line,
                Member = kind + "." + name,
                Message = message,
                Advice = advice,
                NeedsManual = true,
                Text = GetLineText(content, m.Index).Trim(),
            });
        }

        foreach (Match m in OverrideDecl.Matches(content))
            Consider(m);
        foreach (Match m in OverrideDeclBare.Matches(content))
            Consider(m);

        if (MutationClassHint.IsMatch(content))
        {
            foreach (Match m in BaseMutationSetterAssign.Matches(content))
            {
                if (HitFilter.IsInsideComment(content, m.Index) ||
                    HitFilter.IsInsideStringLiteral(content, m.Index))
                    continue;
                var name = m.Groups["name"].Value;
                if (!PreferXmlNames.Contains(name))
                    continue;
                var line = GetLineNumber(content, m.Index);
                if (!seen.Add((line, PreferXmlMember, name + "Assign")))
                    continue;
                hits.Add(new RemainingHit
                {
                    Line = line,
                    Member = PreferXmlMember + "." + name,
                    Message = "PreferXML — BaseMutation entry data belongs in Mutations.xml; do not add [Obsolete]",
                    Advice = ManualAdvice.PreferXmlAdvice(name),
                    NeedsManual = true,
                    Text = GetLineText(content, m.Index).Trim(),
                });
            }
        }

        hits.Sort((a, b) => a.Line.CompareTo(b.Line));
        return hits;
    }

    /// <summary>
    /// Documentation stub for agents (not auto-written into mod files).
    /// </summary>
    public static string HarmonyStubTemplate(string targetType, string methodName) =>
        string.Join("\n",
            "// Extension mechanism only — PreferXML first if this is data.",
            "// Safer Harmony (Prefix/Postfix); C# override only when there is no other option.",
            "// Do not add [Obsolete] to silence CS0672.",
            $"[HarmonyPatch(typeof({targetType}), nameof({targetType}.{methodName}))]",
            $"public static class {targetType}_{methodName}_Patch",
            "{",
            $"    public static void Postfix({targetType} __instance)",
            "    {",
            "        if (__instance == null) return;",
            "        // ... behavior formerly in override ...",
            "    }",
            "}");

    /// <summary>
    /// True when the override sits on a mod extension base (IPart / Effect / BaseMutation / *Part / *Effect),
    /// not a concrete vanilla replacement type.
    /// </summary>
    public static bool ClassIsExtensionBase(string content, int index)
    {
        Match? last = null;
        foreach (Match m in ClassDecl.Matches(content))
        {
            if (m.Index >= index) break;
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            last = m;
        }
        if (last is null || !last.Groups["bases"].Success)
            return false;

        var basesRaw = last.Groups["bases"].Value;
        var whereAt = basesRaw.IndexOf(" where ", StringComparison.Ordinal);
        if (whereAt >= 0)
            basesRaw = basesRaw[..whereAt];

        foreach (var piece in SplitTopLevel(basesRaw, ','))
        {
            var simple = SimpleBaseName(piece);
            if (simple.Length == 0) continue;
            if (ExtensionBases.Contains(simple)) return true;
            if (simple.EndsWith("Part", StringComparison.Ordinal) ||
                simple.EndsWith("Effect", StringComparison.Ordinal))
                return true;
        }
        return false;
    }

    static bool ClassHasBase(string content, int index, string baseName)
    {
        Match? last = null;
        foreach (Match m in ClassDecl.Matches(content))
        {
            if (m.Index >= index) break;
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            last = m;
        }
        if (last is null || !last.Groups["bases"].Success)
            return false;
        return Regex.IsMatch(last.Groups["bases"].Value, @"\b" + Regex.Escape(baseName) + @"\b");
    }

    static bool TryEnclosingClassName(string content, int index, out string className)
    {
        className = "";
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
        className = last.Groups["cname"].Value;
        return className.Length > 0;
    }

    static string SimpleBaseName(string piece)
    {
        var t = piece.Trim();
        var lt = t.IndexOf('<');
        if (lt >= 0) t = t[..lt];
        t = t.Trim();
        var dot = t.LastIndexOf('.');
        return dot >= 0 ? t[(dot + 1)..] : t;
    }

    static IEnumerable<string> SplitTopLevel(string s, char sep)
    {
        var depth = 0;
        var start = 0;
        for (var i = 0; i < s.Length; i++)
        {
            var c = s[i];
            if (c == '<') depth++;
            else if (c == '>' && depth > 0) depth--;
            else if (c == sep && depth == 0)
            {
                yield return s[start..i];
                start = i + 1;
            }
        }
        if (start <= s.Length)
            yield return s[start..];
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
