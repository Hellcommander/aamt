using System.Text;

namespace ApiMigrator.Core;

public static class ReportWriter
{
    public static string ToMarkdown(MigrationReport report)
    {
        var sb = new StringBuilder();
        var mode = report.Applied ? "APPLY (files written)" : "DRY-RUN (no files written)";
        sb.AppendLine("# Caves of Qud Obsolete-API Migration Report");
        sb.AppendLine();
        sb.AppendLine($"- Mode: **{mode}**");
        sb.AppendLine($"- Generated: {report.GeneratedAt:yyyy-MM-dd HH:mm:ss}");
        sb.AppendLine($"- Dump source: `{report.DumpPath}`");
        sb.AppendLine($"- Rules source: `{report.RulesPath}`");
        sb.AppendLine($"- Scan roots: {string.Join(", ", report.ScanRoots)}");
        if (!string.IsNullOrEmpty(report.ModFilter)) sb.AppendLine($"- Mod filter: `{report.ModFilter}`");
        sb.AppendLine($"- Files scanned: {report.FilesScanned}");
        sb.AppendLine($"- Files with auto-fixes and/or remaining hits: {report.FileResults.Count}");
        sb.AppendLine($"- Total auto-fix rewrites: **{report.TotalAutoFixes}**");
        sb.AppendLine($"- Total remaining obsolete-pattern hits needing review: **{report.TotalRemainingHits}**");
        sb.AppendLine();
        sb.AppendLine("> Advice never says to add `[Obsolete]`. PreferXML → PreferHarmonyPatch → C# override only when there is no other option. In-place API body fixes are separate.");
        sb.AppendLine();

        if (report.FileResults.Count == 0)
        {
            sb.AppendLine("No obsolete-API patterns or auto-fixes found in scope. Clean.");
            return sb.ToString();
        }

        foreach (var fr in report.FileResults)
        {
            sb.AppendLine($"## {fr.FilePath}");
            sb.AppendLine();
            if (fr.AppliedFixes.Count > 0)
            {
                sb.AppendLine(report.Applied ? "**Auto-fixes applied:**" : "**Auto-fixes that WOULD be applied with Apply:**");
                foreach (var af in fr.AppliedFixes) sb.AppendLine($"- {af.RuleName} × {af.Count}");
                sb.AppendLine();
            }
            if (fr.RemainingHits.Count > 0)
            {
                sb.AppendLine("**Remaining hits needing human review:**");
                sb.AppendLine();
                foreach (var h in fr.RemainingHits)
                {
                    var code = h.Text.Replace("|", "\\|").Replace("`", "\\`");
                    if (code.Length > 160) code = code[..157] + "...";
                    sb.AppendLine($"- **L{h.Line}** `{h.Member}` — {h.Message}");
                    sb.AppendLine($"  - Code: `{code}`");
                    if (!string.IsNullOrWhiteSpace(h.Advice))
                    {
                        sb.AppendLine("  - Advice:");
                        sb.AppendLine("    ```");
                        foreach (var line in h.Advice.Replace("\r\n", "\n").Split('\n'))
                            sb.AppendLine("    " + line);
                        sb.AppendLine("    ```");
                    }
                }
                sb.AppendLine();
            }
        }

        return sb.ToString();
    }

    /// <summary>
    /// Short agent-facing digest: prefer this over full Markdown so a local LLM
    /// can fix remaining hits without loading every file into context.
    /// </summary>
    public static string ToCompactAgentSummary(MigrationReport report, int maxChars = 6000)
    {
        var sb = new StringBuilder();
        var mode = report.Applied ? "APPLY" : "DRY-RUN";
        sb.AppendLine("API_MIGRATE " + mode);
        sb.AppendLine("files_scanned=" + report.FilesScanned
            + " files_flagged=" + report.FileResults.Count
            + " auto_fixes=" + report.TotalAutoFixes
            + " remaining=" + report.TotalRemainingHits);
        if (!string.IsNullOrEmpty(report.ModFilter))
            sb.AppendLine("mod_filter=" + report.ModFilter);
        foreach (var root in report.ScanRoots.Take(4))
            sb.AppendLine("root=" + root);

        var autoByRule = report.FileResults
            .SelectMany(f => f.AppliedFixes)
            .GroupBy(a => a.RuleName)
            .OrderByDescending(g => g.Sum(x => x.Count))
            .Take(12);
        if (autoByRule.Any())
        {
            sb.AppendLine("auto_by_rule:");
            foreach (var g in autoByRule)
                sb.AppendLine("- " + g.Key + " x" + g.Sum(x => x.Count));
        }

        var remaining = report.FileResults
            .SelectMany(f => f.RemainingHits.Select(h => (f.FilePath, h)))
            .Take(40)
            .ToList();
        if (remaining.Count > 0)
        {
            sb.AppendLine("remaining_hits (fix these; do not dump whole files unless needed):");
            foreach (var (path, h) in remaining)
            {
                var rel = path;
                foreach (var root in report.ScanRoots)
                {
                    if (path.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    {
                        rel = path[root.Length..].TrimStart('\\', '/');
                        break;
                    }
                }
                var advice = (h.Advice ?? "").Replace('\r', ' ').Replace('\n', ' ').Trim();
                if (advice.Length > 120) advice = advice[..117] + "...";
                var code = (h.Text ?? "").Replace('\r', ' ').Replace('\n', ' ').Trim();
                if (code.Length > 100) code = code[..97] + "...";
                sb.AppendLine("- " + rel + ":L" + h.Line + " " + h.Member);
                if (!string.IsNullOrWhiteSpace(h.Message))
                    sb.AppendLine("  msg: " + h.Message);
                if (!string.IsNullOrWhiteSpace(advice))
                    sb.AppendLine("  advice: " + advice);
                if (!string.IsNullOrWhiteSpace(code))
                    sb.AppendLine("  code: " + code);
            }
            if (report.TotalRemainingHits > remaining.Count)
                sb.AppendLine("… +" + (report.TotalRemainingHits - remaining.Count) + " more remaining hits");
        }
        else if (report.TotalAutoFixes == 0)
        {
            sb.AppendLine("clean: no obsolete-API auto-fixes or remaining hits in scope.");
        }

        sb.AppendLine("next: compile active mod; only read_file the listed remaining paths.");
        var text = sb.ToString();
        if (text.Length > maxChars)
            return text[..(maxChars - 20)] + "\n…[compact truncated]";
        return text;
    }

    public static void WriteMarkdown(MigrationReport report, string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, ToMarkdown(report));
    }
}
