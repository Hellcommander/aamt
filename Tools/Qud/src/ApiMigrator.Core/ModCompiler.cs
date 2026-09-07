using System.Diagnostics;
using System.Text;

namespace ApiMigrator.Core;

/// <summary>
/// Compiles a mod's .cs files against the game's Managed folder (read-only) and returns the
/// raw compiler stdout/stderr so <see cref="Cs0618Parser"/> can harvest obsolete warnings.
/// Does not require launching the game — a single-mod compile is seconds, not minutes.
/// </summary>
public static class ModCompiler
{
    public sealed class CompileResult
    {
        public int ExitCode { get; set; }
        public string Output { get; set; } = "";
        public string ProjectPath { get; set; } = "";
        public List<string> SourceFiles { get; set; } = new();
        public List<string> Notes { get; set; } = new();
    }

    /// <summary>
    /// Builds a throwaway netstandard2.1 project referencing Managed DLLs and compiling every
    /// .cs under <paramref name="modFolder"/> (excluding bin/obj/_tools). Managed is never written.
    /// </summary>
    public static CompileResult CompileAgainstManaged(
        string modFolder,
        string managedDir,
        Action<string>? onLog = null,
        IEnumerable<string>? excludeDirNames = null)
    {
        if (!Directory.Exists(modFolder))
            throw new DirectoryNotFoundException("Mod folder not found: " + modFolder);
        if (!Directory.Exists(managedDir))
            throw new DirectoryNotFoundException("Managed folder not found: " + managedDir);

        var excludes = new HashSet<string>(
            excludeDirNames ?? new[] { "bin", "obj", ".git", ".vs", "_tools", "_decompile", "_decompile_il", "scratch" },
            StringComparer.OrdinalIgnoreCase);

        var sources = Directory.EnumerateFiles(modFolder, "*.cs", SearchOption.AllDirectories)
            .Where(f =>
            {
                var rel = Path.GetRelativePath(modFolder, f);
                var parts = rel.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                return !parts.Any(p => excludes.Contains(p));
            })
            .OrderBy(f => f, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var result = new CompileResult { SourceFiles = sources };
        if (sources.Count == 0)
        {
            result.Notes.Add("No .cs files found under " + modFolder);
            result.ExitCode = 1;
            return result;
        }

        var work = Path.Combine(Path.GetTempPath(), "CoQ_Cs0618_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(work);
        var projPath = Path.Combine(work, "ModCompile.csproj");
        result.ProjectPath = projPath;

        try
        {
            WriteProject(projPath, sources, managedDir);
            onLog?.Invoke($"Compiling {sources.Count} file(s) against Managed...");

            var psi = new ProcessStartInfo
            {
                FileName = "dotnet",
                Arguments = $"build \"{projPath}\" -c Release -v:q --nologo",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = work,
            };

            using var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Failed to start `dotnet`.");
            var stdoutTask = proc.StandardOutput.ReadToEndAsync();
            var stderrTask = proc.StandardError.ReadToEndAsync();
            if (!proc.WaitForExit(180_000))
            {
                try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
                result.Notes.Add("Compile timed out after 180s.");
                result.ExitCode = -1;
                result.Output = DrainPipes(stdoutTask, stderrTask);
                return result;
            }

            result.ExitCode = proc.ExitCode;
            result.Output = DrainPipes(stdoutTask, stderrTask);
            if (proc.ExitCode != 0)
            {
                result.Notes.Add(
                    "Compile exited non-zero (often expected: missing Unity/mod-only refs). " +
                    "CS0618 lines in the output are still usable when present.");
            }
        }
        finally
        {
            try
            {
                if (Directory.Exists(work))
                    Directory.Delete(work, recursive: true);
            }
            catch
            {
                result.Notes.Add("Could not delete temp project folder: " + work);
            }
        }

        return result;
    }

    private static void WriteProject(string projPath, List<string> sources, string managedDir)
    {
        var sb = new StringBuilder();
        sb.AppendLine("""
            <Project Sdk="Microsoft.NET.Sdk">
              <PropertyGroup>
                <TargetFramework>netstandard2.1</TargetFramework>
                <LangVersion>latest</LangVersion>
                <Nullable>disable</Nullable>
                <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
                <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
                <GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute>
                <NoWarn>CS1701;CS1702;CS1705;CS8019</NoWarn>
                <WarningLevel>4</WarningLevel>
                <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
              </PropertyGroup>
              <ItemGroup>
            """);

        foreach (var src in sources)
        {
            var escaped = XmlEscape(src);
            sb.Append("    <Compile Include=\"").Append(escaped).AppendLine("\" />");
        }

        sb.AppendLine("  </ItemGroup>");
        sb.AppendLine("  <ItemGroup>");

        foreach (var dll in Directory.EnumerateFiles(managedDir, "*.dll")
                     .OrderBy(f => f, StringComparer.OrdinalIgnoreCase))
        {
            var name = Path.GetFileNameWithoutExtension(dll);
            if (name.StartsWith("api-ms-", StringComparison.OrdinalIgnoreCase)) continue;
            if (name.Equals("UnityPlayer", StringComparison.OrdinalIgnoreCase)) continue;

            var hint = XmlEscape(dll);
            sb.Append("    <Reference Include=\"").Append(name).Append("\">")
              .Append("<HintPath>").Append(hint).Append("</HintPath>")
              .Append("<Private>false</Private>")
              .AppendLine("</Reference>");
        }

        sb.AppendLine("""
              </ItemGroup>
            </Project>
            """);

        File.WriteAllText(projPath, sb.ToString());
    }

    static string DrainPipes(Task<string> stdoutTask, Task<string> stderrTask)
    {
        var stdout = "";
        var stderr = "";
        try { stdout = stdoutTask.GetAwaiter().GetResult(); } catch { /* killed */ }
        try { stderr = stderrTask.GetAwaiter().GetResult(); } catch { /* killed */ }
        return stdout + Environment.NewLine + stderr;
    }

    static string XmlEscape(string s) =>
        s.Replace("&", "&amp;", StringComparison.Ordinal)
            .Replace("\"", "&quot;", StringComparison.Ordinal)
            .Replace("<", "&lt;", StringComparison.Ordinal);
}
