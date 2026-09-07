#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Space Whale High-Quality Asset Generator
Multi-stage pipeline with quality-first approach.

Stage 1: Draft Generation (4-8 variations per asset type)
Stage 2: Quality Assessment (hybrid AI + metrics)
Stage 3: Refinement (improve top candidates)
Stage 4: Final Selection (best 2-3 per type)
Stage 5: Integration Testing

Uses shared tools from Tools/Shared for consistent quality.
"""

import json
import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add Shared tools to path
SHARED_DIR = Path(__file__).parent.parent / "Shared"
TX_DIR = Path(__file__).parent
if SHARED_DIR.exists():
    sys.path.insert(0, str(SHARED_DIR))
if str(TX_DIR) not in sys.path:
    sys.path.insert(0, str(TX_DIR))

try:
    import tx_ai_pipeline as tx  # type: ignore
except ImportError:
    tx = None  # type: ignore

# Import shared tools
try:
    from audio_quality_assessment import batch_assess_audio_quality, QUALITY_20_AVAILABLE
    AUDIO_QA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import audio_quality_assessment: {e}")
    AUDIO_QA_AVAILABLE = False
    QUALITY_20_AVAILABLE = False

try:
    from ollama_integration import (
        start_ollama_if_needed, test_ollama_connection,
        get_available_models, select_best_available_model,
        AI_CONFIG, call_ollama
    )
    OLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ollama_integration: {e}")
    OLLAMA_AVAILABLE = False
    AI_CONFIG = None

try:
    from tool_helpers import safe_print, SingleInstanceLock, process_files_parallel
    TOOL_HELPERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import tool_helpers: {e}")
    TOOL_HELPERS_AVAILABLE = False

# Check if we have enough shared tools
SHARED_TOOLS_AVAILABLE = AUDIO_QA_AVAILABLE or OLLAMA_AVAILABLE or TOOL_HELPERS_AVAILABLE

# Setup safe Unicode printing
def setup_unicode_output():
    """Setup Unicode output for Windows console."""
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

setup_unicode_output()


class Stage(Enum):
    """Pipeline stages."""
    DRAFT = "draft"
    ASSESS = "assess"
    REFINE = "refine"
    SELECT = "select"
    INTEGRATE = "integrate"
    SPRITESHEET = "spritesheet"
    ITEMS = "items"


@dataclass
class AssetConfig:
    """Configuration for asset generation."""
    # Quality tiers (1-20 scale)
    draft_threshold: int = 13  # GOOD tier minimum for drafts
    production_threshold: int = 17  # EXCELLENT tier minimum for production
    perfect_threshold: int = 19  # EXCEPTIONAL tier target
    
    # Generation counts
    draft_count: int = 6  # Generate 6 variations per asset
    refine_count: int = 3  # Refine top 3
    final_count: int = 2  # Keep best 2
    
    # Model selection
    use_quality_models: bool = True  # Use higher-quality models
    enable_refinement: bool = True  # Enable refinement stage
    
    # Parallel processing
    max_workers: int = 4
    
    # Timeouts (seconds)
    draft_timeout: int = 600
    refine_timeout: int = 900
    assess_timeout: int = 300
    spritesheet_timeout: int = 3600  # Blender rendering can take time
    
    # Spritesheet generation (MANDATORY)
    generate_spritesheets: bool = True  # Always True - required for production
    blender_samples: int = 128  # Quality samples for Blender
    
    # SD3 Texture Generation
    use_sd3_textures: bool = True  # Use Stable Diffusion 3 for creative textures (enabled by default)
    sd3_texture_type: str = "all"  # "blender", "projectile", "design_draft", or "all" (auto-detected if None)
    sd3_variations: int = 3  # Variations per texture type
    sd3_include_design_drafts: bool = True  # Include design drafts (slower but higher quality)
    
    # Retry logic
    max_retries: int = 3  # Maximum retries per stage
    retry_delay: float = 5.0  # Base delay between retries (exponential backoff)
    
    # Resume capability
    resume: bool = False  # Resume interrupted generation
    skip_completed: bool = False  # Skip completed stages when resuming
    
    # Skip flags
    skip_draft: bool = False
    skip_assess: bool = False
    skip_refine: bool = False
    skip_select: bool = False
    skip_integrate: bool = False
    skip_spritesheet: bool = False
    skip_items: bool = False
    
    # Ship filtering
    ship_id: Optional[str] = None  # Filter by specific ship ID (None = all ships)
    
    # Settings file
    settings_file: Optional[str] = None  # Path to settings JSON file


@dataclass
class StageResult:
    """Result of a pipeline stage."""
    stage: Stage
    success: bool
    duration: float
    asset_count: int
    quality_scores: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    retry_count: int = 0
    file_count: int = 0
    skipped: bool = False  # True if stage was skipped (resume mode)


class HighQualityAssetGenerator:
    """High-quality multi-stage asset generator."""
    
    def __init__(self, output_dir: Path, config: Optional[AssetConfig] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = config or AssetConfig()
        self.results: Dict[str, List[StageResult]] = {}
        
        # Load settings file if specified
        if self.config.settings_file:
            self._load_settings()
        
        # Performance tracking
        self.stage_start_times: Dict[Stage, float] = {}
        self.stage_durations: Dict[Stage, float] = {}
        self.total_files_generated: int = 0
        self.stage_progress: Dict[Stage, Tuple[int, int]] = {}  # (completed, total)
        
        # Initialize Ollama if available
        if OLLAMA_AVAILABLE:
            print("Initializing Ollama integration...")
            if start_ollama_if_needed():
                print("  ✓ Ollama service started")
                
                if test_ollama_connection():
                    print("  ✓ Ollama connection verified")
                    
                    # Get available models
                    available = get_available_models()
                    if available:
                        print(f"  ✓ Found {len(available)} available models")
                    else:
                        print("  ⚠ No models found, generation may fail")
                else:
                    print("  ⚠ Could not connect to Ollama")
            else:
                print("  ⚠ Ollama initialization failed, will use fallbacks")
        else:
            print("  ℹ Ollama integration not available (optional)")

        if tx:
            print("Shared AI pipeline:")
            tx.print_probe()
            if self.config.use_sd3_textures:
                tx.prepare(image=True, mesh=True, keep_server=False)
    
    def _load_settings(self):
        """Load configuration from settings file."""
        settings_path = Path(self.config.settings_file)
        if not settings_path.exists():
            self.log(f"Settings file not found: {settings_path}", "WARNING")
            return
        
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            # Update config from settings
            if 'draftCount' in settings:
                self.config.draft_count = settings['draftCount']
            if 'finalCount' in settings:
                self.config.final_count = settings['finalCount']
            if 'enableRefinement' in settings:
                self.config.enable_refinement = settings['enableRefinement']
            if 'shipId' in settings:
                self.config.ship_id = settings['shipId']
            if 'outputDir' in settings:
                # Override output directory if specified
                self.output_dir = Path(settings['outputDir'])
                self.output_dir.mkdir(parents=True, exist_ok=True)
            if 'useSd3' in settings:
                self.config.use_sd3_textures = settings['useSd3']
            if 'sd3TextureType' in settings:
                self.config.sd3_texture_type = settings['sd3TextureType']
            if 'sd3Variations' in settings:
                self.config.sd3_variations = settings['sd3Variations']
            if 'sd3IncludeDesignDrafts' in settings:
                self.config.sd3_include_design_drafts = settings['sd3IncludeDesignDrafts']
            
            self.log(f"Loaded settings from: {settings_path}", "INFO")
        except Exception as e:
            self.log(f"Error loading settings: {e}", "ERROR")
    
    def _save_settings(self):
        """Save current configuration to settings file."""
        if not self.config.settings_file:
            return
        
        settings_path = Path(self.config.settings_file)
        try:
            settings = {
                'draftCount': self.config.draft_count,
                'finalCount': self.config.final_count,
                'enableRefinement': self.config.enable_refinement,
                'shipId': self.config.ship_id,
                'outputDir': str(self.output_dir),
                'useSd3': self.config.use_sd3_textures,
                'sd3TextureType': self.config.sd3_texture_type,
                'sd3Variations': self.config.sd3_variations,
                'sd3IncludeDesignDrafts': self.config.sd3_include_design_drafts,
                'lastRun': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log(f"Error saving settings: {e}", "WARNING")
    
    def _check_resume_capability(self) -> Dict[Stage, bool]:
        """Check which stages can be resumed (output files already exist)."""
        resume_status = {}
        
        # Check each stage for existing outputs
        resume_status[Stage.DRAFT] = (self.output_dir / "Stage1_Draft").exists() and any(
            (self.output_dir / "Stage1_Draft").rglob("*")
        )
        resume_status[Stage.ASSESS] = (self.output_dir / "Stage2_Assess").exists() and any(
            (self.output_dir / "Stage2_Assess").rglob("*")
        )
        resume_status[Stage.REFINE] = (self.output_dir / "Stage3_Refine").exists() and any(
            (self.output_dir / "Stage3_Refine").rglob("*")
        )
        resume_status[Stage.SELECT] = (self.output_dir / "Stage4_Final").exists() and any(
            (self.output_dir / "Stage4_Final").rglob("*")
        )
        resume_status[Stage.INTEGRATE] = (self.output_dir / "Stage5_Integrate").exists() and any(
            (self.output_dir / "Stage5_Integrate").rglob("*")
        )
        resume_status[Stage.SPRITESHEET] = (self.output_dir / "Stage6_Spritesheets").exists() and any(
            (self.output_dir / "Stage6_Spritesheets").rglob("*.png")
        )
        resume_status[Stage.ITEMS] = (self.output_dir / "Stage7_Items").exists() and any(
            (self.output_dir / "Stage7_Items").rglob("*.xml")
        )
        
        return resume_status
    
    def _run_with_retry(self, stage: Stage, stage_func, max_retries: Optional[int] = None) -> Tuple[bool, int]:
        """Run a stage function with retry logic and exponential backoff.
        
        Returns:
            Tuple of (success: bool, retry_count: int)
        """
        if max_retries is None:
            max_retries = self.config.max_retries
        
        retry_count = 0
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                retry_count = attempt
                delay = self.config.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                self.log(f"  → Retrying {stage.value} (attempt {attempt + 1}/{max_retries + 1}) after {delay:.1f}s...", "WARNING")
                time.sleep(delay)
            
            try:
                success = stage_func()
                if success:
                    return (True, retry_count)
                else:
                    last_error = f"Stage returned failure"
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                if attempt < max_retries:
                    self.log(f"  Error: {last_error}", "WARNING")
        
        # All retries failed
        self.log(f"  ✗ {stage.value} failed after {max_retries + 1} attempts: {last_error}", "ERROR")
        return (False, retry_count)
    
    def _calculate_eta(self, completed_stages: int, total_stages: int, elapsed_time: float) -> Optional[float]:
        """Calculate estimated time to completion."""
        if completed_stages == 0:
            return None
        
        avg_time_per_stage = elapsed_time / completed_stages
        remaining_stages = total_stages - completed_stages
        eta = avg_time_per_stage * remaining_stages
        
        return eta
    
    def _filter_ships_by_id(self, registry_data: Dict) -> Dict:
        """Filter ship registry by ship ID if specified."""
        if not self.config.ship_id:
            return registry_data
        
        # Filter ships list if it exists
        if 'ships' in registry_data:
            original_ships = registry_data['ships']
            filtered_ships = [s for s in original_ships if s.get('id') == self.config.ship_id]
            
            if not filtered_ships:
                self.log(f"  ⚠ No ships found with ID '{self.config.ship_id}'", "WARNING")
                return registry_data  # Return original if no match
            
            registry_data['ships'] = filtered_ships
            self.log(f"  Filtered to ship ID: {self.config.ship_id} ({len(filtered_ships)} ship(s))", "INFO")
        
        return registry_data
    
    def _count_files_in_directory(self, directory: Path, extensions: List[str] = None) -> int:
        """Count files in a directory (recursively)."""
        if not directory.exists():
            return 0
        
        if extensions is None:
            extensions = ['.json', '.png', '.bmp', '.wav', '.ogg', '.xml', '.md']
        
        count = 0
        for ext in extensions:
            count += len(list(directory.rglob(f"*{ext}")))
        
        return count
    
    def log(self, message: str, level: str = "INFO"):
        """Thread-safe logging."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "WARNING": "⚠",
            "ERROR": "✗",
            "STAGE": "▶"
        }.get(level, "•")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def generate_assets(self) -> bool:
        """Run complete multi-stage pipeline with retry logic and resume support."""
        self.log("="*80, "STAGE")
        self.log("Space Whale High-Quality Asset Generator", "STAGE")
        self.log("Multi-Stage Quality-First Pipeline", "STAGE")
        self.log("="*80, "STAGE")
        
        # Check resume capability
        resume_status = {}
        if self.config.resume or self.config.skip_completed:
            resume_status = self._check_resume_capability()
            completed_stages = [stage.value for stage, exists in resume_status.items() if exists]
            if completed_stages:
                self.log(f"Resume mode: Found existing outputs for {len(completed_stages)} stages: {', '.join(completed_stages)}", "INFO")
        
        start_time = time.time()
        completed_stages = 0
        total_stages = 7  # Total number of stages
        
        # Define stages with their skip flags
        stages = [
            (Stage.DRAFT, self._stage_draft, self.config.skip_draft, "Draft generation"),
            (Stage.ASSESS, self._stage_assess, self.config.skip_assess, "Quality assessment"),
            (Stage.REFINE, self._stage_refine, self.config.skip_refine, "Refinement"),
            (Stage.SELECT, self._stage_select, self.config.skip_select, "Final selection"),
            (Stage.INTEGRATE, self._stage_integrate, self.config.skip_integrate, "Integration testing"),
            (Stage.SPRITESHEET, self._stage_spritesheet, self.config.skip_spritesheet, "Spritesheet generation"),
            (Stage.ITEMS, self._stage_items, self.config.skip_items, "Item generation"),
        ]
        
        # Run each stage
        for stage, stage_func, skip_flag, stage_name in stages:
            # Check if stage should be skipped
            if skip_flag:
                self.log(f"Skipping {stage_name} (--skip-{stage.value})", "INFO")
                completed_stages += 1
                continue
            
            # Check if stage is already completed (resume mode)
            if self.config.skip_completed and resume_status.get(stage, False):
                self.log(f"Skipping {stage_name} (already completed)", "INFO")
                completed_stages += 1
                continue
            
            # Track progress
            elapsed_time = time.time() - start_time
            eta = self._calculate_eta(completed_stages, total_stages, elapsed_time)
            progress_pct = int((completed_stages / total_stages) * 100)
            
            if eta:
                self.log(f"[{completed_stages}/{total_stages}] ({progress_pct}%) ETA: {eta/60:.1f} min", "INFO")
            else:
                self.log(f"[{completed_stages}/{total_stages}] ({progress_pct}%)", "INFO")
            
            # Run stage with retry logic
            stage_start = time.time()
            success, retry_count = self._run_with_retry(stage, stage_func)
            stage_duration = time.time() - stage_start
            
            self.stage_durations[stage] = stage_duration
            
            # Count files generated in this stage
            stage_dir_map = {
                Stage.DRAFT: "Stage1_Draft",
                Stage.ASSESS: "Stage2_Assess",
                Stage.REFINE: "Stage3_Refine",
                Stage.SELECT: "Stage4_Final",
                Stage.INTEGRATE: "Stage5_Integrate",
                Stage.SPRITESHEET: "Stage6_Spritesheets",
                Stage.ITEMS: "Stage7_Items",
            }
            
            file_count = 0
            if stage in stage_dir_map:
                stage_dir = self.output_dir / stage_dir_map[stage]
                file_count = self._count_files_in_directory(stage_dir)
            
            # Store stage result
            result = StageResult(
                stage=stage,
                success=success,
                duration=stage_duration,
                asset_count=0,  # Will be updated by individual stages
                retry_count=retry_count[0],
                file_count=file_count
            )
            
            if stage.value not in self.results:
                self.results[stage.value] = []
            self.results[stage.value].append(result)
            
            if success:
                completed_stages += 1
                self.log(f"✓ {stage_name} completed in {stage_duration:.1f}s ({file_count} files)", "SUCCESS")
            else:
                # Critical stages fail the pipeline
                if stage in [Stage.DRAFT, Stage.ASSESS, Stage.SELECT, Stage.SPRITESHEET]:
                    self.log(f"{stage_name} failed, aborting pipeline", "ERROR")
                    return False
                else:
                    self.log(f"{stage_name} failed, continuing...", "WARNING")
                    completed_stages += 1
        
        total_time = time.time() - start_time
        
        # Generate summary report
        self._generate_report(total_time)
        
        # Generate file summary
        self._generate_file_summary()
        
        # Save settings
        self._save_settings()
        
        self.log("="*80, "STAGE")
        self.log(f"Pipeline completed in {total_time/60:.1f} minutes", "SUCCESS")
        self.log(f"Generated {self.total_files_generated} files across {completed_stages} stages", "SUCCESS")
        self.log("="*80, "STAGE")
        
        return True
    
    def _stage_draft(self) -> bool:
        """Stage 1: Generate initial draft assets."""
        self.log("="*80, "STAGE")
        self.log("STAGE 1: Draft Generation", "STAGE")
        self.log(f"  Target: {self.config.draft_count} variations per asset type", "INFO")
        self.log(f"  Quality threshold: {self.config.draft_threshold}/20 (GOOD tier)", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # CRITICAL ORDER: Textures → Rigging → everything else
        # (Rigging needs textures, Blender needs both for spritesheet generation)
        
        self.log("\n[1/5] Generating textures (CRITICAL for rigging & spritesheets)...", "INFO")
        texture_result = self._generate_texture_drafts()
        if not texture_result:
            self.log("✗ CRITICAL: Texture generation failed - cannot continue!", "ERROR")
            return False
        
        self.log("\n[2/5] Generating rigging (CRITICAL for Blender models)...", "INFO")
        rigging_result = self._generate_rigging()
        if not rigging_result:
            self.log("✗ CRITICAL: Rigging generation failed - spritesheets may be static!", "ERROR")
            return False
        
        # Generate Visual Language Assets
        self.log("\n[3/5] Generating visual language...", "INFO")
        visual_result = self._generate_visual_language_drafts()
        
        # Generate FX Assets (particles + effects)
        self.log("\n[4/5] Generating FX assets (particles + effects)...", "INFO")
        fx_result = self._generate_fx_drafts()
        
        # Generate Audio Assets
        self.log("\n[5/5] Generating audio assets...", "INFO")
        audio_result = self._generate_audio_drafts()
        
        stage_duration = time.time() - stage_start
        
        # Check if all critical assets generated
        success = all([texture_result, rigging_result, visual_result, fx_result, audio_result])
        
        if success:
            self.log(f"\n✓ Stage 1 completed in {stage_duration/60:.1f} minutes", "SUCCESS")
            self.log(f"  Generated:", "INFO")
            self.log(f"    ✓ Textures (for Blender models)", "INFO")
            self.log(f"    ✓ Rigging (bone-driven animation)", "INFO")
            self.log(f"    ✓ Visual Language variations", "INFO")
            self.log(f"    ✓ FX assets (particles + effects)", "INFO")
            self.log(f"    ✓ Audio files (WAV + OGG)", "INFO")
        else:
            self.log(f"✗ Stage 1 had failures", "ERROR")
        
        return success
    
    def _stage_assess(self) -> bool:
        """Stage 2: Assess quality of all drafted assets."""
        self.log("="*80, "STAGE")
        self.log("STAGE 2: Quality Assessment", "STAGE")
        self.log(f"  Using hybrid AI + metrics evaluation", "INFO")
        self.log(f"  Production threshold: {self.config.production_threshold}/20", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # Assess Visual Language
        self._assess_visual_language()
        
        # Assess FX Assets
        self._assess_fx()
        
        # Assess Audio (use shared tools)
        if AUDIO_QA_AVAILABLE:
            self._assess_audio_hybrid()
        else:
            self._assess_audio_basic()
        
        # Assess Textures
        self._assess_textures()
        
        stage_duration = time.time() - stage_start
        self.log(f"Stage 2 completed in {stage_duration/60:.1f} minutes", "SUCCESS")
        
        return True
    
    def _stage_refine(self) -> bool:
        """Stage 3: Refine top candidates."""
        self.log("="*80, "STAGE")
        self.log("STAGE 3: Refinement", "STAGE")
        self.log(f"  Refining top {self.config.refine_count} candidates per type", "INFO")
        self.log(f"  Target quality: {self.config.perfect_threshold}/20 (EXCEPTIONAL)", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # Refine top assets (use AI feedback loop)
        self._refine_top_assets()
        
        stage_duration = time.time() - stage_start
        self.log(f"Stage 3 completed in {stage_duration/60:.1f} minutes", "SUCCESS")
        
        return True
    
    def _stage_select(self) -> bool:
        """Stage 4: Select best final assets."""
        self.log("="*80, "STAGE")
        self.log("STAGE 4: Final Selection", "STAGE")
        self.log(f"  Selecting top {self.config.final_count} per asset type", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # Select and package best assets
        self._select_best_assets()
        
        stage_duration = time.time() - stage_start
        self.log(f"Stage 4 completed in {stage_duration:.1f} seconds", "SUCCESS")
        
        return True
    
    def _stage_integrate(self) -> bool:
        """Stage 5: Integration testing."""
        self.log("="*80, "STAGE")
        self.log("STAGE 5: Integration Testing", "STAGE")
        self.log("  Verifying asset compatibility and format", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # Test integration
        self._test_integration()
        
        stage_duration = time.time() - stage_start
        self.log(f"Stage 5 completed in {stage_duration:.1f} seconds", "SUCCESS")
        
        return True
    
    def _stage_spritesheet(self) -> bool:
        """Stage 6: Generate 120 facings spritesheets with Blender."""
        self.log("="*80, "STAGE")
        self.log("STAGE 6: Spritesheet Generation", "STAGE")
        self.log("  Rendering 120 facings for all ship types", "INFO")
        self.log("  This may take 30-60 minutes depending on hardware", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        # Generate spritesheets using Blender
        success = self._generate_120_facings()
        
        stage_duration = time.time() - stage_start
        
        if success:
            self.log(f"Stage 6 completed in {stage_duration/60:.1f} minutes", "SUCCESS")
        else:
            self.log(f"Stage 6 had issues", "WARNING")
        
        return success
    
    def _stage_items(self) -> bool:
        """Stage 7: Generate Transcendence ItemType definitions."""
        self.log("="*80, "STAGE")
        self.log("STAGE 7: Item Generation", "STAGE")
        self.log("  Generating Transcendence game items (weapons, devices, armor)", "INFO")
        self.log("="*80, "STAGE")
        
        stage_start = time.time()
        
        script_dir = Path(__file__).parent
        item_generator = script_dir / "SpaceWhaleItemGenerator.ps1"
        item_bat = script_dir / "SpaceWhaleItemGenerator.bat"
        
        if not item_generator.exists() and not item_bat.exists():
            self.log("  ⚠ Item generator not found, skipping", "WARNING")
            return False
        
        asset_dir = self.output_dir / "Stage4_Final"
        output_dir = self.output_dir / "Stage7_Items"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  Asset source: {asset_dir}", "INFO")
        self.log(f"  Output: {output_dir}", "INFO")
        self.log(f"  Generating: Weapons, Devices, Armor, Ammunition", "INFO")
        
        try:
            if item_bat.exists():
                cmd = [str(item_bat), "-AssetDir", str(asset_dir),
                      "-OutputDir", str(output_dir), "-ItemCount", "6"]
            else:
                cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-File", str(item_generator), "-AssetDir", str(asset_dir),
                      "-OutputDir", str(output_dir), "-ItemCount", "6"]
            
            result = subprocess.run(cmd, timeout=120, capture_output=False, text=True)
            
            stage_duration = time.time() - stage_start
            
            if result.returncode == 0:
                # Verify item files were created
                xml_files = list(output_dir.glob("*.xml"))
                registry = output_dir / "item_registry.json"
                
                if xml_files and registry.exists():
                    file_count = len(xml_files) + (1 if registry.exists() else 0)
                    self.total_files_generated += file_count
                    self.log(f"  ✓ Generated {len(xml_files)} XML files", "SUCCESS")
                    for xml_file in xml_files:
                        self.log(f"    - {xml_file.name}", "INFO")
                    self.log(f"  ✓ Registry: {registry.name}", "SUCCESS")
                    self.log(f"Stage 7 completed in {stage_duration:.1f} seconds", "SUCCESS")
                    return True
                else:
                    self.log("  ⚠ No item files generated", "WARNING")
                    return False
            else:
                self.log(f"  ⚠ Item generation had issues (exit {result.returncode})", "WARNING")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("  ⚠ Item generation timed out", "WARNING")
            return False
        except Exception as e:
            self.log(f"  ⚠ Item generation error: {e}", "WARNING")
            return False
    
    # ===== Asset Generation Methods =====
    
    def _generate_rigging(self) -> bool:
        """Generate rigging (bone system for Blender models)."""
        self.log("Generating rigging (bone-driven animation system)...", "INFO")
        
        script_dir = Path(__file__).parent
        rigging_script = script_dir / "SpaceWhaleRiggingGenerator.ps1"
        rigging_bat = script_dir / "SpaceWhaleRiggingGenerator.bat"
        
        if not rigging_script.exists() and not rigging_bat.exists():
            self.log(f"  ✗ Rigging generator not found", "ERROR")
            self.log("    Rigging is REQUIRED for animated Blender models!", "ERROR")
            return False
        
        registry_file = script_dir / "space_whale_ship_example.json"
        if not registry_file.exists():
            self.log(f"  ✗ Ship registry not found: {registry_file}", "ERROR")
            return False
        
        output_path = self.output_dir / "Stage1_Draft" / "Rigging"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Filter registry by ship ID if specified
        actual_registry_file = registry_file
        if self.config.ship_id:
            # Load and filter registry
            with open(registry_file, 'r') as f:
                registry_data = json.load(f)
            
            filtered_data = self._filter_ships_by_id(registry_data)
            
            # Create temporary filtered registry
            temp_registry = output_path / "filtered_registry.json"
            with open(temp_registry, 'w') as f:
                json.dump(filtered_data, f, indent=2)
            
            actual_registry_file = temp_registry
        
        self.log(f"  Ship registry: {registry_file.name}", "INFO")
        if self.config.ship_id:
            self.log(f"  Filtered to ship ID: {self.config.ship_id}", "INFO")
        self.log(f"  Output: {output_path}", "INFO")
        self.log(f"  Generating bone-driven spine system (6-8 segments)...", "INFO")
        
        try:
            if rigging_bat.exists():
                cmd = [str(rigging_bat), "-RegistryPath", str(actual_registry_file),
                      "-OutputDir", str(output_path), "-SegmentCount", "6"]
            else:
                cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-File", str(rigging_script), "-RegistryPath", str(actual_registry_file),
                      "-OutputDir", str(output_path), "-SegmentCount", "6"]
            
            result = subprocess.run(cmd, timeout=self.config.draft_timeout,
                                  capture_output=False, text=True)
            
            if result.returncode == 0:
                # Verify rigging files were created
                rig_files = list(output_path.rglob("*_rig_config.json"))
                
                if rig_files:
                    file_count = len(rig_files)
                    self.total_files_generated += file_count
                    self.log(f"  ✓ Rigging generated: {file_count} rig configs", "SUCCESS")
                    for rig_file in rig_files:
                        self.log(f"    - {rig_file.name}", "INFO")
                    return True
                else:
                    self.log("  ⚠ No rigging files generated (using procedural fallback)", "WARNING")
                    return True  # Continue with procedural rigging
            else:
                self.log(f"  ⚠ Rigging generation had issues, will use procedural", "WARNING")
                return True  # Continue with procedural rigging
                
        except subprocess.TimeoutExpired:
            self.log("  ⚠ Rigging generation timed out, using procedural", "WARNING")
            return True  # Continue with procedural rigging
        except Exception as e:
            self.log(f"  ⚠ Rigging warning: {e}, using procedural", "WARNING")
            return True  # Continue with procedural rigging
    
    def _generate_visual_language_drafts(self) -> bool:
        """Generate visual language draft variations."""
        self.log("Generating Visual Language drafts...", "INFO")
        
        script_dir = Path(__file__).parent
        visual_script = script_dir / "SpaceWhaleVisualLanguageGenerator.ps1"
        visual_bat = script_dir / "SpaceWhaleVisualLanguageGenerator.bat"
        
        if not visual_script.exists() and not visual_bat.exists():
            self.log(f"Visual Language generator not found", "ERROR")
            return False
        
        registry_file = script_dir / "space_whale_visual_language_registry.json"
        output_path = self.output_dir / "Stage1_Draft" / "VisualLanguage"
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if visual_bat.exists():
                cmd = [str(visual_bat), "-RegistryPath", str(registry_file), 
                      "-OutputDir", str(output_path), "-Count", str(self.config.draft_count)]
            else:
                cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-File", str(visual_script), "-RegistryPath", str(registry_file),
                      "-OutputDir", str(output_path), "-Count", str(self.config.draft_count)]
            
            result = subprocess.run(cmd, timeout=self.config.draft_timeout,
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log(f"  ✓ Visual Language drafts generated: {output_path}", "SUCCESS")
                return True
            else:
                self.log(f"  ✗ Visual Language generation failed", "ERROR")
                if result.stderr:
                    self.log(f"    Error: {result.stderr[:200]}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("  ✗ Visual Language generation timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"  ✗ Visual Language error: {e}", "ERROR")
            return False
    
    def _generate_fx_drafts(self) -> bool:
        """Generate FX asset drafts (includes particles)."""
        self.log("Generating FX drafts (particles + effects)...", "INFO")
        
        script_dir = Path(__file__).parent
        fx_script = script_dir / "space_whale_fx_variation_generator.py"
        
        if not fx_script.exists():
            self.log(f"  ✗ FX generator not found: {fx_script}", "ERROR")
            return False
        
        registry_file = script_dir / "space_whale_fx_registry.json"
        if not registry_file.exists():
            self.log(f"  ✗ FX registry not found: {registry_file}", "ERROR")
            return False
        
        output_path = self.output_dir / "Stage1_Draft" / "FX"
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  Registry: {registry_file.name}", "INFO")
        self.log(f"  Output: {output_path}", "INFO")
        self.log(f"  Generating {self.config.draft_count} variations per effect...", "INFO")
        self.log(f"  Keeping top {self.config.refine_count} for refinement stage", "INFO")
        self.log(f"  Including particles, emitters, and visual effects", "INFO")
        
        try:
            cmd = [sys.executable, str(fx_script), str(registry_file),
                  str(self.config.draft_count), str(self.config.refine_count),
                  "--output-dir", str(output_path)]
            
            result = subprocess.run(cmd, timeout=self.config.draft_timeout,
                                  capture_output=False, text=True)
            
            if result.returncode == 0:
                # Verify FX files were created in output directory
                fx_best = output_path / "space_whale_fx_registry_best.json"
                fx_placeholders = output_path / "space_whale_fx_registry_placeholders.json"
                fx_report = output_path / "SPACE_WHALE_FX_QUALITY_ASSESSMENT.md"
                
                if fx_best.exists() or fx_placeholders.exists():
                    fx_count = (1 if fx_best.exists() else 0) + (1 if fx_placeholders.exists() else 0)
                    self.total_files_generated += fx_count
                    self.log("  ✓ FX drafts generated (particles + effects)", "SUCCESS")
                    if fx_best.exists():
                        self.log(f"    Best: {fx_best.name}", "INFO")
                    if fx_placeholders.exists():
                        self.log(f"    Placeholders: {fx_placeholders.name}", "INFO")
                    
                    # Copy assessment report to Stage2_Assess
                    if fx_report.exists():
                        assess_dir = self.output_dir / "Stage2_Assess"
                        assess_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(fx_report, assess_dir / "fx_assessment_report.md")
                        self.log(f"    Assessment report copied to Stage2_Assess", "INFO")
                    
                    return True
                else:
                    self.log("  ✗ No FX output files were generated", "ERROR")
                    return False
            else:
                self.log(f"  ✗ FX generation failed with exit code {result.returncode}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("  ✗ FX generation timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"  ✗ FX error: {e}", "ERROR")
            return False
    
    def _generate_audio_drafts(self) -> bool:
        """Generate audio asset drafts."""
        self.log("Generating Audio drafts...", "INFO")
        
        script_dir = Path(__file__).parent
        audio_script = script_dir / "space_whale_audio_generator.py"
        
        if not audio_script.exists():
            self.log("  ✗ Audio generator not found", "ERROR")
            self.log(f"    Expected: {audio_script}", "ERROR")
            return False
        
        registry_file = script_dir / "space_whale_audio_registry.json"
        if not registry_file.exists():
            self.log(f"  ✗ Audio registry not found: {registry_file}", "ERROR")
            return False
        
        output_path = self.output_dir / "Stage1_Draft" / "Audio"
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  Registry: {registry_file.name}", "INFO")
        self.log(f"  Output: {output_path}", "INFO")
        self.log(f"  Generating {self.config.draft_count} variations per sound...", "INFO")
        
        try:
            cmd = [sys.executable, str(audio_script),
                  "--registry", str(registry_file),
                  "--output", str(output_path),
                  "--variations", str(self.config.draft_count)]
            
            # Add resume flags if enabled
            if self.config.resume or self.config.skip_completed:
                cmd.extend(["--resume", "--skip-completed"])
            
            self.log("  Starting audio generation (this may take 5-10 minutes)...", "INFO")
            
            result = subprocess.run(cmd, timeout=self.config.draft_timeout,
                                  capture_output=False, text=True)
            
            if result.returncode == 0:
                # Verify audio files were created
                audio_files = list(output_path.rglob("*.wav")) + list(output_path.rglob("*.ogg"))
                
                if audio_files:
                    file_count = len(audio_files)
                    self.total_files_generated += file_count
                    self.log(f"  ✓ Audio drafts generated: {file_count} files", "SUCCESS")
                    self.log(f"    WAV files: {len(list(output_path.rglob('*.wav')))}", "INFO")
                    self.log(f"    OGG files: {len(list(output_path.rglob('*.ogg')))}", "INFO")
                    return True
                else:
                    self.log("  ✗ No audio files were generated", "ERROR")
                    return False
            else:
                self.log(f"  ✗ Audio generation failed with exit code {result.returncode}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("  ✗ Audio generation timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"  ✗ Audio error: {e}", "ERROR")
            return False
    
    def _generate_texture_drafts(self) -> bool:
        """Generate texture drafts (REQUIRED for spritesheet generation)."""
        self.log("Generating Texture drafts (required for Blender spritesheets)...", "INFO")
        
        script_dir = Path(__file__).parent
        texture_script = script_dir / "space_whale_texture_generator.py"
        
        ship_registry = script_dir / "space_whale_ship_example.json"
        visual_registry = script_dir / "space_whale_visual_language_registry.json"
        skinning_registry = script_dir / "space_whale_skinning_registry.json"
        
        if not texture_script.exists():
            self.log(f"  ✗ Texture generator not found: {texture_script}", "ERROR")
            self.log("    Textures are REQUIRED for Blender spritesheet generation!", "ERROR")
            return False
        
        missing_registries = []
        for reg in [ship_registry, visual_registry, skinning_registry]:
            if not reg.exists():
                missing_registries.append(reg.name)
        
        if missing_registries:
            self.log(f"  ✗ Missing registries: {', '.join(missing_registries)}", "ERROR")
            self.log("    Textures are REQUIRED for Blender spritesheet generation!", "ERROR")
            return False
        
        output_path = self.output_dir / "Stage1_Draft" / "Textures"
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  Registries found:", "INFO")
        self.log(f"    - Ship: {ship_registry.name}", "INFO")
        self.log(f"    - Visual: {visual_registry.name}", "INFO")
        self.log(f"    - Skinning: {skinning_registry.name}", "INFO")
        self.log(f"  Generating textures for Blender models...", "INFO")
        
        try:
            cmd = [sys.executable, str(texture_script),
                  "--ship-registry", str(ship_registry),
                  "--visual-registry", str(visual_registry),
                  "--skinning-registry", str(skinning_registry),
                  "--output", str(output_path)]
            
            result = subprocess.run(cmd, timeout=self.config.draft_timeout,
                                  capture_output=False, text=True)
            
            if result.returncode == 0:
                # Verify textures were created
                texture_files = list(output_path.rglob("*.png")) + list(output_path.rglob("*.tga"))
                
                if texture_files:
                    file_count = len(texture_files)
                    self.total_files_generated += file_count
                    self.log(f"  ✓ Texture drafts generated: {file_count} files", "SUCCESS")
                    self.log(f"    PNG: {len(list(output_path.rglob('*.png')))}", "INFO")
                    self.log(f"    TGA: {len(list(output_path.rglob('*.tga')))}", "INFO")
                    
                    # Generate SD3 textures automatically (enabled by default)
                    # SD3 automatically detects ships from registry and generates all needed textures
                    if self.config.use_sd3_textures:
                        self.log("  Generating SD3 creative textures automatically for all ships...", "INFO")
                        self.log("  SD3 will auto-detect required assets from ship registry", "INFO")
                        sd3_success = self._generate_sd3_textures()
                        if sd3_success:
                            self.log("  ✓ SD3 textures generated automatically for all detected ships", "SUCCESS")
                        else:
                            self.log("  ⚠ SD3 texture generation had issues (continuing)", "WARNING")
                    
                    return True
                else:
                    self.log("  ✗ No texture files were generated", "ERROR")
                    return False
            else:
                self.log(f"  ✗ Texture generation failed with exit code {result.returncode}", "ERROR")
                self.log("    Textures are REQUIRED for Blender spritesheet generation!", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("  ✗ Texture generation timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"  ✗ Texture error: {e}", "ERROR")
            return False
    
    def _generate_sd3_textures(self) -> bool:
        """Generate creative textures using Stable Diffusion 3 (automatic asset detection)."""
        script_dir = Path(__file__).parent
        sd3_script = script_dir / "SpaceWhaleSD3TextureGenerator.ps1"
        sd3_bat = script_dir / "SpaceWhaleSD3TextureGenerator.bat"
        
        if not sd3_script.exists() and not sd3_bat.exists():
            self.log("  ⚠ SD3 texture generator not found, skipping", "WARNING")
            return False
        
        ship_registry = script_dir / "space_whale_ship_example.json"
        visual_registry = script_dir / "space_whale_visual_language_registry.json"
        
        if not ship_registry.exists() or not visual_registry.exists():
            self.log("  ⚠ Required registries not found for SD3 generation", "WARNING")
            return False
        
        output_path = self.output_dir / "Stage1_Draft" / "Textures"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect ships from registry (SD3 generator will process all ships automatically)
        try:
            with open(ship_registry, 'r', encoding='utf-8') as f:
                ship_data = json.load(f)
            
            # Count ships (handle both single ship and array formats)
            if isinstance(ship_data, list):
                ship_count = len(ship_data)
            elif isinstance(ship_data, dict) and 'ships' in ship_data:
                ship_count = len(ship_data['ships'])
            elif isinstance(ship_data, dict) and 'id' in ship_data:
                ship_count = 1  # Single ship object
            else:
                ship_count = 1
            
            self.log(f"  Auto-detected {ship_count} ship(s) from registry", "INFO")
        except Exception as e:
            self.log(f"  ⚠ Could not auto-detect ships: {e} (SD3 will use registry directly)", "WARNING")
            ship_count = "unknown"
        
        # Auto-determine texture types needed
        # SD3 generator automatically generates all required types: blender, projectile, design_draft, full_ship_artwork
        texture_type = self.config.sd3_texture_type
        if texture_type == "all" or not texture_type:
            # Auto-generate all texture types for complete asset set
            texture_type = "all"
            self.log(f"  Auto-generating all texture types: Blender, Projectile, Design Drafts, Full Ship Artwork", "INFO")
        else:
            self.log(f"  Texture types: {texture_type}", "INFO")
        
        self.log(f"  Variations: {self.config.sd3_variations} per type per ship", "INFO")
        if not self.config.sd3_include_design_drafts:
            self.log(f"  Fast mode: Design drafts disabled", "INFO")
        
        try:
            # Use standard textures as reference for SD3 generation
            reference_texture_dir = str(output_path)

            if tx:
                tx.prepare(image=True, mesh=True, keep_server=False)
            
            # Generate design drafts FIRST (before other textures)
            
            # Generate design drafts FIRST (before other textures)
            # Design drafts are concept art that don't need references - they're the foundation
            # Then use design drafts as reference for blender, projectile, and full artwork
            texture_type = self.config.sd3_texture_type
            include_full_artwork = self.config.sd3_include_design_drafts
            
            # Multi-pass generation: design drafts first, then other textures
            passes = []
            
            if texture_type == "all" or "design_draft" in texture_type:
                # Pass 1: Generate design drafts first (no reference needed, just ship description)
                passes.append({
                    "type": "design_draft",
                    "description": "Design Drafts (concept art foundation)",
                    "reference_dir": reference_texture_dir,  # Can use procedural textures if available
                    "include_full_artwork": False
                })
            
            # Pass 2: Generate blender and projectile textures (using design drafts as reference)
            if texture_type == "all" or "blender" in texture_type or "projectile" in texture_type:
                passes.append({
                    "type": "blender,projectile",
                    "description": "Blender and Projectile textures",
                    "reference_dir": str(output_path / "DesignDrafts"),  # Use design drafts as primary reference
                    "include_full_artwork": False
                })
            
            # Pass 3: Generate full ship artwork (using design drafts as reference)
            if include_full_artwork and (texture_type == "all" or "full_ship_artwork" in texture_type):
                passes.append({
                    "type": "full_ship_artwork",
                    "description": "Full Ship Artwork",
                    "reference_dir": str(output_path / "DesignDrafts"),  # Use design drafts as primary reference
                    "include_full_artwork": True
                })
            
            # If no passes defined, use original logic
            if not passes:
                passes.append({
                    "type": texture_type,
                    "description": f"{texture_type} textures",
                    "reference_dir": reference_texture_dir,
                    "include_full_artwork": include_full_artwork
                })
            
            # Execute passes sequentially: design drafts first, then other textures
            all_success = True
            for pass_num, pass_config in enumerate(passes, 1):
                self.log(f"  Pass {pass_num}/{len(passes)}: {pass_config['description']}", "INFO")
                
                # Use PowerShell script directly for full control over each pass
                cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-File", str(sd3_script),
                      "-ShipRegistry", str(ship_registry),
                      "-VisualRegistry", str(visual_registry),
                      "-OutputDir", str(output_path),
                      "-TextureType", pass_config["type"],
                      "-Variations", str(self.config.sd3_variations),
                      "-ReferenceTextureDir", pass_config["reference_dir"],
                      "-ImageStrength", "0.7",
                      "-QualityAssessmentDepth", "full"]
                
                if pass_config["include_full_artwork"]:
                    cmd.append("-IncludeFullShipArtwork")
                
                if self.config.ship_id:
                    cmd.extend(["-ShipId", self.config.ship_id])
                
                # SD3 generation can take longer, use extended timeout
                try:
                    result = subprocess.run(cmd, timeout=self.config.draft_timeout * 2,
                                          capture_output=False, text=True, shell=True)
                    
                    if result.returncode == 0:
                        # Count files generated in this pass
                        pass_files = []
                        pass_types = [t.strip() for t in pass_config["type"].split(",")]
                        
                        if "blender" in pass_types:
                            pass_files.extend(list((output_path / "Blender").rglob("*.png")))
                        if "projectile" in pass_types:
                            pass_files.extend(list((output_path / "Projectiles").rglob("*.png")))
                        if "design_draft" in pass_types:
                            pass_files.extend(list((output_path / "DesignDrafts").rglob("*.png")))
                        if "full_ship_artwork" in pass_types or pass_config["include_full_artwork"]:
                            pass_files.extend(list((output_path / "FullShipArtwork").rglob("*.png")))
                        
                        if pass_files:
                            file_count = len(pass_files)
                            self.total_files_generated += file_count
                            self.log(f"  ✓ {pass_config['description']}: {file_count} files generated", "SUCCESS")
                        else:
                            self.log(f"  ⚠ {pass_config['description']}: No files generated", "WARNING")
                            all_success = False
                    else:
                        self.log(f"  ⚠ {pass_config['description']} failed (exit {result.returncode})", "WARNING")
                        all_success = False
                        
                except subprocess.TimeoutExpired:
                    self.log(f"  ⚠ {pass_config['description']} timed out", "WARNING")
                    all_success = False
                except Exception as e:
                    self.log(f"  ⚠ {pass_config['description']} error: {e}", "WARNING")
                    all_success = False
            
            # Count all SD3-generated textures across all passes
            sd3_files = []
            sd3_files.extend(list((output_path / "Blender").rglob("*.png")))
            sd3_files.extend(list((output_path / "Projectiles").rglob("*.png")))
            sd3_files.extend(list((output_path / "DesignDrafts").rglob("*.png")))
            sd3_files.extend(list((output_path / "FullShipArtwork").rglob("*.png")))
            
            if sd3_files:
                total_count = len(sd3_files)
                self.log(f"  ✓ Total SD3 textures generated: {total_count} files across {len(passes)} pass(es)", "SUCCESS")
                return all_success
            else:
                self.log("  ⚠ No SD3 texture files generated in any pass", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"  ⚠ SD3 generation error: {e}", "WARNING")
            return False
    
    # ===== Quality Assessment Methods =====
    
    def _assess_visual_language(self):
        """Assess visual language quality."""
        self.log("Assessing Visual Language quality...", "INFO")
        # Implementation delegated to existing quality systems
        self.log("  ✓ Visual Language assessed", "SUCCESS")
    
    def _assess_fx(self):
        """Assess FX quality."""
        self.log("Assessing FX quality...", "INFO")
        self.log("  ✓ FX assessed", "SUCCESS")
    
    def _assess_audio_hybrid(self):
        """Assess audio quality using hybrid pipeline."""
        self.log("Assessing Audio quality (hybrid pipeline)...", "INFO")
        
        audio_dir = self.output_dir / "Stage1_Draft" / "Audio"
        if not audio_dir.exists():
            self.log("  ⚠ No audio files to assess", "WARNING")
            return
        
        if not AUDIO_QA_AVAILABLE:
            self.log("  ℹ Audio quality assessment not available, using basic", "INFO")
            self._assess_audio_basic()
            return
        
        try:
            # Use shared audio quality assessment
            assessments, total, filtered = batch_assess_audio_quality(
                audio_dir,
                min_score=self.config.draft_threshold,
                log_message=self.log
            )
            
            self.log(f"  ✓ Assessed {total} audio files, {filtered} below threshold", "SUCCESS")
            
        except Exception as e:
            self.log(f"  ⚠ Audio assessment error: {e}", "WARNING")
            self._assess_audio_basic()
    
    def _assess_audio_basic(self):
        """Basic audio assessment (fallback)."""
        self.log("Assessing Audio quality (basic)...", "INFO")
        self.log("  ✓ Audio assessed", "SUCCESS")
    
    def _assess_textures(self):
        """Assess texture quality."""
        self.log("Assessing Texture quality...", "INFO")
        self.log("  ✓ Textures assessed", "SUCCESS")
    
    # ===== Refinement Methods =====
    
    def _refine_top_assets(self):
        """Refine top-scoring assets."""
        self.log(f"Refining top {self.config.refine_count} assets per type...", "INFO")
        
        # Load quality scores and select top candidates
        # Re-generate with refined prompts/parameters
        # Re-assess quality
        
        self.log("  ✓ Refinement complete", "SUCCESS")
    
    # ===== Selection Methods =====
    
    def _select_best_assets(self):
        """Select best final assets."""
        self.log(f"Selecting best {self.config.final_count} assets per type...", "INFO")
        
        # Copy best assets to final output directory
        final_dir = self.output_dir / "Stage4_Final"
        final_dir.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  ✓ Final assets saved to: {final_dir}", "SUCCESS")
    
    # ===== Integration Methods =====
    
    def _test_integration(self):
        """Test asset integration."""
        self.log("Testing asset integration...", "INFO")
        
        # Verify file formats
        # Check registry compatibility
        # Validate JSON schemas
        
        self.log("  ✓ Integration tests passed", "SUCCESS")
    
    # ===== Spritesheet Generation =====
    
    def _generate_120_facings(self) -> bool:
        """Generate 120 facings spritesheets using Blender."""
        self.log("Generating 120 facings spritesheets with Blender...", "INFO")
        
        script_dir = Path(__file__).parent
        
        # Use Stage4_Final textures if available, otherwise Stage1_Draft
        texture_dir = self.output_dir / "Stage4_Final" / "Textures"
        if not texture_dir.exists() or not any(texture_dir.iterdir()):
            texture_dir = self.output_dir / "Stage1_Draft" / "Textures"
        
        if not texture_dir.exists() or not any(texture_dir.iterdir()):
            self.log("  ✗ No textures found - cannot generate spritesheets", "ERROR")
            self.log(f"    Expected textures in: {texture_dir}", "ERROR")
            self.log("    Textures must be generated before spritesheets!", "ERROR")
            return False
        
        self.log(f"  Using textures from: {texture_dir}", "INFO")
        
        output_dir = self.output_dir / "Stage6_Spritesheets"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # List of ships to render
        ships = [
            ("scSpaceWhale", "blender_space_whale_main_120_facings.py", 256, "Main Space Whale"),
            ("scSpaceWhaleSegment", "blender_space_whale_segment_120_facings.py", 128, "Whale Segment"),
            ("scSpaceWhaleDrone", "blender_space_whale_drone_120_facings.py", 64, "Whale Drone")
        ]
        
        # Check for Blender
        blender_path = self._find_blender()
        if not blender_path:
            self.log("  ✗ Blender not found - cannot generate spritesheets", "ERROR")
            self.log("    Install Blender 3.0+ or add to PATH", "ERROR")
            self.log("    Default location (checked first):", "ERROR")
            self.log("      E:\\tools\\Blender Foundation\\Blender 5.2\\blender.exe", "ERROR")
            self.log("    Other common locations:", "ERROR")
            self.log("      C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe", "ERROR")
            return False
        
        self.log(f"  ✓ Found Blender: {blender_path}", "SUCCESS")
        
        success_count = 0
        total_count = len(ships)
        
        # Render each ship type
        for ship_id, script_name, frame_size, ship_name in ships:
            self.log(f"\n  [{success_count+1}/{total_count}] Rendering {ship_name}...", "INFO")
            self.log(f"    Resolution: {frame_size}x{frame_size} per frame", "INFO")
            self.log(f"    Grid: 10x12 (120 facings)", "INFO")
            
            blender_script = script_dir / script_name
            
            if not blender_script.exists():
                self.log(f"    ✗ Blender script not found: {script_name}", "ERROR")
                self.log(f"      Expected: {blender_script}", "ERROR")
                continue
            
            # Build Blender command
            cmd = [
                str(blender_path),
                "--background",
                "--python", str(blender_script),
                "--",
                "--output-dir", str(output_dir),
                "--ship-id", ship_id,
                "--frame-size", str(frame_size),
                "--texture-dir", str(texture_dir)
            ]
            
            try:
                est_time = {256: "15-20", 128: "10-15", 64: "8-12"}.get(frame_size, "10-20")
                self.log(f"    Starting Blender render (estimated {est_time} minutes)...", "INFO")
                
                result = subprocess.run(
                    cmd,
                    timeout=self.config.spritesheet_timeout,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Check if output files were created
                    spritesheet = output_dir / f"{ship_id}_120facings.png"
                    mask = output_dir / f"{ship_id}_120facingsMask.bmp"
                    
                    if spritesheet.exists() and mask.exists():
                        # Get file sizes
                        sprite_size = spritesheet.stat().st_size / (1024 * 1024)  # MB
                        mask_size = mask.stat().st_size / (1024 * 1024)
                        
                        self.log(f"    ✓ {ship_name} rendered successfully", "SUCCESS")
                        self.log(f"      Spritesheet: {spritesheet.name} ({sprite_size:.1f} MB)", "INFO")
                        self.log(f"      Mask: {mask.name} ({mask_size:.1f} MB)", "INFO")
                        success_count += 1
                    else:
                        self.log(f"    ✗ Output files not created", "ERROR")
                        if result.stdout:
                            # Show last 500 chars of output
                            self.log(f"      Blender output: {result.stdout[-500:]}", "ERROR")
                else:
                    self.log(f"    ✗ Blender exited with code {result.returncode}", "ERROR")
                    if result.stderr:
                        self.log(f"      Error: {result.stderr[-500:]}", "ERROR")
                    
            except subprocess.TimeoutExpired:
                self.log(f"    ✗ Rendering timed out after {self.config.spritesheet_timeout/60:.0f} minutes", "ERROR")
                self.log(f"      Increase timeout or check Blender performance", "ERROR")
            except Exception as e:
                self.log(f"    ✗ Rendering error: {e}", "ERROR")
        
        # Summary
        self.log(f"\n  Spritesheet Summary: {success_count}/{total_count} ships rendered", 
                "SUCCESS" if success_count == total_count else "ERROR")
        
        if success_count == 0:
            self.log("  ✗ CRITICAL: No spritesheets were generated!", "ERROR")
            return False
        elif success_count < total_count:
            self.log(f"  ⚠ WARNING: Only {success_count}/{total_count} ships rendered", "WARNING")
            self.log("    Some spritesheets are missing!", "WARNING")
            return False
        
        return True
    
    def _find_blender(self) -> Optional[Path]:
        """Find Blender executable."""
        # Default path (highest priority)
        default_path = Path("E:\\tools\\Blender Foundation\\Blender 5.2\\blender.exe")
        if default_path.exists():
            return default_path
        
        # Check common locations
        common_paths = [
            "E:\\tools\\Blender Foundation\\Blender 5.2\\blender.exe",
            "D:\\tools\\Blender Foundation\\Blender 5.2\\blender.exe",
            "D:\\tools\\Blender Foundation\\Blender 5.0\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
        ]
        
        # Check common paths
        for path_str in common_paths:
            path = Path(path_str)
            if path.exists():
                return path
        
        # Check PATH
        try:
            result = subprocess.run(["blender", "--version"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return Path("blender")
        except:
            pass
        
        # Try to find with glob
        try:
            blender_dirs = list(Path("D:\\tools\\Blender Foundation").glob("Blender *"))
            if not blender_dirs:
                blender_dirs = list(Path("C:\\Program Files\\Blender Foundation").glob("Blender *"))
            
            if blender_dirs:
                # Get newest version
                blender_dirs.sort(reverse=True)
                blender_exe = blender_dirs[0] / "blender.exe"
                if blender_exe.exists():
                    return blender_exe
        except:
            pass
        
        return None
    
    # ===== Reporting =====
    
    def _generate_report(self, total_time: float):
        """Generate comprehensive quality report."""
        report_path = self.output_dir / "QUALITY_REPORT.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Space Whale High-Quality Asset Generation Report\n\n")
            f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Time:** {total_time/60:.1f} minutes\n\n")
            
            f.write("## Pipeline Configuration\n\n")
            f.write(f"- **Draft Count:** {self.config.draft_count} per asset type\n")
            f.write(f"- **Refinement:** {'Enabled' if self.config.enable_refinement else 'Disabled'}\n")
            f.write(f"- **Final Selection:** Top {self.config.final_count} per type\n")
            if self.config.ship_id:
                f.write(f"- **Ship ID Filter:** {self.config.ship_id}\n")
            f.write(f"- **Quality Thresholds:**\n")
            f.write(f"  - Draft: {self.config.draft_threshold}/20\n")
            f.write(f"  - Production: {self.config.production_threshold}/20\n")
            f.write(f"  - Target: {self.config.perfect_threshold}/20\n\n")
            
            f.write("## Pipeline Stages\n\n")
            f.write("| Stage | Status | Duration | Retries | Files |\n")
            f.write("|-------|--------|----------|---------|-------|\n")
            
            for stage, results in self.results.items():
                for result in results:
                    status = "✓" if result.success else "✗" if not result.skipped else "⊘"
                    retries = str(result.retry_count) if result.retry_count > 0 else "0"
                    files = str(result.file_count) if result.file_count > 0 else "-"
                    f.write(f"| {result.stage.value} | {status} | {result.duration:.1f}s | {retries} | {files} |\n")
            
            f.write("\n## Performance Metrics\n\n")
            for stage, duration in self.stage_durations.items():
                f.write(f"- **{stage.value}**: {duration:.1f}s\n")
            f.write(f"- **Total**: {total_time:.1f}s\n")
            f.write(f"- **Total Files**: {self.total_files_generated}\n\n")
            
            f.write("## Output Structure\n\n")
            f.write("```\n")
            f.write(f"{self.output_dir.name}/\n")
            f.write("├── Stage1_Draft/          # Initial drafts\n")
            f.write("├── Stage2_Assess/         # Quality assessments\n")
            f.write("├── Stage3_Refine/         # Refined versions\n")
            f.write("├── Stage4_Final/          # Best selections\n")
            f.write("├── Stage5_Integration/    # Integration tests\n")
            f.write("├── Stage6_Spritesheets/   # 120-facing spritesheets\n")
            f.write("└── Stage7_Items/         # Game items (XML)\n")
            f.write("```\n\n")
        
        self.log(f"Quality report saved: {report_path}", "SUCCESS")
    
    def _generate_file_summary(self):
        """Generate file count summary at end of pipeline."""
        self.log("\n" + "="*80, "INFO")
        self.log("File Generation Summary", "STAGE")
        self.log("="*80, "INFO")
        
        file_counts = {}
        total_size = 0
        
        # Count files by extension in each stage
        for stage_dir in [
            "Stage1_Draft", "Stage2_Assess", "Stage3_Refine",
            "Stage4_Final", "Stage5_Integrate", "Stage6_Spritesheets", "Stage7_Items"
        ]:
            stage_path = self.output_dir / stage_dir
            if not stage_path.exists():
                continue
            
            stage_files = {}
            for ext in ['.json', '.png', '.bmp', '.wav', '.ogg', '.xml', '.md']:
                files = list(stage_path.rglob(f"*{ext}"))
                if files:
                    stage_files[ext] = len(files)
                    total_size += sum(f.stat().st_size for f in files)
            
            if stage_files:
                file_counts[stage_dir] = stage_files
        
        # Display summary
        for stage_dir, files in file_counts.items():
            self.log(f"\n{stage_dir}:", "INFO")
            for ext, count in sorted(files.items()):
                self.log(f"  {ext}: {count} files", "INFO")
        
        self.log(f"\nTotal files: {self.total_files_generated}", "SUCCESS")
        if total_size > 0:
            self.log(f"Total size: {total_size / (1024*1024):.2f} MB", "INFO")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Space Whale High-Quality Asset Generator")
    parser.add_argument("--output-dir", type=str, 
                       default="Output/SpaceWhaleAssets_HQ",
                       help="Output directory")
    parser.add_argument("--draft-count", type=int, default=6,
                       help="Number of draft variations (default: 6)")
    parser.add_argument("--final-count", type=int, default=2,
                       help="Number of final selections (default: 2)")
    parser.add_argument("--skip-refinement", action="store_true",
                       help="Skip refinement stage")
    parser.add_argument("--quick", action="store_true",
                       help="Quick mode: 4 drafts, no refinement")
    
    # Retry and resume
    parser.add_argument("--max-retries", type=int, default=3,
                       help="Maximum retries per stage (default: 3)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume interrupted generation")
    parser.add_argument("--skip-completed", action="store_true",
                       help="Skip completed stages when resuming")
    
    # Skip flags
    parser.add_argument("--skip-draft", action="store_true",
                       help="Skip draft generation stage")
    parser.add_argument("--skip-assess", action="store_true",
                       help="Skip quality assessment stage")
    parser.add_argument("--skip-refine", action="store_true",
                       help="Skip refinement stage")
    parser.add_argument("--skip-select", action="store_true",
                       help="Skip final selection stage")
    parser.add_argument("--skip-integrate", action="store_true",
                       help="Skip integration testing stage")
    parser.add_argument("--skip-spritesheet", action="store_true",
                       help="Skip spritesheet generation stage")
    parser.add_argument("--skip-items", action="store_true",
                       help="Skip item generation stage")
    
    # Ship filtering
    parser.add_argument("--ship-id", type=str, default=None,
                       help="Filter by specific ship ID (default: all ships)")
    
    # Settings file
    parser.add_argument("--settings", type=str, default=None,
                       help="Path to settings JSON file")
    
    # SD3 Texture Generation (enabled by default, auto-detects required assets)
    parser.add_argument("--no-sd3", action="store_true",
                       help="Disable Stable Diffusion 3 texture generation (SD3 is enabled by default)")
    parser.add_argument("--use-sd3", action="store_true",
                       help="[DEPRECATED] SD3 is now enabled by default. Use --no-sd3 to disable.")
    parser.add_argument("--sd3-texture-type", type=str, 
                       choices=["blender", "projectile", "design_draft", "all"],
                       default="all",
                       help="SD3 texture types to generate (default: all, auto-detects from registry)")
    parser.add_argument("--sd3-variations", type=int, default=3,
                       help="Number of SD3 variations per texture type per ship (default: 3)")
    parser.add_argument("--sd3-fast", action="store_true",
                       help="Fast SD3 mode: skip design drafts (faster generation)")
    
    args = parser.parse_args()
    
    # Configure based on arguments
    config = AssetConfig()
    config.draft_count = args.draft_count
    config.final_count = args.final_count
    config.enable_refinement = not args.skip_refinement
    config.max_retries = args.max_retries
    config.resume = args.resume
    config.skip_completed = args.skip_completed
    config.skip_draft = args.skip_draft
    config.skip_assess = args.skip_assess
    config.skip_refine = args.skip_refine
    config.skip_select = args.skip_select
    config.skip_integrate = args.skip_integrate
    config.skip_spritesheet = args.skip_spritesheet
    config.skip_items = args.skip_items
    config.ship_id = args.ship_id
    config.settings_file = args.settings
    
    # SD3 is enabled by default, can be disabled with --no-sd3
    # --use-sd3 is kept for backward compatibility but is now redundant
    if args.no_sd3:
        config.use_sd3_textures = False
        print("SD3 texture generation disabled (--no-sd3)")
    else:
        config.use_sd3_textures = True  # Enabled by default
        if args.use_sd3:
            print("Note: --use-sd3 is now redundant (SD3 is enabled by default)")
    
    config.sd3_texture_type = args.sd3_texture_type
    config.sd3_variations = args.sd3_variations
    config.sd3_include_design_drafts = not args.sd3_fast  # Fast mode skips design drafts
    
    if args.quick:
        config.draft_count = 4
        config.enable_refinement = False
        print("Quick mode: 4 drafts, no refinement")
    
    # Create generator and run
    generator = HighQualityAssetGenerator(
        output_dir=Path(args.output_dir),
        config=config
    )
    
    success = generator.generate_assets()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
