using System.IO;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;

namespace AamtSpellInjector
{
  [BepInPlugin(PluginInfo.GUID, PluginInfo.Name, PluginInfo.Version)]
  public class Plugin : BaseUnityPlugin
  {
    public static ManualLogSource Log { get; private set; }
    public static string ResolvedDefsPath { get; private set; }

    public static ConfigEntry<bool> AutoGrant { get; private set; }
    public static ConfigEntry<bool> GiveSpellbooks { get; private set; }
    public static ConfigEntry<bool> PlayCustomFx { get; private set; }
    public static ConfigEntry<KeyboardShortcut> GrantHotkey { get; private set; }

    private ConfigEntry<string> _defsPath;

    private void Awake()
    {
      Log = Logger;
      _defsPath = Config.Bind(
        "General",
        "DefsPath",
        "",
        "Folder of *_elin_ability.json files. Empty = <plugin>/defs");

      AutoGrant = Config.Bind(
        "Grant",
        "AutoGrantOnGameStart",
        true,
        "When a game is running, grant all injected AAMT spells to the PC once per load.");
      GiveSpellbooks = Config.Bind(
        "Grant",
        "GiveSpellbooks",
        true,
        "Also put a spellbook for each injected spell into inventory on grant.");
      GrantHotkey = Config.Bind(
        "Grant",
        "GrantHotkey",
        new KeyboardShortcut(KeyCode.F8),
        "Hotkey to grant AAMT spells (+ books if GiveSpellbooks).");
      PlayCustomFx = Config.Bind(
        "FX",
        "PlayCustomFx",
        true,
        "Overlay generated projectile/FX sprites when casting injected spells.");

      string pluginDir = Path.GetDirectoryName(Info.Location) ?? Paths.PluginPath;
      ResolvedDefsPath = string.IsNullOrWhiteSpace(_defsPath.Value)
        ? Path.Combine(pluginDir, "defs")
        : _defsPath.Value;

      Directory.CreateDirectory(ResolvedDefsPath);

      var harmony = new Harmony(PluginInfo.GUID);
      harmony.PatchAll();
      Log.LogInfo($"AAMT Spell Injector {PluginInfo.Version} ready. Defs: {ResolvedDefsPath}");
      Log.LogInfo($"Grant hotkey: {GrantHotkey.Value} | AutoGrant={AutoGrant.Value} | FX={PlayCustomFx.Value}");
    }

    private void Update()
    {
      AbilityGrant.TryAutoGrant();
      if (GrantHotkey.Value.IsDown())
        AbilityGrant.GrantAll(GiveSpellbooks.Value);
    }
  }

  internal static class PluginInfo
  {
    public const string GUID = "com.aamt.elin.spellinjector";
    public const string Name = "AAMT Spell Injector";
    public const string Version = "1.1.0";
  }
}
