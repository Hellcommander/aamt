using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

// Generic, spec-driven prefab + asset-bundle builder for Arendeth's Caves of Qud Spring Molting UI windows.
// Reads a RESOLVED *.springui.json (theme colors already inlined by qud_spring_ui.py generate) and turns the
// node tree into plain uGUI objects (RectTransform, Image, ScrollRect, RectMask2D, layout groups, LayoutElement,
// ContentSizeFitter), saves Assets/QudUI/<Prefab>.prefab and packs one bundle per platform.
//
//   Unity.exe -batchmode -nographics -quit -projectPath <staged project> -executeMethod BuildQudUI.Build
//             -spec <Prefab>.resolved.json -out <OutDir>/Bundles [-bundle <name>]
//
// Node schema: see `python -I qud_spring_ui.py schema`. The mods' runtime code attaches TextMeshPro, UITextSkin,
// FrameworkScroller etc. by object NAME, so this script never references the game's assemblies.
public static class BuildQudUI
{
    const string PrefabDir = "Assets/QudUI";

    public static void Build()
    {
        string specPath = Arg("-spec");
        if (string.IsNullOrEmpty(specPath) || !File.Exists(specPath))
        {
            Debug.LogError("QUDUI error: -spec <resolved.json> missing or not found: " + specPath);
            return;
        }
        string outDir = Arg("-out") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Bundles"));
        Directory.CreateDirectory(outDir);

        Dictionary<string, object> spec;
        try
        {
            spec = MiniJson.Parse(File.ReadAllText(specPath)) as Dictionary<string, object>;
        }
        catch (Exception ex)
        {
            Debug.LogError("QUDUI error: cannot parse spec: " + ex.Message);
            return;
        }
        if (spec == null)
        {
            Debug.LogError("QUDUI error: spec root is not an object");
            return;
        }

        string prefabName = Str(spec, "prefab");
        string bundle = Arg("-bundle") ?? Str(spec, "bundle");
        var rootSpec = spec["root"] as Dictionary<string, object>;
        if (string.IsNullOrEmpty(prefabName) || string.IsNullOrEmpty(bundle) || rootSpec == null)
        {
            Debug.LogError("QUDUI error: spec needs prefab, bundle and root");
            return;
        }

        string prefabPath = PrefabDir + "/" + prefabName + ".prefab";
        try
        {
            GameObject root = BuildNode(rootSpec, null, true);
            Directory.CreateDirectory(PrefabDir);
            PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("QUDUI prefab written to " + prefabPath + " (" + CountNodes(rootSpec) + " objects)");
        }
        catch (Exception ex)
        {
            Debug.LogError("QUDUI error: building prefab failed: " + ex);
            return;
        }

        var targets = new List<KeyValuePair<BuildTarget, string>>
        {
            new KeyValuePair<BuildTarget, string>(BuildTarget.StandaloneWindows64, "windows"),
            new KeyValuePair<BuildTarget, string>(BuildTarget.StandaloneOSX, "osx"),
            new KeyValuePair<BuildTarget, string>(BuildTarget.StandaloneLinux64, "linux")
        };
        foreach (var t in targets)
        {
            if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, t.Key))
            {
                Debug.Log("QUDUI skipping " + t.Value + ": that build support isn't installed in Unity Hub.");
                continue;
            }
            string dir = Path.Combine(outDir, t.Value);
            Directory.CreateDirectory(dir);
            var b = new AssetBundleBuild { assetBundleName = bundle + "_" + t.Value, assetNames = new[] { prefabPath } };
            var manifest = BuildPipeline.BuildAssetBundles(dir, new[] { b },
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode, t.Key);
            Debug.Log(manifest != null ? "QUDUI built " + t.Value : "QUDUI FAILED " + t.Value);
        }
        Debug.Log("QUDUI done");
    }

    // ------------------------------------------------------------------------------------------ node builder

    static GameObject BuildNode(Dictionary<string, object> n, Transform parent, bool isRoot)
    {
        string name = Str(n, "name") ?? "Node";
        string type = Str(n, "type") ?? "panel";
        var go = new GameObject(name, typeof(RectTransform));
        var rt = go.GetComponent<RectTransform>();
        if (parent != null)
            rt.SetParent(parent, false);
        rt.localScale = Vector3.one;

        ApplyRect(rt, n.ContainsKey("rect") ? n["rect"] as Dictionary<string, object> : null, parent == null);

        if (isRoot)
        {
            go.AddComponent<Canvas>();
            go.AddComponent<GraphicRaycaster>();
            go.AddComponent<CanvasGroup>();
        }

        // fill / image
        string fill = Str(n, "fill");
        bool raycast = Bool(n, "raycast", false);
        if (fill != null || type == "image")
        {
            var img = go.AddComponent<Image>();
            img.color = fill != null ? Hex(fill) : Color.white;
            img.raycastTarget = raycast;
            if (type == "image")
                img.preserveAspect = Bool(n, "preserveAspect", true);
        }

        // layout element
        var el = n.ContainsKey("element") ? n["element"] as Dictionary<string, object> : null;
        if (el != null)
        {
            var le = go.AddComponent<LayoutElement>();
            if (el.ContainsKey("minHeight")) le.minHeight = Num(el, "minHeight");
            if (el.ContainsKey("minWidth")) le.minWidth = Num(el, "minWidth");
            if (el.ContainsKey("preferredHeight")) le.preferredHeight = Num(el, "preferredHeight");
            if (el.ContainsKey("preferredWidth")) le.preferredWidth = Num(el, "preferredWidth");
            if (el.ContainsKey("flexibleHeight")) le.flexibleHeight = Num(el, "flexibleHeight");
            if (el.ContainsKey("flexibleWidth")) le.flexibleWidth = Num(el, "flexibleWidth");
            if (el.ContainsKey("ignoreLayout")) le.ignoreLayout = Bool(el, "ignoreLayout", false);
        }

        // layout group
        var lay = n.ContainsKey("layout") ? n["layout"] as Dictionary<string, object> : null;
        if (lay != null)
        {
            string lt = Str(lay, "type") ?? "vertical";
            var pad = lay.ContainsKey("padding") ? Ints(lay["padding"], 4) : new[] { 0, 0, 0, 0 };
            TextAnchor align = ParseAnchor(Str(lay, "alignment"));
            if (lt == "grid")
            {
                var g = go.AddComponent<GridLayoutGroup>();
                g.padding = new RectOffset(pad[0], pad[1], pad[2], pad[3]);
                var cell = lay.ContainsKey("cell") ? Floats(lay["cell"], 2) : new[] { 40f, 56f };
                var sp = lay.ContainsKey("cellSpacing") ? Floats(lay["cellSpacing"], 2) : new[] { 0f, 0f };
                g.cellSize = new Vector2(cell[0], cell[1]);
                g.spacing = new Vector2(sp[0], sp[1]);
                g.childAlignment = align;
                g.startCorner = GridLayoutGroup.Corner.UpperLeft;
                g.startAxis = GridLayoutGroup.Axis.Horizontal;
                g.constraint = GridLayoutGroup.Constraint.Flexible;
            }
            else
            {
                HorizontalOrVerticalLayoutGroup hv = lt == "horizontal"
                    ? (HorizontalOrVerticalLayoutGroup)go.AddComponent<HorizontalLayoutGroup>()
                    : go.AddComponent<VerticalLayoutGroup>();
                hv.padding = new RectOffset(pad[0], pad[1], pad[2], pad[3]);
                hv.spacing = lay.ContainsKey("spacing") ? Num(lay, "spacing") : 0f;
                hv.childAlignment = align;
                hv.childControlWidth = Bool(lay, "controlWidth", true);
                hv.childControlHeight = Bool(lay, "controlHeight", true);
                hv.childForceExpandWidth = Bool(lay, "expandWidth", false);
                hv.childForceExpandHeight = Bool(lay, "expandHeight", false);
            }
        }

        // fitter
        string fit = Str(n, "fitter");
        if (fit != null)
        {
            var f = go.AddComponent<ContentSizeFitter>();
            f.horizontalFit = (fit == "horizontal" || fit == "both") ? ContentSizeFitter.FitMode.PreferredSize : ContentSizeFitter.FitMode.Unconstrained;
            f.verticalFit = (fit == "vertical" || fit == "both") ? ContentSizeFitter.FitMode.PreferredSize : ContentSizeFitter.FitMode.Unconstrained;
        }

        if (Bool(n, "mask", false))
            go.AddComponent<RectMask2D>();

        // border edges (ignored by layout groups)
        var border = n.ContainsKey("border") ? n["border"] as Dictionary<string, object> : null;
        if (border != null)
        {
            Color c = Hex(Str(border, "color") ?? "#FFFFFFFF");
            float th = border.ContainsKey("thickness") ? Num(border, "thickness") : 1f;
            Edge(rt, "BorderTop", c, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, -th), Vector2.zero);
            Edge(rt, "BorderBottom", c, new Vector2(0f, 0f), new Vector2(1f, 0f), Vector2.zero, new Vector2(0f, th));
            Edge(rt, "BorderLeft", c, new Vector2(0f, 0f), new Vector2(0f, 1f), Vector2.zero, new Vector2(th, 0f));
            Edge(rt, "BorderRight", c, new Vector2(1f, 0f), new Vector2(1f, 1f), new Vector2(-th, 0f), Vector2.zero);
        }

        // children
        var kids = n.ContainsKey("children") ? n["children"] as List<object> : null;
        if (kids != null)
        {
            foreach (object k in kids)
            {
                var kd = k as Dictionary<string, object>;
                if (kd != null)
                    BuildNode(kd, rt, false);
            }
        }

        // scroll rect (after children exist so viewport/content can be resolved)
        if (type == "scroll")
        {
            var sc = n.ContainsKey("scroll") ? n["scroll"] as Dictionary<string, object> : new Dictionary<string, object>();
            var sr = go.AddComponent<ScrollRect>();
            sr.horizontal = Bool(sc, "horizontal", false);
            sr.vertical = Bool(sc, "vertical", true);
            sr.movementType = ScrollRect.MovementType.Clamped;
            sr.inertia = Bool(sc, "inertia", false);
            if (sc.ContainsKey("sensitivity")) sr.scrollSensitivity = Num(sc, "sensitivity");
            string vp = Str(sc, "viewport");
            string ct = Str(sc, "content");
            if (vp != null)
            {
                Transform v = Find(rt, vp);
                if (v != null) sr.viewport = v as RectTransform;
            }
            if (ct != null)
            {
                Transform c = Find(rt, ct);
                if (c != null) sr.content = c as RectTransform;
                else Debug.LogWarning("QUDUI warning: scroll content '" + ct + "' not found under " + name);
            }
        }

        if (!Bool(n, "active", true))
            go.SetActive(false);
        return go;
    }

    static void ApplyRect(RectTransform rt, Dictionary<string, object> r, bool isRoot)
    {
        if (r == null)
        {
            if (isRoot)
                Stretch(rt, 0, 0, 0, 0);
            return;
        }
        if (r.ContainsKey("stretch"))
        {
            var v = Floats(r["stretch"], 4);
            Stretch(rt, v[0], v[1], v[2], v[3]);
        }
        else if (r.ContainsKey("anchors"))
        {
            var v = Floats(r["anchors"], 4);
            rt.anchorMin = new Vector2(v[0], v[1]);
            rt.anchorMax = new Vector2(v[2], v[3]);
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
        }
        else if (r.ContainsKey("top"))
        {
            var v = Floats(r["top"], 3);
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.offsetMin = new Vector2(v[2], -(v[0] + v[1]));
            rt.offsetMax = new Vector2(-v[2], -v[0]);
        }
        else if (r.ContainsKey("bottom"))
        {
            var v = Floats(r["bottom"], 3);
            rt.anchorMin = new Vector2(0f, 0f);
            rt.anchorMax = new Vector2(1f, 0f);
            rt.pivot = new Vector2(0.5f, 0f);
            rt.offsetMin = new Vector2(v[2], v[0]);
            rt.offsetMax = new Vector2(-v[2], v[0] + v[1]);
        }
        else if (r.ContainsKey("left"))
        {
            var v = Floats(r["left"], 2);
            rt.anchorMin = new Vector2(0f, 0f);
            rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 0.5f);
            rt.offsetMin = new Vector2(v[0], 0f);
            rt.offsetMax = new Vector2(v[0] + v[1], 0f);
        }
        else if (r.ContainsKey("right"))
        {
            var v = Floats(r["right"], 2);
            rt.anchorMin = new Vector2(1f, 0f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(1f, 0.5f);
            rt.offsetMin = new Vector2(-(v[0] + v[1]), 0f);
            rt.offsetMax = new Vector2(-v[0], 0f);
        }
        else if (r.ContainsKey("topStretch"))
        {
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            rt.sizeDelta = Vector2.zero;
        }
        else if (r.ContainsKey("size"))
        {
            var size = Floats(r["size"], 2);
            var anchor = r.ContainsKey("anchor") ? Floats(r["anchor"], 2) : new[] { 0.5f, 0.5f };
            var pivot = r.ContainsKey("pivot") ? Floats(r["pivot"], 2) : new[] { 0.5f, 0.5f };
            var pos = r.ContainsKey("pos") ? Floats(r["pos"], 2) : new[] { 0f, 0f };
            rt.anchorMin = rt.anchorMax = new Vector2(anchor[0], anchor[1]);
            rt.pivot = new Vector2(pivot[0], pivot[1]);
            rt.sizeDelta = new Vector2(size[0], size[1]);
            rt.anchoredPosition = new Vector2(pos[0], pos[1]);
        }
    }

    static void Stretch(RectTransform rt, float left, float bottom, float right, float top)
    {
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = new Vector2(left, bottom);
        rt.offsetMax = new Vector2(-right, -top);
    }

    static void Edge(RectTransform parent, string name, Color color, Vector2 anchorMin, Vector2 anchorMax, Vector2 offsetMin, Vector2 offsetMax)
    {
        var go = new GameObject(name, typeof(RectTransform));
        var rt = go.GetComponent<RectTransform>();
        rt.SetParent(parent, false);
        rt.localScale = Vector3.one;
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.offsetMin = offsetMin;
        rt.offsetMax = offsetMax;
        var le = go.AddComponent<LayoutElement>();
        le.ignoreLayout = true;
        var img = go.AddComponent<Image>();
        img.color = color;
        img.raycastTarget = false;
    }

    static Transform Find(Transform root, string name)
    {
        if (root == null) return null;
        for (int i = 0; i < root.childCount; i++)
        {
            Transform c = root.GetChild(i);
            if (c.name == name) return c;
            Transform hit = Find(c, name);
            if (hit != null) return hit;
        }
        return null;
    }

    static int CountNodes(Dictionary<string, object> n)
    {
        int count = 1;
        var kids = n.ContainsKey("children") ? n["children"] as List<object> : null;
        if (kids != null)
            foreach (object k in kids)
                if (k is Dictionary<string, object> kd)
                    count += CountNodes(kd);
        return count;
    }

    // ------------------------------------------------------------------------------------------ value helpers

    static string Str(Dictionary<string, object> d, string key)
    {
        object v;
        return d != null && d.TryGetValue(key, out v) && v != null ? v.ToString() : null;
    }

    static bool Bool(Dictionary<string, object> d, string key, bool def)
    {
        object v;
        if (d == null || !d.TryGetValue(key, out v) || v == null) return def;
        if (v is bool b) return b;
        bool parsed;
        return bool.TryParse(v.ToString(), out parsed) ? parsed : def;
    }

    static float Num(Dictionary<string, object> d, string key)
    {
        object v;
        if (d == null || !d.TryGetValue(key, out v) || v == null) return 0f;
        return Convert.ToSingle(v, CultureInfo.InvariantCulture);
    }

    static float[] Floats(object v, int n)
    {
        var list = v as List<object>;
        var r = new float[n];
        if (list == null) return r;
        for (int i = 0; i < n && i < list.Count; i++)
            r[i] = Convert.ToSingle(list[i], CultureInfo.InvariantCulture);
        return r;
    }

    static int[] Ints(object v, int n)
    {
        var f = Floats(v, n);
        var r = new int[n];
        for (int i = 0; i < n; i++) r[i] = Mathf.RoundToInt(f[i]);
        return r;
    }

    static Color Hex(string s)
    {
        if (string.IsNullOrEmpty(s) || s[0] != '#' || (s.Length != 7 && s.Length != 9))
            return Color.magenta;
        float r = int.Parse(s.Substring(1, 2), NumberStyles.HexNumber) / 255f;
        float g = int.Parse(s.Substring(3, 2), NumberStyles.HexNumber) / 255f;
        float b = int.Parse(s.Substring(5, 2), NumberStyles.HexNumber) / 255f;
        float a = s.Length == 9 ? int.Parse(s.Substring(7, 2), NumberStyles.HexNumber) / 255f : 1f;
        return new Color(r, g, b, a);
    }

    static TextAnchor ParseAnchor(string s)
    {
        if (string.IsNullOrEmpty(s)) return TextAnchor.UpperLeft;
        try { return (TextAnchor)Enum.Parse(typeof(TextAnchor), s); }
        catch { return TextAnchor.UpperLeft; }
    }

    static string Arg(string name)
    {
        string[] args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == name)
                return args[i + 1];
        return null;
    }

    // ------------------------------------------------------------------------------------------ tiny JSON parser
    // Objects -> Dictionary<string, object>, arrays -> List<object>, numbers -> double, plus string/bool/null.
    static class MiniJson
    {
        public static object Parse(string json)
        {
            int i = 0;
            object v = ParseValue(json, ref i);
            SkipWs(json, ref i);
            if (i != json.Length) throw new Exception("trailing characters at " + i);
            return v;
        }

        static void SkipWs(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object ParseValue(string s, ref int i)
        {
            SkipWs(s, ref i);
            if (i >= s.Length) throw new Exception("unexpected end");
            char c = s[i];
            if (c == '{') return ParseObject(s, ref i);
            if (c == '[') return ParseArray(s, ref i);
            if (c == '"') return ParseString(s, ref i);
            if (c == 't' && s.Substring(i, 4) == "true") { i += 4; return true; }
            if (c == 'f' && s.Substring(i, 5) == "false") { i += 5; return false; }
            if (c == 'n' && s.Substring(i, 4) == "null") { i += 4; return null; }
            return ParseNumber(s, ref i);
        }

        static Dictionary<string, object> ParseObject(string s, ref int i)
        {
            var d = new Dictionary<string, object>();
            i++; // {
            SkipWs(s, ref i);
            if (s[i] == '}') { i++; return d; }
            while (true)
            {
                SkipWs(s, ref i);
                string key = ParseString(s, ref i);
                SkipWs(s, ref i);
                if (s[i] != ':') throw new Exception("expected ':' at " + i);
                i++;
                d[key] = ParseValue(s, ref i);
                SkipWs(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return d; }
                throw new Exception("expected ',' or '}' at " + i);
            }
        }

        static List<object> ParseArray(string s, ref int i)
        {
            var l = new List<object>();
            i++; // [
            SkipWs(s, ref i);
            if (s[i] == ']') { i++; return l; }
            while (true)
            {
                l.Add(ParseValue(s, ref i));
                SkipWs(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return l; }
                throw new Exception("expected ',' or ']' at " + i);
            }
        }

        static string ParseString(string s, ref int i)
        {
            if (s[i] != '"') throw new Exception("expected string at " + i);
            i++;
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c == '\\')
                {
                    char e = s[i++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            sb.Append((char)int.Parse(s.Substring(i, 4), NumberStyles.HexNumber));
                            i += 4;
                            break;
                        default: throw new Exception("bad escape at " + i);
                    }
                }
                else sb.Append(c);
            }
            throw new Exception("unterminated string");
        }

        static object ParseNumber(string s, ref int i)
        {
            int start = i;
            while (i < s.Length && ("+-0123456789.eE".IndexOf(s[i]) >= 0)) i++;
            string num = s.Substring(start, i - start);
            double d;
            if (!double.TryParse(num, NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                throw new Exception("bad number '" + num + "' at " + start);
            return d;
        }
    }
}
