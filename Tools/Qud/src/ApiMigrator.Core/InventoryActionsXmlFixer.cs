
namespace ApiMigrator.Core;

/// <summary>
/// PreferXML: static string <c>AddAction("Name", …)</c> with literal Display/Command/Key
/// → <c>AddXMLAction("Name")</c> plus a merged <c>InventoryActions.xml</c> overlay.
/// Dynamic remaining calls stay for <see cref="AddActionFixer"/> (InventoryAction object).
/// </summary>
public static class InventoryActionsXmlFixer
{
    public const string FixRuleName =
        "AddAction(string,…) → AddXMLAction + InventoryActions.xml";

    public static SidecarModFixResult FixMod(string modRoot, IReadOnlyDictionary<string, string> pathToContent)
    {
        var result = new SidecarModFixResult();
        if (string.IsNullOrEmpty(modRoot) || pathToContent == null || pathToContent.Count == 0)
            return result;

        var collected = new List<(string Name, string InnerXml)>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var (path, content) in pathToContent)
        {
            if (!path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                continue;
            if (content.IndexOf("AddAction", StringComparison.Ordinal) < 0)
                continue;

            var (next, edits, xml) = AddActionFixer.Rewrite(content, preferXml: true, resolveCommandConsts: true);
            if (edits == 0 && xml.Count == 0)
                continue;

            foreach (var a in xml)
            {
                if (!seen.Add(a.Name)) continue;
                collected.Add((a.Name, a.ToInnerXml()));
            }

            if (next != content)
            {
                result.UpdatedContents[path] = next;
                result.Fixes.Add((path, new AppliedFix { RuleName = FixRuleName, Count = edits }));
            }
        }

        if (collected.Count == 0)
            return result;

        var xmlPath = Path.Combine(modRoot, "InventoryActions.xml");
        string existing = "";
        if (pathToContent.TryGetValue(xmlPath, out var fromMap))
            existing = fromMap;
        else if (File.Exists(xmlPath))
            existing = File.ReadAllText(xmlPath);

        var merged = XmlOverlayMerger.MergeNamedChildren(existing, "inventoryactions", "inventoryaction", collected);
        result.SidecarFiles[xmlPath] = merged;
        result.Fixes.Add((xmlPath, new AppliedFix
        {
            RuleName = FixRuleName + " (write InventoryActions.xml)",
            Count = collected.Count,
        }));
        return result;
    }
}
