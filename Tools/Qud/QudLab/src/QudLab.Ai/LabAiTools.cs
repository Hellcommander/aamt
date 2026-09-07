using System.Text;
using System.Text.Json;
using QudLab.Assistant;
using QudLab.Core;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.Logs;
using QudLab.Indexer;
using QudLab.RoslynCompile;
using QudLab.Simulator;

namespace QudLab.Ai;

/// <summary>Cursor-like tools the local Ollama agent can call via <c>/api/chat</c>.</summary>
public sealed class LabAiTools
{
    readonly Func<IntelligenceCache?> _cache;
    readonly Func<QudInstallInfo?> _install;
    readonly Func<string?, string?> _read;
    readonly Action<string, string>? _write;
    readonly bool _allowWrite;
    readonly ActiveProjectManager? _projectManager;

    public LabAiTools(
        Func<IntelligenceCache?> cache,
        Func<QudInstallInfo?> install,
        Func<string?, string?> read,
        Action<string, string>? write,
        bool allowWrite,
        ActiveProjectManager? projectManager = null)
    {
        _cache = cache;
        _install = install;
        _read = read;
        _write = write;
        _allowWrite = allowWrite;
        _projectManager = projectManager;
    }

    public static IReadOnlyList<OllamaToolSpec> Specs(bool allowWrite)
    {
        var list = new List<OllamaToolSpec>
        {
            Fn("search", "Search the Qud intelligence cache for types, blueprints, mutations, or abilities. Use this instead of inventing XRL names.",
                Props(("q", "string", "Query text"), ("kind", "string", "all|type|blueprint|mutation|ability|genotype|subtype|pregen")),
                "q"),
            Fn("lookup_type", "Get one type node (methods/fields/base) from the cache.",
                Props(("name", "string", "Full or partial type name")),
                "name"),
            Fn("lookup_blueprint", "Get one ObjectBlueprint (inherits, parts, stats).",
                Props(("name", "string", "Blueprint name")),
                "name"),
            Fn("list_mods", "List installed LocalLow + Steam Workshop CoQ mods (id, title, path, cs count). Use before diagnosing MODERROR / type conflicts.",
                Props(("q", "string", "Optional filter by id/title/folder"))),
            Fn("set_project", "Switch the active AI/compile project to a LocalLow or Workshop mod path (or Workspace/src). Persists for serve.",
                Props(("path", "string", "Absolute mod folder, or mod id/title fragment")),
                "path"),
            Fn("mod_errors", "Read CoQ build_log.txt TYPE CONFLICTS + recent Player.log MODERROR lines. Call this for type-conflict MODERRORs.",
                Props()),
            Fn("game_logs", "Tail live CoQ logs: build_log TYPE CONFLICTS, Player.log (MODERROR/CTA/energy/pool), ThreadingAPI NDJSON.",
                Props(
                    ("kind", "string", "all | build | player | threading"),
                    ("tail", "integer", "Max lines, default 200"),
                    ("grep", "string", "Optional substring filter"))),
            Fn("event_pools", "Audit every MinEvent pool (base game + mod ModAssemblies/*.dll). Detects mod pooled-event bloat and FNV1A32 ID conflicts. Includes Player.log runtime pool counts when present.",
                Props(
                    ("scan", "boolean", "Rescan DLLs (default: use cache from qudlab index)"),
                    ("mod", "string", "Filter to mod folder/title fragment"),
                    ("q", "string", "Filter type/assembly name"),
                    ("cache", "string", "Pool | Singleton | None"),
                    ("top", "integer", "Max entries, default 60"))),
            Fn("list_files", "List source files in the ACTIVE project root (may be a real mod, not Workspace/src).", Props()),
            Fn("read_file", "Read one file relative to the active project root.",
                Props(("path", "string", "Path relative to active project")),
                "path"),
            Fn("grep", "Search all active-project .cs/.xml files for a string.",
                Props(("q", "string", "Substring to find")),
                "q"),
            Fn("scan_project", "Read EVERY active-project file plus last compile diagnostics and sim timeline.",
                Props()),
            Fn("compile", "Roslyn-compile the active project against the live Qud install. Returns diagnostics.",
                Props()),
            Fn("simulate", "Run the restricted debug simulator (not a playable game). scenario=chargen walks character generation. scenario=worldgen-getzone walks bootGame ResolveCell/GetZone (bug = IndexOf hang; stress = skip GetZoneEvent). scenario=crowd-load is an oversized map + many NPCs + simulated player. Default path is turn/energy/event bugs.",
                Props(
                    ("blueprint", "string", "Species/blueprint, default Human"),
                    ("turns", "integer", "Turn count after chargen/GetZone, default 8 (0 = pipeline only)"),
                    ("stress", "boolean", "crowd-load: ThreadingAPI offload of NPC think + LiquidVolume/IPowerTransmission TurnTick. Chargen: sweep. worldgen-getzone: skip GetZoneEvent"),
                    ("scenario", "string", "lag-diagnose | lag-suite | npc-cta-no-spend | move-input-lag | crowd-load | yd-load | chargen | worldgen-getzone | player-turn-starvation | cta-inf-turn | broodmother-bta-starve"),
                    ("genotype", "string", "Chargen genotype, e.g. Mutated Human or True Kin"),
                    ("subtype", "string", "Chargen calling/caste, e.g. Apostle or Horticulturist"),
                    ("chartype", "string", "New | Pregen | Random"),
                    ("pregen", "string", "Preset name from EmbarkModules.xml"),
                    ("mutations", "string", "Comma-separated mutation names for chargen"),
                    ("zone", "string", "Zone id for worldgen-getzone, or WxH map size for crowd-load"),
                    ("npcs", "integer", "crowd-load NPC count (default 64)"),
                    ("map", "string", "crowd-load map size WxH, e.g. 160x50 (vanilla is 80x25)"),
                    ("water", "boolean", "crowd-load city canal LiquidVolume ticks (default true)"),
                    ("pipes", "boolean", "crowd-load Yd HydraulicPowerTransmission pipes (default true)"),
                    ("yd", "boolean", "denser Yd Freehold pipe lattice"))),
            Fn("sim_timeline", "Return the last simulation timeline from cache.",
                Props())
        };
        if (allowWrite)
        {
            list.Add(Fn("write_file", "Write a complete file under the active project root (not a diff). Recompile afterwards.",
                Props(("path", "string", "Relative path"), ("content", "string", "Full file contents")),
                "path", "content"));
        }

        return list;
    }

    public string Execute(string name, JsonElement args, List<string> written, out bool compiledTouched)
    {
        compiledTouched = false;
        name = name.Trim().ToLowerInvariant();
        try
        {
            return name switch
            {
                "search" => Search(Str(args, "q"), Str(args, "kind") ?? "all"),
                "lookup_type" or "type" => LookupType(Str(args, "name") ?? Str(args, "q")),
                "lookup_blueprint" or "blueprint" => LookupBlueprint(Str(args, "name") ?? Str(args, "q")),
                "list_mods" or "mods" => ListMods(Str(args, "q") ?? Str(args, "query")),
                "set_project" or "project" => SetProject(Str(args, "path") ?? Str(args, "q") ?? Str(args, "mod")),
                "mod_errors" or "type_conflicts" or "conflicts" => ModErrors(),
                "game_logs" or "logs" => GameLogs(args),
                "event_pools" or "event_pool" or "pools" => EventPools(args),
                "list_files" => ListFiles(),
                "read_file" => ReadFile(Str(args, "path") ?? Str(args, "file")),
                "grep" => Grep(Str(args, "q") ?? Str(args, "query")),
                "scan_project" or "scan" => ScanProject(),
                "compile" => Compile(out compiledTouched),
                "simulate" or "sim" => Simulate(args),
                "sim_timeline" or "timeline" => Timeline(),
                "write_file" or "write" => WriteFile(Str(args, "path") ?? Str(args, "file"), Str(args, "content") ?? Str(args, "source"), written),
                _ => $"unknown tool '{name}'"
            };
        }
        catch (Exception ex)
        {
            return "tool error: " + ex.Message;
        }
    }

    string Search(string? q, string kind)
    {
        if (string.IsNullOrWhiteSpace(q))
            return "q required";
        var json = JsonSerializer.Serialize(CacheSearch.Search(_cache(), q, kind, 24), CacheIO.JsonOptions);
        return OllamaClient.Truncate(json, 6000);
    }

    string LookupType(string? name)
    {
        var cache = _cache();
        if (string.IsNullOrWhiteSpace(name) || cache is null)
            return "name required / cache missing";
        if (cache.TypeGraph.Types.TryGetValue(name, out var exact))
            return OllamaClient.Truncate(JsonSerializer.Serialize(exact, CacheIO.JsonOptions), 6000);
        var hits = cache.TypeGraph.Types
            .Where(kv => kv.Key.Contains(name, StringComparison.OrdinalIgnoreCase))
            .Take(8)
            .Select(kv => kv.Value)
            .ToList();
        return hits.Count == 0
            ? "not found: " + name
            : OllamaClient.Truncate(JsonSerializer.Serialize(hits, CacheIO.JsonOptions), 6000);
    }

    string LookupBlueprint(string? name)
    {
        var cache = _cache();
        if (string.IsNullOrWhiteSpace(name) || cache is null)
            return "name required / cache missing";
        if (cache.BlueprintGraph.Objects.TryGetValue(name, out var exact))
            return OllamaClient.Truncate(JsonSerializer.Serialize(exact, CacheIO.JsonOptions), 4000);
        var hits = cache.BlueprintGraph.Objects
            .Where(kv => kv.Key.Contains(name, StringComparison.OrdinalIgnoreCase))
            .Take(8)
            .Select(kv => kv.Value)
            .ToList();
        return hits.Count == 0
            ? "not found: " + name
            : OllamaClient.Truncate(JsonSerializer.Serialize(hits, CacheIO.JsonOptions), 4000);
    }

    string ListMods(string? query)
    {
        var install = _install()?.RootPath;
        var mods = QudModPaths.ListAllMods(install);
        if (!string.IsNullOrWhiteSpace(query))
        {
            mods = mods.Where(m =>
                    (m.Title?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
                    || (m.Id?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
                    || m.Name.Contains(query, StringComparison.OrdinalIgnoreCase)
                    || m.Path.Contains(query, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }

        var sb = new StringBuilder();
        sb.AppendLine("mods=" + mods.Count + " localLow=" + QudModPaths.LocalModsRoot());
        var ws = QudModPaths.WorkshopModsRoot(install);
        if (ws is not null)
            sb.AppendLine("workshop=" + ws);
        foreach (var m in mods.Take(120))
        {
            sb.AppendLine($"{m.Source}\t{m.Id ?? "-"}\t{m.Title ?? m.Name}\tcs={m.CsFileCount}\t{m.Path}");
        }

        if (mods.Count > 120)
            sb.AppendLine("…truncated");
        return sb.ToString();
    }

    string SetProject(string? pathOrQuery)
    {
        if (string.IsNullOrWhiteSpace(pathOrQuery))
            return "path required (absolute folder, mod id, or title fragment)";

        if (_projectManager is not null)
        {
            var result = _projectManager.Set(pathOrQuery);
            return result.Success
                ? "active project set to " + result.RootPath
                  + "\nid=" + (result.Id ?? "?")
                  + "\nfiles=" + result.FileCount
                  + "\n(persisted to " + QudModPaths.ConfigPath() + ")"
                : result.Error ?? "set failed";
        }

        string? resolved = null;
        if (Directory.Exists(pathOrQuery))
            resolved = Path.GetFullPath(pathOrQuery);
        else
        {
            var hit = QudModPaths.FindMod(pathOrQuery, _install()?.RootPath);
            resolved = hit?.Path;
        }

        if (string.IsNullOrWhiteSpace(resolved) || !Directory.Exists(resolved))
            return "mod/project not found: " + pathOrQuery;

        var cache = _cache();
        if (cache is null)
            return "cache missing — run qudlab index";

        CacheIO.ScanProject(cache.Project, resolved);
        CacheIO.Save(cache);
        var manifest = QudModPaths.ReadManifest(resolved);
        QudModPaths.SaveConfig(new ActiveProjectConfig
        {
            ProjectPath = resolved,
            ProjectName = QudModPaths.StripQudMarkup(manifest?.Title) ?? Path.GetFileName(resolved)
        });

        return "active project set to " + resolved
               + "\nid=" + (manifest?.Id ?? "?")
               + "\nfiles=" + cache.Project.Files.Count
               + "\n(persisted to " + QudModPaths.ConfigPath() + ")";
    }

    string GameLogs(JsonElement args)
    {
        var kind = Str(args, "kind") ?? "all";
        var tail = Int(args, "tail") ?? 200;
        var grep = Str(args, "grep") ?? Str(args, "q");
        var snap = GameLogTail.Snapshot(kind, tail, grep);
        return OllamaClient.Truncate(GameLogTail.FormatSnapshot(snap), 12000);
    }

    string EventPools(JsonElement args)
    {
        var top = Int(args, "top") ?? 60;
        var scan = Bool(args, "scan") ?? false;
        EventPoolAudit? audit = null;

        if (scan)
        {
            var install = _install();
            if (install is null)
                return "no install bound — run qudlab gate";
            audit = EventPoolAuditor.Audit(install);
            audit.RuntimePoolReport = EventPoolReport.TailRuntimePools(80);
            var cache = _cache();
            if (cache is not null)
            {
                cache.EventGraph.PoolAudit = audit;
                EventPoolAuditor.SaveAudit(audit);
                CacheIO.Save(cache);
            }
            else
            {
                EventPoolAuditor.SaveAudit(audit);
            }
        }
        else
        {
            audit = _cache()?.EventGraph.PoolAudit ?? EventPoolReport.LoadCached();
        }

        if (audit is null)
            return "no event pool audit — run qudlab index or event_pools scan=true";

        var payload = EventPoolReport.BuildResponse(
            audit,
            Str(args, "q"),
            Str(args, "mod"),
            Str(args, "cache") ?? Str(args, "kind"),
            top,
            true);

        var sb = new StringBuilder();
        sb.AppendLine($"event pools built={audit.BuiltAt:u}");
        sb.AppendLine($"total={audit.TotalEvents} pooled={audit.PooledCount} singleton={audit.SingletonCount}");
        sb.AppendLine($"modEvents={audit.ModEventCount} modPooled={audit.ModPooledCount} idConflicts={audit.IdConflicts.Count}");
        if (audit.IdConflicts.Count > 0)
        {
            sb.AppendLine("ID conflicts (duplicate FNV1A32 — can break pools):");
            foreach (var c in audit.IdConflicts.Take(12))
                sb.AppendLine($"  id={c.EventId} -> {string.Join(", ", c.Types.Take(4))}");
        }

        var modPooled = audit.Entries
            .Where(e => e.IsMod && e.CacheKind == "Pool" && !e.IsAbstract)
            .OrderBy(e => e.TypeFullName, StringComparer.OrdinalIgnoreCase)
            .Take(top)
            .ToList();
        if (modPooled.Count > 0)
        {
            sb.AppendLine("mod pooled events:");
            foreach (var e in modPooled)
                sb.AppendLine($"  {e.TypeFullName} [{e.Assembly}] {e.ModFolder}");
        }

        if (!string.IsNullOrWhiteSpace(audit.RuntimePoolReport))
        {
            sb.AppendLine();
            sb.AppendLine(audit.RuntimePoolReport);
        }

        if (audit.ScanErrors.Count > 0)
        {
            sb.AppendLine("scan errors:");
            foreach (var err in audit.ScanErrors.Take(8))
                sb.AppendLine("  " + err);
        }

        sb.AppendLine();
        sb.AppendLine("(json) " + OllamaClient.Truncate(JsonSerializer.Serialize(payload, CacheIO.JsonOptions), 4000));
        return OllamaClient.Truncate(sb.ToString(), 12000);
    }

    string ModErrors() =>
        OllamaClient.Truncate(QudModPaths.ReadTypeConflicts(), 12000);

    string ListFiles()
    {
        var cache = _cache();
        var files = cache?.Project.Files ?? new List<string>();
        return "root=" + (cache?.Project.RootPath ?? "?") + "\n" + string.Join("\n", files);
    }

    string ReadFile(string? path)
    {
        var rel = CodePatchParser.NormalizeRelPath(path) ?? path?.Replace('\\', '/').Trim();
        if (string.IsNullOrWhiteSpace(rel))
            return "path required";
        var text = _read(rel);
        return text is null ? "not found: " + rel : $"----- FILE {rel} -----\n{text}";
    }

    string Grep(string? q)
    {
        if (string.IsNullOrWhiteSpace(q))
            return "q required";
        var cache = _cache();
        var files = cache?.Project.Files ?? new List<string>();
        var sb = new StringBuilder();
        var hits = 0;
        foreach (var rel in files)
        {
            var text = _read(rel);
            if (text is null) continue;
            var lines = text.Replace("\r\n", "\n").Split('\n');
            for (var i = 0; i < lines.Length; i++)
            {
                if (lines[i].IndexOf(q, StringComparison.OrdinalIgnoreCase) < 0)
                    continue;
                sb.AppendLine($"{rel}:{i + 1}: {lines[i].Trim()}");
                hits++;
                if (hits >= 60)
                    return sb + "\n(truncated)";
            }
        }

        return hits == 0 ? "no matches" : sb.ToString();
    }

    public string ScanProject()
    {
        var cache = _cache();
        var sb = new StringBuilder();
        sb.AppendLine("SCAN PROJECT");
        sb.AppendLine("root=" + (cache?.Project.RootPath ?? "?"));
        var files = cache?.Project.Files ?? new List<string>();
        sb.AppendLine("files=" + files.Count);
        if (cache?.Project.Diagnostics is { Count: > 0 })
        {
            sb.AppendLine("Last diagnostics:");
            foreach (var d in cache.Project.Diagnostics.Take(40))
                sb.AppendLine("  " + d);
        }

        if (cache?.Simulation.Timeline is { Count: > 0 })
        {
            sb.AppendLine("Last sim timeline:");
            foreach (var e in cache.Simulation.Timeline.Take(30))
                sb.AppendLine($"  t{e.Turn} {e.Kind} {e.Label} {e.Detail}");
        }

        foreach (var rel in files)
        {
            var text = _read(rel) ?? "";
            sb.AppendLine();
            sb.AppendLine($"----- FILE {rel} -----");
            if (text.Length > 8000)
                sb.AppendLine(text[..8000] + "\n…(truncated)");
            else
                sb.AppendLine(text);
            if (sb.Length > 24000)
            {
                sb.AppendLine("…scan truncated for local-model context");
                break;
            }
        }

        return sb.ToString();
    }

    string Compile(out bool touched)
    {
        touched = true;
        var install = _install();
        var cache = _cache();
        var project = cache?.Project.RootPath;
        if (install is null)
            return "no install bound — run qudlab gate";
        if (string.IsNullOrWhiteSpace(project) || !Directory.Exists(project))
            return "project directory not found";

        var compiler = new QudModCompiler();
        var result = compiler.CompileProject(install, project);
        if (cache is not null)
        {
            QudModCompiler.ApplyDiagnosticsToCache(cache, result);
            CacheIO.Save(cache);
        }

        var sb = new StringBuilder();
        sb.AppendLine(result.Success ? "COMPILE OK" : "COMPILE FAILED");
        sb.AppendLine("refs=" + result.ReferenceCount);
        if (!string.IsNullOrEmpty(result.OutputPath))
            sb.AppendLine("out=" + result.OutputPath);
        foreach (var d in result.Diagnostics.Take(50))
            sb.AppendLine(d.ToString());
        return sb.ToString();
    }

    string Simulate(JsonElement args)
    {
        var install = _install();
        if (install is null)
            return "no install bound";
        var blueprint = Str(args, "blueprint") ?? "Human";
        var turns = Int(args, "turns") ?? 8;
        var stress = Bool(args, "stress") ?? false;
        var scenario = Str(args, "scenario");
        var genotype = Str(args, "genotype");
        var subtype = Str(args, "subtype");
        var chartype = Str(args, "chartype");
        var pregen = Str(args, "pregen");
        var mutations = StrList(args, "mutations");
        var cybernetics = StrList(args, "cybernetics");
        var zoneId = Str(args, "zone") ?? Str(args, "zoneId");
        var npcCount = Int(args, "npcs") ?? Int(args, "npcCount") ?? 0;
        var mapWidth = Int(args, "mapWidth") ?? 0;
        var mapHeight = Int(args, "mapHeight") ?? 0;
        var mapSpec = Str(args, "map");
        if (!string.IsNullOrWhiteSpace(mapSpec) && CrowdLoadScenario.TryParseMap(mapSpec, out var mw, out var mh))
        {
            mapWidth = mw;
            mapHeight = mh;
        }
        var lab = new LabHost();
        var gate = lab.Startup(install.RootPath);
        if (!gate.Ok)
            return "gate: " + gate.Message;

        var sim = SimulatorFactory.Create(lab, cacheProvider: _cache);
        var snap = sim.RunTurnsAsync(new SimRequest
        {
            BlueprintOrSpecies = blueprint,
            Turns = Math.Clamp(turns, 0, 40),
            RestrictedDebugOnly = true,
            Stress = stress,
            Scenario = scenario,
            Genotype = genotype,
            Subtype = subtype,
            Chartype = chartype,
            Pregen = pregen,
            Mutations = mutations,
            Cybernetics = cybernetics,
            ZoneId = zoneId,
            NpcCount = npcCount,
            MapWidth = mapWidth,
            MapHeight = mapHeight,
            WaterFlow = Bool(args, "water") ?? Bool(args, "waterFlow"),
            PowerPipes = Bool(args, "pipes") ?? Bool(args, "powerPipes"),
            YdDense = Bool(args, "yd") ?? Bool(args, "ydDense") ?? false
        }).GetAwaiter().GetResult();

        var cache = _cache();
        if (cache is not null)
        {
            sim.ApplySnapshotToCache(cache, snap, scenario);
            CacheIO.Save(cache);
        }

        var sb = new StringBuilder();
        sb.AppendLine($"simulate blueprint={blueprint} turns={snap.TurnsExecuted}" +
                      (string.IsNullOrWhiteSpace(scenario) ? "" : " scenario=" + scenario) +
                      (string.IsNullOrWhiteSpace(genotype) ? "" : " genotype=" + genotype) +
                      (string.IsNullOrWhiteSpace(subtype) ? "" : " subtype=" + subtype));
        foreach (var line in snap.Log.Take(40))
            sb.AppendLine(line);
        sb.AppendLine("timeline:");
        foreach (var e in snap.Timeline.Take(50))
            sb.AppendLine($"t{e.Turn} {e.Kind} {e.Label} {e.Detail}");
        return OllamaClient.Truncate(sb.ToString(), 8000);
    }

    string Timeline()
    {
        var cache = _cache();
        if (cache is null)
            return "no cache";
        var sb = new StringBuilder();
        foreach (var e in cache.Simulation.Timeline.Take(80))
            sb.AppendLine($"t{e.Turn} {e.Kind} {e.Label} {e.Detail}");
        foreach (var line in cache.Simulation.TurnLogs.Take(20))
            sb.AppendLine(line);
        return sb.Length == 0 ? "no timeline — run simulate first" : sb.ToString();
    }

    string WriteFile(string? path, string? content, List<string> written)
    {
        if (!_allowWrite || _write is null)
            return "writes disabled — use Fix mode (apply=true)";
        var rel = CodePatchParser.NormalizeRelPath(path);
        if (rel is null)
            return "invalid path (must be .cs/.xml under the active project)";
        if (content is null)
            return "content required";
        _write(rel, content);
        written.Add(rel);
        var cache = _cache();
        if (cache is not null && !string.IsNullOrWhiteSpace(cache.Project.RootPath))
        {
            CacheIO.ScanProject(cache.Project, cache.Project.RootPath);
            CacheIO.Save(cache);
        }

        return "wrote " + rel + " (" + content.Length + " chars)";
    }

    static OllamaToolSpec Fn(string name, string desc, object parameters, params string?[] required)
    {
        required ??= Array.Empty<string?>();
        var req = required.Where(s => !string.IsNullOrWhiteSpace(s)).Cast<string>().ToArray();
        return new OllamaToolSpec
        {
            Function = new OllamaToolFn
            {
                Name = name,
                Description = desc,
                Parameters = new
                {
                    type = "object",
                    properties = parameters,
                    required = req
                }
            }
        };
    }

    static object Props(params (string name, string type, string desc)[] fields)
    {
        var dict = new Dictionary<string, object>(StringComparer.Ordinal);
        foreach (var (name, type, desc) in fields)
            dict[name] = new { type, description = desc };
        return dict;
    }

    static IReadOnlyList<string> StrList(JsonElement args, string name)
    {
        if (args.ValueKind != JsonValueKind.Object)
            return Array.Empty<string>();
        if (!args.TryGetProperty(name, out var p))
            return Array.Empty<string>();
        if (p.ValueKind == JsonValueKind.Array)
        {
            var list = new List<string>();
            foreach (var e in p.EnumerateArray())
            {
                var s = e.GetString();
                if (!string.IsNullOrWhiteSpace(s))
                    list.Add(s.Trim());
            }

            return list;
        }

        var raw = p.ValueKind == JsonValueKind.String ? p.GetString() : p.ToString();
        if (string.IsNullOrWhiteSpace(raw))
            return Array.Empty<string>();
        return raw.Split(new[] { ',', ';' }, StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
    }

    static string? Str(JsonElement args, string name)
    {
        if (args.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
            return null;
        if (args.ValueKind == JsonValueKind.String)
            return args.GetString();
        if (args.TryGetProperty(name, out var p))
        {
            return p.ValueKind switch
            {
                JsonValueKind.String => p.GetString(),
                JsonValueKind.Number => p.ToString(),
                JsonValueKind.True => "true",
                JsonValueKind.False => "false",
                _ => p.ToString()
            };
        }

        return null;
    }

    static int? Int(JsonElement args, string name)
    {
        if (args.ValueKind != JsonValueKind.Object)
            return null;
        if (!args.TryGetProperty(name, out var p))
            return null;
        if (p.ValueKind == JsonValueKind.Number && p.TryGetInt32(out var n))
            return n;
        return int.TryParse(p.GetString(), out var s) ? s : null;
    }

    static bool? Bool(JsonElement args, string name)
    {
        if (args.ValueKind != JsonValueKind.Object)
            return null;
        if (!args.TryGetProperty(name, out var p))
            return null;
        return p.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            _ => bool.TryParse(p.GetString(), out var b) ? b : null
        };
    }
}
