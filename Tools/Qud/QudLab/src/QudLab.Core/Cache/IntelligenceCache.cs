using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using QudLab.Core.Install;

namespace QudLab.Core.Cache;

public sealed class IntelligenceCache
{
    public TypeGraph TypeGraph { get; set; } = new();
    public BlueprintGraph BlueprintGraph { get; set; } = new();
    public EventGraph EventGraph { get; set; } = new();
    public MutationGraph MutationGraph { get; set; } = new();
    public AbilityGraph AbilityGraph { get; set; } = new();
    public CommandGraph CommandGraph { get; set; } = new();
    public CatalogGraph Catalogs { get; set; } = new();
    public ProjectCache Project { get; set; } = new();
    public SimulationCache Simulation { get; set; } = new();
    public IndexStamp Stamp { get; set; } = new();
    public string? GameRoot { get; set; }
    public DateTimeOffset BuiltAt { get; set; } = DateTimeOffset.UtcNow;
    public string SchemaVersion { get; set; } = "2.0";
}

public sealed class IndexStamp
{
    public string? GameRoot { get; set; }
    public DateTimeOffset? AssemblyCSharpUtc { get; set; }
    public DateTimeOffset BuiltAt { get; set; } = DateTimeOffset.UtcNow;
    public string SchemaVersion { get; set; } = "2.0";
}

public sealed class TypeGraph
{
    public Dictionary<string, TypeNode> Types { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class TypeNode
{
    public required string FullName { get; set; }
    public string? Namespace { get; set; }
    public string? BaseType { get; set; }
    public List<string> Interfaces { get; set; } = new();
    public List<string> Methods { get; set; } = new();
    public List<string> Fields { get; set; } = new();
    public List<string> Properties { get; set; } = new();
    public List<string> Attributes { get; set; } = new();
}

public sealed class BlueprintGraph
{
    public Dictionary<string, BlueprintNode> Objects { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class BlueprintNode
{
    public required string Name { get; set; }
    public string? Inherits { get; set; }
    public List<string> Parts { get; set; } = new();
    public Dictionary<string, string> Stats { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public Dictionary<string, string> Tags { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public string? SourceFile { get; set; }
}

public sealed class EventGraph
{
    public List<string> EventNames { get; set; } = new();
    public List<string> EventTypeNames { get; set; } = new();
    public Dictionary<string, List<string>> HandlersByType { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public EventPoolAudit? PoolAudit { get; set; }
}

/// <summary>Static MinEvent / pool audit (base game + mod ModAssemblies).</summary>
public sealed class EventPoolAudit
{
    public DateTimeOffset BuiltAt { get; set; }
    public int TotalEvents { get; set; }
    public int PooledCount { get; set; }
    public int SingletonCount { get; set; }
    public int ModEventCount { get; set; }
    public int ModPooledCount { get; set; }
    public List<EventPoolEntry> Entries { get; set; } = new();
    public List<EventIdConflict> IdConflicts { get; set; } = new();
    public List<string> ScanErrors { get; set; } = new();
    public string? RuntimePoolReport { get; set; }
}

public sealed class EventPoolEntry
{
    public required string TypeFullName { get; set; }
    public string? Assembly { get; set; }
    public string Source { get; set; } = "game";
    public string? ModFolder { get; set; }
    public bool IsMod { get; set; }
    public bool IsAbstract { get; set; }
    public string CacheKind { get; set; } = "Unknown";
    public int? Cascade { get; set; }
    public string? BaseType { get; set; }
    public int EventId { get; set; }
    public bool Suspicious { get; set; }
}

public sealed class EventIdConflict
{
    public int EventId { get; set; }
    public List<string> Types { get; set; } = new();
}

public sealed class MutationGraph
{
    public Dictionary<string, MutationNode> Mutations { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class MutationNode
{
    public required string Name { get; set; }
    public string? Class { get; set; }
    public string? Category { get; set; }
    public string? Cost { get; set; }
    public string? Exclusions { get; set; }
    public string? Tile { get; set; }
    public string? SourceFile { get; set; }
}

public sealed class AbilityGraph
{
    public Dictionary<string, AbilityNode> Abilities { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class AbilityNode
{
    public required string Command { get; set; }
    public string? Description { get; set; }
    public string? Tile { get; set; }
    public string? SourceFile { get; set; }
}

public sealed class CommandGraph
{
    public Dictionary<string, CommandNode> Commands { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class CommandNode
{
    public required string Id { get; set; }
    public string Kind { get; set; } = "command";
    public string? SourceFile { get; set; }
    public Dictionary<string, string> Attrs { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class CatalogGraph
{
    /// <summary>Bodies, Skills, EffectsDetails, Genotypes, Subtypes — name/id lists.</summary>
    public Dictionary<string, List<CatalogEntry>> BySource { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class CatalogEntry
{
    public required string Id { get; set; }
    public string? DisplayName { get; set; }
    public string? Kind { get; set; }
    /// <summary>Grouping: genotype class (Callings/Castes), subtype category, embark window, etc.</summary>
    public string? Parent { get; set; }
    public Dictionary<string, string> Attrs { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> Skills { get; set; } = new();
}

public sealed class ProjectCache
{
    public string? RootPath { get; set; }
    public List<string> Files { get; set; } = new();
    public Dictionary<string, string> FileHashes { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> Diagnostics { get; set; } = new();
}

public sealed class SimulationCache
{
    public List<string> TurnLogs { get; set; } = new();
    public List<ThreadActionDto> ThreadActions { get; set; } = new();
    public List<TimelineEventDto> Timeline { get; set; } = new();
    public StressMetricsDto? Stress { get; set; }
    public string? ActiveScenario { get; set; }
    public DateTimeOffset? LastIngestAt { get; set; }
}

public sealed class ThreadActionDto
{
    public DateTimeOffset Timestamp { get; set; }
    public int ThreadId { get; set; }
    public string Action { get; set; } = "";
    public string Detail { get; set; } = "";
}

public sealed class TimelineEventDto
{
    public int Turn { get; set; }
    public string Kind { get; set; } = "";
    public string Label { get; set; } = "";
    public string Detail { get; set; } = "";
    public int ThreadId { get; set; }
    public DateTimeOffset Timestamp { get; set; }
}

public sealed class StressMetricsDto
{
    public int Turns { get; set; }
    public int MainTicks { get; set; }
    public int WorkerPlaceholders { get; set; }
    public long ElapsedMs { get; set; }
    public double EventsPerTurn { get; set; }
}

public static class CacheIO
{
    public const string CurrentSchemaVersion = "2.0";

    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public static string DefaultCacheDir()
    {
        var dir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "QudLab",
            "cache");
        Directory.CreateDirectory(dir);
        return dir;
    }

    public static void Save(IntelligenceCache cache, string? directory = null)
    {
        directory ??= DefaultCacheDir();
        Directory.CreateDirectory(directory);
        File.WriteAllText(Path.Combine(directory, "intelligence.json"),
            JsonSerializer.Serialize(cache, JsonOptions));
        File.WriteAllText(Path.Combine(directory, "TypeGraph.json"),
            JsonSerializer.Serialize(cache.TypeGraph, JsonOptions));
        File.WriteAllText(Path.Combine(directory, "BlueprintGraph.json"),
            JsonSerializer.Serialize(cache.BlueprintGraph, JsonOptions));
        File.WriteAllText(Path.Combine(directory, "EventGraph.json"),
            JsonSerializer.Serialize(cache.EventGraph, JsonOptions));
        File.WriteAllText(Path.Combine(directory, "MutationGraph.json"),
            JsonSerializer.Serialize(cache.MutationGraph, JsonOptions));
    }

    public static IntelligenceCache? Load(string? directory = null)
    {
        directory ??= DefaultCacheDir();
        var path = Path.Combine(directory, "intelligence.json");
        if (!File.Exists(path))
            return null;
        return JsonSerializer.Deserialize<IntelligenceCache>(File.ReadAllText(path), JsonOptions);
    }

    public static bool IsStale(IntelligenceCache? cache, QudInstallInfo install)
    {
        if (cache is null)
            return true;
        if (!string.Equals(cache.SchemaVersion, CurrentSchemaVersion, StringComparison.Ordinal))
            return true;
        if (!string.Equals(cache.Stamp.GameRoot ?? cache.GameRoot, install.RootPath, StringComparison.OrdinalIgnoreCase))
            return true;

        DateTimeOffset asmUtc;
        try
        {
            asmUtc = File.GetLastWriteTimeUtc(install.AssemblyCSharpPath);
        }
        catch
        {
            return true;
        }

        if (cache.Stamp.AssemblyCSharpUtc is null)
            return true;
        // Allow 2s skew
        return Math.Abs((cache.Stamp.AssemblyCSharpUtc.Value - asmUtc).TotalSeconds) > 2;
    }

    public static IndexStamp CreateStamp(QudInstallInfo install)
    {
        DateTimeOffset asmUtc = DateTimeOffset.MinValue;
        try { asmUtc = File.GetLastWriteTimeUtc(install.AssemblyCSharpPath); } catch { /* ignore */ }
        return new IndexStamp
        {
            GameRoot = install.RootPath,
            AssemblyCSharpUtc = asmUtc,
            BuiltAt = DateTimeOffset.UtcNow,
            SchemaVersion = CurrentSchemaVersion
        };
    }

    public static void ScanProject(ProjectCache project, string projectRoot)
    {
        project.RootPath = Path.GetFullPath(projectRoot);
        project.Files.Clear();
        project.FileHashes.Clear();
        if (!Directory.Exists(project.RootPath))
            return;

        void AddFiles(string pattern)
        {
            foreach (var file in QudModPaths.EnumerateSourceFiles(project.RootPath, pattern))
            {
                var rel = Path.GetRelativePath(project.RootPath, file).Replace('\\', '/');
                if (project.FileHashes.ContainsKey(rel))
                    continue;
                project.Files.Add(rel);
                try
                {
                    var bytes = File.ReadAllBytes(file);
                    var hash = Convert.ToHexString(SHA256.HashData(bytes))[..12];
                    project.FileHashes[rel] = hash;
                }
                catch
                {
                    project.FileHashes[rel] = "";
                }
            }
        }

        AddFiles("*.cs");
        AddFiles("*.xml");
        project.Files.Sort(StringComparer.OrdinalIgnoreCase);
    }

    public static string ShortHash(string text)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(text));
        return Convert.ToHexString(hash)[..12];
    }
}
