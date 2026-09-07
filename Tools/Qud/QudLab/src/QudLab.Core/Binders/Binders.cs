using QudLab.Core.Abstractions;
using QudLab.Core.Install;

namespace QudLab.Core.Binders;

/// <summary>Proprietary-bound: loads assembly paths from verified install only (no bundling).</summary>
public sealed class QudAssemblyBinder : IQudAssemblyBinder
{
    public bool IsBound { get; private set; }
    public string? BoundManagedPath { get; private set; }
    QudInstallInfo? _install;

    public GateResult Bind(QudInstallInfo install)
    {
        if (!Directory.Exists(install.ManagedPath) || !File.Exists(install.AssemblyCSharpPath))
            return GateResult.Fail("Managed assemblies not found on install path.");

        _install = install;
        BoundManagedPath = install.ManagedPath;
        IsBound = true;
        return GateResult.Success(install, $"Bound Managed at {install.ManagedPath}");
    }

    public IReadOnlyList<string> ListManagedAssemblies()
    {
        if (!IsBound || BoundManagedPath is null)
            return Array.Empty<string>();
        return Directory.GetFiles(BoundManagedPath, "*.dll")
            .Select(Path.GetFileName)
            .Where(n => n is not null)
            .Cast<string>()
            .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public QudInstallInfo? Install => _install;
}

/// <summary>Proprietary-bound: references StreamingAssets / asset files from install only.</summary>
public sealed class QudAssetBinder : IQudAssetBinder
{
    public bool IsBound { get; private set; }
    QudInstallInfo? _install;

    public GateResult Bind(QudInstallInfo install)
    {
        if (!Directory.Exists(install.StreamingAssetsPath))
            return GateResult.Fail("StreamingAssets missing — refuse to run without game assets.");

        _install = install;
        IsBound = true;
        return GateResult.Success(install, $"Bound assets at {install.StreamingAssetsPath}");
    }

    public IReadOnlyList<AssetMeta> ListAssetMetadata(string relativePrefix = "")
    {
        if (!IsBound || _install is null)
            return Array.Empty<AssetMeta>();

        var root = _install.DataPath;
        var search = string.IsNullOrEmpty(relativePrefix)
            ? root
            : Path.Combine(root, relativePrefix.Replace('/', Path.DirectorySeparatorChar));
        if (!Directory.Exists(search))
            return Array.Empty<AssetMeta>();

        var list = new List<AssetMeta>();
        foreach (var file in Directory.EnumerateFiles(search, "*", SearchOption.AllDirectories))
        {
            var rel = Path.GetRelativePath(root, file).Replace('\\', '/');
            var ext = Path.GetExtension(file).ToLowerInvariant();
            var kind = ext switch
            {
                ".xml" => "xml",
                ".json" => "json",
                ".rpm" => "map",
                ".bmp" or ".png" or ".jpg" => "texture_ref",
                ".assets" or ".ress" or ".resource" => "unity_asset",
                ".txt" => "text",
                _ => "file"
            };
            list.Add(new AssetMeta
            {
                RelativePath = rel,
                Kind = kind,
                ByteLength = new FileInfo(file).Length
            });
        }

        return list;
    }
}

public sealed class InMemoryThreadActionSink : IThreadActionSink
{
    readonly List<ThreadActionRecord> _items = new();
    readonly object _lock = new();

    public void Record(ThreadActionRecord record)
    {
        lock (_lock)
            _items.Add(record);
    }

    public IReadOnlyList<ThreadActionRecord> Snapshot()
    {
        lock (_lock)
            return _items.ToList();
    }

    public void Clear()
    {
        lock (_lock)
            _items.Clear();
    }
}
