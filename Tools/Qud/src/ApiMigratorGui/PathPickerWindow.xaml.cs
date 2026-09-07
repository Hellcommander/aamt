using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using MessageBox = System.Windows.MessageBox;
using MessageBoxButton = System.Windows.MessageBoxButton;
using MessageBoxImage = System.Windows.MessageBoxImage;
using MessageBoxResult = System.Windows.MessageBoxResult;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;

namespace ApiMigratorGui;

/// <summary>
/// Pure-WPF folder path picker. Avoids OpenFolderDialog / FolderBrowserDialog, which
/// hard-crash (native/COM) on this machine when Browse is clicked.
/// </summary>
public partial class PathPickerWindow : Window
{
    private readonly string _localMods;
    private readonly string _workshop;
    private readonly string _managed;
    private bool _suppressCombo;
    private readonly List<FolderChoice> _allChoices = new();

    public string SelectedPath { get; private set; } = "";

    public PathPickerWindow(
        string prompt,
        string? initialPath,
        string localModsDefault,
        string workshopDefault,
        string managedDefault,
        IEnumerable<string>? recentFolders = null)
    {
        InitializeComponent();
        Title = prompt;
        PromptText.Text = prompt + "\n\nNative folder Browse dialogs crash here — paste a path, pick a Workshop mod, use a preset, or pick any file inside the folder.";
        _localMods = localModsDefault;
        _workshop = workshopDefault;
        _managed = managedDefault;
        PathTextBox.Text = initialPath?.Trim() ?? "";
        FillWorkshopCombo(recentFolders);
        PathTextBox.SelectAll();
        PathTextBox.Focus();
    }

    sealed class FolderChoice
    {
        public string Display { get; set; } = "";
        public string Path { get; set; } = "";
    }

    private void FillWorkshopCombo(IEnumerable<string>? recentFolders)
    {
        var items = new List<FolderChoice>();
        if (recentFolders is not null)
        {
            foreach (var r in recentFolders.Take(8))
            {
                if (string.IsNullOrWhiteSpace(r)) continue;
                items.Add(new FolderChoice { Display = "Recent — " + r, Path = r });
            }
        }

        try
        {
            if (Directory.Exists(_workshop))
            {
                foreach (var dir in Directory.EnumerateDirectories(_workshop).OrderBy(d => d, StringComparer.OrdinalIgnoreCase).Take(80))
                {
                    var id = System.IO.Path.GetFileName(dir);
                    var title = TryReadWorkshopTitle(dir);
                    var label = string.IsNullOrEmpty(title) ? id : id + " — " + title;
                    items.Add(new FolderChoice { Display = label, Path = dir });
                }
            }
        }
        catch { /* ignore listing errors */ }

        _suppressCombo = true;
        _allChoices.Clear();
        _allChoices.AddRange(items);
        ApplyWorkshopFilter();
        _suppressCombo = false;
        WorkshopModCombo.IsEnabled = _allChoices.Count > 0;
    }

    private void WorkshopFilterBox_TextChanged(object sender, TextChangedEventArgs e)
        => ApplyWorkshopFilter();

    private void ApplyWorkshopFilter()
    {
        var q = WorkshopFilterBox?.Text?.Trim() ?? "";
        IEnumerable<FolderChoice> shown = _allChoices;
        if (q.Length > 0)
        {
            shown = _allChoices.Where(c =>
                (c.Display ?? "").Contains(q, StringComparison.OrdinalIgnoreCase) ||
                (c.Path ?? "").Contains(q, StringComparison.OrdinalIgnoreCase));
        }
        var keep = WorkshopModCombo.SelectedItem as FolderChoice;
        var was = _suppressCombo;
        _suppressCombo = true;
        WorkshopModCombo.ItemsSource = shown.ToList();
        if (keep is not null)
            WorkshopModCombo.SelectedItem = keep;
        _suppressCombo = was;
    }

    static string? TryReadWorkshopTitle(string dir)
    {
        try
        {
            foreach (var name in new[] { "workshop.json", "Manifest.json", "manifest.json" })
            {
                var p = System.IO.Path.Combine(dir, name);
                if (!File.Exists(p)) continue;
                var text = File.ReadAllText(p);
                var m = System.Text.RegularExpressions.Regex.Match(text, @"""(?:Title|title)""\s*:\s*""([^""]+)""");
                if (m.Success) return m.Groups[1].Value;
            }
        }
        catch { /* ignore */ }
        return null;
    }

    private void WorkshopModCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_suppressCombo) return;
        if (WorkshopModCombo.SelectedItem is FolderChoice c && !string.IsNullOrWhiteSpace(c.Path))
            PathTextBox.Text = c.Path;
    }

    private void UseLocalMods_Click(object sender, RoutedEventArgs e) => PathTextBox.Text = _localMods;
    private void UseWorkshop_Click(object sender, RoutedEventArgs e) => PathTextBox.Text = _workshop;
    private void UseManaged_Click(object sender, RoutedEventArgs e) => PathTextBox.Text = _managed;

    private void PickFileInFolder_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select any file inside the target folder",
                Filter = "All files (*.*)|*.*",
                CheckFileExists = true,
                Multiselect = false,
            };
            var seed = PathTextBox.Text.Trim();
            if (seed.Length > 0)
            {
                try
                {
                    var full = Path.GetFullPath(seed);
                    if (Directory.Exists(full))
                        dlg.InitialDirectory = full;
                    else if (File.Exists(full))
                        dlg.InitialDirectory = Path.GetDirectoryName(full) ?? "";
                }
                catch { /* ignore */ }
            }

            if (dlg.ShowDialog(this) != true || string.IsNullOrWhiteSpace(dlg.FileName))
                return;

            var dir = Path.GetDirectoryName(dlg.FileName);
            if (string.IsNullOrWhiteSpace(dir))
            {
                MessageBox.Show("Could not determine the parent folder.", Title,
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            PathTextBox.Text = Path.GetFullPath(dir);
        }
        catch (Exception ex)
        {
            MessageBox.Show("File picker failed:\n\n" + ex.Message, Title,
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Ok_Click(object sender, RoutedEventArgs e)
    {
        var raw = PathTextBox.Text?.Trim() ?? "";
        if (raw.Length == 0)
        {
            MessageBox.Show("Enter a folder path first.", Title,
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            var full = Path.GetFullPath(raw);
            if (!Directory.Exists(full))
            {
                var answer = MessageBox.Show(
                    "That folder does not exist:\n\n" + full + "\n\nUse it anyway?",
                    Title, MessageBoxButton.YesNo, MessageBoxImage.Warning);
                if (answer != MessageBoxResult.Yes)
                    return;
            }
            SelectedPath = full;
            DialogResult = true;
            Close();
        }
        catch (Exception ex)
        {
            MessageBox.Show("Invalid path:\n\n" + ex.Message, Title,
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
