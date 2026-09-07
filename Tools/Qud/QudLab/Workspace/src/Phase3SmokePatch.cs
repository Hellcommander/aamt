using System;
using HarmonyLib;
using XRL.World;

namespace QudLab.Patches
{
    /// <summary>
    /// Harmony patch scaffold. Target type hint: XRL.World.GameObject
    /// Confirm method signatures via qudlab explain / GET /type before enabling a postfix.
    /// </summary>
    [HarmonyPatch(typeof(GameObject))]
    public static class Phase3SmokePatch
    {
        // [HarmonyPostfix]
        // [HarmonyPatch(nameof(SomeMethod))]
        // public static void Postfix(/* args */)
        // {
        // }
    }
}