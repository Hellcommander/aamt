using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Merge named child elements into a game XML overlay (Liquids / Statistics / InventoryActions).
/// Existing same-Name children are left alone (hand-tuned overlays win).
/// </summary>
public static class XmlOverlayMerger
{
    public static string XmlEscape(string text)
    {
        if (string.IsNullOrEmpty(text)) return "";
        return text
            .Replace("&", "&amp;")
            .Replace("<", "&lt;")
            .Replace(">", "&gt;")
            .Replace("\"", "&quot;");
    }

    /// <summary>
    /// Insert <paramref name="children"/> (Name attribute + inner XML) before the root close tag.
    /// Skips a child when that Name already exists in <paramref name="existing"/>.
    /// </summary>
    public static string MergeNamedChildren(
        string? existing,
        string rootName,
        string childName,
        IReadOnlyList<(string Name, string InnerXml)> children)
    {
        if (children == null || children.Count == 0)
            return existing ?? "";

        var root = string.IsNullOrWhiteSpace(rootName) ? "root" : rootName.Trim();
        var child = string.IsNullOrWhiteSpace(childName) ? "item" : childName.Trim();
        var working = string.IsNullOrWhiteSpace(existing)
            ? $"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<{root} Encoding=\"utf-8\">\n</{root}>\n"
            : existing;

        var nameRx = new Regex(
            $@"<\s*{Regex.Escape(child)}\b[^>]*\bName\s*=\s*(?<q>['""])(?<n>[^'""]*)\k<q>",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        var have = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in nameRx.Matches(working))
            have.Add(m.Groups["n"].Value);

        var sb = new StringBuilder();
        var added = 0;
        foreach (var (name, inner) in children)
        {
            if (string.IsNullOrWhiteSpace(name) || !have.Add(name))
                continue;
            sb.Append("  <").Append(child).Append(" Name=\"").Append(XmlEscape(name)).Append("\">\n");
            sb.Append(inner);
            if (inner.Length > 0 && inner[^1] != '\n')
                sb.Append('\n');
            sb.Append("  </").Append(child).Append(">\n");
            added++;
        }

        if (added == 0)
            return working;

        var closeRx = new Regex(@"</\s*" + Regex.Escape(root) + @"\s*>",
            RegexOptions.IgnoreCase);
        var close = closeRx.Match(working);
        if (!close.Success)
            return working.TrimEnd() + "\n" + sb + $"</{root}>\n";

        return working[..close.Index] + sb + working[close.Index..];
    }

    /// <summary>
    /// When a named child already exists, insert any incoming top-level elements that the
    /// existing block lacks. Never overwrites hand-tuned values. Empty <c>&lt;render /&gt;</c>
    /// is replaced when incoming has a populated render block.
    /// </summary>
    public static string MergeMissingInner(
        string existing,
        string childName,
        string name,
        string innerXml)
    {
        if (string.IsNullOrWhiteSpace(existing) ||
            string.IsNullOrWhiteSpace(name) ||
            string.IsNullOrWhiteSpace(innerXml))
            return existing;

        if (!TryFindNamedElement(existing, childName, name,
                out _, out var innerStart, out var innerEnd, out _))
            return existing;

        var blockInner = existing[innerStart..innerEnd];
        var incoming = ParseTopLevelElements(innerXml);
        if (incoming.Count == 0)
            return existing;

        var workingInner = blockInner;
        var changed = false;

        foreach (var frag in incoming)
        {
            if (string.Equals(frag.Tag, "render", StringComparison.OrdinalIgnoreCase) &&
                HasRenderChildren(frag.Outer) &&
                TryReplaceEmptyRender(ref workingInner, frag.Outer))
            {
                changed = true;
                continue;
            }

            if (InnerHasFragment(workingInner, frag))
                continue;

            workingInner = InsertBeforeClose(workingInner, frag.Outer);
            changed = true;
        }

        if (!changed)
            return existing;

        return existing[..innerStart] + workingInner + existing[innerEnd..];
    }

    public static bool TryFindNamedElement(
        string xml, string childName, string name,
        out int openStart, out int innerStart, out int innerEnd, out int closeEnd)
    {
        openStart = innerStart = innerEnd = closeEnd = -1;
        if (string.IsNullOrEmpty(xml)) return false;

        var openRx = new Regex(
            $@"<\s*{Regex.Escape(childName)}\b(?<attrs>[^>]*)>",
            RegexOptions.IgnoreCase);
        foreach (Match m in openRx.Matches(xml))
        {
            var attrs = m.Groups["attrs"].Value;
            if (attrs.TrimEnd().EndsWith("/", StringComparison.Ordinal))
                continue;
            var nm = Regex.Match(attrs, @"\bName\s*=\s*(?<q>['""])(?<n>[^'""]*)\k<q>",
                RegexOptions.IgnoreCase);
            if (!nm.Success || !string.Equals(nm.Groups["n"].Value, name, StringComparison.OrdinalIgnoreCase))
                continue;

            var gt = m.Index + m.Length - 1;
            if (!TryFindMatchingXmlClose(xml, m.Index, childName, out var closeLt, out var closeEndLocal))
                continue;

            openStart = m.Index;
            innerStart = gt + 1;
            innerEnd = closeLt;
            closeEnd = closeEndLocal;
            return true;
        }
        return false;
    }

    static bool TryFindMatchingXmlClose(string xml, int openLt, string tag, out int closeLt, out int closeEnd)
    {
        closeLt = closeEnd = -1;
        var depth = 0;
        var i = openLt;
        while (i < xml.Length)
        {
            var lt = xml.IndexOf('<', i);
            if (lt < 0) return false;
            if (lt + 1 >= xml.Length) return false;
            if (xml[lt + 1] == '!')
            {
                if (lt + 3 < xml.Length && xml[lt + 2] == '-' && xml[lt + 3] == '-')
                {
                    var dash = xml.IndexOf("-->", lt, StringComparison.Ordinal);
                    i = dash < 0 ? xml.Length : dash + 3;
                }
                else if (lt + 8 < xml.Length &&
                         xml.AsSpan(lt).StartsWith("<![CDATA[", StringComparison.Ordinal))
                {
                    var end = xml.IndexOf("]]>", lt, StringComparison.Ordinal);
                    i = end < 0 ? xml.Length : end + 3;
                }
                else
                {
                    var gtDecl = xml.IndexOf('>', lt);
                    i = gtDecl < 0 ? xml.Length : gtDecl + 1;
                }
                continue;
            }
            var isClose = xml[lt + 1] == '/';
            var nameStart = isClose ? lt + 2 : lt + 1;
            var nameEnd = nameStart;
            while (nameEnd < xml.Length && (char.IsLetterOrDigit(xml[nameEnd]) || xml[nameEnd] is '_' or '-'))
                nameEnd++;
            var name = xml[nameStart..nameEnd];
            var gt = xml.IndexOf('>', nameEnd);
            if (gt < 0) return false;
            var selfClose = xml[gt - 1] == '/';

            if (name.Equals(tag, StringComparison.OrdinalIgnoreCase))
            {
                if (isClose)
                {
                    depth--;
                    if (depth == 0)
                    {
                        closeLt = lt;
                        closeEnd = gt + 1;
                        return true;
                    }
                }
                else if (!selfClose)
                    depth++;
            }
            i = gt + 1;
        }
        return false;
    }

    sealed record XmlFrag(string Tag, string? NameAttr, string Outer);

    static List<XmlFrag> ParseTopLevelElements(string innerXml)
    {
        var list = new List<XmlFrag>();
        var i = 0;
        while (i < innerXml.Length)
        {
            var lt = innerXml.IndexOf('<', i);
            if (lt < 0) break;
            if (lt + 1 < innerXml.Length && innerXml[lt + 1] == '/')
            {
                i = lt + 1;
                continue;
            }
            var nameStart = lt + 1;
            var nameEnd = nameStart;
            while (nameEnd < innerXml.Length && (char.IsLetterOrDigit(innerXml[nameEnd]) || innerXml[nameEnd] is '_' or '-'))
                nameEnd++;
            if (nameEnd == nameStart)
            {
                i = lt + 1;
                continue;
            }
            var tag = innerXml[nameStart..nameEnd];
            var gt = innerXml.IndexOf('>', nameEnd);
            if (gt < 0) break;
            var sliceEnd = innerXml[gt - 1] == '/' ? gt + 1
                : TryFindMatchingXmlClose(innerXml, lt, tag, out _, out var closeEnd) ? closeEnd
                : -1;
            if (sliceEnd < 0)
            {
                i = gt + 1;
                continue;
            }
            var outer = innerXml[lt..sliceEnd];

            var nameM = Regex.Match(outer, @"\bName\s*=\s*(?<q>['""])(?<n>[^'""]*)\k<q>",
                RegexOptions.IgnoreCase);
            list.Add(new XmlFrag(tag, nameM.Success ? nameM.Groups["n"].Value : null, outer.Trim()));
            i = sliceEnd;
        }
        return list;
    }

    static bool InnerHasFragment(string inner, XmlFrag frag)
    {
        if (string.Equals(frag.Tag, "part", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(frag.Tag, "stainElement", StringComparison.OrdinalIgnoreCase))
        {
            if (string.IsNullOrEmpty(frag.NameAttr))
                return Regex.IsMatch(inner, $@"<\s*{Regex.Escape(frag.Tag)}\b", RegexOptions.IgnoreCase);
            return Regex.IsMatch(inner,
                $@"<\s*{Regex.Escape(frag.Tag)}\b[^>]*\bName\s*=\s*(['""]){Regex.Escape(frag.NameAttr)}\1",
                RegexOptions.IgnoreCase);
        }

        return Regex.IsMatch(inner, $@"<\s*{Regex.Escape(frag.Tag)}\b", RegexOptions.IgnoreCase);
    }

    static bool HasRenderChildren(string outer) =>
        Regex.IsMatch(outer, @"<\s*render\b[^>]*>[\s\S]*?<\s*\w", RegexOptions.IgnoreCase);

    static bool TryReplaceEmptyRender(ref string inner, string incomingRender)
    {
        var empty = new Regex(@"<\s*render\s*/>|<\s*render\s*>\s*</\s*render\s*>",
            RegexOptions.IgnoreCase);
        var m = empty.Match(inner);
        if (!m.Success) return false;
        inner = inner[..m.Index] + incomingRender.Trim() + inner[(m.Index + m.Length)..];
        return true;
    }

    static string InsertBeforeClose(string inner, string fragment)
    {
        var trimmed = fragment.Trim();
        if (!trimmed.EndsWith('\n'))
            trimmed += "\n";
        if (!trimmed.StartsWith("    ", StringComparison.Ordinal))
            trimmed = "    " + trimmed;
        return inner.TrimEnd() + "\n" + trimmed;
    }
}
