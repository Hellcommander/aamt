using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Per-game-version profiles under <c>data/by-version/{FileVersion}/</c> holding both the
/// obsolete dump and curated rewrite rules. Syncs active
/// <c>obsolete_api_dump.json</c> + <c>curated_rewrite_rules.json</c> when Managed FileVersion
/// (Steam branch) changes, unless a <c>switch-api</c> pin is in effect.
/// </summary>
public static class DumpVersionControl
{
    public const string ActiveDumpFileName = "obsolete_api_dump.json";
    public const string ActiveRulesFileName = "curated_rewrite_rules.json";
    public const string ChartsFolderName = "charts";
    public const string VersionsFolderName = "by-version";
    public const string OverrideFileName = "active-override.json";
    public const string ProfileMetaFileName = "meta.json";
    public static string DefaultManagedDir => SteamInstall.ManagedDirOrFallback;
    public static string DefaultAppManifest =>
        SteamInstall.LibraryRoot is null
            ? Path.Combine(SteamInstall.FallbackLibraryRoots[0], "steamapps", "appmanifest_333640.acf")
            : Path.Combine(SteamInstall.LibraryRoot, "steamapps", "appmanifest_333640.acf");

    static readonly JsonSerializerOptions OverrideJson = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
    };

    public sealed class ProfileOverride
    {
        public string? ForceFileVersion { get; set; }
        public string? Reason { get; set; }
        public string? Updated { get; set; }
    }

    public sealed class VersionProfileInfo
    {
        public string FileVersion { get; set; } = "";
        public string Directory { get; set; } = "";
        public string? SteamBetaKey { get; set; }
        public string? SteamBuildId { get; set; }
        public bool HasDump { get; set; }
    }

    public sealed class ResolveResult
    {
        public string DataDir { get; set; } = "";
        public string ActiveDumpPath { get; set; } = "";
        public string ActiveRulesPath { get; set; } = "";
        public string? ProfileDir { get; set; }
        public string? GameFileVersion { get; set; }
        public string? SteamBetaKey { get; set; }
        public string? SteamBuildId { get; set; }
        public bool SwitchedActive { get; set; }
        public bool SnapshottedPrevious { get; set; }
        public bool Forced { get; set; }
        public string? ForcedFileVersion { get; set; }
        public string? LiveFileVersion { get; set; }
        public string Message { get; set; } = "";
    }

    public static string VersionsDirectory(string dataDir) =>
        Path.Combine(dataDir, VersionsFolderName);

    public static string OverridePath(string dataDir) =>
        Path.Combine(VersionsDirectory(dataDir), OverrideFileName);

    public static string ProfileDirectory(string dataDir, string fileVersion) =>
        Path.Combine(VersionsDirectory(dataDir), SanitizeFileVersion(fileVersion));

    public static string SanitizeFileVersion(string fileVersion)
    {
        var s = fileVersion.Trim();
        if (string.IsNullOrEmpty(s)) return "unknown";
        return Regex.Replace(s, @"[^\w\.\-]+", "_");
    }

    public static string? TryGetManagedFileVersion(string? managedDir = null)
    {
        managedDir ??= DefaultManagedDir;
        var dll = Path.Combine(managedDir, "Assembly-CSharp.dll");
        if (!File.Exists(dll)) return null;
        try
        {
            return FileVersionInfo.GetVersionInfo(dll).FileVersion?.Trim();
        }
        catch
        {
            return null;
        }
    }

    public static (string? BetaKey, string? BuildId) TryReadSteamBranch(string? appManifestPath = null)
    {
        appManifestPath ??= DefaultAppManifest;
        if (!File.Exists(appManifestPath)) return (null, null);
        try
        {
            var text = File.ReadAllText(appManifestPath);
            var user = Regex.Match(text,
                @"UserConfig\s*\{[^}]*""BetaKey""\s+""([^""]+)""",
                RegexOptions.Singleline | RegexOptions.IgnoreCase);
            string? beta = user.Success ? user.Groups[1].Value : null;
            if (beta is null)
            {
                var any = Regex.Match(text, @"""BetaKey""\s+""([^""]+)""");
                if (any.Success) beta = any.Groups[1].Value;
            }
            var build = Regex.Match(text, @"""buildid""\s+""(\d+)""");
            return (beta, build.Success ? build.Groups[1].Value : null);
        }
        catch
        {
            return (null, null);
        }
    }

    static string? ReadActiveGameFileVersion(string activeDumpPath)
    {
        if (!File.Exists(activeDumpPath)) return null;
        try
        {
            return DumpStore.LoadDump(activeDumpPath).Meta?.GameFileVersion?.Trim();
        }
        catch
        {
            return null;
        }
    }

    public static ProfileOverride? ReadOverride(string dataDir)
    {
        var path = OverridePath(dataDir);
        if (!File.Exists(path)) return null;
        try
        {
            var ov = JsonSerializer.Deserialize<ProfileOverride>(File.ReadAllText(path), OverrideJson);
            if (ov is null || string.IsNullOrWhiteSpace(ov.ForceFileVersion)) return null;
            ov.ForceFileVersion = ov.ForceFileVersion.Trim();
            return ov;
        }
        catch
        {
            return null;
        }
    }

    public static void WriteOverride(string dataDir, string fileVersion, string? reason = null)
    {
        Directory.CreateDirectory(VersionsDirectory(dataDir));
        var ov = new ProfileOverride
        {
            ForceFileVersion = SanitizeFileVersion(fileVersion),
            Reason = reason,
            Updated = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
        };
        File.WriteAllText(OverridePath(dataDir), JsonSerializer.Serialize(ov, OverrideJson));
    }

    public static void ClearOverride(string dataDir)
    {
        var path = OverridePath(dataDir);
        if (File.Exists(path)) File.Delete(path);
    }

    public static IReadOnlyList<VersionProfileInfo> ListProfiles(string dataDir, bool includeSnapshots = true)
    {
        var dir = VersionsDirectory(dataDir);
        if (!Directory.Exists(dir)) return Array.Empty<VersionProfileInfo>();

        var list = new List<VersionProfileInfo>();
        foreach (var folder in Directory.GetDirectories(dir))
        {
            var name = Path.GetFileName(folder) ?? "";
            if (string.IsNullOrEmpty(name)) continue;
            if (!includeSnapshots && name.StartsWith("unknown-", StringComparison.OrdinalIgnoreCase))
                continue;

            var info = new VersionProfileInfo
            {
                FileVersion = name,
                Directory = folder,
                HasDump = File.Exists(Path.Combine(folder, ActiveDumpFileName)),
            };
            var meta = TryReadProfileMeta(folder);
            if (meta is not null)
            {
                if (!string.IsNullOrWhiteSpace(meta.GameFileVersion))
                    info.FileVersion = meta.GameFileVersion.Trim();
                info.SteamBetaKey = meta.SteamBetaKey;
                info.SteamBuildId = meta.SteamBuildId;
            }
            list.Add(info);
        }

        return list
            .OrderBy(p => p.FileVersion, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    sealed class ProfileMetaFields
    {
        public string? GameFileVersion { get; set; }
        public string? SteamBetaKey { get; set; }
        public string? SteamBuildId { get; set; }
    }

    static ProfileMetaFields? TryReadProfileMeta(string profileDir)
    {
        var path = Path.Combine(profileDir, ProfileMetaFileName);
        if (!File.Exists(path)) return null;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var root = doc.RootElement;
            string? Get(params string[] names)
            {
                foreach (var n in names)
                {
                    if (root.TryGetProperty(n, out var el) && el.ValueKind == JsonValueKind.String)
                    {
                        var s = el.GetString();
                        if (!string.IsNullOrWhiteSpace(s)) return s;
                    }
                }
                return null;
            }
            return new ProfileMetaFields
            {
                GameFileVersion = Get("gameFileVersion", "GameFileVersion"),
                SteamBetaKey = Get("steamBetaKey", "SteamBetaKey"),
                SteamBuildId = Get("steamBuildId", "SteamBuildId"),
            };
        }
        catch
        {
            return null;
        }
    }

    public static bool IsFollowLiveAlias(string alias)
    {
        var s = alias.Trim().ToLowerInvariant();
        return s is "live" or "auto" or "steam" or "follow" or "follow-steam";
    }

    /// <summary>
    /// Resolve <c>public</c>/<c>lang</c>/<c>2.0.211.51</c> to a profile FileVersion.
    /// Returns null for follow-live aliases and unknown names.
    /// </summary>
    public static string? ResolveProfileAlias(string dataDir, string aliasOrVersion)
    {
        var s = aliasOrVersion.Trim();
        if (string.IsNullOrEmpty(s) || IsFollowLiveAlias(s)) return null;

        var profiles = ListProfiles(dataDir, includeSnapshots: false);
        var sanitized = SanitizeFileVersion(s);
        var exact = profiles.FirstOrDefault(p =>
            string.Equals(p.FileVersion, s, StringComparison.OrdinalIgnoreCase)
            || string.Equals(Path.GetFileName(p.Directory), sanitized, StringComparison.OrdinalIgnoreCase));
        if (exact is not null) return exact.FileVersion;

        var key = s.ToLowerInvariant();
        if (key is "public" or "stable" or "public-stable" or "release")
        {
            return PickByBeta(profiles, "public")
                   ?? PickVersionPrefix(profiles, "2.0.211");
        }
        if (key is "lang" or "beta" or "lang-experimental" or "lang-beta" or "experimental")
        {
            return PickByBetaContains(profiles, "lang")
                   ?? PickVersionPrefix(profiles, "2.0.212");
        }

        return null;
    }

    static string? PickByBeta(IReadOnlyList<VersionProfileInfo> profiles, string beta) =>
        profiles.LastOrDefault(p =>
            p.HasDump && string.Equals(p.SteamBetaKey, beta, StringComparison.OrdinalIgnoreCase))
            ?.FileVersion;

    static string? PickByBetaContains(IReadOnlyList<VersionProfileInfo> profiles, string fragment) =>
        profiles.LastOrDefault(p =>
            p.HasDump && p.SteamBetaKey is not null
            && p.SteamBetaKey.Contains(fragment, StringComparison.OrdinalIgnoreCase))
            ?.FileVersion;

    static string? PickVersionPrefix(IReadOnlyList<VersionProfileInfo> profiles, string prefix) =>
        profiles.LastOrDefault(p =>
            p.HasDump && p.FileVersion.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            ?.FileVersion;

    public static string DescribeAvailableProfiles(string dataDir)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Aliases: live / auto (follow Steam), public / stable, lang / beta / lang-experimental, or a FileVersion folder.");
        var profiles = ListProfiles(dataDir);
        if (profiles.Count == 0)
        {
            sb.AppendLine("  (no by-version profiles yet — run sync-version --save-profile after a dump refresh)");
            return sb.ToString();
        }
        foreach (var p in profiles)
        {
            var beta = string.IsNullOrEmpty(p.SteamBetaKey) ? "" : $" ({p.SteamBetaKey})";
            var dump = p.HasDump ? "" : " [no dump]";
            sb.AppendLine($"  {p.FileVersion}{beta}{dump}");
        }
        return sb.ToString().TrimEnd();
    }

    public static string FormatProfileStatus(string dataDir, string? managedDir = null)
    {
        var live = TryGetManagedFileVersion(managedDir);
        var (beta, _) = TryReadSteamBranch();
        var ov = ReadOverride(dataDir);
        var active = ReadActiveGameFileVersion(Path.Combine(dataDir, ActiveDumpFileName));
        var liveLabel = string.IsNullOrEmpty(live)
            ? "unknown"
            : live + (string.IsNullOrEmpty(beta) ? "" : $" ({beta})");

        if (ov?.ForceFileVersion is { Length: > 0 } forced)
        {
            var pinBeta = TryReadProfileMeta(ProfileDirectory(dataDir, forced))?.SteamBetaKey;
            var pinLabel = forced + (string.IsNullOrEmpty(pinBeta) ? "" : $" ({pinBeta})");
            return $"Pinned {pinLabel}. Live Steam is {liveLabel}. Active dump: {active ?? "unstamped"}.";
        }

        return $"Following Steam: {liveLabel}. Active dump: {active ?? "unstamped"}.";
    }

    /// <summary>
    /// Pin active dump+rules to a named profile, or <c>live</c> to follow Managed FileVersion again.
    /// </summary>
    public static ResolveResult SwitchActiveProfile(
        string dataDir,
        string aliasOrVersion,
        string? managedDir = null,
        Action<string>? log = null)
    {
        if (IsFollowLiveAlias(aliasOrVersion))
        {
            ClearOverride(dataDir);
            log?.Invoke("Cleared API profile pin — following live Managed FileVersion.");
            return EnsureActiveProfile(dataDir, managedDir, log);
        }

        var resolved = ResolveProfileAlias(dataDir, aliasOrVersion);
        if (resolved is null)
        {
            throw new ArgumentException(
                $"Unknown API profile '{aliasOrVersion}'.\n{DescribeAvailableProfiles(dataDir)}");
        }

        var profileDump = Path.Combine(ProfileDirectory(dataDir, resolved), ActiveDumpFileName);
        if (!File.Exists(profileDump))
        {
            throw new FileNotFoundException(
                $"Profile {resolved} has no {ActiveDumpFileName}. Run sync-version --save-profile on that game version first.",
                profileDump);
        }

        WriteOverride(dataDir, resolved, reason: $"switch-api {aliasOrVersion.Trim()}");
        log?.Invoke($"Pinned API profile to {resolved} (migrate/GUI/PS1 will not follow Steam until switch-api live).");
        return EnsureActiveProfile(dataDir, managedDir, log);
    }

    /// <summary>
    /// Snapshot active dump+rules into <c>by-version/{version}/</c>, then switch active files
    /// to the pinned profile or live Managed FileVersion when that profile exists.
    /// </summary>
    public static ResolveResult EnsureActiveProfile(
        string dataDir,
        string? managedDir = null,
        Action<string>? log = null)
    {
        managedDir ??= DefaultManagedDir;
        var activeDump = Path.Combine(dataDir, ActiveDumpFileName);
        var activeRules = Path.Combine(dataDir, ActiveRulesFileName);
        var liveVer = TryGetManagedFileVersion(managedDir);
        var (liveBeta, liveBuildId) = TryReadSteamBranch();
        var ov = ReadOverride(dataDir);

        var result = new ResolveResult
        {
            DataDir = dataDir,
            ActiveDumpPath = activeDump,
            ActiveRulesPath = activeRules,
            LiveFileVersion = liveVer,
            SteamBetaKey = liveBeta,
            SteamBuildId = liveBuildId,
            GameFileVersion = liveVer,
        };

        string? targetVer;
        string? stampBeta;
        string? stampBuild;

        if (ov?.ForceFileVersion is { Length: > 0 } forced)
        {
            result.Forced = true;
            result.ForcedFileVersion = forced;
            targetVer = forced;
            var meta = TryReadProfileMeta(ProfileDirectory(dataDir, forced));
            stampBeta = meta?.SteamBetaKey;
            stampBuild = meta?.SteamBuildId;
            result.SteamBetaKey = stampBeta ?? liveBeta;
            result.SteamBuildId = stampBuild ?? liveBuildId;
            result.GameFileVersion = targetVer;
        }
        else
        {
            targetVer = liveVer;
            stampBeta = liveBeta;
            stampBuild = liveBuildId;
        }

        if (string.IsNullOrEmpty(targetVer))
        {
            result.Message =
                $"Could not read FileVersion from {Path.Combine(managedDir, "Assembly-CSharp.dll")}; leaving active dump/rules unchanged.";
            log?.Invoke(result.Message);
            return result;
        }

        Directory.CreateDirectory(VersionsDirectory(dataDir));
        var profileDir = ProfileDirectory(dataDir, targetVer);
        result.ProfileDir = profileDir;

        var activeVer = ReadActiveGameFileVersion(activeDump);
        var versionsDiffer = !string.Equals(activeVer, targetVer, StringComparison.OrdinalIgnoreCase);

        if (File.Exists(activeDump) && versionsDiffer)
        {
            var snapVer = string.IsNullOrEmpty(activeVer)
                ? $"unknown-{DateTime.Now:yyyyMMdd_HHmmss}"
                : activeVer;
            var snapDir = ProfileDirectory(dataDir, snapVer);
            try
            {
                string? snapBeta = null;
                string? snapBuild = null;
                try
                {
                    var m = DumpStore.LoadDump(activeDump).Meta;
                    snapBeta = m?.SteamBetaKey;
                    snapBuild = m?.SteamBuildId;
                }
                catch { /* keep nulls — do not stamp live Steam onto another version */ }

                SaveProfileFromActive(dataDir, snapDir, snapVer, beta: snapBeta, buildId: snapBuild,
                    notes: null);
                result.SnapshottedPrevious = true;
                log?.Invoke($"Snapshotted previous active dump+rules → {snapDir}");
            }
            catch (Exception ex)
            {
                log?.Invoke($"Warning: could not snapshot previous profile: {ex.Message}");
            }
        }

        var profileDump = Path.Combine(profileDir, ActiveDumpFileName);
        var profileRules = Path.Combine(profileDir, ActiveRulesFileName);
        var profileReady = File.Exists(profileDump);
        var pinNote = result.Forced
            ? $"pinned {targetVer}" + (string.IsNullOrEmpty(stampBeta) ? "" : $" ({stampBeta})")
              + $"; live Steam is {liveVer ?? "unknown"}" + (string.IsNullOrEmpty(liveBeta) ? "" : $" ({liveBeta})")
            : $"FileVersion {targetVer} (Steam: {liveBeta ?? "unknown"})";

        if (profileReady && (versionsDiffer || !File.Exists(activeDump)))
        {
            Directory.CreateDirectory(dataDir);
            File.Copy(profileDump, activeDump, overwrite: true);
            if (File.Exists(profileRules))
                File.Copy(profileRules, activeRules, overwrite: true);

            var profileCharts = Path.Combine(profileDir, ChartsFolderName);
            var activeCharts = Path.Combine(dataDir, ChartsFolderName);
            if (Directory.Exists(profileCharts))
                RuleChartCompiler.CopyChartsDirectory(profileCharts, activeCharts);

            StampActiveMeta(dataDir, targetVer, stampBeta, stampBuild);
            result.SwitchedActive = true;
            result.Message = $"Active dump+rules switched to {pinNote} from {profileDir}";
            log?.Invoke(result.Message);
            WriteIndex(dataDir);
            return result;
        }

        result.Message = profileReady
            ? $"Active dump+rules already match {pinNote}."
            : $"No by-version profile for {targetVer} yet — using active files. Run refresh-dump --save (or sync-version --save-profile) to create {profileDir}.";
        log?.Invoke(result.Message);
        return result;
    }

    /// <summary>Copy active dump+rules into a version profile folder and write meta.json.</summary>
    public static string SaveProfileFromActive(
        string dataDir,
        string? profileDir = null,
        string? fileVersion = null,
        string? beta = null,
        string? buildId = null,
        string? notes = null,
        string? managedDir = null)
    {
        managedDir ??= DefaultManagedDir;
        fileVersion ??= TryGetManagedFileVersion(managedDir) ?? "unknown";
        var liveVer = TryGetManagedFileVersion(managedDir);
        var (steamBeta, steamBuild) = TryReadSteamBranch();
        // Only fill Steam branch from the live install when this profile is that install.
        // Snapshots of another FileVersion must keep their own steamBetaKey (public vs lang).
        if (string.Equals(fileVersion, liveVer, StringComparison.OrdinalIgnoreCase))
        {
            beta ??= steamBeta;
            buildId ??= steamBuild;
        }
        profileDir ??= ProfileDirectory(dataDir, fileVersion);

        Directory.CreateDirectory(profileDir);
        var activeDump = Path.Combine(dataDir, ActiveDumpFileName);
        var activeRules = Path.Combine(dataDir, ActiveRulesFileName);
        if (!File.Exists(activeDump))
            throw new FileNotFoundException("Active obsolete dump not found.", activeDump);

        File.Copy(activeDump, Path.Combine(profileDir, ActiveDumpFileName), overwrite: true);
        if (File.Exists(activeRules))
            File.Copy(activeRules, Path.Combine(profileDir, ActiveRulesFileName), overwrite: true);

        var activeCharts = Path.Combine(dataDir, ChartsFolderName);
        var profileCharts = Path.Combine(profileDir, ChartsFolderName);
        if (Directory.Exists(activeCharts))
            RuleChartCompiler.CopyChartsDirectory(activeCharts, profileCharts);

        StampDumpFileMeta(Path.Combine(profileDir, ActiveDumpFileName), fileVersion, beta, buildId, notes);
        if (File.Exists(Path.Combine(profileDir, ActiveRulesFileName)))
            StampRulesFileMeta(Path.Combine(profileDir, ActiveRulesFileName), fileVersion, beta, buildId, notes);

        var meta = new
        {
            gameFileVersion = fileVersion,
            steamBetaKey = beta,
            steamBuildId = buildId,
            notes,
            updated = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
            files = new[] { ActiveDumpFileName, ActiveRulesFileName, ChartsFolderName + "/" },
        };
        File.WriteAllText(
            Path.Combine(profileDir, ProfileMetaFileName),
            JsonSerializer.Serialize(meta, new JsonSerializerOptions { WriteIndented = true }));

        WriteIndex(dataDir);
        return profileDir;
    }

    /// <summary>After refresh-dump --save: stamp active dump meta and refresh the live version profile (dump + rules).</summary>
    public static string AfterDumpSaved(string dataDir, ObsoleteDump merged, string? managedDir = null)
    {
        managedDir ??= DefaultManagedDir;
        var fileVer = TryGetManagedFileVersion(managedDir) ?? "unknown";
        var (beta, buildId) = TryReadSteamBranch();
        merged.Meta ??= new ObsoleteDumpMeta();
        merged.Meta.GameFileVersion = fileVer;
        merged.Meta.SteamBetaKey = beta;
        merged.Meta.SteamBuildId = buildId;
        merged.Meta.CapturedDate = DateTime.Now.ToString("yyyy-MM-dd");

        var activeDump = Path.Combine(dataDir, ActiveDumpFileName);
        DumpStore.SaveDump(activeDump, merged);
        return SaveProfileFromActive(dataDir, fileVersion: fileVer, beta: beta, buildId: buildId,
            notes: "Updated by refresh-dump --save.", managedDir: managedDir);
    }

    static void StampActiveMeta(string dataDir, string fileVer, string? beta, string? buildId)
    {
        StampDumpFileMeta(Path.Combine(dataDir, ActiveDumpFileName), fileVer, beta, buildId, notes: null);
        var activeRules = Path.Combine(dataDir, ActiveRulesFileName);
        if (File.Exists(activeRules))
            StampRulesFileMeta(activeRules, fileVer, beta, buildId, notes: null);
    }

    static void StampDumpFileMeta(string path, string fileVer, string? beta, string? buildId, string? notes)
    {
        if (!File.Exists(path)) return;
        try
        {
            var dump = DumpStore.LoadDump(path);
            dump.Meta ??= new ObsoleteDumpMeta();
            dump.Meta.GameFileVersion = fileVer;
            if (beta is not null) dump.Meta.SteamBetaKey = beta;
            if (buildId is not null) dump.Meta.SteamBuildId = buildId;
            if (!string.IsNullOrEmpty(notes)) dump.Meta.Notes = notes;
            dump.Meta.CapturedDate = DateTime.Now.ToString("yyyy-MM-dd");
            DumpStore.SaveDump(path, dump);
        }
        catch { /* keep bytes */ }
    }

    /// <summary>
    /// Patch only <c>_meta</c> version fields via JsonNode so hand-maintained underscore
    /// note blocks (<c>_gameTextCallSites</c>, etc.) are never stripped.
    /// </summary>
    public static void StampRulesFileMeta(string path, string fileVer, string? beta, string? buildId, string? notes)
    {
        if (!File.Exists(path)) return;
        try
        {
            var node = JsonNode.Parse(File.ReadAllText(path)) as JsonObject;
            if (node is null) return;
            var meta = node["_meta"] as JsonObject ?? new JsonObject();
            meta["gameFileVersion"] = fileVer;
            if (beta is not null) meta["steamBetaKey"] = beta;
            if (buildId is not null) meta["steamBuildId"] = buildId;
            meta["capturedDate"] = DateTime.Now.ToString("yyyy-MM-dd");
            if (!string.IsNullOrEmpty(notes)) meta["notes"] = notes;
            node["_meta"] = meta;
            File.WriteAllText(path, node.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { /* keep bytes */ }
    }

    public static string WriteIndex(string dataDir)
    {
        var dir = VersionsDirectory(dataDir);
        Directory.CreateDirectory(dir);
        var versions = Directory.Exists(dir)
            ? Directory.GetDirectories(dir)
                .Select(Path.GetFileName)
                .Where(n => !string.IsNullOrEmpty(n))
                .OrderBy(x => x)
                .ToList()
            : new List<string?>();
        var (beta, buildId) = TryReadSteamBranch();
        var live = TryGetManagedFileVersion();
        var ov = ReadOverride(dataDir);
        var index = new
        {
            description =
                "ApiMigrator per-game-version profiles. Each folder holds obsolete_api_dump.json + curated_rewrite_rules.json. Active copies live in data/ and are synced by DumpVersionControl.EnsureActiveProfile. switch-api writes by-version/active-override.json to pin a profile (omit that file when sharing).",
            liveGameFileVersion = live,
            liveSteamBetaKey = beta,
            liveSteamBuildId = buildId,
            forcedFileVersion = ov?.ForceFileVersion,
            versions,
            updated = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
        };
        var indexPath = Path.Combine(dir, "index.json");
        File.WriteAllText(indexPath, JsonSerializer.Serialize(index, new JsonSerializerOptions { WriteIndented = true }));
        return indexPath;
    }
}
