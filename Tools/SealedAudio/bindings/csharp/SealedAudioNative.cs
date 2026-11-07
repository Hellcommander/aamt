// P/Invoke binding for SealedAudioCore.dll (include/sealed_audio.h). For a managed host (a BepInEx or MelonLoader
// plugin, a Unity mod, a launcher) that wants sealed sound archives to appear as loose files in its process.
//
//   var cfg = SealedAudioNative.Defaults();
//   cfg.data_dir = Path.Combine(gameDir, "Data");
//   cfg.log_file = Path.Combine(gameDir, "SealedAudio.log");
//   int hooked = SealedAudioNative.sa_init(ref cfg);
//   ... later: SealedAudioNative.sa_mark_loaded();
//
// The dll must be x64 and found by the loader (beside the host dll, or an absolute path via a resolver).
using System;
using System.Runtime.InteropServices;

namespace SealedAudio
{
    public static class SealedAudioNative
    {
        private const string Dll = "SealedAudioCore.dll";

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void LogFn(int level, [MarshalAs(UnmanagedType.LPStr)] string message, IntPtr user);

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct Config
        {
            public uint size;
            [MarshalAs(UnmanagedType.LPWStr)] public string data_dir;
            [MarshalAs(UnmanagedType.LPWStr)] public string data_folder_name;
            [MarshalAs(UnmanagedType.LPWStr)] public string archive_dir;
            [MarshalAs(UnmanagedType.LPWStr)] public string log_file;
            public LogFn log;
            public IntPtr log_user;
            public IntPtr key32;            // pin a 32-byte array and pass its address, or IntPtr.Zero for the compiled-in key
            public int hook_listings, hook_attributes, hook_serve, hook_mappings;
            public int patch_modules;
            [MarshalAs(UnmanagedType.LPWStr)] public string module_prefixes;
            public int log_probes, max_probe_lines, log_imports;
        }

        public static Config Defaults()
        {
            var c = new Config();
            c.size = (uint)Marshal.SizeOf<Config>();
            c.hook_listings = c.hook_attributes = c.hook_serve = c.hook_mappings = 1;
            c.patch_modules = 1;
            c.max_probe_lines = 200;
            return c;
        }

        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern int sa_init(ref Config config);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern int sa_patch_new_modules();
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern void sa_mark_loaded();
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern void sa_diagnostics(int crashLog, int exitHooks, int firstChance);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern int sa_self_test();
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)] public static extern int sa_has(string relativePath);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)] public static extern int sa_read(string relativePath, byte[] buffer, uint capacity, out uint size);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern void sa_mounted(out uint archives, out uint entries);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] public static extern void sa_counters([Out] ulong[] counters);
        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)] private static extern IntPtr sa_version();

        public static string Version() => Marshal.PtrToStringAnsi(sa_version());

        /// <summary>The unsealed bytes of a mounted entry, or null.</summary>
        public static byte[] Read(string relativePath)
        {
            if (sa_read(relativePath, null, 0, out uint size) == 0) return null;
            var buffer = new byte[size];
            return sa_read(relativePath, buffer, size, out size) == 1 ? buffer : null;
        }
    }
}
