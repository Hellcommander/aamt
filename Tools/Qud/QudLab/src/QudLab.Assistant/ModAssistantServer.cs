using System.Net;
using System.Text;
using System.Text.Json;
using QudLab.Core;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.Logs;
using QudLab.Core.References;
using QudLab.Indexer;
using QudLab.RoslynCompile;
using QudLab.Simulator;

namespace QudLab.Assistant;

/// <summary>
/// Local multi-client mod-assistant HTTP API (Cursor, Ollama, VS Code, Windsurf).
/// </summary>
public sealed class ModAssistantServer : IModAssistantHost
{
    readonly Func<IntelligenceCache?> _cacheProvider;
    readonly Func<QudInstallInfo?>? _installProvider;
    readonly Func<IQudAssetBinder?>? _assetsProvider;
    readonly Func<string?, string?>? _fileReader;
    readonly Action<string, string>? _fileWriter;
    readonly ActiveProjectManager? _projectManager;
    readonly ILabAiService? _ai;
    HttpListener? _listener;
    CancellationTokenSource? _cts;
    Task? _loop;

    public ModAssistantServer(
        Func<IntelligenceCache?> cacheProvider,
        int port = 47821,
        Func<string?, string?>? fileReader = null,
        Action<string, string>? fileWriter = null,
        Func<QudInstallInfo?>? installProvider = null,
        Func<IQudAssetBinder?>? assetsProvider = null,
        ILabAiService? ai = null,
        ActiveProjectManager? projectManager = null)
    {
        _cacheProvider = cacheProvider;
        Port = port;
        _fileReader = fileReader;
        _fileWriter = fileWriter;
        _installProvider = installProvider;
        _assetsProvider = assetsProvider;
        _ai = ai;
        _projectManager = projectManager;
    }

    public bool IsRunning => _listener?.IsListening == true;
    public int Port { get; }

    public Task StartAsync(CancellationToken ct = default)
    {
        if (IsRunning)
            return Task.CompletedTask;

        _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        _listener = new HttpListener();
        _listener.Prefixes.Add($"http://127.0.0.1:{Port}/");
        _listener.Start();
        _loop = Task.Run(() => ListenLoop(_cts.Token));
        return Task.CompletedTask;
    }

    public async Task StopAsync(CancellationToken ct = default)
    {
        try { _cts?.Cancel(); } catch { }
        try { _listener?.Stop(); } catch { }
        if (_loop is not null)
        {
            try { await _loop.WaitAsync(TimeSpan.FromSeconds(2), ct); } catch { }
        }
        _listener?.Close();
        _listener = null;
    }

    async Task ListenLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested && _listener is not null)
        {
            HttpListenerContext ctx;
            try
            {
                ctx = await _listener.GetContextAsync().WaitAsync(ct);
            }
            catch (OperationCanceledException) { break; }
            catch (HttpListenerException) { break; }
            catch { continue; }

            _ = Task.Run(() => Handle(ctx), ct);
        }
    }

    void Handle(HttpListenerContext ctx)
    {
        try
        {
            var path = ctx.Request.Url?.AbsolutePath.TrimEnd('/').ToLowerInvariant() ?? "/";
            var cache = _cacheProvider();
            var install = _installProvider?.Invoke();
            var qs = ctx.Request.QueryString;

            object payload = new { error = "unhandled" };
            int status = 200;

            switch (path)
            {
                case "":
                case "/":
                    payload = new
                    {
                        name = "QudLab Mod Assistant",
                        schema = CacheIO.CurrentSchemaVersion,
                        port = Port,
                        endpoints = new[]
                        {
                            "/health", "/cache/status", "/search", "/namespaces",
                            "/types", "/type", "/blueprints", "/blueprint",
                            "/mutations", "/abilities", "/events", "/events/pools", "/events/pools/scan", "/assets",
                            "/refs", "/assemblies", "/browse", "/compile", "/diagnostics",
                            "/mods", "/project", "/project/set", "/project/conflicts", "/project/rescan",
                            "/project/files", "/project/file", "/project/write",
                            "/logs/game", "/logs/conflicts",
                            "/simulate", "/simulate/scenarios",
                            "/simulation/logs", "/simulation/timeline", "/simulation/ingest",
                            "/genotypes", "/subtypes", "/catalogs",
                            "/ai/status", "/ai/models", "/ai/run", "/ai/ask", "/ai/scan", "/ai/fix", "/ai/analyze"
                        },
                        note = "ThreadingAPI is a separate WIP mod — not part of this service. POST /ai/run is the Cursor-like Ollama agent."
                    };
                    break;
                case "/health":
                    payload = new { ok = true, cache = cache is not null };
                    break;
                case "/cache/status":
                    payload = BuildCacheStatus(cache, install);
                    break;
                case "/search":
                    payload = CacheSearch.Search(cache, qs["q"], qs["kind"], ParseInt(qs["limit"], 40));
                    break;
                case "/namespaces":
                    payload = BuildNamespaces(cache);
                    break;
                case "/types":
                    payload = FilterTypes(cache, qs["q"], ParseInt(qs["limit"], 50));
                    break;
                case "/type":
                    payload = LookupType(cache, qs["name"] ?? qs["q"], out status);
                    break;
                case "/blueprints":
                    payload = FilterBlueprints(cache, qs["q"], ParseInt(qs["limit"], 50));
                    break;
                case "/blueprint":
                    payload = LookupBlueprint(cache, qs["name"] ?? qs["q"], out status);
                    break;
                case "/mutations":
                    payload = FilterMutations(cache, qs["q"], ParseInt(qs["limit"], 50));
                    break;
                case "/genotypes":
                    payload = FilterCatalog(cache, "genotype", qs["q"], ParseInt(qs["limit"], 80));
                    break;
                case "/subtypes":
                    payload = FilterCatalog(cache, "subtype", qs["q"], ParseInt(qs["limit"], 80));
                    break;
                case "/catalogs":
                    payload = FilterCatalog(cache, qs["kind"] ?? qs["source"] ?? "genotype", qs["q"], ParseInt(qs["limit"], 80));
                    break;
                case "/abilities":
                    payload = FilterAbilities(cache, qs["q"], ParseInt(qs["limit"], 50));
                    break;
                case "/events":
                    payload = cache?.EventGraph ?? new EventGraph();
                    break;
                case "/events/pools":
                    {
                        var audit = cache?.EventGraph.PoolAudit ?? EventPoolReport.LoadCached();
                        var top = ParseInt(qs["top"], 80);
                        var includeRuntime = !string.Equals(qs["runtime"], "false", StringComparison.OrdinalIgnoreCase);
                        payload = EventPoolReport.BuildResponse(
                            audit,
                            qs["q"],
                            qs["mod"],
                            qs["cache"] ?? qs["kind"],
                            top,
                            includeRuntime);
                        break;
                    }
                case "/events/pools/scan":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST to rescan MinEvent pools (base game + mod DLLs)" };
                            break;
                        }
                        if (install is null)
                        {
                            status = 503;
                            payload = new { error = "no install bound — run qudlab gate" };
                            break;
                        }
                        cache ??= _cacheProvider() ?? CacheIO.Load();
                        if (cache is null)
                        {
                            status = 503;
                            payload = new { error = "no cache — run qudlab index" };
                            break;
                        }
                        var audit = EventPoolAuditor.Audit(install);
                        audit.RuntimePoolReport = EventPoolReport.TailRuntimePools(80);
                        cache.EventGraph.PoolAudit = audit;
                        EventPoolAuditor.SaveAudit(audit);
                        CacheIO.Save(cache);
                        payload = EventPoolReport.BuildResponse(audit, null, null, null, 80, true);
                        break;
                    }
                case "/assets":
                    {
                        var binder = _assetsProvider?.Invoke();
                        if (binder is null || !binder.IsBound)
                        {
                            status = 503;
                            payload = new { error = "assets not bound — run gate/setup" };
                        }
                        else
                        {
                            var prefix = qs["prefix"] ?? "";
                            var limit = ParseInt(qs["limit"], 200);
                            payload = binder.ListAssetMetadata(prefix).Take(Math.Clamp(limit, 1, 2000)).ToList();
                        }
                        break;
                    }
                case "/refs":
                case "/assemblies":
                    {
                        var root = cache?.GameRoot ?? install?.RootPath;
                        if (string.IsNullOrWhiteSpace(root) || !GamePathResolver.LooksLikeQud(root, out var info))
                        {
                            status = 404;
                            payload = new { error = "no install bound — run qudlab gate && qudlab sync-refs" };
                        }
                        else
                        {
                            payload = QudReferenceSet.FromInstall(info).ToAssistantPayload();
                        }
                        break;
                    }
                case "/browse":
                    payload = BuildBrowse(cache, qs["ns"], qs["q"], ParseInt(qs["limit"], 80));
                    break;
                case "/mods":
                    {
                        var q = qs["q"];
                        var mods = _projectManager?.ListMods(q) ?? QudModPaths.ListAllMods(install?.RootPath);
                        if (!string.IsNullOrWhiteSpace(q) && _projectManager is null)
                        {
                            mods = mods.Where(m =>
                                    (m.Title?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                                    || (m.Id?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                                    || m.Name.Contains(q, StringComparison.OrdinalIgnoreCase))
                                .ToList();
                        }
                        payload = new
                        {
                            count = mods.Count,
                            localModsRoot = QudModPaths.LocalModsRoot(),
                            workshopRoot = QudModPaths.WorkshopModsRoot(install?.RootPath),
                            mods
                        };
                        break;
                    }
                case "/project":
                    if (string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        goto case "/project/set";
                    if (_projectManager is null)
                    {
                        payload = new
                        {
                            root = cache?.Project.RootPath,
                            fileCount = cache?.Project.Files.Count ?? 0
                        };
                    }
                    else
                    {
                        var info = _projectManager.Get();
                        payload = info;
                    }
                    break;
                case "/project/set":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST JSON { path?, query? }" };
                            break;
                        }
                        if (_projectManager is null)
                        {
                            status = 503;
                            payload = new { error = "project manager not configured" };
                            break;
                        }
                        using var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding);
                        var body = reader.ReadToEnd();
                        string? pathArg = qs["path"] ?? qs["query"];
                        if (!string.IsNullOrWhiteSpace(body))
                        {
                            try
                            {
                                using var doc = JsonDocument.Parse(body);
                                pathArg = JsonStr(doc.RootElement, "path", "query", "mod") ?? pathArg;
                            }
                            catch
                            {
                                status = 400;
                                payload = new { error = "invalid JSON body" };
                                break;
                            }
                        }
                        if (string.IsNullOrWhiteSpace(pathArg))
                        {
                            status = 400;
                            payload = new { error = "path or query required" };
                            break;
                        }
                        var result = _projectManager.Set(pathArg);
                        if (!result.Success)
                        {
                            status = 404;
                            payload = new { error = result.Error };
                        }
                        else
                        {
                            payload = new
                            {
                                ok = true,
                                rootPath = result.RootPath,
                                name = result.Name,
                                id = result.Id,
                                fileCount = result.FileCount
                            };
                        }
                        break;
                    }
                case "/project/conflicts":
                    payload = new { text = QudModPaths.ReadTypeConflicts() };
                    break;
                case "/project/rescan":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST to rescan active project files" };
                            break;
                        }
                        if (_projectManager is null)
                        {
                            status = 503;
                            payload = new { error = "project manager not configured" };
                            break;
                        }
                        var count = _projectManager.Rescan();
                        payload = new { ok = true, fileCount = count, root = _projectManager.Get().RootPath };
                        break;
                    }
                case "/logs/game":
                    {
                        var kind = qs["kind"] ?? "all";
                        var tail = ParseInt(qs["tail"], 200);
                        var grep = qs["grep"] ?? qs["q"];
                        var snap = GameLogTail.Snapshot(kind, tail, grep);
                        payload = snap;
                        break;
                    }
                case "/logs/conflicts":
                    payload = new { text = QudModPaths.ReadTypeConflicts() };
                    break;
                case "/simulate/scenarios":
                    payload = SimScenarioCatalog.All;
                    break;
                case "/diagnostics":
                    payload = new
                    {
                        diagnostics = cache?.Project.Diagnostics ?? new List<string>(),
                        projectRoot = cache?.Project.RootPath
                    };
                    break;
                case "/compile":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST JSON { project?: path } (empty = Workspace/src)" };
                            break;
                        }

                        if (install is null)
                        {
                            status = 503;
                            payload = new { error = "no install bound — run qudlab gate" };
                            break;
                        }

                        string? projectDir = null;
                        using (var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding))
                        {
                            var body = reader.ReadToEnd();
                            if (!string.IsNullOrWhiteSpace(body))
                            {
                                try
                                {
                                    using var doc = JsonDocument.Parse(body);
                                    if (doc.RootElement.TryGetProperty("project", out var pe))
                                        projectDir = pe.GetString();
                                }
                                catch
                                {
                                    status = 400;
                                    payload = new { error = "invalid JSON body" };
                                    break;
                                }
                            }
                        }

                        if (string.IsNullOrWhiteSpace(projectDir))
                            projectDir = cache?.Project.RootPath;

                        if (string.IsNullOrWhiteSpace(projectDir) || !Directory.Exists(projectDir))
                        {
                            status = 400;
                            payload = new { error = "project directory not found", project = projectDir };
                            break;
                        }

                        var compiler = new QudModCompiler();
                        var result = compiler.CompileProject(install, projectDir);
                        if (cache is not null)
                        {
                            QudModCompiler.ApplyDiagnosticsToCache(cache, result);
                            CacheIO.Save(cache);
                        }

                        status = result.Success ? 200 : 422;
                        payload = new
                        {
                            success = result.Success,
                            diagnostics = result.Diagnostics.Select(d => d.ToString()).ToList(),
                            referenceCount = result.ReferenceCount,
                            outputPath = result.OutputPath
                        };
                        break;
                    }
                case "/project/files":
                    payload = new
                    {
                        root = cache?.Project.RootPath,
                        files = cache?.Project.Files ?? new List<string>(),
                        hashes = cache?.Project.FileHashes ?? new Dictionary<string, string>()
                    };
                    break;
                case "/project/file":
                    {
                        var p = qs["path"];
                        if (string.IsNullOrWhiteSpace(p))
                        {
                            status = 400;
                            payload = new { error = "path required" };
                        }
                        else
                        {
                            var text = ReadProjectFile(p);
                            payload = text is null
                                ? (object)new { error = "not found" }
                                : new { path = p, content = text };
                            if (text is null) status = 404;
                        }
                        break;
                    }
                case "/project/write":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase) &&
                            !string.Equals(ctx.Request.HttpMethod, "PUT", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST body JSON { path, content }" };
                            break;
                        }
                        if (_fileWriter is null && _projectManager is null)
                        {
                            status = 503;
                            payload = new { error = "writes disabled" };
                            break;
                        }
                        using var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding);
                        var body = reader.ReadToEnd();
                        var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(body) ? "{}" : body);
                        var wp = doc.RootElement.TryGetProperty("path", out var pe) ? pe.GetString() : qs["path"];
                        var content = doc.RootElement.TryGetProperty("content", out var ce) ? ce.GetString() : null;
                        if (string.IsNullOrWhiteSpace(wp) || content is null)
                        {
                            status = 400;
                            payload = new { error = "path and content required" };
                        }
                        else
                        {
                            try
                            {
                                WriteProjectFile(wp, content);
                                payload = new { ok = true, path = wp };
                            }
                            catch (Exception ex)
                            {
                                status = 400;
                                payload = new { error = ex.Message };
                            }
                        }
                        break;
                    }
                case "/simulation/logs":
                    payload = cache?.Simulation ?? new SimulationCache();
                    break;
                case "/simulation/timeline":
                    payload = new
                    {
                        timeline = cache?.Simulation.Timeline ?? new List<TimelineEventDto>(),
                        stress = cache?.Simulation.Stress,
                        turnLogs = cache?.Simulation.TurnLogs ?? new List<string>(),
                        threadActions = cache?.Simulation.ThreadActions ?? new List<ThreadActionDto>(),
                        activeScenario = cache?.Simulation.ActiveScenario,
                        threadActionCount = cache?.Simulation.ThreadActions.Count ?? 0,
                        lastIngestAt = cache?.Simulation.LastIngestAt
                    };
                    break;
                case "/simulation/ingest":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST JSON { log[], timeline[], stats?, success?, turnsExecuted? }" };
                            break;
                        }

                        cache ??= _cacheProvider() ?? CacheIO.Load();
                        if (cache is null)
                        {
                            status = 503;
                            payload = new { error = "no cache — run qudlab index/serve" };
                            break;
                        }

                        using (var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding))
                        {
                            var body = reader.ReadToEnd();
                            if (string.IsNullOrWhiteSpace(body))
                            {
                                status = 400;
                                payload = new { error = "empty body" };
                                break;
                            }

                            try
                            {
                                using var doc = JsonDocument.Parse(body);
                                var root = doc.RootElement;
                                IngestSimulation(cache, root);
                                CacheIO.Save(cache);
                                payload = new
                                {
                                    ok = true,
                                    timeline = cache.Simulation.Timeline.Count,
                                    turnLogs = cache.Simulation.TurnLogs.Count,
                                    source = root.TryGetProperty("source", out var src) ? src.GetString() : "ingest"
                                };
                            }
                            catch (Exception ex)
                            {
                                status = 400;
                                payload = new { error = ex.Message };
                            }
                        }

                        break;
                    }
                case "/simulate":
                    {
                        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
                        {
                            status = 405;
                            payload = new { error = "POST JSON { blueprint?, turns?, parts?, mutations?, stress?, remote?, scenario?, genotype?, subtype?, chartype?, pregen?, gameMode?, cybernetics?, zoneId?, npcCount?, mapWidth?, mapHeight?, map?, waterFlow?, powerPipes?, ydDense? }" };
                            break;
                        }

                        if (install is null)
                        {
                            status = 503;
                            payload = new { error = "no install bound — run qudlab gate" };
                            break;
                        }

                        string blueprint = "Human";
                        var turns = 10;
                        var parts = new List<string>();
                        var mutations = new List<string>();
                        var cybernetics = new List<string>();
                        var stress = false;
                        var remote = false;
                        string? scenario = null;
                        string? genotype = null;
                        string? subtype = null;
                        string? chartype = null;
                        string? pregen = null;
                        string? gameMode = null;
                        string? zoneId = null;
                        var npcCount = 0;
                        var mapWidth = 0;
                        var mapHeight = 0;
                        bool? waterFlow = null;
                        bool? powerPipes = null;
                        var ydDense = false;

                        using (var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding))
                        {
                            var body = reader.ReadToEnd();
                            if (!string.IsNullOrWhiteSpace(body))
                            {
                                try
                                {
                                    using var doc = JsonDocument.Parse(body);
                                    var root = doc.RootElement;
                                    if (root.TryGetProperty("blueprint", out var be) || root.TryGetProperty("BlueprintOrSpecies", out be))
                                        blueprint = be.GetString() ?? blueprint;
                                    if (root.TryGetProperty("turns", out var te) && te.TryGetInt32(out var tn))
                                        turns = tn;
                                    if (root.TryGetProperty("stress", out var se) && (se.ValueKind is JsonValueKind.True or JsonValueKind.False))
                                        stress = se.GetBoolean();
                                    if (root.TryGetProperty("remote", out var re) && (re.ValueKind is JsonValueKind.True or JsonValueKind.False))
                                        remote = re.GetBoolean();
                                    scenario = JsonStr(root, "scenario", "Scenario");
                                    genotype = JsonStr(root, "genotype", "Genotype");
                                    subtype = JsonStr(root, "subtype", "Subtype");
                                    chartype = JsonStr(root, "chartype", "Chartype");
                                    pregen = JsonStr(root, "pregen", "Pregen");
                                    gameMode = JsonStr(root, "gameMode", "GameMode");
                                    zoneId = JsonStr(root, "zoneId", "ZoneId", "zone");
                                    npcCount = GetIntEl(root, "npcCount") ?? GetIntEl(root, "npcs") ?? GetIntEl(root, "NpcCount") ?? 0;
                                    mapWidth = GetIntEl(root, "mapWidth") ?? GetIntEl(root, "MapWidth") ?? 0;
                                    mapHeight = GetIntEl(root, "mapHeight") ?? GetIntEl(root, "MapHeight") ?? 0;
                                    var mapSpec = JsonStr(root, "map", "Map");
                                    if (!string.IsNullOrWhiteSpace(mapSpec) && CrowdLoadScenario.TryParseMap(mapSpec, out var mw, out var mh))
                                    {
                                        mapWidth = mw;
                                        mapHeight = mh;
                                    }
                                    waterFlow = GetBool(root, "waterFlow") ?? GetBool(root, "WaterFlow") ?? GetBool(root, "water");
                                    powerPipes = GetBool(root, "powerPipes") ?? GetBool(root, "PowerPipes") ?? GetBool(root, "pipes");
                                    ydDense = GetBool(root, "ydDense") ?? GetBool(root, "YdDense") ?? GetBool(root, "yd") ?? false;
                                    ReadStringArray(root, "parts", parts);
                                    ReadStringArray(root, "mutations", mutations);
                                    ReadStringArray(root, "cybernetics", cybernetics);
                                    ReadStringArray(root, "Cybernetics", cybernetics);
                                }
                                catch
                                {
                                    status = 400;
                                    payload = new { error = "invalid JSON body" };
                                    break;
                                }
                            }
                        }

                        if (status == 400)
                            break;

                        var req = new SimRequest
                        {
                            BlueprintOrSpecies = blueprint,
                            Turns = turns,
                            Parts = parts,
                            Mutations = mutations,
                            RestrictedDebugOnly = true,
                            Stress = stress,
                            Scenario = scenario,
                            Genotype = genotype,
                            Subtype = subtype,
                            Chartype = chartype,
                            Pregen = pregen,
                            GameMode = gameMode,
                            Cybernetics = cybernetics,
                            ZoneId = zoneId,
                            NpcCount = npcCount,
                            MapWidth = mapWidth,
                            MapHeight = mapHeight,
                            WaterFlow = waterFlow,
                            PowerPipes = powerPipes,
                            YdDense = ydDense
                        };

                        SimSnapshot? snap = null;
                        try
                        {
                            if (remote)
                            {
                                if (!SimIpc.IsReachableAsync().GetAwaiter().GetResult())
                                {
                                    status = 503;
                                    payload = new { error = "SimHost not reachable — start qudlab simhost" };
                                    break;
                                }

                                snap = SimIpc.CallRemoteAsync(req).GetAwaiter().GetResult();
                            }
                            else
                            {
                                var lab = new LabHost();
                                var gate = lab.Startup(install.RootPath);
                                if (!gate.Ok)
                                {
                                    status = 503;
                                    payload = new { error = gate.Message };
                                    break;
                                }

                                var sim = new RestrictedSimulator(lab, cacheProvider: () => _cacheProvider());
                                snap = sim.RunTurnsAsync(req).GetAwaiter().GetResult();
                                if (cache is not null)
                                {
                                    sim.ApplySnapshotToCache(cache, snap, scenario);
                                    CacheIO.Save(cache);
                                }
                            }

                            if (remote && cache is not null && snap is not null)
                            {
                                var apply = new RestrictedSimulator(new LabHost());
                                apply.ApplySnapshotToCache(cache, snap, scenario);
                                CacheIO.Save(cache);
                            }
                        }
                        catch (Exception ex)
                        {
                            status = 500;
                            payload = new { error = ex.Message };
                            break;
                        }

                        if (snap is null)
                        {
                            status = 500;
                            payload = new { error = "simulate produced no snapshot" };
                            break;
                        }

                        var refused = snap.Log.Any(l => l.StartsWith("REFUSED", StringComparison.Ordinal));
                        status = refused ? 422 : 200;
                        payload = new
                        {
                            success = !refused,
                            turnsExecuted = snap.TurnsExecuted,
                            log = snap.Log,
                            stats = snap.Stats,
                            timeline = snap.Timeline,
                            threadActions = snap.ThreadActions,
                            stress = snap.Stress
                        };
                        break;
                    }
                case "/ai":
                case "/ai/status":
                    if (_ai is null)
                    {
                        status = 503;
                        payload = new { error = "Ollama agent not wired — restart qudlab serve" };
                    }
                    else
                    {
                        payload = _ai.StatusAsync().GetAwaiter().GetResult();
                    }
                    break;
                case "/ai/models":
                    if (_ai is null)
                    {
                        status = 503;
                        payload = new { error = "Ollama agent not wired — restart qudlab serve" };
                    }
                    else
                    {
                        var st = _ai.StatusAsync().GetAwaiter().GetResult();
                        payload = new { ollama = st.Ollama, models = st.Models, resolved = st.ResolvedModel, baseUrl = st.BaseUrl };
                    }
                    break;
                case "/ai/run":
                case "/ai/ask":
                case "/ai/scan":
                case "/ai/fix":
                case "/ai/analyze":
                    HandleAi(ctx, path, out status, out payload);
                    break;
                default:
                    status = 404;
                    payload = new { error = "not found", path };
                    break;
            }

            WriteJson(ctx.Response, status, payload);
        }
        catch (Exception ex)
        {
            try { WriteJson(ctx.Response, 500, new { error = ex.Message }); } catch { }
        }
    }

    void HandleAi(HttpListenerContext ctx, string path, out int status, out object payload)
    {
        status = 200;
        if (_ai is null)
        {
            status = 503;
            payload = new { error = "Ollama agent not wired — restart qudlab serve" };
            return;
        }

        if (!string.Equals(ctx.Request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase))
        {
            status = 405;
            payload = new { error = "POST JSON { prompt, mode?, model?, apply?, maxRounds?, simulate?, turns?, blueprint? }" };
            return;
        }

        var req = new AiAgentRequest();
        using (var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding))
        {
            var body = reader.ReadToEnd();
            if (!string.IsNullOrWhiteSpace(body))
            {
                try
                {
                    using var doc = JsonDocument.Parse(body);
                    var root = doc.RootElement;
                    req.Prompt = GetStr(root, "prompt") ?? GetStr(root, "q") ?? GetStr(root, "message") ?? "";
                    req.Mode = GetStr(root, "mode") ?? GetStr(root, "task") ?? ModeFromPath(path);
                    req.Model = GetStr(root, "model");
                    req.Apply = GetBool(root, "apply") ?? path.EndsWith("/fix", StringComparison.Ordinal);
                    req.Simulate = GetBool(root, "simulate") ?? path.EndsWith("/analyze", StringComparison.Ordinal);
                    req.MaxRounds = GetIntEl(root, "maxRounds") ?? GetIntEl(root, "rounds") ?? 10;
                    req.Turns = GetIntEl(root, "turns") ?? 8;
                    req.Blueprint = GetStr(root, "blueprint") ?? "Human";
                }
                catch
                {
                    status = 400;
                    payload = new { error = "invalid JSON body" };
                    return;
                }
            }
            else
            {
                req.Mode = ModeFromPath(path);
                req.Apply = path.EndsWith("/fix", StringComparison.Ordinal);
                req.Simulate = path.EndsWith("/analyze", StringComparison.Ordinal);
            }
        }

        if (string.IsNullOrWhiteSpace(req.Mode))
            req.Mode = ModeFromPath(path);

        try
        {
            var result = _ai.RunAsync(req).GetAwaiter().GetResult();
            status = result.Ok ? 200 : 502;
            payload = result;
        }
        catch (Exception ex)
        {
            status = 502;
            payload = new { error = ex.Message };
        }
    }

    static string ModeFromPath(string path) =>
        path switch
        {
            "/ai/fix" => "fix",
            "/ai/scan" => "scan",
            "/ai/analyze" => "analyze",
            _ => "ask"
        };

    static string? GetStr(JsonElement root, string name) =>
        root.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() : null;

    static bool? GetBool(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var p))
            return null;
        return p.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            _ => bool.TryParse(p.GetString(), out var b) ? b : null
        };
    }

    static int? GetIntEl(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var p))
            return null;
        if (p.ValueKind == JsonValueKind.Number && p.TryGetInt32(out var n))
            return n;
        return int.TryParse(p.GetString(), out var s) ? s : null;
    }

    static object BuildCacheStatus(IntelligenceCache? cache, QudInstallInfo? install)
    {
        if (cache is null)
            return new { ready = false, schemaVersion = CacheIO.CurrentSchemaVersion };

        var stale = install is not null && CacheIO.IsStale(cache, install);
        var xrlCount = cache.TypeGraph.Types.Keys.Count(k =>
            k.StartsWith("XRL.", StringComparison.Ordinal) || k.StartsWith("Qud.", StringComparison.Ordinal));

        return new
        {
            ready = true,
            stale,
            schemaVersion = cache.SchemaVersion,
            gameRoot = cache.GameRoot,
            builtAt = cache.BuiltAt,
            stamp = cache.Stamp,
            types = cache.TypeGraph.Types.Count,
            xrlTypes = xrlCount,
            blueprints = cache.BlueprintGraph.Objects.Count,
            mutations = cache.MutationGraph.Mutations.Count,
            abilities = cache.AbilityGraph.Abilities.Count,
            genotypes = cache.Catalogs.BySource.TryGetValue("genotype", out var g) ? g.Count : 0,
            subtypes = cache.Catalogs.BySource.TryGetValue("subtype", out var s) ? s.Count : 0,
            events = cache.EventGraph.EventNames.Count,
            eventTypes = cache.EventGraph.EventTypeNames.Count,
            eventPools = cache.EventGraph.PoolAudit?.TotalEvents ?? 0,
            modEventPools = cache.EventGraph.PoolAudit?.ModPooledCount ?? 0,
            eventIdConflicts = cache.EventGraph.PoolAudit?.IdConflicts.Count ?? 0,
            projectFiles = cache.Project.Files.Count,
            projectRoot = cache.Project.RootPath
        };
    }

    static object BuildNamespaces(IntelligenceCache? cache)
    {
        if (cache is null) return Array.Empty<object>();
        return cache.TypeGraph.Types.Values
            .GroupBy(t => t.Namespace ?? "(global)", StringComparer.Ordinal)
            .Select(g => new { ns = g.Key, count = g.Count() })
            .OrderByDescending(x => x.count)
            .ThenBy(x => x.ns, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    static object BuildBrowse(IntelligenceCache? cache, string? ns, string? q, int limit)
    {
        if (cache is null)
            return new { namespaces = Array.Empty<object>(), types = Array.Empty<object>() };

        limit = Math.Clamp(limit, 1, 500);
        var namespaces = cache.TypeGraph.Types.Values
            .GroupBy(t => t.Namespace ?? "(global)", StringComparer.Ordinal)
            .Select(g => new { ns = g.Key, count = g.Count() })
            .OrderByDescending(x => x.count)
            .ThenBy(x => x.ns, StringComparer.OrdinalIgnoreCase)
            .Take(200)
            .ToList();

        IEnumerable<TypeNode> types = cache.TypeGraph.Types.Values;
        if (!string.IsNullOrWhiteSpace(ns))
            types = types.Where(t => string.Equals(t.Namespace, ns, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(q))
            types = types.Where(t =>
                t.FullName.Contains(q, StringComparison.OrdinalIgnoreCase));

        var typeList = types
            .OrderBy(t => t.FullName, StringComparer.OrdinalIgnoreCase)
            .Take(limit)
            .Select(t =>
            {
                var full = t.FullName ?? "";
                var shortName = full.Contains('.') ? full[(full.LastIndexOf('.') + 1)..] : full;
                return new
                {
                    fullName = full,
                    name = shortName,
                    ns = t.Namespace,
                    baseType = t.BaseType,
                    methodCount = t.Methods?.Count ?? 0
                };
            })
            .ToList();

        return new { namespaces, types = typeList, query = q, ns };
    }

    static object LookupType(IntelligenceCache? cache, string? name, out int status)
    {
        status = 200;
        if (string.IsNullOrWhiteSpace(name) || cache is null)
        {
            status = 400;
            return new { error = "name required (full or partial type name)" };
        }
        if (cache.TypeGraph.Types.TryGetValue(name, out var exact))
            return exact;
        var hits = cache.TypeGraph.Types
            .Where(kv => kv.Key.Contains(name, StringComparison.OrdinalIgnoreCase))
            .Take(20)
            .Select(kv => kv.Value)
            .ToList();
        if (hits.Count == 0)
        {
            status = 404;
            return new { error = "not found", name };
        }
        return hits;
    }

    static object LookupBlueprint(IntelligenceCache? cache, string? name, out int status)
    {
        status = 200;
        if (string.IsNullOrWhiteSpace(name) || cache is null)
        {
            status = 400;
            return new { error = "name required" };
        }
        if (cache.BlueprintGraph.Objects.TryGetValue(name, out var exact))
            return exact;
        var hits = cache.BlueprintGraph.Objects
            .Where(kv => kv.Key.Contains(name, StringComparison.OrdinalIgnoreCase))
            .Take(20)
            .Select(kv => kv.Value)
            .ToList();
        if (hits.Count == 0)
        {
            status = 404;
            return new { error = "not found", name };
        }
        return hits;
    }

    static object FilterTypes(IntelligenceCache? cache, string? q, int limit)
    {
        if (cache is null) return Array.Empty<object>();
        IEnumerable<KeyValuePair<string, TypeNode>> qy = cache.TypeGraph.Types;
        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(kv => kv.Key.Contains(q, StringComparison.OrdinalIgnoreCase));
        return qy.Take(Math.Clamp(limit, 1, 500)).Select(kv => kv.Value).ToList();
    }

    static object FilterBlueprints(IntelligenceCache? cache, string? q, int limit)
    {
        if (cache is null) return Array.Empty<object>();
        IEnumerable<KeyValuePair<string, BlueprintNode>> qy = cache.BlueprintGraph.Objects;
        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(kv => kv.Key.Contains(q, StringComparison.OrdinalIgnoreCase));
        return qy.Take(Math.Clamp(limit, 1, 500)).Select(kv => kv.Value).ToList();
    }

    static object FilterMutations(IntelligenceCache? cache, string? q, int limit)
    {
        if (cache is null) return Array.Empty<object>();
        IEnumerable<KeyValuePair<string, MutationNode>> qy = cache.MutationGraph.Mutations;
        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(kv =>
                kv.Key.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (kv.Value.Class?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (kv.Value.Category?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));
        return qy.Take(Math.Clamp(limit, 1, 500)).Select(kv => kv.Value).ToList();
    }

    static object FilterCatalog(IntelligenceCache? cache, string source, string? q, int limit)
    {
        if (cache is null)
            return Array.Empty<object>();
        if (!cache.Catalogs.BySource.TryGetValue(source, out var list))
            return new { source, results = Array.Empty<object>() };
        IEnumerable<CatalogEntry> qy = list;
        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(e =>
                e.Id.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (e.DisplayName?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (e.Parent?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));
        return new { source, results = qy.Take(Math.Clamp(limit, 1, 500)).ToList() };
    }

    static string? JsonStr(JsonElement root, params string[] names)
    {
        foreach (var name in names)
        {
            if (root.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String)
            {
                var s = p.GetString();
                if (!string.IsNullOrWhiteSpace(s))
                    return s;
            }
        }

        return null;
    }

    static object FilterAbilities(IntelligenceCache? cache, string? q, int limit)
    {
        if (cache is null) return Array.Empty<object>();
        IEnumerable<KeyValuePair<string, AbilityNode>> qy = cache.AbilityGraph.Abilities;
        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(kv =>
                kv.Key.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (kv.Value.Description?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));
        return qy.Take(Math.Clamp(limit, 1, 500)).Select(kv => kv.Value).ToList();
    }

    static void IngestSimulation(IntelligenceCache cache, JsonElement root)
    {
        if (root.TryGetProperty("log", out var logEl) && logEl.ValueKind == JsonValueKind.Array)
        {
            cache.Simulation.TurnLogs = new List<string>();
            foreach (var e in logEl.EnumerateArray())
            {
                var s = e.GetString();
                if (!string.IsNullOrEmpty(s))
                    cache.Simulation.TurnLogs.Add(s);
            }
        }

        if (root.TryGetProperty("timeline", out var tl) && tl.ValueKind == JsonValueKind.Array)
        {
            cache.Simulation.Timeline = new List<TimelineEventDto>();
            foreach (var e in tl.EnumerateArray())
            {
                cache.Simulation.Timeline.Add(new TimelineEventDto
                {
                    Turn = e.TryGetProperty("turn", out var turn) && turn.TryGetInt32(out var tn) ? tn : 0,
                    Kind = e.TryGetProperty("kind", out var k) ? k.GetString() ?? "" : "",
                    Label = e.TryGetProperty("label", out var l) ? l.GetString() ?? "" : "",
                    Detail = e.TryGetProperty("detail", out var d) ? d.GetString() ?? "" : "",
                    ThreadId = e.TryGetProperty("threadId", out var tid) && tid.TryGetInt32(out var ti) ? ti : 0,
                    Timestamp = e.TryGetProperty("timestamp", out var ts) &&
                                DateTimeOffset.TryParse(ts.GetString(), out var dto)
                        ? dto
                        : DateTimeOffset.UtcNow
                });
            }
        }

        if (root.TryGetProperty("threadActions", out var ta) && ta.ValueKind == JsonValueKind.Array)
        {
            cache.Simulation.ThreadActions = new List<ThreadActionDto>();
            foreach (var e in ta.EnumerateArray())
            {
                cache.Simulation.ThreadActions.Add(new ThreadActionDto
                {
                    Timestamp = e.TryGetProperty("timestamp", out var ts) &&
                                DateTimeOffset.TryParse(ts.GetString(), out var dto)
                        ? dto
                        : DateTimeOffset.UtcNow,
                    ThreadId = e.TryGetProperty("threadId", out var tid) && tid.TryGetInt32(out var ti) ? ti : 0,
                    Action = e.TryGetProperty("action", out var a) ? a.GetString() ?? "" : "",
                    Detail = e.TryGetProperty("detail", out var d) ? d.GetString() ?? "" : ""
                });
            }
        }

        // Stamp a header line so CLI/UI see Unity source
        var source = root.TryGetProperty("source", out var src) ? src.GetString() : "ingest";
        var ok = !root.TryGetProperty("success", out var se) || se.ValueKind != JsonValueKind.False;
        var turns = root.TryGetProperty("turnsExecuted", out var te) && te.TryGetInt32(out var tn2) ? tn2 : 0;
        cache.Simulation.TurnLogs.Insert(0,
            $"[ingest:{source}] success={ok} turns={turns} timeline={cache.Simulation.Timeline.Count}");
        cache.Simulation.LastIngestAt = DateTimeOffset.UtcNow;
    }

    string? ReadProjectFile(string? p) =>
        _projectManager?.ReadFile(p) ?? _fileReader?.Invoke(p);

    void WriteProjectFile(string p, string content)
    {
        if (_projectManager is not null)
            _projectManager.WriteFile(p, content);
        else if (_fileWriter is not null)
            _fileWriter(p, content);
        else
            throw new InvalidOperationException("writes disabled");
    }

    static void ReadStringArray(JsonElement root, string name, List<string> dest)
    {
        if (!root.TryGetProperty(name, out var arr) || arr.ValueKind != JsonValueKind.Array)
            return;
        foreach (var el in arr.EnumerateArray())
        {
            var s = el.GetString();
            if (!string.IsNullOrWhiteSpace(s))
                dest.Add(s);
        }
    }

    static int ParseInt(string? s, int fallback) =>
        int.TryParse(s, out var n) ? n : fallback;

    static void WriteJson(HttpListenerResponse res, int status, object payload)
    {
        var json = JsonSerializer.Serialize(payload, CacheIO.JsonOptions);
        var bytes = Encoding.UTF8.GetBytes(json);
        res.StatusCode = status;
        res.ContentType = "application/json; charset=utf-8";
        res.ContentLength64 = bytes.Length;
        res.AddHeader("Access-Control-Allow-Origin", "*");
        res.OutputStream.Write(bytes, 0, bytes.Length);
        res.OutputStream.Close();
    }
}

public static class CacheSearch
{
    public static object Search(IntelligenceCache? cache, string? q, string? kind, int limit)
    {
        if (cache is null || string.IsNullOrWhiteSpace(q))
            return new { query = q, results = Array.Empty<object>() };

        kind = (kind ?? "all").Trim().ToLowerInvariant();
        limit = Math.Clamp(limit, 1, 200);
        var hits = new List<SearchHit>();

        bool Want(string k) =>
            kind is "all" or "" ||
            kind == k ||
            kind == k + "s";

        if (Want("type"))
            foreach (var (key, score) in Rank(cache.TypeGraph.Types.Keys, q))
                hits.Add(new SearchHit("type", key, score));
        if (Want("blueprint"))
            foreach (var (key, score) in Rank(cache.BlueprintGraph.Objects.Keys, q))
                hits.Add(new SearchHit("blueprint", key, score));
        if (Want("mutation"))
            foreach (var (key, score) in Rank(cache.MutationGraph.Mutations.Keys, q))
                hits.Add(new SearchHit("mutation", key, score));
        if (Want("ability"))
            foreach (var (key, score) in Rank(cache.AbilityGraph.Abilities.Keys, q))
                hits.Add(new SearchHit("ability", key, score));
        if (Want("genotype"))
            foreach (var (key, score) in Rank(CatalogIds(cache, "genotype"), q))
                hits.Add(new SearchHit("genotype", key, score));
        if (Want("subtype"))
            foreach (var (key, score) in Rank(CatalogIds(cache, "subtype"), q))
                hits.Add(new SearchHit("subtype", key, score));
        if (Want("pregen"))
            foreach (var (key, score) in Rank(CatalogIds(cache, "pregen"), q))
                hits.Add(new SearchHit("pregen", key, score));

        var top = hits.OrderByDescending(h => h.Score).Take(limit).Select(h =>
        {
            object extra = h.Kind switch
            {
                "type" when cache.TypeGraph.Types.TryGetValue(h.Id, out var t) => new { h.Kind, h.Id, h.Score, baseType = t.BaseType },
                "blueprint" when cache.BlueprintGraph.Objects.TryGetValue(h.Id, out var b) => new { h.Kind, h.Id, h.Score, inherits = b.Inherits },
                "mutation" when cache.MutationGraph.Mutations.TryGetValue(h.Id, out var m) => new { h.Kind, h.Id, h.Score, className = m.Class, category = m.Category },
                _ => new { h.Kind, h.Id, h.Score }
            };
            return extra;
        }).ToList();

        return new { query = q, kind, results = top };
    }

    static IEnumerable<(string key, int score)> Rank(IEnumerable<string> keys, string q)
    {
        foreach (var key in keys)
        {
            var score = Score(key, q);
            if (score > 0)
                yield return (key, score);
        }
    }

    static IEnumerable<string> CatalogIds(IntelligenceCache cache, string source)
    {
        if (cache.Catalogs.BySource.TryGetValue(source, out var list))
        {
            foreach (var e in list)
                yield return e.Id;
        }
    }

    static int Score(string key, string q)
    {
        if (key.Equals(q, StringComparison.OrdinalIgnoreCase))
            return 1000;
        if (key.EndsWith("." + q, StringComparison.OrdinalIgnoreCase) ||
            key.EndsWith(q, StringComparison.OrdinalIgnoreCase))
            return 800;
        var idx = key.IndexOf(q, StringComparison.OrdinalIgnoreCase);
        if (idx < 0)
            return 0;
        // Prefer XRL.* and earlier matches
        var bonus = key.StartsWith("XRL.", StringComparison.Ordinal) ? 50 : 0;
        return 500 - Math.Min(idx, 400) + bonus;
    }

    /// <summary>Flat hits for AiContextBuilder (no anonymous-type sorting issues).</summary>
    public static List<SearchHit> SearchHits(IntelligenceCache? cache, string q, int limit = 30)
    {
        var list = new List<SearchHit>();
        if (cache is null || string.IsNullOrWhiteSpace(q))
            return list;

        foreach (var (key, score) in Rank(cache.TypeGraph.Types.Keys, q))
            list.Add(new SearchHit("type", key, score));
        foreach (var (key, score) in Rank(cache.BlueprintGraph.Objects.Keys, q))
            list.Add(new SearchHit("blueprint", key, score));
        foreach (var (key, score) in Rank(cache.MutationGraph.Mutations.Keys, q))
            list.Add(new SearchHit("mutation", key, score));
        foreach (var (key, score) in Rank(CatalogIds(cache, "genotype"), q))
            list.Add(new SearchHit("genotype", key, score));
        foreach (var (key, score) in Rank(CatalogIds(cache, "subtype"), q))
            list.Add(new SearchHit("subtype", key, score));

        return list.OrderByDescending(h => h.Score).Take(limit).ToList();
    }
}

public readonly record struct SearchHit(string Kind, string Id, int Score);
