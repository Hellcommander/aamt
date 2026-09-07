namespace QudLab.Simulator;

/// <summary>MIT catalog. Full list is loaded from the private pack DLL when present.</summary>
public static class SimScenarioCatalog
{
    public static IReadOnlyList<SimScenarioInfo> Fallback { get; } =
    [
        new SimScenarioInfo
        {
            Id = "",
            Label = "Simulator pack not installed",
            Description = "Restricted Caves of Qud simulator is download-only. See README.md in this folder.",
            SupportsStress = false
        }
    ];

    public static IReadOnlyList<SimScenarioInfo> All => SimulatorFactory.GetScenarios();
}

public sealed class SimScenarioInfo
{
    public required string Id { get; init; }
    public required string Label { get; init; }
    public required string Description { get; init; }
    public bool SupportsStress { get; init; }
}
