using ApiMigrator.Core;
using ApiMigrator.Cli;

return IsolatedBootstrap.Execute(args, RunCli);

int RunCli(string[] args)
{
var toolsRoot = IsolatedBootstrap.FindToolsRoot();
var dataDir = Path.Combine(toolsRoot, "data");
var defaultDump = Path.Combine(dataDir, "obsolete_api_dump.json");
var defaultRules = Path.Combine(dataDir, "curated_rewrite_rules.json");
var defaultManaged = SteamInstall.ManagedDirOrFallback;
var modsRoot = CoqPaths.ResolveModsRoot(toolsRoot);

if (args.Length == 0)
{
    PrintUsage();
    return 1;
}

try
{
switch (args[0].ToLowerInvariant())
{
    case "migrate":
        return RunMigrate(args.Skip(1).ToArray());
    case "refresh-dump":
        return RunRefreshDump(args.Skip(1).ToArray());
    case "resolve-cs0618":
        return RunResolveCs0618(args.Skip(1).ToArray());
    case "convert-cp437":
        return RunConvertCp437(args.Skip(1).ToArray());
    case "sync-version":
        return RunSyncVersion(args.Skip(1).ToArray());
    case "switch-api":
    case "switch-profile":
        return RunSwitchApi(args.Skip(1).ToArray());
    case "compile-rules":
        return RunCompileRules(args.Skip(1).ToArray());
    case "export-charts":
        return RunExportCharts(args.Skip(1).ToArray());
    case "export-promotions":
        return RunExportPromotions(args.Skip(1).ToArray());
    case "apply-promotions":
        return RunApplyPromotions(args.Skip(1).ToArray());
    case "ollama-probe":
        return RunOllamaProbe(args.Skip(1).ToArray()).GetAwaiter().GetResult();
    case "ollama-suggest":
        return RunOllamaSuggest(args.Skip(1).ToArray()).GetAwaiter().GetResult();
    default:
        PrintUsage();
        return 1;
}
}
catch (ArgumentException ex)
{
    Console.Error.WriteLine(ex.Message);
    return 1;
}

int RunMigrate(string[] a)
{
    var opts = new MigrationOptions
    {
        DumpPath = defaultDump,
        RulesPath = defaultRules,
    };
    var paths = new List<string>();
    string? reportPath = null;
    var managedDir = defaultManaged;
    var skipSync = false;

    for (var i = 0; i < a.Length; i++)
    {
        if (IsolatedBootstrap.IsPathFlag(a[i]))
        {
            i = IsolatedBootstrap.ConsumePathArgs(a, i, paths);
            continue;
        }
        switch (a[i])
        {
            case "--mod":
                opts.ModFilter = IsolatedBootstrap.RequireValue(a, ref i, "--mod");
                break;
            case "--apply":
                opts.Apply = true;
                break;
            case "--no-backup":
                opts.Backup = false;
                break;
            case "--report":
                reportPath = IsolatedBootstrap.RequireValue(a, ref i, "--report");
                break;
            case "--dump":
                opts.DumpPath = IsolatedBootstrap.RequireValue(a, ref i, "--dump");
                break;
            case "--rules":
                opts.RulesPath = IsolatedBootstrap.RequireValue(a, ref i, "--rules");
                break;
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, "--managed");
                break;
            case "--no-version-sync":
                skipSync = true;
                break;
            case "--include-workshop":
                paths.Add(SteamInstall.WorkshopContentDirOrFallback);
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    if (!skipSync && opts.DumpPath == defaultDump)
        DumpVersionControl.EnsureActiveProfile(dataDir, managedDir, Console.WriteLine);

    opts.Paths = paths.Count > 0 ? paths : new List<string> { modsRoot };
    reportPath ??= Path.Combine(toolsRoot, "reports", $"ApiMigration_{DateTime.Now:yyyyMMdd_HHmmss}.md");

    Console.WriteLine("Scan roots:");
    foreach (var p in opts.Paths) Console.WriteLine($"  {p}");

    var report = MigrationRunner.Run(opts, Console.WriteLine, (done, total) =>
    {
        if (done == 1 || done % 25 == 0 || done == total)
            Console.WriteLine($"Scanning {done}/{total}...");
    });
    ReportWriter.WriteMarkdown(report, reportPath);

    Console.WriteLine();
    Console.WriteLine("=== Summary ===");
    Console.WriteLine($"Mode:                     {(opts.Apply ? "APPLY (files written)" : "DRY-RUN (no files written)")}");
    Console.WriteLine($"Files scanned:            {report.FilesScanned}");
    Console.WriteLine($"Files needing attention:  {report.FileResults.Count}");
    Console.WriteLine($"Auto-fix rewrites:        {report.TotalAutoFixes}");
    Console.WriteLine($"Remaining manual hits:    {report.TotalRemainingHits}");
    Console.WriteLine($"Report written to:        {reportPath}");

    return 0;
}

int RunRefreshDump(string[] a)
{
    var managedDir = defaultManaged;
    var dumpPath = defaultDump;
    var save = false;
    var skipSync = false;
    var dlls = new List<string> { "Assembly-CSharp.dll" };

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, "--managed");
                break;
            case "--dump":
                dumpPath = IsolatedBootstrap.RequireValue(a, ref i, "--dump");
                break;
            case "--dll":
                dlls.Add(IsolatedBootstrap.RequireValue(a, ref i, "--dll"));
                break;
            case "--save":
                save = true;
                break;
            case "--no-version-sync":
                skipSync = true;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    if (!skipSync && dumpPath == defaultDump)
        DumpVersionControl.EnsureActiveProfile(dataDir, managedDir, Console.WriteLine);

    Console.WriteLine($"Reflecting: {string.Join(", ", dlls)}");
    Console.WriteLine($"Managed dir: {managedDir}");
    Console.WriteLine("(read-only - Managed DLLs are never modified)");
    Console.WriteLine();

    var preview = DumpRefresher.Scan(managedDir, dlls, dumpPath);
    foreach (var w in preview.Scan.Warnings) Console.WriteLine("WARNING: " + w);
    Console.WriteLine($"Types scanned: {preview.Scan.TypesScanned}");
    Console.WriteLine($"Obsolete members found: {preview.Scan.Members.Count}");

    if (preview.Diff is { } diff)
    {
        Console.WriteLine();
        Console.WriteLine("=== Diff vs current dump ===");
        Console.WriteLine($"Unchanged:       {diff.UnchangedCount}");
        Console.WriteLine($"Added:           {diff.Added.Count}");
        Console.WriteLine($"Removed:         {diff.Removed.Count}");
        Console.WriteLine($"Message changed: {diff.MessageChanged.Count}");
        foreach (var m in diff.Added) Console.WriteLine($"  + {m.Type}.{m.Member} :: {m.ObsoleteMessage}");
        foreach (var e in diff.Removed) Console.WriteLine($"  - {e.Type}.{e.Member}");
        foreach (var (oldE, newM) in diff.MessageChanged)
            Console.WriteLine($"  ~ {oldE.FullName} :: '{oldE.ObsoleteMessage}' -> '{newM.ObsoleteMessage}'");
    }
    else
    {
        Console.WriteLine("No existing dump found to diff against - this would be a brand new dump.");
    }

    if (save)
    {
        var managedPaths = dlls.Select(d => Path.Combine(managedDir, d));
        var merged = DumpRefresher.BuildMerged(preview, managedPaths);
        var backupDir = Path.Combine(dataDir, "backups");
        var backedUpTo = DumpRefresher.SaveWithBackup(dumpPath, backupDir, merged,
            dataDir: dumpPath == defaultDump ? dataDir : Path.GetDirectoryName(Path.GetFullPath(dumpPath)),
            managedDir: managedDir);
        if (backedUpTo is not null) Console.WriteLine($"Backed up existing dump to: {backedUpTo}");
        Console.WriteLine($"Saved merged dump ({merged.Entries.Count} entries total) to: {dumpPath}");
        var ver = DumpVersionControl.TryGetManagedFileVersion(managedDir);
        if (ver is not null)
            Console.WriteLine($"Version profile updated: {DumpVersionControl.ProfileDirectory(dataDir, ver)}");
    }
    else
    {
        Console.WriteLine();
        Console.WriteLine("Dry run only - re-run with --save to write the refreshed dump (a timestamped backup of the old one is kept automatically).");
    }

    return 0;
}

int RunResolveCs0618(string[] a)
{
    var opts = new Cs0618Resolver.Options
    {
        DumpPath = defaultDump,
        RulesPath = defaultRules,
        ManagedDir = defaultManaged,
        Compile = false,
    };
    string? reportPath = null;
    var skipSync = false;

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--mod":
            case "--path":
                opts.ModFolder = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--managed":
                opts.ManagedDir = IsolatedBootstrap.RequireValue(a, ref i, "--managed");
                break;
            case "--no-version-sync":
                skipSync = true;
                break;
            case "--from-log":
                opts.WarningLogPath = IsolatedBootstrap.RequireValue(a, ref i, "--from-log");
                break;
            case "--compile":
                opts.Compile = true;
                break;
            case "--no-compile":
                opts.Compile = false;
                break;
            case "--apply":
                opts.Apply = true;
                break;
            case "--no-backup":
                opts.Backup = false;
                break;
            case "--report":
                reportPath = IsolatedBootstrap.RequireValue(a, ref i, "--report");
                break;
            case "--dump":
                opts.DumpPath = IsolatedBootstrap.RequireValue(a, ref i, "--dump");
                break;
            case "--rules":
                opts.RulesPath = IsolatedBootstrap.RequireValue(a, ref i, "--rules");
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    if (string.IsNullOrWhiteSpace(opts.ModFolder) && string.IsNullOrWhiteSpace(opts.WarningLogPath))
    {
        Console.Error.WriteLine("resolve-cs0618 requires --mod <folder> and/or --from-log <file>.");
        return 1;
    }

    if (!skipSync && opts.DumpPath == defaultDump)
        DumpVersionControl.EnsureActiveProfile(dataDir, opts.ManagedDir, Console.WriteLine);

    // Default: compile when a mod folder is given and no log was supplied.
    if (!string.IsNullOrWhiteSpace(opts.ModFolder) && string.IsNullOrWhiteSpace(opts.WarningLogPath) &&
        !a.Any(x => x is "--compile" or "--no-compile"))
        opts.Compile = true;

    reportPath ??= Path.Combine(toolsRoot, "reports", $"Cs0618_{DateTime.Now:yyyyMMdd_HHmmss}.md");

    Console.WriteLine("CS0618 resolver (no game launch required)");
    if (!string.IsNullOrWhiteSpace(opts.ModFolder)) Console.WriteLine($"  Mod:     {opts.ModFolder}");
    if (!string.IsNullOrWhiteSpace(opts.WarningLogPath)) Console.WriteLine($"  Log:     {opts.WarningLogPath}");
    Console.WriteLine($"  Compile: {opts.Compile}");
    Console.WriteLine($"  Apply:   {opts.Apply}");

    var result = Cs0618Resolver.Run(opts, Console.WriteLine);

    Console.WriteLine();
    Console.WriteLine("=== Top obsolete symbols ===");
    foreach (var kv in result.SymbolCounts.OrderByDescending(kv => kv.Value).Take(20))
        Console.WriteLine($"  {kv.Value,4}  {kv.Key}");

    if (result.Migration is { } mig)
        ReportWriter.WriteMarkdown(mig, reportPath);
    else
        File.WriteAllText(reportPath, "# CS0618 Resolver\n\nNo migration report (no resolvable files).\n");

    // Append harvested warnings
    using (var sw = File.AppendText(reportPath))
    {
        sw.WriteLine();
        sw.WriteLine("## Harvested CS0618 warnings");
        sw.WriteLine();
        sw.WriteLine($"Total: **{result.Warnings.Count}**");
        sw.WriteLine();
        foreach (var w in result.Warnings)
            sw.WriteLine($"- `{w.FilePath}`:{w.Line} — `{w.ObsoleteSymbol}` — {w.ObsoleteMessage}");
        if (result.Notes.Count > 0)
        {
            sw.WriteLine();
            sw.WriteLine("## Notes");
            foreach (var n in result.Notes) sw.WriteLine("- " + n);
        }
    }

    Console.WriteLine($"Report: {reportPath}");
    return 0;
}

int RunCompileRules(string[] a)
{
    var chartsDir = RuleChartCompiler.DefaultChartsDir(dataDir);
    string? outPath = defaultRules;
    var check = false;
    var managedDir = defaultManaged;
    var updateProfile = true;

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--charts":
                chartsDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--out":
                outPath = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--check":
                check = true;
                break;
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--no-profile":
                updateProfile = false;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    var result = RuleChartCompiler.Compile(new RuleChartCompiler.CompileOptions
    {
        ChartsDir = chartsDir,
        OutPath = outPath,
        DataDir = dataDir,
        ManagedDir = managedDir,
        CheckOnly = check,
        UpdateVersionProfile = updateProfile && !check,
    }, Console.WriteLine);

    foreach (var w in result.Warnings) Console.WriteLine("WARNING: " + w);
    foreach (var e in result.Errors) Console.Error.WriteLine("ERROR: " + e);

    Console.WriteLine();
    Console.WriteLine($"Rules: {result.RuleCount}  Notes: {result.NoteCount}  PostEnsureUsings: {result.PostEnsureCount}");
    if (check)
    {
        if (result.Errors.Count > 0) return 1;
        if (result.DiffersFromExisting)
        {
            Console.Error.WriteLine("Charts are out of date vs curated_rewrite_rules.json — run compile-rules.");
            return 2;
        }
        Console.WriteLine("OK — compiled charts match existing curated_rewrite_rules.json");
        return 0;
    }

    if (!result.Ok) return 1;
    Console.WriteLine($"Wrote: {result.OutPath}");
    if (result.ProfileDir is not null) Console.WriteLine($"Profile: {result.ProfileDir}");
    return 0;
}

int RunExportPromotions(string[] a)
{
    var promotionsDir = PromotionChartCompiler.DefaultPromotionsDir(dataDir);
    var dumpPath = defaultDump;
    var merge = true;
    var includeAuto = false;

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--promotions":
                promotionsDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--dump":
                dumpPath = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--no-merge":
                merge = false;
                break;
            case "--include-autofixable":
                includeAuto = true;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    var result = PromotionChartCompiler.Export(new PromotionChartCompiler.ExportOptions
    {
        DumpPath = dumpPath,
        PromotionsDir = promotionsDir,
        MergeExisting = merge,
        IncludeAutoFixable = includeAuto,
        NeedsManualOnly = true,
    }, Console.WriteLine);

    foreach (var e in result.Errors) Console.Error.WriteLine("ERROR: " + e);
    if (!result.Ok) return 1;

    Console.WriteLine();
    Console.WriteLine($"Exported {result.EntryCount} needsManual entries → {promotionsDir}");
    if (result.MergedFromExisting > 0)
        Console.WriteLine($"Merged prior Status/ProposedRule from {result.MergedFromExisting} existing sheet entries.");
    Console.WriteLine("Edit Status=Promote + ProposedRule, then: apply-promotions");
    return 0;
}

int RunApplyPromotions(string[] a)
{
    var promotionsDir = PromotionChartCompiler.DefaultPromotionsDir(dataDir);
    var chartsDir = RuleChartCompiler.DefaultChartsDir(dataDir);
    var dumpPath = defaultDump;
    var dry = false;
    var noCompile = false;
    var managedDir = defaultManaged;

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--promotions":
                promotionsDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--charts":
                chartsDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--dump":
                dumpPath = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--dry-run":
                dry = true;
                break;
            case "--no-compile":
                noCompile = true;
                break;
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    var result = PromotionChartCompiler.Apply(new PromotionChartCompiler.ApplyOptions
    {
        PromotionsDir = promotionsDir,
        DumpPath = dumpPath,
        ChartsDir = chartsDir,
        DataDir = dataDir,
        ManagedDir = managedDir,
        CompileRulesAfter = !noCompile && !dry,
        UpdateVersionProfile = !dry,
        DryRun = dry,
    }, Console.WriteLine);

    foreach (var w in result.Warnings) Console.WriteLine("WARNING: " + w);
    foreach (var e in result.Errors) Console.Error.WriteLine("ERROR: " + e);

    Console.WriteLine();
    Console.WriteLine($"Promote={result.Promoted}  Skip={result.Skipped}  AdviceOnly={result.AdviceOnly}  Candidate={result.Candidates}");
    if (!result.Ok) return 1;
    if (result.PromotedChartPath is not null) Console.WriteLine($"Promoted chart: {result.PromotedChartPath}");
    if (result.CompileResult is { } cr)
        Console.WriteLine($"Compiled rules: {cr.RuleCount} → {cr.OutPath}");
    return 0;
}

int RunExportCharts(string[] a)
{
    var chartsDir = RuleChartCompiler.DefaultChartsDir(dataDir);
    var rulesPath = defaultRules;
    var force = false;

    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--charts":
                chartsDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--rules":
                rulesPath = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--force":
                force = true;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    var result = RuleChartCompiler.Export(new RuleChartCompiler.ExportOptions
    {
        RulesPath = rulesPath,
        ChartsDir = chartsDir,
        Overwrite = force,
    }, Console.WriteLine);

    foreach (var e in result.Errors) Console.Error.WriteLine("ERROR: " + e);
    if (!result.Ok) return 1;

    Console.WriteLine();
    Console.WriteLine($"Exported {result.RuleCount} rules + {result.NoteCount} notes → {chartsDir}");
    foreach (var f in result.WrittenFiles) Console.WriteLine("  " + f);
    Console.WriteLine();
    Console.WriteLine("Next: edit charts, then: ApiMigrator.Cli compile-rules");
    return 0;
}

int RunSyncVersion(string[] a)
{
    var managedDir = defaultManaged;
    var saveProfile = false;
    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--save-profile":
                saveProfile = true;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    var resolved = DumpVersionControl.EnsureActiveProfile(dataDir, managedDir, Console.WriteLine);
    if (saveProfile)
    {
        var dir = DumpVersionControl.SaveProfileFromActive(dataDir, managedDir: managedDir,
            notes: "Explicit sync-version --save-profile.");
        Console.WriteLine($"Saved active dump+rules profile → {dir}");
    }
    else
    {
        Console.WriteLine(resolved.Message);
        Console.WriteLine($"Active dump:  {resolved.ActiveDumpPath}");
        Console.WriteLine($"Active rules: {resolved.ActiveRulesPath}");
        if (resolved.ProfileDir is not null)
            Console.WriteLine($"Live profile: {resolved.ProfileDir}");
    }
    return 0;
}

int RunSwitchApi(string[] a)
{
    var managedDir = defaultManaged;
    var listOnly = false;
    string? target = null;
    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--list":
                listOnly = true;
                break;
            case "--managed":
                managedDir = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            default:
                if (a[i].StartsWith('-'))
                {
                    Console.Error.WriteLine($"Unknown switch-api option: {a[i]}");
                    return 1;
                }
                if (target is not null)
                {
                    Console.Error.WriteLine("switch-api takes a single profile (public | lang | live | FileVersion).");
                    return 1;
                }
                target = a[i];
                break;
        }
    }

    Console.WriteLine(DumpVersionControl.FormatProfileStatus(dataDir, managedDir));
    Console.WriteLine();
    Console.WriteLine(DumpVersionControl.DescribeAvailableProfiles(dataDir));

    if (listOnly || target is null)
        return 0;

    Console.WriteLine();
    try
    {
        var resolved = DumpVersionControl.SwitchActiveProfile(dataDir, target, managedDir, Console.WriteLine);
        Console.WriteLine($"Active dump:  {resolved.ActiveDumpPath}");
        Console.WriteLine($"Active rules: {resolved.ActiveRulesPath}");
        if (resolved.ProfileDir is not null)
            Console.WriteLine($"Profile dir:  {resolved.ProfileDir}");
        return 0;
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine(ex.Message);
        return 1;
    }
}

int RunConvertCp437(string[] a)
{
    var opts = new Cp437Converter.Options();
    var paths = new List<string>();
    string? reportPath = null;

    for (var i = 0; i < a.Length; i++)
    {
        if (IsolatedBootstrap.IsPathFlag(a[i]))
        {
            i = IsolatedBootstrap.ConsumePathArgs(a, i, paths);
            continue;
        }
        switch (a[i])
        {
            case "--mod":
                opts.ModFilter = IsolatedBootstrap.RequireValue(a, ref i, "--mod");
                break;
            case "--apply":
                opts.Apply = true;
                break;
            case "--no-backup":
                opts.Backup = false;
                break;
            case "--report":
                reportPath = IsolatedBootstrap.RequireValue(a, ref i, "--report");
                break;
            case "--include-workshop":
                paths.Add(SteamInstall.WorkshopContentDirOrFallback);
                break;
            case "--convert-ambiguous":
                opts.ConvertAmbiguousEscapes = true;
                break;
            case "--force-xml-utf8":
                opts.ForceXmlUtf8Encoding = true;
                break;
            case "--no-xml-encoding":
                opts.EnsureXmlUtf8Encoding = false;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    opts.Paths = paths.Count > 0 ? paths : new List<string> { modsRoot };
    reportPath ??= Path.Combine(toolsRoot, "reports", $"Cp437_{DateTime.Now:yyyyMMdd_HHmmss}.md");
    opts.ReportPath = reportPath;

    Console.WriteLine("CP437 → UTF-16 converter (no game launch required)");
    Console.WriteLine("Scan roots:");
    foreach (var p in opts.Paths) Console.WriteLine($"  {p}");
    Console.WriteLine($"Apply: {opts.Apply}  Ambiguous escapes: {opts.ConvertAmbiguousEscapes}");

    var report = Cp437Converter.Run(opts, Console.WriteLine);

    Console.WriteLine();
    Console.WriteLine("=== Summary ===");
    Console.WriteLine($"Mode:           {(opts.Apply ? "APPLY" : "DRY-RUN")}");
    Console.WriteLine($"Files scanned:  {report.FilesScanned}");
    Console.WriteLine($"Files w/ hits:  {report.FileResults.Count}");
    Console.WriteLine($"Auto-fixes:     {report.TotalAutoFixes}");
    Console.WriteLine($"Needs review:   {report.TotalReviewHits}");
    Console.WriteLine($"Report:         {reportPath}");

    return 0;
}

async Task<int> RunOllamaProbe(string[] a)
{
    var ollama = new OllamaOptions();
    for (var i = 0; i < a.Length; i++)
    {
        switch (a[i])
        {
            case "--url":
            case "--base-url":
                ollama.BaseUrl = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--cloud":
                ollama.UseCloud = true;
                break;
            case "--api-key":
                ollama.ApiKey = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    if (ollama.UseCloud || OllamaClient.IsCloudHost(ollama.BaseUrl))
        ollama.UseCloud = true;

    var status = await OllamaClient.ProbeAsync(ollama);
    Console.WriteLine(status.Summary);
    if (status.Available)
    {
        foreach (var m in status.Models)
            Console.WriteLine("  " + m);
    }
    else if (status.Cloud)
    {
        if (string.IsNullOrWhiteSpace(OllamaClient.ResolveApiKey(ollama.ApiKey)))
        {
            Console.WriteLine("Hint: set OLLAMA_API_KEY or pass --api-key (https://ollama.com/settings/keys).");
            Console.WriteLine("Local *-cloud models: ollama signin && ollama pull gpt-oss:120b-cloud (no --cloud).");
        }
        Console.WriteLine("Free-tier cloud models:");
        Console.WriteLine(OllamaClient.FormatFreeCloudCatalog());
    }
    return status.Available ? 0 : 2;
}

async Task<int> RunOllamaSuggest(string[] a)
{
    var opts = new MigrationOptions
    {
        DumpPath = defaultDump,
        RulesPath = defaultRules,
        Apply = false,
        Backup = false,
    };
    var paths = new List<string>();
    var ollama = new OllamaOptions();
    string? reportPath = null;
    var applySuggestions = false;

    for (var i = 0; i < a.Length; i++)
    {
        if (IsolatedBootstrap.IsPathFlag(a[i]))
        {
            i = IsolatedBootstrap.ConsumePathArgs(a, i, paths);
            continue;
        }
        switch (a[i])
        {
            case "--mod":
                opts.ModFilter = IsolatedBootstrap.RequireValue(a, ref i, "--mod");
                break;
            case "--include-workshop":
                paths.Add(SteamInstall.WorkshopContentDirOrFallback);
                break;
            case "--model":
                ollama.Model = IsolatedBootstrap.RequireValue(a, ref i, "--model");
                break;
            case "--url":
            case "--base-url":
                ollama.BaseUrl = IsolatedBootstrap.RequireValue(a, ref i, a[i]);
                break;
            case "--max":
                ollama.MaxHits = int.Parse(IsolatedBootstrap.RequireValue(a, ref i, "--max"));
                break;
            case "--timeout":
                ollama.TimeoutMs = int.Parse(IsolatedBootstrap.RequireValue(a, ref i, "--timeout"));
                break;
            case "--no-json-format":
                ollama.JsonFormat = false;
                break;
            case "--cloud":
                ollama.UseCloud = true;
                break;
            case "--api-key":
                ollama.ApiKey = IsolatedBootstrap.RequireValue(a, ref i, "--api-key");
                break;
            case "--report":
                reportPath = IsolatedBootstrap.RequireValue(a, ref i, "--report");
                break;
            case "--apply":
                applySuggestions = true;
                break;
            default:
                IsolatedBootstrap.RejectUnknown(a[i]);
                break;
        }
    }

    if (ollama.UseCloud || OllamaClient.IsCloudHost(ollama.BaseUrl))
        ollama.UseCloud = true;

    DumpVersionControl.EnsureActiveProfile(dataDir, defaultManaged, Console.WriteLine);
    opts.Paths = paths.Count > 0 ? paths : new List<string> { modsRoot };
    Console.WriteLine("Dry-run migrate (for leftover hits)...");
    var report = MigrationRunner.Run(opts, Console.WriteLine);
    var suggestions = await OllamaLeftoverSuggester.SuggestAsync(report, ollama, Console.WriteLine);
    reportPath ??= Path.Combine(toolsRoot, "reports", $"ollama-suggest_{DateTime.Now:yyyyMMdd_HHmmss}.md");
    Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
    File.WriteAllText(reportPath, OllamaLeftoverSuggester.ToMarkdown(suggestions));
    Console.WriteLine($"Suggestions: {suggestions.Count} (skipped {suggestions.Count(s => s.Skip)})");
    Console.WriteLine("Report: " + reportPath);

    if (applySuggestions)
    {
        var applied = 0;
        foreach (var s in suggestions)
        {
            if (s.Skip) continue;
            if (OllamaLeftoverSuggester.TryApply(s, out var err))
            {
                applied++;
                Console.WriteLine("Applied " + s.FilePath + ":" + s.Line);
            }
            else
                Console.WriteLine("Skip apply " + s.FilePath + ":" + s.Line + " — " + err);
        }
        Console.WriteLine("Applied " + applied + " unique-line replacement(s).");
    }

    return 0;
}

static void PrintUsage()
{
    Console.WriteLine("""
        ApiMigrator.Cli - Caves of Qud obsolete-API migration tool

        Usage:
          ApiMigrator.Cli migrate [--path <dir> [<dir>...]] [--mod <name>] [--apply] [--no-backup]
                                   [--report <file>] [--dump <file>] [--rules <file>]
                                   [--include-workshop]
              Scans for obsolete API usage and applies curated auto-fixes.
              Dry-run by default; pass --apply to write changes (with .bak backups).
              Never writes under game StreamingAssets / Managed — mods and Workshop only.
              Repeat or space-separate --path values (one --path may list several dirs).

          ApiMigrator.Cli refresh-dump [--managed <dir>] [--dll <name>]... [--dump <file>] [--save]
                                       [--no-version-sync]
              Reflects Assembly-CSharp.dll (and any extra --dll) in the Managed folder for
              [Obsolete] members, diffs against the current dump, and (with --save) writes
              the refreshed dump - after backing up the old one. Also updates
              data/by-version/{{FileVersion}}/ (dump + curated rules). Read-only against Managed.

          ApiMigrator.Cli sync-version [--managed <dir>] [--save-profile]
              Sync active obsolete_api_dump.json + curated_rewrite_rules.json to the profile
              matching live Managed FileVersion / Steam BetaKey (honors a switch-api pin).
              --save-profile writes/updates data/by-version/{{version}}/ from the current active files.

          ApiMigrator.Cli switch-api [public|lang|live|<FileVersion>] [--list] [--managed <dir>]
              Pin the active dump+rules to a by-version profile so migrate/GUI/PS1 keep using
              it even if Steam is on another branch. live/auto clears the pin.
              No argument or --list prints status + available profiles.
              Aliases: public/stable → public profile; lang/beta/lang-experimental → lang beta.

          ApiMigrator.Cli export-charts [--rules <file>] [--charts <dir>] [--force]
              Split curated_rewrite_rules.json into human-editable XML packs under data/charts/
              (plus manifest.json). --force overwrites an existing charts folder.

          ApiMigrator.Cli compile-rules [--charts <dir>] [--out <file>] [--check] [--managed <dir>]
                                       [--no-profile]
              Compile data/charts/*.xml|*.json (via manifest.json) into curated_rewrite_rules.json.
              --check: validate + exit 2 if compiled output differs (no write).

          ApiMigrator.Cli export-promotions [--dump <file>] [--promotions <dir>] [--no-merge]
                                            [--include-autofixable]
              Export needsManual dump entries to data/charts/promotions/*.xml sheets.
              Re-export merges prior Status / ProposedRule by DumpMember.

          ApiMigrator.Cli apply-promotions [--promotions <dir>] [--dump <file>] [--charts <dir>]
                                           [--dry-run] [--no-compile] [--managed <dir>]
              Apply Status=Promote entries (ProposedRule Pattern/Replacement) → charts/Promoted.xml,
              flip dump autoFixable, then compile-rules.

          ApiMigrator.Cli resolve-cs0618 --mod <folder> [--compile|--no-compile] [--from-log <file>]
                                         [--apply] [--no-backup] [--managed <dir>] [--report <file>]
                                         [--no-version-sync]
              Harvests CS0618 obsolete warnings WITHOUT launching the game: optionally compiles
              the mod against Managed (seconds), and/or parses a pasted compiler/MODWARN log.
              Then runs curated auto-fixes on affected files and reports remaining manual hits.

          ApiMigrator.Cli convert-cp437 [--path <dir> [<dir>...]]... [--mod <name>] [--apply] [--no-backup]
                                        [--report <file>] [--include-workshop]
                                        [--convert-ambiguous] [--force-xml-utf8] [--no-xml-encoding]
              Converts legacy CP437 code points in .cs / .xml to UTF-16 glyphs (ConsoleLib.Console.CP437).
              Also sets Encoding="utf-8" on mod XML roots (unless --no-xml-encoding).
              Never writes under game StreamingAssets / Managed.
              Named escapes \\t/\\a/\\b/\\v/\\f are flagged for review unless --convert-ambiguous.

          ApiMigrator.Cli ollama-probe [--url <http://localhost:11434>] [--cloud]
                                       [--api-key <key>]
              GET /api/tags. Default is local Ollama. --cloud uses https://ollama.com
              (Authorization: Bearer from --api-key or OLLAMA_API_KEY).
              Local *-cloud models: ollama signin / ollama pull gpt-oss:120b-cloud (no --cloud).

          ApiMigrator.Cli ollama-suggest [--path <dir> [<dir>...]]... [--mod <name>] [--include-workshop]
                                         [--model <name>] [--url <http://localhost:11434>]
                                         [--cloud] [--api-key <key>]
                                         [--max <n>] [--timeout <ms>] [--no-json-format]
                                         [--report <file>] [--apply]
              Dry-run migrate, then ask Ollama for replacements of leftover DidX / GameText hits.
              --cloud talks to ollama.com (free-tier default gpt-oss:20b for leftover batches;
              gpt-oss:120b quality; gemma4:31b multimodal; nemotron-3-nano/super/ultra 1M agentic)
              with OLLAMA_API_KEY.
              Local proxy still works for pulled *-cloud tags on localhost after ollama signin.
              Resolves llama3.1 vs llama3.1:latest from /api/tags; retries without format=json
              when the model rejects JSON mode; falls back to /api/generate if /api/chat is missing.
              Writes a report by default. The model must emit C# replacements (not advice).
              --apply writes unique original-line hits (still skip [Obsolete] / empty / advisory).
        """);
}
}
