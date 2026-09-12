using ApiMigrator.Core;

// Lightweight smoke checks (vstest parent-process watch fails on this host).
// Run: dotnet run -c Release --project ApiMigrator.Core.Tests

static string FindToolsRoot()
{
    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir != null)
    {
        if (File.Exists(Path.Combine(dir.FullName, "data", "curated_rewrite_rules.json")))
            return dir.FullName;
        dir = dir.Parent;
    }
    throw new DirectoryNotFoundException("Could not locate _tools/data from " + AppContext.BaseDirectory);
}

static void Assert(bool condition, string message)
{
    if (!condition) throw new Exception("ASSERT: " + message);
}

static void AssertContains(string haystack, string needle, string label)
{
    Assert(haystack.Contains(needle, StringComparison.Ordinal), $"{label}: missing '{needle}'\n---\n{haystack}");
}

static void AssertNotContains(string haystack, string needle, string label)
{
    Assert(!haystack.Contains(needle, StringComparison.Ordinal), $"{label}: unexpectedly contains '{needle}'");
}

var toolsRoot = FindToolsRoot();
var engine = new RuleEngine(
    DumpStore.LoadRules(Path.Combine(toolsRoot, "data", "curated_rewrite_rules.json")),
    DumpStore.LoadDump(Path.Combine(toolsRoot, "data", "obsolete_api_dump.json")));

// UsingInserter basics
{
    var (r, inserted) = UsingInserter.EnsureUsings(
        "using System;\r\nusing XRL.World;\r\n\r\nnamespace N;\r\n",
        new[] { "XRL.World.Text" });
    Assert(inserted.SequenceEqual(new[] { "XRL.World.Text" }), "insert list");
    AssertContains(r, "using XRL.World.Text;", "insert using");
}

{
    var (r, inserted) = UsingInserter.EnsureUsings(
        "namespace XRL.World.Parts;\r\nclass C { }\r\n",
        new[] { "XRL" });
    Assert(inserted.Count == 0, "enclosing XRL skip");
    AssertNotContains(r, "using XRL;", "no redundant using XRL under XRL.World.Parts");
}

// NewStringBuilder + using
{
    const string src = """
        using System;
        using XRL.World;

        namespace XRL.World.Parts;

        class C {
          void M() {
            var sb = Event.NewStringBuilder();
          }
        }
        """;
    var (result, fixes) = engine.ApplyCuratedRules(src, "Foo.cs");
    AssertContains(result, "TextBuilder.Get()", "rewrite");
    AssertNotContains(result, "Event.NewStringBuilder", "old API gone");
    AssertContains(result, "using XRL.World.Text;", "using added");
    Assert(fixes.Any(f => f.RuleName.Contains("NewStringBuilder", StringComparison.Ordinal)), "fix recorded");
    Assert(fixes.Any(f => f.RuleName.StartsWith("ensure using:", StringComparison.Ordinal)), "using fix recorded");
}

// Wrong FQN + StringBuilder assign
{
    const string src = """
        using System.Text;
        using XRL.World;

        namespace N;

        class C {
          void M() {
            StringBuilder sb = XRL.World.TextBuilder.Get();
          }
        }
        """;
    var (result, _) = engine.ApplyCuratedRules(src, "Foo.cs");
    AssertNotContains(result, "XRL.World.TextBuilder", "wrong FQN gone");
    AssertContains(result, "TextBuilder sb = TextBuilder.Get()", "typed local fixed");
    AssertContains(result, "using XRL.World.Text;", "using added");
}

// Post-ensure heals bare TextBuilder
{
    const string src = """
        using System;

        namespace N;

        class C {
          void M() {
            var sb = TextBuilder.Get();
          }
        }
        """;
    var (result, fixes) = engine.ApplyCuratedRules(src, "Foo.cs");
    AssertContains(result, "using XRL.World.Text;", "post-ensure using");
    Assert(fixes.Any(f => f.RuleName.StartsWith("ensure using:", StringComparison.Ordinal)), "post-ensure fix");
}

// XML skips usings
{
    const string src = """
        <objects>
          <part Text="Event.NewStringBuilder()" />
        </objects>
        """;
    var (result, fixes) = engine.ApplyCuratedRules(src, "Object.xml");
    AssertContains(result, "TextBuilder.Get()", "xml rewrite");
    AssertNotContains(result, "using ", "xml no using");
    Assert(!fixes.Any(f => f.RuleName.StartsWith("ensure using:", StringComparison.Ordinal)), "xml no using fix");
}

// GivesRep.AppendReputationDescription(StringBuilder) pattern
{
    const string src = """
        using System.Text;
        using XRL.World.Parts;

        namespace N;

        class C {
          void M(GivesRep givesRep) {
            StringBuilder SB = new();
            givesRep.AppendReputationDescription(SB);
            var repString = SB.ToString();
          }
        }
        """;
    var (result, fixes) = engine.ApplyCuratedRules(src, "YouSpotALegendary.cs");
    AssertContains(result, "using TextBuilder SB = TextBuilder.Get();", "TextBuilder local");
    AssertContains(result, "AppendReputationDescription(SB)", "call kept");
    AssertNotContains(result, "StringBuilder SB = new()", "StringBuilder alloc gone");
    AssertContains(result, "using XRL.World.Text;", "using added");
    Assert(fixes.Any(f => f.RuleName == AppendReputationDescriptionFixer.FixRuleName), "rep fix recorded");

    // Empty StringBuilder alloc alone must NOT hang (old curated regex ReDoS'd here).
    var sw = System.Diagnostics.Stopwatch.StartNew();
    var (noRep, noRepFixes) = engine.ApplyCuratedRules(
        "using System.Text;\nclass C { StringBuilder SB = new(); }\n", "NoRep.cs");
    sw.Stop();
    Assert(sw.ElapsedMilliseconds < 2000, "no-AppendReputation file finished quickly: " + sw.ElapsedMilliseconds + "ms");
    Assert(noRepFixes.All(f => f.RuleName != AppendReputationDescriptionFixer.FixRuleName), "no false rep rewrite");
    AssertContains(noRep, "StringBuilder SB = new()", "unrelated alloc left alone");

    // Dump must flag instance call sites (receiver.Append…), not only GivesRep.Append…
    var hits = engine.ScanRemainingHits("givesRep.AppendReputationDescription(SB);");
    Assert(hits.Any(h => h.Member.Contains("AppendReputationDescription", StringComparison.Ordinal)),
        "dump flags .AppendReputationDescription(");
}

// DerivePattern: instance methods use .Member(
{
    var inst = DumpRefresher.DerivePattern(new DiscoveredMember
    {
        Type = "XRL.World.Parts.GivesRep",
        Member = "AppendReputationDescription",
        Kind = "Method",
        Signature = "Void AppendReputationDescription(StringBuilder SB)",
    });
    Assert(inst == @"\.AppendReputationDescription\(", "instance DerivePattern: " + inst);

    var stat = DumpRefresher.DerivePattern(new DiscoveredMember
    {
        Type = "XRL.Language.Grammar",
        Member = "Cardinal",
        Kind = "Method",
        Signature = "static String Cardinal(Int32 Number)",
    });
    Assert(stat == @"Grammar\.Cardinal\(", "static DerivePattern: " + stat);

    var reg = DumpRefresher.DerivePattern(new DiscoveredMember
    {
        Type = "XRL.World.IPart",
        Member = "Register",
        Kind = "Method",
        Signature = "Void Register(GameObject Object)",
    });
    Assert(reg.Contains(@"[^,\)]+", StringComparison.Ordinal), "Register DerivePattern single-arg: " + reg);

    var rpe = DumpRefresher.DerivePattern(new DiscoveredMember
    {
        Type = "XRL.IEventRegistrar",
        Member = "RegisterPartEvent",
        Kind = "Method",
        Signature = "Void RegisterPartEvent(IPart Ef, String Event)",
    });
    Assert(rpe.Contains("Registrar", StringComparison.Ordinal), "RegisterPartEvent DerivePattern: " + rpe);
}

// False-positive suppressions: modern Register / AppendRules(string) / GameText / comments
{
    const string modern = """
        class C : IPart {
          public override void Register(GameObject Object, IEventRegistrar Registrar) {
            Registrar.Register("Equipped");
            base.Register(Object, Registrar);
            E.PostFix.AppendRules(GetDescription());
            return base.GetDescription() + "x";
            equipped.RegisterPartEvent(this, "Command");
            Reader.ReadString();
            E.AddAction(new InventoryAction { Name = "X" });
            Popup.Show($"=subject.The={name}");
            // ParentObject.the was obsolete
          }
        }
        """;
    var hits = engine.ScanRemainingHits(modern);
    Assert(!hits.Any(h => h.Member.Contains("IPart.Register", StringComparison.Ordinal)
            || h.Member.Contains("Effect.Register", StringComparison.Ordinal)),
        "modern Register not flagged: " + string.Join("; ", hits.Select(h => h.Member + ":" + h.Text)));
    Assert(!hits.Any(h => h.Member.Contains("AppendRules", StringComparison.Ordinal)),
        "AppendRules(string) not flagged");
    Assert(!hits.Any(h => h.Member.Contains("IStingerProperties.GetDescription", StringComparison.Ordinal)),
        "unrelated GetDescription not flagged");
    Assert(!hits.Any(h => h.Member.Contains("RegisterPartEvent", StringComparison.Ordinal)),
        "GameObject.RegisterPartEvent not flagged");
    Assert(!hits.Any(h => h.Member.Contains("ReadString", StringComparison.Ordinal)),
        "Reader.ReadString not flagged");
    Assert(!hits.Any(h => h.Member.Contains("AddAction", StringComparison.Ordinal)),
        "AddAction(InventoryAction) not flagged");
    Assert(!hits.Any(h => h.Member.Contains("GameObject.The", StringComparison.Ordinal)
            || h.Member.Contains("GameObject.the", StringComparison.Ordinal)),
        "GameText =subject.The= / comment .the not flagged");

    // Prior // lines must not poison later comment detection
    const string commentedBlock = """
        class C {
          void M() {
            // earlier comment
            // ParentObject.the
            // E.AddAction("Kiss", 'k', false, "x", "y");
            var ok = 1;
          }
        }
        """;
    var commentedHits = engine.ScanRemainingHits(commentedBlock);
    Assert(!commentedHits.Any(h => h.Member.Contains("GameObject.the", StringComparison.Ordinal)),
        "commented .the not flagged after prior //");
    Assert(!commentedHits.Any(h => h.Member.Contains("AddAction", StringComparison.Ordinal)),
        "commented AddAction not flagged after prior //");
}

// Real obsolete single-arg Register and string AddAction still match
{
    const string obsolete = """
        class C : IPart {
          public override void Register(GameObject Object) {
            base.Register(Object);
            Registrar.RegisterPartEvent(this, "Foo");
            E.AddAction("Name", 'k', true, "Display", "Command");
            var t = ParentObject.The;
            sb.AppendRules(s => s.Append("x"));
          }
          bool HandleEvent(IInventoryActionsEvent E) => true;
        }
        """;
    var hits = engine.ScanRemainingHits(obsolete);
    Assert(hits.Any(h => h.Member.Contains("Register", StringComparison.Ordinal) && h.Text.Contains("base.Register(Object)")),
        "obsolete base.Register(Object) flagged");
    Assert(hits.Any(h => h.Member.Contains("RegisterPartEvent", StringComparison.Ordinal)),
        "Registrar.RegisterPartEvent flagged");
    Assert(hits.Any(h => h.Member.Contains("AddAction", StringComparison.Ordinal)),
        "string AddAction flagged");
    Assert(hits.Any(h => h.Member.Contains("GameObject.The", StringComparison.Ordinal)),
        "ParentObject.The flagged");
    Assert(hits.Any(h => h.Member.Contains("AppendRules", StringComparison.Ordinal)),
        "AppendRules(lambda) flagged");
}

// CP437 → UTF16: C# escapes
{
    const string src = """
        class C {
          string S = "{{r|\x03}} {{c|\x1A}} {{k|\xEC}}";
          char H = '\u0003';
          char N = '\u000d';
          string Tab = "{{K|\t}}";
        }
        """;
    var tmp = Path.Combine(toolsRoot, "reports", "_smoke_cp437_" + Guid.NewGuid().ToString("N"));
    Directory.CreateDirectory(tmp);
    var csPath = Path.Combine(tmp, "Glyphs.cs");
    File.WriteAllText(csPath, src);

    var report = Cp437Converter.Run(new Cp437Converter.Options
    {
        Paths = new List<string> { tmp },
        Apply = false,
        ConvertAmbiguousEscapes = false,
        // Smoke dir lives under _tools\reports; default excludes skip \_tools\.
        ExcludeDirs = new List<string> { "bin", "obj", ".git" },
    });
    Assert(report.FileResults.Count == 1, "cp437 one file (got " + report.FileResults.Count + ", scanned " + report.FilesScanned + ")");
    var fr = report.FileResults[0];
    Assert(fr.NewContent != null, "cp437 has new content");
    AssertContains(fr.NewContent!, "♥", "heart");
    AssertContains(fr.NewContent!, "→", "arrow");
    AssertContains(fr.NewContent!, "∞", "infinity from \\xEC");
    AssertContains(fr.NewContent!, "♪", "note from \\u000d");
    AssertContains(fr.NewContent!, @"\t", "tab escape preserved by default");
    Assert(fr.Hits.Any(h => h.NeedsReview && h.From.Contains("\\t")), "tab flagged for review");
    Assert(fr.AutoFixCount >= 4, "cp437 auto-fixes: " + fr.AutoFixCount);

    // XML entities + Encoding
    var xmlPath = Path.Combine(tmp, "Objects.xml");
    File.WriteAllText(xmlPath, "<objects>\n  <object Name=\"X\" RenderString=\"&#x3;\" />\n</objects>\n");
    var xmlReport = Cp437Converter.Run(new Cp437Converter.Options
    {
        Paths = new List<string> { tmp },
        ModFilter = "Objects.xml",
        Apply = false,
        EnsureXmlUtf8Encoding = true,
        ExcludeDirs = new List<string> { "bin", "obj", ".git" },
    });
    Assert(xmlReport.FileResults.Count == 1, "xml one file");
    var xr = xmlReport.FileResults[0];
    AssertContains(xr.NewContent!, "♥", "xml heart");
    AssertContains(xr.NewContent!, "Encoding=\"utf-8\"", "xml encoding");

    // Encoding-only (no CP437 glyphs) — still stamps root Encoding
    var encOnlyPath = Path.Combine(tmp, "Books.xml");
    File.WriteAllText(encOnlyPath, "<books>\n  <book Name=\"A\">hi</book>\n</books>\n");
    var encOnlyReport = Cp437Converter.Run(new Cp437Converter.Options
    {
        Paths = new List<string> { tmp },
        ModFilter = "Books.xml",
        Apply = false,
        EnsureXmlUtf8Encoding = true,
        ExcludeDirs = new List<string> { "bin", "obj", ".git" },
    });
    Assert(encOnlyReport.FileResults.Count == 1, "encoding-only one file");
    AssertContains(encOnlyReport.FileResults[0].NewContent!, "Encoding=\"utf-8\"", "encoding-only stamp");
    Assert(encOnlyReport.FileResults[0].Hits.Any(h => h.Kind == "xml-encoding"), "encoding-only hit");

    try { Directory.Delete(tmp, true); } catch { /* best-effort */ }
}

// ObjectBlueprint inventoryobject Name= → Blueprint=
{
    const string bad = """
        <objects>
          <object Name="BasePlantera">
            <inventoryobject Name="Qudzu_Frond" Number="1d2" />
            <removeinventoryobject Name="Qudzu_Frond"/>
            <inventoryobject Blueprint="AlreadyOk" Number="1" />
          </object>
        </objects>
        """;
    var (fixedXml, fixes) = ObjectBlueprintXmlFixer.Fix(bad);
    Assert(fixes.Count == 1 && fixes[0].Count == 2, "inventoryobject Name→Blueprint count");
    AssertContains(fixedXml, "Blueprint=\"Qudzu_Frond\"", "inventoryobject Blueprint");
    AssertContains(fixedXml, "<removeinventoryobject Blueprint=\"Qudzu_Frond\"/>", "removeinventoryobject Blueprint");
    AssertContains(fixedXml, "Blueprint=\"AlreadyOk\"", "existing Blueprint kept");
    AssertNotContains(fixedXml, "inventoryobject Name=", "no leftover Name on inventoryobject");

    var (enc, encFixes) = XmlUtf8EncodingFixer.Ensure(fixedXml);
    Assert(encFixes.Count == 1, "encoding fix recorded");
    AssertContains(enc, "<objects Encoding=\"utf-8\"", "objects root encoding");
}

// ObjectBlueprintXmlFixer: Wire/Projectile/Examiner attrs, MutationOnEquip, mutation renames, anim alternate
{
    const string bad = """
        <objects>
          <object Name="Tube">
            <part Name="Wire" Material="glass" NameColor="&amp;Y" />
            <part Name="Projectile" BaseDamage="1d6" RequiresPhaseMatch="false" PassByVerb="streak" />
            <part Name="Examiner" AlternateDisplayName="jumpsuit" Complexity="6" />
            <part Name="MutationOnEquip" ClassName="Narcolepsy" Describe="false" />
            <mutation Name="FlamingHands" Level="4" />
            <mutation Name="Double-muscled" Level="3" />
            <mutation Name="TwoHearted " Level="3" />
            <part Name="AnimatedMaterialGeneric" DetailColorAnimationFrames="0=o" />
            <part Name="AnimatedMaterialGeneric" TileAnimationFrames="0=a.png" />
          </object>
          <object Name="Tube2">
            <part Name="MutationOnEquip" ClassName="Telepathy" Mutation="Telepathy" Variant="x" />
          </object>
        </objects>
        """;
    var (fixedXml, fixes) = ObjectBlueprintXmlFixer.Fix(bad);
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.WireMaterialRuleName), "Wire Material strip");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.ProjectilePhaseMatchRuleName), "Projectile phase strip");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.ExaminerAlternateDisplayNameRuleName), "Examiner AlternateDisplayName strip");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MutationOnEquipClassNameRuleName), "MutationOnEquip ClassName");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MutationOnEquipVariantRuleName), "MutationOnEquip Variant");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MutationNameRenameRuleName), "mutation renames");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.NameTrimRuleName), "Name trim");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.AnimatedMaterialAlternateRuleName), "anim alternate");
    AssertNotContains(fixedXml, "Material=", "Wire Material gone");
    AssertNotContains(fixedXml, "RequiresPhaseMatch=", "RequiresPhaseMatch gone");
    AssertNotContains(fixedXml, "AlternateDisplayName=", "AlternateDisplayName gone");
    AssertContains(fixedXml, "Mutation=\"Narcolepsy\"", "ClassName→Mutation");
    AssertContains(fixedXml, "Mutation=\"Telepathy\"", "Telepathy Mutation kept");
    AssertNotContains(fixedXml, "ClassName=", "ClassName gone");
    AssertNotContains(fixedXml, "Variant=", "Variant gone");
    AssertContains(fixedXml, "Name=\"FlamingRay\"", "FlamingHands→FlamingRay");
    AssertContains(fixedXml, "Name=\"HeightenedStrength\"", "Double-muscled→HeightenedStrength");
    AssertContains(fixedXml, "Name=\"TwoHearted\"", "TwoHearted trimmed");
    AssertContains(fixedXml, "Name=\"AnimatedMaterialGenericAlternate\"", "second anim → Alternate");
    AssertContains(fixedXml, "Complexity=\"6\"", "Examiner Complexity kept");
}

// ObjectBlueprintXmlFixer: obsolete attrs, ElementalDamage part, Value=*delete, role, Compat blueprint, duplicates
{
    const string bad = """
        <objects>
          <object Name="Doru" Load="Merge">
            <part Name="MeleeWeapon" RenderString="/" SecondaryStat="Agility" BaseDamage="1d4" ElementalDamage="1d8" Element="Poison" />
            <part Name="Corpse" BodyDrop="false" InventoryDrop="true" CorpseChance="10" />
            <part Name="Brain" Hostile="false" IgnoreCombat="true" />
            <part Name="Physics" Solid="false" Occluding="false" />
            <part Name="acegiak_Seed" Result="Watervine" Chance="0" />
            <part Name="Comwmerce" Value="25" />
            <mutation Name="FreezingHands" Level="4" />
            <mutation Name="Sleep Gas Generation" Level="6" />
            <mutation Name="Albino" Value="*delete" />
            <tag Name="Role" Value="Minion" />
            <role Name="Skirmisher" />
            <tag Name="ExcludeFromDynamicEncounters" />
            <tag Name="ExcludeFromDynamicEncounters" />
            <part Name="CyberneticsHasImplants" Implants="PenetratingRadar@head" />
            <part Name="CyberneticsHasImplants" Implants="GiantHands@hands" />
          </object>
          <object Name="JoppaZealot" Inherits="Doru" Load="Merge" />
        </objects>
        """;
    var (fixedXml, fixes) = ObjectBlueprintXmlFixer.Fix(bad);
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.ObsoletePartAttrRuleName), "obsolete attr strip");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MeleeWeaponSecondaryStatRuleName), "SecondaryStat");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MeleeWeaponElementalRuleName), "ElementalDamage part");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MutationValueDeleteRuleName), "Value=*delete");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.RoleElementRuleName), "role element");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.BlueprintNameRenameRuleName), "blueprint Compat rename");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.DuplicateNamedChildRuleName), "duplicate merge");
    Assert(fixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.CommerceTypoRuleName), "Comwmerce typo");
    AssertNotContains(fixedXml, "RenderString=", "MeleeWeapon RenderString gone");
    AssertNotContains(fixedXml, "SecondaryStat=", "SecondaryStat gone");
    AssertNotContains(fixedXml, "BodyDrop=", "BodyDrop gone");
    AssertNotContains(fixedXml, "InventoryDrop=", "InventoryDrop gone");
    AssertNotContains(fixedXml, "IgnoreCombat=", "IgnoreCombat gone");
    AssertNotContains(fixedXml, "Occluding=", "Physics Occluding gone");
    AssertNotContains(fixedXml, " Chance=\"0\"", "acegiak_Seed Chance gone");
    AssertNotContains(fixedXml, "ElementalDamage=\"", "MeleeWeapon ElementalDamage attr gone");
    AssertNotContains(fixedXml, " Element=\"", "MeleeWeapon Element attr gone");
    AssertContains(fixedXml, "Stat=\"Agility\"", "SecondaryStat→Stat");
    AssertContains(fixedXml, "Name=\"ElementalDamage\"", "ElementalDamage part added");
    AssertContains(fixedXml, "Damage=\"1d8\"", "ElementalDamage Damage");
    AssertContains(fixedXml, "Attributes=\"Poison\"", "ElementalDamage Attributes");
    AssertContains(fixedXml, "Name=\"FreezingRay\"", "FreezingHands→FreezingRay");
    AssertContains(fixedXml, "Name=\"SleepGasGeneration\"", "Sleep Gas→SleepGasGeneration");
    AssertContains(fixedXml, "<removemutation Name=\"Albino\" />", "removemutation");
    AssertNotContains(fixedXml, "<role ", "role element gone");
    AssertContains(fixedXml, "Name=\"Tam\"", "Doru→Tam");
    AssertContains(fixedXml, "Name=\"VillageZeroConvert\"", "JoppaZealot→VillageZeroConvert");
    AssertContains(fixedXml, "Inherits=\"Tam\"", "Inherits Doru→Tam");
    AssertContains(fixedXml, "Name=\"Commerce\"", "Comwmerce→Commerce");
    AssertContains(fixedXml, "Implants=\"PenetratingRadar@head,GiantHands@hands\"", "implants joined");
    // Role tag kept (Minion); role Skirmisher dropped because Role already present
    AssertContains(fixedXml, "Value=\"Minion\"", "Role Minion kept");
    AssertNotContains(fixedXml, "Skirmisher", "role Skirmisher dropped");
    // Self-close preserved after duplicate merge / attr strips
    Assert(System.Text.RegularExpressions.Regex.IsMatch(fixedXml, @"<part Name=""Brain""[^>]*/>"), "Brain remains self-closing");
    Assert(System.Text.RegularExpressions.Regex.IsMatch(fixedXml, @"<tag Name=""ExcludeFromDynamicEncounters""\s*/>"), "Exclude tag self-closing");
}

// Reported workshop regressions: Icy Glaciers duplicate Corpse and Gladiators MutationOnEquip.
{
    const string icyGlaciers = """
        <objects>
          <object Name="Wiz_SnowBear" Inherits="BaseBear">
            <part Name="Corpse" CorpseChance="0" />
            <mutation Name="Carnivorous" />
            <part Name="Corpse" CorpseChance="50" CorpseBlueprint="Wiz_SnowBearCorpse" />
          </object>
        </objects>
        """;
    var (icyFixed, icyFixes) = ObjectBlueprintXmlFixer.Fix(icyGlaciers);
    Assert(icyFixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.DuplicateNamedChildRuleName && f.Count == 1),
        "Icy Glaciers duplicate Corpse merged");
    Assert(icyFixed.Split("<part Name=\"Corpse\"", StringSplitOptions.None).Length - 1 == 1,
        "Icy Glaciers has one Corpse part");
    AssertContains(icyFixed, "CorpseChance=\"50\"", "Icy Glaciers later CorpseChance wins");
    AssertContains(icyFixed, "CorpseBlueprint=\"Wiz_SnowBearCorpse\"", "Icy Glaciers corpse blueprint kept");

    const string gladiators = """
        <objects>
          <object Name="Kai Seeker Tonic">
            <part Name="MutationOnEquip" ClassName="Precognition" Level="30" Describe="false" />
          </object>
          <object Name="Kai Temporal Helm">
            <part Name="MutationOnEquip" ClassName="TemporalFugue" Level="30" />
          </object>
        </objects>
        """;
    var (gladiatorsFixed, gladiatorsFixes) = ObjectBlueprintXmlFixer.Fix(gladiators);
    Assert(gladiatorsFixes.Any(f => f.RuleName == ObjectBlueprintXmlFixer.MutationOnEquipClassNameRuleName && f.Count == 2),
        "Gladiators MutationOnEquip ClassName migrated");
    AssertNotContains(gladiatorsFixed, "ClassName=", "Gladiators ClassName removed");
    AssertContains(gladiatorsFixed, "Mutation=\"Precognition\"", "Gladiators Precognition mutation retained");
    AssertContains(gladiatorsFixed, "Mutation=\"TemporalFugue\"", "Gladiators TemporalFugue mutation retained");
}

// Trailing IPart after helpers → split into XRL.World.Parts
{
    const string mixed = """
        using System;
        using XRL.World;
        using XRL.World.Parts;

        namespace COQMAN.ScrapGraveKing
        {
            public static class COQMAN_UrsaaLoadoutHelper
            {
                public static void Apply(GameObject obj) { }
            }

            [Serializable]
            public partial class COQMAN_UrsaaLoadout : IPart
            {
                public override void Attach()
                {
                    COQMAN_UrsaaLoadoutHelper.Apply(ParentObject);
                }
            }
        }
        """;
    var (fixedCs, nsFixes, moved) = BlueprintTypeNamespaceFixer.FixFile(mixed);
    Assert(nsFixes.Any(f => f.RuleName == BlueprintTypeNamespaceFixer.FixRuleNamePart), "trailing part split");
    AssertContains(fixedCs, "namespace COQMAN.ScrapGraveKing", "helper ns kept");
    AssertContains(fixedCs, "namespace XRL.World.Parts", "part ns");
    AssertContains(fixedCs, "using COQMAN.ScrapGraveKing", "helper using for Parts");
    Assert(moved.Any(m => m.Type == "COQMAN_UrsaaLoadout" && m.TargetNs == BlueprintTypeNamespaceFixer.PartsNs), "moved type");
}

// IPart in custom namespace → XRL.World.Parts (ObjectBlueprintLoader ResolveType)
{
    const string partsFile = """
        using System;
        using XRL.World;
        using XRL.World.Parts;

        namespace COQMAN.HiddenHamlet
        {
            [Serializable]
            public class COQMAN_SurfaceElderTracker : IPart
            {
            }
        }

        namespace COQMAN.HiddenHamlet
        {
            [Serializable]
            public class COQMAN_SaltHorrorTargeting : IPart
            {
            }
        }
        """;
    const string helperFile = """
        using XRL.World;

        namespace COQMAN.HiddenHamlet
        {
            public static class HamletElderSurface
            {
                public static void Ensure(GameObject obj)
                {
                    if (obj.GetPart<COQMAN_SurfaceElderTracker>() == null)
                        obj.AddPart(new COQMAN_SurfaceElderTracker());
                }
            }
        }
        """;

    var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        ["HamletParts.cs"] = partsFile,
        ["HamletElderSurface.cs"] = helperFile,
    };
    var nsResult = BlueprintTypeNamespaceFixer.FixMod(map);
    Assert(nsResult.UpdatedContents.ContainsKey("HamletParts.cs"), "parts file updated");
    AssertContains(nsResult.UpdatedContents["HamletParts.cs"], "namespace XRL.World.Parts", "parts ns");
    AssertNotContains(nsResult.UpdatedContents["HamletParts.cs"], "namespace COQMAN.HiddenHamlet", "old ns gone");
    Assert(nsResult.UpdatedContents.ContainsKey("HamletElderSurface.cs"), "helper got using");
    AssertContains(nsResult.UpdatedContents["HamletElderSurface.cs"], "using XRL.World.Parts;", "helper using Parts");
    // Full IPart ns rename must also keep using for the OLD namespace (sibling types stay there).
    AssertContains(nsResult.UpdatedContents["HamletParts.cs"], "using COQMAN.HiddenHamlet;", "moved parts keep old-ns using");
}

// Full-file IPart rename: preserve using for helper types left in old ns (ThreadingAPI bug)
{
    const string memoryPart = """
        using System;
        using System.Collections.Generic;
        using XRL.World;
        using XRL.World.Parts;

        namespace ThreadingAPI
        {
            [Serializable]
            public class EnhancedAIMemoryPart : IPart
            {
                public AIPersonality Personality { get; set; }
                public static EnhancedAIMemoryPart GetOrCreate(GameObject obj)
                {
                    WorkerThreadGuard.RequireMainThread("x");
                    return null;
                }
            }
        }
        """;
    const string helpers = """
        namespace ThreadingAPI
        {
            public class AIPersonality { }
            public static class WorkerThreadGuard
            {
                public static void RequireMainThread(string op) { }
            }
        }
        """;
    var map2 = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        ["EnhancedAIMemoryPart.cs"] = memoryPart,
        ["Helpers.cs"] = helpers,
    };
    var ns2 = BlueprintTypeNamespaceFixer.FixMod(map2);
    AssertContains(ns2.UpdatedContents["EnhancedAIMemoryPart.cs"], "namespace XRL.World.Parts", "memory part moved");
    AssertContains(ns2.UpdatedContents["EnhancedAIMemoryPart.cs"], "using ThreadingAPI;", "old ns using after move");
}

// Partial siblings without : IPart must move with the primary partial (Broodmother Commands)
{
    const string core = """
        using System;
        using XRL.World;
        using XRL.World.Parts;

        namespace XRL.World.Parts.Mutation
        {
            [Serializable]
            public partial class Arendeth_BroodmotherCommands : IPart
            {
                public int AttackCooldown;
            }
        }
        """;
    const string ai = """
        using XRL.World;
        using XRL.World.Parts;

        namespace XRL.World.Parts.Mutation
        {
            public partial class Arendeth_BroodmotherCommands
            {
                void Tick() { AttackCooldown--; }
            }
        }
        """;

    var mapPartial = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        ["Commands_Core.cs"] = core,
        ["Commands_AI.cs"] = ai,
    };
    var nsPartial = BlueprintTypeNamespaceFixer.FixMod(mapPartial);
    Assert(nsPartial.UpdatedContents.ContainsKey("Commands_Core.cs"), "core updated");
    Assert(nsPartial.UpdatedContents.ContainsKey("Commands_AI.cs"), "AI partial updated");
    Assert(System.Text.RegularExpressions.Regex.IsMatch(
            nsPartial.UpdatedContents["Commands_Core.cs"],
            @"namespace\s+XRL\.World\.Parts\s*\{"),
        "core → exact Parts ns");
    Assert(System.Text.RegularExpressions.Regex.IsMatch(
            nsPartial.UpdatedContents["Commands_AI.cs"],
            @"namespace\s+XRL\.World\.Parts\s*\{"),
        "AI partial synced to exact Parts ns");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(
            nsPartial.UpdatedContents["Commands_AI.cs"],
            @"namespace\s+XRL\.World\.Parts\.Mutation\b"),
        "AI left Mutation");
    Assert(nsPartial.Fixes.Any(f => f.Fix.RuleName == BlueprintTypeNamespaceFixer.FixRuleNamePartialSync),
        "partial sync rule recorded");

    // Same-mod OldNs.Type FQN strip (cross-mod FQNs still need a hand fix)
    const string memoryFq = """
        using System;
        using XRL.World;
        using XRL.World.Parts;

        namespace ThreadingAPI
        {
            [Serializable]
            public class EnhancedAIMemoryPart : IPart
            {
                public static EnhancedAIMemoryPart GetOrCreate(GameObject obj) => null;
            }
        }
        """;
    const string sameModFq = """
        namespace ThreadingAPI
        {
            static class Wire
            {
                static void Go(GameObject g)
                {
                    var m = ThreadingAPI.EnhancedAIMemoryPart.GetOrCreate(g);
                }
            }
        }
        """;
    var mapFq = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        ["EnhancedAIMemoryPart.cs"] = memoryFq,
        ["Wire.cs"] = sameModFq,
    };
    var nsFq = BlueprintTypeNamespaceFixer.FixMod(mapFq);
    AssertContains(nsFq.UpdatedContents["Wire.cs"], "EnhancedAIMemoryPart.GetOrCreate", "FQN stripped to short name");
    AssertNotContains(nsFq.UpdatedContents["Wire.cs"], "ThreadingAPI.EnhancedAIMemoryPart", "old FQN gone");
}

// Truncated / EOF-unclosed XML → append missing closers
{
    const string cyf = """
        <KernelmethodChooseYourFighter Encoding="utf-8">
        	<group ID="NuThPix" Name="Nuclear Throners">
        		<model ID="NucFish" Name="{{G|Fish}}">
        			<tile Path="creatures/x.png" />
        		</model>
        <KernelmethodChooseYourFighter>
        """;
    var (fixedCyf, cyfFixes) = XmlUnclosedElementFixer.Fix(cyf);
    Assert(cyfFixes.Count == 1, "cyf unclosed fix recorded");
    Assert(XmlUnclosedElementFixer.IsWellFormed(fixedCyf), "cyf well-formed after fix");
    AssertContains(fixedCyf, "</group>", "cyf closed group");
    AssertContains(fixedCyf, "</KernelmethodChooseYourFighter>", "cyf closed root");
    AssertNotContains(fixedCyf.TrimEnd().Split('\n').Last(), "<KernelmethodChooseYourFighter>", "trailing reopen gone");

    const string objects = """
        <?xml version="1.0" encoding="utf-8"?>
        <objects Encoding="utf-8">
        	<object Name="X" Inherits="Furniture">
        		<part Name="Render" DisplayName="x" />
        	</object>
        """;
    var (fixedObj, objFixes) = XmlUnclosedElementFixer.Fix(objects);
    Assert(objFixes.Count == 1, "objects unclosed fix");
    AssertContains(fixedObj, "</objects>", "objects closed");

    // Comment-only file — leave alone
    const string commented = "<?xml version=\"1.0\"?>\n<!--\n<subtypes></subtypes>\n-->\n";
    var (still, noFixes) = XmlUnclosedElementFixer.Fix(commented);
    Assert(noFixes.Count == 0, "comment-only not auto-fixed");
    Assert(still == commented, "comment-only unchanged");
}

// Nullable-ref stripper (truncated "file.cs'." MODWARNs / CS8632)
{
    const string src = """
        #nullable enable
        using System;
        using XRL.UI;

        class C {
          public String? Name;
          public object? Box;
          public int? Count;
          public DialogResult? Choice;
          public T? OnlyIf<T>(T value) where T : class => value;
          string M(GameObject? go) => (go?.Blueprint ?? "x").Length > 0 ? "a" : "b";
        }
        """;
    var (cleaned, n) = NullableAnnotationCleaner.Clean(src);
    Assert(n >= 4, "nullable edits: " + n);
    AssertNotContains(cleaned, "#nullable", "directive gone");
    AssertNotContains(cleaned, "String?", "String? gone");
    AssertNotContains(cleaned, "object?", "object? gone");
    AssertContains(cleaned, "int?", "int? kept");
    AssertContains(cleaned, "DialogResult?", "DialogResult? kept");
    AssertContains(cleaned, "go?.Blueprint", "?. kept");
    AssertContains(cleaned, "?? \"x\"", "?? kept");
    // Engine path records the fix
    var (viaEngine, fixes) = engine.ApplyCuratedRules(src, "NullableSmoke.cs");
    AssertNotContains(viaEngine, "#nullable", "engine strip directive");
    Assert(fixes.Any(f => f.RuleName.Contains("nullable-ref", StringComparison.Ordinal)), "engine records nullable fix");

    // Enum? and TEnum? (struct/Enum constrained) must be preserved; List<T>? stripped
    const string enumSrc = """
        enum Mode { A, B }
        class C {
          public Mode? Opt;
          public List<string>? Names;
          public static bool F<TEnum>(ref TEnum? v) where TEnum : struct, System.Enum => true;
        }
        """;
    var (enumCleaned, enumN) = NullableAnnotationCleaner.Clean(enumSrc);
    Assert(enumN >= 1, "List<string>? strip edits: " + enumN);
    AssertContains(enumCleaned, "Mode?", "enum? kept");
    AssertContains(enumCleaned, "TEnum?", "TEnum? kept");
    AssertNotContains(enumCleaned, "List<string>?", "List<string>? gone");
    AssertContains(enumCleaned, "List<string> Names", "List kept without ?");

    // Cross-file enum? with = null must be preserved (ThreadingAPI TaskPriority? bug)
    const string crossFileEnumParam = """
        using System;
        namespace ThreadingAPI
        {
            public sealed class ModJobOptions
            {
                public static ModJobOptions ForWorldBuild(string jobId = null, TaskPriority? priority = null)
                {
                    return new ModJobOptions { Priority = priority ?? TaskPriority.High };
                }
            }
        }
        """;
    var (crossCleaned, crossN) = NullableAnnotationCleaner.Clean(crossFileEnumParam);
    AssertContains(crossCleaned, "TaskPriority?", "cross-file enum? = null kept without enum decl");
    Assert(crossN == 0 || !crossCleaned.Contains("TaskPriority priority = null", StringComparison.Ordinal),
        "must not strip to TaskPriority priority = null");

    var (crossWithExtra, _) = NullableAnnotationCleaner.Clean(
        "TaskPriority? priority = null; string? name = null;",
        new[] { "TaskPriority" });
    AssertContains(crossWithExtra, "TaskPriority?", "extraPreserve keeps TaskPriority?");
    AssertNotContains(crossWithExtra, "string?", "string? still stripped");
    AssertContains(crossWithExtra, "string name = null", "string null default without ?");

    var (arrCleaned, arrN) = NullableAnnotationCleaner.Clean("object?[] parameters = null;");
    Assert(arrN >= 1, "object?[] strip: " + arrN);
    AssertContains(arrCleaned, "object[] parameters", "object?[] -> object[]");

    const string xrlVersionSrc = """
        using System;
        using Version = XRL.Version;
        class C {
          public static Version? LastModVersionSaved
          {
            get => The.Game?.GetObjectGameState("v") as Version?;
          }
        }
        """;
    var (verCleaned, verN) = NullableAnnotationCleaner.Clean(xrlVersionSrc);
    AssertContains(verCleaned, "Version?", "XRL.Version alias keeps Version?");
    AssertContains(verCleaned, "as Version?", "as Version? kept");
    Assert(verN == 0 || verCleaned.Contains("Version?", StringComparison.Ordinal), "must not strip Version?");

    var (xrlQual, _) = NullableAnnotationCleaner.Clean("public static XRL.Version? Last;");
    AssertContains(xrlQual, "XRL.Version?", "qualified XRL.Version? kept");

    var (sysVer, sysN) = NullableAnnotationCleaner.Clean("using System;\nclass C { public Version? V; }");
    Assert(sysN >= 1, "System.Version? strip: " + sysN);
    AssertNotContains(sysVer, "Version?", "System.Version? is NRT — strip");
    AssertContains(sysVer, "Version V", "System.Version without ?");
}

// CS0019 Count method-group fixer (LINQ / IEnumerable; leave List.Count alone)
{
    const string src = """
        using System.Collections.Generic;
        using System.Linq;

        class C {
          int BadLinq(IEnumerable<int> raw) {
            var list = new List<int> { 1, 2 };
            var n1 = raw.Where(x => x > 0).Count > 0;
            var n2 = list.Select(x => x).Count == 1;
            var n3 = list.Count > 0;
            var n4 = list.ToList().Count >= 1;
            IEnumerable<string> xs = raw.Select(i => i.ToString());
            var n5 = xs.Count != 0;
            return n1 && n2 && n3 && n4 && n5 ? 1 : 0;
          }

          object? TupleEmpty(IEnumerable<(int a, string b)> left) {
            return left ?? Enumerable.Empty<(int, string)>();
          }
        }
        """;

    var (fixedContent, n) = CountMethodGroupFixer.Fix(src);
    Assert(n >= 3, "count fixes: " + n);
    AssertContains(fixedContent, ".Where(x => x > 0).Count() > 0", "Where.Count fixed");
    AssertContains(fixedContent, ".Select(x => x).Count() == 1", "Select.Count fixed");
    AssertContains(fixedContent, "xs.Count() != 0", "IEnumerable-typed Count fixed");
    AssertContains(fixedContent, "list.Count > 0", "List.Count property kept");
    AssertContains(fixedContent, "ToList().Count >= 1", "ToList().Count property kept");
    AssertNotContains(fixedContent, "list.Count() > 0", "must not wrap List.Count");

    // Same name: IEnumerable param elsewhere + var List local (Broodmother defects)
    const string nameCollision = """
        using System.Collections.Generic;
        using System.Linq;

        class C {
          static void Format(IEnumerable<string> defects) { }
          static void Append() {
            var beneficial = new List<string>();
            var defects = new List<string>();
            if (beneficial.Count == 0 && defects.Count == 0) return;
            if (defects.Count > 0) { }
          }
        }
        """;
    var (collisionFixed, collisionN) = CountMethodGroupFixer.Fix(nameCollision);
    Assert(collisionN == 0, "name-collision Count edits: " + collisionN);
    AssertContains(collisionFixed, "defects.Count == 0", "List defects.Count kept");
    AssertContains(collisionFixed, "defects.Count > 0", "List defects.Count > kept");
    AssertNotContains(collisionFixed, "defects.Count()", "must not wrap collided List.Count");

    var (viaEngine, fixes) = engine.ApplyCuratedRules(src, "CountSmoke.cs");
    Assert(fixes.Any(f => f.RuleName.Contains("Count method-group", StringComparison.Ordinal)), "engine records Count fix");
    AssertContains(viaEngine, ".Count() > 0", "engine applied Count()");

    // Post-fix scan: List.Count not flagged; tuple Empty coalesce is
    var hits = engine.ScanRemainingHits(viaEngine);
    Assert(!hits.Any(h => h.Member == CountMethodGroupFixer.CountHitMember && h.Text.Contains("list.Count", StringComparison.Ordinal)),
        "List.Count not flagged as method-group");
    Assert(hits.Any(h => h.Member == CountMethodGroupFixer.TupleHitMember),
        "tuple Empty coalesce flagged");
}

// PreferXML / PreferHarmonyPatch — curated override extension points (report-only)
{
    const string src = """
        class Mut : BaseMutation {
          public override string DisplayName { get => "X"; set {} }
          public override void Register(GameObject Object) {
            base.Register(Object);
          }
          public override bool HandleEvent(SomeEvent E) => true;
          // public override void Register(GameObject Object) { }
          public void NotAnOverride() { }
          public override int UnrelatedHelper() => 1;
        }
        class Liq : BaseLiquid {
          public override bool IsLiquid => true;
        }
        """;

    var hits = OverridePreferenceScanner.Scan(src);
    Assert(hits.Any(h => h.Member == "PreferXML.DisplayName"), "DisplayName → PreferXML");
    Assert(hits.Any(h => h.Member == "PreferXML.IsLiquid"), "IsLiquid → PreferXML");
    Assert(!hits.Any(h => h.Member == "PreferHarmonyPatch.Register"),
        "Register on BaseMutation/IPart is the part pipeline, not PreferHarmony");
    Assert(!hits.Any(h => h.Member == "PreferHarmonyPatch.HandleEvent"),
        "HandleEvent on BaseMutation is the part pipeline, not PreferHarmony");
    Assert(!hits.Any(h => h.Text.Contains("// public override void Register", StringComparison.Ordinal)),
        "commented Register override not flagged");
    Assert(!hits.Any(h => h.Member.Contains("UnrelatedHelper", StringComparison.Ordinal)),
        "non-curated override not flagged");

    const string ownDrank = """
        namespace XRL.Liquids {
          class LiquidIchor : BaseLiquid {
            public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, TextBuilder Message, ref bool ExitInterface) => true;
          }
        }
        """;
    var ownDrankHits = OverridePreferenceScanner.Scan(ownDrank);
    Assert(ownDrankHits.Any(h => h.Member == "PreferXML.Drank"), "own BaseLiquid.Drank → PreferXML");
    Assert(!ownDrankHits.Any(h => h.Member == "PreferHarmonyPatch.Drank"), "own Drank is not PreferHarmony");

    const string vanillaDrank = """
        class LiquidBlood : BaseLiquid {
          public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, TextBuilder Message, ref bool ExitInterface) => true;
        }
        """;
    var vanillaDrankHits = OverridePreferenceScanner.Scan(vanillaDrank);
    Assert(vanillaDrankHits.Any(h => h.Member == "PreferHarmonyPatch.Drank"), "vanilla liquid Drank → PreferHarmony");

    const string partDrank = """
        class IchorOnDrink : BaseLiquidPart {
          public override bool Drank(ref DrankEvent E) => true;
        }
        """;
    var partDrankHits = OverridePreferenceScanner.Scan(partDrank);
    Assert(!partDrankHits.Any(h => h.Member.Contains("Drank", StringComparison.Ordinal)),
        "BaseLiquidPart.Drank is the part pipeline");

    const string vanillaReplace = """
        class MyStomach : Stomach {
          public override bool HandleEvent(SomeEvent E) => true;
          public override bool WantEvent(int ID, int cascade) => true;
        }
        """;
    var vanillaHits = OverridePreferenceScanner.Scan(vanillaReplace);
    Assert(vanillaHits.Any(h => h.Member == "PreferHarmonyPatch.HandleEvent"),
        "HandleEvent on Stomach (vanilla replacement) still PreferHarmonyPatch");
    Assert(vanillaHits.Any(h => h.Member == "PreferHarmonyPatch.WantEvent"),
        "WantEvent on Stomach still PreferHarmonyPatch");

    var viaEngine = engine.ScanRemainingHits(src);
    Assert(viaEngine.Any(h => h.Member.StartsWith("PreferXML.", StringComparison.Ordinal)),
        "engine surfaces PreferXML");

    // Modern Register(Object, IEventRegistrar) on IPart is the part pipeline — not PreferHarmony
    const string modernReg = """
        class C : IPart {
          public override void Register(GameObject Object, IEventRegistrar Registrar) {
            Registrar.Register("Equipped");
            base.Register(Object, Registrar);
          }
        }
        """;
    var modernHits = OverridePreferenceScanner.Scan(modernReg);
    Assert(!modernHits.Any(h => h.Member == "PreferHarmonyPatch.Register"),
        "IPart Register override is not PreferHarmonyPatch");

    var stub = OverridePreferenceScanner.HarmonyStubTemplate("IPart", "Register");
    AssertContains(stub, "HarmonyPatch", "stub has HarmonyPatch");
    AssertContains(stub, "Postfix", "stub has Postfix");

    // Advice never recommends [Obsolete]
    var regAdvice = ManualAdvice.PreferHarmonyAdvice("Register");
    AssertContains(regAdvice, "Do not add [Obsolete]", "Register advice bans Obsolete");
    AssertContains(regAdvice, "IEventRegistrar", "Register advice shows last-resort shape");
    Assert(!regAdvice.Contains("add [Obsolete]", StringComparison.OrdinalIgnoreCase) ||
           regAdvice.Contains("Do not add [Obsolete]", StringComparison.Ordinal),
        "must not recommend adding Obsolete");
}

// Curated: pPhysics / pRender / GameObject.create
{
    const string src = """
        class C {
          void M(GameObject go, Brain ParentBrain) {
            go.pPhysics.Takeable = true;
            go.pRender.DisplayName = "x";
            ParentBrain.pPhysics.CurrentCell = null;
            var o = GameObject.create("Seed");
            var s = ScreenBuffer.create(1, 1);
          }
        }
        """;
    var (result, fixes) = engine.ApplyCuratedRules(src, "Phys.cs");
    AssertContains(result, "go.Physics.Takeable", "pPhysics→Physics");
    AssertContains(result, "go.Render.DisplayName", "pRender→Render");
    AssertContains(result, "ParentBrain.ParentObject.Physics", "Brain.pPhysics→ParentObject.Physics");
    AssertContains(result, "GameObject.Create(\"Seed\")", "create→Create");
    AssertContains(result, "ScreenBuffer.create(1, 1)", "ScreenBuffer.create left alone");
    Assert(fixes.Any(f => f.RuleName.Contains("pPhysics", StringComparison.Ordinal)), "pPhysics fix recorded");
    Assert(fixes.Any(f => f.RuleName.Contains("GameObject.create", StringComparison.Ordinal)), "create fix recorded");
}

// ShowOptionList → PickOption (mappable args)
{
    const string src = """
        class C {
          int M() {
            return Popup.ShowOptionList("Choose action", optionsList, charList, AllowEscape: true);
          }
          int N() {
            return Popup.ShowOptionList(
              "Title",
              defaultChoices,
              Intro: item.DisplayName,
              AllowEscape: true);
          }
        }
        """;
    var (fixedContent, sync, async) = ShowOptionListFixer.Fix(src);
    Assert(sync == 2, "two ShowOptionList fixes: " + sync);
    Assert(async == 0, "no async");
    AssertContains(fixedContent, "PickOption(", "renamed");
    AssertNotContains(fixedContent, "ShowOptionList(", "old gone");
    AssertContains(fixedContent, "AllowEscape: true", "named kept");
    AssertContains(fixedContent, "Options:", "positional Options named");

    var (viaEngine, fixes) = engine.ApplyCuratedRules(src, "Popup.cs");
    Assert(fixes.Any(f => f.RuleName.Contains("ShowOptionList", StringComparison.Ordinal)),
        "engine records PickOption fix");
    AssertContains(viaEngine, "PickOption(", "engine applied PickOption");
}

// Register last-resort simple body; complex body advice-only
{
    const string simple = """
        class C : IPart {
          public override void Register(GameObject Object)
          {
            Object.RegisterPartEvent(this, "BeforePhysicsRejectObjectEntringCell");
            base.Register(Object);
          }
        }
        """;
    var (simpleFixed, n) = RegisterOverrideFixer.Fix(simple);
    Assert(n == 1, "simple Register fixed: " + n);
    AssertContains(simpleFixed, "IEventRegistrar Registrar", "sig bumped");
    AssertContains(simpleFixed, "Registrar.Register(\"BeforePhysicsRejectObjectEntringCell\")", "event via Registrar");
    AssertContains(simpleFixed, "base.Register(Object, Registrar)", "base updated");
    AssertNotContains(simpleFixed, "[Obsolete]", "never adds Obsolete");

    const string complex = """
        class C : IPart {
          public override void Register(GameObject Object)
          {
            Object.RegisterPartEvent(this, "X");
            SomeField = 1;
            base.Register(Object);
          }
        }
        """;
    var (_, complexN) = RegisterOverrideFixer.Fix(complex);
    Assert(complexN == 0, "complex Register not auto-fixed");

    var (viaEngine, fixes) = engine.ApplyCuratedRules(simple, "Reg.cs");
    Assert(fixes.Any(f => f.RuleName.Contains("IEventRegistrar", StringComparison.Ordinal)),
        "engine records Register last-resort");
    // IPart Register is the part pipeline — last-resort bump is not PreferHarmony
    var hits = engine.ScanRemainingHits(viaEngine);
    Assert(!hits.Any(h => h.Member == "PreferHarmonyPatch.Register"),
        "IPart Register after last-resort bump is not PreferHarmony");

    const string vanillaReg = """
        class MyStomach : Stomach {
          public override void Register(GameObject Object)
          {
            Object.RegisterPartEvent(this, "BeforePhysicsRejectObjectEntringCell");
            base.Register(Object);
          }
        }
        """;
    var (vanillaFixed, _) = engine.ApplyCuratedRules(vanillaReg, "StomachReg.cs");
    var vanillaHits = engine.ScanRemainingHits(vanillaFixed);
    Assert(vanillaHits.Any(h => h.Member == "PreferHarmonyPatch.Register"),
        "Register on Stomach (vanilla replacement) still PreferHarmony after bump");
    Assert(vanillaHits.All(h => !string.IsNullOrWhiteSpace(h.Advice)), "all hits carry Advice");
    Assert(vanillaHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "Advice bans [Obsolete] on every hit");
}

// ManualAdvice for ShowOptionList dump leftover
{
    var advice = ManualAdvice.ForMember("XRL.UI.Popup.ShowOptionList", "Use PickOption", "Popup.ShowOptionList(");
    AssertContains(advice, "Do not add [Obsolete]", "ShowOptionList bans Obsolete");
    AssertContains(advice, "PickOption", "suggests PickOption");
    AssertContains(advice, "OnResult", "named remap hint");
}

// ManualAdvice for ApplyStatShift / UnapplyStatShift → StatShifter
{
    var apply = ManualAdvice.ForMember("XRL.World.GameObject.ApplyStatShift",
        "You may want to switch to using the new StatShifter API",
        "ParentObject.ApplyStatShift(MoveSpeedStat, -MoveSpeedPenalty);");
    AssertContains(apply, "Do not add [Obsolete]", "ApplyStatShift bans Obsolete");
    AssertContains(apply, "StatShifter.SetStatShift", "suggests SetStatShift");
    AssertContains(apply, "Not autofixable", "marks non-autofix");

    var unapply = ManualAdvice.ForMember("XRL.World.GameObject.UnapplyStatShift",
        "You may want to switch to using the new StatShifter API",
        "ParentObject.UnapplyStatShift(MoveSpeedStat, -MoveSpeedPenalty);");
    AssertContains(unapply, "RemoveStatShift", "suggests RemoveStatShift");
    AssertContains(unapply, "StatShifter", "names StatShifter API");
}

// ReverseTranslateBit — ID vs color confidence; ambiguous left alone
{
    const string idSrc = """
        class C {
          string Translate(char c) {
            string translated = BitType.ReverseTranslateBit(c);
            if (translated == "?") return "";
            string bits = "";
            bits += BitType.ReverseTranslateBit(c);
            return bits;
          }
          string Colorize(char c) {
            return "{{" + BitType.ReverseTranslateBit(c) + "|x}}";
          }
          char Ch(char c) => BitType.ReverseCharTranslateBit(c);
          string Ambiguous(char c) => BitType.ReverseTranslateBit(c);
        }
        """;
    var (fixedContent, idN, colorN, charN) = ReverseTranslateBitFixer.Fix(idSrc);
    Assert(idN == 2, "two ID ReverseTranslateBit fixes: " + idN);
    Assert(colorN == 1, "one color ReverseTranslateBit fix: " + colorN);
    Assert(charN == 1, "one ReverseChar fix: " + charN);
    AssertContains(fixedContent, "BitID.ToString()", "ID path");
    AssertContains(fixedContent, "DisplayColor", "color path");
    AssertContains(fixedContent, "?.BitID ?? '?'", "char path");
    AssertContains(fixedContent, "Ambiguous(char c) => BitType.ReverseTranslateBit(c)", "ambiguous left");

    var advice = ManualAdvice.ForMember(
        "XRL.World.Tinkering.BitType.ReverseTranslateBit",
        "Use FetchBitByCode(Bit).ID or DisplayColor",
        "bits += BitType.ReverseTranslateBit(c);");
    AssertContains(advice, "BitID", "advice mentions BitID");
    AssertContains(advice, "Do not add [Obsolete]", "bit advice bans Obsolete");
}

// AddAction string → InventoryAction
{
    const string src = """
        class C {
          void M(IInventoryActionsEvent E) {
            E.AddAction("Activate", "&Wa&yctivate", "Activate", null, 'a', FireOnActor: false, 0, 0, Override: false, WorksAtDistance: false, WorksTelekinetically: true);
            E.AddAction("Apply X", "apply X", "Apply X", null, 'X', false, -3, 0, false, false, false, false, true, null, false);
            E.AddAction(new InventoryAction { Name = "Keep" });
            Actions.AddAction("CollectSeeds", 'C', false, "&WC&yollect", "Cmd");
          }
        }
        """;
    var (fixedContent, n) = AddActionFixer.Fix(src);
    Assert(n == 3, "three AddAction fixes (skip InventoryAction form): " + n);
    AssertContains(fixedContent, "new InventoryAction { Name = \"Activate\"", "modern mapped");
    AssertContains(fixedContent, "WorksTelekinetically = true", "named kept");
    AssertNotContains(fixedContent, "Override", "Override omitted");
    AssertContains(fixedContent, "FireOnActor = false", "classic FireOnActor");
    AssertContains(fixedContent, "Name = \"Apply X\"", "all-positional modern with Override slot");
    AssertContains(fixedContent, "AsMinEvent = true", "AsMinEvent mapped");
    AssertContains(fixedContent, "ReturnToModernUI = false", "ReturnToModernUI mapped");
    AssertContains(fixedContent, "new InventoryAction { Name = \"Keep\" }", "object form untouched");

    var advice = ManualAdvice.ForMember(
        "XRL.World.IInventoryActionsEvent.AddAction",
        "Use AddXMLAction",
        "E.AddAction(\"X\", \"y\", \"Z\");");
    AssertContains(advice, "InventoryAction", "AddAction advice");
    AssertContains(advice, "Do not add [Obsolete]", "AddAction bans Obsolete");

    var itisAdvice = ManualAdvice.ForMember(
        "XRL.World.GameObject.Itis",
        "use replacer =GameObject.Itis=",
        "Popup.Show(obj.Itis + \" \" + obj.an() + \"!\");");
    AssertContains(itisAdvice, "StartReplace", "Itis advice mentions StartReplace");
    AssertContains(itisAdvice, "a.name", "Itis advice mentions a.name combo");

    var anAdvice = ManualAdvice.ForMember(
        "XRL.World.GameObject.an",
        "Use replacer =GameObject.a.name=",
        "obj.an()");
    AssertContains(anAdvice, "a.name", "an advice");
    AssertContains(anAdvice, "Do not add [Obsolete]", "an bans Obsolete");
}

// Drank StringBuilder → TextBuilder is last-resort for vanilla liquid types only
{
    const string ownSrc = """
        using System.Text;
        class LiquidIchor : BaseLiquid {
          public override bool Drank(
              LiquidVolume Liquid,
              int Volume,
              GameObject Target,
              StringBuilder Message,
              ref bool ExitInterface)
          {
            Message.Compound("x");
            return true;
          }
        }
        """;
    var (ownFixed, ownN) = DrankOverrideFixer.Fix(ownSrc);
    Assert(ownN == 0, "own BaseLiquid.Drank is not signature-bumped: " + ownN);
    AssertContains(ownFixed, "StringBuilder Message", "own Drank left for OnDrink part");

    const string vanillaSrc = """
        using System.Text;
        class LiquidBlood : BaseLiquid {
          public override bool Drank(
              LiquidVolume Liquid,
              int Volume,
              GameObject Target,
              StringBuilder Message,
              ref bool ExitInterface)
          {
            Message.Compound("x");
            return true;
          }
        }
        """;
    var (fixedContent, n) = DrankOverrideFixer.Fix(vanillaSrc);
    Assert(n == 1, "vanilla Drank signature fixed: " + n);
    AssertContains(fixedContent, "TextBuilder Message", "TextBuilder param");
    AssertNotContains(fixedContent, "StringBuilder Message", "StringBuilder param gone");
    AssertContains(fixedContent, "Message.Compound", "body untouched");

    var (viaEngine, fixes) = engine.ApplyCuratedRules(vanillaSrc, "LiquidBlood.cs");
    Assert(fixes.Any(f => f.RuleName.Contains("TextBuilder", StringComparison.Ordinal)),
        "engine records Drank bump on vanilla liquid");
    AssertContains(viaEngine, "using XRL.World.Text;", "Drank ensures Text using");
}

// LiquidXmlAdviceScanner + PreferXML IsLiquid snippet
{
    const string src = """
        class LiquidIchor : BaseLiquid {
          public LiquidIchor() : base("ichor") {
            this.FlameTemperature = 400;
            this.VaporTemperature = 1200;
          }
          public override bool IsLiquid => true;
          public override List<string> GetColors() => LiquidBlood.Colors;
        }
        """;
    var hits = LiquidXmlAdviceScanner.Scan(src);
    Assert(hits.Any(h => h.Member == LiquidXmlAdviceScanner.LiquidPropsMember),
        "liquid props PreferXML");
    Assert(hits.Any(h => h.Member.Contains("LiquidBlood", StringComparison.Ordinal)),
        "LiquidBlood PreferXML");
    Assert(hits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "liquid advice bans Obsolete");

    var isLiquidAdvice = ManualAdvice.PreferXmlAdvice("IsLiquid");
    AssertContains(isLiquidAdvice, "flameTemperature", "IsLiquid advice lists fields");
    AssertContains(isLiquidAdvice, "<liquids", "IsLiquid advice has XML snippet");

    var mutAdvice = ManualAdvice.PreferXmlAdvice("DisplayName");
    AssertContains(mutAdvice, "<mutations", "DisplayName Mutations.xml snippet");
    AssertContains(mutAdvice, "remove the DisplayName", "asks to remove setter");

    var moe = ManualAdvice.ForMember(
        "XRL.World.Parts.MutationOnEquip.ClassName",
        "Use Mutation=",
        "ClassName = \"Telepathy\"");
    AssertContains(moe, "Mutation=", "MutationOnEquip advice");
    AssertContains(moe, "GetMutationEntry", "GetMutationEntry mention");

    var foe = ManualAdvice.ForMember(
        "XRL.World.Parts.GenerateFriendOrFoe.hateReasons",
        "Now uses =spice:friendOrFoe.$spiceKey.hateReasons=",
        "GenerateFriendOrFoe.hateReasons.Add(\"x\");");
    AssertContains(foe, "HistorySpice.json", "FriendOrFoe spice file");
    AssertContains(foe, "PreferXML/spice", "FriendOrFoe PreferXML tag");
    AssertContains(foe, "MergeModJson", "FriendOrFoe merge note");
    AssertContains(foe, "Do not add [Obsolete]", "FriendOrFoe bans Obsolete");

    var foeXml = ManualAdvice.PreferXmlAdvice("FriendOrFoeReasons");
    AssertContains(foeXml, "likeReasons", "PreferXML FriendOrFoeReasons");
}

// Player.log harvest 2026-08-04 — LiquidWarmStatic / TextBuilder half-migration / Capitalize / FinalRender
{
    const string warm = """
        using XRL.Liquids;
        class C {
          void M(GameObject o, Zone z) {
            LiquidWarmStatic.ApplyRandomEffectTo(o, 1);
            LiquidWarmStatic.GlitchObject(o, "x");
            LiquidWarmStatic.GlitchZone(z);
            var id = LiquidWarmStatic.ID;
            this.Cleansing = 1;
            this.SlipperyWhenFrozen = true;
          }
        }
        """;
    var warmHits = LiquidXmlAdviceScanner.Scan(warm);
    Assert(warmHits.Any(h => h.Member.Contains("LiquidWarmStatic", StringComparison.Ordinal)),
        "LiquidWarmStatic PreferXML");
    Assert(warmHits.Any(h => h.Member == LiquidXmlAdviceScanner.LiquidPropsMember),
        "Cleansing/Slippery PreferXML props");
    Assert(warmHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "warm advice bans Obsolete");

    var (idFixed, idFixes) = engine.ApplyCuratedRules(
        "var id = LiquidWarmStatic.ID;\n", "Warm.cs");
    AssertContains(idFixed, "LiquidID.WarmStatic", "ID curated rewrite");
    AssertContains(idFixed, "using XRL.Liquids;", "LiquidID using");

    const string half = """
        using XRL.World.Text;
        class C {
          void M(TextBuilder tb, StringBuilder stringBuilder) {
            tb.AppendSigned(3);
            tb.AppendArmor("x", 1, 2);
            stringBuilder.AppendSigned(1); // SB local — not flagged
            E.DefaultDisplayOrder = 5;
            AddsRep.AppendDescription(tb, "f", 1, "pre", "post", true, true);
          }
        }
        """;
    var halfHits = TextBuilderHalfMigrationScanner.Scan(half);
    Assert(halfHits.Any(h => h.Member.Contains("AppendSigned", StringComparison.Ordinal)),
        "AppendSigned half-migration");
    Assert(!halfHits.Any(h => h.Text.Contains("stringBuilder.AppendSigned", StringComparison.Ordinal)),
        "SB local AppendSigned not flagged");
    Assert(halfHits.Any(h => h.Member.Contains("DefaultDisplayOrder", StringComparison.Ordinal)),
        "DefaultDisplayOrder advice");
    Assert(halfHits.Any(h => h.Member.Contains("AppendDescription", StringComparison.Ordinal)),
        "AddsRep arity advice");
    Assert(halfHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "half advice bans Obsolete");

    const string capSrc = """
        class C {
          string M(string text) => text.Capitalize();
          string N(string text) => text.Capitalize(true);
          string Skip() => Extensions.Capitalize("x");
        }
        """;
    var (capFixed, capN) = CapitalizeFixer.Fix(capSrc);
    Assert(capN == 2, "two instance Capitalize fixes: " + capN);
    AssertContains(capFixed, "Translator.InitUpper(text)", "InitUpper");
    AssertContains(capFixed, "Extensions.Capitalize(\"x\")", "static left for curated");

    const string vrSrc = """
        using XRL.World.Text.Attributes;
        using XRL.World.Text.Delegates;
        class C {
          [VariableReplacer]
          public static string Simple(DelegateContext Context) => Context.Default;

          [VariableObjectReplacer("ud_personTerm")]
          public static string Person(DelegateContext Context)
          {
            if (Context.Target is GameObject go)
              return Context.Capitalize ? go.PersonTerm : Context.Pronouns.PersonTerm;
            return "person";
          }
        }
        """;
    var (vrAfterRules, _) = engine.ApplyCuratedRules(vrSrc, "VR.cs");
    AssertContains(vrAfterRules, "VariableContext Context", "curated DelegateContext→VariableContext");
    AssertContains(vrAfterRules, "[VariableReplacer(\"ud_personTerm\", Capitalization = true)]", "ObjectReplacer→Replacer Cap");
    AssertContains(vrAfterRules, "GameObject Object", "Target→GameObject Object param");
    AssertContains(vrAfterRules, "Object is GameObject go", "Context.Target→Object");
    AssertContains(vrAfterRules, "Object.GetPronounProvider().PersonTerm", "Pronouns→GetPronounProvider");
    AssertContains(ManualAdvice.VariableObjectReplacerAdvice(), "Capitalization = true", "ObjectReplacer advice");
    AssertContains(ManualAdvice.VariableReplacerDelegateContextAdvice(), "VariableContext", "DelegateContext advice");

    const string frSrc = """
        class C : IPart {
          public override bool FinalRender(RenderEvent E, bool bAlt)
          {
            return true;
          }
          public override bool FinalRender(RenderEvent E2, bool used)
          {
            if (used) return false;
            return true;
          }
        }
        """;
    var (frFixed, frN) = FinalRenderOverrideFixer.Fix(frSrc);
    Assert(frN == 1, "one unused-Alt FinalRender: " + frN);
    AssertContains(frFixed, "FinalRender(RenderEvent E)", "sig dropped bool");
    AssertContains(frFixed, "bool used", "used Alt left alone");

    var (addReplContent, _) = engine.ApplyCuratedRules(
        "rb.AddReplacer(\"oppName\", Opp.Name);\nrb.AddReplacer(\"n\", \"x\");\nrb.AddReplacer(\"bare\", OppName);\nrb.AddReplacer(\"foil\", Foil ? \" (F)\" : null);\n",
        "Board.cs");
    AssertContains(addReplContent, ".SetArgument(\"oppName\", Opp.Name)", "expr AddReplacer");
    AssertContains(addReplContent, ".SetArgument(\"n\", \"x\")", "literal AddReplacer");
    AssertContains(addReplContent, ".AddReplacer(\"bare\", OppName)", "bare left for advice");
    AssertContains(addReplContent, ".SetArgument(\"foil\", Foil ? \" (F)\" : null)", "ternary AddReplacer");

    var (calContent, calFixes) = engine.ApplyCuratedRules(
        "var d = Calendar.getDay();\nvar m = Calendar.getMonth();\nvar y = Calendar.getYear();\nvar t = Calendar.getTime();\nvar e = Calendar.GetDay();\n",
        "Cal.cs");
    AssertContains(calContent, "Calendar.GetDay()", "getDay→GetDay");
    AssertContains(calContent, "Calendar.GetMonth()", "getMonth→GetMonth");
    AssertContains(calContent, "Calendar.GetYear()", "getYear→GetYear");
    AssertContains(calContent, "Calendar.GetTime()", "getTime→GetTime");
    Assert(!calContent.Contains("=time.day="), "GetDay must not auto-rewrite to =time.day=");
    Assert(calFixes.Count >= 4, "four Calendar casing fixes: " + calFixes.Count);
    AssertContains(ManualAdvice.CalendarGetDayAdvice(), "=time.day=", "GetDay GameText advice");
    AssertContains(ManualAdvice.CalendarGetDayAdvice(), "message/Popup/journal", "GetDay messaging scope");
    AssertContains(ManualAdvice.CalendarCamelAdvice("getDay"), "GetDay", "camel advice");
    AssertContains(ManualAdvice.CalendarCamelAdvice("getDay"), "auto-rewrites", "getDay casing autofix advice");

    var pronounAdvice = ManualAdvice.GameObjectGameTextAdvice("It", "Use =GameObject.They=");
    AssertContains(pronounAdvice, "=GameObject.They=", "It → They GameText");
    AssertContains(pronounAdvice, "Do not add [Obsolete]", "pronoun bans Obsolete");

    var tickAdvice = ManualAdvice.PreferHarmonyAdvice("WantHundredTurnTick");
    AssertContains(tickAdvice, "WantTurnTick", "tick advice");
    AssertContains(tickAdvice, "Do not add [Obsolete]", "tick bans Obsolete");

    var warmAdvice = ManualAdvice.LiquidWarmStaticAdvice("ApplyRandomEffectTo");
    AssertContains(warmAdvice, "BaseGlitchPart", "WarmStatic → BaseGlitchPart");
}

// Player.log Worlds.xml MODWARNs + Compat / disabled-rule regression (2026-08)
{
    const string worlds = """
        <?xml version="1.0" encoding="utf-8"?>
        <worlds Encoding="utf-8">
          <world Name="JoppaWorld" Load="Merge">
            <builder Class="WorldOk" />
            <cell Name="Bethesda Susa" Load="Merge" ApplyTo="TerrainBethesdaSusa"
                  DisableForcedConnections="Yes">
              <builder Class="Music" Track="bad" />
              <zone Level="5-9" x="0-2" y="0-2" Name="sky">
                <builder Class="Sky" />
              </zone>
              <zone Level="10" x="1" y="1" Name="Bethesda Susa" Load="Replace"
                    DisableForcedConnections="Yes">
                <map FileName="ok.rpm" />
              </zone>
              <zone Level="11" x="1" y="1" Name="healing pools">
                <postbuilder Class="ZoneTemplate:X" />
              </zone>
            </cell>
            <cell Name="CustomNew" ApplyTo="MyTerrain">
              <zone Level="10" x="1" y="1" Name="brand new">
                <builder Class="Sky" />
              </zone>
            </cell>
          </world>
        </worlds>
        """;

    var worldsHits = WorldsXmlAdviceScanner.Scan(worlds);
    Assert(worldsHits.Any(h => h.Member == WorldsXmlAdviceScanner.ZoneLoadMember),
        "zone without Load under Merge cell flagged");
    Assert(worldsHits.Any(h => h.Member == WorldsXmlAdviceScanner.CellBuilderMember),
        "cell-level builder flagged");
    Assert(worldsHits.Any(h => h.Member == WorldsXmlAdviceScanner.CellDisableForcedMember),
        "cell DisableForcedConnections flagged before fix");
    Assert(!worldsHits.Any(h => h.Text.Contains("Load=\"Replace\"", StringComparison.Ordinal) &&
                                h.Member == WorldsXmlAdviceScanner.ZoneLoadMember),
        "zone with Load=Replace not flagged for Load create");
    Assert(!worldsHits.Any(h => h.Text.Contains("brand new", StringComparison.Ordinal)),
        "new custom cell zones without Load not flagged");
    Assert(worldsHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "Worlds advice bans Obsolete");
    AssertContains(ManualAdvice.WorldsZoneLoadAdvice(), "Bethesda Susa", "Bethesda Susa example");
    AssertContains(ManualAdvice.WorldsCellBuilderAdvice(), "<music", "music on zone advice");

    var (worldsFixed, worldsFixes) = WorldsXmlFixer.Fix(worlds);
    Assert(worldsFixes.Count == 1 && worldsFixes[0].Count == 1, "one cell DisableForced strip");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(worldsFixed,
            @"<\s*cell\b[^>]*\bDisableForcedConnections\s*=",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase),
        "cell DisableForced gone");
    AssertContains(worldsFixed, "DisableForcedConnections=\"Yes\"", "zone DisableForced kept");
    var afterFixHits = WorldsXmlAdviceScanner.Scan(worldsFixed);
    Assert(!afterFixHits.Any(h => h.Member == WorldsXmlAdviceScanner.CellDisableForcedMember),
        "no cell DisableForced remaining hit after Fixer");

    // Factions.xml — Load=Merge strip, skill case, EEmblem typo; bare interest report-only
    const string factionsBad = """
        <?xml version="1.0" encoding="utf-8"?>
        <factions Encoding="utf-8" Load="Merge">
          <faction Name="Fish" Load="Merge">
            <interest Tags="humanoid,lair" />
            <waterritual
              skill="Tactics"
            />
          </faction>
          <faction Name="KeepReplace" Load="Replace" DisplayName="x" EEmblemTileColor="o" />
          <factions Load="Merge">
            <faction Name="Plants" Load="Merge">
              <partreputation About="X" Value="1" />
            </faction>
          </factions>
        </factions>
        """;

    var factionsHits = FactionsXmlAdviceScanner.Scan(factionsBad);
    Assert(factionsHits.Any(h => h.Member == FactionsXmlAdviceScanner.LoadMergeMember),
        "Load=Merge flagged before fix");
    Assert(factionsHits.Any(h => h.Member == FactionsXmlAdviceScanner.BareInterestMember),
        "bare interest flagged");
    Assert(factionsHits.Any(h => h.Member == FactionsXmlAdviceScanner.WaterRitualSkillCaseMember),
        "skill= case flagged");
    Assert(factionsHits.Any(h => h.Member == FactionsXmlAdviceScanner.EmblemTileColorTypoMember),
        "EEmblem typo flagged");
    Assert(factionsHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "Factions advice bans Obsolete");
    AssertContains(ManualAdvice.FactionsBareInterestAdvice(), "<interests>", "wrap under interests");
    AssertContains(ManualAdvice.FactionsLoadMergeAdvice(), "Replace", "Replace kept note");

    var (factionsFixed, factionsFixes) = FactionsXmlFixer.Fix(factionsBad);
    Assert(factionsFixes.Any(f => f.RuleName == FactionsXmlFixer.LoadMergeRuleName && f.Count >= 3),
        "Load=Merge stripped from root/nested/faction");
    Assert(factionsFixes.Any(f => f.RuleName == FactionsXmlFixer.WaterRitualSkillCaseRuleName),
        "skill→Skill applied");
    Assert(factionsFixes.Any(f => f.RuleName == FactionsXmlFixer.EmblemTileColorTypoRuleName),
        "EEmblem→Emblem applied");
    AssertContains(factionsFixed, "Load=\"Replace\"", "Load=Replace kept");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(factionsFixed,
            @"\bLoad\s*=\s*(['""])Merge\1",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase),
        "no Load=Merge left");
    AssertContains(factionsFixed, "Skill=", "Skill= present");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(factionsFixed, @"\b(?!Skill\b)[Ss][Kk][Ii][Ll][Ll]\s*="),
        "wrong-case skill gone");
    AssertContains(factionsFixed, "EmblemTileColor=", "EmblemTileColor present");
    Assert(!factionsFixed.Contains("EEmblemTileColor", StringComparison.Ordinal), "EEmblem gone");
    AssertContains(factionsFixed, "<interest Tags=\"humanoid,lair\" />", "bare interest left for advice");
    var afterFactionHits = FactionsXmlAdviceScanner.Scan(factionsFixed);
    Assert(!afterFactionHits.Any(h => h.Member == FactionsXmlAdviceScanner.LoadMergeMember),
        "no Load=Merge remaining after Fixer");
    Assert(!afterFactionHits.Any(h => h.Member == FactionsXmlAdviceScanner.WaterRitualSkillCaseMember),
        "no skill case remaining after Fixer");
    Assert(!afterFactionHits.Any(h => h.Member == FactionsXmlAdviceScanner.EmblemTileColorTypoMember),
        "no EEmblem remaining after Fixer");
    Assert(afterFactionHits.Any(h => h.Member == FactionsXmlAdviceScanner.BareInterestMember),
        "bare interest still reported after Fixer");

    // Populations.xml — Name/Load/Style casing Fixer; nameless group advice-only
    const string populationsBad = """
        <?xml version="1.0" encoding="utf-8"?>
        <populations Encoding="utf-8">
          <population name="StartingGear_X" load="merge" style="pickeach">
            <group Style="pickeach">
              <object Blueprint="Torch" Number="1" />
            </group>
            <group Name="Ok" style="pickone">
              <object Blueprint="Bandage" />
            </group>
          </population>
          <population Name="Keep" Load="Merge">
            <group Name="Items" Style="pickeach" />
          </population>
        </populations>
        """;

    var popHits = PopulationXmlAdviceScanner.Scan(populationsBad);
    Assert(popHits.Any(h => h.Member == PopulationXmlAdviceScanner.GroupNameMissingMember),
        "nameless group flagged");
    Assert(popHits.Any(h => h.Member == PopulationXmlAdviceScanner.AttrCaseMember),
        "wrong-case attrs flagged before fix");
    Assert(popHits.All(h => h.Advice.Contains("Do not add [Obsolete]", StringComparison.Ordinal)),
        "Population advice bans Obsolete");
    AssertContains(ManualAdvice.PopulationGroupNameAdvice(), "Items", "StartingGear Items hint");
    AssertContains(ManualAdvice.PopulationAttrCaseAdvice(), "PopulationXmlFixer", "fixer mention");

    var (popFixed, popFixes) = PopulationXmlFixer.Fix(populationsBad);
    Assert(popFixes.Any(f => f.RuleName == PopulationXmlFixer.NameCaseRuleName), "name→Name applied");
    Assert(popFixes.Any(f => f.RuleName == PopulationXmlFixer.LoadCaseRuleName), "load→Load applied");
    Assert(popFixes.Any(f => f.RuleName == PopulationXmlFixer.StyleCaseRuleName), "style→Style applied");
    AssertContains(popFixed, "Name=\"StartingGear_X\"", "population Name cased");
    AssertContains(popFixed, "Load=\"Merge\"", "Load=Merge present");
    AssertContains(popFixed, "Style=\"pickeach\"", "Style cased on population");
    AssertContains(popFixed, "Name=\"Ok\" Style=\"pickone\"", "group style cased");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(popFixed,
            @"<\s*(?:population|group|object|table)\b[^>]*\b(?!Name\b)[Nn][Aa][Mm][Ee]\s*=",
            System.Text.RegularExpressions.RegexOptions.None),
        "no wrong-case name left");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(popFixed,
            @"<\s*(?:population|group)\b[^>]*\b(?!Style\b)[Ss][Tt][Yy][Ll][Ee]\s*=",
            System.Text.RegularExpressions.RegexOptions.None),
        "no wrong-case style left");
    var afterPopHits = PopulationXmlAdviceScanner.Scan(popFixed);
    Assert(!afterPopHits.Any(h => h.Member == PopulationXmlAdviceScanner.AttrCaseMember),
        "no attr-case remaining after Fixer");
    Assert(afterPopHits.Any(h => h.Member == PopulationXmlAdviceScanner.GroupNameMissingMember),
        "nameless group still reported after Fixer");

    var (popCurated, popCuratedFixes) = engine.ApplyCuratedRules(
        "<populations><population name=\"X\" load=\"merge\" style=\"pickeach\"><group name=\"Y\" style=\"pickone\"/></population></populations>",
        "PopulationTables.xml");
    AssertContains(popCurated, "Name=\"X\"", "curated population name→Name");
    AssertContains(popCurated, "Load=\"Merge\"", "curated load→Load=Merge");
    AssertContains(popCurated, "Style=\"pickeach\"", "curated style→Style");
    AssertContains(popCurated, "Name=\"Y\"", "curated group name→Name");
    Assert(popCuratedFixes.Any(f => f.RuleName.Contains("populations", StringComparison.Ordinal)),
        "populations curated rules recorded");

    // MutationsXmlFixer: Load/Code strip, Description→child, ExludeFromPool typo
    {
        const string mutBad = """
            <mutations Encoding="utf-8" Load="Merge" ExludeFromPool="true">
              <category Name="Mental" Load="Merge" IncludeInMutatePool="true">
                <mutation Name="Telekinesis" Cost="4" Class="Telekinesis" Code="d0" Load="Merge" />
                <mutation Name="S_Necromancy" Cost="4" Class="S_Necro" Description="You seize dead tissue." Tile="x.png" />
                <mutation Name="Bark" Code="wd" Cost="1" Class="Bark"></mutation>
              </category>
            </mutations>
            """;
        var (mutFixed, mutFixes) = MutationsXmlFixer.Fix(mutBad);
        Assert(mutFixes.Any(f => f.RuleName == MutationsXmlFixer.LoadStripRuleName && f.Count >= 3),
            "Load stripped on mutations/category/mutation");
        Assert(mutFixes.Any(f => f.RuleName == MutationsXmlFixer.CodeStripRuleName && f.Count >= 2),
            "Code stripped");
        Assert(mutFixes.Any(f => f.RuleName == MutationsXmlFixer.DescriptionAttrRuleName),
            "Description attr→child");
        Assert(mutFixes.Any(f => f.RuleName == MutationsXmlFixer.ExcludeFromPoolTypoRuleName),
            "ExludeFromPool typo");
        AssertNotContains(mutFixed, "Load=", "no Load left");
        AssertNotContains(mutFixed, "Code=", "no Code left");
        AssertNotContains(mutFixed, "Description=", "no Description attr");
        AssertNotContains(mutFixed, "ExludeFromPool", "typo gone");
        AssertContains(mutFixed, "ExcludeFromPool=\"true\"", "ExcludeFromPool fixed");
        AssertContains(mutFixed, "<description>", "description child");
        AssertContains(mutFixed, "<p>You seize dead tissue.</p>", "description text");
        AssertContains(mutFixed, "IncludeInMutatePool=\"true\"", "valid category attr kept");
        AssertContains(mutFixed, "Name=\"Bark\"", "Bark kept");
        AssertContains(mutFixed, "</mutation>", "closers present");
        // Bark was open+close without Description — still one closer
        Assert(System.Text.RegularExpressions.Regex.Matches(mutFixed, "</mutation>").Count >= 2,
            "at least two mutation closers");
    }

    // NamingXmlFixer: *Var*→=var=, templatevar camelCase, Load strip
    {
        const string namingBad = """
            <naming Encoding="utf-8">
              <namestyles>
                <namestyle Name="Troll Hero Title">
                  <templates>
                    <template Name="Who *Occupation*" />
                    <template Name="*Disposition* *CreatureType*" />
                    <template Name="of Clan *Clan*" />
                  </templates>
                  <templatevars>
                    <templatevar Name="Occupation" Load="Replace">
                      <value Name="Hunts Game" />
                    </templatevar>
                    <templatevar Name="Disposition" />
                    <templatevar Name="Clan" />
                  </templatevars>
                </namestyle>
              </namestyles>
            </naming>
            """;
        var (namingFixed, namingFixes) = NamingXmlFixer.Fix(namingBad);
        Assert(namingFixes.Any(f => f.RuleName == NamingXmlFixer.StarVarRuleName && f.Count >= 4),
            "*Var* replacements");
        Assert(namingFixes.Any(f => f.RuleName == NamingXmlFixer.TemplateVarCaseRuleName && f.Count >= 3),
            "templatevar camelCase");
        Assert(namingFixes.Any(f => f.RuleName == NamingXmlFixer.TemplateVarLoadRuleName),
            "templatevar Load strip");
        AssertContains(namingFixed, "Who =occupation=", "Occupation placeholder");
        AssertContains(namingFixed, "=disposition= =creatureType=", "multi placeholders");
        AssertContains(namingFixed, "of Clan =clan=", "Clan placeholder");
        AssertContains(namingFixed, "Name=\"occupation\"", "Occupation→occupation");
        AssertContains(namingFixed, "Name=\"disposition\"", "Disposition→disposition");
        AssertContains(namingFixed, "Name=\"clan\"", "Clan→clan");
        AssertNotContains(namingFixed, "*Occupation*", "star Occupation gone");
        AssertNotContains(namingFixed, "Load=", "templatevar Load gone");
    }

    // GenotypesXmlFixer + SubtypesXmlFixer
    {
        const string genoBad = """
            <genotypes Encoding="utf-8">
              <genotype Name="Golem" Load="Merge" BaseHPGain="2-3"></genotype>
              <genotype Name="Mutated Human" Load="Merge" AllowedMutationCategories="*" />
            </genotypes>
            """;
        var (genoFixed, genoFixes) = GenotypesXmlFixer.Fix(genoBad);
        Assert(genoFixes.Any(f => f.RuleName == GenotypesXmlFixer.LoadStripRuleName && f.Count >= 2),
            "genotype Load stripped");
        AssertNotContains(genoFixed, "Load=", "no genotype Load left");
        AssertContains(genoFixed, "Name=\"Golem\"", "Golem kept");
        AssertContains(genoFixed, "BaseHPGain=\"2-3\"", "BaseHPGain kept");

        const string subBad = """
            <subtypes Encoding="utf-8">
              <class ID="Frames" DisplayName="choose frame" SingularTitle="frame" Class="X" Tile="a.bmp" Load="Merge">
                <category Name="Standard" Load="Merge">
                  <subtype Name="AVR" Code="a" Load="Merge" Gear="G" Tile="t.png" DetailColor="c" Foreground="y">
                    <skills Load="Merge"><skill Name="Tactics_Run" /></skills>
                  </subtype>
                </category>
              </class>
            </subtypes>
            """;
        var (subFixed, subFixes) = SubtypesXmlFixer.Fix(subBad);
        Assert(subFixes.Any(f => f.RuleName == SubtypesXmlFixer.LoadStripRuleName && f.Count >= 4),
            "subtype Load stripped");
        Assert(subFixes.Any(f => f.RuleName == SubtypesXmlFixer.CodeStripRuleName),
            "Code stripped");
        Assert(subFixes.Any(f => f.RuleName == SubtypesXmlFixer.ClassDisplayNameRuleName),
            "DisplayName→ChargenTitle");
        Assert(subFixes.Any(f => f.RuleName == SubtypesXmlFixer.ClassUnusedAttrRuleName && f.Count >= 2),
            "class Class/Tile stripped");
        Assert(subFixes.Any(f => f.RuleName == SubtypesXmlFixer.ForegroundRuleName),
            "Foreground handled");
        AssertContains(subFixed, "ChargenTitle=\"choose frame\"", "ChargenTitle set");
        AssertNotContains(subFixed, "DisplayName=", "class DisplayName gone");
        AssertNotContains(subFixed, "Code=", "Code gone");
        AssertNotContains(subFixed, "Load=", "Load gone");
        AssertNotContains(subFixed, "Foreground=", "Foreground gone");
        AssertContains(subFixed, "DetailColor=\"c\"", "existing DetailColor kept");
        AssertContains(subFixed, "Tile=\"t.png\"", "subtype Tile kept");
        AssertNotContains(subFixed, "Class=\"X\"", "class Class gone");
        AssertNotContains(subFixed, "Tile=\"a.bmp\"", "class Tile gone");

        const string orphanBare = """
            <subtypes Encoding="utf-8">
              <subtype Name="Consul" Gear="StartingGear_Consul" Tile="c.bmp" DetailColor="c" Load="Merge">
                <stat Name="Ego" Bonus="3" />
              </subtype>
            </subtypes>
            """;
        var (orphanFixed, orphanFixes) = SubtypesXmlFixer.Fix(orphanBare);
        Assert(orphanFixes.Any(f => f.RuleName == SubtypesXmlFixer.OrphanSubtypeWrapRuleName),
            "orphan wrap recorded");
        AssertContains(orphanFixed, "<class ID=\"Callings\">", "wrapped under Callings");
        AssertContains(orphanFixed, "Name=\"Consul\"", "Consul kept");
        AssertNotContains(orphanFixed, "Load=", "orphan Load stripped");

        const string orphanSelfClose = """
            <subtypes Encoding="utf-8">
              <class ID="Callings" Load="Merge"/>
              <subtype Name="Harvester" Gear="G" Tile="t.png" ForegroundColor="w" DetailColor="y">
                <stat Name="Toughness" Bonus="2" />
              </subtype>
            </subtypes>
            """;
        var (scFixed, scFixes) = SubtypesXmlFixer.Fix(orphanSelfClose);
        Assert(scFixes.Any(f => f.RuleName == SubtypesXmlFixer.OrphanSubtypeWrapRuleName),
            "self-close class expanded");
        AssertContains(scFixed, "<class ID=\"Callings\">", "Callings opened");
        AssertContains(scFixed, "Name=\"Harvester\"", "Harvester nested");
        AssertContains(scFixed, "</class>", "class closed");
        AssertNotContains(scFixed, "Load=", "class Load stripped");
        AssertNotContains(scFixed, "ForegroundColor=", "ForegroundColor gone");
        AssertContains(scFixed, "DetailColor=\"y\"", "DetailColor kept over ForegroundColor");
    }

    // Dual_Wield → Multiweapon + *Wares → GenericInventoryRestocker
    var (compat, _) = engine.ApplyCuratedRules(
        "<skill Name=\"Dual_Wield\" />\n<skill Name=\"Dual_Wield_Fussilade\" />\n" +
        "<builder Name=\"Tier2Wares\"/>\n" +
        "<builder Name=\"GritGateWares\"/>\n<builder Name=\"Tier2Wares\"/>\n",
        "Skills.xml");
    AssertContains(compat, "Multiweapon_Fighting", "Dual_Wield → Multiweapon_Fighting");
    AssertContains(compat, "Multiweapon_Flurry", "Fussilade → Flurry");
    AssertContains(compat, "GenericInventoryRestocker\" Table=\"Tier2Wares\"", "Tier2Wares restocker");
    AssertContains(compat, "Table=\"MafeoWares\"", "GritGate+Tier2 → MafeoWares");

    // enabled:false rules must not fire
    var (disabledLeft, disabledFixes) = engine.ApplyCuratedRules(
        "ColorUtility.CapitalizeExceptFormatting(s);\nx.hasEventProperty(\"a\");\n",
        "Disabled.cs");
    AssertContains(disabledLeft, "ColorUtility.CapitalizeExceptFormatting", "ColorUtility disabled");
    AssertContains(disabledLeft, ".hasEventProperty(", "HistoricEvent.hasEventProperty disabled");
    Assert(!disabledFixes.Any(f => f.RuleName.Contains("ColorUtility", StringComparison.Ordinal) ||
                                   f.RuleName.Contains("hasEventProperty", StringComparison.Ordinal)),
        "disabled rules must not record fixes");

    // GameTextCallSiteFixer — Hacking/Gadgets high-confidence shapes
    {
        const string gtSrc = """
            using XRL.Messages;
            using XRL.UI;
            class GT {
              void M(GameObject gameObject) {
                string isOrAre = "is";
                MessageQueue.AddPlayerMessage($"{gameObject.t()} {isOrAre} compromised.");
                MessageQueue.AddPlayerMessage($"{gameObject.its} CPU is strained.");
                Popup.Show($"You fail to demand {gameObject.its} secretion.");
                var xs = list.Select(x => x.an()).ToList();
                this.DidX("start", "to radiate", FromDialog: true);
                IComponent<GameObject>.EmitMessage(Object, Object.Poss("radiance") + " dims out.");
              }
            }
            """;
        var (gtFixed, gtN) = GameTextCallSiteFixer.Fix(gtSrc);
        Assert(gtN >= 5, "GameTextCallSiteFixer edits");
        AssertContains(gtFixed, "=subject.the.name= =subject.verb:are= compromised.", "t+isOrAre");
        AssertContains(gtFixed, "=subject.its= CPU is strained.", "its");
        AssertContains(gtFixed, "You fail to demand =subject.its= secretion.", "fail its");
        AssertContains(gtFixed, "=object.a.name=", "an lambda");
        AssertContains(gtFixed, "=subject.Does:start= to radiate", "DidX");
        AssertContains(gtFixed, "EmitMessage(FromDialog: true)", "DidX FromDialog");
        AssertContains(gtFixed, "=subject.poss:radiance=", "Poss concat");
        AssertContains(gtFixed, "using XRL.World.Text;", "GameText using");
        AssertContains(gtFixed, "using XRL;", "StartReplace extension using");
        // HotkeySpread.get must NOT be treated as Reputation.get by dump pattern
        Assert(!System.Text.RegularExpressions.Regex.IsMatch("HotkeySpread.get((IEnumerable<string>)x)", @"Reputation\.get\("),
            "Reputation.get pattern must not match HotkeySpread");
    }

    // PreferXML IsLiquid requires XRL.Liquids namespace
    AssertContains(ManualAdvice.PreferXmlAdvice("IsLiquid"), "XRL.Liquids", "IsLiquid XRL.Liquids");
    AssertContains(ManualAdvice.PreferXmlAdvice("IsLiquid"), "baseColorText", "IsLiquid render attr mapping");
    AssertContains(ManualAdvice.PreferXmlAdvice("IsLiquid"), "<render>", "IsLiquid requires render element");
    AssertContains(ManualAdvice.LiquidPropertiesAdvice("FlameTemperature"), "XRL.Liquids",
        "LiquidProperties XRL.Liquids");
    AssertContains(ManualAdvice.LiquidXmlRenderAdvice, "BaseLiquid.Initialize", "render NRE advice");

    // LiquidXmlFixer: missing <render />, obsolete colors, glow move; merge-only report
    const string liquidMissing = """
        <liquids Encoding="utf-8">
          <liquid Name="Ichor">
            <slug>ichor</slug>
            <class>LiquidIchor</class>
            <colors>WO</colors>
          </liquid>
          <liquid Name="Water">
            <part Name="VampireWaterOnDrink" Priority="100" />
          </liquid>
        </liquids>
        """;
    var (liqFixed, liqFixes) = LiquidXmlFixer.Fix(liquidMissing);
    Assert(liqFixes.Any(f => f.RuleName == LiquidXmlFixer.MissingRenderRuleName && f.Count == 1),
        "one missing-render insert for class liquid");
    AssertContains(liqFixed, "<render />", "inserted empty render");
    AssertContains(liqFixed, "VampireWaterOnDrink", "merge overlay untouched");
    var mergeHits = LiquidXmlRenderAdviceScanner.Scan(liqFixed);
    Assert(!mergeHits.Any(h => h.Member == LiquidXmlRenderAdviceScanner.MissingRenderMergeMember),
        "merge-only overlay without <class> is not flagged");
    const string classNoRender = """
        <liquids>
          <liquid Name="Ichor">
            <class>LiquidIchor</class>
          </liquid>
        </liquids>
        """;
    var classHits = LiquidXmlRenderAdviceScanner.Scan(classNoRender);
    Assert(classHits.Any(h => h.Member == LiquidXmlRenderAdviceScanner.MissingRenderMergeMember),
        "class liquid missing <render> still reported");

    const string liquidColors = """
        <liquids>
          <liquid Name="Mana">
            <class>TQAQ_Mana</class>
            <render colorText="&amp;M^m" colorTile="&amp;Y" colorDetail="O" BrighterWithVolume="true" LightLevel="1" />
          </liquid>
          <liquid Name="Algae">
            <class>LiquidAlgae</class>
            <render>
              <part Name="RenderSecondToAlgae">
                <colorText>&amp;r^C</colorText>
              </part>
              <colorText>&amp;r^k</colorText>
            </render>
          </liquid>
        </liquids>
        """;
    var (liqColorFixed, liqColorFixes) = LiquidXmlFixer.Fix(liquidColors);
    Assert(liqColorFixes.Any(f => f.RuleName == LiquidXmlFixer.RenderColorRenameRuleName),
        "color rename fixes recorded");
    AssertContains(liqColorFixed, "baseColorText", "colorText → baseColorText");
    AssertContains(liqColorFixed, "baseColorTile", "colorTile → baseColorTile");
    AssertContains(liqColorFixed, "baseColorDetail", "colorDetail → baseColorDetail");
    AssertContains(liqColorFixed, "Name=\"Glows\"", "glow attrs → Glows part");
    AssertContains(liqColorFixed, "Class=\"Glows\"", "Glows part gets Class=");
    AssertContains(liqColorFixed, "BrighterWithVolume=\"true\"", "BrighterWithVolume preserved on Glows");
    AssertContains(liqColorFixed, "<colorText>&amp;r^C</colorText>", "RenderSecondTo* colorText kept");
    AssertContains(liqColorFixed, "Class=\"RenderSecondToAlgae\"", "RenderSecondTo* gets Class=");
    AssertNotContains(liqColorFixed, "colorText=\"&amp;M^m\"", "obsolete render attr gone");
    Assert(liqColorFixes.Any(f => f.RuleName == LiquidXmlFixer.RenderPartClassRuleName),
        "render part Class= fixes recorded");

    // Name-only render parts → Class=; scanner flags leftovers before fix
    const string liquidNameOnly = """
        <liquids>
          <liquid Name="Convalessence">
            <class>LiquidConvalessence</class>
            <render>
              <part Name="Glows" BrighterWithVolume="true" LightLevel="1" />
            </render>
          </liquid>
        </liquids>
        """;
    var nameOnlyHits = LiquidXmlRenderAdviceScanner.Scan(liquidNameOnly);
    Assert(nameOnlyHits.Any(h => h.Member == LiquidXmlRenderAdviceScanner.MissingPartClassMember),
        "MissingPartClass reported for Name-only Glows");
    AssertContains(ManualAdvice.LiquidXmlRenderAdvice, "Class=", "LiquidXmlRenderAdvice mentions Class=");
    var (liqClassFixed, liqClassFixes) = LiquidXmlFixer.Fix(liquidNameOnly);
    Assert(liqClassFixes.Any(f => f.RuleName == LiquidXmlFixer.RenderPartClassRuleName && f.Count >= 1),
        "Class= autofix recorded for Name-only Glows");
    AssertContains(liqClassFixed, "Name=\"Glows\"", "Glows Name preserved");
    AssertContains(liqClassFixed, "Class=\"Glows\"", "Glows Class added");
    AssertContains(liqClassFixed, "BrighterWithVolume=\"true\"", "BrighterWithVolume kept on Glows");
    Assert(!LiquidXmlRenderAdviceScanner.Scan(liqClassFixed)
            .Any(h => h.Member == LiquidXmlRenderAdviceScanner.MissingPartClassMember),
        "MissingPartClass cleared after autofix");

    // Bodies Flipper → Fin + Laterality Middle → Mid
    var (bodies, _) = engine.ApplyCuratedRules(
        "<part Type=\"Flipper\" Laterality=\"Right\" />\n" +
        "<part Type=\"Bine\" Laterality=\"Middle\" />\n" +
        "<bodyparttype Type=\"Flipper\" Name=\"flipper\" />\n",
        "Bodies.xml");
    AssertContains(bodies, "Type=\"Fin\"", "Flipper → Fin");
    AssertContains(bodies, "Laterality=\"Mid\"", "Middle → Mid");
    AssertNotContains(bodies, "Flipper", "no Flipper left");
    AssertNotContains(bodies, "Laterality=\"Middle\"", "no Middle laterality left");

    // AddAction Override skipped (no InventoryAction field)
    const string addOverride = """
        class C {
          void M(IInventoryActionsEvent E) {
            E.AddAction("X", "disp", "Cmd", null, 'x', false, 0, 0, Override: true, WorksTelekinetically: true);
          }
        }
        """;
    var (addFixed, addN) = AddActionFixer.Fix(addOverride);
    Assert(addN == 1, "AddAction with Override still rewritten: " + addN);
    AssertContains(addFixed, "new InventoryAction", "InventoryAction object");
    AssertNotContains(addFixed, "Override", "Override omitted from InventoryAction");

    const string vendorAdd = """
        class C {
          public virtual bool HandleEvent(UD_GetVendorActionsEvent E) {
            E.AddAction("Look", "look", "CmdVendorLook", Key: 'l', Priority: 10);
            E.AddAction("Repair", "repair", "CmdVendorRepair", Key: 'r', Priority: 7);
          }
        }
        """;
    var (vendorFixed, vendorN) = AddActionFixer.Fix(vendorAdd);
    Assert(vendorN == 0, "custom vendor AddAction not rewritten: " + vendorN);
    AssertContains(vendorFixed, "E.AddAction(\"Look\"", "Look call kept");
    AssertNotContains(vendorFixed, "AddXMLAction", "no AddXMLAction on vendor event");
    AssertNotContains(vendorFixed, "new InventoryAction", "no InventoryAction on vendor event");

    var vendorTmp = Path.Combine(toolsRoot, "scratch", "apimigrator-vendor-addaction");
    Directory.CreateDirectory(vendorTmp);
    try
    {
        var vendorXml = InventoryActionsXmlFixer.FixMod(vendorTmp, new Dictionary<string, string>
        {
            [Path.Combine(vendorTmp, "H.cs")] = vendorAdd,
        });
        Assert(vendorXml.UpdatedContents.Count == 0, "vendor AddAction not XML-rewritten");
        Assert(vendorXml.SidecarFiles.Count == 0, "no InventoryActions.xml for vendor AddAction");
    }
    finally
    {
        try { Directory.Delete(vendorTmp, true); } catch { }
    }

    var vendorDump = new ObsoleteEntry
    {
        Type = "XRL.World.IInventoryActionsEvent",
        Member = "AddAction",
        SearchPattern = @"\.AddAction\(\s*(?:\$?@?""|Name\s*:)",
    };
    var vendorLook = System.Text.RegularExpressions.Regex.Match(vendorAdd, vendorDump.SearchPattern);
    Assert(vendorLook.Success, "dump pattern still matches vendor Look");
    Assert(!HitFilter.ShouldReport(vendorDump, vendorAdd, vendorLook),
        "dump must not flag custom vendor AddAction");

    const string invTyped = """
        class C {
          void M(IInventoryActionsEvent E) {
            E.AddAction("Look", "look", "CmdLook", Key: 'l', Priority: 10);
          }
        }
        """;
    var invLook = System.Text.RegularExpressions.Regex.Match(invTyped, vendorDump.SearchPattern);
    Assert(invLook.Success, "dump pattern matches inventory Look");
    Assert(HitFilter.ShouldReport(vendorDump, invTyped, invLook),
        "dump still flags real inventory AddAction");
}

// CS8209 void discard + AddXMLAction literals + Statistic 5-arg + liquid ctor + GameText extras
{
    const string discardSrc = """
        class C {
          void M(IInventoryActionsEvent E) {
            _ = E.AddAction("Kiss", "kiss", "CmdKiss", null, 'k', true, 0, 0, false, true);
            _ = E.AddAction(new InventoryAction { Name = "Keep" });
          }
        }
        """;
    var tmpMod = Path.Combine(toolsRoot, "scratch", "apimigrator-sidecar-test");
    Directory.CreateDirectory(tmpMod);
    try
    {
        var inv = InventoryActionsXmlFixer.FixMod(tmpMod, new Dictionary<string, string>
        {
            [Path.Combine(tmpMod, "E.cs")] = discardSrc,
        });
        Assert(inv.UpdatedContents.Count == 1, "inventory C# rewritten");
        var invCs = inv.UpdatedContents.Values.First();
        AssertContains(invCs, "AddXMLAction(\"Kiss\")", "literal → AddXMLAction");
        AssertNotContains(invCs, "_ = E.AddXMLAction", "Kiss discard stripped");
        AssertNotContains(invCs, "_ = E.AddAction", "InventoryAction discard stripped");
        Assert(inv.SidecarFiles.Count == 1, "InventoryActions.xml written");
        var invXml = inv.SidecarFiles.Values.First();
        AssertContains(invXml, "Name=\"Kiss\"", "Kiss xml name");
        AssertContains(invXml, "<command>CmdKiss</command>", "Kiss command");
        AssertContains(invXml, "<worksAtDistance>true</worksAtDistance>", "worksAtDistance");
    }
    finally
    {
        try { Directory.Delete(tmpMod, true); } catch { }
    }

    var invRunMod = Path.Combine(Path.GetDirectoryName(toolsRoot)!, "_reports", "apimigrator-invxml-run");
    Directory.CreateDirectory(invRunMod);
    try
    {
        File.WriteAllText(Path.Combine(invRunMod, "manifest.json"),
            """{ "id": "invxmltest", "title": "InvXmlTest" }""");
        File.WriteAllText(Path.Combine(invRunMod, "E.cs"), """
            class C {
              void M(IInventoryActionsEvent E) {
                E.AddAction("Kiss", "kiss", "CmdKiss", null, 'k', true, 0, 0, false, true);
              }
            }
            """);
        MigrationRunner.Run(new MigrationOptions
        {
            Paths = { invRunMod },
            Apply = true,
            Backup = false,
            DumpPath = Path.Combine(toolsRoot, "data", "obsolete_api_dump.json"),
            RulesPath = Path.Combine(toolsRoot, "data", "curated_rewrite_rules.json"),
            ExcludeDirs = new List<string> { "_tools", "bin", "obj", ".git" },
        });
        var invXmlPath = Path.Combine(invRunMod, "InventoryActions.xml");
        Assert(File.Exists(invXmlPath), "MigrationRunner writes InventoryActions.xml sidecar");
        AssertContains(File.ReadAllText(invXmlPath), "Name=\"Kiss\"", "Kiss in written xml");
        AssertContains(File.ReadAllText(Path.Combine(invRunMod, "E.cs")), "AddXMLAction(\"Kiss\")",
            "C# AddXMLAction on disk");
    }
    finally
    {
        try { Directory.Delete(invRunMod, true); } catch { }
    }

    var (discFixed, discN) = AddActionFixer.Fix("_ = E.AddAction(new InventoryAction { Name = \"X\" });");
    Assert(discN >= 1, "discard strip on object form: " + discN);
    AssertContains(discFixed, "E.AddAction(new InventoryAction", "receiver kept");
    AssertNotContains(discFixed, "_ =", "discard gone");

    const string statSrc = """
        class C {
          Statistic Make(GameObject GO) {
            return new Statistic("PsiCharges", 0, 9999, 3, GO);
          }
        }
        """;
    var (statFixed, statN, statXml) = StatisticCtorFixer.FixContent(statSrc);
    Assert(statN == 1, "one Statistic ctor: " + statN);
    AssertContains(statFixed, "StatisticBlueprint.TryGet(\"PsiCharges\"", "TryGet");
    AssertContains(statFixed, "Owner = GO", "Owner kept");
    AssertContains(statFixed, "BaseValue = 3", "BaseValue");
    AssertNotContains(statFixed, "new Statistic(\"PsiCharges\", 0", "5-arg gone");
    Assert(statXml.Any(s => s.Name == "PsiCharges"), "xml name");

    const string liqSrc = """
        namespace XRL.Liquids {
          [IsLiquid]
          class PoisonIchor : BaseLiquid {
            public PoisonIchor() : base("poisonichor") {
              FlameTemperature = 250;
              ConsiderDangerousToDrink = true;
            }
            public override bool IsLiquid => true;
            public override bool Drank() => true;
          }
        }
        """;
    var (liqFixed, liqN, liqKids) = LiquidCsToXmlFixer.FixContent(liqSrc);
    Assert(liqN >= 3, "liquid edits: " + liqN);
    AssertNotContains(liqFixed, "[IsLiquid]", "attr gone");
    AssertNotContains(liqFixed, "FlameTemperature", "setter gone");
    AssertNotContains(liqFixed, "IsLiquid =>", "override gone");
    AssertContains(liqFixed, "Drank()", "behavior kept");
    Assert(liqKids.Any(l => l.Name == "poisonichor" && l.InnerXml.Contains("flameTemperature")), "xml name is ctor slug");

    const string ichorSrc = """
        namespace XRL.Liquids {
          public class LiquidIchor : BaseLiquid {
            public LiquidIchor() : base("ichor") { }
            public static List<string> Colors = new List<string> { "r", "K" };
            public override string GetName() => "{{r|ichor}}";
            public override string GetColor() => "r";
            public override List<string> GetColors() => Colors;
            public override float GetValuePerDram() => 3f;
            public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, StringBuilder Message, ref bool ExitInterface)
            {
              Message.Compound("The flavor of otherworldly metals burns your mouth.");
              return true;
            }
          }
        }
        """;
    var (ichorCs, ichorN, ichorKids) = LiquidCsToXmlFixer.FixContent(ichorSrc);
    Assert(ichorN >= 4, "ichor name/color/value edits: " + ichorN);
    Assert(ichorKids.Any(l => l.Name == "ichor" && l.InnerXml.Contains("displayName")), "ichor xml Name=slug");
    Assert(ichorKids.Any(l => l.InnerXml.Contains("<colors>rK</colors>")), "colors concatenated");
    var (drankCs, drankEdits, drankParts) = LiquidDrankToPartFixer.FixContent(ichorCs);
    Assert(drankEdits == 1, "own Drank extracted: " + drankEdits);
    AssertNotContains(drankCs, "override bool Drank", "Drank override gone");
    Assert(drankParts.Any(p => p.InnerXml.Contains("MessageOnDrink")), "static drink → MessageOnDrink");

    const string complexDrank = """
        namespace XRL.Liquids {
          public class LiquidIchor : BaseLiquid {
            public LiquidIchor() : base("ichor") { }
            public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, StringBuilder Message, ref bool ExitInterface)
            {
              if (Target == null) return true;
              Target.Statistics["MA"].BaseValue += Volume;
              return true;
            }
          }
        }
        """;
    var (partCs, partEdits, partKids) = LiquidDrankToPartFixer.FixContent(complexDrank);
    Assert(partEdits == 1, "complex Drank → part: " + partEdits);
    AssertContains(partCs, "class IchorOnDrink : BaseLiquidPart", "OnDrink part class");
    AssertContains(partCs, "Drank(ref DrankEvent E)", "DrankEvent signature");
    AssertNotContains(partCs, "override bool Drank(LiquidVolume", "old Drank gone");
    Assert(partKids.Any(p => p.LiquidName == "ichor" && p.InnerXml.Contains("IchorOnDrink")), "xml part Name");

    const string existingLiquid = """
        <?xml version="1.0" encoding="utf-8"?>
        <liquids Encoding="utf-8">
          <liquid Name="ichor">
            <slug>ichor</slug>
            <class>LiquidIchor</class>
            <render />
          </liquid>
        </liquids>
        """;
    var incoming = "    <part Name=\"IchorOnDrink\" Class=\"IchorOnDrink\" />\n    <render>\n      <baseColor>&amp;r</baseColor>\n    </render>\n";
    var mergedInner = XmlOverlayMerger.MergeMissingInner(existingLiquid, "liquid", "ichor", incoming);
    AssertContains(mergedInner, "IchorOnDrink", "merge-missing part");
    AssertContains(mergedInner, "baseColor", "empty render replaced");
    AssertNotContains(mergedInner, "<render />", "empty render gone");
    var mergedAgain = XmlOverlayMerger.MergeMissingInner(mergedInner, "liquid", "ichor", incoming);
    Assert(mergedAgain == mergedInner, "second merge does not duplicate");

    var freezeIncoming = """
            <freezeObject Name="SmallBoulder" Threshold="1" Verb="solidify" />
            <freezeObject Name="MediumBoulder" Threshold="100" Verb="solidify" />
        """;
    var freezeMerged = XmlOverlayMerger.MergeMissingInner(existingLiquid, "liquid", "ichor", freezeIncoming);
    AssertContains(freezeMerged, "Name=\"SmallBoulder\"", "first freeze object merged");
    AssertContains(freezeMerged, "Name=\"MediumBoulder\"", "second freeze object merged");

    AssertContains(ManualAdvice.DrankAdvice(), "MessageOnDrink", "DrankAdvice OnDrink");
    AssertContains(ManualAdvice.PreferXmlAdvice("Drank"), "LiquidDrankToPartFixer", "PreferXML.Drank");
    AssertContains(ManualAdvice.PreferHarmonyAdvice("Drank"), "Prefix/Postfix", "vanilla Drank Harmony");
    AssertNotContains(ManualAdvice.DrankAdvice(), "bump StringBuilder Message → TextBuilder Message (`using XRL.World.Text;`)", "no keep-override bump");

    const string gtSrc = """
        class G {
          void M(GameObject go, GameObject tgt) {
            XDidY(go, "emerge", "from the depths", "!");
            XDidYToZ(go, "grab", "at", tgt, null, "!");
            var s = Grammar.InitLowerIfArticle(go.DisplayName);
            var t = go.its + " hide";
            var v = go.GetVerb("are");
          }
        }
        """;
    var (gtFixed, gtN) = GameTextCallSiteFixer.Fix(gtSrc);
    Assert(gtN >= 4, "GameText extra edits: " + gtN);
    AssertContains(gtFixed, "=subject.Does:emerge= from the depths!", "XDidY endmark");
    AssertContains(gtFixed, "=subject.Does:grab= at =object.the.name=!", "XDidYToZ");
    AssertContains(gtFixed, "=text|initLowerIfArticle=", "InitLowerIfArticle");
    AssertContains(gtFixed, "=object.its=", "its property");
    AssertContains(gtFixed, "=object.verb:are=", "GetVerb");

    // Real-world Winged-Monotone overload shapes: positional colors/subjects,
    // variable-backed words, and long calls with optional named arguments.
    const string extendedMessages = """
        class ExtendedMessages {
          void A(GameObject ParentObject, GameObject O) {
            string verb1 = "begin to gather";
            string extra1 = "psionic energy";
            string termiPun1 = ".";
            XDidY(ParentObject, verb1, extra1, termiPun1, "C", ParentObject);
            IComponent<GameObject>.XDidY(ParentObject, "breath", "a cone of " + GetBreathName(), "!", null, null,
              ParentObject, null, UseFullNames: false, IndefiniteSubject: false, null, null,
              DescribeSubjectDirection: true);
            XDidY(Verb: "disappears", Actor: O);
            XDidY(Actor: ParentObject, Verb: "rush", Extra: "from the depths to strike!",
              EndMark: "!", ColorAsGoodFor: ParentObject);
          }
          void B(GameObject Object) {
            DidX("are", "incapacitated", "!", null, null, Object);
          }
        }
        """;
    var (extendedOut, extendedN) = GameTextCallSiteFixer.Fix(extendedMessages);
    Assert(extendedN >= 6, "extended message calls and locals: " + extendedN);
    AssertNotContains(extendedOut, "XDidY(", "all extended XDidY calls gone");
    AssertNotContains(extendedOut, "DidX(", "extended DidX gone");
    AssertContains(extendedOut, "EmitMessage('C', ColorAsBadFor: ParentObject)", "color string becomes char");
    AssertContains(extendedOut, "=subject.Does:disappears=", "named XDidY verb");
    AssertContains(extendedOut, ".SetSubject(O).EmitMessage()", "named XDidY actor");
    AssertContains(extendedOut, "EmitMessage(ColorAsGoodFor: ParentObject)", "named XDidY good color");
    AssertContains(extendedOut, ".SetArgument(\"extra\", \"a cone of \" + GetBreathName())", "dynamic extra retained");
    AssertContains(extendedOut, ".SetSubject(Object)", "trailing DidX subject retained");
    AssertNotContains(extendedOut, "string verb1", "consumed verb local removed");
    AssertNotContains(extendedOut, "string extra1", "consumed extra local removed");
    AssertNotContains(extendedOut, "string termiPun1", "consumed punctuation local removed");

    const string becomingText = """
        class BecomingText {
          string M(GameObject target, GameObject item, string word) =>
            target.t() + item.an() + target.does("carry") + target.Does("move") + target.poss("armor") +
            target.them + target.itis + Grammar.MakeTitleCase(word);
          string Flags(GameObject target) => target.t(int.MaxValue, Stripped: true, WithoutTitles: true);
          string Liquid(LiquidVolume liquid) => liquid.GetLiquidName();
        }
        """;
    var (becomingOut, becomingN) = GameTextCallSiteFixer.Fix(becomingText);
    Assert(becomingN == 10, "Becoming GameText calls: " + becomingN);
    AssertContains(becomingOut, "=object.the.name=", "t call");
    AssertContains(becomingOut, "=object.a.name=", "an call");
    AssertContains(becomingOut, "=object.does:carry=", "does call");
    AssertContains(becomingOut, "=object.Does:move=", "Does call");
    AssertContains(becomingOut, "=object.the.name's:withTitles= armor", "poss call");
    AssertContains(becomingOut, "=object.them=", "them property");
    AssertContains(becomingOut, "=object.itis=", "itis property");
    AssertContains(becomingOut, "=text|title=", "MakeTitleCase call");
    AssertContains(becomingOut, "=LiquidVolume.liquid.name=", "GetLiquidName call");

    const string sulfurLiquid = """
        namespace XRL.Liquids {
          class LiquidSulfur : BaseLiquid {
            public LiquidSulfur() : base("liquidsulfur") {
              FlameTemperature = 800;
              Temperature = 360;
              Weight = 0.3;
              Glows = true;
              FreezeObject1 = "SmallBoulder";
              FreezeObjectThreshold1 = 1;
              FreezeObjectVerb1 = "solidify";
            }
            public static List<string> Colors = new List<string>(3) { "A", "a", "y" };
            public override List<string> GetColors() { return Colors; }
            public override void BeforeRender(LiquidVolume Liquid) {
              if (!Liquid.Sealed) { Liquid.AddLight(50); }
            }
            public override bool Vaporized(LiquidVolume Liquid, GameObject Object) { return false; }
            public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, StringBuilder Message, ref bool ExitInterface) {
              Target.TemperatureChange(Temperature, Target);
              ExitInterface = true;
              return true;
            }
          }
        }
        """;
    var (sulfurDrinkCs, sulfurDrinkN, _) = LiquidDrankToPartFixer.FixContent(sulfurLiquid);
    Assert(sulfurDrinkN == 1, "sulfur Drank extracted first");
    AssertContains(sulfurDrinkCs, "TemperatureChange(360, Target)", "part binds liquid Temperature literal");
    AssertContains(sulfurDrinkCs, "try", "OnDrink body protected by finally");
    AssertContains(sulfurDrinkCs, "E.ExitInterface = ExitInterface", "ExitInterface propagated");
    AssertNotContains(sulfurDrinkCs, "SulfurOnDrinkBody", "no nested local return wrapper");
    var (sulfurCs, sulfurN, sulfurXml) = LiquidCsToXmlFixer.FixContent(sulfurDrinkCs);
    Assert(sulfurN >= 5, "consecutive sulfur fields migrated: " + sulfurN);
    AssertNotContains(sulfurCs, "static List<string> Colors", "literal Colors field removed with getter");
    AssertNotContains(sulfurCs, "GetColors()", "literal Colors getter removed");
    AssertContains(sulfurCs, "TemperatureChange(360, Target)", "removed liquid property references bind to literals");
    Assert(sulfurXml.Any(l => l.InnerXml.Contains("<temperature>360</temperature>") &&
                              l.InnerXml.Contains("<weight>0.3</weight>") &&
                              l.InnerXml.Contains("<colors>Aay</colors>") &&
                              l.InnerXml.Contains("<part Name=\"Glows\" Class=\"Glows\" LightLevel=\"50\" />") &&
                              l.InnerXml.Contains("<part Name=\"NoVapor\" Class=\"NoVapor\" />") &&
                              l.InnerXml.Contains("<freezeObject Name=\"SmallBoulder\" Threshold=\"1\" Verb=\"solidify\" />")),
        "all consecutive liquid metadata emitted");
    AssertNotContains(sulfurCs, "BeforeRender", "simple obsolete glow hook migrated");
    AssertNotContains(sulfurCs, "Vaporized", "simple obsolete no-vapor hook migrated");

    const string globalLiquid = """
        class PoisonIchor : BaseLiquid {
          public PoisonIchor() : base("poisonichor") { Temperature = 0; }
          public override bool Drank(LiquidVolume Liquid, int Volume, GameObject Target, StringBuilder Message, ref bool ExitInterface) {
            return true;
          }
        }
        """;
    var (globalDrinkOut, globalDrinkN, _) = LiquidDrankToPartFixer.FixContent(globalLiquid);
    Assert(globalDrinkN == 1, "global-namespace liquid Drank extracted");
    AssertContains(globalDrinkOut, "namespace XRL.Liquids.Parts", "global liquid gets namespaced part");
    AssertNotContains(globalDrinkOut, "override bool Drank(LiquidVolume", "global obsolete Drank removed");

    const string dynamicColors = """
        class LiquidDynamic : BaseLiquid {
          public static List<string> Colors = new List<string>(3) { "A", "a", GoldString };
          public override List<string> GetColors() { return Colors; }
        }
        """;
    var (dynamicColorsOut, _, _) = LiquidCsToXmlFixer.FixContent(dynamicColors);
    AssertContains(dynamicColorsOut, "GoldString", "dynamic Colors field retained");
    AssertContains(dynamicColorsOut, "GetColors()", "dynamic Colors getter retained");

    const string modernDiagnostics = """
        class ModernDiagnostics {
          private int SecondDuration;
          public override bool Render(RenderEvent E) { if (SecondDuration > 0) return false; return base.Render(E); }
          void Damage(GameObject GO, GameObject attacker) {
            TextBuilder stringBuilder = TextBuilder.Get();
            int amount = 3;
            GO.TakeDamage(amount, stringBuilder, null, null, null, attacker);
            bool flag = false;
            Brain.HasGoal("FleeLocation");
            ParentObject.WantTurnTick(this);
            E.Actor.GiveDramsEvent(10, "water");
            FetchBitById('A');
          }
          bool Tick() { return base.Does = TurnTick; }
          void Icons(IEnumerable<MissileWeaponAreaWeaponStatus> statuses) {
            using var icons = ScopeDisposedList<IRenderable>.GetFromPoolFilledWith(statuses.Select(s => s.renderable));
          }
        }
        """;
    var (modernOut, modernN) = ModernCompilerFixer.Fix(modernDiagnostics);
    Assert(modernN >= 8, "modern compiler diagnostics fixed: " + modernN);
    AssertContains(modernOut, "override bool Render", "current bool Render return type preserved");
    AssertContains(modernOut, "return base.Render(E)", "Render return value preserved");
    AssertContains(modernOut, "TakeDamage(ref amount, stringBuilder.ToString(),", "TakeDamage ref/TextBuilder fixed");
    AssertContains(modernOut, "HasGoal<FleeLocation>()", "HasGoal generic fixed");
    AssertContains(modernOut, "WantTurnTick()", "WantTurnTick arity fixed");
    AssertContains(modernOut, ".GiveDrams(10", "GiveDramsEvent renamed");
    AssertContains(modernOut, "BitType.FetchBitByCode('A')", "bit lookup renamed");
    AssertNotContains(modernOut, "bool flag", "unused literal local removed");
    AssertContains(modernOut, "SecondDuration = 0", "read-only default field explicitly initialized");
    AssertContains(modernOut, "return base.WantTurnTick();", "older mangled tick return repaired");
    AssertContains(modernOut, "Select(s => (IRenderable)s.renderable)",
        "Visual value sequence cast to IRenderable");

    const string mangledRender = "class OldOutput { public override void Render(RenderEvent E) { base.Render(E); } }";
    var (healedRender, healedRenderN) = ModernCompilerFixer.Fix(mangledRender);
    Assert(healedRenderN == 1, "older void Render output healed");
    AssertContains(healedRender, "override bool Render", "void Render changed back to bool");
    AssertContains(healedRender, "return base.Render(E);", "base Render result returned");
}

// Improved Mutations follow-ups — FinalizeString CS1503, AppendSigned, DidX trailing defaults, itself, The+DisplayName
{
    const string tbSrc = """
        using XRL.World.Text;
        class C {
          string M(int Level) {
            TextBuilder stringBuilder = TextBuilder.Get("");
            stringBuilder.AppendSigned(3, "rules");
            AddsRep.AppendDescription(stringBuilder, "arachnids", 300, null, null, false, false);
            return Event.FinalizeString(stringBuilder);
          }
        }
        """;
    var (tbOut, tbFixes) = TextBuilderCsFixer.Fix(tbSrc);
    Assert(tbFixes.Any(f => f.RuleName == TextBuilderCsFixer.FinalizeRuleName), "FinalizeString fix");
    Assert(tbFixes.Any(f => f.RuleName == TextBuilderCsFixer.AppendSignedRuleName), "AppendSigned fix");
    Assert(tbFixes.Any(f => f.RuleName == TextBuilderCsFixer.AddsRepRuleName), "AddsRep arity fix");
    AssertContains(tbOut, "AppendModifier(3, \"rules\")", "AppendModifier");
    AssertContains(tbOut, "AppendDescription(stringBuilder, 300, \"arachnids\", false)", "AddsRep swap");
    AssertContains(tbOut, "stringBuilder.ToString()", "Finalize → ToString");
    AssertNotContains(tbOut, "Event.FinalizeString", "FinalizeString gone");
    AssertNotContains(tbOut, "AppendSigned", "AppendSigned gone");

    const string refSbSrc = """
        using System.Text;
        using XRL.World.Text;
        class C {
          string M() {
            var SB = TextBuilder.Get();
            return ApplyHotkey("look", 'l', null, ref SB);
          }
          private static string ApplyHotkey(string Display, char Key, string Prefer, ref StringBuilder SB)
          {
            SB ??= TextBuilder.Get();
            return Display;
          }
        }
        """;
    var (refSbOut, refSbFixes) = TextBuilderCsFixer.Fix(refSbSrc);
    Assert(refSbFixes.Any(f => f.RuleName == TextBuilderCsFixer.RefStringBuilderParamRuleName),
        "ref StringBuilder param retarget recorded");
    AssertContains(refSbOut, "ref TextBuilder SB", "param is TextBuilder");
    AssertNotContains(refSbOut, "ref StringBuilder", "StringBuilder param gone");

    const string didSrc = """
        class Fluffy {
          void M() {
            base.DidX("skid", "around but quickly recover", ".", null, "&R", null, this.ParentObject, false, false, null, null, false, false, false, false, false, null);
            MessageQueue.AddPlayerMessage("=object.The=".StartReplace().SetObject(this.ParentObject).ToString() + this.ParentObject.DisplayName + " falls.");
            if (list.Count == 1 && mutation.ParentObject.IsPlayer() && Popup.ShowYesNoCancel("Are you sure you want to target " + mutation.ParentObject.itself + "?", "Sounds/UI/ui_notification", true, DialogResult.Cancel) != DialogResult.Yes)
              return;
            var x = this.ParentObject.itself;
          }
        }
        """;
    var (didOut, didN) = GameTextCallSiteFixer.Fix(didSrc);
    Assert(didN >= 3, "DidX/itself/The.name edits: " + didN);
    AssertContains(didOut, "=subject.Does:skid= around but quickly recover.", "DidX trailing defaults");
    AssertContains(didOut, "=object.The.name=", "The+DisplayName collapse");
    AssertContains(didOut, "!mutation.TargetSelfConfirm()", "TargetSelfConfirm");
    AssertContains(didOut, "=object.itself=", "itself token");
    AssertNotContains(didOut, "base.DidX(", "DidX gone");

    const string hearthSrc = """
        namespace Hearthpyre.AI {
          class Cook {
            void M() {
              ParentObject.Physics.DidX("start", "cooking");
              Messaging.XDidYToZ(ParentObject, "pray", "to", altar, null, "!");
              switch (key) { case Keys.A: break; }
              extraDimension.a = Grammar.weirdLowerAs.GetRandomElement();
              var s = "=object.The=".StartReplace().SetObject(go).ToString() + go.DisplayNameOnly;
            }
          }
        }
        """;
    var (hearthOut, hearthN) = GameTextCallSiteFixer.Fix(hearthSrc);
    Assert(hearthN >= 3, "Hearthpyre-class GameText edits: " + hearthN);
    AssertContains(hearthOut, "=subject.Does:start= cooking", "Physics.DidX template");
    AssertContains(hearthOut, "SetSubject(ParentObject)", "Physics.DidX subject is GO");
    AssertNotContains(hearthOut, "Physics.\"", "DidX does not leave Physics.\" remnant");
    AssertNotContains(hearthOut, "Messaging.\"", "XDidYToZ does not leave Messaging.\" remnant");
    AssertContains(hearthOut, "case Keys.A:", "Keys.A case label kept");
    AssertNotContains(hearthOut, "SetObject(Keys)", "Keys.A not rewritten as pronoun");
    AssertContains(hearthOut, "extraDimension.a =", "pronoun assignment kept");
    AssertContains(hearthOut, "=object.The.name=", "DisplayNameOnly collapsed");
    AssertNotContains(hearthOut, "ToString()Only", "DisplayName prefix does not leave Only");
    AssertContains(hearthOut, "using XRL;", "Hearthpyre.AI gets using XRL");
    AssertContains(hearthOut, "using XRL.World.Text;", "Hearthpyre.AI gets Text using");

    // XRL.The is the static helper (The.Game / The.Player), not GameObject.The
    const string xrlTheSrc = """
        using XRL;
        class BodySwap {
          void M() {
            var OriginalBody = XRL.The.Game.Player._Body;
            Cell cell = XRL.The.Game.Player._Body.PickDirection();
            XRL.The.Game.Player._Body = TargetHusk;
            XRL.The.Game.Player.Body = ParentObject;
            var t = ParentObject.The;
          }
        }
        """;
    var (xrlTheOut, xrlTheN) = GameTextCallSiteFixer.Fix(xrlTheSrc);
    AssertContains(xrlTheOut, "XRL.The.Game.Player._Body", "XRL.The.Game not mangled");
    AssertContains(xrlTheOut, "XRL.The.Game.Player.Body", "XRL.The.Game.Player.Body kept");
    AssertNotContains(xrlTheOut, "SetObject(XRL)", "XRL.The not rewritten as GameText");
    AssertContains(xrlTheOut, "=object.The=", "real GameObject.The still rewritten");
    Assert(xrlTheN >= 1, "ParentObject.The still auto-fixed");

    const string mangledXrlTheSrc = """
        class Broken {
          void M() {
            var b = "=object.The=".StartReplace().SetObject(XRL).ToString().Game.Player._Body;
          }
        }
        """;
    var (repairedXrlThe, repairedN) = GameTextCallSiteFixer.Fix(mangledXrlTheSrc);
    Assert(repairedN >= 1, "mangled XRL.The repaired: " + repairedN);
    AssertContains(repairedXrlThe, "XRL.The.Game.Player._Body", "repair restores XRL.The");
    AssertNotContains(repairedXrlThe, "SetObject(XRL)", "mangled SetObject(XRL) gone");

    const string tbSbSrc = """
        using System.Text;
        class Material {
          void M() {
            var SB = TextBuilder.Get();
            AppendName(SB, item);
            Substitute(SB, "x");
          }
        }
        """;
    var (tbSbOut, tbSbFixes) = TextBuilderCsFixer.Fix(tbSbSrc);
    Assert(tbSbFixes.Any(f => f.RuleName == TextBuilderCsFixer.StringBuilderConsumerRuleName),
        "StringBuilder consumer revert recorded");
    AssertContains(tbSbOut, "new StringBuilder()", "Get reverted");
    AssertNotContains(tbSbOut, "TextBuilder.Get()", "Get gone when passed to AppendName");

    const string mutSrc = """
        class Improved_MultipleArms : BaseMutation {
          public override void SetVariant(string Variant) {
            this.Pairs = Convert.ToInt32(Variant);
            this.DisplayName = "Multiple Arms (" + (2 * (this.Pairs + 1)) + ")";
          }
        }
        """;
    var (mutOut, mutN) = BaseMutationSetterFixer.Fix(mutSrc);
    Assert(mutN == 1, "SetVariant DisplayName removed");
    AssertNotContains(mutOut, "this.DisplayName =", "DisplayName setter gone");

    var (exprMutOut, exprMutN) = BaseMutationSetterFixer.Fix(
        "class EatersInterdiction : BaseMutation { public EatersInterdiction() => this.Type = \"Mental\"; }");
    Assert(exprMutN == 1, "expression-bodied Type setter removed");
    AssertContains(exprMutOut, "public EatersInterdiction() { }", "constructor remains valid");

    const string mutationOnEquipReads = """
        class C {
          void M(GameObject item) {
            MutationOnEquip mutationOnEquip = item.GetPart<MutationOnEquip>();
            Add(mutationOnEquip.ClassName, mutationOnEquip.Variant);
          }
        }
        """;
    var (mutationReadsOut, mutationReadsN) = MutationOnEquipCsFixer.Fix(mutationOnEquipReads);
    Assert(mutationReadsN == 2, "MutationOnEquip reads migrated");
    AssertContains(mutationReadsOut, "mutationOnEquip.GetMutationEntry().Class", "ClassName read");
    AssertContains(mutationReadsOut, "Add(mutationOnEquip.GetMutationEntry().Class, null)", "Variant read removed");
}

// Ollama leftover suggester — JSON parse, skip PreferHarmony, model tag resolve
{
    AssertNotContains(OllamaLeftoverSuggester.SystemPrompt, "If unsure, set skip=true", "no skip-if-unsure");
    AssertContains(OllamaLeftoverSuggester.SystemPrompt, "PERFORM the migration", "rewrite not advise");

    var parsed = OllamaLeftoverSuggester.ParseResponse("""
        {"skip":false,"confidence":"high","replacement":"go.EmitMessage(\"=subject.Does:fling= =object.its= quills.\");","explanation":"concat Extra"}
        """);
    Assert(!parsed.Skip, "ollama json not skip");
    Assert(parsed.Confidence == "high", "confidence");
    AssertContains(parsed.Replacement, "EmitMessage", "replacement");

    var fenced = OllamaLeftoverSuggester.ParseResponse("""
        ```json
        {"skip":true,"confidence":"low","replacement":"","explanation":"unsure"}
        ```
        """);
    Assert(fenced.Skip, "fenced skip");

    var hedge = OllamaLeftoverSuggester.ParseResponse(
        "{\"skip\":true,\"confidence\":\"medium\",\"replacement\":\"go.EmitMessage(\\\"=subject.Does:fling=\\\");\",\"explanation\":\"maybe\"}");
    Assert(!hedge.Skip, "hedged skip with C# rewrite kept");

    var advice = OllamaLeftoverSuggester.ParseResponse(
        "{\"skip\":false,\"confidence\":\"high\",\"replacement\":\"You should use EmitMessage instead.\",\"explanation\":\"advice\"}");
    Assert(advice.Skip, "advisory replacement rejected");

    var obsolete = OllamaLeftoverSuggester.ParseResponse(
        "{\"skip\":false,\"confidence\":\"high\",\"replacement\":\"[Obsolete] void M() {}\",\"explanation\":\"nope\"}");
    AssertContains(obsolete.Replacement, "[Obsolete]", "parse keeps text; Suggest/TryApply reject it");

    var report = new MigrationReport();
    report.FileResults.Add(new FileScanResult
    {
        FilePath = @"C:\tmp\Foo.cs",
        RemainingHits =
        {
            new RemainingHit { Line = 10, Member = "GameObject.DidX", NeedsManual = true, Text = "DidX(\"fling\");" },
            new RemainingHit { Line = 11, Member = "PreferHarmonyPatch.Register", NeedsManual = true, Text = "override void Register" },
            new RemainingHit { Line = 12, Member = "PreferXML.MutationDisplayName", NeedsManual = true, Text = "DisplayName" },
        },
    });
    var hits = OllamaLeftoverSuggester.CollectHits(report, 20);
    Assert(hits.Count == 1, "skip PreferHarmony/PreferXML");
    Assert(hits[0].Hit.Member == "GameObject.DidX", "kept DidX");

    var status = new OllamaStatus
    {
        Available = true,
        Models = new List<string> { "qwen2.5-coder:7b", "llama3.1:latest" },
    };
    Assert(OllamaClient.ResolveModel(status, "llama3.1") == "llama3.1:latest", "resolve tag");
    var other = new OllamaStatus { Available = true, Models = new List<string> { "phi3:mini", "qwen2.5-coder:7b" } };
    Assert(OllamaClient.ResolveModel(other, "missing") == "qwen2.5-coder:7b", "prefer coding model");

    Assert(OllamaClient.IsCloudHost("https://ollama.com"), "cloud host");
    Assert(OllamaClient.IsLocalHost("http://localhost:11434"), "local host");
    Assert(OllamaClient.NormalizeModelForHost("gpt-oss:120b-cloud", "https://ollama.com") == "gpt-oss:120b", "strip -cloud on direct API");
    Assert(OllamaClient.NormalizeModelForHost("gpt-oss:120b-cloud", "http://localhost:11434") == "gpt-oss:120b-cloud", "keep -cloud on local proxy");
    var cloudOpts = new OllamaOptions { UseCloud = true, BaseUrl = "http://localhost:11434", Model = "llama3.1" };
    OllamaClient.ApplyHostDefaults(cloudOpts);
    Assert(cloudOpts.BaseUrl == OllamaClient.CloudBaseUrl, "cloud switches host");
    Assert(cloudOpts.Model == OllamaClient.DefaultCloudModel, "cloud default model");
    var cloudStatus = new OllamaStatus
    {
        Available = true,
        Cloud = true,
        Models = new List<string> { "glm-5.2", "gpt-oss:120b" },
    };
    Assert(OllamaClient.ResolveModel(cloudStatus, "") == "gpt-oss:20b", "cloud default 20b kept");
    Assert(OllamaClient.ResolveModel(cloudStatus, "gpt-oss:20b") == "gpt-oss:20b", "20b not swapped for 120b");
    Assert(OllamaClient.FindCloudProfile("gpt-oss:20b")?.Title.Contains("20B") == true, "20b profile");
    AssertContains(OllamaClient.DescribeCloudModel("gemma4:31b"), "Multimodal", "gemma blurb");
    AssertContains(OllamaClient.DescribeCloudModel("nemotron-3-ultra"), "1M", "nemotron context");
    Assert(OllamaClient.IsFreeCloudModel("gpt-oss:20b"), "free gpt-oss:20b");
    Assert(OllamaClient.IsFreeCloudModel("gemma4:31b"), "free gemma4");
    Assert(OllamaClient.IsFreeCloudModel("nemotron-3-ultra"), "free nemotron ultra");
    Assert(!OllamaClient.IsFreeCloudModel("glm-5.2"), "paid glm not free");
    var merged = OllamaClient.MergeCloudCatalog(new[] { "glm-5.2", "gpt-oss:120b" });
    Assert(merged[0] == "gemma4:31b", "free catalog first");
    Assert(merged.Contains("gpt-oss:20b"), "seed gpt-oss:20b");
    Assert(merged.Contains("glm-5.2"), "keep extra paid tag");
    Assert(merged.IndexOf("gpt-oss:120b") < merged.IndexOf("glm-5.2"), "free before extra");
}

// Creature Control shapes: interpolated GameObject.The + ShortDisplayName (CS0618);
// GetDisplayName(WithAnnotations:) (CS1739); capital The concat.
{
    const string ccSrc = """
        class CC {
          string Others(GameObject ParentObject, bool enabling, string displayName) {
            var a = $"{ParentObject.The}{ParentObject.ShortDisplayName} resumes leaving a trail.";
            var b = enabling
              ? $"{ParentObject.The}{ParentObject.ShortDisplayName} readies {displayName} spores."
              : $"{ParentObject.The}{ParentObject.ShortDisplayName} quells {displayName} spores.";
            var c = "As " + target.the + target.ShortDisplayName + " dissolves.";
            var d = absorber.The + absorber.ShortDisplayName + " burns brighter.";
            var e = mutation?.GetDisplayName(WithAnnotations: false);
            var f = sporePuffer?.GetDisplayName(WithAnnotations: false);
            return a + b + c + d + e + f;
          }
        }
        """;
    var (ccGt, ccN) = GameTextCallSiteFixer.Fix(ccSrc);
    Assert(ccN >= 4, "The+ShortDisplayName GameText edits: " + ccN);
    AssertContains(ccGt, "=object.The.name= resumes leaving a trail.", "interpolated The+name");
    AssertContains(ccGt, "=object.The.name= readies {displayName} spores.", "keep extra interpolation");
    AssertContains(ccGt, "$\"=object.The.name= readies {displayName} spores.\"", "keep $ when extra holes");
    AssertContains(ccGt, "As =object.the.name= dissolves.", "concat lowercase the");
    AssertContains(ccGt, "=object.The.name=", "concat capital The");
    AssertNotContains(ccGt, "ParentObject.The", "The property gone");
    AssertNotContains(ccGt, "absorber.The", "absorber.The gone");
    var (ccGdn, gdnN) = GetDisplayNameArgFixer.Fix(ccGt);
    Assert(gdnN == 2, "WithAnnotations rename count");
    AssertContains(ccGdn, "GetDisplayName(Annotations: false)", "Annotations named arg");
    AssertNotContains(ccGdn, "WithAnnotations", "WithAnnotations gone");
}

// HarmonyDynamicPatchFixer — removed minigame typeof → Prepare/TargetMethod
{
    const string src = """
        using HarmonyLib;
        [HarmonyPatch(typeof(SifrahGame), "Play")]
        class Patch_SifrahGame
        {
            static void Prefix() { }
            static void Postfix() { }
        }
        """;
    var (fixedSrc, n) = HarmonyDynamicPatchFixer.Fix(src);
    Assert(n == 1, "Harmony dynamic patch edits: " + n);
    AssertContains(fixedSrc, "[HarmonyPatch]", "bare HarmonyPatch");
    AssertNotContains(fixedSrc, "typeof(SifrahGame)", "typeof gone");
    AssertContains(fixedSrc, "static bool Prepare()", "Prepare");
    AssertContains(fixedSrc, "static MethodBase TargetMethod()", "TargetMethod");
    AssertContains(fixedSrc, "AccessTools.TypeByName(\"XRL.World.SifrahGame\")", "TypeByName FQN");
    AssertContains(fixedSrc, "AccessTools.Method(t, \"Play\")", "method Play");
    AssertContains(fixedSrc, "using System.Reflection;", "Reflection using");

    var already = """
        using HarmonyLib;
        using System.Reflection;
        [HarmonyPatch]
        class Patch_SifrahGame
        {
            static bool Prepare() => TargetMethod() != null;
            static MethodBase TargetMethod()
            {
                var t = AccessTools.TypeByName("XRL.World.SifrahGame");
                return t == null ? null : AccessTools.Method(t, "Play");
            }
            static void Prefix() { }
        }
        """;
    var (_, n2) = HarmonyDynamicPatchFixer.Fix(already);
    Assert(n2 == 0, "already-dynamic Harmony patch left alone");
}

// Harmony parameter-name drift: Disarming.Disarm Object → Subject.
{
    const string harmonyParameter = """
        using HarmonyLib;
        [HarmonyPatch]
        static class DisarmingPatch {
          [HarmonyPatch(typeof(Disarming), nameof(Disarming.Disarm))]
          public static void Postfix(GameObject Object, GameObject __result) {
            if (__result == null || Object.Brain == null) return;
            Object.Brain.PushGoal(new EquipObject(__result));
          }
        }
        """;
    var (harmonyParameterOut, harmonyParameterN) = HarmonyPatchParameterFixer.Fix(harmonyParameter);
    Assert(harmonyParameterN == 1, "Harmony Disarm parameter migrated");
    AssertContains(harmonyParameterOut, "Postfix(GameObject Subject, GameObject __result)", "Harmony signature");
    AssertContains(harmonyParameterOut, "Subject.Brain.PushGoal", "Harmony body references");
    AssertNotContains(harmonyParameterOut, "GameObject Object", "stale Harmony parameter gone");
}

// RemovedGameApiFixer — Options.Sifrah* if-block + leftover type report
{
    const string src = """
        class C {
          int M() {
            int attackModifier = 3;
            if (Options.SifrahPsychicCombat)
            {
                PsychicCombatSifrah psychicCombatSifrah = new PsychicCombatSifrah(Target, "Domination");
                psychicCombatSifrah.Play(Target);
                attackModifier = attackModifier * (psychicCombatSifrah.Performance + 50) / 100;
            }
            return attackModifier;
          }
        }
        """;
    var (fixedSrc, n) = RemovedGameApiFixer.Fix(src);
    Assert(n >= 1, "Sifrah if-block stripped: " + n);
    AssertNotContains(fixedSrc, "Options.SifrahPsychicCombat", "option gone");
    AssertNotContains(fixedSrc, "PsychicCombatSifrah", "minigame type gone with block");
    AssertContains(fixedSrc, "return attackModifier;", "fallback kept");

    const string ternary = """
        string GetDetails() => Options.AnySifrah ? "play sifrah" : "stats only";
        """;
    var (ternFixed, tn) = RemovedGameApiFixer.Fix(ternary);
    Assert(tn >= 1, "AnySifrah ternary rewritten");
    AssertContains(ternFixed, "stats only", "false branch kept");
    AssertNotContains(ternFixed, "play sifrah", "true branch dropped");
    AssertNotContains(ternFixed, "AnySifrah", "option gone");

    var leftover = "class X : SocialSifrah { }";
    var hits = RemovedGameApiFixer.Scan(leftover).ToList();
    Assert(hits.Any(h => h.Member == "RemovedType.SocialSifrah"), "leftover type reported");
}

// Campaign learnings: XML Weight= is not PreferXML.LiquidProperties; C# liquid assigns still are
{
    const string xml = """
        <?xml version="1.0" encoding="utf-8"?>
        <objects Encoding="utf-8">
          <object Name="Hookah">
            <part Name="Physics" Weight="10" Takeable="true" />
          </object>
        </objects>
        """;
    var xmlHits = engine.ScanRemainingHits(xml, "ObjectBlueprints.xml");
    Assert(!xmlHits.Any(h => h.Member == LiquidXmlAdviceScanner.LiquidPropsMember),
        "XML Physics Weight= is not LiquidProperties");

    const string cs = """
        class LiquidIchor : BaseLiquid {
          public LiquidIchor() { this.FlameTemperature = 400; }
        }
        """;
    var csHits = engine.ScanRemainingHits(cs, "LiquidIchor.cs");
    Assert(csHits.Any(h => h.Member == LiquidXmlAdviceScanner.LiquidPropsMember),
        "C# FlameTemperature still LiquidProperties");
}

// Faction.getFormattedName / PopupMessage._SingleButton / CachedDoubleSemicolonExpansion
{
    const string src = """
        class C {
          void M(string faction) {
            var n = Faction.getFormattedName(faction);
            Popup.WaitNewPopupMessage("x", buttons: PopupMessage._SingleButton);
            Popup.WaitNewPopupMessage("y", buttons: PopupMessage._YesNoCancelButton);
            List<string> parts = TileStrings.CachedDoubleSemicolonExpansion();
          }
        }
        """;
    var (fixedSrc, fixes) = engine.ApplyCuratedRules(src, "Dice.cs");
    AssertContains(fixedSrc, "GetFormattedName", "getFormattedName PascalCase");
    AssertNotContains(fixedSrc, "getFormattedName", "camelCase gone");
    AssertContains(fixedSrc, "PopupMessage.SingleButton", "public SingleButton");
    AssertNotContains(fixedSrc, "PopupMessage._SingleButton", "private backing gone");
    AssertContains(fixedSrc, "PopupMessage.YesNoCancelButton", "longer _YesNoCancel before _YesNo");
    AssertNotContains(fixedSrc, "PopupMessage._YesNoCancelButton", "private YesNoCancel gone");
    AssertContains(fixedSrc, "IReadOnlyList<string> parts", "IReadOnlyList local");
    Assert(!System.Text.RegularExpressions.Regex.IsMatch(fixedSrc, @"(?<!IReadOnly)List\s*<\s*string\s*>\s+parts"),
        "bare List<string> parts gone");
    Assert(fixes.Any(f => f.RuleName.Contains("getFormattedName", StringComparison.Ordinal) ||
                          f.RuleName.Contains("GetFormattedName", StringComparison.Ordinal)),
        "getFormattedName rule recorded");
    Assert(fixes.Any(f => f.RuleName.Contains("CachedDoubleSemicolonExpansion", StringComparison.Ordinal)),
        "expansion fixer recorded");
}

// WorkshopWrite clears ReadOnly and overwrites
{
    var dir = Path.Combine(toolsRoot, "scratch");
    Directory.CreateDirectory(dir);
    var tmp = Path.Combine(dir, "apimigrator-workshopwrite-test.txt");
    var created = Path.Combine(dir, "apimigrator-workshopwrite-new.txt");
    try
    {
        File.WriteAllText(tmp, "old");
        File.SetAttributes(tmp, File.GetAttributes(tmp) | FileAttributes.ReadOnly);
        WorkshopWrite.WriteAllText(tmp, "new-content");
        Assert(File.ReadAllText(tmp) == "new-content", "WorkshopWrite overwrote ReadOnly file");
        Assert((File.GetAttributes(tmp) & FileAttributes.ReadOnly) == 0, "ReadOnly cleared");

        if (File.Exists(created)) File.Delete(created);
        WorkshopWrite.WriteAllText(created, "brand-new");
        Assert(File.Exists(created), "WorkshopWrite creates missing file");
        Assert(File.ReadAllText(created) == "brand-new", "WorkshopWrite new-file contents");
    }
    finally
    {
        try
        {
            if (File.Exists(tmp))
            {
                File.SetAttributes(tmp, FileAttributes.Normal);
                File.Delete(tmp);
            }
            if (File.Exists(created))
            {
                File.SetAttributes(created, FileAttributes.Normal);
                File.Delete(created);
            }
        }
        catch { /* best-effort cleanup */ }
    }
}

// ManifestFixer — Dependency shorthand (JsonProperty) + LoadAfter, not Dependencies object/caret
{
    const string shotguns = """
        {
          "id": "tyrirshotguns",
          "title": "{{C|{{rocket|Shotguns}}!}}",
          "version": "1.3.0",
          "Dependencies": {
            "moremoddinggoodies": "^1.4.0"
          }
        }
        """;
    var (sg, sgFixes) = ManifestFixer.Fix(shotguns);
    Assert(sgFixes.Count > 0, "Shotguns-style Dependencies object is rewritten");
    AssertContains(sg, "\"Dependency\": \"moremoddinggoodies\"", "Dependency shorthand");
    AssertContains(sg, "\"LoadAfter\": \"moremoddinggoodies\"", "LoadAfter compile order");
    AssertNotContains(sg, "\"Dependencies\"", "Dependencies object gone for single dep");
    AssertNotContains(sg, "^1.4.0", "caret range gone");
    AssertContains(sg, "\"id\": \"tyrirshotguns\"", "id preserved");
    AssertContains(sg, "\"title\": \"{{C|{{rocket|Shotguns}}!}}\"", "title preserved");

    const string already = """
        {
          "id": "tyrirshotguns",
          "title": "Shotguns",
          "version": "1.3.0",
          "Dependency": "moremoddinggoodies",
          "LoadAfter": "moremoddinggoodies"
        }
        """;
    var (alreadyOut, alreadyFixes) = ManifestFixer.Fix(already);
    Assert(alreadyFixes.Count == 0, "already-correct Dependency+LoadAfter is a no-op");
    Assert(alreadyOut == already, "no-op returns original text");

    const string arr = """
        { "id": "pickpocket", "version": "1.0.0", "dependencies": ["Base"] }
        """;
    var (arrOut, arrFixes) = ManifestFixer.Fix(arr);
    Assert(arrFixes.Any(f => f.RuleName.Contains("array", StringComparison.OrdinalIgnoreCase)
                          || f.RuleName.Contains("shorthand", StringComparison.Ordinal)),
        "array deps rewritten: " + string.Join("; ", arrFixes.Select(f => f.RuleName)));
    AssertContains(arrOut, "\"Dependency\": \"Base\"", "array of one → Dependency");
    AssertContains(arrOut, "\"LoadAfter\": \"Base\"", "array of one gets LoadAfter");

    const string multi = """
        {
          "id": "combo",
          "version": "1.0.0",
          "Dependencies": {
            "alpha": "^1.0.0",
            "beta": "1.2.0"
          }
        }
        """;
    var (multiOut, multiFixes) = ManifestFixer.Fix(multi);
    AssertContains(multiOut, "\"Dependencies\"", "multi-dep keeps object");
    AssertNotContains(multiOut, "\"Dependency\"", "multi-dep does not use shorthand");
    AssertContains(multiOut, "\"alpha\": \"*\"", "caret → *");
    AssertContains(multiOut, "\"beta\": \"*\"", "exact version → *");
    AssertContains(multiOut, "\"LoadAfter\": [", "multi-dep LoadAfter is an array");
    AssertContains(multiOut, "alpha", "LoadAfter includes alpha");
    AssertContains(multiOut, "beta", "LoadAfter includes beta");
    Assert(multiFixes.Count > 0, "multi-dep caret/exact rewritten");

    const string workshopKey = """
        {
          "id": "x",
          "version": "1.0.0",
          "Dependencies": {
            "moremoddinggoodies": "*",
            "3403942187": "*"
          }
        }
        """;
    var (wsOut, wsFixes) = ManifestFixer.Fix(workshopKey);
    AssertContains(wsOut, "\"Dependency\": \"moremoddinggoodies\"", "numeric workshop key dropped; leftover single → shorthand");
    AssertNotContains(wsOut, "3403942187", "workshop folder id not a required ModMap key");
    Assert(wsFixes.Any(f => f.RuleName.Contains("workshop", StringComparison.OrdinalIgnoreCase)
                          || f.RuleName.Contains("shorthand", StringComparison.Ordinal)),
        "workshop-id strip recorded");

    Assert(ManifestFixer.IsAnyVersionRange("*"), "* is any-version");
    Assert(ManifestFixer.IsAnyVersionRange("1.0.0 - *"), "wiki closed interval with * high");
    Assert(!ManifestFixer.IsAnyVersionRange("^1.4.0"), "caret is not treated as already-any");
    const string dShotguns = """
        {
            "id": "tyrirshotguns",
            "loadorder": 50000000,
            "title": "{{C|{{rocket|Shotguns}}!}}",
            "version": "1.3.0",
            "previewImage": "preview.png"
        }
        """;
    var inferred = ManifestFixer.InferKnownLibraryModIds(
        new[] { "using tyrir.lib;\nclass C {}" }, "tyrirshotguns");
    Assert(inferred.Contains("moremoddinggoodies"), "tyrir.lib infers moremoddinggoodies");
    var (dOut, dFixes) = ManifestFixer.Fix(dShotguns, inferred);
    Assert(dFixes.Any(f => f.RuleName.Contains("loadOrder", StringComparison.OrdinalIgnoreCase)
                        || f.RuleName.Contains("inferred", StringComparison.Ordinal)
                        || f.RuleName.Contains("shorthand", StringComparison.Ordinal)),
        "D: Shotguns original rewritten: " + string.Join("; ", dFixes.Select(f => f.RuleName)));
    AssertContains(dOut, "\"Dependency\": \"moremoddinggoodies\"", "inferred Dependency");
    AssertContains(dOut, "\"LoadAfter\": \"moremoddinggoodies\"", "inferred LoadAfter");
    AssertNotContains(dOut, "loadorder", "obsolete loadorder removed");
    AssertNotContains(dOut, "LoadOrder", "LoadOrder not reintroduced");
    AssertContains(dOut, "\"id\": \"tyrirshotguns\"", "id still original");
}

{
    var tmp = Path.Combine(Path.GetTempPath(), "apimigrator-modid-" + Guid.NewGuid().ToString("N"));
    var lib = Path.Combine(tmp, "More Modding Goodies!");
    var shot = Path.Combine(tmp, "Shotguns!");
    var leftover = Path.Combine(tmp, "1756765609");
    var fishing = Path.Combine(tmp, "Qud Fishing");
    Directory.CreateDirectory(lib);
    Directory.CreateDirectory(shot);
    Directory.CreateDirectory(leftover);
    Directory.CreateDirectory(fishing);
    File.WriteAllText(Path.Combine(lib, "manifest.json"),
        """{"id":"moremoddinggoodies","title":"More Modding Goodies!","version":"1.0.0"}""");
    File.WriteAllText(Path.Combine(lib, "workshop.json"),
        """{"WorkshopId":3403942187,"Title":"More Modding Goodies!"}""");
    File.WriteAllText(Path.Combine(shot, "manifest.json"),
        """{"title":"Shotguns!","version":"1.3.0","Dependencies":{"3403942187":"*"},"LoadAfter":["3403942187","More Modding Goodies!"]}""");
    File.WriteAllText(Path.Combine(fishing, "manifest.json"),
        """{"id":"Qud_Fishing","title":"Qud Fishing","version":"1.0.0"}""");
    File.WriteAllText(Path.Combine(fishing, "workshop.json"),
        """{"WorkshopId":1756765609,"Title":"Qud Fishing"}""");
    File.WriteAllText(Path.Combine(leftover, "workshop.json"),
        """{"WorkshopId":1756765609,"Title":"Qud Fishing"}""");

    try
    {
        var cat = ModIdCatalog.Build(new[] { tmp });
        Assert(cat.Resolve("3403942187") == "moremoddinggoodies", "workshop id → manifest id");
        Assert(cat.Resolve("More Modding Goodies!") == "moremoddinggoodies", "folder title → manifest id");
        Assert(cat.Resolve("1756765609") == "Qud_Fishing", "numeric leftover workshop id prefers named folder");
        Assert(cat.Resolve("Qud Fishing") == "Qud_Fishing", "folder name → manifest id");
        Assert(cat.CanonicalIdForDirectory(shot) == "Shotguns", "missing id uses sanitized folder");

        var src = File.ReadAllText(Path.Combine(shot, "manifest.json"));
        var (fixedShot, shotFixes) = ManifestFixer.Fix(src, null, cat, cat.CanonicalIdForDirectory(shot));
        AssertContains(fixedShot, "\"id\": \"Shotguns\"", "filled missing id");
        AssertContains(fixedShot, "\"Dependency\": \"moremoddinggoodies\"", "workshop dep remapped");
        AssertNotContains(fixedShot, "3403942187", "workshop folder id gone");
        AssertContains(fixedShot, "\"LoadAfter\": \"moremoddinggoodies\"", "LoadAfter collapsed to canonical");
        Assert(shotFixes.Any(f => f.RuleName.Contains("remap", StringComparison.OrdinalIgnoreCase)
                               || f.RuleName.Contains("fill missing id", StringComparison.OrdinalIgnoreCase)),
            "remap/fill recorded: " + string.Join("; ", shotFixes.Select(f => f.RuleName)));

        var hyphen = """{ "id": "x", "version": "1.0.0", "Dependency": "actual-centipedes" }""";
        var (hyphenOut, _) = ManifestFixer.Fix(hyphen);
        AssertContains(hyphenOut, "\"Dependency\": \"actualcentipedes\"", "hyphen stripped to match ModInfo.ID");

    const string stubsCycle = """
        {
          "id": "WMExtendedMutations_Stubs",
          "version": "1.1.0",
          "Dependency": "WMexMutationsStable",
          "LoadBefore": "WMexMutationsStable",
          "LoadAfter": ["Base", "WMexMutationsStable"]
        }
        """;
    var (stubsOut, stubsFixes) = ManifestFixer.Fix(stubsCycle);
    AssertNotContains(stubsOut, "\"Dependency\"", "LoadBefore host is not also a required Dependency");
    AssertNotContains(stubsOut, "\"Dependencies\"", "no Dependencies object left");
    AssertContains(stubsOut, "\"LoadBefore\": [", "LoadBefore is both WM editions");
    AssertContains(stubsOut, "WMexMutationsBeta", "LoadBefore includes beta");
    AssertContains(stubsOut, "WMexMutationsStable", "LoadBefore includes stable");
    AssertContains(stubsOut, "\"LoadAfter\": \"Base\"", "LoadAfter is only Base");
    Assert(stubsFixes.Any(f => f.RuleName.Contains("LoadBefore", StringComparison.OrdinalIgnoreCase)
                            || f.RuleName.Contains("cycle", StringComparison.OrdinalIgnoreCase)
                            || f.RuleName.Contains("beta or stable", StringComparison.OrdinalIgnoreCase)),
        "cycle strip / WM family recorded: " + string.Join("; ", stubsFixes.Select(f => f.RuleName)));

    const string wmRequiredStable = """
        {
          "id": "WMExtendedMutations_Extended",
          "version": "1.1.0",
          "Dependencies": {
            "WMexMutationsStable": "*",
            "WMExtendedMutations_Stubs": "*"
          },
          "LoadAfter": ["Base", "WMExtendedMutations_Stubs", "WMexMutationsStable"]
        }
        """;
    var (wmReqOut, wmReqFixes) = ManifestFixer.Fix(wmRequiredStable);
    AssertContains(wmReqOut, "\"WMexMutationsBeta|WMexMutationsStable\": \"*\"", "required beta OR stable (one key)");
    AssertNotContains(wmReqOut, "\"WMexMutationsBeta\": \"*\"", "beta is not a separate required AND key");
    AssertNotContains(wmReqOut, "\"WMexMutationsStable\": \"*\"", "stable is not a separate required AND key");
    AssertContains(wmReqOut, "\"WMExtendedMutations_Stubs\": \"*\"", "stubs still required");
    AssertContains(wmReqOut, "WMexMutationsBeta", "LoadAfter includes beta");
    Assert(wmReqFixes.Any(f => f.RuleName.Contains("beta|stable", StringComparison.OrdinalIgnoreCase)
                            || f.RuleName.Contains("beta or stable", StringComparison.OrdinalIgnoreCase)),
        "WM family required recorded: " + string.Join("; ", wmReqFixes.Select(f => f.RuleName)));

    const string wmLoadAfterOnly = """
        { "id": "x", "version": "1.0.0", "LoadAfter": ["Base", "WMexMutationsStable"] }
        """;
    var (wmAfterOut, wmAfterFixes) = ManifestFixer.Fix(wmLoadAfterOnly);
    AssertNotContains(wmAfterOut, "\"Dependency\"", "LoadAfter-only does not invent a required WM dep");
    AssertNotContains(wmAfterOut, "\"Dependencies\"", "LoadAfter-only has no Dependencies object");
    AssertContains(wmAfterOut, "WMexMutationsBeta", "LoadAfter gained beta");
    AssertContains(wmAfterOut, "WMexMutationsStable", "LoadAfter kept stable");
    Assert(wmAfterFixes.Any(f => f.RuleName.Contains("beta or stable", StringComparison.OrdinalIgnoreCase)),
        "WM family LoadAfter recorded");

    const string wmWorkshopDep = """
        { "id": "x", "version": "1.0.0", "Dependency": "2198787801" }
        """;
    var (wmWsOut, _) = ManifestFixer.Fix(wmWorkshopDep);
    AssertContains(wmWsOut, "\"Dependency\": \"WMexMutationsBeta|WMexMutationsStable\"",
        "workshop stable id → single OR required dep");
    AssertNotContains(wmWsOut, "2198787801", "workshop folder id not left as a required key");
    AssertNotContains(wmWsOut, "\"WMexMutationsBeta\": \"*\"", "not AND-required beta");

    const string wmAlreadyOr = """
        {
          "id": "WMexMutations_GelatinousPatch",
          "version": "1.0.2",
          "Dependency": "WMexMutationsBeta|WMexMutationsStable",
          "LoadAfter": ["WMexMutationsBeta", "WMexMutationsStable"]
        }
        """;
    var (wmOrOut, wmOrFixes) = ManifestFixer.Fix(wmAlreadyOr);
    Assert(wmOrFixes.Count == 0, "already beta|stable OR + LoadAfter both is a no-op: "
        + string.Join("; ", wmOrFixes.Select(f => f.RuleName)));
    Assert(wmOrOut == wmAlreadyOr, "no-op returns original text");

    const string wmAndBoth = """
        {
          "id": "x",
          "version": "1.0.0",
          "Dependencies": {
            "WMexMutationsBeta": "*",
            "WMexMutationsStable": "*"
          }
        }
        """;
    var (wmAndOut, _) = ManifestFixer.Fix(wmAndBoth);
    AssertContains(wmAndOut, "\"Dependency\": \"WMexMutationsBeta|WMexMutationsStable\"",
        "AND of both editions collapses to one OR key");
    AssertNotContains(wmAndOut, "\"WMexMutationsBeta\": \"*\"", "AND beta key gone");

    Assert(ManifestFixer.IsWmExtendedFamilyId("2065946296"), "beta workshop id is family");
    Assert(ManifestFixer.MapWmExtendedToken("2198787801") == ManifestFixer.WmExtendedStableId,
        "stable workshop id maps to named stable");
    Assert(ManifestFixer.MapWmExtendedToken("WMexMutationsBeta|WMexMutationsStable")
           == ManifestFixer.WmExtendedEitherId, "pipe is the either-token");
    Assert(!ManifestFixer.IsWmExtendedFamilyId("WMExtendedMutations_Extended"),
        "overlay id is not the WM host family");

    Assert(!ManifestFixer.IsTargetFile(Path.Combine(tmp, "Packages", "manifest.json")),
        "Unity Packages/manifest.json is not a CoQ mod manifest");
    Assert(ManifestFixer.IsTargetFile(Path.Combine(shot, "manifest.json")),
        "mod-root manifest.json is a CoQ target");
    }
    finally
    {
        try { Directory.Delete(tmp, true); } catch { /* best-effort */ }
    }
}

// SteamInstall — registry + libraryfolders autodetection; truncated log paths resolve there
{
    var ws = SteamInstall.WorkshopContentDir;
    var managed = SteamInstall.ManagedDir;
    var lib = SteamInstall.LibraryRoot;
    if (ws is not null)
    {
        Assert(Directory.Exists(ws), "workshop dir exists");
        AssertContains(ws.Replace('/', '\\'), @"workshop\content\333640", "workshop 333640");
    }
    if (managed is not null)
        Assert(File.Exists(Path.Combine(managed, "Assembly-CSharp.dll")), "Managed dll");
    if (lib is not null && managed is not null)
        AssertContains(managed.Replace('/', '\\'), lib.Replace('/', '\\'), "Managed under discovered library");

    // Must not hard-prefer a stale drive when a newer install exists elsewhere.
    var candidates = SteamInstall.CandidateLibraryRoots();
    Assert(candidates.Count > 0, "candidate library roots non-empty");

    var truncated = @"<...>/steamapps/workshop/content/333640/3422802359/manifest.json";
    var resolved = SteamInstall.ResolveLoggedPath(truncated);
    if (ws is not null && Directory.Exists(Path.Combine(ws, "3422802359")))
    {
        Assert(resolved is not null, "truncated workshop path resolved");
        AssertContains(resolved!.Replace('/', '\\'), ws.Replace('/', '\\'), "truncated path used live workshop root");
        Assert(File.Exists(resolved!), "resolved Shotguns manifest exists");
    }
}

// CoqPaths — Mods is LocalLow, not the toolkit parent
{
    Assert(CoqPaths.PathIsUnderRoot(@"C:\mods\Foo\a.cs", @"C:\mods\Foo"), "under root");
    Assert(!CoqPaths.PathIsUnderRoot(@"C:\mods\FooBar\a.cs", @"C:\mods\Foo"), "prefix collision");
    var mods = CoqPaths.ResolveModsRoot(@"D:\games\Ai assisted toolkit\Tools\Qud");
    Assert(mods.EndsWith(@"CavesOfQud\Mods", StringComparison.OrdinalIgnoreCase)
           || Directory.Exists(mods), "ResolveModsRoot finds LocalLow Mods or an existing folder");
}

Console.WriteLine("All ApiMigrator smoke checks passed.");
