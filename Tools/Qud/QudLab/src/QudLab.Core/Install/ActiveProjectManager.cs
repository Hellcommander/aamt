namespace QudLab.Core.Install;

/// <summary>
/// Thread-safe active mod/workspace root for serve, AI tools, and HTTP clients.
/// Hot-switch rescans <see cref="Cache.ProjectCache"/> without restarting serve.
/// </summary>
public sealed class ActiveProjectManager
{
    readonly object _lock = new();
    readonly Func<Cache.IntelligenceCache?> _cacheProvider;
    readonly Func<string?> _fallbackWorkspace;
    readonly Func<string?> _installRoot;

    public ActiveProjectManager(
        Func<Cache.IntelligenceCache?> cacheProvider,
        Func<string?> fallbackWorkspace,
        Func<string?> installRoot)
    {
        _cacheProvider = cacheProvider;
        _fallbackWorkspace = fallbackWorkspace;
        _installRoot = installRoot;
    }

    public ActiveProjectInfo Get()
    {
        lock (_lock)
        {
            var root = ResolveRoot();
            var cfg = QudModPaths.LoadConfig();
            var cache = _cacheProvider();
            var manifest = root is not null ? QudModPaths.ReadManifest(root) : null;
            var mod = root is not null ? QudModPaths.FindMod(root, _installRoot()) : null;
            var name = !string.IsNullOrWhiteSpace(cfg.ProjectName)
                ? cfg.ProjectName
                : QudModPaths.StripQudMarkup(manifest?.Title)
                  ?? (root is not null ? Path.GetFileName(root) : null);
            return new ActiveProjectInfo
            {
                RootPath = root,
                Name = name,
                Id = manifest?.Id ?? mod?.Id,
                Source = mod?.Source ?? (IsWorkspace(root) ? "workspace" : "path"),
                FileCount = cache?.Project.Files.Count ?? 0,
                ConfigPath = QudModPaths.ConfigPath()
            };
        }
    }

    public IReadOnlyList<ModFolderInfo> ListMods(string? query = null)
    {
        var mods = QudModPaths.ListAllMods(_installRoot());
        if (string.IsNullOrWhiteSpace(query))
            return mods;
        return mods.Where(m =>
                (m.Title?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
                || (m.Id?.Contains(query, StringComparison.OrdinalIgnoreCase) ?? false)
                || m.Name.Contains(query, StringComparison.OrdinalIgnoreCase)
                || m.Path.Contains(query, StringComparison.OrdinalIgnoreCase))
            .ToList();
    }

    public ActiveProjectSetResult Set(string pathOrQuery)
    {
        if (string.IsNullOrWhiteSpace(pathOrQuery))
            return ActiveProjectSetResult.Fail("path or query required");

        lock (_lock)
        {
            string? resolved = Directory.Exists(pathOrQuery)
                ? Path.GetFullPath(pathOrQuery)
                : QudModPaths.FindMod(pathOrQuery, _installRoot())?.Path;

            if (string.IsNullOrWhiteSpace(resolved) || !Directory.Exists(resolved))
                return ActiveProjectSetResult.Fail("mod/project not found: " + pathOrQuery);

            var cache = _cacheProvider();
            if (cache is null)
                return ActiveProjectSetResult.Fail("cache missing — run qudlab index");

            Cache.CacheIO.ScanProject(cache.Project, resolved);
            Cache.CacheIO.Save(cache);

            var manifest = QudModPaths.ReadManifest(resolved);
            var name = QudModPaths.StripQudMarkup(manifest?.Title) ?? Path.GetFileName(resolved);
            QudModPaths.SaveConfig(new ActiveProjectConfig
            {
                ProjectPath = resolved,
                ProjectName = name
            });

            return ActiveProjectSetResult.Ok(resolved, name, manifest?.Id, cache.Project.Files.Count);
        }
    }

    public int Rescan()
    {
        lock (_lock)
        {
            var cache = _cacheProvider();
            var root = ResolveRoot();
            if (cache is null || string.IsNullOrWhiteSpace(root) || !Directory.Exists(root))
                return 0;
            Cache.CacheIO.ScanProject(cache.Project, root);
            Cache.CacheIO.Save(cache);
            return cache.Project.Files.Count;
        }
    }

    public string? ReadFile(string? rel)
    {
        var root = ResolveRoot();
        if (string.IsNullOrWhiteSpace(rel) || string.IsNullOrWhiteSpace(root))
            return null;
        var full = Path.GetFullPath(Path.Combine(root, rel.Replace('/', Path.DirectorySeparatorChar)));
        var rootFull = Path.GetFullPath(root);
        if (!full.StartsWith(rootFull, StringComparison.OrdinalIgnoreCase))
            return null;
        return File.Exists(full) ? File.ReadAllText(full) : null;
    }

    public void WriteFile(string rel, string content)
    {
        var root = ResolveRoot();
        if (string.IsNullOrWhiteSpace(root))
            throw new InvalidOperationException("No project root");
        var full = Path.GetFullPath(Path.Combine(root, rel.Replace('/', Path.DirectorySeparatorChar)));
        var rootFull = Path.GetFullPath(root);
        if (!full.StartsWith(rootFull, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Write path escapes active project root");
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, content);

        var cache = _cacheProvider();
        if (cache is not null)
        {
            Cache.CacheIO.ScanProject(cache.Project, root);
            Cache.CacheIO.Save(cache);
        }
    }

    string? ResolveRoot()
    {
        var cache = _cacheProvider();
        if (!string.IsNullOrWhiteSpace(cache?.Project.RootPath) && Directory.Exists(cache.Project.RootPath))
            return cache.Project.RootPath;
        return QudModPaths.ResolveProject(null, _fallbackWorkspace());
    }

    static bool IsWorkspace(string? root)
    {
        if (string.IsNullOrWhiteSpace(root))
            return false;
        return root.Replace('\\', '/').EndsWith("/Workspace/src", StringComparison.OrdinalIgnoreCase);
    }
}

public sealed class ActiveProjectInfo
{
    public string? RootPath { get; init; }
    public string? Name { get; init; }
    public string? Id { get; init; }
    public string Source { get; init; } = "path";
    public int FileCount { get; init; }
    public string ConfigPath { get; init; } = "";
}

public sealed class ActiveProjectSetResult
{
    public bool Success { get; init; }
    public string? Error { get; init; }
    public string? RootPath { get; init; }
    public string? Name { get; init; }
    public string? Id { get; init; }
    public int FileCount { get; init; }

    public static ActiveProjectSetResult Ok(string root, string name, string? id, int files) =>
        new() { Success = true, RootPath = root, Name = name, Id = id, FileCount = files };

    public static ActiveProjectSetResult Fail(string error) =>
        new() { Success = false, Error = error };
}
