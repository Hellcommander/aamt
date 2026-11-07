using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

// Builds the Spring Molting UI picker prefab for the Conjoined Extended mod and packs it into one
// asset bundle per platform. Run from the command line (Build-ConjoinedUIBundle.ps1 does this):
//
//   Unity.exe -batchmode -nographics -quit -projectPath <staged project> -executeMethod BuildConjoinedUI.Build
//             -out <mod>/Bundles [-bundle conjoined_ui] [-regenerate]
//
// The prefab (Assets/ConjoinedUI/ConjoinedPicker.prefab) is generated from code the first time, or
// whenever -regenerate is passed; after that you can open the staged project in the Unity editor
// and tweak the layout by hand (Qud > Conjoined UI menu has the same commands). Keep the object
// NAMES: the mod's UI/ConjoinedPickerScreen.cs looks them up and attaches the game's own UI
// components (TextMeshPro + UITextSkin, FrameworkScroller, UIThreeColorProperties, ...) at runtime.
// Only plain uGUI components (RectTransform, Image, ScrollRect, layout groups) go into the prefab,
// so the bundle has no dependency on the game's assemblies or on a TextMeshPro version.
public static class BuildConjoinedUI
{
    const string PrefabDir = "Assets/ConjoinedUI";
    const string PrefabPath = PrefabDir + "/ConjoinedPicker.prefab";
    const string DefaultBundle = "conjoined_ui";

    // Qud-ish palette (dark teal panels, pale borders, 'W' yellow highlight).
    static readonly Color Backdrop = new Color(0f, 0f, 0f, 0.86f);
    static readonly Color FrameFill = new Color(0.035f, 0.055f, 0.065f, 0.98f);
    static readonly Color PanelFill = new Color(0.055f, 0.085f, 0.095f, 1f);
    static readonly Color PanelBorder = new Color(0.33f, 0.47f, 0.47f, 1f);
    static readonly Color SearchFill = new Color(0.10f, 0.14f, 0.16f, 1f);
    static readonly Color Highlight = new Color(1f, 1f, 0f, 1f);
    static readonly Color BadgeFill = new Color(0.75f, 0.18f, 0.18f, 1f);
    static readonly Color Transparent = new Color(0f, 0f, 0f, 0f);

    public static readonly Vector2 TileSize = new Vector2(40f, 56f);

    // ------------------------------------------------------------------------------------------
    // Entry points
    // ------------------------------------------------------------------------------------------

    public static void Build()
    {
        string outDir = Arg("-out") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Bundles"));
        string bundle = Arg("-bundle") ?? DefaultBundle;
        bool regenerate = HasFlag("-regenerate");
        Directory.CreateDirectory(outDir);

        if (regenerate || !File.Exists(PrefabPath))
        {
            Debug.Log(regenerate ? "CONJUI regenerating prefab" : "CONJUI prefab missing, generating");
            GeneratePrefab();
        }
        else
        {
            Debug.Log("CONJUI using existing prefab " + PrefabPath + " (pass -regenerate to rebuild it from code)");
        }

        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        if (prefab == null)
        {
            Debug.LogError("CONJUI error: could not load " + PrefabPath);
            return;
        }
        string check = Validate(prefab);
        if (check != null)
        {
            Debug.LogError("CONJUI error: prefab is missing required objects: " + check);
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
                Debug.Log("CONJUI skipping " + t.Value + ": that build support isn't installed in Unity Hub.");
                continue;
            }
            string dir = Path.Combine(outDir, t.Value);
            Directory.CreateDirectory(dir);
            var b = new AssetBundleBuild { assetBundleName = bundle + "_" + t.Value, assetNames = new[] { PrefabPath } };
            var manifest = BuildPipeline.BuildAssetBundles(dir, new[] { b },
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode, t.Key);
            Debug.Log(manifest != null ? "CONJUI built " + t.Value : "CONJUI FAILED " + t.Value);
        }
        Debug.Log("CONJUI done");
    }

    [MenuItem("Qud/Conjoined UI/Regenerate picker prefab from code")]
    public static void GeneratePrefab()
    {
        GameObject root = BuildHierarchy();
        Directory.CreateDirectory(PrefabDir);
        PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        UnityEngine.Object.DestroyImmediate(root);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("CONJUI prefab written to " + PrefabPath);
    }

    [MenuItem("Qud/Conjoined UI/Validate picker prefab")]
    public static void ValidateMenu()
    {
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        string check = prefab == null ? "prefab not found" : Validate(prefab);
        Debug.Log(check == null ? "CONJUI prefab OK" : "CONJUI prefab problem: " + check);
    }

    // The runtime looks these up by name. Keep in sync with UI/ConjoinedPickerScreen.cs.
    static readonly string[] RequiredNames =
    {
        "TitleText", "PromptText", "ChosenRow", "SearchBar", "SearchText",
        "GridScroll", "GridViewport", "GridContent",
        "DetailScroll", "DetailViewport", "DetailContent", "DetailText",
        "HotkeyBar", "HotkeyContent", "StatusText",
        "Templates", "TileTemplate", "Icon", "Frame", "Badge", "BadgeText"
    };

    static string Validate(GameObject prefab)
    {
        var missing = new List<string>();
        foreach (string name in RequiredNames)
        {
            if (Find(prefab.transform, name) == null)
                missing.Add(name);
        }
        if (missing.Count > 0)
            return string.Join(", ", missing.ToArray());
        if (Find(prefab.transform, "GridScroll").GetComponent<ScrollRect>() == null)
            return "GridScroll has no ScrollRect";
        if (Find(prefab.transform, "GridContent").GetComponent<GridLayoutGroup>() == null)
            return "GridContent has no GridLayoutGroup";
        if (Find(prefab.transform, "DetailScroll").GetComponent<ScrollRect>() == null)
            return "DetailScroll has no ScrollRect";
        if (Find(prefab.transform, "HotkeyBar").GetComponent<ScrollRect>() == null)
            return "HotkeyBar has no ScrollRect";
        return null;
    }

    // ------------------------------------------------------------------------------------------
    // Hierarchy
    // ------------------------------------------------------------------------------------------

    static GameObject BuildHierarchy()
    {
        // Root: full-screen window (the mod also adds Canvas/GraphicRaycaster/CanvasGroup if missing).
        RectTransform root = Rect("ConjoinedPicker", null);
        Stretch(root, 0, 0, 0, 0);
        root.gameObject.AddComponent<Canvas>();
        root.gameObject.AddComponent<GraphicRaycaster>();
        root.gameObject.AddComponent<CanvasGroup>();
        Img(root, Backdrop, true);

        // Frame: the dialog body with safe margins.
        RectTransform frame = Rect("Frame", root);
        Anchors(frame, 0.03f, 0.04f, 0.97f, 0.96f);
        Img(frame, FrameFill, true);
        Border(frame, PanelBorder, 2f);

        // ---- Header -------------------------------------------------------------------------
        RectTransform header = Rect("Header", frame);
        TopBand(header, 0f, 140f, 16f);

        RectTransform title = Rect("TitleText", header);
        TopBand(title, 0f, 42f, 0f);

        RectTransform prompt = Rect("PromptText", header);
        TopBand(prompt, 44f, 30f, 0f);

        RectTransform chosenRow = Rect("ChosenRow", header);
        TopBand(chosenRow, 78f, TileSize.y + 6f, 0f);
        var chosenLayout = chosenRow.gameObject.AddComponent<HorizontalLayoutGroup>();
        chosenLayout.childAlignment = TextAnchor.MiddleCenter;
        chosenLayout.spacing = 8f;
        chosenLayout.childControlWidth = false;
        chosenLayout.childControlHeight = false;
        chosenLayout.childForceExpandWidth = false;
        chosenLayout.childForceExpandHeight = false;

        // ---- Body ---------------------------------------------------------------------------
        RectTransform body = Rect("Body", frame);
        Stretch(body, 16f, 70f, 16f, 160f);

        // Grid panel (left ~64%).
        RectTransform gridPanel = Rect("GridPanel", body);
        Anchors(gridPanel, 0f, 0f, 0.64f, 1f);
        Img(gridPanel, PanelFill, false);
        Border(gridPanel, PanelBorder, 1f);

        RectTransform searchBar = Rect("SearchBar", gridPanel);
        TopBand(searchBar, 6f, 34f, 6f);
        Img(searchBar, SearchFill, true);
        Border(searchBar, PanelBorder, 1f);
        var searchButton = searchBar.gameObject.AddComponent<Button>();
        searchButton.transition = Selectable.Transition.None;
        RectTransform searchText = Rect("SearchText", searchBar);
        Stretch(searchText, 10f, 2f, 10f, 2f);

        RectTransform gridScroll = Rect("GridScroll", gridPanel);
        Stretch(gridScroll, 6f, 6f, 6f, 46f);
        gridScroll.gameObject.AddComponent<LayoutElement>();
        var gridRect = gridScroll.gameObject.AddComponent<ScrollRect>();
        gridRect.horizontal = false;
        gridRect.vertical = true;
        gridRect.movementType = ScrollRect.MovementType.Clamped;
        gridRect.scrollSensitivity = 15f;
        gridRect.inertia = false;

        RectTransform gridViewport = Rect("GridViewport", gridScroll);
        Stretch(gridViewport, 0, 0, 0, 0);
        Img(gridViewport, Transparent, true);
        gridViewport.gameObject.AddComponent<RectMask2D>();

        RectTransform gridContent = Rect("GridContent", gridViewport);
        TopStretch(gridContent);
        var gridLayout = gridContent.gameObject.AddComponent<GridLayoutGroup>();
        gridLayout.cellSize = TileSize;
        gridLayout.spacing = new Vector2(6f, 6f);
        gridLayout.padding = new RectOffset(8, 8, 8, 8);
        gridLayout.childAlignment = TextAnchor.UpperLeft;
        gridLayout.startCorner = GridLayoutGroup.Corner.UpperLeft;
        gridLayout.startAxis = GridLayoutGroup.Axis.Horizontal;
        gridLayout.constraint = GridLayoutGroup.Constraint.Flexible; // runtime switches to FixedColumnCount
        var gridFitter = gridContent.gameObject.AddComponent<ContentSizeFitter>();
        gridFitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        gridFitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        gridRect.viewport = gridViewport;
        gridRect.content = gridContent;

        // Detail panel (right ~35%).
        RectTransform detailPanel = Rect("DetailPanel", body);
        Anchors(detailPanel, 0.655f, 0f, 1f, 1f);
        Img(detailPanel, PanelFill, false);
        Border(detailPanel, PanelBorder, 1f);

        RectTransform detailScroll = Rect("DetailScroll", detailPanel);
        Stretch(detailScroll, 6f, 6f, 6f, 6f);
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
        var detailLayout = detailContent.gameObject.AddComponent<VerticalLayoutGroup>();
        detailLayout.padding = new RectOffset(12, 12, 10, 10);
        detailLayout.childControlWidth = true;
        detailLayout.childControlHeight = true;
        detailLayout.childForceExpandWidth = true;
        detailLayout.childForceExpandHeight = false;
        var detailFitter = detailContent.gameObject.AddComponent<ContentSizeFitter>();
        detailFitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        detailFitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        RectTransform detailText = Rect("DetailText", detailContent);
        TopStretch(detailText);

        detailRect.viewport = detailViewport;
        detailRect.content = detailContent;

        // ---- Footer -------------------------------------------------------------------------
        RectTransform footer = Rect("Footer", frame);
        BottomBand(footer, 10f, 52f, 16f);

        RectTransform hotkeyBar = Rect("HotkeyBar", footer);
        Anchors(hotkeyBar, 0f, 0f, 0.68f, 1f);
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

        RectTransform status = Rect("StatusText", footer);
        Anchors(status, 0.68f, 0f, 1f, 1f);
        status.offsetMax = new Vector2(-8f, 0f);

        // ---- Templates (inactive container; the template itself stays active so clones are active)
        RectTransform templates = Rect("Templates", root);
        Stretch(templates, 0, 0, 0, 0);
        templates.gameObject.SetActive(false);

        RectTransform tile = Rect("TileTemplate", templates);
        tile.anchorMin = tile.anchorMax = new Vector2(0.5f, 0.5f);
        tile.sizeDelta = TileSize;
        Image hit = Img(tile, Transparent, true); // raycast target for hover/click
        hit.raycastTarget = true;

        RectTransform icon = Rect("Icon", tile);
        Stretch(icon, 2f, 2f, 2f, 2f);
        Image iconImage = Img(icon, Color.white, false);
        iconImage.preserveAspect = true;

        RectTransform tileFrame = Rect("Frame", tile);
        Stretch(tileFrame, -2f, -2f, -2f, -2f);
        Border(tileFrame, Highlight, 2f);
        Image frameTint = Img(tileFrame, new Color(1f, 1f, 0f, 0.12f), false);
        frameTint.raycastTarget = false;
        tileFrame.gameObject.SetActive(false);

        RectTransform badge = Rect("Badge", tile);
        badge.anchorMin = badge.anchorMax = new Vector2(1f, 0f);
        badge.pivot = new Vector2(1f, 0f);
        badge.sizeDelta = new Vector2(18f, 18f);
        badge.anchoredPosition = new Vector2(2f, -2f);
        Img(badge, BadgeFill, false);
        RectTransform badgeText = Rect("BadgeText", badge);
        Stretch(badgeText, 0, 0, 0, 0);
        badge.gameObject.SetActive(false);

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

    /// <summary>Fill the parent with pixel margins (left, bottom, right, top).</summary>
    static void Stretch(RectTransform rt, float left, float bottom, float right, float top)
    {
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = new Vector2(left, bottom);
        rt.offsetMax = new Vector2(-right, -top);
    }

    /// <summary>Full-width band hugging the top edge: y offset from top, fixed height, side margins.</summary>
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

    /// <summary>Scroll content: stretches horizontally, grows downward from the top.</summary>
    static void TopStretch(RectTransform rt)
    {
        rt.anchorMin = new Vector2(0f, 1f);
        rt.anchorMax = new Vector2(1f, 1f);
        rt.pivot = new Vector2(0.5f, 1f);
        rt.offsetMin = new Vector2(0f, 0f);
        rt.offsetMax = new Vector2(0f, 0f);
        rt.sizeDelta = new Vector2(0f, 0f);
    }

    /// <summary>Four thin edge images (no sprite needed).</summary>
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
