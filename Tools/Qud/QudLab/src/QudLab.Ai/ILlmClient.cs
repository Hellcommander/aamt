namespace QudLab.Ai;

/// <summary>
/// Local LLM used by the Qud Lab agent. Implementations: Ollama (<c>/api/chat</c>)
/// and SGLang (OpenAI-compatible <c>/v1/chat/completions</c>, Hugging Face model ids).
/// </summary>
public interface ILlmClient
{
    /// <summary><c>vllm</c>, <c>sglang</c>, or <c>ollama</c>.</summary>
    string Backend { get; }
    string BaseUrl { get; }
    string DefaultModel { get; }
    int MaxContextChars { get; }

    Task<bool> IsAvailableAsync(CancellationToken ct = default);
    Task<IReadOnlyList<string>> ListModelsAsync(CancellationToken ct = default);
    Task<(string model, string? error)> ResolveModelAsync(string? requested, CancellationToken ct = default);
    Task<string> GenerateAsync(
        string prompt,
        string? model = null,
        string? system = null,
        bool json = false,
        CancellationToken ct = default);
    Task<OllamaChatMessage> ChatAsync(
        IReadOnlyList<OllamaChatMessage> messages,
        string model,
        IReadOnlyList<OllamaToolSpec>? tools = null,
        CancellationToken ct = default);
}
