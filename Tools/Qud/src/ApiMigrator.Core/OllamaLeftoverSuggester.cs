using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Asks Ollama (local or optional ollama.com cloud) for a replacement of leftover migrate hits that curated autofix
/// cannot safely rewrite (concatenated DidX Extra, GameObject.Does, …).
/// Suggestions are C# replacements. Callers apply with TryApply / --apply / GUI Apply.
/// </summary>
public static class OllamaLeftoverSuggester
{
    public const string SystemPrompt =
        "You are a Caves of Qud C# rewriter. Your job is to PERFORM the migration, not advise. " +
        "Rewrite the ONE offending statement to current-API C#. " +
        "Return JSON only: " +
        "{\"skip\":false,\"confidence\":\"high|medium|low\",\"replacement\":\"C# statement(s)\",\"explanation\":\"one clause\"}. " +
        "replacement MUST be compilable C# that drops in for the offending line (keep surrounding logic). " +
        "Never add [Obsolete] or pragma warning disable. Never invent APIs. " +
        "Prefer GameText StartReplace/EmitMessage (=subject.Does:verb=, =object.the.name=, =object.its=, =object.itself=) " +
        "with SetSubject/SetObject. Prefer Mutations.xml DisplayName over BaseMutation.DisplayName setters. " +
        "Do not quote Advice/PreferXML/Harmony essays as the answer — those name the target API; emit the C# that uses it. " +
        "skip=true ONLY if the offending line is already current-API C# or is not a rewriteable statement. " +
        "If you can write a replacement, skip MUST be false. Do not skip because you are unsure; use confidence=medium instead.";

    static readonly HashSet<string> SkipMemberPrefixes = new(StringComparer.OrdinalIgnoreCase)
    {
        "PreferHarmonyPatch.",
        "PreferXML.",
        "CS1929.TextBuilderStringBuilderOnly",
    };

    public static bool IsSuggestable(RemainingHit hit)
    {
        if (hit is null || string.IsNullOrWhiteSpace(hit.Text))
            return false;
        var m = hit.Member ?? "";
        foreach (var p in SkipMemberPrefixes)
        {
            if (m.StartsWith(p, StringComparison.OrdinalIgnoreCase))
                return false;
        }
        if (m.Contains("DefaultDisplayOrder", StringComparison.Ordinal))
            return true;
        return hit.NeedsManual || m.Contains("DidX", StringComparison.Ordinal)
            || m.Contains("XDidY", StringComparison.Ordinal)
            || m.Contains("GameObject.", StringComparison.Ordinal)
            || m.Contains("Grammar.", StringComparison.Ordinal)
            || m.Contains("Event.", StringComparison.Ordinal);
    }

    public static List<(FileScanResult File, RemainingHit Hit)> CollectHits(
        MigrationReport report, int maxHits)
    {
        var list = new List<(FileScanResult, RemainingHit)>();
        if (report?.FileResults is null)
            return list;
        foreach (var file in report.FileResults)
        {
            if (!file.FilePath.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            foreach (var hit in file.RemainingHits)
            {
                if (!IsSuggestable(hit))
                    continue;
                list.Add((file, hit));
                if (list.Count >= maxHits)
                    return list;
            }
        }
        return list;
    }

    public static async Task<List<OllamaSuggestion>> SuggestAsync(
        MigrationReport report,
        OllamaOptions? options = null,
        Action<string>? onLog = null,
        Action<int, int>? onProgress = null,
        CancellationToken ct = default)
    {
        options ??= new OllamaOptions();
        OllamaClient.ApplyHostDefaults(options);
        var results = new List<OllamaSuggestion>();
        var batch = CollectHits(report, Math.Max(1, options.MaxHits));
        var hostKind = OllamaClient.IsCloudHost(options.BaseUrl) ? "cloud" : "local";
        onLog?.Invoke($"Ollama leftover suggest: {batch.Count} hit(s), model {options.Model} @ {options.BaseUrl} ({hostKind})");

        var status = await OllamaClient.ProbeAsync(options, ct).ConfigureAwait(false);
        if (!status.Available)
            throw new InvalidOperationException(status.Summary);

        var resolved = OllamaClient.ResolveModel(status, options.Model);
        if (!string.Equals(resolved, options.Model, StringComparison.OrdinalIgnoreCase))
        {
            onLog?.Invoke($"Using installed model '{resolved}' (requested '{options.Model}').");
            options.Model = resolved;
        }

        var jsonFormat = options.JsonFormat;
        for (var i = 0; i < batch.Count; i++)
        {
            ct.ThrowIfCancellationRequested();
            var (file, hit) = batch[i];
            onProgress?.Invoke(i + 1, batch.Count);
            onLog?.Invoke($"[{i + 1}/{batch.Count}] {Path.GetFileName(file.FilePath)}:{hit.Line} {hit.Member}");
            try
            {
                var snippet = ReadSnippet(file.FilePath, hit.Line, 18);
                var prompt = BuildPrompt(file.FilePath, hit, snippet);
                var raw = await OllamaClient.ChatAsync(
                    options,
                    prompt,
                    SystemPrompt,
                    jsonFormat,
                    ct: ct).ConfigureAwait(false);
                var parsed = ParseSuggestion(raw);
                if (parsed.Skip
                    && string.Equals(parsed.Explanation, "Model did not return JSON.", StringComparison.Ordinal)
                    && jsonFormat)
                {
                    onLog?.Invoke("Retrying without format=json…");
                    raw = await OllamaClient.ChatAsync(
                        options,
                        prompt,
                        SystemPrompt,
                        jsonFormat: false,
                        ct: ct).ConfigureAwait(false);
                    parsed = ParseSuggestion(raw);
                    jsonFormat = false;
                }
                parsed.FilePath = file.FilePath;
                parsed.Line = hit.Line;
                parsed.Member = hit.Member;
                parsed.Original = hit.Text;
                parsed.RawResponse = raw;
                if (!parsed.Skip && !IsSafeReplacement(parsed.Replacement))
                {
                    parsed.Skip = true;
                    parsed.Explanation = string.IsNullOrEmpty(parsed.Explanation)
                        ? "Rejected unsafe replacement ([Obsolete] or empty)."
                        : parsed.Explanation + " (rejected: unsafe replacement)";
                }
                results.Add(parsed);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                results.Add(new OllamaSuggestion
                {
                    FilePath = file.FilePath,
                    Line = hit.Line,
                    Member = hit.Member,
                    Original = hit.Text,
                    Skip = true,
                    Explanation = ex.GetBaseException().Message,
                });
            }
        }

        onProgress?.Invoke(batch.Count, Math.Max(1, batch.Count));
        return results;
    }

    /// <summary>Parse a model JSON blob (fenced or raw). Used by tests and SuggestAsync.</summary>
    public static OllamaSuggestion ParseResponse(string raw) => ParseSuggestion(raw);

    public static string ToMarkdown(IReadOnlyList<OllamaSuggestion> suggestions)
    {
        var sb = new StringBuilder();
        sb.AppendLine("# Ollama leftover rewrites");
        sb.AppendLine();
        sb.AppendLine("These are C# replacements, not advice. `--apply` / GUI Apply writes unique-line hits.");
        sb.AppendLine("Rows with skip=true were already current-API, unsafe (`[Obsolete]`), or advisory (rejected).");
        sb.AppendLine();
        foreach (var s in suggestions)
        {
            sb.AppendLine($"## `{s.FilePath}` L{s.Line} — `{s.Member}`");
            sb.AppendLine();
            sb.AppendLine($"- Confidence: {s.Confidence}");
            sb.AppendLine($"- Skip: {s.Skip}");
            if (!string.IsNullOrEmpty(s.Explanation))
                sb.AppendLine($"- {s.Explanation}");
            sb.AppendLine();
            sb.AppendLine("Original:");
            sb.AppendLine();
            sb.AppendLine("```csharp");
            sb.AppendLine(s.Original);
            sb.AppendLine("```");
            if (!s.Skip && !string.IsNullOrWhiteSpace(s.Replacement))
            {
                sb.AppendLine();
                sb.AppendLine("Suggested:");
                sb.AppendLine();
                sb.AppendLine("```csharp");
                sb.AppendLine(s.Replacement);
                sb.AppendLine("```");
            }
            sb.AppendLine();
        }
        return sb.ToString();
    }

    static string BuildPrompt(string filePath, RemainingHit hit, string snippet)
    {
        return
            "TASK: Rewrite the offending C# statement to the current API. Output JSON. " +
            "skip=false and a C# replacement unless the line is already migrated.\n" +
            "Do not write tutorials, PreferXML essays, or \"you should\" advice.\n\n" +
            $"File: {filePath}\n" +
            $"Line: {hit.Line}\n" +
            $"Obsolete member: {hit.Member}\n" +
            $"Game message: {hit.Message}\n" +
            "Target API (use this in the replacement; do not paste it as the answer):\n" +
            (string.IsNullOrWhiteSpace(hit.Advice) ? "(none)\n" : hit.Advice.Trim() + "\n") +
            "\nOffending line:\n" + hit.Text + "\n\n" +
            "Surrounding C# (rewrite only the obsolete statement):\n" +
            snippet;
    }

    static string ReadSnippet(string path, int line, int radius)
    {
        try
        {
            var lines = File.ReadAllLines(path);
            var i = Math.Max(0, line - 1);
            var from = Math.Max(0, i - radius);
            var to = Math.Min(lines.Length - 1, i + radius);
            var sb = new StringBuilder();
            for (var n = from; n <= to; n++)
                sb.Append(n + 1).Append('|').AppendLine(lines[n]);
            return sb.ToString();
        }
        catch (Exception ex)
        {
            return "(could not read file: " + ex.Message + ")";
        }
    }

    static OllamaSuggestion ParseSuggestion(string raw)
    {
        var json = ExtractJsonObject(raw);
        if (json is null)
        {
            return new OllamaSuggestion
            {
                Skip = true,
                Explanation = "Model did not return JSON.",
                RawResponse = raw,
            };
        }

        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var skip = root.TryGetProperty("skip", out var sk) && sk.ValueKind == JsonValueKind.True;
        var replacement = root.TryGetProperty("replacement", out var r) ? r.GetString() ?? "" : "";
        var explanation = root.TryGetProperty("explanation", out var e) ? e.GetString() ?? "" : "";
        var confidence = root.TryGetProperty("confidence", out var c) ? c.GetString() ?? "low" : "low";
        replacement = replacement.Trim();
        // Models hedge with skip=true while still emitting a rewrite — keep the rewrite.
        if (skip && LooksLikeCsharpStatement(replacement) && IsSafeReplacement(replacement))
            skip = false;
        if (!skip && !LooksLikeCsharpStatement(replacement))
        {
            skip = true;
            if (string.IsNullOrEmpty(explanation))
                explanation = "Rejected advisory output (no C# statement).";
            else if (!explanation.Contains("advisory", StringComparison.OrdinalIgnoreCase))
                explanation += " (rejected: advisory output)";
        }
        return new OllamaSuggestion
        {
            Skip = skip || string.IsNullOrWhiteSpace(replacement),
            Replacement = replacement,
            Explanation = explanation.Trim(),
            Confidence = confidence.Trim().ToLowerInvariant(),
        };
    }

    static string? ExtractJsonObject(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;
        var t = raw.Trim();
        if (t.StartsWith("```", StringComparison.Ordinal))
        {
            var nl = t.IndexOf('\n');
            if (nl > 0) t = t[(nl + 1)..];
            var fence = t.LastIndexOf("```", StringComparison.Ordinal);
            if (fence >= 0) t = t[..fence];
            t = t.Trim();
        }
        if (t.StartsWith('{') && t.EndsWith('}'))
            return t;
        var start = t.IndexOf('{');
        var end = t.LastIndexOf('}');
        if (start >= 0 && end > start)
            return t[start..(end + 1)];
        return null;
    }

    static bool LooksLikeCsharpStatement(string replacement)
    {
        if (string.IsNullOrWhiteSpace(replacement))
            return false;
        if (IsAdvisoryText(replacement))
            return false;
        return replacement.Contains(';')
            || replacement.Contains("EmitMessage", StringComparison.Ordinal)
            || replacement.Contains("StartReplace", StringComparison.Ordinal)
            || replacement.Contains("=>");
    }

    static bool IsAdvisoryText(string text)
    {
        var t = text.TrimStart();
        if (t.Length < 8)
            return false;
        return Regex.IsMatch(t,
            @"^(you should|you could|consider |try to |preferxml|prefer harmony|do not add|migrate to|instead of rewriting|the advice is)\b",
            RegexOptions.IgnoreCase);
    }

    static bool IsSafeReplacement(string replacement)
    {
        if (string.IsNullOrWhiteSpace(replacement))
            return false;
        if (replacement.Contains("[Obsolete]", StringComparison.OrdinalIgnoreCase))
            return false;
        if (Regex.IsMatch(replacement, @"\bpragma\s+warning\s+disable\b", RegexOptions.IgnoreCase))
            return false;
        return replacement.Length is > 2 and < 4000;
    }

    /// <summary>
    /// Replace the original line text once in the file when it occurs exactly once.
    /// Returns false if the line is missing, ambiguous, or the suggestion was skipped.
    /// </summary>
    public static bool TryApply(OllamaSuggestion suggestion, out string error)
    {
        error = "";
        if (suggestion.Skip || string.IsNullOrWhiteSpace(suggestion.Replacement))
        {
            error = "Suggestion was skipped or empty.";
            return false;
        }
        if (!LooksLikeCsharpStatement(suggestion.Replacement) || !IsSafeReplacement(suggestion.Replacement))
        {
            error = "Replacement failed safety checks (advisory text or unsafe).";
            return false;
        }
        if (string.IsNullOrWhiteSpace(suggestion.FilePath) || !File.Exists(suggestion.FilePath))
        {
            error = "File not found.";
            return false;
        }
        var text = File.ReadAllText(suggestion.FilePath);
        var orig = suggestion.Original.Trim();
        if (orig.Length == 0)
        {
            error = "Original line is empty.";
            return false;
        }
        var first = text.IndexOf(orig, StringComparison.Ordinal);
        if (first < 0)
        {
            error = "Original line no longer present in the file.";
            return false;
        }
        if (text.IndexOf(orig, first + orig.Length, StringComparison.Ordinal) >= 0)
        {
            error = "Original line occurs more than once — apply by hand.";
            return false;
        }
        var next = text[..first] + suggestion.Replacement.Trim() + text[(first + orig.Length)..];
        WorkshopWrite.WriteAllText(suggestion.FilePath, next);
        return true;
    }

    /// <summary>
    /// Apply unique-line replacements. When <paramref name="highConfidenceOnly"/> is true,
    /// only <c>confidence=high</c> rows (and <c>medium</c> when <paramref name="includeMedium"/>)
    /// that were not skipped are written.
    /// </summary>
    public static (int Applied, int Failed) TryApplyMany(
        IEnumerable<OllamaSuggestion> suggestions,
        bool highConfidenceOnly,
        out List<string> errors,
        bool includeMedium = false)
    {
        errors = new List<string>();
        var applied = 0;
        var failed = 0;
        foreach (var s in suggestions)
        {
            if (s.Skip) continue;
            if (highConfidenceOnly && !MeetsApplyConfidence(s.Confidence, includeMedium))
                continue;
            if (TryApply(s, out var err))
            {
                applied++;
                s.Skip = true;
                s.Explanation = string.IsNullOrEmpty(s.Explanation) ? "Applied." : s.Explanation + " (applied)";
            }
            else
            {
                failed++;
                errors.Add($"{Path.GetFileName(s.FilePath)}:{s.Line} — {err}");
            }
        }
        return (applied, failed);
    }

    static bool MeetsApplyConfidence(string confidence, bool includeMedium)
    {
        if (string.Equals(confidence, "high", StringComparison.OrdinalIgnoreCase))
            return true;
        return includeMedium &&
               string.Equals(confidence, "medium", StringComparison.OrdinalIgnoreCase);
    }
}

public sealed class OllamaSuggestion
{
    public string FilePath { get; set; } = "";
    public int Line { get; set; }
    public string Member { get; set; } = "";
    public string Original { get; set; } = "";
    public string Replacement { get; set; } = "";
    public string Explanation { get; set; } = "";
    public string Confidence { get; set; } = "low";
    public bool Skip { get; set; }
    public string? RawResponse { get; set; }

    public string FileName =>
        string.IsNullOrEmpty(FilePath) ? "" : Path.GetFileName(FilePath);

    public string Status => Skip ? "skip" : (string.IsNullOrEmpty(Confidence) ? "ok" : Confidence);
}
