using System.Diagnostics;
using System.Text;

namespace XEdit.Clr;

public sealed class XEditRunOptions
{
    public required XEditInstall Install { get; init; }
    public required XEditJob Job { get; init; }
    public string? DataPath { get; init; }
    public TimeSpan Timeout { get; init; } = TimeSpan.FromMinutes(15);
    public bool NoBuildRefs { get; init; } = true;
}

public sealed class XEditProcessResult
{
    public int ExitCode { get; init; }
    public string StdOut { get; init; } = "";
    public string StdErr { get; init; } = "";
    public string ResultJson { get; init; } = "";
    public string SessionDir { get; init; } = "";
}

/// <summary>
/// Launches xEdit/SF1Edit headless with AiAssistHost.pas.
/// Uses TES5Edit CLI: -SF1 -autoload -autoexit -IKnowWhatImDoing -nobuildrefs -script:
/// </summary>
public static class XEditProcess
{
    public static XEditProcessResult Run(XEditRunOptions options, CancellationToken ct = default)
    {
        var install = options.Install;
        var session = Path.Combine(XEditPaths.WorkDir, DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(session);

        var hostSrc = XEditPaths.HostScript;
        if (!File.Exists(hostSrc))
            throw new FileNotFoundException("AiAssistHost.pas missing", hostSrc);

        File.Copy(hostSrc, Path.Combine(session, "AiAssistHost.pas"), overwrite: true);
        File.WriteAllText(Path.Combine(session, "job.json"), options.Job.ToJson(), Encoding.UTF8);

        var args = new List<string>
        {
            XEditGameModes.Switch(options.Job.GameMode),
            "-IKnowWhatImDoing",
            "-autoload",
            "-autoexit",
            $"-S:{session}",
            "-script:AiAssistHost.pas"
        };

        if (options.NoBuildRefs)
            args.Add("-nobuildrefs");

        if (options.Job.EditMasters)
            args.Add("-AllowMasterFilesEdit");

        var data = options.DataPath ?? install.GameDataPath;
        if (!string.IsNullOrWhiteSpace(data))
        {
            var gameRoot = Directory.Exists(data) && Path.GetFileName(data).Equals("Data", StringComparison.OrdinalIgnoreCase)
                ? Path.GetDirectoryName(data)!
                : data;
            args.Add($"-D:{gameRoot}");
        }

        foreach (var plugin in PluginsToLoad(options.Job))
            args.Add(plugin);

        var psi = new ProcessStartInfo
        {
            FileName = install.ExePath,
            WorkingDirectory = install.Directory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = false
        };
        foreach (var a in args)
            psi.ArgumentList.Add(a);

        using var proc = new Process { StartInfo = psi };
        var stdout = new StringBuilder();
        var stderr = new StringBuilder();
        proc.OutputDataReceived += (_, e) => { if (e.Data is not null) stdout.AppendLine(e.Data); };
        proc.ErrorDataReceived += (_, e) => { if (e.Data is not null) stderr.AppendLine(e.Data); };

        if (!proc.Start())
            throw new InvalidOperationException("Failed to start " + install.ExePath);

        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();

        using var reg = ct.Register(() => { try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ } });
        if (!proc.WaitForExit((int)options.Timeout.TotalMilliseconds))
        {
            try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
            throw new TimeoutException($"xEdit timed out after {options.Timeout}.");
        }

        var resultPath = Path.Combine(session, "result.json");
        var resultJson = File.Exists(resultPath) ? File.ReadAllText(resultPath) : "";

        return new XEditProcessResult
        {
            ExitCode = proc.ExitCode,
            StdOut = stdout.ToString(),
            StdErr = stderr.ToString(),
            ResultJson = resultJson,
            SessionDir = session
        };
    }

    static IEnumerable<string> PluginsToLoad(XEditJob job)
    {
        var list = new List<string>();
        if (job.Plugins is { Count: > 0 })
            list.AddRange(job.Plugins);
        if (!string.IsNullOrWhiteSpace(job.Plugin) && !list.Contains(job.Plugin, StringComparer.OrdinalIgnoreCase))
            list.Add(job.Plugin);
        if (!string.IsNullOrWhiteSpace(job.TargetPlugin) && !list.Contains(job.TargetPlugin, StringComparer.OrdinalIgnoreCase))
            list.Add(job.TargetPlugin);
        return list;
    }
}
