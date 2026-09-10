namespace ApiMigrator.Core;

public static class MigrationRunner
{
    /// <summary>
    /// Runs a full scan (and, if options.Apply, writes fixes to disk with .bak backups)
    /// across the given options' paths. Progress is reported per-file via onProgress.
    /// </summary>
    public static MigrationReport Run(MigrationOptions options, Action<string>? onLog = null,
        Action<int, int>? onProgress = null)
    {
        var dump = DumpStore.LoadDump(options.DumpPath);
        var rules = DumpStore.LoadRules(options.RulesPath);
        var engine = new RuleEngine(rules, dump);

        onLog?.Invoke($"Loaded {dump.Entries.Count} obsolete-API entries from {options.DumpPath}");
        onLog?.Invoke($"Loaded {rules.Rules.Count} curated auto-fix rules from {options.RulesPath}");

        var files = FileScanner.GetTargetFiles(options.Paths, options.ExcludeDirs, options.Extensions,
            options.ModFilter, msg => onLog?.Invoke("WARNING: " + msg));
        var manifestFiles = ManifestFixer.GetTargetFiles(options.Paths, options.ExcludeDirs,
            options.ModFilter, msg => onLog?.Invoke("WARNING: " + msg));
        onLog?.Invoke($"Found {files.Count} candidate .cs/.xml files to scan.");
        onLog?.Invoke($"Found {manifestFiles.Count} manifest.json/config.json files to scan.");

        ModIdCatalog catalog;
        try
        {
            catalog = ModIdCatalog.Build(ModIdCatalog.DefaultScanRoots(options.Paths));
            onLog?.Invoke($"Mod ID catalog: {catalog.CanonicalIds.Count} live mods (local + workshop aliases).");
        }
        catch (Exception ex)
        {
            onLog?.Invoke("WARNING: mod ID catalog failed (" + ex.Message + "); Dependency remap disabled.");
            catalog = ModIdCatalog.Build(Array.Empty<string>());
        }

        var report = new MigrationReport
        {
            Applied = options.Apply,
            DumpPath = options.DumpPath,
            RulesPath = options.RulesPath,
            ScanRoots = options.Paths.ToList(),
            ModFilter = options.ModFilter,
            FilesScanned = files.Count + manifestFiles.Count,
        };

        // Pre-read + mod-scoped IPart/Mutation/Builder namespace fix (XML ResolveType).
        var originals = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var workingMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var preFixes = new Dictionary<string, List<AppliedFix>>(StringComparer.OrdinalIgnoreCase);

        foreach (var file in files)
        {
            try
            {
                var text = File.ReadAllText(file);
                originals[file] = text;
                workingMap[file] = text;
            }
            catch (Exception ex)
            {
                onLog?.Invoke($"Could not read {file}: {ex.Message}");
            }
        }

        var csByMod = files
            .Where(f => f.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) && workingMap.ContainsKey(f))
            .GroupBy(FileScanner.GetModRoot, StringComparer.OrdinalIgnoreCase);

        // Per-mod enum names for nullable stripper (cross-file enum? preserve).
        var enumsByMod = new Dictionary<string, HashSet<string>>(StringComparer.OrdinalIgnoreCase);
        foreach (var modGroup in csByMod)
        {
            enumsByMod[modGroup.Key] = NullableAnnotationCleaner.CollectEnumNames(
                modGroup.Select(p => workingMap[p]));
        }

        foreach (var modGroup in csByMod)
        {
            var batch = modGroup
                .Select(p => (Path: p, Content: workingMap[p]))
                .ToDictionary(t => t.Path, t => t.Content, StringComparer.OrdinalIgnoreCase);
            var nsResult = BlueprintTypeNamespaceFixer.FixMod(batch);
            foreach (var (path, content) in nsResult.UpdatedContents)
                workingMap[path] = content;
            foreach (var (path, fix) in nsResult.Fixes)
            {
                if (!preFixes.TryGetValue(path, out var list))
                {
                    list = new List<AppliedFix>();
                    preFixes[path] = list;
                }
                list.Add(fix);
            }

            // FriendOrFoe List.Add → HistorySpice.json (may create JSON beside mod root)
            var fofBatch = modGroup
                .Where(p => workingMap.ContainsKey(p))
                .ToDictionary(p => p, p => workingMap[p], StringComparer.OrdinalIgnoreCase);
            var fofResult = FriendOrFoeSpiceFixer.FixMod(modGroup.Key, fofBatch);
            foreach (var err in fofResult.Errors)
                onLog?.Invoke("ERROR: " + err);

            var spiceOk = fofResult.Errors.Count == 0;
            foreach (var (spicePath, spiceContent) in fofResult.SpiceFiles)
            {
                onLog?.Invoke($"FriendOrFoe spice → {spicePath}");
                var wrote = !options.Apply;
                if (options.Apply)
                {
                    try
                    {
                        WriteFileResilient(spicePath, spiceContent);
                        wrote = true;
                    }
                    catch (Exception ex)
                    {
                        spiceOk = false;
                        onLog?.Invoke($"ERROR writing {spicePath}: {ex.Message}");
                    }
                }
                report.FileResults.Add(new FileScanResult
                {
                    FilePath = spicePath,
                    Changed = wrote,
                    AppliedFixes = wrote
                        ? fofResult.Fixes
                            .Where(f => string.Equals(f.File, spicePath, StringComparison.OrdinalIgnoreCase))
                            .Select(f => f.Fix)
                            .ToList()
                        : new List<AppliedFix>(),
                    NewContent = wrote ? spiceContent : null,
                });
            }

            if (spiceOk)
            {
                foreach (var (path, content) in fofResult.UpdatedContents)
                    workingMap[path] = content;
                foreach (var (path, fix) in fofResult.Fixes)
                {
                    if (fofResult.SpiceFiles.ContainsKey(path))
                        continue;
                    if (!preFixes.TryGetValue(path, out var list))
                    {
                        list = new List<AppliedFix>();
                        preFixes[path] = list;
                    }
                    list.Add(fix);
                }
            }

            var csMap = modGroup
                .Where(p => workingMap.ContainsKey(p))
                .ToDictionary(p => p, p => workingMap[p], StringComparer.OrdinalIgnoreCase);
            ApplySidecar(modGroup.Key, csMap, workingMap, preFixes, files, originals, onLog,
                InventoryActionsXmlFixer.FixMod, "InventoryActions.xml");
            csMap = modGroup
                .Where(p => workingMap.ContainsKey(p))
                .ToDictionary(p => p, p => workingMap[p], StringComparer.OrdinalIgnoreCase);
            ApplySidecar(modGroup.Key, csMap, workingMap, preFixes, files, originals, onLog,
                StatisticCtorFixer.FixMod, "Statistics.xml");
            csMap = WithSidecar(modGroup.Key, "Liquids.xml",
                modGroup.Where(p => workingMap.ContainsKey(p))
                    .ToDictionary(p => p, p => workingMap[p], StringComparer.OrdinalIgnoreCase),
                workingMap);
            ApplySidecar(modGroup.Key, csMap, workingMap, preFixes, files, originals, onLog,
                LiquidCsToXmlFixer.FixMod, "Liquids.xml");
            csMap = WithSidecar(modGroup.Key, "Liquids.xml",
                modGroup.Where(p => workingMap.ContainsKey(p))
                    .ToDictionary(p => p, p => workingMap[p], StringComparer.OrdinalIgnoreCase),
                workingMap);
            ApplySidecar(modGroup.Key, csMap, workingMap, preFixes, files, originals, onLog,
                LiquidDrankToPartFixer.FixMod, "Liquids.xml (OnDrink part)");
        }

        if (preFixes.Count > 0)
            onLog?.Invoke($"Mod-scoped pre-fixes in {preFixes.Count} file(s).");

        var total = files.Count + manifestFiles.Count;
        var progress = 0;

        for (var i = 0; i < files.Count; i++)
        {
            var file = files[i];
            progress++;
            onProgress?.Invoke(progress, total);

            if (!originals.TryGetValue(file, out var original))
                continue;

            var working = workingMap[file];
            var appliedFixes = preFixes.TryGetValue(file, out var pf)
                ? new List<AppliedFix>(pf)
                : new List<AppliedFix>();

            if (onProgress is null && onLog is not null && (progress == 1 || progress % 25 == 0 || progress == total))
                onLog($"Scanning {progress}/{total}: {Path.GetFileName(file)}");

            var (afterRules, ruleFixes) = engine.ApplyCuratedRules(
                working,
                file,
                enumsByMod.TryGetValue(FileScanner.GetModRoot(file), out var modEnums) ? modEnums : null);
            working = afterRules;
            appliedFixes.AddRange(ruleFixes);
            foreach (var w in engine.Warnings)
                onLog?.Invoke("WARNING: " + w);

            // Object-blueprint + Encoding XML hygiene (inventoryobject Blueprint=, root utf-8).
            if (file.EndsWith(".xml", StringComparison.OrdinalIgnoreCase))
            {
                var (closed, closeFixes) = XmlUnclosedElementFixer.Fix(working);
                working = closed;
                appliedFixes.AddRange(closeFixes);

                var (invFixed, invFixes) = ObjectBlueprintXmlFixer.Fix(working);
                working = invFixed;
                appliedFixes.AddRange(invFixes);

                var (worldsFixed, worldsFixes) = WorldsXmlFixer.Fix(working);
                working = worldsFixed;
                appliedFixes.AddRange(worldsFixes);

                var (factionsFixed, factionsFixes) = FactionsXmlFixer.Fix(working);
                working = factionsFixed;
                appliedFixes.AddRange(factionsFixes);

                var (popFixed, popFixes) = PopulationXmlFixer.Fix(working);
                working = popFixed;
                appliedFixes.AddRange(popFixes);

                var (liquidFixed, liquidFixes) = LiquidXmlFixer.Fix(working);
                working = liquidFixed;
                appliedFixes.AddRange(liquidFixes);

                var (mutFixed, mutFixes) = MutationsXmlFixer.Fix(working);
                working = mutFixed;
                appliedFixes.AddRange(mutFixes);

                var (namingFixed, namingFixes) = NamingXmlFixer.Fix(working);
                working = namingFixed;
                appliedFixes.AddRange(namingFixes);

                var (genoFixed, genoFixes) = GenotypesXmlFixer.Fix(working);
                working = genoFixed;
                appliedFixes.AddRange(genoFixes);

                var (subFixed, subFixes) = SubtypesXmlFixer.Fix(working);
                working = subFixed;
                appliedFixes.AddRange(subFixes);

                var (encFixed, encFixes) = XmlUtf8EncodingFixer.Ensure(working);
                working = encFixed;
                appliedFixes.AddRange(encFixes);
            }

            var remainingHits = engine.ScanRemainingHits(working, file);
            foreach (var w in engine.Warnings)
                onLog?.Invoke("WARNING: " + w);
            var changed = working != original;

            if (!changed && remainingHits.Count == 0) continue;

            var result = new FileScanResult
            {
                FilePath = file,
                Changed = changed,
                AppliedFixes = appliedFixes,
                RemainingHits = remainingHits,
                NewContent = changed ? working : null,
            };
            report.FileResults.Add(result);

            TryWrite(file, working, changed, options, result, onLog);
        }

        foreach (var file in manifestFiles)
        {
            progress++;
            onProgress?.Invoke(progress, total);

            string original;
            try
            {
                original = File.ReadAllText(file);
            }
            catch (Exception ex)
            {
                onLog?.Invoke($"Could not read {file}: {ex.Message}");
                continue;
            }

            var (working, appliedFixes) = ManifestFixer.Fix(
                original,
                InferDepsForManifest(file, workingMap),
                catalog,
                catalog.CanonicalIdForDirectory(FileScanner.GetModRoot(file)));
            var changed = working != original;
            if (!changed) continue;

            var result = new FileScanResult
            {
                FilePath = file,
                Changed = changed,
                AppliedFixes = appliedFixes,
                NewContent = working,
            };
            report.FileResults.Add(result);
            TryWrite(file, working, changed, options, result, onLog);
        }

        return report;
    }

    static void ApplySidecar(
        string modRoot,
        IReadOnlyDictionary<string, string> csMap,
        Dictionary<string, string> workingMap,
        Dictionary<string, List<AppliedFix>> preFixes,
        List<string> scannedFiles,
        Dictionary<string, string> originals,
        Action<string>? onLog,
        Func<string, IReadOnlyDictionary<string, string>, SidecarModFixResult> fixer,
        string sidecarLabel)
    {
        var result = fixer(modRoot, csMap);
        foreach (var w in result.Warnings)
            onLog?.Invoke("WARNING: " + w);
        foreach (var (path, content) in result.UpdatedContents)
            workingMap[path] = content;
        foreach (var (path, fix) in result.Fixes)
        {
            if (result.SidecarFiles.ContainsKey(path))
                continue;
            if (!preFixes.TryGetValue(path, out var list))
            {
                list = new List<AppliedFix>();
                preFixes[path] = list;
            }
            list.Add(fix);
        }

        var scanned = new HashSet<string>(scannedFiles, StringComparer.OrdinalIgnoreCase);
        foreach (var (sidecarPath, sidecarContent) in result.SidecarFiles)
        {
            workingMap[sidecarPath] = sidecarContent;
            onLog?.Invoke($"{sidecarLabel} → {sidecarPath}");

            if (!originals.ContainsKey(sidecarPath))
            {
                try
                {
                    originals[sidecarPath] = File.Exists(sidecarPath)
                        ? File.ReadAllText(sidecarPath)
                        : "";
                }
                catch (Exception ex)
                {
                    onLog?.Invoke($"WARNING: could not read sidecar {sidecarPath}: {ex.Message}");
                    originals[sidecarPath] = "";
                }
            }
            if (!scanned.Contains(sidecarPath))
            {
                scannedFiles.Add(sidecarPath);
                scanned.Add(sidecarPath);
            }

            if (!preFixes.TryGetValue(sidecarPath, out var list))
            {
                list = new List<AppliedFix>();
                preFixes[sidecarPath] = list;
            }
            foreach (var (path, fix) in result.Fixes)
            {
                if (string.Equals(path, sidecarPath, StringComparison.OrdinalIgnoreCase))
                    list.Add(fix);
            }
        }
    }

    static Dictionary<string, string> WithSidecar(
        string modRoot,
        string fileName,
        Dictionary<string, string> csMap,
        Dictionary<string, string> workingMap)
    {
        var xmlPath = Path.Combine(modRoot, fileName);
        if (workingMap.TryGetValue(xmlPath, out var xml))
            csMap[xmlPath] = xml;
        else if (File.Exists(xmlPath))
        {
            try { csMap[xmlPath] = File.ReadAllText(xmlPath); }
            catch { /* leave sidecar out of this pass */ }
        }
        return csMap;
    }

    static IReadOnlyList<string> InferDepsForManifest(string manifestPath,
        IReadOnlyDictionary<string, string> workingMap)
    {
        var modRoot = FileScanner.GetModRoot(manifestPath);
        string? thisId = null;
        try
        {
            var m = System.Text.RegularExpressions.Regex.Match(
                File.ReadAllText(manifestPath),
                "\"(?:id|ID)\"\\s*:\\s*\"([^\"]+)\"",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            if (m.Success) thisId = m.Groups[1].Value;
        }
        catch { /* still infer from usings */ }

        var sources = new List<string>();
        foreach (var kv in workingMap)
        {
            if (!kv.Key.EndsWith(".cs", StringComparison.OrdinalIgnoreCase)) continue;
            if (!CoqPaths.PathIsUnderRoot(kv.Key, modRoot)) continue;
            sources.Add(kv.Value);
        }

        return ManifestFixer.InferKnownLibraryModIds(sources, thisId);
    }

    static void TryWrite(string file, string working, bool changed, MigrationOptions options,
        FileScanResult result, Action<string>? onLog)
    {
        if (!changed || !options.Apply) return;

        try
        {
            if (options.Backup)
            {
                var bak = file + ".bak";
                if (!File.Exists(bak))
                {
                    try
                    {
                        File.Copy(file, bak);
                    }
                    catch (UnauthorizedAccessException)
                    {
                        // Workshop / ACL quirks: still write the fix; note missing backup.
                        onLog?.Invoke($"WARNING: could not write backup {bak}; applying without .bak");
                    }
                }
            }
            WriteFileResilient(file, working);
        }
        catch (Exception ex)
        {
            onLog?.Invoke($"ERROR writing {file}: {ex.Message}");
            result.Changed = false;
            result.NewContent = null;
        }
    }

    static void WriteFileResilient(string file, string working) =>
        WorkshopWrite.WriteAllText(file, working);
}
