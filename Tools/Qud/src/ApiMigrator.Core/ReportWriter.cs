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

    public static void WriteMarkdown(MigrationReport report, string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, ToMarkdown(report));
    }
}
