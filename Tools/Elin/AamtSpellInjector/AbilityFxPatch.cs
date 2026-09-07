using System;
using HarmonyLib;
using UnityEngine;

namespace AamtSpellInjector
{
  /// <summary>
  /// After a successful AAMT act, overlay projectile/impact sprites onto a vanilla Effect prefab.
  /// Combat still uses EffectId from proc[]; this adds the generated art on top.
  /// </summary>
  [HarmonyPatch(typeof(Act), nameof(Act.Perform), new Type[] { typeof(Chara), typeof(Card), typeof(Point) })]
  internal static class AbilityFxPatch
  {
    [HarmonyPostfix]
    private static void Postfix(Act __instance, bool __result)
    {
      if (!__result || !Plugin.PlayCustomFx.Value)
        return;
      if (__instance?.source == null)
        return;
      if (!InjectedAbilityRegistry.TryGet(__instance.source.alias, out InjectedAbilityInfo info))
        return;

      try
      {
        Point from = Act.CC != null ? Act.CC.pos : null;
        Point to = Act.TP != null && Act.TP.IsValid ? Act.TP : (Act.TC != null ? Act.TC.pos : from);
        if (from == null || to == null)
          return;

        Sprite proj = info.ProjectileSprites.Count > 0
          ? info.ProjectileSprites[UnityEngine.Random.Range(0, info.ProjectileSprites.Count)]
          : null;
        Sprite impact = info.FxSprites.Count > 0
          ? info.FxSprites[UnityEngine.Random.Range(0, info.FxSprites.Count)]
          : info.Icon;

        if (proj != null)
          PlayEffect(from, to, proj, traveling: true);
        if (impact != null)
          PlayEffect(to, null, impact, traveling: false);
      }
      catch (Exception ex)
      {
        Plugin.Log?.LogDebug($"AAMT FX skip: {ex.Message}");
      }
    }

    private static void PlayEffect(Point from, Point to, Sprite sprite, bool traveling)
    {
      Effect fx = TryCreateEffect(traveling);
      if (fx == null)
        return;
      if (traveling && to != null)
        fx.Play(from, to: to, sprite: sprite);
      else
        fx.Play(from, sprite: sprite);
    }

    private static Effect TryCreateEffect(bool traveling)
    {
      string[] ids = traveling
        ? new[] { "arrow", "bolt", "missile", "element" }
        : new[] { "hit", "smoke", "element", "arrow", "bolt" };
      foreach (string id in ids)
      {
        try
        {
          Effect e = Effect.Get(id);
          if (e != null)
            return e;
        }
        catch
        {
          // try next
        }
      }
      return null;
    }
  }
}
