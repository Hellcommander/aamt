using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace Error142Analyzer
{
    /// <summary>
    /// Static analysis tool to find potential Error 142 causes in tModLoader mod source code.
    /// Error 142 occurs during type loading when classes inherit from types that aren't available.
    /// This tool scans source files to identify problematic patterns.
    /// </summary>
    class Error142Analyzer
    {
        private readonly string modSourcePath;
        private readonly List<Issue> issues = new List<Issue>();
        
        public Error142Analyzer(string modSourcePath)
        {
            this.modSourcePath = modSourcePath;
        }
        
        public void Analyze()
        {
            Console.WriteLine("Error 142 Analyzer - Scanning for potential type loading issues...");
            Console.WriteLine($"Mod Source: {modSourcePath}");
            Console.WriteLine();
            
            if (!Directory.Exists(modSourcePath))
            {
                Console.WriteLine($"ERROR: Directory not found: {modSourcePath}");
                return;
            }
            
            // Read build.txt to understand dependencies
            var buildTxt = ReadBuildTxt();
            var requiredMods = ParseRequiredMods(buildTxt);
            var weakMods = ParseWeakMods(buildTxt);
            
            Console.WriteLine($"Required Mods: {string.Join(", ", requiredMods)}");
            Console.WriteLine($"Weak Reference Mods: {string.Join(", ", weakMods)}");
            Console.WriteLine();
            
            // Scan all C# files
            var csFiles = Directory.GetFiles(modSourcePath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\"))
                .ToList();
            
            Console.WriteLine($"Found {csFiles.Count} C# files to analyze...");
            Console.WriteLine();
            
            foreach (var file in csFiles)
            {
                AnalyzeFile(file, requiredMods, weakMods);
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
            
            var match = Regex.Match(buildTxt, @"modReferences\s*=\s*(.+)");
            if (match.Success)
            {
                var refs = match.Groups[1].Value.Split(',')
                    .Select(r => r.Trim())
                    .Where(r => !string.IsNullOrEmpty(r));
                mods.AddRange(refs);
            }
            
            return mods;
        }
        
        private List<string> ParseWeakMods(string? buildTxt)
        {
            var mods = new List<string>();
            if (buildTxt == null) return mods;
            
            var match = Regex.Match(buildTxt, @"weakReferences\s*=\s*(.+)");
            if (match.Success)
            {
                var refs = match.Groups[1].Value.Split(',')
                    .Select(r => r.Trim())
                    .Where(r => !string.IsNullOrEmpty(r));
                mods.AddRange(refs);
            }
            
            return mods;
        }
        
        private void AnalyzeFile(string filePath, List<string> requiredMods, List<string> weakMods)
        {
            var content = File.ReadAllText(filePath);
            var fileName = Path.GetFileName(filePath);
            var relativePath = Path.GetRelativePath(modSourcePath, filePath);
            
            // Check for classes inheriting from external mod types
            CheckInheritanceFromExternalMods(content, relativePath, requiredMods, weakMods);
            
            // Check for using statements referencing external mods
            CheckUsingStatements(content, relativePath, requiredMods, weakMods);
            
            // Check for static field initializers that might reference external types
            CheckStaticFieldInitializers(content, relativePath, requiredMods, weakMods);
            
            // Check for missing JITWhenModsEnabled attributes
            CheckMissingJITAttributes(content, relativePath, requiredMods);
            
            // Check for typeof() calls that might fail
            CheckTypeofCalls(content, relativePath, requiredMods, weakMods);
        }
        
        private void CheckInheritanceFromExternalMods(string content, string filePath, List<string> requiredMods, List<string> weakMods)
        {
            // Pattern: public class ClassName : ExternalMod.Type
            var inheritancePattern = @"public\s+class\s+(\w+)\s*:\s*(\w+(?:\.\w+)*)";
            var matches = Regex.Matches(content, inheritancePattern);
            
            foreach (Match match in matches)
            {
                var className = match.Groups[1].Value;
                var baseType = match.Groups[2].Value;
                
                // Skip tModLoader base classes
                if (IsTModLoaderBaseClass(baseType))
                {
                    // Special case: Subworld needs SubworldLibrary
                    if (baseType.Equals("Subworld", StringComparison.OrdinalIgnoreCase) ||
                        baseType.EndsWith(".Subworld", StringComparison.OrdinalIgnoreCase))
                    {
                        // Check if it has JITWhenModsEnabled for SubworldLibrary
                        var hasJITAttribute = Regex.IsMatch(content, 
                            $@"\[JITWhenModsEnabled\s*\(\s*[""']?SubworldLibrary[""']?\s*\)\]\s*public\s+class\s+{Regex.Escape(className)}");
                        
                        if (!hasJITAttribute && !requiredMods.Contains("SubworldLibrary", StringComparer.OrdinalIgnoreCase))
                        {
                            issues.Add(new Issue
                            {
                                Severity = IssueSeverity.High,
                                File = filePath,
                                Line = GetLineNumber(content, match.Index),
                                Message = $"Class '{className}' inherits from 'Subworld' but SubworldLibrary is not in modReferences and class lacks [JITWhenModsEnabled(\"SubworldLibrary\")] attribute. This WILL cause Error 142 if SubworldLibrary isn't available.",
                                Suggestion = $"Add [JITWhenModsEnabled(\"SubworldLibrary\")] attribute above the class declaration, or add SubworldLibrary to modReferences in build.txt."
                            });
                        }
                    }
                    continue; // Skip tModLoader base classes
                }
                
                // Check if base type is from an external mod
                var modName = ExtractModNameFromType(baseType);
                if (modName != null)
                {
                    var isRequired = requiredMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                    var isWeak = weakMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                    
                    // Check if class has JITWhenModsEnabled attribute
                    var hasJITAttribute = Regex.IsMatch(content, 
                        $@"\[JITWhenModsEnabled\s*\(\s*[""']?{Regex.Escape(modName)}[""']?\s*\)\]\s*public\s+class\s+{Regex.Escape(className)}");
                    
                    if (isWeak && !hasJITAttribute)
                    {
                        issues.Add(new Issue
                        {
                            Severity = IssueSeverity.High,
                            File = filePath,
                            Line = GetLineNumber(content, match.Index),
                            Message = $"Class '{className}' inherits from '{baseType}' (weak reference mod '{modName}') but missing [JITWhenModsEnabled] attribute. This can cause Error 142 if {modName} isn't available.",
                            Suggestion = $"Add [JITWhenModsEnabled(\"{modName}\")] attribute above the class declaration."
                        });
                    }
                    else if (!isRequired && !isWeak && !hasJITAttribute)
                    {
                        issues.Add(new Issue
                        {
                            Severity = IssueSeverity.Medium,
                            File = filePath,
                            Line = GetLineNumber(content, match.Index),
                            Message = $"Class '{className}' inherits from '{baseType}' which appears to be from external mod '{modName}', but '{modName}' is not in build.txt dependencies.",
                            Suggestion = $"Add '{modName}' to modReferences in build.txt, or add [JITWhenModsEnabled(\"{modName}\")] attribute."
                        });
                    }
                }
            }
        }
        
        private void CheckUsingStatements(string content, string filePath, List<string> requiredMods, List<string> weakMods)
        {
            // Pattern: using ModName;
            var usingPattern = @"using\s+(\w+)\s*;";
            var matches = Regex.Matches(content, usingPattern);
            
            foreach (Match match in matches)
            {
                var namespaceName = match.Groups[1].Value;
                
                // Check if this looks like a mod namespace (not System, Terraria, etc.)
                if (IsSystemNamespace(namespaceName)) continue;
                
                var modName = namespaceName;
                var isRequired = requiredMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                var isWeak = weakMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                
                if (!isRequired && !isWeak && !IsTerrariaNamespace(namespaceName))
                {
                    // Check if file has JITWhenModsEnabled at class level
                    var hasJITAttribute = Regex.IsMatch(content, @"\[JITWhenModsEnabled");
                    
                    if (!hasJITAttribute)
                    {
                        issues.Add(new Issue
                        {
                            Severity = IssueSeverity.Low,
                            File = filePath,
                            Line = GetLineNumber(content, match.Index),
                            Message = $"Using statement for '{namespaceName}' but mod is not in build.txt dependencies.",
                            Suggestion = $"If '{namespaceName}' is an external mod, add it to modReferences or weakReferences in build.txt, or add [JITWhenModsEnabled] attribute to classes using it."
                        });
                    }
                }
            }
        }
        
        private void CheckStaticFieldInitializers(string content, string filePath, List<string> requiredMods, List<string> weakMods)
        {
            // Pattern: private static Type field = new Type(...) or = Type.Method()
            var staticInitPattern = @"(?:private|public|internal|protected)\s+static\s+\w+\s+\w+\s*=\s*(?:new\s+)?(\w+(?:\.\w+)*)";
            var matches = Regex.Matches(content, staticInitPattern);
            
            foreach (Match match in matches)
            {
                var typeName = match.Groups[1].Value;
                var modName = ExtractModNameFromType(typeName);
                
                if (modName != null)
                {
                    var isWeak = weakMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                    
                    if (isWeak)
                    {
                        issues.Add(new Issue
                        {
                            Severity = IssueSeverity.High,
                            File = filePath,
                            Line = GetLineNumber(content, match.Index),
                            Message = $"Static field initializer references '{typeName}' from weak reference mod '{modName}'. This can cause Error 142 if {modName} isn't available during type loading.",
                            Suggestion = $"Move initialization to a method (like Load()) that can check if {modName} is available first."
                        });
                    }
                }
            }
        }
        
        private void CheckMissingJITAttributes(string content, string filePath, List<string> requiredMods)
        {
            // Check if file has classes that inherit from required mod types but lack JITWhenModsEnabled
            // This is already covered in CheckInheritanceFromExternalMods, but we can add more specific checks here
        }
        
        private void CheckTypeofCalls(string content, string filePath, List<string> requiredMods, List<string> weakMods)
        {
            // Pattern: typeof(ModName.Type)
            var typeofPattern = @"typeof\s*\(\s*(\w+(?:\.\w+)*)\s*\)";
            var matches = Regex.Matches(content, typeofPattern);
            
            foreach (Match match in matches)
            {
                var typeName = match.Groups[1].Value;
                var modName = ExtractModNameFromType(typeName);
                
                if (modName != null)
                {
                    var isWeak = weakMods.Contains(modName, StringComparer.OrdinalIgnoreCase);
                    
                    if (isWeak)
                    {
                        issues.Add(new Issue
                        {
                            Severity = IssueSeverity.High,
                            File = filePath,
                            Line = GetLineNumber(content, match.Index),
                            Message = $"typeof({typeName}) call references weak reference mod '{modName}'. This can cause Error 142 if {modName} isn't available during type loading.",
                            Suggestion = $"Use reflection or ModLoader.GetMod(\"{modName}\")?.Code?.GetType() instead, or wrap in try-catch."
                        });
                    }
                }
            }
        }
        
        private string? ExtractModNameFromType(string typeName)
        {
            // Common patterns:
            // - SubworldLibrary.Subworld -> SubworldLibrary
            // - ModName.TypeName -> ModName
            // - ModName.Namespace.Type -> ModName
            
            var parts = typeName.Split('.');
            if (parts.Length > 0)
            {
                var firstPart = parts[0];
                
                // Skip system namespaces
                if (IsSystemNamespace(firstPart)) return null;
                if (IsTerrariaNamespace(firstPart)) return null;
                
                // Check if it looks like a mod name (not a common C# namespace)
                if (!IsCommonNamespace(firstPart))
                {
                    return firstPart;
                }
            }
            
            return null;
        }
        
        private bool IsSystemNamespace(string name)
        {
            var systemNamespaces = new[] { "System", "Microsoft", "Mono", "ReLogic", "FNA" };
            return systemNamespaces.Any(n => name.StartsWith(n, StringComparison.OrdinalIgnoreCase));
        }
        
        private bool IsTerrariaNamespace(string name)
        {
            return name.Equals("Terraria", StringComparison.OrdinalIgnoreCase);
        }
        
        private bool IsCommonNamespace(string name)
        {
            var commonNamespaces = new[] { "CrossModStabilizer", "CrossModLayer" };
            return commonNamespaces.Any(n => name.Equals(n, StringComparison.OrdinalIgnoreCase));
        }
        
        private bool IsTModLoaderBaseClass(string typeName)
        {
            // tModLoader base classes that are always available
            var tmlBaseClasses = new[]
            {
                "Mod", "ModSystem", "ModItem", "ModTile", "ModPlayer", "ModNPC",
                "ModProjectile", "ModBuff", "ModCommand", "ModConfig", "ModType",
                "GlobalItem", "GlobalNPC", "GlobalProjectile", "GlobalTile", "GlobalBuff",
                "GenPass", "Subworld" // Subworld is from SubworldLibrary, but we check it separately
            };
            
            return tmlBaseClasses.Any(c => typeName.Equals(c, StringComparison.OrdinalIgnoreCase) ||
                                           typeName.EndsWith("." + c, StringComparison.OrdinalIgnoreCase));
        }
        
        private int GetLineNumber(string content, int index)
        {
            return content.Substring(0, index).Count(c => c == '\n') + 1;
        }
        
        private void ReportResults()
        {
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine("ANALYSIS RESULTS");
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();
            
            if (issues.Count == 0)
            {
                Console.WriteLine("✓ No potential Error 142 issues found!");
                Console.WriteLine();
                Console.WriteLine("However, Error 142 can still occur if:");
                Console.WriteLine("  1. The mod hasn't been rebuilt in tModLoader");
                Console.WriteLine("  2. Required mods (like SubworldLibrary) aren't installed");
                Console.WriteLine("  3. There are version mismatches");
                return;
            }
            
            var highSeverity = issues.Where(i => i.Severity == IssueSeverity.High).ToList();
            var mediumSeverity = issues.Where(i => i.Severity == IssueSeverity.Medium).ToList();
            var lowSeverity = issues.Where(i => i.Severity == IssueSeverity.Low).ToList();
            
            Console.WriteLine($"Found {issues.Count} potential issues:");
            Console.WriteLine($"  HIGH: {highSeverity.Count}");
            Console.WriteLine($"  MEDIUM: {mediumSeverity.Count}");
            Console.WriteLine($"  LOW: {lowSeverity.Count}");
            Console.WriteLine();
            
            if (highSeverity.Count > 0)
            {
                Console.WriteLine("HIGH SEVERITY ISSUES (Can cause Error 142):");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var issue in highSeverity)
                {
                    Console.WriteLine($"[{issue.File}:{issue.Line}] {issue.Message}");
                    Console.WriteLine($"  → {issue.Suggestion}");
                    Console.WriteLine();
                }
            }
            
            if (mediumSeverity.Count > 0)
            {
                Console.WriteLine("MEDIUM SEVERITY ISSUES:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var issue in mediumSeverity)
                {
                    Console.WriteLine($"[{issue.File}:{issue.Line}] {issue.Message}");
                    Console.WriteLine($"  → {issue.Suggestion}");
                    Console.WriteLine();
                }
            }
            
            if (lowSeverity.Count > 0)
            {
                Console.WriteLine("LOW SEVERITY ISSUES:");
                Console.WriteLine("-".PadRight(80, '-'));
                foreach (var issue in lowSeverity)
                {
                    Console.WriteLine($"[{issue.File}:{issue.Line}] {issue.Message}");
                    Console.WriteLine($"  → {issue.Suggestion}");
                    Console.WriteLine();
                }
            }
            
            Console.WriteLine("=".PadRight(80, '='));
            Console.WriteLine();
            Console.WriteLine("RECOMMENDATIONS:");
            Console.WriteLine("1. Fix HIGH severity issues first - these can directly cause Error 142");
            Console.WriteLine("2. Ensure all classes inheriting from external mod types have [JITWhenModsEnabled]");
            Console.WriteLine("3. Rebuild the mod in tModLoader after making changes");
            Console.WriteLine("4. Verify required mods are installed and enabled");
        }
        
        static void Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("Error 142 Analyzer - Static analysis tool for tModLoader mods");
                Console.WriteLine();
                Console.WriteLine("Usage: Error142Analyzer.exe <mod-source-path>");
                Console.WriteLine();
                Console.WriteLine("Example:");
                Console.WriteLine("  Error142Analyzer.exe \"D:\\User_Directories\\Documents\\My Games\\Terraria\\tModLoader\\ModSources\\CrossModStabilizer\"");
                Console.WriteLine();
                return;
            }
            
            var modPath = args[0];
            var analyzer = new Error142Analyzer(modPath);
            analyzer.Analyze();
        }
    }
    
    class Issue
    {
        public IssueSeverity Severity { get; set; }
        public string File { get; set; } = "";
        public int Line { get; set; }
        public string Message { get; set; } = "";
        public string Suggestion { get; set; } = "";
    }
    
    enum IssueSeverity
    {
        Low,
        Medium,
        High
    }
}

