#!/usr/bin/env python3
"""
AI-Enhanced ToME Asset Generator
Uses Ollama dual-agent system (CodeLlama + WizardLM) for AI-powered content generation.
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

# Import base generators
from tome_asset_generator import (
    ToMEAssetGenerator,
    AssetType,
    ShapeModule,
    DeterministicRNG
)
from tome_asset_generator_extended import (
    ExtendedToMEAssetGenerator,
    ExtendedAssetType
)

# Import Ollama model router
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import (
            get_router, get_code_model, get_visual_model,
            TASK_CODE, TASK_VISUAL, TASK_ORCHESTRATION, TASK_XML
        )
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_CODE = "code"
        TASK_VISUAL = "visual"
        TASK_ORCHESTRATION = "orchestration"
        TASK_XML = "xml"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_CODE = "code"
    TASK_VISUAL = "visual"
    TASK_ORCHESTRATION = "orchestration"
    TASK_XML = "xml"


class AIEnhancedToMEGenerator(ExtendedToMEAssetGenerator):
    """AI-enhanced generator using Ollama dual-agent system + SD3.5 sprites."""
    
    def __init__(
        self,
        output_dir: str,
        mod_name: str = "tomegen_mod",
        mod_author: str = "Generated",
        mod_version: str = "1.0.0",
        ollama_url: str = "http://localhost:11434",
        use_ai: bool = True,
        use_sd: bool = True,
        require_sd: bool = False,
    ):
        super().__init__(output_dir, mod_name, mod_author, mod_version)
        self.ollama_url = ollama_url
        self.use_ai = use_ai
        self.use_sd = use_sd
        self.require_sd = require_sd
        self.code_model = None
        self.visual_model = None
        
        if use_ai and MODEL_ROUTER_AVAILABLE:
            self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Initialize Ollama models."""
        try:
            router = get_router()
            router.print_model_assignment()
            self.code_model = router.get_code_model()
            self.visual_model = router.get_visual_model()
            print(f"AI Models initialized:")
            print(f"  Code Model: {self.code_model}")
            print(f"  Visual Model: {self.visual_model}")
        except Exception as e:
            print(f"Warning: Could not initialize Ollama: {e}")
            self.use_ai = False
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        if not self.use_ai:
            return False
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _call_ollama(
        self,
        prompt: str,
        task_type: str = TASK_VISUAL,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Call Ollama API for text generation."""
        if not self.use_ai or not self._check_ollama_available():
            return None
        
        if model is None:
            if task_type in (TASK_CODE, TASK_XML):
                model = self.code_model
            else:
                model = self.visual_model
        
        if not model:
            return None
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '').strip()
            else:
                print(f"Ollama API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Ollama call failed: {e}")
            return None
    
    def _generate_ai_lore_text(self, category: str, seed: int) -> str:
        """Generate lore text using AI."""
        prompt = f"""Generate a short lore entry for Tales of Maj'Eyal in the {category} category.
The entry should be 2-4 paragraphs, atmospheric, and fit the game's fantasy setting.
Make it mysterious and engaging. Do not include markdown formatting."""
        
        system_prompt = "You are a creative writer for a fantasy RPG. Write engaging, atmospheric lore entries."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            return result
        return f"This is a tale of ancient times, when the world was young and magic flowed freely through the lands of Maj'Eyal."
    
    def _generate_ai_flavor_text(self, asset_type: str, seed: int) -> str:
        """Generate flavor text using AI."""
        prompt = f"""Generate a short, atmospheric flavor text (1-2 sentences) for a {asset_type} in Tales of Maj'Eyal.
Make it mysterious and evocative. Do not include markdown formatting."""
        
        system_prompt = "You are a creative writer for a fantasy RPG. Write short, atmospheric flavor text."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            return result
        return "A mysterious power flows through you."
    
    def _generate_ai_achievement_desc(self, achievement_type: str, count: int) -> str:
        """Generate achievement description using AI."""
        prompt = f"""Generate a short achievement description for Tales of Maj'Eyal.
Achievement type: {achievement_type} ({count} required).
Make it concise and engaging. Do not include markdown formatting."""
        
        system_prompt = "You are a game designer writing achievement descriptions."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            return result
        return f"Completed {achievement_type} {count} times."
    
    def _generate_ai_quest_desc(self, quest_type: str) -> str:
        """Generate quest description using AI."""
        prompt = f"""Generate a short quest description for a {quest_type} quest in Tales of Maj'Eyal.
Make it engaging and fit the game's fantasy setting. Do not include markdown formatting."""
        
        system_prompt = "You are a game designer writing quest descriptions."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            return result
        return f"A {quest_type} quest awaits you."
    
    def _generate_ai_npc_desc(self, npc_type: str) -> str:
        """Generate NPC description using AI."""
        prompt = f"""Generate a short NPC description for a {npc_type} in Tales of Maj'Eyal.
Make it atmospheric and fit the game's fantasy setting. Do not include markdown formatting."""
        
        system_prompt = "You are a creative writer for a fantasy RPG. Write NPC descriptions."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            return result
        return f"A {npc_type} entity."
    
    def _generate_ai_color_palette(self, theme: str) -> List[tuple]:
        """Generate color palette using AI."""
        prompt = f"""Suggest a color palette for a {theme} themed spell/effect in Tales of Maj'Eyal.
Return only a JSON array of 3 RGB color tuples like: [[r,g,b], [r,g,b], [r,g,b]]
Each color should be 0-255. Base color, glow color, accent color."""
        
        system_prompt = "You are a game artist suggesting color palettes. Return only valid JSON arrays."
        
        result = self._call_ollama(prompt, TASK_VISUAL, system_prompt=system_prompt)
        if result:
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\[\[.*?\]\]', result)
                if json_match:
                    colors = json.loads(json_match.group())
                    if len(colors) >= 2:
                        return [tuple(c) for c in colors[:3]]
            except:
                pass
        
        # Fallback palette
        palettes = {
            'fire': [(255, 100, 100), (255, 200, 100)],
            'ice': [(100, 150, 255), (150, 200, 255)],
            'nature': [(150, 255, 150), (200, 255, 200)],
            'arcane': [(200, 100, 255), (255, 150, 255)],
            'light': [(255, 200, 100), (255, 255, 150)],
            'dark': [(100, 100, 150), (150, 150, 200)],
        }
        return palettes.get(theme, [(255, 200, 100), (255, 255, 150)])
    
    # Override methods to use AI
    
    def _generate_localization(
        self,
        asset_id: str,
        template: AssetType,
        params: Dict,
        rng: DeterministicRNG
    ) -> Path:
        """Generate localization file with AI-enhanced flavor text."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('"', '').replace("'", '').replace('\\', '')
        
        # Use AI for flavor text if available
        if self.use_ai:
            flavor = self._generate_ai_flavor_text(template.value, hash(asset_id) % 10000)
        else:
            flavor_texts = [
                "A mysterious power flows through you.",
                "The arcane energies coalesce into form.",
                "Ancient magic awakens at your command.",
                "Reality bends to your will.",
                "The void whispers secrets to you.",
            ]
            flavor = rng.choice(flavor_texts)
        
        content = f"""local _M = loadPrevious(...)

return {{
  ["{safe_id}"] = {{
    name = "{name}",
    desc = [[Generated {template.value} talent.]],
    lore = [[{flavor}]],
  }},
}}
"""
        
        locale_path = self.data_path / "locale" / "en" / f"{safe_id}.lua"
        with open(locale_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return locale_path
    
    def _generate_lore(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate lore entry with AI-enhanced text."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        categories = ['history', 'legend', 'misc', 'location', 'person']
        category = rng.choice(categories)
        
        # Use AI for lore text if available
        if self.use_ai:
            lore_text = self._generate_ai_lore_text(category, hash(asset_id) % 10000)
        else:
            lore_templates = [
                "This is a tale of ancient times, when the world was young and magic flowed freely.",
                "Legends speak of a powerful artifact hidden in the depths of forgotten ruins.",
                "The history of this place is shrouded in mystery and shadow.",
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
    
    def _generate_achievement(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate achievement with AI-enhanced description."""
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
        
        # Use AI for description if available
        if self.use_ai:
            desc = self._generate_ai_achievement_desc(a_type, count)
        else:
            desc = desc_template.format(count=count)
        
        content = f"""local _M = loadPrevious(...)

newAchievement{{
  name = "{name}",
  id = "{safe_id}",
  category = "{category}",
  show = "full",
  desc = _t[[{desc}]],
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
    
    def _generate_npc(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate NPC with AI-enhanced description."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        npc_types = ['humanoid', 'giant', 'undead', 'dragon', 'elemental', 'animal']
        npc_type = rng.choice(npc_types)
        npc_subtype = safe_id.lower()
        
        level = rng.randint(1, 20)
        max_life = rng.randint(50, 200)
        
        # Use AI for description if available
        if self.use_ai:
            desc = self._generate_ai_npc_desc(npc_type)
        else:
            desc = "Generated NPC entity."
        
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
  desc = _t[[{desc}]],
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
    
    def _generate_quest(self, asset_id: str, rng: DeterministicRNG, **kwargs) -> Dict:
        """Generate quest with AI-enhanced description."""
        name = asset_id.replace('_', ' ').title()
        safe_id = asset_id.replace('-', '_')
        
        quest_types = ['kill', 'collect', 'explore', 'escort', 'deliver']
        quest_type = rng.choice(quest_types)
        
        # Use AI for quest description if available
        if self.use_ai:
            quest_desc = self._generate_ai_quest_desc(quest_type)
        else:
            quest_desc = f"A {quest_type} quest."
        
        content = f"""local _M = loadPrevious(...)

newQuest{{
  name = "{name}",
  id = "{safe_id}",
  desc = _t[[{quest_desc}]],
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
    
    def _generate_parameters(
        self,
        template: AssetType,
        shapes: List[ShapeModule],
        rng: DeterministicRNG
    ) -> Dict:
        """Generate parameters with AI-enhanced color palettes."""
        params = super()._generate_parameters(template, shapes, rng)
        
        # Use AI for color palette if available
        if self.use_ai:
            themes = ['fire', 'ice', 'nature', 'arcane', 'light', 'dark']
            theme = rng.choice(themes)
            colors = self._generate_ai_color_palette(theme)
            if len(colors) >= 2:
                params['color'] = colors[0]
                params['glow_color'] = colors[1] if len(colors) > 1 else colors[0]
        
        return params

    def _generate_sprite(
        self,
        asset_id: str,
        template: AssetType,
        params: Dict,
        rng: DeterministicRNG
    ):
        """Prefer Ollama+SD3.5 icons; fall back to Pillow only if SD is optional."""
        if self.use_sd:
            try:
                from tome_sd_pipeline import generate_tome_icon, sd_ready

                if sd_ready() or self.require_sd:
                    kind_map = {
                        AssetType.SPELL: "spell",
                        AssetType.VFX: "effect",
                        AssetType.ITEM: "item",
                        AssetType.ACTOR: "talent",
                    }
                    kind = kind_map.get(template, "talent")
                    theme = "arcane"
                    color = params.get("color") or (200, 100, 255)
                    if isinstance(color, (list, tuple)) and len(color) >= 3:
                        # Heuristic theme from palette
                        r, g, b = color[0], color[1], color[2]
                        if r > g and r > b:
                            theme = "fire"
                        elif b > r and b > g:
                            theme = "arcane"
                        elif g > r:
                            theme = "nature"

                    frame_width = 64
                    frame_height = 64
                    frames = int(params.get("frames") or 1)
                    fps = int(params.get("fps") or 8)
                    sprite_path = self.data_path / "gfx" / "sprites" / f"{asset_id}.png"
                    meta = generate_tome_icon(
                        asset_id,
                        sprite_path,
                        kind=kind,
                        theme=theme,
                        description=asset_id.replace("_", " "),
                        seed=int(getattr(rng, "seed", 0) or hash(asset_id) % 100000),
                        size=frame_width,
                        require_sd=self.require_sd,
                    )
                    if meta.get("ok"):
                        from tome_asset_generator import SpriteMetadata

                        # Single-frame SD icon (animated sheets stay procedural)
                        if frames > 1:
                            try:
                                from PIL import Image

                                icon = Image.open(sprite_path).convert("RGBA")
                                sheet = Image.new(
                                    "RGBA", (frame_width * frames, frame_height), (0, 0, 0, 0)
                                )
                                for i in range(frames):
                                    sheet.paste(icon, (i * frame_width, 0), icon)
                                sheet.save(sprite_path)
                            except Exception as exc:
                                print(f"  [WARN] SD sheet expand failed: {exc}")

                        metadata = SpriteMetadata(
                            frame_width=frame_width,
                            frame_height=frame_height,
                            frames=frames,
                            fps=fps,
                            anchor_x=frame_width // 2,
                            anchor_y=frame_height - 8,
                            loop=True,
                        )
                        meta_path = self.data_path / "gfx" / "sprites" / f"{asset_id}.meta.json"
                        with open(meta_path, "w", encoding="utf-8") as f:
                            json.dump(metadata.to_dict(), f, indent=2)
                        print(f"  [SD] sprite {asset_id}")
                        return sprite_path, metadata
                    print(f"  [WARN] SD sprite failed: {meta.get('error')}")
                    if self.require_sd:
                        raise RuntimeError(meta.get("error") or "SD required but failed")
            except Exception as exc:
                print(f"  [WARN] SD pipeline unavailable: {exc}")
                if self.require_sd:
                    raise

        return super()._generate_sprite(asset_id, template, params, rng)

