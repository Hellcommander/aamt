using System.Text.Json;
using System.Text.RegularExpressions;

namespace QudLab.Ai;

public sealed record CodePatch(string Path, string Content);

public static class CodePatchParser
{
    public static IReadOnlyList<CodePatch> Parse(string text)
    {
        var patches = new List<CodePatch>();
        if (string.IsNullOrWhiteSpace(text))
            return patches;

        TryJson(text, patches);
        if (patches.Count > 0)
            return Dedup(patches);

        TryFences(text, patches);
        TryFileHeaders(text, patches);
        return Dedup(patches);
    }

    static void TryJson(string text, List<CodePatch> dest)
    {
        var json = ExtractJsonObject(text);
        if (json is null)
            return;
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (root.TryGetProperty("files", out var files) && files.ValueKind == JsonValueKind.Array)
            {
                foreach (var f in files.EnumerateArray())
                    Add(dest, GetStr(f, "path") ?? GetStr(f, "file"), GetStr(f, "content") ?? GetStr(f, "source"));
            }
            else if (root.TryGetProperty("path", out _) && root.TryGetProperty("content", out _))
            {
                Add(dest, GetStr(root, "path"), GetStr(root, "content"));
            }
        }
        catch
        {
            // not JSON — ignore
        }
    }

    static void TryFences(string text, List<CodePatch> dest)
    {
        var rx = new Regex(
            @"```(?:csharp|cs|xml|json)?[ \t]*([^\r\n`]*)\r?\n([\s\S]*?)```",
            RegexOptions.IgnoreCase);
        foreach (Match m in rx.Matches(text))
        {
            var header = m.Groups[1].Value.Trim().Trim('"');
            var body = m.Groups[2].Value.Trim();
            if (string.IsNullOrWhiteSpace(body))
                continue;
            if (header.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) ||
                header.EndsWith(".xml", StringComparison.OrdinalIgnoreCase))
                Add(dest, header, body);
        }
    }

    static void TryFileHeaders(string text, List<CodePatch> dest)
    {
        var rx = new Regex(
            @"^FILE:\s*(\S+)\s*\r?\n```(?:csharp|cs|xml)?\r?\n([\s\S]*?)```",
            RegexOptions.Multiline | RegexOptions.IgnoreCase);
        foreach (Match m in rx.Matches(text))
            Add(dest, m.Groups[1].Value, m.Groups[2].Value.Trim());
    }

    static void Add(List<CodePatch> dest, string? path, string? content)
    {
        var rel = NormalizeRelPath(path);
        if (rel is null || string.IsNullOrEmpty(content))
            return;
        dest.Add(new CodePatch(rel, content.Replace("\r\n", "\n")));
    }

    public static string? NormalizeRelPath(string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
            return null;
        var p = path.Replace('\\', '/').Trim().Trim('"');
        while (p.StartsWith("./", StringComparison.Ordinal))
            p = p[2..];
        p = p.TrimStart('/');
        const string prefix = "Workspace/src/";
        if (p.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            p = p[prefix.Length..];
        if (p.StartsWith("src/", StringComparison.OrdinalIgnoreCase) && p.Count(c => c == '/') == 1)
            p = p[4..];
        if (p.Contains("..", StringComparison.Ordinal) || p.Contains(':'))
            return null;
        if (!(p.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) ||
              p.EndsWith(".xml", StringComparison.OrdinalIgnoreCase)))
            return null;
        return p;
    }

    static string? ExtractJsonObject(string text)
    {
        var start = text.IndexOf('{');
        var end = text.LastIndexOf('}');
        if (start < 0 || end <= start)
            return null;
        return text[start..(end + 1)];
    }

    static string? GetStr(JsonElement el, string name) =>
        el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() : null;

    static List<CodePatch> Dedup(List<CodePatch> patches)
    {
        var map = new Dictionary<string, CodePatch>(StringComparer.OrdinalIgnoreCase);
        foreach (var p in patches)
            map[p.Path] = p;
        return map.Values.ToList();
    }
}
