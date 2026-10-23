# Soulash 2 skill effect catalog

Generated 2026-10-22T10:12:53.679506+00:00

Sources: official `data/docs/index.html`, vanilla `core_2`, Steam Workshop skill mods, `Soulash 2.exe` strings, `catalog/patch_overlay.json`.
Hydromancy is excluded. EXE-only ids are `unconfirmed`. Patch overlay ids are `patch` (dropdown-valid).

## Enums

- damage_type: physical, fire, frost, electricity, death, nature, acid, holy, none, true
- target: actor, ally_command, any, aoe_self, aoe_target, aoe_tile, back_and_forth, cone, corpse, health, horizontal_line, line, line_cone, line_health, non_actor, random, self, tile
- amplifier type: offensive, defensive, utility
- exp_source: location_discovery, location_details_discovery, resource_discovery, attack, parry, ability, craft, upgrade_item, drag, throw, climb, salvage, settle, jump_down, walk, carve, production, companion_build, companion_kill, order, pet, pickpocket, rob, take_control, track, trade
- milestone reward: ability (174), action (12), amplifier (118), control_action (3), passive (212), production_action (9), recipe (946)

## Effects

| kind | id | schema | count | confidence | description |
| --- | --- | --- | ---: | --- | --- |
| ability | `ability_can_crit` | int | 5 | workshop | ability can critically hit. |
| ability | `ability_damage_multiplier` | float | 1 | vanilla |  |
| ability | `aoe_break` | int | 46 | vanilla | breaks AoE shape on collidables. |
| ability | `aoe_range` | int | 82 | vanilla | value will set the range for AOE of this ability. |
| ability | `aoe_shape` | int | 80 | vanilla | choose the shape for AOE in Value. |
| ability | `attack_speed` | float | 5 | vanilla | buff stat |
| ability | `bleed` | int | 9 | vanilla | ability will cause bleed status. |
| ability | `bleed_per_damage` | null | 2 | workshop | how much bleed will this ability deal per damage. |
| ability | `break_armor` | int | 3 | workshop |  |
| ability | `burn` | int | 8 | vanilla | will apply burning effect on enemy. |
| ability | `burn_stamina` | int | 3 | vanilla | removes stamina on target. |
| ability | `burning_light` | int | 1 | vanilla |  |
| ability | `cage` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `cast_heals` | int | 1 | workshop |  |
| ability | `chain` | int | 4 | vanilla | ability will chain for more than one enemy. |
| ability | `challenge` | null | 2 | vanilla | forces enemy to attack you. |
| ability | `charge` | int | 5 | vanilla | Charges at a target. |
| ability | `clear_cooldowns` | null | 2 | vanilla | clears all cooldowns except this ability. |
| ability | `construct_item_cost` | float | 7 | vanilla | cost of using construc effect |
| ability | `consume_tick_damage` | null | 2 | vanilla | if the target has an effect it will be removed. |
| ability | `corrupt` | null | 1 | docs_unused | takes control of the enemy for duration. |
| ability | `critical_hit` | null | 1 | docs_unused | buff stat |
| ability | `critical_hit_chance` | float | 2 | workshop |  |
| ability | `damage` | int_pair | 195 | vanilla |  |
| ability | `damage_as_life` | float | 3 | vanilla | ability will steal HP from enemy. Value defines percent damage dealt. |
| ability | `damage_bonus` | int | 8 | vanilla | extra damage buff. |
| ability | `damage_bonus_percent` | float | 6 | vanilla | self-explanatory buff. |
| ability | `damage_on_missing_health` | null | 1 | docs_unused | extra damage when missing health. |
| ability | `damage_on_missing_stamina` | null | 1 | docs_unused | extra damage when missing health. |
| ability | `damage_receive_bonus_percent` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `damage_reduce` | int | 5 | vanilla | self-explanatory buff. |
| ability | `damage_reduce_percent` | float | 5 | vanilla | self-explanatory buff. |
| ability | `damage_to_bloodlust` | float | 1 | vanilla |  |
| ability | `damage_type` | string | 217 | vanilla |  |
| ability | `damage_weapon` | float | 101 | vanilla | % damage of the weapon wielded will apply to ability damage. |
| ability | `deflection` | float | 3 | vanilla | deflects arrows back at the attacker. |
| ability | `dexterity` | int | 3 | vanilla | buff/debuff stat |
| ability | `disadvantage` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `disarm` | int | 3 | vanilla | ability will disarm enemy. |
| ability | `dmg_without_companions` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `endurance` | int | 5 | vanilla | buff/debuff stat |
| ability | `fear` | int | 6 | vanilla | ability will cause fear effect. |
| ability | `fertility` | int | 1 | vanilla |  |
| ability | `frostbite` | int | 2 | vanilla |  |
| ability | `full_vision` | null | 2 | vanilla | 360 vision |
| ability | `heal` | int_pair | 7 | vanilla | this will cause ability to add health. |
| ability | `health_for_stamina` | null | 1 | docs_unused | % of stamina cost is returned as health. |
| ability | `hide` | null | 2 | vanilla | hides the character from sight. |
| ability | `hide_health` | int | 3 | vanilla | ability will hide health bar. |
| ability | `hit_chance` | int | 7 | vanilla | Reduces hit chance of the opponent. |
| ability | `hit_self` | null | 2 | vanilla | causes enemy to hit themselves. |
| ability | `ignore_party` | bool | 1 | workshop |  |
| ability | `immobilize` | int | 24 | vanilla | ability will immobilize enemy. |
| ability | `increase_target_cooldown` | null | 1 | docs_unused | increases ability cooldown of target. Value defines turns. |
| ability | `intelligence` | int | 5 | vanilla | buff/debuff stat |
| ability | `knockback` | int | 19 | vanilla | ability will knock back an enemy. Value defines range. |
| ability | `knockback_damage_percent` | null | 2 | vanilla | defines how much damage will knockback do. |
| ability | `light_source` | null | 2 | vanilla | ability will give light. Value is numer of tiles that will be illuminated. |
| ability | `lunge` | int | 6 | vanilla | Lunge at position. |
| ability | `magic_deflection` | null | 2 | vanilla | deflects abilities back at caster. |
| ability | `magic_power` | float | 1 | vanilla |  |
| ability | `magic_power_damage` | float | 63 | vanilla | bonus damage from Magic Power property |
| ability | `magic_power_per_entity` | null | 1 | docs_unused | additional magic power for every entity in range. |
| ability | `magic_to_weapon_damage` | null | 1 | docs_unused | replaces weapon damage with magic power. |
| ability | `move_to_side` | int | 1 | vanilla |  |
| ability | `movement_speed` | float | 9 | vanilla | ability will buff or debuff movement speed. |
| ability | `neutralize` | string_list | 5 | vanilla | ability will neutralize one status. Choose which from the list. |
| ability | `parry_chance` | int | 3 | vanilla | buff/debuff stat |
| ability | `pierce` | int | 12 | vanilla | the first target doesn't break the line, can be used to hit multiple targets in straight line. |
| ability | `poison_effect` | int | 10 | vanilla | poison effect. |
| ability | `power_up` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `pull_target` | int | 7 | vanilla | pulls target towards ability user. |
| ability | `regeneration` | float | 8 | vanilla | ability will regenerate HP of its user. |
| ability | `remove_on_next_ability` | int | 1 | vanilla |  |
| ability | `repeat_ability_second_weapon` | int | 4 | workshop | self-explanatory |
| ability | `reset_cooldown_on_kill` | int | 3 | vanilla | ability will reset its cooldown, if user kills an enemy with it. |
| ability | `resistance` | int | 18 | vanilla | ability will buff or debuff resistance. |
| ability | `resistance_percent` | null | 1 | docs_unused | buff / debuff resistance by percentage. |
| ability | `restrict_to_tag` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `revenge_counter` | null | 2 | vanilla | deal damage related to last 5 hits done on you. |
| ability | `rollback` | int | 4 | vanilla | ability will roll player back. Value defines range. |
| ability | `sight` | int | 8 | vanilla | buff/debuff stat |
| ability | `silence` | int | 6 | vanilla | ability will silence an enemy. |
| ability | `stacker_count` | int | 2 | vanilla |  |
| ability | `stacker_to_dot` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `stamina` | null | 2 | vanilla | regen stamina |
| ability | `stamina_regen` | null | 1 | patch | Increases stamina regeneration. Valid on abilities and stackers (patch). Not seen in vanilla ability JSON; do not confus |
| ability | `strength` | int | 4 | vanilla | buff/debuff stat |
| ability | `stun` | float | 23 | vanilla | ability will stun an enemy. |
| ability | `summon` | int | 1 | vanilla |  |
| ability | `summon_count` | int | 39 | vanilla | max summons to create in case of large AoE spell. |
| ability | `thorns` | int | 6 | vanilla | buff stat |
| ability | `trade_places` | int | 3 | vanilla | ability will exchange places of its user and enemy. |
| ability | `vulnerable` | null | 2 | vanilla | applies to target, bumps damage received. |
| ability | `willpower` | int | 5 | vanilla | buff/debuff stat |
| ability_key | `aura` | string | 2 | vanilla |  |
| ability_key | `construct` | null | 1 | docs_unused | ability will allow to construct an entity. Choose entity from the list. |
| ability_key | `magic_power_damage` | float | 1 | vanilla |  |
| ability_key | `sense` | null | 2 | vanilla | ability will help sense certain creatures nearby. Value will define which creature type. |
| ability_key | `stacker` | string | 3 | vanilla | ability will give target an effect on target. Choose effect from Value list. |
| ability_key | `summon` | string | 39 | vanilla | ability will summon one entity. Choose which one. |
| ability_key | `summon_on_move` | string | 4 | vanilla | Summons an entity in the tile you moved from. You can choose entity that will be summoned. |
| ability_key | `summon_weather` | string | 3 | vanilla | ability wil summon weather. Choose weather effect. |
| ability_key | `transform` | string | 1 | vanilla |  |
| amplifier | `ability_can_crit` | int | 3 | vanilla |  |
| amplifier | `always_hit` | bool | 1 | vanilla |  |
| amplifier | `aoe_range` | int | 1 | vanilla |  |
| amplifier | `bleed` | int | 1 | vanilla |  |
| amplifier | `bleed_per_damage` | float | 1 | vanilla |  |
| amplifier | `burn` | int | 1 | vanilla |  |
| amplifier | `burn_stamina` | int | 1 | vanilla |  |
| amplifier | `cast_heals` | int | 1 | vanilla |  |
| amplifier | `chain` | int | 3 | vanilla |  |
| amplifier | `consume_tick_damage` | string | 1 | vanilla |  |
| amplifier | `copy_to_party` | bool | 1 | vanilla |  |
| amplifier | `damage` | int_pair | 6 | vanilla |  |
| amplifier | `damage_as_life` | float | 1 | vanilla |  |
| amplifier | `damage_bonus_percent` | float | 6 | vanilla |  |
| amplifier | `damage_from_thorns` | float | 1 | vanilla |  |
| amplifier | `damage_on_missing_health` | float | 1 | vanilla |  |
| amplifier | `damage_on_missing_stamina` | float | 1 | vanilla |  |
| amplifier | `damage_per_stacks` | int | 1 | vanilla |  |
| amplifier | `damage_reduce` | int | 2 | vanilla |  |
| amplifier | `damage_type` | string | 11 | vanilla |  |
| amplifier | `damage_without_companions` | float | 1 | vanilla |  |
| amplifier | `distance_damage` | int | 1 | vanilla |  |
| amplifier | `dmg_on_cooldown` | int | 1 | vanilla |  |
| amplifier | `dmg_per_companion` | float | 1 | vanilla |  |
| amplifier | `effect_per_stack` | string | 4 | vanilla |  |
| amplifier | `endurance` | int | 1 | vanilla |  |
| amplifier | `fear` | int | 1 | vanilla |  |
| amplifier | `health_for_stamina` | float | 1 | vanilla |  |
| amplifier | `ignore_party` | bool | 1 | vanilla |  |
| amplifier | `immobilize` | int | 1 | workshop |  |
| amplifier | `increase_effect` | string | 2 | vanilla |  |
| amplifier | `increase_target_cooldown` | int | 1 | vanilla |  |
| amplifier | `intelligence` | int | 1 | workshop |  |
| amplifier | `knockback` | int | 1 | vanilla |  |
| amplifier | `knockback_damage_percent` | float | 1 | vanilla |  |
| amplifier | `magic_power_per_entity` | string | 2 | vanilla |  |
| amplifier | `magic_power_per_tag` | string | 1 | vanilla |  |
| amplifier | `magic_to_weapon_damage` | int | 1 | vanilla |  |
| amplifier | `movement_speed` | float | 3 | vanilla |  |
| amplifier | `parry_chance` | int | 3 | vanilla |  |
| amplifier | `pierce` | int | 1 | vanilla |  |
| amplifier | `poison_effect` | int | 2 | vanilla |  |
| amplifier | `reduce_random_cooldown` | int | 2 | vanilla |  |
| amplifier | `repeat_ability_second_weapon` | float | 1 | vanilla |  |
| amplifier | `resistance` | int | 2 | vanilla |  |
| amplifier | `resistance_percent` | float | 1 | vanilla |  |
| amplifier | `revenge_counter` | int | 1 | vanilla |  |
| amplifier | `rollback` | int | 1 | vanilla |  |
| amplifier | `skill_level_damage` | float | 1 | vanilla |  |
| amplifier | `stacker` | string | 2 | vanilla |  |
| amplifier | `stamina` | int | 1 | vanilla |  |
| amplifier | `strength` | int | 1 | vanilla |  |
| amplifier | `stun` | int | 2 | vanilla |  |
| amplifier | `summon` | string | 1 | vanilla |  |
| amplifier | `summon_count` | int | 1 | vanilla |  |
| amplifier | `thorns` | int | 2 | vanilla |  |
| amplifier | `turn_damage_to_stacks` | string | 1 | vanilla |  |
| amplifier | `vulnerable` | int | 2 | vanilla |  |
| amplifier | `weapon_damage_to_magic` | int | 7 | vanilla |  |
| amplifier | `willpower` | int | 1 | vanilla |  |
| amplifier_field | `cast_time` | float | 2 | vanilla | Amplifier top-level field applied to the socketed ability (cast_time). |
| amplifier_field | `cooldown` | int | 17 | vanilla | Amplifier top-level field applied to the socketed ability (cooldown). |
| amplifier_field | `cost_stamina` | int | 11 | vanilla | Amplifier top-level field applied to the socketed ability (cost_stamina). |
| amplifier_field | `duration` | int | 6 | vanilla | Amplifier top-level field applied to the socketed ability (duration). |
| amplifier_field | `range` | int | 2 | vanilla | Amplifier top-level field applied to the socketed ability (range). |
| amplifier_field | `range_melee` | int | 3 | vanilla | Amplifier top-level field applied to the socketed ability (range_melee). |
| amplifier_field | `secondary_value` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| amplifier_field | `third_value` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| milestone_field | `innate` | bool | 2 | vanilla | Innate milestones are skipped when checking skill level-up requirements. Grant on entities via skills.milestones (Entity |
| passive | `2h_dual_wield` | null | 1 | vanilla | In-game: You can wield 2-handed weapons in both hands. |
| passive | `ability_extend_duration` | string | 2 | vanilla | Extends duration of a buff/ability. value is ability id; secondary_value is duration modifier (1.0 = +100%). Vanilla Spr |
| passive | `all_roads_lead_here` | int | 1 | vanilla | In-game: Set buy orders, and caravans from other towns will attempt to deliver requested goods to this settlement. |
| passive | `analyze_speed` | int | 1 | vanilla | In-game: You can see character's movement speed in their tooltips. |
| passive | `analyze_weakness` | int | 1 | vanilla | In-game: You can see character's weakest resistance in their tootltips. |
| passive | `area_maps` | int | 1 | vanilla | In-game: When you enter a new region of z-level ::value, the region map for that level becomes fully discovered. |
| passive | `attack_on_parry` | float | 1 | vanilla |  |
| passive | `attack_speed` | float | 4 | vanilla | In-game: Speed up basic attacks by ::value. |
| passive | `aura_extra_aoe_range` | string | 1 | vanilla | In-game: When casting ::value the aura range is increased by +::secondary_value (This passive effect does not stack with |
| passive | `better_deals` | unknown | 0 | patch | Better sale prices for a specific item type. value is likely the bonus; secondary_value is item_type index from messages |
| passive | `block_counter` | int | 1 | vanilla |  |
| passive | `bloodlust` | null | 1 | vanilla | In-game: Replaces Hunger and Thirst with Bloodthirst, requiring consumption of blood for survival. |
| passive | `bonus_attack` | float | 1 | vanilla | Chance for an extra attack when attacking (not abilities). Docs: 0.1 = 10%. |
| passive | `bonus_crafting_unit` | float | 3 | vanilla | In-game: ::value% chance to craft 1 extra unit of stackable item of type ::secondary_value. |
| passive | `bonus_damage` | int | 1 | vanilla | In-game: Damage +::value (::secondary_value). |
| passive | `bonus_knockback_damage_percent` | float | 1 | vanilla | Increases damage dealt on knockback collisions. Vanilla Knock It Down uses 0.2. |
| passive | `bonus_one_handed_damage_percent` | int | 1 | vanilla | In-game: ::value% bonus damage with 1-handed weapons. |
| passive | `bonus_production_action` | string | 9 | vanilla | In-game: ::secondary_value% bonus production from action ::value. |
| passive | `bonus_production_chance_item_type` | string | 1 | vanilla | In-game: ::secondary_value% higher chance to produce items of type ::value when using a relevant action. |
| passive | `bonus_two_handed_damage_percent` | int | 1 | vanilla | In-game: ::value% bonus damage with 2-handed weapons. |
| passive | `bounty_reduce` | float | 1 | vanilla | In-game: Your bounties reduce by ::value% every day, minimum 1 gold. Doesn't apply to unforgivable crimes. |
| passive | `buy_plot` | int | 1 | vanilla | In-game: Buy a plot of land in a town you do not own and found a home for your family. |
| passive | `camp` | int | 1 | vanilla | In-game: Can set up ::value camp on the world map. |
| passive | `camp_unlimited` | int | 1 | vanilla | In-game: Can set up unlimited camps on the world map. |
| passive | `caravan_capacity` | int | 3 | vanilla | In-game: Caravans can carry +::value resources in each slot. |
| passive | `caravan_speed` | float | 1 | vanilla | In-game: Caravans from your cities travel ::value% quicker. |
| passive | `carry_capacity` | int | 2 | vanilla | In-game: Carry Capacity +::value. |
| passive | `companion` | int | 8 | vanilla | In-game: +::value Party Companion Slot. |
| passive | `craft_persona` | string | 3 | vanilla | City-worker companion craft. Third parameter is the number of resources (patch). Still a settlement trick — do not ship  |
| passive | `craft_save_resource_tier` | float | 4 | vanilla | In-game: ::value% chance to not consume a tier ::secondary_value resource when crafting. |
| passive | `critical_damage` | float | 2 | vanilla | In-game: +::value% critical damage. |
| passive | `critical_hit` | float | 4 | vanilla | In-game: Your attacks have an additional ::value% chance to critically hit. |
| passive | `critical_hit_from_dex` | float | 1 | vanilla | In-game: Every point of your Dexterity adds additional ::value% chance to critically hit. |
| passive | `damage_negation` | string | 2 | vanilla | In-game: When getting hit by ::value damage you have ::secondary_value% chance to negate the damage. |
| passive | `damage_reduce` | unknown | 0 | patch | Flat incoming damage reduction. Warlock Dark One's Own Luck / Greater Ward. value is an int (2, 3, 4). Not in vanilla pa |
| passive | `damage_reduction_missing_health` | float | 1 | vanilla | In-game: Reduces damage received by ::value% for each ::secondary_value% of missing health. |
| passive | `damage_to_effect` | string | 1 | vanilla |  |
| passive | `damage_type_reduction` | string | 8 | vanilla | In-game: You reduce any ::value damage done to you by ::secondary_value%. |
| passive | `darkvision` | int | 1 | vanilla | Ignore infravision daylight penalty to sight (same as Dread Mask). Docs example value 1. This is not infravision/sight a |
| passive | `death_under_effect_gain_health` | string | 1 | vanilla | In-game: When anyone in the region dies while having active ::value effect, you regain ::secondary_value health. |
| passive | `death_under_effect_gain_stamina` | string | 2 | vanilla | In-game: When anyone in the region dies while having active ::value effect, you regain ::secondary_value stamina. |
| passive | `disable_consumer` | null | 1 | vanilla |  |
| passive | `discover_all_tiers` | null | 1 | vanilla | In-game: While traveling you reveal locations of all difficulties, independently of your combat skills. |
| passive | `discover_poi_range` | int | 1 | vanilla | In-game: You discover special locations in range of ::value instead of 1. |
| passive | `dodge` | float | 4 | vanilla | In-game: You have ::value% chance to dodge basic attacks. |
| passive | `dot_on_crit` | string | 1 | vanilla | In-game: Your basic attacks can cause ::value Effect when you critically hit. |
| passive | `economic_migration` | int | 1 | vanilla | In-game: Set a gold budget to lure families from other towns to your settlement. |
| passive | `extra_backpack_slots` | int | 2 | vanilla | In-game: Gain additional ::value backpack slots. |
| passive | `extra_duration` | float | 1 | vanilla | In-game: Extend duration of buffs on self by ::value%. |
| passive | `extra_equip_slot` | string | 2 | vanilla | In-game: You gain additional equipment slot for ::value. |
| passive | `extra_loot` | float | 1 | vanilla | In-game: Acquire ::value% more loot from treasure chests found in discoverable locations. |
| passive | `fall_damage` | float | 1 | vanilla | In-game: You're immune to fall damage. |
| passive | `famine_display` | int | 1 | vanilla | In-game: Settlements with food shortage are marked with Famine icon on World Map. |
| passive | `festival` | int | 1 | vanilla | In-game: Unlocks throwing a festival in your settlements. Traveling traders visit and productivity is increased by 20% f |
| passive | `flank_protection` | int | 1 | vanilla | In-game: Reduce combat position disadvantage when hit by one level: from backstab to flanking, or from flanking to front |
| passive | `food_during_travel` | int | 1 | vanilla |  |
| passive | `food_sabotage` | int | 1 | vanilla | In-game: You're able to pay unoccupied settlement inhabitant to sabotage the food supplies. |
| passive | `fund_rebellion` | int | 1 | vanilla | In-game: Pay an unemployed citizen in an occupied town to start a rebellion. |
| passive | `heal_on_damage_type` | string | 1 | vanilla | Converts incoming damage of this type into healing. value is the damage type string; secondary_value is the heal ratio ( |
| passive | `heal_on_kill` | float | 1 | vanilla | In-game: Heal for ::value% of the health of the killed Actor. |
| passive | `health_bonus_percent` | float | 2 | vanilla | In-game: Max Health is increased by +::value%. Applies to base Health and Health gained from Endurance. |
| passive | `health_tick` | float | 2 | vanilla | In-game: Health Regeneration Time -::value%. |
| passive | `hide_identity` | int | 1 | vanilla | In-game: When you have a bounty on your head, military units in a settlement recognize you only when you're in the range |
| passive | `hit_bonus` | int | 2 | vanilla | In-game: Hit +::value%. |
| passive | `immunity` | string | 4 | vanilla | In-game: You are immune to knockback effects. |
| passive | `increase_effect_value` | string | 2 | vanilla | In-game: If the target has ::value, its effect is increased by ::secondary_value%. |
| passive | `infravision` | null | 1 | vanilla | In-game: You see at a full distance in the dark but half a distance during the day. |
| passive | `leader_stats` | float | 1 | vanilla | In-game: Party members benefit from ::value% of the leader's base statistics. |
| passive | `light_source` | int | 2 | vanilla | In-game: You always emit light in the range of ::value. |
| passive | `local_craftsman` | int | 1 | vanilla | In-game: Unlocks assigning a crafting-skill role to your home. |
| passive | `local_prices` | int | 1 | vanilla | In-game: Unlocks the economy screen for towns. |
| passive | `max_stamina` | int | 2 | vanilla | In-game: Max Stamina +::value. |
| passive | `mercenaries` | int | 1 | vanilla | In-game: Hire an adventuring party to raid a nearby location and bring the loot to your family stash. |
| passive | `middle_aged` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `move_speed` | float | 3 | vanilla | In-game: Movement Speed ::value. |
| passive | `movement_penalty` | float | 2 | vanilla | In-game: Movement penalty from rough terrain is reduced by ::value%. |
| passive | `movement_stamina` | float | 1 | vanilla | In-game: Stamina cost to move ::value%. |
| passive | `ocean_travel` | null | 1 | vanilla | In-game: You can pass the ocean as if you were sailing at any time. Your travel cannot end on the ocean. |
| passive | `on_attack_cast` | string | 2 | vanilla | In-game: On every melee or ranged attack, have a ::secondary_value% chance to cast ability ::value. |
| passive | `on_attack_stack` | string | 9 | vanilla | In-game: Basic melee and ranged attacks add 1 stack of ::value. |
| passive | `on_damage_type_stack` | string | 2 | vanilla |  |
| passive | `on_kill_create_item` | null | 1 | patch | Creates an item for the player when any being is killed. value is item id; secondary_value is chance (vanilla Taste for  |
| passive | `on_kill_persona_create_item` | string | 1 | vanilla | Creates an item when a persona (settlement NPC) is killed. Vanilla Taste for Souls: value core_2_Soul_Piece, secondary_v |
| passive | `on_max_stacks` | string | 1 | vanilla | In-game: When stacks of ::value reach max count, a electric explosion is triggered consuming all stacks, dealing damage  |
| passive | `parry` | int | 1 | vanilla | In-game: Parry +::value%. |
| passive | `party_move_speed` | int | 1 | vanilla | In-game: All party members share the player character's move speed. |
| passive | `plant_growth_time` | float | 1 | vanilla | In-game: Plants you seed grow ::value% faster. |
| passive | `points_of_interest` | null | 1 | vanilla | In-game: You can now ask innkeepers and hunters to discover Points of Interest close to their settlement. |
| passive | `poison_transfer_on_kill` | int | 1 | vanilla | In-game: When killing an enemy, any remaining poison stacks on it will transfer to other nearby enemy in range of ::valu |
| passive | `port_building` | int | 1 | vanilla | In-game: Allows building a Port in a town with a shore. |
| passive | `production_action` | int | 1 | vanilla | In-game: Unlocks action ::value. |
| passive | `production_action_speed` | string | 1 | vanilla | In-game: Speed of ::value action is reduced by ::secondary_value%. |
| passive | `purchase_prices` | float | 1 | vanilla | In-game: Reduce purchase price in settlements by ::value%. |
| passive | `random_spread` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `range` | int | 1 | vanilla | In-game: Ranged weapons used by you have +::value range. |
| passive | `regeneration` | float | 1 | vanilla | In-game: Health Regeneration changed by ::value. |
| passive | `regeneration_low_health` | float | 1 | vanilla | In-game: When under 50% health, the health regeneration is increased by +::value% |
| passive | `remigration` | int | 1 | vanilla | In-game: Unlocks banishing a family to a town of their people, or remigrating them to another town you control. |
| passive | `resource_discovery` | null | 1 | vanilla | In-game: You can now spend a few hours to discover a resource on the World Map. |
| passive | `resting_bonus` | float | 1 | vanilla | In-game: Fatigue Recovery during sleep is quicker by ::value%. |
| passive | `reveal_poi` | null | 1 | vanilla | In-game: The details of discovered locations during world travels are immediately revealed. |
| passive | `salvage_chance` | float | 1 | vanilla | In-game: Bonus ::value% chance to recover resources when salvaging items. |
| passive | `salvage_chance_tier` | float | 5 | vanilla | In-game: ::value% chance to recover a resource of tier ::secondary_value when salvaging. |
| passive | `see_souls` | int | 1 | vanilla | In-game: You can see Soul Deposits on world map, where a lot of civilized beings have died. |
| passive | `see_stamina` | null | 1 | vanilla | In-game: You can see the stamina of hurt beings under their health bar. |
| passive | `self_resistance` | null | 1 | unconfirmed | In-game: Your resistance to ::value damage is increased by ::secondary_value%. |
| passive | `sell_bonus` | float | 1 | vanilla |  |
| passive | `sell_bonus_crafted` | float | 4 | vanilla | In-game: Improve sell prices of crafted items by ::value%. |
| passive | `sell_bonus_resource` | float | 4 | vanilla | In-game: Improve sell prices of resources by ::value%. Also applies to resources used in crafted items. |
| passive | `sell_no_abundance_discount` | int | 1 | vanilla | In-game: You can sell as many items as you can to the same person without a discount related to abundance. |
| passive | `settlement_upgrade` | int | 2 | vanilla | In-game: Can upgrade ::value camp to a settlement. |
| passive | `settlement_upgrade_unlimited` | int | 1 | vanilla | In-game: Can upgrade unlimited camps to settlements. |
| passive | `settlement_wage_reduction` | float | 1 | vanilla | In-game: Pay for military units stationed in your settlements reduced by ::value%. |
| passive | `settlement_worker_production` | int | 1 | vanilla | In-game: Workers in your towns produce +::value resource per day. |
| passive | `sight` | int | 1 | vanilla | In-game: Base Sight +::value. |
| passive | `sight_behind` | float | 1 | vanilla | In-game: You can see behind you up to ::value% of your normal range. |
| passive | `spread_entity` | string | 1 | vanilla | In-game: Any ::value entity in the range of 10 tiles has a ::secondary_value% chance to duplicate into an adjacent tile. |
| passive | `stamina_on_stack_consume` | string | 1 | vanilla | In-game: When stacks of ::value are consumed on max stacks or death, recover stamina equal to number of stacks. |
| passive | `stamina_percent_on_kill` | float | 1 | vanilla | Restore this fraction of max stamina on kill. Docs: 0.1 = 10%. |
| passive | `statistic_percent` | string | 81 | vanilla | In-game: ::value increased by ::secondary_value%. |
| passive | `stun_on_hit` | float | 1 | vanilla | In-game: Your basic attacks has a ::value% chance to inflict stun. |
| passive | `target_resistance` | string | 4 | vanilla | In-game: Your target resistance to ::value damage is reduced by ::secondary_value%. |
| passive | `terraformer` | int | 1 | vanilla | In-game: Change up to five natural resources on a claimed town tile to other resources that can appear in that biome. |
| passive | `thirst_on_effect` | string | 1 | vanilla | In-game: Reduce thirst by ::secondary_value per turn while under effect of ::value. |
| passive | `thorns` | int | 1 | vanilla | In-game: Thorns +::value. |
| passive | `thorns_crit` | int | 1 | vanilla | In-game: Thorns can critically hit. |
| passive | `thorns_for_missing_health` | float | 1 | vanilla | In-game: Gain +1 Thorns for every ::value% of missing health. |
| passive | `thorns_ranged` | float | 1 | vanilla | In-game: ::value% of thorns apply when striken by a basic ranged attack. |
| passive | `tool_type` | int | 4 | vanilla | In-game: You gain the ::value tool with quality ::secondary_value. |
| passive | `town_buyout` | int | 1 | vanilla | In-game: Pay gold to assimilate a town into your state without military conquest. |
| passive | `trade_embargo` | int | 1 | vanilla | In-game: Block caravans from chosen states so they cannot trade with towns of your state. |
| passive | `training_cost` | float | 1 | vanilla | In-game: Potential training gold cost is multiplied by ::value. |
| passive | `trigger_ability_on_cast` | string | 1 | vanilla | In-game: When casting ::value you have ::third_value% chance to also cast ::secondary_value. |
| passive | `uncover_entity_with_tag` | null | 1 | unconfirmed | In-game: When entering local map, your supernatural senses can find positions of entities of type '::value'. |
| passive | `uncover_resources_of_type` | int | 1 | vanilla | In-game: While traveling the world map, you can sense ::value type of resources in the region. |
| passive | `unique_companion` | int | 1 | vanilla | In-game: +::value Party Companion Slot. (This passive effect does not stack with others of the same type) |
| passive | `working_class` | int | 1 | vanilla | In-game: Unlocks assigning an extraction role to your home. |
| passive_field | `apply_mode` | string | 7 | vanilla | Replaces only_party. party_only = bonuses only on companions. solo_only = only with no companions. Omit for everyone. |
| passive_field | `party_only` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive_field | `restrict_shield` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive_field | `restrict_tags` | string_list | 2 | vanilla | Passive top-level field (restrict_tags). apply_mode replaces only_party. |
| passive_field | `restrict_tags_enemy` | bool | 1 | vanilla | Passive top-level field (restrict_tags_enemy). apply_mode replaces only_party. |
| passive_field | `restrict_weapon_type` | string | 16 | vanilla | Passive top-level field (restrict_weapon_type). apply_mode replaces only_party. |
| passive_field | `solo_only` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| skill_field | `combat_skill` | bool | 32 | vanilla | skills.json flag: true for weapon/magic combat skills (planner + character creation grouping). |
| skill_field | `difficulty` | int | 30 | vanilla | Optional skills.json difficulty shown on character creation (core_2 uses 0-2). |
| skill_field | `start_level` | int | 17 | vanilla | Optional skills.json level the skill starts at (core_2 crafting skills and Economy use 1; default 10). Older SkillCreato |
| skill_field | `weapon_type` | int | 15 | vanilla | skills.json weapon skill link (core_2 weapon skills use 0-6). |
| stacker | `attack_speed` | float | 3 | vanilla |  |
| stacker | `bonus_damage` | unknown | 0 | patch | Per-stack bonus damage. Patch: Bonus Damage now works in stackers. |
| stacker | `bonus_damage_percent` | unknown | 0 | patch | Per-stack bonus damage percent. Patch: Bonus Damage Percent now works in stackers. |
| stacker | `critical_hit_chance` | float | 2 | vanilla |  |
| stacker | `damage_bonus` | unknown | 0 | patch | Per-stack bonus damage (ability key name damage_bonus). Patch: works in stackers. |
| stacker | `damage_bonus_percent` | float | 3 | vanilla | Per-stack bonus damage percent (ability key name damage_bonus_percent). |
| stacker | `magic_power` | float | 1 | workshop |  |
| stacker | `movement_speed` | float | 2 | vanilla |  |
| stacker | `stamina_regen` | unknown | 0 | patch | Per-stack stamina regeneration bonus. |
| stacker | `willpower` | int | 1 | vanilla |  |
| stacker_field | `apply_caster` | bool | 10 | vanilla | ability_stackers.json field (apply_caster). |
| stacker_field | `duration` | int | 9 | vanilla | ability_stackers.json field (duration). |
| stacker_field | `max_stacks` | int | 10 | vanilla | ability_stackers.json field (max_stacks). |
| stacker_field | `max_stacks_cast_unlock` | bool | 2 | vanilla | ability_stackers.json field (max_stacks_cast_unlock). |
| stacker_field | `on_max_stacks_cast` | string | 2 | vanilla | ability_stackers.json field (on_max_stacks_cast). |
