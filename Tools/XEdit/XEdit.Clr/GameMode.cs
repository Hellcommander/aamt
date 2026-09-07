namespace XEdit.Clr;

/// <summary>xEdit game modes from TES5Edit README (dev-4.1.6).</summary>
public enum XEditGame
{
    Auto = 0,
    TES4,
    TES4R,
    TES5,
    TES5VR,
    SSE,
    Enderal,
    EnderalSE,
    FO3,
    FNV,
    FO4,
    FO4VR,
    FO76,
    SF1
}

public static class XEditGameModes
{
    public static string Switch(XEditGame game) => game switch
    {
        XEditGame.TES4 => "-TES4",
        XEditGame.TES4R => "-TES4R",
        XEditGame.TES5 => "-TES5",
        XEditGame.TES5VR => "-TES5VR",
        XEditGame.SSE => "-SSE",
        XEditGame.Enderal => "-Enderal",
        XEditGame.EnderalSE => "-EnderalSE",
        XEditGame.FO3 => "-FO3",
        XEditGame.FNV => "-FNV",
        XEditGame.FO4 => "-FO4",
        XEditGame.FO4VR => "-FO4VR",
        XEditGame.FO76 => "-FO76",
        XEditGame.SF1 => "-SF1",
        _ => "-SF1"
    };

    public static string AppName(XEditGame game) => game switch
    {
        XEditGame.TES4 => "TES4",
        XEditGame.TES4R => "TES4R",
        XEditGame.TES5 => "TES5",
        XEditGame.TES5VR => "TES5VR",
        XEditGame.SSE => "SSE",
        XEditGame.Enderal => "Enderal",
        XEditGame.EnderalSE => "EnderalSE",
        XEditGame.FO3 => "FO3",
        XEditGame.FNV => "FNV",
        XEditGame.FO4 => "FO4",
        XEditGame.FO4VR => "FO4VR",
        XEditGame.FO76 => "FO76",
        _ => "SF1"
    };

    public static string MasterPlugin(XEditGame game) => game switch
    {
        XEditGame.TES4 or XEditGame.TES4R => "Oblivion.esm",
        XEditGame.TES5 or XEditGame.TES5VR or XEditGame.SSE or XEditGame.Enderal or XEditGame.EnderalSE => "Skyrim.esm",
        XEditGame.FO3 => "Fallout3.esm",
        XEditGame.FNV => "FalloutNV.esm",
        XEditGame.FO4 or XEditGame.FO4VR => "Fallout4.esm",
        XEditGame.FO76 => "SeventySix.esm",
        _ => "Starfield.esm"
    };

    public static string[] RequiredMasters(XEditGame game) => game == XEditGame.SF1
        ? ["Starfield.esm"]
        : [MasterPlugin(game)];

    public static XEditGame FromExeName(string path)
    {
        var name = Path.GetFileNameWithoutExtension(path).ToLowerInvariant();
        if (name.Contains("sf1")) return XEditGame.SF1;
        if (name.Contains("sse")) return XEditGame.SSE;
        if (name.Contains("fo4vr")) return XEditGame.FO4VR;
        if (name.Contains("fo4")) return XEditGame.FO4;
        if (name.Contains("fo76")) return XEditGame.FO76;
        if (name.Contains("fo3")) return XEditGame.FO3;
        if (name.Contains("fnv")) return XEditGame.FNV;
        if (name.Contains("tes4r")) return XEditGame.TES4R;
        if (name.Contains("tes4")) return XEditGame.TES4;
        if (name.Contains("tes5vr")) return XEditGame.TES5VR;
        if (name.Contains("enderalse")) return XEditGame.EnderalSE;
        if (name.Contains("enderal")) return XEditGame.Enderal;
        if (name.Contains("tes5")) return XEditGame.TES5;
        return XEditGame.Auto;
    }
}
