using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Maps the many names a CoQ mod is known by onto the ID <c>ModManager.ModMap</c> actually
/// uses: <c>Regex.Replace(Manifest.ID ?? folderName, "[^\\w ]", "")</c>.
/// </summary>
/// <remarks>
/// Workshop copies turned local often keep <c>Dependencies</c> / <c>LoadAfter</c> keys that
/// were the Steam folder number or the old folder title. After a rename those strings no
/// longer match ModMap, so required edges go Missing and LoadAfter is a no-op.
/// </remarks>
public sealed class ModIdCatalog
{
    /// <summary>Same character class as <c>ModInfo.ReadConfigurations</c>.</summary>
    static readonly Regex SanitizeRegex = new(@"[^\w ]", RegexOptions.Compiled);

    static readonly Regex WorkshopFolderId = new(@"^\d{8,}$", RegexOptions.Compiled);

    static readonly HashSet<string> SkipDirNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "bin", "obj", "reports", ".git", ".vs", ".cursor",
        "Library", "Packages", "Temp", "Logs",
        "ProjectSettings",
    };

    readonly Dictionary<string, string> _aliasToCanonical = new(StringComparer.OrdinalIgnoreCase);
    readonly Dictionary<string, int> _aliasScore = new(StringComparer.OrdinalIgnoreCase);
    readonly HashSet<string> _canonical = new(StringComparer.Ordinal);
    readonly Dictionary<string, string> _dirToCanonical = new(StringComparer.OrdinalIgnoreCase);

    public static string SanitizeId(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        return SanitizeRegex.Replace(raw.Trim(), "");
    }

    public static string StripQudMarkup(string? title)
    {
        if (string.IsNullOrWhiteSpace(title)) return title ?? "";
        return Regex.Replace(title, @"\{\{[^}]*\}\}", "").Trim();
    }

    public static bool LooksLikeWorkshopFolderId(string? raw) =>
        !string.IsNullOrWhiteSpace(raw) && WorkshopFolderId.IsMatch(raw.Trim());

    /// <summary>
    /// Scan each root: a mod folder (has manifest/workshop.json) or a parent of mod folders
    /// (LocalLow Mods / Steam workshop content). Duplicate roots are ignored.
    /// </summary>
    public static ModIdCatalog Build(IEnumerable<string> roots)
    {
        var catalog = new ModIdCatalog();
        catalog.AddAlias("Base", "Base", score: 100);

        var seenRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var entries = new List<Entry>();
        foreach (var root in roots)
        {
            if (string.IsNullOrWhiteSpace(root)) continue;
            string full;
            try { full = Path.GetFullPath(root); }
            catch { continue; }
            if (!Directory.Exists(full)) continue;
            if (!seenRoots.Add(full)) continue;

            if (LooksLikeModDirectory(full))
                TryAddEntry(full, entries);
            else
            {
                string[] children;
                try { children = Directory.GetDirectories(full); }
                catch { continue; }
                foreach (var child in children)
                    TryAddEntry(child, entries);
            }
        }

        foreach (var e in entries)
            catalog._canonical.Add(e.Canonical);

        foreach (var e in entries.OrderByDescending(e => e.Score))
            catalog.RegisterEntry(e);

        return catalog;
    }

    /// <summary>LocalLow Mods + live Steam workshop + any extra roots (migrate --path).</summary>
    public static IEnumerable<string> DefaultScanRoots(IEnumerable<string>? extra = null)
    {
        if (extra is not null)
        {
            foreach (var e in extra)
            {
                if (!string.IsNullOrWhiteSpace(e))
                    yield return e;
            }
        }

        yield return CoqPaths.DefaultModsRoot;
        var ws = SteamInstall.WorkshopContentDir;
        if (!string.IsNullOrWhiteSpace(ws))
            yield return ws;
    }

    public IReadOnlyCollection<string> CanonicalIds => _canonical;

    public bool IsCanonical(string? token) =>
        !string.IsNullOrWhiteSpace(token) && _canonical.Contains(token.Trim());

    /// <summary>Game ModMap id for this mod directory, or null if it was not scanned.</summary>
    public string? CanonicalIdForDirectory(string? dir)
    {
        if (string.IsNullOrWhiteSpace(dir)) return null;
        try
        {
            var full = Path.GetFullPath(dir);
            return _dirToCanonical.TryGetValue(full, out var id) ? id : null;
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Resolve a Dependency / LoadAfter token to the live ModMap id.
    /// Workshop published-file ids prefer the renamed local copy when both a numeric leftover
    /// folder and a titled folder exist.
    /// </summary>
    public string? Resolve(string? token)
    {
        if (string.IsNullOrWhiteSpace(token)) return null;
        var t = token.Trim();
        if (t.Equals("Base", StringComparison.OrdinalIgnoreCase))
            return "Base";

        if (LooksLikeWorkshopFolderId(t) && _aliasToCanonical.TryGetValue(t, out var fromWs))
            return fromWs;

        if (_canonical.Contains(t))
            return t;

        if (_aliasToCanonical.TryGetValue(t, out var mapped))
            return mapped;

        var san = SanitizeId(t);
        if (san.Length > 0 && san != t)
        {
            if (_canonical.Contains(san))
                return san;
            if (_aliasToCanonical.TryGetValue(san, out mapped))
                return mapped;
        }

        return null;
    }

    void RegisterEntry(Entry e)
    {
        _dirToCanonical[e.Dir] = e.Canonical;
        AddAlias(e.Canonical, e.Canonical, e.Score);
        AddAlias(e.Folder, e.Canonical, e.Score);
        AddAlias(SanitizeId(e.Folder), e.Canonical, e.Score);
        if (!string.IsNullOrEmpty(e.ManifestId))
        {
            AddAlias(e.ManifestId, e.Canonical, e.Score);
            AddAlias(SanitizeId(e.ManifestId), e.Canonical, e.Score);
        }
        if (!string.IsNullOrEmpty(e.Title))
        {
            AddAlias(e.Title, e.Canonical, e.Score);
            AddAlias(SanitizeId(e.Title), e.Canonical, e.Score);
        }
        if (!string.IsNullOrEmpty(e.WorkshopId))
            AddAlias(e.WorkshopId, e.Canonical, e.Score + 1);
    }

    void AddAlias(string? alias, string canonical, int score)
    {
        if (string.IsNullOrWhiteSpace(alias) || string.IsNullOrEmpty(canonical)) return;
        var key = alias.Trim();
        if (key.Length == 0) return;
        if (_aliasScore.TryGetValue(key, out var existing) && existing >= score)
            return;
        _aliasToCanonical[key] = canonical;
        _aliasScore[key] = score;
    }

    static bool LooksLikeModDirectory(string dir)
    {
        foreach (var name in new[] { "manifest.json", "Manifest.json", "config.json", "Config.json", "workshop.json" })
        {
            if (File.Exists(Path.Combine(dir, name)))
                return true;
        }
        return false;
    }

    static void TryAddEntry(string dir, List<Entry> entries)
    {
        var name = Path.GetFileName(dir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        if (string.IsNullOrWhiteSpace(name) || name.StartsWith('.') || SkipDirNames.Contains(name))
            return;

        string? manifestId = null;
        string? title = null;
        foreach (var file in new[] { "manifest.json", "Manifest.json", "config.json", "Config.json" })
        {
            var path = Path.Combine(dir, file);
            if (!File.Exists(path)) continue;
            if (TryReadJsonObject(path, out var obj) && obj is not null)
            {
                manifestId ??= ReadString(obj, "id", "ID");
                title ??= StripQudMarkup(ReadString(obj, "title", "Title", "name"));
                break;
            }
        }

        string? workshopId = null;
        var wsPath = Path.Combine(dir, "workshop.json");
        if (File.Exists(wsPath) && TryReadJsonObject(wsPath, out var ws) && ws is not null)
        {
            workshopId = ReadWorkshopId(ws);
            title ??= StripQudMarkup(ReadString(ws, "Title", "title"));
        }

        var canonical = SanitizeId(!string.IsNullOrWhiteSpace(manifestId) ? manifestId : name);
        if (string.IsNullOrEmpty(canonical))
            return;

        var numericFolder = LooksLikeWorkshopFolderId(name);
        var score = 0;
        if (!numericFolder) score += 8;
        if (!string.IsNullOrEmpty(manifestId) && !LooksLikeWorkshopFolderId(SanitizeId(manifestId)))
            score += 4;
        if (!string.IsNullOrEmpty(manifestId)) score += 2;

        entries.Add(new Entry
        {
            Dir = Path.GetFullPath(dir),
            Folder = name,
            Canonical = canonical,
            ManifestId = manifestId,
            Title = title,
            WorkshopId = workshopId,
            Score = score,
        });
    }

    static bool TryReadJsonObject(string path, out JsonObject? obj)
    {
        obj = null;
        try
        {
            var node = JsonNode.Parse(File.ReadAllText(path));
            obj = node as JsonObject;
            return obj is not null;
        }
        catch
        {
            return false;
        }
    }

    static string? ReadString(JsonObject obj, params string[] names)
    {
        foreach (var p in obj)
        {
            foreach (var want in names)
            {
                if (!string.Equals(p.Key, want, StringComparison.OrdinalIgnoreCase))
                    continue;
                if (p.Value is JsonValue jv && jv.TryGetValue<string>(out var s) && !string.IsNullOrWhiteSpace(s))
                    return s.Trim();
            }
        }
        return null;
    }

    static string? ReadWorkshopId(JsonObject obj)
    {
        foreach (var p in obj)
        {
            if (!p.Key.Equals("WorkshopId", StringComparison.OrdinalIgnoreCase)
                && !p.Key.Equals("PublishedFileId", StringComparison.OrdinalIgnoreCase))
                continue;
            if (p.Value is not JsonValue jv) continue;
            if (jv.TryGetValue<ulong>(out var u) && u > 0) return u.ToString();
            if (jv.TryGetValue<long>(out var l) && l > 0) return l.ToString();
            if (jv.TryGetValue<decimal>(out var d) && d > 0) return decimal.Truncate(d).ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (jv.TryGetValue<string>(out var s) && ulong.TryParse(s.Trim(), out var parsed) && parsed > 0)
                return parsed.ToString();
        }
        return null;
    }

    sealed class Entry
    {
        public required string Dir { get; init; }
        public required string Folder { get; init; }
        public required string Canonical { get; init; }
        public string? ManifestId { get; init; }
        public string? Title { get; init; }
        public string? WorkshopId { get; init; }
        public int Score { get; init; }
    }
}
