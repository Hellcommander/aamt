using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Migrates <c>GenerateFriendOrFoe.hateReasons.Add("…")</c> /
/// <c>likeReasons.Add("…")</c> (and HEB variants) into mod
/// <c>HistorySpice.json</c> under <c>spice.friendOrFoe.default</c>, then strips
/// the obsolete C# Add / ??= init lines. Mod-scoped (may create a new JSON file).
/// </summary>
public static class FriendOrFoeSpiceFixer
{
    public const string FixRuleName =
        "GenerateFriendOrFoe hate/likeReasons → HistorySpice.json";

    static readonly Regex AddCall = new(
        @"GenerateFriendOrFoe(?:_HEB)?\.(?<list>hateReasons|likeReasons)\s*\.\s*Add\s*\(\s*""(?<text>(?:[^""\\]|\\.)*)""\s*\)\s*;",
        RegexOptions.Compiled);

    static readonly Regex InitLine = new(
        @"^[ \t]*GenerateFriendOrFoe(?:_HEB)?\.(?:hateReasons|likeReasons)\s*\?\?=.*$",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public sealed class ModFixResult
    {
        public Dictionary<string, string> UpdatedContents { get; } = new(StringComparer.OrdinalIgnoreCase);
        public List<(string File, AppliedFix Fix)> Fixes { get; } = new();
        /// <summary>Path → content for new or updated HistorySpice.json.</summary>
        public Dictionary<string, string> SpiceFiles { get; } = new(StringComparer.OrdinalIgnoreCase);
        public List<string> Errors { get; } = new();
    }

    public static ModFixResult FixMod(string modRoot, IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new ModFixResult();
        if (string.IsNullOrEmpty(modRoot) || pathToContent == null || pathToContent.Count == 0)
            return result;

        var hate = new List<string>();
        var like = new List<string>();
        var seenHate = new HashSet<string>(StringComparer.Ordinal);
        var seenLike = new HashSet<string>(StringComparer.Ordinal);

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("GenerateFriendOrFoe", StringComparison.Ordinal) < 0)
                continue;

            foreach (Match m in AddCall.Matches(content))
            {
                if (HitFilter.IsInsideComment(content, m.Index))
                    continue;
                var text = Unescape(m.Groups["text"].Value).Trim();
                if (string.IsNullOrEmpty(text))
                    continue;
                if (m.Groups["list"].Value == "hateReasons")
                {
                    if (seenHate.Add(text)) hate.Add(text);
                }
                else if (seenLike.Add(text))
                {
                    like.Add(text);
                }
            }
        }

        if (hate.Count == 0 && like.Count == 0)
            return result;

        var spicePath = Path.Combine(modRoot, "HistorySpice.json");
        if (!TryMergeSpice(spicePath, hate, like, out var spiceContent, out var spiceError))
        {
            result.Errors.Add(spiceError ?? "HistorySpice.json merge aborted.");
            return result;
        }
        result.SpiceFiles[spicePath] = spiceContent;

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("GenerateFriendOrFoe", StringComparison.Ordinal) < 0)
                continue;

            var removed = 0;
            var next = AddCall.Replace(content, m =>
            {
                if (HitFilter.IsInsideComment(content, m.Index))
                    return m.Value;
                removed++;
                return "";
            });
            next = InitLine.Replace(next, m =>
            {
                removed++;
                return "";
            });
            // Collapse blank runs left by removals inside methods
            next = Regex.Replace(next, @"(\r?\n)[ \t]*(\r?\n){2,}", "$1$1");

            if (removed == 0 || next == content)
                continue;

            result.UpdatedContents[path] = next;
            result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleName, Count = removed }));
        }

        if (result.SpiceFiles.Count > 0)
        {
            result.Fixes.Add((spicePath, new AppliedFix
            {
                RuleName = FixRuleName + " (write HistorySpice.json)",
                Count = hate.Count + like.Count,
            }));
        }

        return result;
    }

    static bool TryMergeSpice(string spicePath, List<string> hate, List<string> like,
        out string content, out string? error)
    {
        content = "";
        error = null;
        JsonObject root;
        if (File.Exists(spicePath))
        {
            try
            {
                var parsed = JsonNode.Parse(File.ReadAllText(spicePath));
                if (parsed is not JsonObject obj)
                {
                    error = "HistorySpice.json root is not a JSON object; aborting FriendOrFoe spice merge (C# Adds left in place).";
                    return false;
                }
                root = obj;
            }
            catch (Exception ex)
            {
                error = "Could not parse HistorySpice.json (" + ex.Message +
                        "); aborting FriendOrFoe spice merge (C# Adds left in place).";
                return false;
            }
        }
        else
        {
            root = new JsonObject();
        }

        if (root["lang"] is null)
            root["lang"] = "en";

        var spice = root["spice"] as JsonObject ?? new JsonObject();
        root["spice"] = spice;
        var fof = spice["friendOrFoe"] as JsonObject ?? new JsonObject();
        spice["friendOrFoe"] = fof;
        var def = fof["default"] as JsonObject ?? new JsonObject();
        fof["default"] = def;

        AppendUnique(def, "hateReasons", hate);
        AppendUnique(def, "likeReasons", like);

        // Avoid JsonSerializerOptions TypeInfoResolver issues under trimmed/AOT hosts.
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
        {
            root.WriteTo(writer);
        }
        content = Encoding.UTF8.GetString(stream.ToArray()) + "\n";
        return true;
    }

    static void AppendUnique(JsonObject parent, string key, List<string> values)
    {
        var arr = parent[key] as JsonArray ?? new JsonArray();
        parent[key] = arr;
        var existing = new HashSet<string>(StringComparer.Ordinal);
        foreach (var n in arr)
        {
            if (n is JsonValue v && v.TryGetValue<string>(out var s) && s is not null)
                existing.Add(s);
        }
        foreach (var s in values)
        {
            if (existing.Add(s))
                arr.Add(s);
        }
    }

    static string Unescape(string s)
    {
        var sb = new StringBuilder(s.Length);
        for (var i = 0; i < s.Length; i++)
        {
            if (s[i] == '\\' && i + 1 < s.Length)
            {
                sb.Append(s[i + 1]);
                i++;
            }
            else sb.Append(s[i]);
        }
        return sb.ToString();
    }
}
