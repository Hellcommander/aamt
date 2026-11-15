namespace ApiMigrator.Core;

/// <summary>
/// Resolves CS0618 obsolete-API warnings without launching the game:
/// harvest warnings (compile against Managed, or parse a pasted/log file), then run the
/// shared curated-rule migrator on the affected files and report what still needs a human.
/// </summary>
public static class Cs0618Resolver
{
    public sealed class Options
    {
        public string? ModFolder { get; set; }
        public string ManagedDir { get; set; } = SteamInstall.ManagedDirOrFallback;
        /// <summary>Optional path to a text file of compiler / MODWARN lines.</summary>
        public string? WarningLogPath { get; set; }
        /// <summary>Optional raw warning text (paste).</summary>
        public string? WarningText { get; set; }
        public bool Compile { get; set; } = true;
        public bool Apply { get; set; }
        public bool Backup { get; set; } = true;
        public string DumpPath { get; set; } = "";
        public string RulesPath { get; set; } = "";
        /// <summary>Refuse a rewrite that unbalances brackets or changes string-literal text (ApplyGuard).</summary>
        public bool TextGuard { get; set; } = true;
        /// <summary>Compile the mod before and after applying; restore its files on new errors (CompileGuard).</summary>
        public bool CompileGuard { get; set; } = true;
    }

    public sealed class Result
    {
        public List<Cs0618Warning> Warnings { get; set; } = new();
        public List<string> AffectedFiles { get; set; } = new();
        public MigrationReport? Migration { get; set; }
        public ModCompiler.CompileResult? Compile { get; set; }
        public List<string> Notes { get; set; } = new();
        public Dictionary<string, int> SymbolCounts { get; set; } = new(StringComparer.Ordinal);
    }

    public static Result Run(Options options, Action<string>? onLog = null)
    {
        var result = new Result();
        var warnings = new List<Cs0618Warning>();

        // --mod may be a bare folder name ("Arendeth_PoisonCrafter"): resolve it under the Mods root so the
        // compile, the path fallback and the scope filter below all work on a real directory.
        var modFolder = ResolveModFolder(options.ModFolder, result.Notes);
        options.ModFolder = modFolder;

        if (!string.IsNullOrWhiteSpace(options.WarningText))
            warnings.AddRange(Cs0618Parser.Parse(options.WarningText));

        if (!string.IsNullOrWhiteSpace(options.WarningLogPath))
        {
            if (!File.Exists(options.WarningLogPath))
                throw new FileNotFoundException("Warning log not found", options.WarningLogPath);
            warnings.AddRange(Cs0618Parser.ParseFile(options.WarningLogPath!));
        }

        if (options.Compile)
        {
            if (string.IsNullOrWhiteSpace(options.ModFolder))
                throw new ArgumentException("ModFolder is required when Compile=true.");
            // Other mods' assemblies too: a mod that depends on another mod otherwise fails to bind, and a
            // file with binding errors reports few or none of its CS0618 warnings.
            var compile = ModCompiler.CompileAgainstManaged(
                options.ModFolder!, options.ManagedDir, onLog, null, CompileGuard.OtherModAssemblies(options.ModFolder!));
            result.Compile = compile;
            result.Notes.AddRange(compile.Notes);
            onLog?.Invoke($"Compile finished (exit {compile.ExitCode}). Parsing CS0618...");
            warnings.AddRange(Cs0618Parser.Parse(compile.Output));
        }

        // Deduplicate
        var dedup = new Dictionary<string, Cs0618Warning>(StringComparer.OrdinalIgnoreCase);
        foreach (var w in warnings)
        {
            var key = $"{NormalizePath(w.FilePath)}|{w.Line}|{w.Column}|{w.ObsoleteSymbol}";
            dedup[key] = w;
        }
        result.Warnings = dedup.Values
            .OrderBy(w => w.FilePath, StringComparer.OrdinalIgnoreCase)
            .ThenBy(w => w.Line)
            .ToList();

        var harvested = result.Warnings.Count;

        // Resolve file paths: prefer real files under ModFolder when the log used truncated paths.
        // A log (build_log.txt, Player.log) usually holds every mod's warnings. When a mod folder was given,
        // only that mod's files are in scope: before this filter, --mod X --from-log <whole log> --apply
        // rewrote every file the log named, in every mod.
        var scopeRoot = modFolder is null
            ? null
            : Path.TrimEndingDirectorySeparator(Path.GetFullPath(modFolder)) + Path.DirectorySeparatorChar;
        var affected = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var inScope = new List<Cs0618Warning>();
        var outOfScope = 0;
        foreach (var w in result.Warnings)
        {
            var resolved = ResolveFilePath(w.FilePath, modFolder);
            if (resolved != null && File.Exists(resolved))
            {
                var full = Path.GetFullPath(resolved);
                if (scopeRoot != null && !full.StartsWith(scopeRoot, StringComparison.OrdinalIgnoreCase))
                {
                    outOfScope++;
                    continue;
                }
                affected.Add(full);
                w.FilePath = full;
                inScope.Add(w);
            }
            else if (scopeRoot != null && !string.IsNullOrWhiteSpace(options.WarningLogPath))
            {
                // With a whole-game log and a mod filter, an unresolvable path is almost always another mod's file.
                outOfScope++;
            }
            else
            {
                inScope.Add(w);
                result.Notes.Add($"Could not resolve file for warning: {w.FilePath}({w.Line}) {w.ObsoleteSymbol}");
            }
        }
        result.Warnings = inScope;

        foreach (var g in result.Warnings.GroupBy(w => ShortSymbol(w.ObsoleteSymbol)))
            result.SymbolCounts[g.Key] = g.Count();

        onLog?.Invoke($"Harvested {harvested} CS0618 warning(s); {result.Warnings.Count} in scope across {affected.Count} file(s)" +
            (outOfScope > 0 ? $", {outOfScope} outside {modFolder} ignored." : "."));
        result.AffectedFiles = affected.OrderBy(f => f, StringComparer.OrdinalIgnoreCase).ToList();

        if (result.AffectedFiles.Count == 0)
        {
            result.Notes.Add("No resolvable source files — skipping migrator apply.");
            return result;
        }

        // Run curated migrator only on affected files' parent folders, then filter results.
        // Simpler: apply RuleEngine per file directly.
        var dump = DumpStore.LoadDump(options.DumpPath);
        var rules = DumpStore.LoadRules(options.RulesPath);
        var engine = new RuleEngine(rules, dump);

        var compileGuard = options.Apply && options.CompileGuard
            ? new CompileGuard(options.ManagedDir, onLog)
            : null;

        var migration = new MigrationReport
        {
            Applied = options.Apply,
            DumpPath = options.DumpPath,
            RulesPath = options.RulesPath,
            ScanRoots = options.ModFolder is null ? new List<string>() : new List<string> { options.ModFolder },
            FilesScanned = result.AffectedFiles.Count,
        };

        foreach (var file in result.AffectedFiles)
        {
            string original;
            try { original = File.ReadAllText(file); }
            catch (Exception ex)
            {
                result.Notes.Add($"Could not read {file}: {ex.Message}");
                continue;
            }

            var fileWarnings = result.Warnings
                .Where(w => string.Equals(NormalizePath(w.FilePath), NormalizePath(file), StringComparison.OrdinalIgnoreCase))
                .ToList();

            // Fixes that need the compiler's overload and position go first, while the reported lines and
            // columns still match the file.
            var (positioned, positionEdits) = Cs0618PositionFixer.Apply(original, fileWarnings);

            var (working, fixes) = engine.ApplyCuratedRules(positioned, file);
            if (positionEdits > 0)
                fixes.Add(new AppliedFix { RuleName = Cs0618PositionFixer.FixRuleName, Count = positionEdits });
            var remaining = engine.ScanRemainingHits(working, file);
            var changed = !string.Equals(working, original, StringComparison.Ordinal);

            var scan = new FileScanResult
            {
                FilePath = file,
                Changed = changed,
                AppliedFixes = fixes,
                RemainingHits = remaining,
                NewContent = changed ? working : null,
            };
            migration.FileResults.Add(scan);

            if (changed && options.Apply)
            {
                // Guards (ApplyGuard.cs): never write a rewrite that drops string text or unbalances
                // brackets, and never write into a mod that can't be compiled first.
                var refusal = options.TextGuard ? ApplyGuard.CheckRewrite(original, working) : new List<string>();
                if (refusal.Count == 0 && compileGuard != null && !compileGuard.BeforeWrite(file, original))
                    refusal.Add("the mod could not be compiled before the change, so the result could not be checked");
                if (refusal.Count > 0)
                {
                    var why = $"GUARD: not writing {file}: {string.Join("; ", refusal)}";
                    result.Notes.Add(why);
                    onLog?.Invoke(why);
                    scan.Changed = false;
                    scan.NewContent = null;
                    scan.AppliedFixes = new List<AppliedFix>();
                    continue;
                }
                try
                {
                    if (options.Backup)
                    {
                        var bak = file + ".bak";
                        if (!File.Exists(bak))
                        {
                            try { File.Copy(file, bak); }
                            catch (UnauthorizedAccessException)
                            {
                                result.Notes.Add($"WARNING: no .bak for {file}");
                            }
                        }
                    }
                    WorkshopWrite.WriteAllText(file, working);
                    onLog?.Invoke($"Wrote {file} ({fixes.Sum(f => f.Count)} auto-fix(es)).");
                }
                catch (Exception ex)
                {
                    result.Notes.Add($"ERROR writing {file}: {ex.Message}");
                    scan.Changed = false;
                    scan.NewContent = null;
                }
            }

            // Annotate unmatched CS0618 symbols (no curated rule hit this file)
            foreach (var w in fileWarnings)
            {
                var stillOnLine = remaining.Any(h => Math.Abs(h.Line - w.Line) <= 1)
                    || (!changed && working.Contains(MemberToken(w.ObsoleteSymbol), StringComparison.Ordinal));
                if (stillOnLine || fixes.Count == 0)
                {
                    // Ensure the warning appears in remaining if dump didn't catch it
                    if (!remaining.Any(h => h.Line == w.Line && h.Member.Contains(MemberToken(w.ObsoleteSymbol), StringComparison.OrdinalIgnoreCase)))
                    {
                        scan.RemainingHits.Add(new RemainingHit
                        {
                            Line = w.Line,
                            Member = w.ObsoleteSymbol,
                            Message = string.IsNullOrEmpty(w.ObsoleteMessage)
                                ? "CS0618 (no replacement message)"
                                : w.ObsoleteMessage,
                            NeedsManual = true,
                            Text = w.Raw,
                        });
                    }
                }
            }
        }

        if (compileGuard != null)
        {
            foreach (var outcome in compileGuard.Finish().Where(o => o.Reverted))
            {
                var restored = new HashSet<string>(outcome.RevertedFiles, StringComparer.OrdinalIgnoreCase);
                foreach (var fileResult in migration.FileResults)
                {
                    if (!restored.Contains(Path.GetFullPath(fileResult.FilePath))) continue;
                    fileResult.Changed = false;
                    fileResult.NewContent = null;
                    fileResult.AppliedFixes = new List<AppliedFix>();
                }
                result.Notes.Add($"GUARD: restored {outcome.RevertedFiles.Count} file(s) in {outcome.ModFolder}: the rewrite added compile error(s): " +
                    string.Join(" | ", outcome.NewErrors.Take(5)));
            }
        }

        result.Migration = migration;
        onLog?.Invoke(
            $"Migrator: {migration.TotalAutoFixes} auto-fix(es), " +
            $"{migration.TotalRemainingHits} remaining hit(s) across {migration.FileResults.Count} file(s). " +
            $"Mode={(options.Apply ? "APPLY" : "DRY-RUN")}.");
        return result;
    }

    private static string ShortSymbol(string symbol)
    {
        // 'GameObject.the' or 'IComponent<GameObject>.DidX(...)' → trim args
        var s = symbol;
        var paren = s.IndexOf('(');
        if (paren > 0) s = s[..paren];
        return s.Trim();
    }

    private static string MemberToken(string symbol)
    {
        var s = ShortSymbol(symbol);
        var dot = s.LastIndexOf('.');
        return dot >= 0 ? s[(dot + 1)..] : s;
    }

    /// <summary>A mod folder given as a path or as a bare folder name under the Mods root; null when not given.</summary>
    private static string? ResolveModFolder(string? modFolder, List<string> notes)
    {
        if (string.IsNullOrWhiteSpace(modFolder)) return null;
        if (Directory.Exists(modFolder)) return Path.GetFullPath(modFolder);
        try
        {
            var underMods = Path.Combine(CoqPaths.ResolveModsRoot(), modFolder);
            if (Directory.Exists(underMods)) return Path.GetFullPath(underMods);
        }
        catch
        {
            // fall through to the note
        }
        notes.Add($"Mod folder not found as a path or under the Mods root: {modFolder}");
        return modFolder;
    }

    private static string NormalizePath(string path) =>
        path.Replace('/', '\\').Trim();

    private static string? ResolveFilePath(string loggedPath, string? modFolder)
    {
        var p = NormalizePath(loggedPath);
        var fromSteam = SteamInstall.ResolveLoggedPath(loggedPath) ?? SteamInstall.ResolveLoggedPath(p);
        if (fromSteam != null && File.Exists(fromSteam)) return fromSteam;
        if (File.Exists(p)) return p;

        // Truncated Player.log style: steamapps/workshop/content/333640/ID/File.cs
        var fileName = Path.GetFileName(p);
        if (string.IsNullOrEmpty(fileName) || string.IsNullOrWhiteSpace(modFolder))
            return null;

        // Cap recursive lookup — browsing/resolving must never walk an entire Workshop tree unboundedly.
        List<string> matches;
        try
        {
            matches = Directory.EnumerateFiles(modFolder, fileName, SearchOption.AllDirectories)
                .Take(64)
                .ToList();
        }
        catch
        {
            return null;
        }

        // A bare file name can only be matched by name; a logged path with folders must also agree on the
        // folder the file sits in. Matching on the name alone handed another mod's warning to any mod that
        // happened to have one file of the same name (Extensions.cs, Utils.cs...).
        var segments = p.Split('\\', StringSplitOptions.RemoveEmptyEntries);
        var tail = Path.DirectorySeparatorChar +
            (segments.Length >= 2 ? segments[^2] + Path.DirectorySeparatorChar + segments[^1] : fileName);
        var agreeing = matches
            .Where(m => m.Replace('/', '\\').EndsWith(tail, StringComparison.OrdinalIgnoreCase))
            .ToList();
        // Ambiguous or no agreement: do not guess.
        return agreeing.Count == 1 ? agreeing[0] : null;
    }
}
