namespace QudLab.Ai;

/// <summary>
/// Picks vLLM (Hugging Face models on :8000), SGLang (:30000), or Ollama (:11434).
/// <c>QUDLAB_LLM_BACKEND</c>: <c>auto</c> (default), <c>vllm</c>, <c>sglang</c> / <c>sglang-vllm</c>, <c>ollama</c>.
/// Auto prefers vLLM (:8000), then the SGLang frontend (:30000), then Ollama.
/// <c>sglang</c> is the Windows OpenAI frontend that can proxy vLLM — they do not merge into one runtime.
/// </summary>
public static class LlmClientFactory
{
    public static string PreferredBackend() =>
        (Environment.GetEnvironmentVariable("QUDLAB_LLM_BACKEND") ?? "auto").Trim().ToLowerInvariant();

    public static async Task<ILlmClient> CreateAsync(string? backend = null, CancellationToken ct = default)
    {
        var kind = (backend ?? PreferredBackend()).Trim().ToLowerInvariant();
        if (kind is "vllm")
            return SglangClient.ForVllm();
        if (kind is "sglang" or "sgl" or "hf" or "sglang-vllm" or "stack")
            return new SglangClient();
        if (kind is "ollama")
            return new OllamaClient();

        var vllm = SglangClient.ForVllm();
        if (await vllm.IsAvailableAsync(ct))
            return vllm;
        var sgl = new SglangClient();
        if (await sgl.IsAvailableAsync(ct))
            return sgl;
        return new OllamaClient();
    }
}
