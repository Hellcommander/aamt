#!/usr/bin/env python3
"""
Extended ToME Asset Generator
Adds support for additional ToME asset types: achievements, NPCs, zones, quests, lore, etc.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import base generator
from tome_asset_generator import (
    ToMEAssetGenerator,
    AssetType,
    ShapeModule,
    DeterministicRNG,
    SpriteMetadata,
    BalanceScore,
    VFXMetadata
)


class ExtendedAssetType(Enum):
    """Extended asset types beyond basic sprites."""
    ACHIEVEMENT = "achievement"
    BIRTH_RACE = "birth_race"
    BIRTH_CLASS = "birth_class"
    NPC = "npc"
    LORE = "lore"
    QUEST = "quest"
    ZONE = "zone"
    TIMED_EFFECT = "timed_effect"
    DAMAGE_TYPE = "damage_type"
    FACTION = "faction"
    INGREDIENT = "ingredient"
    TINKER = "tinker"


class ExtendedToMEAssetGenerator(ToMEAssetGenerator):
    """Extended generator with support for additional ToME asset types."""
    
    def __init__(self, output_dir: str, mod_name: str = "tomegen_mod", mod_author: str = "Generated", mod_version: str = "1.0.0"):
        super().__init__(output_dir, mod_name)
        self.mod_author = mod_author
        self.mod_version = mod_version
        
        # Create additional directories
        self._create_extended_directory_structure()
    
    def _create_extended_directory_structure(self):
        """Create extended directory structure for additional asset types."""
        dirs = [
            self.data_path / "achievements",
            self.data_path / "birth" / "races",
            self.data_path / "birth" / "classes",
            self.data_path / "general" / "npcs",
            self.data_path / "general" / "objects",
            self.data_path / "general" / "events",
            self.data_path / "general" / "grids",
            self.data_path / "general" / "encounters",
            self.data_path / "general" / "traps",
            self.data_path / "lore",
            self.data_path / "quests",
            self.data_path / "zones",
            self.data_path / "timed_effects",
            self.data_path / "maps" / "zones",
            self.data_path / "maps" / "towns",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def generate_extended(
        self,
        asset_type: ExtendedAssetType,
        seed: int,
        variant: str = "",
        **kwargs
    ) -> Dict:
        """Generate extended asset types."""
        rng = DeterministicRNG(seed)
        
        asset_id = f"gen_{asset_type.value}_{seed:05d}"
        if variant:
            asset_id += f"_{variant}"
        
        if asset_type == ExtendedAssetType.ACHIEVEMENT:
            return self._generate_achievement(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.BIRTH_RACE:
            return self._generate_birth_race(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.BIRTH_CLASS:
            return self._generate_birth_class(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.NPC:
            return self._generate_npc(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.LORE:
            return self._generate_lore(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.QUEST:
            return self._generate_quest(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.ZONE:
            return self._generate_zone(asset_id, rng, **kwargs)
        elif asset_type == ExtendedAssetType.TIMED_EFFECT:
            return self._generate_timed_effect(asset_id, rng, **kwargs)
        else:
            raise ValueError(f"Unsupported extended asset type: {asset_type}")
    
    def _generate_achievement(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate an achievement."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.upper().replace('-', '_')
        category = kwargs.get('category', 'Generated')
        
        achievement_types = [
            ('kill', 'Killed {count} enemies.', rng.randint(10, 100)),
            ('collect', 'Collected {count} items.', rng.randint(5, 50)),
            ('complete', 'Completed {count} quests.', rng.randint(3, 20)),
            ('explore', 'Explored {count} zones.', rng.randint(5, 30)),
        ]
        
        a_type, desc_template, count = rng.choice(achievement_types)
        
        content = f"""local _M = loadPrevious(...)

newAchievement{{
  name = "{name}",
  id = "{safe_id}",
  category = "{category}",
  show = "full",
  desc = _t[[{desc_template.format(count=count)}]],
  mode = "player",
"""
        
        if a_type == 'kill' or a_type == 'collect':
            content += f"""  can_gain = function(self, who, target)
    self.nb = (self.nb or 0) + 1
    if self.nb >= {count} then return true end
  end,
  track = function(self) return tstring{{tostring(self.nb or 0), " / {count}"}} end,
"""
        
        content += "}\n"
        
        file_path = self.data_path / "achievements" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'achievement',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name
        }
    
    def _generate_birth_race(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a birth race descriptor."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        race_types = ['humanoid', 'giant', 'undead', 'dragon', 'elemental']
        race_type = rng.choice(race_types)
        
        stat_bonuses = {
            'str': rng.randint(-2, 3),
            'dex': rng.randint(-2, 3),
            'mag': rng.randint(-2, 3),
            'con': rng.randint(-2, 3),
            'wil': rng.randint(-2, 3),
            'cun': rng.randint(-2, 3),
        }
        
        content = f"""local _M = loadPrevious(...)

newBirthDescriptor{{
  type = "race",
  name = "{name}",
  desc = {{
    _t"Generated race description.",
    _t"Created by the ToME asset generator.",
  }},
  descriptor_choices = {{
    subrace = {{
      __ALL__ = "disallow",
      {safe_id} = "allow",
    }},
  }},
  copy = {{
    type = "{race_type}",
    subtype = "{safe_id.lower()}",
    stats = {{
      str = {stat_bonuses['str']},
      dex = {stat_bonuses['dex']},
      mag = {stat_bonuses['mag']},
      con = {stat_bonuses['con']},
      wil = {stat_bonuses['wil']},
      cun = {stat_bonuses['cun']},
    }},
  }},
}}
"""
        
        file_path = self.data_path / "birth" / "races" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'birth_race',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'race_type': race_type,
            'stat_bonuses': stat_bonuses
        }
    
    def _generate_birth_class(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a birth class descriptor."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        class_types = ['warrior', 'rogue', 'mage', 'wilderness', 'psionic']
        class_type = rng.choice(class_types)
        
        content = f"""local _M = loadPrevious(...)

newBirthDescriptor{{
  type = "class",
  name = "{name}",
  desc = {{
    _t"Generated class description.",
    _t"Created by the ToME asset generator.",
  }},
  descriptor_choices = {{
    subrace = {{
      __ALL__ = "allow",
    }},
  }},
  copy = {{
    type = "class",
    class = "{class_type}",
    starting_equipment = {{}},
  }},
}}
"""
        
        file_path = self.data_path / "birth" / "classes" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'birth_class',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'class_type': class_type
        }
    
    def _generate_npc(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate an NPC entity."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        npc_types = ['humanoid', 'giant', 'undead', 'dragon', 'elemental', 'animal']
        npc_type = rng.choice(npc_types)
        npc_subtype = safe_id.lower()
        
        level = rng.randint(1, 20)
        max_life = rng.randint(50, 200)
        
        content = f"""local _M = loadPrevious(...)

newEntity{{
  define_as = "BASE_NPC_{safe_id.upper()}",
  type = "{npc_type}",
  subtype = "{npc_subtype}",
  display = "?",
  color = colors.WHITE,
  body = {{ INVEN = 10 }},
  
  max_stamina = 100,
  rank = 2,
  size_category = 3,
  
  autolevel = "warrior",
  ai = "dumb_talented_simple",
  ai_state = {{ ai_move = "move_complex", talent_in = 2 }},
  stats = {{ str = 10, dex = 10, mag = 5, con = 10 }},
  combat = {{ dammod = {{ str = 1 }} }},
  combat_armor = 2,
  combat_def = 10,
}}

newEntity{{
  base = "BASE_NPC_{safe_id.upper()}",
  name = "{name.lower()}",
  desc = _t[[Generated NPC entity.]],
  level_range = {{{level}, nil}},
  exp_worth = 1,
  rarity = 2,
  rank = 1,
  max_life = {max_life},
  life_rating = 10,
  combat = {{ dam = resolvers.levelup(5, 1, 0.7), atk = 0, apr = 3 }},
}}
"""
        
        file_path = self.data_path / "general" / "npcs" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'npc',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'npc_type': npc_type,
            'level': level
        }
    
    def _generate_lore(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a lore entry."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        categories = ['history', 'legend', 'misc', 'location', 'person']
        category = rng.choice(categories)
        
        lore_templates = [
            "This is a tale of ancient times, when the world was young and magic flowed freely.",
            "Legends speak of a powerful artifact hidden in the depths of forgotten ruins.",
            "The history of this place is shrouded in mystery and shadow.",
            "Once, long ago, a great hero walked these lands and changed everything.",
            "The records tell of a time when the balance of power shifted dramatically.",
        ]
        
        lore_text = rng.choice(lore_templates)
        
        content = f"""local _M = loadPrevious(...)

newLore{{
  id = "{safe_id}",
  category = "{category}",
  name = _t"{name}",
  lore = _t[[{lore_text}]],
}}
"""
        
        file_path = self.data_path / "lore" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'lore',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'category': category
        }
    
    def _generate_quest(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a quest."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        quest_types = ['kill', 'collect', 'explore', 'escort', 'deliver']
        quest_type = rng.choice(quest_types)
        
        content = f"""local _M = loadPrevious(...)

newQuest{{
  name = "{name}",
  id = "{safe_id}",
  starts_at = function(self, who)
    return true
  end,
  start = function(self, who)
    self:setStatus(self.ACTIVE)
    return true
  end,
  is_completed = function(self, who)
    return false
  end,
  is_done = function(self, who)
    return false
  end,
}}
"""
        
        file_path = self.data_path / "quests" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'quest',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'quest_type': quest_type
        }
    
    def _generate_zone(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a zone."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        zone_types = ['dungeon', 'wilderness', 'town', 'cave', 'ruins']
        zone_type = rng.choice(zone_types)
        
        content = f"""local _M = loadPrevious(...)

newZone{{
  name = "{name}",
  id = "{safe_id}",
  level_range = {{1, 5}},
  max_level = 5,
  width = 50,
  height = 50,
  generator = function(zone, level)
    local g = {{}}
    -- Generated zone - customize as needed
    return g
  end,
}}
"""
        
        zone_dir = self.data_path / "zones" / safe_id
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = zone_dir / "zone.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'zone',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'zone_type': zone_type
        }
    
    def _generate_timed_effect(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate a timed effect."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        effect_types = ['physical', 'magical', 'mental', 'other']
        effect_type = rng.choice(effect_types)
        
        duration = rng.randint(3, 10)
        
        content = f"""local _M = loadPrevious(...)

newEffect{{
  name = "{name}",
  desc = _t[[Generated timed effect.]],
  type = "{effect_type}",
  subtype = {{}},
  status = "beneficial",
  parameters = {{}},
  on_gain = function(self, err) return true end,
  on_timeout = function(self, eff)
    -- Effect expires
  end,
  on_lose = function(self, err)
    -- Effect removed
  end,
  activate = function(self, eff)
    eff.dur = {duration}
  end,
}}
"""
        
        file_path = self.data_path / "timed_effects" / f"{asset_id}.lua"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': asset_id,
            'type': 'timed_effect',
            'file': str(file_path.relative_to(self.mod_path)),
            'name': name,
            'effect_type': effect_type,
            'duration': duration
        }
    
    def generate_mod_init(self) -> Path:
        """Generate mod init.lua file."""
        content = f"""-- Generated ToME Mod
-- Created by ToME Asset Generator

long_name = "{self.mod_name.replace('_', ' ').title()}"
short_name = "{self.mod_name}"
for_module = "tome"
version = {{1, 7, 4}}
addon_version = {{1, 0, 0}}
weight = 1
author = {{ "{self.mod_author}" }}
homepage = "http://te4.org/"
description = [[Generated mod created by ToME Asset Generator.]]
overload = false
superload = false
hooks = false
data = true
"""
        
        init_path = self.mod_path / "init.lua"
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return init_path
    
    def generate_extended_manifest(self) -> Path:
        """Generate extended manifest with all asset types."""
        manifest = {
            'mod_name': self.mod_name,
            'version': self.mod_version,
            'generator': 'tome_asset_generator_extended',
            'assets': [],
            'extended_assets': [],
            'export_hashes': {}
        }
        
        # Add base assets
        for asset in self.assets:
            manifest['assets'].append({
                'id': asset['id'],
                'template': asset['template'],
                'balance_score': asset['balance']['total_score']
            })
        
        # Extended assets would be added here if tracked
        # (currently generated but not stored in self.assets)
        
        manifest_path = self.mod_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return manifest_path

