using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using QudLab.Core.Install;

namespace QudLab.Gui;

static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}

sealed class MainForm : Form
{
    const string AssistantUrl = "http://127.0.0.1:47821";
    const string OllamaUrl = "http://127.0.0.1:11434";
    const string SglangUrl = "http://127.0.0.1:30000";
    const string VllmUrl = "http://127.0.0.1:8000";
    const string UnityEditor = @"E:\tools\Unity_Editor\6000.0.77f1\Editor\Unity.exe";

    readonly string _labRoot;
    readonly string _cliDll;
    readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(8) };

    Label _statusGate = null!;
    Label _statusServe = null!;
    Label _statusOllama = null!;
    Label _llmLoaded = null!;
    ComboBox _llmModel = null!;
    Button _btnVllm = null!;
    Button _btnSglang = null!;
    TextBox _prompt = null!;
    TextBox _log = null!;
    ComboBox _mode = null!;
    ComboBox _project = null!;
    ComboBox _scenario = null!;
    CheckBox _scenarioStress = null!;
    Button _btnServe = null!;
    Process? _serveProc;
    Process? _vllmProc;
    Process? _sglangProc;
    System.Windows.Forms.Timer _poll = null!;
    bool _busy;
    bool _loadingProjects;
    bool _loadingModels;

    public MainForm()
    {
        _labRoot = FindLabRoot();
        _cliDll = Path.Combine(_labRoot, "artifacts", "bin", "QudLab.Cli", "Release", "net8.0", "QudLab.Cli.dll");

        Text = "Qud Lab";
        Width = 980;
        Height = 860;
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(860, 740);
        Font = new Font("Segoe UI", 9.5f);

        BuildUi();
        FormClosing += (_, _) =>
        {
            StopServe(quiet: true);
            // Leave GPU/frontend running if the user started them; they take minutes to reload.
        };
        Shown += async (_, _) =>
        {
            Append("Lab root: " + _labRoot);
            ReloadProjectCombo();
            await RefreshStatusAsync();
        };

        _poll = new System.Windows.Forms.Timer { Interval = 4000 };
        _poll.Tick += async (_, _) => await RefreshStatusAsync();
        _poll.Start();
    }

    void BuildUi()
    {
        var status = new Panel
        {
            Dock = DockStyle.Top,
            Height = 88,
            Padding = new Padding(12, 10, 12, 8)
        };
        _statusGate = MkStatus(12, 10, "Gate: …");
        _statusServe = MkStatus(12, 34, "Serve :47821: …");
        _statusOllama = MkStatus(12, 58, "LLM: …");
        status.Controls.AddRange(new Control[] { _statusGate, _statusServe, _statusOllama });

        var tools = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 44,
            Padding = new Padding(8, 6, 8, 4),
            WrapContents = false
        };
        tools.Controls.Add(MkBtn("Setup", async () => await RunCliAsync("setup")));
        tools.Controls.Add(MkBtn("Sync refs", async () => await RunCliAsync("sync-refs")));
        tools.Controls.Add(MkBtn("Index", async () => await RunCliAsync("index")));
        _btnServe = MkBtn("Start serve", async () => await ToggleServeAsync());
        tools.Controls.Add(_btnServe);
        tools.Controls.Add(MkBtn("Compile", async () => await RunCliAsync("compile")));
        tools.Controls.Add(MkBtn("Simulate", async () => await RunCliAsync("simulate", "--turns", "8", "--blueprint", "Human")));
        tools.Controls.Add(MkBtn("Sim chargen", async () => await RunCliAsync("simulate", "--scenario", "chargen", "--turns", "4", "--genotype", "Mutated Human", "--subtype", "Apostle")));
        tools.Controls.Add(MkBtn("Run scenario", async () => await RunScenarioAsync()));
        tools.Controls.Add(MkBtn("Lag diagnose", async () => await RunLagDiagnoseAsync()));
        tools.Controls.Add(MkBtn("Refresh", async () => await RefreshStatusAsync()));

        var openers = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 40,
            Padding = new Padding(8, 2, 8, 4),
            WrapContents = false
        };
        openers.Controls.Add(MkBtn("Open Workspace", () =>
        {
            var ws = Path.Combine(_labRoot, "QudLab.code-workspace");
            if (File.Exists(ws))
                Process.Start(new ProcessStartInfo(ws) { UseShellExecute = true });
            else
                Process.Start("explorer.exe", Path.Combine(_labRoot, "Workspace", "src"));
        }));
        openers.Controls.Add(MkBtn("Open Unity", () =>
        {
            var proj = Path.Combine(_labRoot, "UnityProject");
            if (File.Exists(UnityEditor))
                Process.Start(UnityEditor, $"-projectPath \"{proj}\"");
            else
                Process.Start("explorer.exe", proj);
        }));
        openers.Controls.Add(MkBtn("Lab folder", () => Process.Start("explorer.exe", _labRoot)));
        openers.Controls.Add(MkBtn("Type conflicts", async () => await ShowConflictsAsync()));

        var projectRow = new Panel
        {
            Dock = DockStyle.Top,
            Height = 36,
            Padding = new Padding(12, 4, 12, 4)
        };
        var projLabel = new Label
        {
            Text = "Active mod:",
            AutoSize = true,
            Location = new Point(4, 8)
        };
        _project = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Location = new Point(90, 4),
            Width = 640,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
        };
        _project.SelectedIndexChanged += async (_, _) => await OnProjectSelectedAsync();
        projectRow.Controls.Add(projLabel);
        projectRow.Controls.Add(_project);

        var scenarioRow = new Panel
        {
            Dock = DockStyle.Top,
            Height = 36,
            Padding = new Padding(12, 4, 12, 4)
        };
        var scenLabel = new Label { Text = "Scenario:", AutoSize = true, Location = new Point(4, 8) };
        _scenario = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Location = new Point(90, 4),
            Width = 280
        };
        _scenario.Items.AddRange(new object[]
        {
            "(default turn loop)",
            "lag-diagnose",
            "lag-suite",
            "npc-cta-no-spend",
            "move-input-lag",
            "crowd-load",
            "yd-load",
            "chargen",
            "worldgen-getzone",
            "player-turn-starvation",
            "cta-inf-turn",
            "broodmother-bta-starve"
        });
        _scenario.SelectedIndex = 0;
        _scenarioStress = new CheckBox
        {
            Text = "stress (fixed path)",
            AutoSize = true,
            Location = new Point(380, 6)
        };
        scenarioRow.Controls.Add(scenLabel);
        scenarioRow.Controls.Add(_scenario);
        scenarioRow.Controls.Add(_scenarioStress);

        var llmBox = new GroupBox
        {
            Text = "GPU model slot (vLLM in WSL; restart to switch weights)",
            Dock = DockStyle.Top,
            Height = 118,
            Padding = new Padding(10)
        };
        var modelLabel = new Label { Text = "Model:", AutoSize = true, Location = new Point(14, 32) };
        _llmModel = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDown,
            Location = new Point(70, 28),
            Width = 520,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
        };
        ReloadModelCombo();
        _llmModel.SelectedIndexChanged += (_, _) =>
        {
            if (!_loadingModels)
                LlmModels.SaveLast(SelectedModel());
        };
        _btnVllm = MkBtn("Start GPU", async () => await ToggleVllmAsync());
        _btnSglang = MkBtn("Start frontend", async () => await ToggleSglangAsync());
        var llmBtns = new FlowLayoutPanel
        {
            Location = new Point(600, 24),
            Size = new Size(360, 72),
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
            WrapContents = true
        };
        llmBtns.Controls.Add(_btnVllm);
        llmBtns.Controls.Add(MkBtn("Swap model", async () => await SwapVllmAsync(restartFrontend: true)));
        llmBtns.Controls.Add(MkBtn("Escalate ctx", async () => await EscalateContextAsync()));
        llmBtns.Controls.Add(_btnSglang);
        llmBtns.Controls.Add(MkBtn("Rescan cache", () =>
        {
            ReloadModelCombo();
            Append("Model list: presets + HF cache (incl. D:\\hf-cache).");
        }));
        llmBtns.Controls.Add(MkBtn("CLI help", () =>
        {
            Append("CLI: qudlab vllm list | status | stop | swap --model org/name [--frontend]");
            Append("CLI: qudlab vllm shelve | escalate [--task …] | unshelve");
            Append("Bat:  Swap-Vllm.bat list | status | swap org/name [--frontend]");
        }));
        _llmLoaded = new Label
        {
            AutoSize = true,
            Location = new Point(14, 78),
            Text = "Loaded: (query /v1/models after Start GPU / Swap)"
        };
        llmBox.Controls.Add(modelLabel);
        llmBox.Controls.Add(_llmModel);
        llmBox.Controls.Add(llmBtns);
        llmBox.Controls.Add(_llmLoaded);
        llmBox.Height = 128;
        llmBox.Resize += (_, _) =>
        {
            _llmModel.Width = Math.Max(280, llmBox.ClientSize.Width - 450);
            llmBtns.Left = Math.Max(360, llmBox.ClientSize.Width - 370);
        };

        var aiBox = new GroupBox
        {
            Text = "Local agent (uses whichever backend is up: vLLM, SGLang frontend, or Ollama)",
            Dock = DockStyle.Top,
            Height = 168,
            Padding = new Padding(10)
        };
        _mode = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Location = new Point(14, 28),
            Width = 120
        };
        _mode.Items.AddRange(new object[] { "ask", "scan", "fix", "analyze" });
        _mode.SelectedIndex = 0;
        _prompt = new TextBox
        {
            Multiline = true,
            ScrollBars = ScrollBars.Vertical,
            Location = new Point(14, 58),
            Size = new Size(720, 70),
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
            Font = new Font("Consolas", 10f)
        };
        _prompt.PlaceholderText = "Ask like Cursor — scan all files, compile, simulate, fix…";
        var aiBtns = new FlowLayoutPanel
        {
            Location = new Point(14, 132),
            Size = new Size(900, 30),
            WrapContents = false
        };
        aiBtns.Controls.Add(MkBtn("Ask", async () => await RunAiAsync("ask")));
        aiBtns.Controls.Add(MkBtn("Scan all", async () => await RunAiAsync("scan")));
        aiBtns.Controls.Add(MkBtn("Fix", async () => await RunAiAsync("fix")));
        aiBtns.Controls.Add(MkBtn("Sim+Ask", async () => await RunAiAsync("analyze")));
        aiBtns.Controls.Add(MkBtn("Run mode", async () => await RunAiAsync(_mode.SelectedItem?.ToString() ?? "ask")));
        aiBox.Controls.Add(_mode);
        aiBox.Controls.Add(_prompt);
        aiBox.Controls.Add(aiBtns);
        aiBox.Resize += (_, _) =>
        {
            _prompt.Width = Math.Max(400, aiBox.ClientSize.Width - 40);
        };

        _log = new TextBox
        {
            Dock = DockStyle.Fill,
            Multiline = true,
            ScrollBars = ScrollBars.Both,
            ReadOnly = true,
            Font = new Font("Consolas", 9.5f),
            WordWrap = false,
            BackColor = Color.FromArgb(24, 26, 30),
            ForeColor = Color.FromArgb(220, 220, 220)
        };

        Controls.Add(_log);
        Controls.Add(aiBox);
        Controls.Add(llmBox);
        Controls.Add(scenarioRow);
        Controls.Add(projectRow);
        Controls.Add(openers);
        Controls.Add(tools);
        Controls.Add(status);
    }

    static Label MkStatus(int x, int y, string text) =>
        new()
        {
            AutoSize = true,
            Location = new Point(x, y),
            Text = text,
            Font = new Font("Segoe UI", 9.5f, FontStyle.Bold)
        };

    Button MkBtn(string text, Func<Task> onClick)
    {
        var b = new Button
        {
            Text = text,
            AutoSize = true,
            Margin = new Padding(4, 2, 4, 2),
            Padding = new Padding(8, 2, 8, 2)
        };
        b.Click += async (_, _) =>
        {
            if (_busy) return;
            try
            {
                _busy = true;
                UseWaitCursor = true;
                await onClick();
            }
            catch (Exception ex)
            {
                Append("ERROR: " + ex.Message);
            }
            finally
            {
                _busy = false;
                UseWaitCursor = false;
            }
        };
        return b;
    }

    Button MkBtn(string text, Action onClick)
    {
        var b = new Button
        {
            Text = text,
            AutoSize = true,
            Margin = new Padding(4, 2, 4, 2),
            Padding = new Padding(8, 2, 4, 2)
        };
        b.Click += (_, _) =>
        {
            try { onClick(); }
            catch (Exception ex) { Append("ERROR: " + ex.Message); }
        };
        return b;
    }

    async Task RefreshStatusAsync()
    {
        try
        {
            var gate = await RunCliCaptureAsync("gate");
            var pass = gate.StartsWith("PASS", StringComparison.OrdinalIgnoreCase);
            _statusGate.Text = pass
                ? "Gate: PASS — " + Truncate(gate.Replace("\r", "").Replace("\n", " | "), 90)
                : "Gate: FAIL — " + Truncate(gate.Replace("\r", "").Replace("\n", " | "), 90);
            _statusGate.ForeColor = pass ? Color.DarkGreen : Color.Firebrick;
        }
        catch (Exception ex)
        {
            _statusGate.Text = "Gate: " + ex.Message;
            _statusGate.ForeColor = Color.Firebrick;
        }

        var serveUp = await PingJsonAsync(AssistantUrl + "/health");
        var serveOwned = _serveProc is { HasExited: false };
        _statusServe.Text = serveUp
            ? "Serve :47821: UP" + (serveOwned ? " (this launcher)" : " (external)")
            : "Serve :47821: down — click Start serve";
        _statusServe.ForeColor = serveUp ? Color.DarkGreen : Color.DarkOrange;
        _btnServe.Text = serveOwned ? "Stop serve" : "Start serve";

        var (llmUp, llmLabel) = await ReadLlmStatusAsync(serveUp);
        _statusOllama.Text = llmLabel;
        _statusOllama.ForeColor = llmUp ? Color.DarkGreen : Color.DarkOrange;
        await RefreshLlmSlotAsync();
    }

    async Task ToggleServeAsync()
    {
        if (_serveProc is { HasExited: false })
        {
            StopServe();
            Append("Serve stopped.");
            await RefreshStatusAsync();
            return;
        }

        EnsureCliBuilt();
        if (!File.Exists(_cliDll))
            throw new InvalidOperationException("CLI missing — build failed.");

        if (await PingJsonAsync(AssistantUrl + "/health"))
        {
            Append("Serve already running externally on :47821.");
            await RefreshStatusAsync();
            return;
        }

        var psi = new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = $"\"{_cliDll}\" serve",
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        _serveProc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _serveProc.OutputDataReceived += (_, e) => { if (e.Data is not null) BeginInvoke(() => Append(e.Data)); };
        _serveProc.ErrorDataReceived += (_, e) => { if (e.Data is not null) BeginInvoke(() => Append(e.Data)); };
        _serveProc.Exited += (_, _) => BeginInvoke(async () =>
        {
            Append("Serve process exited.");
            await RefreshStatusAsync();
        });
        if (!_serveProc.Start())
            throw new InvalidOperationException("Failed to start serve.");
        _serveProc.BeginOutputReadLine();
        _serveProc.BeginErrorReadLine();
        Append("Starting serve…");
        for (var i = 0; i < 20; i++)
        {
            await Task.Delay(250);
            if (await PingJsonAsync(AssistantUrl + "/health"))
                break;
        }
        await RefreshStatusAsync();
    }

    void StopServe(bool quiet = false)
    {
        try
        {
            if (_serveProc is { HasExited: false })
            {
                _serveProc.Kill(entireProcessTree: true);
                _serveProc.WaitForExit(3000);
            }
        }
        catch (Exception ex)
        {
            if (!quiet) Append("Stop serve: " + ex.Message);
        }
        finally
        {
            _serveProc?.Dispose();
            _serveProc = null;
        }
    }

    async Task RunAiAsync(string mode)
    {
        var prompt = _prompt.Text.Trim();
        if (string.IsNullOrWhiteSpace(prompt))
        {
            prompt = mode switch
            {
                "scan" => "Find compile errors, wrong XRL types, and logic bugs. For MODERROR type conflicts use mod_errors.",
                "fix" => "Fix MODERROR type conflicts / compile errors. Call mod_errors, set_project on the real mod, then write_file.",
                "analyze" => "Simulate, then scan all files and explain the issue.",
                _ => "Inspect this Caves of Qud mod. Use tools; do not guess type names."
            };
        }

        if (!await PingJsonAsync(AssistantUrl + "/health"))
        {
            Append("Serve is down — starting it for /ai/run…");
            await ToggleServeAsync();
            if (!await PingJsonAsync(AssistantUrl + "/health"))
                throw new InvalidOperationException("Could not start serve.");
        }

        Append($"AI {mode}… (vLLM/SGLang/Ollama may take several minutes)");
        var body = JsonSerializer.Serialize(new
        {
            prompt,
            mode,
            apply = mode == "fix",
            simulate = mode == "analyze",
            turns = 8,
            blueprint = "Human"
        });
        using var req = new HttpRequestMessage(HttpMethod.Post, AssistantUrl + "/ai/run")
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json")
        };
        using var longHttp = new HttpClient { Timeout = TimeSpan.FromMinutes(12) };
        using var res = await longHttp.SendAsync(req);
        var text = await res.Content.ReadAsStringAsync();
        Append($"AI HTTP {(int)res.StatusCode}");
        try
        {
            using var doc = JsonDocument.Parse(text);
            if (doc.RootElement.TryGetProperty("reply", out var reply))
                Append(reply.GetString() ?? "");
            else
                Append(Truncate(text, 4000));
            if (doc.RootElement.TryGetProperty("written", out var written) && written.ValueKind == JsonValueKind.Array)
            {
                foreach (var w in written.EnumerateArray())
                    Append("wrote: " + w.GetString());
            }
        }
        catch
        {
            Append(Truncate(text, 4000));
        }
    }

    async Task RunCliAsync(params string[] args)
    {
        Append("> qudlab " + string.Join(' ', args));
        var output = await RunCliCaptureAsync(args);
        if (!string.IsNullOrWhiteSpace(output))
            Append(output.TrimEnd());
        await RefreshStatusAsync();
    }

    async Task<string> RunCliCaptureAsync(params string[] args)
    {
        EnsureCliBuilt();
        if (!File.Exists(_cliDll))
            throw new InvalidOperationException("CLI not found: " + _cliDll);

        var psi = new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = $"\"{_cliDll}\" {string.Join(' ', args.Select(Quote))}",
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start CLI.");
        var stdout = await p.StandardOutput.ReadToEndAsync();
        var stderr = await p.StandardError.ReadToEndAsync();
        await p.WaitForExitAsync();
        var sb = new StringBuilder();
        if (!string.IsNullOrWhiteSpace(stdout)) sb.Append(stdout);
        if (!string.IsNullOrWhiteSpace(stderr))
        {
            if (sb.Length > 0) sb.AppendLine();
            sb.Append(stderr);
        }
        if (p.ExitCode != 0 && sb.Length == 0)
            sb.Append("exit " + p.ExitCode);
        return sb.ToString();
    }

    void EnsureCliBuilt()
    {
        if (File.Exists(_cliDll))
            return;
        Append("Building QudLab.sln (Release)…");
        var psi = new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = "build QudLab.sln -c Release -v q",
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi) ?? throw new InvalidOperationException("dotnet build failed to start.");
        var o = p.StandardOutput.ReadToEnd();
        var e = p.StandardError.ReadToEnd();
        p.WaitForExit();
        if (!string.IsNullOrWhiteSpace(o)) Append(o.TrimEnd());
        if (!string.IsNullOrWhiteSpace(e)) Append(e.TrimEnd());
        if (p.ExitCode != 0)
            throw new InvalidOperationException("Build failed.");
    }

    async Task<(bool up, string label)> ReadLlmStatusAsync(bool serveUp)
    {
        if (serveUp)
        {
            try
            {
                var body = await _http.GetStringAsync(AssistantUrl + "/ai/status");
                using var doc = JsonDocument.Parse(body);
                var root = doc.RootElement;
                var available = root.TryGetProperty("available", out var av) && av.GetBoolean()
                    || root.TryGetProperty("vllm", out var vl) && vl.GetBoolean()
                    || root.TryGetProperty("sglang", out var sg) && sg.GetBoolean()
                    || root.TryGetProperty("ollama", out var ol) && ol.GetBoolean();
                var backend = root.TryGetProperty("backend", out var b) ? b.GetString() ?? "llm" : "llm";
                var model = root.TryGetProperty("resolvedModel", out var rm) ? rm.GetString()
                    : root.TryGetProperty("defaultModel", out var dm) ? dm.GetString() : null;
                var url = root.TryGetProperty("baseUrl", out var u) ? u.GetString() : "";
                if (available)
                    return (true, backend + " UP" + (string.IsNullOrEmpty(model) ? "" : " · " + model) + (string.IsNullOrEmpty(url) ? "" : " · " + url));
                var hint = root.TryGetProperty("hint", out var h) ? h.GetString() : null;
                return (false, backend + " down — " + (hint ?? "qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct"));
            }
            catch { /* fall through to direct pings */ }
        }

        if (await PingAsync(VllmUrl + "/v1/models") || await PingAsync(VllmUrl + "/health"))
            return (true, "vLLM :8000 UP (start serve to bind the agent)");
        if (await PingAsync(SglangUrl + "/v1/models") || await PingAsync(SglangUrl + "/health"))
            return (true, "SGLang :30000 UP (start serve to bind the agent)");
        if (await PingAsync(OllamaUrl + "/api/tags"))
            return (true, "Ollama :11434 UP (start serve to bind the agent)");
        return (false, "LLM down — qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct");
    }

    async Task<bool> PingJsonAsync(string url)
    {
        try
        {
            using var res = await _http.GetAsync(url);
            return res.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    async Task<bool> PingAsync(string url)
    {
        try
        {
            using var res = await _http.GetAsync(url);
            return res.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    void Append(string line)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => Append(line));
            return;
        }
        _log.AppendText(line + Environment.NewLine);
    }

    string SelectedModel()
    {
        var t = _llmModel.Text?.Trim();
        if (!string.IsNullOrWhiteSpace(t))
            return t;
        return _llmModel.SelectedItem?.ToString() ?? LlmModels.Presets[0];
    }

    void ReloadModelCombo()
    {
        _loadingModels = true;
        try
        {
            var keep = _llmModel.Text?.Trim();
            if (string.IsNullOrWhiteSpace(keep))
                keep = LlmModels.LoadLast();
            _llmModel.Items.Clear();
            foreach (var m in LlmModels.Catalog())
                _llmModel.Items.Add(m);
            var idx = -1;
            for (var i = 0; i < _llmModel.Items.Count; i++)
            {
                if (string.Equals(_llmModel.Items[i]?.ToString(), keep, StringComparison.OrdinalIgnoreCase))
                {
                    idx = i;
                    break;
                }
            }
            if (idx >= 0)
                _llmModel.SelectedIndex = idx;
            else
            {
                _llmModel.Text = keep;
            }
        }
        finally
        {
            _loadingModels = false;
        }
    }

    async Task RefreshLlmSlotAsync()
    {
        var vllmUp = await PingAsync(VllmUrl + "/v1/models") || await PingAsync(VllmUrl + "/health");
        var sglUp = await PingAsync(SglangUrl + "/v1/models") || await PingAsync(SglangUrl + "/health");
        var loaded = await ReadOpenAiModelsAsync(VllmUrl);
        if (loaded.Count == 0 && sglUp)
            loaded = await ReadOpenAiModelsAsync(SglangUrl);
        var ownedGpu = _vllmProc is { HasExited: false };
        var ownedFe = _sglangProc is { HasExited: false };
        _btnVllm.Text = !vllmUp && !ownedGpu
            ? "Start GPU"
            : (loaded.Count > 0 && !loaded.Any(m => string.Equals(m, SelectedModel(), StringComparison.OrdinalIgnoreCase))
                ? "Switch GPU"
                : "Stop GPU");
        _btnSglang.Text = sglUp || ownedFe ? "Stop frontend" : "Start frontend";
        var loadedText = loaded.Count > 0 ? string.Join(", ", loaded) : "(none)";
        _llmLoaded.Text = vllmUp
            ? "Loaded on :8000: " + loadedText + (sglUp ? "  · frontend :30000 UP" : "  · frontend down")
            : sglUp
                ? "Frontend :30000 UP, vLLM :8000 down — start GPU"
                : "GPU down — pick a Hugging Face id and click Start GPU (11GB: 3B FP16 or 7B AWQ)";
        _llmLoaded.ForeColor = vllmUp ? Color.DarkGreen : Color.DarkOrange;
    }

    async Task<List<string>> ReadOpenAiModelsAsync(string baseUrl)
    {
        var list = new List<string>();
        try
        {
            using var res = await _http.GetAsync(baseUrl.TrimEnd('/') + "/v1/models");
            if (!res.IsSuccessStatusCode)
                return list;
            using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
            if (!doc.RootElement.TryGetProperty("data", out var data) || data.ValueKind != JsonValueKind.Array)
                return list;
            foreach (var m in data.EnumerateArray())
            {
                if (m.TryGetProperty("id", out var id))
                {
                    var s = id.GetString();
                    if (!string.IsNullOrWhiteSpace(s))
                        list.Add(s);
                }
            }
        }
        catch { /* down */ }
        return list;
    }

    async Task EscalateContextAsync()
    {
        var script = Path.Combine(_labRoot, "scripts", "Escalate-VllmContext.ps1");
        if (!File.Exists(script))
            throw new InvalidOperationException("Missing " + script);
        var task = _prompt.Text?.Trim() ?? "";
        Append("Escalating context: shelve chat-index -> high-ctx model -> unshelve next turn…");
        var args = "-NoProfile -ExecutionPolicy Bypass -File " + Quote(script);
        if (!string.IsNullOrWhiteSpace(task))
            args += " -Task " + Quote(task.Length > 500 ? task[..500] : task);
        var high = LlmModels.Presets.FirstOrDefault(p => p.Contains("Coder-7B", StringComparison.OrdinalIgnoreCase))
                   ?? "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ";
        args += " -ToModel " + Quote(high);
        var psi = new ProcessStartInfo
        {
            FileName = "powershell",
            Arguments = args,
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start escalate");
        var stdout = await p.StandardOutput.ReadToEndAsync();
        var stderr = await p.StandardError.ReadToEndAsync();
        await p.WaitForExitAsync();
        foreach (var line in (stdout + "\n" + stderr).Split('\n'))
        {
            var t = line.TrimEnd('\r');
            if (!string.IsNullOrWhiteSpace(t))
                Append("[escalate] " + t);
        }
        try
        {
            _llmModel.Text = high;
            LlmModels.SaveLast(high);
        }
        catch { /* ignore */ }
        _vllmProc = null;
        _sglangProc = null;
        await RefreshStatusAsync();
        Append("Send the next Agent message — proxy will inject SHELVED CONTEXT.");
    }

    async Task SwapVllmAsync(bool restartFrontend)
    {
        var model = SelectedModel();
        if (string.IsNullOrWhiteSpace(model) || model.Contains(' ', StringComparison.Ordinal))
            throw new InvalidOperationException("Pick a Hugging Face id (org/name).");
        LlmModels.SaveLast(model);

        var script = Path.Combine(_labRoot, "scripts", "Swap-VllmModel.ps1");
        if (!File.Exists(script))
            throw new InvalidOperationException("Missing " + script);

        Append("Swapping GPU model → " + model + (restartFrontend ? " (+ restart :30000)" : "") + "…");
        var args = "-NoProfile -ExecutionPolicy Bypass -File " + Quote(script)
                   + " swap -Model " + Quote(model)
                   + (restartFrontend ? " -RestartFrontend" : "");
        var psi = new ProcessStartInfo
        {
            FileName = "powershell",
            Arguments = args,
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start swap");
        var stdout = await p.StandardOutput.ReadToEndAsync();
        var stderr = await p.StandardError.ReadToEndAsync();
        await p.WaitForExitAsync();
        foreach (var line in (stdout + "\n" + stderr).Split('\n'))
        {
            var t = line.TrimEnd('\r');
            if (!string.IsNullOrWhiteSpace(t))
                Append("[swap] " + t);
        }
        if (p.ExitCode != 0)
            Append("Swap exit code " + p.ExitCode);
        _vllmProc = null;
        _sglangProc = null;
        await RefreshStatusAsync();
    }

    async Task ToggleVllmAsync()
    {
        var model = SelectedModel();
        if (string.IsNullOrWhiteSpace(model) || model.Contains(' '))
            throw new InvalidOperationException("Pick a Hugging Face id (org/name).");
        LlmModels.SaveLast(model);

        var vllmUp = await PingAsync(VllmUrl + "/v1/models") || _vllmProc is { HasExited: false };
        if (vllmUp)
        {
            var loaded = await ReadOpenAiModelsAsync(VllmUrl);
            var same = loaded.Any(m => string.Equals(m, model, StringComparison.OrdinalIgnoreCase));
            if (!same)
            {
                // Different model selected while GPU is up → swap path.
                await SwapVllmAsync(restartFrontend: true);
                return;
            }
            StopVllm();
            Append("Stopping vLLM…");
            for (var i = 0; i < 24 && (await PingAsync(VllmUrl + "/health") || await PingAsync(VllmUrl + "/v1/models")); i++)
                await Task.Delay(250);
            await RefreshStatusAsync();
            return;
        }

        EnsureCliBuilt();
        var script = Path.Combine(_labRoot, "scripts", "Serve-Vllm.ps1");
        if (!File.Exists(script))
            throw new InvalidOperationException("Missing " + script);

        Append("Starting vLLM with " + model + " (first load can take several minutes)…");
        _vllmProc = StartOwned("vLLM", "powershell",
            "-NoProfile -ExecutionPolicy Bypass -File " + Quote(script) + " -Model " + Quote(model) + " -Port 8000");
        for (var i = 0; i < 80; i++)
        {
            await Task.Delay(500);
            if (await PingAsync(VllmUrl + "/v1/models"))
            {
                Append("vLLM is up: http://127.0.0.1:8000/v1  model=" + model);
                break;
            }
            if (_vllmProc is { HasExited: true })
            {
                Append("vLLM process exited while starting. Check the log / WSL.");
                break;
            }
        }
        await RefreshStatusAsync();
    }

    async Task ToggleSglangAsync()
    {
        if (_sglangProc is { HasExited: false } || await PingAsync(SglangUrl + "/v1/models"))
        {
            StopSglang();
            Append("Stopping SGLang frontend…");
            await Task.Delay(400);
            await RefreshStatusAsync();
            return;
        }

        var script = Path.Combine(_labRoot, "scripts", "Serve-Sglang.ps1");
        if (!File.Exists(script))
            throw new InvalidOperationException("Missing " + script);
        Append("Starting SGLang frontend :30000 -> vLLM :8000 …");
        _sglangProc = StartOwned("SGLang", "powershell",
            "-NoProfile -ExecutionPolicy Bypass -File " + Quote(script) + " -Remote -RemoteUrl http://127.0.0.1:8000/v1 -Port 30000");
        for (var i = 0; i < 20; i++)
        {
            await Task.Delay(250);
            if (await PingAsync(SglangUrl + "/v1/models") || await PingAsync(SglangUrl + "/health"))
            {
                Append("Frontend is up: http://127.0.0.1:30000/v1");
                break;
            }
            if (_sglangProc is { HasExited: true })
            {
                Append("Frontend process exited. Red PowerShell errors used to come from UTF-8 dashes in Serve-Sglang.ps1 — that script is ASCII now.");
                break;
            }
        }
        await RefreshStatusAsync();
    }

    Process StartOwned(string name, string fileName, string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            WorkingDirectory = _labRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        var p = new Process { StartInfo = psi, EnableRaisingEvents = true };
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) BeginInvoke(() => Append("[" + name + "] " + e.Data)); };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) BeginInvoke(() => Append("[" + name + "] " + e.Data)); };
        p.Exited += (_, _) => BeginInvoke(async () =>
        {
            Append(name + " process exited.");
            await RefreshStatusAsync();
        });
        if (!p.Start())
            throw new InvalidOperationException("Failed to start " + name);
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();
        return p;
    }

    void StopVllm()
    {
        try
        {
            if (_vllmProc is { HasExited: false })
            {
                _vllmProc.Kill(entireProcessTree: true);
                _vllmProc.WaitForExit(4000);
            }
        }
        catch (Exception ex) { Append("Stop GPU: " + ex.Message); }
        finally
        {
            _vllmProc?.Dispose();
            _vllmProc = null;
        }
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "wsl",
                Arguments = "-d Ubuntu -u arendeth -- bash -lc \"pkill -f vllm || true\"",
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using var p = Process.Start(psi);
            p?.WaitForExit(4000);
        }
        catch { /* WSL may already be down */ }
    }

    void StopSglang()
    {
        try
        {
            if (_sglangProc is { HasExited: false })
            {
                _sglangProc.Kill(entireProcessTree: true);
                _sglangProc.WaitForExit(3000);
            }
        }
        catch (Exception ex) { Append("Stop frontend: " + ex.Message); }
        finally
        {
            _sglangProc?.Dispose();
            _sglangProc = null;
        }
    }

    static string Quote(string s) =>
        s.Contains(' ') || s.Contains('"') ? "\"" + s.Replace("\"", "\\\"") + "\"" : s;

    static string Truncate(string s, int max) =>
        string.IsNullOrEmpty(s) ? "" : (s.Length <= max ? s : s[..max] + "…");

    void ReloadProjectCombo()
    {
        _loadingProjects = true;
        try
        {
            _project.Items.Clear();
            var workspace = Path.Combine(_labRoot, "Workspace", "src");
            if (Directory.Exists(workspace))
                _project.Items.Add(new ProjectItem("Workspace/src (lab)", workspace));

            foreach (var m in QudModPaths.ListAllMods())
            {
                var label = $"{m.Source}: {m.Title ?? m.Name}" + (string.IsNullOrWhiteSpace(m.Id) ? "" : $" [{m.Id}]");
                _project.Items.Add(new ProjectItem(label, m.Path));
            }

            var active = QudModPaths.ResolveProject(null, Directory.Exists(workspace) ? workspace : null);
            var idx = 0;
            for (var i = 0; i < _project.Items.Count; i++)
            {
                if (_project.Items[i] is ProjectItem pi &&
                    string.Equals(pi.Path, active, StringComparison.OrdinalIgnoreCase))
                {
                    idx = i;
                    break;
                }
            }

            if (_project.Items.Count > 0)
                _project.SelectedIndex = idx;
        }
        catch (Exception ex)
        {
            Append("Project list: " + ex.Message);
        }
        finally
        {
            _loadingProjects = false;
        }
    }

    async Task OnProjectSelectedAsync()
    {
        if (_loadingProjects || _project.SelectedItem is not ProjectItem item)
            return;
        try
        {
            if (await PingJsonAsync(AssistantUrl + "/health"))
            {
                var json = JsonSerializer.Serialize(new { path = item.Path });
                using var content = new StringContent(json, Encoding.UTF8, "application/json");
                var resp = await _http.PostAsync(AssistantUrl + "/project/set", content);
                var body = await resp.Content.ReadAsStringAsync();
                Append(resp.IsSuccessStatusCode
                    ? "Hot-switched project: " + item.Path + " (" + Truncate(body.Replace("\r", "").Replace("\n", " "), 120) + ")"
                    : "Set project HTTP " + (int)resp.StatusCode + " " + Truncate(body, 200));
            }
            else
            {
                await RunCliAsync("project", "set", item.Path);
                Append("Active mod (CLI): " + item.Path);
            }
        }
        catch (Exception ex)
        {
            Append("Set project failed: " + ex.Message);
        }
    }

    async Task ShowConflictsAsync()
    {
        try
        {
            if (await PingJsonAsync(AssistantUrl + "/health"))
            {
                var body = await _http.GetStringAsync(AssistantUrl + "/project/conflicts");
                using var doc = JsonDocument.Parse(body);
                var text = doc.RootElement.TryGetProperty("text", out var t) ? t.GetString() : body;
                Append(text ?? "(no conflicts text)");
            }
            else
                await RunCliAsync("project", "conflicts");
        }
        catch (Exception ex)
        {
            Append("Conflicts: " + ex.Message);
        }
    }

    async Task RunLagDiagnoseAsync()
    {
        if (await PingJsonAsync(AssistantUrl + "/health"))
        {
            var payload = JsonSerializer.Serialize(new { turns = 8, scenario = "lag-diagnose" });
            using var content = new StringContent(payload, Encoding.UTF8, "application/json");
            var resp = await _http.PostAsync(AssistantUrl + "/simulate", content);
            var body = await resp.Content.ReadAsStringAsync();
            Append("Lag diagnose HTTP " + (int)resp.StatusCode);
            Append(Truncate(body.Replace("\r", "").Replace("\n", " "), 500));
        }
        else
            await RunCliAsync("simulate", "--scenario", "lag-diagnose", "--turns", "8");
    }

    async Task RunScenarioAsync()
    {
        var selected = _scenario.SelectedItem?.ToString() ?? "";
        var scenario = selected.StartsWith('(') ? "" : selected;
        var args = new List<string> { "simulate", "--turns", "8", "--blueprint", "Human" };
        if (!string.IsNullOrWhiteSpace(scenario))
            args.AddRange(new[] { "--scenario", scenario });
        if (_scenarioStress.Checked)
            args.Add("--stress");

        if (await PingJsonAsync(AssistantUrl + "/health"))
        {
            var payload = new Dictionary<string, object>
            {
                ["blueprint"] = "Human",
                ["turns"] = 8,
                ["stress"] = _scenarioStress.Checked
            };
            if (!string.IsNullOrWhiteSpace(scenario))
                payload["scenario"] = scenario;
            var json = JsonSerializer.Serialize(payload);
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            var resp = await _http.PostAsync(AssistantUrl + "/simulate", content);
            var body = await resp.Content.ReadAsStringAsync();
            Append("Scenario sim HTTP " + (int)resp.StatusCode + " " + Truncate(body.Replace("\r", "").Replace("\n", " "), 200));
            try
            {
                var tl = await _http.GetStringAsync(AssistantUrl + "/simulation/timeline");
                Append(Truncate(tl.Replace("\r", "").Replace("\n", " "), 400));
            }
            catch { /* ignore */ }
        }
        else
        {
            await RunCliAsync(args.ToArray());
        }
    }

    sealed record ProjectItem(string Label, string Path)
    {
        public override string ToString() => Label;
    }

    static string FindLabRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "QudLab.sln")))
                return dir.FullName;
            dir = dir.Parent;
        }
        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
    }
}
