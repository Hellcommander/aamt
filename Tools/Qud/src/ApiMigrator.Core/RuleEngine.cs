using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Applies curated auto-fix rules to file content and scans the resulting content for
/// remaining obsolete-API hits described by the dump. Mirrors the exact same regex engine
/// (System.Text.RegularExpressions) and matching semantics used by the PowerShell CLI, so
/// both tools produce identical results for the same rule/dump JSON files.
/// </summary>
public sealed class RuleEngine
{
    private static readonly TimeSpan MatchTimeout = TimeSpan.FromSeconds(2);
    /// <summary>Dump remaining-hit scan: fail fast so one bad pattern cannot pin a file.</summary>
    private static readonly TimeSpan DumpMatchTimeout = TimeSpan.FromMilliseconds(500);

    public sealed record CompiledRule(
        string Name,
        Regex Regex,
        string Replacement,
        string? DumpMember,
        string? Note,
        IReadOnlyList<string> EnsureUsings,
        string? RequiresSubstring);

    public sealed record CompiledPostEnsure(
        string Name,
        Regex IfRegex,
        IReadOnlyList<string> Usings);

    public sealed record CompiledDumpEntry(ObsoleteEntry Entry, Regex Regex, string? Needle);

    public List<CompiledRule> Rules { get; }
    public List<CompiledPostEnsure> PostEnsureUsings { get; }
    public List<CompiledDumpEntry> DumpEntries { get; }

    /// <summary>Regex timeouts / skipped rules from the last Apply/Scan (cleared per call).</summary>
    public List<string> Warnings { get; } = new();

    public RuleEngine(CuratedRulesFile rulesFile, ObsoleteDump dump)
    {
        Rules = rulesFile.Rules
            .Where(r => r.Enabled)
            .Select(r => new CompiledRule(
                r.Name,
                new Regex(r.Pattern, RegexOptions.Compiled, MatchTimeout),
                r.Replacement,
                r.DumpMember,
                r.Note,
                (IReadOnlyList<string>)(r.EnsureUsings ?? new List<string>()),
                string.IsNullOrWhiteSpace(r.RequiresSubstring) ? null : r.RequiresSubstring))
            .ToList();
        PostEnsureUsings = (rulesFile.PostEnsureUsings ?? new List<PostEnsureUsing>())
            .Select(p => new CompiledPostEnsure(
                p.Name,
                new Regex(p.IfPattern, RegexOptions.Compiled, MatchTimeout),
                (IReadOnlyList<string>)(p.Usings ?? new List<string>())))
            .ToList();
        DumpEntries = dump.Entries
            .Select(e => new CompiledDumpEntry(
                e,
                new Regex(e.SearchPattern, RegexOptions.Compiled, DumpMatchTimeout),
                TryGetDumpScanNeedle(e)))
            .ToList();
    }

    /// <summary>
    /// Cheap Ordinal gate before running a dump <see cref="ObsoleteEntry.SearchPattern"/>.
    /// Long identifier members only — short GameObject tokens (<c>a</c>/<c>Is</c>) stay unfiltered.
    /// </summary>
    public static string? TryGetDumpScanNeedle(ObsoleteEntry entry)
    {
        var m = entry.Member;
        if (m.Length < 4) return null;
        for (var i = 0; i < m.Length; i++)
        {
            var c = m[i];
            if (i == 0)
            {
                if (!(char.IsLetter(c) || c == '_')) return null;
            }
            else if (!(char.IsLetterOrDigit(c) || c == '_'))
            {
                return null;
            }
        }
        return m;
    }

    /// <summary>
    /// Applies every curated rule to <paramref name="content"/> in order, then inserts any
    /// required usings (from rule <c>ensureUsings</c> and file-wide <c>postEnsureUsings</c>).
    /// Using insertion only runs for <c>.cs</c> files.
    /// </summary>
    public (string NewContent, List<AppliedFix> Fixes) ApplyCuratedRules(
        string content, string? filePath = null,
        IEnumerable<string>? extraNullablePreserveTypes = null)
    {
        Warnings.Clear();
        var working = content;
        var fixes = new List<AppliedFix>();
        var pendingUsings = new HashSet<string>(StringComparer.Ordinal);
        var isCs = IsCSharpPath(filePath);
        var label = string.IsNullOrEmpty(filePath) ? "(content)" : Path.GetFileName(filePath);

        foreach (var rule in Rules)
        {
            if (rule.RequiresSubstring is not null &&
                working.IndexOf(rule.RequiresSubstring, StringComparison.Ordinal) < 0)
                continue;

            MatchCollection matches;
            try
            {
                matches = rule.Regex.Matches(working);
                if (matches.Count == 0) continue;
            }
            catch (RegexMatchTimeoutException)
            {
                Warnings.Add($"{label}: regex timeout on curated rule '{rule.Name}' (skipped)");
                continue;
            }

            fixes.Add(new AppliedFix { RuleName = rule.Name, Count = matches.Count });
            try
            {
                working = rule.Regex.Replace(working, rule.Replacement);
            }
            catch (RegexMatchTimeoutException)
            {
                fixes.RemoveAt(fixes.Count - 1);
                Warnings.Add($"{label}: regex timeout replacing curated rule '{rule.Name}' (skipped)");
                continue;
            }
            if (isCs)
            {
                foreach (var u in rule.EnsureUsings)
                    pendingUsings.Add(u);
            }
        }

        if (isCs)
        {
            foreach (var post in PostEnsureUsings)
            {
                try
                {
                    if (!post.IfRegex.IsMatch(working))
                        continue;
                }
                catch (RegexMatchTimeoutException)
                {
                    Warnings.Add($"{label}: regex timeout on post-ensure '{post.Name}' (skipped)");
                    continue;
                }
                foreach (var u in post.Usings)
                    pendingUsings.Add(u);
            }

            if (pendingUsings.Count > 0)
            {
                var (withUsings, inserted) = UsingInserter.EnsureUsings(working, pendingUsings);
                working = withUsings;
                if (inserted.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", inserted),
                        Count = inserted.Count,
                    });
                }
            }

            // CoQ Roslyn rejects NRTs / #nullable — those show up as truncated "file.cs'." MODWARNs.
            // Pass mod-wide enum names so cross-file enum? (TaskPriority?) is not stripped to CS1750.
            var (cleaned, nullableEdits) = NullableAnnotationCleaner.Clean(working, extraNullablePreserveTypes);
            if (nullableEdits > 0)
            {
                working = cleaned;
                fixes.Add(new AppliedFix
                {
                    RuleName = "strip nullable-ref annotations (#nullable / Type?)",
                    Count = nullableEdits,
                });
            }

            // CS0019 method-group Count (LINQ .Count without ()) — high-confidence only.
            var (countFixed, countEdits) = CountMethodGroupFixer.Fix(working);
            if (countEdits > 0)
            {
                working = countFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = "Count method-group → Count() (LINQ / IEnumerable)",
                    Count = countEdits,
                });
            }

            // Popup.ShowOptionList → PickOption when args map confidently.
            var (pickFixed, syncPick, asyncPick) = ShowOptionListFixer.Fix(working);
            if (syncPick + asyncPick > 0)
            {
                working = pickFixed;
                if (syncPick > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = ShowOptionListFixer.FixRuleName,
                        Count = syncPick,
                    });
                }
                if (asyncPick > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = ShowOptionListFixer.FixRuleNameAsync,
                        Count = asyncPick,
                    });
                }
            }

            // Last-resort simple Register(GameObject) → Register(GameObject, IEventRegistrar).
            var (regFixed, regEdits) = RegisterOverrideFixer.Fix(working);
            if (regEdits > 0)
            {
                working = regFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = RegisterOverrideFixer.FixRuleName,
                    Count = regEdits,
                });
            }

            // BitType.ReverseTranslateBit / ReverseCharTranslateBit → FetchBitByCode (ID vs color).
            var (bitFixed, bitId, bitColor, bitChar) = ReverseTranslateBitFixer.Fix(working);
            if (bitId + bitColor + bitChar > 0)
            {
                working = bitFixed;
                if (bitId > 0)
                    fixes.Add(new AppliedFix { RuleName = ReverseTranslateBitFixer.FixRuleNameId, Count = bitId });
                if (bitColor > 0)
                    fixes.Add(new AppliedFix { RuleName = ReverseTranslateBitFixer.FixRuleNameColor, Count = bitColor });
                if (bitChar > 0)
                    fixes.Add(new AppliedFix { RuleName = ReverseTranslateBitFixer.FixRuleNameChar, Count = bitChar });
            }

            // Obsolete string AddAction → InventoryAction object when args map.
            var (addFixed, addEdits) = AddActionFixer.Fix(working);
            if (addEdits > 0)
            {
                working = addFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = AddActionFixer.FixRuleName,
                    Count = addEdits,
                });
            }

            var (expFixed, expEdits) = CachedDoubleSemicolonExpansionFixer.Fix(working);
            if (expEdits > 0)
            {
                working = expFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = CachedDoubleSemicolonExpansionFixer.FixRuleName,
                    Count = expEdits,
                });
            }

            // StringBuilder local + AppendReputationDescription → TextBuilder.Get (no ReDoS regex).
            var (repFixed, repEdits) = AppendReputationDescriptionFixer.Fix(working);
            if (repEdits > 0)
            {
                working = repFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = AppendReputationDescriptionFixer.FixRuleName,
                    Count = repEdits,
                });
                pendingUsings.Add("XRL.World.Text");
                var (withRepUsing, repUsings) =
                    UsingInserter.EnsureUsings(working, new[] { "XRL.World.Text" });
                working = withRepUsing;
                if (repUsings.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", repUsings),
                        Count = repUsings.Count,
                    });
                }
            }

            // Extensions.Things / .Things(literal) → _T(=number.things:…=) when what is literal.
            var (thingsFixed, thingsEdits) = ThingsFixer.Fix(working);
            if (thingsEdits > 0)
            {
                working = thingsFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = ThingsFixer.FixRuleName,
                    Count = thingsEdits,
                });
                var (withThingsUsing, thingsUsings) =
                    UsingInserter.EnsureUsings(working, new[] { "XRL.World.Text" });
                working = withThingsUsing;
                if (thingsUsings.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", thingsUsings),
                        Count = thingsUsings.Count,
                    });
                }
            }

            // GameText: .t()/.its, DidX/XDidY/XDidYToZ, GetVerb, InitLowerIfArticle, pronouns,
            // interpolated $"{go.The}{go.ShortDisplayName}" (CS0618).
            var (gtFixed, gtEdits) = GameTextCallSiteFixer.Fix(working);
            if (gtEdits > 0)
            {
                working = gtFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = GameTextCallSiteFixer.FixRuleName,
                    Count = gtEdits,
                });
            }

            // Event.FinalizeString(TB) / AppendSigned / AddsRep 7-arg (Improved Mutations CS1503).
            var (tbFixed, tbFixes) = TextBuilderCsFixer.Fix(working);
            if (tbFixes.Count > 0)
            {
                working = tbFixed;
                fixes.AddRange(tbFixes);
            }

            // Current compiler signature repairs + healing for a few older malformed rewrites.
            var (modernFixed, modernEdits) = ModernCompilerFixer.Fix(working);
            if (modernEdits > 0)
            {
                working = modernFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = ModernCompilerFixer.FixRuleName,
                    Count = modernEdits,
                });
            }

            // CS1739: GetDisplayName(WithAnnotations:) → Annotations:
            var (gdnFixed, gdnEdits) = GetDisplayNameArgFixer.Fix(working);
            if (gdnEdits > 0)
            {
                working = gdnFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = GetDisplayNameArgFixer.FixRuleName,
                    Count = gdnEdits,
                });
            }

            // BaseMutation DisplayName=/Type= setters → remove (PreferXML Mutations.xml)
            var (mutSetFixed, mutSetEdits) = BaseMutationSetterFixer.Fix(working);
            if (mutSetEdits > 0)
            {
                working = mutSetFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = BaseMutationSetterFixer.FixRuleName,
                    Count = mutSetEdits,
                });
            }

            // MutationOnEquip ClassName="…" / Variant= → Mutation=
            var (moeFixed, moeEdits) = MutationOnEquipCsFixer.Fix(working);
            if (moeEdits > 0)
            {
                working = moeFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = MutationOnEquipCsFixer.FixRuleName,
                    Count = moeEdits,
                });
            }

            // Drank(..., StringBuilder, ...) → TextBuilder signature bump.
            var (drankFixed, drankEdits) = DrankOverrideFixer.Fix(working);
            if (drankEdits > 0)
            {
                working = drankFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = DrankOverrideFixer.FixRuleName,
                    Count = drankEdits,
                });
                pendingUsings.Add("XRL.World.Text");
                var (withUsings, inserted) = UsingInserter.EnsureUsings(working, pendingUsings);
                working = withUsings;
                if (inserted.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", inserted),
                        Count = inserted.Count,
                    });
                }
            }

            // recv.Capitalize() → Translator.InitUpper(recv)
            var (capFixed, capEdits) = CapitalizeFixer.Fix(working);
            if (capEdits > 0)
            {
                working = capFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = CapitalizeFixer.FixRuleName,
                    Count = capEdits,
                });
                pendingUsings.Add("XRL.Language");
                var (withUsings, inserted) = UsingInserter.EnsureUsings(working, pendingUsings);
                working = withUsings;
                if (inserted.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", inserted),
                        Count = inserted.Count,
                    });
                }
            }

            // [VariableObjectReplacer] / DelegateContext Target → VariableContext + GameObject Object
            var (vrFixed, vrAttr, vrSig) = VariableReplacerFixer.Fix(working);
            if (vrAttr + vrSig > 0)
            {
                working = vrFixed;
                if (vrAttr > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = VariableReplacerFixer.FixRuleNameAttr,
                        Count = vrAttr,
                    });
                }
                if (vrSig > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = VariableReplacerFixer.FixRuleNameSignature,
                        Count = vrSig,
                    });
                }
                pendingUsings.Add("XRL.World");
                pendingUsings.Add("XRL.World.Text.Delegates");
                pendingUsings.Add("XRL.World.Text.Attributes");
                var (withUsings, inserted) = UsingInserter.EnsureUsings(working, pendingUsings);
                working = withUsings;
                if (inserted.Count > 0)
                {
                    fixes.Add(new AppliedFix
                    {
                        RuleName = "ensure using: " + string.Join(", ", inserted),
                        Count = inserted.Count,
                    });
                }
            }

            // FinalRender(RenderEvent, bool) → FinalRender(RenderEvent) when Alt unused.
            var (frFixed, frEdits) = FinalRenderOverrideFixer.Fix(working);
            if (frEdits > 0)
            {
                working = frFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = FinalRenderOverrideFixer.FixRuleName,
                    Count = frEdits,
                });
            }

            // HarmonyPatch(typeof(removed minigame)) → Prepare/TargetMethod.
            var (dynFixed, dynEdits) = HarmonyDynamicPatchFixer.Fix(working);
            if (dynEdits > 0)
            {
                working = dynFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = HarmonyDynamicPatchFixer.FixRuleName,
                    Count = dynEdits,
                });
            }

            // Options.Sifrah* / AnySifrah if-blocks (minigames removed).
            var (sifFixed, sifEdits) = RemovedGameApiFixer.Fix(working);
            if (sifEdits > 0)
            {
                working = sifFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = RemovedGameApiFixer.FixRuleName,
                    Count = sifEdits,
                });
            }

            // Harmony Prefix/Postfix argument names must match the current target signature.
            var (harmonyParamFixed, harmonyParamEdits) = HarmonyPatchParameterFixer.Fix(working);
            if (harmonyParamEdits > 0)
            {
                working = harmonyParamFixed;
                fixes.Add(new AppliedFix
                {
                    RuleName = HarmonyPatchParameterFixer.FixRuleName,
                    Count = harmonyParamEdits,
                });
            }
        }

        return (working, fixes);
    }

    /// <summary>
    /// Scans content (normally AFTER curated rules have been applied) for anything the dump
    /// says is still obsolete, returning line numbers and the offending line text.
    /// Applies <see cref="HitFilter"/> suppressions (comments, GameText templates, etc.).
    /// Also appends Count method-group / tuple-Empty coalesce CS0019 notes from
    /// <see cref="CountMethodGroupFixer"/>, PreferXML / PreferHarmonyPatch guidance from
    /// <see cref="OverridePreferenceScanner"/>, liquid PreferXML from
    /// <see cref="LiquidXmlAdviceScanner"/> (C# only — XML <c>Weight=</c> is not a liquid field),
    /// Liquids.xml render hygiene from
    /// <see cref="LiquidXmlRenderAdviceScanner"/>, Worlds.xml Load/builder hygiene from
    /// <see cref="WorldsXmlAdviceScanner"/>, removed minigame types from
    /// <see cref="RemovedGameApiFixer"/>, and actionable <see cref="ManualAdvice"/>
    /// (never recommends adding <c>[Obsolete]</c>).
    /// </summary>
    public List<RemainingHit> ScanRemainingHits(string content) =>
        ScanRemainingHits(content, null);

    public List<RemainingHit> ScanRemainingHits(string content, string? filePath)
    {
        Warnings.Clear();
        var hits = new List<RemainingHit>();
        var isCs = IsCSharpPath(filePath);
        var ctx = HitFilter.BuildContext(content);
        foreach (var dr in DumpEntries)
        {
            if (dr.Needle is not null &&
                content.IndexOf(dr.Needle, StringComparison.Ordinal) < 0)
                continue;

            MatchCollection matches;
            try { matches = dr.Regex.Matches(content); }
            catch (RegexMatchTimeoutException)
            {
                Warnings.Add($"regex timeout scanning dump entry '{dr.Entry.FullName}' (skipped)");
                continue;
            }
            foreach (Match m in matches)
            {
                if (!HitFilter.ShouldReport(dr.Entry, content, m, ctx))
                    continue;

                hits.Add(new RemainingHit
                {
                    Line = GetLineNumber(content, m.Index),
                    Member = dr.Entry.FullName,
                    Message = dr.Entry.ObsoleteMessage,
                    NeedsManual = dr.Entry.NeedsManual,
                    Text = GetLineText(content, m.Index).Trim(),
                });
            }
        }

        if (isCs)
        {
            hits.AddRange(CountMethodGroupFixer.Scan(content));
            hits.AddRange(OverridePreferenceScanner.Scan(content));
            hits.AddRange(LiquidXmlAdviceScanner.Scan(content));
            hits.AddRange(TextBuilderHalfMigrationScanner.Scan(content));
            hits.AddRange(RemovedGameApiFixer.Scan(content));
        }

        hits.AddRange(LiquidXmlRenderAdviceScanner.Scan(content));
        hits.AddRange(WorldsXmlAdviceScanner.Scan(content));
        hits.AddRange(FactionsXmlAdviceScanner.Scan(content));
        hits.AddRange(PopulationXmlAdviceScanner.Scan(content));
        ManualAdvice.Enrich(hits);
        hits.Sort((a, b) => a.Line.CompareTo(b.Line));
        return hits;
    }

    private static bool IsCSharpPath(string? filePath)
    {
        if (string.IsNullOrEmpty(filePath)) return true; // content-only API: C# scanners (see ScanRemainingHits(content))
        return filePath.EndsWith(".cs", StringComparison.OrdinalIgnoreCase);
    }

    private static int GetLineNumber(string text, int index)
    {
        var count = 1;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            if (text[i] == '\n') count++;
        }
        return count;
    }

    private static string GetLineText(string text, int index)
    {
        var start = index <= 0 ? -1 : text.LastIndexOf('\n', index - 1);
        var end = text.IndexOf('\n', index);
        if (end < 0) end = text.Length;
        var s = start + 1;
        return s <= end && s >= 0 && s <= text.Length ? text.Substring(s, Math.Max(end - s, 0)) : "";
    }
}
