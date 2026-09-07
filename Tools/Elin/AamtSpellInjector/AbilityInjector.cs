using System;
using System.Collections.Generic;
using System.IO;
using BepInEx.Logging;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace AamtSpellInjector
{
  internal static class AbilityInjector
  {
    public static void InjectAll(string defsRoot)
    {
      ManualLogSource log = Plugin.Log;
      if (string.IsNullOrWhiteSpace(defsRoot) || !Directory.Exists(defsRoot))
      {
        log?.LogWarning($"AAMT defs folder missing: {defsRoot}");
        return;
      }

      SourceElement elements;
      try
      {
        elements = EClass.sources.elements;
      }
      catch (Exception ex)
      {
        log?.LogError($"AAMT inject skipped (sources unavailable): {ex.Message}");
        return;
      }

      if (elements == null)
      {
        log?.LogWarning("AAMT inject skipped: elements is null");
        return;
      }

      string[] files = Directory.GetFiles(defsRoot, "*_elin_ability.json", SearchOption.AllDirectories);
      if (files.Length == 0)
      {
        log?.LogInfo($"AAMT: no *_elin_ability.json under {defsRoot}");
        return;
      }

      InjectedAbilityRegistry.Clear();

      int added = 0;
      int skipped = 0;
      int icons = 0;
      foreach (string path in files)
      {
        try
        {
          if (TryInjectFile(elements, path, log, out bool iconOk))
          {
            ++added;
            if (iconOk)
              ++icons;
          }
          else
            ++skipped;
        }
        catch (Exception ex)
        {
          log?.LogError($"AAMT failed {path}: {ex}");
        }
      }

      log?.LogInfo($"AAMT inject done: added={added} icons={icons} skipped={skipped} scanned={files.Length}");
    }

    private static bool TryInjectFile(SourceElement elements, string path, ManualLogSource log, out bool iconRegistered)
    {
      iconRegistered = false;
      JObject root = JObject.Parse(File.ReadAllText(path));
      JToken rowTok = root["row"];
      if (rowTok == null || rowTok.Type != JTokenType.Object)
      {
        log?.LogWarning($"AAMT skip (no row object): {path}");
        return false;
      }

      JObject j = (JObject)rowTok;
      string alias = j.Value<string>("alias");
      int id = j.Value<int?>("id") ?? 0;
      if (string.IsNullOrEmpty(alias) || id <= 0)
      {
        log?.LogWarning($"AAMT skip (bad alias/id): {path}");
        return false;
      }

      if (elements.alias != null && elements.alias.ContainsKey(alias))
      {
        log?.LogDebug($"AAMT skip existing alias {alias}");
        return false;
      }

      if (elements.map != null && elements.map.ContainsKey(id))
      {
        // Keep alias unique; bump id into free high band if collision.
        int free = id;
        while (elements.map.ContainsKey(free))
          ++free;
        log?.LogWarning($"AAMT id {id} taken; using {free} for {alias}");
        id = free;
      }

      SourceElement.Row row = BuildRow(j, id, alias);
      row.OnImportData(elements);
      row.isSpell = string.Equals(row.categorySub, "spell", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(row.group, "SPELL", StringComparison.OrdinalIgnoreCase);
      row.isSkill = string.Equals(row.category, "skill", StringComparison.OrdinalIgnoreCase);
      row.isAttribute = string.Equals(row.category, "attribute", StringComparison.OrdinalIgnoreCase);
      row.isTrait = ContainsTag(row.tag, "trait");

      elements.rows.Add(row);
      elements.map[row.id] = row;
      elements.alias[row.GetAlias] = row;
      if (elements.fuzzyAlias != null)
        elements.fuzzyAlias[row.GetAlias] = row.GetAlias;

      string group = row.group ?? "";
      if (string.Equals(group, "SPELL", StringComparison.OrdinalIgnoreCase)
          || string.Equals(group, "ABILITY", StringComparison.OrdinalIgnoreCase))
      {
        ACT.dict[row.alias] = ACT.Create(row);
      }

      iconRegistered = RegisterAssets(root, path, alias, row.id, log);
      log?.LogInfo($"AAMT injected {row.alias} id={row.id} type={row.type} proc={(row.proc != null && row.proc.Length > 0 ? row.proc[0] : "")} icon={iconRegistered}");
      return true;
    }

    private static bool RegisterAssets(JObject root, string jsonPath, string alias, int id, ManualLogSource log)
    {
      string jsonDir = Path.GetDirectoryName(jsonPath) ?? "";
      var info = new InjectedAbilityInfo { Id = id, Alias = alias };

      string iconPng = ResolveIconPath(root, jsonDir, alias);
      if (iconPng != null)
      {
        Sprite icon = SpriteLoader.LoadPng(iconPng, alias);
        if (icon != null)
        {
          SpriteSheet.Add(icon);
          info.Icon = icon;
          log?.LogDebug($"AAMT icon registered {alias} from {iconPng}");
        }
      }

      // Preferred layout from Deploy-AamtElinAbility: defs/fx/{alias}/*.png and defs/proj/{alias}/*.png
      string fxDir = Path.Combine(jsonDir, "fx", alias);
      string projDir = Path.Combine(jsonDir, "proj", alias);
      info.FxSprites.AddRange(SpriteLoader.LoadPngFolder(fxDir, alias + "_fx"));
      info.ProjectileSprites.AddRange(SpriteLoader.LoadPngFolder(projDir, alias + "_proj"));

      // Fallback: assets.fxPaths / projectilePaths relative to json dir
      JToken assets = root["assets"];
      if (assets != null && assets.Type == JTokenType.Object)
      {
        if (info.FxSprites.Count == 0)
        {
          foreach (string p in RelPaths(assets["fxPaths"], jsonDir))
          {
            Sprite s = SpriteLoader.LoadPng(p, alias + "_fx_" + info.FxSprites.Count);
            if (s != null)
              info.FxSprites.Add(s);
          }
        }
        if (info.ProjectileSprites.Count == 0)
        {
          foreach (string p in RelPaths(assets["projectilePaths"], jsonDir))
          {
            Sprite s = SpriteLoader.LoadPng(p, alias + "_proj_" + info.ProjectileSprites.Count);
            if (s != null)
              info.ProjectileSprites.Add(s);
          }
        }
      }

      InjectedAbilityRegistry.Register(info);
      log?.LogDebug($"AAMT assets {alias}: fx={info.FxSprites.Count} proj={info.ProjectileSprites.Count}");
      return info.Icon != null;
    }

    private static string ResolveIconPath(JObject root, string jsonDir, string alias)
    {
      var candidates = new List<string>
      {
        Path.Combine(jsonDir, "icons", alias + ".png"),
        Path.Combine(jsonDir, alias + ".png"),
      };
      JToken assets = root["assets"];
      if (assets != null && assets.Type == JTokenType.Object)
      {
        string iconRel = assets.Value<string>("iconPath");
        if (!string.IsNullOrEmpty(iconRel))
        {
          candidates.Insert(0, Path.Combine(jsonDir, iconRel));
          string parent = Directory.GetParent(jsonDir)?.FullName;
          if (!string.IsNullOrEmpty(parent))
            candidates.Insert(0, Path.Combine(parent, iconRel));
        }
      }
      foreach (string c in candidates)
      {
        if (!string.IsNullOrEmpty(c) && File.Exists(c))
          return c;
      }
      return null;
    }

    private static IEnumerable<string> RelPaths(JToken tok, string jsonDir)
    {
      if (tok == null || tok.Type != JTokenType.Array)
        yield break;
      foreach (JToken t in (JArray)tok)
      {
        string rel = t?.ToString();
        if (string.IsNullOrEmpty(rel))
          continue;
        string full = Path.IsPathRooted(rel) ? rel : Path.Combine(jsonDir, rel);
        if (File.Exists(full))
          yield return full;
      }
    }

    private static SourceElement.Row BuildRow(JObject j, int id, string alias)
    {
      return new SourceElement.Row
      {
        id = id,
        alias = alias,
        name = Str(j, "name", alias),
        name_JP = Str(j, "name_JP", Str(j, "name", alias)),
        altname = Str(j, "altname", ""),
        altname_JP = Str(j, "altname_JP", ""),
        aliasParent = Str(j, "aliasParent", ""),
        aliasRef = Str(j, "aliasRef", ""),
        aliasMtp = Str(j, "aliasMtp", ""),
        parentFactor = j.Value<float?>("parentFactor") ?? 1f,
        lvFactor = j.Value<int?>("lvFactor") ?? 10,
        encFactor = j.Value<int?>("encFactor") ?? 0,
        encSlot = Str(j, "encSlot", ""),
        mtp = j.Value<int?>("mtp") ?? 1,
        LV = j.Value<int?>("LV") ?? 1,
        chance = j.Value<int?>("chance") ?? 100,
        value = j.Value<int?>("value") ?? 0,
        cost = IntArr(j["cost"], new[] { 8 }),
        geneSlot = j.Value<int?>("geneSlot") ?? 0,
        sort = j.Value<int?>("sort") ?? id,
        target = Str(j, "target", "Enemy"),
        proc = StrArr(j["proc"], new[] { "Arrow" }),
        type = Str(j, "type", "Spell"),
        group = Str(j, "group", "SPELL"),
        category = Str(j, "category", "ability"),
        categorySub = Str(j, "categorySub", "spell"),
        abilityType = StrArr(j["abilityType"], new[] { "attack" }),
        tag = StrArr(j["tag"], new[] { "aamt" }),
        thing = Str(j, "thing", ""),
        eleP = j.Value<int?>("eleP") ?? 100,
        cooldown = j.Value<int?>("cooldown") ?? 0,
        charge = j.Value<int?>("charge") ?? 15,
        radius = j.Value<float?>("radius") ?? 0f,
        max = j.Value<int?>("max") ?? 0,
        req = StrArr(j["req"], Array.Empty<string>()),
        idTrainer = Str(j, "idTrainer", ""),
        partySkill = j.Value<int?>("partySkill") ?? 0,
        tagTrainer = Str(j, "tagTrainer", ""),
        detail = Str(j, "detail", ""),
        detail_JP = Str(j, "detail_JP", Str(j, "detail", "")),
        textPhase = Str(j, "textPhase", ""),
        textPhase_JP = Str(j, "textPhase_JP", ""),
        textExtra = Str(j, "textExtra", ""),
        textExtra_JP = Str(j, "textExtra_JP", ""),
        textInc = Str(j, "textInc", ""),
        textInc_JP = Str(j, "textInc_JP", ""),
        textDec = Str(j, "textDec", ""),
        textDec_JP = Str(j, "textDec_JP", ""),
        levelBonus = Str(j, "levelBonus", ""),
        levelBonus_JP = Str(j, "levelBonus_JP", ""),
        foodEffect = StrArr(j["foodEffect"], Array.Empty<string>()),
        langAct = StrArr(j["langAct"], Array.Empty<string>()),
        textAlt = StrArr(j["textAlt"], Array.Empty<string>()),
        textAlt_JP = StrArr(j["textAlt_JP"], Array.Empty<string>()),
        adjective = StrArr(j["adjective"], Array.Empty<string>()),
        adjective_JP = StrArr(j["adjective_JP"], Array.Empty<string>()),
        idMold = j.Value<int?>("idMold") ?? 0,
      };
    }

    private static string Str(JObject j, string key, string fallback)
    {
      string v = j.Value<string>(key);
      return string.IsNullOrEmpty(v) ? fallback : v;
    }

    private static string[] StrArr(JToken tok, string[] fallback)
    {
      if (tok == null || tok.Type != JTokenType.Array)
        return fallback;
      var list = new List<string>();
      foreach (JToken t in (JArray)tok)
      {
        if (t != null && t.Type != JTokenType.Null)
          list.Add(t.ToString());
      }
      return list.Count > 0 ? list.ToArray() : fallback;
    }

    private static int[] IntArr(JToken tok, int[] fallback)
    {
      if (tok == null || tok.Type != JTokenType.Array)
        return fallback;
      var list = new List<int>();
      foreach (JToken t in (JArray)tok)
      {
        if (t != null && t.Type != JTokenType.Null && int.TryParse(t.ToString(), out int n))
          list.Add(n);
      }
      return list.Count > 0 ? list.ToArray() : fallback;
    }

    private static bool ContainsTag(string[] tags, string needle)
    {
      if (tags == null)
        return false;
      foreach (string t in tags)
      {
        if (string.Equals(t, needle, StringComparison.OrdinalIgnoreCase))
          return true;
      }
      return false;
    }
  }
}
