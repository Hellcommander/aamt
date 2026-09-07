using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// ObjectBlueprintLoader resolves <c>&lt;part Name="X"/&gt;</c> via
/// <c>ModManager.ResolveType("XRL.World.Parts", "X")</c> → exact type
/// <c>XRL.World.Parts.X</c>. IPart classes in a custom namespace
/// (e.g. <c>COQMAN.HiddenHamlet.COQMAN_SurfaceElderTracker</c>) produce:
/// <c>Could not find XRL.World.Parts.X, element ignored</c> and the related
/// "Unnamed part nodes detected" WARN (failed load returns an empty child node).
/// Same pattern for mutations (<c>XRL.World.Parts.Mutation</c>) and object
/// builders (<c>XRL.World.ObjectBuilders</c>).
/// </summary>
public static class BlueprintTypeNamespaceFixer
{
    public const string FixRuleNamePart = "IPart namespace → XRL.World.Parts (XML ResolveType)";
    public const string FixRuleNameMutation = "mutation namespace → XRL.World.Parts.Mutation";
    public const string FixRuleNameBuilder = "object-builder namespace → XRL.World.ObjectBuilders";
    public const string FixRuleNameUsing = "ensure using for moved blueprint types";
    public const string FixRuleNamePartialSync =
        "partial class namespace → match moved IPart/mutation/builder";

    public const string PartsNs = "XRL.World.Parts";
    public const string MutationNs = "XRL.World.Parts.Mutation";
    public const string ObjectBuildersNs = "XRL.World.ObjectBuilders";

    static readonly Regex NamespaceBlockRx = new(
        @"\bnamespace\s+(?<ns>[A-Za-z_][\w.]*)\s*(?<body>\{)",
        RegexOptions.Compiled);

    static readonly Regex ClassDeclRx = new(
        @"\b(?:public|internal)\s+(?:(?:abstract|sealed|partial|static)\s+)*class\s+(?<name>[A-Za-z_]\w*)\s*(?::\s*(?<bases>[^\{]+))?",
        RegexOptions.Compiled);

    static readonly Regex MutationBaseRx = new(
        @"\b(?:BaseMutation|IMutation|MutationBase)\b",
        RegexOptions.Compiled);

    static readonly Regex PartBaseRx = new(
        @"\bIPart\b",
        RegexOptions.Compiled);

    static readonly Regex ObjectBuilderBaseRx = new(
        @"\b(?:IObjectBuilder|ObjectBuilder)\b",
        RegexOptions.Compiled);

    public sealed class ModFixResult
    {
        public Dictionary<string, string> UpdatedContents { get; } = new(StringComparer.OrdinalIgnoreCase);
        public List<(string File, AppliedFix Fix)> Fixes { get; } = new();
    }

    /// <summary>
    /// Mod-scoped pass: rewrite wrong namespaces for XML-resolvable types, sync
    /// sibling <c>partial class</c> files that lack a base list (so they were not
    /// classified as IPart/mutation), then ensure sibling .cs files can still
    /// compile (add target usings).
    /// </summary>
    /// <remarks>
    /// Broodmother-style splits declare <c>: IPart</c> only on the Core partial;
    /// other files are <c>partial class Name</c> with Kind=Other and stayed in the
    /// old namespace — that produced hundreds of CS0103 / CS0311. After any type is
    /// moved, every namespace block whose top-level types are all among those moved
    /// types (same target ns) is rewritten to match.
    /// </remarks>
    public static ModFixResult FixMod(IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new ModFixResult();
        if (pathToContent == null || pathToContent.Count == 0) return result;

        var working = new Dictionary<string, string>(pathToContent, StringComparer.OrdinalIgnoreCase);
        var moved = new Dictionary<string, string>(StringComparer.Ordinal); // type → target ns
        var movedFrom = new Dictionary<string, string>(StringComparer.Ordinal); // type → old ns

        foreach (var path in working.Keys.ToList())
        {
            var (next, fixes, movedHere) = FixFile(working[path]);
            if (fixes.Count == 0) continue;

            working[path] = next;
            result.UpdatedContents[path] = next;
            foreach (var f in fixes)
                result.Fixes.Add((path, f));
            foreach (var (typeName, ns) in movedHere)
                moved[typeName] = ns;
        }

        // Capture old namespaces from pre-fix content for FQN rewrites / partial sync.
        foreach (var path in pathToContent.Keys)
        {
            if (!pathToContent.TryGetValue(path, out var original) || string.IsNullOrEmpty(original))
                continue;
            foreach (Match m in NamespaceBlockRx.Matches(original))
            {
                if (HitFilter.IsInsideComment(original, m.Index) ||
                    HitFilter.IsInsideStringLiteral(original, m.Index))
                    continue;
                var nsName = m.Groups["ns"].Value;
                var braceOpen = m.Groups["body"].Index;
                var braceClose = FindMatchingBrace(original, braceOpen);
                if (braceClose < 0) continue;
                var body = original.Substring(braceOpen + 1, braceClose - braceOpen - 1);
                foreach (var c in ClassifyPublicClasses(body))
                {
                    if (moved.ContainsKey(c.Name) && !movedFrom.ContainsKey(c.Name))
                        movedFrom[c.Name] = nsName;
                }
            }
        }

        if (moved.Count == 0) return result;

        SyncPartialClassNamespaces(working, result, moved);

        // Rewrite OldNs.TypeName FQNs inside this mod (other mods still need a hand fix /
        // short name + using — we cannot rewrite across mod folders here).
        RewriteMovedTypeFqns(working, result, moved, movedFrom);

        // Group moved types by target namespace for using insertion.
        var byNs = moved.GroupBy(kv => kv.Value, StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.Select(x => x.Key).ToHashSet(StringComparer.Ordinal),
                StringComparer.Ordinal);

        foreach (var path in working.Keys.ToList())
        {
            var content = working[path];
            var fileFixes = new List<AppliedFix>();
            var next = content;

            foreach (var (ns, typeNames) in byNs)
            {
                if (!ReferencesAnyType(next, typeNames)) continue;
                if (HasUsing(next, ns)) continue;

                // Always insert when needed. A file may declare XRL.World.Parts *and*
                // still host helpers in another namespace (trailing IPart split) that need
                // the using. Redundant `using` on an all-Parts file is harmless.

                var (withUsing, inserted) = UsingInserter.EnsureUsings(next, new[] { ns });
                if (inserted.Count == 0) continue;
                next = withUsing;
                fileFixes.Add(new AppliedFix { RuleName = FixRuleNameUsing + $" ({ns})", Count = inserted.Count });
            }

            if (fileFixes.Count == 0) continue;
            working[path] = next;
            result.UpdatedContents[path] = next;
            foreach (var f in fileFixes)
                result.Fixes.Add((path, f));
        }

        return result;
    }

    /// <summary>
    /// After a primary <c>: IPart</c> / mutation / builder file moved, pull sibling
    /// <c>partial class</c> files (no base list → Kind=Other) into the same target ns.
    /// </summary>
    static void SyncPartialClassNamespaces(
        Dictionary<string, string> working,
        ModFixResult result,
        Dictionary<string, string> moved)
    {
        foreach (var path in working.Keys.ToList())
        {
            var content = working[path];
            if (string.IsNullOrEmpty(content)) continue;

            var edits = new List<(int NameStart, int NameLen, string NewNs)>();
            var syncCount = 0;

            foreach (Match m in NamespaceBlockRx.Matches(content))
            {
                if (HitFilter.IsInsideComment(content, m.Index) ||
                    HitFilter.IsInsideStringLiteral(content, m.Index))
                    continue;

                var nsName = m.Groups["ns"].Value;
                var braceOpen = m.Groups["body"].Index;
                var braceClose = FindMatchingBrace(content, braceOpen);
                if (braceClose < 0) continue;

                var body = content.Substring(braceOpen + 1, braceClose - braceOpen - 1);
                var classes = ClassifyPublicClasses(body);
                if (classes.Count == 0) continue;

                // Every top-level type in this block must be one we already moved,
                // and they must all share one target namespace.
                string? target = null;
                var allMoved = true;
                foreach (var c in classes)
                {
                    if (!moved.TryGetValue(c.Name, out var dest))
                    {
                        allMoved = false;
                        break;
                    }
                    if (target == null) target = dest;
                    else if (!target.Equals(dest, StringComparison.Ordinal))
                    {
                        allMoved = false;
                        break;
                    }
                }

                if (!allMoved || target == null) continue;
                if (nsName.Equals(target, StringComparison.Ordinal)) continue;

                edits.Add((m.Groups["ns"].Index, m.Groups["ns"].Length, target));
                syncCount++;
            }

            if (edits.Count == 0) continue;

            edits.Sort((a, b) => b.NameStart.CompareTo(a.NameStart));
            var sb = new StringBuilder(content);
            foreach (var e in edits)
            {
                sb.Remove(e.NameStart, e.NameLen);
                sb.Insert(e.NameStart, e.NewNs);
            }

            var next = sb.ToString();
            working[path] = next;
            result.UpdatedContents[path] = next;
            result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleNamePartialSync, Count = syncCount }));
        }
    }

    /// <summary>
    /// Rewrite <c>OldNs.TypeName</c> → <c>TypeName</c> after a namespace move (same mod only).
    /// </summary>
    static void RewriteMovedTypeFqns(
        Dictionary<string, string> working,
        ModFixResult result,
        Dictionary<string, string> moved,
        Dictionary<string, string> movedFrom)
    {
        if (movedFrom.Count == 0) return;

        foreach (var path in working.Keys.ToList())
        {
            var content = working[path];
            if (string.IsNullOrEmpty(content)) continue;

            var next = content;
            var total = 0;
            foreach (var (typeName, oldNs) in movedFrom)
            {
                if (!moved.TryGetValue(typeName, out var newNs)) continue;
                if (oldNs.Equals(newNs, StringComparison.Ordinal)) continue;

                // ThreadingAPI.EnhancedAIMemoryPart → EnhancedAIMemoryPart (using covers new ns)
                var pattern = $@"\b{Regex.Escape(oldNs)}\.{Regex.Escape(typeName)}\b";
                var replaced = Regex.Replace(next, pattern, typeName);
                if (ReferenceEquals(replaced, next) || replaced == next) continue;
                var delta = Regex.Matches(next, pattern).Count;
                next = replaced;
                total += delta;
            }

            if (total == 0) continue;
            working[path] = next;
            result.UpdatedContents[path] = next;
            result.Fixes.Add((path, new AppliedFix
            {
                RuleName = FixRuleNameUsing + " (strip old FQN)",
                Count = total,
            }));
        }
    }

    /// <summary>Convenience overload for list-of-tuples callers.</summary>
    public static ModFixResult FixMod(IReadOnlyList<(string Path, string Content)> csFiles)
    {
        var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (csFiles != null)
        {
            foreach (var (path, content) in csFiles)
                map[path] = content ?? "";
        }
        return FixMod(map);
    }

    /// <summary>
    /// Single-file namespace rewrites (IPart-only / mutation-only / builder-only blocks).
    /// </summary>
    public static (string Content, List<AppliedFix> Fixes, List<(string Type, string TargetNs)> Moved)
        FixFile(string content)
    {
        var fixes = new List<AppliedFix>();
        var moved = new List<(string Type, string TargetNs)>();
        if (string.IsNullOrEmpty(content)) return (content, fixes, moved);

        var edits = new List<(int NsStart, int NsNameStart, int NsNameEnd, string OldNs, string NewNs, List<string> Types, string Rule)>();
        var trailingSplits = new List<(int BraceOpen, int BraceClose, int PartStartAbs, List<string> PartTypes, string OldNs)>();

        foreach (Match m in NamespaceBlockRx.Matches(content))
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                continue;

            var nsName = m.Groups["ns"].Value;
            var braceOpen = m.Groups["body"].Index;
            var braceClose = FindMatchingBrace(content, braceOpen);
            if (braceClose < 0) continue;

            var body = content.Substring(braceOpen + 1, braceClose - braceOpen - 1);
            var classes = ClassifyPublicClasses(body);
            if (classes.Count == 0) continue;

            string? target = null;
            string? rule = null;

            if (classes.All(c => c.Kind == TypeKind.Part) &&
                !nsName.Equals(PartsNs, StringComparison.Ordinal))
            {
                target = PartsNs;
                rule = FixRuleNamePart;
            }
            else if (classes.All(c => c.Kind == TypeKind.Mutation) &&
                     !nsName.Equals(MutationNs, StringComparison.Ordinal))
            {
                target = MutationNs;
                rule = FixRuleNameMutation;
            }
            else if (classes.All(c => c.Kind == TypeKind.ObjectBuilder) &&
                     !nsName.Equals(ObjectBuildersNs, StringComparison.Ordinal))
            {
                target = ObjectBuildersNs;
                rule = FixRuleNameBuilder;
            }
            else if (!nsName.Equals(PartsNs, StringComparison.Ordinal) &&
                     TryTrailingPartSplit(classes, out var splitAt))
            {
                // Helpers + trailing IPart(s) in one namespace (Scrap Grave King loadouts).
                // Close original ns before first Part class; open XRL.World.Parts for the rest.
                trailingSplits.Add((
                    braceOpen,
                    braceClose,
                    braceOpen + 1 + FindDeclStart(body, splitAt),
                    classes.Where(c => c.Kind == TypeKind.Part).Select(c => c.Name).ToList(),
                    nsName));
                continue;
            }

            if (target == null || rule == null) continue;

            edits.Add((
                m.Index,
                m.Groups["ns"].Index,
                m.Groups["ns"].Index + m.Groups["ns"].Length,
                nsName,
                target,
                classes.Select(c => c.Name).ToList(),
                rule));
        }

        if (edits.Count == 0 && trailingSplits.Count == 0) return (content, fixes, moved);

        // Apply from end so indices stay valid. Trailing splits first (same namespace is
        // never both split and renamed); shift ns-name edits by prior inserts.
        trailingSplits.Sort((a, b) => b.PartStartAbs.CompareTo(a.PartStartAbs));
        edits.Sort((a, b) => b.NsNameStart.CompareTo(a.NsNameStart));
        var sb = new StringBuilder(content);
        var ruleCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        const string partsInsert = "}\n\nnamespace XRL.World.Parts\n{\n";

        foreach (var split in trailingSplits)
        {
            sb.Insert(split.PartStartAbs, partsInsert);
            ruleCounts[FixRuleNamePart] = ruleCounts.GetValueOrDefault(FixRuleNamePart) + 1;
            foreach (var t in split.PartTypes)
                moved.Add((t, PartsNs));
        }

        foreach (var e in edits)
        {
            var shift = 0;
            foreach (var split in trailingSplits)
            {
                if (split.PartStartAbs < e.NsNameStart)
                    shift += partsInsert.Length;
            }

            var nameStart = e.NsNameStart + shift;
            var nameLen = e.NsNameEnd - e.NsNameStart;
            sb.Remove(nameStart, nameLen);
            sb.Insert(nameStart, e.NewNs);
            ruleCounts[e.Rule] = ruleCounts.GetValueOrDefault(e.Rule) + 1;
            foreach (var t in e.Types)
                moved.Add((t, e.NewNs));
        }

        var resultText = sb.ToString();

        // Always keep a using for the previous namespace: moved IParts still reference helpers /
        // types that remain in the old ns (ThreadingAPI EnhancedAIMemoryPart → CS0246 without
        // `using ThreadingAPI;`). Trailing splits already needed this; full renames do too.
        var oldNamespaces = edits.Select(e => e.OldNs)
            .Concat(trailingSplits.Select(s => s.OldNs))
            .Where(ns => !string.IsNullOrEmpty(ns))
            .Distinct(StringComparer.Ordinal)
            .ToArray();
        if (oldNamespaces.Length > 0)
        {
            var (withUsing, inserted) = UsingInserter.EnsureUsings(resultText, oldNamespaces);
            if (inserted.Count > 0)
            {
                resultText = withUsing;
                fixes.Add(new AppliedFix { RuleName = FixRuleNameUsing + " (helper ns)", Count = inserted.Count });
            }
        }

        foreach (var (rule, count) in ruleCounts)
            fixes.Add(new AppliedFix { RuleName = rule, Count = count });

        return (resultText, fixes, moved);
    }

    /// <summary>
    /// True when body has ≥1 non-Part and ≥1 Part, and every Part is after every Other
    /// (helpers first, IPart classes last). Returns body-relative index of first Part decl.
    /// </summary>
    static bool TryTrailingPartSplit(List<ClassInfo> classes, out int firstPartBodyIndex)
    {
        firstPartBodyIndex = -1;
        if (classes.Count < 2) return false;
        if (!classes.Any(c => c.Kind == TypeKind.Part)) return false;
        if (!classes.Any(c => c.Kind != TypeKind.Part)) return false;

        var seenPart = false;
        foreach (var c in classes)
        {
            if (c.Kind == TypeKind.Part)
            {
                if (!seenPart)
                {
                    firstPartBodyIndex = c.BodyIndex;
                    seenPart = true;
                }
            }
            else if (seenPart)
            {
                // Other after a Part — not a clean trailing split.
                return false;
            }
        }

        return seenPart && firstPartBodyIndex >= 0;
    }

    enum TypeKind { Other, Part, Mutation, ObjectBuilder }

    sealed class ClassInfo
    {
        public string Name { get; init; } = "";
        public TypeKind Kind { get; init; }
        /// <summary>Index of the <c>class</c> keyword within the namespace body.</summary>
        public int BodyIndex { get; init; }
    }

    static List<ClassInfo> ClassifyPublicClasses(string body)
    {
        var list = new List<ClassInfo>();
        foreach (Match m in ClassDeclRx.Matches(body))
        {
            if (HitFilter.IsInsideComment(body, m.Index) ||
                HitFilter.IsInsideStringLiteral(body, m.Index))
                continue;

            // Skip nested classes roughly: require declaration at brace depth 0 of body…
            // ClassDeclRx may match nested; count braces before match.
            if (BraceDepthAt(body, m.Index) != 0) continue;

            var name = m.Groups["name"].Value;
            var bases = m.Groups["bases"].Success ? m.Groups["bases"].Value : "";
            var kind = ClassifyBases(bases);
            list.Add(new ClassInfo { Name = name, Kind = kind, BodyIndex = m.Index });
        }
        return list;
    }

    /// <summary>Walk back over <c>[Attr]</c> stacks so they move with the class.</summary>
    static int FindDeclStart(string body, int classIndex)
    {
        var i = classIndex;
        while (true)
        {
            var j = i - 1;
            while (j >= 0 && char.IsWhiteSpace(body[j])) j--;
            if (j < 0 || body[j] != ']') return i;

            var depth = 1;
            j--;
            while (j >= 0 && depth > 0)
            {
                if (body[j] == ']') depth++;
                else if (body[j] == '[') depth--;
                j--;
            }

            i = j + 1;
        }
    }

    static TypeKind ClassifyBases(string bases)
    {
        if (string.IsNullOrWhiteSpace(bases)) return TypeKind.Other;
        if (MutationBaseRx.IsMatch(bases)) return TypeKind.Mutation;
        if (ObjectBuilderBaseRx.IsMatch(bases)) return TypeKind.ObjectBuilder;
        if (PartBaseRx.IsMatch(bases)) return TypeKind.Part;
        return TypeKind.Other;
    }

    static int FindMatchingBrace(string text, int openIndex)
    {
        if (openIndex < 0 || openIndex >= text.Length || text[openIndex] != '{') return -1;
        var depth = 0;
        for (var i = openIndex; i < text.Length; i++)
        {
            var c = text[i];
            if (c is '"' or '\'')
            {
                i = SkipString(text, i);
                continue;
            }
            if (c == '/' && i + 1 < text.Length)
            {
                if (text[i + 1] == '/')
                {
                    while (i < text.Length && text[i] != '\n') i++;
                    continue;
                }
                if (text[i + 1] == '*')
                {
                    i += 2;
                    while (i + 1 < text.Length && !(text[i] == '*' && text[i + 1] == '/')) i++;
                    i++;
                    continue;
                }
            }
            if (c == '{') depth++;
            else if (c == '}')
            {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }

    static int BraceDepthAt(string text, int index)
    {
        var depth = 0;
        for (var i = 0; i < index && i < text.Length; i++)
        {
            var c = text[i];
            if (c is '"' or '\'')
            {
                i = SkipString(text, i);
                continue;
            }
            if (c == '/' && i + 1 < text.Length)
            {
                if (text[i + 1] == '/')
                {
                    while (i < text.Length && text[i] != '\n') i++;
                    continue;
                }
                if (text[i + 1] == '*')
                {
                    i += 2;
                    while (i + 1 < text.Length && !(text[i] == '*' && text[i + 1] == '/')) i++;
                    i++;
                    continue;
                }
            }
            if (c == '{') depth++;
            else if (c == '}') depth--;
        }
        return depth;
    }

    static int SkipString(string text, int i)
    {
        var q = text[i++];
        while (i < text.Length)
        {
            if (text[i] == '\\') { i += 2; continue; }
            if (text[i] == q) return i;
            i++;
        }
        return text.Length - 1;
    }

    static bool HasUsing(string content, string ns) =>
        Regex.IsMatch(content, $@"(?m)^\s*using\s+{Regex.Escape(ns)}\s*;", RegexOptions.CultureInvariant);

    static bool FileDeclaresNamespace(string content, string ns) =>
        Regex.IsMatch(content, $@"\bnamespace\s+{Regex.Escape(ns)}\b", RegexOptions.CultureInvariant);

    static bool ReferencesAnyType(string content, HashSet<string> typeNames)
    {
        foreach (var name in typeNames)
        {
            // Word-boundary type mention (GetPart<T>, new T, typeof(T), etc.)
            if (Regex.IsMatch(content, $@"\b{Regex.Escape(name)}\b", RegexOptions.CultureInvariant))
                return true;
        }
        return false;
    }
}
