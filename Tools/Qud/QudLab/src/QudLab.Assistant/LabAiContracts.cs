namespace QudLab.Assistant;

/// <summary>
/// Local Ollama agent (Cursor-like tools) hosted by <c>qudlab serve</c>.
/// </summary>
public interface ILabAiService
{
    Task<AiStatusResult> StatusAsync(CancellationToken ct = default);
    Task<AiAgentResult> RunAsync(AiAgentRequest request, CancellationToken ct = default);
}

public sealed class AiAgentRequest
{
    public string Prompt { get; set; } = "";
    /// <summary>ask | scan | fix | analyze</summary>
    public string Mode { get; set; } = "ask";
    public string? Model { get; set; }
    public bool Apply { get; set; }
    public int MaxRounds { get; set; } = 10;
    public bool Simulate { get; set; }
    public int Turns { get; set; } = 8;
    public string Blueprint { get; set; } = "Human";
}

public sealed class AiAgentResult
{
    public bool Ok { get; set; }
    public string Reply { get; set; } = "";
    public string Model { get; set; } = "";
    public string Mode { get; set; } = "";
    public List<AiToolTrace> Tools { get; set; } = new();
    public List<string> Written { get; set; } = new();
    public bool? Compiled { get; set; }
    public List<string> Diagnostics { get; set; } = new();
    public string? Error { get; set; }
}

public sealed class AiToolTrace
{
    public string Name { get; set; } = "";
    public string Args { get; set; } = "";
    public string ResultPreview { get; set; } = "";
}

public sealed class AiStatusResult
{
    public bool Ollama { get; set; }
    public string BaseUrl { get; set; } = "";
    public string DefaultModel { get; set; } = "";
    public string? ResolvedModel { get; set; }
    public List<string> Models { get; set; } = new();
    public string Hint { get; set; } = "";
}
