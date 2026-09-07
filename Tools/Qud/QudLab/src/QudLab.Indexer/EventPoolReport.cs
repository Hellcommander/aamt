using System.Text;
using System.Text.RegularExpressions;
using QudLab.Core.Cache;
using QudLab.Core.Install;

namespace QudLab.Indexer;

public static class EventPoolReport
{
    static readonly Regex PoolLine = new(
        @"^([A-Za-z0-9_.]+):\s*(\d+)\s*$",
        RegexOptions.Compiled);

    public static string AuditLogPath() =>
        Path.Combine(CacheIO.DefaultCacheDir(), "event-pools-audit.json");

    public static EventPoolAudit? LoadCached()
    {
        try
        {
            var path = AuditLogPath();
            if (!File.Exists(path))
                return null;
            return System.Text.Json.JsonSerializer.Deserialize<EventPoolAudit>(
                File.ReadAllText(path), CacheIO.JsonOptions);
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Parse Player.log lines from MinEvent.GetTopPoolCountReport or pool registration errors.</summary>
    public static string TailRuntimePools(int maxLines = 40)
    {
        var player = QudModPaths.PlayerLogPath();
        var sb = new StringBuilder();
        if (!File.Exists(player))
        {
            sb.AppendLine("Player.log missing at " + player);
            return sb.ToString();
        }

        sb.AppendLine("=== Player.log runtime pool lines ===");
        var hits = 0;
        try
        {
            foreach (var line in TailFileLines(player, Math.Max(maxLines * 8, 400)).Reverse())
            {
                if (!IsPoolLine(line))
                    continue;
                sb.AppendLine(line);
                hits++;
                if (hits >= maxLines)
                    break;
            }
        }
        catch (Exception ex)
        {
            sb.AppendLine("(could not read Player.log: " + ex.Message + ")");
            return sb.ToString();
        }

        if (hits == 0)
            sb.AppendLine("(no pool count / duplicate pool registration lines — play with action log, or check after lag repro)");

        return sb.ToString();
    }

    public static List<RuntimePoolCount> ParseRuntimeCounts(string logText)
    {
        var list = new List<RuntimePoolCount>();
        foreach (var line in logText.Split('\n'))
        {
            var m = PoolLine.Match(line.Trim());
            if (!m.Success)
                continue;
            if (int.TryParse(m.Groups[2].Value, out var count))
            {
                list.Add(new RuntimePoolCount
                {
                    TypeFullName = m.Groups[1].Value,
                    Count = count
                });
            }
        }
        return list;
    }

    static IEnumerable<string> TailFileLines(string path, int maxLines)
    {
        const int chunk = 64 * 1024;
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        var length = stream.Length;
        var buffer = new byte[Math.Min(chunk, length)];
        var text = "";
        var pos = length;
        while (pos > 0 && text.Count(c => c == '\n') < maxLines + 2)
        {
            var read = (int)Math.Min(buffer.Length, pos);
            pos -= read;
            stream.Seek(pos, SeekOrigin.Begin);
            if (stream.Read(buffer, 0, read) != read)
                break;
            text = Encoding.UTF8.GetString(buffer, 0, read) + text;
        }

        return text.Replace("\r\n", "\n").Split('\n', StringSplitOptions.RemoveEmptyEntries);
    }

    static bool IsPoolLine(string line)
    {
        if (string.IsNullOrWhiteSpace(line))
            return false;
        if (PoolLine.IsMatch(line.Trim()))
            return true;
        return line.Contains("pool retrieval registration", StringComparison.OrdinalIgnoreCase)
               || line.Contains("Duplicate event registration", StringComparison.OrdinalIgnoreCase)
               || line.Contains("GetTopPoolCountReport", StringComparison.OrdinalIgnoreCase)
               || line.Contains("EventPoolCount", StringComparison.OrdinalIgnoreCase);
    }

    public static object BuildResponse(EventPoolAudit? audit, string? q, string? mod, string? cacheKind, int top, bool includeRuntime)
    {
        audit ??= new EventPoolAudit();
        IEnumerable<EventPoolEntry> qy = audit.Entries;

        if (!string.IsNullOrWhiteSpace(q))
            qy = qy.Where(e =>
                e.TypeFullName.Contains(q, StringComparison.OrdinalIgnoreCase)
                || (e.ModFolder?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                || (e.Assembly?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));

        if (!string.IsNullOrWhiteSpace(mod))
            qy = qy.Where(e => e.IsMod && (
                (e.ModFolder?.Contains(mod, StringComparison.OrdinalIgnoreCase) ?? false)
                || e.TypeFullName.Contains(mod, StringComparison.OrdinalIgnoreCase)));

        if (!string.IsNullOrWhiteSpace(cacheKind))
            qy = qy.Where(e => e.CacheKind.Equals(cacheKind, StringComparison.OrdinalIgnoreCase));

        var entries = qy
            .Where(e => !e.IsAbstract)
            .Take(Math.Clamp(top, 1, 500))
            .ToList();

        var runtime = includeRuntime ? TailRuntimePools(60) : null;

        return new
        {
            builtAt = audit.BuiltAt,
            summary = new
            {
                audit.TotalEvents,
                audit.PooledCount,
                audit.SingletonCount,
                audit.ModEventCount,
                audit.ModPooledCount,
                idConflicts = audit.IdConflicts.Count,
                scanErrors = audit.ScanErrors.Count
            },
            idConflicts = audit.IdConflicts.Take(50),
            modPooled = audit.Entries
                .Where(e => e.IsMod && e.CacheKind == "Pool" && !e.IsAbstract)
                .OrderBy(e => e.TypeFullName, StringComparer.OrdinalIgnoreCase)
                .Take(100)
                .ToList(),
            entries,
            runtimePoolLog = runtime,
            logPath = AuditLogPath()
        };
    }
}

public sealed class RuntimePoolCount
{
    public required string TypeFullName { get; set; }
    public int Count { get; set; }
}
