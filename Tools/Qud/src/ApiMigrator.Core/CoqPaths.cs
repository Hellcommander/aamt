namespace ApiMigrator.Core;

/// <summary>
/// Locates the migrator install, local Mods, and LocalLow CoQ data independently of
/// whether this toolkit still lives next to <c>CavesOfQud</c> or under a separate Tools folder.
/// </summary>
public static class CoqPaths
{
    public const string ToolsRootEnvVar = "COQ_TOOLS_ROOT";
    public const string ModsRootEnvVar = "COQ_MODS_ROOT";
    public const string DefaultInstall = @"D:\games\Ai assisted toolkit\Tools\Qud";

    public static string LocalLowCoqRoot =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            "AppData", "LocalLow", "Freehold Games", "CavesOfQud");

    public static string DefaultModsRoot => Path.Combine(LocalLowCoqRoot, "Mods");

    public static bool LooksLikeToolsRoot(string dir) =>
        File.Exists(Path.Combine(dir, "data", "obsolete_api_dump.json"))
        || File.Exists(Path.Combine(dir, "data", "curated_rewrite_rules.json"));

    public static string FindToolsRoot(string? startDir = null)
    {
        var env = Environment.GetEnvironmentVariable(ToolsRootEnvVar);
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env) && LooksLikeToolsRoot(env))
            return Path.GetFullPath(env);

        var dir = new DirectoryInfo(string.IsNullOrEmpty(startDir) ? AppContext.BaseDirectory : startDir);
        while (dir is not null)
        {
            if (LooksLikeToolsRoot(dir.FullName))
                return dir.FullName;
            dir = dir.Parent;
        }

        if (LooksLikeToolsRoot(DefaultInstall))
            return DefaultInstall;

        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
    }

    public static string ResolveModsRoot(string? toolsRoot = null)
    {
        var env = Environment.GetEnvironmentVariable(ModsRootEnvVar);
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return Path.GetFullPath(env);

        if (!string.IsNullOrEmpty(toolsRoot))
        {
            try
            {
                var parent = Path.GetDirectoryName(Path.GetFullPath(toolsRoot));
                if (!string.IsNullOrEmpty(parent))
                {
                    var sibling = Path.Combine(parent, "Mods");
                    if (Directory.Exists(sibling))
                        return sibling;
                }
            }
            catch
            {
                /* fall through to LocalLow */
            }
        }

        return DefaultModsRoot;
    }

    /// <summary>
    /// True when a saved/default path is the CoQ data root or the toolkit parent rather than Mods.
    /// </summary>
    public static bool IsMisrootedModsPath(string path, string toolsRoot)
    {
        try
        {
            var full = Path.GetFullPath(path).TrimEnd('\\', '/');
            var toolsParent = Path.GetDirectoryName(Path.GetFullPath(toolsRoot))?.TrimEnd('\\', '/');
            if (toolsParent is not null &&
                string.Equals(full, toolsParent, StringComparison.OrdinalIgnoreCase))
                return true;
            var coq = Path.GetFullPath(LocalLowCoqRoot).TrimEnd('\\', '/');
            if (string.Equals(full, coq, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        catch
        {
            /* ignore */
        }
        return false;
    }

    public static bool PathIsUnderRoot(string path, string root)
    {
        try
        {
            var r = Path.GetFullPath(root)
                .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var p = Path.GetFullPath(path);
            if (string.Equals(p, r, StringComparison.OrdinalIgnoreCase))
                return true;
            return p.StartsWith(r + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        }
        catch
        {
            return false;
        }
    }
}
