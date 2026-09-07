using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;

namespace ApiMigrator.Core;

/// <summary>
/// Compiles human-editable XML/JSON rule charts under <c>data/charts/</c> into
/// <c>curated_rewrite_rules.json</c>, and exports the reverse split for editing.
/// </summary>
public static class RuleChartCompiler
{
    public const string ChartsFolderName = "charts";
    public const string ManifestFileName = "manifest.json";
    public static readonly TimeSpan RegexTimeout = TimeSpan.FromSeconds(2);

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };

    public sealed class CompileOptions
    {
        public string ChartsDir { get; set; } = "";
        public string? OutPath { get; set; }
        public string? DataDir { get; set; }
        public string? ManagedDir { get; set; }
        public bool CheckOnly { get; set; }
        public bool UpdateVersionProfile { get; set; } = true;
        public string? MetaDescription { get; set; }
    }

    public sealed class CompileResult
    {
        public bool Ok { get; set; }
        public string? OutPath { get; set; }
        public int RuleCount { get; set; }
        public int NoteCount { get; set; }
        public int PostEnsureCount { get; set; }
        public List<string> Warnings { get; set; } = new();
        public List<string> Errors { get; set; } = new();
        public bool DiffersFromExisting { get; set; }
        public string? CompiledJson { get; set; }
        public string? ProfileDir { get; set; }
    }

    public sealed class ExportOptions
    {
        public string RulesPath { get; set; } = "";
        public string ChartsDir { get; set; } = "";
        public bool Overwrite { get; set; }
    }

    public sealed class ExportResult
    {
        public bool Ok { get; set; }
        public List<string> WrittenFiles { get; set; } = new();
        public List<string> Errors { get; set; } = new();
        public int RuleCount { get; set; }
        public int NoteCount { get; set; }
    }

    public static string DefaultChartsDir(string dataDir) =>
        Path.Combine(dataDir, ChartsFolderName);

    public static CompileResult Compile(CompileOptions options, Action<string>? log = null)
    {
        var result = new CompileResult();
        if (string.IsNullOrWhiteSpace(options.ChartsDir) || !Directory.Exists(options.ChartsDir))
        {
            result.Errors.Add($"Charts directory not found: {options.ChartsDir}");
            return result;
        }

        var manifestPath = Path.Combine(options.ChartsDir, ManifestFileName);
        if (!File.Exists(manifestPath))
        {
            result.Errors.Add($"Missing {ManifestFileName} in {options.ChartsDir}");
            return result;
        }

        RuleChartManifest? manifest;
        try
        {
            manifest = JsonSerializer.Deserialize<RuleChartManifest>(File.ReadAllText(manifestPath), JsonOpts);
        }
        catch (Exception ex)
        {
            result.Errors.Add($"Failed to parse manifest: {ex.Message}");
            return result;
        }

        if (manifest?.Files is null || manifest.Files.Count == 0)
        {
            result.Errors.Add("manifest.json has no files[] entries.");
            return result;
        }

        var notes = new Dictionary<string, string>(StringComparer.Ordinal);
        var rulesByName = new Dictionary<string, (RuleChartRule Rule, string Source)>(StringComparer.Ordinal);
        var postByName = new Dictionary<string, (RuleChartPostEnsureUsing P, string Source)>(StringComparer.Ordinal);
        string? chartVersion = null;
        string? chartBeta = null;

        foreach (var rel in manifest.Files)
        {
            var path = Path.Combine(options.ChartsDir, rel.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(path))
            {
                result.Errors.Add($"Chart file missing: {rel}");
                continue;
            }

            log?.Invoke($"Loading chart: {rel}");
            RuleChartFile chart;
            try
            {
                chart = LoadChart(path);
            }
            catch (Exception ex)
            {
                result.Errors.Add($"{rel}: {ex.Message}");
                continue;
            }

            if (!string.IsNullOrWhiteSpace(chart.GameFileVersion))
                chartVersion ??= chart.GameFileVersion;
            if (!string.IsNullOrWhiteSpace(chart.SteamBetaKey))
                chartBeta ??= chart.SteamBetaKey;

            if (chart.Notes is not null)
            {
                foreach (var n in chart.Notes)
                {
                    if (string.IsNullOrWhiteSpace(n.Name)) continue;
                    var key = n.Name.StartsWith('_') ? n.Name : "_" + n.Name;
                    if (notes.ContainsKey(key))
                        result.Warnings.Add($"Note '{key}' overridden by {rel}");
                    notes[key] = n.Text ?? "";
                }
            }

            if (chart.Rules is not null)
            {
                foreach (var r in chart.Rules)
                {
                    if (string.IsNullOrWhiteSpace(r.Name))
                    {
                        result.Errors.Add($"{rel}: rule missing Name");
                        continue;
                    }
                    if (string.IsNullOrEmpty(r.Pattern))
                    {
                        result.Errors.Add($"{rel}: rule '{r.Name}' missing Pattern");
                        continue;
                    }
                    if (r.Replacement is null)
                    {
                        result.Errors.Add($"{rel}: rule '{r.Name}' missing Replacement");
                        continue;
                    }

                    try
                    {
                        _ = new Regex(r.Pattern, RegexOptions.CultureInvariant, RegexTimeout);
                    }
                    catch (Exception ex)
                    {
                        result.Errors.Add($"{rel}: rule '{r.Name}' invalid pattern: {ex.Message}");
                        continue;
                    }

                    if (rulesByName.ContainsKey(r.Name))
                        result.Warnings.Add($"Rule '{r.Name}' overridden by {rel}");
                    rulesByName[r.Name] = (r, rel);
                }
            }

            if (chart.PostEnsureUsings is not null)
            {
                foreach (var p in chart.PostEnsureUsings)
                {
                    if (string.IsNullOrWhiteSpace(p.Name))
                    {
                        result.Errors.Add($"{rel}: PostEnsureUsing missing Name");
                        continue;
                    }
                    if (string.IsNullOrEmpty(p.IfPattern))
                    {
                        result.Errors.Add($"{rel}: PostEnsureUsing '{p.Name}' missing IfPattern");
                        continue;
                    }
                    try
                    {
                        _ = new Regex(p.IfPattern, RegexOptions.CultureInvariant, RegexTimeout);
                    }
                    catch (Exception ex)
                    {
                        result.Errors.Add($"{rel}: PostEnsureUsing '{p.Name}' invalid IfPattern: {ex.Message}");
                        continue;
                    }
                    if (postByName.ContainsKey(p.Name))
                        result.Warnings.Add($"PostEnsureUsing '{p.Name}' overridden by {rel}");
                    postByName[p.Name] = (p, rel);
                }
            }
        }

        if (result.Errors.Count > 0)
            return result;

        var orderedRules = rulesByName.Values
            .Select(x => x.Rule)
            .OrderBy(r => r.Order ?? int.MaxValue)
            .ThenBy(r => r.Name, StringComparer.Ordinal)
            .ToList();

        var fileVer = DumpVersionControl.TryGetManagedFileVersion(options.ManagedDir)
                      ?? chartVersion
                      ?? "unknown";
        var (beta, buildId) = DumpVersionControl.TryReadSteamBranch();
        beta ??= chartBeta;

        var root = new JsonObject();
        var meta = new JsonObject
        {
            ["description"] = options.MetaDescription
                ?? "Hand-verified, mechanically-safe find/replace rules applied by both the PowerShell CLI (Update-ObsoleteApis.ps1) and the C# ApiMigrator.Core engine used by the GUI. Compiled from data/charts/*.xml|*.json via ApiMigrator.Cli compile-rules. Regex syntax is .NET System.Text.RegularExpressions. Optional ensureUsings / requiresSubstring / enabled:false / postEnsureUsings as documented in data/charts/README.md.",
            ["gameFileVersion"] = fileVer,
            ["capturedDate"] = DateTime.Now.ToString("yyyy-MM-dd"),
        };
        if (beta is not null) meta["steamBetaKey"] = beta;
        if (buildId is not null) meta["steamBuildId"] = buildId;
        meta["notes"] = "Source of truth for edits: data/charts/ (compile-rules). Do not hand-edit this JSON except via compile.";
        root["_meta"] = meta;

        foreach (var kv in notes.OrderBy(k => k.Key, StringComparer.Ordinal))
        {
            root[kv.Key] = new JsonObject { ["note"] = kv.Value };
        }

        var rulesArr = new JsonArray();
        foreach (var r in orderedRules)
        {
            var obj = new JsonObject
            {
                ["name"] = r.Name,
                ["pattern"] = r.Pattern,
                ["replacement"] = r.Replacement,
            };
            if (!string.IsNullOrEmpty(r.DumpMember)) obj["dumpMember"] = r.DumpMember;
            else obj["dumpMember"] = (string?)null;
            if (r.EnsureUsings is { Count: > 0 })
            {
                var ua = new JsonArray();
                foreach (var u in r.EnsureUsings) ua.Add(u);
                obj["ensureUsings"] = ua;
            }
            if (!r.Enabled) obj["enabled"] = false;
            if (!string.IsNullOrEmpty(r.RequiresSubstring))
                obj["requiresSubstring"] = r.RequiresSubstring;
            if (r.Note is not null) obj["note"] = r.Note;
            else obj["note"] = (string?)null;
            rulesArr.Add(obj);
        }
        root["rules"] = rulesArr;

        if (postByName.Count > 0)
        {
            // Preserve first-seen / last-override insertion order (not alphabetical).
            var pa = new JsonArray();
            foreach (var p in postByName.Values.Select(x => x.P))
            {
                var uarr = new JsonArray();
                foreach (var u in p.Usings) uarr.Add(u);
                pa.Add(new JsonObject
                {
                    ["name"] = p.Name,
                    ["ifPattern"] = p.IfPattern,
                    ["usings"] = uarr,
                });
            }
            root["postEnsureUsings"] = pa;
        }

        var compiled = SerializeJsonNode(root);
        result.CompiledJson = compiled;
        result.RuleCount = orderedRules.Count;
        result.NoteCount = notes.Count;
        result.PostEnsureCount = postByName.Count;

        var outPath = options.OutPath;
        if (string.IsNullOrWhiteSpace(outPath) && !string.IsNullOrWhiteSpace(options.DataDir))
            outPath = Path.Combine(options.DataDir, DumpVersionControl.ActiveRulesFileName);
        result.OutPath = outPath;

        if (!string.IsNullOrWhiteSpace(outPath) && File.Exists(outPath))
        {
            try
            {
                var existing = NormalizeJson(File.ReadAllText(outPath));
                var next = NormalizeJson(compiled);
                result.DiffersFromExisting = !string.Equals(existing, next, StringComparison.Ordinal);
            }
            catch
            {
                result.DiffersFromExisting = true;
            }
        }
        else
        {
            result.DiffersFromExisting = true;
        }

        if (options.CheckOnly)
        {
            result.Ok = result.Errors.Count == 0;
            if (result.DiffersFromExisting)
                result.Warnings.Add("Compiled charts differ from existing curated_rewrite_rules.json — run compile-rules without --check.");
            return result;
        }

        if (string.IsNullOrWhiteSpace(outPath))
        {
            result.Errors.Add("No output path (--out or DataDir).");
            return result;
        }

        var dir = Path.GetDirectoryName(Path.GetFullPath(outPath));
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outPath, compiled);
        log?.Invoke($"Wrote {orderedRules.Count} rules → {outPath}");

        if (options.UpdateVersionProfile && !string.IsNullOrWhiteSpace(options.DataDir))
        {
            try
            {
                var profileDir = DumpVersionControl.SaveProfileFromActive(
                    options.DataDir, managedDir: options.ManagedDir,
                    notes: "Updated by compile-rules.");
                // Ensure charts mirror into profile (SaveProfileFromActive copies charts too once wired).
                result.ProfileDir = profileDir;
                log?.Invoke($"Version profile updated: {profileDir}");
            }
            catch (Exception ex)
            {
                result.Warnings.Add($"Profile update skipped: {ex.Message}");
            }
        }

        result.Ok = true;
        return result;
    }

    public static RuleChartFile LoadChart(string path)
    {
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (ext is ".json")
        {
            var chart = JsonSerializer.Deserialize<RuleChartFile>(File.ReadAllText(path), JsonOpts)
                        ?? throw new InvalidDataException("Empty JSON chart");
            return chart;
        }

        if (ext is ".xml")
            return LoadChartXml(path);

        throw new InvalidDataException($"Unsupported chart extension: {ext}");
    }

    public static RuleChartFile LoadChartXml(string path)
    {
        var doc = XDocument.Load(path, LoadOptions.PreserveWhitespace);
        var root = doc.Root ?? throw new InvalidDataException("XML chart has no root");
        if (!string.Equals(root.Name.LocalName, "RuleChart", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException($"Expected root <RuleChart>, got <{root.Name.LocalName}>");

        var chart = new RuleChartFile
        {
            GameFileVersion = Attr(root, "GameFileVersion"),
            SteamBetaKey = Attr(root, "SteamBetaKey"),
            Category = Attr(root, "Category"),
            Description = Attr(root, "Description"),
            Notes = new List<RuleChartNote>(),
            Rules = new List<RuleChartRule>(),
            PostEnsureUsings = new List<RuleChartPostEnsureUsing>(),
        };

        var notesEl = root.Element("Notes") ?? root.Elements().FirstOrDefault(e =>
            string.Equals(e.Name.LocalName, "Notes", StringComparison.OrdinalIgnoreCase));
        if (notesEl is not null)
        {
            foreach (var n in notesEl.Elements().Where(e =>
                         string.Equals(e.Name.LocalName, "Note", StringComparison.OrdinalIgnoreCase)))
            {
                chart.Notes.Add(new RuleChartNote
                {
                    Name = Attr(n, "Name") ?? "",
                    Text = ElementText(n),
                });
            }
        }

        // Also allow top-level <Note> outside <Notes> (for _notes.xml convenience).
        foreach (var n in root.Elements().Where(e =>
                     string.Equals(e.Name.LocalName, "Note", StringComparison.OrdinalIgnoreCase)))
        {
            chart.Notes.Add(new RuleChartNote
            {
                Name = Attr(n, "Name") ?? "",
                Text = ElementText(n),
            });
        }

        foreach (var r in root.Elements().Where(e =>
                     string.Equals(e.Name.LocalName, "Rule", StringComparison.OrdinalIgnoreCase)))
        {
            var enabledAttr = Attr(r, "Enabled");
            var enabled = enabledAttr is null
                          || !string.Equals(enabledAttr, "false", StringComparison.OrdinalIgnoreCase);
            int? order = null;
            if (int.TryParse(Attr(r, "Order"), out var o)) order = o;

            var ensure = r.Elements()
                .Where(e => string.Equals(e.Name.LocalName, "EnsureUsing", StringComparison.OrdinalIgnoreCase))
                .Select(ElementText)
                .Where(s => !string.IsNullOrWhiteSpace(s))
                .ToList();

            chart.Rules.Add(new RuleChartRule
            {
                Name = Attr(r, "Name") ?? "",
                DumpMember = Attr(r, "DumpMember"),
                Enabled = enabled,
                RequiresSubstring = Attr(r, "RequiresSubstring"),
                Order = order,
                Pattern = ChildText(r, "Pattern"),
                Replacement = ChildText(r, "Replacement"),
                Note = NullableChildText(r, "Note"),
                EnsureUsings = ensure.Count > 0 ? ensure! : null,
            });
        }

        foreach (var p in root.Elements().Where(e =>
                     string.Equals(e.Name.LocalName, "PostEnsureUsing", StringComparison.OrdinalIgnoreCase)))
        {
            var usings = p.Elements()
                .Where(e => string.Equals(e.Name.LocalName, "Using", StringComparison.OrdinalIgnoreCase))
                .Select(ElementText)
                .Where(s => !string.IsNullOrWhiteSpace(s))
                .Select(s => s!)
                .ToList();
            chart.PostEnsureUsings.Add(new RuleChartPostEnsureUsing
            {
                Name = Attr(p, "Name") ?? "",
                IfPattern = Attr(p, "IfPattern") ?? ChildText(p, "IfPattern"),
                Usings = usings,
            });
        }

        return chart;
    }

    public static ExportResult Export(ExportOptions options, Action<string>? log = null)
    {
        var result = new ExportResult();
        if (!File.Exists(options.RulesPath))
        {
            result.Errors.Add($"Rules file not found: {options.RulesPath}");
            return result;
        }

        JsonObject root;
        try
        {
            root = JsonNode.Parse(File.ReadAllText(options.RulesPath)) as JsonObject
                   ?? throw new InvalidDataException("Not a JSON object");
        }
        catch (Exception ex)
        {
            result.Errors.Add($"Parse failed: {ex.Message}");
            return result;
        }

        Directory.CreateDirectory(options.ChartsDir);
        if (!options.Overwrite && Directory.EnumerateFileSystemEntries(options.ChartsDir).Any())
        {
            // Allow overwrite of known chart outputs; refuse only if non-empty and not overwrite
            // when any .xml already exists that we didn't create in this run — user must pass overwrite.
            var existing = Directory.GetFiles(options.ChartsDir, "*.*", SearchOption.TopDirectoryOnly);
            if (existing.Length > 0)
            {
                result.Errors.Add($"Charts dir not empty (pass Overwrite / --force): {options.ChartsDir}");
                return result;
            }
        }

        var meta = root["_meta"] as JsonObject;
        var gameVer = meta?["gameFileVersion"]?.GetValue<string>();
        var beta = meta?["steamBetaKey"]?.GetValue<string>();

        // Documentary underscore notes
        var noteItems = new List<RuleChartNote>();
        foreach (var prop in root)
        {
            if (prop.Key is "rules" or "postEnsureUsings" or "_meta") continue;
            if (!prop.Key.StartsWith('_')) continue;
            var noteObj = prop.Value as JsonObject;
            var text = noteObj?["note"]?.GetValue<string>() ?? prop.Value?.ToString() ?? "";
            noteItems.Add(new RuleChartNote { Name = prop.Key.TrimStart('_'), Text = text });
        }

        if (noteItems.Count > 0)
        {
            var notesPath = Path.Combine(options.ChartsDir, "_notes.xml");
            WriteNotesXml(notesPath, noteItems, gameVer, beta);
            result.WrittenFiles.Add(notesPath);
            result.NoteCount = noteItems.Count;
            log?.Invoke($"Wrote {noteItems.Count} notes → _notes.xml");
        }

        var rulesArr = root["rules"] as JsonArray;
        var categorized = new Dictionary<string, List<(int Order, RuleChartRule Rule)>>(StringComparer.Ordinal);
        var packOrder = new List<string>();

        void AddTo(string pack, int order, RuleChartRule rule)
        {
            if (!categorized.ContainsKey(pack))
            {
                categorized[pack] = new List<(int, RuleChartRule)>();
                packOrder.Add(pack);
            }
            categorized[pack].Add((order, rule));
        }

        if (rulesArr is not null)
        {
            for (var i = 0; i < rulesArr.Count; i++)
            {
                var o = rulesArr[i] as JsonObject;
                if (o is null) continue;
                var rule = JsonSerializer.Deserialize<RuleChartRule>(o.ToJsonString(), JsonOpts)
                           ?? new RuleChartRule();
                rule.Order = i;
                // enabled defaults true; Json may omit
                if (o.TryGetPropertyValue("enabled", out var en) && en is not null)
                    rule.Enabled = en.GetValue<bool>();
                else
                    rule.Enabled = true;

                var pack = CategorizeRule(rule);
                AddTo(pack, i, rule);
            }
        }

        var manifestFiles = new List<string>();
        if (noteItems.Count > 0)
            manifestFiles.Add("_notes.xml");

        foreach (var pack in packOrder)
        {
            var fileName = pack + ".xml";
            var path = Path.Combine(options.ChartsDir, fileName);
            var list = categorized[pack].OrderBy(x => x.Order).Select(x => x.Rule).ToList();
            WriteRulesXml(path, pack, list, gameVer, beta,
                description: $"Auto-exported pack '{pack}' from curated_rewrite_rules.json");
            result.WrittenFiles.Add(path);
            result.RuleCount += list.Count;
            manifestFiles.Add(fileName);
            log?.Invoke($"Wrote {list.Count} rules → {fileName}");
        }

        var postArr = root["postEnsureUsings"] as JsonArray;
        if (postArr is { Count: > 0 })
        {
            var posts = new List<RuleChartPostEnsureUsing>();
            foreach (var node in postArr)
            {
                if (node is not JsonObject o) continue;
                var p = JsonSerializer.Deserialize<RuleChartPostEnsureUsing>(o.ToJsonString(), JsonOpts);
                if (p is not null) posts.Add(p);
            }
            var postPath = Path.Combine(options.ChartsDir, "PostEnsureUsings.xml");
            WritePostEnsureXml(postPath, posts, gameVer, beta);
            result.WrittenFiles.Add(postPath);
            manifestFiles.Add("PostEnsureUsings.xml");
            log?.Invoke($"Wrote {posts.Count} postEnsureUsings → PostEnsureUsings.xml");
        }

        var manifest = new RuleChartManifest
        {
            Description = "Ordered chart packs. Later files override earlier Rules/Notes/PostEnsureUsings with the same Name. Compile with: ApiMigrator.Cli compile-rules",
            Files = manifestFiles,
        };
        var manifestPath = Path.Combine(options.ChartsDir, ManifestFileName);
        File.WriteAllText(manifestPath, JsonSerializer.Serialize(manifest, JsonOpts));
        result.WrittenFiles.Add(manifestPath);

        result.Ok = true;
        return result;
    }

    public static string CategorizeRule(RuleChartRule rule)
    {
        var n = rule.Name ?? "";
        if (!rule.Enabled) return "Disabled";
        if (n.Contains("Grammar.", StringComparison.Ordinal) || n.Contains("Translator.", StringComparison.Ordinal) && n.Contains("Grammar", StringComparison.Ordinal))
            return "Grammar";
        if (n.Contains("TextBuilder", StringComparison.Ordinal) || n.Contains("NewStringBuilder", StringComparison.Ordinal)
            || n.Contains("StringBuilder x = TextBuilder", StringComparison.Ordinal))
            return "TextBuilder";
        if (n.Contains("pPhysics", StringComparison.Ordinal) || n.Contains("pBrain", StringComparison.Ordinal)
            || n.Contains("pRender", StringComparison.Ordinal) || n.Contains("_pPhysics", StringComparison.Ordinal)
            || n.Contains("_pRender", StringComparison.Ordinal))
            return "PhysicsAccessors";
        if (n.Contains("GameObject.create", StringComparison.Ordinal) || n.Contains("FlushWantTurnTick", StringComparison.Ordinal))
            return "GameObject";
        if (n.Contains("Calendar.", StringComparison.Ordinal))
            return "Calendar";
        if (n.Contains("Reputation.", StringComparison.Ordinal) || n.Contains("Factions.", StringComparison.Ordinal)
            || n.Contains("Location2D.", StringComparison.Ordinal))
            return "ReputationFactions";
        if (n.Contains("ReplaceBuilder", StringComparison.Ordinal) || n.Contains("AddReplacer", StringComparison.Ordinal)
            || n.Contains("AddObject", StringComparison.Ordinal) || n.Contains("VariableReplacer", StringComparison.Ordinal)
            || n.Contains("DelegateContext", StringComparison.Ordinal))
            return "ReplaceBuilder";
        if (n.Contains("Liquid", StringComparison.Ordinal))
            return "Liquids";
        if (n.Contains("Capitalize", StringComparison.Ordinal))
            return "Capitalize";
        if (n.Contains("Dual_Wield", StringComparison.Ordinal) || n.Contains("Multiweapon", StringComparison.Ordinal))
            return "Skills";
        if (n.Contains("Wares", StringComparison.Ordinal) || n.Contains("builder", StringComparison.OrdinalIgnoreCase))
            return "Builders";
        if (n.Contains("Laterality", StringComparison.Ordinal) || n.Contains("Flipper", StringComparison.Ordinal)
            || n.Contains("Bodies", StringComparison.Ordinal))
            return "Bodies";
        if (n.Contains("population", StringComparison.OrdinalIgnoreCase) || n.Contains("Load=", StringComparison.Ordinal))
            return "Populations";
        return "Misc";
    }

    static void WriteNotesXml(string path, List<RuleChartNote> notes, string? gameVer, string? beta)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""<?xml version="1.0" encoding="utf-8"?>""");
        sb.Append("<RuleChart Encoding=\"utf-8\"");
        if (!string.IsNullOrEmpty(gameVer)) sb.Append($" GameFileVersion=\"{EscAttr(gameVer)}\"");
        if (!string.IsNullOrEmpty(beta)) sb.Append($" SteamBetaKey=\"{EscAttr(beta)}\"");
        sb.AppendLine(" Category=\"Notes\" Description=\"Documentary underscore notes for fixers / PreferXML / PreferHarmony (compiled into curated_rewrite_rules.json as _Name objects).\">");
        sb.AppendLine("  <Notes>");
        foreach (var n in notes.OrderBy(x => x.Name, StringComparer.Ordinal))
        {
            sb.AppendLine($"    <Note Name=\"{EscAttr(n.Name)}\">{CdataOrText(n.Text)}</Note>");
        }
        sb.AppendLine("  </Notes>");
        sb.AppendLine("</RuleChart>");
        File.WriteAllText(path, sb.ToString());
    }

    static void WriteRulesXml(string path, string category, List<RuleChartRule> rules, string? gameVer, string? beta, string description)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""<?xml version="1.0" encoding="utf-8"?>""");
        sb.Append("<RuleChart Encoding=\"utf-8\"");
        if (!string.IsNullOrEmpty(gameVer)) sb.Append($" GameFileVersion=\"{EscAttr(gameVer)}\"");
        if (!string.IsNullOrEmpty(beta)) sb.Append($" SteamBetaKey=\"{EscAttr(beta)}\"");
        sb.AppendLine($" Category=\"{EscAttr(category)}\" Description=\"{EscAttr(description)}\">");
        foreach (var r in rules)
        {
            sb.Append($"  <Rule Name=\"{EscAttr(r.Name)}\"");
            if (r.Order is int ord) sb.Append($" Order=\"{ord}\"");
            if (!string.IsNullOrEmpty(r.DumpMember)) sb.Append($" DumpMember=\"{EscAttr(r.DumpMember)}\"");
            if (!r.Enabled) sb.Append(" Enabled=\"false\"");
            if (!string.IsNullOrEmpty(r.RequiresSubstring))
                sb.Append($" RequiresSubstring=\"{EscAttr(r.RequiresSubstring)}\"");
            sb.AppendLine(">");
            sb.AppendLine($"    <Pattern>{CdataOrText(r.Pattern)}</Pattern>");
            sb.AppendLine($"    <Replacement>{CdataOrText(r.Replacement)}</Replacement>");
            if (r.EnsureUsings is { Count: > 0 })
            {
                foreach (var u in r.EnsureUsings)
                    sb.AppendLine($"    <EnsureUsing>{EscText(u)}</EnsureUsing>");
            }
            if (!string.IsNullOrEmpty(r.Note))
                sb.AppendLine($"    <Note>{CdataOrText(r.Note)}</Note>");
            sb.AppendLine("  </Rule>");
        }
        sb.AppendLine("</RuleChart>");
        File.WriteAllText(path, sb.ToString());
    }

    static void WritePostEnsureXml(string path, List<RuleChartPostEnsureUsing> posts, string? gameVer, string? beta)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""<?xml version="1.0" encoding="utf-8"?>""");
        sb.Append("<RuleChart Encoding=\"utf-8\"");
        if (!string.IsNullOrEmpty(gameVer)) sb.Append($" GameFileVersion=\"{EscAttr(gameVer)}\"");
        if (!string.IsNullOrEmpty(beta)) sb.Append($" SteamBetaKey=\"{EscAttr(beta)}\"");
        sb.AppendLine(" Category=\"PostEnsureUsings\" Description=\"File-wide using hygiene after curated rewrites.\">");
        foreach (var p in posts)
        {
            sb.AppendLine($"  <PostEnsureUsing Name=\"{EscAttr(p.Name)}\" IfPattern=\"{EscAttr(p.IfPattern)}\">");
            foreach (var u in p.Usings)
                sb.AppendLine($"    <Using>{EscText(u)}</Using>");
            sb.AppendLine("  </PostEnsureUsing>");
        }
        sb.AppendLine("</RuleChart>");
        File.WriteAllText(path, sb.ToString());
    }

    static string? Attr(XElement el, string name) =>
        el.Attributes().FirstOrDefault(a =>
            string.Equals(a.Name.LocalName, name, StringComparison.OrdinalIgnoreCase))?.Value;

    static string ChildText(XElement parent, string name)
    {
        var el = parent.Elements().FirstOrDefault(e =>
            string.Equals(e.Name.LocalName, name, StringComparison.OrdinalIgnoreCase));
        return el is null ? "" : ElementText(el);
    }

    static string? NullableChildText(XElement parent, string name)
    {
        var el = parent.Elements().FirstOrDefault(e =>
            string.Equals(e.Name.LocalName, name, StringComparison.OrdinalIgnoreCase));
        if (el is null) return null;
        var t = ElementText(el);
        return string.IsNullOrEmpty(t) ? null : t;
    }

    static string ElementText(XElement el)
    {
        // Prefer concatenated text/CDATA (ignore nested element markup).
        var sb = new StringBuilder();
        foreach (var node in el.Nodes())
        {
            switch (node)
            {
                case XCData cd:
                    sb.Append(cd.Value);
                    break;
                case XText t:
                    sb.Append(t.Value);
                    break;
            }
        }
        return sb.ToString().Trim();
    }

    static string EscAttr(string s) =>
        s.Replace("&", "&amp;").Replace("\"", "&quot;").Replace("<", "&lt;").Replace(">", "&gt;");

    static string EscText(string s) =>
        s.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

    static string CdataOrText(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        // CDATA cannot contain ]]>
        if (s.Contains("]]>", StringComparison.Ordinal))
            return EscText(s);
        if (s.IndexOfAny(new[] { '<', '>', '&', '"' }) >= 0 || s.Contains('\\') || s.Contains('\n'))
            return $"<![CDATA[{s}]]>";
        return EscText(s);
    }

    /// <summary>Normalize JSON for --check compare (parse + re-serialize).</summary>
    public static string NormalizeJson(string json)
    {
        var node = JsonNode.Parse(json);
        return node is null ? json : SerializeJsonNode(node);
    }

    static string SerializeJsonNode(JsonNode node)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
        {
            node.WriteTo(writer);
        }
        return Encoding.UTF8.GetString(stream.ToArray()) + Environment.NewLine;
    }

    /// <summary>Copy charts directory (including promotions/) into a version profile.</summary>
    public static void CopyChartsDirectory(string sourceChartsDir, string destChartsDir)
    {
        if (!Directory.Exists(sourceChartsDir)) return;
        Directory.CreateDirectory(destChartsDir);
        foreach (var file in Directory.GetFiles(sourceChartsDir, "*.*", SearchOption.AllDirectories))
        {
            var rel = Path.GetRelativePath(sourceChartsDir, file);
            var dest = Path.Combine(destChartsDir, rel);
            var destParent = Path.GetDirectoryName(dest);
            if (!string.IsNullOrEmpty(destParent)) Directory.CreateDirectory(destParent);
            File.Copy(file, dest, overwrite: true);
        }
    }
}
