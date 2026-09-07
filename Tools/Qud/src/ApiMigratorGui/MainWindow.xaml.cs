using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using ApiMigrator.Core;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;
using SaveFileDialog = Microsoft.Win32.SaveFileDialog;

namespace ApiMigratorGui;

public partial class MainWindow : Window
{
    private readonly string _toolsRoot;
    private readonly string _modsRoot;
    private readonly string _dumpPath;
    private readonly string _rulesPath;
    private readonly string _workshopPath;
    private readonly string _managedDir;

    private readonly ObservableCollection<string> _paths = new();
    private readonly ObservableCollection<string> _cp437Paths = new();
    private MigrationReport? _lastReport;
    private Cp437Converter.Report? _lastCp437Report;
    private DumpRefresher.RefreshPreview? _lastPreview;
    private readonly GuiSettings _settings;
    private List<FileResultRow> _fileRows = new();
    private List<OllamaSuggestion> _ollamaSuggestions = new();
    private CancellationTokenSource? _ollamaCts;
    private bool _ollamaProbed;
    private bool _suppressCloudUi;
    private string _ollamaSavedLocalUrl = OllamaClient.DefaultBaseUrl;

    public MainWindow()
    {
        InitializeComponent();

        // WindowStartupLocation="CenterScreen" can resolve to whatever screen the OS currently
        // considers "active" (e.g. a secondary monitor at negative coordinates), which made the
        // window open fully off-screen for some multi-monitor setups. Pin it to the primary
        // monitor's work area explicitly instead so it's always where the user can see it.
        var work = SystemParameters.WorkArea;
        Width = Math.Min(Width, work.Width - 40);
        Height = Math.Min(Height, work.Height - 40);
        Left = work.Left + (work.Width - Width) / 2;
        Top = work.Top + (work.Height - Height) / 2;

        _toolsRoot = CoqPaths.FindToolsRoot();
        _modsRoot = CoqPaths.ResolveModsRoot(_toolsRoot);
        _dumpPath = Path.Combine(_toolsRoot, "data", "obsolete_api_dump.json");
        _rulesPath = Path.Combine(_toolsRoot, "data", "curated_rewrite_rules.json");
        _workshopPath = SteamInstall.WorkshopContentDirOrFallback;
        _managedDir = SteamInstall.ManagedDirOrFallback;

        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var sync = DumpVersionControl.EnsureActiveProfile(dataDir, _managedDir);
            if (!string.IsNullOrEmpty(sync.Message))
                System.Diagnostics.Debug.WriteLine("[ApiMigrator] " + sync.Message);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine("[ApiMigrator] version sync: " + ex.Message);
        }

        LocalModsPathTextBox.Text = _modsRoot;
        WorkshopPathTextBox.Text = _workshopPath;
        // Pre-check Include Workshop when the default Steam path exists (mirrors PS1 -IncludeWorkshop).
        IncludeWorkshopCheckBox.IsChecked = Directory.Exists(_workshopPath);
        UpdateWorkshopPathEnabled();

        PathsListBox.ItemsSource = _paths;

        Cp437PathsListBox.ItemsSource = _cp437Paths;
        _cp437Paths.Add(_modsRoot);
        if (Directory.Exists(_workshopPath) && !_cp437Paths.Contains(_workshopPath))
            _cp437Paths.Add(_workshopPath);

        ManagedDirTextBox.Text = _managedDir;
        Cs0618ManagedTextBox.Text = _managedDir;
        ResearchDumpPathText.Text = "ApiMigrator dump (updated by step 2): " + _dumpPath;

        LoadMapTab();
        RefreshApiProfileBar();

        _settings = GuiSettings.Load(_toolsRoot);
        ApplyGuiSettings();
    }

    private void ApplyGuiSettings()
    {
        try
        {
            if (!string.IsNullOrWhiteSpace(_settings.LastLocalMods) &&
                !CoqPaths.IsMisrootedModsPath(_settings.LastLocalMods, _toolsRoot))
                LocalModsPathTextBox.Text = _settings.LastLocalMods;
            if (!string.IsNullOrWhiteSpace(_settings.LastWorkshop))
                WorkshopPathTextBox.Text = _settings.LastWorkshop;
            IncludeWorkshopCheckBox.IsChecked = _settings.IncludeWorkshop;
            if (!string.IsNullOrWhiteSpace(_settings.LastModFilter))
                ModFilterTextBox.Text = _settings.LastModFilter;
            if (!string.IsNullOrWhiteSpace(_settings.LastCs0618Mod))
                Cs0618ModFolderTextBox.Text = _settings.LastCs0618Mod;
            OllamaUrlBox.Text = string.IsNullOrWhiteSpace(_settings.OllamaUrl)
                ? "http://localhost:11434" : _settings.OllamaUrl;
            OllamaModelCombo.Text = string.IsNullOrWhiteSpace(_settings.OllamaModel)
                ? "llama3.1" : _settings.OllamaModel;
            OllamaMaxBox.Text = Math.Max(1, _settings.OllamaMaxHits).ToString();
            _suppressCloudUi = true;
            if (OllamaUseCloudCheck is not null)
                OllamaUseCloudCheck.IsChecked = _settings.OllamaUseCloud;
            if (OllamaRememberKeyCheck is not null)
                OllamaRememberKeyCheck.IsChecked = _settings.OllamaRememberApiKey;
            if (_settings.OllamaRememberApiKey &&
                !string.IsNullOrEmpty(_settings.OllamaApiKey) &&
                OllamaApiKeyBox is not null)
            {
                OllamaApiKeyBox.Password = _settings.OllamaApiKey;
            }
            _suppressCloudUi = false;
            ApplyOllamaCloudPanel();
            UpdateOllamaApiKeyHint();
            if (OllamaUseCloudCheck?.IsChecked == true)
            {
                if (string.IsNullOrWhiteSpace(OllamaModelCombo.Text) ||
                    OllamaModelCombo.Text.Equals(OllamaClient.DefaultModel, StringComparison.OrdinalIgnoreCase))
                {
                    OllamaModelCombo.Text = OllamaClient.DefaultCloudModel;
                }
                FillOllamaCloudModelCombo();
            }
            if (_settings.SelectedTab >= 0 && _settings.SelectedTab < MainTabs.Items.Count)
                MainTabs.SelectedIndex = _settings.SelectedTab;
            ApplySavedWindowBounds();
        }
        catch { /* settings are best-effort */ }
    }

    private void ApplySavedWindowBounds()
    {
        var work = SystemParameters.WorkArea;
        if (_settings.WindowWidth is >= 500 and <= 4000)
            Width = Math.Min(_settings.WindowWidth.Value, work.Width - 20);
        if (_settings.WindowHeight is >= 400 and <= 3000)
            Height = Math.Min(_settings.WindowHeight.Value, work.Height - 20);

        if (_settings.WindowLeft is { } left && _settings.WindowTop is { } top)
        {
            var intersects =
                left + Width > work.Left + 40 &&
                left < work.Right - 40 &&
                top + Height > work.Top + 40 &&
                top < work.Bottom - 40;
            if (intersects)
            {
                Left = left;
                Top = top;
                return;
            }
        }

        Left = work.Left + (work.Width - Width) / 2;
        Top = work.Top + (work.Height - Height) / 2;
    }

    private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
    {
        try
        {
            _settings.LastLocalMods = LocalModsPathTextBox.Text;
            _settings.LastWorkshop = WorkshopPathTextBox.Text;
            _settings.IncludeWorkshop = IncludeWorkshopCheckBox.IsChecked == true;
            _settings.LastModFilter = ModFilterTextBox.Text;
            _settings.LastCs0618Mod = Cs0618ModFolderTextBox.Text;
            _settings.OllamaUrl = OllamaUrlBox.Text;
            _settings.OllamaModel = OllamaModelCombo.Text;
            _settings.OllamaUseCloud = OllamaUseCloudCheck.IsChecked == true;
            _settings.OllamaRememberApiKey = OllamaRememberKeyCheck.IsChecked == true;
            _settings.OllamaApiKey = _settings.OllamaRememberApiKey
                ? OllamaApiKeyBox.Password
                : null;
            if (int.TryParse(OllamaMaxBox.Text, out var max))
                _settings.OllamaMaxHits = max;
            _settings.SelectedTab = MainTabs.SelectedIndex;
            if (WindowState == WindowState.Normal)
            {
                _settings.WindowWidth = Width;
                _settings.WindowHeight = Height;
                _settings.WindowLeft = Left;
                _settings.WindowTop = Top;
            }
            _settings.Save(_toolsRoot);
        }
        catch { /* ignore */ }
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        // Force the window to the foreground once at startup (helps in environments where a
        // freshly-launched process doesn't automatically get focus), then stop being Topmost
        // so it behaves like a normal window afterwards.
        Activate();
        Focus();
        Topmost = false;
        MainTabs.SelectionChanged += MainTabs_SelectionChanged;
        if (MainTabs.SelectedItem is TabItem startTab
            && string.Equals(startTab.Header as string, "Ollama leftovers", StringComparison.Ordinal)
            && !_ollamaProbed)
        {
            _ollamaProbed = true;
            OllamaProbe_Click(this, new RoutedEventArgs());
        }
    }

    private void MainTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (MainTabs.SelectedItem is not TabItem tab)
            return;
        if (string.Equals(tab.Header as string, "Ollama leftovers", StringComparison.Ordinal)
            && !_ollamaProbed)
        {
            _ollamaProbed = true;
            OllamaProbe_Click(sender, new RoutedEventArgs());
        }
    }

    sealed class ProfileChoice
    {
        public string Display { get; set; } = "";
        public string Alias { get; set; } = "live";
    }

    private void RefreshApiProfileBar()
    {
        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            ApiProfileStatusText.Text = DumpVersionControl.FormatProfileStatus(dataDir, _managedDir);

            var items = new List<ProfileChoice>
            {
                new() { Alias = "live", Display = "Follow Steam (live)" },
            };
            foreach (var p in DumpVersionControl.ListProfiles(dataDir, includeSnapshots: false))
            {
                if (!p.HasDump) continue;
                var beta = string.IsNullOrEmpty(p.SteamBetaKey) ? "" : $" — {p.SteamBetaKey}";
                items.Add(new ProfileChoice { Alias = p.FileVersion, Display = p.FileVersion + beta });
            }

            var ov = DumpVersionControl.ReadOverride(dataDir);
            ApiProfileCombo.ItemsSource = items;
            if (ov?.ForceFileVersion is { Length: > 0 } forced)
            {
                var match = items.FirstOrDefault(i =>
                    string.Equals(i.Alias, forced, StringComparison.OrdinalIgnoreCase));
                ApiProfileCombo.SelectedItem = match ?? items[0];
            }
            else
            {
                ApiProfileCombo.SelectedItem = items[0];
            }
        }
        catch (Exception ex)
        {
            ApiProfileStatusText.Text = "Could not read API profiles: " + ex.Message;
        }
    }

    private void SwitchApiProfile_Click(object sender, RoutedEventArgs e)
    {
        if (ApiProfileCombo.SelectedItem is not ProfileChoice choice)
        {
            MessageBox.Show("Pick a dump profile first.", "API dump profile",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var result = DumpVersionControl.SwitchActiveProfile(dataDir, choice.Alias, _managedDir);
            LoadMapTab();
            RefreshApiProfileBar();
            ApiProfileStatusText.Text = string.IsNullOrEmpty(result.Message)
                ? DumpVersionControl.FormatProfileStatus(dataDir, _managedDir)
                : result.Message;
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "API dump profile", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    // ============================================================
    // MIGRATE TAB
    // ============================================================

    private void BrowseLocalMods_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (TryPickFolder("Choose the local Mods folder", LocalModsPathTextBox.Text, out var folder))
                LocalModsPathTextBox.Text = folder;
        }
        catch (Exception ex)
        {
            MessageBox.Show("Browse failed:\n\n" + ex.Message, "Local Mods", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BrowseWorkshop_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (TryPickFolder("Choose the Steam Workshop content folder (333640)", WorkshopPathTextBox.Text, out var folder))
                WorkshopPathTextBox.Text = folder;
        }
        catch (Exception ex)
        {
            MessageBox.Show("Browse failed:\n\n" + ex.Message, "Workshop", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void IncludeWorkshopCheckBox_Changed(object sender, RoutedEventArgs e)
        => UpdateWorkshopPathEnabled();

    private void UpdateWorkshopPathEnabled()
    {
        // May run from Checked during InitializeComponent before sibling named fields exist.
        if (IncludeWorkshopCheckBox is null || WorkshopPathTextBox is null || BrowseWorkshopButton is null)
            return;

        var on = IncludeWorkshopCheckBox.IsChecked == true;
        WorkshopPathTextBox.IsEnabled = on;
        BrowseWorkshopButton.IsEnabled = on;
        if (WorkshopPathGrid is not null)
            WorkshopPathGrid.Opacity = on ? 1.0 : 0.5;
    }

    /// <summary>
    /// Builds scan roots the same way as PS1 <c>-IncludeWorkshop</c> / CLI <c>--include-workshop</c>:
    /// local Mods always, Workshop when the checkbox is on, plus any additional folders.
    /// </summary>
    private List<string> BuildMigrateScanRoots()
    {
        var roots = new List<string>();
        void AddUnique(string? path)
        {
            if (string.IsNullOrWhiteSpace(path)) return;
            try
            {
                var full = Path.GetFullPath(path.Trim());
                if (roots.Any(r => string.Equals(r, full, StringComparison.OrdinalIgnoreCase))) return;
                roots.Add(full);
            }
            catch
            {
                // Skip invalid path text — browse/run will surface a clear dialog if nothing remains.
            }
        }

        AddUnique(LocalModsPathTextBox.Text);
        if (IncludeWorkshopCheckBox.IsChecked == true)
            AddUnique(WorkshopPathTextBox.Text);
        foreach (var extra in _paths)
            AddUnique(extra);
        return roots;
    }

    private void AddFolderButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryPickFolder("Choose an additional folder to scan", null, out var folder))
            return;
        if (!_paths.Any(p => string.Equals(p, folder, StringComparison.OrdinalIgnoreCase)))
            _paths.Add(folder);
    }

    private void RemovePathButton_Click(object sender, RoutedEventArgs e)
    {
        if (PathsListBox.SelectedItem is string s) _paths.Remove(s);
    }

    private sealed class FileResultRow
    {
        public string FilePath { get; set; } = "";
        public int AutoFixCount { get; set; }
        public int RemainingCount { get; set; }
        public FileScanResult Result { get; set; } = null!;
    }

    private sealed class DetailRow
    {
        public string Kind { get; set; } = "";
        public string Line { get; set; } = "";
        public string NameOrMember { get; set; } = "";
        public string Detail { get; set; } = "";
        public string Code { get; set; } = "";
    }

    private async void RunMigrationButton_Click(object sender, RoutedEventArgs e)
    {
        var scanRoots = BuildMigrateScanRoots();
        if (!PrepareScanRoots(ref scanRoots))
            return;

        var options = new MigrationOptions
        {
            Paths = scanRoots,
            ModFilter = string.IsNullOrWhiteSpace(ModFilterTextBox.Text) ? null : ModFilterTextBox.Text.Trim(),
            Apply = ApplyCheckBox.IsChecked == true,
            Backup = BackupCheckBox.IsChecked == true,
            DumpPath = _dumpPath,
            RulesPath = _rulesPath,
        };

        await RunMigrationCoreAsync(
            options,
            statusPreface: "Starting...\n" + string.Join("\n", scanRoots.Select(p => "  " + p)),
            autoSaveReportPath: null);
    }

    /// <summary>
    /// One-click safe autofix pass over Local Mods + Workshop (when Include Workshop is on).
    /// Equivalent to PS1 <c>-IncludeWorkshop -Apply -NoBackup</c> — curated RuleEngine autofixes only.
    /// </summary>
    private async void ApplyAllSafeAutofixesButton_Click(object sender, RoutedEventArgs e)
    {
        // Force Local + Workshop roots (ignore additional folders / mod filter for this bulk path).
        var roots = new List<string>();
        void AddUnique(string? path)
        {
            if (string.IsNullOrWhiteSpace(path)) return;
            try
            {
                var full = Path.GetFullPath(path.Trim());
                if (!roots.Any(r => string.Equals(r, full, StringComparison.OrdinalIgnoreCase)))
                    roots.Add(full);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Invalid path:\n" + path + "\n\n" + ex.Message,
                    "Apply safe autofixes", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }

        AddUnique(LocalModsPathTextBox.Text);
        if (IncludeWorkshopCheckBox.IsChecked == true)
            AddUnique(WorkshopPathTextBox.Text);

        if (!PrepareScanRoots(ref roots))
            return;

        var confirm =
            "This will APPLY curated safe autofixes to ALL mods under:\n\n" +
            string.Join("\n", roots.Select(r => "  • " + r)) +
            "\n\n" +
            "• Writes files in place (same as PS1 -IncludeWorkshop -Apply -NoBackup)\n" +
            "• No .bak backups\n" +
            "• Safe autofixes only — leftover manual hits are reported, not blocked\n" +
            "• Can touch many Workshop + local mods\n\n" +
            "Continue?";
        if (MessageBox.Show(confirm, "Apply safe autofixes (Local + Workshop)",
                MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;

        var reportPath = Path.Combine(_toolsRoot, "reports", "all-mods-gui-apply.md");
        var options = new MigrationOptions
        {
            Paths = roots,
            ModFilter = null,
            Apply = true,
            Backup = false,
            DumpPath = _dumpPath,
            RulesPath = _rulesPath,
        };

        await RunMigrationCoreAsync(
            options,
            statusPreface: "Applying safe autofixes (Local + Workshop)...\n" +
                           string.Join("\n", roots.Select(p => "  " + p)),
            autoSaveReportPath: reportPath);
    }

    private bool PrepareScanRoots(ref List<string> scanRoots)
    {
        if (scanRoots.Count == 0)
        {
            MessageBox.Show("Set a Local Mods path (and/or Workshop / additional folders).",
                "No paths", MessageBoxButton.OK, MessageBoxImage.Warning);
            return false;
        }

        var missing = scanRoots.Where(p => !Directory.Exists(p)).ToList();
        if (missing.Count == 0)
            return true;

        if (missing.Count == scanRoots.Count)
        {
            MessageBox.Show("None of the scan roots exist:\n\n" + string.Join("\n", missing),
                "No paths", MessageBoxButton.OK, MessageBoxImage.Warning);
            return false;
        }

        var msg = "These scan roots do not exist:\n\n" + string.Join("\n", missing) +
                  "\n\nContinue anyway with the remaining roots?";
        if (MessageBox.Show(msg, "Missing folders", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return false;

        scanRoots = scanRoots.Where(Directory.Exists).ToList();
        return scanRoots.Count > 0;
    }

    private async System.Threading.Tasks.Task RunMigrationCoreAsync(
        MigrationOptions options,
        string statusPreface,
        string? autoSaveReportPath)
    {
        RunMigrationButton.IsEnabled = false;
        ApplyAllSafeAutofixesButton.IsEnabled = false;
        SaveReportButton.IsEnabled = false;
        MigrateProgressBar.Value = 0;
        MigrateStatusText.Text = statusPreface;
        FileResultsGrid.ItemsSource = null;
        DetailsGrid.ItemsSource = null;

        try
        {
            var report = await System.Threading.Tasks.Task.Run(() => MigrationRunner.Run(
                options,
                onLog: msg => Dispatcher.Invoke(() => MigrateStatusText.Text = msg),
                onProgress: (done, total) => Dispatcher.Invoke(() =>
                {
                    if (total > 0) MigrateProgressBar.Value = 100.0 * done / total;
                })));

            _lastReport = report;

            _fileRows = report.FileResults.Select(f => new FileResultRow
            {
                FilePath = f.FilePath ?? "",
                AutoFixCount = f.AppliedFixes.Sum(a => a.Count),
                RemainingCount = f.RemainingHits.Count,
                Result = f,
            }).ToList();
            ApplyMigrateFilter();

            var mode = options.Apply ? "APPLY (files written)" : "DRY-RUN (no files written)";
            var workshopNote = options.Paths.Any(p =>
                p.Contains("workshop", StringComparison.OrdinalIgnoreCase))
                ? " (includes Workshop)"
                : "";
            var ollamaN = OllamaLeftoverSuggester.CollectHits(report, 10_000).Count;
            MigrateSummaryText.Text =
                $"Mode: {mode}\n" +
                $"Scan roots: {options.Paths.Count}{workshopNote}\n" +
                $"Files scanned: {report.FilesScanned}\n" +
                $"Files needing attention: {report.FileResults.Count}\n" +
                $"Auto-fix rewrites: {report.TotalAutoFixes}\n" +
                $"Remaining manual hits: {report.TotalRemainingHits}" +
                (ollamaN > 0 ? $"\nOllama-suggestable leftovers: {ollamaN}" : "") +
                (options.Backup ? "" : "\nBackups: off");

            OpenOllamaTabButton.IsEnabled = ollamaN > 0;

            if (!string.IsNullOrWhiteSpace(autoSaveReportPath))
            {
                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(autoSaveReportPath)!);
                    ReportWriter.WriteMarkdown(report, autoSaveReportPath);
                    MigrateStatusText.Text = "Done. Report: " + autoSaveReportPath;
                    MessageBox.Show(
                        $"Safe autofixes finished.\n\n" +
                        $"Auto-fix rewrites: {report.TotalAutoFixes}\n" +
                        $"Remaining manual hits: {report.TotalRemainingHits}\n" +
                        $"Files needing attention: {report.FileResults.Count}\n\n" +
                        $"Report saved to:\n{autoSaveReportPath}",
                        "Apply safe autofixes",
                        MessageBoxButton.OK,
                        MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MigrateStatusText.Text = "Done, but report save failed: " + ex.Message;
                    MessageBox.Show("Migration finished but report save failed:\n\n" + ex,
                        "Report save failed", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
            else
            {
                MigrateStatusText.Text = "Done.";
            }

            SaveReportButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            MigrateStatusText.Text = "Error: " + ex.Message;
            MessageBox.Show(ex.ToString(), "Migration failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            RunMigrationButton.IsEnabled = true;
            ApplyAllSafeAutofixesButton.IsEnabled = true;
            MigrateProgressBar.Value = 100;
        }
    }

    private void OpenOllamaTab_Click(object sender, RoutedEventArgs e)
    {
        var ollamaTab = MainTabs.Items.OfType<TabItem>()
            .FirstOrDefault(t => string.Equals(t.Header as string, "Ollama leftovers", StringComparison.Ordinal));
        if (ollamaTab is not null)
            MainTabs.SelectedItem = ollamaTab;
    }

    private void FileResultsGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        try
        {
            if (FileResultsGrid.SelectedItem is not FileResultRow row || row.Result is null)
            {
                DetailsGrid.ItemsSource = null;
                return;
            }

            var rows = new List<DetailRow>();
            foreach (var fix in row.Result.AppliedFixes)
            {
                rows.Add(new DetailRow
                {
                    Kind = "Auto-fix",
                    Line = "",
                    NameOrMember = fix.RuleName ?? "",
                    Detail = $"×{fix.Count}",
                    Code = "",
                });
            }
            foreach (var hit in row.Result.RemainingHits)
            {
                var detail = hit.Message ?? "";
                if (!string.IsNullOrWhiteSpace(hit.Advice))
                {
                    var adviceOneLine = hit.Advice.Replace("\r\n", " ").Replace('\n', ' ');
                    if (adviceOneLine.Length > 240) adviceOneLine = adviceOneLine[..237] + "...";
                    detail = string.IsNullOrWhiteSpace(detail) ? adviceOneLine : detail + " | " + adviceOneLine;
                }
                rows.Add(new DetailRow
                {
                    Kind = "Needs review",
                    Line = hit.Line.ToString(),
                    NameOrMember = hit.Member ?? "",
                    Detail = detail,
                    Code = hit.Text ?? "",
                });
            }
            DetailsGrid.ItemsSource = rows;
        }
        catch (Exception ex)
        {
            DetailsGrid.ItemsSource = null;
            MessageBox.Show("Could not show file details:\n\n" + ex.Message,
                "Migrate", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void ApplyMigrateFilter()
    {
        var q = MigrateFilterBox?.Text?.Trim() ?? "";
        IEnumerable<FileResultRow> rows = _fileRows;
        if (q.Length > 0)
        {
            rows = _fileRows.Where(r =>
                (r.FilePath ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                r.Result.RemainingHits.Any(h =>
                    (h.Member ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                    (h.Text ?? "").Contains(q, StringComparison.OrdinalIgnoreCase)));
        }
        FileResultsGrid.ItemsSource = rows.ToList();
    }

    private void MigrateFilterBox_TextChanged(object sender, TextChangedEventArgs e) => ApplyMigrateFilter();

    private void FileResultsGrid_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        => OpenSelectedFile_Click(sender, e);

    private void OpenSelectedFile_Click(object sender, RoutedEventArgs e)
    {
        var path = (FileResultsGrid.SelectedItem as FileResultRow)?.FilePath;
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return;
        try
        {
            Process.Start(new ProcessStartInfo { FileName = path, UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Open file", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void OpenSelectedFolder_Click(object sender, RoutedEventArgs e)
    {
        var path = (FileResultsGrid.SelectedItem as FileResultRow)?.FilePath;
        if (string.IsNullOrWhiteSpace(path)) return;
        var dir = File.Exists(path) ? Path.GetDirectoryName(path) : path;
        if (string.IsNullOrWhiteSpace(dir) || !Directory.Exists(dir)) return;
        try
        {
            Process.Start(new ProcessStartInfo { FileName = dir, UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Open folder", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void CopySelectedPath_Click(object sender, RoutedEventArgs e)
    {
        var path = (FileResultsGrid.SelectedItem as FileResultRow)?.FilePath;
        if (string.IsNullOrWhiteSpace(path)) return;
        try { Clipboard.SetText(path); }
        catch { /* ignore */ }
    }

    private void OllamaUseCloud_Changed(object sender, RoutedEventArgs e)
    {
        if (_suppressCloudUi) return;
        if (OllamaUseCloudCheck is null || OllamaUrlBox is null) return;

        var on = OllamaUseCloudCheck.IsChecked == true;
        if (on)
        {
            if (OllamaClient.IsLocalHost(OllamaUrlBox.Text))
            {
                _ollamaSavedLocalUrl = OllamaUrlBox.Text.Trim();
                OllamaUrlBox.Text = OllamaClient.CloudBaseUrl;
            }
            if (OllamaModelCombo is not null &&
                (string.IsNullOrWhiteSpace(OllamaModelCombo.Text) ||
                 OllamaModelCombo.Text.Equals(OllamaClient.DefaultModel, StringComparison.OrdinalIgnoreCase)))
            {
                OllamaModelCombo.Text = OllamaClient.DefaultCloudModel;
            }
            FillOllamaCloudModelCombo();
        }
        else if (OllamaClient.IsCloudHost(OllamaUrlBox.Text))
        {
            OllamaUrlBox.Text = string.IsNullOrWhiteSpace(_ollamaSavedLocalUrl)
                ? OllamaClient.DefaultBaseUrl
                : _ollamaSavedLocalUrl;
        }

        ApplyOllamaCloudPanel();
        UpdateOllamaApiKeyHint();
    }

    private void ApplyOllamaCloudPanel()
    {
        if (OllamaCloudPanel is null || OllamaUseCloudCheck is null) return;
        OllamaCloudPanel.Visibility = OllamaUseCloudCheck.IsChecked == true
            ? Visibility.Visible
            : Visibility.Collapsed;
    }

    private void UpdateOllamaApiKeyHint()
    {
        if (OllamaApiKeyHint is not null)
        {
            OllamaApiKeyHint.Text = OllamaClient.EnvApiKeyIsSet()
                ? "OLLAMA_API_KEY is set in the environment (the box overrides it if filled)."
                : "Create a key at ollama.com/settings/keys, or set OLLAMA_API_KEY.";
        }
        if (OllamaFreeModelsHint is not null)
        {
            OllamaFreeModelsHint.Text =
                "Free-tier leftover pick: gpt-oss:20b (fast). 120b = quality. Gemma-4 = multimodal. Nemotron Super/Ultra = 1M / agentic.";
        }
        UpdateOllamaModelCapability();
    }

    private void OllamaModelCombo_Changed(object sender, RoutedEventArgs e) => UpdateOllamaModelCapability();

    private void OllamaModelCombo_SelectionChanged(object sender, SelectionChangedEventArgs e) => UpdateOllamaModelCapability();

    private void UpdateOllamaModelCapability()
    {
        if (OllamaModelCapabilityText is null) return;
        var useCloud = OllamaUseCloudCheck?.IsChecked == true
            || OllamaClient.IsCloudHost(OllamaUrlBox?.Text);
        if (!useCloud)
        {
            OllamaModelCapabilityText.Text = "";
            return;
        }
        var id = OllamaModelCombo?.Text?.Trim() ?? "";
        var dash = id.IndexOf(" — ", StringComparison.Ordinal);
        if (dash > 0) id = id[..dash];
        var desc = OllamaClient.DescribeCloudModel(id);
        OllamaModelCapabilityText.Text = string.IsNullOrEmpty(desc)
            ? OllamaClient.FormatFreeCloudCatalog()
            : desc;
    }

    private void FillOllamaCloudModelCombo(IEnumerable<string>? extra = null)
    {
        if (OllamaModelCombo is null) return;
        var current = OllamaModelCombo.Text;
        OllamaModelCombo.ItemsSource = OllamaClient.MergeCloudCatalog(extra);
        if (!string.IsNullOrWhiteSpace(current))
            OllamaModelCombo.Text = current;
        else
            OllamaModelCombo.Text = OllamaClient.DefaultCloudModel;
        UpdateOllamaModelCapability();
    }

    private OllamaOptions BuildOllamaOptions(int maxHits)
    {
        var useCloud = OllamaUseCloudCheck.IsChecked == true
            || OllamaClient.IsCloudHost(OllamaUrlBox.Text);
        return new OllamaOptions
        {
            UseCloud = useCloud,
            BaseUrl = OllamaUrlBox.Text.Trim(),
            ApiKey = OllamaApiKeyBox.Password,
            Model = string.IsNullOrWhiteSpace(OllamaModelCombo.Text)
                ? (useCloud ? OllamaClient.DefaultCloudModel : OllamaClient.DefaultModel)
                : OllamaModelCombo.Text.Trim(),
            MaxHits = maxHits,
        };
    }

    private async void OllamaProbe_Click(object sender, RoutedEventArgs e)
    {
        OllamaStatusText.Text = "Probing...";
        try
        {
            var options = BuildOllamaOptions(12);
            var status = await Task.Run(() =>
                OllamaClient.ProbeAsync(options).GetAwaiter().GetResult());
            OllamaStatusText.Text = status.Summary;
            if (!string.IsNullOrWhiteSpace(status.BaseUrl) &&
                !string.Equals(OllamaUrlBox.Text.Trim().TrimEnd('/'), status.BaseUrl, StringComparison.OrdinalIgnoreCase))
            {
                OllamaUrlBox.Text = status.BaseUrl;
            }
            if (status.Available || status.Cloud)
            {
                var current = OllamaModelCombo.Text;
                if (status.Cloud)
                    FillOllamaCloudModelCombo(status.Models);
                else
                {
                    OllamaModelCombo.ItemsSource = status.Models;
                    if (!string.IsNullOrWhiteSpace(current))
                        OllamaModelCombo.Text = current;
                }
                var resolved = OllamaClient.ResolveModel(status, current);
                OllamaModelCombo.Text = resolved;
                if (!string.Equals(resolved, current, StringComparison.OrdinalIgnoreCase)
                    && !string.IsNullOrWhiteSpace(current) && status.Available)
                {
                    OllamaStatusText.Text = status.Summary + $" — using '{resolved}'";
                }
            }
        }
        catch (Exception ex)
        {
            OllamaStatusText.Text = "Probe failed: " + ex.Message;
        }
    }

    private async void OllamaSuggest_Click(object sender, RoutedEventArgs e)
    {
        if (_lastReport is null)
        {
            MessageBox.Show("Run Migrate first (dry-run is fine). Leftover hits come from that report.",
                "Ollama", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        if (!int.TryParse(OllamaMaxBox.Text, out var max) || max < 1)
            max = 12;

        var options = BuildOllamaOptions(max);

        _ollamaCts?.Cancel();
        _ollamaCts?.Dispose();
        _ollamaCts = new CancellationTokenSource();
        var ct = _ollamaCts.Token;

        OllamaSuggestButton.IsEnabled = false;
        OllamaCancelButton.IsEnabled = true;
        OllamaProgressBar.IsIndeterminate = false;
        OllamaProgressBar.Value = 0;
        OllamaStatusText.Text = "Asking Ollama...";
        OllamaGrid.ItemsSource = null;
        try
        {
            var suggestions = await Task.Run(() =>
                OllamaLeftoverSuggester.SuggestAsync(
                    _lastReport,
                    options,
                    msg => Dispatcher.Invoke(() => OllamaStatusText.Text = msg),
                    (done, total) => Dispatcher.Invoke(() =>
                    {
                        if (total > 0) OllamaProgressBar.Value = 100.0 * done / total;
                    }),
                    ct)
                    .GetAwaiter().GetResult(), ct);
            _ollamaSuggestions = suggestions;
            ApplyOllamaFilter();
            var n = suggestions.Count(s => !s.Skip);
            OllamaSummaryText.Text = $"{suggestions.Count} suggestion(s), {n} with a replacement, {suggestions.Count - n} skipped.";
            OllamaStatusText.Text = "Done.";
        }
        catch (OperationCanceledException)
        {
            OllamaStatusText.Text = "Cancelled.";
        }
        catch (Exception ex)
        {
            OllamaStatusText.Text = "Error: " + ex.Message;
            MessageBox.Show(ex.Message, "Ollama", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            OllamaSuggestButton.IsEnabled = true;
            OllamaCancelButton.IsEnabled = false;
            if (OllamaProgressBar.Value < 100 && OllamaStatusText.Text == "Done.")
                OllamaProgressBar.Value = 100;
        }
    }

    private void OllamaCancel_Click(object sender, RoutedEventArgs e)
    {
        try { _ollamaCts?.Cancel(); }
        catch { /* ignore */ }
        OllamaStatusText.Text = "Cancelling...";
    }

    private void ApplyOllamaFilter()
    {
        var q = OllamaFilterBox?.Text?.Trim() ?? "";
        IEnumerable<OllamaSuggestion> rows = _ollamaSuggestions;
        if (q.Length > 0)
        {
            rows = _ollamaSuggestions.Where(s =>
                (s.FilePath ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (s.FileName ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (s.Member ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (s.Original ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (s.Replacement ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (s.Explanation ?? "").Contains(q, StringComparison.OrdinalIgnoreCase));
        }
        OllamaGrid.ItemsSource = rows.ToList();
    }

    private void OllamaFilterBox_TextChanged(object sender, TextChangedEventArgs e) => ApplyOllamaFilter();

    private void OllamaGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (OllamaGrid.SelectedItem is OllamaSuggestion s)
        {
            OllamaOriginalBox.Text = s.Original ?? "";
            OllamaReplacementBox.Text = s.Skip
                ? (string.IsNullOrWhiteSpace(s.Explanation) ? "(skipped)" : s.Explanation)
                : (s.Replacement ?? "");
        }
        else
        {
            OllamaOriginalBox.Text = "";
            OllamaReplacementBox.Text = "";
        }
    }

    private void OllamaGrid_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        => OllamaOpenFile_Click(sender, e);

    private void OllamaOpenFile_Click(object sender, RoutedEventArgs e)
    {
        var path = (OllamaGrid.SelectedItem as OllamaSuggestion)?.FilePath;
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return;
        try
        {
            Process.Start(new ProcessStartInfo { FileName = path, UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Open file", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void OllamaCopyOriginal_Click(object sender, RoutedEventArgs e)
    {
        if (OllamaGrid.SelectedItem is OllamaSuggestion s && !string.IsNullOrEmpty(s.Original))
        {
            try { Clipboard.SetText(s.Original); } catch { /* ignore */ }
        }
    }

    private void OllamaCopyReplacement_Click(object sender, RoutedEventArgs e)
    {
        if (OllamaGrid.SelectedItem is OllamaSuggestion s && !string.IsNullOrEmpty(s.Replacement))
        {
            try { Clipboard.SetText(s.Replacement); } catch { /* ignore */ }
        }
    }

    private void OllamaApplySelected_Click(object sender, RoutedEventArgs e)
    {
        if (OllamaGrid.SelectedItem is not OllamaSuggestion s)
        {
            MessageBox.Show("Select a suggestion row first.", "Ollama",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        if (OllamaLeftoverSuggester.TryApply(s, out var err))
        {
            s.Skip = true;
            s.Explanation = "Applied.";
            ApplyOllamaFilter();
            MessageBox.Show("Replaced the original line in:\n" + s.FilePath, "Ollama",
                MessageBoxButton.OK, MessageBoxImage.Information);
        }
        else
        {
            MessageBox.Show(err, "Could not apply", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void OllamaApplyHighConfidence_Click(object sender, RoutedEventArgs e)
    {
        var ready = _ollamaSuggestions.Count(s =>
            !s.Skip && (
                string.Equals(s.Confidence, "high", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(s.Confidence, "medium", StringComparison.OrdinalIgnoreCase)));
        if (ready == 0)
        {
            MessageBox.Show("No high/medium C# rewrites to apply.", "Ollama",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        if (MessageBox.Show(
                $"Apply {ready} high/medium unique-line C# replacement(s)?\n\nSkipped, low, and advisory rows are left alone.",
                "Apply rewrites",
                MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes)
            return;

        var (applied, failed) = OllamaLeftoverSuggester.TryApplyMany(
            _ollamaSuggestions, highConfidenceOnly: true, out var errors, includeMedium: true);
        ApplyOllamaFilter();
        var extra = errors.Count == 0 ? "" : "\n\n" + string.Join("\n", errors.Take(8));
        MessageBox.Show($"Applied {applied}. Failed {failed}." + extra, "Ollama",
            MessageBoxButton.OK, failed > 0 ? MessageBoxImage.Warning : MessageBoxImage.Information);
    }

    private void OllamaSaveReport_Click(object sender, RoutedEventArgs e)
    {
        if (_ollamaSuggestions.Count == 0)
        {
            MessageBox.Show("No suggestions yet.", "Ollama", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        var dlg = new SaveFileDialog
        {
            Filter = "Markdown (*.md)|*.md|All files (*.*)|*.*",
            FileName = $"ollama-suggest_{DateTime.Now:yyyyMMdd_HHmmss}.md",
            InitialDirectory = Path.Combine(_toolsRoot, "reports"),
        };
        if (dlg.ShowDialog() == true)
        {
            File.WriteAllText(dlg.FileName, OllamaLeftoverSuggester.ToMarkdown(_ollamaSuggestions));
            MessageBox.Show("Saved:\n" + dlg.FileName, "Ollama", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void SaveReportButton_Click(object sender, RoutedEventArgs e)
    {
        if (_lastReport is null) return;
        var dlg = new SaveFileDialog
        {
            Filter = "Markdown (*.md)|*.md|All files (*.*)|*.*",
            FileName = $"ApiMigration_{DateTime.Now:yyyyMMdd_HHmmss}.md",
            InitialDirectory = Path.Combine(_toolsRoot, "reports"),
        };
        if (dlg.ShowDialog() == true)
        {
            ReportWriter.WriteMarkdown(_lastReport, dlg.FileName);
            MessageBox.Show($"Report saved to:\n{dlg.FileName}", "Saved", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    // ============================================================
    // OBSOLETE MAP TAB
    // ============================================================

    private sealed class MapRow
    {
        public string Type { get; set; } = "";
        public string Member { get; set; } = "";
        public string Kind { get; set; } = "";
        public string AutoFixable { get; set; } = "";
        public string ObsoleteMessage { get; set; } = "";
        public string Notes { get; set; } = "";
    }

    private List<MapRow> _allMapRows = new();

    private void LoadMapTab()
    {
        try
        {
            var dump = DumpStore.LoadDump(_dumpPath);
            _allMapRows = dump.Entries.Select(e => new MapRow
            {
                Type = e.Type,
                Member = e.Member,
                Kind = e.Kind,
                AutoFixable = e.AutoFixable ? "Yes" : (e.NeedsManual ? "No (manual)" : "No"),
                ObsoleteMessage = e.ObsoleteMessage,
                Notes = e.Notes ?? "",
            }).ToList();

            MapInfoText.Text = $"Dump: {_dumpPath}\n{dump.Entries.Count} entries" +
                                (dump.Meta?.CapturedDate is { } d ? $" (captured {d})" : "");
            ApplyMapFilter();
        }
        catch (Exception ex)
        {
            MapInfoText.Text = "Could not load dump: " + ex.Message;
        }
    }

    private void ApplyMapFilter()
    {
        var q = MapSearchBox.Text?.Trim() ?? "";
        IEnumerable<MapRow> rows = _allMapRows;
        if (q.Length > 0)
        {
            rows = rows.Where(r =>
                r.Type.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                r.Member.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                r.ObsoleteMessage.Contains(q, StringComparison.OrdinalIgnoreCase));
        }
        MapGrid.ItemsSource = rows.ToList();
    }

    private void MapSearchBox_TextChanged(object sender, TextChangedEventArgs e) => ApplyMapFilter();

    private void ReloadMapButton_Click(object sender, RoutedEventArgs e) => LoadMapTab();

    private void CompileChartsButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var chartsDir = RuleChartCompiler.DefaultChartsDir(dataDir);
            if (!Directory.Exists(chartsDir))
            {
                MessageBox.Show(
                    $"No charts folder at:\n{chartsDir}\n\nUse “Export charts from JSON” first, or run:\nApiMigrator.Cli export-charts --force",
                    "Compile rule charts", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var result = RuleChartCompiler.Compile(new RuleChartCompiler.CompileOptions
            {
                ChartsDir = chartsDir,
                OutPath = _rulesPath,
                DataDir = dataDir,
                ManagedDir = _managedDir,
                CheckOnly = false,
                UpdateVersionProfile = true,
            });

            if (result.Errors.Count > 0)
            {
                MessageBox.Show(string.Join("\n", result.Errors), "Compile failed",
                    MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            var msg =
                $"Compiled {result.RuleCount} rules (+ {result.NoteCount} notes, {result.PostEnsureCount} postEnsureUsings)\n\n" +
                $"Wrote:\n{_rulesPath}\n" +
                (result.ProfileDir is not null ? $"\nProfile:\n{result.ProfileDir}" : "") +
                (result.Warnings.Count > 0 ? "\n\nWarnings:\n" + string.Join("\n", result.Warnings) : "");
            MessageBox.Show(msg, "Rule charts compiled", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "Compile failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void ExportChartsButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var chartsDir = RuleChartCompiler.DefaultChartsDir(dataDir);
            if (Directory.Exists(chartsDir) && Directory.EnumerateFileSystemEntries(chartsDir).Any())
            {
                var confirm = MessageBox.Show(
                    $"Overwrite existing charts in:\n{chartsDir}\n\nContinue?",
                    "Export charts", MessageBoxButton.YesNo, MessageBoxImage.Warning);
                if (confirm != MessageBoxResult.Yes) return;
            }

            var result = RuleChartCompiler.Export(new RuleChartCompiler.ExportOptions
            {
                RulesPath = _rulesPath,
                ChartsDir = chartsDir,
                Overwrite = true,
            });

            if (!result.Ok)
            {
                MessageBox.Show(string.Join("\n", result.Errors), "Export failed",
                    MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            MessageBox.Show(
                $"Exported {result.RuleCount} rules + {result.NoteCount} notes →\n{chartsDir}\n\n" +
                "Edit the XML packs, then click “Compile rule charts”.",
                "Charts exported", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "Export failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void ExportPromotionsButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var promotionsDir = PromotionChartCompiler.DefaultPromotionsDir(dataDir);
            var result = PromotionChartCompiler.Export(new PromotionChartCompiler.ExportOptions
            {
                DumpPath = _dumpPath,
                PromotionsDir = promotionsDir,
                MergeExisting = true,
                NeedsManualOnly = true,
            });
            if (!result.Ok)
            {
                MessageBox.Show(string.Join("\n", result.Errors), "Export promotions failed",
                    MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }
            MessageBox.Show(
                $"Exported {result.EntryCount} needsManual entries →\n{promotionsDir}\n\n" +
                (result.MergedFromExisting > 0
                    ? $"Merged {result.MergedFromExisting} prior Status/ProposedRule decisions.\n\n"
                    : "") +
                "Set Status=Promote, fill ProposedRule, then Apply promotions.",
                "Promotions exported", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "Export promotions failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void ApplyPromotionsButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dataDir = Path.Combine(_toolsRoot, "data");
            var promotionsDir = PromotionChartCompiler.DefaultPromotionsDir(dataDir);
            if (!Directory.Exists(promotionsDir))
            {
                MessageBox.Show("No promotions folder yet. Click “Export promotions” first.",
                    "Apply promotions", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var confirm = MessageBox.Show(
                "Apply all Status=Promote entries?\n\n" +
                "Writes charts/Promoted.xml, updates dump autoFixable flags, and compile-rules.",
                "Apply promotions", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (confirm != MessageBoxResult.Yes) return;

            var result = PromotionChartCompiler.Apply(new PromotionChartCompiler.ApplyOptions
            {
                PromotionsDir = promotionsDir,
                DumpPath = _dumpPath,
                ChartsDir = RuleChartCompiler.DefaultChartsDir(dataDir),
                DataDir = dataDir,
                ManagedDir = _managedDir,
                CompileRulesAfter = true,
                UpdateVersionProfile = true,
            });

            if (!result.Ok)
            {
                MessageBox.Show(string.Join("\n", result.Errors), "Apply promotions failed",
                    MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            MessageBox.Show(
                $"Promote={result.Promoted}  Skip={result.Skipped}  AdviceOnly={result.AdviceOnly}  Candidate={result.Candidates}\n" +
                (result.PromotedChartPath is not null ? $"\n{result.PromotedChartPath}\n" : "") +
                (result.CompileResult is { } cr ? $"\nCompiled {cr.RuleCount} rules." : "") +
                (result.Warnings.Count > 0 ? "\n\nWarnings:\n" + string.Join("\n", result.Warnings) : ""),
                "Promotions applied", MessageBoxButton.OK, MessageBoxImage.Information);
            LoadMapTab();
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "Apply promotions failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ============================================================
    // DLL RESEARCH TAB
    // ============================================================

    private sealed class DiffRow
    {
        public string Change { get; set; } = "";
        public string Type { get; set; } = "";
        public string Member { get; set; } = "";
        public string Message { get; set; } = "";
    }

    private void BrowseManagedButton_Click(object sender, RoutedEventArgs e)
    {
        if (TryPickFolder("Choose the Managed folder", ManagedDirTextBox.Text, out var folder))
            ManagedDirTextBox.Text = folder;
    }

    private async void ScanNowButton_Click(object sender, RoutedEventArgs e)
    {
        var managedDir = ManagedDirTextBox.Text.Trim();
        var dlls = DllNamesTextBox.Text.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries).ToList();
        if (dlls.Count == 0) dlls.Add("Assembly-CSharp.dll");

        ScanNowButton.IsEnabled = false;
        SaveMergedButton.IsEnabled = false;
        ResearchProgressBar.IsIndeterminate = true;
        ResearchStatusText.Text = "Reflecting Managed DLLs (read-only)... this can take a few seconds.";
        ResearchSummaryText.Text = "";
        DiffGrid.ItemsSource = null;

        try
        {
            var preview = await System.Threading.Tasks.Task.Run(() => DumpRefresher.Scan(managedDir, dlls, _dumpPath));
            _lastPreview = preview;

            var rows = new List<DiffRow>();
            foreach (var w in preview.Scan.Warnings)
                rows.Add(new DiffRow { Change = "warning", Type = "", Member = "", Message = w });

            if (preview.Diff is { } diff)
            {
                foreach (var m in diff.Added) rows.Add(new DiffRow { Change = "added", Type = m.Type, Member = m.Member, Message = m.ObsoleteMessage });
                foreach (var m in diff.MessageChanged) rows.Add(new DiffRow { Change = "changed", Type = m.Old.Type, Member = m.Old.Member, Message = $"'{m.Old.ObsoleteMessage}' -> '{m.New.ObsoleteMessage}'" });
                foreach (var m in diff.Removed) rows.Add(new DiffRow { Change = "removed", Type = m.Type, Member = m.Member, Message = m.ObsoleteMessage });

                ResearchSummaryText.Text = $"Types scanned: {preview.Scan.TypesScanned}   Obsolete members found: {preview.Scan.Members.Count}   " +
                                            $"Unchanged: {diff.UnchangedCount}   Added: {diff.Added.Count}   Removed: {diff.Removed.Count}   Changed: {diff.MessageChanged.Count}";
            }
            else
            {
                ResearchSummaryText.Text = $"Types scanned: {preview.Scan.TypesScanned}   Obsolete members found: {preview.Scan.Members.Count}   (no existing dump to diff against)";
            }

            DiffGrid.ItemsSource = rows;
            ResearchStatusText.Text =
                "Scan complete. Review the diff, then click “2. Update ApiMigrator (save dump)” to write " +
                "obsolete_api_dump.json (this is what Migrate / CS0618 / Obsolete Map use).";
            SaveMergedButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            ResearchStatusText.Text = "Error: " + ex.Message;
            MessageBox.Show(ex.ToString(), "Scan failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            ScanNowButton.IsEnabled = true;
            ResearchProgressBar.IsIndeterminate = false;
        }
    }

    private void SaveMergedButton_Click(object sender, RoutedEventArgs e)
    {
        if (_lastPreview is null)
        {
            MessageBox.Show("Run “1. Scan Managed” first.", "Update ApiMigrator",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        try
        {
            var managedDir = ManagedDirTextBox.Text.Trim();
            var dlls = DllNamesTextBox.Text.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
            var managedPaths = dlls.Select(d => Path.Combine(managedDir, d));

            var merged = DumpRefresher.BuildMerged(_lastPreview, managedPaths);
            var dataDir = Path.Combine(_toolsRoot, "data");
            var backupDir = Path.Combine(dataDir, "backups");
            var backedUpTo = DumpRefresher.SaveWithBackup(_dumpPath, backupDir, merged,
                dataDir: dataDir, managedDir: managedDir);

            string? reportPath = null;
            if (ResearchWriteReportCheckBox.IsChecked == true)
            {
                reportPath = Path.Combine(_toolsRoot, "reports",
                    $"dll-research_{DateTime.Now:yyyyMMdd_HHmmss}.md");
                DumpRefresher.WriteResearchReport(_lastPreview, reportPath, _dumpPath);
            }

            var msg =
                $"ApiMigrator dump updated ({merged.Entries.Count} entries).\n\n" +
                $"Wrote:\n{_dumpPath}\n\n" +
                (backedUpTo is not null ? $"Previous dump backed up to:\n{backedUpTo}\n\n" : "") +
                (reportPath is not null ? $"Research report:\n{reportPath}\n\n" : "") +
                "Migrate, CS0618 Resolve, and Obsolete Map now use this dump.\n" +
                "New members are needsManual until you promote them to curated_rewrite_rules.json autofixes.";

            MessageBox.Show(msg, "ApiMigrator updated", MessageBoxButton.OK, MessageBoxImage.Information);

            ResearchStatusText.Text = "ApiMigrator dump updated: " + _dumpPath;
            SaveMergedButton.IsEnabled = false;
            _lastPreview = null;
            LoadMapTab();
        }
        catch (Exception ex)
        {
            ResearchStatusText.Text = "Update failed: " + ex.Message;
            MessageBox.Show(ex.ToString(), "Update ApiMigrator failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ============================================================
    // CS0618 RESOLVE TAB
    // ============================================================

    private sealed class Cs0618SymbolRow
    {
        public int Count { get; set; }
        public string Symbol { get; set; } = "";
    }

    private sealed class Cs0618WarningRow
    {
        public string File { get; set; } = "";
        public int Line { get; set; }
        public string Symbol { get; set; } = "";
        public string Message { get; set; } = "";
    }

    private void Cs0618BrowseMod_Click(object sender, RoutedEventArgs e)
    {
        if (TryPickFolder("Choose a mod folder", Cs0618ModFolderTextBox.Text, out var folder))
            Cs0618ModFolderTextBox.Text = folder;
    }

    private void Cs0618LoadLog_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dlg = new OpenFileDialog
            {
                Title = "Load CS0618 / MODWARN log",
                Filter = "Text / log (*.txt;*.log;*.md)|*.txt;*.log;*.md|All files (*.*)|*.*",
            };
            if (dlg.ShowDialog() != true || string.IsNullOrWhiteSpace(dlg.FileName))
                return;
            Cs0618PasteBox.Text = File.ReadAllText(dlg.FileName);
        }
        catch (Exception ex)
        {
            MessageBox.Show("Could not load log file:\n\n" + ex.Message,
                "CS0618", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void Cs0618Run_Click(object sender, RoutedEventArgs e)
    {
        var mod = Cs0618ModFolderTextBox.Text.Trim();
        var paste = Cs0618PasteBox.Text ?? "";
        if (string.IsNullOrWhiteSpace(mod) && string.IsNullOrWhiteSpace(paste))
        {
            MessageBox.Show("Pick a mod folder and/or paste CS0618 lines.", "CS0618", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        Cs0618RunButton.IsEnabled = false;
        Cs0618ProgressBar.IsIndeterminate = true;
        Cs0618StatusText.Text = "Running...";
        Cs0618SummaryText.Text = "";
        Cs0618SymbolGrid.ItemsSource = null;
        Cs0618WarningGrid.ItemsSource = null;

        var opts = new Cs0618Resolver.Options
        {
            ModFolder = string.IsNullOrWhiteSpace(mod) ? null : mod,
            ManagedDir = string.IsNullOrWhiteSpace(Cs0618ManagedTextBox.Text) ? _managedDir : Cs0618ManagedTextBox.Text.Trim(),
            WarningText = string.IsNullOrWhiteSpace(paste) ? null : paste,
            Compile = Cs0618CompileCheckBox.IsChecked == true && !string.IsNullOrWhiteSpace(mod),
            Apply = Cs0618ApplyCheckBox.IsChecked == true,
            Backup = Cs0618BackupCheckBox.IsChecked == true,
            DumpPath = _dumpPath,
            RulesPath = _rulesPath,
        };

        try
        {
            var result = await System.Threading.Tasks.Task.Run(() =>
                Cs0618Resolver.Run(opts, msg => Dispatcher.Invoke(() => Cs0618StatusText.Text = msg)));

            Cs0618SymbolGrid.ItemsSource = result.SymbolCounts
                .OrderByDescending(kv => kv.Value)
                .Select(kv => new Cs0618SymbolRow { Count = kv.Value, Symbol = kv.Key })
                .ToList();

            Cs0618WarningGrid.ItemsSource = result.Warnings.Select(w => new Cs0618WarningRow
            {
                File = string.IsNullOrWhiteSpace(w.FilePath) ? "" : (Path.GetFileName(w.FilePath) ?? w.FilePath),
                Line = w.Line,
                Symbol = w.ObsoleteSymbol ?? "",
                Message = w.ObsoleteMessage ?? "",
            }).ToList();

            var mig = result.Migration;
            Cs0618SummaryText.Text =
                $"CS0618 harvested: {result.Warnings.Count}\n" +
                $"Affected files: {result.AffectedFiles.Count}\n" +
                $"Auto-fixes: {mig?.TotalAutoFixes ?? 0}\n" +
                $"Remaining hits: {mig?.TotalRemainingHits ?? 0}\n" +
                $"Mode: {(opts.Apply ? "APPLY" : "DRY-RUN")}";

            if (result.Notes.Count > 0)
                Cs0618StatusText.Text = "Done. Notes: " + string.Join(" | ", result.Notes.Take(3));
            else
                Cs0618StatusText.Text = "Done.";
        }
        catch (Exception ex)
        {
            Cs0618StatusText.Text = "Error: " + ex.Message;
            MessageBox.Show(ex.ToString(), "CS0618 resolve failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            Cs0618RunButton.IsEnabled = true;
            Cs0618ProgressBar.IsIndeterminate = false;
        }
    }

    // ============================================================
    // CP437 → UTF16 TAB
    // ============================================================

    private sealed class Cp437FileRow
    {
        public string FilePath { get; set; } = "";
        public int AutoFixCount { get; set; }
        public int ReviewCount { get; set; }
        public Cp437Converter.FileResult Result { get; set; } = null!;
    }

    private sealed class Cp437HitRow
    {
        public int Line { get; set; }
        public string Kind { get; set; } = "";
        public string From { get; set; } = "";
        public string To { get; set; } = "";
        public string Auto { get; set; } = "";
        public string Review { get; set; } = "";
        public string Context { get; set; } = "";
    }

    private void Cp437AddMods_Click(object sender, RoutedEventArgs e)
    {
        if (!_cp437Paths.Contains(_modsRoot)) _cp437Paths.Add(_modsRoot);
    }

    private void Cp437AddWorkshop_Click(object sender, RoutedEventArgs e)
    {
        if (!_cp437Paths.Contains(_workshopPath)) _cp437Paths.Add(_workshopPath);
    }

    private void Cp437AddFolder_Click(object sender, RoutedEventArgs e)
    {
        if (!TryPickFolder("Choose a folder to scan", null, out var folder))
            return;
        if (!_cp437Paths.Any(p => string.Equals(p, folder, StringComparison.OrdinalIgnoreCase)))
            _cp437Paths.Add(folder);
    }

    private void Cp437RemovePath_Click(object sender, RoutedEventArgs e)
    {
        if (Cp437PathsListBox.SelectedItem is string s) _cp437Paths.Remove(s);
    }

    private async void Cp437Run_Click(object sender, RoutedEventArgs e)
    {
        if (_cp437Paths.Count == 0)
        {
            MessageBox.Show("Add at least one scan root first.", "CP437", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        Cp437RunButton.IsEnabled = false;
        Cp437SaveReportButton.IsEnabled = false;
        Cp437ProgressBar.Value = 0;
        Cp437StatusText.Text = "Starting...";
        Cp437SummaryText.Text = "";
        Cp437FileGrid.ItemsSource = null;
        Cp437HitGrid.ItemsSource = null;

        var opts = new Cp437Converter.Options
        {
            Paths = _cp437Paths.ToList(),
            ModFilter = string.IsNullOrWhiteSpace(Cp437ModFilterTextBox.Text) ? null : Cp437ModFilterTextBox.Text.Trim(),
            Apply = Cp437ApplyCheckBox.IsChecked == true,
            Backup = Cp437BackupCheckBox.IsChecked == true,
            ConvertAmbiguousEscapes = Cp437AmbiguousCheckBox.IsChecked == true,
            ForceXmlUtf8Encoding = Cp437ForceUtf8CheckBox.IsChecked == true,
        };

        try
        {
            var report = await System.Threading.Tasks.Task.Run(() => Cp437Converter.Run(
                opts,
                onLog: msg => Dispatcher.Invoke(() => Cp437StatusText.Text = msg),
                onProgress: (done, total) => Dispatcher.Invoke(() =>
                {
                    if (total > 0) Cp437ProgressBar.Value = 100.0 * done / total;
                })));

            _lastCp437Report = report;
            Cp437FileGrid.ItemsSource = report.FileResults.Select(f => new Cp437FileRow
            {
                FilePath = f.FilePath,
                AutoFixCount = f.AutoFixCount,
                ReviewCount = f.ReviewCount,
                Result = f,
            }).ToList();

            Cp437SummaryText.Text =
                $"Mode: {(opts.Apply ? "APPLY" : "DRY-RUN")}\n" +
                $"Files scanned: {report.FilesScanned}\n" +
                $"Files with hits: {report.FileResults.Count}\n" +
                $"Auto-fixes: {report.TotalAutoFixes}\n" +
                $"Needs review: {report.TotalReviewHits}";

            Cp437StatusText.Text = "Done.";
            Cp437SaveReportButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            Cp437StatusText.Text = "Error: " + ex.Message;
            MessageBox.Show(ex.ToString(), "CP437 convert failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            Cp437RunButton.IsEnabled = true;
            Cp437ProgressBar.Value = 100;
        }
    }

    private void Cp437FileGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (Cp437FileGrid.SelectedItem is not Cp437FileRow row)
        {
            Cp437HitGrid.ItemsSource = null;
            return;
        }

        Cp437HitGrid.ItemsSource = row.Result.Hits.Select(h => new Cp437HitRow
        {
            Line = h.Line,
            Kind = h.Kind,
            From = h.From,
            To = h.To,
            Auto = h.AutoFixed ? "✓" : "",
            Review = h.NeedsReview ? "!" : "",
            Context = h.Context,
        }).ToList();
    }

    private void Cp437SaveReport_Click(object sender, RoutedEventArgs e)
    {
        if (_lastCp437Report is null) return;
        var dlg = new SaveFileDialog
        {
            Filter = "Markdown (*.md)|*.md|All files (*.*)|*.*",
            FileName = $"Cp437_{DateTime.Now:yyyyMMdd_HHmmss}.md",
            InitialDirectory = Path.Combine(_toolsRoot, "reports"),
        };
        if (dlg.ShowDialog() == true)
        {
            File.WriteAllText(dlg.FileName, _lastCp437Report.ToMarkdown());
            MessageBox.Show($"Report saved to:\n{dlg.FileName}", "Saved", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    // ============================================================
    // Shared folder picker (no native folder COM dialogs — those hard-crash here)
    // ============================================================

    /// <summary>
    /// Pure-WPF path entry (+ optional OpenFileDialog for “file in folder”).
    /// Does not call <c>OpenFolderDialog</c> or WinForms <c>FolderBrowserDialog</c>.
    /// Browse only sets a path string — never auto-compiles or scans.
    /// </summary>
    private bool TryPickFolder(string title, string? initialDirectory, out string folderPath)
    {
        folderPath = "";
        try
        {
            var dlg = new PathPickerWindow(
                title,
                initialDirectory,
                _modsRoot,
                _workshopPath,
                _managedDir,
                _settings.RecentFolders)
            {
                Owner = this,
            };
            if (dlg.ShowDialog() != true || string.IsNullOrWhiteSpace(dlg.SelectedPath))
                return false;
            folderPath = dlg.SelectedPath;
            _settings.RememberFolder(folderPath);
            return true;
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Could not select a folder.\n\n" + ex.Message,
                title, MessageBoxButton.OK, MessageBoxImage.Error);
            return false;
        }
    }

    private static string FindToolsRoot() => CoqPaths.FindToolsRoot();
}
