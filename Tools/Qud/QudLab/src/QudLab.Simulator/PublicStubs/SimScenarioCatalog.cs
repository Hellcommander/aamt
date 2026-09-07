namespace QudLab.Simulator;

/// <summary>MIT catalog stub. Full scenario list ships in the private pack.</summary>
public static class SimScenarioCatalog
{
    public static IReadOnlyList<SimScenarioInfo> All { get; } =
    [
        new SimScenarioInfo
        {
            Id = "",
            Label = "Simulator pack not installed",
            Description = "Restricted Caves of Qud simulator is download-only. See README.md in this folder.",
            SupportsStress = false
        }
    ];
}

public sealed class SimScenarioInfo
{
    public required string Id { get; init; }
    public required string Label { get; init; }
    public required string Description { get; init; }
    public bool SupportsStress { get; init; }
}
