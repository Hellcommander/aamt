using System.Text;
using System.Text.RegularExpressions;
using QudLab.Assistant;
using QudLab.Core.Cache;

namespace QudLab.Ai;

public sealed class AiContextBuilder
{
    public string Build(
        IntelligenceCache? cache,
        string task,
        string userPrompt,
        IReadOnlyList<SearchHit>? hits = null,
        string? systemExtra = null,
        IReadOnlyList<(string path, string text)>? files = null,
        IReadOnlyList<string>? diagnostics = null,
        IReadOnlyList<string>? timeline = null,
        int maxChars = 12000)
    {
        var sb = new StringBuilder();
        sb.AppendLine("You are the Qud Lab local coding agent. Use ONLY provided game metadata and workspace files.");
        sb.AppendLine("Never invent XRL type names. Prefer FullName values from the type graph / search hits.");
        sb.AppendLine("If unsure, say which tool (/type, /search, read_file, compile, simulate) to run next.");
        sb.AppendLine("ThreadingAPI is a separate WIP mod — do not assume it exists.");
        sb.AppendLine($"Task: {task}");
        if (!string.IsNullOrWhiteSpace(systemExtra))
        {
            sb.AppendLine();
            sb.AppendLine(systemExtra.Trim());
        }

        sb.AppendLine();

        if (cache is not null)
        {
            sb.AppendLine($"GameRoot: {cache.GameRoot}");
            sb.AppendLine($"Schema: {cache.SchemaVersion}");
            sb.AppendLine($"Types: {cache.TypeGraph.Types.Count}; Blueprints: {cache.BlueprintGraph.Objects.Count}; Mutations: {cache.MutationGraph.Mutations.Count}");
            sb.AppendLine();
        }

        if (diagnostics is { Count: > 0 })
        {
            sb.AppendLine("Compile diagnostics:");
            foreach (var d in diagnostics.Take(40))
                sb.AppendLine("- " + d);
            sb.AppendLine();
        }

        if (timeline is { Count: > 0 })
        {
            sb.AppendLine("Simulation timeline (truncated):");
            foreach (var line in timeline.Take(40))
                sb.AppendLine("- " + line);
            sb.AppendLine();
        }

        if (files is { Count: > 0 })
        {
            sb.AppendLine("Workspace files:");
            foreach (var (path, text) in files)
            {
                sb.AppendLine($"----- FILE {path} -----");
                sb.AppendLine(text);
                sb.AppendLine();
                if (sb.Length > maxChars * 3 / 4)
                    break;
            }
        }

        if (hits is { Count: > 0 })
        {
            sb.AppendLine("Ranked search hits (use these names):");
            foreach (var h in hits.Take(30))
            {
                sb.AppendLine($"- [{h.Kind}] {h.Id} (score {h.Score})");
                if (cache is not null && h.Kind == "type" && cache.TypeGraph.Types.TryGetValue(h.Id, out var t))
                    sb.AppendLine($"    base={t.BaseType}; methods={string.Join(',', t.Methods.Take(8))}");
                if (cache is not null && h.Kind == "mutation" && cache.MutationGraph.Mutations.TryGetValue(h.Id, out var m))
                    sb.AppendLine($"    class={m.Class}; category={m.Category}");
                if (sb.Length > maxChars * 3 / 4)
                    break;
            }

            sb.AppendLine();
        }

        sb.AppendLine("User request:");
        sb.AppendLine(userPrompt);

        var textOut = sb.ToString();
        return textOut.Length <= maxChars ? textOut : textOut[..maxChars];
    }

    public static List<string> ExtractSymbols(string text)
    {
        var list = new List<string>();
        if (string.IsNullOrWhiteSpace(text))
            return list;
        foreach (Match m in Regex.Matches(text, @"\b(XRL\.[A-Za-z0-9_.]+|[A-Z][A-Za-z0-9_]{3,})\b"))
        {
            var s = m.Value;
            if (s is "System" or "Unity" or "Harmony" or "String" or "Object" or "Error" or "Warning")
                continue;
            if (!list.Contains(s, StringComparer.Ordinal))
                list.Add(s);
            if (list.Count >= 16)
                break;
        }

        return list;
    }
}
