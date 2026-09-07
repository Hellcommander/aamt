using QudLab.Core;
using QudLab.Core.Abstractions;
using QudLab.Core.Cache;

namespace QudLab.Simulator;

/// <summary>
/// MIT stub compiled only when the private simulator pack is absent.
/// Does not load or run Caves of Qud. Install the compiled pack via
/// Fetch-PrivatePack.ps1 (QudLab.Simulator.Private.dll).
/// </summary>
public sealed class RestrictedSimulator : IRestrictedSimulator
{
    public RestrictedSimulator(
        LabHost host,
        IThreadActionSink? threads = null,
        Func<IntelligenceCache?>? cacheProvider = null)
    {
        _ = host;
        _ = threads;
        _ = cacheProvider;
    }

    public bool IsReady => false;

    public string Status =>
        "Private Qud Lab simulator pack is not installed. " +
        "Clone access to AAMT does not include this component. " +
        "See src/QudLab.Simulator/README.md and LICENSE-PROPRIETARY.md.";

    public Task<SimSnapshot> RunTurnsAsync(SimRequest request, CancellationToken ct = default)
    {
        _ = request;
        ct.ThrowIfCancellationRequested();
        return Task.FromResult(Refuse());
    }

    public void ApplySnapshotToCache(IntelligenceCache cache, SimSnapshot snap, string? scenario = null)
    {
        _ = cache;
        _ = snap;
        _ = scenario;
    }

    static SimSnapshot Refuse() => new()
    {
        TurnsExecuted = 0,
        Log = new[]
        {
            "REFUSED: Qud Lab restricted simulator is download-only. " +
            "Ask the maintainer for the private pack (Fetch-PrivatePack.ps1). " +
            "A legitimate Caves of Qud install is required; game DLLs are never bundled."
        },
        Stats = new Dictionary<string, string> { ["simulator"] = "not-installed" }
    };
}
