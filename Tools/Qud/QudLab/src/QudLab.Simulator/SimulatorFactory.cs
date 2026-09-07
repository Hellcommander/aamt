using System.Reflection;
using QudLab.Core;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;

namespace QudLab.Simulator;

/// <summary>
/// MIT loader for the access-gated simulator. Public clones get <see cref="RestrictedSimulator"/>
/// stubs. Granted users drop portable <c>net8.0</c> DLLs (Windows / Linux / macOS IL — not a
/// Windows-only native build) via <c>Fetch-PrivatePack.ps1</c>.
/// </summary>
public static class SimulatorFactory
{
    public const string SimulatorPrivateDll = "QudLab.Simulator.Private.dll";
    public const string SimHostPrivateDll = "QudLab.SimHost.Private.dll";

    static readonly object Gate = new();
    static Assembly? _simAsm;
    static bool _simLoadAttempted;

    public static bool PrivatePackPresent => TryFindDll(SimulatorPrivateDll) is not null;

    public static IRestrictedSimulator Create(
        LabHost host,
        IThreadActionSink? threads = null,
        Func<IntelligenceCache?>? cacheProvider = null)
    {
        var asm = LoadSimulatorPrivate();
        if (asm is not null)
        {
            var type = asm.GetType("QudLab.Simulator.RestrictedSimulator");
            if (type is not null)
            {
                var inst = Activator.CreateInstance(type, host, threads, cacheProvider);
                if (inst is IRestrictedSimulator sim)
                    return sim;
            }
        }

        return new RestrictedSimulator(host, threads, cacheProvider);
    }

    public static IReadOnlyList<SimScenarioInfo> GetScenarios()
    {
        var asm = LoadSimulatorPrivate();
        var type = asm?.GetType("QudLab.Simulator.SimScenarioCatalog");
        var prop = type?.GetProperty("All", BindingFlags.Public | BindingFlags.Static);
        if (prop?.GetValue(null) is not System.Collections.IEnumerable raw)
            return SimScenarioCatalog.Fallback;

        var list = new List<SimScenarioInfo>();
        foreach (var item in raw)
        {
            if (item is null) continue;
            var t = item.GetType();
            list.Add(new SimScenarioInfo
            {
                Id = t.GetProperty("Id")?.GetValue(item) as string ?? "",
                Label = t.GetProperty("Label")?.GetValue(item) as string ?? "",
                Description = t.GetProperty("Description")?.GetValue(item) as string ?? "",
                SupportsStress = t.GetProperty("SupportsStress")?.GetValue(item) as bool? ?? false
            });
        }

        return list.Count > 0 ? list : SimScenarioCatalog.Fallback;
    }

    /// <summary>Invoke the private SimHost entry point when the pack DLL is present.</summary>
    public static async Task<int> RunSimHostAsync(string[] args)
    {
        var path = TryFindDll(SimHostPrivateDll);
        if (path is null)
        {
            Console.Error.WriteLine(
                "QudLab SimHost private pack is not installed (QudLab.SimHost.Private.dll).");
            Console.Error.WriteLine(
                "Unpack it with Tools/Qud/QudLab/Fetch-PrivatePack.ps1. Portable net8.0 — needs the .NET 8 runtime.");
            return 2;
        }

        var asm = Assembly.LoadFrom(path);
        var type = asm.GetType("QudLab.SimHost.Program")
                   ?? asm.GetType("QudLab.SimHost.HostEntry");
        var main = type?.GetMethod("Main", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        if (main is null)
        {
            Console.Error.WriteLine("Private SimHost DLL has no Program.Main / HostEntry.Main.");
            return 2;
        }

        var result = main.GetParameters().Length == 0
            ? main.Invoke(null, null)
            : main.Invoke(null, new object[] { args });

        switch (result)
        {
            case Task<int> ti:
                return await ti.ConfigureAwait(false);
            case Task t:
                await t.ConfigureAwait(false);
                return 0;
            case int i:
                return i;
            default:
                return 0;
        }
    }

    static Assembly? LoadSimulatorPrivate()
    {
        lock (Gate)
        {
            if (_simLoadAttempted)
                return _simAsm;
            _simLoadAttempted = true;
            var path = TryFindDll(SimulatorPrivateDll);
            if (path is null)
                return null;
            try
            {
                _simAsm = Assembly.LoadFrom(path);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Failed to load {SimulatorPrivateDll}: {ex.Message}");
            }

            return _simAsm;
        }
    }

    public static string? TryFindDll(string fileName)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var dir in CandidateDirs())
        {
            if (string.IsNullOrWhiteSpace(dir) || !seen.Add(dir))
                continue;
            var path = Path.Combine(dir, fileName);
            if (File.Exists(path))
                return Path.GetFullPath(path);
        }

        return null;
    }

    static IEnumerable<string> CandidateDirs()
    {
        var env = Environment.GetEnvironmentVariable("QUDLAB_PRIVATE_PACK");
        if (!string.IsNullOrWhiteSpace(env))
            yield return env;

        yield return AppContext.BaseDirectory;

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 8 && dir is not null; i++, dir = dir.Parent)
        {
            yield return Path.Combine(dir.FullName, "pack", "private");
            yield return Path.Combine(dir.FullName, "artifacts", "bin", "QudLab.Simulator.Private", "Release", "net8.0");
            yield return Path.Combine(dir.FullName, "artifacts", "bin", "QudLab.Simulator.Private", "Debug", "net8.0");
            yield return Path.Combine(dir.FullName, "artifacts", "bin", "QudLab.SimHost.Private", "Release", "net8.0");
            yield return Path.Combine(dir.FullName, "artifacts", "bin", "QudLab.SimHost.Private", "Debug", "net8.0");
        }
    }
}
