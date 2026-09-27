using System.Net.Http.Json;
using System.Text.Json;

namespace QudLab.Ai;

/// <summary>
/// SGLang OpenAI-compatible HTTP API (v0.5.19+). Default <c>http://127.0.0.1:30000</c>.
/// Slot a Hugging Face id on vLLM in WSL, then optionally a Windows SGLang frontend:
/// <c>qudlab vllm serve --model org/name</c> then <c>qudlab sglang serve --remote</c>.
/// </summary>
public sealed class SglangOptions
{
    public string BaseUrl { get; set; } = ResolveHost();
    /// <summary>
    /// Hugging Face repo id or local snapshot. Override with <c>QUDLAB_SGLANG_MODEL</c>
    /// / <c>QUDLAB_HF_MODEL</c>. 11GB 2080 Ti: 3B BF16 or 7B AWQ/GPTQ.
    /// </summary>
    public string DefaultModel { get; set; } =
        FirstEnv("QUDLAB_SGLANG_MODEL", "QUDLAB_HF_MODEL") ?? "Qwen/Qwen2.5-3B-Instruct";
    public int MaxContextChars { get; set; } = 12000;
    public int NumPredict { get; set; } = 2048;
    public TimeSpan Timeout { get; set; } = TimeSpan.FromMinutes(10);

    public static string ResolveHost() =>
        NormalizeUrl(FirstEnv("QUDLAB_SGLANG_URL", "SGLANG_URL", "SGLANG_HOST") ?? "", "http://127.0.0.1:30000");

    public static string? FirstEnv(params string[] names)
    {
        foreach (var n in names)
        {
            var v = Environment.GetEnvironmentVariable(n);
            if (!string.IsNullOrWhiteSpace(v))
                return v.Trim();
        }

        return null;
    }

    public static string NormalizeUrl(string env, string fallback)
    {
        if (string.IsNullOrWhiteSpace(env))
            return fallback;
        var u = env.Trim().TrimEnd('/');
        if (!u.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
            !u.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            u = "http://" + u;
        // Clients request /v1/models; strip a trailing /v1 so it is not doubled.
        if (u.EndsWith("/v1", StringComparison.OrdinalIgnoreCase))
            u = u[..^3].TrimEnd('/');
        return u;
    }
}

public sealed class SglangClient : ILlmClient
{
    readonly HttpClient _http;
    readonly SglangOptions _options;

    readonly string _backend;

    public SglangOptions Options => _options;
    public string Backend => _backend;
    public string BaseUrl => _options.BaseUrl;
    public string DefaultModel => _options.DefaultModel;
    public int MaxContextChars => _options.MaxContextChars;

    public static SglangClient ForVllm()
    {
        var opt = new SglangOptions
        {
            BaseUrl = SglangOptions.NormalizeUrl(
                SglangOptions.FirstEnv("QUDLAB_VLLM_URL", "VLLM_URL", "VLLM_HOST") ?? "",
                "http://127.0.0.1:8000"),
            DefaultModel = SglangOptions.FirstEnv("QUDLAB_VLLM_MODEL", "QUDLAB_HF_MODEL")
                           ?? "Qwen/Qwen2.5-3B-Instruct"
        };
        return new SglangClient(opt, backend: "vllm");
    }

    public SglangClient(SglangOptions? options = null, HttpClient? http = null, string? backend = null)
    {
        _options = options ?? new SglangOptions();
        _backend = string.IsNullOrWhiteSpace(backend) ? "sglang" : backend;
        _http = http ?? new HttpClient { BaseAddress = new Uri(_options.BaseUrl), Timeout = _options.Timeout };
        var token = Environment.GetEnvironmentVariable("HF_TOKEN")
                    ?? Environment.GetEnvironmentVariable("HUGGING_FACE_HUB_TOKEN");
        if (!string.IsNullOrWhiteSpace(token) && !_http.DefaultRequestHeaders.Contains("Authorization"))
            _http.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", "Bearer " + token);
    }

    public async Task<bool> IsAvailableAsync(CancellationToken ct = default)
    {
        try
        {
            using var models = await _http.GetAsync("/v1/models", ct);
            if (models.IsSuccessStatusCode)
                return true;
            using var health = await _http.GetAsync("/health", ct);
            return health.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<IReadOnlyList<string>> ListModelsAsync(CancellationToken ct = default)
    {
        try
        {
            using var res = await _http.GetAsync("/v1/models", ct);
            res.EnsureSuccessStatusCode();
            using var doc = await JsonDocument.ParseAsync(await res.Content.ReadAsStreamAsync(ct), cancellationToken: ct);
            var list = new List<string>();
            if (!doc.RootElement.TryGetProperty("data", out var data) || data.ValueKind != JsonValueKind.Array)
                return list;
            foreach (var m in data.EnumerateArray())
            {
                if (m.TryGetProperty("id", out var id))
                {
                    var name = id.GetString();
                    if (!string.IsNullOrWhiteSpace(name))
                        list.Add(name);
                }
            }

            return list;
        }
        catch
        {
            return Array.Empty<string>();
        }
    }

    public async Task<(string model, string? error)> ResolveModelAsync(string? requested, CancellationToken ct = default)
    {
        var installed = await ListModelsAsync(ct);
        if (installed.Count == 0)
        {
            if (!await IsAvailableAsync(ct))
            {
                return ("",
                    _backend + " not reachable at " + _options.BaseUrl +
                    (string.Equals(_backend, "vllm", StringComparison.OrdinalIgnoreCase)
                        ? " — start: qudlab vllm serve --model " + _options.DefaultModel
                        : " — start: qudlab sglang serve --remote  (vLLM on :8000)"));
            }

            var fallback = string.IsNullOrWhiteSpace(requested) ? _options.DefaultModel : requested.Trim();
            return (fallback, null);
        }

        bool Match(string have, string want) =>
            have.Equals(want, StringComparison.OrdinalIgnoreCase) ||
            have.EndsWith("/" + want, StringComparison.OrdinalIgnoreCase) ||
            want.EndsWith("/" + have, StringComparison.OrdinalIgnoreCase) ||
            have.Contains(want, StringComparison.OrdinalIgnoreCase) ||
            want.Contains(have, StringComparison.OrdinalIgnoreCase);

        if (!string.IsNullOrWhiteSpace(requested))
        {
            var exact = installed.FirstOrDefault(m => Match(m, requested));
            if (exact is not null)
                return (exact, null);
            // Single-model server: OpenAI `model` is often ignored; use the loaded weights.
            return (installed[0], null);
        }

        var prefer = installed.FirstOrDefault(m => Match(m, _options.DefaultModel));
        return (prefer ?? installed[0], null);
    }

    public async Task<string> GenerateAsync(
        string prompt,
        string? model = null,
        string? system = null,
        bool json = false,
        CancellationToken ct = default)
    {
        var (resolved, err) = await ResolveModelAsync(model, ct);
        if (err is not null)
            throw new InvalidOperationException(err);

        var messages = new List<OllamaChatMessage>();
        if (!string.IsNullOrWhiteSpace(system))
            messages.Add(new OllamaChatMessage { Role = "system", Content = system });
        messages.Add(new OllamaChatMessage { Role = "user", Content = prompt });

        var msg = await ChatCompletionsAsync(messages, resolved, tools: null, json, ct);
        return OllamaClient.StripThink(msg.Content ?? "");
    }

    public Task<OllamaChatMessage> ChatAsync(
        IReadOnlyList<OllamaChatMessage> messages,
        string model,
        IReadOnlyList<OllamaToolSpec>? tools = null,
        CancellationToken ct = default) =>
        ChatCompletionsAsync(messages, model, tools, json: false, ct);

    async Task<OllamaChatMessage> ChatCompletionsAsync(
        IReadOnlyList<OllamaChatMessage> messages,
        string model,
        IReadOnlyList<OllamaToolSpec>? tools,
        bool json,
        CancellationToken ct)
    {
        var payload = new Dictionary<string, object?>
        {
            ["model"] = model,
            ["messages"] = ToOpenAiMessages(messages),
            ["temperature"] = 0.2,
            ["max_tokens"] = _options.NumPredict,
            ["stream"] = false
        };
        if (tools is { Count: > 0 })
            payload["tools"] = tools;
        if (json)
            payload["response_format"] = new { type = "json_object" };

        using var res = await _http.PostAsJsonAsync("/v1/chat/completions", payload, OllamaJson.Options, ct);
        var text = await res.Content.ReadAsStringAsync(ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException($"{_backend} /v1/chat/completions HTTP {(int)res.StatusCode}: {OllamaClient.Truncate(text, 800)}");

        using var doc = JsonDocument.Parse(text);
        if (!doc.RootElement.TryGetProperty("choices", out var choices) ||
            choices.ValueKind != JsonValueKind.Array ||
            choices.GetArrayLength() == 0)
        {
            return new OllamaChatMessage { Role = "assistant", Content = OllamaClient.Truncate(text, 800) };
        }

        var msgEl = choices[0].GetProperty("message");
        var content = msgEl.TryGetProperty("content", out var c) ? c.GetString() : null;
        if (msgEl.TryGetProperty("reasoning_content", out var reason))
        {
            var r = reason.GetString();
            if (!string.IsNullOrWhiteSpace(r) && string.IsNullOrWhiteSpace(content))
                content = r;
        }

        List<OllamaToolCall>? calls = null;
        if (msgEl.TryGetProperty("tool_calls", out var tc) && tc.ValueKind == JsonValueKind.Array)
        {
            calls = new List<OllamaToolCall>();
            foreach (var item in tc.EnumerateArray())
            {
                var id = item.TryGetProperty("id", out var idEl) ? idEl.GetString() : null;
                if (!item.TryGetProperty("function", out var fn))
                    continue;
                var name = fn.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                var args = ParseArgs(fn.TryGetProperty("arguments", out var a) ? a : default);
                calls.Add(new OllamaToolCall
                {
                    Id = id,
                    Function = new OllamaToolFunction { Name = name, Arguments = args }
                });
            }
        }

        return new OllamaChatMessage
        {
            Role = "assistant",
            Content = OllamaClient.StripThink(content ?? ""),
            ToolCalls = calls is { Count: > 0 } ? calls : null
        };
    }

    static List<Dictionary<string, object?>> ToOpenAiMessages(IReadOnlyList<OllamaChatMessage> messages)
    {
        var pending = new Queue<string>();
        var n = 0;
        var list = new List<Dictionary<string, object?>>();
        foreach (var m in messages)
        {
            if (string.Equals(m.Role, "tool", StringComparison.OrdinalIgnoreCase))
            {
                var id = m.ToolCallId;
                if (string.IsNullOrWhiteSpace(id) && pending.Count > 0)
                    id = pending.Dequeue();
                if (string.IsNullOrWhiteSpace(id))
                    id = "call_" + (m.ToolName ?? "tool");
                list.Add(new Dictionary<string, object?>
                {
                    ["role"] = "tool",
                    ["content"] = m.Content ?? "",
                    ["tool_call_id"] = id
                });
                continue;
            }

            if (m.ToolCalls is { Count: > 0 })
            {
                var calls = new List<Dictionary<string, object?>>();
                foreach (var call in m.ToolCalls)
                {
                    var id = string.IsNullOrWhiteSpace(call.Id) ? "call_" + (++n) : call.Id!;
                    call.Id = id;
                    pending.Enqueue(id);
                    calls.Add(new Dictionary<string, object?>
                    {
                        ["id"] = id,
                        ["type"] = "function",
                        ["function"] = new Dictionary<string, object?>
                        {
                            ["name"] = call.Function?.Name ?? "",
                            ["arguments"] = ArgsToString(call.Function?.Arguments)
                        }
                    });
                }

                list.Add(new Dictionary<string, object?>
                {
                    ["role"] = "assistant",
                    ["content"] = m.Content ?? "",
                    ["tool_calls"] = calls
                });
                continue;
            }

            list.Add(new Dictionary<string, object?>
            {
                ["role"] = string.IsNullOrWhiteSpace(m.Role) ? "user" : m.Role,
                ["content"] = m.Content ?? ""
            });
        }

        return list;
    }

    static string ArgsToString(JsonElement? args)
    {
        if (args is not { } el || el.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
            return "{}";
        return el.ValueKind == JsonValueKind.String ? (el.GetString() ?? "{}") : el.GetRawText();
    }

    static JsonElement ParseArgs(JsonElement args)
    {
        try
        {
            if (args.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
                return default;
            if (args.ValueKind == JsonValueKind.String)
            {
                var s = args.GetString();
                if (string.IsNullOrWhiteSpace(s))
                    return default;
                using var doc = JsonDocument.Parse(s);
                return doc.RootElement.Clone();
            }

            return args.Clone();
        }
        catch
        {
            return default;
        }
    }
}
