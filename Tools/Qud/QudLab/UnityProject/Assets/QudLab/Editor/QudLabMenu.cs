#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace QudLab.Unity.Editor
{
    /// <summary>Editor helpers — sync refs / open workspace docs without leaving Unity.</summary>
    public static class QudLabMenu
    {
        const string LabRootKey = "QudLab.Root";

        [MenuItem("Qud Lab/Open Lab Folder")]
        static void OpenLabFolder()
        {
            var root = FindLabRoot();
            if (root == null)
            {
                EditorUtility.DisplayDialog("Qud Lab", "Could not find QudLab folder (look for QudLab.sln).", "OK");
                return;
            }
            EditorUtility.RevealInFinder(root);
        }

        [MenuItem("Qud Lab/Copy sync-refs command")]
        static void CopySyncRefs()
        {
            var root = FindLabRoot() ?? @"D:\games\Ai assisted toolkit\Tools\Qud\QudLab";
            var cmd = $"cd /d \"{root}\" && Sync-Refs.bat";
            EditorGUIUtility.systemCopyBuffer = cmd;
            Debug.Log("[Qud Lab] Copied to clipboard: " + cmd);
        }

        [MenuItem("Qud Lab/Remind: Copilot needs Workspace project")]
        static void Remind()
        {
            EditorUtility.DisplayDialog(
                "Qud Lab — Copilot refs",
                "1. Run Sync-Refs.bat (or qudlab setup)\n" +
                "2. Open QudLab.code-workspace in Cursor\n" +
                "3. Edit Workspace/src — HintPaths resolve XRL.* from your Qud install\n\n" +
                "ThreadingAPI is a separate WIP mod and is not bundled.",
                "OK");
        }

        static string FindLabRoot()
        {
            var cached = EditorPrefs.GetString(LabRootKey, "");
            if (!string.IsNullOrEmpty(cached) && System.IO.File.Exists(System.IO.Path.Combine(cached, "QudLab.sln")))
                return cached;

            // UnityProject is …/QudLab/UnityProject
            var data = Application.dataPath; // …/UnityProject/Assets
            var unityProject = System.IO.Directory.GetParent(data)?.FullName;
            var lab = unityProject != null ? System.IO.Directory.GetParent(unityProject)?.FullName : null;
            if (lab != null && System.IO.File.Exists(System.IO.Path.Combine(lab, "QudLab.sln")))
            {
                EditorPrefs.SetString(LabRootKey, lab);
                return lab;
            }
            return null;
        }
    }
}
#endif
