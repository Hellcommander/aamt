namespace ApiMigrator.Core;

/// <summary>
/// Result of a mod-scoped fixer that rewrites .cs files and may create/update a sidecar XML/JSON file.
/// </summary>
public sealed class SidecarModFixResult
{
    public Dictionary<string, string> UpdatedContents { get; } = new(StringComparer.OrdinalIgnoreCase);
    public List<(string File, AppliedFix Fix)> Fixes { get; } = new();
    public Dictionary<string, string> SidecarFiles { get; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> Warnings { get; } = new();
}
