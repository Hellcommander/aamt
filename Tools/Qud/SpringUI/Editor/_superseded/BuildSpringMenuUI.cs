using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

// Builds the shared Spring Molting list-window prefab for the Arendeth_SpringUI library mod and packs it
// into one asset bundle per platform. Run from the command line (Build-SpringUIBundle.ps1 does this):
//
//   Unity.exe -batchmode -nographics -quit -projectPath <staged project> -executeMethod BuildSpringMenuUI.Build
//             -out <mod>/Bundles [-bundle arendeth_springui] [-regenerate]
//
// The prefab (Assets/SpringUI/SpringMenu.prefab) is generated from code the first time or with -regenerate;
// afterwards open the staged project in the Unity editor and tune the layout by hand (Qud > Spring UI menu).
// Keep the object NAMES: the mod's SpringMenuWindow.cs looks them up and attaches the game's own UI components
// (TextMeshPro + UITextSkin, FrameworkScroller, UIThreeColorProperties, ...) at runtime. Only plain uGUI goes
// into the prefab, so the bundle has no dependency on the game's assemblies or on a TextMeshPro version.
public static class BuildSpringMenuUI
{
    const string PrefabDir = "Assets/SpringUI";
    const string PrefabPath = PrefabDir + "/SpringMenu.prefab";
    const string DefaultBundle = "arendeth_springui";

    // Qud-ish palette: dark umber/teal panels, pale borders, 'W' yellow highlight.
    static readonly Color Backdrop = new Color(0f, 0f, 0f, 0.84f);
    static readonly Color FrameFill = new Color(0.045f, 0.05f, 0.055f, 0.98f);
    static readonly Color PanelFill = new Color(0.07f, 0.085f, 0.09f, 1f);
    static readonly Color PanelBorder = new Color(0.36f, 0.45f, 0.44f, 1f);
    static readonly Color StatusFill = new Color(0.10f, 0.12f, 0.13f, 1f);
    static readonly Color RowSelect = new Color(1f, 1f, 0f, 0.16f);
    static readonly Color RowSelectEdge = new Color(1f, 1f, 0f, 0.9f);
    static readonly Color Transparent = new Color(0f, 0f, 0f, 0f);

    // ------------------------------------------------------------------------------------------

    public static void Build()
    {
        string outDir = Arg("-out") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Bundles"));
        string bundle = Arg("-bundle") ?? DefaultBundle;
        bool regenerate = HasFlag("-regenerate");
        Directory.CreateDirectory(outDir);

        if (regenerate || !File.Exists(PrefabPath))
        {
            Debug.Log(regenerate ? "SPRINGUI regenerating prefab" : "SPRINGUI prefab missing, generating");
            GeneratePrefab();
        }
        else
        {
            Debug.Log("SPRINGUI using existing prefab " + PrefabPath + " (pass -regenerate to rebuild it from code)");
        }

        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        if (prefab == null)
        {
            Debug.LogError("SPRINGUI error: could not load " + PrefabPath);
            return;
        }
        string check = Validate(prefab);
        if (check != null)
        {
            Debug.LogError("SPRINGUI error: prefab is missing required objects: " + check);
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
                Debug.Log("SPRINGUI skipping " + t.Value + ": that build support isn't installed in Unity Hub.");
                continue;
            }
            string dir = Path.Combine(outDir, t.Value);
            Directory.CreateDirectory(dir);
            var b = new AssetBundleBuild { assetBundleName = bundle + "_" + t.Value, assetNames = new[] { PrefabPath } };
            var manifest = BuildPipeline.BuildAssetBundles(dir, new[] { b },
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode, t.Key);
            Debug.Log(manifest != null ? "SPRINGUI built " + t.Value : "SPRINGUI FAILED " + t.Value);
        }
        Debug.Log("SPRINGUI done");
    }

    [MenuItem("Qud/Spring UI/Regenerate SpringMenu prefab from code")]
    public static void GeneratePrefab()
    {
        GameObject root = BuildHierarchy();
        Directory.CreateDirectory(PrefabDir);
        PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        UnityEngine.Object.DestroyImmediate(root);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("SPRINGUI prefab written to " + PrefabPath);
    }

    [MenuItem("Qud/Spring UI/Validate SpringMenu prefab")]
    public static void ValidateMenu()
    {
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        string check = prefab == null ? "prefab not found" : Validate(prefab);
        Debug.Log(check == null ? "SPRINGUI prefab OK" : "SPRINGUI prefab problem: " + check);
    }

    static readonly string[] RequiredNames =
    {
        "TitleText", "StatusText", "Body",
        "HeaderScroll", "HeaderViewport", "HeaderContent", "HeaderText",
        "ListScroll", "ListViewport", "ListContent",
        "DetailScroll", "DetailViewport", "DetailContent", "DetailText",
        "HotkeyBar", "HotkeyContent", "HintText",
        "Templates", "RowTemplate", "Selection", "HotkeySlot", "HotkeyText", "IconSlot", "Icon", "LabelText", "SecondaryText"
    };

    static string Validate(GameObject prefab)
    {
        var missing = new List<string>();
        foreach (string name in RequiredNames)
            if (Find(prefab.transform, name) == null)
                missing.Add(name);
        if (missing.Count > 0)
            return string.Join(", ", missing.ToArray());
        if (Find(prefab.transform, "ListScroll").GetComponent<ScrollRect>() == null) return "ListScroll has no ScrollRect";
        if (Find(prefab.transform, "DetailScroll").GetComponent<ScrollRect>() == null) return "DetailScroll has no ScrollRect";
        if (Find(prefab.transform, "HeaderScroll").GetComponent<ScrollRect>() == null) return "HeaderScroll has no ScrollRect";
        if (Find(prefab.transform, "HotkeyBar").GetComponent<ScrollRect>() == null) return "HotkeyBar has no ScrollRect";
        if (Find(prefab.transform, "ListContent").GetComponent<VerticalLayoutGroup>() == null) return "ListContent has no VerticalLayoutGroup";
        return null;
    }

    // ------------------------------------------------------------------------------------------
    // Hierarchy
    // ------------------------------------------------------------------------------------------

    static GameObject BuildHierarchy()
    {
        RectTransform root = Rect("SpringMenu", null);
        Stretch(root, 0, 0, 0, 0);
        root.gameObject.AddComponent<Canvas>();
        root.gameObject.AddComponent<GraphicRaycaster>();
        root.gameObject.AddComponent<CanvasGroup>();
        Img(root, Backdrop, true);

        RectTransform frame = Rect("Frame", root);
        Anchors(frame, 0.08f, 0.06f, 0.92f, 0.94f);
        Img(frame, FrameFill, true);
        Border(frame, PanelBorder, 2f);

        // ---- Title + status -------------------------------------------------------------------
        RectTransform title = Rect("TitleText", frame);
        TopBand(title, 8f, 40f, 16f);

        RectTransform status = Rect("StatusText", frame);
        TopBand(status, 50f, 26f, 16f);
        Image statusBg = Img(status, StatusFill, false);
        statusBg.raycastTarget = false;

        // ---- Body -----------------------------------------------------------------------------
        RectTransform body = Rect("Body", frame);
        Stretch(body, 16f, 70f, 16f, 84f);

        // Left column: header block (capped at runtime) over the list.
        RectTransform left = Rect("LeftPanel", body);
        Anchors(left, 0f, 0f, 0.58f, 1f);
        var leftLayout = left.gameObject.AddComponent<VerticalLayoutGroup>();
        leftLayout.spacing = 8f;
        leftLayout.childControlWidth = true;
        leftLayout.childControlHeight = true;
        leftLayout.childForceExpandWidth = true;
        leftLayout.childForceExpandHeight = false;

        RectTransform headerScroll = Rect("HeaderScroll", left);
        var headerLE = headerScroll.gameObject.AddComponent<LayoutElement>();
        headerLE.preferredHeight = 120f;
        headerLE.flexibleHeight = 0f;
        Img(headerScroll, PanelFill, false);
        Border(headerScroll, PanelBorder, 1f);
        var headerRect = headerScroll.gameObject.AddComponent<ScrollRect>();
        headerRect.horizontal = false;
        headerRect.vertical = true;
        headerRect.movementType = ScrollRect.MovementType.Clamped;
        headerRect.inertia = false;
        RectTransform headerViewport = Rect("HeaderViewport", headerScroll);
        Stretch(headerViewport, 2f, 2f, 2f, 2f);
        Img(headerViewport, Transparent, true);
        headerViewport.gameObject.AddComponent<RectMask2D>();
        RectTransform headerContent = Rect("HeaderContent", headerViewport);
        TopStretch(headerContent);
        var headerVL = headerContent.gameObject.AddComponent<VerticalLayoutGroup>();
        headerVL.padding = new RectOffset(10, 10, 8, 8);
        headerVL.childControlWidth = true;
        headerVL.childControlHeight = true;
        headerVL.childForceExpandWidth = true;
        headerVL.childForceExpandHeight = false;
        var headerFit = headerContent.gameObject.AddComponent<ContentSizeFitter>();
        headerFit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        RectTransform headerText = Rect("HeaderText", headerContent);
        TopStretch(headerText);
        headerRect.viewport = headerViewport;
        headerRect.content = headerContent;

        RectTransform listScroll = Rect("ListScroll", left);
        var listLE = listScroll.gameObject.AddComponent<LayoutElement>();
        listLE.flexibleHeight = 1f;
        listLE.minHeight = 120f;
        Img(listScroll, PanelFill, false);
        Border(listScroll, PanelBorder, 1f);
        var listRect = listScroll.gameObject.AddComponent<ScrollRect>();
        listRect.horizontal = false;
        listRect.vertical = true;
        listRect.movementType = ScrollRect.MovementType.Clamped;
        listRect.scrollSensitivity = 20f;
        listRect.inertia = false;
        RectTransform listViewport = Rect("ListViewport", listScroll);
        Stretch(listViewport, 2f, 2f, 2f, 2f);
        Img(listViewport, Transparent, true);
        listViewport.gameObject.AddComponent<RectMask2D>();
        RectTransform listContent = Rect("ListContent", listViewport);
        TopStretch(listContent);
        var listVL = listContent.gameObject.AddComponent<VerticalLayoutGroup>();
        listVL.padding = new RectOffset(6, 6, 6, 6);
        listVL.spacing = 2f;
        listVL.childControlWidth = true;
        listVL.childControlHeight = true;
        listVL.childForceExpandWidth = true;
        listVL.childForceExpandHeight = false;
        var listFit = listContent.gameObject.AddComponent<ContentSizeFitter>();
        listFit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        listRect.viewport = listViewport;
        listRect.content = listContent;

        // Right column: detail pane.
        RectTransform detailPanel = Rect("DetailPanel", body);
        Anchors(detailPanel, 0.595f, 0f, 1f, 1f);
        Img(detailPanel, PanelFill, false);
        Border(detailPanel, PanelBorder, 1f);
        RectTransform detailScroll = Rect("DetailScroll", detailPanel);
        Stretch(detailScroll, 4f, 4f, 4f, 4f);
        var detailRect = detailScroll.gameObject.AddComponent<ScrollRect>();
        detailRect.horizontal = false;
        detailRect.vertical = true;
        detailRect.movementType = ScrollRect.MovementType.Clamped;
        detailRect.scrollSensitivity = 25f;
        detailRect.inertia = false;
        RectTransform detailViewport = Rect("DetailViewport", detailScroll);
        Stretch(detailViewport, 0, 0, 0, 0);
        Img(detailViewport, Transparent, true);
        detailViewport.gameObject.AddComponent<RectMask2D>();
        RectTransform detailContent = Rect("DetailContent", detailViewport);
        TopStretch(detailContent);
        var detailVL = detailContent.gameObject.AddComponent<VerticalLayoutGroup>();
        detailVL.padding = new RectOffset(12, 12, 10, 10);
        detailVL.childControlWidth = true;
        detailVL.childControlHeight = true;
        detailVL.childForceExpandWidth = true;
        detailVL.childForceExpandHeight = false;
        var detailFit = detailContent.gameObject.AddComponent<ContentSizeFitter>();
        detailFit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        RectTransform detailText = Rect("DetailText", detailContent);
        TopStretch(detailText);
        detailRect.viewport = detailViewport;
        detailRect.content = detailContent;

        // ---- Footer ---------------------------------------------------------------------------
        RectTransform footer = Rect("Footer", frame);
        BottomBand(footer, 10f, 52f, 16f);
        RectTransform hotkeyBar = Rect("HotkeyBar", footer);
        Anchors(hotkeyBar, 0f, 0f, 0.75f, 1f);
        hotkeyBar.gameObject.AddComponent<LayoutElement>();
        var barRect = hotkeyBar.gameObject.AddComponent<ScrollRect>();
        barRect.horizontal = false;
        barRect.vertical = false;
        barRect.movementType = ScrollRect.MovementType.Clamped;
        barRect.inertia = false;
        RectTransform hotkeyContent = Rect("HotkeyContent", hotkeyBar);
        Stretch(hotkeyContent, 0, 0, 0, 0);
        var barLayout = hotkeyContent.gameObject.AddComponent<HorizontalLayoutGroup>();
        barLayout.padding = new RectOffset(8, 8, 4, 4);
        barLayout.spacing = 28f;
        barLayout.childAlignment = TextAnchor.MiddleLeft;
        barLayout.childControlWidth = true;
        barLayout.childControlHeight = true;
        barLayout.childForceExpandWidth = false;
        barLayout.childForceExpandHeight = false;
        barRect.content = hotkeyContent;
        RectTransform hint = Rect("HintText", footer);
        Anchors(hint, 0.75f, 0f, 1f, 1f);
        hint.offsetMax = new Vector2(-8f, 0f);

        // ---- Row template (inactive container, active template) ---------------------------------
        RectTransform templates = Rect("Templates", root);
        Stretch(templates, 0, 0, 0, 0);
        templates.gameObject.SetActive(false);

        RectTransform row = Rect("RowTemplate", templates);
        row.anchorMin = new Vector2(0f, 1f);
        row.anchorMax = new Vector2(1f, 1f);
        row.pivot = new Vector2(0.5f, 1f);
        row.sizeDelta = new Vector2(0f, 32f);
        var rowLE = row.gameObject.AddComponent<LayoutElement>();
        rowLE.minHeight = 30f;
        rowLE.flexibleWidth = 1f;
        Image rowHit = Img(row, Transparent, true);
        rowHit.raycastTarget = true;
        var rowHL = row.gameObject.AddComponent<HorizontalLayoutGroup>();
        rowHL.padding = new RectOffset(8, 8, 3, 3);
        rowHL.spacing = 8f;
        rowHL.childAlignment = TextAnchor.MiddleLeft;
        rowHL.childControlWidth = true;
        rowHL.childControlHeight = true;
        rowHL.childForceExpandWidth = false;
        rowHL.childForceExpandHeight = false;

        RectTransform selection = Rect("Selection", row);
        Stretch(selection, 0, 0, 0, 0);
        var selLE = selection.gameObject.AddComponent<LayoutElement>();
        selLE.ignoreLayout = true;
        Image selImg = Img(selection, RowSelect, false);
        selImg.raycastTarget = false;
        Edge(selection, "SelectionEdge", RowSelectEdge, new Vector2(0f, 0f), new Vector2(0f, 1f), Vector2.zero, new Vector2(3f, 0f));
        selection.gameObject.SetActive(false);

        RectTransform hotkeySlot = Rect("HotkeySlot", row);
        var hkLE = hotkeySlot.gameObject.AddComponent<LayoutElement>();
        hkLE.preferredWidth = 34f;
        hkLE.minWidth = 34f;
        RectTransform hotkeyText = Rect("HotkeyText", hotkeySlot);
        Stretch(hotkeyText, 0, 0, 0, 0);

        RectTransform iconSlot = Rect("IconSlot", row);
        var iconLE = iconSlot.gameObject.AddComponent<LayoutElement>();
        iconLE.preferredWidth = 22f;
        iconLE.minWidth = 22f;
        iconLE.preferredHeight = 30f;
        RectTransform icon = Rect("Icon", iconSlot);
        Stretch(icon, 0, 0, 0, 0);
        Image iconImg = Img(icon, Color.white, false);
        iconImg.preserveAspect = true;

        RectTransform textColumn = Rect("TextColumn", row);
        var textLE = textColumn.gameObject.AddComponent<LayoutElement>();
        textLE.flexibleWidth = 1f;
        var textVL = textColumn.gameObject.AddComponent<VerticalLayoutGroup>();
        textVL.spacing = 0f;
        textVL.childControlWidth = true;
        textVL.childControlHeight = true;
        textVL.childForceExpandWidth = true;
        textVL.childForceExpandHeight = false;
        RectTransform label = Rect("LabelText", textColumn);
        TopStretch(label);
        RectTransform secondary = Rect("SecondaryText", textColumn);
        TopStretch(secondary);

        return root.gameObject;
    }

    // ------------------------------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------------------------------

    static RectTransform Rect(string name, Transform parent)
    {
        var go = new GameObject(name, typeof(RectTransform));
        var rt = go.GetComponent<RectTransform>();
        if (parent != null)
            rt.SetParent(parent, false);
        rt.localScale = Vector3.one;
        return rt;
    }

    static Image Img(RectTransform rt, Color color, bool raycast)
    {
        var img = rt.gameObject.AddComponent<Image>();
        img.color = color;
        img.raycastTarget = raycast;
        return img;
    }

    static void Anchors(RectTransform rt, float minX, float minY, float maxX, float maxY)
    {
        rt.anchorMin = new Vector2(minX, minY);
        rt.anchorMax = new Vector2(maxX, maxY);
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
    }

    static void Stretch(RectTransform rt, float left, float bottom, float right, float top)
    {
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = new Vector2(left, bottom);
        rt.offsetMax = new Vector2(-right, -top);
    }

    static void TopBand(RectTransform rt, float fromTop, float height, float sideMargin)
    {
        rt.anchorMin = new Vector2(0f, 1f);
        rt.anchorMax = new Vector2(1f, 1f);
        rt.pivot = new Vector2(0.5f, 1f);
        rt.offsetMin = new Vector2(sideMargin, -(fromTop + height));
        rt.offsetMax = new Vector2(-sideMargin, -fromTop);
    }

    static void BottomBand(RectTransform rt, float fromBottom, float height, float sideMargin)
    {
        rt.anchorMin = new Vector2(0f, 0f);
        rt.anchorMax = new Vector2(1f, 0f);
        rt.pivot = new Vector2(0.5f, 0f);
        rt.offsetMin = new Vector2(sideMargin, fromBottom);
        rt.offsetMax = new Vector2(-sideMargin, fromBottom + height);
    }

    static void TopStretch(RectTransform rt)
    {
        rt.anchorMin = new Vector2(0f, 1f);
        rt.anchorMax = new Vector2(1f, 1f);
        rt.pivot = new Vector2(0.5f, 1f);
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
        rt.sizeDelta = Vector2.zero;
    }

    static void Border(RectTransform parent, Color color, float thickness)
    {
        Edge(parent, "BorderTop", color, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, -thickness), Vector2.zero);
        Edge(parent, "BorderBottom", color, new Vector2(0f, 0f), new Vector2(1f, 0f), Vector2.zero, new Vector2(0f, thickness));
        Edge(parent, "BorderLeft", color, new Vector2(0f, 0f), new Vector2(0f, 1f), Vector2.zero, new Vector2(thickness, 0f));
        Edge(parent, "BorderRight", color, new Vector2(1f, 0f), new Vector2(1f, 1f), new Vector2(-thickness, 0f), Vector2.zero);
    }

    static void Edge(RectTransform parent, string name, Color color, Vector2 anchorMin, Vector2 anchorMax, Vector2 offsetMin, Vector2 offsetMax)
    {
        RectTransform rt = Rect(name, parent);
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.offsetMin = offsetMin;
        rt.offsetMax = offsetMax;
        var le = rt.gameObject.AddComponent<LayoutElement>();
        le.ignoreLayout = true;
        Image img = Img(rt, color, false);
        img.raycastTarget = false;
    }

    static Transform Find(Transform root, string name)
    {
        if (root == null)
            return null;
        if (root.name == name)
            return root;
        for (int i = 0; i < root.childCount; i++)
        {
            Transform hit = Find(root.GetChild(i), name);
            if (hit != null)
                return hit;
        }
        return null;
    }

    static string Arg(string name)
    {
        string[] args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == name)
                return args[i + 1];
        return null;
    }

    static bool HasFlag(string name)
    {
        foreach (string a in Environment.GetCommandLineArgs())
            if (a == name)
                return true;
        return false;
    }
}
