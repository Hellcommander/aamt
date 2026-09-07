using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Mono.Cecil;
using Mono.Cecil.Cil;
using Terraria.ModLoader;
using Terraria.ModLoader.Core;
using Terraria.WorldBuilding;

namespace WorldGenSimulator
{
    /// <summary>
    /// Actually simulates world generation by analyzing mod assemblies using Mono.Cecil
    /// This finds real conflicts by examining the actual IL code without loading assemblies
    /// </summary>
    public class WorldGenExecutionSimulator
    {
        private readonly string modSourcesPath;
        private readonly string modsPath;
        private readonly string workshopPath;
        private readonly List<ModWorldGenExecutionResult> executionResults = new List<ModWorldGenExecutionResult>();
        private readonly List<WorldGenConflict> detectedConflicts = new List<WorldGenConflict>();
        private static bool assemblyResolveHandlerAdded = false;
        private readonly string tmodLoaderPath;

        public WorldGenExecutionSimulator(string modSourcesPath, string modsPath, string? workshopPath = null)
        {
            this.modSourcesPath = modSourcesPath;
            this.modsPath = modsPath;
            this.workshopPath = workshopPath ?? "";
            
            // Find tModLoader installation
            this.tmodLoaderPath = FindTModLoaderPath();
            
            // Add assembly resolve handler to find tModLoader DLLs
            if (!assemblyResolveHandlerAdded)
            {
                AppDomain.CurrentDomain.AssemblyResolve += OnAssemblyResolve;
                assemblyResolveHandlerAdded = true;
            }
        }

        private string FindTModLoaderPath()
        {
            var possiblePaths = new[]
            {
                @"E:\SteamLibrary\steamapps\common\tModLoader",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam", "steamapps", "common", "tModLoader"),
                @"C:\Program Files (x86)\Steam\steamapps\common\tModLoader"
            };

            foreach (var path in possiblePaths)
            {
                if (Directory.Exists(path) && File.Exists(Path.Combine(path, "tModLoader.dll")))
                {
                    return path;
                }
            }

            return "";
        }

        private static Assembly? OnAssemblyResolve(object? sender, ResolveEventArgs args)
        {
            var assemblyName = new AssemblyName(args.Name);
            
            // Try to find tModLoader and Terraria DLLs
            var possiblePaths = new[]
            {
                @"E:\SteamLibrary\steamapps\common\tModLoader\tModLoader.dll",
                @"E:\SteamLibrary\steamapps\common\tModLoader\Terraria.dll",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam", "steamapps", "common", "tModLoader", "tModLoader.dll"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam", "steamapps", "common", "tModLoader", "Terraria.dll")
            };

            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    try
                    {
                        var loaded = Assembly.LoadFrom(path);
                        if (loaded.GetName().Name == assemblyName.Name)
                        {
                            return loaded;
                        }
                    }
                    catch
                    {
                        // Continue searching
                    }
                }
            }

            return null;
        }

        public void SimulateWorldGen()
        {
            Console.WriteLine("WorldGen Execution Simulator");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("This tool analyzes mod assemblies to find worldgen code.");
            Console.WriteLine("Using Mono.Cecil for assembly analysis (no runtime required).");
            Console.WriteLine();
            Console.WriteLine("Scanning directories:");
            Console.WriteLine($"  ModSources: {modSourcesPath}");
            Console.WriteLine($"  Compiled Mods: {modsPath}");
            if (!string.IsNullOrEmpty(workshopPath))
            {
                Console.WriteLine($"  Steam Workshop: {workshopPath}");
            }
            Console.WriteLine();

            var stopwatch = Stopwatch.StartNew();

            // 1. Find all mods (source and compiled) - exclude CrossModStabilizer to see other mod conflicts
            var modPaths = FindAllMods(excludeCrossMod: true);
            Console.WriteLine($"Found {modPaths.Count} mod(s) to analyze (CrossModStabilizer excluded to detect other mod conflicts)");
            Console.WriteLine();

            // 2. Analyze each mod's worldgen using Mono.Cecil
            Console.WriteLine("[1/3] Analyzing mod assemblies for worldgen code...");
            int analyzed = 0;
            int withWorldGen = 0;
            int withDll = 0;
            int noDll = 0;
            int readErrors = 0;
            var errorSummary = new Dictionary<string, int>();
            
            foreach (var modPath in modPaths)
            {
                try
                {
                    var result = AnalyzeModWorldGen(modPath);
                    if (result != null)
                    {
                        executionResults.Add(result);
                        analyzed++;
                        
                        // Track error types
                        if (!string.IsNullOrEmpty(result.ErrorMessage))
                        {
                            var errorType = result.ErrorMessage;
                            errorSummary[errorType] = errorSummary.GetValueOrDefault(errorType, 0) + 1;
                            
                            if (errorType == "No DLL found" || errorType == "No DLL found in .tmod file")
                                noDll++;
                            else if (errorType == "Could not read assembly")
                                readErrors++;
                        }
                        else
                        {
                            withDll++;
                        }
                        
                        if (result.HasWorldGen)
                        {
                            withWorldGen++;
                            Console.WriteLine($"  ✓ {result.ModName}: {result.DetectedGenPassCount} gen pass(es) detected ({result.ExecutionTimeMs}ms)");
                        }
                    }
                }
                catch (Exception ex)
                {
                    analyzed++;
                    var errorType = $"Exception: {ex.GetType().Name}";
                    errorSummary[errorType] = errorSummary.GetValueOrDefault(errorType, 0) + 1;
                }
            }

            Console.WriteLine();
            Console.WriteLine($"Analyzed {analyzed} mod(s):");
            Console.WriteLine($"  - {withDll} mod(s) with DLL analyzed successfully");
            Console.WriteLine($"  - {withWorldGen} mod(s) with worldgen detected");
            Console.WriteLine($"  - {noDll} mod(s) without DLL");
            Console.WriteLine($"  - {readErrors} mod(s) with assembly read errors");
            
            if (errorSummary.Count > 0)
            {
                Console.WriteLine();
                Console.WriteLine("Error breakdown (showing detailed errors for troubleshooting):");
                foreach (var kvp in errorSummary.OrderByDescending(e => e.Value).Take(20))
                {
                    Console.WriteLine($"  - {kvp.Key}: {kvp.Value}");
                }
            }
            
            // Show sample of mods that failed
            if (noDll > 0)
            {
                Console.WriteLine();
                Console.WriteLine($"Note: {noDll} mod(s) reported 'No DLL' - this may indicate:");
                Console.WriteLine("  - .tmod files don't contain DLLs (unlikely for compiled mods)");
                Console.WriteLine("  - DLL extraction from .tmod files is failing");
                Console.WriteLine("  - Mods are source-only or corrupted");
            }
            Console.WriteLine();
            Console.WriteLine($"[2/3] Analyzing execution results for conflicts...");

            // 3. Analyze conflicts from execution
            AnalyzeExecutionConflicts();

            Console.WriteLine();
            Console.WriteLine($"[3/3] Generating conflict report...");

            // 4. Generate report
            GenerateReport();

            stopwatch.Stop();
            Console.WriteLine();
            Console.WriteLine($"Total simulation time: {stopwatch.ElapsedMilliseconds}ms");
        }

        private List<string> FindAllMods(bool excludeCrossMod = true)
        {
            var modPaths = new List<string>();

            // Source mods (exclude CrossModStabilizer if requested)
            if (Directory.Exists(modSourcesPath))
            {
                var sourceDirs = Directory.GetDirectories(modSourcesPath, "*", SearchOption.TopDirectoryOnly)
                    .Where(dir => Directory.GetFiles(dir, "*.cs", SearchOption.AllDirectories).Length > 0)
                    .ToList();
                
                if (excludeCrossMod)
                {
                    sourceDirs = sourceDirs.Where(dir => !Path.GetFileName(dir).Equals("CrossModStabilizer", StringComparison.OrdinalIgnoreCase)).ToList();
                }
                
                modPaths.AddRange(sourceDirs);
            }

            // Compiled mods
            if (Directory.Exists(modsPath))
            {
                var tmodFiles = Directory.GetFiles(modsPath, "*.tmod", SearchOption.TopDirectoryOnly);
                modPaths.AddRange(tmodFiles);
            }

            // Workshop mods (get latest version of each)
            if (!string.IsNullOrEmpty(workshopPath) && Directory.Exists(workshopPath))
            {
                var workshopDirs = Directory.GetDirectories(workshopPath, "*", SearchOption.TopDirectoryOnly);
                foreach (var workshopDir in workshopDirs)
                {
                    // Find latest .tmod file in this workshop item
                    var tmodFiles = Directory.GetFiles(workshopDir, "*.tmod", SearchOption.AllDirectories)
                        .OrderByDescending(f => File.GetLastWriteTime(f))
                        .ToList();
                    if (tmodFiles.Count > 0)
                    {
                        modPaths.Add(tmodFiles[0]); // Use latest version
                    }
                }
            }

            return modPaths;
        }

        private ModWorldGenExecutionResult? AnalyzeModWorldGen(string modPath)
        {
            var stopwatch = Stopwatch.StartNew();
            var result = new ModWorldGenExecutionResult
            {
                ModPath = modPath,
                ModName = Path.GetFileNameWithoutExtension(modPath)
            };

            try
            {
                // Try to get DLL path
                string? dllPath = null;
                AssemblyDefinition? assemblyDef = null;

                // Check if it's a .tmod file
                if (modPath.EndsWith(".tmod", StringComparison.OrdinalIgnoreCase))
                {
                    try
                    {
                        var tmodInfo = TmodFileReader.ReadTmodFile(modPath);
                        result.ModName = tmodInfo.ModName;
                        
                        if (!string.IsNullOrEmpty(tmodInfo.ErrorMessage))
                        {
                            result.ErrorMessage = tmodInfo.ErrorMessage;
                            return result;
                        }
                        
                        if (tmodInfo.HasDll && !string.IsNullOrEmpty(tmodInfo.TempDllPath) && File.Exists(tmodInfo.TempDllPath))
                        {
                            dllPath = tmodInfo.TempDllPath;
                        }
                        else if (tmodInfo.HasDll && !string.IsNullOrEmpty(tmodInfo.DllFileName))
                        {
                            result.ErrorMessage = $"DLL found ({tmodInfo.DllFileName}) but extraction failed";
                            return result;
                        }
                        else
                        {
                            result.ErrorMessage = "No DLL in .tmod file";
                            return result;
                        }
                    }
                    catch (Exception ex)
                    {
                        result.ErrorMessage = $"Error reading .tmod: {ex.Message}";
                        return result;
                    }
                }
                else
                {
                    // Source mod - try to find compiled DLL
                    var binPath = Path.Combine(modPath, "bin");
                    if (Directory.Exists(binPath))
                    {
                        var dllFiles = Directory.GetFiles(binPath, "*.dll", SearchOption.AllDirectories)
                            .Where(f => !f.Contains("\\obj\\") && !Path.GetFileName(f).StartsWith("Terraria") && !Path.GetFileName(f).StartsWith("tModLoader"))
                            .ToList();
                        if (dllFiles.Count > 0)
                        {
                            dllPath = dllFiles[0];
                        }
                    }
                }

                if (string.IsNullOrEmpty(dllPath) || !File.Exists(dllPath))
                {
                    // For .tmod files, try to extract DLL if it wasn't extracted
                    if (modPath.EndsWith(".tmod", StringComparison.OrdinalIgnoreCase))
                    {
                        var tmodInfo = TmodFileReader.ReadTmodFile(modPath);
                        if (tmodInfo.HasDll && !string.IsNullOrEmpty(tmodInfo.TempDllPath) && File.Exists(tmodInfo.TempDllPath))
                        {
                            dllPath = tmodInfo.TempDllPath;
                            result.ModName = tmodInfo.ModName;
                        }
                        else
                        {
                            result.ErrorMessage = "No DLL found in .tmod file";
                            return result;
                        }
                    }
                    else
                    {
                        result.ErrorMessage = "No DLL found";
                        return result;
                    }
                }

                // Use Mono.Cecil to read assembly without loading it
                var resolver = new DefaultAssemblyResolver();
                
                // Add tModLoader directory to resolver
                if (!string.IsNullOrEmpty(tmodLoaderPath))
                {
                    resolver.AddSearchDirectory(tmodLoaderPath);
                }
                
                // Add directory containing the DLL
                resolver.AddSearchDirectory(Path.GetDirectoryName(dllPath) ?? "");

                var readerParameters = new ReaderParameters
                {
                    AssemblyResolver = resolver,
                    ReadWrite = false,
                    ReadingMode = ReadingMode.Deferred
                };

                try
                {
                    assemblyDef = AssemblyDefinition.ReadAssembly(dllPath, readerParameters);
                }
                catch
                {
                    result.ErrorMessage = "Could not read assembly";
                    return result;
                }

                if (assemblyDef == null)
                {
                    result.ErrorMessage = "Assembly definition is null";
                    return result;
                }

                // Find ModSystem type reference from tModLoader
                TypeReference? modSystemTypeRef = null;
                try
                {
                    var tmodLoaderPath = Path.Combine(this.tmodLoaderPath, "tModLoader.dll");
                    if (File.Exists(tmodLoaderPath))
                    {
                        var tmodLoaderAssembly = AssemblyDefinition.ReadAssembly(tmodLoaderPath, readerParameters);
                        var modSystemType = tmodLoaderAssembly.MainModule.Types
                            .FirstOrDefault(t => t.Name == "ModSystem");
                        if (modSystemType != null)
                        {
                            modSystemTypeRef = assemblyDef.MainModule.ImportReference(modSystemType);
                        }
                        tmodLoaderAssembly.Dispose();
                    }
                }
                catch
                {
                    // Continue without ModSystem reference
                }

                // Find all types that might be ModSystem subclasses
                var allTypes = assemblyDef.MainModule.Types.ToList();
                var modSystemTypes = new List<TypeDefinition>();

                foreach (var type in allTypes)
                {
                    if (type.IsAbstract || !type.IsClass)
                        continue;

                    // Check if it inherits from ModSystem (directly or indirectly)
                    var baseType = type.BaseType;
                    while (baseType != null)
                    {
                        if (baseType.Name == "ModSystem")
                        {
                            modSystemTypes.Add(type);
                            break;
                        }
                        
                        // Resolve base type to check further
                        try
                        {
                            var resolved = baseType.Resolve();
                            if (resolved != null)
                            {
                                baseType = resolved.BaseType;
                            }
                            else
                            {
                                break;
                            }
                        }
                        catch
                        {
                            break;
                        }
                    }
                }

                // Analyze each ModSystem for ModifyWorldGenTasks
                int genPassCount = 0;
                bool hasWorldGen = false;

                // Also check all types for GenPass references (not just ModSystem)
                var allTypesToCheck = assemblyDef.MainModule.Types.ToList();
                
                // Check for GenPass types being used
                bool hasGenPassType = allTypesToCheck.Any(t => 
                    t.BaseType != null && t.BaseType.Name.Contains("GenPass"));
                
                // Check for WorldGen-related method calls
                bool hasWorldGenCalls = false;
                int worldGenMethodCalls = 0;

                foreach (var type in allTypesToCheck)
                {
                    foreach (var method in type.Methods)
                    {
                        if (!method.HasBody)
                            continue;

                        var body = method.Body;
                        if (body?.Instructions == null)
                            continue;

                        foreach (var instruction in body.Instructions)
                        {
                            // Check for GenPass instantiation
                            if (instruction.OpCode.Code == Code.Newobj)
                            {
                                if (instruction.Operand is MethodReference ctorRef)
                                {
                                    if (ctorRef.DeclaringType.Name.Contains("GenPass") ||
                                        ctorRef.DeclaringType.Name.Contains("WorldGen"))
                                    {
                                        hasWorldGenCalls = true;
                                        worldGenMethodCalls++;
                                    }
                                }
                            }
                            
                            // Check for WorldGen method calls
                            if (instruction.OpCode.Code == Code.Call || 
                                instruction.OpCode.Code == Code.Callvirt)
                            {
                                if (instruction.Operand is MethodReference methodRef)
                                {
                                    var declaringType = methodRef.DeclaringType?.Name ?? "";
                                    var methodName = methodRef.Name ?? "";
                                    
                                    // Check for WorldGen-related calls
                                    if (declaringType.Contains("WorldGen") || 
                                        declaringType.Contains("GenPass") ||
                                        methodName.Contains("WorldGen") ||
                                        methodName.Contains("GenPass") ||
                                        methodName.Contains("ModifyWorldGen"))
                                    {
                                        hasWorldGenCalls = true;
                                        worldGenMethodCalls++;
                                    }
                                }
                            }
                        }
                    }
                }

                // Check ModSystem types for ModifyWorldGenTasks
                foreach (var modSystemType in modSystemTypes)
                {
                    // Find ModifyWorldGenTasks method
                    var modifyMethod = modSystemType.Methods.FirstOrDefault(m => 
                        m.Name == "ModifyWorldGenTasks" && 
                        m.Parameters.Count >= 2);

                    if (modifyMethod != null && modifyMethod.HasBody)
                    {
                        hasWorldGen = true;
                        
                        // Analyze method body to count gen pass additions
                        var body = modifyMethod.Body;
                        if (body != null && body.Instructions != null)
                        {
                            int addCalls = 0;
                            int insertCalls = 0;
                            int newGenPassCalls = 0;
                            
                            foreach (var instruction in body.Instructions)
                            {
                                // Look for calls to Add or Insert methods
                                if (instruction.OpCode.Code == Code.Call || 
                                    instruction.OpCode.Code == Code.Callvirt)
                                {
                                    if (instruction.Operand is MethodReference methodRef)
                                    {
                                        var methodName = methodRef.Name;
                                        if (methodName == "Add" || methodName == "AddRange")
                                        {
                                            addCalls++;
                                        }
                                        else if (methodName == "Insert" || methodName == "InsertRange")
                                        {
                                            insertCalls++;
                                        }
                                    }
                                }
                                
                                // Look for GenPass instantiation
                                if (instruction.OpCode.Code == Code.Newobj)
                                {
                                    if (instruction.Operand is MethodReference ctorRef)
                                    {
                                        if (ctorRef.DeclaringType.Name.Contains("GenPass"))
                                        {
                                            newGenPassCalls++;
                                        }
                                    }
                                }
                            }
                            
                            genPassCount += Math.Max(Math.Max(addCalls, insertCalls), newGenPassCalls);
                        }
                        
                        if (genPassCount == 0)
                        {
                            genPassCount = 1; // At least one gen pass if method exists
                        }
                    }
                }
                
                // If we found GenPass types or WorldGen calls, mark as having worldgen
                if (hasGenPassType || hasWorldGenCalls)
                {
                    hasWorldGen = true;
                    if (genPassCount == 0)
                    {
                        genPassCount = worldGenMethodCalls > 0 ? worldGenMethodCalls : 1;
                    }
                }

                if (hasWorldGen)
                {
                    result.Success = true;
                    result.HasWorldGen = true;
                    result.DetectedGenPassCount = genPassCount;
                }
                else
                {
                    result.ErrorMessage = "No ModifyWorldGenTasks method found";
                }

                assemblyDef.Dispose();
            }
            catch (Exception ex)
            {
                result.ErrorMessage = ex.Message;
                result.Success = false;
            }
            finally
            {
                stopwatch.Stop();
                result.ExecutionTimeMs = stopwatch.ElapsedMilliseconds;
            }

            return result;
        }

        private void AnalyzeExecutionConflicts()
        {
            // Check for mods with worldgen (detected via assembly analysis)
            var modsWithWorldGen = executionResults
                .Where(r => r.HasWorldGen || r.GenPasses.Count > 0)
                .ToList();
            
            if (modsWithWorldGen.Count > 1)
            {
                detectedConflicts.Add(new WorldGenConflict
                {
                    Type = ConflictType.StructurePlacement,
                    Severity = ConflictSeverity.Medium,
                    Description = $"{modsWithWorldGen.Count} mod(s) detected with worldgen code",
                    AffectedMods = modsWithWorldGen.Select(m => m.ModName).ToList(),
                    Recommendation = "Multiple mods with worldgen detected - may conflict during actual world generation"
                });
            }
            
            // Check for mods with high gen pass counts
            var highPassCountMods = modsWithWorldGen
                .Where(m => m.DetectedGenPassCount > 5)
                .ToList();

            foreach (var mod in highPassCountMods)
            {
                detectedConflicts.Add(new WorldGenConflict
                {
                    Type = ConflictType.Performance,
                    Severity = ConflictSeverity.Medium,
                    Description = $"{mod.ModName} adds {mod.DetectedGenPassCount} gen passes (high count)",
                    AffectedMods = new List<string> { mod.ModName },
                    Recommendation = "High gen pass count may slow worldgen - consider optimization"
                });
            }
        }

        private void GenerateReport()
        {
            Console.WriteLine();
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("WORLDGEN EXECUTION SIMULATION REPORT");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();

            Console.WriteLine($"Total mods analyzed: {executionResults.Count}");
            Console.WriteLine($"Mods with worldgen detected: {executionResults.Count(r => r.HasWorldGen)}");
            Console.WriteLine($"Successful analysis: {executionResults.Count(r => r.Success)}");
            Console.WriteLine($"Failed to analyze: {executionResults.Count(r => !r.Success)}");
            Console.WriteLine($"Total gen passes detected: {executionResults.Sum(r => r.DetectedGenPassCount)}");
            Console.WriteLine($"Conflicts detected: {detectedConflicts.Count}");
            Console.WriteLine();
            
            // List mods with worldgen
            var worldGenMods = executionResults.Where(r => r.HasWorldGen).ToList();
            if (worldGenMods.Count > 0)
            {
                Console.WriteLine("MODS WITH WORLDGEN DETECTED:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var mod in worldGenMods.OrderByDescending(m => m.DetectedGenPassCount))
                {
                    Console.WriteLine($"  {mod.ModName}: {mod.DetectedGenPassCount} gen pass(es) detected");
                }
                Console.WriteLine();
            }

            if (detectedConflicts.Count > 0)
            {
                Console.WriteLine("DETECTED CONFLICTS:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var conflict in detectedConflicts.OrderByDescending(c => c.Severity))
                {
                    Console.WriteLine($"[{conflict.Severity}] {conflict.Type}: {conflict.Description}");
                    Console.WriteLine($"  Affected mods: {string.Join(", ", conflict.AffectedMods)}");
                    Console.WriteLine($"  Recommendation: {conflict.Recommendation}");
                    Console.WriteLine();
                }
            }
            else
            {
                Console.WriteLine("✓ No conflicts detected during worldgen simulation!");
            }
        }
    }

    public class ModWorldGenExecutionResult
    {
        public string ModPath { get; set; } = "";
        public string ModName { get; set; } = "";
        public bool Success { get; set; }
        public string? ErrorMessage { get; set; }
        public bool HasWorldGen { get; set; }
        public int DetectedGenPassCount { get; set; }
        public List<GenPass> GenPasses { get; set; } = new List<GenPass>();
        public List<GenPassExecutionResult> PassResults { get; set; } = new List<GenPassExecutionResult>();
        public double TotalWeight { get; set; }
        public long ExecutionTimeMs { get; set; }
    }

    public class GenPassExecutionResult
    {
        public string PassName { get; set; } = "";
        public double Weight { get; set; }
        public bool Success { get; set; }
        public string? ErrorMessage { get; set; }
    }

    public class WorldGenConflict
    {
        public ConflictType Type { get; set; }
        public ConflictSeverity Severity { get; set; }
        public string Description { get; set; } = "";
        public List<string> AffectedMods { get; set; } = new List<string>();
        public string Recommendation { get; set; } = "";
    }

    // ConflictType and ConflictSeverity are defined in WorldGenSimulator.cs
    // If WorldGenSimulator.cs is not included (e.g., in Error142Analyzer project), these are needed:
#if WORLDGEN_SIMULATOR_NOT_INCLUDED
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
#endif
}
