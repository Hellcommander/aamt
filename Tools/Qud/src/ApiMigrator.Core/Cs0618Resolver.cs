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
            var compile = ModCompiler.CompileAgainstManaged(
                options.ModFolder!, options.ManagedDir, onLog);
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

        foreach (var g in result.Warnings.GroupBy(w => ShortSymbol(w.ObsoleteSymbol)))
            result.SymbolCounts[g.Key] = g.Count();

        onLog?.Invoke($"Harvested {result.Warnings.Count} CS0618 warning(s) across {result.Warnings.Select(w => NormalizePath(w.FilePath)).Distinct(StringComparer.OrdinalIgnoreCase).Count()} file path(s).");

        // Resolve file paths: prefer real files under ModFolder when the log used truncated paths.
        var affected = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var w in result.Warnings)
        {
            var resolved = ResolveFilePath(w.FilePath, options.ModFolder);
            if (resolved != null && File.Exists(resolved))
            {
                affected.Add(Path.GetFullPath(resolved));
                w.FilePath = Path.GetFullPath(resolved);
            }
            else
            {
                result.Notes.Add($"Could not resolve file for warning: {w.FilePath}({w.Line}) {w.ObsoleteSymbol}");
            }
        }
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

            var (working, fixes) = engine.ApplyCuratedRules(original, file);
            var remaining = engine.ScanRemainingHits(working, file);
            var changed = !string.Equals(working, original, StringComparison.Ordinal);

            // Keep only remaining hits that correspond to CS0618 lines in this file (approx by line),
            // but also keep all dump hits so the report stays useful.
            var fileWarnings = result.Warnings
                .Where(w => string.Equals(NormalizePath(w.FilePath), NormalizePath(file), StringComparison.OrdinalIgnoreCase))
                .ToList();

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

        if (matches.Count == 1) return matches[0];

        // Prefer path suffix match
        var normLogged = p.TrimStart('\\');
        foreach (var m in matches)
        {
            if (m.EndsWith(fileName, StringComparison.OrdinalIgnoreCase) &&
                (normLogged.EndsWith(fileName, StringComparison.OrdinalIgnoreCase) ||
                 m.Replace('/', '\\').EndsWith(normLogged, StringComparison.OrdinalIgnoreCase)))
                return m;
        }
        // Ambiguous: truncated log path matched multiple files. Do not guess.
        return null;
    }
}
