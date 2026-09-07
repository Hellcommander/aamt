using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace ApiMigrator.Core;

/// <summary>
/// Human-editable needsManual promotion sheets under <c>data/charts/promotions/</c>.
/// Export candidates from the obsolete dump; mark <c>Status=Promote</c> with a ProposedRule;
/// apply to append curated chart rules and flip dump autoFixable flags.
/// </summary>
public static class PromotionChartCompiler
{
    public const string PromotionsFolderName = "promotions";
    public const string ManifestFileName = "manifest.json";
    public const string PromotedRulesChartFileName = "Promoted.xml";
    public static readonly TimeSpan RegexTimeout = TimeSpan.FromSeconds(2);

    public const string StatusCandidate = "Candidate";
    public const string StatusPromote = "Promote";
    public const string StatusSkip = "Skip";
    public const string StatusAdviceOnly = "AdviceOnly";

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };

    public sealed class PromotionEntry
    {
        public string DumpMember { get; set; } = "";
        public string Type { get; set; } = "";
        public string Member { get; set; } = "";
        public string Kind { get; set; } = "";
        public string Status { get; set; } = StatusCandidate;
        public string? Category { get; set; }
        public string? ObsoleteMessage { get; set; }
        public string? SearchPattern { get; set; }
        public string? Replacement { get; set; }
        public string? Notes { get; set; }
        public string? ProposedRuleName { get; set; }
        public string? ProposedPattern { get; set; }
        public string? ProposedReplacement { get; set; }
        public List<string>? EnsureUsings { get; set; }
        public string? RequiresSubstring { get; set; }
        public string? ProposedNote { get; set; }
    }

    public sealed class ExportOptions
    {
        public string DumpPath { get; set; } = "";
        public string PromotionsDir { get; set; } = "";
        public bool MergeExisting { get; set; } = true;
        public bool IncludeAutoFixable { get; set; }
        /// <summary>When false, only needsManual entries are exported (default).</summary>
        public bool NeedsManualOnly { get; set; } = true;
    }

    public sealed class ExportResult
    {
        public bool Ok { get; set; }
        public int EntryCount { get; set; }
        public int MergedFromExisting { get; set; }
        public List<string> WrittenFiles { get; set; } = new();
        public List<string> Errors { get; set; } = new();
    }

    public sealed class ApplyOptions
    {
        public string PromotionsDir { get; set; } = "";
        public string DumpPath { get; set; } = "";
        public string ChartsDir { get; set; } = "";
        public string? DataDir { get; set; }
        public string? ManagedDir { get; set; }
        public bool CompileRulesAfter { get; set; } = true;
        public bool UpdateVersionProfile { get; set; } = true;
        public bool DryRun { get; set; }
    }

    public sealed class ApplyResult
    {
        public bool Ok { get; set; }
        public int Promoted { get; set; }
        public int Skipped { get; set; }
        public int AdviceOnly { get; set; }
        public int Candidates { get; set; }
        public List<string> Warnings { get; set; } = new();
        public List<string> Errors { get; set; } = new();
        public string? PromotedChartPath { get; set; }
        public RuleChartCompiler.CompileResult? CompileResult { get; set; }
    }

    public static string DefaultPromotionsDir(string dataDir) =>
        Path.Combine(dataDir, RuleChartCompiler.ChartsFolderName, PromotionsFolderName);

    public static ExportResult Export(ExportOptions options, Action<string>? log = null)
    {
        var result = new ExportResult();
        if (!File.Exists(options.DumpPath))
        {
            result.Errors.Add($"Dump not found: {options.DumpPath}");
            return result;
        }

        ObsoleteDump dump;
        try
        {
            dump = DumpStore.LoadDump(options.DumpPath);
        }
        catch (Exception ex)
        {
            result.Errors.Add(ex.Message);
            return result;
        }

        var existing = new Dictionary<string, PromotionEntry>(StringComparer.Ordinal);
        if (options.MergeExisting && Directory.Exists(options.PromotionsDir))
        {
            foreach (var e in LoadAllEntries(options.PromotionsDir, result.Errors))
            {
                if (!string.IsNullOrEmpty(e.DumpMember))
                    existing[e.DumpMember] = e;
            }
            result.MergedFromExisting = existing.Count;
        }

        Directory.CreateDirectory(options.PromotionsDir);

        var gameVer = dump.Meta?.GameFileVersion;
        var beta = dump.Meta?.SteamBetaKey;
        var byPack = new Dictionary<string, List<PromotionEntry>>(StringComparer.Ordinal);
        var packOrder = new List<string>();

        foreach (var entry in dump.Entries)
        {
            if (options.NeedsManualOnly && !entry.NeedsManual && !(options.IncludeAutoFixable && entry.AutoFixable))
                continue;
            if (!options.NeedsManualOnly && !entry.NeedsManual && !entry.AutoFixable)
                continue;

            var dumpMember = string.IsNullOrEmpty(entry.FullName)
                ? $"{entry.Type}.{entry.Member}"
                : entry.FullName;
            // Prefer Type.Member without FullName property quirks
            dumpMember = $"{entry.Type}.{entry.Member}";

            var pe = new PromotionEntry
            {
                DumpMember = dumpMember,
                Type = entry.Type,
                Member = entry.Member,
                Kind = entry.Kind,
                Status = StatusCandidate,
                ObsoleteMessage = entry.ObsoleteMessage,
                SearchPattern = entry.SearchPattern,
                Replacement = entry.Replacement,
                Notes = entry.Notes,
                Category = CategorizeDumpEntry(entry),
            };

            if (existing.TryGetValue(dumpMember, out var prev))
            {
                // Preserve human decisions / proposed autofix from prior sheet.
                pe.Status = string.IsNullOrWhiteSpace(prev.Status) ? StatusCandidate : prev.Status;
                pe.ProposedRuleName = prev.ProposedRuleName;
                pe.ProposedPattern = prev.ProposedPattern;
                pe.ProposedReplacement = prev.ProposedReplacement;
                pe.EnsureUsings = prev.EnsureUsings;
                pe.RequiresSubstring = prev.RequiresSubstring;
                pe.ProposedNote = prev.ProposedNote;
                if (!string.IsNullOrWhiteSpace(prev.Category))
                    pe.Category = prev.Category;
                if (!string.IsNullOrWhiteSpace(prev.Notes) &&
                    (string.IsNullOrWhiteSpace(pe.Notes) || pe.Notes == entry.Notes))
                    pe.Notes = prev.Notes;
            }

            // Already auto-fixable in dump → mark Skip unless user set Promote
            if (entry.AutoFixable && !entry.NeedsManual &&
                string.Equals(pe.Status, StatusCandidate, StringComparison.OrdinalIgnoreCase))
            {
                pe.Status = StatusSkip;
            }

            var pack = pe.Category ?? "Other";
            if (!byPack.ContainsKey(pack))
            {
                byPack[pack] = new();
                packOrder.Add(pack);
            }
            byPack[pack].Add(pe);
        }

        var manifestFiles = new List<string>();
        foreach (var pack in packOrder.OrderBy(x => x, StringComparer.Ordinal))
        {
            var fileName = SanitizePackFileName(pack) + ".xml";
            var path = Path.Combine(options.PromotionsDir, fileName);
            var list = byPack[pack]
                .OrderBy(e => e.Type, StringComparer.Ordinal)
                .ThenBy(e => e.Member, StringComparer.Ordinal)
                .ToList();
            WritePromotionXml(path, pack, list, gameVer, beta);
            result.WrittenFiles.Add(path);
            result.EntryCount += list.Count;
            manifestFiles.Add(fileName);
            log?.Invoke($"Wrote {list.Count} entries → promotions/{fileName}");
        }

        var manifest = new RuleChartManifest
        {
            Description =
                "needsManual promotion sheets. Status=Candidate|Promote|Skip|AdviceOnly. " +
                "Fill ProposedRule then: ApiMigrator.Cli apply-promotions. Re-export merges prior Status/ProposedRule.",
            Files = manifestFiles,
        };
        var manifestPath = Path.Combine(options.PromotionsDir, ManifestFileName);
        File.WriteAllText(manifestPath, JsonSerializer.Serialize(manifest, JsonOpts));
        result.WrittenFiles.Add(manifestPath);

        // Keep a tiny README next to promotions (not in manifest).
        var readme = Path.Combine(options.PromotionsDir, "README.md");
        if (!File.Exists(readme))
            File.WriteAllText(readme, PromotionsReadmeText());

        result.Ok = true;
        return result;
    }

    public static ApplyResult Apply(ApplyOptions options, Action<string>? log = null)
    {
        var result = new ApplyResult();
        if (!Directory.Exists(options.PromotionsDir))
        {
            result.Errors.Add($"Promotions dir not found: {options.PromotionsDir}");
            return result;
        }
        if (!File.Exists(options.DumpPath))
        {
            result.Errors.Add($"Dump not found: {options.DumpPath}");
            return result;
        }

        var entries = LoadAllEntries(options.PromotionsDir, result.Errors);
        if (result.Errors.Count > 0) return result;

        ObsoleteDump dump;
        try
        {
            dump = DumpStore.LoadDump(options.DumpPath);
        }
        catch (Exception ex)
        {
            result.Errors.Add(ex.Message);
            return result;
        }

        var dumpByKey = new Dictionary<string, ObsoleteEntry>(StringComparer.Ordinal);
        foreach (var e in dump.Entries)
            dumpByKey[$"{e.Type}.{e.Member}"] = e;

        var toPromote = new List<PromotionEntry>();
        foreach (var pe in entries)
        {
            var status = (pe.Status ?? StatusCandidate).Trim();
            if (string.Equals(status, StatusPromote, StringComparison.OrdinalIgnoreCase))
            {
                if (string.IsNullOrWhiteSpace(pe.ProposedPattern) || pe.ProposedReplacement is null)
                {
                    result.Errors.Add(
                        $"Promote '{pe.DumpMember}' needs ProposedRule Pattern + Replacement.");
                    continue;
                }
                try
                {
                    _ = new Regex(pe.ProposedPattern, RegexOptions.CultureInvariant, RegexTimeout);
                }
                catch (Exception ex)
                {
                    result.Errors.Add($"Promote '{pe.DumpMember}' bad ProposedPattern: {ex.Message}");
                    continue;
                }
                toPromote.Add(pe);
                result.Promoted++;
            }
            else if (string.Equals(status, StatusSkip, StringComparison.OrdinalIgnoreCase))
            {
                result.Skipped++;
            }
            else if (string.Equals(status, StatusAdviceOnly, StringComparison.OrdinalIgnoreCase))
            {
                result.AdviceOnly++;
                if (dumpByKey.TryGetValue(pe.DumpMember, out var de))
                {
                    de.NeedsManual = true;
                    de.AutoFixable = false;
                    if (!string.IsNullOrWhiteSpace(pe.Notes))
                        de.Notes = pe.Notes;
                    if (!string.IsNullOrWhiteSpace(pe.SearchPattern))
                        de.SearchPattern = pe.SearchPattern!;
                }
            }
            else
            {
                result.Candidates++;
            }
        }

        if (result.Errors.Count > 0)
            return result;

        if (toPromote.Count == 0)
        {
            log?.Invoke("No Status=Promote entries with ProposedRule — nothing to promote.");
            if (!options.DryRun && result.AdviceOnly > 0)
            {
                DumpStore.SaveDump(options.DumpPath, dump);
                log?.Invoke($"Updated AdviceOnly flags on dump: {options.DumpPath}");
            }
            result.Ok = true;
            return result;
        }

        // Build / merge Promoted.xml chart rules
        var chartsDir = options.ChartsDir;
        Directory.CreateDirectory(chartsDir);
        var promotedPath = Path.Combine(chartsDir, PromotedRulesChartFileName);
        result.PromotedChartPath = promotedPath;

        var existingPromoted = new Dictionary<string, RuleChartRule>(StringComparer.Ordinal);
        if (File.Exists(promotedPath))
        {
            try
            {
                var chart = RuleChartCompiler.LoadChart(promotedPath);
                foreach (var r in chart.Rules ?? new())
                    existingPromoted[r.Name] = r;
            }
            catch (Exception ex)
            {
                result.Warnings.Add($"Could not read existing Promoted.xml: {ex.Message}");
            }
        }

        var nextOrder = existingPromoted.Values.Select(r => r.Order ?? 0).DefaultIfEmpty(9000).Max() + 1;
        foreach (var pe in toPromote)
        {
            var ruleName = !string.IsNullOrWhiteSpace(pe.ProposedRuleName)
                ? pe.ProposedRuleName!
                : $"{pe.Member} → autofix ({pe.Type})";

            var rule = new RuleChartRule
            {
                Name = ruleName,
                Order = existingPromoted.TryGetValue(ruleName, out var old) ? old.Order ?? nextOrder : nextOrder++,
                Pattern = pe.ProposedPattern!,
                Replacement = pe.ProposedReplacement!,
                DumpMember = pe.DumpMember,
                EnsureUsings = pe.EnsureUsings,
                RequiresSubstring = pe.RequiresSubstring,
                Note = pe.ProposedNote ?? pe.Notes ?? pe.ObsoleteMessage,
                Enabled = true,
            };
            existingPromoted[ruleName] = rule;

            if (dumpByKey.TryGetValue(pe.DumpMember, out var de))
            {
                de.NeedsManual = false;
                de.AutoFixable = true;
                de.SearchPattern = pe.ProposedPattern!;
                de.Replacement = InferSimpleReplacementToken(pe.ProposedReplacement!) ?? pe.Replacement;
                if (!string.IsNullOrWhiteSpace(pe.ProposedNote))
                    de.Notes = pe.ProposedNote;
                else if (!string.IsNullOrWhiteSpace(pe.Notes))
                    de.Notes = pe.Notes;
            }
            else
            {
                result.Warnings.Add($"Dump entry not found for '{pe.DumpMember}' — rule still added to Promoted.xml");
            }

            log?.Invoke($"Promote: {pe.DumpMember} → rule '{ruleName}'");
        }

        if (options.DryRun)
        {
            result.Ok = true;
            log?.Invoke($"Dry-run: would write {existingPromoted.Count} rules to Promoted.xml and update dump.");
            return result;
        }

        var gameVer = dump.Meta?.GameFileVersion
                      ?? DumpVersionControl.TryGetManagedFileVersion(options.ManagedDir);
        var beta = dump.Meta?.SteamBetaKey;
        WriteRulesChart(promotedPath, existingPromoted.Values
            .OrderBy(r => r.Order ?? int.MaxValue)
            .ThenBy(r => r.Name, StringComparer.Ordinal)
            .ToList(), gameVer, beta);

        EnsureManifestListsPromoted(chartsDir, log);

        DumpStore.SaveDump(options.DumpPath, dump);
        log?.Invoke($"Updated dump: {options.DumpPath}");

        // Mark promotion sheet entries that were applied as Skip (so re-apply is idempotent)
        RewritePromotionStatuses(options.PromotionsDir, toPromote.Select(p => p.DumpMember).ToHashSet(StringComparer.Ordinal), StatusSkip, log);

        if (options.CompileRulesAfter)
        {
            var dataDir = options.DataDir ?? Path.GetDirectoryName(Path.GetFullPath(options.DumpPath));
            result.CompileResult = RuleChartCompiler.Compile(new RuleChartCompiler.CompileOptions
            {
                ChartsDir = chartsDir,
                OutPath = dataDir is null ? null : Path.Combine(dataDir, DumpVersionControl.ActiveRulesFileName),
                DataDir = dataDir,
                ManagedDir = options.ManagedDir,
                CheckOnly = false,
                UpdateVersionProfile = options.UpdateVersionProfile,
            }, log);
            if (result.CompileResult.Errors.Count > 0)
            {
                result.Errors.AddRange(result.CompileResult.Errors);
                return result;
            }
        }

        if (options.UpdateVersionProfile && options.DataDir is not null)
        {
            try
            {
                DumpVersionControl.SaveProfileFromActive(options.DataDir, managedDir: options.ManagedDir,
                    notes: "Updated by apply-promotions.");
            }
            catch (Exception ex)
            {
                result.Warnings.Add($"Profile update: {ex.Message}");
            }
        }

        result.Ok = true;
        return result;
    }

    public static string CategorizeDumpEntry(ObsoleteEntry e)
    {
        var t = e.Type ?? "";
        // UI / nested types before broad "GameObject" substring (PickGameObjectScreen, etc.).
        if (t.StartsWith("Qud.UI", StringComparison.Ordinal) || t.Contains(".UI.", StringComparison.Ordinal)
            || t.StartsWith("ConsoleLib", StringComparison.Ordinal)) return "UI";
        if (t.Contains("Grammar", StringComparison.Ordinal) || t.StartsWith("XRL.Language", StringComparison.Ordinal))
            return "Language";
        if (t.Contains("GameText", StringComparison.Ordinal) || t.Contains("ReplaceBuilder", StringComparison.Ordinal)
            || t.Contains("TextBuilder", StringComparison.Ordinal) || t.StartsWith("XRL.World.Text", StringComparison.Ordinal))
            return "GameText";
        if (t.Contains("Liquid", StringComparison.Ordinal)) return "Liquids";
        if (t.StartsWith("HistoryKit", StringComparison.Ordinal) || t.Contains("Historic", StringComparison.Ordinal))
            return "HistoryKit";
        if (t.Contains("Mutation", StringComparison.Ordinal)) return "Mutations";
        if (t.StartsWith("XRL.World.Parts", StringComparison.Ordinal)) return "Parts";
        if (t.StartsWith("XRL.World.GameObject", StringComparison.Ordinal)
            || string.Equals(t, "XRL.World.GameObject", StringComparison.Ordinal)) return "GameObject";
        if (t.Contains("Calendar", StringComparison.Ordinal) || t.Contains("Faction", StringComparison.Ordinal)
            || t.Contains("Reputation", StringComparison.Ordinal)) return "World";
        if (t.Contains("XmlDataHelper", StringComparison.Ordinal) || t.StartsWith("XRL.Xml", StringComparison.Ordinal))
            return "XmlData";
        // Collapse noisy XRL_* singleton packs into coarser buckets when possible
        if (t.StartsWith("XRL.World.", StringComparison.Ordinal)) return "XRL_World";
        if (t.StartsWith("XRL.", StringComparison.Ordinal))
        {
            var parts = t.Split('.');
            if (parts.Length >= 2) return SanitizePackFileName(parts[0] + "_" + parts[1]);
        }
        var segs = t.Split('.');
        if (segs.Length >= 2) return SanitizePackFileName(segs[0] + "_" + segs[1]);
        return "Other";
    }

    static IEnumerable<PromotionEntry> LoadAllEntries(string promotionsDir, List<string> errors)
    {
        var manifestPath = Path.Combine(promotionsDir, ManifestFileName);
        IEnumerable<string> files;
        if (File.Exists(manifestPath))
        {
            try
            {
                var m = JsonSerializer.Deserialize<RuleChartManifest>(File.ReadAllText(manifestPath), JsonOpts);
                files = (m?.Files ?? new()).Select(f => Path.Combine(promotionsDir, f.Replace('/', Path.DirectorySeparatorChar)));
            }
            catch (Exception ex)
            {
                errors.Add($"manifest.json: {ex.Message}");
                yield break;
            }
        }
        else
        {
            files = Directory.GetFiles(promotionsDir, "*.xml").Concat(Directory.GetFiles(promotionsDir, "*.json"));
        }

        foreach (var path in files)
        {
            if (!File.Exists(path)) continue;
            if (string.Equals(Path.GetFileName(path), "README.md", StringComparison.OrdinalIgnoreCase)) continue;
            List<PromotionEntry> list;
            try
            {
                list = LoadPromotionFile(path);
            }
            catch (Exception ex)
            {
                errors.Add($"{Path.GetFileName(path)}: {ex.Message}");
                continue;
            }
            foreach (var e in list) yield return e;
        }
    }

    public static List<PromotionEntry> LoadPromotionFile(string path)
    {
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (ext == ".json")
        {
            var doc = JsonSerializer.Deserialize<PromotionJsonFile>(File.ReadAllText(path), JsonOpts)
                      ?? new PromotionJsonFile();
            return doc.Entries ?? new();
        }

        var root = XDocument.Load(path).Root
                   ?? throw new InvalidDataException("No root");
        if (!string.Equals(root.Name.LocalName, "PromotionChart", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException($"Expected <PromotionChart>, got <{root.Name.LocalName}>");

        var list = new List<PromotionEntry>();
        foreach (var el in root.Elements().Where(e =>
                     string.Equals(e.Name.LocalName, "Entry", StringComparison.OrdinalIgnoreCase)))
        {
            var pe = new PromotionEntry
            {
                DumpMember = Attr(el, "DumpMember") ?? "",
                Type = Attr(el, "Type") ?? "",
                Member = Attr(el, "Member") ?? "",
                Kind = Attr(el, "Kind") ?? "",
                Status = Attr(el, "Status") ?? StatusCandidate,
                Category = Attr(el, "Category"),
                ObsoleteMessage = ChildText(el, "ObsoleteMessage"),
                SearchPattern = ChildText(el, "SearchPattern"),
                Replacement = ChildText(el, "Replacement"),
                Notes = ChildText(el, "Notes"),
            };
            if (string.IsNullOrEmpty(pe.DumpMember) && !string.IsNullOrEmpty(pe.Type))
                pe.DumpMember = $"{pe.Type}.{pe.Member}";

            var pr = el.Elements().FirstOrDefault(e =>
                string.Equals(e.Name.LocalName, "ProposedRule", StringComparison.OrdinalIgnoreCase));
            if (pr is not null)
            {
                pe.ProposedRuleName = Attr(pr, "Name");
                pe.RequiresSubstring = Attr(pr, "RequiresSubstring");
                pe.ProposedPattern = ChildText(pr, "Pattern");
                pe.ProposedReplacement = ChildText(pr, "Replacement");
                pe.ProposedNote = ChildText(pr, "Note");
                var usings = pr.Elements()
                    .Where(e => string.Equals(e.Name.LocalName, "EnsureUsing", StringComparison.OrdinalIgnoreCase))
                    .Select(ElementText)
                    .Where(s => !string.IsNullOrWhiteSpace(s))
                    .Select(s => s!)
                    .ToList();
                if (usings.Count > 0) pe.EnsureUsings = usings;
            }
            list.Add(pe);
        }
        return list;
    }

    static void WritePromotionXml(string path, string category, List<PromotionEntry> entries, string? gameVer, string? beta)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""<?xml version="1.0" encoding="utf-8"?>""");
        sb.Append("<PromotionChart Encoding=\"utf-8\"");
        if (!string.IsNullOrEmpty(gameVer)) sb.Append($" GameFileVersion=\"{EscAttr(gameVer)}\"");
        if (!string.IsNullOrEmpty(beta)) sb.Append($" SteamBetaKey=\"{EscAttr(beta)}\"");
        sb.AppendLine($" Category=\"{EscAttr(category)}\" Description=\"needsManual promotion candidates — set Status=Promote and fill ProposedRule, then apply-promotions.\">");
        foreach (var e in entries)
        {
            sb.Append($"  <Entry DumpMember=\"{EscAttr(e.DumpMember)}\"");
            if (!string.IsNullOrEmpty(e.Type)) sb.Append($" Type=\"{EscAttr(e.Type)}\"");
            if (!string.IsNullOrEmpty(e.Member)) sb.Append($" Member=\"{EscAttr(e.Member)}\"");
            if (!string.IsNullOrEmpty(e.Kind)) sb.Append($" Kind=\"{EscAttr(e.Kind)}\"");
            sb.Append($" Status=\"{EscAttr(e.Status)}\"");
            if (!string.IsNullOrEmpty(e.Category)) sb.Append($" Category=\"{EscAttr(e.Category)}\"");
            sb.AppendLine(">");
            if (!string.IsNullOrEmpty(e.ObsoleteMessage))
                sb.AppendLine($"    <ObsoleteMessage>{Cdata(e.ObsoleteMessage)}</ObsoleteMessage>");
            if (!string.IsNullOrEmpty(e.SearchPattern))
                sb.AppendLine($"    <SearchPattern>{Cdata(e.SearchPattern)}</SearchPattern>");
            if (!string.IsNullOrEmpty(e.Replacement))
                sb.AppendLine($"    <Replacement>{Cdata(e.Replacement)}</Replacement>");
            if (!string.IsNullOrEmpty(e.Notes))
                sb.AppendLine($"    <Notes>{Cdata(e.Notes)}</Notes>");

            var hasProposed = !string.IsNullOrEmpty(e.ProposedPattern) || !string.IsNullOrEmpty(e.ProposedRuleName)
                              || e.ProposedReplacement is not null;
            if (hasProposed || string.Equals(e.Status, StatusPromote, StringComparison.OrdinalIgnoreCase))
            {
                sb.Append("    <ProposedRule");
                if (!string.IsNullOrEmpty(e.ProposedRuleName))
                    sb.Append($" Name=\"{EscAttr(e.ProposedRuleName)}\"");
                if (!string.IsNullOrEmpty(e.RequiresSubstring))
                    sb.Append($" RequiresSubstring=\"{EscAttr(e.RequiresSubstring)}\"");
                sb.AppendLine(">");
                if (!string.IsNullOrEmpty(e.ProposedPattern))
                    sb.AppendLine($"      <Pattern>{Cdata(e.ProposedPattern)}</Pattern>");
                if (e.ProposedReplacement is not null)
                    sb.AppendLine($"      <Replacement>{Cdata(e.ProposedReplacement)}</Replacement>");
                if (e.EnsureUsings is { Count: > 0 })
                {
                    foreach (var u in e.EnsureUsings)
                        sb.AppendLine($"      <EnsureUsing>{EscText(u)}</EnsureUsing>");
                }
                if (!string.IsNullOrEmpty(e.ProposedNote))
                    sb.AppendLine($"      <Note>{Cdata(e.ProposedNote)}</Note>");
                sb.AppendLine("    </ProposedRule>");
            }
            else
            {
                // Stub for editors — empty ProposedRule commented via placeholder Note on Entry
            }
            sb.AppendLine("  </Entry>");
        }
        sb.AppendLine("</PromotionChart>");
        File.WriteAllText(path, sb.ToString());
    }

    static void WriteRulesChart(string path, List<RuleChartRule> rules, string? gameVer, string? beta)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""<?xml version="1.0" encoding="utf-8"?>""");
        sb.Append("<RuleChart Encoding=\"utf-8\"");
        if (!string.IsNullOrEmpty(gameVer)) sb.Append($" GameFileVersion=\"{EscAttr(gameVer)}\"");
        if (!string.IsNullOrEmpty(beta)) sb.Append($" SteamBetaKey=\"{EscAttr(beta)}\"");
        sb.AppendLine(" Category=\"Promoted\" Description=\"Rules promoted from charts/promotions via apply-promotions. Edit here or re-promote.\">");
        foreach (var r in rules)
        {
            sb.Append($"  <Rule Name=\"{EscAttr(r.Name)}\"");
            if (r.Order is int o) sb.Append($" Order=\"{o}\"");
            if (!string.IsNullOrEmpty(r.DumpMember)) sb.Append($" DumpMember=\"{EscAttr(r.DumpMember)}\"");
            if (!r.Enabled) sb.Append(" Enabled=\"false\"");
            if (!string.IsNullOrEmpty(r.RequiresSubstring))
                sb.Append($" RequiresSubstring=\"{EscAttr(r.RequiresSubstring)}\"");
            sb.AppendLine(">");
            sb.AppendLine($"    <Pattern>{Cdata(r.Pattern)}</Pattern>");
            sb.AppendLine($"    <Replacement>{Cdata(r.Replacement)}</Replacement>");
            if (r.EnsureUsings is { Count: > 0 })
            {
                foreach (var u in r.EnsureUsings)
                    sb.AppendLine($"    <EnsureUsing>{EscText(u)}</EnsureUsing>");
            }
            if (!string.IsNullOrEmpty(r.Note))
                sb.AppendLine($"    <Note>{Cdata(r.Note)}</Note>");
            sb.AppendLine("  </Rule>");
        }
        sb.AppendLine("</RuleChart>");
        File.WriteAllText(path, sb.ToString());
    }

    static void EnsureManifestListsPromoted(string chartsDir, Action<string>? log)
    {
        var manifestPath = Path.Combine(chartsDir, RuleChartCompiler.ManifestFileName);
        RuleChartManifest manifest;
        if (File.Exists(manifestPath))
        {
            manifest = JsonSerializer.Deserialize<RuleChartManifest>(File.ReadAllText(manifestPath), JsonOpts)
                       ?? new RuleChartManifest();
        }
        else
        {
            manifest = new RuleChartManifest { Files = new() };
        }
        manifest.Files ??= new();
        if (!manifest.Files.Any(f => string.Equals(f, PromotedRulesChartFileName, StringComparison.OrdinalIgnoreCase)))
        {
            manifest.Files.Add(PromotedRulesChartFileName);
            File.WriteAllText(manifestPath, JsonSerializer.Serialize(manifest, JsonOpts));
            log?.Invoke($"Added {PromotedRulesChartFileName} to charts/manifest.json");
        }
    }

    static void RewritePromotionStatuses(string promotionsDir, HashSet<string> dumpMembers, string newStatus, Action<string>? log)
    {
        var manifestPath = Path.Combine(promotionsDir, ManifestFileName);
        if (!File.Exists(manifestPath)) return;
        var m = JsonSerializer.Deserialize<RuleChartManifest>(File.ReadAllText(manifestPath), JsonOpts);
        if (m?.Files is null) return;

        foreach (var rel in m.Files)
        {
            var path = Path.Combine(promotionsDir, rel);
            if (!File.Exists(path) || !path.EndsWith(".xml", StringComparison.OrdinalIgnoreCase)) continue;
            var entries = LoadPromotionFile(path);
            var changed = false;
            foreach (var e in entries)
            {
                if (dumpMembers.Contains(e.DumpMember))
                {
                    e.Status = newStatus;
                    changed = true;
                }
            }
            if (!changed) continue;
            var cat = entries.FirstOrDefault()?.Category ?? Path.GetFileNameWithoutExtension(path);
            // Preserve game ver from file if present
            string? gameVer = null, beta = null;
            try
            {
                var root = XDocument.Load(path).Root;
                gameVer = Attr(root!, "GameFileVersion");
                beta = Attr(root!, "SteamBetaKey");
            }
            catch { /* ignore */ }
            WritePromotionXml(path, cat ?? "Other", entries, gameVer, beta);
            log?.Invoke($"Marked applied entries Status={newStatus} in {rel}");
        }
    }

    /// <summary>If replacement is a simple identifier rename, store that token on the dump entry.</summary>
    static string? InferSimpleReplacementToken(string proposedReplacement)
    {
        var t = proposedReplacement.Trim();
        if (t.EndsWith('(')) t = t[..^1];
        if (Regex.IsMatch(t, @"^[\w\.]+$")) return t.TrimStart('.');
        return null;
    }

    static string SanitizePackFileName(string pack) =>
        Regex.Replace(pack.Trim(), @"[^\w\.\-]+", "_");

    static string? Attr(XElement el, string name) =>
        el.Attributes().FirstOrDefault(a =>
            string.Equals(a.Name.LocalName, name, StringComparison.OrdinalIgnoreCase))?.Value;

    static string? ChildText(XElement parent, string name)
    {
        var el = parent.Elements().FirstOrDefault(e =>
            string.Equals(e.Name.LocalName, name, StringComparison.OrdinalIgnoreCase));
        if (el is null) return null;
        var t = ElementText(el);
        return string.IsNullOrEmpty(t) ? null : t;
    }

    static string ElementText(XElement el)
    {
        var sb = new StringBuilder();
        foreach (var node in el.Nodes())
        {
            switch (node)
            {
                case XCData cd: sb.Append(cd.Value); break;
                case XText t: sb.Append(t.Value); break;
            }
        }
        return sb.ToString().Trim();
    }

    static string EscAttr(string s) =>
        s.Replace("&", "&amp;").Replace("\"", "&quot;").Replace("<", "&lt;").Replace(">", "&gt;");

    static string EscText(string s) =>
        s.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

    static string Cdata(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        if (s.Contains("]]>", StringComparison.Ordinal)) return EscText(s);
        return $"<![CDATA[{s}]]>";
    }

    static string PromotionsReadmeText() =>
        """
        # needsManual promotion sheets

        Exported from `obsolete_api_dump.json`. For each entry:

        | Status | Meaning |
        |--------|---------|
        | `Candidate` | Not decided yet (default) |
        | `Promote` | Fill `ProposedRule` Pattern/Replacement, then run `apply-promotions` |
        | `Skip` | Leave as dump advice / already handled |
        | `AdviceOnly` | Force dump `needsManual` (never autofix) |

        ```powershell
        dotnet run --project "..\..\..\src\ApiMigrator.Cli" -c Release -- export-promotions
        # edit Status + ProposedRule…
        dotnet run --project "..\..\..\src\ApiMigrator.Cli" -c Release -- apply-promotions
        ```

        Apply appends rules to `../Promoted.xml`, flips dump `autoFixable`, and runs `compile-rules`.
        Re-export merges prior Status / ProposedRule by DumpMember.
        """;

    sealed class PromotionJsonFile
    {
        public string? Category { get; set; }
        public List<PromotionEntry>? Entries { get; set; }
    }
}
