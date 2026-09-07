using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// C# <c>MutationOnEquip</c> object-initializer / field assigns:
/// <c>ClassName = "Name"</c> → <c>Mutation = "Name"</c>; drops literal <c>Variant = …</c>.
/// Variable ClassName assigns stay for ManualAdvice.
/// </summary>
public static class MutationOnEquipCsFixer
{
    public const string FixRuleName =
        "MutationOnEquip ClassName/Variant C# → Mutation=";

    static readonly Regex ClassNameLit = new(
        @"\bClassName\s*=\s*(""[^""\\]*(?:\\.[^""\\]*)*"")",
        RegexOptions.Compiled);

    static readonly Regex VariantLit = new(
        @"\bVariant\s*=\s*(?:""[^""\\]*(?:\\.[^""\\]*)*""|null)\s*,?\s*",
        RegexOptions.Compiled);

    public static (string Content, int EditCount) Fix(string content)
    {
        if (string.IsNullOrEmpty(content))
            return (content, 0);
        if (content.IndexOf("ClassName", StringComparison.Ordinal) < 0 &&
            content.IndexOf("Variant", StringComparison.Ordinal) < 0)
            return (content, 0);
        // Only touch files that mention MutationOnEquip (avoid unrelated ClassName fields)
        if (content.IndexOf("MutationOnEquip", StringComparison.Ordinal) < 0)
            return (content, 0);

        var edits = 0;
        var working = ClassNameLit.Replace(content, m =>
        {
            if (HitFilter.IsInsideComment(content, m.Index) ||
                HitFilter.IsInsideStringLiteral(content, m.Index))
                return m.Value;
            // Require nearby MutationOnEquip context (object init / part)
            var start = Math.Max(0, m.Index - 120);
            var window = content[start..Math.Min(content.Length, m.Index + 80)];
            if (window.IndexOf("MutationOnEquip", StringComparison.Ordinal) < 0 &&
                window.IndexOf("new MutationOnEquip", StringComparison.Ordinal) < 0)
                return m.Value;
            edits++;
            return "Mutation = " + m.Groups[1].Value;
        });

        working = VariantLit.Replace(working, m =>
        {
            if (HitFilter.IsInsideComment(working, m.Index))
                return m.Value;
            var start = Math.Max(0, m.Index - 160);
            var window = working[start..Math.Min(working.Length, m.Index + 40)];
            if (window.IndexOf("MutationOnEquip", StringComparison.Ordinal) < 0 &&
                window.IndexOf("Mutation =", StringComparison.Ordinal) < 0)
                return m.Value;
            edits++;
            return "";
        });

        return edits == 0 ? (content, 0) : (working, edits);
    }
}
