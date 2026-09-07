namespace QudLab.Core.Abstractions;

using QudLab.Core.Cache;
using QudLab.Core.Install;

/// <summary>Closed-core seams used by the Unity shell and CLI. Fill implementations over time.</summary>
public interface IQudAssemblyBinder
{
    bool IsBound { get; }
    string? BoundManagedPath { get; }
    GateResult Bind(QudInstallInfo install);
    IReadOnlyList<string> ListManagedAssemblies();
}

public interface IQudAssetBinder
{
    bool IsBound { get; }
    GateResult Bind(QudInstallInfo install);
    /// <summary>Metadata only — never export raw game texture bytes to AI clients.</summary>
    IReadOnlyList<AssetMeta> ListAssetMetadata(string relativePrefix = "");
}

public sealed class AssetMeta
{
    public required string RelativePath { get; init; }
    public required string Kind { get; init; }
    public long ByteLength { get; init; }
}

public interface IModAssistantHost
{
    bool IsRunning { get; }
    int Port { get; }
    Task StartAsync(CancellationToken ct = default);
    Task StopAsync(CancellationToken ct = default);
}

public interface IRestrictedSimulator
{
    bool IsReady { get; }
    string Status { get; }
    Task<SimSnapshot> RunTurnsAsync(SimRequest request, CancellationToken ct = default);
    void ApplySnapshotToCache(IntelligenceCache cache, SimSnapshot snap, string? scenario = null);
}

public sealed class SimRequest
{
    public string BlueprintOrSpecies { get; init; } = "Human";
    public int Turns { get; init; } = 10;
    public IReadOnlyList<string> Parts { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> Mutations { get; init; } = Array.Empty<string>();
    /// <summary>Debug-only sandbox — not a playable arena. Worldgen/GetZone is a named scenario.</summary>
    public bool RestrictedDebugOnly { get; init; } = true;
    /// <summary>Optional zone id for worldgen-getzone (e.g. JoppaWorld.11.22.1.1.10). crowd-load also accepts WxH (e.g. 160x50).</summary>
    public string? ZoneId { get; init; }
    /// <summary>crowd-load NPC count (0 = scenario default, typically 64).</summary>
    public int NpcCount { get; init; }
    /// <summary>crowd-load map width in cells (0 = default 160; vanilla Qud zones are 80).</summary>
    public int MapWidth { get; init; }
    /// <summary>crowd-load map height in cells (0 = default 50; vanilla Qud zones are 25).</summary>
    public int MapHeight { get; init; }
    /// <summary>
    /// crowd-load open <c>LiquidVolume</c> canal. Null = on (city water lag). False = <c>--no-water</c>.
    /// </summary>
    public bool? WaterFlow { get; init; }
    /// <summary>
    /// crowd-load Yd Freehold-style <c>HydraulicPowerTransmission</c> pipes. Null = on. False = <c>--no-pipes</c>.
    /// </summary>
    public bool? PowerPipes { get; init; }
    /// <summary>Denser pipe lattice (Yd Freehold / <c>--yd</c> / scenario yd-load).</summary>
    public bool YdDense { get; init; }
    /// <summary>Increase worker-placeholder density and fill stress metrics.</summary>
    public bool Stress { get; init; }
    /// <summary>
    /// Named debug scenario (e.g. player-turn-starvation, chargen). Empty = default turn loop.
    /// </summary>
    public string? Scenario { get; init; }
    /// <summary>Chargen genotype (e.g. Mutated Human, True Kin).</summary>
    public string? Genotype { get; init; }
    /// <summary>Chargen subtype — calling (mutant) or caste (True Kin).</summary>
    public string? Subtype { get; init; }
    /// <summary>Chargen character type: New, Pregen, Random, Library, Last.</summary>
    public string? Chartype { get; init; }
    /// <summary>Preset name from EmbarkModules.xml when Chartype=Pregen.</summary>
    public string? Pregen { get; init; }
    /// <summary>Game mode: Classic, Roleplay, Wander, Tutorial, Daily.</summary>
    public string? GameMode { get; init; }
    /// <summary>True Kin starting cybernetic blueprint names (empty = none / +1 Toughness).</summary>
    public IReadOnlyList<string> Cybernetics { get; init; } = Array.Empty<string>();
}

public sealed class SimSnapshot
{
    public int TurnsExecuted { get; init; }
    public IReadOnlyList<string> Log { get; init; } = Array.Empty<string>();
    public IReadOnlyDictionary<string, string> Stats { get; init; } =
        new Dictionary<string, string>();
    public IReadOnlyList<ThreadActionRecord> ThreadActions { get; init; } = Array.Empty<ThreadActionRecord>();
    public IReadOnlyList<TimelineEvent> Timeline { get; init; } = Array.Empty<TimelineEvent>();
    public StressMetrics? Stress { get; init; }
}

/// <summary>
/// Structured sim timeline entry. Kinds: Spawn|Part|Mutation|Energy|BeginTakeAction|EndTurn|Event|Worker|Stress|Refuse|Module|Genotype|Subtype|Chargen|Boot|DataError|DataWarning|Cybernetic|Skill|Attribute|Pregen|Chartype|Location|Worldgen|Zone|GetZone|ResolveCell|GenerateZone|Hang|Builder|Type|Load|Crowd|Input|Lag|CTA|UseEnergy|Diagnose|Suite
/// </summary>
public sealed class TimelineEvent
{
    public int Turn { get; init; }
    public string Kind { get; init; } = "";
    public string Label { get; init; } = "";
    public string Detail { get; init; } = "";
    public int ThreadId { get; init; }
    public DateTimeOffset Timestamp { get; init; }
}

public sealed class StressMetrics
{
    public int Turns { get; init; }
    public int MainTicks { get; init; }
    public int WorkerPlaceholders { get; init; }
    public long ElapsedMs { get; init; }
    public double EventsPerTurn { get; init; }
}

/// <summary>
/// Generic thread-action log for sim debugging. Not tied to any specific mod ThreadingAPI
/// (that remains a separate WIP mod). Hooks can be added later when that mod is ready.
/// </summary>
public sealed class ThreadActionRecord
{
    public DateTimeOffset Timestamp { get; init; }
    public int ThreadId { get; init; }
    public string Action { get; init; } = "";
    public string Detail { get; init; } = "";
}

public interface IThreadActionSink
{
    void Record(ThreadActionRecord record);
    IReadOnlyList<ThreadActionRecord> Snapshot();
    void Clear();
}
