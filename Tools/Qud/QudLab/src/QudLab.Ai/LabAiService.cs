using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using QudLab.Assistant;
using QudLab.Core.Cache;
using QudLab.Core.Install;
using QudLab.Core.Logs;

namespace QudLab.Ai;

/// <summary>
/// Cursor-style local agent: Ollama <c>/api/chat</c> + tools (search, scan, compile, simulate, write).
/// Models without native tool_calls fall back to a packed scan + <c>/api/generate</c>.
/// </summary>
public sealed class LabAiService : ILabAiService
{
    readonly OllamaClient _ollama;
    readonly Func<IntelligenceCache?> _cache;
    readonly Func<QudInstallInfo?> _install;
    readonly Func<string?, string?> _read;
    readonly Action<string, string>? _write;
    readonly string _labRoot;
    readonly ActiveProjectManager? _projectManager;
    readonly AiContextBuilder _ctx = new();

    public LabAiService(
        OllamaClient ollama,
        Func<IntelligenceCache?> cache,
        Func<QudInstallInfo?> install,
        Func<string?, string?> read,
        Action<string, string>? write,
        string labRoot,
        ActiveProjectManager? projectManager = null)
    {
        _ollama = ollama;
        _cache = cache;
        _install = install;
        _read = read;
        _write = write;
        _labRoot = labRoot;
        _projectManager = projectManager;
    }

    public async Task<AiStatusResult> StatusAsync(CancellationToken ct = default)
    {
        var ok = await _ollama.IsAvailableAsync(ct);
        var models = ok ? (await _ollama.ListModelsAsync(ct)).ToList() : new List<string>();
        string? resolved = null;
        if (ok)
        {
            var (m, err) = await _ollama.ResolveModelAsync(null, ct);
            resolved = err is null ? m : null;
        }

        return new AiStatusResult
        {
            Ollama = ok,
            BaseUrl = _ollama.Options.BaseUrl,
            DefaultModel = _ollama.Options.DefaultModel,
            ResolvedModel = resolved,
            Models = models,
            Hint = ok
                ? "POST /ai/run { prompt, mode: ask|scan|fix|analyze }"
                : "Start Ollama (https://github.com/ollama/ollama) so http://127.0.0.1:11434/api/tags responds."
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

        if (!await _ollama.IsAvailableAsync(ct))
        {
            return Fail(mode, "Ollama not reachable at " + _ollama.Options.BaseUrl +
                              " — install/start from https://github.com/ollama/ollama");
        }

        var (model, modelErr) = await _ollama.ResolveModelAsync(request.Model, ct);
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
            var msg = await _ollama.ChatAsync(messages, model, specs, ct);
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
            maxChars: _ollama.Options.MaxContextChars);

        return await _ollama.GenerateAsync(packed, model, system: pack, json: false, ct);
    }

    string BuildSystem(string mode, bool apply)
    {
        var sb = new StringBuilder();
        sb.AppendLine("You are the Qud Lab local coding agent running through Ollama.");
        sb.AppendLine("You have the same job as Cursor here: inspect the real game types and the user's mod, then answer or fix.");
        sb.AppendLine("Use tools. Do not guess XRL type/event names — call search or lookup_type.");
        sb.AppendLine("For MODERROR / type conflicts: call mod_errors FIRST (reads build_log.txt), then list_mods, set_project to the conflicting mod, grep/read_file, fix via write_file.");
        sb.AppendLine("For runtime/turn bugs: call game_logs (player/threading), then simulate(scenario=lag-diagnose). Crowded-zone / city water / Yd pipe lag → crowd-load or yd-load (stress = ThreadingAPI offload of LiquidVolume + HydraulicPowerTransmission TurnTick). New Game stuck on Starting game → worldgen-getzone (stress = skip GetZoneEvent).");
        sb.AppendLine("For event-pool bloat / duplicate MinEvent IDs: call event_pools (scan=true after mod changes). Check modPooled count and idConflicts.");
        sb.AppendLine("Active project may be Workspace/src OR a LocalLow/Workshop mod — list_files/scan_project/compile use that root. Hot-switch via set_project without restarting serve.");
        sb.AppendLine("scan_project reads every active-project file. grep searches them. compile checks them. simulate reproduces turn bugs, chargen, or GetZone (scenario=worldgen-getzone).");
        sb.AppendLine("Never invent XRL names. Never request texture bytes. ThreadingAPI is a separate WIP mod.");
        sb.AppendLine("When fixing, write COMPLETE files via write_file (not unified diffs), then compile.");
        if (!apply)
            sb.AppendLine("Writes are disabled this turn — propose edits in fenced FILE: path blocks.");
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
                "If the prompt mentions MODERROR/type conflicts, call mod_errors + list_mods first. Then set_project to the right mod, scan_project, compile, grep/search. Report every issue with evidence.\n\n" + prompt,
            "fix" =>
                "If the prompt mentions MODERROR/type conflicts, call mod_errors + list_mods, set_project to the conflicting mod, remove/rename duplicate types, write_file, compile. Otherwise scan+compile the active project and fix.\n\n" + prompt,
            "analyze" =>
                "Call game_logs + mod_errors. If Starting game / ResolveCell / GetZone hang, simulate scenario=worldgen-getzone (and --stress for the skip-GetZoneEvent path). Crowded map / city water lag / Yd Freehold pipes → simulate scenario=crowd-load or yd-load (stress = ThreadingAPI offload). Read sim_timeline, then explain the failure and what code to change.\n\n" + prompt,
            _ => prompt
        };

    static string DefaultPrompt(string mode) =>
        mode switch
        {
            "scan" => "Find compile errors, wrong XRL types, Harmony mistakes, and logic bugs in this workspace.",
            "fix" => "Fix MODERROR type conflicts and compile errors. Use mod_errors, list_mods, set_project on the real mod folders.",
            "analyze" => "Run or read the last restricted simulation and explain what went wrong in the mod code.",
            _ => "Help with this Caves of Qud mod. Use tools to inspect types and files before answering."
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
