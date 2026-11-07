using System;
using System.Drawing;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.WinForms;

namespace AAMT.AudioBench
{
    internal sealed class MainForm : Form
    {
        private readonly string[] _args;
        private ToolkitLocation _loc;
        private BenchServer _server;
        private WebView2 _web;
        private TextBox _log;
        private SplitContainer _split;
        private ToolStripStatusLabel _status;
        private ToolStripMenuItem _logItem;

        public MainForm(string[] args)
        {
            _args = args;
            Text = "Audio Bench";
            Width = 1480; Height = 980;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(7, 19, 28);
            BuildUi();
            Shown += async (s, e) => await StartAsync();
            FormClosed += (s, e) => _server?.Dispose();
        }

        private void BuildUi()
        {
            var menu = new MenuStrip();
            var file = new ToolStripMenuItem("&File");
            file.DropDownItems.Add("&Open sound as source...", null, async (s, e) => await OpenSoundAsync());
            file.DropDownItems.Add("&Export last render...", null, async (s, e) => await ExportAsync());
            file.DropDownItems.Add(new ToolStripSeparator());
            file.DropDownItems.Add("&Restart server", null, async (s, e) => { _server?.Dispose(); await StartAsync(); });
            file.DropDownItems.Add("Choose &toolkit folder / Python...", null, (s, e) => ChooseToolkit());
            file.DropDownItems.Add(new ToolStripSeparator());
            file.DropDownItems.Add("E&xit", null, (s, e) => Close());
            var view = new ToolStripMenuItem("&View");
            _logItem = new ToolStripMenuItem("Server &log") { CheckOnClick = true, Checked = true };
            _logItem.CheckedChanged += (s, e) => _split.Panel2Collapsed = !_logItem.Checked;
            view.DropDownItems.Add(_logItem);
            view.DropDownItems.Add("&Reload page", null, (s, e) => _web?.Reload());
            view.DropDownItems.Add("Open in &browser", null, (s, e) => { if (_server != null) System.Diagnostics.Process.Start(_server.Url); });
            var help = new ToolStripMenuItem("&Help");
            help.DropDownItems.Add("&Catalog (effects, presets, recipe schema)", null, (s, e) => { if (_server != null) _web.CoreWebView2?.Navigate(_server.Url + "api/catalog"); });
            help.DropDownItems.Add("&Bench page", null, (s, e) => { if (_server != null) _web.CoreWebView2?.Navigate(_server.Url); });
            help.DropDownItems.Add("&About", null, (s, e) => MessageBox.Show(this,
                "AAMT Audio Bench\n\nProgrammatic mixing, blending and sound shaping. The page and every effect come from the toolkit repo " +
                "(Tools/Shared/audio_bench*.py); this program finds the repo and its Python, runs the bench server, and shows the page.\n\n" +
                "No model touches audio: the agent and the listener only decide and judge.", "About", MessageBoxButtons.OK, MessageBoxIcon.Information));
            menu.Items.AddRange(new ToolStripItem[] { file, view, help });
            MainMenuStrip = menu;

            var statusBar = new StatusStrip();
            _status = new ToolStripStatusLabel("starting") { Spring = true, TextAlign = ContentAlignment.MiddleLeft };
            statusBar.Items.Add(_status);

            _split = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 760, BackColor = Color.FromArgb(31, 95, 110) };
            _web = new WebView2 { Dock = DockStyle.Fill, DefaultBackgroundColor = Color.FromArgb(7, 19, 28) };
            _log = new TextBox { Dock = DockStyle.Fill, Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, BackColor = Color.FromArgb(6, 16, 24), ForeColor = Color.FromArgb(127, 168, 179), Font = new Font("Consolas", 9f), BorderStyle = BorderStyle.None };
            _split.Panel1.Controls.Add(_web);
            _split.Panel2.Controls.Add(_log);

            Controls.Add(_split);
            Controls.Add(statusBar);
            Controls.Add(menu);
        }

        private void Log(string line)
        {
            if (IsDisposed) return;
            if (InvokeRequired) { BeginInvoke(new Action<string>(Log), line); return; }
            _log.AppendText(line + Environment.NewLine);
        }

        private void Status(string text)
        {
            if (InvokeRequired) { BeginInvoke(new Action<string>(Status), text); return; }
            _status.Text = text;
        }

        private bool Locate()
        {
            var tools = ToolkitLocation.FindToolsDir();
            var python = tools != null ? ToolkitLocation.FindPython(tools) : null;
            if (tools == null || python == null)
            {
                MessageBox.Show(this, tools == null
                    ? "This program lives in the AI asset toolkit's Tools folder (or a folder under it). It could not find Tools\\Shared\\audio_bench_server.py from here; pick the toolkit's Tools folder."
                    : "No Python found (TranscendenceTools.ini PythonPath, miniconda, or PATH). Pick python.exe.", "Audio Bench", MessageBoxButtons.OK, MessageBoxIcon.Information);
                ChooseToolkit(tools, python);
                return _loc != null && _loc.Valid;
            }
            _loc = new ToolkitLocation { ToolsDir = tools, Python = python };
            _loc.Save();
            return true;
        }

        private void ChooseToolkit(string tools = null, string python = null)
        {
            tools = tools ?? _loc?.ToolsDir;
            python = python ?? _loc?.Python;
            if (tools == null || !File.Exists(Path.Combine(tools, "Shared", "audio_bench_server.py")))
            {
                using (var d = new FolderBrowserDialog { Description = "The toolkit's Tools folder (holds Shared\\audio_bench_server.py)" })
                {
                    if (d.ShowDialog(this) != DialogResult.OK) return;
                    tools = d.SelectedPath;
                }
            }
            if (python == null || !File.Exists(python))
            {
                using (var d = new OpenFileDialog { Title = "python.exe to run the bench with", Filter = "python.exe|python.exe" })
                {
                    if (d.ShowDialog(this) != DialogResult.OK) return;
                    python = d.FileName;
                }
            }
            _loc = new ToolkitLocation { ToolsDir = tools, Python = python };
            if (_loc.Valid) _loc.Save();
            else MessageBox.Show(this, "That folder has no Shared\\audio_bench_server.py, or the Python path is wrong.", "Audio Bench", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }

        private async Task StartAsync()
        {
            if (_loc == null || !_loc.Valid)
            {
                if (!Locate()) { Status("no toolkit: File > Choose toolkit folder / Python"); return; }
            }
            Status("starting the bench server from " + _loc.SharedDir + " with " + _loc.Python);
            _server = new BenchServer();
            _server.Line += Log;
            _server.Exited += () => Status("the bench server stopped; File > Restart server");
            bool ok = await _server.StartAsync(_loc);
            if (!ok)
            {
                Status("the bench server did not start; see the log (missing Python packages? numpy, scipy, soundfile)");
                return;
            }
            Status("bench at " + _server.Url + "  ·  python " + _loc.Python);
            try
            {
                await _web.EnsureCoreWebView2Async();
                _web.CoreWebView2.Settings.AreDevToolsEnabled = true;
                _web.CoreWebView2.Navigate(_server.Url);
                _web.CoreWebView2.NewWindowRequested += (s, e) => { e.Handled = true; _web.CoreWebView2.Navigate(e.Uri); };
            }
            catch (Exception ex)
            {
                Log("WebView2 is not available (" + ex.Message + "); opening the page in your browser instead.");
                System.Diagnostics.Process.Start(_server.Url);
            }
            foreach (var arg in _args)
                if (File.Exists(arg)) await AddSourceAsync(arg);
        }

        private async Task OpenSoundAsync()
        {
            using (var d = new OpenFileDialog { Title = "Sound to load as a source", Filter = "Sounds|*.wav;*.ogg;*.flac;*.mp3;*.aif;*.aiff|All files|*.*", Multiselect = true })
            {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                foreach (var f in d.FileNames) await AddSourceAsync(f);
            }
        }

        private async Task AddSourceAsync(string path)
        {
            if (_server == null || !_server.Running) return;
            var name = Path.GetFileNameWithoutExtension(path);
            var reply = await BenchApi.PostAsync(_server.Url + "api/source_path", "{\"name\":" + BenchApi.JsonString(name) + ",\"path\":" + BenchApi.JsonString(path) + "}");
            Log("source " + name + ": " + (reply.Length > 160 ? reply.Substring(0, 160) + "..." : reply));
            _web.CoreWebView2?.Reload();
        }

        private async Task ExportAsync()
        {
            if (_server == null || !_server.Running) return;
            using (var d = new SaveFileDialog { Title = "Save the last render", Filter = "WAV|*.wav|OGG Vorbis|*.ogg|FLAC|*.flac", DefaultExt = "wav", FileName = "render.wav" })
            {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                var reply = await BenchApi.PostAsync(_server.Url + "api/export", "{\"path\":" + BenchApi.JsonString(d.FileName) + "}");
                Log("export: " + reply);
                Status(reply.Contains("saved") ? "saved " + d.FileName : "export failed: " + reply);
            }
        }
    }
}
