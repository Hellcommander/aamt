using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Batch import: scan Assets/Resources for *_def.json and create AamtGameAssetDef assets.
/// </summary>
public static class AamtDefImporter
{
    public static void ImportAll()
    {
        AssetDatabase.Refresh();
        string[] guids = AssetDatabase.FindAssets("_def", new[] { "Assets/Resources" });
        int created = 0;
        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (string.IsNullOrEmpty(path) || !path.EndsWith("_def.json"))
                continue;
            if (ImportOne(path))
                created++;
        }
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[AAMT] Def import complete. Created/updated " + created + " ScriptableObject(s).");
        EditorApplication.Exit(0);
    }

    public static bool ImportOne(string defAssetPath)
    {
        TextAsset jsonAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(defAssetPath);
        string raw;
        if (jsonAsset != null)
            raw = jsonAsset.text;
        else
        {
            string abs = Path.Combine(Directory.GetParent(Application.dataPath).FullName, defAssetPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(abs))
            {
                Debug.LogWarning("[AAMT] Missing def: " + defAssetPath);
                return false;
            }
            raw = File.ReadAllText(abs);
        }

        AamtDefJsonRoot data = JsonUtility.FromJson<AamtDefJsonRoot>(raw);
        if (data == null || string.IsNullOrEmpty(data.id))
        {
            Debug.LogWarning("[AAMT] Could not parse def: " + defAssetPath);
            return false;
        }

        string folder = Path.GetDirectoryName(defAssetPath).Replace('\\', '/');
        string soPath = folder + "/" + data.id + "_AamtDef.asset";

        AamtGameAssetDef so = AssetDatabase.LoadAssetAtPath<AamtGameAssetDef>(soPath);
        if (so == null)
        {
            so = ScriptableObject.CreateInstance<AamtGameAssetDef>();
            AssetDatabase.CreateAsset(so, soPath);
        }

        so.schema = string.IsNullOrEmpty(data.schema) ? "aamt.game_asset.v1" : data.schema;
        so.kind = data.kind;
        so.id = data.id;
        so.displayName = data.displayName;
        so.theme = data.theme;
        so.systemName = data.system;
        so.resourcesPath = data.resourcesPath;
        so.sourceDefJsonPath = defAssetPath;

        if (data.assets != null)
        {
            so.icon = LoadTex(folder, data.assets.icon);
            so.sprite = LoadTex(folder, data.assets.sprite);
            so.fxFrames = LoadTexArray(folder, data.assets.fxFrames);
            so.projectileFrames = LoadTexArray(folder, data.assets.projectileFrames);
            so.frames = LoadTexArray(folder, data.assets.frames);
            if (!string.IsNullOrEmpty(data.assets.mesh))
            {
                string meshPath = Combine(folder, data.assets.mesh);
                so.meshPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(meshPath);
                so.mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                if (so.mesh == null && so.meshPrefab != null)
                {
                    MeshFilter mf = so.meshPrefab.GetComponentInChildren<MeshFilter>();
                    if (mf != null) so.mesh = mf.sharedMesh;
                }
            }
        }

        if (data.stats != null)
        {
            so.damage = data.stats.damage > 0 ? data.stats.damage : so.damage;
            so.manaCost = data.stats.manaCost > 0 ? data.stats.manaCost : so.manaCost;
            so.cooldownSec = data.stats.cooldownSec > 0 ? data.stats.cooldownSec : so.cooldownSec;
            so.range = data.stats.range > 0 ? data.stats.range : so.range;
            so.projectileSpeed = data.stats.projectileSpeed > 0 ? data.stats.projectileSpeed : (data.stats.speed > 0 ? data.stats.speed : so.projectileSpeed);
            so.lifetimeSec = data.stats.lifetimeSec > 0 ? data.stats.lifetimeSec : so.lifetimeSec;
            so.hull = data.stats.hull > 0 ? data.stats.hull : so.hull;
            so.armor = data.stats.armor > 0 ? data.stats.armor : so.armor;
            so.thrust = data.stats.thrust > 0 ? data.stats.thrust : so.thrust;
            so.primaryColor = data.stats.primaryColor;
            so.secondaryColor = data.stats.secondaryColor;
        }

        // Element / Elin SourceElement fields from sibling *_elin_ability.json
        string elinPath = folder + "/" + data.id + "_elin_ability.json";
        string absElin = Path.Combine(Directory.GetParent(Application.dataPath).FullName, elinPath.Replace('/', Path.DirectorySeparatorChar));
        string elinText = null;
        TextAsset elin = AssetDatabase.LoadAssetAtPath<TextAsset>(elinPath);
        if (elin != null) elinText = elin.text;
        else if (File.Exists(absElin)) elinText = File.ReadAllText(absElin);
        if (!string.IsNullOrEmpty(elinText))
        {
            so.elementHint = ExtractJsonString(elinText, "elementHint") ?? so.elementHint;
            // nested row.alias / row.id / row.proc
            string alias = ExtractJsonString(elinText, "alias");
            if (!string.IsNullOrEmpty(alias)) so.elinAlias = alias;
            int eid = ExtractJsonInt(elinText, "\"id\"");
            if (eid > 0) so.elinElementId = eid;
            string proc = ExtractJsonString(elinText, "proc");
            // proc may be array ["Arrow"] — grab first quoted token after "proc"
            if (string.IsNullOrEmpty(proc))
            {
                int pi = elinText.IndexOf("\"proc\"");
                if (pi >= 0)
                {
                    int q1 = elinText.IndexOf('"', elinText.IndexOf('[', pi) + 1);
                    int q2 = elinText.IndexOf('"', q1 + 1);
                    if (q1 >= 0 && q2 > q1) so.elinProc = elinText.Substring(q1 + 1, q2 - q1 - 1);
                }
            }
        }

        EditorUtility.SetDirty(so);
        Debug.Log("[AAMT] Imported def -> " + soPath + " (" + so.kind + "/" + so.id + ")");
        return true;
    }

    static string ExtractJsonString(string text, string key)
    {
        string needle = "\"" + key.Trim('"') + "\"";
        int i = text.IndexOf(needle);
        if (i < 0) return null;
        int q1 = text.IndexOf('"', i + needle.Length);
        // skip whitespace/colon
        int colon = text.IndexOf(':', i + needle.Length);
        if (colon < 0) return null;
        q1 = text.IndexOf('"', colon + 1);
        if (q1 < 0) return null;
        int q2 = text.IndexOf('"', q1 + 1);
        if (q2 <= q1) return null;
        return text.Substring(q1 + 1, q2 - q1 - 1);
    }

    static int ExtractJsonInt(string text, string keyWithQuotes)
    {
        int i = text.IndexOf(keyWithQuotes);
        if (i < 0) return 0;
        int colon = text.IndexOf(':', i);
        if (colon < 0) return 0;
        int j = colon + 1;
        while (j < text.Length && (text[j] == ' ' || text[j] == '\t')) j++;
        int k = j;
        while (k < text.Length && ((text[k] >= '0' && text[k] <= '9') || text[k] == '-')) k++;
        int v;
        if (int.TryParse(text.Substring(j, k - j), out v)) return v;
        return 0;
    }

    static string Combine(string folder, string rel)
    {
        if (string.IsNullOrEmpty(rel)) return folder;
        if (rel.StartsWith("Assets/")) return rel.Replace('\\', '/');
        return (folder.TrimEnd('/') + "/" + rel.Replace('\\', '/')).Replace("//", "/");
    }

    static Texture2D LoadTex(string folder, string rel)
    {
        if (string.IsNullOrEmpty(rel)) return null;
        return AssetDatabase.LoadAssetAtPath<Texture2D>(Combine(folder, rel));
    }

    static Texture2D[] LoadTexArray(string folder, string[] rels)
    {
        if (rels == null || rels.Length == 0) return new Texture2D[0];
        var list = new System.Collections.Generic.List<Texture2D>();
        foreach (string r in rels)
        {
            Texture2D t = LoadTex(folder, r);
            if (t != null) list.Add(t);
        }
        return list.ToArray();
    }
}
