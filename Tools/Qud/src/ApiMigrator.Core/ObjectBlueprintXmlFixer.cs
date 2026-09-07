using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Auto-fixes ObjectBlueprintLoader XML pitfalls that emit load ERROR/WARN:
/// inventoryobject Name→Blueprint, obsolete Wire/Projectile/Examiner/MeleeWeapon/
/// Corpse/Brain/Physics attrs, MutationOnEquip ClassName→Mutation, mutation
/// Compat/Class Name renames, Compat blueprint Name renames, Value=*delete→
/// removemutation, role→Role tag, MeleeWeapon ElementalDamage→part, Comwmerce
/// typo, Name whitespace trim, duplicate AnimatedMaterialGeneric→Alternate,
/// duplicate named part/tag merge (later attrs win; CyberneticsHasImplants joins).
/// </summary>
public static class ObjectBlueprintXmlFixer
{
    public const string InventoryBlueprintRuleName =
        "inventoryobject/removeinventoryobject Name= → Blueprint=";

    public const string WireMaterialRuleName =
        "Wire Material= → remove (obsolete Unused)";

    public const string ProjectilePhaseMatchRuleName =
        "Projectile RequiresPhaseMatch= → remove (not a Projectile field)";

    public const string ExaminerAlternateDisplayNameRuleName =
        "Examiner AlternateDisplayName= → remove (not an Examiner field)";

    public const string MutationOnEquipClassNameRuleName =
        "MutationOnEquip ClassName= → Mutation=";

    public const string MutationOnEquipVariantRuleName =
        "MutationOnEquip Variant= → remove (use Mutation=)";

    public const string MutationNameRenameRuleName =
        "object-blueprint mutation Name Compat/Class rename";

    public const string BlueprintNameRenameRuleName =
        "object-blueprint Name/Inherits Compat rename";

    public const string NameTrimRuleName =
        "part/mutation Name= trim whitespace";

    public const string AnimatedMaterialAlternateRuleName =
        "duplicate AnimatedMaterialGeneric → AnimatedMaterialGenericAlternate";

    public const string ObsoletePartAttrRuleName =
        "obsolete part attr strip (MeleeWeapon/Corpse/Brain/Physics/acegiak_Seed)";

    public const string MeleeWeaponSecondaryStatRuleName =
        "MeleeWeapon SecondaryStat= → Stat= (when Stat missing) or remove";

    public const string MeleeWeaponElementalRuleName =
        "MeleeWeapon ElementalDamage/Element → ElementalDamage part";

    public const string MutationValueDeleteRuleName =
        "mutation Value=*delete → removemutation";

    public const string RoleElementRuleName =
        "role Name= → tag Name=Role Value=";

    public const string CommerceTypoRuleName =
        "part Name=Comwmerce → Commerce";

    public const string DuplicateNamedChildRuleName =
        "duplicate named part/tag merge (later wins)";

    /// <summary>
    /// Object-blueprint <c>&lt;mutation Name&gt;</c> / <c>Mutation=</c> values that
    /// ObjectBlueprintLoader resolves via <c>ResolveType(…Mutation, name)</c> (class
    /// name) or Compat renames — not Mutations.xml display entry Names.
    /// </summary>
    public static readonly IReadOnlyDictionary<string, string> MutationNameRenames =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            // Compat.xml
            ["FreezingHands"] = "FreezingRay",
            ["FlamingHands"] = "FlamingRay",
            ["HooksForFeet2"] = "HooksForFeet",
            ["MentalBlast"] = "SunderMind",
            // Display Name / spaced → Class (Mutations.xml Class=)
            ["Freezing Ray"] = "FreezingRay",
            ["Flaming Ray"] = "FlamingRay",
            ["Sleep Gas Generation"] = "SleepGasGeneration",
            ["Stunning Force"] = "StunningForce",
            ["Nerve Poppy"] = "Analgesia",
            ["Two-hearted"] = "TwoHearted",
            ["Two Hearted"] = "TwoHearted",
            ["Double-muscled"] = "HeightenedStrength",
            ["Triple-jointed"] = "HeightenedAgility",
            ["Temporal Fugue"] = "TemporalFugue",
            ["Time Dilation"] = "TimeDilation",
        };

    /// <summary>
    /// Compat.xml <c>&lt;blueprint Old= New=&gt;</c> — rewrite object Name=/Inherits=
    /// so Load=Merge targets the live blueprint id.
    /// </summary>
    public static readonly IReadOnlyDictionary<string, string> BlueprintNameRenames =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["Cyberliver"] = "BionicLiver",
            ["NotakeFurniture"] = "MountedFurniture",
            ["VehicleGolemConsole N"] = "VehicleConsole N",
            ["VehicleGolemConsole S"] = "VehicleConsole S",
            ["Wild Watervine Merchant"] = "Wild Water Merchant",
            ["Glow Wight"] = "BaseGyreWight",
            ["Glow Wight Apotheote"] = "Gyre Wight Apotheote",
            ["Glow-Wight Cultist of Agolgut"] = "Gyre Wight of Agolgot",
            ["Glow-Wight Cultist of Bethsaida"] = "Gyre Wight of Bethsaida",
            ["Glow-Wight Hero of Agolgut 1"] = "Uplifted Still Gyre Wight of Agolgot",
            ["Glow-Wight Hero of Bethsaida 1"] = "Uplifted Still Gyre Wight of Bethsaida",
            ["Naphtaali"] = "BaseNaphtaali",
            ["Chrome Idol Hero 1"] = "Planished Godhed",
            ["Naphtaali Corpse"] = "Woodsprog Corpse",
            ["JoppaZealot"] = "VillageZeroConvert",
            ["Warden Ualraig"] = "Warden Yrame",
            ["Doru"] = "Tam",
            ["Beetlebum Corpse"] = "Giant Beetle Corpse",
            ["Bloated Leech Corpse"] = "Leech Corpse",
            ["UnknownTinyTrinket"] = "UnknownOddTrinket",
            ["UnknownSmallTrinket"] = "UnknownOddTrinket",
        };

    static readonly Regex InventoryObjectTagRx = new(
        @"<(?<tag>removeinventoryobject|inventoryobject)\b(?<attrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Attrs may contain '/' inside quoted values (e.g. RenderString="/"); never use [^>/]*.
    const string AttrsChunk = @"(?<attrs>(?:[^>""'/]|""[^""]*""|'[^']*')*)";

    static readonly Regex PartTagRx = new(
        @"<(?<tag>part)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex MutationTagRx = new(
        @"<(?<tag>mutation)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ObjectTagRx = new(
        @"<(?<tag>object)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex NameAttrRx = new(
        @"\bName\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex InheritsAttrRx = new(
        @"\bInherits\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex MutationAttrRx = new(
        @"\bMutation\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ClassNameAttrRx = new(
        @"\s+ClassName\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex VariantAttrRx = new(
        @"\s+Variant\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex BlueprintAttrRx = new(
        @"\bBlueprint\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex WireMaterialAttrRx = new(
        @"\s+Material\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex RequiresPhaseMatchAttrRx = new(
        @"\s+RequiresPhaseMatch\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex AlternateDisplayNameAttrRx = new(
        @"\s+AlternateDisplayName\s*=\s*(?<q>[""'])[^'""]*\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex AttrRx = new(
        @"\s+(?<name>[A-Za-z_][\w.]*)\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.Compiled);

    static readonly Regex ValueDeleteAttrRx = new(
        @"\s+Value\s*=\s*(?<q>[""'])\*delete\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex StatAttrRx = new(
        @"\bStat\s*=",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex SecondaryStatAttrRx = new(
        @"\s+SecondaryStat\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ElementalDamageAttrRx = new(
        @"\s+ElementalDamage\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ElementAttrRx = new(
        @"\s+Element\s*=\s*(?<q>[""'])(?<val>.*?)\k<q>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static readonly Regex ObjectOpenCloseRx = new(
        @"<(?<close>/)?object\b(?<attrs>[^>]*)>|<(?<tag>part)\b(?<partAttrs>[^>]*)>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // object open/close + named children we may dedupe (attrs never swallow trailing /)
    static readonly Regex ObjectChildScanRx = new(
        @"<(?<close>/)?object\b[^>]*>|<(?<tag>part|tag|mutation|skill|stag|stat|intproperty|property|builder)\b" + AttrsChunk + @"(?<slash>\s*/\s*)?>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    static string RebuildOpenTag(string tag, string attrs, bool selfClose) =>
        selfClose ? $"<{tag}{attrs} />" : $"<{tag}{attrs}>";

    static bool IsSelfClose(Match m) =>
        m.Groups["slash"].Success && m.Groups["slash"].Value.IndexOf('/') >= 0;

    public static (string Content, List<AppliedFix> Fixes) Fix(string content)
    {
        var fixes = new List<AppliedFix>();
        if (string.IsNullOrEmpty(content)) return (content, fixes);

        var next = content;
        next = ApplyInventoryBlueprint(next, fixes);
        next = ApplyBlueprintNameRenames(next, fixes);
        next = ApplyPartAttrStripsAndMutationOnEquip(next, fixes);
        next = ApplyMutationTags(next, fixes);
        next = ApplyRoleElements(next, fixes);
        next = ApplyAnimatedMaterialDuplicates(next, fixes);
        next = ApplyDuplicateNamedChildren(next, fixes);
        return (next, fixes);
    }

    static string ApplyInventoryBlueprint(string content, List<AppliedFix> fixes)
    {
        if (content.IndexOf("inventoryobject", StringComparison.OrdinalIgnoreCase) < 0)
            return content;

        var count = 0;
        var next = InventoryObjectTagRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            if (BlueprintAttrRx.IsMatch(attrs)) return m.Value;

            var nameMatch = NameAttrRx.Match(attrs);
            if (!nameMatch.Success) return m.Value;

            var newAttrs = NameAttrRx.Replace(attrs, "Blueprint=${q}${val}${q}", 1);
            count++;
            return $"<{m.Groups["tag"].Value}{newAttrs}>";
        });

        if (count > 0)
            fixes.Add(new AppliedFix { RuleName = InventoryBlueprintRuleName, Count = count });
        return next;
    }

    static string ApplyBlueprintNameRenames(string content, List<AppliedFix> fixes)
    {
        if (content.IndexOf("<object", StringComparison.OrdinalIgnoreCase) < 0)
            return content;

        var count = 0;
        var next = ObjectTagRx.Replace(content, m =>
        {
            var attrs = m.Groups["attrs"].Value;
            var orig = attrs;

            attrs = RewriteNamedAttr(attrs, NameAttrRx, BlueprintNameRenames, ref count);
            attrs = RewriteNamedAttr(attrs, InheritsAttrRx, BlueprintNameRenames, ref count);

            if (attrs == orig) return m.Value;
            return RebuildOpenTag(m.Groups["tag"].Value, attrs, IsSelfClose(m));
        });

        if (count > 0)
            fixes.Add(new AppliedFix { RuleName = BlueprintNameRenameRuleName, Count = count });
        return next;
    }

    static string ApplyPartAttrStripsAndMutationOnEquip(string content, List<AppliedFix> fixes)
    {
        var wire = 0;
        var phase = 0;
        var altDn = 0;
        var className = 0;
        var variant = 0;
        var mutRename = 0;
        var nameTrim = 0;
        var obsoleteAttr = 0;
        var secondaryStat = 0;
        var elemental = 0;
        var commerceTypo = 0;
        var sb = new StringBuilder(content.Length + 64);
        var last = 0;
        var any = false;

        foreach (Match m in PartTagRx.Matches(content))
        {
            var attrs = m.Groups["attrs"].Value;
            var nameMatch = NameAttrRx.Match(attrs);
            if (!nameMatch.Success) continue;

            var partName = nameMatch.Groups["val"].Value;
            var trimmedPartName = partName.Trim();
            var changed = false;
            string? insertAfter = null;

            if (trimmedPartName != partName)
            {
                attrs = ReplaceAttrValue(attrs, NameAttrRx, nameMatch.Groups["q"].Value, trimmedPartName);
                nameTrim++;
                partName = trimmedPartName;
                changed = true;
            }

            if (partName.Equals("Comwmerce", StringComparison.OrdinalIgnoreCase))
            {
                attrs = ReplaceAttrValue(attrs, NameAttrRx, nameMatch.Groups["q"].Value, "Commerce");
                commerceTypo++;
                partName = "Commerce";
                changed = true;
            }

            if (partName.Equals("Wire", StringComparison.OrdinalIgnoreCase) &&
                WireMaterialAttrRx.IsMatch(attrs))
            {
                attrs = WireMaterialAttrRx.Replace(attrs, "");
                wire++;
                changed = true;
            }

            if (partName.Equals("Projectile", StringComparison.OrdinalIgnoreCase) &&
                RequiresPhaseMatchAttrRx.IsMatch(attrs))
            {
                attrs = RequiresPhaseMatchAttrRx.Replace(attrs, "");
                phase++;
                changed = true;
            }

            if (partName.Equals("Examiner", StringComparison.OrdinalIgnoreCase) &&
                AlternateDisplayNameAttrRx.IsMatch(attrs))
            {
                attrs = AlternateDisplayNameAttrRx.Replace(attrs, "");
                altDn++;
                changed = true;
            }

            if (partName.Equals("MutationOnEquip", StringComparison.OrdinalIgnoreCase))
            {
                var classMatch = ClassNameAttrRx.Match(attrs);
                if (classMatch.Success)
                {
                    var classVal = classMatch.Groups["val"].Value.Trim();
                    if (!MutationAttrRx.IsMatch(attrs))
                    {
                        var q = classMatch.Groups["q"].Value;
                        attrs = ClassNameAttrRx.Replace(attrs, $" Mutation={q}{classVal}{q}", 1);
                        className++;
                        changed = true;
                    }
                    else
                    {
                        attrs = ClassNameAttrRx.Replace(attrs, "", 1);
                        className++;
                        changed = true;
                    }
                }

                if (VariantAttrRx.IsMatch(attrs))
                {
                    attrs = VariantAttrRx.Replace(attrs, "");
                    variant++;
                    changed = true;
                }
            }

            // Mutation="…" on any part (MutationOnEquip / similar)
            var beforeMut = attrs;
            attrs = RewriteNamedAttr(attrs, MutationAttrRx, MutationNameRenames, ref mutRename);
            if (attrs != beforeMut) changed = true;

            if (partName.Equals("MeleeWeapon", StringComparison.OrdinalIgnoreCase))
            {
                // RenderString never belonged on MeleeWeapon
                if (StripAttr(ref attrs, "RenderString"))
                {
                    obsoleteAttr++;
                    changed = true;
                }

                var sec = SecondaryStatAttrRx.Match(attrs);
                if (sec.Success)
                {
                    var secVal = sec.Groups["val"].Value;
                    attrs = SecondaryStatAttrRx.Replace(attrs, "", 1);
                    if (!StatAttrRx.IsMatch(attrs))
                    {
                        var q = sec.Groups["q"].Value;
                        attrs += $" Stat={q}{secVal}{q}";
                    }
                    secondaryStat++;
                    changed = true;
                }

                var dmg = ElementalDamageAttrRx.Match(attrs);
                var elem = ElementAttrRx.Match(attrs);
                if (dmg.Success || elem.Success)
                {
                    var damage = dmg.Success ? dmg.Groups["val"].Value : "";
                    var attributes = elem.Success ? elem.Groups["val"].Value : "";
                    if (dmg.Success) attrs = ElementalDamageAttrRx.Replace(attrs, "", 1);
                    if (elem.Success) attrs = ElementAttrRx.Replace(attrs, "", 1);
                    var edAttrs = "";
                    if (!string.IsNullOrEmpty(damage))
                        edAttrs += $" Damage=\"{EscapeXmlAttr(damage)}\"";
                    if (!string.IsNullOrEmpty(attributes))
                        edAttrs += $" Attributes=\"{EscapeXmlAttr(attributes)}\"";
                    insertAfter = $"\n    <part Name=\"ElementalDamage\"{edAttrs} />";
                    elemental++;
                    changed = true;
                }
            }

            if (partName.Equals("Corpse", StringComparison.OrdinalIgnoreCase))
            {
                if (StripAttr(ref attrs, "BodyDrop") | StripAttr(ref attrs, "InventoryDrop"))
                {
                    obsoleteAttr++;
                    changed = true;
                }
            }

            if (partName.Equals("Brain", StringComparison.OrdinalIgnoreCase) &&
                StripAttr(ref attrs, "IgnoreCombat"))
            {
                obsoleteAttr++;
                changed = true;
            }

            if (partName.Equals("Physics", StringComparison.OrdinalIgnoreCase) &&
                StripAttr(ref attrs, "Occluding"))
            {
                obsoleteAttr++;
                changed = true;
            }

            // Chance lives on acegiak_SeedDropper, not acegiak_Seed
            if (partName.Equals("acegiak_Seed", StringComparison.OrdinalIgnoreCase) &&
                StripAttr(ref attrs, "Chance"))
            {
                obsoleteAttr++;
                changed = true;
            }

            if (!changed) continue;

            any = true;
            sb.Append(content, last, m.Index - last);
            sb.Append(RebuildOpenTag(m.Groups["tag"].Value, attrs, IsSelfClose(m)));
            if (insertAfter != null)
                sb.Append(insertAfter);
            last = m.Index + m.Length;
        }

        if (any)
        {
            sb.Append(content, last, content.Length - last);
            content = sb.ToString();
        }

        if (wire > 0)
            fixes.Add(new AppliedFix { RuleName = WireMaterialRuleName, Count = wire });
        if (phase > 0)
            fixes.Add(new AppliedFix { RuleName = ProjectilePhaseMatchRuleName, Count = phase });
        if (altDn > 0)
            fixes.Add(new AppliedFix { RuleName = ExaminerAlternateDisplayNameRuleName, Count = altDn });
        if (className > 0)
            fixes.Add(new AppliedFix { RuleName = MutationOnEquipClassNameRuleName, Count = className });
        if (variant > 0)
            fixes.Add(new AppliedFix { RuleName = MutationOnEquipVariantRuleName, Count = variant });
        if (mutRename > 0)
            fixes.Add(new AppliedFix { RuleName = MutationNameRenameRuleName, Count = mutRename });
        if (nameTrim > 0)
            fixes.Add(new AppliedFix { RuleName = NameTrimRuleName, Count = nameTrim });
        if (obsoleteAttr > 0)
            fixes.Add(new AppliedFix { RuleName = ObsoletePartAttrRuleName, Count = obsoleteAttr });
        if (secondaryStat > 0)
            fixes.Add(new AppliedFix { RuleName = MeleeWeaponSecondaryStatRuleName, Count = secondaryStat });
        if (elemental > 0)
            fixes.Add(new AppliedFix { RuleName = MeleeWeaponElementalRuleName, Count = elemental });
        if (commerceTypo > 0)
            fixes.Add(new AppliedFix { RuleName = CommerceTypoRuleName, Count = commerceTypo });

        return content;
    }

    static string ApplyMutationTags(string content, List<AppliedFix> fixes)
    {
        if (content.IndexOf("<mutation", StringComparison.OrdinalIgnoreCase) < 0)
            return content;

        var mutRename = 0;
        var nameTrim = 0;
        var valueDelete = 0;
        var sb = new StringBuilder(content.Length);
        var last = 0;
        var any = false;

        foreach (Match m in MutationTagRx.Matches(content))
        {
            var attrs = m.Groups["attrs"].Value;
            var nameMatch = NameAttrRx.Match(attrs);
            if (!nameMatch.Success) continue;

            var name = nameMatch.Groups["val"].Value;
            var trimmed = name.Trim();
            var q = nameMatch.Groups["q"].Value;
            var changed = false;

            if (trimmed != name)
            {
                attrs = ReplaceAttrValue(attrs, NameAttrRx, q, trimmed);
                nameTrim++;
                name = trimmed;
                changed = true;
            }

            if (MutationNameRenames.TryGetValue(name, out var renamed))
            {
                attrs = ReplaceAttrValue(attrs, NameAttrRx, q, renamed);
                mutRename++;
                name = renamed;
                changed = true;
            }

            if (ValueDeleteAttrRx.IsMatch(attrs))
            {
                // <mutation Name="X" Value="*delete" /> → <removemutation Name="X" />
                any = true;
                valueDelete++;
                sb.Append(content, last, m.Index - last);
                sb.Append("<removemutation Name=").Append(q).Append(name).Append(q).Append(" />");
                last = m.Index + m.Length;
                continue;
            }

            if (!changed) continue;

            any = true;
            sb.Append(content, last, m.Index - last);
            sb.Append(RebuildOpenTag(m.Groups["tag"].Value, attrs, IsSelfClose(m)));
            last = m.Index + m.Length;
        }

        if (any)
        {
            sb.Append(content, last, content.Length - last);
            content = sb.ToString();
        }

        if (mutRename > 0)
        {
            var existing = fixes.Find(f => f.RuleName == MutationNameRenameRuleName);
            if (existing != null) existing.Count += mutRename;
            else fixes.Add(new AppliedFix { RuleName = MutationNameRenameRuleName, Count = mutRename });
        }

        if (nameTrim > 0)
        {
            var existing = fixes.Find(f => f.RuleName == NameTrimRuleName);
            if (existing != null) existing.Count += nameTrim;
            else fixes.Add(new AppliedFix { RuleName = NameTrimRuleName, Count = nameTrim });
        }

        if (valueDelete > 0)
            fixes.Add(new AppliedFix { RuleName = MutationValueDeleteRuleName, Count = valueDelete });

        return content;
    }

    static string ApplyRoleElements(string content, List<AppliedFix> fixes)
    {
        if (content.IndexOf("<role", StringComparison.OrdinalIgnoreCase) < 0)
            return content;

        // Per-object: drop <role> when a Role tag already exists; else convert to tag.
        var count = 0;
        var sb = new StringBuilder(content.Length);
        var last = 0;
        var objectDepth = 0;
        var objectHasRoleTag = false;

        var scanRx = new Regex(
            @"<(?<close>/)?object\b[^>]*>|<(?<role>role)\b(?<attrs>[^>]*)\s*(?:/>|>\s*</role>)|<(?<tag>tag)\b(?<tagAttrs>[^>]*)>",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        foreach (Match m in scanRx.Matches(content))
        {
            if (m.Groups["role"].Success)
            {
                if (objectDepth <= 0) continue;
                var attrs = m.Groups["attrs"].Value;
                var nameMatch = NameAttrRx.Match(attrs);
                if (!nameMatch.Success) continue;
                var role = nameMatch.Groups["val"].Value.Trim();
                sb.Append(content, last, m.Index - last);
                if (!objectHasRoleTag && !string.IsNullOrEmpty(role))
                    sb.Append($"<tag Name=\"Role\" Value=\"{EscapeXmlAttr(role)}\" />");
                // else drop — Role tag already present
                last = m.Index + m.Length;
                count++;
                continue;
            }

            if (m.Groups["tag"].Success)
            {
                if (objectDepth > 0)
                {
                    var nameMatch = NameAttrRx.Match(m.Groups["tagAttrs"].Value);
                    if (nameMatch.Success &&
                        nameMatch.Groups["val"].Value.Trim().Equals("Role", StringComparison.OrdinalIgnoreCase))
                        objectHasRoleTag = true;
                }
                continue;
            }

            if (m.Groups["close"].Success)
            {
                objectDepth = Math.Max(0, objectDepth - 1);
            }
            else
            {
                objectDepth++;
                if (objectDepth == 1)
                    objectHasRoleTag = false;
            }
        }

        if (count == 0) return content;
        sb.Append(content, last, content.Length - last);
        fixes.Add(new AppliedFix { RuleName = RoleElementRuleName, Count = count });
        return sb.ToString();
    }

    static string ApplyAnimatedMaterialDuplicates(string content, List<AppliedFix> fixes)
    {
        if (content.IndexOf("AnimatedMaterialGeneric", StringComparison.OrdinalIgnoreCase) < 0)
            return content;

        var count = 0;
        var objectDepth = 0;
        var genericCount = 0;
        var hasAlternate = false;
        var sb = new StringBuilder(content.Length);
        var last = 0;

        foreach (Match m in ObjectOpenCloseRx.Matches(content))
        {
            if (m.Groups["tag"].Success)
            {
                // part tag — only rewrite inside an object
                if (objectDepth <= 0) continue;

                var attrs = m.Groups["partAttrs"].Value;
                var nameMatch = NameAttrRx.Match(attrs);
                if (!nameMatch.Success) continue;

                var partName = nameMatch.Groups["val"].Value.Trim();
                if (partName.Equals("AnimatedMaterialGenericAlternate", StringComparison.OrdinalIgnoreCase))
                {
                    hasAlternate = true;
                    continue;
                }

                if (!partName.Equals("AnimatedMaterialGeneric", StringComparison.OrdinalIgnoreCase))
                    continue;

                genericCount++;
                if (genericCount < 2 || hasAlternate) continue;

                // Rename 2nd+ Generic to Alternate when no Alternate exists yet.
                sb.Append(content, last, m.Index - last);
                var q = nameMatch.Groups["q"].Value;
                var newAttrs = ReplaceAttrValue(attrs, NameAttrRx, q, "AnimatedMaterialGenericAlternate");
                sb.Append("<part").Append(newAttrs).Append('>');
                last = m.Index + m.Length;
                count++;
                hasAlternate = true;
                continue;
            }

            // object open/close
            if (m.Groups["close"].Success)
            {
                objectDepth = Math.Max(0, objectDepth - 1);
            }
            else
            {
                objectDepth++;
                if (objectDepth == 1)
                {
                    genericCount = 0;
                    hasAlternate = false;
                }
            }
        }

        if (count == 0) return content;

        sb.Append(content, last, content.Length - last);
        fixes.Add(new AppliedFix { RuleName = AnimatedMaterialAlternateRuleName, Count = count });
        return sb.ToString();
    }

    /// <summary>
    /// Within each object, duplicate named part/tag/mutation/… children error then
    /// merge (later attrs win). Rewrite XML to a single node with merged attrs.
    /// CyberneticsHasImplants concatenates Implants= values.
    /// </summary>
    static string ApplyDuplicateNamedChildren(string content, List<AppliedFix> fixes)
    {
        var count = 0;
        var objectDepth = 0;
        Dictionary<string, (int Index, int Length, string Attrs, string Tag, bool SelfClose)>? first = null;
        var replacements = new List<(int Index, int Length, string Replacement)>();

        foreach (Match m in ObjectChildScanRx.Matches(content))
        {
            if (!m.Groups["tag"].Success)
            {
                if (m.Groups["close"].Success)
                {
                    if (objectDepth == 1)
                        first = null;
                    objectDepth = Math.Max(0, objectDepth - 1);
                }
                else
                {
                    objectDepth++;
                    if (objectDepth == 1)
                        first = new Dictionary<string, (int, int, string, string, bool)>(StringComparer.OrdinalIgnoreCase);
                }
                continue;
            }

            if (objectDepth <= 0 || first == null) continue;

            var tag = m.Groups["tag"].Value;
            var attrs = m.Groups["attrs"].Value;
            var selfClose = IsSelfClose(m);
            var nameMatch = NameAttrRx.Match(attrs);
            if (!nameMatch.Success) continue;

            var childName = nameMatch.Groups["val"].Value.Trim();
            // Skip AnimatedMaterialGeneric — handled by dedicated rule (Alternate rename)
            if (tag.Equals("part", StringComparison.OrdinalIgnoreCase) &&
                (childName.Equals("AnimatedMaterialGeneric", StringComparison.OrdinalIgnoreCase) ||
                 childName.Equals("AnimatedMaterialGenericAlternate", StringComparison.OrdinalIgnoreCase)))
                continue;

            var key = tag + "\0" + childName;
            if (!first.TryGetValue(key, out var prev))
            {
                first[key] = (m.Index, m.Length, attrs, tag, selfClose);
                continue;
            }

            // Duplicate — merge into first, drop this node (matches loader merge-after-error)
            var merged = MergeAttrs(prev.Attrs, attrs, childName);
            // Prefer self-close if either occurrence was self-closing (typical for part/tag)
            var newFirst = RebuildOpenTag(prev.Tag, merged, prev.SelfClose || selfClose);

            replacements.RemoveAll(r => r.Index == prev.Index);
            replacements.Add((prev.Index, prev.Length, newFirst));
            first[key] = (prev.Index, prev.Length, merged, prev.Tag, prev.SelfClose || selfClose);
            replacements.Add((m.Index, m.Length, ""));
            count++;
        }

        if (count == 0) return content;

        replacements.Sort((a, b) => b.Index.CompareTo(a.Index));
        var result = content;
        foreach (var (index, length, replacement) in replacements)
            result = result.Substring(0, index) + replacement + result.Substring(index + length);

        result = Regex.Replace(result, @"[ \t]*\r?\n[ \t]*\r?\n[ \t]*\r?\n", "\n\n");

        fixes.Add(new AppliedFix { RuleName = DuplicateNamedChildRuleName, Count = count });
        return result;
    }

    static string MergeAttrs(string firstAttrs, string secondAttrs, string partName)
    {
        var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var order = new List<string>();

        void Ingest(string attrs, bool isSecond)
        {
            foreach (Match a in AttrRx.Matches(attrs))
            {
                var n = a.Groups["name"].Value;
                var v = a.Groups["val"].Value;
                var q = a.Groups["q"].Value;
                if (isSecond &&
                    partName.Equals("CyberneticsHasImplants", StringComparison.OrdinalIgnoreCase) &&
                    n.Equals("Implants", StringComparison.OrdinalIgnoreCase) &&
                    map.TryGetValue(n, out var existing) &&
                    !string.IsNullOrEmpty(existing) &&
                    !string.IsNullOrEmpty(v))
                {
                    // Join implant lists
                    var parts = (existing + "," + v).Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                    var joined = new List<string>();
                    foreach (var p in parts)
                    {
                        if (seen.Add(p)) joined.Add(p);
                    }
                    map[n] = string.Join(",", joined);
                    continue;
                }

                if (!map.ContainsKey(n))
                    order.Add(n);
                map[n] = v;
                // preserve quote style loosely — always double for rebuild
                _ = q;
            }
        }

        Ingest(firstAttrs, false);
        Ingest(secondAttrs, true);

        var sb = new StringBuilder();
        foreach (var n in order)
        {
            sb.Append(' ').Append(n).Append("=\"").Append(EscapeXmlAttr(map[n])).Append('"');
        }
        return sb.ToString();
    }

    static bool StripAttr(ref string attrs, string attrName)
    {
        var rx = new Regex(
            $@"\s+{Regex.Escape(attrName)}\s*=\s*(?<q>[""'])[^'""]*\k<q>",
            RegexOptions.IgnoreCase);
        if (!rx.IsMatch(attrs)) return false;
        attrs = rx.Replace(attrs, "", 1);
        return true;
    }

    static string EscapeXmlAttr(string value) =>
        value.Replace("&", "&amp;").Replace("\"", "&quot;");

    static string RewriteNamedAttr(
        string attrs,
        Regex attrRx,
        IReadOnlyDictionary<string, string> map,
        ref int renameCount)
    {
        var m = attrRx.Match(attrs);
        if (!m.Success) return attrs;
        var val = m.Groups["val"].Value.Trim();
        if (!map.TryGetValue(val, out var renamed)) return attrs;
        renameCount++;
        return ReplaceAttrValue(attrs, attrRx, m.Groups["q"].Value, renamed);
    }

    static string ReplaceAttrValue(string attrs, Regex attrRx, string quote, string newVal) =>
        attrRx.Replace(attrs, m =>
        {
            // Preserve original attribute name casing from the match.
            var raw = m.Value;
            var eq = raw.IndexOf('=');
            if (eq < 0) return $"{m.Groups[0].Value.Split('=')[0]}={quote}{newVal}{quote}";
            var leadingWs = "";
            var i = 0;
            while (i < raw.Length && char.IsWhiteSpace(raw[i])) i++;
            leadingWs = raw.Substring(0, i);
            var name = raw.Substring(i, eq - i).Trim();
            return $"{leadingWs}{name}={quote}{newVal}{quote}";
        }, 1);
}
