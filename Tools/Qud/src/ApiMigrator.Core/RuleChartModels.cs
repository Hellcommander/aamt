using System.Text.Json.Serialization;

namespace ApiMigrator.Core;

/// <summary>manifest.json — ordered list of chart files under data/charts/.</summary>
public sealed class RuleChartManifest
{
    [JsonPropertyName("description")] public string? Description { get; set; }
    [JsonPropertyName("files")] public List<string> Files { get; set; } = new();
}

/// <summary>JSON twin of a RuleChart XML pack (same fields).</summary>
public sealed class RuleChartFile
{
    [JsonPropertyName("gameFileVersion")] public string? GameFileVersion { get; set; }
    [JsonPropertyName("steamBetaKey")] public string? SteamBetaKey { get; set; }
    [JsonPropertyName("category")] public string? Category { get; set; }
    [JsonPropertyName("description")] public string? Description { get; set; }
    [JsonPropertyName("notes")] public List<RuleChartNote>? Notes { get; set; }
    [JsonPropertyName("rules")] public List<RuleChartRule>? Rules { get; set; }
    [JsonPropertyName("postEnsureUsings")] public List<RuleChartPostEnsureUsing>? PostEnsureUsings { get; set; }
}

public sealed class RuleChartNote
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("text")] public string Text { get; set; } = "";
}

public sealed class RuleChartRule
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("pattern")] public string Pattern { get; set; } = "";
    [JsonPropertyName("replacement")] public string Replacement { get; set; } = "";
    [JsonPropertyName("dumpMember")] public string? DumpMember { get; set; }
    [JsonPropertyName("note")] public string? Note { get; set; }
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;
    [JsonPropertyName("ensureUsings")] public List<string>? EnsureUsings { get; set; }
    [JsonPropertyName("requiresSubstring")] public string? RequiresSubstring { get; set; }
    /// <summary>Stable merge order from export (lower first).</summary>
    [JsonPropertyName("order")] public int? Order { get; set; }
}

public sealed class RuleChartPostEnsureUsing
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("ifPattern")] public string IfPattern { get; set; } = "";
    [JsonPropertyName("usings")] public List<string> Usings { get; set; } = new();
}
