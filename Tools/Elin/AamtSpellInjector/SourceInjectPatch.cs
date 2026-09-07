using HarmonyLib;

namespace AamtSpellInjector
{
  /// <summary>
  /// SourceManager.Init ends with ACT.Init() then elin.source.imported.
  /// Postfix injects AAMT rows and registers them in ACT.dict.
  /// </summary>
  [HarmonyPatch(typeof(SourceManager), nameof(SourceManager.Init))]
  internal static class SourceManagerInitPatch
  {
    [HarmonyPostfix]
    private static void Postfix()
    {
      AbilityInjector.InjectAll(Plugin.ResolvedDefsPath);
    }
  }
}
