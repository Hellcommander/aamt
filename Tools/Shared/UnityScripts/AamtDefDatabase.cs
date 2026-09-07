using UnityEngine;

/// <summary>
/// Runtime helper: load AamtGameAssetDef from Resources by id or system folder.
/// Expected Resources path pattern: {system}/Spells|{Projectiles}|{Ships}/{id}/{id}_AamtDef
/// </summary>
public static class AamtDefDatabase
{
    public static AamtGameAssetDef Load(string resourcesKey)
    {
        return Resources.Load<AamtGameAssetDef>(resourcesKey);
    }

    public static AamtGameAssetDef LoadInSystem(string system, string kindFolder, string id)
    {
        string key = system + "/" + kindFolder + "/" + id + "/" + id + "_AamtDef";
        return Resources.Load<AamtGameAssetDef>(key);
    }

    public static AamtGameAssetDef[] LoadAll()
    {
        return Resources.LoadAll<AamtGameAssetDef>("");
    }
}
