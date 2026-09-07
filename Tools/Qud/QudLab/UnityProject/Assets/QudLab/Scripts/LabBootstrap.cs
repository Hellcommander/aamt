using UnityEngine;

namespace QudLab.Unity
{
    /// <summary>Bootstraps LabShellUI in an empty scene.</summary>
    public sealed class LabBootstrap : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (Object.FindFirstObjectByType<LabShellUI>() != null)
                return;
            var go = new GameObject("QudLab");
            go.AddComponent<LabShellUI>();
            Object.DontDestroyOnLoad(go);
        }
    }
}
