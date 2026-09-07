using System.Reflection;

namespace ApiMigrator.Core;

/// <summary>
/// Read-only reflection over the game's Managed DLLs to find every [Obsolete] member and its
/// message. This NEVER writes to the Managed folder - it only loads assemblies from there
/// (via Assembly.LoadFrom, the same approach already proven to work against Assembly-CSharp.dll
/// by the scratch\ApiDump tool) purely to inspect metadata.
///
/// Loading (not MetadataLoadContext) is used deliberately: Assembly-CSharp.dll's dependencies
/// (UnityEngine.* modules, etc.) are resolved lazily by the CLR, and simply enumerating types /
/// members / attributes for the purpose of reading [Obsolete] text does not usually force those
/// dependencies to load. A custom AssemblyResolve handler is still wired up against the Managed
/// folder as a safety net for the cases where it does.
/// </summary>
public static class DllResearcher
{
    public sealed class ScanResult
    {
        public List<DiscoveredMember> Members { get; } = new();
        public List<string> Warnings { get; } = new();
        public int TypesScanned { get; set; }
    }

    private static readonly object ResolverLock = new();
    private static bool _resolverAttached;
    private static readonly HashSet<string> ProbeDirs = new(StringComparer.OrdinalIgnoreCase);

    private static void EnsureResolver(string managedDir)
    {
        lock (ResolverLock)
        {
            ProbeDirs.Add(managedDir);
            if (_resolverAttached) return;
            AppDomain.CurrentDomain.AssemblyResolve += (_, args) =>
            {
                try
                {
                    var name = new AssemblyName(args.Name).Name;
                    if (name is null) return null;
                    string[] dirs;
                    lock (ResolverLock)
                        dirs = ProbeDirs.ToArray();
                    foreach (var dir in dirs)
                    {
                        var path = Path.Combine(dir, name + ".dll");
                        if (File.Exists(path))
                            return Assembly.LoadFrom(path);
                    }
                    return null;
                }
                catch
                {
                    return null;
                }
            };
            _resolverAttached = true;
        }
    }

    /// <summary>
    /// Scans one or more assemblies (by file name, e.g. "Assembly-CSharp.dll") in
    /// <paramref name="managedDir"/> for every member (method/property/field) carrying an
    /// [Obsolete] attribute, at the type level too.
    /// </summary>
    public static ScanResult ScanForObsoleteMembers(string managedDir, IEnumerable<string> dllFileNames)
    {
        EnsureResolver(managedDir);
        var result = new ScanResult();

        foreach (var dllName in dllFileNames)
        {
            var path = Path.Combine(managedDir, dllName);
            if (!File.Exists(path))
            {
                result.Warnings.Add($"Assembly not found, skipped: {path}");
                continue;
            }

            Assembly asm;
            try
            {
                asm = Assembly.LoadFrom(path);
            }
            catch (Exception ex)
            {
                result.Warnings.Add($"Could not load {dllName}: {ex.Message}");
                continue;
            }

            Type?[] types;
            try
            {
                types = asm.GetTypes();
            }
            catch (ReflectionTypeLoadException rtle)
            {
                types = rtle.Types;
                result.Warnings.Add($"{dllName}: {rtle.LoaderExceptions.Length} type(s) failed to load fully; continuing with the {types.Count(t => t != null)} that did.");
            }
            catch (Exception ex)
            {
                result.Warnings.Add($"Could not enumerate types in {dllName}: {ex.Message}");
                continue;
            }

            const BindingFlags flags = BindingFlags.Public | BindingFlags.NonPublic |
                                        BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;

            foreach (var t in types)
            {
                if (t is null) continue;
                result.TypesScanned++;

                TryAddTypeLevel(result, t);

                MethodInfo[] methods;
                PropertyInfo[] props;
                FieldInfo[] fields;
                try { methods = t.GetMethods(flags); } catch { methods = Array.Empty<MethodInfo>(); }
                try { props = t.GetProperties(flags); } catch { props = Array.Empty<PropertyInfo>(); }
                try { fields = t.GetFields(flags); } catch { fields = Array.Empty<FieldInfo>(); }

                foreach (var m in methods)
                {
                    if (m.IsSpecialName) continue; // skip property/event accessor plumbing
                    TryAddMember(result, t, m, "Method", () => FormatMethodSignature(m));
                }
                foreach (var p in props)
                {
                    TryAddMember(result, t, p, "Property", () => $"{p.PropertyType.Name} {p.Name}");
                }
                foreach (var f in fields)
                {
                    TryAddMember(result, t, f, "Field", () => $"{(f.IsStatic ? "static " : "")}{f.FieldType.Name} {f.Name}");
                }
            }
        }

        return result;
    }

    private static void TryAddTypeLevel(ScanResult result, Type t)
    {
        try
        {
            var attr = t.GetCustomAttribute<ObsoleteAttribute>();
            if (attr is not null)
            {
                result.Members.Add(new DiscoveredMember
                {
                    Type = t.FullName ?? t.Name,
                    Member = "(type)",
                    Kind = "Type",
                    Signature = t.FullName ?? t.Name,
                    ObsoleteMessage = attr.Message ?? "",
                    IsError = attr.IsError,
                });
            }
        }
        catch
        {
            // ignore types whose attribute data can't be resolved
        }
    }

    private static void TryAddMember(ScanResult result, Type t, MemberInfo m, string kind, Func<string> signature)
    {
        try
        {
            var attr = m.GetCustomAttribute<ObsoleteAttribute>();
            if (attr is null) return;
            result.Members.Add(new DiscoveredMember
            {
                Type = t.FullName ?? t.Name,
                Member = m.Name,
                Kind = kind,
                Signature = signature(),
                ObsoleteMessage = attr.Message ?? "",
                IsError = attr.IsError,
            });
        }
        catch
        {
            // ignore members whose attribute data can't be resolved (e.g. referencing an
            // unavailable Unity type) - this is read-only research, not correctness-critical.
        }
    }

    private static string FormatMethodSignature(MethodInfo m)
    {
        string ps;
        try
        {
            ps = string.Join(", ", m.GetParameters().Select(p =>
                $"{p.ParameterType.Name} {p.Name}" + (p.HasDefaultValue ? $" = {p.DefaultValue}" : "")));
        }
        catch
        {
            ps = "?";
        }
        return $"{(m.IsStatic ? "static " : "")}{m.ReturnType.Name} {m.Name}({ps})";
    }

    /// <summary>
    /// Compares a previously-saved dump against a freshly discovered member list, so a user
    /// can see exactly what changed between game versions before committing a refresh.
    /// </summary>
    public static DumpDiffResult Diff(ObsoleteDump oldDump, List<DiscoveredMember> newMembers)
    {
        var diff = new DumpDiffResult();

        // Members can be overloaded (multiple entries sharing Type+Member with different
        // Signature), so group rather than assume a unique key - a dump built by hand may
        // merge overloads into one entry, while a freshly-reflected dump keeps them separate.
        var oldGroups = oldDump.Entries.GroupBy(e => (e.Type, e.Member))
            .ToDictionary(g => g.Key, g => g.ToList());
        var newGroups = newMembers.GroupBy(m => (m.Type, m.Member))
            .ToDictionary(g => g.Key, g => g.ToList());

        foreach (var (key, newList) in newGroups)
        {
            if (!oldGroups.TryGetValue(key, out var oldList))
            {
                diff.Added.AddRange(newList);
                continue;
            }

            var oldMessages = oldList.Select(e => e.ObsoleteMessage?.Trim() ?? "").ToHashSet(StringComparer.Ordinal);
            foreach (var newM in newList)
            {
                var msg = newM.ObsoleteMessage?.Trim() ?? "";
                if (oldMessages.Contains(msg))
                {
                    diff.UnchangedCount++;
                }
                else if (oldList.Count == 1)
                {
                    diff.MessageChanged.Add((oldList[0], newM));
                }
                else
                {
                    // Ambiguous which specific old overload this corresponds to; report as added
                    // rather than guessing which old entry it "changed" from.
                    diff.Added.Add(newM);
                }
            }
        }

        foreach (var (key, oldList) in oldGroups)
        {
            if (!newGroups.ContainsKey(key))
            {
                diff.Removed.AddRange(oldList);
            }
        }

        return diff;
    }
}
