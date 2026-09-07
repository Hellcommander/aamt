using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace AamtSpellInjector
{
  internal static class SpriteLoader
  {
    public static Sprite LoadPng(string path, string name)
    {
      if (string.IsNullOrEmpty(path) || !File.Exists(path))
        return null;
      byte[] bytes = File.ReadAllBytes(path);
      var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
      if (!ImageConversion.LoadImage(tex, bytes))
      {
        UnityEngine.Object.Destroy(tex);
        return null;
      }

      tex.filterMode = FilterMode.Point;
      tex.wrapMode = TextureWrapMode.Clamp;
      tex.name = name;
      var sprite = Sprite.Create(
        tex,
        new Rect(0f, 0f, tex.width, tex.height),
        new Vector2(0.5f, 0.5f),
        100f);
      sprite.name = name;
      return sprite;
    }

    public static List<Sprite> LoadPngFolder(string dir, string namePrefix)
    {
      var list = new List<Sprite>();
      if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir))
        return list;
      string[] files = Directory.GetFiles(dir, "*.png");
      Array.Sort(files, StringComparer.OrdinalIgnoreCase);
      for (int i = 0; i < files.Length; i++)
      {
        Sprite s = LoadPng(files[i], namePrefix + "_" + i);
        if (s != null)
          list.Add(s);
      }
      return list;
    }

    public static List<Sprite> LoadPngPaths(IEnumerable<string> paths, string namePrefix)
    {
      var list = new List<Sprite>();
      int i = 0;
      foreach (string path in paths)
      {
        Sprite s = LoadPng(path, namePrefix + "_" + i);
        if (s != null)
          list.Add(s);
        ++i;
      }
      return list;
    }
  }
}
