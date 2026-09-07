using System.Runtime.Versioning;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace ApiMigrator.Core;

/// <summary>
/// Locates the live Caves of Qud Steam library (Managed + Workshop) by autodetection —
/// Steam registry → <c>libraryfolders.vdf</c> → common fallback roots — not a hardcoded drive.
/// Compile / Player.log paths are often truncated to
/// <c>steamapps/workshop/content/333640/&lt;id&gt;/File.cs</c> — resolve those against
/// <see cref="WorkshopContentDir"/>, not a stale second library.
/// </summary>
public static class SteamInstall
{
    public const string AppId = "333640";
    public const string GameFolderName = "Caves of Qud";

    /// <summary>
    /// Last-resort roots when registry / VDF discovery finds nothing. Order is not a preference
    /// for which install “wins” — <see cref="Discover"/> picks by live DLL + workshop presence.
    /// </summary>
    public static readonly string[] FallbackLibraryRoots =
    {
        @"D:\games\Steam",
        @"E:\SteamLibrary",
        @"F:\SteamLibrary",
        @"G:\SteamLibrary",
        @"H:\SteamLibrary",
        @"C:\Program Files (x86)\Steam",
        @"C:\Program Files\Steam",
    };

    /// <summary>Alias of <see cref="FallbackLibraryRoots"/> (compat).</summary>
    public static readonly string[] PreferredLibraryRoots = FallbackLibraryRoots;

    static readonly Regex WorkshopMarker = new(
        @"steamapps[/\\]workshop[/\\]content[/\\]333640[/\\]",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Compiled);

    static readonly Regex GameMarker = new(
        @"steamapps[/\\]common[/\\]Caves of Qud[/\\]",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Compiled);

    static readonly Lazy<Resolved> Cached = new(Discover);

    public static string? LibraryRoot => Cached.Value.LibraryRoot;
    public static string? GameInstallDir => Cached.Value.GameInstallDir;
    public static string? ManagedDir => Cached.Value.ManagedDir;
    public static string? WorkshopContentDir => Cached.Value.WorkshopContentDir;
    public static string? StreamingAssetsBase =>
        GameInstallDir is null ? null : Path.Combine(GameInstallDir, "CoQ_Data", "StreamingAssets", "Base");
    public static string? StreamingAssetsDlc =>
        GameInstallDir is null ? null : Path.Combine(GameInstallDir, "CoQ_Data", "StreamingAssets", "DLC");

    public static string ManagedDirOrFallback =>
        ManagedDir
        ?? Path.Combine(
            LibraryRoot ?? FallbackLibraryRoots[0],
            "steamapps", "common", GameFolderName, "CoQ_Data", "Managed");

    public static string WorkshopContentDirOrFallback =>
        WorkshopContentDir
        ?? Path.Combine(
            LibraryRoot ?? FallbackLibraryRoots[0],
            "steamapps", "workshop", "content", AppId);

    /// <summary>
    /// Turn a compiler / Player.log path (full, truncated, or <c>&lt;...&gt;/steamapps/...</c>)
    /// into a real file under the live Steam library when possible.
    /// </summary>
    public static string? ResolveLoggedPath(string? loggedPath)
    {
        if (string.IsNullOrWhiteSpace(loggedPath)) return null;
        var p = loggedPath.Trim().Replace('/', '\\');
        if (p.StartsWith("<...>", StringComparison.Ordinal))
            p = p[5..].TrimStart('\\', '/');

        if (File.Exists(loggedPath.Trim()) || Directory.Exists(loggedPath.Trim()))
            return Path.GetFullPath(loggedPath.Trim());
        if (File.Exists(p) || Directory.Exists(p))
            return Path.GetFullPath(p);

        var wm = WorkshopMarker.Match(p);
        if (wm.Success && WorkshopContentDir is not null)
        {
            var rel = p[(wm.Index + wm.Length)..].TrimStart('\\', '/');
            var combined = string.IsNullOrEmpty(rel)
                ? WorkshopContentDir
                : Path.Combine(WorkshopContentDir, rel);
            if (File.Exists(combined) || Directory.Exists(combined))
                return Path.GetFullPath(combined);
        }

        var gm = GameMarker.Match(p);
        if (gm.Success && GameInstallDir is not null)
        {
            var rel = p[(gm.Index + gm.Length)..].TrimStart('\\', '/');
            var combined = string.IsNullOrEmpty(rel)
                ? GameInstallDir
                : Path.Combine(GameInstallDir, rel);
            if (File.Exists(combined) || Directory.Exists(combined))
                return Path.GetFullPath(combined);
        }

        return null;
    }

    /// <summary>
    /// Candidate Steam library roots: registry Steam + all <c>libraryfolders.vdf</c> paths,
    /// then <see cref="FallbackLibraryRoots"/>. Deduped, registry-first.
    /// </summary>
    public static IReadOnlyList<string> CandidateLibraryRoots()
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var list = new List<string>();

        void Add(string? root)
        {
            if (string.IsNullOrWhiteSpace(root)) return;
            var full = NormalizeRoot(root);
            if (full.Length == 0 || !seen.Add(full)) return;
            list.Add(full);
        }

        foreach (var steam in ReadSteamClientRootsFromRegistry())
            Add(steam);

        // Expand every known Steam client via libraryfolders.vdf before fallbacks.
        foreach (var r in list.ToList())
        {
            foreach (var fromVdf in ParseLibraryFolders(r))
                Add(fromVdf);
        }

        foreach (var r in FallbackLibraryRoots)
            Add(r);

        // Fallbacks may themselves be Steam clients with more libraries.
        foreach (var r in list.ToList())
        {
            foreach (var fromVdf in ParseLibraryFolders(r))
                Add(fromVdf);
        }

        return list;
    }

    internal static Resolved Discover()
    {
        var candidates = CandidateLibraryRoots();
        var withGame = new List<(string Root, string GameDir, string Managed, DateTime DllWrite, bool HasWorkshop)>();
        foreach (var root in candidates)
        {
            var gameDir = Path.Combine(root, "steamapps", "common", GameFolderName);
            var dll = Path.Combine(gameDir, "CoQ_Data", "Managed", "Assembly-CSharp.dll");
            if (!File.Exists(dll)) continue;
            var ws = Path.Combine(root, "steamapps", "workshop", "content", AppId);
            DateTime write;
            try { write = File.GetLastWriteTimeUtc(dll); }
            catch { write = DateTime.MinValue; }
            withGame.Add((root, gameDir, Path.GetDirectoryName(dll)!, write, Directory.Exists(ws)));
        }

        (string Root, string GameDir, string Managed, DateTime DllWrite, bool HasWorkshop)? pick = null;
        if (withGame.Count > 0)
        {
            // Live install = newest Assembly-CSharp among libraries that also host workshop
            // content when possible; otherwise newest DLL. Never hardcode a drive letter win.
            var pool = withGame.Any(g => g.HasWorkshop)
                ? withGame.Where(g => g.HasWorkshop).ToList()
                : withGame;
            pick = pool.OrderByDescending(g => g.DllWrite).First();
        }

        string? workshop = null;
        if (pick is not null)
        {
            var nextToGame = Path.Combine(pick.Value.Root, "steamapps", "workshop", "content", AppId);
            if (Directory.Exists(nextToGame))
                workshop = nextToGame;
        }

        if (workshop is null)
        {
            (string Path, DateTime Stamp)? best = null;
            foreach (var root in candidates)
            {
                var ws = Path.Combine(root, "steamapps", "workshop", "content", AppId);
                if (!Directory.Exists(ws)) continue;
                DateTime stamp;
                try { stamp = Directory.GetLastWriteTimeUtc(ws); }
                catch { stamp = DateTime.MinValue; }
                if (best is null || stamp > best.Value.Stamp)
                    best = (ws, stamp);
            }
            workshop = best?.Path;
        }

        return new Resolved
        {
            LibraryRoot = pick?.Root,
            GameInstallDir = pick?.GameDir,
            ManagedDir = pick?.Managed,
            WorkshopContentDir = workshop,
        };
    }

    static IEnumerable<string> ReadSteamClientRootsFromRegistry()
    {
        if (!OperatingSystem.IsWindows())
            yield break;

        foreach (var path in TryRegSteamPathsWindows())
            yield return path;
    }

    [SupportedOSPlatform("windows")]
    static IEnumerable<string> TryRegSteamPathsWindows()
    {
        string?[] keys =
        {
            TryRegValue(RegistryHive.CurrentUser, @"Software\Valve\Steam", "SteamPath"),
            TryRegValue(RegistryHive.LocalMachine, @"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            TryRegValue(RegistryHive.LocalMachine, @"SOFTWARE\Valve\Steam", "InstallPath"),
        };
        foreach (var p in keys)
        {
            if (!string.IsNullOrWhiteSpace(p))
                yield return p!;
        }
    }

    [SupportedOSPlatform("windows")]
    static string? TryRegValue(RegistryHive hive, string subKey, string name)
    {
#pragma warning disable CA1416 // Called only after OperatingSystem.IsWindows()
        try
        {
            using var baseKey = RegistryKey.OpenBaseKey(hive, RegistryView.Registry64);
            using var key = baseKey.OpenSubKey(subKey);
            var v = key?.GetValue(name) as string;
            if (!string.IsNullOrWhiteSpace(v))
                return v.Replace('/', '\\');
        }
        catch { /* ignore */ }

        try
        {
            using var baseKey = RegistryKey.OpenBaseKey(hive, RegistryView.Registry32);
            using var key = baseKey.OpenSubKey(subKey);
            var v = key?.GetValue(name) as string;
            if (!string.IsNullOrWhiteSpace(v))
                return v.Replace('/', '\\');
        }
        catch { /* ignore */ }
#pragma warning restore CA1416

        return null;
    }

    static IEnumerable<string> ParseLibraryFolders(string steamRoot)
    {
        var vdFs = new[]
        {
            Path.Combine(steamRoot, "steamapps", "libraryfolders.vdf"),
            Path.Combine(steamRoot, "config", "libraryfolders.vdf"),
        };
        foreach (var vdf in vdFs)
        {
            if (!File.Exists(vdf)) continue;
            string text;
            try { text = File.ReadAllText(vdf); }
            catch { continue; }

            foreach (Match m in Regex.Matches(text, "\"path\"\\s+\"([^\"]+)\""))
            {
                var path = m.Groups[1].Value.Replace(@"\\", @"\");
                if (!string.IsNullOrWhiteSpace(path))
                    yield return path;
            }
        }
    }

    static string NormalizeRoot(string root)
    {
        try
        {
            var full = Path.GetFullPath(root.Trim().TrimEnd('\\', '/'));
            return full.TrimEnd('\\', '/');
        }
        catch
        {
            return root.Trim().TrimEnd('\\', '/');
        }
    }

    internal readonly struct Resolved
    {
        public string? LibraryRoot { get; init; }
        public string? GameInstallDir { get; init; }
        public string? ManagedDir { get; init; }
        public string? WorkshopContentDir { get; init; }
    }
}
