using System.Diagnostics;
using System.Text.Json;

namespace XEdit.Clr;

/// <summary>
/// AI-facing API. Fast local reads use TES4 walking + wbDefinitionsSF1.pas.
/// Writes and decoded dumps launch the newest SF1Edit/xEdit host.
/// </summary>
public sealed class XEditClient
{
    public XEditFork Fork { get; } = XEditFork.Load();

    public XEditResult Locate(XEditGame game = XEditGame.SF1)
    {
        var all = XEditLocator.LocateAll(game);
        var best = XEditLocator.Locate(game);
        return new XEditResult
        {
            Ok = best is not null,
            Error = best is null ? "No xEdit/SF1Edit executable found. Put a 4.1.5q+ build in Tools/XEdit/bin or set XEDIT." : null,
            Warning = best?.Warning,
            Op = "locate",
            Fork = Fork,
            XEdit = best,
            Data = JsonSerializer.SerializeToElement(all, JsonOptions.Indented)
        };
    }

    public XEditResult ForkInfo() => new()
    {
        Ok = Fork.SourcePresent,
        Error = Fork.SourcePresent ? null : "TES5Edit source missing. Run: xedit-assist sync",
        Op = "fork",
        Fork = Fork
    };

    public XEditResult Defs(string? signature = null)
    {
        var cat = Sf1Definitions.Load();
        object data = string.IsNullOrWhiteSpace(signature)
            ? cat
            : cat.Records.Where(r =>
                  r.Signature.Equals(signature, StringComparison.OrdinalIgnoreCase) ||
                  r.Name.Contains(signature, StringComparison.OrdinalIgnoreCase))
              .ToList();
        return new XEditResult { Ok = true, Op = "defs", Fork = Fork, Data = JsonSerializer.SerializeToElement(data, JsonOptions.Indented) };
    }

    public XEditResult Header(string pluginPath)
    {
        var info = PluginHeader.Read(ResolvePlugin(pluginPath));
        return new XEditResult { Ok = true, Op = "header", Fork = Fork, Data = JsonSerializer.SerializeToElement(info, JsonOptions.Indented) };
    }

    public XEditResult Groups(string pluginPath)
    {
        var idx = PluginWalker.Index(ResolvePlugin(pluginPath), limit: 1);
        return new XEditResult { Ok = true, Op = "groups", Data = JsonSerializer.SerializeToElement(idx.TopGroups, JsonOptions.Indented) };
    }

    public XEditResult Records(string pluginPath, string? signature = null, string? query = null, int limit = 200)
    {
        var idx = PluginWalker.Index(ResolvePlugin(pluginPath), signature, limit: 0);
        IEnumerable<IndexedRecord> rows = idx.Records;
        if (!string.IsNullOrWhiteSpace(query))
        {
            rows = rows.Where(r =>
                r.EditorId.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                r.FormIdHex.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                r.Signature.Contains(query, StringComparison.OrdinalIgnoreCase));
        }
        if (limit > 0)
            rows = rows.Take(limit);

        var payload = new
        {
            idx.Path,
            idx.Header,
            groups = idx.TopGroups,
            count = idx.Records.Count,
            records = rows.ToList()
        };
        return new XEditResult { Ok = true, Op = "records", Data = JsonSerializer.SerializeToElement(payload, JsonOptions.Indented) };
    }

    public XEditResult RunJob(XEditJob job, CancellationToken ct = default)
    {
        var op = (job.Op ?? "").Trim().ToLowerInvariant();
        try
        {
            return op switch
            {
                "locate" or "info" when string.IsNullOrEmpty(job.Plugin) => Locate(job.GameMode),
                "fork" => ForkInfo(),
                "defs" => Defs(job.Signature ?? job.Query),
                "header" => Header(NeedPlugin(job)),
                "groups" => Groups(NeedPlugin(job)),
                "records" or "search" => Records(NeedPlugin(job), job.Signature, job.Query, job.Limit),
                "sync" => SyncFork(),
                _ => RunXEdit(job, ct)
            };
        }
        catch (Exception ex)
        {
            return XEditResult.Fail(ex.Message);
        }
    }

    public XEditResult SyncFork()
    {
        var repo = XEditPaths.Tes5EditDir;
        if (!Directory.Exists(Path.Combine(repo, ".git")))
            return XEditResult.Fail("No git clone at " + repo);

        var psi = new ProcessStartInfo
        {
            FileName = "git",
            WorkingDirectory = repo,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        psi.ArgumentList.Add("pull");
        psi.ArgumentList.Add("--ff-only");
        psi.ArgumentList.Add("origin");
        psi.ArgumentList.Add(Fork.Branch);

        using var p = Process.Start(psi)!;
        var stdout = p.StandardOutput.ReadToEnd();
        var stderr = p.StandardError.ReadToEnd();
        p.WaitForExit();
        return new XEditResult
        {
            Ok = p.ExitCode == 0,
            Error = p.ExitCode == 0 ? null : stderr,
            Op = "sync",
            Fork = XEditFork.Load(),
            Log = stdout + stderr
        };
    }

    XEditResult RunXEdit(XEditJob job, CancellationToken ct)
    {
        var install = XEditLocator.Locate(job.GameMode);
        if (install is null)
            return XEditResult.Fail("xEdit executable not found. Place a TES5Edit 4.1.5q+ / SF1Edit build in Tools\\XEdit\\bin or set XEDIT.");

        var run = XEditProcess.Run(new XEditRunOptions { Install = install, Job = job }, ct);
        XEditResult parsed;
        if (!string.IsNullOrWhiteSpace(run.ResultJson))
        {
            using var doc = JsonDocument.Parse(run.ResultJson);
            var root = doc.RootElement.Clone();
            var ok = !root.TryGetProperty("ok", out var okEl) || okEl.ValueKind != JsonValueKind.False;
            string? err = null;
            if (root.TryGetProperty("error", out var errEl) && errEl.ValueKind == JsonValueKind.String)
                err = errEl.GetString();
            parsed = new XEditResult
            {
                Ok = ok && string.IsNullOrEmpty(err),
                Error = string.IsNullOrEmpty(err) ? null : err,
                Data = root
            };
        }
        else
        {
            parsed = new XEditResult
            {
                Ok = run.ExitCode == 0,
                Error = run.ExitCode == 0 ? "xEdit produced no result.json" : $"xEdit exit {run.ExitCode}"
            };
        }

        parsed.Warning ??= install.Warning;
        parsed.XEdit = install;
        parsed.Fork = Fork;
        parsed.Log = run.StdErr + run.StdOut;
        parsed.Op ??= job.Op;
        return parsed;
    }

    static string NeedPlugin(XEditJob job)
    {
        if (string.IsNullOrWhiteSpace(job.Plugin))
            throw new ArgumentException("plugin is required");
        return job.Plugin;
    }

    public static string ResolvePlugin(string plugin)
    {
        if (File.Exists(plugin))
            return Path.GetFullPath(plugin);

        var name = Path.GetFileName(plugin);
        var install = XEditLocator.Locate(XEditGame.SF1);
        var data = install?.GameDataPath;
        if (!string.IsNullOrEmpty(data))
        {
            var p = Path.Combine(data, name);
            if (File.Exists(p)) return p;
        }

        foreach (var root in new[]
                 {
                     @"F:\SteamLibrary\steamapps\common\Starfield\Data",
                     @"G:\SteamLibrary\steamapps\common\Starfield\Data"
                 })
        {
            var p = Path.Combine(root, name);
            if (File.Exists(p)) return p;
        }

        throw new FileNotFoundException("Plugin not found", plugin);
    }
}
