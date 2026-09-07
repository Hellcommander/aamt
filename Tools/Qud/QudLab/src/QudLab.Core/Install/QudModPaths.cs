using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace QudLab.Core.Install;

/// <summary>
/// Live CoQ mod folders under LocalLow + Steam Workshop, plus the Qud Lab Workspace.
/// The AI/serve project root must point at a real mod — not only Workspace/src.
/// </summary>
public static class QudModPaths
{
    static readonly HashSet<string> SkipDirNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "bin", "obj", "Library", "Packages", "Temp", "Logs", "UserSettings",
        "ProjectSettings", ".git", ".vs", "node_modules", "DesignDrafts",
        "ModCompileCache", "ModAssemblies"
    };

    public static string LocalLowQudRoot() =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) + "Low",
            "Freehold Games",
            "CavesOfQud");

    public static string LocalModsRoot() => Path.Combine(LocalLowQudRoot(), "Mods");

    public static string BuildLogPath() => Path.Combine(LocalLowQudRoot(), "build_log.txt");

    public static string PlayerLogPath() => Path.Combine(LocalLowQudRoot(), "Player.log");

    public static string ConfigPath() =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "QudLab",
            "active-project.json");

    /// <summary>Steam workshop content for CoQ (app 333640), if present.</summary>
    public static string? WorkshopModsRoot(string? qudInstallRoot = null)
    {
        foreach (var candidate in WorkshopCandidates(qudInstallRoot))
        {
            if (Directory.Exists(candidate))
                return candidate;
        }

        return null;
    }

    static IEnumerable<string> WorkshopCandidates(string? qudInstallRoot)
    {
        if (!string.IsNullOrWhiteSpace(qudInstallRoot))
        {
            var steamapps = FindSteamapps(qudInstallRoot);
            if (steamapps is not null)
                yield return Path.Combine(steamapps, "workshop", "content", "333640");
        }

        yield return @"D:\games\Steam\steamapps\workshop\content\333640";
        yield return @"C:\Program Files (x86)\Steam\steamapps\workshop\content\333640";
        yield return Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
            "Steam", "steamapps", "workshop", "content", "333640");
    }

    static string? FindSteamapps(string start)
    {
        try
        {
            var dir = new DirectoryInfo(Path.GetFullPath(start));
            while (dir is not null)
            {
                if (dir.Name.Equals("steamapps", StringComparison.OrdinalIgnoreCase))
                    return dir.FullName;
                if (Directory.Exists(Path.Combine(dir.FullName, "steamapps")))
                    return Path.Combine(dir.FullName, "steamapps");
                dir = dir.Parent;
            }
        }
        catch { }

        return null;
    }

    public static IReadOnlyList<ModFolderInfo> ListAllMods(string? qudInstallRoot = null)
    {
        var byId = new Dictionary<string, ModFolderInfo>(StringComparer.OrdinalIgnoreCase);

        void AddRange(IEnumerable<ModFolderInfo> mods)
        {
            foreach (var m in mods)
            {
                var key = !string.IsNullOrWhiteSpace(m.Id) ? m.Id! : m.Path;
                if (!byId.ContainsKey(key))
                    byId[key] = m;
            }
        }

        AddRange(ListLocalMods());
        var workshop = WorkshopModsRoot(qudInstallRoot);
        if (workshop is not null)
            AddRange(ListWorkshopMods(workshop));

        return byId.Values
            .OrderBy(m => m.Title ?? m.Name, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public static IReadOnlyList<ModFolderInfo> ListLocalMods()
    {
        var root = LocalModsRoot();
        if (!Directory.Exists(root))
            return Array.Empty<ModFolderInfo>();

        return Directory.EnumerateDirectories(root)
            .Select(dir => TryDescribeMod(dir, "local"))
            .Where(m => m is not null)
            .Cast<ModFolderInfo>()
            .OrderBy(m => m.Name, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public static IReadOnlyList<ModFolderInfo> ListWorkshopMods(string workshopRoot)
    {
        if (!Directory.Exists(workshopRoot))
            return Array.Empty<ModFolderInfo>();

        return Directory.EnumerateDirectories(workshopRoot)
            .Select(dir => TryDescribeMod(dir, "workshop"))
            .Where(m => m is not null)
            .Cast<ModFolderInfo>()
            .OrderBy(m => m.Title ?? m.Name, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    static ModFolderInfo? TryDescribeMod(string dir, string source)
    {
        var name = Path.GetFileName(dir);
        if (string.IsNullOrWhiteSpace(name) || name.StartsWith('.') || name.StartsWith('_'))
            return null;
        if (name is "bin" or "obj" or "reports")
            return null;

        var manifest = ReadManifest(dir);
        var cs = SafeCountCs(dir);
        var hasManifest = manifest is not null;
        if (cs == 0 && !hasManifest && !File.Exists(Path.Combine(dir, "Mutations.xml")))
            return null;

        var title = StripQudMarkup(manifest?.Title) ?? name;
        return new ModFolderInfo
        {
            Name = name,
            Path = dir,
            CsFileCount = cs,
            HasManifest = hasManifest,
            Id = manifest?.Id,
            Title = title,
            Source = source
        };
    }

    public static ModManifestLite? ReadManifest(string modDir)
    {
        foreach (var file in new[] { "manifest.json", "Manifest.json" })
        {
            var path = Path.Combine(modDir, file);
            if (!File.Exists(path))
                continue;
            try
            {
                return JsonSerializer.Deserialize<ModManifestLite>(File.ReadAllText(path), JsonOpts);
            }
            catch
            {
                return null;
            }
        }

        return null;
    }

    public static string StripQudMarkup(string? title)
    {
        if (string.IsNullOrWhiteSpace(title))
            return title ?? "";
        var s = Regex.Replace(title, "\\{\\{[^}]*\\}\\}", "");
        return s.Trim();
    }

    static int SafeCountCs(string dir)
    {
        try
        {
            return EnumerateSourceFiles(dir, "*.cs").Count();
        }
        catch
        {
            return 0;
        }
    }

    public static bool ShouldSkipDirectory(string dirName) =>
        SkipDirNames.Contains(dirName);

    public static IEnumerable<string> EnumerateSourceFiles(string projectRoot, string pattern = "*.cs")
    {
        projectRoot = Path.GetFullPath(projectRoot);
        if (!Directory.Exists(projectRoot))
            yield break;

        var stack = new Stack<string>();
        stack.Push(projectRoot);
        while (stack.Count > 0)
        {
            var dir = stack.Pop();
            string[]? children;
            try { children = Directory.GetDirectories(dir); }
            catch { continue; }

            foreach (var child in children)
            {
                var name = Path.GetFileName(child);
                if (ShouldSkipDirectory(name))
                    continue;
                stack.Push(child);
            }

            string[]? files;
            try { files = Directory.GetFiles(dir, pattern); }
            catch { continue; }

            foreach (var f in files)
                yield return f;
        }
    }

    public static ActiveProjectConfig LoadConfig()
    {
        try
        {
            var path = ConfigPath();
            if (!File.Exists(path))
                return new ActiveProjectConfig();
            return JsonSerializer.Deserialize<ActiveProjectConfig>(File.ReadAllText(path), JsonOpts)
                   ?? new ActiveProjectConfig();
        }
        catch
        {
            return new ActiveProjectConfig();
        }
    }

    public static void SaveConfig(ActiveProjectConfig cfg)
    {
        var path = ConfigPath();
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(cfg, JsonOpts));
    }

    /// <summary>
    /// Resolve active project: CLI --project → env QUDLAB_PROJECT → saved config → Workspace/src.
    /// </summary>
    public static string? ResolveProject(string? cliProject, string? labWorkspaceSrc)
    {
        if (!string.IsNullOrWhiteSpace(cliProject) && Directory.Exists(cliProject))
            return Path.GetFullPath(cliProject);

        var env = Environment.GetEnvironmentVariable("QUDLAB_PROJECT");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return Path.GetFullPath(env);

        var cfg = LoadConfig();
        if (!string.IsNullOrWhiteSpace(cfg.ProjectPath) && Directory.Exists(cfg.ProjectPath))
            return Path.GetFullPath(cfg.ProjectPath);

        if (!string.IsNullOrWhiteSpace(labWorkspaceSrc) && Directory.Exists(labWorkspaceSrc))
            return Path.GetFullPath(labWorkspaceSrc);

        return null;
    }

    /// <summary>Find a mod directory by id, title fragment, or folder name.</summary>
    public static ModFolderInfo? FindMod(string query, string? qudInstallRoot = null)
    {
        if (string.IsNullOrWhiteSpace(query))
            return null;
        if (Directory.Exists(query))
        {
            return TryDescribeMod(Path.GetFullPath(query), "path");
        }

        var mods = ListAllMods(qudInstallRoot);
        var exact = mods.FirstOrDefault(m =>
            string.Equals(m.Id, query, StringComparison.OrdinalIgnoreCase)
            || string.Equals(m.Name, query, StringComparison.OrdinalIgnoreCase)
            || string.Equals(m.Title, query, StringComparison.OrdinalIgnoreCase));
        if (exact is not null)
            return exact;

        return mods.FirstOrDefault(m =>
            (m.Title?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
            || (m.Id?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
            || m.Name.Contains(query, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>Parse CoQ build_log.txt TYPE CONFLICTS section (and Player.log MODERROR lines).</summary>
    public static string ReadTypeConflicts(int maxLines = 80)
    {
        var sb = new StringBuilder();
        var buildLog = BuildLogPath();
        if (File.Exists(buildLog))
        {
            sb.AppendLine("=== " + buildLog + " ===");
            var lines = File.ReadAllLines(buildLog);
            var start = -1;
            for (var i = 0; i < lines.Length; i++)
            {
                if (lines[i].Contains("TYPE CONFLICTS DETECTED", StringComparison.OrdinalIgnoreCase))
                    start = i;
            }

            if (start >= 0)
            {
                for (var i = start; i < lines.Length && i < start + maxLines; i++)
                {
                    var line = lines[i];
                    if (i > start && line.Contains("====", StringComparison.Ordinal) && !line.Contains("TYPE CONFLICT", StringComparison.OrdinalIgnoreCase))
                        break;
                    sb.AppendLine(line);
                    if (Regex.IsMatch(line, @"^\s*\d+:\s") && i > start + 5)
                        break;
                }
            }
            else
            {
                sb.AppendLine("(no TYPE CONFLICTS section in build_log — run the game once to regenerate)");
            }
        }
        else
        {
            sb.AppendLine("build_log.txt missing at " + buildLog);
        }

        var player = PlayerLogPath();
        if (File.Exists(player))
        {
            sb.AppendLine();
            sb.AppendLine("=== Player.log MODERROR (type / conflict) ===");
            var hits = 0;
            foreach (var line in File.ReadLines(player).Reverse())
            {
                if (line.Contains("MODERROR", StringComparison.OrdinalIgnoreCase)
                    || line.Contains("Type conflicts", StringComparison.OrdinalIgnoreCase)
                    || line.Contains("conflicting types", StringComparison.OrdinalIgnoreCase))
                {
                    sb.AppendLine(line);
                    hits++;
                    if (hits >= 20)
                        break;
                }
            }

            if (hits == 0)
                sb.AppendLine("(no recent MODERROR type-conflict lines)");
        }

        return sb.ToString();
    }

    static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };
}

public sealed class ModFolderInfo
{
    public required string Name { get; init; }
    public required string Path { get; init; }
    public int CsFileCount { get; init; }
    public bool HasManifest { get; init; }
    public string? Id { get; init; }
    public string? Title { get; init; }
    public string Source { get; init; } = "local";
}

public sealed class ModManifestLite
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }
}

public sealed class ActiveProjectConfig
{
    public string? ProjectPath { get; set; }
    public string? ProjectName { get; set; }
}
