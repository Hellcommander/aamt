using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// High-confidence GameText migrations for obsolete message helpers (Hacking/Gadgets shapes):
/// interpolated <c>.t()</c>/<c>.its</c> in MessageQueue/Popup, interpolated
/// <c>$"{go.The}{go.ShortDisplayName}"</c> (CS0618), <c>x =&gt; x.an()</c>,
/// simple <c>DidX("verb"…)</c>, and <c>recv.Poss("word") + "…"</c>.
/// Ambiguous sites stay for dump + ManualAdvice. Ensures <c>using XRL.World.Text</c> and
/// <c>using XRL</c> (StartReplace extension) when edits fire.
/// Does <b>not</b> rewrite <c>XRL.The.Game</c> / <c>XRL.The.Player</c> (static helper class).
/// </summary>
public static class GameTextCallSiteFixer
{
    public const string FixRuleName =
        "GameText call sites (.t/.its/.an/DidX/XDidY/Poss → StartReplace/EmitMessage)";

    /// <summary>
    /// Prior buggy Apply rewrote <c>XRL.The</c> (static) as GameObject article GameText.
    /// Undo that exact mangled form so re-running migrate is safe.
    /// </summary>
    public const string RepairXrlTheRuleName =
        "Repair mangled XRL.The (static helper, not GameObject.The)";

    static readonly Regex MsgCallOpen = new(
        @"(?<call>MessageQueue\.AddPlayerMessage|Popup\.Show|IComponent<\s*GameObject\s*>\.AddPlayerMessage)\s*\(\s*\$""",
        RegexOptions.Compiled);

    static readonly Regex AnLambda = new(
        @"\(\s*(?<x>\w+)\s*=>\s*\k<x>\.an\(\s*\)\s*\)",
        RegexOptions.Compiled);

    static readonly Regex DidXCall = new(
        @"(?<![A-Za-z0-9_])(?:(?:this|base)\.)?(?:IComponent\s*<\s*GameObject\s*>\s*\.)?DidX\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex XDidYCall = new(
        @"(?:IComponent\s*<\s*GameObject\s*>\s*\.)?XDidY\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex PossConcat = new(
        @"(?<recv>(?:this\.)?\w+(?:\.\w+)*)\.Poss\s*\(\s*""(?<word>[A-Za-z][\w\-]*)""\s*\)\s*\+\s*""(?<rest>(?:[^""\\]|\\.)*)""",
        RegexOptions.Compiled);

    // "…" + go.The/the + go.ShortDisplayName[WithoutTitles] + "…"
    static readonly Regex TheShortNameConcat = new(
        @"""(?<pre>(?:[^""\\]|\\.)*)""\s*\+\s*(?<recv>(?:this\.)?\w+(?:\.\w+)*)\.(?<art>The|the)\s*\+\s*\k<recv>\.ShortDisplayName(?:WithoutTitles)?\s*\+\s*""(?<post>(?:[^""\\]|\\.)*)""",
        RegexOptions.Compiled);

    // go.The/the + go.ShortDisplayName[WithoutTitles] mid-expression (XDidY Extra, etc.)
    static readonly Regex TheShortNameMid = new(
        @"(?<recv>(?:this\.)?\w+(?:\.\w+)*)\.(?<art>The|the)\s*\+\s*\k<recv>\.ShortDisplayName(?:WithoutTitles)?",
        RegexOptions.Compiled);

    // "…" + go.poss("word")  (trailing, no further concat required)
    static readonly Regex PossInConcat = new(
        @"""(?<pre>(?:[^""\\]|\\.)*)""\s*\+\s*(?<recv>(?:this\.)?\w+(?:\.\w+)*)\.poss\s*\(\s*""(?<word>[A-Za-z][\w\-]*)""\s*\)",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    static readonly Regex SimpleObjectTextCall = new(
        @"(?<recv>(?:this|base|[A-Za-z_]\w*)(?:\.[A-Za-z_]\w*)*(?:\[[^\]\r\n]+\])?)\.(?<method>t|an|does|Does|poss)\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex MakeTitleCaseCall = new(
        @"Grammar\.MakeTitleCase\s*(?<paren>\()",
        RegexOptions.Compiled);

    static readonly Regex GetLiquidNameCall = new(
        @"(?<recv>(?:this|base|[A-Za-z_]\w*)(?:\.[A-Za-z_]\w*)*)\.GetLiquidName\s*(?<paren>\()",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var edits = 0;
        var working = RepairMangledXrlThe(content, ref edits);
        working = FixInterpolatedMessages(working, ref edits);
        working = FixInterpolatedTheShortName(working, ref edits);
        working = FixSimpleObjectTextCalls(working, ref edits);
        working = FixMakeTitleCase(working, ref edits);
        working = FixGetLiquidName(working, ref edits);
        working = FixAnLambdas(working, ref edits);
        working = FixSimpleDidX(working, ref edits);
        working = FixSimpleXDidY(working, ref edits);
        working = FixSimpleXDidYToZ(working, ref edits);
        working = FixPossConcat(working, ref edits);
        working = FixTheShortNameConcat(working, ref edits);
        working = FixTheShortNameMid(working, ref edits);
        working = FixPossInConcat(working, ref edits);
        working = FixGetVerb(working, ref edits);
        working = FixInitLowerIfArticle(working, ref edits);
        working = FixTargetSelfConfirm(working, ref edits);
        working = FixPronounProperties(working, ref edits);
        working = FixPronounNameConcat(working, ref edits);
        working = FixSimpleDidXToY(working, ref edits);
        working = RemoveNowUnusedMessageLocals(working, ref edits);

        if (edits == 0)
            return (content, 0);

        var (withUsing, _) = UsingInserter.EnsureUsings(working, UsingInserter.UsingsForStartReplace(working));
        return (withUsing, edits);
    }

    static string FixInterpolatedMessages(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;

        foreach (Match open in MsgCallOpen.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, open.Index))
                continue;

            var quoteOpen = open.Index + open.Length - 1; // "
            if (!TryFindInterpolatedStringEnd(content, quoteOpen, out var quoteClose))
                continue;

            var inner = content[(quoteOpen + 1)..quoteClose];
            if (!TryRewriteInterpolation(inner, out var rewrittenInner, out var subjectExpr))
                continue;

            var j = quoteClose + 1;
            while (j < content.Length && char.IsWhiteSpace(content[j])) j++;
            if (j >= content.Length || content[j] != ')')
                continue;
            j++;

            sb.Append(content, last, open.Index - last);
            sb.Append(open.Groups["call"].Value)
                .Append("(\"")
                .Append(rewrittenInner)
                .Append("\".StartReplace().SetSubject(")
                .Append(subjectExpr)
                .Append(").ToString())");
            last = j;
            localEdits++;
        }

        if (localEdits == 0)
            return content;

        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static bool TryFindInterpolatedStringEnd(string content, int openQuoteIndex, out int closeQuoteIndex)
    {
        closeQuoteIndex = -1;
        if (openQuoteIndex < 0 || openQuoteIndex >= content.Length || content[openQuoteIndex] != '"')
            return false;

        var i = openQuoteIndex + 1;
        var braceDepth = 0;
        while (i < content.Length)
        {
            var c = content[i];
            if (c == '\\' && braceDepth == 0)
            {
                i += 2;
                continue;
            }

            if (braceDepth == 0 && c == '{' && i + 1 < content.Length && content[i + 1] == '{')
            {
                i += 2;
                continue;
            }

            if (braceDepth == 0 && c == '}' && i + 1 < content.Length && content[i + 1] == '}')
            {
                i += 2;
                continue;
            }

            if (c == '{' && braceDepth == 0)
            {
                braceDepth = 1;
                i++;
                continue;
            }

            if (braceDepth > 0)
            {
                if (c == '{') braceDepth++;
                else if (c == '}') braceDepth--;
                i++;
                continue;
            }

            if (c == '"')
            {
                closeQuoteIndex = i;
                return true;
            }

            i++;
        }

        return false;
    }

    static readonly Regex InterpolatedTheShortName = new(
        @"^(?<pre>(?:[^{\\]|\\.|\{\{|\}\})*)\{(?<recv>(?:this\.)?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.(?<art>The|the)\}\{\k<recv>\.ShortDisplayName(?:WithoutTitles)?\}(?<post>.*)$",
        RegexOptions.Compiled | RegexOptions.Singleline);

    /// <summary>
    /// <c>$"{go.The}{go.ShortDisplayName} …"</c> is skipped by pronoun-property rewrite
    /// (HitFilter treats interpolation holes as inside a string). CS0618 GameObject.The.
    /// </summary>
    static string FixInterpolatedTheShortName(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var local = 0;
        var i = 0;
        while (i < content.Length - 1)
        {
            if (content[i] != '$' || content[i + 1] != '"')
            {
                i++;
                continue;
            }
            if (HitFilter.IsInsideComment(content, i))
            {
                i++;
                continue;
            }

            var quoteOpen = i + 1;
            if (!TryFindInterpolatedStringEnd(content, quoteOpen, out var quoteClose))
            {
                i++;
                continue;
            }

            var inner = content[(quoteOpen + 1)..quoteClose];
            if (!TryRewriteTheShortNameInterpolation(inner, out var rewritten, out var recv, out var keepDollar))
            {
                i = quoteClose + 1;
                continue;
            }

            sb.Append(content, last, i - last);
            if (keepDollar)
                sb.Append('$');
            sb.Append('"').Append(rewritten)
                .Append("\".StartReplace().SetObject(")
                .Append(recv)
                .Append(").ToString()");
            last = quoteClose + 1;
            local++;
            i = last;
        }

        if (local == 0)
            return content;

        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static bool TryRewriteTheShortNameInterpolation(
        string inner, out string rewritten, out string recv, out bool keepDollar)
    {
        rewritten = "";
        recv = "";
        keepDollar = false;
        var m = InterpolatedTheShortName.Match(inner);
        if (!m.Success)
            return false;
        recv = m.Groups["recv"].Value;
        if (!IsSafeReceiver(recv))
            return false;
        var post = m.Groups["post"].Value;
        rewritten = m.Groups["pre"].Value + TheNameToken(m.Groups["art"].Value) + post;
        keepDollar = HasInterpolationHole(post);
        return true;
    }

    static bool HasInterpolationHole(string s)
    {
        for (var i = 0; i < s.Length; i++)
        {
            if (s[i] != '{')
                continue;
            if (i + 1 < s.Length && s[i + 1] == '{')
            {
                i++;
                continue;
            }
            return true;
        }
        return false;
    }

    static string TheNameToken(string art) =>
        art == "The" ? "=object.The.name=" : "=object.the.name=";

    static bool TryRewriteInterpolation(string inner, out string rewritten, out string subjectExpr)
    {
        rewritten = "";
        subjectExpr = "";

        var m = Regex.Match(inner,
            @"^\{(?<go>[^{}]+)\.t\(\)\} \{isOrAre\} organic and \{doOrDoes\} (?<rest>.*)$");
        if (m.Success)
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"=subject.the.name= =subject.verb:are= organic and =subject.verb:do= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner,
            @"^\{(?<go>[^{}]+)\.t\(\)\} \{isOrAre\} not robotic and \{hasOrHave\} (?<rest>.*)$");
        if (m.Success)
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"=subject.the.name= =subject.verb:are= not robotic and =subject.verb:have= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner, @"^\{(?<go>[^{}]+)\.t\(\)\} \{isOrAre\} (?<rest>.*)$");
        if (m.Success && !m.Groups["rest"].Value.Contains('{'))
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"=subject.the.name= =subject.verb:are= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner, @"^\{(?<go>[^{}]+)\.t\(\)\} \{hasOrHave\} (?<rest>.*)$");
        if (m.Success && !m.Groups["rest"].Value.Contains('{'))
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"=subject.the.name= =subject.verb:have= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner, @"^\{(?<go>[^{}]+)\.its\} (?<rest>.*)$");
        if (m.Success && !m.Groups["rest"].Value.Contains('{'))
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"=subject.its= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner, @"^You fail to (?<verb>[^{]+)\{(?<go>[^{}]+)\.its\} (?<rest>.*)$");
        if (m.Success && !m.Groups["rest"].Value.Contains('{'))
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = $"You fail to {m.Groups["verb"].Value}=subject.its= {m.Groups["rest"].Value}";
            return IsSafeReceiver(subjectExpr);
        }

        m = Regex.Match(inner, @"^\{(?<go>[^{}]+)\.t\(\)\}$");
        if (m.Success)
        {
            subjectExpr = m.Groups["go"].Value.Trim();
            rewritten = "=subject.the.name=";
            return IsSafeReceiver(subjectExpr);
        }

        return false;
    }

    static bool IsSafeReceiver(string expr) =>
        !string.IsNullOrWhiteSpace(expr) &&
        expr is not "null" and not "true" and not "false" &&
        Regex.IsMatch(expr, @"^[\w\.]+(?:\[[^\]]+\])?$");

    static string FixSimpleObjectTextCalls(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var local = 0;
        foreach (Match m in SimpleObjectTextCall.Matches(content))
        {
            if (m.Index < last || HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var recv = m.Groups["recv"].Value;
            if (!IsSafeReceiver(recv) || recv is "XRL" or "Grammar")
                continue;
            if (!CallArgParser.TryParseArgumentList(
                    content, m.Groups["paren"].Index, out var args, out var close))
                continue;

            var method = m.Groups["method"].Value;
            string token;
            if (method == "t")
                token = "=object.the.name=";
            else if (method == "an")
                token = "=object.a.name=";
            else
            {
                // The first argument is the grammatical word represented by the token;
                // remaining obsolete flags only controlled the legacy string renderer.
                if (args.Count < 1 || !TryStringLit(args[0], out var word) ||
                    !IsSafeVerb(word))
                    continue;
                if (method is "does" or "Does")
                    token = $"=object.{method}:{word}=";
                else
                {
                    var definite = args.Count < 2 || args[1].Expression.Trim() != "false";
                    token = $"=object.{(definite ? "the" : "a")}.name's:withTitles= {word}";
                }
            }

            sb.Append(content, last, m.Index - last);
            sb.Append('"').Append(token).Append("\".StartReplace().SetObject(")
                .Append(recv).Append(").ToString()");
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixMakeTitleCase(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var local = 0;
        foreach (Match m in MakeTitleCaseCall.Matches(content))
        {
            if (m.Index < last || HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            if (!CallArgParser.TryParseArgumentList(
                    content, m.Groups["paren"].Index, out var args, out var close) ||
                args.Count != 1 || string.IsNullOrWhiteSpace(args[0].Expression))
                continue;
            sb.Append(content, last, m.Index - last);
            sb.Append("\"=text|title=\".StartReplace().SetArgument(\"text\", ")
                .Append(args[0].Expression.Trim()).Append(").ToString()");
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixGetLiquidName(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var local = 0;
        foreach (Match m in GetLiquidNameCall.Matches(content))
        {
            if (m.Index < last || HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var recv = m.Groups["recv"].Value;
            if (!IsSafeReceiver(recv) ||
                !CallArgParser.TryParseArgumentList(
                    content, m.Groups["paren"].Index, out var args, out var close) ||
                args.Count != 0)
                continue;
            sb.Append(content, last, m.Index - last);
            sb.Append("\"=LiquidVolume.liquid.name=\".StartReplace().SetArgument(\"LiquidVolume\", ")
                .Append(recv).Append(").ToString()");
            last = close + 1;
            local++;
        }
        if (local == 0) return content;
        edits += local;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixAnLambdas(string content, ref int edits)
    {
        var local = 0;
        var next = AnLambda.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            local++;
            var x = m.Groups["x"].Value;
            return $"({x} => \"=object.a.name=\".StartReplace().SetObject({x}).ToString())";
        });
        edits += local;
        return next;
    }

    static string FixSimpleDidX(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;

        foreach (Match m in DidXCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count == 0)
                continue;
            string verb;
            string? explicitSubject = null;
            if (!TryStringValue(content, args[0], m.Index, out verb))
            {
                var isVerb = Regex.Match(args[0].Expression.Trim(),
                    @"^(?<recv>(?:this\.)?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.Is$");
                if (!isVerb.Success)
                    continue;
                explicitSubject = isVerb.Groups["recv"].Value;
                verb = "are";
            }
            if (!IsSafeVerb(verb))
                continue;

            string? extra = null;
            string? extraExpr = null;
            string endMark = "";
            var fromDialog = (bool?)null;
            string? colorGood = null;
            string? colorBad = null;
            char? color = null;
            var ok = true;
            var positionalSeen = 0;

            foreach (var a in args)
            {
                if (a.Name is null)
                {
                    positionalSeen++;
                    if (positionalSeen == 1) continue; // verb
                    if (positionalSeen == 2 && TryStringValue(content, a, m.Index, out var ex))
                    {
                        extra = ex;
                        continue;
                    }
                    if (positionalSeen == 2 && a.Expression.Trim() != "null")
                    {
                        extraExpr = a.Expression.Trim();
                        continue;
                    }
                    if (positionalSeen == 3 &&
                        TryStringValue(content, a, m.Index, out var em) && em.Length <= 3)
                    {
                        endMark = em;
                        continue;
                    }
                    if (positionalSeen is 4 or 5 &&
                        TryStringValue(content, a, m.Index, out var colorText) &&
                        (colorText.Length == 0 || TryColorChar(colorText, out _)))
                    {
                        if (TryColorChar(colorText, out var colorChar))
                            color ??= colorChar;
                        continue;
                    }
                    if (positionalSeen >= 4 && IsSafeReceiver(a.Expression.Trim()))
                    {
                        explicitSubject ??= a.Expression.Trim();
                        continue;
                    }
                    // Obsolete DidX has many trailing ColorString/bool/GameObject defaults.
                    if (IsIgnorableDidXPositional(a.Expression.Trim()))
                        continue;
                    ok = false;
                    break;
                }

                switch (a.Name)
                {
                    case "Verb":
                        if (!TryStringValue(content, a, m.Index, out verb) || !IsSafeVerb(verb)) ok = false;
                        break;
                    case "Extra":
                        if (!TryStringValue(content, a, m.Index, out extra!))
                            extraExpr = a.Expression.Trim();
                        break;
                    case "EndMark":
                        if (!TryStringValue(content, a, m.Index, out endMark!) || endMark.Length > 3) ok = false;
                        break;
                    case "FromDialog":
                        if (a.Expression.Trim() is "true" or "false")
                            fromDialog = a.Expression.Trim() == "true";
                        else ok = false;
                        break;
                    case "ColorAsGoodFor":
                        colorGood = a.Expression.Trim();
                        break;
                    case "ColorAsBadFor":
                        colorBad = a.Expression.Trim();
                        break;
                    case "UseFullNames":
                    case "IndefiniteSubject":
                    case "DescribeSubjectDirection":
                    case "DescribeSubjectDirectionLate":
                    case "AlwaysVisible":
                    case "SubjectPossessedBy":
                    case "PossessiveObject":
                        break;
                    default:
                        ok = false;
                        break;
                }
                if (!ok) break;
            }

            if (!ok) continue;

            var identIndex = CallIdentIndex(m, "DidX");
            var replaceStart = Math.Min(m.Index, DottedReceiverStart(content, identIndex));
            var subject = explicitSubject ??
                InferDidXSubject(content, m.Index, ReceiverChain(content, replaceStart, identIndex));
            var template = extra is not null
                ? $"=subject.Does:{verb}= {extra}{endMark}"
                : extraExpr is not null
                    ? $"=subject.Does:{verb}= =extra={endMark}"
                    : $"=subject.Does:{verb}={endMark}";

            var emitParts = new List<string>();
            if (color is char colorValue)
                emitParts.Add("'" + EscapeCharLiteral(colorValue) + "'");
            if (fromDialog is bool fd)
                emitParts.Add($"FromDialog: {(fd ? "true" : "false")}");
            if (!string.IsNullOrEmpty(colorGood))
                emitParts.Add($"ColorAsGoodFor: {colorGood}");
            if (!string.IsNullOrEmpty(colorBad))
                emitParts.Add($"ColorAsBadFor: {colorBad}");
            var emit = emitParts.Count == 0
                ? "EmitMessage()"
                : $"EmitMessage({string.Join(", ", emitParts)})";

            sb.Append(content, last, replaceStart - last);
            sb.Append('"').Append(template).Append("\".StartReplace().SetSubject(")
                .Append(subject).Append(')');
            if (extraExpr is not null)
                sb.Append(".SetArgument(\"extra\", ").Append(extraExpr).Append(')');
            sb.Append('.').Append(emit);
            last = close + 1;
            localEdits++;
        }

        if (localEdits == 0)
            return content;

        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string InferDidXSubject(string content, int index, string? receiverChain = null)
    {
        var fromRecv = SubjectFromReceiver(receiverChain);
        if (!string.IsNullOrEmpty(fromRecv))
            return fromRecv;
        var start = Math.Max(0, index - 500);
        var window = content[start..index];
        if (Regex.IsMatch(window, @"\b(?:Apply|Remove)\s*\(\s*GameObject\s+Object\b"))
            return "Object";
        foreach (Match classMatch in Regex.Matches(content[..index],
                     @"\bclass\s+[A-Za-z_]\w*\s*:\s*(?<bases>[^\{]+)\{"))
        {
            if (!Regex.IsMatch(classMatch.Groups["bases"].Value, @"\bEffect\b"))
                continue;
            var open = classMatch.Index + classMatch.Length - 1;
            if (CsText.TryFindMatchingBrace(content, open, out var close) && close >= index)
                return "Object";
        }
        return "ParentObject";
    }

    static readonly HashSet<string> ComponentReceiverLeaves = new(StringComparer.Ordinal)
    {
        "Physics", "pPhysics", "Brain", "pBrain", "Body", "Render",
        "Inventory", "LiquidVolume", "Description",
    };

    /// <summary>
    /// <c>ParentObject.Physics.DidX</c> messages as ParentObject; <c>this</c>/<c>base</c> fall
    /// through to the Apply/Remove heuristic.
    /// </summary>
    static string? SubjectFromReceiver(string? chain)
    {
        if (string.IsNullOrEmpty(chain) || chain is "this" or "base")
            return null;
        var parts = chain.Split('.');
        while (parts.Length >= 2 && ComponentReceiverLeaves.Contains(parts[^1]))
            parts = parts[..^1];
        var subject = string.Join(".", parts);
        return IsSafeReceiver(subject) && subject is not "this" and not "base" ? subject : null;
    }

    static bool IsIdentChar(char c) => char.IsLetterOrDigit(c) || c == '_';

    /// <summary>
    /// Walk left from the DidX/XDidY identifier over <c>.ident</c> so the replace span
    /// includes the receiver (<c>ParentObject.Physics.DidX</c>, <c>Messaging.XDidY</c>).
    /// </summary>
    static int DottedReceiverStart(string content, int identIndex)
    {
        var i = identIndex;
        while (true)
        {
            var j = i;
            while (j > 0 && char.IsWhiteSpace(content[j - 1])) j--;
            if (j < 2 || content[j - 1] != '.')
                return i;
            var k = j - 1;
            while (k > 0 && char.IsWhiteSpace(content[k - 1])) k--;
            if (k == 0 || !IsIdentChar(content[k - 1]))
                return i;
            k--;
            while (k > 0 && IsIdentChar(content[k - 1]))
                k--;
            i = k;
        }
    }

    static int CallIdentIndex(Match m, string ident)
    {
        var rel = m.Value.LastIndexOf(ident, StringComparison.Ordinal);
        return rel < 0 ? m.Index : m.Index + rel;
    }

    static int ReplaceStartForCall(string content, Match m, string ident)
    {
        var identIndex = CallIdentIndex(m, ident);
        return Math.Min(m.Index, DottedReceiverStart(content, identIndex));
    }

    static string? ReceiverChain(string content, int replaceStart, int identIndex)
    {
        if (identIndex <= replaceStart) return null;
        var chain = content[replaceStart..identIndex].Trim().TrimEnd('.');
        return string.IsNullOrEmpty(chain) ? null : chain;
    }

    static string FixPossConcat(string content, ref int edits)
    {
        var local = 0;
        var next = PossConcat.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;

            var recv = m.Groups["recv"].Value;
            var word = m.Groups["word"].Value;
            var rest = m.Groups["rest"].Value;
            if (!IsSafeReceiver(recv) || !IsSafeToken(word))
                return m.Value;

            local++;
            return $"\"=subject.poss:{word}={rest}\".StartReplace().SetSubject({recv}).ToString()";
        });
        edits += local;
        return next;
    }

    static string FixSimpleXDidY(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;

        foreach (Match m in XDidYCall.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count < 2)
                continue;

            // XDidY(who, verb, extra?, …) or the same overload with out-of-order
            // named Actor:/Verb: arguments (used by WM Extended Mutations).
            var actorIndex = args.FindIndex(a => a.Name == "Actor");
            var verbIndex = args.FindIndex(a => a.Name == "Verb");
            var namedCore = actorIndex >= 0 || verbIndex >= 0;
            if (namedCore && (actorIndex < 0 || verbIndex < 0))
                continue;

            var whoArg = namedCore ? args[actorIndex] : args[0];
            var verbArg = namedCore ? args[verbIndex] : args[1];
            var who = whoArg.Expression.Trim();
            if (!IsSafeReceiver(who) ||
                !TryStringValue(content, verbArg, m.Index, out var verb) ||
                !IsSafeVerb(verb))
                continue;

            string? extraLit = null;
            string? extraExpr = null;
            string endMark = "";
            bool? fromDialog = null;
            string? colorGood = null;
            string? colorBad = null;
            char? color = null;
            var ok = true;
            for (var i = namedCore ? 0 : 2; i < args.Count; i++)
            {
                var a = args[i];
                if (namedCore && a.Name is "Actor" or "Verb")
                    continue;
                if (a.Name == "Extra")
                {
                    if (a.Expression.Trim() == "null")
                        continue;
                    if (TryStringValue(content, a, m.Index, out var extra))
                        extraLit = extra;
                    else
                        extraExpr = a.Expression.Trim();
                    continue;
                }
                if (a.Name == "EndMark")
                {
                    if (a.Expression.Trim() == "null")
                        continue;
                    if (!TryStringValue(content, a, m.Index, out endMark) ||
                        endMark.Length > 3 || !IsPunctuationEndMark(endMark))
                        ok = false;
                    if (!ok) break;
                    continue;
                }
                if (a.Name is "ColorAsBadFor" or "ColorAsGoodFor")
                {
                    if (a.Name == "ColorAsBadFor")
                        colorBad = a.Expression.Trim();
                    else
                        colorGood = a.Expression.Trim();
                    continue;
                }
                if (a.Name is "FromDialog")
                {
                    if (a.Expression.Trim() is not ("true" or "false"))
                    {
                        ok = false;
                        break;
                    }
                    fromDialog = a.Expression.Trim() == "true";
                    continue;
                }
                if (a.Name is "UsePopup" or "AlwaysVisible" or "UseFullNames" or
                    "IndefiniteSubject" or "DescribeSubjectDirection" or
                    "DescribeSubjectDirectionLate" or "SubjectPossessedBy")
                {
                    continue;
                }
                if (a.Name is not null)
                {
                    ok = false;
                    break;
                }
                var expr = a.Expression.Trim();
                if (expr is "null")
                    continue;
                if (i == 2)
                {
                    if (TryStringValue(content, a, m.Index, out var extra))
                        extraLit = extra;
                    else
                        extraExpr = expr;
                    continue;
                }
                if (i == 3 && TryStringValue(content, a, m.Index, out var mark) &&
                    mark.Length <= 3 && IsPunctuationEndMark(mark))
                {
                    endMark = mark;
                    continue;
                }
                if (i is 4 or 5 && TryStringValue(content, a, m.Index, out var colorText) &&
                    (colorText.Length == 0 || TryColorChar(colorText, out _)))
                {
                    if (TryColorChar(colorText, out var colorChar))
                        color ??= colorChar;
                    continue;
                }
                if (colorBad is null && i >= 5 && IsSafeReceiver(expr))
                {
                    colorBad = expr;
                    continue;
                }
                ok = false;
                break;
            }
            if (!ok) continue;

            string template;
            var extraArg = "";
            if (extraLit is not null)
                template = $"=subject.Does:{verb}= {extraLit}{endMark}";
            else if (extraExpr is not null)
            {
                template = $"=subject.Does:{verb}= =extra={endMark}";
                extraArg = extraExpr;
            }
            else
                template = $"=subject.Does:{verb}={endMark}";

            var emitParts = new List<string>();
            if (color is char colorValue)
                emitParts.Add("'" + EscapeCharLiteral(colorValue) + "'");
            if (fromDialog is bool fd)
                emitParts.Add($"FromDialog: {(fd ? "true" : "false")}");
            if (colorGood is not null)
                emitParts.Add("ColorAsGoodFor: " + colorGood);
            if (colorBad is not null)
                emitParts.Add("ColorAsBadFor: " + colorBad);
            var emit = emitParts.Count == 0
                ? "EmitMessage()"
                : "EmitMessage(" + string.Join(", ", emitParts) + ")";
            var chain = $"\"{template}\".StartReplace().SetSubject({who})";
            if (extraArg.Length > 0)
                chain += $".SetArgument(\"extra\", {extraArg})";
            chain += "." + emit;

            var replaceStart = ReplaceStartForCall(content, m, "XDidY");
            sb.Append(content, last, replaceStart - last);
            sb.Append(chain);
            last = close + 1;
            localEdits++;
        }

        if (localEdits == 0)
            return content;

        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixTheShortNameConcat(string content, ref int edits)
    {
        var local = 0;
        var next = TheShortNameConcat.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index))
                return m.Value;
            var recv = m.Groups["recv"].Value;
            if (!IsSafeReceiver(recv))
                return m.Value;
            local++;
            var pre = m.Groups["pre"].Value;
            var post = m.Groups["post"].Value;
            var token = TheNameToken(m.Groups["art"].Value);
            return $"\"{pre}{token}{post}\".StartReplace().SetObject({recv}).ToString()";
        });
        edits += local;
        return next;
    }

    static string FixTheShortNameMid(string content, ref int edits)
    {
        var local = 0;
        var next = TheShortNameMid.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            var recv = m.Groups["recv"].Value;
            if (!IsSafeReceiver(recv))
                return m.Value;
            // Skip if already inside a StartReplace chain we produced
            var before = content[Math.Max(0, m.Index - 40)..m.Index];
            if (before.Contains("StartReplace", StringComparison.Ordinal))
                return m.Value;
            local++;
            var token = TheNameToken(m.Groups["art"].Value);
            return $"\"{token}\".StartReplace().SetObject({recv}).ToString()";
        });
        edits += local;
        return next;
    }

    static string FixSimpleXDidYToZ(string content, ref int edits)
    {
        var callRx = new Regex(
            @"(?:IComponent\s*<\s*GameObject\s*>\s*\.)?XDidYToZ\s*(?<paren>\()",
            RegexOptions.Compiled);
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;

        foreach (Match m in callRx.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count < 4)
                continue;

            var who = args[0].Expression.Trim();
            var obj = args[3].Expression.Trim();
            if (!IsSafeReceiver(who) || !IsSafeReceiver(obj) ||
                !TryStringValue(content, args[1], m.Index, out var verb) || !IsSafeVerb(verb))
                continue;

            var prep = "";
            if (args[2].Expression.Trim() != "null" &&
                (!TryStringValue(content, args[2], m.Index, out prep) || prep.Length > 40))
                continue;

            string extra = "";
            string? extraExpr = null;
            string endMark = "";
            string? colorGood = null;
            string? colorBad = null;
            var fromDialog = false;
            var ok = true;
            for (var i = 4; i < args.Count; i++)
            {
                var a = args[i];
                if (a.Name is not null)
                {
                    switch (a.Name)
                    {
                        case "ColorAsGoodFor": colorGood = a.Expression.Trim(); break;
                        case "ColorAsBadFor": colorBad = a.Expression.Trim(); break;
                        case "FromDialog": fromDialog = a.Expression.Trim() == "true"; break;
                        case "PossessiveObject":
                        case "UseFullNames":
                        case "IndefiniteSubject":
                        case "DescribeSubjectDirection":
                        case "DescribeSubjectDirectionLate":
                        case "AlwaysVisible":
                        case "SubjectPossessedBy":
                            break;
                        default: ok = false; break;
                    }
                    if (!ok) break;
                    continue;
                }
                var expr = a.Expression.Trim();
                if (expr is "null" or "true" or "false" || IsSafeReceiver(expr)) continue;
                if (TryStringValue(content, a, m.Index, out var lit))
                {
                    if (lit.Length <= 3 && IsPunctuationEndMark(lit) && endMark.Length == 0)
                    {
                        endMark = lit;
                        continue;
                    }
                    if (extra.Length == 0)
                    {
                        extra = " " + lit;
                        continue;
                    }
                }
                if (extra.Length == 0 && extraExpr is null)
                    extraExpr = expr;
                else
                    ok = false;
                if (!ok) break;
            }
            if (!ok) continue;

            var template = $"=subject.Does:{verb}=";
            if (prep.Length > 0) template += " " + prep;
            template += " =object.the.name=" + extra;
            if (extraExpr is not null) template += " =extra=";
            template += endMark;
            var replaceStart = ReplaceStartForCall(content, m, "XDidYToZ");
            sb.Append(content, last, replaceStart - last);
            sb.Append('"').Append(template).Append("\".StartReplace().SetSubject(")
                .Append(who).Append(").SetObject(").Append(obj).Append(')');
            if (extraExpr is not null)
                sb.Append(".SetArgument(\"extra\", ").Append(extraExpr).Append(')');
            var emitArgs = new List<string>();
            if (fromDialog) emitArgs.Add("FromDialog: true");
            if (colorGood is not null) emitArgs.Add("ColorAsGoodFor: " + colorGood);
            if (colorBad is not null) emitArgs.Add("ColorAsBadFor: " + colorBad);
            sb.Append(emitArgs.Count == 0
                ? ".EmitMessage()"
                : ".EmitMessage(" + string.Join(", ", emitArgs) + ")");
            last = close + 1;
            localEdits++;
        }

        if (localEdits == 0)
            return content;
        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixGetVerb(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?<recv>(?:this\.)?\w+(?:\.\w+)*)\.GetVerb\s*(?<paren>\()",
            RegexOptions.Compiled);
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;
        foreach (Match m in rx.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var recv = m.Groups["recv"].Value;
            if (!IsSafeReceiver(recv)) continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count == 0 || !TryStringLit(args[0], out var verb) || !IsSafeToken(verb))
                continue;
            sb.Append(content, last, m.Index - last);
            sb.Append("\"=object.verb:").Append(verb).Append("=\".StartReplace().SetObject(")
                .Append(recv).Append(").ToString()");
            last = close + 1;
            localEdits++;
        }
        if (localEdits == 0) return content;
        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static string FixInitLowerIfArticle(string content, ref int edits)
    {
        var rx = new Regex(
            @"Grammar\.InitLowerIfArticle\s*(?<paren>\()",
            RegexOptions.Compiled);
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;
        foreach (Match m in rx.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count != 1) continue;
            var expr = args[0].Expression.Trim();
            if (string.IsNullOrEmpty(expr)) continue;
            sb.Append(content, last, m.Index - last);
            sb.Append("\"=text|initLowerIfArticle=\".StartReplace().SetArgument(\"text\", ")
                .Append(expr).Append(").ToString()");
            last = close + 1;
            localEdits++;
        }
        if (localEdits == 0) return content;
        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    static readonly Regex PronounProp = new(
        @"(?<recv>(?:this|[A-Za-z_]\w*)(?:\.[A-Za-z_]\w*)*(?:\[[^\]\r\n]+\])?)\.(?<prop>a|A|the|The|its|Its|it|It|itself|Itself|them|Them|itis|Itis|Is)\b(?!\s*\()",
        RegexOptions.Compiled);

    // Prior Apply bug: XRL.The (static) → "=object.The=".StartReplace().SetObject(XRL).ToString()
    static readonly Regex MangledXrlThe = new(
        @"""=object\.The=""\.StartReplace\(\)\.SetObject\(XRL\)\.ToString\(\)",
        RegexOptions.Compiled);

    static string RepairMangledXrlThe(string content, ref int edits)
    {
        var local = 0;
        var next = MangledXrlThe.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index))
                return m.Value;
            local++;
            return "XRL.The";
        });
        edits += local;
        return next;
    }

    static string FixPronounProperties(string content, ref int edits)
    {
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;
        foreach (Match m in PronounProp.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var recv = m.Groups["recv"].Value;
            var prop = m.Groups["prop"].Value;
            if (!IsSafeReceiver(recv)) continue;
            if (HitFilter.IsPronounEnumName(recv)) continue;
            if (HitFilter.IsCaseLabelOrAssignment(content, m.Index, m.Index + m.Length) &&
                !IsTernaryArm(content, m.Index, m.Index + m.Length))
                continue;
            // Match obsolete_api_dump GameObject.The/the searchPattern (?![.=:#]):
            // XRL.The.Game / XRL.The.Player are the static helper, not article props.
            if (IsContinuedMemberAccessOrGameText(content, m.Index + m.Length))
                continue;
            // FQN namespace receiver — never a GameObject holding .The/.the articles.
            if ((prop is "The" or "the") && recv is "XRL")
                continue;
            if (prop == "Is" && !LooksLikeGameObjectRecv(recv))
                continue;
            var token = PronounToken(prop);
            if (token is null) continue;
            sb.Append(content, last, m.Index - last);
            sb.Append('"').Append(token).Append("\".StartReplace().SetObject(")
                .Append(recv).Append(").ToString()");
            last = m.Index + m.Length;
            localEdits++;
        }
        if (localEdits == 0) return content;
        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }

    /// <summary>
    /// True when the match is followed by <c>.</c>/<c>=</c>/<c>:</c>/<c>#</c> — same
    /// exclusions as dump patterns for GameObject article properties.
    /// </summary>
    static bool IsContinuedMemberAccessOrGameText(string content, int afterMatch)
    {
        if (afterMatch < 0 || afterMatch >= content.Length) return false;
        return content[afterMatch] is '.' or '=' or ':' or '#';
    }

    static bool IsTernaryArm(string content, int expressionStart, int expressionEnd)
    {
        var after = expressionEnd;
        while (after < content.Length && char.IsWhiteSpace(content[after])) after++;
        if (after >= content.Length || content[after] != ':') return false;
        var lineStart = content.LastIndexOf('\n', Math.Max(0, expressionStart - 1));
        return content.IndexOf('?', lineStart + 1, expressionStart - lineStart - 1) >= 0;
    }

    static string? PronounToken(string prop) => prop switch
    {
        "a" => "=object.a=",
        "A" => "=object.A=",
        "the" => "=object.the=",
        "The" => "=object.The=",
        "its" => "=object.its=",
        "Its" => "=object.Its=",
        "it" => "=object.they=",
        "It" => "=object.They=",
        "itself" => "=object.itself=",
        "Itself" => "=object.itself=",
        "them" => "=object.them=",
        "Them" => "=object.Them=",
        "itis" => "=object.itis=",
        "Itis" => "=object.Itis=",
        "Is" => "=object.verb:are=",
        _ => null,
    };

    static bool LooksLikeGameObjectRecv(string recv)
    {
        var leaf = recv.Contains('.') ? recv[(recv.LastIndexOf('.') + 1)..] : recv;
        return leaf is "ParentObject" or "Object" or "GO" or "gameObject" or "GameObject"
            or "Actor" or "Target" or "who" or "Subject" or "Defender" or "Attacker"
            or "E.Object" or "item" or "Item";
    }

    static bool IsPunctuationEndMark(string lit) =>
        lit is "!" or "." or "?" or "…" or "!." or "..." or "";

    static string FixPossInConcat(string content, ref int edits)
    {
        var local = 0;
        var next = PossInConcat.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index))
                return m.Value;
            var recv = m.Groups["recv"].Value;
            var word = m.Groups["word"].Value;
            if (!IsSafeReceiver(recv) || !IsSafeToken(word))
                return m.Value;
            // Avoid double-fixing sites already handled by PossConcat
            var after = m.Index + m.Length;
            if (after < content.Length)
            {
                var rest = content[after..Math.Min(content.Length, after + 8)].TrimStart();
                if (rest.StartsWith("+", StringComparison.Ordinal))
                    return m.Value; // leave complex chains
            }
            local++;
            var pre = m.Groups["pre"].Value;
            return $"\"{pre}=subject.poss:{word}=\".StartReplace().SetSubject({recv}).ToString()";
        });
        edits += local;
        return next;
    }

    static bool TryStringLit(CallArgParser.Arg a, out string lit)
    {
        lit = "";
        var e = a.Expression.Trim();
        if (e.Length < 2 || e[0] != '"') return false;
        var i = 1;
        var sb = new StringBuilder();
        while (i < e.Length)
        {
            if (e[i] == '\\' && i + 1 < e.Length)
            {
                sb.Append(e[i + 1]);
                i += 2;
                continue;
            }
            if (e[i] == '"')
            {
                if (i != e.Length - 1) return false;
                lit = sb.ToString();
                return true;
            }
            sb.Append(e[i]);
            i++;
        }
        return false;
    }

    /// <summary>Accept a literal or a nearby local initialized from one.</summary>
    static bool TryStringValue(
        string content, CallArgParser.Arg arg, int callIndex, out string value)
    {
        if (TryStringLit(arg, out value))
            return true;

        var name = arg.Expression.Trim();
        if (!Regex.IsMatch(name, @"^[A-Za-z_]\w*$"))
            return false;
        var start = Math.Max(0, callIndex - 800);
        var window = content[start..callIndex];
        var declaration = new Regex(
            @"\b(?:string|var)\s+" + Regex.Escape(name) +
            @"\s*=\s*(?<literal>""(?:[^""\\]|\\.)*"")\s*;",
            RegexOptions.Compiled).Matches(window).Cast<Match>().LastOrDefault();
        if (declaration is null)
            return false;

        var afterDeclaration = window[(declaration.Index + declaration.Length)..];
        if (afterDeclaration.IndexOf('}') >= 0 ||
            Regex.IsMatch(afterDeclaration, @"\b" + Regex.Escape(name) + @"\s*="))
            return false;
        return TryStringLit(new CallArgParser.Arg(null, declaration.Groups["literal"].Value), out value);
    }

    static string RemoveNowUnusedMessageLocals(string content, ref int edits)
    {
        var rx = new Regex(
            @"(?m)^[ \t]*(?:string|var)\s+(?<name>(?:verb|extra|termi(?:p|pun)?|preposition)[A-Za-z0-9_]*)\s*=\s*""(?:[^""\\]|\\.)*""\s*;[ \t]*(?<eol>\r?\n|$)",
            RegexOptions.Compiled | RegexOptions.IgnoreCase);
        var local = 0;
        var next = rx.Replace(content, m =>
        {
            var name = m.Groups["name"].Value;
            var declarations = Regex.Matches(content,
                @"\b(?:string|var)\s+" + Regex.Escape(name) +
                @"\s*=\s*""(?:[^""\\]|\\.)*""\s*;").Count;
            if (Regex.Matches(content, @"\b" + Regex.Escape(name) + @"\b").Count != declarations)
                return m.Value;
            local++;
            return m.Groups["eol"].Value;
        });
        edits += local;
        return next;
    }

    static bool IsSafeToken(string verb) =>
        Regex.IsMatch(verb, @"^[A-Za-z][\w\-]*$");

    static bool IsSafeVerb(string verb) =>
        verb.Length > 0 && char.IsLetter(verb[0]) &&
        verb.All(c => char.IsLetterOrDigit(c) || c is ' ' or '_' or '-' or '\'');

    static bool TryColorChar(string value, out char color)
    {
        color = default;
        if (value.Length == 1)
        {
            color = value[0];
            return true;
        }
        if (value.Length == 2 && value[0] == '&')
        {
            color = value[1];
            return true;
        }
        return false;
    }

    static string EscapeCharLiteral(char value) => value switch
    {
        '\\' => "\\\\",
        '\'' => "\\'",
        '\n' => "\\n",
        '\r' => "\\r",
        '\t' => "\\t",
        _ => value.ToString(),
    };

    static bool IsIgnorableDidXPositional(string expr)
    {
        if (string.IsNullOrWhiteSpace(expr)) return false;
        var t = expr.Trim();
        if (t is "null" or "true" or "false" or "this") return true;
        if (t is "this.ParentObject" or "ParentObject") return true;
        if (t.Length >= 2 && t[0] == '"' && t[^1] == '"' && t.Length <= 6)
            return true; // "&R", "", "!"
        return false;
    }

    static string FixPronounNameConcat(string content, ref int edits)
    {
        // After pronoun rewrite: "=object.The=".StartReplace().SetObject(X).ToString() + X.DisplayName
        // → "=object.The.name=".StartReplace().SetObject(X).ToString()
        var rx = new Regex(
            @"""=object\.(?<art>The|the)=""\.StartReplace\(\)\.SetObject\((?<recv>[^)]+)\)\.ToString\(\)\s*\+\s*\k<recv>\.(?:DisplayNameOnly(?:Direct)?|DisplayName|ShortDisplayName(?:WithoutTitles)?)\b",
            RegexOptions.Compiled);
        var local = 0;
        var next = rx.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index))
                return m.Value;
            local++;
            var art = m.Groups["art"].Value;
            var recv = m.Groups["recv"].Value;
            return $"\"=object.{art}.name=\".StartReplace().SetObject({recv}).ToString()";
        });
        edits += local;
        return next;
    }

    static string FixTargetSelfConfirm(string content, ref int edits)
    {
        if (content.IndexOf(".itself", StringComparison.Ordinal) < 0 ||
            content.IndexOf("ShowYesNoCancel", StringComparison.Ordinal) < 0)
            return content;

        var rx = new Regex(
            @"Popup\.ShowYesNoCancel\s*\(\s*""Are you sure you want to target ""\s*\+\s*(?<recv>[\w\.]+)\.itself\s*\+\s*""\?""\s*,[^;]{0,400}?\)\s*!=\s*DialogResult\.Yes",
            RegexOptions.Compiled);
        var local = 0;
        var next = rx.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index))
                return m.Value;
            var recv = m.Groups["recv"].Value;
            var component = InferTargetSelfComponent(recv);
            local++;
            return $"!{component}.TargetSelfConfirm()";
        });
        edits += local;
        return next;
    }

    static string InferTargetSelfComponent(string parentObjectRecv)
    {
        if (parentObjectRecv == "ParentObject" || parentObjectRecv == "this.ParentObject")
            return "this";
        const string suffix = ".ParentObject";
        if (parentObjectRecv.EndsWith(suffix, StringComparison.Ordinal))
            return parentObjectRecv[..^suffix.Length];
        return parentObjectRecv;
    }

    static string FixSimpleDidXToY(string content, ref int edits)
    {
        var callRx = new Regex(
            @"(?<![A-Za-z0-9_])(?:(?:this|base)\.)?(?:IComponent\s*<\s*GameObject\s*>\s*\.)?DidXToY\s*(?<paren>\()",
            RegexOptions.Compiled);
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var localEdits = 0;

        foreach (Match m in callRx.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;
            var open = m.Groups["paren"].Index;
            if (!CallArgParser.TryParseArgumentList(content, open, out var args, out var close))
                continue;
            if (args.Count < 2 ||
                !TryStringValue(content, args[0], m.Index, out var verb) || !IsSafeVerb(verb))
                continue;
            var prep = "";
            var objectIndex = 1;
            var obj = args[objectIndex].Expression.Trim();
            if (!IsSafeReceiver(obj) && args.Count >= 3 &&
                TryStringValue(content, args[1], m.Index, out prep))
            {
                objectIndex = 2;
                obj = args[objectIndex].Expression.Trim();
            }
            if (!IsSafeReceiver(obj))
                continue;
            var extra = "";
            var endMark = "";
            string? colorGood = null;
            string? colorBad = null;
            var fromDialog = false;
            var ok = true;
            for (var i = objectIndex + 1; i < args.Count; i++)
            {
                var a = args[i];
                if (a.Name is not null)
                {
                    switch (a.Name)
                    {
                        case "FromDialog": fromDialog = a.Expression.Trim() == "true"; break;
                        case "ColorAsGoodFor": colorGood = a.Expression.Trim(); break;
                        case "ColorAsBadFor": colorBad = a.Expression.Trim(); break;
                        case "PossessiveObject":
                        case "UseFullNames":
                        case "IndefiniteSubject":
                        case "DescribeSubjectDirection":
                        case "DescribeSubjectDirectionLate":
                        case "AlwaysVisible":
                            break;
                        default: ok = false; break;
                    }
                    if (!ok) break;
                    continue;
                }
                var expr = a.Expression.Trim();
                if (expr is "null" or "true" or "false" || IsSafeReceiver(expr))
                    continue;
                if (TryStringValue(content, a, m.Index, out var lit))
                {
                    if (lit.Length <= 3 && IsPunctuationEndMark(lit))
                        endMark = lit;
                    else if (extra.Length == 0)
                        extra = " " + lit;
                    else
                        ok = false;
                    if (!ok) break;
                    continue;
                }
                ok = false;
                break;
            }
            if (!ok) continue;

            var identIndex = CallIdentIndex(m, "DidXToY");
            var replaceStart = Math.Min(m.Index, DottedReceiverStart(content, identIndex));
            var subject = InferDidXSubject(content, m.Index, ReceiverChain(content, replaceStart, identIndex));
            sb.Append(content, last, replaceStart - last);
            sb.Append("\"=subject.Does:").Append(verb)
                .Append("=");
            if (prep.Length > 0) sb.Append(' ').Append(prep);
            sb.Append(" =object.the.name=").Append(extra).Append(endMark)
                .Append("\".StartReplace().SetSubject(")
                .Append(subject).Append(").SetObject(").Append(obj).Append(')');
            var emitArgs = new List<string>();
            if (fromDialog) emitArgs.Add("FromDialog: true");
            if (colorGood is not null) emitArgs.Add("ColorAsGoodFor: " + colorGood);
            if (colorBad is not null) emitArgs.Add("ColorAsBadFor: " + colorBad);
            sb.Append(emitArgs.Count == 0
                ? ".EmitMessage()"
                : ".EmitMessage(" + string.Join(", ", emitArgs) + ")");
            last = close + 1;
            localEdits++;
        }

        if (localEdits == 0) return content;
        edits += localEdits;
        sb.Append(content, last, content.Length - last);
        return sb.ToString();
    }
}
