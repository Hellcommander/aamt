using System.Text.Json;
using System.Text.Json.Serialization;

namespace QudLab.Ai;

/// <summary>Ollama HTTP payloads use snake_case (<c>tool_calls</c>, <c>keep_alive</c>).</summary>
public static class OllamaJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };
}

public sealed class OllamaChatRequest
{
    public string Model { get; set; } = "";
    public List<OllamaChatMessage> Messages { get; set; } = new();
    public List<OllamaToolSpec>? Tools { get; set; }
    public bool Stream { get; set; }
    public object? Think { get; set; }
    public string KeepAlive { get; set; } = "10m";
    public object? Options { get; set; }
}

public sealed class OllamaChatResponse
{
    public OllamaChatMessage? Message { get; set; }
    public bool Done { get; set; }
    public string? Error { get; set; }
}

public sealed class OllamaChatMessage
{
    public string Role { get; set; } = "user";
    public string? Content { get; set; }
    public string? Thinking { get; set; }
    public List<OllamaToolCall>? ToolCalls { get; set; }
    public string? ToolName { get; set; }
    /// <summary>OpenAI/SGLang tool result pairing (<c>tool_call_id</c>).</summary>
    public string? ToolCallId { get; set; }
}

public sealed class OllamaToolCall
{
    public string? Id { get; set; }
    public OllamaToolFunction? Function { get; set; }
}

public sealed class OllamaToolFunction
{
    public string Name { get; set; } = "";
    public JsonElement Arguments { get; set; }
}

public sealed class OllamaToolSpec
{
    public string Type { get; set; } = "function";
    public OllamaToolFn Function { get; set; } = new();
}

public sealed class OllamaToolFn
{
    public string Name { get; set; } = "";
    public string Description { get; set; } = "";
    public object? Parameters { get; set; }
}

public sealed class OllamaGenerateRequest
{
    public string Model { get; set; } = "";
    public string Prompt { get; set; } = "";
    public string? System { get; set; }
    public bool Stream { get; set; }
    public object? Think { get; set; }
    public string KeepAlive { get; set; } = "10m";
    public object? Format { get; set; }
    public object? Options { get; set; }
}

public sealed class OllamaGenerateResponse
{
    public string? Response { get; set; }
    public string? Thinking { get; set; }
    public bool Done { get; set; }
    public string? Error { get; set; }
}
