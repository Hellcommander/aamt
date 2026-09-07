using System.Text.Json;

namespace ApiMigrator.Core;

public static class DumpStore
{
    private static readonly JsonSerializerOptions WriteOptions = new()
    {
        WriteIndented = true,
    };

    public static ObsoleteDump LoadDump(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException($"Obsolete API dump not found: {path}", path);
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<ObsoleteDump>(json)
               ?? throw new InvalidDataException($"Could not parse dump JSON: {path}");
    }

    public static void SaveDump(string path, ObsoleteDump dump)
    {
        var json = JsonSerializer.Serialize(dump, WriteOptions);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, json);
    }

    public static CuratedRulesFile LoadRules(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException($"Curated rewrite rules file not found: {path}", path);
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<CuratedRulesFile>(json)
               ?? throw new InvalidDataException($"Could not parse rules JSON: {path}");
    }

    public static void SaveRules(string path, CuratedRulesFile rules)
    {
        var json = JsonSerializer.Serialize(rules, WriteOptions);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, json);
    }

    /// <summary>Timestamped backup copy of a dump/rules file before it gets overwritten by a refresh.</summary>
    public static string Backup(string path, string backupDir)
    {
        Directory.CreateDirectory(backupDir);
        var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        var name = Path.GetFileNameWithoutExtension(path) + "_" + stamp + Path.GetExtension(path);
        var dest = Path.Combine(backupDir, name);
        File.Copy(path, dest, overwrite: false);
        return dest;
    }
}
