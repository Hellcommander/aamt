using UnityEngine;
using UnityEditor;
using System.IO;

public static class AamtAssetBundleBuilder
{
    public static void BuildBundles()
    {
        string resourcesRoot = "Assets/Resources";
        if (AssetDatabase.IsValidFolder(resourcesRoot))
        {
            string[] guids = AssetDatabase.FindAssets("t:Texture t:Material t:Mesh t:GameObject t:Prefab", new[] { resourcesRoot });
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path)) continue;
                if (path.EndsWith(".cs")) continue;
                AssetImporter importer = AssetImporter.GetAtPath(path);
                if (importer == null) continue;
                if (string.IsNullOrEmpty(importer.assetBundleName))
                    importer.assetBundleName = "aamt_resources";
            }
            AssetDatabase.SaveAssets();
        }

        string outDir = Path.Combine(Application.dataPath, "AssetBundles", "Windows");
        Directory.CreateDirectory(outDir);
        var manifests = BuildPipeline.BuildAssetBundles(
            outDir,
            BuildAssetBundleOptions.ChunkBasedCompression,
            BuildTarget.StandaloneWindows64
        );
        if (manifests == null)
            Debug.LogWarning("[AAMT] BuildAssetBundles returned null (no labeled assets?).");
        else
            Debug.Log("[AAMT] AssetBundles built to " + outDir);
        AssetDatabase.Refresh();
        EditorApplication.Exit(0);
    }
}
