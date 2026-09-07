namespace QudLab.Core.Install;

/// <summary>
/// Ownership / install gate. No asset hashes — structural dependency only.
/// Steam/GOG plugin presence strengthens confidence but path validity is required.
/// </summary>
public sealed class OwnershipGate
{
    public GateResult Evaluate(string? overridePath = null)
    {
        var install = GamePathResolver.TryResolve(overridePath);
        if (install is null)
        {
            return GateResult.Fail(
                "Caves of Qud install not found. Own the game on Steam or GOG, install it, " +
                "or set QUDLAB_QUD_PATH to the game root (folder containing CoQ.exe).");
        }

        if (!File.Exists(install.AssemblyCSharpPath))
            return GateResult.Fail("Assembly-CSharp.dll missing under CoQ_Data/Managed.");

        if (!Directory.Exists(install.BaseDataPath))
            return GateResult.Fail("StreamingAssets/Base missing — cannot bind game data.");

        var steamApi = Path.Combine(install.PluginsPath, "x86_64", "steam_api64.dll");
        var galaxy = Path.Combine(install.PluginsPath, "x86_64", "Galaxy64.dll");
        var hasSteam = File.Exists(steamApi);
        var hasGog = File.Exists(galaxy);

        if (install.Store == GameStore.Steam && !hasSteam)
        {
            return GateResult.Fail(
                "Steam install detected but steam_api64.dll is missing. " +
                "Repair the game via Steam and retry.");
        }

        if (install.Store == GameStore.Gog && !hasGog && !hasSteam)
        {
            return GateResult.Fail(
                "GOG install detected but Galaxy/Steam plugins are missing. " +
                "Repair the install and retry.");
        }

        // Prefer at least one platform plugin when store unknown
        if (install.Store == GameStore.Unknown && !hasSteam && !hasGog)
        {
            return GateResult.Fail(
                "Install looks incomplete (no Steam/GOG native plugins). " +
                "Qud Lab refuses to run without a verified platform install.");
        }

        var msg =
            $"OK — {install.Store} install at {install.RootPath}" +
            (install.DetectedUnityVersion is null ? "" : $" (Unity {install.DetectedUnityVersion})");
        return GateResult.Success(install, msg);
    }
}
