using UnityEngine;
using UnityEditor;
using System.IO;

public static class AamtMeshPrefabBuilder
{
    // Replaced at install time: __SYS__ / __PREF__
    const string SystemName = "__SYS__";
    const string PrefabName = "__PREF__";

    public static void Build()
    {
        AssetDatabase.Refresh();
        string stem = System.Text.RegularExpressions.Regex.Replace(SystemName, "[^A-Za-z0-9_]", "_");
        string skinRel = "Assets/Resources/" + SystemName + "/Textures/Skins";
        string matRel = "Assets/Resources/" + SystemName + "/Materials/" + SystemName + "_Material.mat";
        string prefabRel = "Assets/Resources/" + SystemName + "/Prefabs/" + PrefabName + ".prefab";

        Directory.CreateDirectory(Path.Combine(Application.dataPath, "Resources", SystemName, "Materials"));
        Directory.CreateDirectory(Path.Combine(Application.dataPath, "Resources", SystemName, "Prefabs"));

        Material mat = new Material(Shader.Find("Standard"));
        TryMap(mat, skinRel, stem + "_diffuse.png", "_MainTex", false);
        if (mat.HasProperty("_MainTex") && mat.GetTexture("_MainTex") != null)
            mat.mainTexture = mat.GetTexture("_MainTex");
        TryMap(mat, skinRel, stem + "_normal.png", "_BumpMap", true);
        if (!TryMap(mat, skinRel, stem + "_metallicgloss.png", "_MetallicGlossMap", false))
            TryMap(mat, skinRel, stem + "_metallic.png", "_MetallicGlossMap", false);
        TryMap(mat, skinRel, stem + "_emission.png", "_EmissionMap", false);
        if (mat.HasProperty("_MetallicGlossMap") && mat.GetTexture("_MetallicGlossMap") != null)
            mat.EnableKeyword("_METALLICGLOSSMAP");
        if (mat.HasProperty("_EmissionMap") && mat.GetTexture("_EmissionMap") != null)
        {
            mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        }
        AssetDatabase.CreateAsset(mat, matRel);
        Debug.Log("[AAMT] Material created: " + matRel);

        string[] meshPaths = new string[] {
            "Assets/Resources/" + SystemName + "/Meshes/" + stem + ".fbx",
            "Assets/Resources/" + SystemName + "/Meshes/" + SystemName + ".fbx",
            "Assets/Resources/Meshes/" + stem + ".fbx",
            "Assets/Resources/Meshes/qud_mod.fbx"
        };
        GameObject go = null;
        string used = null;
        foreach (string meshPath in meshPaths)
        {
            string abs = Path.Combine(Application.dataPath.Substring(0, Application.dataPath.Length - "Assets".Length), meshPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(abs)) continue;
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(meshPath);
            if (model != null)
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                if (go != null) { go.name = PrefabName; used = meshPath; break; }
            }
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (mesh != null)
            {
                go = new GameObject(PrefabName);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>();
                used = meshPath;
                break;
            }
        }
        if (go == null) go = new GameObject(PrefabName);
        mat = AssetDatabase.LoadAssetAtPath<Material>(matRel);
        if (mat != null)
        {
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>(true))
                r.sharedMaterial = mat;
        }
        PrefabUtility.SaveAsPrefabAsset(go, prefabRel);
        Object.DestroyImmediate(go);
        if (used != null) Debug.Log("[AAMT] Prefab created with mesh " + used + ": " + prefabRel);
        else Debug.LogWarning("[AAMT] Prefab created without FBX: " + prefabRel);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        EditorApplication.Exit(0);
    }

    static bool TryMap(Material mat, string skinRelDir, string fileName, string property, bool asNormal)
    {
        string path = skinRelDir + "/" + fileName;
        Texture2D map = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        if (map == null) return false;
        if (!mat.HasProperty(property)) return false;
        mat.SetTexture(property, map);
        if (asNormal) mat.EnableKeyword("_NORMALMAP");
        Debug.Log("[AAMT] Assigned " + property + " <- " + path);
        return true;
    }
}
