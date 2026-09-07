using System.IO;
using System.Text.Json;

namespace ApiMigratorGui;

public sealed class GuiSettings
{
    public string? LastLocalMods { get; set; }
    public string? LastWorkshop { get; set; }
    public bool IncludeWorkshop { get; set; } = true;
    public string? LastModFilter { get; set; }
    public string? LastCs0618Mod { get; set; }
    public string OllamaUrl { get; set; } = "http://localhost:11434";
    public string OllamaModel { get; set; } = "llama3.1";
    public int OllamaMaxHits { get; set; } = 12;
    public bool OllamaUseCloud { get; set; }
    public bool OllamaRememberApiKey { get; set; }
    public string? OllamaApiKey { get; set; }
    public List<string> RecentFolders { get; set; } = new();
    public int SelectedTab { get; set; }
    public double? WindowWidth { get; set; }
    public double? WindowHeight { get; set; }
    public double? WindowLeft { get; set; }
    public double? WindowTop { get; set; }

    public static string PathFor(string toolsRoot) =>
        System.IO.Path.Combine(toolsRoot, "data", "gui-settings.json");

    public static GuiSettings Load(string toolsRoot)
    {
        try
        {
            var path = PathFor(toolsRoot);
            if (!File.Exists(path))
                return new GuiSettings();
            return JsonSerializer.Deserialize<GuiSettings>(File.ReadAllText(path))
                   ?? new GuiSettings();
        }
        catch
        {
            return new GuiSettings();
        }
    }

    public void RememberFolder(string? folder)
    {
        if (string.IsNullOrWhiteSpace(folder)) return;
        try
        {
            var full = Path.GetFullPath(folder.Trim());
            RecentFolders.RemoveAll(p => string.Equals(p, full, StringComparison.OrdinalIgnoreCase));
            RecentFolders.Insert(0, full);
            if (RecentFolders.Count > 12)
                RecentFolders.RemoveRange(12, RecentFolders.Count - 12);
        }
        catch { /* ignore */ }
    }

    public void Save(string toolsRoot)
    {
        try
        {
            var path = PathFor(toolsRoot);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, JsonSerializer.Serialize(this, new JsonSerializerOptions
            {
                WriteIndented = true,
            }));
        }
        catch { /* never block UI on settings */ }
    }
}
