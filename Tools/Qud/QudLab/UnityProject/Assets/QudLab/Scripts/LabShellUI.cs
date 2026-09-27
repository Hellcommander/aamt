using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace QudLab.Unity
{
    /// <summary>
    /// Lab shell chrome. Compile / type browser / Ollama agent talk to qudlab serve over HTTP
    /// (no Roslyn embedded). Ask / Scan all / Fix / Sim+Ask use POST /ai/run (Ollama tools).
    /// Open with Unity 6000.0.77f1 at E:\tools\Unity_Editor\6000.0.77f1.
    /// </summary>
    public sealed class LabShellUI : MonoBehaviour
    {
        [Header("Panels (wire in scene or auto-create)")]
        public Text statusText;
        public Text fileTreeText;
        public Text codePaneText;
        public Text typeBrowserText;
        public Text logText;
        public Button compileButton;
        public Button simulateButton;
        public Button indexButton;
        public InputField aiPromptField;
        public Button askAiButton;
        public Button scanAiButton;
        public Button fixAiButton;
        public Button analyzeAiButton;

        [Header("Phase 6 — mod + scenario")]
        public Button conflictsButton;
        public Button modPrevButton;
        public Button modNextButton;
        public Button scenarioCycleButton;
        public Button stressToggleButton;
        public Button gameLogsButton;
        public bool simulateStress;

        readonly System.Collections.Generic.List<string> _modPaths = new System.Collections.Generic.List<string>();
        readonly System.Collections.Generic.List<string> _modLabels = new System.Collections.Generic.List<string>();
        readonly System.Collections.Generic.List<string> _scenarioIds = new System.Collections.Generic.List<string>();
        readonly System.Collections.Generic.List<string> _scenarioLabels = new System.Collections.Generic.List<string>();
        int _modIndex;
        int _scenarioIndex;
        string _activeProjectLabel = "";

        [Header("Assistant")]
        public string assistantBaseUrl = "http://127.0.0.1:47821";

        readonly LabAssistantClient _client = new LabAssistantClient();
        string _status = "Qud Lab — starting gate…";
        string _log = "";
        bool _gateOk;
        bool _assistantOk;
        string _installRoot;
        bool _aiBusy;
        QudManagedHost _managedHost;
        bool _hostReady;
        QudRestrictedObjectSim _objectSim;
        public string simulateBlueprint = "Human";
        public int simulateTurns = 10;
        [Header("Chargen (Phase 4a HTTP — set scenario=chargen)")]
        public string simulateScenario = "";
        public string simulateGenotype = "Mutated Human";
        public string simulateSubtype = "Apostle";

        void Start()
        {
            _client.BaseUrl = assistantBaseUrl;
            EnsureUi();
            AppendLog("Qud Lab. ThreadingAPI is a separate WIP mod — not bundled.");
            RunGate();
            if (_gateOk)
                TryInitManagedHost();
            WireButtons();
            if (_gateOk)
                StartCoroutine(RefreshFromAssistant());
        }

        void WireButtons()
        {
            if (compileButton != null)
            {
                compileButton.interactable = _gateOk;
                compileButton.onClick.RemoveAllListeners();
                compileButton.onClick.AddListener(() => StartCoroutine(DoCompile()));
            }

            if (simulateButton != null)
            {
                simulateButton.interactable = _gateOk;
                simulateButton.onClick.RemoveAllListeners();
                simulateButton.onClick.AddListener(() => StartCoroutine(DoSimulate()));
            }

            if (indexButton != null)
            {
                indexButton.onClick.RemoveAllListeners();
                indexButton.onClick.AddListener(() => StartCoroutine(DoIndexRefresh()));
            }

            WireAiButton(askAiButton, () => StartCoroutine(DoAi("ask", apply: false, simulate: false)));
            WireAiButton(scanAiButton, () => StartCoroutine(DoAi("scan", apply: false, simulate: false)));
            WireAiButton(fixAiButton, () => StartCoroutine(DoAi("fix", apply: true, simulate: false)));
            WireAiButton(analyzeAiButton, () => StartCoroutine(DoAi("analyze", apply: false, simulate: true)));
        }

        static void WireAiButton(Button btn, UnityEngine.Events.UnityAction action)
        {
            if (btn == null)
                return;
            btn.onClick.RemoveAllListeners();
            btn.onClick.AddListener(action);
        }

        void EnsureUi()
        {
            var canvasGo = GameObject.Find("QudLabCanvas");
            if (canvasGo == null)
            {
                canvasGo = new GameObject("QudLabCanvas");
                var canvas = canvasGo.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvasGo.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                canvasGo.AddComponent<GraphicRaycaster>();
            }

            EnsureEventSystem();

            if (statusText == null)
                statusText = CreateLabel(canvasGo.transform, "Status", new Vector2(0, 250), new Vector2(980, 36));
            if (fileTreeText == null)
                fileTreeText = CreateLabel(canvasGo.transform, "Files", new Vector2(-340, 70), new Vector2(260, 260));
            if (codePaneText == null)
                codePaneText = CreateLabel(canvasGo.transform, "Code", new Vector2(0, 70), new Vector2(380, 260));
            if (typeBrowserText == null)
                typeBrowserText = CreateLabel(canvasGo.transform, "Types", new Vector2(340, 70), new Vector2(260, 260));
            if (logText == null)
                logText = CreateLabel(canvasGo.transform, "Log", new Vector2(0, -250), new Vector2(980, 90));

            EnsureAiChrome(canvasGo.transform);

            if (fileTreeText != null)
                fileTreeText.text = "File tree\n— start qudlab serve";
            if (codePaneText != null)
                codePaneText.text = "// Ask / Scan / Fix / Sim+Ask uses vLLM (:8000) or SGLang frontend (:30000)\n// qudlab serve + qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct\n// optional: qudlab sglang serve --remote";
            if (typeBrowserText != null)
                typeBrowserText.text = "Type browser\n— start qudlab serve";
            Refresh();
        }

        static void EnsureEventSystem()
        {
            if (FindFirstObjectByType<EventSystem>() != null)
                return;
            var es = new GameObject("EventSystem");
            es.AddComponent<EventSystem>();
            es.AddComponent<StandaloneInputModule>();
        }

        void EnsureAiChrome(Transform canvas)
        {
            if (aiPromptField == null)
                aiPromptField = CreateInput(canvas, "AiPrompt", "Ask local AI like Cursor — it can scan files, compile, simulate…", new Vector2(0, -120), new Vector2(980, 48));
            if (compileButton == null)
                compileButton = CreateButton(canvas, "CompileBtn", "Compile", new Vector2(-420, -175), new Vector2(110, 32));
            if (simulateButton == null)
                simulateButton = CreateButton(canvas, "SimulateBtn", "Simulate", new Vector2(-300, -175), new Vector2(110, 32));
            if (indexButton == null)
                indexButton = CreateButton(canvas, "IndexBtn", "Index", new Vector2(-180, -175), new Vector2(90, 32));
            if (askAiButton == null)
                askAiButton = CreateButton(canvas, "AskAiBtn", "Ask", new Vector2(-40, -175), new Vector2(90, 32), new Color(0.18f, 0.38f, 0.32f, 0.95f));
            if (scanAiButton == null)
                scanAiButton = CreateButton(canvas, "ScanAiBtn", "Scan all", new Vector2(70, -175), new Vector2(100, 32), new Color(0.2f, 0.3f, 0.42f, 0.95f));
            if (fixAiButton == null)
                fixAiButton = CreateButton(canvas, "FixAiBtn", "Fix", new Vector2(185, -175), new Vector2(90, 32), new Color(0.42f, 0.3f, 0.12f, 0.95f));
            if (analyzeAiButton == null)
                analyzeAiButton = CreateButton(canvas, "AnalyzeAiBtn", "Sim+Ask", new Vector2(310, -175), new Vector2(110, 32), new Color(0.32f, 0.2f, 0.4f, 0.95f));
            if (conflictsButton == null)
            {
                conflictsButton = CreateButton(canvas, "ConflictsBtn", "Conflicts", new Vector2(430, -175), new Vector2(100, 32), new Color(0.45f, 0.18f, 0.18f, 0.95f));
                conflictsButton.onClick.AddListener(() => StartCoroutine(DoConflicts()));
            }
            if (modPrevButton == null)
            {
                modPrevButton = CreateButton(canvas, "ModPrevBtn", "◀ mod", new Vector2(-420, -210), new Vector2(80, 28));
                modPrevButton.onClick.AddListener(() => StartCoroutine(CycleMod(-1)));
            }
            if (modNextButton == null)
            {
                modNextButton = CreateButton(canvas, "ModNextBtn", "mod ▶", new Vector2(-330, -210), new Vector2(80, 28));
                modNextButton.onClick.AddListener(() => StartCoroutine(CycleMod(1)));
            }
            if (scenarioCycleButton == null)
            {
                scenarioCycleButton = CreateButton(canvas, "ScenarioBtn", "Scenario", new Vector2(-220, -210), new Vector2(110, 28));
                scenarioCycleButton.onClick.AddListener(CycleScenario);
            }
            if (stressToggleButton == null)
            {
                stressToggleButton = CreateButton(canvas, "StressBtn", "stress: off", new Vector2(-90, -210), new Vector2(110, 28));
                stressToggleButton.onClick.AddListener(ToggleStress);
            }
            if (gameLogsButton == null)
            {
                gameLogsButton = CreateButton(canvas, "LogsBtn", "Logs", new Vector2(30, -210), new Vector2(80, 28));
                gameLogsButton.onClick.AddListener(() => StartCoroutine(DoGameLogs()));
            }
        }

        static Text CreateLabel(Transform parent, string name, Vector2 anchored, Vector2 size)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = size;
            rt.anchoredPosition = anchored;
            var text = go.AddComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (text.font == null)
                text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = 14;
            text.color = Color.white;
            text.alignment = TextAnchor.UpperLeft;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            return text;
        }

        static Button CreateButton(Transform parent, string name, string label, Vector2 anchored, Vector2 size, Color? color = null)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = size;
            rt.anchoredPosition = anchored;
            var img = go.AddComponent<Image>();
            img.color = color ?? new Color(0.18f, 0.32f, 0.28f, 0.95f);
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            var colors = btn.colors;
            colors.highlightedColor = img.color * 1.2f;
            colors.pressedColor = img.color * 0.7f;
            colors.disabledColor = new Color(0.2f, 0.2f, 0.2f, 0.55f);
            btn.colors = colors;

            var textGo = new GameObject("Label");
            textGo.transform.SetParent(go.transform, false);
            var trt = textGo.AddComponent<RectTransform>();
            trt.anchorMin = Vector2.zero;
            trt.anchorMax = Vector2.one;
            trt.offsetMin = Vector2.zero;
            trt.offsetMax = Vector2.zero;
            var text = textGo.AddComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (text.font == null)
                text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = 13;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = Color.white;
            text.text = label;
            return btn;
        }

        static InputField CreateInput(Transform parent, string name, string placeholder, Vector2 anchored, Vector2 size)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = size;
            rt.anchoredPosition = anchored;
            var img = go.AddComponent<Image>();
            img.color = new Color(0.1f, 0.12f, 0.16f, 0.95f);
            var input = go.AddComponent<InputField>();
            input.lineType = InputField.LineType.MultiLineNewline;

            var textGo = new GameObject("Text");
            textGo.transform.SetParent(go.transform, false);
            var trt = textGo.AddComponent<RectTransform>();
            trt.anchorMin = Vector2.zero;
            trt.anchorMax = Vector2.one;
            trt.offsetMin = new Vector2(8, 4);
            trt.offsetMax = new Vector2(-8, -4);
            var text = textGo.AddComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (text.font == null)
                text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = 14;
            text.color = Color.white;
            text.supportRichText = false;
            text.alignment = TextAnchor.UpperLeft;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Overflow;

            var phGo = new GameObject("Placeholder");
            phGo.transform.SetParent(go.transform, false);
            var prt = phGo.AddComponent<RectTransform>();
            prt.anchorMin = Vector2.zero;
            prt.anchorMax = Vector2.one;
            prt.offsetMin = new Vector2(8, 4);
            prt.offsetMax = new Vector2(-8, -4);
            var ph = phGo.AddComponent<Text>();
            ph.font = text.font;
            ph.fontSize = 14;
            ph.fontStyle = FontStyle.Italic;
            ph.color = new Color(1, 1, 1, 0.35f);
            ph.text = placeholder;
            ph.alignment = TextAnchor.UpperLeft;

            input.textComponent = text;
            input.placeholder = ph;
            return input;
        }

        void RunGate()
        {
            if (!QudInstallProbe.TryFind(out var found, out var reason))
            {
                _gateOk = false;
                _installRoot = null;
                _status = "FAIL — Caves of Qud not found. Own Steam/GOG install required.";
                AppendLog(_status + " (" + reason + ")");
                Refresh();
                return;
            }

            _gateOk = true;
            _installRoot = found;
            _status = "PASS — bound " + found;
            AppendLog(_status);
            AppendLog("Assets/DLLs load from install only. Editor: E:\\tools\\Unity_Editor\\6000.0.77f1");
            var managed = QudInstallProbe.ManagedPath(found);
            var dllCount = System.IO.Directory.Exists(managed)
                ? System.IO.Directory.GetFiles(managed, "*.dll").Length
                : 0;
            AppendLog($"Managed refs available: {dllCount} DLLs");
            Refresh();
        }

        void TryInitManagedHost()
        {
            AppendLog("Phase 4b: initializing Managed host (LoadFrom install)…");
            if (!QudManagedHost.TryInitialize(_installRoot, out _managedHost, out var err))
            {
                _hostReady = false;
                AppendLog("host=failed: " + err);
                AppendLog("Simulate will fall back to POST /simulate (Phase 4a).");
                _status = "PASS install — host failed (synthetic simulate OK)";
                Refresh();
                return;
            }

            _hostReady = _managedHost != null && _managedHost.IsReady;
            AppendLog("host=" + (_hostReady ? "ready" : "failed") + " — " + _managedHost.Status);
            if (_hostReady)
            {
                _objectSim = new QudRestrictedObjectSim(_managedHost);
                _status = "PASS — install + object host";
            }
            Refresh();
        }

        IEnumerator RefreshFromAssistant()
        {
            yield return _client.Get("/health", (ok, body) =>
            {
                _assistantOk = ok;
                if (!ok)
                {
                    _status = "PASS install — start `qudlab serve` for type browser / compile";
                    if (typeBrowserText != null)
                        typeBrowserText.text = "Type browser offline\nstart qudlab serve";
                    if (fileTreeText != null)
                        fileTreeText.text = "File tree offline\nstart qudlab serve";
                    AppendLog("Assistant down: " + (body ?? "unreachable"));
                    Refresh();
                }
            });

            if (!_assistantOk)
                yield break;

            _status = "PASS — install + assistant :" + ExtractPort();
            AppendLog("Assistant healthy.");

            yield return _client.Get("/project", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                    return;
                var name = ExtractJsonString(body, "name") ?? ExtractJsonString(body, "rootPath");
                _activeProjectLabel = name ?? "";
                if (!string.IsNullOrEmpty(name))
                    _status = "PASS — project: " + Truncate(name, 60);
            });

            yield return _client.Get("/mods", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                    return;
                ParseModsJson(body);
            });

            yield return _client.Get("/simulate/scenarios", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                    return;
                ParseScenariosJson(body);
            });

            yield return _client.Get("/browse?q=IPart&limit=40", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body) || typeBrowserText == null)
                    return;
                typeBrowserText.text = FormatBrowse(body);
            });

            yield return _client.Get("/project/files", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body) || fileTreeText == null)
                    return;
                fileTreeText.text = FormatFiles(body);
            });

            yield return _client.Get("/diagnostics", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body) || codePaneText == null)
                    return;
                codePaneText.text = FormatDiagnostics(body);
            });

            yield return _client.Get("/ai/status", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                {
                    AppendLog("LLM agent offline — start `qudlab serve` then `qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct`.");
                    return;
                }

                var reachable = body.IndexOf("\"available\":true", StringComparison.OrdinalIgnoreCase) >= 0
                    || body.IndexOf("\"vllm\":true", StringComparison.OrdinalIgnoreCase) >= 0
                    || body.IndexOf("\"sglang\":true", StringComparison.OrdinalIgnoreCase) >= 0
                    || body.IndexOf("\"ollama\":true", StringComparison.OrdinalIgnoreCase) >= 0;
                var backend = ExtractJsonString(body, "backend") ?? "llm";
                var model = ExtractJsonString(body, "resolvedModel") ?? ExtractJsonString(body, "defaultModel");
                AppendLog(reachable
                    ? backend + " OK" + (string.IsNullOrEmpty(model) ? "" : " model=" + model)
                    : backend + " down — qudlab vllm serve --model Qwen/Qwen2.5-3B-Instruct");
            }, 8);

            Refresh();
        }

        IEnumerator DoCompile()
        {
            AppendLog("Compile → POST /compile …");
            yield return _client.PostJson("/compile", "{}", (ok, code, body) =>
            {
                if (string.IsNullOrEmpty(body))
                {
                    AppendLog("Compile failed: empty response (is serve running?)");
                    return;
                }

                if (codePaneText != null)
                    codePaneText.text = Truncate(body, 3500);
                AppendLog(ok || code == 422
                    ? "Compile response HTTP " + code
                    : "Compile error: " + Truncate(body, 400));
            });

            yield return _client.Get("/diagnostics", (ok, body) =>
            {
                if (ok && !string.IsNullOrEmpty(body) && codePaneText != null)
                    codePaneText.text = FormatDiagnostics(body);
            });
        }

        IEnumerator DoSimulate()
        {
            var chargen = !string.IsNullOrWhiteSpace(simulateScenario)
                          && simulateScenario.IndexOf("chargen", StringComparison.OrdinalIgnoreCase) >= 0;
            var worldgen = !string.IsNullOrWhiteSpace(simulateScenario)
                           && (simulateScenario.IndexOf("worldgen", StringComparison.OrdinalIgnoreCase) >= 0
                               || simulateScenario.IndexOf("getzone", StringComparison.OrdinalIgnoreCase) >= 0
                               || simulateScenario.IndexOf("embark-boot", StringComparison.OrdinalIgnoreCase) >= 0
                               || simulateScenario.IndexOf("starting-game", StringComparison.OrdinalIgnoreCase) >= 0);
            if (worldgen && _hostReady && _managedHost != null)
            {
                var zone = string.IsNullOrWhiteSpace(simulateBlueprint) || simulateBlueprint.IndexOf('.') < 0
                    ? "JoppaWorld.11.22.1.1.10"
                    : simulateBlueprint.Trim();
                AppendLog("Simulate → Phase 4b GetZone probe (" + zone + ") then HTTP worldgen-getzone…");
                try
                {
                    var probe = QudZoneGetProbe.Probe(_managedHost, zone);
                    if (codePaneText != null)
                    {
                        var sb = new System.Text.StringBuilder();
                        sb.AppendLine("// Phase 4b GetZone probe");
                        foreach (var line in probe.log)
                            sb.AppendLine(line);
                        codePaneText.text = Truncate(sb.ToString(), 3500);
                    }
                    AppendLog(probe.stats.ContainsKey("Invoked")
                        ? "GetZone probe invoked=" + probe.stats["Invoked"]
                        : "GetZone probe (types only)");
                    var json = QudRestrictedObjectSim.ToIngestJson(probe);
                    yield return _client.PostJson("/simulation/ingest", json, (ok, code, body) =>
                    {
                        AppendLog(ok ? "Ingested GetZone probe HTTP " + code : "Ingest skipped: " + Truncate(body ?? "", 160));
                    });
                }
                catch (Exception ex)
                {
                    AppendLog("GetZone probe failed: " + ex.Message);
                }
                yield return DoSimulateHttp();
                yield break;
            }

            if (!chargen && _hostReady && _managedHost != null)
            {
                if (_objectSim == null)
                    _objectSim = new QudRestrictedObjectSim(_managedHost);

                var turns = Mathf.Max(simulateTurns, QudRestrictedObjectSim.MinUsefulTurns);
                var bp = string.IsNullOrWhiteSpace(simulateBlueprint) ? "Human" : simulateBlueprint;
                AppendLog("Simulate → Phase 4b multi-turn on one entity (" + bp + ", " + turns + " turns)…");

                QudRestrictedObjectSim.Result result = null;
                Exception runEx = null;
                try
                {
                    // First click spawns; later clicks ContinueTurns on the same entity ref.
                    result = _objectSim.ActiveEntity != null
                             && string.Equals(_objectSim.ActiveBlueprint, bp, StringComparison.OrdinalIgnoreCase)
                        ? _objectSim.ContinueTurns(turns, restrictedDebugOnly: true)
                        : _objectSim.RunTicks(bp, turns, restrictedDebugOnly: true, forceRespawn: false);
                }
                catch (Exception ex)
                {
                    runEx = ex;
                }

                if (runEx != null)
                {
                    AppendLog("Object host tick crashed: " + runEx.Message + " — falling back to HTTP.");
                    _objectSim?.ClearEntity();
                    yield return DoSimulateHttp();
                    yield break;
                }

                if (result != null && !result.success && result.log.Count > 0
                    && result.log[0].IndexOf("no live entity", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    AppendLog("No live entity — falling back to Phase 4a HTTP (multi-turn synthetic).");
                    yield return DoSimulateHttp();
                    yield break;
                }

                if (codePaneText != null && result != null)
                {
                    var sb = new StringBuilder();
                    sb.AppendLine("// Phase 4b — entityRef=" + result.entityRef + " id=" + (result.entityId ?? "?"));
                    sb.AppendLine("// reused=" + result.reusedEntity + " turns=" + result.turnsExecuted);
                    foreach (var line in result.log)
                        sb.AppendLine(line);
                    codePaneText.text = Truncate(sb.ToString(), 3500);
                }

                if (typeBrowserText != null && result != null)
                {
                    var sb = new StringBuilder();
                    sb.AppendLine("Turn timeline (same entity)");
                    sb.AppendLine("ref=" + result.entityRef + " id=" + (result.entityId ?? "?"));
                    var n = 0;
                    foreach (var e in result.timeline)
                    {
                        if (n++ >= 80) break;
                        sb.AppendLine("t" + e.turn + " " + e.kind + " " + e.label
                                      + (string.IsNullOrEmpty(e.detail) ? "" : " | " + e.detail));
                    }

                    typeBrowserText.text = sb.ToString();
                }

                AppendLog(result != null && result.success
                    ? "Object host OK entityRef=" + result.entityRef
                      + " turns=" + result.turnsExecuted
                      + (result.reusedEntity ? " (continued)" : " (spawned)")
                    : "Object host failed — see log");

                if (result != null)
                {
                    var json = QudRestrictedObjectSim.ToIngestJson(result);
                    yield return _client.PostJson("/simulation/ingest", json, (ok, code, body) =>
                    {
                        AppendLog(ok
                            ? "Ingested timeline → assistant HTTP " + code
                            : "Ingest skipped/failed (serve down?): " + Truncate(body ?? "", 200));
                    });
                }

                yield break;
            }

            if (chargen)
                AppendLog("Chargen → Phase 4a HTTP (no GetZone).");
            else if (worldgen)
                AppendLog("Worldgen/GetZone → Phase 4a HTTP.");
            else
                AppendLog("Object host not ready — Phase 4a HTTP simulate.");
            yield return DoSimulateHttp();
        }

        IEnumerator DoSimulateHttp()
        {
            AppendLog("Simulate → POST /simulate …");
            var turns = Mathf.Max(simulateTurns, 0);
            var bp = string.IsNullOrWhiteSpace(simulateBlueprint) ? "Human" : simulateBlueprint;
            var sb = new StringBuilder();
            sb.Append("{\"blueprint\":\"").Append(EscapeJson(bp)).Append("\",\"turns\":").Append(turns)
                .Append(",\"stress\":").Append(simulateStress ? "true" : "false");
            if (!string.IsNullOrWhiteSpace(simulateScenario))
            {
                sb.Append(",\"scenario\":\"").Append(EscapeJson(simulateScenario.Trim())).Append("\"");
                if (!string.IsNullOrWhiteSpace(simulateGenotype))
                    sb.Append(",\"genotype\":\"").Append(EscapeJson(simulateGenotype.Trim())).Append("\"");
                if (!string.IsNullOrWhiteSpace(simulateSubtype))
                    sb.Append(",\"subtype\":\"").Append(EscapeJson(simulateSubtype.Trim())).Append("\"");
                if (bp.IndexOf('.') >= 0 && char.IsDigit(bp[bp.Length - 1]))
                    sb.Append(",\"zoneId\":\"").Append(EscapeJson(bp)).Append("\"");
            }
            sb.Append('}');
            var bodyJson = sb.ToString();
            yield return _client.PostJson("/simulate", bodyJson, (ok, code, body) =>
            {
                if (string.IsNullOrEmpty(body))
                {
                    AppendLog("Simulate failed: empty response — start `qudlab serve`");
                    return;
                }

                if (codePaneText != null)
                    codePaneText.text = "// Sim log\n" + Truncate(body, 3500);
                AppendLog(ok || code == 422
                    ? "Simulate HTTP " + code
                    : "Simulate error: " + Truncate(body, 400));
            });

            yield return _client.Get("/simulation/timeline", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                {
                    if (!_assistantOk)
                        AppendLog("start `qudlab serve` for timeline");
                    return;
                }

                if (typeBrowserText != null)
                    typeBrowserText.text = FormatTimeline(body);
            });
        }

        IEnumerator DoIndexRefresh()
        {
            AppendLog("Index: refreshing /cache/status (reindex via CLI if stale).");
            yield return _client.Get("/cache/status", (ok, body) =>
            {
                if (!ok)
                {
                    AppendLog("start `qudlab serve` (and `qudlab index` if cache missing)");
                    return;
                }

                AppendLog(Truncate(body ?? "", 500));
            });
            yield return RefreshFromAssistant();
            yield return _client.Get("/simulation/timeline", (ok, body) =>
            {
                if (ok && !string.IsNullOrEmpty(body) && typeBrowserText != null && body.Contains("\"kind\""))
                    typeBrowserText.text = FormatTimeline(body) + "\n---\n" + typeBrowserText.text;
            });
        }

        IEnumerator DoAi(string mode, bool apply, bool simulate)
        {
            if (_aiBusy)
            {
                AppendLog("AI already running.");
                yield break;
            }

            var prompt = aiPromptField != null ? aiPromptField.text : "";
            if (string.IsNullOrWhiteSpace(prompt))
            {
                prompt = mode switch
                {
                    "scan" => "Find compile errors, wrong XRL types, and logic bugs in every workspace file.",
                    "fix" => "Fix compile errors and API misuse in Workspace/src.",
                    "analyze" => "Simulate, then scan all files and explain the issue.",
                    _ => "Inspect this Caves of Qud mod. Use tools; do not guess type names."
                };
            }

            SetAiBusy(true);
            AppendLog("Ollama " + mode + " — local model may take several minutes (tools: scan/compile/simulate)…");
            var bodyJson = "{\"prompt\":\"" + EscapeJson(prompt) + "\",\"mode\":\"" + mode
                           + "\",\"apply\":" + (apply ? "true" : "false")
                           + ",\"simulate\":" + (simulate ? "true" : "false")
                           + ",\"turns\":" + Mathf.Max(simulateTurns, 2)
                           + ",\"blueprint\":\"" + EscapeJson(string.IsNullOrWhiteSpace(simulateBlueprint) ? "Human" : simulateBlueprint) + "\""
                           + (string.IsNullOrWhiteSpace(simulateScenario) ? "" : ",\"scenario\":\"" + EscapeJson(simulateScenario) + "\"")
                           + "}";

            yield return _client.PostJson("/ai/run", bodyJson, (ok, code, body) =>
            {
                if (string.IsNullOrEmpty(body))
                {
                    AppendLog("AI failed: empty response — start `qudlab serve` and Ollama.");
                    return;
                }

                var reply = ExtractJsonString(body, "reply");
                var err = ExtractJsonString(body, "error");
                var model = ExtractJsonString(body, "model");
                var written = CountJsonArray(body, "written");
                var tools = CountJsonArray(body, "tools");
                if (codePaneText != null)
                    codePaneText.text = Truncate(
                        "// Ollama " + mode + (string.IsNullOrEmpty(model) ? "" : " (" + model + ")") + "\n"
                        + (string.IsNullOrEmpty(reply) ? Truncate(body, 3500) : reply),
                        4000);
                AppendLog((ok ? "AI HTTP " : "AI error HTTP ") + code
                          + " tools=" + tools
                          + " wrote=" + written
                          + (string.IsNullOrEmpty(err) ? "" : " " + Truncate(err, 160)));
            }, 600);

            SetAiBusy(false);
            yield return _client.Get("/project/files", (ok, body) =>
            {
                if (ok && !string.IsNullOrEmpty(body) && fileTreeText != null)
                    fileTreeText.text = FormatFiles(body);
            });
        }

        void SetAiBusy(bool busy)
        {
            _aiBusy = busy;
            if (askAiButton != null) askAiButton.interactable = !busy;
            if (scanAiButton != null) scanAiButton.interactable = !busy;
            if (fixAiButton != null) fixAiButton.interactable = !busy;
            if (analyzeAiButton != null) analyzeAiButton.interactable = !busy;
        }

        static string FormatBrowse(string json)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Type browser");
            // Lightweight parse without JsonUtility models: pull fullName lines
            var marker = "\"fullName\":\"";
            var idx = 0;
            var n = 0;
            while ((idx = json.IndexOf(marker, idx, System.StringComparison.Ordinal)) >= 0 && n < 40)
            {
                idx += marker.Length;
                var end = json.IndexOf('"', idx);
                if (end < 0) break;
                sb.AppendLine(json.Substring(idx, end - idx));
                idx = end + 1;
                n++;
            }

            if (n == 0)
                sb.AppendLine(Truncate(json, 1200));
            return sb.ToString();
        }

        static string FormatTimeline(string json)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Sim timeline");
            var kindMarker = "\"kind\":\"";
            var labelMarker = "\"label\":\"";
            var idx = 0;
            var n = 0;
            while ((idx = json.IndexOf(kindMarker, idx, System.StringComparison.Ordinal)) >= 0 && n < 60)
            {
                idx += kindMarker.Length;
                var kend = json.IndexOf('"', idx);
                if (kend < 0) break;
                var kind = json.Substring(idx, kend - idx);
                var label = "";
                var lpos = json.IndexOf(labelMarker, kend, System.StringComparison.Ordinal);
                if (lpos >= 0 && lpos < kend + 80)
                {
                    lpos += labelMarker.Length;
                    var lend = json.IndexOf('"', lpos);
                    if (lend > lpos)
                        label = json.Substring(lpos, lend - lpos);
                }

                sb.AppendLine(kind + (string.IsNullOrEmpty(label) ? "" : " " + label));
                idx = kend + 1;
                n++;
            }

            if (n == 0)
                sb.AppendLine(Truncate(json, 1500));
            return sb.ToString();
        }

        static string FormatFiles(string json)
        {
            var sb = new StringBuilder();
            var root = ExtractJsonString(json, "root");
            sb.AppendLine(string.IsNullOrEmpty(root) ? "Project files" : "Project: " + Truncate(root, 48));
            var marker = "\"";
            // Prefer files array entries ending in .cs
            var idx = 0;
            var n = 0;
            while ((idx = json.IndexOf(".cs\"", idx, System.StringComparison.OrdinalIgnoreCase)) >= 0 && n < 50)
            {
                var start = json.LastIndexOf('"', idx);
                if (start >= 0 && idx > start)
                {
                    var path = json.Substring(start + 1, idx - start + 2);
                    sb.AppendLine(System.IO.Path.GetFileName(path.Replace('/', '\\')));
                    n++;
                }
                idx += 4;
            }

            if (n == 0)
                sb.AppendLine(Truncate(json, 800));
            return sb.ToString();
        }

        static string FormatDiagnostics(string json)
        {
            var sb = new StringBuilder();
            sb.AppendLine("// Last compile diagnostics");
            var marker = "\"diagnostics\":";
            var i = json.IndexOf(marker, System.StringComparison.Ordinal);
            if (i < 0)
                return Truncate(json, 2000);
            sb.AppendLine(Truncate(json.Substring(i), 3000));
            return sb.ToString();
        }

        string ExtractPort()
        {
            try
            {
                var u = new System.Uri(assistantBaseUrl);
                return u.Port.ToString();
            }
            catch
            {
                return "47821";
            }
        }

        static string Truncate(string s, int max) =>
            string.IsNullOrEmpty(s) ? "" : (s.Length <= max ? s : s.Substring(0, max) + "…");

        static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s))
                return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t");
        }

        static string ExtractJsonString(string json, string key)
        {
            var marker = "\"" + key + "\":";
            var i = json.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (i < 0)
                return null;
            i += marker.Length;
            while (i < json.Length && char.IsWhiteSpace(json[i]))
                i++;
            if (i < json.Length && json[i] == 'n')
                return null;
            if (i >= json.Length || json[i] != '"')
                return null;
            i++;
            var sb = new StringBuilder();
            for (; i < json.Length; i++)
            {
                var c = json[i];
                if (c == '\\' && i + 1 < json.Length)
                {
                    var n = json[++i];
                    sb.Append(n switch { 'n' => '\n', 'r' => '\r', 't' => '\t', '"' => '"', '\\' => '\\', _ => n });
                    continue;
                }
                if (c == '"')
                    break;
                sb.Append(c);
            }
            return sb.ToString();
        }

        static int CountJsonArray(string json, string key)
        {
            var marker = "\"" + key + "\":";
            var i = json.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (i < 0)
                return 0;
            var start = json.IndexOf('[', i);
            var end = json.IndexOf(']', start + 1);
            if (start < 0 || end < 0 || end <= start + 1)
                return 0;
            var slice = json.Substring(start, end - start);
            var n = 0;
            for (var p = 0; p < slice.Length; p++)
            {
                if (slice[p] == '{' || (key == "written" && slice[p] == '"'))
                    n++;
            }
            if (key == "written")
                return n / 2;
            return n;
        }

        void AppendLog(string line)
        {
            _log = line + "\n" + _log;
            if (_log.Length > 4000)
                _log = _log.Substring(0, 4000);
            Refresh();
        }

        IEnumerator DoGameLogs()
        {
            AppendLog("Logs → GET /logs/game?kind=threading …");
            yield return _client.Get("/logs/game?kind=threading&tail=80", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                {
                    AppendLog("Logs failed — start qudlab serve; enable THREADINGAPI_ACTION_LOG in-game");
                    return;
                }
                if (codePaneText != null)
                    codePaneText.text = Truncate(body, 3500);
                AppendLog("ThreadingAPI log tail loaded");
            });
        }

        IEnumerator DoConflicts()
        {
            AppendLog("Conflicts → GET /project/conflicts …");
            yield return _client.Get("/project/conflicts", (ok, body) =>
            {
                if (!ok || string.IsNullOrEmpty(body))
                {
                    AppendLog("Conflicts failed — start qudlab serve");
                    return;
                }
                var text = ExtractJsonString(body, "text") ?? body;
                if (codePaneText != null)
                    codePaneText.text = Truncate(text, 3500);
                AppendLog("Type conflicts loaded (" + text.Length + " chars)");
            });
        }

        IEnumerator CycleMod(int delta)
        {
            if (_modPaths.Count == 0)
            {
                AppendLog("No mods loaded — start qudlab serve");
                yield break;
            }
            _modIndex = (_modIndex + delta + _modPaths.Count) % _modPaths.Count;
            var path = _modPaths[_modIndex];
            var label = _modLabels.Count > _modIndex ? _modLabels[_modIndex] : path;
            var json = "{\"path\":\"" + EscapeJson(path) + "\"}";
            yield return _client.PostJson("/project/set", json, (ok, code, body) =>
            {
                AppendLog(ok ? "Hot-switched mod: " + label : "Set mod failed HTTP " + code);
                if (ok)
                {
                    _activeProjectLabel = label;
                    _status = "PASS — project: " + Truncate(label, 60);
                    Refresh();
                }
            });
            yield return _client.Get("/project/files", (ok, body) =>
            {
                if (ok && !string.IsNullOrEmpty(body) && fileTreeText != null)
                    fileTreeText.text = FormatFiles(body);
            });
        }

        void CycleScenario()
        {
            if (_scenarioIds.Count == 0)
            {
                _scenarioIds.Add("");
                _scenarioLabels.Add("(default)");
            }
            _scenarioIndex = (_scenarioIndex + 1) % _scenarioIds.Count;
            simulateScenario = _scenarioIds[_scenarioIndex];
            var label = _scenarioLabels.Count > _scenarioIndex ? _scenarioLabels[_scenarioIndex] : simulateScenario;
            if (scenarioCycleButton != null)
            {
                var btnText = scenarioCycleButton.GetComponentInChildren<Text>();
                if (btnText != null)
                    btnText.text = string.IsNullOrEmpty(simulateScenario) ? "Scenario" : Truncate(label, 14);
            }
            AppendLog("Scenario: " + (string.IsNullOrEmpty(simulateScenario) ? "(default)" : simulateScenario));
        }

        void ToggleStress()
        {
            simulateStress = !simulateStress;
            if (stressToggleButton != null)
            {
                var btnText = stressToggleButton.GetComponentInChildren<Text>();
                if (btnText != null)
                    btnText.text = simulateStress ? "stress: ON" : "stress: off";
            }
            AppendLog("Sim stress=" + simulateStress);
        }

        void ParseModsJson(string json)
        {
            _modPaths.Clear();
            _modLabels.Clear();
            var pathMarker = "\"path\":\"";
            var titleMarker = "\"title\":\"";
            var idx = 0;
            while ((idx = json.IndexOf(pathMarker, idx, StringComparison.Ordinal)) >= 0)
            {
                idx += pathMarker.Length;
                var end = json.IndexOf('"', idx);
                if (end < 0) break;
                var path = json.Substring(idx, end - idx).Replace("\\\\", "\\");
                var title = path;
                var tpos = json.LastIndexOf(titleMarker, idx, Math.Min(400, idx));
                if (tpos >= 0)
                {
                    tpos += titleMarker.Length;
                    var tend = json.IndexOf('"', tpos);
                    if (tend > tpos)
                        title = json.Substring(tpos, tend - tpos);
                }
                _modPaths.Add(path);
                _modLabels.Add(title);
                idx = end + 1;
            }
            if (_modPaths.Count > 0 && _modIndex >= _modPaths.Count)
                _modIndex = 0;
        }

        void ParseScenariosJson(string json)
        {
            _scenarioIds.Clear();
            _scenarioLabels.Clear();
            _scenarioIds.Add("");
            _scenarioLabels.Add("(default)");
            var idMarker = "\"id\":\"";
            var labelMarker = "\"label\":\"";
            var idx = 0;
            while ((idx = json.IndexOf(idMarker, idx, StringComparison.Ordinal)) >= 0)
            {
                idx += idMarker.Length;
                var end = json.IndexOf('"', idx);
                if (end < 0) break;
                var id = json.Substring(idx, end - idx);
                var label = id;
                var lpos = json.IndexOf(labelMarker, end, StringComparison.Ordinal);
                if (lpos >= 0 && lpos < end + 120)
                {
                    lpos += labelMarker.Length;
                    var lend = json.IndexOf('"', lpos);
                    if (lend > lpos)
                        label = json.Substring(lpos, lend - lpos);
                }
                if (!string.IsNullOrEmpty(id))
                {
                    _scenarioIds.Add(id);
                    _scenarioLabels.Add(label);
                }
                idx = end + 1;
            }
            _scenarioIndex = 0;
            simulateScenario = "";
        }

        void Refresh()
        {
            if (statusText != null)
            {
                var extra = string.IsNullOrEmpty(_activeProjectLabel) ? "" : " | " + Truncate(_activeProjectLabel, 48);
                statusText.text = _status + extra;
            }
            if (logText != null) logText.text = _log;
        }
    }
}
