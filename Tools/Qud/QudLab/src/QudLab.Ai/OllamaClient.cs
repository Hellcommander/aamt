using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace QudLab.Ai;

/// <summary>
/// Official Ollama HTTP API: https://github.com/ollama/ollama
/// Base URL default <c>http://127.0.0.1:11434</c> (override with OLLAMA_HOST).
/// </summary>
public sealed class OllamaOptions
{
    public string BaseUrl { get; set; } = ResolveHost();
    /// <summary>
    /// Comfortable on 11GB 2080 Ti. Override with QUDLAB_OLLAMA_MODEL.
    /// Pairing: deepseek-r1:7b, qwen3:8b, deepseek-r1:14b (CPU spillover).
    /// </summary>
    public string DefaultModel { get; set; } =
        Environment.GetEnvironmentVariable("QUDLAB_OLLAMA_MODEL") is { Length: > 0 } m
            ? m
            : "deepseek-r1:7b";
    /// <summary>Qwen 3 8B — preferred for /api/chat tool calling on 11GB.</summary>
    public string AlternateModel { get; set; } = "qwen3:8b";
    /// <summary>Fits 11GB only with CPU/RAM spillover (~9GB weights).</summary>
    public string SpilloverModel { get; set; } = "deepseek-r1:14b";
    public int MaxContextChars { get; set; } = 12000;
    public int NumCtx { get; set; } = 8192;
    public int NumPredict { get; set; } = 2048;
    public TimeSpan Timeout { get; set; } = TimeSpan.FromMinutes(10);

    static string ResolveHost()
    {
        var env = Environment.GetEnvironmentVariable("OLLAMA_HOST");
        if (string.IsNullOrWhiteSpace(env))
            return "http://127.0.0.1:11434";
        if (env.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
            env.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            return env.TrimEnd('/');
        return "http://" + env.Trim().TrimEnd('/');
    }
}

public sealed class OllamaClient : ILlmClient
{
    readonly HttpClient _http;
    readonly OllamaOptions _options;

    public OllamaOptions Options => _options;
    public string Backend => "ollama";
    public string BaseUrl => _options.BaseUrl;
    public string DefaultModel => _options.DefaultModel;
    public int MaxContextChars => _options.MaxContextChars;

    public OllamaClient(OllamaOptions? options = null, HttpClient? http = null)
    {
        _options = options ?? new OllamaOptions();
        _http = http ?? new HttpClient { BaseAddress = new Uri(_options.BaseUrl), Timeout = _options.Timeout };
    }

    public async Task<bool> IsAvailableAsync(CancellationToken ct = default)
    {
        try
        {
            using var res = await _http.GetAsync("/api/tags", ct);
            if (res.IsSuccessStatusCode)
                return true;
            using var ping = await _http.GetAsync("/", ct);
            return ping.IsSuccessStatusCode;
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
            using var res = await _http.GetAsync("/api/tags", ct);
            res.EnsureSuccessStatusCode();
            using var doc = await JsonDocument.ParseAsync(await res.Content.ReadAsStreamAsync(ct), cancellationToken: ct);
            var list = new List<string>();
            if (!doc.RootElement.TryGetProperty("models", out var models))
                return list;
            foreach (var m in models.EnumerateArray())
            {
                if (m.TryGetProperty("name", out var n))
                {
                    var name = n.GetString();
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

    /// <summary>Prefer a locally installed model; never trigger a silent <c>ollama pull</c>.</summary>
    public async Task<(string model, string? error)> ResolveModelAsync(string? requested, CancellationToken ct = default)
    {
        var installed = await ListModelsAsync(ct);
        if (installed.Count == 0)
            return ("", "No Ollama models installed. Run: ollama pull qwen3:8b && ollama pull deepseek-r1:7b");

        bool Has(string name) =>
            installed.Any(m => m.Equals(name, StringComparison.OrdinalIgnoreCase));

        string? Find(params string[] wants)
        {
            foreach (var w in wants)
            {
                var exact = installed.FirstOrDefault(m => m.Equals(w, StringComparison.OrdinalIgnoreCase));
                if (exact is not null) return exact;
                var prefix = installed.FirstOrDefault(m =>
                    m.StartsWith(w + ":", StringComparison.OrdinalIgnoreCase) ||
                    m.StartsWith(w, StringComparison.OrdinalIgnoreCase));
                if (prefix is not null) return prefix;
            }

            return null;
        }

        if (!string.IsNullOrWhiteSpace(requested))
        {
            if (Has(requested))
                return (requested, null);
            var fuzzy = Find(requested);
            if (fuzzy is not null)
                return (fuzzy, null);
            return ("", $"Model '{requested}' is not installed. Available: {string.Join(", ", installed)}");
        }

        // 11GB 2080 Ti pairing: Qwen 3 8B (tools) → R1 7B (fits VRAM) → R1 14B last (CPU spillover).
        var pick = Find(
            _options.AlternateModel,
            "qwen3:8b",
            "qwen3",
            _options.DefaultModel,
            "deepseek-r1:7b",
            "qwen2.5-coder:7b",
            "llama3.1:8b",
            _options.SpilloverModel,
            "deepseek-r1:14b",
            "codellama");
        return (pick ?? installed[0], null);
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

        var body = new OllamaGenerateRequest
        {
            Model = resolved,
            Prompt = prompt,
            System = system,
            Stream = false,
            Think = false,
            KeepAlive = "10m",
            Format = json ? "json" : null,
            Options = new { temperature = 0.2, num_ctx = _options.NumCtx, num_predict = _options.NumPredict }
        };

        var jsonRes = await PostGenerateAsync(body, withThink: true, ct);
        return StripThink(jsonRes?.Response ?? jsonRes?.Error ?? "");
    }

    public async Task<OllamaChatMessage> ChatAsync(
        IReadOnlyList<OllamaChatMessage> messages,
        string model,
        IReadOnlyList<OllamaToolSpec>? tools = null,
        CancellationToken ct = default)
    {
        var body = new OllamaChatRequest
        {
            Model = model,
            Messages = messages.ToList(),
            Tools = tools is { Count: > 0 } ? tools.ToList() : null,
            Stream = false,
            Think = false,
            KeepAlive = "10m",
            Options = new { temperature = 0.2, num_ctx = _options.NumCtx, num_predict = _options.NumPredict }
        };

        var res = await PostChatAsync(body, withThink: true, ct);
        var msg = res.Message ?? new OllamaChatMessage { Role = "assistant", Content = res.Error ?? "" };
        if (!string.IsNullOrEmpty(msg.Content))
            msg.Content = StripThink(msg.Content);
        return msg;
    }

    async Task<OllamaGenerateResponse?> PostGenerateAsync(OllamaGenerateRequest body, bool withThink, CancellationToken ct)
    {
        if (!withThink)
            body.Think = null;
        using var res = await _http.PostAsJsonAsync("/api/generate", body, OllamaJson.Options, ct);
        var text = await res.Content.ReadAsStringAsync(ct);
        if ((int)res.StatusCode == 400 && withThink)
            return await PostGenerateAsync(body, withThink: false, ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException($"Ollama /api/generate HTTP {(int)res.StatusCode}: {Truncate(text, 800)}");
        return JsonSerializer.Deserialize<OllamaGenerateResponse>(text, OllamaJson.Options);
    }

    async Task<OllamaChatResponse> PostChatAsync(OllamaChatRequest body, bool withThink, CancellationToken ct)
    {
        if (!withThink)
            body.Think = null;
        using var res = await _http.PostAsJsonAsync("/api/chat", body, OllamaJson.Options, ct);
        var text = await res.Content.ReadAsStringAsync(ct);
        if ((int)res.StatusCode == 400 && withThink)
            return await PostChatAsync(body, withThink: false, ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException($"Ollama /api/chat HTTP {(int)res.StatusCode}: {Truncate(text, 800)}");
        return JsonSerializer.Deserialize<OllamaChatResponse>(text, OllamaJson.Options)
               ?? new OllamaChatResponse { Error = "empty chat response" };
    }

    public static string StripThink(string s)
    {
        if (string.IsNullOrEmpty(s))
            return s;
        s = Regex.Replace(s, "<think>[\\s\\S]*?</think>", "", RegexOptions.IgnoreCase);
        var open = s.IndexOf("<think>", StringComparison.OrdinalIgnoreCase);
        if (open >= 0)
            s = s[..open];
        return s.Trim();
    }

    public static string Truncate(string s, int max) =>
        string.IsNullOrEmpty(s) ? "" : (s.Length <= max ? s : s[..max] + "…");
}
