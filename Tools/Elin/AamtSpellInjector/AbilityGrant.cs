using System;
using HarmonyLib;

namespace AamtSpellInjector
{
  internal static class AbilityGrant
  {
    private static bool _autoGrantedThisSession;

    public static void ResetSession() => _autoGrantedThisSession = false;

    public static void TryAutoGrant()
    {
      if (!Plugin.AutoGrant.Value || _autoGrantedThisSession)
        return;
      if (!IsPcReady())
        return;
      GrantAll(Plugin.GiveSpellbooks.Value);
      _autoGrantedThisSession = true;
    }

    public static void GrantAll(bool giveBooks)
    {
      if (!IsPcReady())
      {
        Plugin.Log?.LogWarning("AAMT grant skipped: PC not ready");
        return;
      }

      Chara pc = EClass.pc;
      int gained = 0;
      int books = 0;
      int total = 0;
      foreach (InjectedAbilityInfo info in InjectedAbilityRegistry.All)
      {
        ++total;
        try
        {
          Element existing = pc.elements.GetElement(info.Id);
          if (existing == null || existing.ValueWithoutLink == 0)
          {
            pc.GainAbility(info.Id, 100);
            ++gained;
          }

          if (giveBooks)
          {
            Thing book = ThingGen.CreateSpellbook(info.Alias);
            if (book != null)
            {
              pc.Pick(book, false);
              ++books;
            }
          }
        }
        catch (Exception ex)
        {
          Plugin.Log?.LogError($"AAMT grant failed for {info.Alias}: {ex.Message}");
        }
      }

      Plugin.Log?.LogInfo($"AAMT grant: gained={gained} books={books} tracked={total}");
      try
      {
        Msg.SayRaw($"AAMT: granted {gained} spell(s)" + (giveBooks ? $", {books} spellbook(s)" : ""));
      }
      catch
      {
        // UI feed may be unavailable during early boot
      }
    }

    private static bool IsPcReady()
    {
      try
      {
        return EClass.core != null
               && EClass.core.IsGameStarted
               && EClass.pc != null
               && EClass.sources != null
               && EClass.sources.elements != null;
      }
      catch
      {
        return false;
      }
    }
  }

  [HarmonyPatch(typeof(Game), nameof(Game.Load), new Type[] { typeof(string), typeof(bool) })]
  internal static class AbilityGrantOnLoadPatch
  {
    [HarmonyPostfix]
    private static void Postfix() => AbilityGrant.ResetSession();
  }

  [HarmonyPatch(typeof(Game), nameof(Game.StartNewGame))]
  internal static class AbilityGrantOnNewGamePatch
  {
    [HarmonyPostfix]
    private static void Postfix() => AbilityGrant.ResetSession();
  }
}
