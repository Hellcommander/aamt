using System.Text;
using System.Text.Json;
using QudLab.Core.Cache;
using QudLab.Core.Install;

namespace QudLab.Core.References;

/// <summary>
/// Authoritative Qud Managed assembly lists for IDE / Copilot / Roslyn.
/// Paths always point at the verified install — never copied into the repo.
/// </summary>
public sealed class QudReferenceSet
{
    public required string GameRoot { get; init; }
    public required string ManagedPath { get; init; }
    /// <summary>Full set used by Roslyn compile (Managed-only, no host BCL).</summary>
    public required IReadOnlyList<string> AssemblyPaths { get; init; }
    /// <summary>Curated set for Copilot/OmniSharp — fewer facade conflicts.</summary>
    public required IReadOnlyList<string> IdeEssentialPaths { get; init; }

    public string AssemblyCSharpPath => Path.Combine(ManagedPath, "Assembly-CSharp.dll");
    public string? XmlDocPath
    {
        get
        {
            var p = Path.Combine(ManagedPath, "Assembly-CSharp.xml");
            return File.Exists(p) ? p : null;
        }
    }

    static readonly string[] SkipPrefixes =
    {
        "Microsoft.CodeAnalysis",
        "RoslynCSharp",
        "nunit.framework",
        "Trivial.Mono.Cecil",
        "Trivial.CodeSecurity"
    };

    /// <summary>
    /// Names that matter for mod IntelliSense. Everything else in Managed is still
    /// available to Roslyn via <see cref="AssemblyPaths"/>.
    /// </summary>
    static readonly string[] IdeEssentialNames =
    {
        "mscorlib.dll",
        "netstandard.dll",
        "System.dll",
        "System.Core.dll",
        "System.Xml.dll",
        "System.Xml.Linq.dll",
        "System.Runtime.dll",
        "System.Runtime.Serialization.dll",
        "System.Data.dll",
        "System.Drawing.dll",
        "System.Numerics.dll",
        "System.Configuration.dll",
        "System.Runtime.CompilerServices.Unsafe.dll",
        "System.Threading.Tasks.Extensions.dll",
        "System.Memory.dll",
        "System.Buffers.dll",
        "System.Collections.Immutable.dll",
        "System.Reflection.Metadata.dll",
        "Newtonsoft.Json.dll",
        "0Harmony.dll",
        "Assembly-CSharp.dll",
        "UnityEngine.dll",
        "UnityEngine.CoreModule.dll",
        "UnityEngine.IMGUIModule.dll",
        "UnityEngine.InputLegacyModule.dll",
        "UnityEngine.JSONSerializeModule.dll",
        "UnityEngine.PhysicsModule.dll",
        "UnityEngine.Physics2DModule.dll",
        "UnityEngine.TextRenderingModule.dll",
        "UnityEngine.UI.dll",
        "UnityEngine.UIModule.dll",
        "UnityEngine.UIElementsModule.dll",
        "UnityEngine.SharedInternalsModule.dll",
        "Unity.TextMeshPro.dll",
        "UniTask.dll",
        "UniTask.Linq.dll",
        "ZString.dll",
        "com.rlabrecque.steamworks.net.dll",
        "GalaxyCSharp.dll",
        "NAudio.dll",
        "PlayFab.dll"
    };

    public static QudReferenceSet FromInstall(QudInstallInfo install)
    {
        var all = Directory.EnumerateFiles(install.ManagedPath, "*.dll")
            .Where(p =>
            {
                var name = Path.GetFileName(p);
                return !SkipPrefixes.Any(s => name.StartsWith(s, StringComparison.OrdinalIgnoreCase));
            })
            .OrderBy(p => Path.GetFileName(p), StringComparer.OrdinalIgnoreCase)
            .ToList();

        var essentialWanted = new HashSet<string>(IdeEssentialNames, StringComparer.OrdinalIgnoreCase);
        var essential = all.Where(p => essentialWanted.Contains(Path.GetFileName(p)!)).ToList();

        // Always include remaining UnityEngine.* modules for completeness in IDE
        foreach (var p in all)
        {
            var name = Path.GetFileName(p)!;
            if (name.StartsWith("UnityEngine.", StringComparison.OrdinalIgnoreCase) &&
                !essential.Contains(p))
                essential.Add(p);
        }

        essential = essential
            .OrderBy(p => Path.GetFileName(p), StringComparer.OrdinalIgnoreCase)
            .ToList();

        return new QudReferenceSet
        {
            GameRoot = install.RootPath,
            ManagedPath = install.ManagedPath,
            AssemblyPaths = all,
            IdeEssentialPaths = essential
        };
    }

    public object ToAssistantPayload() => new
    {
        gameRoot = GameRoot,
        managedPath = ManagedPath,
        assemblyCSharp = AssemblyCSharpPath,
        xmlDoc = XmlDocPath,
        count = AssemblyPaths.Count,
        ideEssentialCount = IdeEssentialPaths.Count,
        assemblies = AssemblyPaths.Select(p => new
        {
            fileName = Path.GetFileName(p),
            fullPath = p,
            ideEssential = IdeEssentialPaths.Contains(p)
        }).ToList(),
        ideNote =
            "Open Workspace/QudLab.ModWorkspace.csproj in Cursor so Copilot resolves XRL.* from HintPaths."
    };
}

/// <summary>
/// Writes a mod workspace .csproj that HintPaths Qud Managed DLLs for Copilot.
/// </summary>
public static class IdeProjectSync
{
    public const string DefaultWorkspaceName = "Workspace";

    public static string Sync(QudInstallInfo install, string labRoot, string? workspaceName = null)
    {
        var refs = QudReferenceSet.FromInstall(install);
        var wsName = workspaceName ?? DefaultWorkspaceName;
        var ws = Path.Combine(labRoot, wsName);
        Directory.CreateDirectory(ws);
        Directory.CreateDirectory(Path.Combine(ws, "src"));

        var csprojPath = Path.Combine(ws, "QudLab.ModWorkspace.csproj");
        var propsPath = Path.Combine(ws, "Qud.Install.props");
        var omnisharp = Path.Combine(labRoot, "omnisharp.json");
        var vscodeDir = Path.Combine(labRoot, ".vscode");
        Directory.CreateDirectory(vscodeDir);

        File.WriteAllText(propsPath, BuildProps(refs));
        File.WriteAllText(csprojPath, BuildCsproj());
        WriteIfMissing(Path.Combine(ws, "src", "AssemblyInfo.cs"),
            """
            // Qud Lab mod workspace — references Caves of Qud Managed assemblies from your install.
            // Do not commit game DLLs. HintPaths are generated by: qudlab sync-refs
            using System.Runtime.CompilerServices;

            [assembly: InternalsVisibleTo("QudLab.ModWorkspace.Tests")]
            """);

        File.WriteAllText(Path.Combine(ws, "README.md"),
            """
            # QudLab Mod Workspace

            This project references **your** Caves of Qud `CoQ_Data/Managed` assemblies via HintPath.
            Open `QudLab.ModWorkspace.csproj` in Cursor / VS so Copilot has real `XRL.*` types.

            ```
            Sync-Refs.bat
            ```

            ThreadingAPI is a separate WIP mod — not referenced here unless you add it yourself.
            """);

        File.WriteAllText(omnisharp,
            """
            {
              "MSBuild": {
                "LoadProjectsOnDemand": false
              },
              "RoslynExtensionsOptions": {
                "EnableAnalyzersSupport": true
              }
            }
            """);

        File.WriteAllText(Path.Combine(vscodeDir, "settings.json"),
            $$"""
            {
              "dotnet.defaultSolution": "QudLab.code-workspace",
              "omnisharp.enableRoslynAnalyzers": true,
              "files.exclude": {
                "**/artifacts": true
              },
              "dotnet.preferCSharpExtension": true
            }
            """);

        // Multi-root workspace: Lab tools + mod workspace project for Copilot
        File.WriteAllText(Path.Combine(labRoot, "QudLab.code-workspace"),
            """
            {
              "folders": [
                { "name": "QudLab", "path": "." },
                { "name": "ModWorkspace (Copilot refs)", "path": "Workspace" }
              ],
              "settings": {
                "dotnet.defaultSolution": "Workspace/QudLab.ModWorkspace.csproj",
                "files.exclude": { "**/artifacts": true }
              }
            }
            """);

        var manifestPath = Path.Combine(CacheIO.DefaultCacheDir(), "assembly-refs.json");
        File.WriteAllText(manifestPath, JsonSerializer.Serialize(refs.ToAssistantPayload(), CacheIO.JsonOptions));
        File.WriteAllText(Path.Combine(ws, "assembly-refs.json"),
            JsonSerializer.Serialize(refs.ToAssistantPayload(), CacheIO.JsonOptions));

        return csprojPath;
    }

    static void WriteIfMissing(string path, string content)
    {
        if (!File.Exists(path))
            File.WriteAllText(path, content);
    }

    static string BuildProps(QudReferenceSet refs)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<Project>");
        sb.AppendLine("  <PropertyGroup>");
        sb.AppendLine($"    <QudGameRoot>{Escape(refs.GameRoot)}</QudGameRoot>");
        sb.AppendLine($"    <QudManagedDir>{Escape(refs.ManagedPath)}</QudManagedDir>");
        sb.AppendLine("    <TargetFramework>net48</TargetFramework>");
        sb.AppendLine("    <LangVersion>9.0</LangVersion>");
        sb.AppendLine("    <Nullable>disable</Nullable>");
        sb.AppendLine("    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>");
        sb.AppendLine("    <DisableImplicitFrameworkReferences>true</DisableImplicitFrameworkReferences>");
        sb.AppendLine("    <DisableImplicitNamespaceImports>true</DisableImplicitNamespaceImports>");
        sb.AppendLine("    <GenerateDocumentationFile>false</GenerateDocumentationFile>");
        sb.AppendLine("    <NoWarn>CS1591;CS0618;CS8021;MSB3277</NoWarn>");
        sb.AppendLine("    <DefineConstants>QUD;QUDLAB_WORKSPACE</DefineConstants>");
        sb.AppendLine("    <AutomaticallyUseReferenceAssemblyPackages>false</AutomaticallyUseReferenceAssemblyPackages>");
        sb.AppendLine("    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>");
        sb.AppendLine("  </PropertyGroup>");
        sb.AppendLine("  <ItemGroup>");
        // Copilot gets curated essentials (+ all UnityEngine.*) to cut facade noise
        foreach (var dll in refs.IdeEssentialPaths)
        {
            var name = Path.GetFileNameWithoutExtension(dll);
            var xml = Path.ChangeExtension(dll, ".xml");
            sb.AppendLine($"    <Reference Include=\"{Escape(name)}\">");
            sb.AppendLine($"      <HintPath>{Escape(dll)}</HintPath>");
            sb.AppendLine("      <Private>false</Private>");
            sb.AppendLine("      <SpecificVersion>false</SpecificVersion>");
            if (File.Exists(xml))
                sb.AppendLine($"      <Documentation>{Escape(xml)}</Documentation>");
            sb.AppendLine("    </Reference>");
        }
        sb.AppendLine("  </ItemGroup>");
        sb.AppendLine("</Project>");
        return sb.ToString();
    }

    static string BuildCsproj() =>
        """
        <Project Sdk="Microsoft.NET.Sdk">
          <Import Project="Qud.Install.props" />
          <PropertyGroup>
            <OutputType>Library</OutputType>
            <AssemblyName>QudLab.ModWorkspace</AssemblyName>
            <RootNamespace>XRL</RootNamespace>
            <EnableDefaultCompileItems>true</EnableDefaultCompileItems>
          </PropertyGroup>
        </Project>
        """;

    static string Escape(string path) =>
        path.Replace("&", "&amp;").Replace("\"", "&quot;");
}
