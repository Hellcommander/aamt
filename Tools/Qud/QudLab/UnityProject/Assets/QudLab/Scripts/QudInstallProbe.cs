using System;
using System.IO;

namespace QudLab.Unity
{
    /// <summary>
    /// Locates a verified Caves of Qud install (Steam/GOG). Never bundles game files.
    /// </summary>
    public static class QudInstallProbe
    {
        public static string[] DefaultCandidates => new[]
        {
            @"D:\games\Steam\steamapps\common\Caves of Qud",
            @"E:\SteamLibrary\steamapps\common\Caves of Qud",
            Environment.GetEnvironmentVariable("QUDLAB_QUD_PATH")
        };

        public static bool TryFind(out string rootPath, out string failReason)
        {
            foreach (var c in DefaultCandidates)
            {
                if (string.IsNullOrWhiteSpace(c))
                    continue;
                if (LooksLikeQud(c, out failReason))
                {
                    rootPath = Path.GetFullPath(c);
                    failReason = null;
                    return true;
                }
            }

            rootPath = null;
            failReason = "No CoQ install found (checked Steam paths + QUDLAB_QUD_PATH).";
            return false;
        }

        public static bool LooksLikeQud(string root, out string failReason)
        {
            failReason = null;
            if (string.IsNullOrWhiteSpace(root) || !Directory.Exists(root))
            {
                failReason = "root missing";
                return false;
            }

            var exe = Path.Combine(root, "CoQ.exe");
            var asm = Path.Combine(root, "CoQ_Data", "Managed", "Assembly-CSharp.dll");
            var bas = Path.Combine(root, "CoQ_Data", "StreamingAssets", "Base");
            if (!File.Exists(exe))
            {
                failReason = "CoQ.exe missing";
                return false;
            }

            if (!File.Exists(asm))
            {
                failReason = "Assembly-CSharp.dll missing";
                return false;
            }

            if (!Directory.Exists(bas))
            {
                failReason = "StreamingAssets/Base missing";
                return false;
            }

            return true;
        }

        public static string ManagedPath(string root) =>
            Path.Combine(root, "CoQ_Data", "Managed");

        public static string AssemblyCSharpPath(string root) =>
            Path.Combine(ManagedPath(root), "Assembly-CSharp.dll");
    }
}
