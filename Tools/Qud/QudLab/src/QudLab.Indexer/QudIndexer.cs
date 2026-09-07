using System.Reflection;
using System.Xml.Linq;
using QudLab.Core.Cache;
using QudLab.Core.Install;

namespace QudLab.Indexer;

public sealed class QudIndexer
{
    const int NonGameSoftCap = 2000;

    public IntelligenceCache Build(QudInstallInfo install, string? projectRoot = null)
    {
        var cache = new IntelligenceCache
        {
            GameRoot = install.RootPath,
            BuiltAt = DateTimeOffset.UtcNow,
            SchemaVersion = CacheIO.CurrentSchemaVersion,
            Stamp = CacheIO.CreateStamp(install)
        };

        IndexAssemblies(install, cache);
        IndexBlueprints(install, cache);
        IndexBaseXml(install, cache);

        if (!string.IsNullOrWhiteSpace(projectRoot))
            CacheIO.ScanProject(cache.Project, projectRoot);

        return cache;
    }

    void IndexAssemblies(QudInstallInfo install, IntelligenceCache cache)
    {
        var asmPath = install.AssemblyCSharpPath;
        if (!File.Exists(asmPath))
            return;

        var managedDlls = Directory.GetFiles(install.ManagedPath, "*.dll");
        var resolver = new PathAssemblyResolver(managedDlls);
        using var mlc = new MetadataLoadContext(resolver, coreAssemblyName: "mscorlib");

        Assembly asm;
        try
        {
            asm = mlc.LoadFromAssemblyPath(asmPath);
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Failed to load Assembly-CSharp: {ex.Message}");
            return;
        }

        Type[] types;
        try
        {
            types = asm.GetTypes();
        }
        catch (ReflectionTypeLoadException ex)
        {
            types = ex.Types.Where(t => t is not null).Cast<Type>().ToArray();
            cache.Project.Diagnostics.Add($"Partial type load: {ex.LoaderExceptions?.Length ?? 0} errors");
        }

        // Prefer XRL.World / Parts / Mutation first, then remaining XRL/Qud, then noise (soft-capped).
        var ordered = types
            .Where(t => t?.FullName is not null)
            .OrderBy(t => TypePriority(t!.FullName!))
            .ThenBy(t => t!.FullName, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var eventNames = new HashSet<string>(StringComparer.Ordinal);
        var eventTypeNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var nonGameCount = 0;

        foreach (var t in ordered)
        {
            var full = t!.FullName!;
            var isGame = IsGameType(full);
            if (!isGame)
            {
                if (nonGameCount >= NonGameSoftCap)
                    continue;
                nonGameCount++;
            }

            var node = BuildTypeNode(t, eventNames);
            cache.TypeGraph.Types[full] = node;

            if (LooksLikeEventType(full))
                eventTypeNames.Add(full);

            var eventMethods = node.Methods
                .Where(m => m.Contains("Event", StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (eventMethods.Count > 0 && (isGame || full.Contains("Event", StringComparison.OrdinalIgnoreCase)))
                cache.EventGraph.HandlersByType[full] = eventMethods;
        }

        cache.EventGraph.EventNames = eventNames.OrderBy(n => n).ToList();
        cache.EventGraph.EventTypeNames = eventTypeNames.OrderBy(n => n, StringComparer.OrdinalIgnoreCase).ToList();

        try
        {
            cache.EventGraph.PoolAudit = EventPoolAuditor.Audit(install);
            EventPoolAuditor.SaveAudit(cache.EventGraph.PoolAudit);
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Event pool audit: {ex.Message}");
        }
    }

    static int TypePriority(string fullName)
    {
        if (fullName.StartsWith("XRL.World.Parts.Mutation", StringComparison.Ordinal)) return 0;
        if (fullName.StartsWith("XRL.World.Parts", StringComparison.Ordinal)) return 1;
        if (fullName.StartsWith("XRL.World", StringComparison.Ordinal)) return 2;
        if (fullName.StartsWith("XRL.", StringComparison.Ordinal)) return 3;
        if (fullName.StartsWith("Qud.", StringComparison.Ordinal)) return 4;
        return 10;
    }

    static bool IsGameType(string fullName) =>
        fullName.StartsWith("XRL.", StringComparison.Ordinal) ||
        fullName.StartsWith("Qud.", StringComparison.Ordinal);

    static bool LooksLikeEventType(string fullName) =>
        fullName.Contains(".Event", StringComparison.OrdinalIgnoreCase) ||
        fullName.EndsWith("Event", StringComparison.OrdinalIgnoreCase) ||
        fullName.Contains("MinEvent", StringComparison.OrdinalIgnoreCase);

    static TypeNode BuildTypeNode(Type t, HashSet<string> eventNames)
    {
        var node = new TypeNode
        {
            FullName = t.FullName!,
            Namespace = t.Namespace,
            BaseType = SafeName(t.BaseType)
        };

        try
        {
            foreach (var i in t.GetInterfaces())
            {
                var n = SafeName(i);
                if (n is not null)
                    node.Interfaces.Add(n);
            }
        }
        catch { /* metadata gaps */ }

        try
        {
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
            {
                if (m.IsSpecialName)
                    continue;
                node.Methods.Add($"{m.Name}({m.GetParameters().Length})");
                if (m.Name is "FireEvent" or "HandleEvent" or "WantEvent" ||
                    m.Name.Contains("Event", StringComparison.Ordinal))
                {
                    eventNames.Add(m.Name);
                }
            }
        }
        catch { }

        try
        {
            foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                node.Fields.Add(f.Name);
        }
        catch { }

        try
        {
            foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                node.Properties.Add(p.Name);
        }
        catch { }

        try
        {
            foreach (var a in t.GetCustomAttributesData())
                node.Attributes.Add(a.AttributeType.Name);
        }
        catch { }

        return node;
    }

    void IndexBlueprints(QudInstallInfo install, IntelligenceCache cache)
    {
        var bpDir = Path.Combine(install.BaseDataPath, "ObjectBlueprints");
        if (!Directory.Exists(bpDir))
            return;

        foreach (var file in Directory.EnumerateFiles(bpDir, "*.xml", SearchOption.AllDirectories))
        {
            try
            {
                var doc = LoadXml(file);
                foreach (var obj in doc.Descendants("object"))
                {
                    var name = Attr(obj, "Name", "name");
                    if (string.IsNullOrWhiteSpace(name))
                        continue;

                    var node = new BlueprintNode
                    {
                        Name = name,
                        Inherits = Attr(obj, "Inherits", "inherits"),
                        SourceFile = Rel(install, file)
                    };

                    foreach (var part in obj.Elements("part"))
                    {
                        var pn = Attr(part, "Name", "name");
                        if (!string.IsNullOrWhiteSpace(pn))
                            node.Parts.Add(pn);
                    }

                    foreach (var stat in obj.Elements("stat"))
                    {
                        var sn = Attr(stat, "Name", "name");
                        var sv = Attr(stat, "sValue", "Value", "value") ?? stat.Value;
                        if (!string.IsNullOrWhiteSpace(sn))
                            node.Stats[sn] = sv ?? "";
                    }

                    foreach (var tag in obj.Elements("tag"))
                    {
                        var tn = Attr(tag, "Name", "name");
                        var tv = Attr(tag, "Value", "value") ?? "";
                        if (!string.IsNullOrWhiteSpace(tn))
                            node.Tags[tn] = tv;
                    }

                    cache.BlueprintGraph.Objects[name] = node;
                }
            }
            catch (Exception ex)
            {
                cache.Project.Diagnostics.Add($"Blueprint parse {file}: {ex.Message}");
            }
        }
    }

    void IndexBaseXml(QudInstallInfo install, IntelligenceCache cache)
    {
        IndexMutations(install, cache, "Mutations.xml");
        IndexMutations(install, cache, "HiddenMutations.xml");
        IndexAbilities(install, cache, "ActivatedAbilities.xml");
        IndexCommandsAndActions(install, cache, "Commands.xml", "command");
        IndexCommandsAndActions(install, cache, "InventoryActions.xml", "inventory");
        IndexCatalog(install, cache, "Bodies.xml", "body", "body", "Name", "name", "ID", "id");
        IndexSkills(install, cache);
        IndexCatalog(install, cache, "EffectsDetails.xml", "effect", "effect", "Name", "name", "Class", "class");
        IndexGenotypes(install, cache);
        IndexSubtypes(install, cache);
        IndexEmbarkModules(install, cache);
        IndexPopulations(install, cache);
    }

    void IndexMutations(QudInstallInfo install, IntelligenceCache cache, string fileName)
    {
        var path = Path.Combine(install.BaseDataPath, fileName);
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            foreach (var cat in doc.Descendants("category"))
            {
                var catName = Attr(cat, "Name", "name") ?? "";
                foreach (var m in cat.Elements("mutation"))
                {
                    var name = Attr(m, "Name", "name");
                    if (string.IsNullOrWhiteSpace(name))
                        continue;
                    cache.MutationGraph.Mutations[name] = new MutationNode
                    {
                        Name = name,
                        Class = Attr(m, "Class", "class"),
                        Category = catName,
                        Cost = Attr(m, "Cost", "cost"),
                        Exclusions = Attr(m, "Exclusions", "exclusions"),
                        Tile = Attr(m, "Tile", "tile"),
                        SourceFile = Rel(install, path)
                    };
                }
            }

            // Some files may place mutations outside categories
            foreach (var m in doc.Descendants("mutation"))
            {
                var name = Attr(m, "Name", "name");
                if (string.IsNullOrWhiteSpace(name) || cache.MutationGraph.Mutations.ContainsKey(name))
                    continue;
                cache.MutationGraph.Mutations[name] = new MutationNode
                {
                    Name = name,
                    Class = Attr(m, "Class", "class"),
                    Cost = Attr(m, "Cost", "cost"),
                    Exclusions = Attr(m, "Exclusions", "exclusions"),
                    Tile = Attr(m, "Tile", "tile"),
                    SourceFile = Rel(install, path)
                };
            }
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Mutation parse {fileName}: {ex.Message}");
        }
    }

    void IndexAbilities(QudInstallInfo install, IntelligenceCache cache, string fileName)
    {
        var path = Path.Combine(install.BaseDataPath, fileName);
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            foreach (var a in doc.Descendants("ability"))
            {
                var cmd = Attr(a, "Command", "command", "Name", "name");
                if (string.IsNullOrWhiteSpace(cmd))
                    continue;
                var desc = a.Element("description")?.Value?.Trim();
                if (string.IsNullOrWhiteSpace(desc))
                    desc = string.Join(" ", a.Element("description")?.Elements("p").Select(p => p.Value.Trim()) ?? Array.Empty<string>());
                var tile = a.Element("UITile") is { } tileEl ? Attr(tileEl, "Tile", "tile") : null;
                cache.AbilityGraph.Abilities[cmd] = new AbilityNode
                {
                    Command = cmd,
                    Description = Truncate(desc, 400),
                    Tile = tile,
                    SourceFile = Rel(install, path)
                };
            }
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Ability parse {fileName}: {ex.Message}");
        }
    }

    void IndexCommandsAndActions(QudInstallInfo install, IntelligenceCache cache, string fileName, string kind)
    {
        var path = Path.Combine(install.BaseDataPath, fileName);
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            foreach (var el in doc.Descendants())
            {
                if (el.Name.LocalName is not ("command" or "action" or "layer" or "navcategory"))
                    continue;
                var id = Attr(el, "ID", "Id", "id", "Name", "name", "Command", "command");
                if (string.IsNullOrWhiteSpace(id))
                    continue;
                var key = $"{kind}:{id}";
                var node = new CommandNode
                {
                    Id = id,
                    Kind = kind + "/" + el.Name.LocalName,
                    SourceFile = Rel(install, path)
                };
                foreach (var atr in el.Attributes())
                    node.Attrs[atr.Name.LocalName] = atr.Value;
                cache.CommandGraph.Commands[key] = node;
            }
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Command parse {fileName}: {ex.Message}");
        }
    }

    void IndexSkills(QudInstallInfo install, IntelligenceCache cache)
    {
        var path = Path.Combine(install.BaseDataPath, "Skills.xml");
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var list = new List<CatalogEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var el in doc.Descendants())
            {
                if (el.Name.LocalName is not ("skill" or "power"))
                    continue;
                var classId = Attr(el, "Class", "class");
                var name = Attr(el, "Name", "name");
                var id = classId ?? name;
                if (string.IsNullOrWhiteSpace(id) || !seen.Add(id))
                    continue;
                var entry = new CatalogEntry
                {
                    Id = id,
                    DisplayName = name ?? id,
                    Kind = el.Name.LocalName,
                    Parent = el.Parent is null ? null : Attr(el.Parent, "Class", "class", "Name", "name")
                };
                CopyAttrs(el, entry);
                list.Add(entry);
            }

            cache.Catalogs.BySource["skill"] = list;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Skills parse: {ex.Message}");
        }
    }

    void IndexPopulations(QudInstallInfo install, IntelligenceCache cache)
    {
        var path = Path.Combine(install.BaseDataPath, "PopulationTables.xml");
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var list = new List<CatalogEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var el in doc.Descendants("population"))
            {
                var id = Attr(el, "Name", "name");
                if (string.IsNullOrWhiteSpace(id) || !seen.Add(id))
                    continue;
                list.Add(new CatalogEntry
                {
                    Id = id,
                    DisplayName = id,
                    Kind = "population"
                });
            }

            cache.Catalogs.BySource["population"] = list;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"PopulationTables parse: {ex.Message}");
        }
    }

    void IndexGenotypes(QudInstallInfo install, IntelligenceCache cache)
    {
        var path = Path.Combine(install.BaseDataPath, "Genotypes.xml");
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var list = new List<CatalogEntry>();
            foreach (var el in doc.Descendants("genotype"))
            {
                var id = Attr(el, "Name", "name");
                if (string.IsNullOrWhiteSpace(id))
                    continue;
                var entry = new CatalogEntry
                {
                    Id = id,
                    DisplayName = Attr(el, "DisplayName", "displayName") ?? id,
                    Kind = "genotype",
                    Parent = Attr(el, "Subtypes", "subtypes")
                };
                CopyAttrs(el, entry);
                entry.Skills.AddRange(DescendantNames(el, "skill"));
                list.Add(entry);
            }

            cache.Catalogs.BySource["genotype"] = list;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Genotype parse: {ex.Message}");
        }
    }

    void IndexSubtypes(QudInstallInfo install, IntelligenceCache cache)
    {
        var path = Path.Combine(install.BaseDataPath, "Subtypes.xml");
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var list = new List<CatalogEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var classEl in doc.Descendants("class"))
            {
                var classId = Attr(classEl, "ID", "Id", "id") ?? "";
                foreach (var sub in classEl.Descendants("subtype"))
                {
                    var id = Attr(sub, "Name", "name");
                    if (string.IsNullOrWhiteSpace(id) || !seen.Add(id))
                        continue;
                    var category = sub.Parent is null ? null : Attr(sub.Parent, "Name", "name");
                    if (string.Equals(sub.Parent?.Name.LocalName, "class", StringComparison.OrdinalIgnoreCase))
                        category = null;
                    var entry = new CatalogEntry
                    {
                        Id = id,
                        DisplayName = Attr(sub, "DisplayName", "displayName") ?? id,
                        Kind = "subtype",
                        Parent = classId
                    };
                    CopyAttrs(sub, entry);
                    if (!string.IsNullOrWhiteSpace(category))
                        entry.Attrs["Category"] = category;
                    if (!string.IsNullOrWhiteSpace(classId))
                        entry.Attrs["Class"] = classId;
                    entry.Skills.AddRange(DescendantNames(sub, "skill"));
                    var stats = sub.Elements("stat")
                        .Select(s =>
                        {
                            var n = Attr(s, "Name", "name");
                            var b = Attr(s, "Bonus", "bonus") ?? Attr(s, "Value", "value");
                            return string.IsNullOrWhiteSpace(n) ? null : n + ":" + (b ?? "0");
                        })
                        .Where(s => s is not null)
                        .Cast<string>()
                        .ToList();
                    if (stats.Count > 0)
                        entry.Attrs["stats"] = string.Join(",", stats);
                    list.Add(entry);
                }
            }

            cache.Catalogs.BySource["subtype"] = list;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Subtype parse: {ex.Message}");
        }
    }

    void IndexEmbarkModules(QudInstallInfo install, IntelligenceCache cache)
    {
        var path = Path.Combine(install.BaseDataPath, "EmbarkModules.xml");
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var modules = new List<CatalogEntry>();
            var pregens = new List<CatalogEntry>();
            var locations = new List<CatalogEntry>();
            var order = 0;
            foreach (var mod in doc.Descendants("module"))
            {
                var cls = Attr(mod, "Class", "class");
                if (string.IsNullOrWhiteSpace(cls))
                    continue;
                var shortName = cls.Contains('.') ? cls[(cls.LastIndexOf('.') + 1)..] : cls;
                var window = mod.Element("window");
                var entry = new CatalogEntry
                {
                    Id = shortName,
                    DisplayName = cls,
                    Kind = "embark-module",
                    Parent = window is null ? null : Attr(window, "ID", "Id", "id")
                };
                entry.Attrs["Class"] = cls;
                entry.Attrs["Order"] = order.ToString();
                modules.Add(entry);
                order++;
            }

            foreach (var pre in doc.Descendants("pregen"))
            {
                var id = Attr(pre, "Name", "name");
                if (string.IsNullOrWhiteSpace(id))
                    continue;
                var entry = new CatalogEntry
                {
                    Id = id,
                    DisplayName = id,
                    Kind = "pregen",
                    Parent = Attr(pre, "Genotype", "genotype")
                };
                CopyAttrs(pre, entry);
                pregens.Add(entry);
            }

            foreach (var loc in doc.Descendants("location"))
            {
                var id = Attr(loc, "ID", "Id", "id");
                if (string.IsNullOrWhiteSpace(id))
                    continue;
                var entry = new CatalogEntry
                {
                    Id = id,
                    DisplayName = Attr(loc, "Name", "name") ?? id,
                    Kind = "starting-location"
                };
                CopyAttrs(loc, entry);
                locations.Add(entry);
            }

            cache.Catalogs.BySource["embark-module"] = modules;
            cache.Catalogs.BySource["pregen"] = pregens;
            cache.Catalogs.BySource["starting-location"] = locations;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"EmbarkModules parse: {ex.Message}");
        }
    }

    static void CopyAttrs(XElement el, CatalogEntry entry)
    {
        foreach (var atr in el.Attributes())
        {
            if (string.Equals(atr.Name.LocalName, "Name", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(atr.Name.LocalName, "DisplayName", StringComparison.OrdinalIgnoreCase))
                continue;
            entry.Attrs[atr.Name.LocalName] = atr.Value;
        }
    }

    static IEnumerable<string> DescendantNames(XElement el, string localName)
    {
        foreach (var child in el.Descendants(localName))
        {
            var n = Attr(child, "Name", "name", "Class", "class");
            if (!string.IsNullOrWhiteSpace(n))
                yield return n;
        }
    }

    void IndexCatalog(
        QudInstallInfo install,
        IntelligenceCache cache,
        string fileName,
        string sourceKey,
        string kind,
        params string[] idAttrs)
    {
        var path = Path.Combine(install.BaseDataPath, fileName);
        if (!File.Exists(path))
            return;
        try
        {
            var doc = LoadXml(path);
            var list = new List<CatalogEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var el in doc.Descendants())
            {
                if (el == doc.Root)
                    continue;
                string? id = null;
                foreach (var a in idAttrs)
                {
                    id = (string?)el.Attribute(a);
                    if (!string.IsNullOrWhiteSpace(id))
                        break;
                }
                if (string.IsNullOrWhiteSpace(id) || !seen.Add(id))
                    continue;
                list.Add(new CatalogEntry
                {
                    Id = id,
                    DisplayName = Attr(el, "DisplayName", "displayName") ?? id,
                    Kind = kind
                });
            }
            cache.Catalogs.BySource[sourceKey] = list;
        }
        catch (Exception ex)
        {
            cache.Project.Diagnostics.Add($"Catalog parse {fileName}: {ex.Message}");
        }
    }

    static XDocument LoadXml(string file)
    {
        var settings = new System.Xml.XmlReaderSettings
        {
            CheckCharacters = false,
            DtdProcessing = System.Xml.DtdProcessing.Prohibit,
            IgnoreComments = true
        };
        using var reader = System.Xml.XmlReader.Create(file, settings);
        return XDocument.Load(reader, LoadOptions.None);
    }

    static string? Attr(XElement el, params string[] names)
    {
        foreach (var n in names)
        {
            var v = (string?)el.Attribute(n);
            if (!string.IsNullOrWhiteSpace(v))
                return v;
        }
        return null;
    }

    static string Rel(QudInstallInfo install, string file) =>
        Path.GetRelativePath(install.BaseDataPath, file).Replace('\\', '/');

    static string? Truncate(string? s, int max)
    {
        if (string.IsNullOrEmpty(s))
            return s;
        s = string.Join(' ', s.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        return s.Length <= max ? s : s[..max] + "…";
    }

    static string? SafeName(Type? t)
    {
        try { return t?.FullName ?? t?.Name; }
        catch { return null; }
    }
}
