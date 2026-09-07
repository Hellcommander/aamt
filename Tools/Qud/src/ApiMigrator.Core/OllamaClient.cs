using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ApiMigrator.Core;

/// <summary>
/// Ollama HTTP client (<c>/api/tags</c>, <c>/api/chat</c>). Used for leftover-hit
/// leftover rewrites. Default host is local <c>http://localhost:11434</c>.
/// Optional cloud: <c>https://ollama.com</c> with <c>OLLAMA_API_KEY</c> (or an explicit key).
/// Local <c>*-cloud</c> models still work on localhost after <c>ollama signin</c> / <c>ollama pull</c>.
/// </summary>
public static class OllamaClient
{
    public const string DefaultBaseUrl = "http://localhost:11434";
    public const string CloudBaseUrl = "https://ollama.com";
    public const string DefaultModel = "llama3.1";
    /// <summary>Fast free-tier cloud default for leftover DidX batches (code / structured JSON).</summary>
    public const string DefaultCloudModel = "gpt-oss:20b";
    public const string ApiKeyEnvVar = "OLLAMA_API_KEY";

    /// <summary>Free-tier ollama.com cloud models, with capability notes for leftover suggest.</summary>
    public static readonly CloudModelProfile[] CloudModelProfiles =
    {
        new()
        {
            Id = "gemma4:31b",
            Title = "Gemma-4 31B",
            Context = "256K",
            OneLiner = "multimodal (vision+audio+text); strong reasoning; coding/modding/assets",
            Summary =
                "Multimodal (vision + audio + text). Strong reasoning, 256K context. " +
                "Beats typical local 7B–70B general intelligence. Best when leftovers involve " +
                "mixed media or you want a strong all-rounder.",
        },
        new()
        {
            Id = "gpt-oss:120b",
            Title = "GPT-OSS 120B",
            Context = "large",
            OneLiner = "frontier reasoning (MoE); slower; GPT-4-class on many tasks",
            Summary =
                "Frontier-tier MoE reasoning. Comparable to GPT-4-class on many tasks; " +
                "no local model comes close. Use for hard leftover hits when 20B is unsure.",
        },
        new()
        {
            Id = "gpt-oss:20b",
            Title = "GPT-OSS 20B",
            Context = "fast",
            OneLiner = "recommended leftover default — very fast; code/logic/structured JSON",
            Summary =
                "Mid-range reasoning and very fast. Good for code, logic, and structured tasks; " +
                "beats local 13B–20B. Default for leftover DidX / GameText batches.",
        },
        new()
        {
            Id = "nemotron-3-nano:30b",
            Title = "Nemotron-3 Nano 30B",
            Context = "1M",
            OneLiner = "agentic; 1M context; multi-token prediction",
            Summary =
                "Nemotron-3 family: agentic, long-context (1M), multi-token prediction. " +
                "Nano is the lighter of Super/Ultra. Designed for automation, planning, " +
                "and multi-step reasoning — overkill for a single call-site rewrite, useful " +
                "if you paste a large file.",
        },
        new()
        {
            Id = "nemotron-3-super",
            Title = "Nemotron-3 Super",
            Context = "1M",
            OneLiner = "agentic long-context monster; 1M; planning / multi-step",
            Summary =
                "Agentic, 1M context, multi-token prediction. Built for automation, planning, " +
                "and multi-step reasoning. No local model replicates this behavior.",
        },
        new()
        {
            Id = "nemotron-3-ultra",
            Title = "Nemotron-3 Ultra",
            Context = "1M",
            OneLiner = "largest Nemotron-3; 1M context; multi-step / agentic",
            Summary =
                "Top of the Nemotron-3 cloud line: agentic, 1M context, multi-token prediction. " +
                "Use for the hardest multi-step leftover refactors.",
        },
    };

    public static readonly string[] FreeCloudModels =
        CloudModelProfiles.Select(p => p.Id).ToArray();

    static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public static bool IsCloudHost(string? baseUrl)
    {
        var u = NormalizeBase(baseUrl);
        return u.Contains("ollama.com", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsLocalHost(string? baseUrl)
    {
        var u = NormalizeBase(baseUrl);
        return u.Contains("localhost", StringComparison.OrdinalIgnoreCase)
            || u.Contains("127.0.0.1", StringComparison.Ordinal)
            || u.Contains("[::1]", StringComparison.OrdinalIgnoreCase);
    }

    public static string ResolveApiKey(string? explicitKey = null)
    {
        if (!string.IsNullOrWhiteSpace(explicitKey))
            return explicitKey.Trim();
        return (Environment.GetEnvironmentVariable(ApiKeyEnvVar) ?? "").Trim();
    }

    public static bool EnvApiKeyIsSet() =>
        !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(ApiKeyEnvVar));

    /// <summary>
    /// When <see cref="OllamaOptions.UseCloud"/> is set, switch localhost → ollama.com,
    /// pick a cloud default model, and load <c>OLLAMA_API_KEY</c>. Strips a trailing
    /// <c>-cloud</c> suffix for the direct cloud host (local proxy keeps the suffix).
    /// </summary>
    public static void ApplyHostDefaults(OllamaOptions options)
    {
        if (options is null) return;
        if (options.UseCloud && IsLocalHost(options.BaseUrl))
            options.BaseUrl = CloudBaseUrl;
        options.BaseUrl = NormalizeBase(options.BaseUrl);
        options.ApiKey = ResolveApiKey(options.ApiKey);
        if (options.UseCloud &&
            (string.IsNullOrWhiteSpace(options.Model) ||
             options.Model.Equals(DefaultModel, StringComparison.OrdinalIgnoreCase)))
        {
            options.Model = DefaultCloudModel;
        }
        if (!string.IsNullOrWhiteSpace(options.Model))
            options.Model = NormalizeModelForHost(options.Model, options.BaseUrl);
    }

    public static CloudModelProfile? FindCloudProfile(string? model)
    {
        if (string.IsNullOrWhiteSpace(model)) return null;
        var n = NormalizeModelForHost(model.Trim(), CloudBaseUrl);
        return CloudModelProfiles.FirstOrDefault(p =>
            TagMatches(p.Id, n) || TagMatches(n, p.Id));
    }

    public static string DescribeCloudModel(string? model)
    {
        var p = FindCloudProfile(model);
        if (p is null) return "";
        return $"{p.Title} ({p.Context}) — {p.Summary}";
    }

    public static string FormatFreeCloudCatalog()
    {
        var sb = new StringBuilder();
        foreach (var p in CloudModelProfiles)
            sb.Append(p.Id).Append(" — ").AppendLine(p.OneLiner);
        return sb.ToString().TrimEnd();
    }

    public static bool IsFreeCloudModel(string? model)
    {
        if (string.IsNullOrWhiteSpace(model)) return false;
        var n = NormalizeModelForHost(model.Trim(), CloudBaseUrl);
        return FreeCloudModels.Any(f => TagMatches(f, n) || TagMatches(n, f));
    }

    /// <summary>
    /// Free-tier tags first (documented order), then any extra discovered names.
    /// </summary>
    public static List<string> MergeCloudCatalog(IEnumerable<string>? discovered)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var list = new List<string>();
        foreach (var m in FreeCloudModels)
        {
            if (seen.Add(m))
                list.Add(m);
        }
        if (discovered is null) return list;
        foreach (var raw in discovered)
        {
            var n = (raw ?? "").Trim();
            if (n.Length == 0) continue;
            n = NormalizeModelForHost(n, CloudBaseUrl);
            if (seen.Add(n))
                list.Add(n);
        }
        return list;
    }

    public static string NormalizeModelForHost(string model, string? baseUrl)
    {
        var m = (model ?? "").Trim();
        if (m.Length == 0) return m;
        if (IsCloudHost(baseUrl) &&
            m.EndsWith("-cloud", StringComparison.OrdinalIgnoreCase) &&
            m.Length > 6)
        {
            return m[..^6];
        }
        return m;
    }

    public static async Task<OllamaStatus> ProbeAsync(OllamaOptions options, CancellationToken ct = default)
    {
        options ??= new OllamaOptions();
        ApplyHostDefaults(options);
        var timeout = IsCloudHost(options.BaseUrl) ? 10_000 : 4000;
        return await ProbeAsync(options.BaseUrl, timeout, ct, options.ApiKey).ConfigureAwait(false);
    }

    public static async Task<OllamaStatus> ProbeAsync(
        string? baseUrl = null, int timeoutMs = 4000, CancellationToken ct = default, string? apiKey = null)
    {
        var url = NormalizeBase(baseUrl);
        var key = ResolveApiKey(apiKey);
        var cloud = IsCloudHost(url);
        try
        {
            using var http = CreateHttp(timeoutMs, key);
            using var resp = await http.GetAsync(url + "/api/tags", ct).ConfigureAwait(false);
            var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            if (!resp.IsSuccessStatusCode)
            {
                var err = $"HTTP {(int)resp.StatusCode}: {TrimErr(body)}";
                if (cloud && resp.StatusCode is System.Net.HttpStatusCode.Unauthorized
                    or System.Net.HttpStatusCode.Forbidden)
                {
                    err += " — set OLLAMA_API_KEY or pass an API key (https://ollama.com/settings/keys).";
                }
                return new OllamaStatus
                {
                    Available = false,
                    BaseUrl = url,
                    Cloud = cloud,
                    Error = err,
                };
            }

            var tags = JsonSerializer.Deserialize<TagsResponse>(body, JsonOpts);
            var models = tags?.Models?
                .Select(m => m.Name ?? "")
                .Where(n => n.Length > 0)
                .Select(n => NormalizeModelForHost(n, url))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList() ?? new List<string>();
            if (cloud)
                models = MergeCloudCatalog(models);
            else
                models.Sort(StringComparer.OrdinalIgnoreCase);
            return new OllamaStatus
            {
                Available = true,
                BaseUrl = url,
                Cloud = cloud,
                Models = models,
            };
        }
        catch (Exception ex)
        {
            return new OllamaStatus
            {
                Available = false,
                BaseUrl = url,
                Cloud = cloud,
                Error = ex.GetBaseException().Message,
            };
        }
    }

    /// <summary>
    /// Pick an installed tag that matches <paramref name="requested"/> (<c>llama3.1</c> vs
    /// <c>llama3.1:latest</c>). Falls back to a coding-friendly installed model, then the first tag.
    /// </summary>
    public static string ResolveModel(OllamaStatus status, string? requested)
    {
        var want = string.IsNullOrWhiteSpace(requested)
            ? (status.Cloud ? DefaultCloudModel : DefaultModel)
            : requested.Trim();
        if (status?.Models is null || status.Models.Count == 0)
            return want;

        if (status.Cloud)
            want = NormalizeModelForHost(want, CloudBaseUrl);

        // Keep an explicit free-tier id (gpt-oss:20b vs gpt-oss:120b) even if /api/tags omitted it.
        if (status.Cloud && IsFreeCloudModel(want))
        {
            var exact = status.Models.FirstOrDefault(m =>
                m.Equals(want, StringComparison.OrdinalIgnoreCase));
            return exact ?? want;
        }

        var hit = status.Models.FirstOrDefault(m => TagMatches(m, want));
        if (hit is not null) return hit;

        if (!want.Contains(':'))
        {
            hit = status.Models.FirstOrDefault(m => TagMatches(m, want));
            if (hit is not null) return hit;
        }

        string[] preferred = status.Cloud
            ? FreeCloudModels
            : new[]
            {
                "llama3.1", "llama3.2", "llama3", "qwen2.5-coder", "qwen2.5",
                "codellama", "mistral", "gemma2", "phi3", "phi4",
            };
        foreach (var p in preferred)
        {
            hit = status.Models.FirstOrDefault(m =>
                m.Equals(p, StringComparison.OrdinalIgnoreCase) || TagMatches(m, p));
            if (hit is not null) return hit;
        }

        return status.Models[0];
    }

    static bool TagMatches(string installed, string requested)
    {
        if (string.IsNullOrEmpty(installed) || string.IsNullOrEmpty(requested))
            return false;
        if (installed.Equals(requested, StringComparison.OrdinalIgnoreCase))
            return true;
        // llama3.1 matches llama3.1:latest — not gpt-oss:20b vs gpt-oss:120b
        if (installed.StartsWith(requested + ":", StringComparison.OrdinalIgnoreCase))
            return true;
        if (requested.StartsWith(installed + ":", StringComparison.OrdinalIgnoreCase))
            return true;
        return false;
    }

    public static async Task<string> ChatAsync(
        string prompt,
        string? system = null,
        string? model = null,
        string? baseUrl = null,
        int timeoutMs = 180_000,
        float temperature = 0.1f,
        int maxTokens = 800,
        bool jsonFormat = true,
        string? apiKey = null,
        CancellationToken ct = default)
    {
        var url = NormalizeBase(baseUrl);
        var chosen = string.IsNullOrWhiteSpace(model) ? DefaultModel : model.Trim();
        chosen = NormalizeModelForHost(chosen, url);
        var key = ResolveApiKey(apiKey);
        if (IsCloudHost(url) && string.IsNullOrWhiteSpace(key))
        {
            throw new InvalidOperationException(
                "Ollama Cloud requires an API key. Set OLLAMA_API_KEY or pass --api-key " +
                "(https://ollama.com/settings/keys). Or uncheck Cloud and use localhost " +
                "with a pulled *-cloud model after `ollama signin`.");
        }

        try
        {
            return await PostChatAsync(url, chosen, prompt, system, timeoutMs, temperature, maxTokens, jsonFormat, key, ct)
                .ConfigureAwait(false);
        }
        catch (InvalidOperationException ex) when (jsonFormat && LooksLikeFormatError(ex))
        {
            return await PostChatAsync(url, chosen, prompt, system, timeoutMs, temperature, maxTokens, jsonFormat: false, key, ct)
                .ConfigureAwait(false);
        }
        catch (InvalidOperationException ex) when (LooksLikeMissingChat(ex))
        {
            return await PostGenerateAsync(url, chosen, prompt, system, timeoutMs, temperature, maxTokens, jsonFormat: false, key, ct)
                .ConfigureAwait(false);
        }
    }

    public static Task<string> ChatAsync(
        OllamaOptions options,
        string prompt,
        string? system = null,
        bool? jsonFormat = null,
        CancellationToken ct = default)
    {
        options ??= new OllamaOptions();
        ApplyHostDefaults(options);
        return ChatAsync(
            prompt,
            system,
            options.Model,
            options.BaseUrl,
            options.TimeoutMs,
            temperature: 0.1f,
            maxTokens: 700,
            jsonFormat: jsonFormat ?? options.JsonFormat,
            apiKey: options.ApiKey,
            ct: ct);
    }

    static async Task<string> PostChatAsync(
        string url, string model, string prompt, string? system,
        int timeoutMs, float temperature, int maxTokens, bool jsonFormat, string? apiKey, CancellationToken ct)
    {
        var messages = new List<object>();
        if (!string.IsNullOrWhiteSpace(system))
            messages.Add(new { role = "system", content = system });
        messages.Add(new { role = "user", content = prompt });

        var payload = new Dictionary<string, object?>
        {
            ["model"] = model,
            ["messages"] = messages,
            ["stream"] = false,
            ["options"] = new Dictionary<string, object?>
            {
                ["temperature"] = temperature,
                ["num_predict"] = maxTokens,
            },
        };
        if (jsonFormat)
            payload["format"] = "json";

        var body = await PostJsonAsync(url + "/api/chat", payload, timeoutMs, apiKey, ct).ConfigureAwait(false);
        using var doc = JsonDocument.Parse(body);
        if (doc.RootElement.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.String)
            throw new InvalidOperationException("Ollama: " + err.GetString());
        if (doc.RootElement.TryGetProperty("message", out var msg) &&
            msg.TryGetProperty("content", out var c))
            return c.GetString() ?? "";
        return body;
    }

    static async Task<string> PostGenerateAsync(
        string url, string model, string prompt, string? system,
        int timeoutMs, float temperature, int maxTokens, bool jsonFormat, string? apiKey, CancellationToken ct)
    {
        var full = string.IsNullOrWhiteSpace(system) ? prompt : system.Trim() + "\n\n" + prompt;
        var payload = new Dictionary<string, object?>
        {
            ["model"] = model,
            ["prompt"] = full,
            ["stream"] = false,
            ["options"] = new Dictionary<string, object?>
            {
                ["temperature"] = temperature,
                ["num_predict"] = maxTokens,
            },
        };
        if (jsonFormat)
            payload["format"] = "json";

        var body = await PostJsonAsync(url + "/api/generate", payload, timeoutMs, apiKey, ct).ConfigureAwait(false);
        using var doc = JsonDocument.Parse(body);
        if (doc.RootElement.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.String)
            throw new InvalidOperationException("Ollama: " + err.GetString());
        if (doc.RootElement.TryGetProperty("response", out var resp))
            return resp.GetString() ?? "";
        return body;
    }

    static async Task<string> PostJsonAsync(
        string endpoint, Dictionary<string, object?> payload, int timeoutMs, string? apiKey, CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(payload, JsonOpts);
        using var http = CreateHttp(timeoutMs, apiKey);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var resp = await http.PostAsync(endpoint, content, ct).ConfigureAwait(false);
        var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode)
            throw new InvalidOperationException($"Ollama {new Uri(endpoint).AbsolutePath} HTTP {(int)resp.StatusCode}: {TrimErr(body)}");
        return body;
    }

    static bool LooksLikeFormatError(Exception ex)
    {
        var m = ex.Message ?? "";
        return m.Contains("400", StringComparison.Ordinal)
            || m.Contains("format", StringComparison.OrdinalIgnoreCase)
            || m.Contains("does not support", StringComparison.OrdinalIgnoreCase);
    }

    static bool LooksLikeMissingChat(Exception ex)
    {
        var m = ex.Message ?? "";
        return m.Contains("404", StringComparison.Ordinal)
            || m.Contains("/api/chat", StringComparison.OrdinalIgnoreCase);
    }

    static HttpClient CreateHttp(int timeoutMs, string? apiKey = null)
    {
        var http = new HttpClient { Timeout = TimeSpan.FromMilliseconds(Math.Max(1000, timeoutMs)) };
        http.DefaultRequestHeaders.TryAddWithoutValidation("Accept", "application/json");
        if (!string.IsNullOrWhiteSpace(apiKey))
            http.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", "Bearer " + apiKey.Trim());
        return http;
    }

    static string NormalizeBase(string? baseUrl)
    {
        var u = string.IsNullOrWhiteSpace(baseUrl) ? DefaultBaseUrl : baseUrl.Trim();
        return u.TrimEnd('/');
    }

    static string TrimErr(string body)
    {
        var t = (body ?? "").Trim();
        if (t.Length > 240) t = t[..237] + "...";
        return t;
    }

    sealed class TagsResponse
    {
        [JsonPropertyName("models")] public List<TagModel>? Models { get; set; }
    }

    sealed class TagModel
    {
        [JsonPropertyName("name")] public string? Name { get; set; }
    }
}

public sealed class OllamaStatus
{
    public bool Available { get; set; }
    public string BaseUrl { get; set; } = OllamaClient.DefaultBaseUrl;
    public bool Cloud { get; set; }
    public List<string> Models { get; set; } = new();
    public string? Error { get; set; }

    public string Summary => Available
        ? (Cloud ? "Ollama Cloud" : "Ollama") + $" at {BaseUrl} — {Models.Count} model(s)"
            + (Models.Count > 0 ? ": " + string.Join(", ", Models.Take(6)) : "")
        : (Cloud ? "Ollama Cloud" : "Ollama") + $" not reachable at {BaseUrl}"
            + (string.IsNullOrEmpty(Error) ? "" : " (" + Error + ")");
}

public sealed class OllamaOptions
{
    public string BaseUrl { get; set; } = OllamaClient.DefaultBaseUrl;
    public string Model { get; set; } = OllamaClient.DefaultModel;
    public int TimeoutMs { get; set; } = 180_000;
    public int MaxHits { get; set; } = 12;
    /// <summary>Ask Ollama for JSON. Some models reject <c>format=json</c>; ChatAsync retries without it.</summary>
    public bool JsonFormat { get; set; } = true;
    /// <summary>Use https://ollama.com (direct cloud API). Local *-cloud models do not need this.</summary>
    public bool UseCloud { get; set; }
    /// <summary>Bearer token for ollama.com. Falls back to OLLAMA_API_KEY.</summary>
    public string? ApiKey { get; set; }
}

public sealed class CloudModelProfile
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public string Context { get; init; } = "";
    public string OneLiner { get; init; } = "";
    public string Summary { get; init; } = "";
}
