using QudLab.Ai;
using QudLab.Assistant;
using QudLab.Core;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.Logs;
using QudLab.Core.References;
using QudLab.Indexer;
using QudLab.RoslynCompile;
using QudLab.Simulator;

namespace QudLab.Cli;

static class Program
{
    static IntelligenceCache? _cache;
    static LabHost _host = new();
    static string LabRoot =>
        Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));

    static async Task<int> Main(string[] args)
    {
        if (args.Length == 0)
        {
            PrintHelp();
            return 1;
        }

        var cmd = args[0].ToLowerInvariant();
        var overridePath = GetOption(args, "--path");

        try
        {
            return cmd switch
            {
                "gate" or "doctor" => CmdGate(overridePath),
                "setup" => CmdSetup(overridePath),
                "index" or "mine" => CmdIndex(overridePath),
                "sync-refs" or "refs-sync" or "workspace" => CmdSyncRefs(overridePath),
                "refs" => CmdRefs(overridePath),
                "serve" => await CmdServe(args, overridePath),
                "explain" => CmdExplain(args),
                "compile" => CmdCompile(args, overridePath),
                "simulate" or "sim" => await CmdSim(args, overridePath),
                "simhost" => CmdSimHost(args, overridePath),
                "template" => CmdTemplate(args),
                "ollama" => await CmdOllama(args),
                "project" or "mod" => CmdProject(args),
                "logs" => CmdLogs(args),
                "events" => CmdEvents(args, overridePath),
                "help" or "-h" or "--help" => PrintHelp(),
                _ => Unknown(cmd)
            };
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 2;
        }
    }

    static int CmdSetup(string? path)
    {
        var gate = CmdGate(path);
        if (gate != 0)
            return gate;
        var sync = CmdSyncRefs(path);
        if (sync != 0)
            return sync;
        var index = CmdIndex(path);
        if (index != 0)
            return index;
        Console.WriteLine();
        Console.WriteLine("Setup complete.");
        Console.WriteLine("  1. Open QudLab.code-workspace in Cursor");
        Console.WriteLine("  2. Edit under Workspace/src — Copilot sees XRL.* from install HintPaths");
        Console.WriteLine("  3. Optional: qudlab serve");
        return 0;
    }

    static int CmdGate(string? path)
    {
        var r = _host.Startup(path);
        Console.WriteLine(r.Ok ? "PASS" : "FAIL");
        Console.WriteLine(r.Message);
        if (r.Install is not null)
        {
            Console.WriteLine($"Root: {r.Install.RootPath}");
            Console.WriteLine($"Store: {r.Install.Store}");
            Console.WriteLine($"Unity: {r.Install.DetectedUnityVersion ?? "?"}");
            Console.WriteLine($"Managed DLLs: {_host.Assemblies.ListManagedAssemblies().Count}");
            var existing = CacheIO.Load();
            var stale = CacheIO.IsStale(existing, r.Install);
            Console.WriteLine(existing is null
                ? "Cache: missing (run index/setup)"
                : $"Cache: schema={existing.SchemaVersion} types={existing.TypeGraph.Types.Count} stale={stale} built={existing.BuiltAt:u}");
            Console.WriteLine("Tip: run `qudlab sync-refs` so Cursor/Copilot load Qud HintPaths.");
        }
        return r.Ok ? 0 : 1;
    }

    static int CmdSyncRefs(string? path)
    {
        var r = _host.Startup(path);
        if (!r.Ok || r.Install is null)
        {
            Console.Error.WriteLine(r.Message);
            return 1;
        }

        // Prefer repo root (…/QudLab) over artifacts bin path
        var labRoot = FindLabRoot();
        var csproj = IdeProjectSync.Sync(r.Install, labRoot);
        var refs = QudReferenceSet.FromInstall(r.Install);
        Console.WriteLine($"Synced IDE workspace for Copilot/OmniSharp");
        Console.WriteLine($"  Lab root:  {labRoot}");
        Console.WriteLine($"  Project:   {csproj}");
        Console.WriteLine($"  Managed:   {refs.ManagedPath}");
        Console.WriteLine($"  Full Managed refs (Roslyn): {refs.AssemblyPaths.Count}");
        Console.WriteLine($"  IDE essential refs (Copilot): {refs.IdeEssentialPaths.Count}");
        Console.WriteLine($"  Assembly-CSharp.xml: {(refs.XmlDocPath is null ? "missing" : "yes")}");
        Console.WriteLine();
        Console.WriteLine("Open QudLab.code-workspace (or Workspace/QudLab.ModWorkspace.csproj) in Cursor.");
        return 0;
    }

    static int CmdRefs(string? path)
    {
        var r = _host.Startup(path);
        if (!r.Ok || r.Install is null)
        {
            Console.Error.WriteLine(r.Message);
            return 1;
        }

        var refs = QudReferenceSet.FromInstall(r.Install);
        Console.WriteLine($"Managed: {refs.ManagedPath}");
        Console.WriteLine($"Roslyn (full): {refs.AssemblyPaths.Count}");
        Console.WriteLine($"IDE essential: {refs.IdeEssentialPaths.Count}");
        Console.WriteLine("-- IDE essentials --");
        foreach (var p in refs.IdeEssentialPaths)
            Console.WriteLine($"  {Path.GetFileName(p)}");
        return 0;
    }

    static string FindLabRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "QudLab.sln")) ||
                Directory.Exists(Path.Combine(dir.FullName, "UnityProject")))
                return dir.FullName;
            dir = dir.Parent;
        }
        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
    }

    static int CmdIndex(string? path)
    {
        var r = _host.Startup(path);
        if (!r.Ok || r.Install is null)
        {
            Console.Error.WriteLine(r.Message);
            return 1;
        }

        var project = ResolveProjectRoot(Environment.GetCommandLineArgs());
        Console.WriteLine("Indexing (XRL types + blueprints + Base XML)...");
        if (project is not null)
            Console.WriteLine($"Project: {project}");

        var indexer = new QudIndexer();
        _cache = indexer.Build(r.Install, project);
        CacheIO.Save(_cache);

        var xrl = _cache.TypeGraph.Types.Keys.Count(k =>
            k.StartsWith("XRL.", StringComparison.Ordinal) || k.StartsWith("Qud.", StringComparison.Ordinal));
        Console.WriteLine($"Schema: {_cache.SchemaVersion}");
        Console.WriteLine($"Types: {_cache.TypeGraph.Types.Count} (XRL/Qud: {xrl})");
        Console.WriteLine($"Blueprints: {_cache.BlueprintGraph.Objects.Count}");
        Console.WriteLine($"Mutations: {_cache.MutationGraph.Mutations.Count}");
        Console.WriteLine($"Abilities: {_cache.AbilityGraph.Abilities.Count}");
        Console.WriteLine($"Events: {_cache.EventGraph.EventNames.Count} / eventTypes={_cache.EventGraph.EventTypeNames.Count}");
        Console.WriteLine($"Project files: {_cache.Project.Files.Count}");
        Console.WriteLine($"Cache: {CacheIO.DefaultCacheDir()}");
        foreach (var d in _cache.Project.Diagnostics.Take(10))
            Console.WriteLine($"warn: {d}");
        return 0;
    }

    static async Task<int> CmdServe(string[] args, string? path)
    {
        EnsureCacheFresh(path, args);
        var project = _cache?.Project.RootPath ?? ResolveProjectRoot(args) ?? DefaultWorkspaceSrc();
        var port = GetInt(args, "--port", 47821);

        ActiveProjectManager CreateProjectManager() => new(
            () => _cache ?? CacheIO.Load(),
            DefaultWorkspaceSrc,
            () => _host.Install?.RootPath);

        var projectManager = CreateProjectManager();

        var ai = new LabAiService(
            new OllamaClient(),
            () => _cache ?? CacheIO.Load(),
            () => _host.Install ?? _host.Startup(path).Install,
            projectManager.ReadFile,
            projectManager.WriteFile,
            FindLabRoot(),
            projectManager);

        var server = new ModAssistantServer(
            () => _cache ?? CacheIO.Load(),
            port,
            projectManager.ReadFile,
            projectManager.WriteFile,
            () => _host.Install ?? _host.Startup(path).Install,
            () => _host.Assets.IsBound ? _host.Assets : null,
            ai,
            projectManager);

        await server.StartAsync();
        var active = projectManager.Get();
        Console.WriteLine($"Mod assistant listening on http://127.0.0.1:{port}/");
        Console.WriteLine($"Cache schema={_cache?.SchemaVersion} types={_cache?.TypeGraph.Types.Count} mutations={_cache?.MutationGraph.Mutations.Count}");
        Console.WriteLine($"Active project (/project/*, AI scan/compile): {active.RootPath} ({active.FileCount} files)");
        Console.WriteLine($"Local mods root: {QudModPaths.LocalModsRoot()}");
        var workshop = QudModPaths.WorkshopModsRoot(_host.Install?.RootPath);
        if (workshop is not null)
            Console.WriteLine($"Workshop mods: {workshop}");
        Console.WriteLine("Ollama agent: POST /ai/run  (ask|scan|fix|analyze) — https://github.com/ollama/ollama");
        Console.WriteLine("Hot-switch mod: POST /project/set {\"query\":\"Broodmother\"}  or  qudlab project set \"Blink\"");
        Console.WriteLine("Live logs: GET /logs/game?kind=threading&tail=100");
        Console.WriteLine("Press Ctrl+C to stop.");
        var tcs = new TaskCompletionSource();
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; tcs.TrySetResult(); };
        await tcs.Task;
        await server.StopAsync();
        return 0;
    }

    static int CmdExplain(string[] args)
    {
        _cache ??= CacheIO.Load();
        if (_cache is null)
        {
            Console.Error.WriteLine("No cache. Run: qudlab index");
            return 1;
        }

        var symbol = args.ElementAtOrDefault(1);
        if (string.IsNullOrWhiteSpace(symbol))
        {
            Console.Error.WriteLine("Usage: qudlab explain <TypeOrBlueprint>");
            return 1;
        }

        var types = _cache.TypeGraph.Types
            .Where(kv => kv.Key.Contains(symbol, StringComparison.OrdinalIgnoreCase))
            .Take(20)
            .ToList();
        foreach (var t in types)
        {
            Console.WriteLine($"TYPE {t.Key}");
            Console.WriteLine($"  base: {t.Value.BaseType}");
            Console.WriteLine($"  methods: {string.Join(", ", t.Value.Methods.Take(15))}...");
        }

        var bps = _cache.BlueprintGraph.Objects
            .Where(kv => kv.Key.Contains(symbol, StringComparison.OrdinalIgnoreCase))
            .Take(20)
            .ToList();
        foreach (var b in bps)
        {
            Console.WriteLine($"BP {b.Key} inherits={b.Value.Inherits}");
            Console.WriteLine($"  parts: {string.Join(", ", b.Value.Parts)}");
        }

        foreach (var source in new[] { "genotype", "subtype", "pregen", "starting-location" })
        {
            if (!_cache.Catalogs.BySource.TryGetValue(source, out var list))
                continue;
            foreach (var e in list.Where(x =>
                         x.Id.Contains(symbol, StringComparison.OrdinalIgnoreCase) ||
                         (x.DisplayName?.Contains(symbol, StringComparison.OrdinalIgnoreCase) ?? false)).Take(12))
            {
                Console.WriteLine($"{source.ToUpperInvariant()} {e.Id} parent={e.Parent}");
                if (e.Skills.Count > 0)
                    Console.WriteLine($"  skills: {string.Join(", ", e.Skills.Take(12))}");
            }
        }

        if (types.Count == 0 && bps.Count == 0)
            Console.WriteLine("No type/blueprint matches (catalogs listed above if any).");
        return 0;
    }

    static int CmdCompile(string[] args, string? path)
    {
        var r = _host.Startup(path);
        if (!r.Ok || r.Install is null)
        {
            Console.Error.WriteLine(r.Message);
            return 1;
        }

        var compiler = new QudModCompiler();
        CompileResult result;
        var file = GetOption(args, "--file");
        var project = GetOption(args, "--project");

        if (!string.IsNullOrWhiteSpace(file))
        {
            if (!File.Exists(file))
            {
                Console.Error.WriteLine($"File not found: {file}");
                return 1;
            }

            result = compiler.Compile(r.Install, new[] { (Path.GetFullPath(file), File.ReadAllText(file)) });
            if (result.Success && result.AssemblyBytes is not null)
            {
                var outPath = Path.ChangeExtension(file, ".dll");
                File.WriteAllBytes(outPath, result.AssemblyBytes);
                result = new CompileResult
                {
                    Success = true,
                    AssemblyBytes = result.AssemblyBytes,
                    OutputPath = outPath,
                    Diagnostics = result.Diagnostics,
                    ReferenceCount = result.ReferenceCount
                };
            }
        }
        else
        {
            var projectDir = !string.IsNullOrWhiteSpace(project)
                ? Path.GetFullPath(project)
                : DefaultWorkspaceSrc();
            if (string.IsNullOrWhiteSpace(projectDir) || !Directory.Exists(projectDir))
            {
                Console.Error.WriteLine("Usage: qudlab compile [--project DIR] | qudlab compile --file path.cs");
                Console.Error.WriteLine("Default project: Workspace/src (run setup first).");
                return 1;
            }

            result = compiler.CompileProject(r.Install, projectDir);
        }

        foreach (var d in result.Diagnostics)
            Console.WriteLine(d.ToString());
        var modRefs = result.ModReferenceCount > 0 ? $" + {result.ModReferenceCount} mod" : "";
        Console.WriteLine(result.Success
            ? $"COMPILE OK ({result.ReferenceCount - result.ModReferenceCount} refs from game Managed{modRefs})"
            : $"COMPILE FAILED ({result.ReferenceCount} refs{modRefs})");
        if (!string.IsNullOrEmpty(result.OutputPath))
            Console.WriteLine($"Wrote {result.OutputPath}");

        EnsureCache(path);
        if (_cache is not null)
        {
            QudModCompiler.ApplyDiagnosticsToCache(_cache, result);
            CacheIO.Save(_cache);
        }

        return result.Success ? 0 : 1;
    }

    static async Task<int> CmdSim(string[] args, string? path)
    {
        var r = _host.Startup(path);
        if (!r.Ok)
        {
            Console.Error.WriteLine(r.Message);
            return 1;
        }

        EnsureCache(path);
        var turns = GetInt(args, "--turns", 10);
        var species = GetOption(args, "--blueprint") ?? "Human";
        var parts = GetAllOptions(args, "--part");
        var mutations = GetAllOptions(args, "--mutation");
        var stress = HasFlag(args, "--stress");
        var remote = HasFlag(args, "--remote");
        var remotePort = GetInt(args, "--sim-port", SimIpc.DefaultPort);
        var scenario = GetOption(args, "--scenario");
        var genotype = GetOption(args, "--genotype");
        var subtype = GetOption(args, "--subtype");
        var chartype = GetOption(args, "--chartype");
        var pregen = GetOption(args, "--pregen");
        var gameMode = GetOption(args, "--game-mode");
        var cybernetics = GetAllOptions(args, "--cybernetic");
        var zoneId = GetOption(args, "--zone");
        var npcCount = GetInt(args, "--npcs", 0);
        if (npcCount == 0)
            npcCount = GetInt(args, "--npc-count", 0);
        var mapWidth = GetInt(args, "--map-width", 0);
        var mapHeight = GetInt(args, "--map-height", 0);
        var mapSpec = GetOption(args, "--map");
        if (!string.IsNullOrWhiteSpace(mapSpec) && CrowdLoadScenario.TryParseMap(mapSpec, out var mw, out var mh))
        {
            mapWidth = mw;
            mapHeight = mh;
        }

        var yd = HasFlag(args, "--yd");
        bool? waterFlow = HasFlag(args, "--no-water") ? false : HasFlag(args, "--water") ? true : null;
        bool? powerPipes = HasFlag(args, "--no-pipes") ? false : (HasFlag(args, "--pipes") || yd) ? true : null;

        var request = new QudLab.Core.Abstractions.SimRequest
        {
            BlueprintOrSpecies = species,
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
            YdDense = yd
        };

        QudLab.Core.Abstractions.SimSnapshot snap;
        IRestrictedSimulator? localSim = null;

        if (remote)
        {
            if (!await SimIpc.IsReachableAsync(port: remotePort))
            {
                Console.Error.WriteLine($"SimHost not reachable on 127.0.0.1:{remotePort}. Start: qudlab simhost");
                return 1;
            }

            Console.WriteLine($"[sim] remote → 127.0.0.1:{remotePort}");
            snap = await SimIpc.CallRemoteAsync(request, port: remotePort);
        }
        else
        {
            localSim = SimulatorFactory.Create(_host, cacheProvider: () => _cache ?? CacheIO.Load());
            snap = await localSim.RunTurnsAsync(request);
        }

        foreach (var line in snap.Log)
            Console.WriteLine(line);

        Console.WriteLine($"Timeline events: {snap.Timeline.Count}");
        Console.WriteLine($"Thread actions: {snap.ThreadActions.Count}");
        if (snap.Stress is not null)
        {
            Console.WriteLine(
                $"Stress: turns={snap.Stress.Turns} main={snap.Stress.MainTicks} workers={snap.Stress.WorkerPlaceholders} " +
                $"ms={snap.Stress.ElapsedMs} evt/turn={snap.Stress.EventsPerTurn:F1}");
        }

        foreach (var kv in snap.Stats.OrderBy(k => k.Key, StringComparer.OrdinalIgnoreCase))
            Console.WriteLine($"stat {kv.Key}={kv.Value}");

        if (_cache is not null)
        {
            (localSim ?? SimulatorFactory.Create(_host)).ApplySnapshotToCache(_cache, snap, scenario);
            CacheIO.Save(_cache);
        }

        return snap.Log.Any(l => l.StartsWith("REFUSED", StringComparison.Ordinal)) ? 1 : 0;
    }

    static int CmdSimHost(string[] args, string? path)
    {
        var port = GetInt(args, "--port", SimIpc.DefaultPort);
        var dll = Path.Combine(FindLabRoot(), "artifacts", "bin", "QudLab.SimHost", "Release", "net8.0", "QudLab.SimHost.dll");
        if (!File.Exists(dll))
            dll = Path.Combine(AppContext.BaseDirectory, "QudLab.SimHost.dll");
        if (!File.Exists(dll))
        {
            // Prefer sibling build output when running from Cli bin
            var sibling = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "QudLab.SimHost", "Release", "net8.0", "QudLab.SimHost.dll"));
            if (File.Exists(sibling)) dll = sibling;
        }

        if (!File.Exists(dll))
        {
            Console.Error.WriteLine("QudLab.SimHost.dll not found. Build the solution, then:");
            Console.Error.WriteLine($"  dotnet artifacts/bin/QudLab.SimHost/Release/net8.0/QudLab.SimHost.dll --port {port}");
            return 1;
        }

        var psi = new System.Diagnostics.ProcessStartInfo
        {
            FileName = "dotnet",
            ArgumentList = { dll, "--port", port.ToString() },
            UseShellExecute = false
        };
        if (!string.IsNullOrWhiteSpace(path))
        {
            psi.ArgumentList.Add("--path");
            psi.ArgumentList.Add(path);
        }

        Console.WriteLine($"Starting SimHost: dotnet \"{dll}\" --port {port}");
        var proc = System.Diagnostics.Process.Start(psi);
        if (proc is null)
        {
            Console.Error.WriteLine("Failed to start SimHost process.");
            return 1;
        }

        Console.WriteLine($"SimHost pid={proc.Id} (listening 127.0.0.1:{port}). This process stays attached until SimHost exits.");
        proc.WaitForExit();
        return proc.ExitCode;
    }

    static int CmdTemplate(string[] args)
    {
        var kind = args.ElementAtOrDefault(1)?.ToLowerInvariant();
        var name = args.ElementAtOrDefault(2) ?? "MyPart";
        var target = GetOption(args, "--target") ?? "XRL.World.GameObject";
        var text = kind switch
        {
            "part" => ModTemplates.NewPart(name),
            "mutation" => ModTemplates.NewMutation(name),
            "harmony" => ModTemplates.NewHarmonyPatch(name, target),
            _ => null
        };
        if (text is null)
        {
            Console.Error.WriteLine("Usage: qudlab template part|mutation|harmony ClassName [--target TypeName] [--write]");
            return 1;
        }

        if (HasFlag(args, "--write"))
        {
            var dir = DefaultWorkspaceSrc();
            if (string.IsNullOrWhiteSpace(dir))
            {
                Console.Error.WriteLine("Workspace/src not found — run qudlab setup first.");
                return 1;
            }

            Directory.CreateDirectory(dir);
            var fileName = ModTemplates.SuggestedFileName(kind!, name);
            var outPath = Path.Combine(dir, fileName);
            if (File.Exists(outPath) && !HasFlag(args, "--force"))
            {
                Console.Error.WriteLine($"Refusing to overwrite {outPath} (pass --force).");
                return 1;
            }

            File.WriteAllText(outPath, text);
            Console.WriteLine($"Wrote {outPath}");
            return 0;
        }

        Console.WriteLine(text);
        return 0;
    }

    static async Task<int> CmdOllama(string[] args)
    {
        EnsureCacheFresh(null, args);
        var client = new OllamaClient();
        var sub = args.ElementAtOrDefault(1)?.ToLowerInvariant();
        if (sub is "models" or "list")
        {
            if (!await client.IsAvailableAsync())
            {
                Console.Error.WriteLine("Ollama not reachable at " + client.Options.BaseUrl);
                Console.Error.WriteLine("Install/start: https://github.com/ollama/ollama");
                return 1;
            }
            foreach (var m in await client.ListModelsAsync())
                Console.WriteLine(m);
            return 0;
        }

        var mode = sub switch
        {
            "ask" or "chat" => "ask",
            "scan" or "audit" => "scan",
            "fix" or "repair" => "fix",
            "analyze" or "debug" or "sim" => "analyze",
            _ => "ask"
        };
        var promptStart = sub is "ask" or "chat" or "scan" or "audit" or "fix" or "repair" or "analyze" or "debug" or "sim"
            ? 2
            : 1;

        var taskFlag = GetOption(args, "--task");
        if (!string.IsNullOrWhiteSpace(taskFlag) && mode == "ask")
        {
            mode = taskFlag.Trim().ToLowerInvariant() switch
            {
                "fix" or "repair" => "fix",
                "scan" or "audit" => "scan",
                "analyze" or "debug" => "analyze",
                _ => "ask"
            };
        }

        var promptParts = new List<string>();
        for (var i = promptStart; i < args.Length; i++)
        {
            if (IsOllamaFlag(args[i]) && i + 1 < args.Length && !args[i + 1].StartsWith('-'))
            {
                i++;
                continue;
            }
            if (args[i] is "--apply" or "--no-apply" or "--simulate")
                continue;
            promptParts.Add(args[i]);
        }

        var prompt = string.Join(' ', promptParts);
        if (string.IsNullOrWhiteSpace(prompt) && mode == "ask" && sub is not "scan" and not "fix" and not "analyze" and not "audit" and not "repair" and not "debug" and not "sim")
        {
            Console.Error.WriteLine("Usage:");
            Console.Error.WriteLine("  qudlab ollama models");
            Console.Error.WriteLine("  qudlab ollama ask [--model M] <prompt>");
            Console.Error.WriteLine("  qudlab ollama scan [prompt]     # read every Workspace/src file + compile");
            Console.Error.WriteLine("  qudlab ollama fix [--no-apply] [prompt]");
            Console.Error.WriteLine("  qudlab ollama analyze [--turns N] [--blueprint Name] [prompt]");
            return 1;
        }

        if (!await client.IsAvailableAsync())
        {
            Console.Error.WriteLine("Ollama not reachable at " + client.Options.BaseUrl);
            Console.Error.WriteLine("https://github.com/ollama/ollama");
            return 1;
        }

        var project = ResolveProjectRoot(args) ?? DefaultWorkspaceSrc();
        string? ReadProjectFile(string? rel)
        {
            if (string.IsNullOrWhiteSpace(rel) || string.IsNullOrWhiteSpace(project))
                return null;
            var full = Path.GetFullPath(Path.Combine(project, rel.Replace('/', Path.DirectorySeparatorChar)));
            var root = Path.GetFullPath(project);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                return null;
            return File.Exists(full) ? File.ReadAllText(full) : null;
        }

        void WriteProjectFile(string rel, string content)
        {
            if (string.IsNullOrWhiteSpace(project))
                throw new InvalidOperationException("No project root");
            var full = Path.GetFullPath(Path.Combine(project, rel.Replace('/', Path.DirectorySeparatorChar)));
            var root = Path.GetFullPath(project);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Write path escapes Workspace/src");
            Directory.CreateDirectory(Path.GetDirectoryName(full)!);
            File.WriteAllText(full, content);
        }

        var ai = new LabAiService(
            client,
            () => _cache ?? CacheIO.Load(),
            () => _host.Install ?? _host.Startup(null).Install,
            ReadProjectFile,
            WriteProjectFile,
            FindLabRoot());

        var apply = !HasFlag(args, "--no-apply") && (mode == "fix" || HasFlag(args, "--apply"));
        var result = await ai.RunAsync(new AiAgentRequest
        {
            Prompt = prompt,
            Mode = mode,
            Model = GetOption(args, "--model"),
            Apply = apply,
            MaxRounds = GetInt(args, "--rounds", 10),
            Simulate = HasFlag(args, "--simulate") || mode == "analyze",
            Turns = GetInt(args, "--turns", 8),
            Blueprint = GetOption(args, "--blueprint") ?? "Human"
        });

        if (result.Tools.Count > 0)
        {
            Console.Error.WriteLine($"model={result.Model} mode={result.Mode} tools={result.Tools.Count}");
            foreach (var t in result.Tools)
                Console.Error.WriteLine($"  {t.Name} {t.Args} -> {TruncateCli(t.ResultPreview, 120)}");
        }

        if (result.Written.Count > 0)
            Console.Error.WriteLine("wrote: " + string.Join(", ", result.Written));

        Console.WriteLine(result.Reply);
        if (!result.Ok)
        {
            Console.Error.WriteLine(result.Error);
            return 1;
        }

        return 0;
    }

    static bool IsOllamaFlag(string a) =>
        a is "--task" or "--model" or "--rounds" or "--turns" or "--blueprint" or "--project" or "--path" or "--port";

    static string TruncateCli(string s, int max) =>
        string.IsNullOrEmpty(s) ? "" : (s.Length <= max ? s : s[..max] + "…");

    static void EnsureCache(string? path) => EnsureCacheFresh(path, Array.Empty<string>());

    static void EnsureCacheFresh(string? path, string[] args)
    {
        var r = _host.Startup(path);
        var project = ResolveProjectRoot(args) ?? DefaultWorkspaceSrc();

        _cache ??= CacheIO.Load();
        if (r.Ok && r.Install is not null && CacheIO.IsStale(_cache, r.Install))
        {
            Console.WriteLine("Cache missing/stale — reindexing…");
            _cache = new QudIndexer().Build(r.Install, project);
            CacheIO.Save(_cache);
            return;
        }

        if (_cache is null && r.Ok && r.Install is not null)
        {
            _cache = new QudIndexer().Build(r.Install, project);
            CacheIO.Save(_cache);
            return;
        }

        // Refresh project file list even when type cache is fresh
        if (_cache is not null && project is not null && Directory.Exists(project))
        {
            CacheIO.ScanProject(_cache.Project, project);
            CacheIO.Save(_cache);
        }
    }

    static string? ResolveProjectRoot(string[] args)
    {
        var opt = GetOption(args, "--project");
        return QudModPaths.ResolveProject(opt, DefaultWorkspaceSrc());
    }

    static string? DefaultWorkspaceSrc()
    {
        var p = Path.Combine(FindLabRoot(), "Workspace", "src");
        return Directory.Exists(p) ? p : null;
    }

    static int CmdProject(string[] args)
    {
        var sub = args.ElementAtOrDefault(1)?.ToLowerInvariant();
        switch (sub)
        {
            case null:
            case "list":
            case "ls":
            {
                var mods = QudModPaths.ListAllMods(_host.Install?.RootPath);
                Console.WriteLine($"LocalLow: {QudModPaths.LocalModsRoot()}");
                var ws = QudModPaths.WorkshopModsRoot(_host.Install?.RootPath);
                if (ws is not null)
                    Console.WriteLine($"Workshop: {ws}");
                Console.WriteLine($"Count: {mods.Count}");
                foreach (var m in mods)
                    Console.WriteLine($"{m.Source,-9} {(m.Id ?? "-"),-28} cs={m.CsFileCount,4}  {m.Title ?? m.Name}");
                var active = QudModPaths.ResolveProject(null, DefaultWorkspaceSrc());
                Console.WriteLine();
                Console.WriteLine("Active: " + (active ?? "(none)"));
                return 0;
            }
            case "get":
            case "show":
            {
                var active = QudModPaths.ResolveProject(GetOption(args, "--project"), DefaultWorkspaceSrc());
                Console.WriteLine(active ?? "(none — default Workspace/src missing)");
                Console.WriteLine("Config: " + QudModPaths.ConfigPath());
                return 0;
            }
            case "set":
            {
                var target = args.ElementAtOrDefault(2) ?? GetOption(args, "--path") ?? GetOption(args, "--project");
                if (string.IsNullOrWhiteSpace(target))
                {
                    Console.Error.WriteLine("Usage: qudlab project set <path|mod-id|title-fragment>");
                    return 1;
                }

                string? resolved = Directory.Exists(target) ? Path.GetFullPath(target) : null;
                if (resolved is null)
                {
                    var hit = QudModPaths.FindMod(target, _host.Install?.RootPath);
                    resolved = hit?.Path;
                }

                if (resolved is null || !Directory.Exists(resolved))
                {
                    Console.Error.WriteLine("Not found: " + target);
                    return 1;
                }

                var manifest = QudModPaths.ReadManifest(resolved);
                QudModPaths.SaveConfig(new ActiveProjectConfig
                {
                    ProjectPath = resolved,
                    ProjectName = QudModPaths.StripQudMarkup(manifest?.Title) ?? Path.GetFileName(resolved)
                });
                _cache ??= CacheIO.Load();
                if (_cache is not null)
                {
                    CacheIO.ScanProject(_cache.Project, resolved);
                    CacheIO.Save(_cache);
                    Console.WriteLine("Rescanned: " + _cache.Project.Files.Count + " files");
                }
                Console.WriteLine("Active project: " + resolved);
                Console.WriteLine("Saved: " + QudModPaths.ConfigPath());
                return 0;
            }
            case "clear":
            {
                QudModPaths.SaveConfig(new ActiveProjectConfig());
                Console.WriteLine("Cleared active project — will fall back to Workspace/src / QUDLAB_PROJECT.");
                return 0;
            }
            case "conflicts":
            case "errors":
            {
                Console.WriteLine(QudModPaths.ReadTypeConflicts());
                return 0;
            }
            default:
                Console.Error.WriteLine("Usage: qudlab project list|get|set <path|id>|clear|conflicts");
                return 1;
        }
    }

    static int CmdEvents(string[] args, string? path)
    {
        var sub = args.ElementAtOrDefault(1)?.ToLowerInvariant() ?? "pools";
        EnsureCache(path);
        var cache = _cache;
        var install = _host.Install ?? _host.Startup(path).Install;

        switch (sub)
        {
            case "scan":
            {
                if (install is null)
                {
                    Console.Error.WriteLine("no install — run qudlab gate");
                    return 1;
                }
                if (cache is null)
                {
                    Console.Error.WriteLine("no cache — run qudlab index");
                    return 1;
                }
                Console.WriteLine("Scanning MinEvent pools (game + mod ModAssemblies)…");
                var audit = EventPoolAuditor.Audit(install);
                audit.RuntimePoolReport = EventPoolReport.TailRuntimePools(80);
                cache.EventGraph.PoolAudit = audit;
                EventPoolAuditor.SaveAudit(audit);
                CacheIO.Save(cache);
                PrintEventPoolSummary(audit);
                return 0;
            }
            case "pools":
            default:
            {
                var audit = cache?.EventGraph.PoolAudit ?? EventPoolReport.LoadCached();
                if (audit is null)
                {
                    Console.Error.WriteLine("no event pool audit — run: qudlab events scan");
                    return 1;
                }
                PrintEventPoolSummary(audit);
                var mod = GetOption(args, "--mod");
                var q = GetOption(args, "--q") ?? GetOption(args, "--grep");
                var kind = GetOption(args, "--cache") ?? GetOption(args, "--kind");
                var top = GetInt(args, "--top", 40);
                var entries = audit.Entries.AsEnumerable();
                if (!string.IsNullOrWhiteSpace(mod))
                    entries = entries.Where(e => e.IsMod && (
                        (e.ModFolder?.Contains(mod, StringComparison.OrdinalIgnoreCase) ?? false)
                        || e.TypeFullName.Contains(mod, StringComparison.OrdinalIgnoreCase)));
                if (!string.IsNullOrWhiteSpace(q))
                    entries = entries.Where(e =>
                        e.TypeFullName.Contains(q, StringComparison.OrdinalIgnoreCase)
                        || (e.Assembly?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));
                if (!string.IsNullOrWhiteSpace(kind))
                    entries = entries.Where(e => e.CacheKind.Equals(kind, StringComparison.OrdinalIgnoreCase));

                Console.WriteLine();
                Console.WriteLine("entries (top " + top + "):");
                foreach (var e in entries.Where(x => !x.IsAbstract).Take(top))
                {
                    var tag = e.IsMod ? "MOD" : "game";
                    Console.WriteLine($"{tag}\t{e.CacheKind}\t{e.TypeFullName}");
                    if (e.IsMod && !string.IsNullOrWhiteSpace(e.ModFolder))
                        Console.WriteLine("\t" + e.ModFolder);
                }

                Console.WriteLine();
                Console.WriteLine(EventPoolReport.TailRuntimePools(40));
                Console.WriteLine("full audit: " + EventPoolReport.AuditLogPath());
                return 0;
            }
        }
    }

    static void PrintEventPoolSummary(EventPoolAudit audit)
    {
        Console.WriteLine($"built {audit.BuiltAt:u}");
        Console.WriteLine($"events={audit.TotalEvents} pooled={audit.PooledCount} singleton={audit.SingletonCount}");
        Console.WriteLine($"modEvents={audit.ModEventCount} modPooled={audit.ModPooledCount} idConflicts={audit.IdConflicts.Count}");
        if (audit.IdConflicts.Count > 0)
        {
            Console.WriteLine("id conflicts:");
            foreach (var c in audit.IdConflicts.Take(20))
                Console.WriteLine($"  {c.EventId}: {string.Join(" | ", c.Types)}");
        }
        if (audit.ScanErrors.Count > 0)
        {
            Console.WriteLine("scan errors:");
            foreach (var e in audit.ScanErrors.Take(10))
                Console.WriteLine("  " + e);
        }
    }

    static int CmdLogs(string[] args)
    {
        var sub = args.ElementAtOrDefault(1)?.ToLowerInvariant() ?? "tail";
        switch (sub)
        {
            case "conflicts":
            case "errors":
                Console.WriteLine(QudModPaths.ReadTypeConflicts());
                return 0;
            case "tail":
            default:
            {
                var kind = GetOption(args, "--kind") ?? "all";
                var tail = GetInt(args, "--tail", 200);
                var grep = GetOption(args, "--grep") ?? GetOption(args, "--q");
                var snap = GameLogTail.Snapshot(kind, tail, grep);
                Console.WriteLine(GameLogTail.FormatSnapshot(snap));
                return 0;
            }
        }
    }

    static int PrintHelp()
    {
        Console.WriteLine("""
            Qud Lab CLI — requires owned Steam/GOG Caves of Qud install.
            ThreadingAPI is a separate WIP mod and is NOT bundled here.

            Commands:
              setup [--path DIR]             Gate + sync-refs + index (recommended first run)
              gate|doctor [--path DIR]       Verify install + cache stale status
              sync-refs [--path DIR]         Write Workspace HintPaths for Copilot
              refs [--path DIR]              List Managed / IDE-essential reference paths
              index [--path DIR] [--project DIR]
                                             Build intelligence cache (schema 2.0)
              serve [--port N] [--project DIR]
                                             HTTP mod-assistant (/search, /type, /mutations, …)
              project list|get|set|clear|conflicts
                                             Active mod for AI/compile (LocalLow + Workshop)
              logs tail [--kind all|build|player|threading] [--tail N] [--grep TEXT]
              logs conflicts                   TYPE CONFLICTS from build_log + Player.log
              events pools [--mod FRAG] [--q TEXT] [--cache Pool|Singleton] [--top N]
              events scan                      Rescan MinEvent pools (game + mod DLLs)
              explain <symbol>               Lookup type or blueprint from cache
              compile [--project DIR]        Compile active project → Workspace/bin/ (or --project)
              compile --file path.cs         Single-file compile (DLL next to source)
              simulate [--turns N] [--blueprint Name] [--part P] [--mutation M] [--stress] [--remote]
                       [--scenario lag-diagnose|lag-suite|npc-cta-no-spend|move-input-lag|crowd-load|yd-load|player-turn-starvation|cta-inf-turn|broodmother-bta-starve|chargen|worldgen-getzone]
                       [--genotype Name] [--subtype Name] [--chartype New|Pregen|Random]
                       [--pregen Name] [--game-mode Classic] [--cybernetic Blueprint] [--zone JoppaWorld.x.y.1.1.10]
                       [--npcs N] [--map WxH] [--yd] [--no-water] [--no-pipes]
              simhost [--port N]             External SimHost TCP :47822 (crash isolation)
              template part|mutation|harmony Name [--target T] [--write]
              ollama models
              ollama ask [--model M] <prompt>
              ollama scan [prompt]            Read every active-project file + compile
              ollama fix [--no-apply] [prompt]
              ollama analyze [--turns N] [--blueprint Name] [prompt]

            Env: QUDLAB_QUD_PATH, QUDLAB_PROJECT, OLLAMA_HOST, QUDLAB_OLLAMA_MODEL

            Phase 6 workflow:
              1) qudlab setup && qudlab serve
              2) start Ollama  e.g. ollama pull qwen3:8b
              3) POST /project/set {"query":"Broodmother"}  or  qudlab project set \"Blink\"
              4) Unity/GUI mod picker — hot switch without restart
              5) GET /logs/game?kind=threading  after in-game repro (ThreadingAPI action log)
              6) qudlab simulate --scenario cta-inf-turn --turns 8 [--stress]
              7) qudlab simulate --scenario worldgen-getzone [--zone JoppaWorld.2.23.1.1.10] [--stress]
              8) qudlab simulate --scenario crowd-load --turns 8 [--yd] [--stress]
                 # baseline = city water + Yd pipes on main; --stress = ThreadingAPI offload
            """);
        return 0;
    }

    static int Unknown(string cmd)
    {
        Console.Error.WriteLine($"Unknown command: {cmd}");
        PrintHelp();
        return 1;
    }

    static bool HasFlag(string[] args, string name) =>
        args.Any(a => a.Equals(name, StringComparison.OrdinalIgnoreCase));

    static string[] GetAllOptions(string[] args, string name)
    {
        var list = new List<string>();
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i].Equals(name, StringComparison.OrdinalIgnoreCase))
                list.Add(args[i + 1]);
        }
        return list.ToArray();
    }

    static string? GetOption(string[] args, string name)
    {
        for (var i = 0; i < args.Length - 1; i++)
            if (args[i].Equals(name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    static int GetInt(string[] args, string name, int fallback)
    {
        var s = GetOption(args, name);
        return int.TryParse(s, out var n) ? n : fallback;
    }
}
