namespace XEdit.Clr;

/// <summary>Resolves the AAMT XEdit tool root (this folder under Tools/XEdit).</summary>
public static class XEditPaths
{
    public static string Root
    {
        get
        {
            var env = Environment.GetEnvironmentVariable("AAMT_XEDIT_ROOT");
            if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
                return Path.GetFullPath(env);

            foreach (var start in new[]
                     {
                         AppContext.BaseDirectory,
                         Directory.GetCurrentDirectory()
                     })
            {
                var dir = new DirectoryInfo(start);
                for (var i = 0; i < 8 && dir is not null; i++, dir = dir.Parent)
                {
                    if (File.Exists(Path.Combine(dir.FullName, "vendor", "fork.json")) ||
                        Directory.Exists(Path.Combine(dir.FullName, "vendor", "TES5Edit", "Core")))
                        return dir.FullName;
                }
            }

            return Path.GetFullPath(@"d:\games\Ai assisted toolkit\Tools\XEdit");
        }
    }

    public static string VendorDir => Path.Combine(Root, "vendor");
    public static string Tes5EditDir => Path.Combine(VendorDir, "TES5Edit");
    public static string ForkManifest => Path.Combine(VendorDir, "fork.json");
    public static string BinDir => Path.Combine(Root, "bin");
    public static string ScriptsDir => Path.Combine(Root, "Scripts");
    public static string WorkDir => Path.Combine(Root, "work");
    public static string HostScript => Path.Combine(ScriptsDir, "AiAssistHost.pas");
    public static string Sf1Definitions => Path.Combine(Tes5EditDir, "Core", "wbDefinitionsSF1.pas");
}
