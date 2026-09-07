using System;
using UnityEngine;

/// <summary>
/// Runtime ScriptableObject created from AAMT *_def.json packs
/// (Shared/game_asset_defs.py schema aamt.game_asset.v1).
/// </summary>
[CreateAssetMenu(fileName = "AamtGameAsset", menuName = "AAMT/Game Asset Def", order = 10)]
public class AamtGameAssetDef : ScriptableObject
{
    public string schema = "aamt.game_asset.v1";
    public string kind; // spell | projectile | ship
    public string id;
    public string displayName;
    public string theme;
    public string systemName;
    public string resourcesPath;

    public Texture2D icon;
    public Texture2D sprite;
    public Texture2D[] fxFrames;
    public Texture2D[] projectileFrames;
    public Texture2D[] frames;
    public Mesh mesh;
    public GameObject meshPrefab;

    public float damage = 10f;
    public float manaCost = 8f;
    public float cooldownSec = 3f;
    public float range = 6f;
    public float projectileSpeed = 14f;
    public float lifetimeSec = 2.5f;
    public float hull = 100f;
    public float armor = 20f;
    public float thrust = 12f;
    public string primaryColor;
    public string secondaryColor;
    public string elementHint;
    public string elinAlias;
    public int elinElementId;
    public string elinProc;
    public string elinIconSheet = "Media/Graphics/Icon/Element/icon_ability";

    public string sourceDefJsonPath;
}

[Serializable]
public class AamtDefJsonRoot
{
    public string schema;
    public string kind;
    public string id;
    public string displayName;
    public string theme;
    public string system;
    public string resourcesPath;
    public AamtDefJsonAssets assets;
    public AamtDefJsonStats stats;
    public AamtDefJsonSpec spec;
}

[Serializable]
public class AamtDefJsonAssets
{
    public string icon;
    public string sprite;
    public string[] fxFrames;
    public string[] projectileFrames;
    public string[] frames;
    public string mesh;
}

[Serializable]
public class AamtDefJsonStats
{
    public float damage;
    public float manaCost;
    public float cooldownSec;
    public float range;
    public float projectileSpeed;
    public float speed;
    public float lifetimeSec;
    public float hull;
    public float armor;
    public float thrust;
    public float turnRate;
    public float cargo;
    public string primaryColor;
    public string secondaryColor;
}

[Serializable]
public class AamtDefJsonSpec
{
    public string shape;
    public string[] colors;
    public bool glow;
    public string pattern;
}
