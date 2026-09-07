using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Strips C# nullable-reference annotations that CoQ's RoslynCSharp mod compiler
/// rejects (CS8632 / <c>#nullable</c>), which surface in Player.log as truncated
/// mystery MODWARNs ending in <c>SomeFile.cs'.</c> (Unity/`#` mangling hides the real text).
/// </summary>
/// <remarks>
/// Preserves null-conditional (<c>?.</c>), null-coalescing (<c>??</c>), ternary (<c>? :</c>),
/// and value-type nullables (<c>int?</c>, <c>bool?</c>, <c>DialogResult?</c>, enums,
/// <c>XRL.Version?</c> / <c>Version?</c> when the file aliases or qualifies <c>XRL.Version</c>,
/// and <c>TEnum?</c> when <c>where TEnum : struct</c>/<c>Enum</c>).
/// <para>
/// Cross-file enums (e.g. <c>TaskPriority?</c> declared in another .cs of the same mod) are
/// preserved when passed via <paramref name="extraPreserveTypeNames"/>, and also when the
/// annotation is a defaulted null parameter/field (<c>Type? name = null</c>) unless the type
/// is a known reference type — stripping those caused CS1750 on ThreadingAPI's
/// <c>ForWorldBuild(..., TaskPriority priority = null)</c>.
/// </para>
/// </remarks>
public static class NullableAnnotationCleaner
{
    static readonly Regex NullableDirective = new(
        @"(?m)^[ \t]*#nullable[ \t]+(?:enable|disable|restore)[ \t]*\r?\n?",
        RegexOptions.Compiled);

    /// <summary>
    /// Value types / common enums whose <c>?</c> means <see cref="Nullable{T}"/>, not NRTs.
    /// </summary>
    static readonly HashSet<string> ValueTypeNames = new(StringComparer.Ordinal)
    {
        "bool", "byte", "sbyte", "short", "ushort", "int", "uint", "long", "ulong",
        "float", "double", "decimal", "char", "nint", "nuint",
        "Boolean", "Byte", "SByte", "Int16", "UInt16", "Int32", "UInt32", "Int64", "UInt64",
        "Single", "Double", "Decimal", "Char",
        "DialogResult", "DateTime", "DateTimeOffset", "TimeSpan", "Guid", "IntPtr", "UIntPtr",
        "Half", "Rune", "Index", "Range", "DayOfWeek", "ConsoleKey", "ConsoleModifiers",
        "KeyCode", "Color", "Color32", "Vector2", "Vector3", "Vector4", "Quaternion",
        "Rect", "RectInt", "Bounds", "BoundsInt", "Ray", "Ray2D", "Plane", "Matrix4x4",
        "Vector2Int", "Vector3Int", "LayerMask", "Hash128",
        // CoQ: XRL.Version is a struct (System.Version is a class — only preserve when
        // the file aliases/qualifies XRL.Version; see Clean).
        "XRL.Version",
    };

    /// <summary>
    /// Reference types that may safely lose <c>?</c> even when written as <c>Type? x = null</c>
    /// (CoQ compiles <c>string x = null</c>; keeping <c>string?</c> is CS8632).
    /// </summary>
    static readonly HashSet<string> KnownReferenceTypesForNullDefault = new(StringComparer.Ordinal)
    {
        "string", "String", "object", "Object", "Exception", "Type", "Delegate",
        "MulticastDelegate", "Array", "Task", "Thread", "Encoding", "Stream",
        "TextWriter", "TextReader", "StringBuilder", "Regex", "Match", "Group",
        "GameObject", "Cell", "Zone", "IPart", "Effect", "Event", "IEvent",
        "Action", "Func", "Predicate", "Comparison", "Converter",
    };

    // Type? in a type position: not after '.' (avoids ?.), not ??, not ternary (?\s+\S).
    // Match identifier (optional dotted) then ? when followed by name/comma/>/)/[/]/=;/]/{ or EOL.
    // Include '[' so object?[] / string?[] are stripped.
    static readonly Regex NullableRefType = new(
        @"(?<![.\w])(?<type>[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\?(?=\s*(?:[A-Za-z_>\],\)=;\{\[]|/\*|$))",
        RegexOptions.Compiled);

    // List<string>?, string[]?, (int, string)? — NRT on constructed / array / tuple types.
    static readonly Regex NullableAfterCloser = new(
        @"(?<=[\]\)>])\?(?=\s*(?:[A-Za-z_>\],\)=;\{]|/\*|$))",
        RegexOptions.Compiled);

    static readonly Regex EnumDecl = new(
        @"\benum\s+(?<name>[A-Za-z_][\w]*)\b",
        RegexOptions.Compiled);

    // where TEnum : struct | Enum | System.Enum  (optionally with more constraints)
    static readonly Regex StructConstrainedTypeParam = new(
        @"\bwhere\s+(?<name>[A-Za-z_][\w]*)\s*:\s*(?:struct\b|Enum\b|System\.Enum\b)",
        RegexOptions.Compiled);

    static readonly Regex XrlVersionAlias = new(
        @"using\s+Version\s*=\s*XRL\.Version\s*;",
        RegexOptions.Compiled);

    // After Type?, a declarator defaulted to null: `? name = null` / `? name =null`
    static readonly Regex NullDefaultAfterNullable = new(
        @"^\?\s*[A-Za-z_][\w]*\s*=\s*null\b",
        RegexOptions.Compiled);

    /// <summary>
    /// Collects enum type names from one or more C# sources (same-mod cross-file preserve).
    /// </summary>
    public static HashSet<string> CollectEnumNames(IEnumerable<string?> contents)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        if (contents == null) return names;
        foreach (var content in contents)
        {
            if (string.IsNullOrEmpty(content)) continue;
            foreach (Match m in EnumDecl.Matches(content))
                names.Add(m.Groups["name"].Value);
        }
        return names;
    }

    /// <summary>
    /// Cleans nullable-reference annotations from C# source.
    /// </summary>
    /// <param name="content">Source text.</param>
    /// <param name="extraPreserveTypeNames">
    /// Additional simple (or dotted) type names to treat as value-type nullables —
    /// typically enums discovered in other files of the same mod.
    /// </param>
    /// <returns>Updated content and number of discrete edits (directives + annotations).</returns>
    public static (string Content, int EditCount) Clean(
        string content,
        IEnumerable<string>? extraPreserveTypeNames = null)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);

        var preserve = new HashSet<string>(ValueTypeNames, StringComparer.Ordinal);
        foreach (Match m in EnumDecl.Matches(content))
            preserve.Add(m.Groups["name"].Value);
        foreach (Match m in StructConstrainedTypeParam.Matches(content))
            preserve.Add(m.Groups["name"].Value);
        // XRL.Version is a struct; System.Version is a class. Keep Version? only when this
        // file clearly means the game struct (alias or XRL.Version qualification).
        if (content.IndexOf("XRL.Version", StringComparison.Ordinal) >= 0 ||
            XrlVersionAlias.IsMatch(content))
        {
            preserve.Add("Version");
        }
        if (extraPreserveTypeNames != null)
        {
            foreach (var name in extraPreserveTypeNames)
            {
                if (!string.IsNullOrWhiteSpace(name))
                    preserve.Add(name.Trim());
            }
        }

        var edits = 0;
        var working = NullableDirective.Replace(content, _ =>
        {
            edits++;
            return "";
        });

        working = NullableRefType.Replace(working, m =>
        {
            var typeName = m.Groups["type"].Value;
            var simple = typeName;
            var dot = typeName.LastIndexOf('.');
            if (dot >= 0)
                simple = typeName[(dot + 1)..];

            if (preserve.Contains(simple) || preserve.Contains(typeName))
                return m.Value; // keep int?, DialogResult?, IngredientSelectionMode?, TEnum?, etc.

            // Cross-file enum? / unknown value-type? with `= null` — keep unless known ref type.
            // Stripping TaskPriority? → TaskPriority with = null caused CS1750 (ThreadingAPI).
            var qIndex = m.Index + typeName.Length; // m starts at type name; '?' follows
            if (IsNullDefaultDeclarator(working, qIndex) &&
                !KnownReferenceTypesForNullDefault.Contains(simple) &&
                !KnownReferenceTypesForNullDefault.Contains(typeName))
            {
                return m.Value;
            }

            edits++;
            return typeName;
        });

        working = NullableAfterCloser.Replace(working, _ =>
        {
            edits++;
            return "";
        });

        return (working, edits);
    }

    /// <summary>
    /// True when <paramref name="nullableQIndex"/> points at the <c>?</c> of a
    /// <c>Type? name = null</c> parameter/field/local declarator.
    /// </summary>
    static bool IsNullDefaultDeclarator(string content, int nullableQIndex)
    {
        if (nullableQIndex < 0 || nullableQIndex >= content.Length || content[nullableQIndex] != '?')
            return false;
        // Match from the ? through `name = null`
        var sliceLen = Math.Min(96, content.Length - nullableQIndex);
        return NullDefaultAfterNullable.IsMatch(content.Substring(nullableQIndex, sliceLen));
    }
}
