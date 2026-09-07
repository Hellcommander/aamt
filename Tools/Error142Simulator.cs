using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

namespace Error142Simulator
{
    /// <summary>
    /// Simulates tModLoader's mod loading process to detect Error 142.
    /// Uses actual tModLoader source references to mirror real game loading.
    /// This catches TypeLoadException that occurs during type resolution.
    /// </summary>
    class Error142Simulator
    {
        private readonly string modSourcePath;
        private readonly string tmlSourcePath;
        private readonly List<TypeLoadFailure> failures = new List<TypeLoadFailure>();
        
        public Error142Simulator(string modSourcePath, string tmlSourcePath)
        {
            this.modSourcePath = modSourcePath;
            this.tmlSourcePath = tmlSourcePath;
        }
        
        public void SimulateLoading()
        {
            Console.WriteLine("Error 142 Simulator - Simulating tModLoader mod loading...");
            Console.WriteLine($"Mod Source: {modSourcePath}");
            Console.WriteLine($"tModLoader Source: {tmlSourcePath}");
            Console.WriteLine();
            
            if (!Directory.Exists(modSourcePath))
            {
                Console.WriteLine($"ERROR: Mod source directory not found: {modSourcePath}");
                return;
            }
            
            if (!Directory.Exists(tmlSourcePath))
            {
                Console.WriteLine($"ERROR: tModLoader source directory not found: {tmlSourcePath}");
                Console.WriteLine("Please provide the path to tModLoader source code.");
                return;
            }
            
            // Read build.txt to understand dependencies
            var buildTxt = ReadBuildTxt();
            var requiredMods = ParseRequiredMods(buildTxt);
            
            Console.WriteLine($"Required Mods: {string.Join(", ", requiredMods)}");
            Console.WriteLine();
            
            // Try to load tModLoader assemblies
            var tmlAssemblies = LoadTModLoaderAssemblies();
            if (tmlAssemblies.Count == 0)
            {
                Console.WriteLine("WARNING: Could not load tModLoader assemblies.");
                Console.WriteLine("This tool needs tModLoader source or compiled assemblies to work properly.");
                Console.WriteLine("Trying alternative locations...");
                
                // Try to find tModLoader in ModAssemblies or game directory
                var altPaths = new[]
                {
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), 
                        "My Games", "Terraria", "tModLoader", "ModAssemblies", "tModLoader.dll"),
                    Path.Combine(modSourcePath, "..", "ModAssemblies", "tModLoader.dll"),
                    @"E:\SteamLibrary\steamapps\common\tModLoader\tModLoader.dll",
                    @"D:\games\Steam\steamapps\common\tModLoader\tModLoader.dll",
                };
                
                foreach (var path in altPaths)
                {
                    if (File.Exists(path))
                    {
                        try
                        {
                            var assembly = Assembly.LoadFrom(path);
                            tmlAssemblies.Add(assembly);
                            Console.WriteLine($"✓ Loaded tModLoader from: {path}");
                            break;
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"  Could not load from {path}: {ex.Message}");
                        }
                    }
                }
                
                if (tmlAssemblies.Count == 0)
                {
                    Console.WriteLine("ERROR: tModLoader.dll not found. SubworldLibrary requires tModLoader.");
                    Console.WriteLine("This WILL cause Error 142 if tModLoader isn't available during mod loading.");
                    Console.WriteLine();
                }
            }
            else
            {
                Console.WriteLine($"✓ Loaded {tmlAssemblies.Count} tModLoader assembly/ies");
            }
            
            // Try to load SubworldLibrary if it's a dependency
            Assembly? subworldLibraryAssembly = null;
            if (requiredMods.Contains("SubworldLibrary", StringComparer.OrdinalIgnoreCase))
            {
                subworldLibraryAssembly = TryLoadSubworldLibrary();
                if (subworldLibraryAssembly == null)
                {
                    Console.WriteLine("WARNING: SubworldLibrary not found. This will cause Error 142!");
                    Console.WriteLine("SubworldLibrary must be available for type resolution.");
                    Console.WriteLine();
                }
                else
                {
                    Console.WriteLine($"✓ SubworldLibrary loaded: {subworldLibraryAssembly.GetName().Name} v{subworldLibraryAssembly.GetName().Version}");
                }
            }
            
            // Find all C# files that inherit from Subworld
            var subworldFiles = FindSubworldClasses();
            Console.WriteLine($"Found {subworldFiles.Count} Subworld classes to test:");
            foreach (var file in subworldFiles)
            {
                Console.WriteLine($"  - {Path.GetFileName(file)}");
            }
            Console.WriteLine();
            
            // ALSO scan ALL C# files for problematic patterns
            Console.WriteLine("Scanning ALL C# files for Error 142 patterns...");
            var allCsFiles = Directory.GetFiles(modSourcePath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\"))
                .ToList();
            Console.WriteLine($"Scanning {allCsFiles.Count} C# files...");
            Console.WriteLine();
            
            // Try to resolve each Subworld class
            Console.WriteLine("Testing type resolution (this simulates Error 142 conditions)...");
            Console.WriteLine();
            
            foreach (var file in subworldFiles)
            {
                TestTypeResolution(file, subworldLibraryAssembly, tmlAssemblies);
            }
            
            // Deep scan ALL files for patterns
            Console.WriteLine();
            Console.WriteLine("Deep scanning all files for Error 142 patterns...");
            foreach (var file in allCsFiles)
            {
                DeepScanFile(file);
            }
            
            // Report results
            ReportResults();
        }
        
        private string? ReadBuildTxt()
        {
            var buildTxtPath = Path.Combine(modSourcePath, "build.txt");
            if (File.Exists(buildTxtPath))
            {
                return File.ReadAllText(buildTxtPath);
            }
            return null;
        }
        
        private List<string> ParseRequiredMods(string? buildTxt)
        {
            var mods = new List<string>();
            if (buildTxt == null) return mods;
            
            var lines = buildTxt.Split('\n');
            foreach (var line in lines)
            {
                if (line.Trim().StartsWith("modReferences", StringComparison.OrdinalIgnoreCase))
                {
                    var parts = line.Split('=');
                    if (parts.Length > 1)
                    {
                        var refs = parts[1].Split(',')
                            .Select(r => r.Trim())
                            .Where(r => !string.IsNullOrEmpty(r));
                        mods.AddRange(refs);
                    }
                }
            }
            
            return mods;
        }
        
        private List<Assembly> LoadTModLoaderAssemblies()
        {
            var assemblies = new List<Assembly>();
            
            // Try to load tModLoader assemblies from common locations
            var possiblePaths = new[]
            {
                Path.Combine(tmlSourcePath, "bin", "Debug", "tModLoader.dll"),
                Path.Combine(tmlSourcePath, "bin", "Release", "tModLoader.dll"),
                Path.Combine(tmlSourcePath, "Terraria", "bin", "Debug", "tModLoader.dll"),
                Path.Combine(tmlSourcePath, "Terraria", "bin", "Release", "tModLoader.dll"),
            };
            
            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    try
                    {
                        var assembly = Assembly.LoadFrom(path);
                        assemblies.Add(assembly);
                        Console.WriteLine($"✓ Loaded: {Path.GetFileName(path)}");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"  Could not load {Path.GetFileName(path)}: {ex.Message}");
                    }
                }
            }
            
            return assemblies;
        }
        
        private Assembly? TryLoadSubworldLibrary()
        {
            // Try to find SubworldLibrary in common locations
            var possiblePaths = new[]
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), 
                    "My Games", "Terraria", "tModLoader", "Mods", "SubworldLibrary.tmod"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), 
                    "My Games", "Terraria", "tModLoader", "ModAssemblies", "SubworldLibrary.dll"),
                Path.Combine(modSourcePath, "..", "ModAssemblies", "SubworldLibrary.dll"),
            };
            
            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    try
                    {
                        // For .tmod files, we'd need to extract, but for now try .dll
                        if (path.EndsWith(".dll"))
                        {
                            var assembly = Assembly.LoadFrom(path);
                            return assembly;
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"  Could not load SubworldLibrary from {path}: {ex.Message}");
                    }
                }
            }
            
            return null;
        }
        
        private List<string> FindSubworldClasses()
        {
            var files = new List<string>();
            var csFiles = Directory.GetFiles(modSourcePath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\"))
                .ToList();
            
            foreach (var file in csFiles)
            {
                var content = File.ReadAllText(file);
                // Check if file has class inheriting from Subworld
                if (System.Text.RegularExpressions.Regex.IsMatch(content, 
                    @"public\s+class\s+\w+\s*:\s*Subworld"))
                {
                    files.Add(file);
                }
            }
            
            return files;
        }
        
        private void TestTypeResolution(string filePath, Assembly? subworldLibraryAssembly, List<Assembly> tmlAssemblies)
        {
            var fileName = Path.GetFileName(filePath);
            var relativePath = Path.GetRelativePath(modSourcePath, filePath);
            
            try
            {
                // Read the file to get class name
                var content = File.ReadAllText(filePath);
                var classNameMatch = System.Text.RegularExpressions.Regex.Match(content, 
                    @"public\s+class\s+(\w+)\s*:\s*Subworld");
                
                if (!classNameMatch.Success)
                {
                    return;
                }
                
                var className = classNameMatch.Groups[1].Value;
                
                // DEEP ANALYSIS - Find code patterns that cause Error 142
                CheckForProblematicPatterns(content, fileName, relativePath, className);
                
                // Check if SubworldLibrary is available
                if (subworldLibraryAssembly == null)
                {
                    failures.Add(new TypeLoadFailure
                    {
                        File = relativePath,
                        ClassName = className,
                        Error = "SubworldLibrary assembly not found",
                        Severity = FailureSeverity.Critical,
                        Message = $"Class '{className}' inherits from Subworld, but SubworldLibrary is not available. This WILL cause Error 142."
                    });
                    Console.WriteLine($"✗ {fileName}: SubworldLibrary not available - Error 142 will occur");
                    return;
                }
                
                // Try to get the Subworld type from SubworldLibrary
                try
                {
                    // First, check if tModLoader is available (SubworldLibrary depends on it)
                    if (tmlAssemblies.Count == 0)
                    {
                        failures.Add(new TypeLoadFailure
                        {
                            File = relativePath,
                            ClassName = className,
                            Error = "tModLoader assembly not found",
                            Severity = FailureSeverity.Critical,
                            Message = $"SubworldLibrary depends on tModLoader, but tModLoader.dll is not available. This WILL cause Error 142. SubworldLibrary cannot load its types without tModLoader."
                        });
                        Console.WriteLine($"✗ {fileName}: tModLoader not available - SubworldLibrary cannot load");
                        return;
                    }
                    
                    // Try different possible type names
                    var possibleTypeNames = new[]
                    {
                        "SubworldLibrary.Subworld",
                        "Subworld",
                        "SubworldLibrary.SubworldLibrary.Subworld"
                    };
                    
                    Type? subworldType = null;
                    string? foundTypeName = null;
                    
                    foreach (var typeName in possibleTypeNames)
                    {
                        try
                        {
                            subworldType = subworldLibraryAssembly.GetType(typeName);
                            if (subworldType != null)
                            {
                                foundTypeName = typeName;
                                break;
                            }
                        }
                        catch (ReflectionTypeLoadException ex)
                        {
                            // This is the actual Error 142 - types can't be loaded
                            var loaderExceptions = ex.LoaderExceptions?.Where(e => e != null).ToList() ?? new List<Exception>();
                            var missingAssemblies = loaderExceptions
                                .Where(e => e.Message.Contains("Could not load file or assembly"))
                                .Select(e => e.Message)
                                .Distinct()
                                .ToList();
                            
                            failures.Add(new TypeLoadFailure
                            {
                                File = relativePath,
                                ClassName = className,
                                Error = $"ReflectionTypeLoadException: {ex.Message}",
                                Severity = FailureSeverity.Critical,
                                Message = $"THIS IS ERROR 142! ReflectionTypeLoadException when trying to load Subworld type. Missing assemblies: {string.Join("; ", missingAssemblies)}",
                                InnerException = string.Join("; ", loaderExceptions.Select(e => e.Message))
                            });
                            Console.WriteLine($"✗ {fileName}: ReflectionTypeLoadException - THIS IS ERROR 142!");
                            if (missingAssemblies.Count > 0)
                            {
                                Console.WriteLine($"  Missing: {string.Join(", ", missingAssemblies.Take(3))}");
                            }
                            return;
                        }
                    }
                    
                    // If not found, try to find any type containing "Subworld"
                    if (subworldType == null)
                    {
                        try
                        {
                            var allTypes = subworldLibraryAssembly.GetTypes();
                            subworldType = allTypes.FirstOrDefault(t => 
                                t.Name == "Subworld" && 
                                (t.Namespace == "SubworldLibrary" || t.Namespace == null));
                            
                            if (subworldType != null)
                            {
                                foundTypeName = subworldType.FullName ?? subworldType.Name;
                            }
                        }
                        catch (ReflectionTypeLoadException ex)
                        {
                            // Error 142 - can't enumerate types
                            failures.Add(new TypeLoadFailure
                            {
                                File = relativePath,
                                ClassName = className,
                                Error = $"ReflectionTypeLoadException enumerating types: {ex.Message}",
                                Severity = FailureSeverity.Critical,
                                Message = $"THIS IS ERROR 142! Cannot enumerate types in SubworldLibrary assembly. This means types cannot be resolved.",
                                InnerException = string.Join("; ", ex.LoaderExceptions?.Where(e => e != null).Select(e => e.Message) ?? Array.Empty<string>())
                            });
                            Console.WriteLine($"✗ {fileName}: Cannot enumerate SubworldLibrary types - THIS IS ERROR 142!");
                            return;
                        }
                    }
                    
                    if (subworldType == null)
                    {
                        // List available types for debugging
                        var allTypes = subworldLibraryAssembly.GetTypes();
                        var subworldTypes = allTypes.Where(t => t.Name.Contains("Subworld")).ToList();
                        
                        var errorMsg = "SubworldLibrary.Subworld type not found in assembly";
                        if (subworldTypes.Count > 0)
                        {
                            errorMsg += $". Found similar types: {string.Join(", ", subworldTypes.Select(t => t.FullName ?? t.Name))}";
                        }
                        else
                        {
                            var namespaces = allTypes.Select(t => t.Namespace).Where(n => n != null).Distinct().Take(5);
                            errorMsg += $". Assembly namespaces: {string.Join(", ", namespaces)}";
                        }
                        
                        failures.Add(new TypeLoadFailure
                        {
                            File = relativePath,
                            ClassName = className,
                            Error = errorMsg,
                            Severity = FailureSeverity.Critical,
                            Message = $"SubworldLibrary assembly loaded, but Subworld type not found. This WILL cause Error 142. The type may have a different name or namespace."
                        });
                        Console.WriteLine($"✗ {fileName}: Subworld type not found in SubworldLibrary");
                        return;
                    }
                    
                    Console.WriteLine($"  Found Subworld type: {foundTypeName}");
                    
                    // Check if class has JITWhenModsEnabled attribute
                    var hasJIT = System.Text.RegularExpressions.Regex.IsMatch(content, 
                        $@"\[JITWhenModsEnabled\s*\(\s*[""']?SubworldLibrary[""']?\s*\)\]\s*public\s+class\s+{System.Text.RegularExpressions.Regex.Escape(className)}");
                    
                    if (!hasJIT)
                    {
                        failures.Add(new TypeLoadFailure
                        {
                            File = relativePath,
                            ClassName = className,
                            Error = "Missing [JITWhenModsEnabled(\"SubworldLibrary\")] attribute",
                            Severity = FailureSeverity.High,
                            Message = $"Class '{className}' inherits from Subworld but lacks [JITWhenModsEnabled(\"SubworldLibrary\")] attribute. This may cause Error 142 if SubworldLibrary isn't available."
                        });
                        Console.WriteLine($"⚠ {fileName}: Missing [JITWhenModsEnabled] attribute");
                    }
                    else
                    {
                        Console.WriteLine($"✓ {fileName}: Properly configured");
                    }
                }
                catch (TypeLoadException ex)
                {
                    failures.Add(new TypeLoadFailure
                    {
                        File = relativePath,
                        ClassName = className,
                        Error = $"TypeLoadException: {ex.Message}",
                        Severity = FailureSeverity.Critical,
                        Message = $"TypeLoadException when trying to resolve Subworld type: {ex.Message}. This WILL cause Error 142.",
                        InnerException = ex.InnerException?.Message
                    });
                    Console.WriteLine($"✗ {fileName}: TypeLoadException - {ex.Message}");
                }
                catch (Exception ex)
                {
                    failures.Add(new TypeLoadFailure
                    {
                        File = relativePath,
                        ClassName = className,
                        Error = $"{ex.GetType().Name}: {ex.Message}",
                        Severity = FailureSeverity.Medium,
                        Message = $"Exception during type resolution: {ex.Message}"
                    });
                    Console.WriteLine($"⚠ {fileName}: {ex.GetType().Name} - {ex.Message}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR analyzing {fileName}: {ex.Message}");
            }
        }
        
        private void CheckForProblematicPatterns(string content, string fileName, string relativePath, string className)
        {
            var issues = new List<string>();
            
            // Pattern 1: Static field initializers using Subworld types
            // Example: private static MySubworld instance = new MySubworld();
            var staticFieldPattern = System.Text.RegularExpressions.Regex.Matches(content, 
                @"(private|public|protected|internal)\s+static\s+(\w+)\s+(\w+)\s*=\s*new\s+\w+\s*\(");
            
            if (staticFieldPattern.Count > 0)
            {
                issues.Add($"CRITICAL: Found {staticFieldPattern.Count} static field(s) with initializers. " +
                    "Static fields that reference Subworld types are initialized BEFORE JIT, causing Error 142. " +
                    "FIX: Remove static field initializers or make them lazy-loaded in a method.");
            }
            
            // Pattern 2: Static constructors
            var staticCtorPattern = System.Text.RegularExpressions.Regex.IsMatch(content, 
                $@"static\s+{System.Text.RegularExpressions.Regex.Escape(className)}\s*\(");
            
            if (staticCtorPattern)
            {
                issues.Add("CRITICAL: Found static constructor. Static constructors run BEFORE JIT, causing Error 142. " +
                    "FIX: Remove static constructor or move initialization to Load() method.");
            }
            
            // Pattern 3: Field declarations using Subworld types without [JITWhenModsEnabled]
            // This is tricky - even instance fields can cause issues if they reference types from SubworldLibrary
            var fieldPattern = System.Text.RegularExpressions.Regex.Matches(content,
                @"(private|public|protected|internal)\s+(Subworld|SubworldSystem|\w+Subworld)\s+\w+\s*;");
            
            if (fieldPattern.Count > 0)
            {
                issues.Add($"HIGH: Found {fieldPattern.Count} field(s) with Subworld types. " +
                    "Field types from SubworldLibrary might cause type loading issues. " +
                    "FIX: Consider making fields nullable or using object type with casts.");
            }
            
            // Pattern 4: Missing [JITWhenModsEnabled] attribute
            var hasJIT = System.Text.RegularExpressions.Regex.IsMatch(content, 
                $@"\[JITWhenModsEnabled\s*\(\s*[""']?SubworldLibrary[""']?\s*\)\]\s*public\s+class\s+{System.Text.RegularExpressions.Regex.Escape(className)}");
            
            if (!hasJIT)
            {
                // Check if it's on the line before
                var hasJITBefore = System.Text.RegularExpressions.Regex.IsMatch(content,
                    $@"\[JITWhenModsEnabled\s*\(\s*[""']?SubworldLibrary[""']?\s*\)\]\s*[\r\n]+\s*public\s+class\s+{System.Text.RegularExpressions.Regex.Escape(className)}");
                
                if (!hasJITBefore)
                {
                    issues.Add("CRITICAL: Missing [JITWhenModsEnabled(\"SubworldLibrary\")] attribute. " +
                        "Class inherits from Subworld but lacks the attribute. " +
                        "FIX: Add [JITWhenModsEnabled(\"SubworldLibrary\")] above the class declaration.");
                }
            }
            
            // Pattern 5: Using statements that might not be available
            var usingSubworld = System.Text.RegularExpressions.Regex.IsMatch(content,
                @"using\s+SubworldLibrary");
            
            if (!usingSubworld)
            {
                issues.Add("MEDIUM: Missing 'using SubworldLibrary;' directive. " +
                    "While not always required, it's recommended for clarity.");
            }
            
            // Pattern 6: Check for method signatures that use Subworld types as parameters
            var methodParams = System.Text.RegularExpressions.Regex.Matches(content,
                @"(public|private|protected|internal)\s+\w+\s+\w+\s*\(\s*Subworld");
            
            if (methodParams.Count > 0)
            {
                issues.Add($"MEDIUM: Found {methodParams.Count} method(s) with Subworld type parameters. " +
                    "Method signatures are resolved during type loading. " +
                    "Consider using base types or interfaces instead.");
            }
            
            // Pattern 7: Check for typeof() usage with Subworld types
            var typeofPattern = System.Text.RegularExpressions.Regex.Matches(content,
                @"typeof\s*\(\s*Subworld");
            
            if (typeofPattern.Count > 0)
            {
                issues.Add($"HIGH: Found {typeofPattern.Count} typeof() call(s) with Subworld types. " +
                    "typeof() is resolved at type loading time, BEFORE JIT. " +
                    "FIX: Use string-based type lookups or move to a method called after JIT.");
            }
            
            // Pattern 8: Check for generic constraints
            var genericConstraint = System.Text.RegularExpressions.Regex.Matches(content,
                @"where\s+\w+\s*:\s*Subworld");
            
            if (genericConstraint.Count > 0)
            {
                issues.Add($"HIGH: Found {genericConstraint.Count} generic constraint(s) using Subworld. " +
                    "Generic constraints are resolved at type loading time. " +
                    "FIX: Use less specific constraints or remove generic constraints.");
            }
            
            if (issues.Count > 0)
            {
                foreach (var issue in issues)
                {
                    var severity = issue.StartsWith("CRITICAL") ? FailureSeverity.Critical :
                                   issue.StartsWith("HIGH") ? FailureSeverity.High :
                                   FailureSeverity.Medium;
                    
                    failures.Add(new TypeLoadFailure
                    {
                        File = relativePath,
                        ClassName = className,
                        Error = issue.Split(':')[0],
                        Severity = severity,
                        Message = issue
                    });
                }
                
                var criticalCount = issues.Count(i => i.StartsWith("CRITICAL"));
                if (criticalCount > 0)
                {
                    Console.WriteLine($"✗ {fileName}: {criticalCount} CRITICAL issue(s) found");
                }
                else
                {
                    Console.WriteLine($"⚠ {fileName}: {issues.Count} issue(s) found");
                }
            }
        }
        
        private void DeepScanFile(string filePath)
        {
            var fileName = Path.GetFileName(filePath);
            var relativePath = Path.GetRelativePath(modSourcePath, filePath);
            
            try
            {
                var content = File.ReadAllText(filePath);
                
                // Extract class name if possible
                var classMatch = System.Text.RegularExpressions.Regex.Match(content,
                    @"public\s+(?:class|struct|interface)\s+(\w+)");
                var className = classMatch.Success ? classMatch.Groups[1].Value : "Unknown";
                
                var issues = new List<string>();
                
                // Pattern 1: Static field initializers with typeof() for SubworldLibrary types
                var staticTypeofPattern = System.Text.RegularExpressions.Regex.Matches(content,
                    @"static\s+.*=.*typeof\s*\([^)]*Subworld[^)]*\)");
                
                if (staticTypeofPattern.Count > 0)
                {
                    issues.Add($"CRITICAL: Found {staticTypeofPattern.Count} static field(s) with typeof(Subworld...). " +
                        "Static fields with typeof() are resolved BEFORE JIT, causing Error 142.");
                }
                
                // Pattern 2: Check for ModSystem with static fields referencing SubworldLibrary
                var isModSystem = System.Text.RegularExpressions.Regex.IsMatch(content, @":\s*ModSystem");
                if (isModSystem)
                {
                    // Look for static FIELDS (not methods) referencing Subworld types
                    // Exclude methods by checking they end with ; not (
                    var staticFieldMatches = System.Text.RegularExpressions.Regex.Matches(content,
                        @"(private|public|protected|internal)\s+static\s+[^(]*Subworld[^(]*;");
                    
                    if (staticFieldMatches.Count > 0)
                    {
                        issues.Add($"CRITICAL: ModSystem with {staticFieldMatches.Count} static field(s) referencing Subworld types. " +
                            "ModSystem types are loaded early. Static fields cause Error 142.");
                    }
                }
                
                // Pattern 3: Class without [JITWhenModsEnabled] but using SubworldLibrary types
                var usesSubworld = System.Text.RegularExpressions.Regex.IsMatch(content, @"Subworld|SubworldSystem");
                var hasJIT = System.Text.RegularExpressions.Regex.IsMatch(content, @"\[JITWhenModsEnabled\(");
                
                if (usesSubworld && !hasJIT && !relativePath.Contains("Examples"))
                {
                    // Check if it's not a Subworld class itself (those need JIT)
                    var inheritsSubworld = System.Text.RegularExpressions.Regex.IsMatch(content, @":\s*Subworld");
                    
                    if (!inheritsSubworld)
                    {
                        issues.Add($"HIGH: Class uses SubworldLibrary types but lacks [JITWhenModsEnabled(\"SubworldLibrary\")]. " +
                            "Any class that references SubworldLibrary types should have this attribute.");
                    }
                }
                
                // Pattern 4: Assembly-level attributes that might cause issues
                var assemblyAttrs = System.Text.RegularExpressions.Regex.Matches(content,
                    @"\[assembly:.*Subworld");
                
                if (assemblyAttrs.Count > 0)
                {
                    issues.Add($"HIGH: Found {assemblyAttrs.Count} assembly attribute(s) referencing Subworld. " +
                        "Assembly-level attributes are loaded very early and can cause Error 142.");
                }
                
                // Pattern 5: Const fields with typeof()
                var constTypeofPattern = System.Text.RegularExpressions.Regex.Matches(content,
                    @"const\s+.*typeof");
                
                if (constTypeofPattern.Count > 0)
                {
                    issues.Add($"MEDIUM: Found {constTypeofPattern.Count} const field(s) with typeof(). " +
                        "While const usually works, combining with external types can cause issues.");
                }
                
                if (issues.Count > 0)
                {
                    var criticalCount = issues.Count(i => i.StartsWith("CRITICAL"));
                    if (criticalCount > 0)
                    {
                        Console.WriteLine($"✗ {relativePath}: {criticalCount} CRITICAL issue(s)");
                    }
                    
                    foreach (var issue in issues)
                    {
                        var severity = issue.StartsWith("CRITICAL") ? FailureSeverity.Critical :
                                       issue.StartsWith("HIGH") ? FailureSeverity.High :
                                       FailureSeverity.Medium;
                        
                        failures.Add(new TypeLoadFailure
                        {
                            File = relativePath,
                            ClassName = className,
                            Error = issue.Split(':')[0],
                            Severity = severity,
                            Message = issue
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR scanning {fileName}: {ex.Message}");
            }
        }
        
        private void ReportResults()
        {
            Console.WriteLine();
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("SIMULATION RESULTS");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();
            
            if (failures.Count == 0)
            {
                Console.WriteLine("✓ No Error 142 issues detected!");
                Console.WriteLine();
                Console.WriteLine("All Subworld classes are properly configured:");
                Console.WriteLine("  - SubworldLibrary is available");
                Console.WriteLine("  - All classes have [JITWhenModsEnabled] attributes");
                Console.WriteLine();
                Console.WriteLine("However, Error 142 can still occur if:");
                Console.WriteLine("  1. The mod hasn't been rebuilt in tModLoader");
                Console.WriteLine("  2. SubworldLibrary isn't enabled in tModLoader");
                Console.WriteLine("  3. There are version mismatches");
                return;
            }
            
            var critical = failures.Where(f => f.Severity == FailureSeverity.Critical).ToList();
            var high = failures.Where(f => f.Severity == FailureSeverity.High).ToList();
            var medium = failures.Where(f => f.Severity == FailureSeverity.Medium).ToList();
            
            Console.WriteLine($"Found {failures.Count} issues:");
            Console.WriteLine($"  CRITICAL: {critical.Count} (WILL cause Error 142)");
            Console.WriteLine($"  HIGH: {high.Count} (May cause Error 142)");
            Console.WriteLine($"  MEDIUM: {medium.Count}");
            Console.WriteLine();
            
            if (critical.Count > 0)
            {
                Console.WriteLine("CRITICAL ISSUES (WILL cause Error 142):");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var failure in critical)
                {
                    Console.WriteLine($"[{failure.File}] {failure.ClassName}");
                    Console.WriteLine($"  Error: {failure.Error}");
                    Console.WriteLine($"  {failure.Message}");
                    if (!string.IsNullOrEmpty(failure.InnerException))
                    {
                        Console.WriteLine($"  Inner: {failure.InnerException}");
                    }
                    Console.WriteLine();
                }
            }
            
            if (high.Count > 0)
            {
                Console.WriteLine("HIGH SEVERITY ISSUES:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var failure in high)
                {
                    Console.WriteLine($"[{failure.File}] {failure.ClassName}");
                    Console.WriteLine($"  {failure.Message}");
                    Console.WriteLine();
                }
            }
            
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();
            Console.WriteLine("RECOMMENDATIONS:");
            if (critical.Count > 0)
            {
                Console.WriteLine("1. Fix CRITICAL issues immediately - these WILL cause Error 142");
            }
            Console.WriteLine("2. Ensure SubworldLibrary is installed and enabled in tModLoader");
            Console.WriteLine("3. Rebuild the mod in tModLoader after making changes");
        }
        
        static void Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Error 142 Simulator - Simulates tModLoader mod loading");
                Console.WriteLine();
                Console.WriteLine("Usage: Error142Simulator.exe <mod-source-path> <tmodloader-source-path>");
                Console.WriteLine();
                Console.WriteLine("Example:");
                Console.WriteLine(@"  Error142Simulator.exe ""D:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer"" ""D:\User_Directories\Documents\My Games\Terraria\tModLoader-1.4.4""");
                Console.WriteLine();
                return;
            }
            
            var modPath = args[0];
            var tmlPath = args[1];
            
            var simulator = new Error142Simulator(modPath, tmlPath);
            simulator.SimulateLoading();
        }
    }
    
    class TypeLoadFailure
    {
        public string File { get; set; } = "";
        public string ClassName { get; set; } = "";
        public string Error { get; set; } = "";
        public FailureSeverity Severity { get; set; }
        public string Message { get; set; } = "";
        public string? InnerException { get; set; }
    }
    
    enum FailureSeverity
    {
        Medium,
        High,
        Critical
    }
}

