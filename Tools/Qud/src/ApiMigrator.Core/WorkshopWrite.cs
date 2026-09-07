using System.Diagnostics;
using System.Text;

namespace ApiMigrator.Core;

/// <summary>
/// Steam Workshop trees often deny <see cref="File.WriteAllText(string,string)"/> from
/// <c>dotnet.exe</c> even when ACLs look writable (Controlled Folder Access, Steam overlay
/// lock, ReadOnly attribute). Try several <em>in-place</em> write strategies, then a
/// <c>powershell.exe</c> subprocess (same host that can write when dotnet cannot).
/// Never copy the final file via <c>%TEMP%</c> (cross-volume Replace/Move fails or leaves
/// Steam watching the wrong inode).
/// </summary>
public static class WorkshopWrite
{
    static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    public static void WriteAllText(string file, string contents)
    {
        var dir = Path.GetDirectoryName(file);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        ClearReadOnly(file);

        try
        {
            File.WriteAllText(file, contents, Utf8NoBom);
            return;
        }
        catch (UnauthorizedAccessException) { }
        catch (IOException) { }

        try
        {
            using var fs = new FileStream(file, FileMode.Create, FileAccess.Write, FileShare.Read);
            using var sw = new StreamWriter(fs, Utf8NoBom);
            sw.Write(contents);
            return;
        }
        catch (UnauthorizedAccessException) { }
        catch (IOException) { }

        // Sibling .tmp in the same directory only (same volume / ACL as the target).
        if (TryWriteViaSiblingTemp(file, contents))
            return;

        // Windows often blocks dotnet.exe from Steam library paths while powershell.exe succeeds.
        if (TryWriteViaPowerShell(file, contents))
            return;

        throw new UnauthorizedAccessException(
            "WorkshopWrite could not update " + file +
            " (direct write, same-folder temp replace, and PowerShell fallback all failed).");
    }

    static bool TryWriteViaSiblingTemp(string file, string contents)
    {
        var dir = Path.GetDirectoryName(file);
        if (string.IsNullOrEmpty(dir))
            return false;

        var tmp = Path.Combine(dir, "apimigrator-" + Guid.NewGuid().ToString("n") + ".tmp");
        try
        {
            File.WriteAllText(tmp, contents, Utf8NoBom);
            ClearReadOnly(file);
            try
            {
                if (!File.Exists(file))
                {
                    File.Move(tmp, file);
                    return true;
                }
                File.Replace(tmp, file, destinationBackupFileName: null);
                return true;
            }
            catch (Exception)
            {
                try { File.Copy(tmp, file, overwrite: true); return true; }
                catch (Exception)
                {
                    // Never delete the destination before a successful commit — a failed
                    // Move after Delete would destroy the Workshop file and then finally
                    // would also drop the sibling temp.
                    return false;
                }
            }
        }
        catch (UnauthorizedAccessException) { return false; }
        catch (IOException) { return false; }
        finally
        {
            try { if (File.Exists(tmp)) File.Delete(tmp); } catch { }
        }
    }

    public static void ClearReadOnly(string file)
    {
        try
        {
            if (!File.Exists(file)) return;
            var attrs = File.GetAttributes(file);
            if ((attrs & FileAttributes.ReadOnly) != 0)
                File.SetAttributes(file, attrs & ~FileAttributes.ReadOnly);
        }
        catch { /* best-effort */ }
    }

    static bool TryWriteViaPowerShell(string file, string contents)
    {
        var staging = Path.Combine(Path.GetTempPath(), "apimigrator-" + Guid.NewGuid().ToString("n") + ".tmp");
        try
        {
            File.WriteAllText(staging, contents, Utf8NoBom);

            var target = EscapePowerShellSingleQuoted(file);
            var stage = EscapePowerShellSingleQuoted(staging);
            // Entire -Command payload must be ONE argv token; unquoted spaces made powershell
            // only see "$ErrorActionPreference='Stop';$t='..." and fail (dotnet CFA often
            // blocks File.WriteAllText on Steam/Temp while powershell.exe is allowed).
            var cmd =
                "$ErrorActionPreference='Stop';" +
                "$t='" + target + "';$s='" + stage + "';" +
                "if (Test-Path -LiteralPath $t) { $a=(Get-Item -LiteralPath $t).Attributes; " +
                "if ($a -band [IO.FileAttributes]::ReadOnly) { (Get-Item -LiteralPath $t).Attributes = $a -bxor [IO.FileAttributes]::ReadOnly } }" +
                "[IO.File]::WriteAllText($t,[IO.File]::ReadAllText($s,[Text.UTF8Encoding]::new($false)),[Text.UTF8Encoding]::new($false))";

            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                ArgumentList = { "-NoProfile", "-NonInteractive", "-Command", cmd },
                UseShellExecute = false,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                CreateNoWindow = true,
            };
            using var proc = Process.Start(psi);
            if (proc == null)
                return false;

            // Drain pipes to avoid RedirectStandard* deadlocks on large stderr.
            var stdoutTask = proc.StandardOutput.ReadToEndAsync();
            var stderrTask = proc.StandardError.ReadToEndAsync();
            if (!proc.WaitForExit(120_000))
            {
                try { proc.Kill(entireProcessTree: true); } catch { }
                return false;
            }
            _ = stdoutTask.GetAwaiter().GetResult();
            _ = stderrTask.GetAwaiter().GetResult();
            return proc.ExitCode == 0;
        }
        catch (UnauthorizedAccessException) { return false; }
        catch (IOException) { return false; }
        finally
        {
            try { if (File.Exists(staging)) File.Delete(staging); } catch { }
        }
    }

    static string EscapePowerShellSingleQuoted(string value) =>
        value.Replace("'", "''");
}
