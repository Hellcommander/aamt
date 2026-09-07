using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Actionable manual-fix guidance for obsolete / PreferXML / PreferHarmonyPatch hits.
/// Never suggests adding <c>[Obsolete]</c>.
/// </summary>
public static class ManualAdvice
{
    public const string DoNotObsolete =
        "Do not add [Obsolete] — migrate to the current API / game XML overlay / Harmony.";

    public const string LiquidXmlFields =
        "flameTemperature, vaporTemperature, freezeTemperature, combustibility, fluidity, evaporativity, staining, thermalConductivity, circulatoryLossTerm, circulatoryLossNoun, colors, displayName, valuePerDram, cooling, heating, …";

    /// <summary>
    /// PreferXML liquid notes: Class resolves under <c>XRL.Liquids</c>; every liquid needs a
    /// <c>&lt;render&gt;</c> (even empty) so <c>BaseLiquid.Initialize</c> can
    /// <c>Blueprint.Render.Part.Create</c>; render colors use <c>baseColor</c>/<c>baseColorText</c>/
    /// <c>baseColorTile</c>/<c>baseColorDetail</c> (not obsolete part-level colorText on
    /// <c>BaseLiquidRenderPart</c>). <c>BrighterWithVolume</c>/<c>LightLevel</c> belong on
    /// <c>Glows</c>, not the default render part. Named render parts need both <c>Name=</c> and
    /// <c>Class=</c> (same type) so ResolveType runs while Namespace is still
    /// <c>XRL.Liquids.Parts</c>.
    /// </summary>
    public const string LiquidXmlRenderAdvice =
        "Every liquid needs a <render> element (may be empty) so Part.Class defaults to BaseLiquidRenderPart — " +
        "without it, BaseLiquid.Initialize NREs on Blueprint.Render.Part.Create. " +
        "Render colors: colorText/colorTile/colorDetail → baseColor or baseColorText / baseColorTile / baseColorDetail " +
        "(LiquidRenderBlueprint). Keep <class> in namespace XRL.Liquids (ResolveType). " +
        "BrighterWithVolume/LightLevel are Glows fields (XRL.Liquids.Parts.Glows), not BaseLiquidRenderPart. " +
        "Named render parts need both Name= and Class= (same type, e.g. Name=\"Glows\" Class=\"Glows\") — " +
        "Name-only parts fall through to BaseLiquidRenderPart and warn Extraneous for colorText/BrighterWithVolume/etc.";

    /// <summary>
    /// Enrich remaining hits with actionable <see cref="RemainingHit.Advice"/>.
    /// PreferXML / PreferHarmonyPatch already carry advice from the scanner; dump hits get keyed guidance.
    /// </summary>
    public static void Enrich(IList<RemainingHit> hits)
    {
        foreach (var h in hits)
        {
            if (!string.IsNullOrWhiteSpace(h.Advice))
                continue;

            h.Advice = ForMember(h.Member, h.Message, h.Text);
        }
    }

    public static string ForMember(string member, string obsoleteMessage, string? code = null)
    {
        var m = member ?? "";
        var shortName = m.Contains('.') ? m[(m.LastIndexOf('.') + 1)..] : m;

        if (m.StartsWith("PreferXML.", StringComparison.Ordinal))
            return PreferXmlAdvice(shortName);

        if (m.StartsWith("PreferHarmonyPatch.", StringComparison.Ordinal))
            return PreferHarmonyAdvice(shortName);

        if (m.StartsWith("WorldsXml.", StringComparison.Ordinal))
            return WorldsXmlAdvice(shortName);

        if (m.StartsWith("CS0118.", StringComparison.Ordinal))
            return NamespaceVsTypeAdvice(shortName);

        if (m.StartsWith("RemovedType.", StringComparison.Ordinal))
            return RemovedGameTypeAdvice(shortName, "minigame");

        if (m.StartsWith("RemovedMember.", StringComparison.Ordinal) ||
            m.Contains("Options.Sifrah", StringComparison.Ordinal) ||
            shortName is "AnySifrah")
            return RemovedSifrahOptionAdvice();

        if (m.Contains("ShowOptionListAsync", StringComparison.Ordinal))
            return ShowOptionListAdvice(async: true);

        if (m.Contains("ShowOptionList", StringComparison.Ordinal))
            return ShowOptionListAdvice(async: false);

        if (m.Contains("ReverseTranslateBit", StringComparison.Ordinal) ||
            m.Contains("ReverseCharTranslateBit", StringComparison.Ordinal))
            return ReverseTranslateBitAdvice(code);

        if (m.Contains("MutationOnEquip", StringComparison.Ordinal) &&
            (shortName is "ClassName" or "Variant" || m.Contains("ClassName") || m.Contains("Variant")))
            return MutationOnEquipAdvice(shortName);

        if (m.Contains("LiquidBlood", StringComparison.Ordinal))
            return LiquidBloodAdvice(shortName is "Colors" or "ID" or "GetColors" ? shortName : null);

        if (m.Contains("LiquidWarmStatic", StringComparison.Ordinal) ||
            shortName is "ApplyRandomEffectTo" or "GlitchObject" or "GlitchZone")
            return LiquidWarmStaticAdvice(shortName is "ApplyRandomEffectTo" or "GlitchObject" or "GlitchZone" or "ID"
                ? shortName
                : null);

        if (m.Contains("DefaultDisplayOrder", StringComparison.Ordinal))
            return InventoryActionDefaultDisplayOrderAdvice();

        if (m.Contains("AppendDescription", StringComparison.Ordinal) &&
            m.Contains("AddsRep", StringComparison.Ordinal))
            return AddsRepAppendDescriptionAdvice();

        if (shortName is "AppendSigned" or "AppendArmor" or "AppendPV" or "AppendDamage" or "AppendAttribute" ||
            m.StartsWith("CS1929.", StringComparison.Ordinal))
            return TextBuilderHalfMigrationAdvice(shortName);

        if (shortName is "AddReplacer" || m.Contains("AddReplacer", StringComparison.Ordinal))
            return AddReplacerAdvice(code);

        if (m.Contains("VariableObjectReplacer", StringComparison.Ordinal))
            return VariableObjectReplacerAdvice();

        if (m.Contains("DelegateContext", StringComparison.Ordinal) &&
            (code?.Contains("[VariableReplacer", StringComparison.Ordinal) == true ||
             code?.Contains("[VariableObjectReplacer", StringComparison.Ordinal) == true ||
             code?.Contains("VariableReplacer(", StringComparison.Ordinal) == true))
            return VariableReplacerDelegateContextAdvice();

        if (shortName is "ExpandString" || m.Contains("ExpandString", StringComparison.Ordinal))
            return ExpandStringAdvice(m, obsoleteMessage);

        if (shortName is "Poss" or "poss")
            return PossAdvice(shortName);

        if (shortName is "Vaporized" || m.Contains("BaseLiquid.Vaporized", StringComparison.Ordinal))
            return $"{DoNotObsolete} PreferHarmonyPatch / signature bump — BaseLiquid.Vaporized is now `Vaporized(LiquidVolume, GameObject)` (not VaporizedEvent). Prefer Harmony when patching vanilla liquids; bump your own override signature when required.";

        if (shortName is "getDay" or "getMonth" or "getYear" or "getTime" ||
            m.Contains("Calendar.getDay", StringComparison.Ordinal) ||
            m.Contains("Calendar.getMonth", StringComparison.Ordinal) ||
            m.Contains("Calendar.getYear", StringComparison.Ordinal) ||
            m.Contains("Calendar.getTime", StringComparison.Ordinal))
            return CalendarCamelAdvice(shortName);

        if (shortName is "GetDay" || m.EndsWith(".GetDay", StringComparison.Ordinal) ||
            m.Contains("Calendar.GetDay", StringComparison.Ordinal))
            return CalendarGetDayAdvice();

        if (shortName is "GetVerb" || m.EndsWith(".GetVerb", StringComparison.Ordinal))
            return $"{DoNotObsolete} GameObject.GetVerb → GameText `=object.verb:verb=` (or =subject.verb:…=) inside EmitMessage / _T / StartReplace — not a StringBuilder concat of GetVerb().";

        if (IsGameObjectArticleOrPronoun(shortName) &&
            (m.Contains("GameObject", StringComparison.Ordinal) ||
             // Distinctive pronouns rarely collide with other types' members:
             shortName is "a" or "A" or "an" or "An" or "the" or "The" or "its" or "Its"
                 or "it" or "It" or "Itis" or "itis" or "itself" or "Itself"
                 or "Does" or "does" or "Them" or "them" or "They" or "they"
                 or "Their" or "their" or "Theirs" or "theirs" or "tis" or "Tis"))
            return GameObjectGameTextAdvice(shortName, obsoleteMessage);

        if (shortName is "indicativeDistal" or "IndicativeDistal" or "indicativeProximal" or "IndicativeProximal")
            return $"{DoNotObsolete} Use GameText `=GameObject.{shortName}=` (or =subject.{shortName}=) inside EmitMessage / ReplaceBuilder — do not read the obsolete property into a string.";

        if (shortName.Contains("GetLongDescription", StringComparison.Ordinal) ||
            m.Contains("GetLongDescription", StringComparison.Ordinal))
            return GetLongDescriptionAdvice();

        if (m.Contains("BaseMutation", StringComparison.Ordinal) &&
            (shortName is "DisplayName" or "_DisplayName" or "Type" or "_Type" or "GetDisplayName"))
            return BaseMutationDisplayNameAdvice(shortName);

        if (shortName is "AddInventoryAction" || m.Contains("AddInventoryAction", StringComparison.Ordinal))
            return $"{DoNotObsolete} Event.AddInventoryAction → `GetParameter(\"Actions\") as EventParameterGetInventoryActions` (then use that bag's AddAction APIs).";

        if (shortName.StartsWith("weird", StringComparison.Ordinal) ||
            m.Contains("weirdLower", StringComparison.Ordinal) ||
            m.Contains("weirdUpper", StringComparison.Ordinal))
            return $"{DoNotObsolete} Grammar.weird* Char[] fields are gone — use `TextConstants.WeirdSets`.";

        if (shortName == "Capitalize" || m.EndsWith(".Capitalize", StringComparison.Ordinal))
            return $"{DoNotObsolete} Use `Translator.InitUpper(s)` (or `|capitalize` GameText post-processor). ApiMigrator auto-fixes `Extensions.Capitalize(` and simple `recv.Capitalize()` under -Apply; chained receivers (e.g. `Grammar.Cardinal(n).Capitalize()`) need a hand wrap: `Translator.InitUpper(Grammar.Cardinal(n))`.";

        if (shortName is "knownRecipies" || m.Contains("knownRecipies", StringComparison.Ordinal))
            return $"{DoNotObsolete} CookingGameState.knownRecipies → JournalAPI.RecipeNotes (List<JournalRecipeNote>, not List<CookingRecipe>). Map notes manually; not a drop-in type swap.";

        if (shortName is "WantHundredTurnTick" or "WantTenTurnTick" or "HundredTurnTick" or "TenTurnTick")
            return TurnTickAdvice(shortName);

        if (shortName is "FinalRender")
            return FinalRenderAdvice();

        if (shortName is "LoadGame" or "SaveGame")
            return GameSystemSerializeAdvice(shortName);

        if (shortName is "pPhysics" or "_pPhysics" || m.EndsWith(".pPhysics", StringComparison.Ordinal))
        {
            if (m.Contains("Brain", StringComparison.Ordinal))
                return $"{DoNotObsolete} Brain.pPhysics → use ParentObject.Physics (Brain has no Physics field).";
            return $"{DoNotObsolete} Use `.Physics` (GameObject field) instead of `.pPhysics`.";
        }

        if (shortName is "pRender" or "_pRender" || m.EndsWith(".pRender", StringComparison.Ordinal))
            return $"{DoNotObsolete} Use `.Render` (GameObject field) instead of `.pRender`.";

        if (shortName is "pBrain" or "_pBrain")
            return $"{DoNotObsolete} Use `.Brain` instead of `.pBrain`.";

        if (shortName is "create" or "createSample" or "createUnmodified")
            return $"{DoNotObsolete} Use GameObject.Create / CreateSample / CreateUnmodified (PascalCase). Avoid rewriting unrelated `*.create(` (e.g. ScreenBuffer.create).";

        if (shortName == "AddAction" || m.Contains("AddAction", StringComparison.Ordinal))
            return AddActionAdvice(code);

        if (shortName is "ApplyStatShift" or "UnapplyStatShift" ||
            m.Contains("ApplyStatShift", StringComparison.Ordinal) ||
            m.Contains("UnapplyStatShift", StringComparison.Ordinal))
            return StatShifterAdvice(unapply: shortName == "UnapplyStatShift" ||
                m.Contains("UnapplyStatShift", StringComparison.Ordinal));

        if (shortName == "Drank" || m.EndsWith(".Drank", StringComparison.Ordinal))
            return DrankAdvice();

        if (shortName is "hateReasons" or "likeReasons" ||
            (m.Contains("GenerateFriendOrFoe", StringComparison.Ordinal) &&
             obsoleteMessage.Contains("friendOrFoe", StringComparison.OrdinalIgnoreCase)))
            return FriendOrFoeSpiceAdvice(shortName is "hateReasons" or "likeReasons" ? shortName : null);

        if (m.Contains("MutationEntry", StringComparison.Ordinal) && shortName == "DisplayName")
            return MutationEntryDisplayNameAdvice(code);

        if (shortName is "DidX" or "DidXToY" or "DidXToYWithZ" or "XDidY" or "XDidYToZ" or "WDidXToYWithZ" ||
            shortName.StartsWith("Did", StringComparison.Ordinal) ||
            obsoleteMessage.Contains("EmitMessage", StringComparison.OrdinalIgnoreCase))
            return DidXEmitMessageAdvice(shortName);

        if (shortName is "Things" || m.EndsWith(".Things", StringComparison.Ordinal))
            return $"{DoNotObsolete} Extensions.Things → GameText `=number.things:what:whatPlural=` via `XRL.Language.Strings._T(…).SetArgument(\"number\", n).ToString()` (or GameText.StartReplace). ApiMigrator ThingsFixer auto-rewrites only when what/plural are string literals under -Apply; non-literal nouns stay manual. Do not bake color markup into the noun token.";

        if (m.Contains("NewStringBuilder", StringComparison.Ordinal))
            return $"{DoNotObsolete} Use `TextBuilder.Get()` (`using XRL.World.Text;`), not Event.NewStringBuilder.";

        if (shortName is "Register" or "Unregister")
            return PreferHarmonyAdvice(shortName);

        // Generic fallback
        var hint = string.IsNullOrWhiteSpace(obsoleteMessage) ? "migrate to the current API" : obsoleteMessage.Trim();
        return $"{DoNotObsolete} Game says: {hint}";
    }

    public static string PreferXmlAdvice(string memberName) => memberName switch
    {
        "DisplayName" or "GetDisplayName" =>
            $"{DoNotObsolete} PreferXML — remove the DisplayName setter/override when feasible; set DisplayName via Mutations.xml overlay (MutationEntry.HandleXMLNode / same-Name redeclare; DataManager root \"mutations\"):\n" +
            "  <mutations Encoding=\"utf-8\">\n" +
            "    <mutation Name=\"YourMutation\" DisplayName=\"Your Name\" Type=\"Mental\" />\n" +
            "  </mutations>\n" +
            "See _tools/docs/coq-internal-patching.md. Not Harmony for pure data. C# override only when there is no other option.",
        "Type" =>
            $"{DoNotObsolete} PreferXML — remove the Type setter/override when feasible; put mutation/liquid Type in Mutations.xml / Liquids.xml (same-Name redeclare / BlueprintReader merge). Example mutation:\n" +
            "  <mutation Name=\"YourMutation\" Type=\"Physical\" DisplayName=\"…\" />\n" +
            "See coq-internal-patching.md.",
        "IsLiquid" =>
            $"{DoNotObsolete} PreferXML — declare/update the liquid in Liquids.xml instead of overriding IsLiquid / assigning BaseLiquid.* setters in C#. " +
            "Required: C# class must be `namespace XRL.Liquids` (Liquids.xml `<class>` resolves only there — custom namespaces → TypeLoadException). Typical fields: {LiquidXmlFields}\n" +
            "  <liquids Encoding=\"utf-8\">\n" +
            "    <liquid Name=\"Ichor\">\n" +
            "      <slug>ichor</slug>\n" +
            "      <class>LiquidIchor</class>\n" +
            "      <flameTemperature>400</flameTemperature>\n" +
            "      <vaporTemperature>1200</vaporTemperature>\n" +
            "      <colors>WO</colors>\n" +
            "      <displayName>{{W|ichor}}</displayName>\n" +
            "      <render />\n" +
            "    </liquid>\n" +
            "  </liquids>\n" +
            "Keep the C# BaseLiquid subclass in namespace `XRL.Liquids` so Liquids.xml `<class>` / Class= resolves (same ResolveType pattern as parts). Move data fields to XML; do not put the liquid class in a custom namespace. " +
            LiquidXmlRenderAdvice +
            " ApiMigrator LiquidXmlFixer inserts empty <render />, renames obsolete render colors, moves " +
            "BrighterWithVolume/LightLevel onto Glows, and adds Class= on named render parts under -Apply when safe. " +
            "See coq-internal-patching.md.",
        "GetLiquidDescription" =>
            $"{DoNotObsolete} PreferXML — liquid description/data belongs in Liquids.xml (displayName / adjective / smeared* elements). Keep the BaseLiquid class in `XRL.Liquids` matching `<class>`. " +
            LiquidXmlRenderAdvice + " See coq-internal-patching.md.",
        "Drank" => DrankAdvice(),
        "LiquidProperties" =>
            LiquidPropertiesAdvice(null),
        "LiquidBlood" or "Colors" or "ID" or "GetColors" =>
            LiquidBloodAdvice(memberName is "LiquidBlood" ? null : memberName),
        "LiquidWarmStatic" or "ApplyRandomEffectTo" or "GlitchObject" or "GlitchZone" =>
            LiquidWarmStaticAdvice(memberName is "LiquidWarmStatic" ? null : memberName),
        "hateReasons" or "likeReasons" or "FriendOrFoe" or "FriendOrFoeReasons" =>
            FriendOrFoeSpiceAdvice(memberName),
        _ =>
            $"{DoNotObsolete} PreferXML — move entry data into the game XML overlay for that domain (DataManager.YieldXMLStreamsWithRoot / Load=Merge / same-Name redeclare). See _tools/docs/coq-internal-patching.md. C# override only when there is no other option.",
    };

    /// <summary>
    /// PreferXML/spice — <c>GenerateFriendOrFoe.hateReasons</c>/<c>likeReasons</c> lists load from
    /// <c>HistorySpice.json(c)</c> via <c>=spice:friendOrFoe.$spiceKey.…=</c> (HistoricSpice.MergeModJson appends arrays).
    /// </summary>
    public static string FriendOrFoeSpiceAdvice(string? listName = null)
    {
        var key = listName is "hateReasons" or "likeReasons" ? listName : "hateReasons|likeReasons";
        return $"{DoNotObsolete} PreferXML/spice — do not Add to GenerateFriendOrFoe.{key}. " +
               "Put strings in a mod HistorySpice.json under spice.friendOrFoe.default (or HEB / custom $spiceKey); " +
               "HistoricSpice.MergeModJson merges mod files named historyspice.* and appends JArray entries onto vanilla. Example:\n" +
               "  {\n" +
               "    \"lang\": \"en\",\n" +
               "    \"spice\": {\n" +
               "      \"friendOrFoe\": {\n" +
               "        \"default\": {\n" +
               "          \"hateReasons\": [ \"your new hate reason\" ],\n" +
               "          \"likeReasons\": [ \"your new like reason\" ]\n" +
               "        }\n" +
               "      }\n" +
               "    }\n" +
               "  }\n" +
               "Runtime picks via =spice:friendOrFoe.$spiceKey.hateReasons.!random= / likeReasons. " +
               "Use =spice:nouns.!random= (not obsolete $noun / reasonReplacers). Remove ModSensitiveCacheInit C# Add lists.";
    }

    public static string LiquidPropertiesAdvice(string? propName)
    {
        var prop = string.IsNullOrEmpty(propName) ? "these fields" : propName;
        return $"{DoNotObsolete} PreferXML — move {prop} into Liquids.xml rather than assigning on BaseLiquid in C#. Supported elements include: {LiquidXmlFields}\n" +
               "Ctor `this.FlameTemperature = …` etc. should become XML on the same liquid Name. Keep the C# BaseLiquid class in namespace `XRL.Liquids` for Liquids.xml `<class>` / Class= resolution; " +
               "ApiMigrator LiquidCsToXmlFixer extracts literal ctor assignments + [IsLiquid] + GetName/GetColor/GetColors/GetValuePerDram/simple Blood-like render into Liquids.xml under -Apply. " +
               "Own BaseLiquid.Drank converts via LiquidDrankToPartFixer (MessageOnDrink or XRL.Liquids.Parts.*OnDrink). " +
               "Keep Render* overrides only when XML parts cannot express them. " +
               LiquidXmlRenderAdvice + " See coq-internal-patching.md.";
    }

    /// <summary>
    /// Worlds.xml XmlDataHelper MODWARNs — zone Load create / cell builder / cell DisableForcedConnections.
    /// </summary>
    public static string WorldsXmlAdvice(string memberName) => memberName switch
    {
        "ZoneLoadCreate" => WorldsZoneLoadAdvice(),
        "CellBuilder" => WorldsCellBuilderAdvice(),
        "CellDisableForcedConnections" => WorldsCellDisableForcedAdvice(),
        _ =>
            $"{DoNotObsolete} Worlds.xml — zone Load Merge/Replace for overlays; builders/music on zones (not cells); DisableForcedConnections on zones only.",
    };

    public static string WorldsZoneLoadAdvice() =>
        $"{DoNotObsolete} Worlds.xml — overlapping vanilla/mod zone ranges default to Load=Create and MODWARN " +
        "\"Found existing zone with range … load mode create doesn't indicate replace or merge\". " +
        "On landmark overlays (e.g. Bethesda Susa under `<cell Name=\"Bethesda Susa\" Load=\"Merge\" …>`) set " +
        "`Load=\"Merge\"` (soft overlay / postbuilders) or `Load=\"Replace\"` (map floors that fully replace vanilla) on each conflicting `<zone>`. " +
        "Leave Create only for brand-new range keys. ApiMigrator never auto-picks Merge vs Replace (intent-dependent); " +
        "WorldsXmlAdviceScanner flags `<zone` without Load= under cells with Load=Merge|Replace.";

    public static string WorldsCellBuilderAdvice() =>
        $"{DoNotObsolete} Worlds.xml — cells only allow `<zone>` / `<properties>` children. " +
        "`<builder>` belongs on `<zone>` (or use `<postbuilder>`); Music builder → prefer `<music Track=\"…\" />` on the zone. " +
        "Do not auto-delete builders (may need relocating). World-level builders are a separate path and are not flagged here.";

    public static string WorldsCellDisableForcedAdvice() =>
        $"{DoNotObsolete} Worlds.xml — `DisableForcedConnections` is valid on `<zone>` only (unused on `<cell>` → MODWARN). " +
        "Move it onto the relevant zone(s), or drop it from the cell. ApiMigrator WorldsXmlFixer safely strips the attribute from `<cell>` opening tags under -Apply.";

    /// <summary>Factions.xml XmlDataHelper MODWARNs — Load=Merge unused, bare interest, skill case, Emblem typo.</summary>
    public static string FactionsLoadMergeAdvice() =>
        $"{DoNotObsolete} Factions.xml — `Load=\"Merge\"` is unused on `<factions>` / `<faction>` (Replace only when the name already exists). " +
        "Strip Load=Merge (FactionsXmlFixer under -Apply) or use Load=\"Replace\" only when intentionally replacing an existing faction.";

    public static string FactionsBareInterestAdvice() =>
        $"{DoNotObsolete} Factions.xml — `<interest>` must be nested under `<interests>`, not bare under `<faction>`. " +
        "Wrap: `<interests><interest …/></interests>`. Never auto-wrapped (ambiguous multi-interest layouts).";

    public static string FactionsWaterRitualSkillAdvice() =>
        $"{DoNotObsolete} Factions.xml — `<waterritual>` attribute is case-sensitive `Skill=` (not `skill=`). " +
        "FactionsXmlFixer renames wrong-case skill→Skill under -Apply when safe.";

    public static string FactionsEmblemTileColorAdvice() =>
        $"{DoNotObsolete} Factions.xml — `EEmblemTileColor` is a typo; use `EmblemTileColor`. " +
        "FactionsXmlFixer renames under -Apply.";

    /// <summary>Populations.xml — required Name on group; case-sensitive Name/Load/Style.</summary>
    public static string PopulationGroupNameAdvice() =>
        $"{DoNotObsolete} Populations.xml — `<group>` requires `Name=` (PopulationManager.LoadPopulationGroup). " +
        "Inventing a Name is unsafe; set the intended group id by hand. " +
        "Common chargen / StartingGear groups use Name=\"Items\" (and similar named buckets) — match vanilla PopulationTables naming when merging.";

    public static string PopulationAttrCaseAdvice() =>
        $"{DoNotObsolete} Populations.xml — XmlDataHelper attrs are case-sensitive: `Name`, `Load`, `Style` (not name/load/style). " +
        "PopulationXmlFixer corrects case under -Apply when unambiguous.";

    public static string LiquidBloodAdvice(string? member)
    {
        var focus = member switch
        {
            "Colors" or "GetColors" => "For colors, put `<colors>…</colors>` on your liquid in Liquids.xml (or call GetColors from your own liquid data) — do not read LiquidBlood.Colors.",
            "ID" => "Use LiquidID.Blood (or your liquid's slug/ID) instead of LiquidBlood.ID.",
            _ => "LiquidBlood is back-compat; behaviors live in Liquids.xml parts. Prefer LiquidID / Liquids.xml colors and current liquid APIs.",
        };
        return $"{DoNotObsolete} PreferXML — {focus} Example Blood colors in vanilla: `<colors>rK</colors>`.";
    }

    public static string LiquidWarmStaticAdvice(string? member)
    {
        var focus = member switch
        {
            "ID" => "Use `LiquidID.WarmStatic` (ApiMigrator auto-rewrites `LiquidWarmStatic.ID` under -Apply).",
            "ApplyRandomEffectTo" =>
                "Call `BaseGlitchPart.ApplyRandomEffectTo(GameObject, tier, emitMessage, fromDialog)` on a glitch part instance (or PreferXML: GlitchOnHit / GlitchOnDrink / GlitchOnPour / GlitchOnSmear / GlitchOnMixed liquid parts). Static `LiquidWarmStatic.ApplyRandomEffectTo` was removed (CS0117).",
            "GlitchObject" =>
                "Call `BaseGlitchPart.GlitchObject(GameObject, message)` (instance). PreferXML GlitchOn* parts when wiring warm-static liquid behavior.",
            "GlitchZone" =>
                "Call `BaseGlitchPart.GlitchZone(Zone)` (instance). PreferXML GlitchOn* parts when possible.",
            _ =>
                "LiquidWarmStatic is back-compat only ('All behaviors ported to parts'). Prefer Liquids.xml + `XRL.Liquids.Parts.BaseGlitchPart` / GlitchOn* / WarmStaticRender; use `LiquidID.WarmStatic` for the slug.",
        };
        return $"{DoNotObsolete} PreferXML — {focus}";
    }

    public static string TextBuilderHalfMigrationAdvice(string? appendName)
    {
        var name = string.IsNullOrEmpty(appendName) || appendName == "TextBuilderStringBuilderOnly"
            ? "AppendSigned/AppendArmor/AppendPV/AppendDamage/AppendAttribute"
            : appendName;
        return $"{DoNotObsolete} Half-migration: Extensions.{name} still takes StringBuilder only (CS1929/CS1503 when passed a TextBuilder). " +
               "ApiMigrator auto-rewrites TextBuilder.AppendSigned(n) → Append(n, true) and AppendSigned(n, \"rules\") → AppendModifier under -Apply; " +
               "Event.FinalizeString(tb) → tb.ToString() when tb is TextBuilder. " +
               "Keep a StringBuilder for AppendArmor/AppendPV/AppendDamage/AppendAttribute, or rewrite with TextBuilder.Append / GameText. " +
               "For AddsRep reputation lines ApiMigrator rewrites the obsolete 7-arg form to AppendDescription(TextBuilder, Value, Faction, SignedRules) (Value/Faction swapped).";
    }

    public static string AddsRepAppendDescriptionAdvice() =>
        $"{DoNotObsolete} AddsRep.AppendDescription(TextBuilder, Faction, Value, Prefix, Postfix, Rules, SignedRules) is obsolete — Prefix/Postfix/Rules are ignored. " +
        "Use AppendDescription(TextBuilder, Value, Faction, SignedRules) or the GameText token =addsRep#value#faction=.";

    public static string InventoryActionDefaultDisplayOrderAdvice() =>
        $"{DoNotObsolete} InventoryAction.DefaultDisplayOrder was removed (CS0117). " +
        "Use `Priority` for menu sort order (see InventoryAction.PriorityCompare), or `Default` for the default-action flag — they are different fields. Example: `Priority = 5`.";

    public static string AddReplacerAdvice(string? code)
    {
        // Dump's generic AddReplacer message is now VariableReplacer; Key,Value / expression
        // forms still migrate to SetArgument (curated autofix for lit+lit, lit+expr, lit+ternary).
        var hint = "Game obsolete message favors [VariableReplacer] for delegate/method-group forms. " +
                   "String/object values still use `.AddReplacer(key, value)` → `.SetArgument(key, value)` (same arg order). " +
                   "ApiMigrator auto-fixes literal+literal, literal+expression-with-`.`/`(`, and literal+ternary under -Apply. " +
                   "Bare second-arg identifiers may be a string local OR a Replacer method group — check before rewriting.";
        if (!string.IsNullOrEmpty(code))
        {
            // Inspect the second argument only (first is usually a string-literal key).
            var m = Regex.Match(code, @"\.AddReplacer\s*\(\s*[^,]+,\s*(?<v>[^)]+)\)");
            var v = m.Success ? m.Groups["v"].Value.Trim() : "";
            if (v.Contains('?', StringComparison.Ordinal) && v.Contains(':', StringComparison.Ordinal))
                hint = "Second arg is a ternary value → `.SetArgument(key, value)` (not VariableReplacer).";
            else if (v.Contains(".ToString(", StringComparison.Ordinal) ||
                (v.StartsWith("\"", StringComparison.Ordinal) && v.EndsWith("\"", StringComparison.Ordinal)) ||
                v.Contains('.', StringComparison.Ordinal) ||
                v.Contains('(', StringComparison.Ordinal))
                hint = "Second arg looks like a value expression → `.SetArgument(key, value)` (not VariableReplacer).";
            else if (Regex.IsMatch(v, @"^[A-Za-z_]\w*$"))
                hint = "Bare second-arg identifier — if it is a string/object local/property use `.SetArgument(key, value)`; " +
                       "if it is a Replacer method group, decorate that method with [VariableReplacer] instead.";
        }
        return $"{DoNotObsolete} {hint}";
    }

    public static string VariableObjectReplacerAdvice() =>
        $"{DoNotObsolete} `[VariableObjectReplacer]` is obsolete — use `[VariableReplacer(Capitalization = true)]` " +
        "(or keep Keys and add `Capitalization = true`). ApiMigrator VariableReplacerFixer does this under -Apply. " +
        "If the method still takes `DelegateContext`, migrate to `VariableContext`; object targets use a typed " +
        "`GameObject Object` parameter (`Context.Target`/`Context.Pronouns` → `Object`/`Object.GetPronounProvider()`).";

    public static string VariableReplacerDelegateContextAdvice() =>
        $"{DoNotObsolete} Variable replacers must take `VariableContext` (not obsolete `DelegateContext`). " +
        "ApiMigrator auto-fixes `[VariableReplacer]`/`[VariableObjectReplacer]` method signatures under -Apply. " +
        "For `=subject.foo=`-style keys that used `Context.Target`/`Pronouns`, add `GameObject Object` as the second " +
        "parameter (vanilla `GameObjectReplacers` pattern). Conversation `DelegateContext` (no VariableReplacer attribute) is still valid.";

    public static string ExpandStringAdvice(string member, string obsoleteMessage)
    {
        if (member.Contains("HistoricEvent", StringComparison.Ordinal))
            return $"{DoNotObsolete} HistoricEvent.ExpandString → `Expand()` (not `_T` / StartReplace).";
        if (member.Contains("HistoricEntity", StringComparison.Ordinal))
            return $"{DoNotObsolete} HistoricEntity.ExpandString → new `=spice.entity:query=` format (see game obsolete message).";
        if (member.Contains("HistoricStringExpander", StringComparison.Ordinal))
            return $"{DoNotObsolete} HistoricStringExpander.ExpandString → `\"=spice:query=\".StartReplacer()` syntax.";
        var hint = string.IsNullOrWhiteSpace(obsoleteMessage) ? "migrate ExpandString to the current HistoryKit API" : obsoleteMessage.Trim();
        return $"{DoNotObsolete} Game says: {hint}";
    }

    public static string PossAdvice(string shortName) =>
        shortName == "Poss"
            ? $"{DoNotObsolete} GameObject.Poss → GameText `=GameObject.Poss#GameObject=` replacer (not The.name's:withTitles templates)."
            : $"{DoNotObsolete} GameObject.poss → GameText `=GameObject.poss#GameObject=` replacer (not the.name's:withTitles templates).";

    public static string TurnTickAdvice(string memberName)
    {
        return memberName switch
        {
            "WantHundredTurnTick" or "WantTenTurnTick" =>
                $"{DoNotObsolete} PreferHarmonyPatch — {memberName} is obsolete; use WantTurnTick() and implement TurnTick(long TimeTick, int Amount). " +
                "Do not stamp [Obsolete]. Prefer safer Harmony Prefix/Postfix on TurnTick when extending vanilla parts; keep override only when there is no other option.",
            "HundredTurnTick" or "TenTurnTick" =>
                $"{DoNotObsolete} PreferHarmonyPatch — {memberName}(long) → TurnTick(long TimeTick, int Amount). Amount encodes how many ten/hundred ticks elapsed. Prefer Harmony on TurnTick when patching vanilla.",
            _ =>
                $"{DoNotObsolete} PreferHarmonyPatch — migrate to WantTurnTick / TurnTick(long, int). Do not add [Obsolete].",
        };
    }

    public static string FinalRenderAdvice() =>
        $"{DoNotObsolete} PreferHarmonyPatch — FinalRender(RenderEvent, bool) → FinalRender(RenderEvent). " +
        "ApiMigrator auto-drops the unused bool parameter under -Apply when the Alt param is unreferenced; if Alt is used, fold that logic into the single-arg override or a Harmony Prefix/Postfix. Do not add [Obsolete].";

    public static string GameSystemSerializeAdvice(string memberName) =>
        memberName == "SaveGame"
            ? $"{DoNotObsolete} PreferHarmonyPatch — IGameSystem.SaveGame(SerializationWriter) → override Write(). Prefer Harmony only when patching another system; for your own IGameSystem, rename/bump to Write()."
            : $"{DoNotObsolete} PreferHarmonyPatch — IGameSystem.LoadGame(SerializationReader) → override Read(). Prefer Harmony only when patching another system; for your own IGameSystem, rename/bump to Read().";

    public static string MutationOnEquipAdvice(string memberName)
    {
        return $"{DoNotObsolete} MutationOnEquip.{memberName} is obsolete — set Mutation=\"Name From Mutations.xml\" on the part in object XML, or call GetMutationEntry() in code. Do not keep ClassName/Variant string fields. ApiMigrator ObjectBlueprintXmlFixer rewrites ClassName→Mutation under -Apply. If the class is missing from base Mutations.xml (e.g. FattyHump, HeightenedSmell), also add a mod Mutations.xml entry (ExcludeFromPool category) so TryGetMutationEntry resolves. Example:\n" +
               "  <part Name=\"MutationOnEquip\" Mutation=\"Telepathy\" />\n" +
               "See coq-internal-patching.md (mutations overlay).";
    }

    /// <summary>
    /// <c>MutationEntry.DisplayName</c> is ambiguous — cannot autofix. Stable blueprint IDs use <c>Name</c>;
    /// UI / caller display strings use <c>GetDisplayName()</c>. Callers often pass XML DisplayName text
    /// (e.g. "Night Vision"), not <c>Name</c> ("NightVision").
    /// </summary>
    public static string MutationEntryDisplayNameAdvice(string? code = null)
    {
        var hint = "Read each site: use `.Name` for stable ID matching (GetMutationEntryByName / XML Name); " +
                   "use `.GetDisplayName()` for UI strings and for Contains/equality against caller display strings " +
                   "(e.g. \"Night Vision\", \"Amphibious\"). Never auto-rewrite — wrong choice breaks consumers.";
        if (!string.IsNullOrEmpty(code))
        {
            if (code.Contains("Contains(", StringComparison.Ordinal) ||
                code.Contains("==", StringComparison.Ordinal) ||
                code.Contains("Equals(", StringComparison.Ordinal))
                hint = "Matching site — prefer `.GetDisplayName()` if the compared strings are UI/DisplayName text; " +
                       "prefer `.Name` only if callers pass Mutations.xml Name IDs. Check consumer string literals before choosing.";
            else if (code.Contains("Log", StringComparison.OrdinalIgnoreCase) ||
                     code.Contains("Popup", StringComparison.OrdinalIgnoreCase) ||
                     code.Contains("Message", StringComparison.OrdinalIgnoreCase) ||
                     code.Contains("+", StringComparison.Ordinal))
                hint = "Looks like a UI/log string → use `.GetDisplayName()` (optional Annotations: true).";
        }
        return $"{DoNotObsolete} MutationEntry.DisplayName is obsolete. {hint}";
    }

    public static string ReverseTranslateBitAdvice(string? code)
    {
        var hint = "Use BitType.FetchBitByCode(c)?.BitID (char; .ToString() for string contexts) when you need the bit ID string historically returned by ReverseTranslateBit; use ?.DisplayColor when you need data.xml display color. Null-unknown → \"?\" / '?'.";
        if (!string.IsNullOrEmpty(code))
        {
            if (code.Contains("Color", StringComparison.OrdinalIgnoreCase) || code.Contains("{{", StringComparison.Ordinal))
                hint = "This site looks color-oriented → prefer FetchBitByCode(c)?.DisplayColor ?? \"?\".";
            else if (code.Contains("+=", StringComparison.Ordinal) || code.Contains("string ", StringComparison.Ordinal) || code.Contains("\"?\"", StringComparison.Ordinal))
                hint = "This site looks ID-oriented → prefer FetchBitByCode(c)?.BitID.ToString() ?? \"?\" (ApiMigrator auto-fixes clear ID/color cases under -Apply).";
        }
        return $"{DoNotObsolete} {hint} Note: obsolete message says `.ID`; live field is BitID.";
    }

    public static string AddActionAdvice(string? code)
    {
        return $"{DoNotObsolete} Prefer InventoryActions.xml same-Name merge (see coq-internal-patching.md) or `AddXMLAction(\"Name\")` for static/localizable actions; for dynamic actions use:\n" +
               "  E.AddAction(new InventoryAction {\n" +
               "    Name = \"Activate\", Display = \"&Wa&yctivate\", Command = \"Activate\",\n" +
               "    Key = 'a', WorksTelekinetically = true });\n" +
               "ApiMigrator: literal Name/Display/Command/Key → AddXMLAction + InventoryActions.xml; remaining string overloads → InventoryAction object; `_ = E.AddAction(...)` void discards (CS8209) are stripped. Do not keep obsolete multi-string overloads.";
    }

    public static string StatShifterAdvice(bool unapply)
    {
        if (unapply)
        {
            return $"{DoNotObsolete} Not autofixable — receiver moves off GameObject onto the part/effect StatShifter. " +
                   "`obj.UnapplyStatShift(stat, amount)` → `StatShifter.RemoveStatShift(obj, stat)` or `StatShifter.RemoveStatShifts()`. " +
                   "Amount is not needed (shifts are GUID-tracked). Example: `StatShifter.RemoveStatShift(ParentObject, MoveSpeedStat);`";
        }

        return $"{DoNotObsolete} Not autofixable — receiver moves off GameObject onto the part/effect StatShifter. " +
               "`obj.ApplyStatShift(stat, amount)` → `StatShifter.SetStatShift(stat, amount)` " +
               "(or `SetStatShift(target, stat, amount)`). SetStatShift replaces any prior shift for the same stat from this shifter. " +
               "Example: `StatShifter.SetStatShift(MoveSpeedStat, -MoveSpeedPenalty);`";
    }

    public static string DrankAdvice() =>
        $"{DoNotObsolete} PreferXML — own BaseLiquid.Drank belongs in Liquids.xml, not a C# override (do not bump StringBuilder→TextBuilder to keep it). " +
        "ApiMigrator LiquidDrankToPartFixer under -Apply: static `Message.Compound(\"…\"); return true;` → `<part Name=\"MessageOnDrink\" Message=\"…\" />`; " +
        "other bodies → `XRL.Liquids.Parts.*OnDrink : BaseLiquidPart` with `Drank(ref DrankEvent E)` plus `<part Name=\"…OnDrink\" Class=\"…OnDrink\" />`. " +
        "Vanilla liquid types (LiquidBlood, …): PreferHarmony Prefix/Postfix or overlay a part on the existing liquid Name. Do not add [Obsolete].";

    public static string CalendarCamelAdvice(string shortName)
    {
        var pascal = shortName switch
        {
            "getDay" => "GetDay",
            "getMonth" => "GetMonth",
            "getYear" => "GetYear",
            "getTime" => "GetTime",
            _ => char.ToUpperInvariant(shortName[0]) + shortName[1..],
        };
        var extra = shortName == "getTime"
            ? " All overloads rename: getTime()/getTime(zoneID)/getTime(int) → GetTime(...)."
            : " ApiMigrator auto-rewrites under -Apply.";
        if (shortName == "getDay")
            extra += " For message/Popup/journal strings, prefer GameText `=time.day=` (see Calendar.GetDay advice); computation/UI may keep GetDay().";
        return $"{DoNotObsolete} Calendar.{shortName} → `Calendar.{pascal}(`.{extra}";
    }

    public static string CalendarGetDayAdvice() =>
        $"{DoNotObsolete} Calendar.GetDay is still callable for computation/UI — do not blanket-replace with GameText. " +
        "For message/Popup/journal strings: `\"=time.day=\".StartReplace().ToString()` (needs `using XRL.World.Text`); " +
        "with a day-of-year/time arg: `.SetArgument(\"time\", expr)`. " +
        "ApiMigrator does not auto-rewrite GetDay() → =time.day= (too broad).";

    public static bool IsGameObjectArticleOrPronoun(string shortName) =>
        shortName is "a" or "A" or "an" or "An" or "the" or "The" or "t" or "T"
            or "it" or "It" or "its" or "Its" or "itself" or "Itself"
            or "Itis" or "itis" or "Tis" or "tis"
            or "Does" or "does"
            or "Them" or "them" or "They" or "they"
            or "Their" or "their" or "Theirs" or "theirs"
            or "Is" or "are" or "Has";

    public static string GameObjectGameTextAdvice(string shortName, string obsoleteMessage)
    {
        var fallback = shortName switch
        {
            "a" or "an" => "=GameObject.a= / =GameObject.a.name=",
            "A" or "An" => "=GameObject.A= / =GameObject.A.name=",
            "the" => "=GameObject.the=",
            "The" => "=GameObject.The=",
            "t" or "T" => "=GameObject.t= (short name; prefer typed templates)",
            "it" => "=GameObject.it= / =GameObject.subjective=",
            "It" => "=GameObject.It= / =GameObject.Subjective=",
            "its" => "=GameObject.its= / =GameObject.their=",
            "Its" => "=GameObject.Its= / =GameObject.Their=",
            "Does" => "=object.Does:verb=",
            "does" => "=object.does:verb=",
            "Itis" or "itis" => $"=GameObject.{shortName}=",
            _ => $"=GameObject.{shortName}=",
        };
        var token = string.IsNullOrWhiteSpace(obsoleteMessage) ? fallback : obsoleteMessage.Trim();
        var extra = shortName is "Itis" or "itis"
            ? " Common combo: \"=subject.Itis= =subject.a.name=!\".StartReplace().SetSubject(obj)."
            : "";
        return $"{DoNotObsolete} Replace GameObject.{shortName} string helpers with GameText templates ({token}) inside EmitMessage / ReplaceBuilder / _T / StartReplace — " +
               "not StringBuilder concatenation. Wire the object via SetSubject/SetObject/SetArgument. Never auto-rewrite — call shape and alias differ per site." +
               extra;
    }

    public static string GetLongDescriptionAdvice() =>
        $"{DoNotObsolete} GetLongDescription(StringBuilder) → GetLongDescription(TextBuilder) (`using XRL.World.Text;`). " +
        "Report-only: Harmony patches must update `[HarmonyPatch(…, new Type[] {{ typeof(TextBuilder) }})]` (or MethodType) to match the live signature — " +
        "a StringBuilder Type[] no longer binds. Overrides/postfix params similarly. Do not blind-regex Harmony attributes.";

    public static string BaseMutationDisplayNameAdvice(string shortName) =>
        shortName switch
        {
            "DisplayName" or "_DisplayName" =>
                $"{DoNotObsolete} PreferXML — BaseMutation.DisplayName setter / _DisplayName → Mutations.xml same-Name `DisplayName=\"…\"` (MutationEntry.HandleXMLNode). " +
                "For reads use `GetDisplayName()` (not autofix: setters/overrides must stay PreferXML). Do not rewrite `.DisplayName =` to GetDisplayName().",
            "Type" or "_Type" =>
                $"{DoNotObsolete} PreferXML — BaseMutation.Type setter / _Type → Mutations.xml `Type=\"…\"` (or category Name). Reads: `GetMutationType()`. Keep C# BaseMutation class for Class= resolution.",
            _ => PreferXmlAdvice("DisplayName"),
        };

    public static string DidXEmitMessageAdvice(string shortName) =>
        $"{DoNotObsolete} {shortName} → ReplaceBuilder.EmitMessage / GameText templates (`=subject.Does:verb=`, `=object.the.name=`, `=object.aForNPCSubject.name=`, …) with SetSubject/SetObject — " +
        "not StringBuilder + GameObject.t/Does helpers. Liquid transfers often use `=liquid.cardinal.drams.of.liquid#amount|strip=` (SetArgument liquid/amount) instead of Grammar.Cardinal concat. " +
        "Arg mapping is site-specific (Verb, Extra, ColorAsGoodFor, FromDialog, …). " +
        "ApiMigrator auto-fixes simple DidX/XDidY/DidXToY with a string-literal verb (trailing null/bool/color defaults ignored) under -Apply. " +
        "Concatenated Extra / GameObject.Does stay for Ollama suggest or hand rewrite. Example:\n" +
        "  \"=subject.Does:transfer= … to =object.aForNPCSubject.name=\".StartReplace().SetSubject(actor).SetObject(target).EmitMessage(FromDialog: true);";

    public static string NamespaceVsTypeAdvice(string typeName) =>
        $"{DoNotObsolete} Possible CS0118 (namespace vs type). Qualify the mutation type explicitly, e.g. `XRL.World.Parts.Mutation.{typeName}`, or remove a `using` that imports a namespace ending in `{typeName}`. Never silence with [Obsolete].";

    public static string RemovedGameTypeAdvice(string typeName, string kind) =>
        $"{DoNotObsolete} `{typeName}` was removed from the game ({(string.IsNullOrWhiteSpace(kind) ? "deleted API" : kind)}). " +
        "Do not `typeof()` it. Harmony: `[HarmonyPatch]` + `Prepare()`/`TargetMethod()` with `AccessTools.TypeByName(\"Full.Name\")` " +
        "(return false / null when missing so PatchAll skips). Call sites that constructed or subclassed the minigame should use the vanilla fallback " +
        "(stats-only text, skip the minigame, keep the original roll). ApiMigrator auto-converts simple HarmonyPatch(typeof) and strips `if (Options.Sifrah*)` blocks under -Apply.";

    public static string RemovedSifrahOptionAdvice() =>
        $"{DoNotObsolete} `Options.Sifrah*` / `Options.AnySifrah` were removed with minigames. Delete the branch (vanilla Lovesick/Domination no longer call Sifrah) or treat the flag as false. ApiMigrator strips `if (Options.Sifrah*) {{ … }}` under -Apply.";
    public static string PreferHarmonyAdvice(string memberName)
    {
        if (memberName == "Register")
        {
            return $"{DoNotObsolete} PreferHarmonyPatch — remove the obsolete Register(GameObject) override when feasible; use safer Harmony Prefix/Postfix for event registration. Only keep Register(GameObject, IEventRegistrar) if there is no other option (ApiMigrator can auto-bump simple RegisterPartEvent bodies as a last resort under -Apply). Example Harmony:\n" +
                   OverridePreferenceScanner.HarmonyStubTemplate("IPart", "Register") +
                   "\nLast-resort override shape:\n" +
                   "  public override void Register(GameObject Object, IEventRegistrar Registrar) {\n" +
                   "    Registrar.Register(\"YourEvent\");\n" +
                   "    base.Register(Object, Registrar);\n" +
                   "  }";
        }

        if (memberName == "Drank")
            return $"{DoNotObsolete} PreferHarmonyPatch — vanilla liquid Drank (LiquidBlood, …) is Prefix/Postfix, not a signature bump. Overlay a Liquids.xml part on the existing Name when the drink effect can be a part. Do not add [Obsolete].";

        if (memberName is "WantHundredTurnTick" or "WantTenTurnTick" or "HundredTurnTick" or "TenTurnTick")
            return TurnTickAdvice(memberName);

        if (memberName == "FinalRender")
            return FinalRenderAdvice();

        if (memberName is "LoadGame" or "SaveGame")
            return GameSystemSerializeAdvice(memberName);

        return $"{DoNotObsolete} PreferHarmonyPatch — prefer safer Harmony Prefix/Postfix on {memberName} over rewriting/keeping the override when extending game behavior. C# override only when there is no other option (required abstract/interface, or no XML/Harmony path). See coq-prefer-xml-then-harmony.";
    }

    public static string ShowOptionListAdvice(bool async)
    {
        var oldName = async ? "ShowOptionListAsync" : "ShowOptionList";
        var newName = async ? "PickOptionAsync" : "PickOption";
        return $"{DoNotObsolete} Replace Popup.{oldName} with Popup.{newName}. Parameter order differs — prefer named arguments. Suggested shape:\n" +
               $"  Popup.{newName}(\n" +
               "    Title: title,\n" +
               "    Options: options,\n" +
               "    Hotkeys: hotkeys,\n" +
               "    Intro: intro,\n" +
               "    AllowEscape: true);\n" +
               "Named-arg remaps: onResult→OnResult, context→Context, centerIntro→CenterIntro, centerIntroIcon→CenterIntroIcon, iconPosition→IconPosition, forceNewPopup→ForceNewPopup. PickOption also has Sound / PopupLocation / PopupID (defaults OK).";
    }
}
