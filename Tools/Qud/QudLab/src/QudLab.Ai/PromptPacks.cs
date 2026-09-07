namespace QudLab.Ai;

public static class PromptPacks
{
    public static string? Load(string labRoot, string task)
    {
        var name = task.Trim().ToLowerInvariant() switch
        {
            "part" => "part.md",
            "mutation" => "mutation.md",
            "blueprint" or "bp" => "blueprint.md",
            "fix" => "fix.md",
            "scan" => "scan.md",
            "analyze" or "sim" or "simulation" => "analyze.md",
            "agent" or "ask" or "mod-help" => "agent.md",
            _ => "agent.md"
        };
        var path = Path.Combine(labRoot, "docs", "prompts", name);
        return File.Exists(path) ? File.ReadAllText(path) : null;
    }
}
