using System.Collections.Generic;
using UnityEngine;

namespace AamtSpellInjector
{
  internal sealed class InjectedAbilityInfo
  {
    public int Id;
    public string Alias;
    public Sprite Icon;
    public readonly List<Sprite> FxSprites = new List<Sprite>();
    public readonly List<Sprite> ProjectileSprites = new List<Sprite>();
  }

  internal static class InjectedAbilityRegistry
  {
    private static readonly Dictionary<string, InjectedAbilityInfo> ByAlias =
      new Dictionary<string, InjectedAbilityInfo>();

    private static readonly Dictionary<int, InjectedAbilityInfo> ById =
      new Dictionary<int, InjectedAbilityInfo>();

    public static IEnumerable<InjectedAbilityInfo> All => ByAlias.Values;

    public static void Clear()
    {
      ByAlias.Clear();
      ById.Clear();
    }

    public static void Register(InjectedAbilityInfo info)
    {
      if (info == null || string.IsNullOrEmpty(info.Alias))
        return;
      ByAlias[info.Alias] = info;
      ById[info.Id] = info;
    }

    public static bool TryGet(string alias, out InjectedAbilityInfo info) =>
      ByAlias.TryGetValue(alias, out info);

    public static bool TryGet(int id, out InjectedAbilityInfo info) =>
      ById.TryGetValue(id, out info);
  }
}
