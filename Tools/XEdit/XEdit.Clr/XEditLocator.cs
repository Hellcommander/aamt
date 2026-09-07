using System.Diagnostics;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace XEdit.Clr;

public sealed class XEditInstall
{
    public required string ExePath { get; init; }
    public XEditGame Game { get; init; }
    public XEditVersion Version { get; init; }
    public bool IsDumpTool { get; init; }
    public bool MeetsMinStarfield { get; init; }
    public string? Warning { get; init; }
    public string? GameDataPath { get; init; }

    [JsonIgnore] public string Directory => Path.GetDirectoryName(ExePath) ?? "";
}

public static class XEditLocator
{
    static readonly string[] ExeNames =
    [
        "xEdit64.exe", "xEdit.exe",
        "SF1Edit64.exe", "SF1Edit.exe",
        "SF1Dump64.exe", "SF1Dump.exe",
        "xDump64.exe", "xDump.exe",
        "TES5Edit64.exe", "TES5Edit.exe",
        "SSEEdit64.exe", "SSEEdit.exe",
        "FO4Edit64.exe", "FO4Edit.exe"
    ];

    public static XEditInstall? Locate(XEditGame game = XEditGame.SF1)
    {
        var candidates = EnumerateCandidates(game)
            .Select(Describe)
            .Where(x => x is not null)
            .Cast<XEditInstall>()
            .ToList();

        if (candidates.Count == 0)
            return null;

        // Prefer current Starfield-capable builds, then 64-bit GUI, then anything.
        return candidates
            .OrderByDescending(c => c.MeetsMinStarfield)
            .ThenByDescending(c => c.Version)
            .ThenBy(c => c.IsDumpTool)
            .ThenByDescending(c => c.ExePath.Contains("64", StringComparison.OrdinalIgnoreCase))
            .First();
    }

    public static IReadOnlyList<XEditInstall> LocateAll(XEditGame game = XEditGame.Auto) =>
        EnumerateCandidates(game)
            .Select(Describe)
            .Where(x => x is not null)
            .Cast<XEditInstall>()
            .DistinctBy(x => x.ExePath, StringComparer.OrdinalIgnoreCase)
            .ToList();

    static IEnumerable<string> EnumerateCandidates(XEditGame game)
    {
        foreach (var env in new[] { "XEDIT", "XEDIT_PATH", "SF1EDIT", "SF1EDIT_PATH" })
        {
            var v = Environment.GetEnvironmentVariable(env);
            if (!string.IsNullOrWhiteSpace(v))
                yield return v;
        }

        foreach (var dir in new[] { XEditPaths.BinDir, XEditPaths.Root })
        {
            if (!Directory.Exists(dir)) continue;
            foreach (var name in ExeNames)
            {
                var p = Path.Combine(dir, name);
                if (File.Exists(p)) yield return p;
            }
        }

        foreach (var p in GuessGameExes(game))
            yield return p;
    }

    static IEnumerable<string> GuessGameExes(XEditGame game)
    {
        var roots = new[]
        {
            @"F:\SteamLibrary\steamapps\common\Starfield",
            @"G:\SteamLibrary\steamapps\common\Starfield",
            @"E:\SteamLibrary\steamapps\common\Starfield",
            @"C:\Program Files (x86)\Steam\steamapps\common\Starfield",
            @"D:\SteamLibrary\steamapps\common\Starfield"
        };

        if (game is XEditGame.SF1 or XEditGame.Auto)
        {
            foreach (var root in roots)
            {
                foreach (var name in new[] { "SF1Edit64.exe", "SF1Edit.exe", "xEdit64.exe", "xEdit.exe" })
                {
                    var p = Path.Combine(root, name);
                    if (File.Exists(p)) yield return p;
                    p = Path.Combine(root, "Optional", name);
                    if (File.Exists(p)) yield return p;
                }
            }
        }
    }

    static XEditInstall? Describe(string path)
    {
        path = Environment.ExpandEnvironmentVariables(path.Trim().Trim('"'));
        if (Directory.Exists(path))
        {
            foreach (var name in ExeNames)
            {
                var p = Path.Combine(path, name);
                if (File.Exists(p))
                {
                    path = p;
                    break;
                }
            }
        }

        if (!File.Exists(path))
            return null;

        var info = FileVersionInfo.GetVersionInfo(path);
        var verText = info.ProductVersion ?? info.FileVersion ?? "";
        var version = XEditVersion.Parse(verText);
        if (version.IsUnknown)
            version = XEditVersion.Parse(info.Comments ?? "") ;

        var game = XEditGameModes.FromExeName(path);
        var dump = Path.GetFileName(path).Contains("Dump", StringComparison.OrdinalIgnoreCase);
        var meets = !version.IsUnknown && version >= XEditVersion.MinStarfieldCurrent;
        string? warning = null;
        if (!version.IsUnknown && version < XEditVersion.MinStarfieldCurrent)
        {
            warning = $"This is {version}. Starfield .esp editing, small/medium masters, and current DLC records need TES5Edit {XEditVersion.MinStarfieldCurrent}+ (branch dev-4.1.6). GitHub's last packaged release is 4.1.5f and is too old.";
        }

        var dir = Path.GetDirectoryName(path)!;
        var data = Path.Combine(dir, "Data");
        if (!Directory.Exists(data) && Directory.Exists(Path.Combine(dir, "..", "Data")))
            data = Path.GetFullPath(Path.Combine(dir, "..", "Data"));

        return new XEditInstall
        {
            ExePath = Path.GetFullPath(path),
            Game = game == XEditGame.Auto ? XEditGame.SF1 : game,
            Version = version,
            IsDumpTool = dump,
            MeetsMinStarfield = meets,
            Warning = warning,
            GameDataPath = Directory.Exists(data) ? data : null
        };
    }
}
