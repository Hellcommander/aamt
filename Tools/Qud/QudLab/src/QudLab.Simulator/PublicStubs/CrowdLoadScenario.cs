namespace QudLab.Simulator;

/// <summary>MIT parsing helper. Scenario bodies are private-pack only.</summary>
public static class CrowdLoadScenario
{
    public const string Name = "crowd-load";

    public static bool TryParseMap(string? spec, out int width, out int height)
    {
        width = 0;
        height = 0;
        if (string.IsNullOrWhiteSpace(spec))
            return false;
        var parts = spec.Split(['x', 'X', '*'], StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        return parts.Length == 2
               && int.TryParse(parts[0], out width)
               && int.TryParse(parts[1], out height)
               && width >= 8
               && height >= 8;
    }
}
