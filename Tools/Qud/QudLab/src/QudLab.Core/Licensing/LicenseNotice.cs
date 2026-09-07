namespace QudLab.Core.Licensing;

/// <summary>
/// Dual-license split: open UI/helpers vs proprietary core (loader, gate, sim, asset bind).
/// ThreadingAPI is a separate user mod (WIP) and is not part of Qud Lab.
/// </summary>
public static class LicenseNotice
{
    public const string OpenLicense = "MIT";
    public const string CoreLicense = "Proprietary (download-only) — see LICENSE-PROPRIETARY.md";

    public const string Disclaimer =
        "Qud Lab requires a legitimate Steam or GOG install of Caves of Qud. " +
        "It does not redistribute game assemblies or assets. " +
        "It must not be used as a standalone Caves of Qud runtime or arena game.";
}
