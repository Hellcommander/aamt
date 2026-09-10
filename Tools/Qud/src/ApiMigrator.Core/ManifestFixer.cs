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
/// <item>Steam workshop folder ids and old folder titles remapped via <see cref="ModIdCatalog"/>
/// to the live ModMap id (sanitized <c>manifest.id</c> or folder name). Unresolved workshop
/// published-file ids are stripped — they never match ModMap after a local rename</item>
/// <item><c>LoadAfter</c> / <c>LoadBefore</c> tokens remapped the same way. Required ids are
/// not also written to LoadAfter when they already appear in LoadBefore (that cycle made
/// XML stub mods load after the host, so dependents saw them as not Active)</item>
/// <item>WM Extended Mutations (beta <c>WMexMutationsBeta</c> / 2065946296 or stable
/// <c>WMexMutationsStable</c> / 2198787801): a required dep on either edition becomes one
/// OR key <c>WMexMutationsBeta|WMexMutationsStable</c> (two keys is AND and fails if only
/// one edition is installed). ThreadingAPI splits <c>|</c> at resolve time. LoadAfter /
/// LoadBefore that name one edition gain the other as separate ids. LoadBefore of either
/// is still not also required</item>
/// <item>Missing <c>id</c> filled with the catalog's canonical id so later folder renames
/// do not change the ModMap key</item>
/// <item>Obsolete numeric <c>loadOrder</c> / <c>LoadOrder</c> → remove field</item>
/// <item>Invalid <c>version</c> strings (e.g. <c>"1.0 Beta"</c>) → semver-like <c>1.0.0</c></item>
/// </list>
/// Does not rewrite an existing <c>id</c> / <c>title</c>. Array <c>dependencies</c> entries
/// are treated as dependency mod ids (Pickpocket pattern), not LoadAfter.
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

    /// <summary>WM Extended Mutations [Beta Edition] ModMap id.</summary>
    public const string WmExtendedBetaId = "WMexMutationsBeta";

    /// <summary>WM Extended Mutations [Stable Edition] ModMap id.</summary>
    public const string WmExtendedStableId = "WMexMutationsStable";

    /// <summary>Workshop published-file id for the beta edition.</summary>
    public const string WmExtendedBetaWorkshopId = "2065946296";

    /// <summary>Workshop published-file id for the stable edition.</summary>
    public const string WmExtendedStableWorkshopId = "2198787801";

    /// <summary>
    /// Generic / legacy id meaning "either edition". Collapsed to
    /// <see cref="WmExtendedEitherId"/>.
    /// </summary>
    public const string WmExtendedGenericId = "WMexMutations";

    /// <summary>
    /// Single required-dep token: beta OR stable. Vanilla AND of two keys would demand
    /// both editions; ThreadingAPI splits <c>|</c> and accepts whichever is installed.
    /// </summary>
    public const string WmExtendedEitherId = WmExtendedBetaId + "|" + WmExtendedStableId;

    static readonly Dictionary<string, string> WmExtendedTokenToEdition = new(StringComparer.OrdinalIgnoreCase)
    {
        [WmExtendedBetaId] = WmExtendedBetaId,
        [WmExtendedBetaWorkshopId] = WmExtendedBetaId,
        [WmExtendedStableId] = WmExtendedStableId,
        [WmExtendedStableWorkshopId] = WmExtendedStableId,
    };

    static readonly HashSet<string> WmExtendedGenericTokens = new(StringComparer.OrdinalIgnoreCase)
    {
        WmExtendedGenericId,
        "WMExtendedMutations",
        "WM Extended Mutations",
    };

    static readonly JsonSerializerOptions WriteOptions = new(JsonSerializerOptions.Default)
    {
        WriteIndented = true,
    };

    static readonly HashSet<string> SkipParentDirNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "Packages", "Library", "ProjectSettings",
    };

    public static bool IsTargetFile(string? path)
    {
        if (string.IsNullOrEmpty(path)) return false;
        var name = Path.GetFileName(path);
        if (!TargetFileNames.Contains(name)) return false;

        var dir = Path.GetDirectoryName(path);
        if (string.IsNullOrEmpty(dir)) return false;

        foreach (var part in dir.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar))
        {
            if (part.Length > 0 && SkipParentDirNames.Contains(part))
                return false;
        }

        return true;
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
    /// Fix every <c>manifest.json</c> / <c>config.json</c> under <paramref name="roots"/>.
    /// </summary>
    public static List<FileScanResult> FixTree(
        IEnumerable<string> roots,
        IReadOnlyList<string> excludeDirs,
        string? modFilter,
        bool apply,
        bool backup,
        Action<string>? onLog,
        ModIdCatalog? catalog = null)
    {
        var rootList = roots.ToList();
        catalog ??= ModIdCatalog.Build(ModIdCatalog.DefaultScanRoots(rootList));
        var files = GetTargetFiles(rootList, excludeDirs, modFilter, onLog);
        var results = new List<FileScanResult>();

        foreach (var file in files)
        {
            string original;
            try { original = File.ReadAllText(file); }
            catch (Exception ex)
            {
                onLog?.Invoke($"Could not read {file}: {ex.Message}");
                continue;
            }

            var modRoot = FileScanner.GetModRoot(file);
            var (working, appliedFixes) = Fix(
                original,
                ensureDependencyIds: null,
                catalog,
                catalog.CanonicalIdForDirectory(modRoot));
            var changed = working != original;
            if (!changed) continue;

            var result = new FileScanResult
            {
                FilePath = file,
                Changed = changed,
                AppliedFixes = appliedFixes,
                NewContent = working,
            };
            results.Add(result);

            onLog?.Invoke($"{(apply ? "wrote" : "would write")} {Path.GetFileName(Path.GetDirectoryName(file))}/{Path.GetFileName(file)}: "
                + string.Join("; ", appliedFixes.Select(f => f.RuleName)));

            if (!apply) continue;
            try
            {
                if (backup)
                {
                    var bak = file + ".bak";
                    if (!File.Exists(bak))
                    {
                        try { File.Copy(file, bak); }
                        catch (UnauthorizedAccessException)
                        {
                            onLog?.Invoke($"WARNING: could not write backup {bak}; applying without .bak");
                        }
                    }
                }
                WorkshopWrite.WriteAllText(file, working);
            }
            catch (Exception ex)
            {
                onLog?.Invoke($"ERROR writing {file}: {ex.Message}");
                result.Changed = false;
                result.NewContent = null;
            }
        }

        return results;
    }

    /// <summary>
    /// Applies safe manifest fixes. Returns original content unchanged when nothing to fix
    /// or when JSON cannot be parsed as an object.
    /// </summary>
    /// <param name="ensureDependencyIds">
    /// Extra required manifest ids to pin (e.g. <c>moremoddinggoodies</c> inferred from
    /// <c>using tyrir.lib</c>). Never invents this mod's own <c>title</c>.
    /// </param>
    /// <param name="catalog">Live mods: remap workshop folder ids / titles to ModMap ids.</param>
    /// <param name="ensureId">
    /// When this file has no <c>id</c>, write this canonical ModMap id (folder-derived).
    /// Does not rewrite an existing id.
    /// </param>
    public static (string Content, List<AppliedFix> Fixes) Fix(string content,
        IEnumerable<string>? ensureDependencyIds = null,
        ModIdCatalog? catalog = null,
        string? ensureId = null)
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
        RemapLoadHints(root, catalog, fixes);
        ExpandWmExtendedLoadHints(root, catalog, fixes);
        NormalizeRequiredDependencies(root, ensureDependencyIds, fixes, catalog);
        RemapDirectoryDependencies(root, catalog, fixes);
        EnsureMissingId(root, ensureId, fixes);
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
        List<AppliedFix> fixes, ModIdCatalog? catalog)
    {
        var shorthandKey = FindActualKey(root, "dependency");
        var mapKey = FindActualKey(root, "dependencies");

        var realIds = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var droppedWorkshop = 0;
        var remapped = 0;
        var skippedLoadBefore = 0;
        var loadBeforeIds = CollectMappedIds(root, "loadBefore", "LoadBefore", catalog);

        void AddReal(string? raw)
        {
            var id = MapToken(raw, catalog, out var dropped);
            if (dropped) { droppedWorkshop++; return; }
            if (id is null) return;
            if (raw is not null && !string.Equals(raw.Trim(), id, StringComparison.Ordinal))
                remapped++;
            if (loadBeforeIds.Contains(id))
            {
                skippedLoadBefore++;
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

        var wmRequired = ExpandWmExtendedRequired(realIds, seen, loadBeforeIds);
        if (wmRequired > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: WM Extended Mutations required dep → beta|stable (OR)",
                Count = wmRequired,
            });
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
                    RuleName = skippedLoadBefore > 0
                        ? "manifest: drop required Dependency that is also LoadBefore (cycle; required means load-after)"
                        : "manifest: drop empty / workshop-id-only required deps",
                    Count = Math.Max(skippedLoadBefore, 1),
                });
            }
        }

        if (remapped > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: remap Dependency keys to live ModMap id (folder title / workshop id)",
                Count = remapped,
            });
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
            EnsureLoadAfter(root, realIds, fixes, catalog, loadBeforeIds);
        else if (loadBeforeIds.Count > 0)
            StripLoadAfterConflicts(root, loadBeforeIds, fixes);
    }

    static HashSet<string> CollectMappedIds(JsonObject root, string lookup, string alt,
        ModIdCatalog? catalog)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var key = FindActualKey(root, lookup) ?? FindActualKey(root, alt);
        if (key is null || !root.TryGetPropertyValue(key, out var node))
            return set;
        CollectIds(node, raw =>
        {
            var id = MapToken(raw, catalog, out var dropped);
            if (dropped || id is null) return;
            set.Add(id);
        });
        return set;
    }

    /// <summary>
    /// Map a Dependency / LoadAfter token onto the live ModMap id. Unresolved Steam
    /// published-file ids are dropped; other unknown tokens are punctuation-sanitized
    /// (same <c>[^\w ]</c> class as <c>ModInfo.ID</c>) so hyphenated manifest ids match.
    /// </summary>
    public static string? MapToken(string? raw, ModIdCatalog? catalog, out bool droppedWorkshop)
    {
        droppedWorkshop = false;
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var id = raw.Trim();
        if (id.Equals("Base", StringComparison.OrdinalIgnoreCase))
            return "Base";

        var wm = MapWmExtendedToken(id);
        if (wm is not null)
            return wm;

        if (catalog is not null)
        {
            var resolved = catalog.Resolve(id);
            if (resolved is not null)
                return resolved;
        }

        if (WorkshopFolderId.IsMatch(id) || ModIdCatalog.LooksLikeWorkshopFolderId(id))
        {
            droppedWorkshop = true;
            return null;
        }

        var san = ModIdCatalog.SanitizeId(id);
        return san.Length > 0 ? san : id;
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

    static void EnsureLoadAfter(JsonObject root, IReadOnlyList<string> requiredIds, List<AppliedFix> fixes,
        ModIdCatalog? catalog, HashSet<string> loadBeforeIds)
    {
        var key = FindActualKey(root, "loadAfter") ?? FindActualKey(root, "LoadAfter");
        var existing = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var remapped = 0;
        var stripped = 0;

        void AddExisting(string? raw)
        {
            var id = MapToken(raw, catalog, out var dropped);
            if (dropped || id is null) return;
            foreach (var part in SplitDependencyAlts(id))
            {
                if (loadBeforeIds.Contains(part)) { stripped++; continue; }
                if (raw is not null && !string.Equals(raw.Trim(), part, StringComparison.Ordinal))
                    remapped++;
                if (!seen.Add(part)) continue;
                existing.Add(part);
            }
        }

        if (key is not null && root.TryGetPropertyValue(key, out var node))
            CollectIds(node, AddExisting);

        var added = 0;
        foreach (var id in requiredIds)
        {
            foreach (var part in SplitDependencyAlts(id))
            {
                if (loadBeforeIds.Contains(part)) continue;
                if (!seen.Add(part)) continue;
                existing.Add(part);
                added++;
            }
        }

        if (added == 0 && remapped == 0 && stripped == 0 && key is not null)
            return;

        var writeKey = key ?? "LoadAfter";
        if (existing.Count == 0)
            root.Remove(writeKey);
        else if (existing.Count == 1)
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
        else if (stripped > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: remove LoadAfter ids that are also LoadBefore (cycle)",
                Count = stripped,
            });
        }
        else if (remapped > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: remap LoadAfter tokens to live ModMap id",
                Count = remapped,
            });
        }
    }

    static void StripLoadAfterConflicts(JsonObject root, HashSet<string> loadBeforeIds, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, "loadAfter") ?? FindActualKey(root, "LoadAfter");
        if (key is null) return;
        if (!root.TryGetPropertyValue(key, out var node) || node is null) return;

        var kept = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var stripped = 0;
        CollectIds(node, raw =>
        {
            if (string.IsNullOrWhiteSpace(raw)) return;
            var id = raw.Trim();
            if (loadBeforeIds.Contains(id)) { stripped++; return; }
            if (!seen.Add(id)) return;
            kept.Add(id);
        });

        if (stripped == 0) return;

        if (kept.Count == 0)
            root.Remove(key);
        else if (kept.Count == 1)
            root[key] = kept[0];
        else
        {
            var arr = new JsonArray();
            foreach (var id in kept)
                arr.Add(id);
            root[key] = arr;
        }

        fixes.Add(new AppliedFix
        {
            RuleName = "manifest: remove LoadAfter ids that are also LoadBefore (cycle)",
            Count = stripped,
        });
    }

    static void RemapLoadHints(JsonObject root, ModIdCatalog? catalog, List<AppliedFix> fixes)
    {
        RemapStringListField(root, "loadAfter", "LoadAfter", catalog, fixes);
        RemapStringListField(root, "loadBefore", "LoadBefore", catalog, fixes);
    }

    /// <summary>
    /// True when <paramref name="id"/> is WM Extended Mutations beta, stable, a workshop
    /// published-file id for either edition, or the generic <c>WMexMutations</c> token.
    /// </summary>
    public static bool IsWmExtendedFamilyId(string? id)
    {
        if (string.IsNullOrWhiteSpace(id)) return false;
        return MapWmExtendedToken(id) is not null;
    }

    /// <summary>
    /// Map a WM Extended Mutations token onto <see cref="WmExtendedBetaId"/>,
    /// <see cref="WmExtendedStableId"/>, <see cref="WmExtendedEitherId"/>, or
    /// <see cref="WmExtendedGenericId"/>. Unknown tokens return null (not an error).
    /// </summary>
    public static string? MapWmExtendedToken(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var id = raw.Trim();
        if (id.IndexOf('|') >= 0)
        {
            var alts = SplitDependencyAlts(id);
            if (alts.Count == 0) return null;
            foreach (var alt in alts)
            {
                if (!IsWmExtendedNamedEdition(alt))
                    return null;
            }
            return WmExtendedEitherId;
        }

        if (string.Equals(id, WmExtendedEitherId, StringComparison.OrdinalIgnoreCase))
            return WmExtendedEitherId;
        if (WmExtendedTokenToEdition.TryGetValue(id, out var edition))
            return edition;
        if (WmExtendedGenericTokens.Contains(id))
            return WmExtendedGenericId;

        var san = ModIdCatalog.SanitizeId(id);
        if (san.Length > 0 && !san.Equals(id, StringComparison.OrdinalIgnoreCase))
        {
            if (WmExtendedTokenToEdition.TryGetValue(san, out edition))
                return edition;
            if (WmExtendedGenericTokens.Contains(san))
                return WmExtendedGenericId;
        }

        return null;
    }

    static bool IsWmExtendedNamedEdition(string? id) =>
        string.Equals(id, WmExtendedBetaId, StringComparison.OrdinalIgnoreCase)
        || string.Equals(id, WmExtendedStableId, StringComparison.OrdinalIgnoreCase);

    /// <summary>
    /// Split a required-dep token on <c>|</c> (OR). The WM either-token expands to beta
    /// then stable so LoadAfter can pin whichever edition is installed.
    /// </summary>
    public static IReadOnlyList<string> SplitDependencyAlts(string? id)
    {
        if (string.IsNullOrWhiteSpace(id))
            return Array.Empty<string>();
        var t = id.Trim();
        if (t.IndexOf('|') < 0)
        {
            if (string.Equals(t, WmExtendedEitherId, StringComparison.OrdinalIgnoreCase)
                || string.Equals(t, WmExtendedGenericId, StringComparison.OrdinalIgnoreCase))
                return new[] { WmExtendedBetaId, WmExtendedStableId };
            var mapped = MapWmExtendedNamedOrSelf(t);
            return new[] { mapped };
        }

        var list = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var raw in t.Split('|'))
        {
            var part = raw.Trim();
            if (part.Length == 0) continue;
            if (string.Equals(part, WmExtendedGenericId, StringComparison.OrdinalIgnoreCase)
                || string.Equals(part, WmExtendedEitherId, StringComparison.OrdinalIgnoreCase))
            {
                TryAddAlt(list, seen, WmExtendedBetaId);
                TryAddAlt(list, seen, WmExtendedStableId);
                continue;
            }
            TryAddAlt(list, seen, MapWmExtendedNamedOrSelf(part));
        }
        return list;
    }

    static string MapWmExtendedNamedOrSelf(string part)
    {
        if (WmExtendedTokenToEdition.TryGetValue(part, out var edition))
            return edition;
        var san = ModIdCatalog.SanitizeId(part);
        if (san.Length > 0 && WmExtendedTokenToEdition.TryGetValue(san, out edition))
            return edition;
        return part;
    }

    static void TryAddAlt(List<string> dest, HashSet<string> seen, string id)
    {
        if (!seen.Add(id)) return;
        dest.Add(id);
    }

    static int ExpandWmExtendedRequired(List<string> realIds, HashSet<string> seen,
        HashSet<string> loadBeforeIds)
    {
        var familyLoadBefore = loadBeforeIds.Any(IsWmExtendedFamilyId);
        if (!realIds.Any(IsWmExtendedFamilyId))
            return 0;

        var familyCount = 0;
        var hasEither = false;
        var hasNamed = false;
        foreach (var id in realIds)
        {
            var mapped = MapWmExtendedToken(id);
            if (mapped is null) continue;
            familyCount++;
            if (string.Equals(mapped, WmExtendedEitherId, StringComparison.OrdinalIgnoreCase))
                hasEither = true;
            else
                hasNamed = true;
        }

        if (familyLoadBefore)
        {
            var removed = 0;
            for (var i = realIds.Count - 1; i >= 0; i--)
            {
                if (!IsWmExtendedFamilyId(realIds[i])) continue;
                seen.Remove(realIds[i]);
                realIds.RemoveAt(i);
                removed++;
            }
            return removed;
        }

        // Already a single OR key; two named keys is AND and must collapse.
        if (hasEither && !hasNamed && familyCount == 1)
            return 0;

        var rebuilt = new List<string>(realIds.Count);
        var placed = false;
        seen.Clear();
        foreach (var id in realIds)
        {
            if (IsWmExtendedFamilyId(id))
            {
                if (placed) continue;
                placed = true;
                if (loadBeforeIds.Contains(WmExtendedBetaId) && loadBeforeIds.Contains(WmExtendedStableId))
                    continue;
                if (!seen.Add(WmExtendedEitherId)) continue;
                rebuilt.Add(WmExtendedEitherId);
                continue;
            }
            if (!seen.Add(id)) continue;
            rebuilt.Add(id);
        }

        realIds.Clear();
        realIds.AddRange(rebuilt);
        return 1;
    }

    static void ExpandWmExtendedLoadHints(JsonObject root, ModIdCatalog? catalog, List<AppliedFix> fixes)
    {
        var beforeN = ExpandWmExtendedHintField(root, "loadBefore", "LoadBefore", catalog,
            skipEditions: null);
        var loadBeforeIds = CollectMappedIds(root, "loadBefore", "LoadBefore", catalog);
        var afterN = ExpandWmExtendedHintField(root, "loadAfter", "LoadAfter", catalog, loadBeforeIds);
        var n = afterN + beforeN;
        if (n <= 0) return;
        fixes.Add(new AppliedFix
        {
            RuleName = "manifest: WM Extended Mutations LoadAfter/LoadBefore → beta or stable",
            Count = n,
        });
    }

    static int ExpandWmExtendedHintField(JsonObject root, string lookup, string writeKeyDefault,
        ModIdCatalog? catalog, HashSet<string>? skipEditions)
    {
        var key = FindActualKey(root, lookup) ?? FindActualKey(root, writeKeyDefault);
        if (key is null) return 0;
        if (!root.TryGetPropertyValue(key, out var node) || node is null) return 0;

        var existing = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var hadFamily = false;
        CollectIds(node, raw =>
        {
            var id = MapToken(raw, catalog, out var dropped);
            if (dropped || id is null) return;
            if (IsWmExtendedFamilyId(id))
                hadFamily = true;
            if (!seen.Add(id)) return;
            existing.Add(id);
        });

        if (!hadFamily) return 0;

        var skip = skipEditions ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var rebuilt = new List<string>();
        var placed = false;
        var added = 0;
        seen.Clear();
        foreach (var id in existing)
        {
            if (IsWmExtendedFamilyId(id))
            {
                if (placed) continue;
                placed = true;
                TryAddHintEdition(rebuilt, seen, skip, WmExtendedBetaId, ref added);
                TryAddHintEdition(rebuilt, seen, skip, WmExtendedStableId, ref added);
                continue;
            }
            if (!seen.Add(id)) continue;
            rebuilt.Add(id);
        }

        var alreadyBoth = existing.Count == rebuilt.Count
            && rebuilt.All(id => existing.Any(e => string.Equals(e, id, StringComparison.OrdinalIgnoreCase)))
            && existing.All(id => rebuilt.Any(e => string.Equals(e, id, StringComparison.OrdinalIgnoreCase)));
        if (alreadyBoth)
            return 0;

        if (rebuilt.Count == 0)
            root.Remove(key);
        else if (rebuilt.Count == 1)
            root[key] = rebuilt[0];
        else
        {
            var arr = new JsonArray();
            foreach (var id in rebuilt)
                arr.Add(id);
            root[key] = arr;
        }

        return Math.Max(added, 1);
    }

    static void TryAddHintEdition(List<string> dest, HashSet<string> seen, HashSet<string> skip,
        string id, ref int added)
    {
        if (skip.Contains(id)) return;
        if (!seen.Add(id)) return;
        dest.Add(id);
        added++;
    }

    static void RemapStringListField(JsonObject root, string lookup, string writeKeyDefault,
        ModIdCatalog? catalog, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, lookup) ?? FindActualKey(root, writeKeyDefault);
        if (key is null) return;
        if (!root.TryGetPropertyValue(key, out var node) || node is null) return;

        var existing = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var remapped = 0;
        var dropped = 0;
        CollectIds(node, raw =>
        {
            var id = MapToken(raw, catalog, out var drop);
            if (drop) { dropped++; return; }
            if (id is null) return;
            if (raw is not null && !string.Equals(raw.Trim(), id, StringComparison.Ordinal))
                remapped++;
            if (!seen.Add(id)) return;
            existing.Add(id);
        });

        if (remapped == 0 && dropped == 0)
            return;

        if (existing.Count == 0)
            root.Remove(key);
        else if (existing.Count == 1)
            root[key] = existing[0];
        else
        {
            var arr = new JsonArray();
            foreach (var id in existing)
                arr.Add(id);
            root[key] = arr;
        }

        fixes.Add(new AppliedFix
        {
            RuleName = $"manifest: remap {writeKeyDefault} tokens to live ModMap id",
            Count = Math.Max(remapped + dropped, 1),
        });
    }

    static void RemapDirectoryDependencies(JsonObject root, ModIdCatalog? catalog, List<AppliedFix> fixes)
    {
        var key = FindActualKey(root, "directories") ?? FindActualKey(root, "Directories");
        if (key is null) return;
        if (root[key] is not JsonArray arr) return;

        var remapped = 0;
        foreach (var el in arr)
        {
            if (el is not JsonObject dir) continue;
            remapped += RemapDepFieldsInPlace(dir, catalog);
        }

        if (remapped > 0)
        {
            fixes.Add(new AppliedFix
            {
                RuleName = "manifest: remap Directories Dependency keys to live ModMap id",
                Count = remapped,
            });
        }
    }

    static int RemapDepFieldsInPlace(JsonObject obj, ModIdCatalog? catalog)
    {
        var n = 0;
        var shorthandKey = FindActualKey(obj, "dependency");
        if (shorthandKey is not null)
        {
            var mapped = MapToken(NodeToString(obj[shorthandKey]), catalog, out var dropped);
            if (dropped)
            {
                obj.Remove(shorthandKey);
                n++;
            }
            else if (mapped is not null && obj[shorthandKey] is JsonValue)
            {
                var current = NodeToString(obj[shorthandKey]);
                if (!string.Equals(current, mapped, StringComparison.Ordinal))
                {
                    obj[shorthandKey] = mapped;
                    n++;
                }
            }
        }

        var mapKey = FindActualKey(obj, "dependencies");
        if (mapKey is not null && obj[mapKey] is JsonObject map)
        {
            var rebuilt = new JsonObject();
            foreach (var p in map)
            {
                var mapped = MapToken(p.Key, catalog, out var dropped);
                if (dropped || mapped is null) { n++; continue; }
                if (!string.Equals(p.Key, mapped, StringComparison.Ordinal)) n++;
                rebuilt[mapped] = p.Value is null ? "*" : p.Value.DeepClone();
            }
            obj[mapKey] = rebuilt;
        }

        return n;
    }

    static void EnsureMissingId(JsonObject root, string? ensureId, List<AppliedFix> fixes)
    {
        if (string.IsNullOrWhiteSpace(ensureId)) return;
        var id = ModIdCatalog.SanitizeId(ensureId);
        if (id.Length == 0) return;
        if (FindActualKey(root, "id") is not null || FindActualKey(root, "ID") is not null)
            return;

        root["id"] = id;
        fixes.Add(new AppliedFix
        {
            RuleName = "manifest: fill missing id with canonical ModMap id (folder name)",
            Count = 1,
        });
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
