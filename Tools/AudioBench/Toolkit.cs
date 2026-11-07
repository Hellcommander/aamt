using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace AAMT.AudioBench
{
    /// <summary>Where the toolkit repo and its Python are, remembered in %APPDATA%\AAMT\AudioBench.ini.</summary>
    internal sealed class ToolkitLocation
    {
        public string ToolsDir;     // ...\Ai assisted toolkit\Tools
        public string Python;       // full path of python.exe

        public string SharedDir => Path.Combine(ToolsDir, "Shared");
        public string ServerScript => Path.Combine(SharedDir, "audio_bench_server.py");
        public bool Valid => File.Exists(ServerScript) && File.Exists(Python);

        private static string IniPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "AAMT", "AudioBench.ini");

        /// <summary>The Tools folder: this exe's own folder or a parent of it, the saved one, else null.</summary>
        public static string FindToolsDir()
        {
            var dir = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
            for (int i = 0; i < 6 && dir != null; i++, dir = dir.Parent)
            {
                if (File.Exists(Path.Combine(dir.FullName, "Shared", "audio_bench_server.py"))) return dir.FullName;
                if (File.Exists(Path.Combine(dir.FullName, "Tools", "Shared", "audio_bench_server.py"))) return Path.Combine(dir.FullName, "Tools");
            }
            var saved = Load();
            return saved != null && Directory.Exists(saved.ToolsDir) ? saved.ToolsDir : null;
        }

        /// <summary>Python the way the toolkit's .bat launchers find it: TranscendenceTools.ini, the usual miniconda, PATH.</summary>
        public static string FindPython(string toolsDir)
        {
            try
            {
                var ini = Path.Combine(toolsDir, "TranscendenceTools.ini");
                if (File.Exists(ini))
                    foreach (var line in File.ReadAllLines(ini))
                        if (line.TrimStart().StartsWith("PythonPath", StringComparison.OrdinalIgnoreCase) && line.Contains("="))
                        {
                            var p = line.Substring(line.IndexOf('=') + 1).Trim().Trim('"');
                            if (File.Exists(p)) return p;
                        }
            }
            catch { }
            var saved = Load();
            if (saved != null && File.Exists(saved.Python)) return saved.Python;
            foreach (var cand in new[] { @"E:\tools\miniconda3\python.exe", @"D:\Python\Python314\python.exe" })
                if (File.Exists(cand)) return cand;
            foreach (var dir in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
            {
                try
                {
                    var p = Path.Combine(dir.Trim(), "python.exe");
                    if (File.Exists(p) && !p.Contains("WindowsApps")) return p;
                }
                catch { }
            }
            return null;
        }

        public static ToolkitLocation Load()
        {
            try
            {
                if (!File.Exists(IniPath)) return null;
                var loc = new ToolkitLocation();
                foreach (var line in File.ReadAllLines(IniPath))
                {
                    var i = line.IndexOf('=');
                    if (i < 0) continue;
                    var k = line.Substring(0, i).Trim(); var v = line.Substring(i + 1).Trim();
                    if (k == "ToolsDir") loc.ToolsDir = v; else if (k == "Python") loc.Python = v;
                }
                return loc;
            }
            catch { return null; }
        }

        public void Save()
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(IniPath));
                File.WriteAllText(IniPath, "ToolsDir=" + ToolsDir + Environment.NewLine + "Python=" + Python + Environment.NewLine);
            }
            catch { }
        }
    }

    /// <summary>A Windows job object with kill-on-close: every process assigned to it dies when this program does, however it ends.</summary>
    internal static class ChildJob
    {
        [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
        private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint length);
        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_LIMIT_INFORMATION { public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags; public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit; public UIntPtr Affinity; public uint PriorityClass, SchedulingClass; }
        [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        private struct IO_COUNTERS { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
        [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION { public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation; public IO_COUNTERS IoInfo; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }

        private static IntPtr _job = IntPtr.Zero;

        public static void Add(Process p)
        {
            try
            {
                if (_job == IntPtr.Zero)
                {
                    _job = CreateJobObject(IntPtr.Zero, null);
                    var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
                    info.BasicLimitInformation.LimitFlags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    int size = System.Runtime.InteropServices.Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
                    IntPtr mem = System.Runtime.InteropServices.Marshal.AllocHGlobal(size);
                    System.Runtime.InteropServices.Marshal.StructureToPtr(info, mem, false);
                    SetInformationJobObject(_job, 9 /* JobObjectExtendedLimitInformation */, mem, (uint)size);
                    System.Runtime.InteropServices.Marshal.FreeHGlobal(mem);
                }
                AssignProcessToJobObject(_job, p.Handle);
            }
            catch { /* without a job the server still dies on a normal close */ }
        }
    }

    /// <summary>The bench server as a child process: started from the repo, watched for its ready line, stopped with the window.</summary>
    internal sealed class BenchServer : IDisposable
    {
        public int Port { get; private set; }
        public string Url => "http://127.0.0.1:" + Port + "/";
        public event Action<string> Line;
        public event Action Exited;
        private Process _proc;

        public static int FreePort()
        {
            var l = new TcpListener(IPAddress.Loopback, 0);
            l.Start();
            int port = ((IPEndPoint)l.LocalEndpoint).Port;
            l.Stop();
            return port;
        }

        public async Task<bool> StartAsync(ToolkitLocation loc, int timeoutMs = 30000)
        {
            Port = FreePort();
            var psi = new ProcessStartInfo
            {
                FileName = loc.Python,
                Arguments = "\"" + loc.ServerScript + "\" --port " + Port,
                WorkingDirectory = loc.SharedDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
            };
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
            var ready = new TaskCompletionSource<bool>();
            _proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
            DataReceivedEventHandler onLine = (s, e) =>
            {
                if (e.Data == null) return;
                Line?.Invoke(e.Data);
                if (e.Data.StartsWith("Audio Bench at")) ready.TrySetResult(true);
            };
            _proc.OutputDataReceived += onLine;
            _proc.ErrorDataReceived += onLine;
            _proc.Exited += (s, e) => { ready.TrySetResult(false); Exited?.Invoke(); };
            _proc.Start();
            ChildJob.Add(_proc);
            _proc.BeginOutputReadLine();
            _proc.BeginErrorReadLine();
            var done = await Task.WhenAny(ready.Task, Task.Delay(timeoutMs));
            return done == ready.Task && ready.Task.Result;
        }

        public bool Running => _proc != null && !_proc.HasExited;

        public void Dispose()
        {
            try { if (_proc != null && !_proc.HasExited) _proc.Kill(); } catch { }
            _proc?.Dispose();
            _proc = null;
        }
    }

    /// <summary>Small JSON calls to the server, for the menu items that act outside the page.</summary>
    internal static class BenchApi
    {
        public static async Task<string> PostAsync(string url, string json)
        {
            using (var client = new System.Net.Http.HttpClient { Timeout = TimeSpan.FromMinutes(10) })
            {
                var resp = await client.PostAsync(url, new System.Net.Http.StringContent(json, Encoding.UTF8, "application/json"));
                return await resp.Content.ReadAsStringAsync();
            }
        }

        public static string JsonString(string s) => "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }
}
