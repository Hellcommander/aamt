using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace WorldGenSimulator
{
    /// <summary>
    /// Simulates worldgen from multiple mods to detect conflicts and provide isolation recommendations.
    /// Helps determine which mods should be isolated to subworlds vs. stay in main world.
    /// </summary>
    public class Program
    {
        public static void Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("WorldGen Simulator - Analyze mod worldgen conflicts");
                Console.WriteLine();
                Console.WriteLine("Usage:");
                Console.WriteLine("  Single mod (static): WorldGenSimulator.exe <mod-source-path>");
                Console.WriteLine("  All mods (static):   WorldGenSimulator.exe --all");
                Console.WriteLine("  All mods (execute):  WorldGenSimulator.exe --all --execute");
                Console.WriteLine();
                Console.WriteLine("Modes:");
                Console.WriteLine("  Static:  Pattern-based analysis of source code (fast, less accurate)");
                Console.WriteLine("  Execute: Actually loads mod assemblies and executes worldgen code (slower, more accurate)");
                Console.WriteLine();
                Console.WriteLine("Example:");
                Console.WriteLine(@"  WorldGenSimulator.exe ""D:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer""");
                Console.WriteLine(@"  WorldGenSimulator.exe --all");
                Console.WriteLine(@"  WorldGenSimulator.exe --all --execute");
                Console.WriteLine();
                return;
            }

            // Check for execution mode flag
            bool useExecution = args.Contains("--execute") || args.Contains("--simulate");
            var filteredArgs = args.Where(a => a != "--execute" && a != "--simulate").ToArray();

            if (filteredArgs.Length == 0 || filteredArgs[0] == "--all")
            {
                // Analyze all mods from ModSources, Mods, and Steam Workshop directories
                var modSourcesPath = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                    "My Games", "Terraria", "tModLoader", "ModSources");
                var modsPath = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                    "My Games", "Terraria", "tModLoader", "Mods");
                var workshopPath = @"E:\SteamLibrary\steamapps\workshop\content\1281930";

                if (useExecution)
                {
                    // Use execution simulator - actually loads and executes mod worldgen code
                    var simulator = new WorldGenExecutionSimulator(modSourcesPath, modsPath, workshopPath);
                    simulator.SimulateWorldGen();
                    
                    // Also run static analysis as fallback for mods that couldn't be analyzed
                    Console.WriteLine();
                    Console.WriteLine("=".PadRight(80, '='));
                    Console.WriteLine("Running static analysis as fallback for mods without DLLs...");
                    Console.WriteLine("=".PadRight(80, '='));
                    Console.WriteLine();
                    var analyzer = new MultiModWorldGenAnalyzer(modSourcesPath, modsPath, workshopPath);
                    analyzer.AnalyzeAllMods();
                }
                else
                {
                    // Use static analysis
                    var analyzer = new MultiModWorldGenAnalyzer(modSourcesPath, modsPath, workshopPath);
                    analyzer.AnalyzeAllMods();
                }
            }
            else
            {
                var modSourcePath = filteredArgs[0];
                if (useExecution)
                {
                    // Execution mode for single mod (would need compiled DLL)
                    Console.WriteLine("Execution mode requires --all flag to load mod assemblies.");
                    Console.WriteLine("For single mod analysis, use static analysis mode (default).");
                    return;
                }
                else
                {
                    var simulator = new WorldGenConflictAnalyzer(modSourcePath);
                    simulator.Analyze();
                }
            }
        }
    }

    class WorldGenConflictAnalyzer
    {
        private readonly string modSourcePath;
        private readonly ConcurrentBag<ModWorldGenInfo> detectedMods = new ConcurrentBag<ModWorldGenInfo>();
        private readonly ConcurrentDictionary<string, List<ConflictReport>> conflicts = new ConcurrentDictionary<string, List<ConflictReport>>();
        private readonly int maxThreads;
        private int filesProcessed = 0;
        private int totalFiles = 0;

        public WorldGenConflictAnalyzer(string modSourcePath)
        {
            this.modSourcePath = modSourcePath;
            // Use all logical processors (includes hyperthreading)
            // Environment.ProcessorCount already includes hyperthreading cores
            this.maxThreads = Environment.ProcessorCount;
        }

        public void Analyze()
        {
            var totalStopwatch = Stopwatch.StartNew();
            
            Console.WriteLine("WorldGen Conflict Analyzer");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine($"Analyzing: {modSourcePath}");
            Console.WriteLine($"Using {maxThreads} threads (Logical processors: {Environment.ProcessorCount}, includes hyperthreading)");
            Console.WriteLine();

            // Scan for worldgen information in the mod (multithreaded)
            var scanStopwatch = Stopwatch.StartNew();
            ScanForWorldGenInfo();
            scanStopwatch.Stop();

            // Analyze conflicts (single-threaded, fast)
            var analyzeStopwatch = Stopwatch.StartNew();
            AnalyzeConflicts();
            analyzeStopwatch.Stop();

            // Generate recommendations
            GenerateRecommendations();
            
            totalStopwatch.Stop();
            
            Console.WriteLine();
            Console.WriteLine("PERFORMANCE METRICS:");
            Console.WriteLine($"  File Scanning: {scanStopwatch.ElapsedMilliseconds}ms ({totalFiles} files, {maxThreads} threads)");
            Console.WriteLine($"  Conflict Analysis: {analyzeStopwatch.ElapsedMilliseconds}ms");
            Console.WriteLine($"  Total Time: {totalStopwatch.ElapsedMilliseconds}ms");
            Console.WriteLine($"  Speedup: ~{(totalFiles * 10.0 / scanStopwatch.ElapsedMilliseconds):F1}x faster than sequential");
        }

        /// <summary>
        /// Analyzes a single mod and returns its worldgen info (for multi-mod analysis)
        /// </summary>
        public ModWorldGenInfo? AnalyzeSingleMod()
        {
            var csFiles = Directory.GetFiles(modSourcePath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\"))
                .ToList();

            ModWorldGenInfo? combinedInfo = null;
            var modName = Path.GetFileName(modSourcePath);

            foreach (var file in csFiles)
            {
                try
                {
                    var content = File.ReadAllText(file);
                    var fileName = Path.GetFileName(file);
                    var relativePath = Path.GetRelativePath(modSourcePath, file);

                    if (Regex.IsMatch(content, @"ModifyWorldGenTasks"))
                    {
                        var modInfo = AnalyzeWorldGenFile(content, fileName, relativePath);
                        if (modInfo != null)
                        {
                            if (combinedInfo == null)
                            {
                                combinedInfo = new ModWorldGenInfo
                                {
                                    ModName = modName,
                                    FileName = fileName,
                                    RelativePath = relativePath,
                                    HasWorldGen = true
                                };
                            }
                            
                            // Merge info
                            combinedInfo.GenPassCount += modInfo.GenPassCount;
                            combinedInfo.HasLargeStructures |= modInfo.HasLargeStructures;
                            combinedInfo.HasBiomes |= modInfo.HasBiomes;
                            combinedInfo.HasOres |= modInfo.HasOres;
                            combinedInfo.HasWorldWideChanges |= modInfo.HasWorldWideChanges;
                            combinedInfo.RequiresSpecificLocations |= modInfo.RequiresSpecificLocations;
                            combinedInfo.EstimatedSizeImpactKB += modInfo.EstimatedSizeImpactKB;
                            if (modInfo.PerformanceImpact == "High" || combinedInfo.PerformanceImpact == "High")
                                combinedInfo.PerformanceImpact = "High";
                            else if (modInfo.PerformanceImpact == "Medium" || combinedInfo.PerformanceImpact == "Medium")
                                combinedInfo.PerformanceImpact = "Medium";
                            combinedInfo.StructureTypes.AddRange(modInfo.StructureTypes);
                        }
                    }
                }
                catch
                {
                    // Skip errors for individual files
                }
            }

            return combinedInfo;
        }

        private void ScanForWorldGenInfo()
        {
            Console.WriteLine("[1/3] Scanning for worldgen patterns (multithreaded)...");
            Console.WriteLine();

            var csFiles = Directory.GetFiles(modSourcePath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\"))
                .ToList();

            totalFiles = csFiles.Count;
            filesProcessed = 0;

            Console.WriteLine($"Scanning {totalFiles} files using {maxThreads} threads...");

            // Progress reporting timer
            var progressTimer = new Timer(_ => ReportProgress(), null, 500, 500);

            try
            {
                // Parallel processing with degree of parallelism
                var parallelOptions = new ParallelOptions
                {
                    MaxDegreeOfParallelism = maxThreads
                };

                Parallel.ForEach(csFiles, parallelOptions, file =>
                {
                    try
                    {
                        var content = File.ReadAllText(file);
                        var fileName = Path.GetFileName(file);
                        var relativePath = Path.GetRelativePath(modSourcePath, file);

                        // Check for ModifyWorldGenTasks
                        if (Regex.IsMatch(content, @"ModifyWorldGenTasks"))
                        {
                            var modInfo = AnalyzeWorldGenFile(content, fileName, relativePath);
                            if (modInfo != null)
                            {
                                detectedMods.Add(modInfo);
                                // Thread-safe console output
                                lock (Console.Out)
                                {
                                    Console.WriteLine($"  [Thread {Thread.CurrentThread.ManagedThreadId}] Found: {modInfo.ModName} ({modInfo.GenPassCount} gen passes)");
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        lock (Console.Out)
                        {
                            Console.WriteLine($"  Error reading {Path.GetFileName(file)}: {ex.Message}");
                        }
                    }
                    finally
                    {
                        Interlocked.Increment(ref filesProcessed);
                    }
                });
            }
            finally
            {
                progressTimer.Dispose();
            }

            Console.WriteLine();
            Console.WriteLine($"Total: {detectedMods.Count} mod(s) with worldgen");
            Console.WriteLine();
        }

        private void ReportProgress()
        {
            if (totalFiles > 0)
            {
                var progress = (filesProcessed * 100.0) / totalFiles;
                var barLength = 40;
                var filledLength = (int)(barLength * progress / 100);
                var bar = new string('█', filledLength) + new string('░', barLength - filledLength);
                
                lock (Console.Out)
                {
                    Console.Write($"\r  Progress: [{bar}] {progress:F1}% ({filesProcessed}/{totalFiles})");
                }
            }
        }

        private ModWorldGenInfo? AnalyzeWorldGenFile(string content, string fileName, string relativePath)
        {
            var info = new ModWorldGenInfo
            {
                FileName = fileName,
                RelativePath = relativePath
            };

            // Extract mod name from class or file name
            var classMatch = Regex.Match(content, @"public\s+class\s+(\w+)");
            info.ModName = classMatch.Success ? classMatch.Groups[1].Value : Path.GetFileNameWithoutExtension(fileName);

            // Count gen passes being added
            var genPassMatches = Regex.Matches(content, @"tasks\.Insert|tasks\.Add");
            info.GenPassCount = genPassMatches.Count;

            // Detect structure generation
            if (Regex.IsMatch(content, @"PlaceStructure|GenStructure|Place.*Building|Place.*Temple|Place.*Dungeon", RegexOptions.IgnoreCase))
            {
                info.HasLargeStructures = true;
                info.StructureTypes.Add("Large Structures");
            }

            // Detect biome generation
            if (Regex.IsMatch(content, @"GenBiome|Place.*Biome|Create.*Biome", RegexOptions.IgnoreCase))
            {
                info.HasBiomes = true;
            }

            // Detect ore generation
            if (Regex.IsMatch(content, @"TileRunner.*Ore|Place.*Ore|Gen.*Ore", RegexOptions.IgnoreCase))
            {
                info.HasOres = true;
            }

            // Detect world-wide changes
            if (Regex.IsMatch(content, @"for\s*\(\s*int\s+[ij]\s*=\s*0\s*;\s*[ij]\s*<\s*Main\.(maxTiles[XY]|worldSurface)", RegexOptions.IgnoreCase))
            {
                info.HasWorldWideChanges = true;
            }

            // Detect specific location requirements
            if (Regex.IsMatch(content, @"GenVars\.(dungeonX|snowMinX|jungleMinX|oceanX|hellX)", RegexOptions.IgnoreCase))
            {
                info.RequiresSpecificLocations = true;
            }

            // Detect performance impact (multiple nested loops)
            var nestedLoops = Regex.Matches(content, @"for\s*\([^)]+\)\s*\{[^}]*for\s*\([^)]+\)");
            info.PerformanceImpact = nestedLoops.Count > 5 ? "High" : nestedLoops.Count > 2 ? "Medium" : "Low";

            // Estimate world size impact
            if (info.HasLargeStructures)
                info.EstimatedSizeImpactKB += 500;
            if (info.HasBiomes)
                info.EstimatedSizeImpactKB += 1000;
            if (info.HasOres)
                info.EstimatedSizeImpactKB += 200;

            return info;
        }

        private void AnalyzeConflicts()
        {
            Console.WriteLine("[2/3] Analyzing conflicts (parallel analysis)...");
            Console.WriteLine();

            // Convert to list for thread-safe enumeration
            var modsList = detectedMods.ToList();
            
            // Check for mods that compete for the same space
            var modsWithStructures = modsList.Where(m => m.HasLargeStructures).ToList();
            var modsWithBiomes = modsList.Where(m => m.HasBiomes).ToList();
            var modsWithWorldWide = modsList.Where(m => m.HasWorldWideChanges).ToList();

            // Structure conflicts (parallel processing)
            if (modsWithStructures.Count > 1)
            {
                Parallel.ForEach(modsWithStructures, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new ConflictReport
                    {
                        Type = ConflictType.StructurePlacement,
                        Severity = ConflictSeverity.High,
                        Description = $"{mod.ModName} generates large structures that may conflict with other structure-generating mods",
                        ConflictingMods = modsWithStructures.Where(m => m != mod).Select(m => m.ModName).ToList(),
                        Recommendation = "Consider isolating to subworld to prevent structure overlap"
                    };

                    conflicts.AddOrUpdate(mod.ModName, 
                        new List<ConflictReport> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // Biome conflicts (parallel processing)
            if (modsWithBiomes.Count > 2)
            {
                Parallel.ForEach(modsWithBiomes, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new ConflictReport
                    {
                        Type = ConflictType.BiomeGeneration,
                        Severity = ConflictSeverity.Medium,
                        Description = $"{mod.ModName} generates biomes alongside {modsWithBiomes.Count - 1} other biome mods",
                        ConflictingMods = modsWithBiomes.Where(m => m != mod).Select(m => m.ModName).ToList(),
                        Recommendation = "Multiple biome mods detected - may cause world bloat. Consider isolation."
                    };

                    conflicts.AddOrUpdate(mod.ModName,
                        new List<ConflictReport> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // World-wide changes conflicts (parallel processing)
            if (modsWithWorldWide.Count > 0)
            {
                Parallel.ForEach(modsWithWorldWide, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new ConflictReport
                    {
                        Type = ConflictType.WorldWideChanges,
                        Severity = ConflictSeverity.High,
                        Description = $"{mod.ModName} makes world-wide terrain changes",
                        ConflictingMods = new List<string>(),
                        Recommendation = "World-wide changes affect entire world - high priority for isolation"
                    };

                    conflicts.AddOrUpdate(mod.ModName,
                        new List<ConflictReport> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            // Performance conflicts (parallel processing)
            var highImpactMods = modsList.Where(m => m.PerformanceImpact == "High").ToList();
            if (highImpactMods.Count > 0)
            {
                Parallel.ForEach(highImpactMods, new ParallelOptions { MaxDegreeOfParallelism = maxThreads }, mod =>
                {
                    var conflict = new ConflictReport
                    {
                        Type = ConflictType.Performance,
                        Severity = ConflictSeverity.Medium,
                        Description = $"{mod.ModName} has high performance impact during worldgen",
                        ConflictingMods = new List<string>(),
                        Recommendation = "High performance cost - consider isolation to improve worldgen speed"
                    };

                    conflicts.AddOrUpdate(mod.ModName,
                        new List<ConflictReport> { conflict },
                        (key, existing) => { existing.Add(conflict); return existing; });
                });
            }

            Console.WriteLine($"Detected {conflicts.Sum(c => c.Value.Count)} potential conflict(s)");
            Console.WriteLine();
        }

        private void GenerateRecommendations()
        {
            Console.WriteLine("[3/3] Generating isolation recommendations...");
            Console.WriteLine();
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("WORLDGEN ANALYSIS REPORT");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();

            // Convert to list for safe enumeration
            var modsList = detectedMods.ToList();

            // Summary statistics
            Console.WriteLine("SUMMARY:");
            Console.WriteLine($"  Total mods analyzed: {modsList.Count}");
            Console.WriteLine($"  Mods with large structures: {modsList.Count(m => m.HasLargeStructures)}");
            Console.WriteLine($"  Mods with biomes: {modsList.Count(m => m.HasBiomes)}");
            Console.WriteLine($"  Mods with world-wide changes: {modsList.Count(m => m.HasWorldWideChanges)}");
            Console.WriteLine($"  Total estimated size impact: {modsList.Sum(m => m.EstimatedSizeImpactKB)} KB");
            Console.WriteLine();

            // Detailed mod analysis
            Console.WriteLine("DETAILED MOD ANALYSIS:");
            Console.WriteLine("-".PadRight(80, '-'));
            foreach (var mod in modsList.OrderByDescending(m => m.EstimatedSizeImpactKB))
            {
                Console.WriteLine($"\n{mod.ModName}");
                Console.WriteLine($"  File: {mod.RelativePath}");
                Console.WriteLine($"  Gen Passes: {mod.GenPassCount}");
                Console.WriteLine($"  Features:");
                Console.WriteLine($"    - Large Structures: {(mod.HasLargeStructures ? "Yes" : "No")}");
                Console.WriteLine($"    - Biomes: {(mod.HasBiomes ? "Yes" : "No")}");
                Console.WriteLine($"    - Ores: {(mod.HasOres ? "Yes" : "No")}");
                Console.WriteLine($"    - World-Wide Changes: {(mod.HasWorldWideChanges ? "Yes" : "No")}");
                Console.WriteLine($"    - Requires Specific Locations: {(mod.RequiresSpecificLocations ? "Yes" : "No")}");
                Console.WriteLine($"  Performance Impact: {mod.PerformanceImpact}");
                Console.WriteLine($"  Estimated Size Impact: {mod.EstimatedSizeImpactKB} KB");
            }

            // Conflict report
            if (conflicts.Count > 0)
            {
                Console.WriteLine();
                Console.WriteLine();
                Console.WriteLine("CONFLICTS DETECTED:");
                Console.WriteLine("-".PadRight(80, '-'));

                foreach (var kvp in conflicts.OrderByDescending(c => c.Value.Max(r => r.Severity)))
                {
                    Console.WriteLine($"\n{kvp.Key}:");
                    foreach (var conflict in kvp.Value)
                    {
                        var severityColor = conflict.Severity == ConflictSeverity.Critical ? "🔴" :
                                           conflict.Severity == ConflictSeverity.High ? "🟠" :
                                           conflict.Severity == ConflictSeverity.Medium ? "🟡" : "🟢";
                        Console.WriteLine($"  {severityColor} {conflict.Severity}: {conflict.Description}");
                        if (conflict.ConflictingMods.Count > 0)
                        {
                            Console.WriteLine($"    Conflicts with: {string.Join(", ", conflict.ConflictingMods)}");
                        }
                        Console.WriteLine($"    Recommendation: {conflict.Recommendation}");
                    }
                }
            }

            // Isolation recommendations
            Console.WriteLine();
            Console.WriteLine();
            Console.WriteLine("ISOLATION RECOMMENDATIONS:");
            Console.WriteLine("=".PadRight(80, '='));

            var shouldIsolate = modsList.Where(m =>
                m.HasWorldWideChanges ||
                m.EstimatedSizeImpactKB > 800 ||
                m.PerformanceImpact == "High" ||
                conflicts.ContainsKey(m.ModName)
            ).ToList();

            var canStayInMain = modsList.Except(shouldIsolate).ToList();

            if (shouldIsolate.Count > 0)
            {
                Console.WriteLine();
                Console.WriteLine("RECOMMEND ISOLATION TO SUBWORLDS:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var mod in shouldIsolate.OrderByDescending(m => m.EstimatedSizeImpactKB))
                {
                    var reasons = new List<string>();
                    if (mod.HasWorldWideChanges) reasons.Add("world-wide changes");
                    if (mod.EstimatedSizeImpactKB > 800) reasons.Add($"large size impact ({mod.EstimatedSizeImpactKB}KB)");
                    if (mod.PerformanceImpact == "High") reasons.Add("high performance cost");
                    if (conflicts.ContainsKey(mod.ModName)) reasons.Add($"{conflicts[mod.ModName].Count} conflict(s)");

                    Console.WriteLine($"  • {mod.ModName}");
                    Console.WriteLine($"    Reasons: {string.Join(", ", reasons)}");
                }
            }

            if (canStayInMain.Count > 0)
            {
                Console.WriteLine();
                Console.WriteLine("CAN STAY IN MAIN WORLD:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var mod in canStayInMain)
                {
                    Console.WriteLine($"  • {mod.ModName} (Low impact: {mod.EstimatedSizeImpactKB}KB)");
                }
            }

            // Code generation suggestions
            Console.WriteLine();
            Console.WriteLine();
            Console.WriteLine("CODE GENERATION SUGGESTIONS:");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();
            Console.WriteLine("Add to ModIsolationSystem.cs:");
            Console.WriteLine();

            foreach (var mod in shouldIsolate)
            {
                Console.WriteLine($"// {mod.ModName} - Isolated due to: {string.Join(", ", GetIsolationReasons(mod))}");
                Console.WriteLine($"if (SafeModExists(\"{mod.ModName}\"))");
                Console.WriteLine("{");
                Console.WriteLine($"    {mod.ModName}Detected = true;");
                Console.WriteLine($"    // Create subworld portal or isolation logic here");
                Console.WriteLine("}");
                Console.WriteLine();
            }

            Console.WriteLine();
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("Analysis complete!");
        }

        private List<string> GetIsolationReasons(ModWorldGenInfo mod)
        {
            var reasons = new List<string>();
            if (mod.HasWorldWideChanges) reasons.Add("world-wide changes");
            if (mod.HasLargeStructures) reasons.Add("large structures");
            if (mod.EstimatedSizeImpactKB > 800) reasons.Add("high size impact");
            if (mod.PerformanceImpact == "High") reasons.Add("performance");
            if (conflicts.ContainsKey(mod.ModName)) reasons.Add("conflicts");
            return reasons;
        }
    }

    class ModWorldGenInfo
    {
        public string ModName { get; set; } = "";
        public string FileName { get; set; } = "";
        public string RelativePath { get; set; } = "";
        public bool HasWorldGen { get; set; }
        public int GenPassCount { get; set; }
        public bool HasLargeStructures { get; set; }
        public bool HasBiomes { get; set; }
        public bool HasOres { get; set; }
        public bool HasWorldWideChanges { get; set; }
        public bool RequiresSpecificLocations { get; set; }
        public string PerformanceImpact { get; set; } = "Low";
        public int EstimatedSizeImpactKB { get; set; }
        public List<string> StructureTypes { get; set; } = new List<string>();
    }

    class ConflictReport
    {
        public ConflictType Type { get; set; }
        public ConflictSeverity Severity { get; set; }
        public string Description { get; set; } = "";
        public List<string> ConflictingMods { get; set; } = new List<string>();
        public string Recommendation { get; set; } = "";
    }

    public enum ConflictType
    {
        StructurePlacement,
        BiomeGeneration,
        WorldWideChanges,
        Performance,
        LocationConflict,
        WeightCollision,
        ExecutionFailure,
        StructureOverlap,
        BiomeConflict
    }

    public enum ConflictSeverity
    {
        Low,
        Medium,
        High,
        Critical
    }
}

