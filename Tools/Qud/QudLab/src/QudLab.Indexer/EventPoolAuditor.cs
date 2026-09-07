using System.Reflection;
using System.Text.Json;
using QudLab.Core.Cache;
using QudLab.Core.Install;

namespace QudLab.Indexer;

/// <summary>
/// Static audit of every <c>MinEvent</c> type in Assembly-CSharp + mod <c>ModAssemblies/*.dll</c>.
/// Detects pooled vs singleton events, mod-added bloat, and FNV1A32 ID conflicts.
/// </summary>
public static class EventPoolAuditor
{
    public static EventPoolAudit Audit(QudInstallInfo install)
    {
        var audit = new EventPoolAudit { BuiltAt = DateTimeOffset.UtcNow };
        var idMap = new Dictionary<int, List<string>>();
        var managed = Directory.Exists(install.ManagedPath)
            ? Directory.GetFiles(install.ManagedPath, "*.dll")
            : Array.Empty<string>();

        Type? minEventType = null;
        ScanAssembly(install.AssemblyCSharpPath, "game", null, managed, ref minEventType, audit, idMap);

        foreach (var mod in QudModPaths.ListAllMods(install.RootPath))
        {
            var asmDir = Path.Combine(mod.Path, "ModAssemblies");
            if (!Directory.Exists(asmDir))
                continue;
            foreach (var dll in Directory.EnumerateFiles(asmDir, "*.dll"))
            {
                ScanAssembly(dll, mod.Source, mod.Path, managed, ref minEventType, audit, idMap);
            }
        }

        foreach (var (id, types) in idMap.Where(kv => kv.Value.Count > 1))
        {
            audit.IdConflicts.Add(new EventIdConflict
            {
                EventId = id,
                Types = types.OrderBy(t => t, StringComparer.OrdinalIgnoreCase).ToList()
            });
        }

        audit.Entries = audit.Entries
            .OrderByDescending(e => e.IsMod)
            .ThenByDescending(e => e.CacheKind == "Pool")
            .ThenBy(e => e.TypeFullName, StringComparer.OrdinalIgnoreCase)
            .ToList();

        audit.TotalEvents = audit.Entries.Count(e => !e.IsAbstract);
        audit.PooledCount = audit.Entries.Count(e => !e.IsAbstract && e.CacheKind == "Pool");
        audit.SingletonCount = audit.Entries.Count(e => !e.IsAbstract && e.CacheKind == "Singleton");
        audit.ModEventCount = audit.Entries.Count(e => !e.IsAbstract && e.IsMod);
        audit.ModPooledCount = audit.Entries.Count(e => !e.IsAbstract && e.IsMod && e.CacheKind == "Pool");

        return audit;
    }

    public static void SaveAudit(EventPoolAudit audit, string? directory = null)
    {
        directory ??= CacheIO.DefaultCacheDir();
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "event-pools-audit.json");
        File.WriteAllText(path, JsonSerializer.Serialize(audit, CacheIO.JsonOptions));
    }

    static void ScanAssembly(
        string assemblyPath,
        string source,
        string? modFolder,
        string[] managedDlls,
        ref Type? minEventType,
        EventPoolAudit audit,
        Dictionary<int, List<string>> idMap)
    {
        if (!File.Exists(assemblyPath))
            return;

        var resolverPaths = managedDlls.Contains(assemblyPath)
            ? managedDlls
            : managedDlls.Concat(new[] { assemblyPath }).Distinct().ToArray();

        try
        {
            var resolver = new PathAssemblyResolver(resolverPaths);
            using var mlc = new MetadataLoadContext(resolver, coreAssemblyName: "mscorlib");
            var asm = mlc.LoadFromAssemblyPath(Path.GetFullPath(assemblyPath));
            minEventType ??= asm.GetType("XRL.World.MinEvent");
            if (minEventType is null && source == "game")
                minEventType = TryLoadMinEventFromGame(assemblyPath, managedDlls);

            Type[] types;
            try { types = asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex)
            {
                types = ex.Types.Where(t => t is not null).Cast<Type>().ToArray();
            }

            foreach (var t in types)
            {
                if (t is null || string.IsNullOrWhiteSpace(t.FullName))
                    continue;
                if (!IsMinEventType(t, minEventType))
                    continue;

                var entry = DescribeEventType(t, source, modFolder, asm.GetName().Name ?? Path.GetFileName(assemblyPath));
                audit.Entries.Add(entry);

                if (!entry.IsAbstract && entry.EventId != 0)
                {
                    if (!idMap.TryGetValue(entry.EventId, out var list))
                    {
                        list = new List<string>();
                        idMap[entry.EventId] = list;
                    }
                    list.Add(entry.TypeFullName);
                }
            }
        }
        catch (Exception ex)
        {
            audit.ScanErrors.Add($"{Path.GetFileName(assemblyPath)}: {ex.Message}");
        }
    }

    static Type? TryLoadMinEventFromGame(string gameAsm, string[] managedDlls)
    {
        try
        {
            var resolver = new PathAssemblyResolver(managedDlls);
            using var mlc = new MetadataLoadContext(resolver, "mscorlib");
            return mlc.LoadFromAssemblyPath(Path.GetFullPath(gameAsm)).GetType("XRL.World.MinEvent");
        }
        catch
        {
            return null;
        }
    }

    static bool IsMinEventType(Type t, Type? minEventType)
    {
        if (minEventType is not null)
        {
            try
            {
                if (minEventType.IsAssignableFrom(t))
                    return true;
            }
            catch { /* metadata */ }
        }

        for (var cur = t; cur is not null; cur = cur.BaseType)
        {
            var name = cur.Name;
            if (name is "MinEvent" or "ModPooledEvent" or "ModSingletonEvent")
                return true;
            if (name.StartsWith("PooledEvent`", StringComparison.Ordinal) ||
                name.StartsWith("SingletonEvent`", StringComparison.Ordinal))
                return true;
        }

        return false;
    }

    static EventPoolEntry DescribeEventType(Type t, string source, string? modFolder, string assemblyName)
    {
        var isMod = !string.Equals(source, "game", StringComparison.OrdinalIgnoreCase);
        var cacheKind = "Unknown";
        int? cascade = null;

        try
        {
            foreach (var data in t.GetCustomAttributesData())
            {
                if (!data.AttributeType.Name.Contains("GameEvent", StringComparison.OrdinalIgnoreCase))
                    continue;
                foreach (var arg in data.NamedArguments)
                {
                    if (arg.MemberName.Equals("Cache", StringComparison.OrdinalIgnoreCase))
                        cacheKind = FormatCacheKind(arg.TypedValue.Value);
                    if (arg.MemberName.Equals("Cascade", StringComparison.OrdinalIgnoreCase) &&
                        arg.TypedValue.Value is int c)
                        cascade = c;
                }
            }
        }
        catch { /* metadata */ }

        if (cacheKind == "Unknown")
            cacheKind = InferCacheFromBase(t);

        var fullName = t.FullName ?? t.Name;
        var eventId = (int)Fnv1a32(fullName);

        return new EventPoolEntry
        {
            TypeFullName = fullName,
            Assembly = assemblyName,
            Source = source,
            ModFolder = modFolder,
            IsMod = isMod,
            IsAbstract = t.IsAbstract,
            CacheKind = cacheKind,
            Cascade = cascade,
            BaseType = SafeName(t.BaseType),
            EventId = eventId,
            Suspicious = isMod && cacheKind == "Pool" && !t.IsAbstract
        };
    }

    static string InferCacheFromBase(Type t)
    {
        for (var cur = t; cur is not null; cur = cur.BaseType)
        {
            var n = cur.Name;
            if (n.StartsWith("PooledEvent`", StringComparison.Ordinal) ||
                n.Contains("ModPooledEvent", StringComparison.OrdinalIgnoreCase))
                return "Pool";
            if (n.StartsWith("SingletonEvent`", StringComparison.Ordinal) ||
                n.Contains("ModSingletonEvent", StringComparison.OrdinalIgnoreCase))
                return "Singleton";
        }
        return "None";
    }

    static string FormatCacheKind(object? value)
    {
        if (value is null)
            return "Unknown";
        var s = value.ToString() ?? "";
        if (s.Contains("Pool", StringComparison.OrdinalIgnoreCase))
            return "Pool";
        if (s.Contains("Singleton", StringComparison.OrdinalIgnoreCase))
            return "Singleton";
        if (s.Contains("None", StringComparison.OrdinalIgnoreCase))
            return "None";
        return s;
    }

    static uint Fnv1a32(string text, uint basis = 2166136261)
    {
        var hash = basis;
        foreach (var c in text)
        {
            hash ^= c;
            hash *= 16777619;
        }
        return hash;
    }

    static string? SafeName(Type? t)
    {
        try { return t?.FullName ?? t?.Name; }
        catch { return null; }
    }
}
