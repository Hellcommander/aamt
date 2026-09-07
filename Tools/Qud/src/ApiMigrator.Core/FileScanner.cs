using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

public static class FileScanner
{
    public static List<string> GetTargetFiles(IEnumerable<string> roots, IReadOnlyList<string> excludeDirs,
        IReadOnlyList<string> extensions, string? modFilter, Action<string>? onWarning = null)
    {
        var files = new List<string>();
        var extSet = new HashSet<string>(extensions.Select(e => e.ToLowerInvariant()));
        var excludeRegexes = excludeDirs
            .Select(d => new Regex($@"(?i)\\{Regex.Escape(d)}(\\|$)", RegexOptions.None))
            .ToList();

        foreach (var root in roots)
        {
            if (File.Exists(root))
            {
                TryAdd(root);
                continue;
            }

            if (!Directory.Exists(root))
            {
                onWarning?.Invoke($"Path not found, skipping: {root}");
                continue;
            }

            IEnumerable<string> found;
            try
            {
                found = Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories);
            }
            catch (Exception ex)
            {
                onWarning?.Invoke($"Could not enumerate {root}: {ex.Message}");
                continue;
            }

            foreach (var f in found)
                TryAdd(f);
        }

        void TryAdd(string f)
        {
            var ext = Path.GetExtension(f).ToLowerInvariant();
            if (!extSet.Contains(ext)) return;

            var normalized = f.Replace('/', '\\');
            if (excludeRegexes.Any(r => r.IsMatch(normalized))) return;

            if (!string.IsNullOrEmpty(modFilter) &&
                normalized.IndexOf(modFilter, StringComparison.OrdinalIgnoreCase) < 0)
            {
                return;
            }

            files.Add(f);
        }

        return files;
    }

    /// <summary>
    /// Walks up from <paramref name="filePath"/> to the nearest folder that contains
    /// <c>manifest.json</c> / <c>config.json</c> (the mod root). Falls back to the
    /// file's directory when none is found.
    /// </summary>
    public static string GetModRoot(string filePath)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(filePath));
        while (!string.IsNullOrEmpty(dir))
        {
            if (File.Exists(Path.Combine(dir, "manifest.json")) ||
                File.Exists(Path.Combine(dir, "Manifest.json")) ||
                File.Exists(Path.Combine(dir, "config.json")) ||
                File.Exists(Path.Combine(dir, "Config.json")))
            {
                return dir;
            }
            var parent = Path.GetDirectoryName(dir);
            if (string.IsNullOrEmpty(parent) ||
                string.Equals(parent, dir, StringComparison.OrdinalIgnoreCase))
                break;
            dir = parent;
        }
        return Path.GetDirectoryName(Path.GetFullPath(filePath)) ?? filePath;
    }
}
