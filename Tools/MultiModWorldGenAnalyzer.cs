using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace WorldGenSimulator
{
    /// <summary>
    /// Analyzes ALL mods in tModLoader ModSources directory to find cross-mod conflicts
    /// </summary>
    class MultiModWorldGenAnalyzer
    {
        private readonly string modSourcesPath;
        private readonly string modsPath;
        private readonly string workshopPath;
        private readonly int maxThreads;
        private readonly ConcurrentDictionary<string, ModWorldGenInfo> allMods = new ConcurrentDictionary<string, ModWorldGenInfo>();
        private readonly ConcurrentDictionary<string, List<CrossModConflict>> crossModConflicts = new ConcurrentDictionary<string, List<CrossModConflict>>();
        private readonly string tempExtractPath;

        public MultiModWorldGenAnalyzer(string modSourcesPath, string modsPath, string? workshopPath = null)
        {
            this.modSourcesPath = modSourcesPath;
            this.modsPath = modsPath;
            this.workshopPath = workshopPath ?? "";
            this.maxThreads = Environment.ProcessorCount;
            this.tempExtractPath = Path.Combine(Path.GetTempPath(), "WorldGenAnalyzer_Extract_" + Guid.NewGuid().ToString("N")[..8]);
            Directory.CreateDirectory(tempExtractPath);
        }

        public void AnalyzeAllMods()
        {
            var totalStopwatch = Stopwatch.StartNew();

            Console.WriteLine("Multi-Mod WorldGen Conflict Analyzer");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine($"Scanning mods from:");
            Console.WriteLine($"  ModSources: {modSourcesPath}");
            Console.WriteLine($"  Compiled Mods: {modsPath}");
            if (!string.IsNullOrEmpty(workshopPath))
            {
                Console.WriteLine($"  Steam Workshop: {workshopPath}");
            }
            Console.WriteLine($"Using {maxThreads} threads (Logical processors: {Environment.ProcessorCount})");
            Console.WriteLine();

            try
            {
                // Find all mod directories from both sources
                var modDirectories = FindModDirectories();
                Console.WriteLine($"Found {modDirectories.Count} mod(s) to analyze");
                Console.WriteLine();

            if (modDirectories.Count == 0)
            {
                Console.WriteLine("ERROR: No mod directories found!");
                Console.WriteLine($"Expected path: {modSourcesPath}");
                return;
            }

            // Analyze each mod in parallel
            var analyzeStopwatch = Stopwatch.StartNew();
            AnalyzeModsInParallel(modDirectories);
            analyzeStopwatch.Stop();

            // Find cross-mod conflicts
            var conflictStopwatch = Stopwatch.StartNew();
            FindCrossModConflicts();
            conflictStopwatch.Stop();

            // Generate comprehensive report
            GenerateMultiModReport();

            totalStopwatch.Stop();

            Console.WriteLine();
            Console.WriteLine("PERFORMANCE METRICS:");
            Console.WriteLine($"  Mod Analysis: {analyzeStopwatch.ElapsedMilliseconds}ms ({modDirectories.Count} mods, {maxThreads} threads)");
            Console.WriteLine($"  Conflict Detection: {conflictStopwatch.ElapsedMilliseconds}ms");
            Console.WriteLine($"  Total Time: {totalStopwatch.ElapsedMilliseconds}ms");
            Console.WriteLine($"  Average per mod: {(analyzeStopwatch.ElapsedMilliseconds / (double)modDirectories.Count):F1}ms");
            }
            finally
            {
                // Cleanup temp extraction directory
                try
                {
                    if (Directory.Exists(tempExtractPath))
                    {
                        Directory.Delete(tempExtractPath, true);
                    }
                }
                catch
                {
                    // Ignore cleanup errors
                }
            }
        }

        private List<string> FindModDirectories()
        {
            var modDirs = new List<string>();

            // 1. Find mods from ModSources directory (source code)
            if (Directory.Exists(modSourcesPath))
            {
                var sourceDirs = Directory.GetDirectories(modSourcesPath, "*", SearchOption.TopDirectoryOnly)
                    .Where(dir =>
                    {
                        var dirName = Path.GetFileName(dir);
                        // Skip known non-mod directories
                        if (dirName == "ModAssemblies" || dirName == "Mod Libraries" || dirName.StartsWith("."))
                            return false;

                        // Check if it has .cs files (likely a mod)
                        return Directory.GetFiles(dir, "*.cs", SearchOption.AllDirectories).Length > 0;
                    })
                    .ToList();

                modDirs.AddRange(sourceDirs);
                Console.WriteLine($"  Found {sourceDirs.Count} mod(s) in ModSources");
            }

            // 2. Find mods from Mods directory (.tmod files - compiled mods)
            if (Directory.Exists(modsPath))
            {
                var tmodFiles = Directory.GetFiles(modsPath, "*.tmod", SearchOption.TopDirectoryOnly).ToList();
                Console.WriteLine($"  Found {tmodFiles.Count} compiled mod(s) (.tmod files)");

                if (tmodFiles.Count > 0)
                {
                    Console.WriteLine($"  Note: Most .tmod files don't include source code.");
                    Console.WriteLine($"  Only mods with source code in .tmod will be analyzed.");
                }

                // Extract and analyze .tmod files in parallel
                var extractedDirs = new ConcurrentBag<string>();
                var skippedCount = 0;
                Parallel.ForEach(tmodFiles, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, tmodFile =>
                {
                    try
                    {
                        var extractedPath = ExtractTmodFile(tmodFile);
                        if (extractedPath != null && Directory.Exists(extractedPath))
                        {
                            extractedDirs.Add(extractedPath);
                        }
                        else
                        {
                            Interlocked.Increment(ref skippedCount);
                        }
                    }
                    catch (Exception ex)
                    {
                        Interlocked.Increment(ref skippedCount);
                        lock (Console.Out)
                        {
                            Console.WriteLine($"  Warning: Could not extract {Path.GetFileName(tmodFile)}: {ex.Message}");
                        }
                    }
                });

                modDirs.AddRange(extractedDirs);
                Console.WriteLine($"  Extracted with source code: {extractedDirs.Count} mod(s)");
                if (skippedCount > 0)
                {
                    Console.WriteLine($"  Skipped (no source code): {skippedCount} mod(s)");
                }
            }

            // 3. Find mods from Steam Workshop directory
            if (!string.IsNullOrEmpty(workshopPath) && Directory.Exists(workshopPath))
            {
                // Workshop mods are in subdirectories, each containing .tmod files
                var workshopDirs = Directory.GetDirectories(workshopPath, "*", SearchOption.TopDirectoryOnly).ToList();
                var workshopTmodFiles = new List<string>();

                foreach (var workshopDir in workshopDirs)
                {
                    var tmodsInDir = Directory.GetFiles(workshopDir, "*.tmod", SearchOption.AllDirectories);
                    workshopTmodFiles.AddRange(tmodsInDir);
                }

                Console.WriteLine($"  Found {workshopTmodFiles.Count} compiled mod(s) in Steam Workshop");

                if (workshopTmodFiles.Count > 0)
                {
                    // Extract and analyze workshop .tmod files in parallel
                    var extractedDirs = new ConcurrentBag<string>();
                    var skippedCount = 0;
                    Parallel.ForEach(workshopTmodFiles, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, tmodFile =>
                    {
                        try
                        {
                            var extractedPath = ExtractTmodFile(tmodFile);
                            if (extractedPath != null && Directory.Exists(extractedPath))
                            {
                                extractedDirs.Add(extractedPath);
                            }
                            else
                            {
                                Interlocked.Increment(ref skippedCount);
                            }
                        }
                        catch (Exception ex)
                        {
                            Interlocked.Increment(ref skippedCount);
                            lock (Console.Out)
                            {
                                Console.WriteLine($"  Warning: Could not extract {Path.GetFileName(tmodFile)}: {ex.Message}");
                            }
                        }
                    });

                    modDirs.AddRange(extractedDirs);
                    Console.WriteLine($"  Extracted with source code: {extractedDirs.Count} mod(s)");
                    if (skippedCount > 0)
                    {
                        Console.WriteLine($"  Skipped (no source code): {skippedCount} mod(s)");
                    }
                }
            }

            return modDirs;
        }

        private string? ExtractTmodFile(string tmodPath)
        {
            try
            {
                // Use TmodFileReader to properly read .tmod structure
                var tmodInfo = TmodFileReader.ReadTmodFile(tmodPath);
                
                if (tmodInfo.HasSourceFiles && tmodInfo.SourceFiles.Count > 0)
                {
                    // Extract source files to temp directory
                    var modName = tmodInfo.ModName;
                    var extractDir = Path.Combine(tempExtractPath, modName);
                    Directory.CreateDirectory(extractDir);

                    foreach (var sourceFile in tmodInfo.SourceFiles)
                    {
                        var filePath = Path.Combine(extractDir, sourceFile.Path.Replace('/', Path.DirectorySeparatorChar));
                        var fileDir = Path.GetDirectoryName(filePath);
                        if (!string.IsNullOrEmpty(fileDir))
                        {
                            Directory.CreateDirectory(fileDir);
                        }
                        File.WriteAllText(filePath, sourceFile.Content);
                    }

                    return extractDir;
                }

                // Try alternative extraction method
                return TmodFileReader.ExtractSourceFiles(tmodPath, Path.Combine(tempExtractPath, Path.GetFileNameWithoutExtension(tmodPath)));
            }
            catch
            {
                return null;
            }
        }

        private void AnalyzeModsInParallel(List<string> modDirectories)
        {
            Console.WriteLine($"[1/3] Analyzing {modDirectories.Count} mod(s) in parallel...");
            Console.WriteLine();

            int processed = 0;
            var progressTimer = new System.Threading.Timer(_ =>
            {
                var count = processed;
                var progress = (count * 100.0) / modDirectories.Count;
                Console.Write($"\r  Progress: [{new string('█', (int)(progress / 2))}{new string('░', 50 - (int)(progress / 2))}] {progress:F1}% ({count}/{modDirectories.Count})");
            }, null, 500, 500);

            try
            {
                var parallelOptions = new ParallelOptions { MaxDegreeOfParallelism = maxThreads };

                Parallel.ForEach(modDirectories, parallelOptions, modDir =>
                {
                    try
                    {
                        var modName = Path.GetFileName(modDir);
                        var analyzer = new WorldGenConflictAnalyzer(modDir);
                        var modInfo = analyzer.AnalyzeSingleMod();

                        if (modInfo != null && modInfo.HasWorldGen)
                        {
                            allMods.TryAdd(modName, modInfo);
                            lock (Console.Out)
                            {
                                Console.WriteLine($"\r  [Thread {System.Threading.Thread.CurrentThread.ManagedThreadId}] Found: {modName} ({modInfo.GenPassCount} gen passes, {modInfo.EstimatedSizeImpactKB}KB)");
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        lock (Console.Out)
                        {
                            Console.WriteLine($"\r  Error analyzing {Path.GetFileName(modDir)}: {ex.Message}");
                        }
                    }
                    finally
                    {
                        System.Threading.Interlocked.Increment(ref processed);
                    }
                });
            }
            finally
            {
                progressTimer.Dispose();
                Console.WriteLine(); // New line after progress
            }

            Console.WriteLine();
            Console.WriteLine($"Total mods with worldgen: {allMods.Count}");
            Console.WriteLine();
        }

        private void FindCrossModConflicts()
        {
            Console.WriteLine($"[2/3] Detecting cross-mod conflicts...");
            Console.WriteLine();

            var modsList = allMods.Values.ToList();

            // Group by conflict types
            var modsWithStructures = modsList.Where(m => m.HasLargeStructures).ToList();
            var modsWithBiomes = modsList.Where(m => m.HasBiomes).ToList();
            var modsWithWorldWide = modsList.Where(m => m.HasWorldWideChanges).ToList();
            var highImpactMods = modsList.Where(m => m.EstimatedSizeImpactKB > 1000).ToList();

            // Structure conflicts
            if (modsWithStructures.Count > 1)
            {
                Parallel.ForEach(modsWithStructures, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new CrossModConflict
                    {
                        Type = ConflictType.StructurePlacement,
                        Severity = ConflictSeverity.High,
                        ModName = mod.ModName,
                        ConflictingMods = modsWithStructures.Where(m => m.ModName != mod.ModName).Select(m => m.ModName).ToList(),
                        Description = $"Multiple mods ({modsWithStructures.Count}) generate large structures - potential overlap",
                        Recommendation = "Isolate structure-generating mods to separate subworlds"
                    };

                    crossModConflicts.AddOrUpdate(mod.ModName,
                        new List<CrossModConflict> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // Biome conflicts
            if (modsWithBiomes.Count > 2)
            {
                Parallel.ForEach(modsWithBiomes, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new CrossModConflict
                    {
                        Type = ConflictType.BiomeGeneration,
                        Severity = ConflictSeverity.Medium,
                        ModName = mod.ModName,
                        ConflictingMods = modsWithBiomes.Where(m => m.ModName != mod.ModName).Select(m => m.ModName).ToList(),
                        Description = $"{modsWithBiomes.Count} mods generate biomes - world bloat risk",
                        Recommendation = "Consider isolating some biome mods to prevent world size issues"
                    };

                    crossModConflicts.AddOrUpdate(mod.ModName,
                        new List<CrossModConflict> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // World-wide changes conflicts
            if (modsWithWorldWide.Count > 0)
            {
                Parallel.ForEach(modsWithWorldWide, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new CrossModConflict
                    {
                        Type = ConflictType.WorldWideChanges,
                        Severity = ConflictSeverity.Critical,
                        ModName = mod.ModName,
                        ConflictingMods = modsWithWorldWide.Where(m => m.ModName != mod.ModName).Select(m => m.ModName).ToList(),
                        Description = $"World-wide terrain changes conflict with other world-altering mods",
                        Recommendation = "CRITICAL: Isolate world-wide change mods - they affect entire world"
                    };

                    crossModConflicts.AddOrUpdate(mod.ModName,
                        new List<CrossModConflict> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // High impact mods
            if (highImpactMods.Count > 0)
            {
                Parallel.ForEach(highImpactMods, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new CrossModConflict
                    {
                        Type = ConflictType.Performance,
                        Severity = ConflictSeverity.High,
                        ModName = mod.ModName,
                        ConflictingMods = new List<string>(),
                        Description = $"High size impact ({mod.EstimatedSizeImpactKB}KB) - may cause worldgen slowdown",
                        Recommendation = "Consider isolation to improve worldgen performance"
                    };

                    crossModConflicts.AddOrUpdate(mod.ModName,
                        new List<CrossModConflict> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            Console.WriteLine($"Detected {crossModConflicts.Sum(c => c.Value.Count)} cross-mod conflict(s)");
            Console.WriteLine();
        }

        private void GenerateMultiModReport()
        {
            Console.WriteLine("[3/3] Generating comprehensive report...");
            Console.WriteLine();
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("CROSS-MOD WORLDGEN CONFLICT REPORT");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();

            var modsList = allMods.Values.ToList();

            // Summary
            Console.WriteLine("SUMMARY:");
            Console.WriteLine($"  Total mods analyzed: {allMods.Count}");
            Console.WriteLine($"  Mods with large structures: {modsList.Count(m => m.HasLargeStructures)}");
            Console.WriteLine($"  Mods with biomes: {modsList.Count(m => m.HasBiomes)}");
            Console.WriteLine($"  Mods with world-wide changes: {modsList.Count(m => m.HasWorldWideChanges)}");
            Console.WriteLine($"  Total estimated size impact: {modsList.Sum(m => m.EstimatedSizeImpactKB)} KB ({modsList.Sum(m => m.EstimatedSizeImpactKB) / 1024.0:F1} MB)");
            Console.WriteLine();

            // Top conflict mods
            if (crossModConflicts.Count > 0)
            {
                Console.WriteLine("TOP CONFLICT MODS:");
                Console.WriteLine("-".PadRight(80, '-'));
                var topConflicts = crossModConflicts.OrderByDescending(c => c.Value.Count).Take(10);
                foreach (var kvp in topConflicts)
                {
                    Console.WriteLine($"  {kvp.Key}: {kvp.Value.Count} conflict(s)");
                }
                Console.WriteLine();
            }

            // Detailed conflicts
            if (crossModConflicts.Count > 0)
            {
                Console.WriteLine("DETAILED CROSS-MOD CONFLICTS:");
                Console.WriteLine("=".PadRight(80, '='));
                foreach (var kvp in crossModConflicts.OrderByDescending(c => c.Value.Max(r => r.Severity)))
                {
                    Console.WriteLine($"\n{kvp.Key}:");
                    foreach (var conflict in kvp.Value.OrderByDescending(c => c.Severity))
                    {
                        var severityIcon = conflict.Severity == ConflictSeverity.Critical ? "🔴" :
                                          conflict.Severity == ConflictSeverity.High ? "🟠" :
                                          conflict.Severity == ConflictSeverity.Medium ? "🟡" : "🟢";
                        Console.WriteLine($"  {severityIcon} {conflict.Severity}: {conflict.Description}");
                        if (conflict.ConflictingMods.Count > 0)
                        {
                            Console.WriteLine($"    Conflicts with: {string.Join(", ", conflict.ConflictingMods.Take(10))}");
                            if (conflict.ConflictingMods.Count > 10)
                                Console.WriteLine($"    ... and {conflict.ConflictingMods.Count - 10} more");
                        }
                        Console.WriteLine($"    → {conflict.Recommendation}");
                    }
                }
                Console.WriteLine();
            }

            // Isolation recommendations
            Console.WriteLine("ISOLATION RECOMMENDATIONS:");
            Console.WriteLine("=".PadRight(80, '='));
            var shouldIsolate = modsList.Where(m =>
                m.HasWorldWideChanges ||
                m.EstimatedSizeImpactKB > 1000 ||
                m.PerformanceImpact == "High" ||
                crossModConflicts.ContainsKey(m.ModName)
            ).OrderByDescending(m => m.EstimatedSizeImpactKB).ToList();

            if (shouldIsolate.Count > 0)
            {
                Console.WriteLine($"\nRECOMMEND ISOLATION ({shouldIsolate.Count} mods):");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var mod in shouldIsolate)
                {
                    var reasons = new List<string>();
                    if (mod.HasWorldWideChanges) reasons.Add("world-wide changes");
                    if (mod.EstimatedSizeImpactKB > 1000) reasons.Add($"{mod.EstimatedSizeImpactKB}KB impact");
                    if (mod.PerformanceImpact == "High") reasons.Add("high performance cost");
                    if (crossModConflicts.ContainsKey(mod.ModName))
                        reasons.Add($"{crossModConflicts[mod.ModName].Count} conflict(s)");

                    Console.WriteLine($"  • {mod.ModName}");
                    Console.WriteLine($"    Reasons: {string.Join(", ", reasons)}");
                }
            }

            // Mods that can coexist
            var canCoexist = modsList.Except(shouldIsolate).ToList();
            if (canCoexist.Count > 0)
            {
                Console.WriteLine($"\nCAN COEXIST IN MAIN WORLD ({canCoexist.Count} mods):");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var mod in canCoexist.OrderBy(m => m.ModName))
                {
                    Console.WriteLine($"  • {mod.ModName} ({mod.EstimatedSizeImpactKB}KB, {mod.PerformanceImpact} impact)");
                }
            }
        }
    }

    class CrossModConflict
    {
        public ConflictType Type { get; set; }
        public ConflictSeverity Severity { get; set; }
        public string ModName { get; set; } = "";
        public List<string> ConflictingMods { get; set; } = new List<string>();
        public string Description { get; set; } = "";
        public string Recommendation { get; set; } = "";
    }
}

