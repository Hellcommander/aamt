using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Emit;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.References;

namespace QudLab.RoslynCompile;

public sealed class CompileDiagnostic
{
    public string Id { get; init; } = "";
    public string Severity { get; init; } = "";
    public string Message { get; init; } = "";
    public string? Path { get; init; }
    public int Line { get; init; }
    public int Column { get; init; }

    public override string ToString() =>
        $"{Severity.ToLowerInvariant()} {Id} {Path ?? ""}({Line},{Column}): {Message}";
}

public sealed class CompileResult
{
    public bool Success { get; init; }
    public byte[]? AssemblyBytes { get; init; }
    public string? OutputPath { get; init; }
    public IReadOnlyList<CompileDiagnostic> Diagnostics { get; init; } = Array.Empty<CompileDiagnostic>();
    public int ReferenceCount { get; init; }

    /// <summary>How many of <see cref="ReferenceCount"/> came from sibling mods rather than game Managed.</summary>
    public int ModReferenceCount { get; init; }
}

/// <summary>
/// Compiles mod sources against the same Managed DLLs as Caves of Qud (Unity/Mono).
/// Does not mix host .NET (CoreLib) with game mscorlib.
/// </summary>
public sealed class QudModCompiler
{
    public IReadOnlyList<string> GetReferencePaths(QudInstallInfo install) =>
        QudReferenceSet.FromInstall(install).AssemblyPaths;

    public CompileResult Compile(
        QudInstallInfo install,
        IEnumerable<(string path, string source)> sources,
        string assemblyName = "QudLabMod",
        IEnumerable<string>? extraReferences = null)
    {
        var sourceList = sources.ToList();
        if (sourceList.Count == 0)
        {
            return new CompileResult
            {
                Success = false,
                Diagnostics = new[]
                {
                    new CompileDiagnostic
                    {
                        Id = "QUDLAB001",
                        Severity = "Error",
                        Message = "No source files to compile.",
                        Line = 1,
                        Column = 1
                    }
                }
            };
        }

        var trees = sourceList.Select(s =>
            CSharpSyntaxTree.ParseText(
                s.source,
                new CSharpParseOptions(LanguageVersion.CSharp9),
                path: s.path)).ToList();

        var refSet = QudReferenceSet.FromInstall(install);
        var refs = BuildReferences(refSet, extraReferences, out int modRefs);

        var compilation = CSharpCompilation.Create(
            assemblyName,
            trees,
            refs,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                .WithOptimizationLevel(OptimizationLevel.Debug)
                .WithAllowUnsafe(true)
                .WithPlatform(Platform.AnyCpu)
                .WithMetadataImportOptions(MetadataImportOptions.All));

        using var pe = new MemoryStream();
        var emitOptions = new EmitOptions(runtimeMetadataVersion: "v4.0.30319");
        var emit = compilation.Emit(pe, options: emitOptions);
        var diags = emit.Diagnostics
            .Where(d => d.Severity >= DiagnosticSeverity.Warning)
            .Select(MapDiagnostic)
            .ToList();

        if (!emit.Success)
            return new CompileResult
            {
                Success = false,
                Diagnostics = diags,
                ReferenceCount = refs.Count,
                ModReferenceCount = modRefs
            };

        return new CompileResult
        {
            Success = true,
            AssemblyBytes = pe.ToArray(),
            Diagnostics = diags,
            ReferenceCount = refs.Count,
            ModReferenceCount = modRefs
        };
    }

    /// <summary>
    /// Compile all *.cs under projectDir; write DLL to sibling bin/ folder (never into game install).
    /// </summary>
    public CompileResult CompileProject(
        QudInstallInfo install,
        string projectDir,
        string assemblyName = "QudLab.ModWorkspace",
        string? outputDir = null)
    {
        projectDir = Path.GetFullPath(projectDir);
        if (!Directory.Exists(projectDir))
        {
            return new CompileResult
            {
                Success = false,
                Diagnostics = new[]
                {
                    new CompileDiagnostic
                    {
                        Id = "QUDLAB002",
                        Severity = "Error",
                        Message = $"Project directory not found: {projectDir}",
                        Line = 1,
                        Column = 1
                    }
                }
            };
        }

        var files = QudLab.Core.Install.QudModPaths.EnumerateSourceFiles(projectDir, "*.cs")
            .OrderBy(f => f, StringComparer.OrdinalIgnoreCase)
            .ToList();

        if (files.Count == 0)
        {
            return new CompileResult
            {
                Success = false,
                Diagnostics = new[]
                {
                    new CompileDiagnostic
                    {
                        Id = "QUDLAB003",
                        Severity = "Error",
                        Message = $"No .cs files under {projectDir} (skipped Library/Packages/bin/obj).",
                        Line = 1,
                        Column = 1
                    }
                }
            };
        }

        // Prefer a stable assembly name for live mods (folder name)
        var leaf = Path.GetFileName(projectDir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        if (string.Equals(assemblyName, "QudLab.ModWorkspace", StringComparison.Ordinal) &&
            !string.IsNullOrWhiteSpace(leaf) &&
            !string.Equals(leaf, "src", StringComparison.OrdinalIgnoreCase))
        {
            assemblyName = SanitizeAsmName(leaf);
        }

        var sources = files.Select(f => (f, File.ReadAllText(f)));
        var result = Compile(install, sources, assemblyName, DiscoverSiblingModAssemblies(projectDir, assemblyName));
        if (!result.Success || result.AssemblyBytes is null)
            return result;

        outputDir ??= Path.Combine(Directory.GetParent(projectDir)?.FullName ?? projectDir, "bin");
        Directory.CreateDirectory(outputDir);
        var outPath = Path.Combine(outputDir, assemblyName + ".dll");
        File.WriteAllBytes(outPath, result.AssemblyBytes);

        return new CompileResult
        {
            Success = true,
            AssemblyBytes = result.AssemblyBytes,
            OutputPath = outPath,
            Diagnostics = result.Diagnostics,
            ReferenceCount = result.ReferenceCount,
            ModReferenceCount = result.ModReferenceCount
        };
    }

    /// <summary>
    /// Assemblies belonging to the other mods installed alongside <paramref name="projectDir"/>.
    ///
    /// Mods legitimately reference each other's types — that is what the "00_" folder prefix
    /// buys, since Qud compiles mods in load order so the dependency exists first. Without
    /// these, any such mod fails here with a wall of CS0103/CS0246 that looks like broken
    /// source but is only a missing reference (plus cascading CS0165 where an unresolved
    /// call's `out` argument never counts as assigned).
    ///
    /// Skips <paramref name="selfAssemblyName"/> so a previous build of the mod being compiled
    /// is never referenced by the new one.
    /// </summary>
    public static List<string> DiscoverSiblingModAssemblies(string projectDir, string? selfAssemblyName = null)
    {
        var found = new List<string>();
        try
        {
            var modsRoot = Directory.GetParent(Path.GetFullPath(projectDir))?.FullName;
            if (string.IsNullOrEmpty(modsRoot) || !Directory.Exists(modsRoot))
                return found;

            // QudLab's own output: <Mods>\bin\<Name>.dll
            var binDir = Path.Combine(modsRoot, "bin");
            if (Directory.Exists(binDir))
                found.AddRange(Directory.EnumerateFiles(binDir, "*.dll", SearchOption.TopDirectoryOnly));

            // Mods that ship prebuilt assemblies: <Mods>\<Mod>\ModAssemblies\*.dll
            foreach (var dir in Directory.EnumerateDirectories(modsRoot))
            {
                var asmDir = Path.Combine(dir, "ModAssemblies");
                if (Directory.Exists(asmDir))
                    found.AddRange(Directory.EnumerateFiles(asmDir, "*.dll", SearchOption.TopDirectoryOnly));
            }
        }
        catch
        {
            return found;
        }

        if (!string.IsNullOrWhiteSpace(selfAssemblyName))
        {
            found.RemoveAll(p => string.Equals(
                Path.GetFileNameWithoutExtension(p), selfAssemblyName, StringComparison.OrdinalIgnoreCase));
        }

        return found;
    }

    public static void ApplyDiagnosticsToCache(IntelligenceCache cache, CompileResult result)
    {
        cache.Project.Diagnostics = result.Diagnostics.Select(d => d.ToString()).ToList();
        if (result.Success && !string.IsNullOrEmpty(result.OutputPath))
            cache.Project.Diagnostics.Insert(0, $"COMPILE OK → {result.OutputPath} ({result.ReferenceCount} refs)");
        else if (!result.Success)
            cache.Project.Diagnostics.Insert(0, $"COMPILE FAILED ({result.ReferenceCount} refs)");
    }

    static CompileDiagnostic MapDiagnostic(Diagnostic d)
    {
        var span = d.Location.GetLineSpan();
        return new CompileDiagnostic
        {
            Id = d.Id,
            Severity = d.Severity.ToString(),
            Message = d.GetMessage(),
            Path = string.IsNullOrEmpty(span.Path) ? null : span.Path,
            Line = span.StartLinePosition.Line + 1,
            Column = span.StartLinePosition.Character + 1
        };
    }

    static List<MetadataReference> BuildReferences(
        QudReferenceSet refSet,
        IEnumerable<string>? extra,
        out int modReferenceCount)
    {
        var list = new List<MetadataReference>(refSet.AssemblyPaths.Count);
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var path in refSet.AssemblyPaths)
        {
            seen.Add(Path.GetFileNameWithoutExtension(path));
            list.Add(MetadataReference.CreateFromFile(path));
        }

        modReferenceCount = 0;
        if (extra is null)
            return list;

        // Game Managed wins on a simple-name clash: a mod shipping its own copy of
        // 0Harmony/Newtonsoft must not be loaded a second time under a new identity.
        foreach (var path in extra)
        {
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                continue;
            if (!seen.Add(Path.GetFileNameWithoutExtension(path)))
                continue;

            try
            {
                list.Add(MetadataReference.CreateFromFile(path));
                modReferenceCount++;
            }
            catch
            {
                // Unreadable or non-managed DLL — a missing reference is a better
                // failure than aborting the whole compile.
            }
        }

        return list;
    }

    static string SanitizeAsmName(string name)
    {
        var chars = name.Select(c => char.IsLetterOrDigit(c) || c is '.' or '_' ? c : '_').ToArray();
        var s = new string(chars).Trim('_');
        return string.IsNullOrWhiteSpace(s) ? "QudLabMod" : s;
    }
}

public static class ModTemplates
{
    public static string NewPart(string className, string ns = "XRL.World.Parts") =>
        $$"""
        using System;
        using XRL.World;

        namespace {{ns}}
        {
            [Serializable]
            public class {{className}} : IPart
            {
                public override bool WantEvent(int ID, int cascade)
                {
                    return base.WantEvent(ID, cascade);
                }
            }
        }
        """;

    public static string NewMutation(string className) =>
        $$"""
        using System;
        using XRL.World;
        using XRL.World.Parts.Mutation;

        namespace XRL.World.Parts.Mutation
        {
            [Serializable]
            public class {{className}} : BaseMutation
            {
                public override bool WantEvent(int ID, int cascade)
                {
                    return base.WantEvent(ID, cascade);
                }

                public override bool Mutate(GameObject GO, int Level)
                {
                    return base.Mutate(GO, Level);
                }

                public override bool Unmutate(GameObject GO)
                {
                    return base.Unmutate(GO);
                }
            }
        }
        """;

    public static string NewHarmonyPatch(string className, string targetTypeHint = "XRL.World.GameObject") =>
        $$"""
        using System;
        using HarmonyLib;
        using XRL.World;

        namespace QudLab.Patches
        {
            /// <summary>
            /// Harmony patch scaffold. Target type hint: {{targetTypeHint}}
            /// Confirm method signatures via qudlab explain / GET /type before enabling a postfix.
            /// </summary>
            [HarmonyPatch(typeof({{SanitizeTypeOf(targetTypeHint)}}))]
            public static class {{className}}
            {
                // [HarmonyPostfix]
                // [HarmonyPatch(nameof(SomeMethod))]
                // public static void Postfix(/* args */)
                // {
                // }
            }
        }
        """;

    static string SanitizeTypeOf(string hint)
    {
        // typeof() needs an unbound simple name or full name without generics noise for the scaffold.
        var t = hint.Trim();
        var tick = t.IndexOf('`');
        if (tick >= 0)
            t = t[..tick];
        var last = t.LastIndexOf('.');
        return last >= 0 ? t[(last + 1)..] : t;
    }

    public static string SuggestedFileName(string kind, string className) =>
        kind.ToLowerInvariant() switch
        {
            "part" => $"{className}.cs",
            "mutation" => $"{className}.cs",
            "harmony" => $"{className}.cs",
            _ => $"{className}.cs"
        };
}
