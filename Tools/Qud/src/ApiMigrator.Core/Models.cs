using System.Text.Json.Serialization;

namespace ApiMigrator.Core;

public sealed class ObsoleteEntry
{
    [JsonPropertyName("type")] public string Type { get; set; } = "";
    [JsonPropertyName("member")] public string Member { get; set; } = "";
    [JsonPropertyName("kind")] public string Kind { get; set; } = "";
    [JsonPropertyName("signature")] public string Signature { get; set; } = "";
    [JsonPropertyName("obsoleteMessage")] public string ObsoleteMessage { get; set; } = "";
    [JsonPropertyName("searchPattern")] public string SearchPattern { get; set; } = "";
    [JsonPropertyName("needsManual")] public bool NeedsManual { get; set; }
    [JsonPropertyName("autoFixable")] public bool AutoFixable { get; set; }
    [JsonPropertyName("replacement")] public string? Replacement { get; set; }
    [JsonPropertyName("notes")] public string? Notes { get; set; }

    public string FullName => $"{Type}.{Member}";
}

public sealed class ObsoleteDumpMeta
{
    [JsonPropertyName("description")] public string? Description { get; set; }
    [JsonPropertyName("source")] public string? Source { get; set; }
    [JsonPropertyName("assemblySource")] public string? AssemblySource { get; set; }
    [JsonPropertyName("apiDumpTool")] public string? ApiDumpTool { get; set; }
    [JsonPropertyName("capturedDate")] public string? CapturedDate { get; set; }
    /// <summary>Assembly-CSharp FileVersion this dump was refreshed against (e.g. 2.0.212.29).</summary>
    [JsonPropertyName("gameFileVersion")] public string? GameFileVersion { get; set; }
    /// <summary>Steam beta key when known (e.g. lang-experimental, public, beta).</summary>
    [JsonPropertyName("steamBetaKey")] public string? SteamBetaKey { get; set; }
    [JsonPropertyName("steamBuildId")] public string? SteamBuildId { get; set; }
    [JsonPropertyName("notes")] public string? Notes { get; set; }
}

public sealed class ObsoleteDump
{
    [JsonPropertyName("_meta")] public ObsoleteDumpMeta? Meta { get; set; }
    [JsonPropertyName("entries")] public List<ObsoleteEntry> Entries { get; set; } = new();
}

public sealed class CuratedRule
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("pattern")] public string Pattern { get; set; } = "";
    [JsonPropertyName("replacement")] public string Replacement { get; set; } = "";
    [JsonPropertyName("dumpMember")] public string? DumpMember { get; set; }
    [JsonPropertyName("note")] public string? Note { get; set; }
    /// <summary>
    /// When false, the rule is skipped by RuleEngine / Update-ObsoleteApis.ps1 (kept for history).
    /// Omit or true = active. Use to disable reverse-risk / over-match autofixes without deleting.
    /// </summary>
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;
    /// <summary>
    /// Namespaces to ensure as <c>using X;</c> in .cs files whenever this rule fires.
    /// </summary>
    [JsonPropertyName("ensureUsings")] public List<string>? EnsureUsings { get; set; }
    /// <summary>
    /// Cheap gate: skip compiling/running this rule's regex unless the file contains this
    /// substring (Ordinal). Use for expensive multi-line / backref patterns.
    /// </summary>
    [JsonPropertyName("requiresSubstring")] public string? RequiresSubstring { get; set; }
}

/// <summary>
/// File-wide using hygiene: if <see cref="IfPattern"/> matches post-rewrite content, ensure
/// each entry in <see cref="Usings"/> is present. Heals leftovers from earlier migrator runs
/// that rewrote call sites without importing the new type's namespace.
/// </summary>
public sealed class PostEnsureUsing
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("ifPattern")] public string IfPattern { get; set; } = "";
    [JsonPropertyName("usings")] public List<string> Usings { get; set; } = new();
}

public sealed class CuratedRulesFileMeta
{
    [JsonPropertyName("description")] public string? Description { get; set; }
    /// <summary>Assembly-CSharp FileVersion this ruleset targets (e.g. 2.0.212.29).</summary>
    [JsonPropertyName("gameFileVersion")] public string? GameFileVersion { get; set; }
    [JsonPropertyName("steamBetaKey")] public string? SteamBetaKey { get; set; }
    [JsonPropertyName("steamBuildId")] public string? SteamBuildId { get; set; }
    [JsonPropertyName("capturedDate")] public string? CapturedDate { get; set; }
    [JsonPropertyName("notes")] public string? Notes { get; set; }
}

public sealed class CuratedRulesFile
{
    [JsonPropertyName("_meta")] public CuratedRulesFileMeta? Meta { get; set; }
    [JsonPropertyName("rules")] public List<CuratedRule> Rules { get; set; } = new();
    [JsonPropertyName("postEnsureUsings")] public List<PostEnsureUsing>? PostEnsureUsings { get; set; }
}

public sealed class AppliedFix
{
    public string RuleName { get; set; } = "";
    public int Count { get; set; }
}

public sealed class RemainingHit
{
    public int Line { get; set; }
    public string Member { get; set; } = "";
    public string Message { get; set; } = "";
    /// <summary>Actionable manual-fix guidance (never suggests adding [Obsolete]).</summary>
    public string Advice { get; set; } = "";
    public bool NeedsManual { get; set; }
    public string Text { get; set; } = "";
}

public sealed class FileScanResult
{
    public string FilePath { get; set; } = "";
    public bool Changed { get; set; }
    public List<AppliedFix> AppliedFixes { get; set; } = new();
    public List<RemainingHit> RemainingHits { get; set; } = new();
    public string? NewContent { get; set; }
}

public sealed class MigrationOptions
{
    public List<string> Paths { get; set; } = new();
    public string? ModFilter { get; set; }
    public bool Apply { get; set; }
    public bool Backup { get; set; } = true;
    public List<string> ExcludeDirs { get; set; } = new() { "_tools", "bin", "obj", ".git", ".vs", "_decompile", "_decompile_il", "scratch", "_reports" };
    public List<string> Extensions { get; set; } = new() { ".cs", ".xml" };
    public string DumpPath { get; set; } = "";
    public string RulesPath { get; set; } = "";
}

public sealed class MigrationReport
{
    public bool Applied { get; set; }
    public DateTime GeneratedAt { get; set; } = DateTime.Now;
    public string DumpPath { get; set; } = "";
    public string RulesPath { get; set; } = "";
    public List<string> ScanRoots { get; set; } = new();
    public string? ModFilter { get; set; }
    public int FilesScanned { get; set; }
    public List<FileScanResult> FileResults { get; set; } = new();
    public int TotalAutoFixes => FileResults.Sum(f => f.AppliedFixes.Sum(a => a.Count));
    public int TotalRemainingHits => FileResults.Sum(f => f.RemainingHits.Count);
}

public sealed class DiscoveredMember
{
    public string Type { get; set; } = "";
    public string Member { get; set; } = "";
    public string Kind { get; set; } = "";
    public string Signature { get; set; } = "";
    public string ObsoleteMessage { get; set; } = "";
    public bool IsError { get; set; }
}

public sealed class DumpDiffResult
{
    public List<DiscoveredMember> Added { get; set; } = new();
    public List<ObsoleteEntry> Removed { get; set; } = new();
    public List<(ObsoleteEntry Old, DiscoveredMember New)> MessageChanged { get; set; } = new();
    public int UnchangedCount { get; set; }
}
