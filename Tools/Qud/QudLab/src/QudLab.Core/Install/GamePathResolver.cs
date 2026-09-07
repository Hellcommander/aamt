using System.Text.Json.Serialization;

namespace QudLab.Core.Install;

public enum GameStore
{
    Unknown = 0,
    Steam = 1,
    Gog = 2
}

public sealed class QudInstallInfo
{
    public required string RootPath { get; init; }
    public required GameStore Store { get; init; }
    public string ExePath => Path.Combine(RootPath, "CoQ.exe");
    public string DataPath => Path.Combine(RootPath, "CoQ_Data");
    public string ManagedPath => Path.Combine(DataPath, "Managed");
    public string PluginsPath => Path.Combine(DataPath, "Plugins");
    public string StreamingAssetsPath => Path.Combine(DataPath, "StreamingAssets");
    public string BaseDataPath => Path.Combine(StreamingAssetsPath, "Base");
    public string AssemblyCSharpPath => Path.Combine(ManagedPath, "Assembly-CSharp.dll");
    public string ScriptingAssembliesPath => Path.Combine(DataPath, "ScriptingAssemblies.json");
    public string? DetectedUnityVersion { get; init; }
}

public sealed class GateResult
{
    public bool Ok { get; init; }
    public string Message { get; init; } = "";
    public QudInstallInfo? Install { get; init; }

    public static GateResult Fail(string message) => new() { Ok = false, Message = message };
    public static GateResult Success(QudInstallInfo install, string message = "Caves of Qud install verified.") =>
        new() { Ok = true, Message = message, Install = install };
}

/// <summary>
/// Structural install discovery — no file hashes (branch-friendly).
/// </summary>
public static class GamePathResolver
{
    public static readonly string[] DefaultCandidates =
    {
        @"D:\games\Steam\steamapps\common\Caves of Qud",
        @"E:\SteamLibrary\steamapps\common\Caves of Qud",
        @"C:\Program Files (x86)\Steam\steamapps\common\Caves of Qud",
        @"C:\Program Files\Steam\steamapps\common\Caves of Qud",
        @"C:\GOG Games\Caves of Qud",
        @"D:\GOG Games\Caves of Qud",
        @"E:\GOG Games\Caves of Qud"
    };

    public static QudInstallInfo? TryResolve(string? overridePath = null, IEnumerable<string>? extraCandidates = null)
    {
        var list = new List<string>();
        var env = Environment.GetEnvironmentVariable("QUDLAB_QUD_PATH")
                  ?? Environment.GetEnvironmentVariable("AAMT_QUD_PATH");
        if (!string.IsNullOrWhiteSpace(overridePath))
            list.Add(overridePath.Trim().Trim('"'));
        if (!string.IsNullOrWhiteSpace(env))
            list.Add(env.Trim().Trim('"'));
        if (extraCandidates != null)
            list.AddRange(extraCandidates);
        list.AddRange(DefaultCandidates);

        foreach (var cand in list.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (LooksLikeQud(cand, out var info))
                return info;
        }

        return null;
    }

    public static bool LooksLikeQud(string root, out QudInstallInfo info)
    {
        info = null!;
        if (string.IsNullOrWhiteSpace(root) || !Directory.Exists(root))
            return false;

        var exe = Path.Combine(root, "CoQ.exe");
        var managed = Path.Combine(root, "CoQ_Data", "Managed", "Assembly-CSharp.dll");
        var streaming = Path.Combine(root, "CoQ_Data", "StreamingAssets", "Base");
        if (!File.Exists(exe) || !File.Exists(managed) || !Directory.Exists(streaming))
            return false;

        var store = DetectStore(root);
        string? unity = null;
        var player = Path.Combine(root, "UnityPlayer.dll");
        if (File.Exists(player))
        {
            try
            {
                var vi = System.Diagnostics.FileVersionInfo.GetVersionInfo(player);
                unity = vi.ProductVersion;
            }
            catch
            {
                /* ignore */
            }
        }

        info = new QudInstallInfo
        {
            RootPath = Path.GetFullPath(root),
            Store = store,
            DetectedUnityVersion = unity
        };
        return true;
    }

    static GameStore DetectStore(string root)
    {
        var norm = root.Replace('/', '\\');
        if (norm.Contains(@"steamapps\common", StringComparison.OrdinalIgnoreCase))
            return GameStore.Steam;
        if (norm.Contains("GOG", StringComparison.OrdinalIgnoreCase) ||
            File.Exists(Path.Combine(root, "goggame-*.info".Replace("*", ""))))
            return GameStore.Gog;
        // GOG often leaves galaxy / goggame id files
        if (Directory.GetFiles(root, "goggame-*.info").Length > 0)
            return GameStore.Gog;
        return GameStore.Unknown;
    }
}
