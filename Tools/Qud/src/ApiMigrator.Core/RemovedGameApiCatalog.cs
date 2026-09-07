using System.Text.Json;
using System.Text.Json.Serialization;

namespace ApiMigrator.Core;

public sealed class RemovedGameType
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("fullNames")] public List<string> FullNames { get; set; } = new();
    [JsonPropertyName("kind")] public string Kind { get; set; } = "";
}

public sealed class RemovedGameApisFile
{
    [JsonPropertyName("types")] public List<RemovedGameType> Types { get; set; } = new();
}

/// <summary>
/// Curated list of types the live game no longer ships (minigames, etc.).
/// Loaded from <c>data/removed_game_apis.json</c>.
/// </summary>
public static class RemovedGameApiCatalog
{
    public const string FileName = "removed_game_apis.json";

    static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    static RemovedGameApisFile? _cached;
    static Dictionary<string, RemovedGameType>? _byName;

    public static string? LastLoadPath { get; private set; }

    public static void ResetCache()
    {
        _cached = null;
        _byName = null;
        LastLoadPath = null;
    }

    public static RemovedGameApisFile Load(string? dataDir = null)
    {
        if (_cached != null && dataDir is null)
            return _cached;

        var dir = dataDir ?? FindDataDir();
        var path = Path.Combine(dir, FileName);
        LastLoadPath = path;
        if (!File.Exists(path))
        {
            _cached = new RemovedGameApisFile();
            _byName = new Dictionary<string, RemovedGameType>(StringComparer.Ordinal);
            return _cached;
        }

        var json = File.ReadAllText(path);
        _cached = JsonSerializer.Deserialize<RemovedGameApisFile>(json, JsonOpts)
                  ?? new RemovedGameApisFile();
        _byName = BuildIndex(_cached);
        return _cached;
    }

    static Dictionary<string, RemovedGameType> BuildIndex(RemovedGameApisFile file)
    {
        var map = new Dictionary<string, RemovedGameType>(StringComparer.Ordinal);
        foreach (var t in file.Types)
        {
            if (string.IsNullOrWhiteSpace(t.Name)) continue;
            map.TryAdd(t.Name, t);
            foreach (var fqn in t.FullNames)
            {
                if (string.IsNullOrWhiteSpace(fqn)) continue;
                map.TryAdd(fqn, t);
                var simple = SimpleName(fqn);
                if (!string.IsNullOrEmpty(simple))
                    map.TryAdd(simple, t);
            }
        }
        return map;
    }

    public static bool TryGet(string typeName, out RemovedGameType entry)
    {
        Load();
        entry = null!;
        if (string.IsNullOrWhiteSpace(typeName) || _byName is null)
            return false;
        var key = typeName.Trim();
        if (_byName.TryGetValue(key, out entry!))
            return true;
        var simple = SimpleName(key);
        return !string.IsNullOrEmpty(simple) && _byName.TryGetValue(simple, out entry!);
    }

    public static string PreferredFullName(RemovedGameType entry)
    {
        if (entry.FullNames.Count > 0 && !string.IsNullOrWhiteSpace(entry.FullNames[0]))
            return entry.FullNames[0];
        return entry.Name;
    }

    public static string SimpleName(string dotted)
    {
        var i = dotted.LastIndexOf('.');
        return i < 0 ? dotted : dotted[(i + 1)..];
    }

    public static bool IsRemovedTypeToken(string token) => TryGet(token, out _);

    static string FindDataDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            var candidate = Path.Combine(dir.FullName, "data", FileName);
            if (File.Exists(candidate))
                return Path.Combine(dir.FullName, "data");
            dir = dir.Parent;
        }
        return Path.Combine(AppContext.BaseDirectory, "data");
    }
}
