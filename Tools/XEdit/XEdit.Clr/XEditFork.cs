using System.Text.Json;
using System.Text.Json.Serialization;

namespace XEdit.Clr;

/// <summary>Pinned TES5Edit fork used for Starfield record definitions.</summary>
public sealed class XEditFork
{
    [JsonPropertyName("repo")] public string Repo { get; set; } = "https://github.com/TES5Edit/TES5Edit.git";
    [JsonPropertyName("branch")] public string Branch { get; set; } = "dev-4.1.6";
    [JsonPropertyName("commit")] public string? Commit { get; set; }
    [JsonPropertyName("minVersion")] public string MinVersion { get; set; } = "4.1.5q";
    [JsonPropertyName("definitions")] public string Definitions { get; set; } = "Core/wbDefinitionsSF1.pas";
    [JsonPropertyName("reflection")] public string Reflection { get; set; } = "Core/wbDefinitionsReflection.pas";
    [JsonPropertyName("nexus")] public string? Nexus { get; set; }
    [JsonPropertyName("notes")] public string? Notes { get; set; }

    public string LocalCommit { get; set; } = "";
    public string DefinitionsPath { get; set; } = "";
    public bool SourcePresent { get; set; }

    public static XEditFork Load()
    {
        var fork = new XEditFork();
        if (File.Exists(XEditPaths.ForkManifest))
        {
            try
            {
                fork = JsonSerializer.Deserialize<XEditFork>(File.ReadAllText(XEditPaths.ForkManifest)) ?? fork;
            }
            catch
            {
                // keep defaults
            }
        }

        fork.DefinitionsPath = Path.Combine(XEditPaths.Tes5EditDir, fork.Definitions.Replace('/', Path.DirectorySeparatorChar));
        fork.SourcePresent = File.Exists(fork.DefinitionsPath);
        fork.LocalCommit = ReadGitHead(XEditPaths.Tes5EditDir);
        return fork;
    }

    static string ReadGitHead(string repo)
    {
        try
        {
            var head = Path.Combine(repo, ".git", "HEAD");
            if (!File.Exists(head)) return "";
            var text = File.ReadAllText(head).Trim();
            if (text.StartsWith("ref:", StringComparison.OrdinalIgnoreCase))
            {
                var refPath = Path.Combine(repo, ".git", text[4..].Trim().Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(refPath))
                    return File.ReadAllText(refPath).Trim();
            }
            return text;
        }
        catch
        {
            return "";
        }
    }
}
