using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Repairs high-confidence Harmony argument-name drift for live Qud methods. Harmony binds
/// ordinary Prefix/Postfix parameters by the original method parameter name, so a stale name
/// throws while patches are applied even though the mod compiled successfully.
/// </summary>
public static class HarmonyPatchParameterFixer
{
    public const string FixRuleName = "Harmony patch parameter names → current target signature";

    private sealed record Rename(string AttributePattern, string OldName, string NewName, string Type);

    // Keep this deliberately explicit: parameter renames cannot safely be inferred without the
    // target assembly. Add entries from a verified current signature and a real Harmony failure.
    private static readonly Rename[] Renames =
    {
        new(@"\[HarmonyPatch\s*\(\s*typeof\s*\(\s*Disarming\s*\)\s*,\s*nameof\s*\(\s*Disarming\.Disarm\s*\)\s*\)\s*\]",
            "Object", "Subject", "GameObject"),
    };

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content) ||
            content.IndexOf("HarmonyPatch", StringComparison.Ordinal) < 0)
            return (content, 0);

        var working = content;
        var edits = 0;
        foreach (var rename in Renames)
        {
            var attributes = Regex.Matches(working, rename.AttributePattern,
                RegexOptions.CultureInvariant).Cast<Match>().Reverse().ToList();
            foreach (var attr in attributes)
            {
                var searchStart = attr.Index + attr.Length;
                var tailLength = Math.Min(600, working.Length - searchStart);
                var method = Regex.Match(working.Substring(searchStart, tailLength),
                    @"\b(?:(?:public|private|internal|protected|static)\s+)+(?:void|bool|GameObject)\s+(?:Prefix|Postfix)\s*\((?<params>[^)]*)\)",
                    RegexOptions.CultureInvariant);
                if (!method.Success)
                    continue;

                var methodStart = searchStart + method.Index;
                var signatureEnd = methodStart + method.Length;
                var oldParam = new Regex(@"\b" + Regex.Escape(rename.Type) + @"\s+" +
                                         Regex.Escape(rename.OldName) + @"\b");
                if (!oldParam.IsMatch(method.Groups["params"].Value) ||
                    Regex.IsMatch(method.Groups["params"].Value,
                        @"\b" + Regex.Escape(rename.NewName) + @"\b"))
                    continue;

                var bodyOpen = CsText.SkipWsAndComments(working, signatureEnd);
                if (bodyOpen >= working.Length || working[bodyOpen] != '{' ||
                    !CsText.TryFindMatchingBrace(working, bodyOpen, out var bodyClose))
                    continue;

                var span = working[methodStart..(bodyClose + 1)];
                span = Regex.Replace(span, @"\b" + Regex.Escape(rename.OldName) + @"\b",
                    rename.NewName);
                working = working[..methodStart] + span + working[(bodyClose + 1)..];
                edits++;
            }
        }
        return edits == 0 ? (content, 0) : (working, edits);
    }
}
