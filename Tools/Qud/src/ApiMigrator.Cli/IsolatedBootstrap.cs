using System.Diagnostics;
using ApiMigrator.Core;

namespace ApiMigrator.Cli;

/// <summary>
/// Relays this process through a shadow copy of the CLI output folder so
/// <c>ApiMigrator.Core.dll</c> is loaded from an isolated instance, not the shared
/// <c>bin\Release</c> path. Concurrent PS1 / GUI / <c>dotnet run</c> sessions can then
/// still read or rebuild the original output instead of failing with a file lock.
/// </summary>
internal static class IsolatedBootstrap
{
    public const string IsolatedEnvVar = "COQ_APIMIGRATOR_ISOLATED";
    public const string ToolsRootEnvVar = "COQ_TOOLS_ROOT";
    public const string NoIsolateEnvVar = "COQ_APIMIGRATOR_NO_ISOLATE";

    public static bool ShouldRelaunch()
    {
        if (string.Equals(Environment.GetEnvironmentVariable(NoIsolateEnvVar), "1", StringComparison.Ordinal))
            return false;
        if (string.Equals(Environment.GetEnvironmentVariable(IsolatedEnvVar), "1", StringComparison.Ordinal))
            return false;
        return true;
    }

    public static int Execute(string[] args, Func<string[], int> run)
    {
        if (!ShouldRelaunch())
            return run(args);

        try
        {
            return Relaunch(args);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(
                "Isolated ApiMigrator instance failed (" + ex.Message + "); running in-place.");
            return run(args);
        }
    }

    public static int Relaunch(string[] args)
    {
        var src = AppContext.BaseDirectory;
        var dest = Path.Combine(
            IsolatedRoot(),
            "cli-" + Environment.ProcessId + "-" + Guid.NewGuid().ToString("n"));

        SweepStaleIsolatedDirs();
        CopyDirectoryWithRetry(src, dest);

        var toolsRoot = FindToolsRoot();
        var exe = Path.Combine(dest, "ApiMigrator.Cli.exe");
        var dll = Path.Combine(dest, "ApiMigrator.Cli.dll");

        using var proc = StartIsolated(exe, dll, args, toolsRoot);
        proc.WaitForExit();
        // Leave dest for SweepStaleIsolatedDirs — immediate delete races the child's
        // still-mapped DLLs and Windows Defender on a brand-new folder.

        return proc.ExitCode;
    }

    static Process StartIsolated(string exe, string dll, string[] args, string toolsRoot)
    {
        Exception? last = null;
        foreach (var psi in BuildStartInfos(exe, dll, args, toolsRoot))
        {
            try
            {
                var proc = Process.Start(psi);
                if (proc is not null)
                    return proc;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or System.ComponentModel.Win32Exception)
            {
                last = ex;
            }
        }

        throw last ?? new InvalidOperationException("Failed to start isolated ApiMigrator.Cli");
    }

    static IEnumerable<ProcessStartInfo> BuildStartInfos(string exe, string dll, string[] args, string toolsRoot)
    {
        if (File.Exists(exe))
            yield return MakeStartInfo(new ProcessStartInfo(exe), args, toolsRoot);
        if (File.Exists(dll))
        {
            var dotnet = new ProcessStartInfo("dotnet");
            dotnet.ArgumentList.Add("exec");
            dotnet.ArgumentList.Add(dll);
            yield return MakeStartInfo(dotnet, args, toolsRoot);
        }
    }

    static ProcessStartInfo MakeStartInfo(ProcessStartInfo psi, string[] args, string toolsRoot)
    {
        foreach (var arg in args)
            psi.ArgumentList.Add(arg);
        psi.UseShellExecute = false;
        psi.WorkingDirectory = Directory.GetCurrentDirectory();
        psi.Environment[IsolatedEnvVar] = "1";
        psi.Environment[ToolsRootEnvVar] = toolsRoot;
        return psi;
    }

    static string IsolatedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (string.Equals(dir.Name, "bin", StringComparison.OrdinalIgnoreCase))
                return Path.Combine(dir.FullName, "isolated");
            dir = dir.Parent;
        }

        return Path.Combine(AppContext.BaseDirectory, "isolated");
    }

    public static string FindToolsRoot() => CoqPaths.FindToolsRoot();

    public static string RequireValue(string[] a, ref int i, string flag)
    {
        if (i + 1 >= a.Length || a[i + 1].StartsWith("--", StringComparison.Ordinal))
            throw new ArgumentException(flag + " requires a value");
        return a[++i];
    }

    public static bool IsPathFlag(string token) =>
        token.Equals("--path", StringComparison.OrdinalIgnoreCase)
        || token.StartsWith("--path=", StringComparison.OrdinalIgnoreCase);

    public static void RejectUnknown(string token)
    {
        if (token.StartsWith("--", StringComparison.Ordinal))
            throw new ArgumentException("Unknown option: " + token);
        throw new ArgumentException("Unexpected argument: " + token);
    }

    /// <summary>
    /// Consumes <c>--path dir1 dir2</c> or <c>--path=dir</c>. Returns the index of the last
    /// argv token eaten so the caller's <c>for (i++)</c> lands on the next flag.
    /// </summary>
    public static int ConsumePathArgs(string[] a, int i, List<string> paths)
    {
        if (i < 0 || i >= a.Length)
            return i;

        var token = a[i];
        if (token.StartsWith("--path=", StringComparison.OrdinalIgnoreCase))
        {
            AddPathToken(paths, token["--path=".Length..]);
            return i;
        }

        i++;
        var added = 0;
        while (i < a.Length && !IsOption(a[i]))
        {
            AddPathToken(paths, a[i]);
            added++;
            i++;
        }

        if (added == 0)
            throw new ArgumentException("migrate --path requires at least one directory");

        return i - 1;
    }

    static void AddPathToken(List<string> paths, string token)
    {
        if (string.IsNullOrWhiteSpace(token))
            return;
        paths.Add(token.Trim().Trim('"'));
    }

    static bool IsOption(string s) =>
        s.StartsWith("--", StringComparison.Ordinal);

    static readonly string[] IsolatedFileNames =
    {
        "ApiMigrator.Cli.exe",
        "ApiMigrator.Cli.dll",
        "ApiMigrator.Cli.deps.json",
        "ApiMigrator.Cli.runtimeconfig.json",
        "ApiMigrator.Cli.pdb",
        "ApiMigrator.Core.dll",
        "ApiMigrator.Core.deps.json",
        "ApiMigrator.Core.pdb",
    };

    static void CopyDirectoryWithRetry(string src, string dest, int attempts = 20)
    {
        Directory.CreateDirectory(dest);
        Exception? last = null;
        for (var n = 0; n < attempts; n++)
        {
            try
            {
                foreach (var name in IsolatedFileNames)
                {
                    var file = Path.Combine(src, name);
                    if (!File.Exists(file))
                        continue;
                    var destFile = Path.Combine(dest, name);
                    using var input = new FileStream(
                        file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                    using var output = new FileStream(
                        destFile, FileMode.Create, FileAccess.Write, FileShare.Read);
                    input.CopyTo(output);
                }

                if (!File.Exists(Path.Combine(dest, "ApiMigrator.Cli.dll")) &&
                    !File.Exists(Path.Combine(dest, "ApiMigrator.Cli.exe")))
                {
                    throw new FileNotFoundException("Isolated copy is missing ApiMigrator.Cli.exe / .dll", dest);
                }

                return;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                last = ex;
                Thread.Sleep(50 * (n + 1));
            }
        }

        throw last ?? new IOException("Could not copy ApiMigrator.Cli to an isolated instance.");
    }

    static void SweepStaleIsolatedDirs()
    {
        var cutoff = DateTime.UtcNow.AddHours(-6);
        foreach (var root in new[]
                 {
                     IsolatedRoot(),
                     Path.Combine(Path.GetTempPath(), "CoQ.ApiMigrator"),
                 })
        {
            try
            {
                if (!Directory.Exists(root))
                    continue;
                foreach (var dir in Directory.GetDirectories(root, "cli-*"))
                {
                    try
                    {
                        if (Directory.GetCreationTimeUtc(dir) < cutoff)
                            Directory.Delete(dir, recursive: true);
                    }
                    catch
                    {
                        /* still in use */
                    }
                }
            }
            catch
            {
                /* best-effort */
            }
        }
    }
}
