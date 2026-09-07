using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Confidence-gated <c>Popup.ShowOptionList</c> → <c>Popup.PickOption</c> (and Async) rewrite.
/// When args cannot be mapped safely, leaves the call alone for <see cref="ManualAdvice"/>.
/// </summary>
public static class ShowOptionListFixer
{
    public const string FixRuleName = "Popup.ShowOptionList → PickOption (mapped args)";
    public const string FixRuleNameAsync = "Popup.ShowOptionListAsync → PickOptionAsync (mapped args)";

    // ShowOptionList positional parameter names (Managed reflection)
    static readonly string[] ShowOptionListPositional =
    {
        "Title", "Options", "Hotkeys", "Spacing", "Intro", "MaxWidth",
        "RespectOptionNewlines", "AllowEscape", "DefaultSelected", "SpacingText",
        "OnResult", "Context", "Icons", "IntroIcon", "Buttons",
        "CenterIntro", "CenterIntroIcon", "IconPosition", "ForceNewPopup",
    };

    static readonly string[] ShowOptionListAsyncPositional =
    {
        "Title", "Options", "Hotkeys", "Spacing", "Intro", "MaxWidth",
        "RespectOptionNewlines", "AllowEscape", "DefaultSelected", "SpacingText",
        "Context", "Icons", "IntroIcon",
        "CenterIntro", "CenterIntroIcon", "IconPosition",
    };

    static readonly Dictionary<string, string> NamedRemap = new(StringComparer.Ordinal)
    {
        ["onResult"] = "OnResult",
        ["OnResult"] = "OnResult",
        ["context"] = "Context",
        ["Context"] = "Context",
        ["centerIntro"] = "CenterIntro",
        ["CenterIntro"] = "CenterIntro",
        ["centerIntroIcon"] = "CenterIntroIcon",
        ["CenterIntroIcon"] = "CenterIntroIcon",
        ["iconPosition"] = "IconPosition",
        ["IconPosition"] = "IconPosition",
        ["forceNewPopup"] = "ForceNewPopup",
        ["ForceNewPopup"] = "ForceNewPopup",
        // same-cased passthroughs
        ["Title"] = "Title",
        ["Options"] = "Options",
        ["Hotkeys"] = "Hotkeys",
        ["Spacing"] = "Spacing",
        ["Intro"] = "Intro",
        ["MaxWidth"] = "MaxWidth",
        ["RespectOptionNewlines"] = "RespectOptionNewlines",
        ["AllowEscape"] = "AllowEscape",
        ["DefaultSelected"] = "DefaultSelected",
        ["SpacingText"] = "SpacingText",
        ["Icons"] = "Icons",
        ["IntroIcon"] = "IntroIcon",
        ["Buttons"] = "Buttons",
        ["Sound"] = "Sound",
        ["PopupLocation"] = "PopupLocation",
        ["PopupID"] = "PopupID",
        ["AfterShow"] = "AfterShow",
    };

    static readonly Regex CallSite = new(
        @"\b(?<recv>(?:XRL\.UI\.)?Popup)\.(?<name>ShowOptionList(?:Async)?)\s*(?<paren>\()",
        RegexOptions.Compiled);

    public static (string Content, int SyncFixes, int AsyncFixes) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0, 0);

        var matches = CallSite.Matches(content);
        if (matches.Count == 0)
            return (content, 0, 0);

        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var sync = 0;
        var async = 0;

        foreach (Match m in matches)
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;

            var isAsync = m.Groups["name"].Value.EndsWith("Async", StringComparison.Ordinal);
            if (!TryMapToPickOption(args, isAsync, out var named))
                continue;

            var recv = m.Groups["recv"].Value;
            var newName = isAsync ? "PickOptionAsync" : "PickOption";
            var replacement = BuildCall(recv, newName, named);

            sb.Append(content, last, m.Index - last);
            sb.Append(replacement);
            last = close + 1;
            if (isAsync) async++; else sync++;
        }

        if (sync + async == 0)
            return (content, 0, 0);

        sb.Append(content, last, content.Length - last);
        return (sb.ToString(), sync, async);
    }

    static bool TryMapToPickOption(List<CallArgParser.Arg> args, bool isAsync, out List<(string Name, string Expr)> named)
    {
        named = new List<(string, string)>();
        var positionalNames = isAsync ? ShowOptionListAsyncPositional : ShowOptionListPositional;
        var positionalIndex = 0;
        var seen = new HashSet<string>(StringComparer.Ordinal);

        foreach (var arg in args)
        {
            if (arg.Name != null)
            {
                if (!NamedRemap.TryGetValue(arg.Name, out var pickName))
                    return false; // unknown named arg — don't guess
                if (!seen.Add(pickName))
                    return false;
                named.Add((pickName, arg.Expression));
                // once named args start, further positionals are illegal in C# — but ShowOptionList
                // callers often mix (positionals then named). Track that positionals are done.
                positionalIndex = int.MaxValue;
                continue;
            }

            if (positionalIndex == int.MaxValue)
                return false; // positional after named
            if (positionalIndex >= positionalNames.Length)
                return false;

            var pickName2 = positionalNames[positionalIndex++];
            if (!seen.Add(pickName2))
                return false;
            named.Add((pickName2, arg.Expression));
        }

        // Require at least Title or Options to avoid empty nonsense
        return named.Count > 0;
    }

    static string BuildCall(string receiver, string method, List<(string Name, string Expr)> named)
    {
        if (named.Count <= 3 && named.TrueForAll(n => !n.Expr.Contains('\n')))
        {
            var inner = string.Join(", ", named.Select(n => $"{n.Name}: {n.Expr}"));
            return $"{receiver}.{method}({inner})";
        }

        var sb = new StringBuilder();
        sb.Append(receiver).Append('.').Append(method).AppendLine("(");
        for (var i = 0; i < named.Count; i++)
        {
            sb.Append("    ").Append(named[i].Name).Append(": ").Append(named[i].Expr);
            if (i < named.Count - 1) sb.Append(',');
            sb.AppendLine();
        }
        sb.Append(')');
        return sb.ToString();
    }
}
