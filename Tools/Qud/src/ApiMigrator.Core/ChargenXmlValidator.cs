using System.Collections.Concurrent;
using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

public sealed class ChargenOptions
{
    public List<string> Paths { get; set; } = new();
    public string? ModFilter { get; set; }
    public bool Apply { get; set; }
    public bool Backup { get; set; } = true;
    public string BasePath { get; set; } = SteamInstall.StreamingAssetsBase
        ?? Path.GetFullPath(Path.Combine(SteamInstall.ManagedDirOrFallback, "..", "StreamingAssets", "Base"));
    public string DlcPath { get; set; } = SteamInstall.StreamingAssetsDlc
        ?? Path.GetFullPath(Path.Combine(SteamInstall.ManagedDirOrFallback, "..", "StreamingAssets", "DLC"));
    public string? ReportPath { get; set; }
}

public enum ChargenSeverity { Error, Warn }

public sealed class ChargenFinding
{
    public ChargenSeverity Severity { get; set; }
    public string Kind { get; set; } = ""; // Population | Genotype | Subtype
    public string Rule { get; set; } = "";
    public string ModName { get; set; } = "";
    public string File { get; set; } = "";
    public int Line { get; set; }
    public string Message { get; set; } = "";
    public string Population { get; set; } = "";
    public bool HighPriority { get; set; }
}

public sealed class ChargenAppliedFix
{
    public string File { get; set; } = "";
    public string Note { get; set; } = "";
}

public sealed class ChargenReport
{
    public bool Applied { get; set; }
    public List<string> ScanRoots { get; set; } = new();
    public string? ModFilter { get; set; }
    public List<ChargenFinding> Findings { get; set; } = new();
    public List<ChargenAppliedFix> AppliedFixes { get; set; } = new();
    public int ModsScanned { get; set; }
    public int PopulationFiles { get; set; }
    public int GenotypeFiles { get; set; }
    public int SubtypeFiles { get; set; }
    public int BlueprintFiles { get; set; }
    public int PopulationsIndexed { get; set; }
    public int BlueprintsIndexed { get; set; }
    public int SubtypeClassesIndexed { get; set; }
    public int SubtypesIndexed { get; set; }
    public int GenotypesIndexed { get; set; }
    public int ErrorCount => Findings.Count(f => f.Severity == ChargenSeverity.Error);
    public int WarnCount => Findings.Count(f => f.Severity == ChargenSeverity.Warn);

    public string ToMarkdown()
    {
        var sb = new StringBuilder();
        sb.AppendLine("# Chargen XML validation report");
        sb.AppendLine();
        sb.AppendLine($"Generated: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
        sb.AppendLine($"Mode: {(Applied ? "Apply" : "Dry-run")}");
        sb.AppendLine();
        sb.AppendLine("## Summary");
        sb.AppendLine();
        sb.AppendLine("| Metric | Count |");
        sb.AppendLine("|---|---:|");
        sb.AppendLine($"| ModsScanned | {ModsScanned} |");
        sb.AppendLine($"| PopulationFiles | {PopulationFiles} |");
        sb.AppendLine($"| GenotypeFiles | {GenotypeFiles} |");
        sb.AppendLine($"| SubtypeFiles | {SubtypeFiles} |");
        sb.AppendLine($"| BlueprintFiles | {BlueprintFiles} |");
        sb.AppendLine($"| Errors | {ErrorCount} |");
        sb.AppendLine($"| Warns | {WarnCount} |");
        sb.AppendLine($"| AppliedFixes | {AppliedFixes.Count} |");
        sb.AppendLine($"| PopulationsIndexed | {PopulationsIndexed} |");
        sb.AppendLine($"| BlueprintsIndexed | {BlueprintsIndexed} |");
        sb.AppendLine($"| SubtypeClassesIndexed | {SubtypeClassesIndexed} |");
        sb.AppendLine($"| SubtypesIndexed | {SubtypesIndexed} |");
        sb.AppendLine($"| GenotypesIndexed | {GenotypesIndexed} |");
        sb.AppendLine();

        var high = Findings.Where(f => f.HighPriority || (f.Severity == ChargenSeverity.Error &&
            Regex.IsMatch(f.Rule, "gear|self-ref|cycle|duplicate-group|empty-pickone|unknown-subtype|missing-gear|gear-population|missing-group|xml-parse", RegexOptions.IgnoreCase)))
            .OrderBy(f => f.ModName).ThenBy(f => f.Kind).ThenBy(f => f.Line).ToList();
        if (high.Count > 0)
        {
            sb.AppendLine("## Highest priority");
            sb.AppendLine();
            foreach (var f in high)
            {
                var loc = f.Line > 0 ? $":{f.Line}" : "";
                sb.AppendLine($"- **{f.Severity}** [{f.Kind}/{f.Rule}] {f.ModName} — `{f.File}{loc}` — {f.Message}");
            }
            sb.AppendLine();
        }

        if (AppliedFixes.Count > 0)
        {
            sb.AppendLine("## Applied fixes");
            sb.AppendLine();
            foreach (var a in AppliedFixes)
                sb.AppendLine($"- `{a.File}` — {a.Note}");
            sb.AppendLine();
        }

        foreach (var kind in new[] { "Population", "Genotype", "Subtype" })
        {
            var group = Findings.Where(f => f.Kind == kind).OrderBy(f => f.ModName).ThenBy(f => f.File).ThenBy(f => f.Line).ToList();
            if (group.Count == 0) continue;
            sb.AppendLine($"## {kind}");
            sb.AppendLine();
            foreach (var modGroup in group.GroupBy(f => f.ModName))
            {
                sb.AppendLine($"### {modGroup.Key}");
                sb.AppendLine();
                foreach (var f in modGroup)
                {
                    var loc = f.Line > 0 ? $":{f.Line}" : "";
                    sb.AppendLine($"- **{f.Severity}** `{f.Rule}` — `{f.File}{loc}` — {f.Message}");
                }
                sb.AppendLine();
            }
        }

        if (Findings.Count == 0)
        {
            sb.AppendLine("_No issues found._");
            sb.AppendLine();
        }

        return sb.ToString();
    }
}

/// <summary>
/// Validates PopulationTables / Genotypes / Subtypes XML for New-Game chargen breakers.
/// Mirrors _tools\Validate-ChargenXml.ps1.
/// </summary>
public static class ChargenXmlValidator
{
    private static readonly string[] SkipDirNames =
        { "_tools", "bin", "obj", ".git", ".vs", ".dotnet", "node_modules", "_decompile", "scratch" };

    private static readonly string[] DynamicPrefixes =
    {
        "DynamicInheritsTable:", "DynamicObjectsTable:", "DynamicSemanticTable:", "DynamicEncounterTable:"
    };

    private static readonly Encoding Latin1 = Encoding.GetEncoding(28591);

    private sealed class NameIndex
    {
        public HashSet<string> Exact { get; } = new(StringComparer.Ordinal);
        public Dictionary<string, string> Lower { get; } = new(StringComparer.Ordinal);

        public void Add(string? name)
        {
            if (string.IsNullOrEmpty(name)) return;
            Exact.Add(name);
            var k = name.ToLowerInvariant();
            if (!Lower.ContainsKey(k)) Lower[k] = name;
        }

        public void Remove(string? name)
        {
            if (string.IsNullOrEmpty(name)) return;
            Exact.Remove(name);
            var k = name.ToLowerInvariant();
            if (Lower.TryGetValue(k, out var cur) && cur == name) Lower.Remove(k);
        }

        public string? CaseMismatch(string name)
        {
            if (Exact.Contains(name)) return null;
            return Lower.TryGetValue(name.ToLowerInvariant(), out var canon) ? canon : null;
        }
    }

    private sealed class ModUnit
    {
        public string Name { get; set; } = "";
        public string Root { get; set; } = "";
    }

    public static ChargenReport Run(ChargenOptions options, Action<string>? onLog = null, Action<int, int>? onProgress = null)
    {
        var report = new ChargenReport
        {
            Applied = options.Apply,
            ScanRoots = options.Paths.ToList(),
            ModFilter = options.ModFilter,
        };

        var popIndex = new NameIndex();
        var bpIndex = new NameIndex();
        var classIndex = new NameIndex();
        var subtypeIndex = new NameIndex();
        var genoIndex = new NameIndex();
        var basePops = new HashSet<string>(StringComparer.Ordinal);
        var findings = new List<ChargenFinding>();
        var applied = new List<ChargenAppliedFix>();

        void Find(ChargenSeverity sev, string kind, string rule, string mod, string file, int line, string msg,
            string pop = "", bool high = false)
        {
            findings.Add(new ChargenFinding
            {
                Severity = sev, Kind = kind, Rule = rule, ModName = mod, File = file, Line = line,
                Message = msg, Population = pop, HighPriority = high
            });
        }

        onLog?.Invoke("Indexing Base / DLC (read-only)...");
        var indexRoots = new List<(string Path, bool IsBase)>();
        if (Directory.Exists(options.BasePath))
            indexRoots.Add((Path.GetFullPath(options.BasePath), true));
        if (!string.IsNullOrWhiteSpace(options.DlcPath) && Directory.Exists(options.DlcPath))
            indexRoots.Add((Path.GetFullPath(options.DlcPath), false));

        foreach (var (root, isBase) in indexRoots)
        {
            foreach (var f in EnumerateXml(root))
            {
                var leaf = Path.GetFileName(f);
                if (IsBlueprintPath(f))
                {
                    IndexBlueprints(f, bpIndex);
                    report.BlueprintFiles++;
                }
                else if (leaf.Equals("PopulationTables.xml", StringComparison.OrdinalIgnoreCase) ||
                         (leaf.Contains("Population", StringComparison.OrdinalIgnoreCase) && leaf.EndsWith(".xml", StringComparison.OrdinalIgnoreCase)))
                {
                    IndexPopulations(f, popIndex, isBase ? basePops : null);
                }
                else if (leaf.Equals("Subtypes.xml", StringComparison.OrdinalIgnoreCase))
                {
                    IndexSubtypes(f, classIndex, subtypeIndex);
                }
                else if (leaf.Equals("Genotypes.xml", StringComparison.OrdinalIgnoreCase))
                {
                    IndexGenotypes(f, genoIndex);
                }
            }
        }

        onLog?.Invoke("Discovering mods...");
        var units = GetModUnits(options.Paths, options.ModFilter);
        onLog?.Invoke($"Mod folders: {units.Count}");

        foreach (var unit in units)
        {
            foreach (var f in EnumerateXml(unit.Root))
            {
                var leaf = Path.GetFileName(f);
                if (IsBlueprintPath(f))
                {
                    IndexBlueprints(f, bpIndex);
                    report.BlueprintFiles++;
                }
                else if (leaf.Equals("PopulationTables.xml", StringComparison.OrdinalIgnoreCase) ||
                         (leaf.Contains("Population", StringComparison.OrdinalIgnoreCase) && leaf.EndsWith(".xml", StringComparison.OrdinalIgnoreCase) && !IsBlueprintPath(f)))
                {
                    IndexPopulations(f, popIndex, null);
                }
                else if (leaf.Equals("Subtypes.xml", StringComparison.OrdinalIgnoreCase))
                    IndexSubtypes(f, classIndex, subtypeIndex);
                else if (leaf.Equals("Genotypes.xml", StringComparison.OrdinalIgnoreCase))
                    IndexGenotypes(f, genoIndex);
            }
        }

        report.PopulationsIndexed = popIndex.Exact.Count;
        report.BlueprintsIndexed = bpIndex.Exact.Count;
        report.SubtypeClassesIndexed = classIndex.Exact.Count;
        report.SubtypesIndexed = subtypeIndex.Exact.Count;
        report.GenotypesIndexed = genoIndex.Exact.Count;
        onLog?.Invoke($"Index: {report.PopulationsIndexed} populations, {report.BlueprintsIndexed} blueprints, {report.SubtypeClassesIndexed} subtype classes, {report.GenotypesIndexed} genotypes");

        if (options.Apply)
        {
            onLog?.Invoke("Applying safe fixes...");
            foreach (var unit in units)
            {
                foreach (var f in GetChargenFiles(unit.Root).Populations)
                    ApplyFixes(f, "Population", options.Backup, applied);
                foreach (var f in GetChargenFiles(unit.Root).Genotypes)
                    ApplyFixes(f, "Genotype", options.Backup, applied);
                foreach (var f in GetChargenFiles(unit.Root).Subtypes)
                    ApplyFixes(f, "Subtype", options.Backup, applied);
            }
        }

        onLog?.Invoke("Validating...");
        var errorPops = new HashSet<string>(StringComparer.Ordinal);
        var done = 0;
        var total = Math.Max(1, units.Count);

        foreach (var unit in units)
        {
            done++;
            onProgress?.Invoke(done, total);
            report.ModsScanned++;
            var files = GetChargenFiles(unit.Root);
            foreach (var f in files.Populations)
            {
                report.PopulationFiles++;
                ValidatePopulation(f, unit.Name, popIndex, bpIndex, basePops, errorPops, Find);
            }
        }

        foreach (var unit in units)
        {
            var files = GetChargenFiles(unit.Root);
            foreach (var f in files.Genotypes)
            {
                report.GenotypeFiles++;
                ValidateGenotype(f, unit.Name, popIndex, bpIndex, classIndex, errorPops, Find);
            }
            foreach (var f in files.Subtypes)
            {
                report.SubtypeFiles++;
                ValidateSubtype(f, unit.Name, unit.Root, popIndex, bpIndex, errorPops, Find);
            }
        }

        report.Findings = findings;
        report.AppliedFixes = applied;

        if (!string.IsNullOrWhiteSpace(options.ReportPath))
        {
            var dir = Path.GetDirectoryName(options.ReportPath);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            File.WriteAllText(options.ReportPath, report.ToMarkdown(), new UTF8Encoding(false));
            onLog?.Invoke("Report: " + options.ReportPath);
        }

        onLog?.Invoke($"Done. Errors={report.ErrorCount} Warns={report.WarnCount} Applied={report.AppliedFixes.Count}");
        return report;
    }

    // ---------- IO helpers ----------

    private static IEnumerable<string> EnumerateXml(string root)
    {
        if (!Directory.Exists(root)) yield break;
        var stack = new Stack<string>();
        stack.Push(root);
        while (stack.Count > 0)
        {
            var dir = stack.Pop();
            IEnumerable<string> subs;
            try { subs = Directory.EnumerateDirectories(dir); }
            catch { continue; }
            foreach (var sub in subs)
            {
                var name = Path.GetFileName(sub);
                if (SkipDirNames.Contains(name, StringComparer.OrdinalIgnoreCase)) continue;
                if (name.StartsWith("_decompile", StringComparison.OrdinalIgnoreCase)) continue;
                stack.Push(sub);
            }
            IEnumerable<string> files;
            try { files = Directory.EnumerateFiles(dir, "*.xml"); }
            catch { continue; }
            foreach (var f in files)
            {
                if (f.EndsWith(".bak", StringComparison.OrdinalIgnoreCase)) continue;
                yield return f;
            }
        }
    }

    private static bool IsBlueprintPath(string path)
    {
        if (path.Contains($"{Path.DirectorySeparatorChar}ObjectBlueprints{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase) ||
            path.Contains("/ObjectBlueprints/", StringComparison.OrdinalIgnoreCase))
            return true;
        var leaf = Path.GetFileName(path);
        return leaf.Equals("ObjectBlueprints.xml", StringComparison.OrdinalIgnoreCase) ||
               leaf.StartsWith("ObjectBlueprints", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsModFolder(string dir)
    {
        foreach (var n in new[] { "manifest.json", "Manifest.json", "manifest.JSON",
                     "PopulationTables.xml", "Genotypes.xml", "Subtypes.xml" })
        {
            if (File.Exists(Path.Combine(dir, n))) return true;
        }
        return false;
    }

    private static List<ModUnit> GetModUnits(IEnumerable<string> roots, string? modFilter)
    {
        var units = new List<ModUnit>();
        foreach (var root in roots)
        {
            if (!Directory.Exists(root)) continue;
            var rootFull = Path.GetFullPath(root);
            if (IsModFolder(rootFull))
            {
                var name = Path.GetFileName(rootFull.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
                if (modFilter != null && !WildcardMatch(name, modFilter)) continue;
                units.Add(new ModUnit { Name = name, Root = rootFull });
                continue;
            }
            foreach (var c in Directory.EnumerateDirectories(rootFull))
            {
                var name = Path.GetFileName(c);
                if (SkipDirNames.Contains(name, StringComparer.OrdinalIgnoreCase)) continue;
                if (modFilter != null && !WildcardMatch(name, modFilter)) continue;
                units.Add(new ModUnit { Name = name, Root = c });
            }
        }
        return units;
    }

    private static bool WildcardMatch(string text, string pattern)
    {
        // simple * wildcard via regex
        var rx = "^" + Regex.Escape(pattern).Replace("\\*", ".*") + "$";
        return Regex.IsMatch(text, rx, RegexOptions.IgnoreCase);
    }

    private sealed class ChargenFiles
    {
        public List<string> Populations { get; } = new();
        public List<string> Genotypes { get; } = new();
        public List<string> Subtypes { get; } = new();
    }

    private static ChargenFiles GetChargenFiles(string modRoot)
    {
        var c = new ChargenFiles();
        foreach (var f in EnumerateXml(modRoot))
        {
            if (IsBlueprintPath(f)) continue;
            var leaf = Path.GetFileName(f);
            if (leaf.Equals("Genotypes.xml", StringComparison.OrdinalIgnoreCase)) c.Genotypes.Add(f);
            else if (leaf.Equals("Subtypes.xml", StringComparison.OrdinalIgnoreCase)) c.Subtypes.Add(f);
            else if (leaf.Equals("PopulationTables.xml", StringComparison.OrdinalIgnoreCase) ||
                     (leaf.Contains("Population", StringComparison.OrdinalIgnoreCase) && leaf.EndsWith(".xml", StringComparison.OrdinalIgnoreCase)))
                c.Populations.Add(f);
        }
        return c;
    }

    private static (byte[] Bytes, int BomLen, string Text) ReadLossless(string path)
    {
        var bytes = File.ReadAllBytes(path);
        var bom = bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF ? 3 : 0;
        var text = Latin1.GetString(bytes, bom, bytes.Length - bom);
        return (bytes, bom, text);
    }

    private static void WriteLossless(string path, byte[] original, int bomLen, string newText)
    {
        var content = Latin1.GetBytes(newText);
        if (bomLen > 0)
        {
            var outBytes = new byte[bomLen + content.Length];
            Buffer.BlockCopy(original, 0, outBytes, 0, bomLen);
            Buffer.BlockCopy(content, 0, outBytes, bomLen, content.Length);
            File.WriteAllBytes(path, outBytes);
        }
        else File.WriteAllBytes(path, content);
    }

    private static string StripComments(string text) =>
        Regex.Replace(text, @"<!--.*?-->", "", RegexOptions.Singleline);

    private static string? Attr(string tagAttrs, string name)
    {
        var m = Regex.Match(tagAttrs, $@"(?i)\b{Regex.Escape(name)}\s*=\s*""([^""]*)""");
        if (m.Success) return m.Groups[1].Value;
        m = Regex.Match(tagAttrs, $@"(?i)\b{Regex.Escape(name)}\s*=\s*'([^']*)'");
        return m.Success ? m.Groups[1].Value : null;
    }

    private static bool HasAttr(string tagAttrs, string name) =>
        Regex.IsMatch(tagAttrs, $@"(?i)\b{Regex.Escape(name)}\s*=");

    private static int LineAt(string text, int index)
    {
        if (index <= 0) return 1;
        var n = 1;
        var end = Math.Min(index, text.Length);
        for (var i = 0; i < end; i++) if (text[i] == '\n') n++;
        return n;
    }

    private static bool IsDynamicTable(string? name)
    {
        if (string.IsNullOrEmpty(name)) return true;
        foreach (var p in DynamicPrefixes)
            if (name.StartsWith(p, StringComparison.OrdinalIgnoreCase)) return true;
        return name.Contains("{zonetier}", StringComparison.OrdinalIgnoreCase) ||
               name.Contains("{ownertier}", StringComparison.OrdinalIgnoreCase);
    }

    private static bool NonPositiveNumber(string? number)
    {
        if (string.IsNullOrWhiteSpace(number)) return false;
        return int.TryParse(number.Trim(), out var n) && n <= 0;
    }

    private static bool HasRootEncoding(string text, string rootName)
    {
        var m = Regex.Match(text, $@"(?is)<\s*{Regex.Escape(rootName)}\b(?<attrs>[^>]*)>");
        if (!m.Success) return true;
        return HasAttr(m.Groups["attrs"].Value, "Encoding");
    }

    // ---------- Index ----------

    private static void IndexPopulations(string file, NameIndex idx, HashSet<string>? basePops)
    {
        var text = ReadLossless(file).Text;
        foreach (Match m in Regex.Matches(text, @"(?is)<\s*population\b([^>]*)>"))
        {
            var name = Attr(m.Groups[1].Value, "Name");
            if (string.IsNullOrEmpty(name)) continue;
            var load = Attr(m.Groups[1].Value, "Load");
            if (string.Equals(load, "Remove", StringComparison.OrdinalIgnoreCase))
            {
                idx.Remove(name);
                basePops?.Remove(name);
                continue;
            }
            idx.Add(name);
            basePops?.Add(name);
        }
    }

    private static void IndexBlueprints(string file, NameIndex idx)
    {
        var text = ReadLossless(file).Text;
        foreach (Match m in Regex.Matches(text, @"(?is)<\s*object\b([^>]*)>"))
        {
            var attrs = m.Groups[1].Value;
            var name = Attr(attrs, "Name");
            if (string.IsNullOrEmpty(name)) continue;
            if (string.Equals(Attr(attrs, "Load"), "Remove", StringComparison.OrdinalIgnoreCase))
                idx.Remove(name);
            else
                idx.Add(name);
        }
    }

    private static void IndexSubtypes(string file, NameIndex classes, NameIndex subtypes)
    {
        var text = ReadLossless(file).Text;
        foreach (Match m in Regex.Matches(text, @"(?is)<\s*class\b([^>]*)>"))
        {
            var id = Attr(m.Groups[1].Value, "ID");
            if (!string.IsNullOrEmpty(id)) classes.Add(id);
        }
        foreach (Match m in Regex.Matches(text, @"(?is)<\s*subtype\b([^>]*)>"))
        {
            var name = Attr(m.Groups[1].Value, "Name");
            if (!string.IsNullOrEmpty(name)) subtypes.Add(name);
        }
    }

    private static void IndexGenotypes(string file, NameIndex idx)
    {
        var text = ReadLossless(file).Text;
        foreach (Match m in Regex.Matches(text, @"(?is)<\s*genotype\b([^>]*)>"))
        {
            var name = Attr(m.Groups[1].Value, "Name");
            if (string.IsNullOrEmpty(name)) continue;
            if (name.StartsWith('-')) idx.Remove(name[1..]);
            else idx.Add(name);
        }
    }

    // ---------- Validate ----------

    private delegate void Finder(ChargenSeverity sev, string kind, string rule, string mod, string file, int line, string msg, string pop = "", bool high = false);

    private static void ValidatePopulation(string file, string mod, NameIndex pops, NameIndex bps,
        HashSet<string> basePops, HashSet<string> errorPops, Finder find)
    {
        var text = ReadLossless(file).Text;
        if (!HasRootEncoding(text, "populations"))
            find(ChargenSeverity.Warn, "Population", "missing-encoding", mod, file, 1,
                "Root <populations> missing Encoding=\"utf-8\"");

        var active = StripComments(text);
        var popMatches = Regex.Matches(active, @"(?is)<\s*population\b([^>]*)>(.*?)</\s*population\s*>");
        if (popMatches.Count == 0 && Regex.IsMatch(active, @"(?i)<\s*population\b"))
        {
            find(ChargenSeverity.Error, "Population", "xml-parse", mod, file, 1,
                "Found <population> tags but could not parse closed population blocks", high: true);
            return;
        }

        var edges = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        foreach (Match pm in popMatches)
        {
            var pattrs = pm.Groups[1].Value;
            var body = pm.Groups[2].Value;
            var popName = Attr(pattrs, "Name");
            var popLine = 1;
            if (!string.IsNullOrEmpty(popName))
            {
                var anchor = Regex.Match(text, $@"(?i)<\s*population\b[^>]*\bName\s*=\s*""{Regex.Escape(popName)}""");
                if (anchor.Success) popLine = LineAt(text, anchor.Index);
            }
            var load = Attr(pattrs, "Load");

            if (string.IsNullOrEmpty(popName))
            {
                find(ChargenSeverity.Error, "Population", "missing-name", mod, file, popLine,
                    "<population> missing required Name", high: true);
                continue;
            }

            if (string.Equals(load, "Replace", StringComparison.OrdinalIgnoreCase) && basePops.Contains(popName))
                find(ChargenSeverity.Warn, "Population", "replace-base", mod, file, popLine,
                    $"Load=\"Replace\" on base population '{popName}' (can wipe worldgen/chargen tables)", popName);

            var groupNames = new HashSet<string>(StringComparer.Ordinal);
            foreach (Match gm in Regex.Matches(body, @"(?is)<\s*group\b([^>]*)>"))
            {
                var gName = Attr(gm.Groups[1].Value, "Name");
                if (string.IsNullOrEmpty(gName))
                {
                    find(ChargenSeverity.Error, "Population", "missing-group-name", mod, file, popLine,
                        $"<population Name=\"{popName}\"> contains <group> without Name", popName, true);
                    continue;
                }
                if (!groupNames.Add(gName))
                {
                    find(ChargenSeverity.Error, "Population", "duplicate-group", mod, file, popLine,
                        $"Duplicate group name '{gName}' inside population '{popName}'", popName, true);
                    errorPops.Add(popName);
                }
            }

            if (popName.StartsWith("StartingGear_", StringComparison.OrdinalIgnoreCase))
            {
                foreach (Match gm in Regex.Matches(body, @"(?is)<\s*group\b([^>]*)>(.*?)</\s*group\s*>"))
                {
                    var style = Attr(gm.Groups[1].Value, "Style");
                    if (string.Equals(style, "pickone", StringComparison.OrdinalIgnoreCase) &&
                        !Regex.IsMatch(gm.Groups[2].Value, @"(?i)<\s*(object|table)\b"))
                    {
                        find(ChargenSeverity.Error, "Population", "empty-pickone-startinggear", mod, file, popLine,
                            $"Empty pickone group in StartingGear population '{popName}'", popName, true);
                        errorPops.Add(popName);
                    }
                }
            }

            if (!Regex.IsMatch(body, @"(?i)<\s*(object|table|group)\b"))
                find(ChargenSeverity.Warn, "Population", "empty-population", mod, file, popLine,
                    $"Population '{popName}' has no object/table/group children", popName);

            var refs = new List<string>();
            foreach (Match tm in Regex.Matches(body, @"(?is)<\s*table\b([^>]*)/?>"))
            {
                var tattrs = tm.Groups[1].Value;
                var tName = Attr(tattrs, "Name");
                var tLoad = Attr(tattrs, "Load");
                var isRemove = string.Equals(tLoad, "Remove", StringComparison.OrdinalIgnoreCase);
                var num = Attr(tattrs, "Number");
                if (string.IsNullOrEmpty(tName))
                {
                    find(ChargenSeverity.Warn, "Population", "table-missing-name", mod, file, popLine,
                        $"<table> missing Name in population '{popName}'", popName);
                    continue;
                }
                if (tName == popName && !isRemove)
                {
                    find(ChargenSeverity.Error, "Population", "self-ref-table", mod, file, popLine,
                        $"Self-referential <table Name=\"{tName}\"/> inside population '{popName}'", popName, true);
                    errorPops.Add(popName);
                }
                else if (!isRemove) refs.Add(tName);

                if (NonPositiveNumber(num))
                    find(ChargenSeverity.Warn, "Population", "nonpositive-number", mod, file, popLine,
                        $"Number=\"{num}\" on table '{tName}' in '{popName}'", popName);

                if (!isRemove && !IsDynamicTable(tName) && !pops.Exact.Contains(tName))
                {
                    var canon = pops.CaseMismatch(tName);
                    if (canon != null)
                        find(ChargenSeverity.Warn, "Population", "table-case-mismatch", mod, file, popLine,
                            $"Table '{tName}' not found; case mismatch with '{canon}'", popName);
                    else
                        find(ChargenSeverity.Warn, "Population", "unknown-table", mod, file, popLine,
                            $"Unknown population table '{tName}' referenced from '{popName}'", popName);
                }
            }

            foreach (Match om in Regex.Matches(body, @"(?is)<\s*object\b([^>]*)/?>"))
            {
                var oattrs = om.Groups[1].Value;
                var bp = Attr(oattrs, "Blueprint");
                var num = Attr(oattrs, "Number");
                if (string.IsNullOrEmpty(bp))
                    find(ChargenSeverity.Warn, "Population", "null-blueprint", mod, file, popLine,
                        $"<object> missing Blueprint in population '{popName}'", popName);
                else if (!bps.Exact.Contains(bp))
                {
                    var canon = bps.CaseMismatch(bp);
                    if (canon != null)
                        find(ChargenSeverity.Warn, "Population", "blueprint-case-mismatch", mod, file, popLine,
                            $"Blueprint '{bp}' not found; case mismatch with '{canon}'", popName);
                    else
                        find(ChargenSeverity.Warn, "Population", "unknown-blueprint", mod, file, popLine,
                            $"Unknown blueprint '{bp}' in population '{popName}'", popName);
                }
                if (NonPositiveNumber(num))
                    find(ChargenSeverity.Warn, "Population", "nonpositive-number", mod, file, popLine,
                        $"Number=\"{num}\" on object '{bp}' in '{popName}'", popName);
            }

            edges[popName] = refs;
        }

        DetectCycles(edges, file, mod, errorPops, find);
    }

    private static void DetectCycles(Dictionary<string, List<string>> edges, string file, string mod,
        HashSet<string> errorPops, Finder find)
    {
        var defined = new HashSet<string>(edges.Keys, StringComparer.Ordinal);
        var state = new Dictionary<string, int>(StringComparer.Ordinal); // 0 unseen 1 stack 2 done
        var path = new List<string>();
        var stack = new Stack<string>();

        foreach (var start in defined)
        {
            if (state.ContainsKey(start)) continue;
            stack.Push(start);
            while (stack.Count > 0)
            {
                var node = stack.Peek();
                if (!state.ContainsKey(node))
                {
                    state[node] = 1;
                    path.Add(node);
                    var pushed = false;
                    if (edges.TryGetValue(node, out var nexts))
                    {
                        foreach (var n in nexts)
                        {
                            if (!defined.Contains(n)) continue;
                            if (state.TryGetValue(n, out var st) && st == 1)
                            {
                                var cycleStart = path.IndexOf(n);
                                if (cycleStart >= 0)
                                {
                                    var cycle = string.Join(" -> ", path.Skip(cycleStart).Append(n));
                                    find(ChargenSeverity.Error, "Population", "table-cycle", mod, file, 1,
                                        $"Population table cycle: {cycle}", n, true);
                                    errorPops.Add(n);
                                }
                            }
                            else if (!state.ContainsKey(n))
                            {
                                stack.Push(n);
                                pushed = true;
                                break;
                            }
                        }
                    }
                    if (pushed) continue;
                }
                if (state.TryGetValue(node, out var cur) && cur == 1)
                {
                    state[node] = 2;
                    if (path.Count > 0 && path[^1] == node) path.RemoveAt(path.Count - 1);
                }
                stack.Pop();
            }
        }
    }

    private static void ValidateGenotype(string file, string mod, NameIndex pops, NameIndex bps,
        NameIndex classes, HashSet<string> errorPops, Finder find)
    {
        var text = ReadLossless(file).Text;
        if (!HasRootEncoding(text, "genotypes"))
            find(ChargenSeverity.Warn, "Genotype", "missing-encoding", mod, file, 1,
                "Root <genotypes> missing Encoding=\"utf-8\"");

        foreach (Match m in Regex.Matches(text, @"(?is)<\s*genotype\b([^>]*)(/?)>"))
        {
            var attrs = m.Groups[1].Value;
            var line = LineAt(text, m.Index);
            var name = Attr(attrs, "Name");
            if (string.IsNullOrEmpty(name))
            {
                find(ChargenSeverity.Error, "Genotype", "missing-name", mod, file, line,
                    "<genotype> missing required Name", high: true);
                continue;
            }
            if (name.StartsWith('-')) continue;

            if (!HasAttr(attrs, "Subtypes"))
                find(ChargenSeverity.Warn, "Genotype", "missing-subtypes-attr", mod, file, line,
                    $"Genotype '{name}' has no Subtypes attribute");
            else
            {
                var subClass = Attr(attrs, "Subtypes");
                if (!string.IsNullOrWhiteSpace(subClass) && !classes.Exact.Contains(subClass!))
                {
                    var canon = classes.CaseMismatch(subClass!);
                    if (canon != null)
                        find(ChargenSeverity.Warn, "Genotype", "subtype-class-case", mod, file, line,
                            $"Genotype '{name}' Subtypes='{subClass}' case-mismatches class '{canon}'");
                    else
                        find(ChargenSeverity.Error, "Genotype", "unknown-subtype-class", mod, file, line,
                            $"Genotype '{name}' Subtypes='{subClass}' — no subtype class ID found", high: true);
                }
            }

            var gear = Attr(attrs, "Gear");
            if (!string.IsNullOrWhiteSpace(gear))
            {
                if (!pops.Exact.Contains(gear!))
                {
                    var canon = pops.CaseMismatch(gear!);
                    if (canon != null)
                        find(ChargenSeverity.Warn, "Genotype", "gear-case-mismatch", mod, file, line,
                            $"Genotype '{name}' Gear='{gear}' case-mismatches population '{canon}'");
                    else
                        find(ChargenSeverity.Error, "Genotype", "missing-gear-population", mod, file, line,
                            $"Genotype '{name}' Gear='{gear}' — population table not found", gear, true);
                }
                else if (errorPops.Contains(gear!))
                    find(ChargenSeverity.Error, "Genotype", "gear-population-broken", mod, file, line,
                        $"Genotype '{name}' Gear='{gear}' points at a population with Error-level issues", gear, true);
            }

            var body = Attr(attrs, "BodyObject");
            if (!string.IsNullOrWhiteSpace(body) && !bps.Exact.Contains(body!))
            {
                var canon = bps.CaseMismatch(body!);
                if (canon != null)
                    find(ChargenSeverity.Warn, "Genotype", "body-case-mismatch", mod, file, line,
                        $"Genotype '{name}' BodyObject='{body}' case-mismatches blueprint '{canon}'");
                else
                    find(ChargenSeverity.Warn, "Genotype", "unknown-bodyobject", mod, file, line,
                        $"Genotype '{name}' BodyObject='{body}' not in blueprint index");
            }

            if (HasAttr(attrs, "Skills"))
                find(ChargenSeverity.Warn, "Genotype", "obsolete-skills-attr", mod, file, line,
                    $"Genotype '{name}' uses obsolete Skills= attribute; prefer <skill> nodes");
            if (HasAttr(attrs, "Reputation"))
                find(ChargenSeverity.Warn, "Genotype", "obsolete-reputation-attr", mod, file, line,
                    $"Genotype '{name}' uses obsolete Reputation= attribute; prefer <reputation> nodes");
        }
    }

    private static void ValidateSubtype(string file, string mod, string modRoot, NameIndex pops, NameIndex bps,
        HashSet<string> errorPops, Finder find)
    {
        var text = ReadLossless(file).Text;
        if (!HasRootEncoding(text, "subtypes"))
            find(ChargenSeverity.Warn, "Subtype", "missing-encoding", mod, file, 1,
                "Root <subtypes> missing Encoding=\"utf-8\"");

        foreach (Match cm in Regex.Matches(text, @"(?is)<\s*class\b([^>]*)>(.*?)</\s*class\s*>"))
        {
            var cattrs = cm.Groups[1].Value;
            var cbody = cm.Groups[2].Value;
            var cLine = LineAt(text, cm.Index);
            var classId = Attr(cattrs, "ID") ?? "(unnamed)";
            if (Attr(cattrs, "ID") == null)
                find(ChargenSeverity.Error, "Subtype", "missing-class-id", mod, file, cLine,
                    "<class> missing required ID", high: true);

            if (HasAttr(cattrs, "DisplayName") && !HasAttr(cattrs, "ChargenTitle"))
                find(ChargenSeverity.Warn, "Subtype", "class-displayname-unused", mod, file, cLine,
                    $"<class ID=\"{classId}\"> has DisplayName without ChargenTitle (UI uses ChargenTitle)");

            if (Regex.Matches(cbody, @"(?is)<\s*subtype\b").Count == 0)
                find(ChargenSeverity.Warn, "Subtype", "empty-class", mod, file, cLine,
                    $"<class ID=\"{classId}\"> has zero <subtype> children (ok if merging into an existing class)");

            foreach (Match sm in Regex.Matches(cbody, @"(?is)<\s*subtype\b([^>]*)(/?)>"))
            {
                var sattrs = sm.Groups[1].Value;
                var sLine = LineAt(text, cm.Groups[2].Index + sm.Index);
                var sName = Attr(sattrs, "Name");
                if (string.IsNullOrEmpty(sName))
                {
                    find(ChargenSeverity.Error, "Subtype", "missing-subtype-name", mod, file, sLine,
                        $"<class ID=\"{classId}\"> contains <subtype> without Name", high: true);
                    continue;
                }

                var gear = Attr(sattrs, "Gear");
                if (!string.IsNullOrWhiteSpace(gear))
                {
                    if (!pops.Exact.Contains(gear!))
                    {
                        var canon = pops.CaseMismatch(gear!);
                        if (canon != null)
                            find(ChargenSeverity.Warn, "Subtype", "gear-case-mismatch", mod, file, sLine,
                                $"Subtype '{sName}' Gear='{gear}' case-mismatches population '{canon}'");
                        else
                            find(ChargenSeverity.Error, "Subtype", "missing-gear-population", mod, file, sLine,
                                $"Subtype '{sName}' Gear='{gear}' — population table not found", gear, true);
                    }
                    else if (errorPops.Contains(gear!))
                        find(ChargenSeverity.Error, "Subtype", "gear-population-broken", mod, file, sLine,
                            $"Subtype '{sName}' Gear='{gear}' points at a population with Error-level issues", gear, true);
                }

                var body = Attr(sattrs, "BodyObject");
                if (!string.IsNullOrWhiteSpace(body) && !bps.Exact.Contains(body!))
                {
                    var canon = bps.CaseMismatch(body!);
                    if (canon != null)
                        find(ChargenSeverity.Warn, "Subtype", "body-case-mismatch", mod, file, sLine,
                            $"Subtype '{sName}' BodyObject='{body}' case-mismatches blueprint '{canon}'");
                    else
                        find(ChargenSeverity.Warn, "Subtype", "unknown-bodyobject", mod, file, sLine,
                            $"Subtype '{sName}' BodyObject='{body}' not in blueprint index");
                }

                if (HasAttr(sattrs, "Foreground"))
                    find(ChargenSeverity.Warn, "Subtype", "unused-foreground", mod, file, sLine,
                        $"Subtype '{sName}' has unused attribute Foreground");
                if (HasAttr(sattrs, "Skills"))
                    find(ChargenSeverity.Warn, "Subtype", "obsolete-skills-attr", mod, file, sLine,
                        $"Subtype '{sName}' uses obsolete Skills= attribute; prefer <skill> nodes");
                if (HasAttr(sattrs, "Reputation"))
                    find(ChargenSeverity.Warn, "Subtype", "obsolete-reputation-attr", mod, file, sLine,
                        $"Subtype '{sName}' uses obsolete Reputation= attribute; prefer <reputation> nodes");
                if (HasAttr(sattrs, "SaveModifierVs"))
                    find(ChargenSeverity.Warn, "Subtype", "obsolete-savemodifier", mod, file, sLine,
                        $"Subtype '{sName}' uses obsolete SaveModifierVs attribute");

                var tile = Attr(sattrs, "Tile");
                if (!string.IsNullOrWhiteSpace(tile) && Regex.IsMatch(tile!, @"[/\\.]"))
                {
                    var norm = tile!.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
                    var found = File.Exists(Path.Combine(modRoot, norm)) ||
                                File.Exists(Path.Combine(Path.GetDirectoryName(file) ?? "", norm));
                    if (!found)
                        find(ChargenSeverity.Warn, "Subtype", "missing-tile-file", mod, file, sLine,
                            $"Subtype '{sName}' Tile='{tile}' — file not found under mod");
                }
            }
        }
    }

    // ---------- Apply ----------

    private static void ApplyFixes(string file, string kind, bool backup, List<ChargenAppliedFix> applied)
    {
        var (bytes, bom, text) = ReadLossless(file);
        var original = text;
        var notes = new List<string>();

        var root = kind switch
        {
            "Population" => "populations",
            "Genotype" => "genotypes",
            "Subtype" => "subtypes",
            _ => null
        };
        if (root != null)
        {
            var withEnc = TryInsertEncoding(text, root);
            if (withEnc != null)
            {
                text = withEnc;
                notes.Add($"Inserted Encoding=\"utf-8\" on <{root}>");
            }
        }

        if (kind == "Population")
            text = ApplyPopulationStructural(text, notes);
        if (kind == "Genotype")
        {
            var (genoFixed, genoFixes) = GenotypesXmlFixer.Fix(text);
            text = genoFixed;
            foreach (var f in genoFixes)
                notes.Add($"{f.RuleName} ×{f.Count}");
        }
        if (kind == "Subtype")
        {
            var (subFixed, subFixes) = SubtypesXmlFixer.Fix(text);
            text = subFixed;
            foreach (var f in subFixes)
                notes.Add($"{f.RuleName} ×{f.Count}");
        }

        if (text == original) return;
        if (backup)
        {
            try { File.Copy(file, file + ".bak", overwrite: true); } catch { /* ignore */ }
        }
        WriteLossless(file, bytes, bom, text);
        if (notes.Count == 0) notes.Add("Applied structural fixes");
        foreach (var n in notes)
            applied.Add(new ChargenAppliedFix { File = file, Note = n });
    }

    private static string? TryInsertEncoding(string text, string rootName)
    {
        var rx = new Regex($@"(?is)(?<prefix>^\s*(<\?xml[^>]*\?>\s*)?((<!--.*?-->|\s)*)?)<(?<name>{Regex.Escape(rootName)})(?<attrs>(?:\s+[\w:.\-]+\s*=\s*""[^""]*"")*)\s*(?<selfclose>/?)>");
        var m = rx.Match(text);
        if (!m.Success) return null;
        if (HasAttr(m.Groups["attrs"].Value, "Encoding")) return null;
        var newTag = $"<{m.Groups["name"].Value} Encoding=\"utf-8\"{m.Groups["attrs"].Value}{m.Groups["selfclose"].Value}>";
        return text[..m.Index] + newTag + text[(m.Index + m.Length)..];
    }

    private static string ApplyPopulationStructural(string text, List<string> notes)
    {
        var rx = new Regex(@"(?is)<\s*population\b([^>]*)>(.*?)</\s*population\s*>");
        var matches = rx.Matches(text);
        if (matches.Count == 0) return text;

        var sb = new StringBuilder();
        var last = 0;
        var removedSelf = 0;
        var renamedGroups = 0;

        foreach (Match pm in matches)
        {
            sb.Append(text, last, pm.Index - last);
            var pattrs = pm.Groups[1].Value;
            var body = pm.Groups[2].Value;
            var popName = Attr(pattrs, "Name");
            var openLen = pm.Groups[2].Index - pm.Index;
            var open = text.Substring(pm.Index, openLen);
            var close = pm.Value[(openLen + body.Length)..];

            if (!string.IsNullOrEmpty(popName))
            {
                var tableRx = new Regex(@"(?is)(\s*)<\s*table\b([^>]*)/\s*>");
                var bodySb = new StringBuilder();
                var tLast = 0;
                foreach (Match tm in tableRx.Matches(body))
                {
                    bodySb.Append(body, tLast, tm.Index - tLast);
                    var tName = Attr(tm.Groups[2].Value, "Name");
                    var tLoad = Attr(tm.Groups[2].Value, "Load");
                    var isRemove = string.Equals(tLoad, "Remove", StringComparison.OrdinalIgnoreCase);
                    if (tName == popName && !isRemove)
                    {
                        removedSelf++;
                        bodySb.Append(tm.Groups[1].Value);
                        bodySb.Append($"<!-- removed self-ref population table: {popName} -->");
                    }
                    else bodySb.Append(tm.Value);
                    tLast = tm.Index + tm.Length;
                }
                bodySb.Append(body, tLast, body.Length - tLast);
                body = bodySb.ToString();

                var seen = new Dictionary<string, int>(StringComparer.Ordinal);
                var groupRx = new Regex(@"(?is)<\s*group\b([^>]*)>");
                bodySb = new StringBuilder();
                var gLast = 0;
                foreach (Match gm in groupRx.Matches(body))
                {
                    bodySb.Append(body, gLast, gm.Index - gLast);
                    var gattrs = gm.Groups[1].Value;
                    var gName = Attr(gattrs, "Name");
                    if (!string.IsNullOrEmpty(gName) && seen.ContainsKey(gName))
                    {
                        seen[gName]++;
                        var newName = $"{gName}_dup{seen[gName]}";
                        renamedGroups++;
                        var newAttrs = Regex.Replace(gattrs, @"(?i)\bName\s*=\s*""[^""]*""", $"Name=\"{newName}\"");
                        bodySb.Append("<group").Append(newAttrs).Append('>');
                    }
                    else
                    {
                        if (!string.IsNullOrEmpty(gName)) seen[gName!] = 0;
                        bodySb.Append(gm.Value);
                    }
                    gLast = gm.Index + gm.Length;
                }
                bodySb.Append(body, gLast, body.Length - gLast);
                body = bodySb.ToString();
            }

            sb.Append(open).Append(body).Append(close);
            last = pm.Index + pm.Length;
        }
        sb.Append(text, last, text.Length - last);
        if (removedSelf > 0) notes.Add($"Removed {removedSelf} self-ref <table> node(s)");
        if (renamedGroups > 0) notes.Add($"Renamed {renamedGroups} duplicate group Name(s) with _dupN suffix");
        return sb.ToString();
    }

    private static string ApplySubtypeClassTitle(string text, List<string> notes)
    {
        var rx = new Regex(@"(?is)<\s*class\b([^>]*)>");
        var matches = rx.Matches(text);
        if (matches.Count == 0) return text;
        var sb = new StringBuilder();
        var last = 0;
        var n = 0;
        foreach (Match m in matches)
        {
            sb.Append(text, last, m.Index - last);
            var attrs = m.Groups[1].Value;
            if (HasAttr(attrs, "DisplayName") && !HasAttr(attrs, "ChargenTitle"))
            {
                n++;
                var newAttrs = Regex.Replace(attrs, @"(?i)\bDisplayName\s*=", "ChargenTitle=");
                sb.Append("<class").Append(newAttrs).Append('>');
            }
            else sb.Append(m.Value);
            last = m.Index + m.Length;
        }
        sb.Append(text, last, text.Length - last);
        if (n > 0) notes.Add($"Renamed {n} class DisplayName= to ChargenTitle=");
        return sb.ToString();
    }
}
