using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Auto-fixes common CoQ <c>manifest.json</c> / <c>config.json</c> load killers:
/// <list type="bullet">
/// <item><c>dependencies</c> as a JSON array (<c>["Base"]</c>) → object, then normalized (below)</item>
/// <item>Single required dep as <c>Dependencies</c> object / string → <c>Dependency</c> shorthand
/// (<c>ModManifest.Dependency</c> is the <c>[JsonProperty]</c> setter that actually fills
/// <c>Manifest.Dependencies</c>; a required edge is what yields <c>ModState.MissingDependency</c>
/// instead of compiling without the other assembly)</item>
/// <item>Caret / exact version ranges → <c>*</c> (or leave wiki <c>1.0.0 - *</c>)</item>
/// <item>Steam workshop folder ids (all digits) stripped from required deps — <c>ModMap</c> is keyed
/// by sanitized manifest id, not published-file id; a numeric required key always looks missing</item>
/// <item><c>LoadAfter</c> ensured for every required manifest id (compile-order hint; weight 1)</item>
/// <item>Obsolete numeric <c>loadOrder</c> / <c>LoadOrder</c> → remove field</item>
/// <item>Invalid <c>version</c> strings (e.g. <c>"1.0 Beta"</c>) → semver-like <c>1.0.0</c></item>
/// </list>
/// Does not touch <c>id</c> / <c>title</c>. Array <c>dependencies</c> entries are treated as
/// dependency mod ids (Pickpocket pattern), not LoadAfter.
/// </summary>
public static class ManifestFixer
{
    static readonly HashSet<string> TargetFileNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "manifest.json",
        "config.json",
    };

    static readonly HashSet<string> LoadOrderKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "loadOrder",
        "LoadOrder",
    };

    static readonly Regex ValidVersion = new(
        @"^\d+(\.\d+)*$",
        RegexOptions.Compiled);

    static readonly Regex VersionNumberChunk = new(
        @"\d+(?:\.\d+)*",
        RegexOptions.Compiled);

    /// <summary>Steam workshop published-file ids are 9–10 digits; 8+ all-digits is the unsafe zone.</summary>
    static readonly Regex WorkshopFolderId = new(
        @"^\d{8,}$",
        RegexOptions.Compiled);

    /// <summary>
    /// Namespace usings that mean a required Workshop library mod. Key is the using
    /// namespace; value is that library's manifest <c>id</c> (ModMap key, not a folder number).
    /// </summary>
    public static readonly Dictionary<string, string> KnownLibraryUsings = new(StringComparer.Ordinal)
    {
        ["tyrir.lib"] = "moremoddinggoodies",
    };

    static readonly JsonSerializerOptions WriteOptions = new(JsonSerializerOptions.Default)
    {
        WriteIndented = true,
    };

    public static bool IsTargetFile(string? path)
    {
        if (string.IsNullOrEmpty(path)) return false;
        var name = Path.GetFileName(path);
        return TargetFileNames.Contains(name);
    }

    /// <summary>
    /// Finds <c>manifest.json</c> / <c>config.json</c> under scan roots (same exclude/mod-filter
    /// semantics as <see cref="FileScanner"/>).
    /// </summary>
    public static List<string> GetTargetFiles(IEnumerable<string> roots, IReadOnlyList<string> excludeDirs,
        string? modFilter, Action<string>? onWarning = null)
    {
        var all = FileScanner.GetTargetFiles(roots, excludeDirs, new[] { ".json" }, modFilter, onWarning);
        return all.Where(IsTargetFile).ToList();
    }

    /// <summary>
    /// Applies safe manifest fixes. Returns original content unchanged when nothing to fix
    /// or when JSON cannot be parsed as an object.
    /// </summary>
    /// <param name="ensureDependencyIds">
    /// Extra required manifest ids to pin (e.g. <c>moremoddinggoodies</c> inferred from
    /// <c>using tyrir.lib</c>). Never invents this mod's own <c>id</c>/<c>title</c>.
    /// </param>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content,
        IEnumerable<string>? ensureDependencyIds = null)
    {
        var fixes = new List<AppliedFix>();
        var nl = (content ?? "").Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";

        // Blank / whitespace-only file — seed a minimal stub (never invents id/title).
        if (string.IsNullOrWhiteSpace(content))
        {
            var stub = "{" + nl + "  \"version\": \"1.0.0\"" + nl + "}" + nl;
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: empty file → minimal { version: \"1.0.0\" }",
                Count = 1,
            });
            return (stub, fixes);
        }

        JsonNode? rootNode;
        try
        {
            rootNode = JsonNode.Parse(content);
        }
        catch (JsonException)
        {
            return (content, fixes);
        }

        if (rootNode is null || (rootNode is JsonValue jvNull && jvNull.GetValueKind() == JsonValueKind.Null))
        {
            var stub = "{" + nl + "  \"version\": \"1.0.0\"" + nl + "}" + nl;
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: null JSON → minimal { version: \"1.0.0\" }",
                Count = 1,
            });
            return (stub, fixes);
        }

        if (rootNode is not JsonObject root)
            return (content, fixes);

        if (root.Count == 0)
        {
            root["version"] = "1.0.0";
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: empty object {} → add version \"1.0.0\"",
                Count = 1,
            });
        }

        FixDependenciesArray(root, fixes);
        NormalizeRequiredDependencies(root, ensureDependencyIds, fixes);
        RemoveLoadOrder(root, fixes);
        NormalizeVersion(root, fixes);

        if (fixes.Count == 0)
            return (content, fixes);

        var written = root.ToJsonString(WriteOptions);
        // System.Text.Json uses \n when indented; match source newline style.
        if (nl == "\r\n")
            written = written.Replace("\n", "\r\n");

        // Preserve a trailing newline if the original had one.
        if (content.EndsWith("\n", StringComparison.Ordinal) && !written.EndsWith(nl, StringComparison.Ordinal))
            written += nl;

        return (written, fixes);
    }

    static void FixDependenciesArray(JsonObject root, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, "dependencies");
        if (key is null) return;
        if (!root.TryGetPropertyValue(key, out var node) || node is null) return;

        if (node is not JsonArray arr)
            return; // object / string handled in NormalizeRequiredDependencies

        var dict = new JsonObject();
        var count = 0;
        foreach (var el in arr)
        {
            if (el is JsonValue jv && jv.TryGetValue<string>(out var id) && !string.IsNullOrWhiteSpace(id))
            {
                // Last duplicate wins; "*" matches Pickpocket / modern CoQ deps.
                dict[id.Trim()] = "*";
                count++;
            }
        }

        root[key] = dict;
        fixes.Add(new AppliedFix
        {
            RuleName = "manifest: dependencies array → object (keys → \"*\")",
            Count = Math.Max(count, 1),
        });
    }

    /// <summary>
    /// Scan C# sources for known library usings and return the Workshop manifest ids they
    /// require (excluding <paramref name="thisModId"/>).
    /// </summary>
    public static List<string> InferKnownLibraryModIds(IEnumerable<string> csharpSources, string? thisModId)
    {
        var ids = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (!string.IsNullOrWhiteSpace(thisModId))
            seen.Add(thisModId.Trim());

        foreach (var src in csharpSources)
        {
            if (string.IsNullOrEmpty(src)) continue;
            foreach (var kv in KnownLibraryUsings)
            {
                if (seen.Contains(kv.Value)) continue;
                if (!HasUsing(src, kv.Key)) continue;
                if (!seen.Add(kv.Value)) continue;
                ids.Add(kv.Value);
            }
        }

        return ids;
    }

    static bool HasUsing(string src, string ns)
    {
        var needle = "using " + ns;
        var i = 0;
        while ((i = src.IndexOf(needle, i, StringComparison.Ordinal)) >= 0)
        {
            var after = i + needle.Length;
            if (i > 0 && (char.IsLetterOrDigit(src[i - 1]) || src[i - 1] == '.' || src[i - 1] == '_'))
            {
                i = after;
                continue;
            }
            while (after < src.Length && char.IsWhiteSpace(src[after])) after++;
            if (after < src.Length && src[after] == ';')
                return true;
            i = after;
        }
        return false;
    }

    static void NormalizeRequiredDependencies(JsonObject root, IEnumerable<string>? ensureDependencyIds,
        List<AppliedFix> fixes)
    {
        var shorthandKey = FindActualKey(root, "dependency");
        var mapKey = FindActualKey(root, "dependencies");

        var realIds = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var droppedWorkshop = 0;

        void AddReal(string? raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return;
            var id = raw.Trim();
            if (WorkshopFolderId.IsMatch(id))
            {
                droppedWorkshop++;
                return;
            }
            if (!seen.Add(id)) return;
            realIds.Add(id);
        }

        if (shorthandKey is not null && root.TryGetPropertyValue(shorthandKey, out var shorthandNode))
            CollectIds(shorthandNode, AddReal);

        if (mapKey is not null && root.TryGetPropertyValue(mapKey, out var mapNode))
        {
            if (mapNode is JsonObject map)
            {
                foreach (var p in map)
                    AddReal(p.Key);
            }
            else
            {
                CollectIds(mapNode, AddReal);
            }
        }

        var idKey = FindActualKey(root, "id") ?? FindActualKey(root, "ID");
        var thisId = idKey is null ? null : NodeToString(root[idKey]);
        if (ensureDependencyIds is not null)
        {
            var inferred = 0;
            foreach (var extra in ensureDependencyIds)
            {
                if (string.IsNullOrWhiteSpace(extra)) continue;
                if (thisId is not null && string.Equals(extra.Trim(), thisId.Trim(), StringComparison.OrdinalIgnoreCase))
                    continue;
                var before = realIds.Count;
                AddReal(extra);
                if (realIds.Count > before) inferred++;
            }
            if (inferred > 0)
            {
                fixes.Add(new AppliedFix
                {
                    RuleName = "manifest: add required Dependency inferred from known library using",
                    Count = inferred,
                });
            }
        }

        var wantShorthand = realIds.Count == 1;
        var wantMap = realIds.Count >= 2;

        var currentShorthand = shorthandKey is not null
            ? NodeToString(root[shorthandKey])
            : null;
        var shorthandOk = wantShorthand
            && currentShorthand is not null
            && string.Equals(currentShorthand.Trim(), realIds[0], StringComparison.OrdinalIgnoreCase);

        var mapOk = false;
        if (wantMap && mapKey is not null && root[mapKey] is JsonObject currentMap)
        {
            mapOk = currentMap.Count == realIds.Count
                && realIds.All(id => currentMap.Any(p =>
                    string.Equals(p.Key, id, StringComparison.OrdinalIgnoreCase)
                    && IsAnyVersionRange(NodeToString(p.Value) ?? "")));
        }

        var shapeOk = (wantShorthand && shorthandOk && mapKey is null)
            || (wantMap && mapOk && shorthandKey is null)
            || (realIds.Count == 0 && shorthandKey is null && mapKey is null);

        if (!shapeOk)
        {
            if (shorthandKey is not null) root.Remove(shorthandKey);
            if (mapKey is not null) root.Remove(mapKey);

            if (wantShorthand)
            {
                root["Dependency"] = realIds[0];
                fixes.Add(new AppliedFix
                {
                    RuleName = "manifest: single required dep → Dependency shorthand (JsonProperty)",
                    Count = 1,
                });
            }
            else if (wantMap)
            {
                var dict = new JsonObject();
                foreach (var id in realIds)
                    dict[id] = "*";
                root["Dependencies"] = dict;
                fixes.Add(new AppliedFix
                {
                    RuleName = "manifest: required deps → Dependencies object (keys → \"*\")",
                    Count = realIds.Count,
                });
            }
            else if (shorthandKey is not null || mapKey is not null)
            {
                fixes.Add(new AppliedFix
                {
                    RuleName = "manifest: drop empty / workshop-id-only required deps",
                    Count = 1,
                });
            }
        }

        if (droppedWorkshop > 0 && realIds.Count > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: strip workshop folder id from required Dependencies (ModMap uses manifest id)",
                Count = droppedWorkshop,
            });
        }

        if (realIds.Count > 0)
            EnsureLoadAfter(root, realIds, fixes);
    }

    static void CollectIds(JsonNode? node, Action<string?> add)
    {
        if (node is null) return;
        if (node is JsonValue)
        {
            add(NodeToString(node));
            return;
        }
        if (node is JsonArray arr)
        {
            foreach (var el in arr)
                add(NodeToString(el));
            return;
        }
        if (node is JsonObject obj)
        {
            foreach (var p in obj)
                add(p.Key);
        }
    }

    static void EnsureLoadAfter(JsonObject root, IReadOnlyList<string> requiredIds, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, "loadAfter") ?? FindActualKey(root, "LoadAfter");
        var existing = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        void AddExisting(string? raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return;
            var id = raw.Trim();
            if (!seen.Add(id)) return;
            existing.Add(id);
        }

        if (key is not null && root.TryGetPropertyValue(key, out var node))
            CollectIds(node, AddExisting);

        var added = 0;
        foreach (var id in requiredIds)
        {
            if (!seen.Add(id)) continue;
            existing.Add(id);
            added++;
        }

        if (added == 0 && key is not null)
            return;

        var writeKey = key ?? "LoadAfter";
        if (existing.Count == 1)
            root[writeKey] = existing[0];
        else
        {
            var arr = new JsonArray();
            foreach (var id in existing)
                arr.Add(id);
            root[writeKey] = arr;
        }

        if (added > 0 || key is null)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: LoadAfter required dep ids (compile order)",
                Count = Math.Max(added, 1),
            });
        }
    }

    static void RemoveLoadOrder(JsonObject root, List<AppliedFix> fixes)
    {
        var removed = 0;
        foreach (var want in LoadOrderKeys.ToList())
        {
            var actual = FindActualKey(root, want);
            if (actual is null) continue;
            root.Remove(actual);
            removed++;
        }

        if (removed > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: remove obsolete loadOrder/LoadOrder",
                Count = removed,
            });
        }
    }

    static void NormalizeVersion(JsonObject root, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, "version") ?? FindActualKey(root, "Version");
        if (key is null) return;
        if (!root.TryGetPropertyValue(key, out var node) || node is null) return;

        string? original;
        if (node is JsonValue jv)
        {
            if (jv.TryGetValue<string>(out var s))
                original = s;
            else if (jv.TryGetValue<decimal>(out var d))
                original = d.ToString(System.Globalization.CultureInfo.InvariantCulture);
            else if (jv.TryGetValue<long>(out var l))
                original = l.ToString(System.Globalization.CultureInfo.InvariantCulture);
            else
                return;
        }
        else
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(original))
        {
            root[key] = "1.0.0";
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: version empty → \"1.0.0\"",
                Count = 1,
            });
            return;
        }

        var trimmed = original.Trim();
        if (ValidVersion.IsMatch(trimmed))
            return; // "1.0", "1.0.0", "2" — leave alone (game accepts these)

        var normalized = TryNormalizeVersion(trimmed);
        var note = normalized == "1.0.0" && !VersionNumberChunk.IsMatch(trimmed)
            ? "manifest: version unparseable → \"1.0.0\""
            : $"manifest: version \"{EscapeForNote(trimmed)}\" → \"{normalized}\"";

        root[key] = normalized;
        fixes.Add(new AppliedFix { RuleName = note, Count = 1 });
    }

    /// <summary>
    /// Strip words / junk; keep the first numeric dotted chunk; pad to major.minor.patch
    /// when we had to rewrite. Unparseable → <c>1.0.0</c>.
    /// </summary>
    public static string TryNormalizeVersion(string raw)
    {
        var m = VersionNumberChunk.Match(raw);
        if (!m.Success)
            return "1.0.0";

        var parts = m.Value.Split('.', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0)
            return "1.0.0";

        var sb = new StringBuilder();
        for (var i = 0; i < 3; i++)
        {
            if (i > 0) sb.Append('.');
            sb.Append(i < parts.Length ? parts[i] : "0");
        }

        // Keep extra components beyond patch if present (4.5.6.7 → 4.5.6.7).
        for (var i = 3; i < parts.Length; i++)
        {
            sb.Append('.');
            sb.Append(parts[i]);
        }

        return sb.ToString();
    }

    /// <summary>
    /// True when CoQ <c>Version.EqualsSemantic</c> treats <paramref name="range"/> as matching
    /// any installed version of the dependency (or already an open high bound).
    /// </summary>
    public static bool IsAnyVersionRange(string range)
    {
        var t = (range ?? "").Trim();
        if (t.Length == 0) return false;
        if (t is "*" or "x" or "X") return true;
        var dash = t.LastIndexOf('-');
        if (dash < 0) return false;
        var high = t[(dash + 1)..].Trim();
        return high is "*" or "x" or "X" or "";
    }

    static string? NodeToString(JsonNode? node)
    {
        if (node is not JsonValue jv) return null;
        if (jv.TryGetValue<string>(out var s)) return s;
        if (jv.TryGetValue<long>(out var l))
            return l.ToString(System.Globalization.CultureInfo.InvariantCulture);
        if (jv.TryGetValue<decimal>(out var d))
            return d.ToString(System.Globalization.CultureInfo.InvariantCulture);
        return jv.ToString();
    }

    static string? FindActualKey(JsonObject root, string wanted)
    {
        foreach (var p in root)
        {
            if (string.Equals(p.Key, wanted, StringComparison.OrdinalIgnoreCase))
                return p.Key;
        }
        return null;
    }

    static string EscapeForNote(string s) =>
        s.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal);
}
