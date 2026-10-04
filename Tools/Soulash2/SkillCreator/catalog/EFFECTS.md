# Soulash 2 skill effect catalog

Generated 2026-08-16T10:40:59.094394+00:00

Sources: official `data/docs/index.html`, vanilla `core_2`, Steam Workshop skill mods, `Soulash 2.exe` strings, `catalog/patch_overlay.json`.
Hydromancy is excluded. EXE-only ids are `unconfirmed`. Patch overlay ids are `patch` (dropdown-valid).

## Enums

- damage_type: physical, fire, frost, electricity, death, nature, acid, holy, none, true
- target: actor, ally_command, any, aoe_self, aoe_target, aoe_tile, back_and_forth, cone, corpse, health, horizontal_line, line, line_cone, line_health, non_actor, random, self, tile
- amplifier type: offensive, defensive, utility

## Effects

| kind | id | schema | count | confidence | description |
| --- | --- | --- | ---: | --- | --- |
| ability | `ability_can_crit` | null | 2 | workshop | ability can critically hit. |
| ability | `ability_damage_multiplier` | float | 1 | vanilla |  |
| ability | `always_hit` | int | 3 | workshop |  |
| ability | `aoe_break` | int | 46 | vanilla | breaks AoE shape on collidables. |
| ability | `aoe_range` | int | 82 | vanilla | value will set the range for AOE of this ability. |
| ability | `aoe_shape` | int | 79 | vanilla | choose the shape for AOE in Value. |
| ability | `attack_speed` | float | 6 | vanilla | buff stat |
| ability | `bleed` | int | 9 | vanilla | ability will cause bleed status. |
| ability | `bleed_per_damage` | null | 2 | workshop | how much bleed will this ability deal per damage. |
| ability | `break_armor` | null | 1 | unconfirmed | break armor is irrelevant for S2, it damaged durability in S1 |
| ability | `burn` | int | 7 | vanilla | will apply burning effect on enemy. |
| ability | `burn_stamina` | int | 3 | vanilla | removes stamina on target. |
| ability | `burning_light` | int | 1 | vanilla |  |
| ability | `cast_heals` | int | 1 | workshop |  |
| ability | `chain` | int | 3 | vanilla | ability will chain for more than one enemy. |
| ability | `challenge` | null | 2 | vanilla | forces enemy to attack you. |
| ability | `change_physical` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `charge` | int | 4 | vanilla | Charges at a target. |
| ability | `clear_cooldowns` | int | 5 | vanilla | clears all cooldowns except this ability. |
| ability | `construct_item_cost` | float | 10 | vanilla | cost of using construc effect |
| ability | `consume_tick_damage` | null | 2 | vanilla | if the target has an effect it will be removed. |
| ability | `corrupt` | null | 1 | docs_unused | takes control of the enemy for duration. |
| ability | `critical_hit` | null | 1 | docs_unused | buff stat |
| ability | `critical_hit_chance` | float | 1 | workshop |  |
| ability | `damage` | int_pair | 179 | vanilla |  |
| ability | `damage_as_life` | float | 3 | vanilla | ability will steal HP from enemy. Value defines percent damage dealt. |
| ability | `damage_bonus` | int | 9 | vanilla | extra damage buff. |
| ability | `damage_bonus_percent` | float | 8 | vanilla | self-explanatory buff. |
| ability | `damage_on_missing_health` | null | 1 | docs_unused | extra damage when missing health. |
| ability | `damage_on_missing_stamina` | null | 1 | docs_unused | extra damage when missing health. |
| ability | `damage_receive_bonus_percent` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `damage_reduce` | int | 4 | vanilla | self-explanatory buff. |
| ability | `damage_reduce_percent` | float | 6 | vanilla | self-explanatory buff. |
| ability | `damage_to_bloodlust` | float | 1 | vanilla |  |
| ability | `damage_type` | string | 201 | vanilla |  |
| ability | `damage_weapon` | float | 88 | vanilla | % damage of the weapon wielded will apply to ability damage. |
| ability | `deflection` | float | 3 | vanilla | deflects arrows back at the attacker. |
| ability | `dexterity` | int | 6 | vanilla | buff/debuff stat |
| ability | `disadvantage` | null | 1 | unconfirmed | disadvantage is also S1 ability effect, deprecated in S2 |
| ability | `disarm` | int | 4 | vanilla | ability will disarm enemy. |
| ability | `dmg_on_cooldown` | int | 1 | workshop |  |
| ability | `dmg_without_companions` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `endurance` | int | 8 | vanilla | buff/debuff stat |
| ability | `fear` | int | 6 | vanilla | ability will cause fear effect. |
| ability | `fertility` | int | 1 | vanilla |  |
| ability | `frostbite` | int | 1 | vanilla |  |
| ability | `full_vision` | int | 3 | vanilla | 360 vision |
| ability | `heal` | int_pair | 8 | vanilla | this will cause ability to add health. |
| ability | `health_for_stamina` | null | 1 | docs_unused | % of stamina cost is returned as health. |
| ability | `hide` | int | 5 | vanilla | hides the character from sight. |
| ability | `hide_health` | int | 3 | vanilla | ability will hide health bar. |
| ability | `hit_chance` | int | 7 | vanilla | Reduces hit chance of the opponent. |
| ability | `hit_self` | null | 2 | vanilla | causes enemy to hit themselves. |
| ability | `ignore_infra_penalty` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `ignore_party` | bool | 1 | workshop |  |
| ability | `immobilize` | int | 24 | vanilla | ability will immobilize enemy. |
| ability | `increase_target_cooldown` | null | 1 | docs_unused | increases ability cooldown of target. Value defines turns. |
| ability | `intelligence` | int | 6 | vanilla | buff/debuff stat |
| ability | `knockback` | int | 17 | vanilla | ability will knock back an enemy. Value defines range. |
| ability | `knockback_damage_percent` | null | 2 | vanilla | defines how much damage will knockback do. |
| ability | `light_source` | int | 4 | vanilla | ability will give light. Value is numer of tiles that will be illuminated. |
| ability | `lunge` | int | 6 | vanilla | Lunge at position. |
| ability | `magic_deflection` | null | 2 | vanilla | deflects abilities back at caster. |
| ability | `magic_power` | float | 1 | vanilla |  |
| ability | `magic_power_damage` | float | 60 | vanilla | bonus damage from Magic Power property |
| ability | `magic_power_per_entity` | null | 1 | docs_unused | additional magic power for every entity in range. |
| ability | `magic_to_weapon_damage` | null | 1 | docs_unused | replaces weapon damage with magic power. |
| ability | `move_to_side` | int | 1 | vanilla |  |
| ability | `movement_speed` | float | 13 | vanilla | ability will buff or debuff movement speed. |
| ability | `neutralize` | string_list | 5 | vanilla | ability will neutralize one status. Choose which from the list. |
| ability | `parry_chance` | null | 2 | vanilla | buff/debuff stat |
| ability | `pierce` | int | 12 | vanilla | the first target doesn't break the line, can be used to hit multiple targets in straight line. |
| ability | `poison_effect` | int | 10 | vanilla | poison effect. |
| ability | `power_up` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `pull_target` | int | 7 | vanilla | pulls target towards ability user. |
| ability | `regeneration` | float | 8 | vanilla | ability will regenerate HP of its user. |
| ability | `remove_on_next_ability` | int | 3 | vanilla |  |
| ability | `repeat_ability_second_weapon` | null | 1 | docs_unused | self-explanatory |
| ability | `reset_cooldown_on_kill` | null | 2 | vanilla | ability will reset its cooldown, if user kills an enemy with it. |
| ability | `resistance` | int | 18 | vanilla | ability will buff or debuff resistance. |
| ability | `resistance_percent` | null | 1 | docs_unused | buff / debuff resistance by percentage. |
| ability | `restrict_to_tag` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `revenge_counter` | null | 2 | vanilla | deal damage related to last 5 hits done on you. |
| ability | `rollback` | int | 4 | vanilla | ability will roll player back. Value defines range. |
| ability | `sight` | int | 8 | vanilla | buff/debuff stat |
| ability | `silence` | int | 7 | vanilla | ability will silence an enemy. |
| ability | `stacker_count` | int | 2 | vanilla |  |
| ability | `stacker_to_dot` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| ability | `stamina` | int | 4 | vanilla | regen stamina |
| ability | `stamina_regen` | null | 1 | patch | Increases stamina regeneration. Valid on abilities and stackers (patch). Not seen in vanilla ability JSON; do not confus |
| ability | `strength` | int | 7 | vanilla | buff/debuff stat |
| ability | `stun` | float | 20 | vanilla | ability will stun an enemy. |
| ability | `summon` | int | 1 | vanilla |  |
| ability | `summon_count` | int | 44 | vanilla | max summons to create in case of large AoE spell. |
| ability | `thorns` | int | 5 | vanilla | buff stat |
| ability | `trade_places` | int | 3 | vanilla | ability will exchange places of its user and enemy. |
| ability | `vulnerable` | null | 2 | vanilla | applies to target, bumps damage received. |
| ability | `willpower` | int | 9 | vanilla | buff/debuff stat |
| ability_key | `aura` | string | 2 | vanilla |  |
| ability_key | `cage` | string | 6 | workshop |  |
| ability_key | `construct` | null | 1 | docs_unused | ability will allow to construct an entity. Choose entity from the list. |
| ability_key | `magic_power_damage` | float | 1 | vanilla |  |
| ability_key | `sense` | string | 3 | vanilla | ability will help sense certain creatures nearby. Value will define which creature type. |
| ability_key | `stacker` | string | 3 | vanilla | ability will give target an effect on target. Choose effect from Value list. |
| ability_key | `summon` | string | 53 | vanilla | ability will summon one entity. Choose which one. |
| ability_key | `summon_on_move` | string | 4 | vanilla | Summons an entity in the tile you moved from. You can choose entity that will be summoned. |
| ability_key | `summon_weather` | string | 3 | vanilla | ability wil summon weather. Choose weather effect. |
| ability_key | `transform` | string | 1 | vanilla |  |
| amplifier | `ability_can_crit` | int | 5 | vanilla |  |
| amplifier | `always_hit` | bool | 2 | vanilla |  |
| amplifier | `aoe_range` | int | 1 | vanilla |  |
| amplifier | `bleed` | int | 1 | vanilla |  |
| amplifier | `bleed_per_damage` | float | 1 | vanilla |  |
| amplifier | `burn` | int | 1 | vanilla |  |
| amplifier | `burn_stamina` | int | 1 | vanilla |  |
| amplifier | `cast_heals` | int | 2 | vanilla |  |
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
| amplifier | `damage_type` | string | 12 | vanilla |  |
| amplifier | `damage_without_companions` | float | 1 | vanilla |  |
| amplifier | `dexterity` | int | 1 | workshop |  |
| amplifier | `distance_damage` | int | 5 | vanilla |  |
| amplifier | `dmg_on_cooldown` | int | 4 | vanilla |  |
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
| amplifier | `knockback` | int | 3 | vanilla |  |
| amplifier | `knockback_damage_percent` | float | 2 | vanilla |  |
| amplifier | `magic_power_per_entity` | string | 2 | vanilla |  |
| amplifier | `magic_power_per_tag` | string | 1 | vanilla |  |
| amplifier | `magic_to_weapon_damage` | int | 1 | vanilla |  |
| amplifier | `movement_speed` | float | 3 | vanilla |  |
| amplifier | `parry_chance` | int | 3 | vanilla |  |
| amplifier | `pierce` | int | 1 | vanilla |  |
| amplifier | `poison_effect` | int | 2 | vanilla |  |
| amplifier | `reduce_random_cooldown` | int | 3 | vanilla |  |
| amplifier | `repeat_ability_second_weapon` | float | 1 | vanilla |  |
| amplifier | `resistance` | int | 2 | vanilla |  |
| amplifier | `resistance_percent` | float | 2 | vanilla |  |
| amplifier | `revenge_counter` | int | 1 | vanilla |  |
| amplifier | `rollback` | int | 2 | vanilla |  |
| amplifier | `skill_level_damage` | float | 2 | vanilla |  |
| amplifier | `stacker` | string | 2 | vanilla |  |
| amplifier | `stamina` | int | 2 | vanilla |  |
| amplifier | `strength` | int | 1 | vanilla |  |
| amplifier | `stun` | int | 2 | vanilla |  |
| amplifier | `summon` | string | 1 | vanilla |  |
| amplifier | `summon_count` | int | 1 | vanilla |  |
| amplifier | `thorns` | int | 2 | vanilla |  |
| amplifier | `turn_damage_to_stacks` | string | 1 | vanilla |  |
| amplifier | `vulnerable` | int | 4 | vanilla |  |
| amplifier | `weapon_damage_to_magic` | int | 7 | vanilla |  |
| amplifier | `willpower` | int | 1 | vanilla |  |
| amplifier_field | `cast_time` | float | 4 | vanilla | Amplifier top-level field applied to the socketed ability (cast_time). |
| amplifier_field | `cooldown` | int | 19 | vanilla | Amplifier top-level field applied to the socketed ability (cooldown). |
| amplifier_field | `cost_health` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| amplifier_field | `cost_stamina` | int | 14 | vanilla | Amplifier top-level field applied to the socketed ability (cost_stamina). |
| amplifier_field | `duration` | int | 7 | vanilla | Amplifier top-level field applied to the socketed ability (duration). |
| amplifier_field | `range` | int | 6 | vanilla | Amplifier top-level field applied to the socketed ability (range). |
| amplifier_field | `range_melee` | int | 3 | vanilla | Amplifier top-level field applied to the socketed ability (range_melee). |
| amplifier_field | `third_value` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| milestone_field | `innate` | bool | 2 | vanilla | Innate milestones are skipped when checking skill level-up requirements. Grant on entities via skills.milestones (Entity |
| passive | `2h_dual_wield` | null | 1 | vanilla |  |
| passive | `ability_extend_duration` | string | 2 | vanilla | Extends duration of a buff/ability. value is ability id; secondary_value is duration modifier (1.0 = +100%). Vanilla Spr |
| passive | `analyze_speed` | int | 1 | vanilla |  |
| passive | `analyze_weakness` | int | 1 | vanilla |  |
| passive | `area_maps` | int | 1 | vanilla |  |
| passive | `ask_favorite_people` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `attack_on_parry` | float | 1 | vanilla |  |
| passive | `attack_speed` | float | 3 | vanilla |  |
| passive | `aura_extra_aoe_range` | string | 1 | vanilla |  |
| passive | `better_deals` | unknown | 0 | patch | Better sale prices for a specific item type. value is likely the bonus; secondary_value is item_type index from messages |
| passive | `block_counter` | int | 1 | vanilla |  |
| passive | `bloodlust` | null | 1 | vanilla | bloodlust is vampire passive effect it changes hunger and thirst to bloodlust |
| passive | `bonus_attack` | float | 1 | vanilla | Chance for an extra attack when attacking (not abilities). Docs: 0.1 = 10%. |
| passive | `bonus_crafting_unit` | float | 3 | vanilla |  |
| passive | `bonus_damage` | int | 1 | vanilla |  |
| passive | `bonus_knockback_damage_percent` | float | 1 | vanilla | Increases damage dealt on knockback collisions. Vanilla Knock It Down uses 0.2. |
| passive | `bonus_one_handed_damage_percent` | int | 1 | vanilla |  |
| passive | `bonus_production_action` | string | 3 | vanilla |  |
| passive | `bonus_production_chance_item_type` | string | 1 | vanilla |  |
| passive | `bonus_two_handed_damage_percent` | int | 2 | vanilla |  |
| passive | `bounty_reduce` | float | 1 | vanilla |  |
| passive | `carry_capacity` | int | 4 | vanilla |  |
| passive | `companion` | int | 10 | vanilla |  |
| passive | `companion_build` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `consuming_souls` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `craft_persona` | string | 3 | vanilla | City-worker companion craft. Third parameter is the number of resources (patch). Still a settlement trick — do not ship  |
| passive | `critical_damage` | float | 4 | vanilla |  |
| passive | `critical_hit` | float | 5 | vanilla |  |
| passive | `critical_hit_from_dex` | float | 2 | vanilla |  |
| passive | `damage_negation` | string | 2 | vanilla |  |
| passive | `damage_reduction_missing_health` | float | 1 | vanilla |  |
| passive | `damage_to_effect` | string | 1 | vanilla |  |
| passive | `damage_type_reduction` | string | 8 | vanilla |  |
| passive | `darkvision` | int | 1 | vanilla | Ignore infravision daylight penalty to sight (same as Dread Mask). Docs example value 1. This is not infravision/sight a |
| passive | `death_under_effect_gain_health` | string | 1 | vanilla |  |
| passive | `death_under_effect_gain_stamina` | string | 3 | vanilla |  |
| passive | `disable_consumer` | null | 1 | vanilla |  |
| passive | `discover_all_tiers` | null | 1 | vanilla |  |
| passive | `discover_poi_range` | int | 1 | vanilla |  |
| passive | `dodge` | float | 4 | vanilla |  |
| passive | `dot_on_crit` | string | 1 | vanilla |  |
| passive | `extra_backpack_slots` | int | 3 | vanilla |  |
| passive | `extra_duration` | float | 1 | vanilla |  |
| passive | `extra_equip_slot` | string | 2 | vanilla |  |
| passive | `extra_loot` | float | 2 | vanilla |  |
| passive | `fall_damage` | float | 1 | vanilla |  |
| passive | `famine_display` | int | 1 | vanilla |  |
| passive | `flank_protection` | int | 1 | vanilla |  |
| passive | `food_during_travel` | int | 1 | vanilla |  |
| passive | `food_sabotage` | int | 1 | vanilla |  |
| passive | `heal_on_damage_type` | string | 1 | vanilla | Converts incoming damage of this type into healing. value is the damage type string; secondary_value is the heal ratio ( |
| passive | `heal_on_kill` | float | 3 | vanilla |  |
| passive | `health_bonus_percent` | float | 3 | vanilla |  |
| passive | `health_tick` | float | 2 | vanilla |  |
| passive | `hide_identity` | int | 2 | vanilla |  |
| passive | `hit_bonus` | int | 1 | vanilla |  |
| passive | `immunity` | string | 4 | vanilla |  |
| passive | `increase_effect_value` | string | 2 | vanilla |  |
| passive | `infravision` | null | 1 | vanilla |  |
| passive | `leader_stats` | float | 1 | vanilla |  |
| passive | `light_source` | int | 2 | vanilla |  |
| passive | `max_stamina` | int | 5 | vanilla |  |
| passive | `move_speed` | float | 5 | vanilla |  |
| passive | `movement_penalty` | float | 2 | vanilla |  |
| passive | `movement_stamina` | float | 1 | vanilla |  |
| passive | `ocean_travel` | null | 1 | vanilla |  |
| passive | `on_attack_cast` | string | 3 | vanilla |  |
| passive | `on_attack_stack` | string | 10 | vanilla |  |
| passive | `on_damage_type_stack` | string | 2 | vanilla |  |
| passive | `on_kill_create_item` | null | 1 | patch | Creates an item for the player when any being is killed. value is item id; secondary_value is chance (vanilla Taste for  |
| passive | `on_kill_persona_create_item` | string | 1 | vanilla | Creates an item when a persona (settlement NPC) is killed. Vanilla Taste for Souls: value core_2_Soul_Piece, secondary_v |
| passive | `on_max_stacks` | string | 1 | vanilla |  |
| passive | `parry` | int | 1 | vanilla |  |
| passive | `party_move_speed` | int | 1 | vanilla |  |
| passive | `plant_growth_time` | float | 1 | vanilla |  |
| passive | `points_of_interest` | null | 1 | vanilla |  |
| passive | `poison_transfer_on_kill` | int | 1 | vanilla |  |
| passive | `production_action` | int | 1 | vanilla |  |
| passive | `production_action_speed` | string | 1 | vanilla |  |
| passive | `purchase_prices` | float | 1 | vanilla |  |
| passive | `range` | int | 1 | vanilla |  |
| passive | `regeneration` | float | 1 | vanilla |  |
| passive | `regeneration_low_health` | float | 1 | vanilla |  |
| passive | `resource_discovery` | null | 1 | vanilla |  |
| passive | `resting_bonus` | float | 2 | vanilla |  |
| passive | `reveal_poi` | null | 1 | vanilla |  |
| passive | `salvage_chance` | float | 1 | vanilla |  |
| passive | `see_souls` | int | 1 | vanilla |  |
| passive | `see_stamina` | null | 1 | vanilla |  |
| passive | `self_resistance` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `sell_bonus` | float | 1 | vanilla |  |
| passive | `sight` | int | 3 | vanilla |  |
| passive | `sight_behind` | float | 2 | vanilla |  |
| passive | `spread_entity` | string | 1 | vanilla |  |
| passive | `stamina_on_stack_consume` | string | 1 | vanilla |  |
| passive | `stamina_percent_on_kill` | float | 1 | vanilla | Restore this fraction of max stamina on kill. Docs: 0.1 = 10%. |
| passive | `statistic_percent` | string | 89 | vanilla |  |
| passive | `stun_on_hit` | float | 1 | vanilla |  |
| passive | `target_resistance` | string | 5 | vanilla |  |
| passive | `thirst_on_effect` | string | 1 | vanilla |  |
| passive | `thorns` | int | 2 | vanilla |  |
| passive | `thorns_crit` | int | 1 | vanilla |  |
| passive | `thorns_for_missing_health` | float | 1 | vanilla |  |
| passive | `thorns_ranged` | float | 1 | vanilla |  |
| passive | `tool_type` | int | 6 | vanilla |  |
| passive | `trigger_ability_on_cast` | string | 1 | vanilla |  |
| passive | `uncover_entity_with_tag` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive | `uncover_resources_of_type` | int | 1 | vanilla |  |
| passive | `unique_companion` | int | 1 | vanilla |  |
| passive | `world_event_interaction` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive_field | `apply_mode` | string | 7 | vanilla | Replaces only_party. party_only = bonuses only on companions. solo_only = only with no companions. Omit for everyone. |
| passive_field | `party_only` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive_field | `restrict_shield` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| passive_field | `restrict_tags` | string_list | 2 | vanilla | Passive top-level field (restrict_tags). apply_mode replaces only_party. |
| passive_field | `restrict_tags_enemy` | bool | 1 | vanilla | Passive top-level field (restrict_tags_enemy). apply_mode replaces only_party. |
| passive_field | `restrict_weapon_type` | string | 18 | vanilla | Passive top-level field (restrict_weapon_type). apply_mode replaces only_party. |
| passive_field | `solo_only` | null | 1 | unconfirmed | Found in Soulash 2.exe string table; not seen in JSON or docs. |
| skill_field | `level_start` | unknown | 0 | patch | Optional skills.json starting level for this skill. |
| stacker | `attack_speed` | float | 3 | vanilla |  |
| stacker | `bonus_damage` | unknown | 0 | patch | Per-stack bonus damage. Patch: Bonus Damage now works in stackers. |
| stacker | `bonus_damage_percent` | unknown | 0 | patch | Per-stack bonus damage percent. Patch: Bonus Damage Percent now works in stackers. |
| stacker | `critical_hit_chance` | float | 3 | vanilla |  |
| stacker | `damage_bonus` | unknown | 0 | patch | Per-stack bonus damage (ability key name damage_bonus). Patch: works in stackers. |
| stacker | `damage_bonus_percent` | float | 3 | vanilla | Per-stack bonus damage percent (ability key name damage_bonus_percent). |
| stacker | `hit_chance` | int | 1 | workshop |  |
| stacker | `magic_power` | float | 1 | workshop |  |
| stacker | `movement_speed` | float | 2 | vanilla |  |
| stacker | `stamina_regen` | unknown | 0 | patch | Per-stack stamina regeneration bonus. |
| stacker | `willpower` | int | 1 | vanilla |  |
| stacker_field | `apply_caster` | bool | 11 | vanilla | ability_stackers.json field (apply_caster). |
| stacker_field | `duration` | int | 10 | vanilla | ability_stackers.json field (duration). |
| stacker_field | `max_stacks` | int | 11 | vanilla | ability_stackers.json field (max_stacks). |
| stacker_field | `max_stacks_cast_unlock` | bool | 2 | vanilla | ability_stackers.json field (max_stacks_cast_unlock). |
| stacker_field | `on_max_stacks_cast` | string | 2 | vanilla | ability_stackers.json field (on_max_stacks_cast). |
