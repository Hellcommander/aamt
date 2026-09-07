using System.Text.Json;
using System.Text.Json.Serialization;

namespace XEdit.Clr;

public sealed class XEditJob
{
    [JsonPropertyName("op")] public string Op { get; set; } = "";
    [JsonPropertyName("game")] public string Game { get; set; } = "SF1";
    [JsonPropertyName("plugin")] public string? Plugin { get; set; }
    [JsonPropertyName("plugins")] public List<string>? Plugins { get; set; }
    [JsonPropertyName("targetPlugin")] public string? TargetPlugin { get; set; }
    [JsonPropertyName("signature")] public string? Signature { get; set; }
    [JsonPropertyName("edid")] public string? EditorId { get; set; }
    [JsonPropertyName("formid")] public string? FormId { get; set; }
    [JsonPropertyName("path")] public string? Path { get; set; }
    [JsonPropertyName("value")] public string? Value { get; set; }
    [JsonPropertyName("query")] public string? Query { get; set; }
    [JsonPropertyName("limit")] public int Limit { get; set; } = 100;
    [JsonPropertyName("maxDepth")] public int MaxDepth { get; set; } = 8;
    [JsonPropertyName("save")] public bool Save { get; set; }
    [JsonPropertyName("editMasters")] public bool EditMasters { get; set; }
    [JsonPropertyName("sets")] public List<XEditSet>? Sets { get; set; }

    [JsonIgnore] public XEditGame GameMode =>
        Enum.TryParse<XEditGame>(Game, ignoreCase: true, out var g) ? g : XEditGame.SF1;

    public string ToJson() => JsonSerializer.Serialize(this, JsonOptions.Indented);

    public static XEditJob Parse(string json) =>
        JsonSerializer.Deserialize<XEditJob>(json, JsonOptions.Indented) ?? new XEditJob();
}

public sealed class XEditSet
{
    [JsonPropertyName("edid")] public string? EditorId { get; set; }
    [JsonPropertyName("formid")] public string? FormId { get; set; }
    [JsonPropertyName("signature")] public string? Signature { get; set; }
    [JsonPropertyName("path")] public string? Path { get; set; }
    [JsonPropertyName("value")] public string? Value { get; set; }
}

public sealed class XEditResult
{
    [JsonPropertyName("ok")] public bool Ok { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("warning")] public string? Warning { get; set; }
    [JsonPropertyName("op")] public string? Op { get; set; }
    [JsonPropertyName("fork")] public object? Fork { get; set; }
    [JsonPropertyName("xedit")] public object? XEdit { get; set; }
    [JsonPropertyName("data")] public JsonElement? Data { get; set; }
    [JsonPropertyName("log")] public string? Log { get; set; }

    public static XEditResult Fail(string error) => new() { Ok = false, Error = error };

    public string ToJson() => JsonSerializer.Serialize(this, JsonOptions.Indented);
}

public static class JsonOptions
{
    public static readonly JsonSerializerOptions Indented = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };
}
