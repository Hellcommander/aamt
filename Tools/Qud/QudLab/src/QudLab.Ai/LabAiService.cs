using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using QudLab.Assistant;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.Logs;

namespace QudLab.Ai;

/// <summary>
/// Cursor-style local agent: vLLM / SGLang OpenAI <c>/v1/chat/completions</c> or Ollama <c>/api/chat</c>
/// plus tools (search, scan, compile, simulate, write). Models without native tool_calls
/// fall back to a packed scan + generate.
/// </summary>
public sealed class LabAiService : ILabAiService
{
    readonly ILlmClient _llm;
    readonly Func<IntelligenceCache?> _cache;
    readonly Func<QudInstallInfo?> _install;
    readonly Func<string?, string?> _read;
    readonly Action<string, string>? _write;
    readonly string _labRoot;
    readonly ActiveProjectManager? _projectManager;
    readonly AiContextBuilder _ctx = new();

    public LabAiService(
        ILlmClient llm,
        Func<IntelligenceCache?> cache,
        Func<QudInstallInfo?> install,
        Func<string?, string?> read,
        Action<string, string>? write,
        string labRoot,
        ActiveProjectManager? projectManager = null)
    {
        _llm = llm;
        _cache = cache;
        _install = install;
        _read = read;
        _write = write;
        _labRoot = labRoot;
        _projectManager = projectManager;
    }

    public async Task<AiStatusResult> StatusAsync(CancellationToken ct = default)
    {
        var ok = await _llm.IsAvailableAsync(ct);
        var models = ok ? (await _llm.ListModelsAsync(ct)).ToList() : new List<string>();
        string? resolved = null;
        if (ok)
        {
            var (m, err) = await _llm.ResolveModelAsync(null, ct);
            resolved = err is null ? m : null;
        }

        var backend = _llm.Backend;
        var vllm = string.Equals(backend, "vllm", StringComparison.OrdinalIgnoreCase);
        var sglang = string.Equals(backend, "sglang", StringComparison.OrdinalIgnoreCase);
        var ollama = string.Equals(backend, "ollama", StringComparison.OrdinalIgnoreCase);
        string hint;
        if (ok)
            hint = "POST /ai/run { prompt, mode: ask|scan|fix|analyze }";
        else if (vllm)
            hint = "Start vLLM: qudlab vllm serve --model " + _llm.DefaultModel + "  (" + _llm.BaseUrl + ")";
        else if (sglang || string.Equals(LlmClientFactory.PreferredBackend(), "sglang", StringComparison.OrdinalIgnoreCase))
            hint = "Start SGLang frontend: qudlab sglang serve --remote  (vLLM on :8000)  (" + _llm.BaseUrl + ")";
        else
            hint = "Start vLLM (`qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct`), then optional `qudlab sglang serve --remote`, or Ollama.";
        return new AiStatusResult
        {
            Available = ok,
            Ollama = ok && ollama,
            Sglang = ok && sglang,
            Vllm = ok && vllm,
            Backend = backend,
            BaseUrl = _llm.BaseUrl,
            DefaultModel = _llm.DefaultModel,
            ResolvedModel = resolved,
            Models = models,
            Hint = hint
        };
    }

    public async Task<AiAgentResult> RunAsync(AiAgentRequest request, CancellationToken ct = default)
    {
        var mode = NormalizeMode(request.Mode);
        var apply = request.Apply || mode == "fix";
        var simulate = request.Simulate || mode == "analyze";
        var prompt = string.IsNullOrWhiteSpace(request.Prompt)
            ? DefaultPrompt(mode)
            : request.Prompt.Trim();
        var maxRounds = request.MaxRounds <= 0 ? 10 : Math.Clamp(request.MaxRounds, 1, 16);

        if (!await _llm.IsAvailableAsync(ct))
        {
            return Fail(mode, _llm.Backend + " not reachable at " + _llm.BaseUrl + BackendStartHint(_llm.Backend, _llm.DefaultModel));
        }

        var (model, modelErr) = await _llm.ResolveModelAsync(request.Model, ct);
        if (modelErr is not null)
            return Fail(mode, modelErr);

        var tools = new LabAiTools(_cache, _install, _read, _write, apply, _projectManager);
        var written = new List<string>();
        var trace = new List<AiToolTrace>();
        bool? compiled = null;

        if (simulate && mode is "analyze" or "fix" or "scan")
        {
            var simArgs = JsonSerializer.SerializeToElement(new
            {
                blueprint = string.IsNullOrWhiteSpace(request.Blueprint) ? "Human" : request.Blueprint,
                turns = request.Turns <= 0 ? 8 : request.Turns,
                stress = false
            });
            var simOut = tools.Execute("simulate", simArgs, written, out _);
            trace.Add(new AiToolTrace { Name = "simulate", Args = simArgs.GetRawText(), ResultPreview = Preview(simOut) });
        }

        try
        {
            var reply = await AgentLoopAsync(
                model, mode, prompt, apply, maxRounds, tools, written, trace,
                compiledSetter: v => compiled = v, ct);

            if (apply && _write is not null)
            {
                foreach (var patch in CodePatchParser.Parse(reply))
                {
                    if (written.Contains(patch.Path, StringComparer.OrdinalIgnoreCase))
                        continue;
                    _write(patch.Path, patch.Content);
                    written.Add(patch.Path);
                    trace.Add(new AiToolTrace
                    {
                        Name = "write_file",
                        Args = patch.Path,
                        ResultPreview = "applied from final reply"
                    });
                }
            }

            if (apply && written.Count > 0)
            {
                var compileOut = tools.Execute("compile", default, written, out var touched);
                if (touched)
                    compiled = compileOut.StartsWith("COMPILE OK", StringComparison.Ordinal);
                trace.Add(new AiToolTrace { Name = "compile", Args = "{}", ResultPreview = Preview(compileOut) });
            }

            var diags = _cache()?.Project.Diagnostics ?? new List<string>();
            return new AiAgentResult
            {
                Ok = true,
                Reply = reply,
                Model = model,
                Mode = mode,
                Tools = trace,
                Written = written,
                Compiled = compiled,
                Diagnostics = diags.Take(40).ToList()
            };
        }
        catch (Exception ex)
        {
            return Fail(mode, ex.Message, model, trace, written);
        }
    }

    async Task<string> AgentLoopAsync(
        string model,
        string mode,
        string prompt,
        bool apply,
        int maxRounds,
        LabAiTools tools,
        List<string> written,
        List<AiToolTrace> trace,
        Action<bool> compiledSetter,
        CancellationToken ct)
    {
        var system = BuildSystem(mode, apply);
        var messages = new List<OllamaChatMessage>
        {
            new() { Role = "system", Content = system },
            new() { Role = "user", Content = BuildUser(mode, prompt) }
        };

        var specs = LabAiTools.Specs(apply);
        var usedTools = false;

        for (var round = 0; round < maxRounds; round++)
        {
            var msg = await _llm.ChatAsync(messages, model, specs, ct);
            var calls = msg.ToolCalls is { Count: > 0 }
                ? msg.ToolCalls
                : ParseTextToolCalls(msg.Content);

            if (calls is { Count: > 0 })
            {
                usedTools = true;
                messages.Add(new OllamaChatMessage
                {
                    Role = "assistant",
                    Content = msg.Content ?? "",
                    ToolCalls = calls
                });

                foreach (var call in calls)
                {
                    var name = call.Function?.Name ?? "";
                    var args = call.Function?.Arguments ?? default;
                    var result = tools.Execute(name, args, written, out var compiledTouched);
                    if (compiledTouched)
                        compiledSetter(result.StartsWith("COMPILE OK", StringComparison.Ordinal));
                    trace.Add(new AiToolTrace
                    {
                        Name = name,
                        Args = ArgsPreview(args),
                        ResultPreview = Preview(result)
                    });
                    messages.Add(new OllamaChatMessage
                    {
                        Role = "tool",
                        ToolName = name,
                        ToolCallId = call.Id,
                        Content = OllamaClient.Truncate(result, 8000)
                    });
                }

                continue;
            }

            if (!string.IsNullOrWhiteSpace(msg.Content))
                return msg.Content!;

            break;
        }

        if (!usedTools)
            return await PackedFallbackAsync(model, mode, prompt, tools, trace, ct);

        return "Stopped after max tool rounds without a final answer. See tool trace.";
    }

    async Task<string> PackedFallbackAsync(
        string model,
        string mode,
        string prompt,
        LabAiTools tools,
        List<AiToolTrace> trace,
        CancellationToken ct)
    {
        var scan = tools.ScanProject();
        trace.Add(new AiToolTrace { Name = "scan_project", Args = "{}", ResultPreview = Preview(scan) });
        var compileOut = tools.Execute("compile", default, new List<string>(), out _);
        trace.Add(new AiToolTrace { Name = "compile", Args = "{}", ResultPreview = Preview(compileOut) });

        var cache = _cache();
        var hits = new List<SearchHit>();
        foreach (var sym in AiContextBuilder.ExtractSymbols(prompt + "\n" + compileOut))
            hits.AddRange(CacheSearch.SearchHits(cache, sym, 8));
        hits = hits.DistinctBy(h => h.Kind + h.Id).Take(24).ToList();

        var pack = PromptPacks.Load(_labRoot, mode) ?? PromptPacks.Load(_labRoot, "agent");
        var packed = _ctx.Build(
            cache,
            mode,
            prompt + "\n\n--- scan_project ---\n" + OllamaClient.Truncate(scan, 8000)
                   + "\n\n--- compile ---\n" + compileOut,
            hits,
            pack,
            maxChars: _llm.MaxContextChars);

        return await _llm.GenerateAsync(packed, model, system: pack, json: false, ct);
    }

    string BuildSystem(string mode, bool apply)
    {
        var sb = new StringBuilder();
        sb.AppendLine("You are the Qud Lab local coding agent on a SMALL GPU model (" + _llm.Backend + " @ " + _llm.BaseUrl + ").");
        sb.AppendLine("No big AI toolset (no Task/subagents/ollama-suggest/scan_project dumps). Programmatic tools only.");
        sb.AppendLine("Mod-fix loop: list_mods → set_project (LocalLow/Workshop) → api_migrate → compile → grep/read only listed paths → write_file → compile.");
        sb.AppendLine("api_migrate is ApiMigrator (deterministic). Dry-run first; apply=true only in fix mode. Never invent XRL names — search/lookup_type.");
        sb.AppendLine("For MODERROR type conflicts: mod_errors FIRST, then set_project, api_migrate, compile.");
        sb.AppendLine("For runtime/turn bugs: game_logs then simulate (analyze mode). Avoid scan_project.");
        sb.AppendLine("When fixing, write COMPLETE files via write_file, then compile. PreferXML → Harmony → override only if required.");
        if (!apply)
            sb.AppendLine("Writes are disabled this turn — propose edits in fenced FILE: path blocks; api_migrate apply is blocked.");
        var extra = PromptPacks.Load(_labRoot, mode) ?? PromptPacks.Load(_labRoot, "agent");
        if (!string.IsNullOrWhiteSpace(extra))
        {
            sb.AppendLine();
            sb.AppendLine(extra.Trim());
        }

        return sb.ToString();
    }

    static string BuildUser(string mode, string prompt) =>
        mode switch
        {
            "scan" =>
                "set_project if needed, then api_migrate (dry-run) + compile + mod_errors. Do NOT scan_project. Report compact evidence.\n\n" + prompt,
            "fix" =>
                "set_project to the LocalLow/Workshop mod, api_migrate apply=true for safe rewrites, compile, fix remaining hits with write_file, compile again. No scan_project.\n\n" + prompt,
            "analyze" =>
                "Call game_logs + mod_errors. If Starting game / ResolveCell / GetZone hang, simulate scenario=worldgen-getzone (and --stress for the skip-GetZoneEvent path). Crowded map / city water lag / Yd Freehold pipes → simulate scenario=crowd-load or yd-load (stress = ThreadingAPI offload). Read sim_timeline, then explain the failure and what code to change.\n\n" + prompt,
            _ => prompt
        };

    static string DefaultPrompt(string mode) =>
        mode switch
        {
            "scan" => "api_migrate + compile the active LocalLow mod; list remaining obsolete hits and CS errors.",
            "fix" => "api_migrate apply + compile; fix remaining hits on the real LocalLow/Workshop mod folders.",
            "analyze" => "Run or read the last restricted simulation and explain what went wrong in the mod code.",
            _ => "Help with this Caves of Qud mod using api_migrate + compile + grep (no whole-mod dumps)."
        };

    static string NormalizeMode(string? mode)
    {
        mode = (mode ?? "ask").Trim().ToLowerInvariant();
        return mode switch
        {
            "fix" or "repair" => "fix",
            "scan" or "audit" => "scan",
            "analyze" or "sim" or "debug" => "analyze",
            "part" or "mutation" or "blueprint" => "ask",
            _ => "ask"
        };
    }

    static List<OllamaToolCall>? ParseTextToolCalls(string? content)
    {
        if (string.IsNullOrWhiteSpace(content))
            return null;
        var calls = new List<OllamaToolCall>();

        foreach (Match m in Regex.Matches(content, "<tool_call>\\s*([\\s\\S]*?)\\s*</tool_call>", RegexOptions.IgnoreCase))
            AddJsonCall(calls, m.Groups[1].Value);

        foreach (Match m in Regex.Matches(content,
                     @"tool\s+call\s+(\w+)\s*[:=]\s*(\{[\s\S]*?\})",
                     RegexOptions.IgnoreCase))
        {
            calls.Add(new OllamaToolCall
            {
                Function = new OllamaToolFunction
                {
                    Name = m.Groups[1].Value,
                    Arguments = ParseArgs(m.Groups[2].Value)
                }
            });
        }

        if (calls.Count == 0)
        {
            foreach (Match m in Regex.Matches(content,
                         @"\b(scan_project|compile|simulate|sim_timeline|list_files|search|lookup_type|lookup_blueprint|read_file|grep|write_file)\s*\(\s*(\{[\s\S]*?\}|[^)]*)\)",
                         RegexOptions.IgnoreCase))
            {
                var argText = m.Groups[2].Value.Trim();
                JsonElement args;
                if (argText.StartsWith('{'))
                    args = ParseArgs(argText);
                else if (argText.Length == 0)
                    args = default;
                else
                    args = JsonSerializer.SerializeToElement(new { q = argText.Trim('"') });
                calls.Add(new OllamaToolCall
                {
                    Function = new OllamaToolFunction { Name = m.Groups[1].Value, Arguments = args }
                });
            }
        }

        return calls.Count == 0 ? null : calls;
    }

    static void AddJsonCall(List<OllamaToolCall> dest, string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var name = root.TryGetProperty("name", out var n) ? n.GetString()
                : root.TryGetProperty("function", out var f) && f.TryGetProperty("name", out var fn) ? fn.GetString()
                : null;
            if (string.IsNullOrWhiteSpace(name))
                return;
            JsonElement args = default;
            if (root.TryGetProperty("arguments", out var a) || root.TryGetProperty("args", out a))
                args = a.Clone();
            dest.Add(new OllamaToolCall { Function = new OllamaToolFunction { Name = name, Arguments = args } });
        }
        catch
        {
            // ignore
        }
    }

    static JsonElement ParseArgs(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.Clone();
        }
        catch
        {
            return default;
        }
    }

    static string ArgsPreview(JsonElement args) =>
        args.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null
            ? "{}"
            : OllamaClient.Truncate(args.GetRawText(), 240);

    static string Preview(string s) => OllamaClient.Truncate(s.Replace("\r\n", "\n"), 400);

    static string BackendStartHint(string backend, string model) =>
        string.Equals(backend, "vllm", StringComparison.OrdinalIgnoreCase)
            ? " — start: qudlab vllm serve --model " + model
            : string.Equals(backend, "sglang", StringComparison.OrdinalIgnoreCase)
                ? " — start: qudlab sglang serve --remote  (vLLM on :8000)"
                : " — start Ollama, or: qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct";

    static AiAgentResult Fail(
        string mode,
        string error,
        string model = "",
        List<AiToolTrace>? tools = null,
        List<string>? written = null) =>
        new()
        {
            Ok = false,
            Error = error,
            Reply = error,
            Mode = mode,
            Model = model,
            Tools = tools ?? new List<AiToolTrace>(),
            Written = written ?? new List<string>()
        };
}
