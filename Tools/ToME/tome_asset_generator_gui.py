#!/usr/bin/env python3
"""
ToME Asset Generator GUI with Progress Indicators
Graphical interface for generating assets with real-time progress tracking.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
from typing import Optional, List
import json
import os
import sys
import shutil

# Try to import tkinterdnd2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("Warning: tkinterdnd2 not available. Install with: pip install tkinterdnd2")

# Import generators
from tome_asset_generator_ai import AIEnhancedToMEGenerator
from tome_asset_generator import AssetType, ShapeModule
from tome_asset_generator_extended import ExtendedAssetType


class AssetGeneratorGUI:
    """GUI for ToME asset generation with progress tracking."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ToME Asset Generator")
        self.root.geometry("1000x700")
        
        self.generator: Optional[AIEnhancedToMEGenerator] = None
        self.is_generating = False
        self.generation_thread: Optional[threading.Thread] = None
        
        # Mod configurations
        self.mod_configs = {
            'smog-devil-class': {
                'name': 'Smog Devil Class',
                'path': r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class",
                'talents_json': 'smog_devil_talents.json',
                'output_dir': r"d:\games\Steam\steamapps\common\Transcendence\Tools\Output\SmogDevilAssets"
            },
            'glutton-remade': {
                'name': 'Glutton Remade',
                'path': r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade",
                'talents_json': 'glutton_remade_talents.json',
                'output_dir': r"d:\games\Steam\steamapps\common\Transcendence\Tools\Output\GluttonRemadeAssets"
            }
        }
        
        self._create_ui()
        self._setup_drag_drop()
    
    def _create_ui(self):
        """Create the UI."""
        # Top frame - Configuration
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Mod selector
        mod_frame = ttk.Frame(config_frame)
        mod_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mod_frame, text="Mod:").pack(side=tk.LEFT, padx=5)
        self.mod_selector_var = tk.StringVar(value='smog-devil-class')
        mod_selector = ttk.Combobox(mod_frame, textvariable=self.mod_selector_var, 
                                    values=list(self.mod_configs.keys()), state='readonly', width=20)
        mod_selector.pack(side=tk.LEFT, padx=5)
        mod_selector.bind('<<ComboboxSelected>>', self._on_mod_selected)
        
        # Mod path
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="Mod Path:").pack(side=tk.LEFT, padx=5)
        self.mod_path_var = tk.StringVar(value=self.mod_configs['smog-devil-class']['path'])
        self.mod_path_entry = ttk.Entry(path_frame, textvariable=self.mod_path_var, width=60)
        self.mod_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self._browse_mod).pack(side=tk.LEFT, padx=5)
        
        # Output path
        output_frame = ttk.Frame(config_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Output Path:").pack(side=tk.LEFT, padx=5)
        self.output_path_var = tk.StringVar(value=self.mod_configs['smog-devil-class']['output_dir'])
        self.output_path_entry = ttk.Entry(output_frame, textvariable=self.output_path_var, width=60)
        self.output_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", command=self._browse_output).pack(side=tk.LEFT, padx=5)
        
        # AI settings
        ai_frame = ttk.Frame(config_frame)
        ai_frame.pack(fill=tk.X, pady=5)
        
        self.use_ai_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ai_frame, text="Use AI Enhancement", variable=self.use_ai_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(ai_frame, text="Variations per asset:").pack(side=tk.LEFT, padx=5)
        self.variations_var = tk.IntVar(value=20)
        variations_spin = ttk.Spinbox(ai_frame, from_=1, to=100, textvariable=self.variations_var, width=10)
        variations_spin.pack(side=tk.LEFT, padx=5)
        
        # Asset selection
        assets_frame = ttk.LabelFrame(self.root, text="Assets to Generate", padding="10")
        assets_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(assets_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main assets tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main Assets")
        
        # Asset checkboxes
        self.asset_vars = {}
        assets_config = [
            ('steam_staff', 'Steam Staff (Weapon)', AssetType.ITEM),
            ('steam_overload', 'Steam Overload (Effect)', AssetType.VFX),
            ('steam_mana_converter', 'Steam Mana Converter (Effect)', AssetType.VFX),
            ('steam_mana_symphony', 'Steam Mana Symphony (Effect)', AssetType.VFX),
            ('smog_devil_apotheosis', 'Smog Devil Apotheosis (Effect)', AssetType.VFX),
        ]
        
        for i, (key, label, asset_type) in enumerate(assets_config):
            var = tk.BooleanVar(value=True)
            self.asset_vars[key] = {'var': var, 'type': asset_type, 'label': label}
            ttk.Checkbutton(main_tab, text=label, variable=var).grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=5)
        
        # Talents tab
        talents_tab = ttk.Frame(notebook)
        notebook.add(talents_tab, text="Talent Icons")
        
        # Load talents (will be populated by _load_talents)
        self.talents_tab = talents_tab
        self.talent_vars = {}
        self._load_talents()
        
        # Progress frame
        progress_frame = ttk.LabelFrame(self.root, text="Generation Progress", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Overall progress
        self.overall_label = ttk.Label(progress_frame, text="Ready to generate", font=("Arial", 10, "bold"))
        self.overall_label.pack(anchor=tk.W, pady=5)
        
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.overall_progress.pack(fill=tk.X, pady=5)
        
        # Current asset progress
        self.current_label = ttk.Label(progress_frame, text="")
        self.current_label.pack(anchor=tk.W, pady=5)
        
        self.current_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.current_progress.pack(fill=tk.X, pady=5)
        
        # Log area
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(log_frame, text="Generation Log:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Assets", command=self._start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop", command=self._stop_generation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Manifest", command=self._export_manifest).pack(side=tk.LEFT, padx=5)
        
        # Cleanup options
        cleanup_frame = ttk.LabelFrame(self.root, text="Cleanup Options", padding="10")
        cleanup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.remove_old_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cleanup_frame, text="Remove old/lower quality assets after generation", variable=self.remove_old_var).pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_drag_drop(self):
        """Setup drag and drop."""
        if not DND_AVAILABLE:
            return
        
        try:
            self.mod_path_entry.drop_target_register(DND_FILES)
            self.mod_path_entry.dnd_bind('<<Drop>>', self._on_drop_mod)
        except:
            pass
    
    def _on_drop_mod(self, event):
        """Handle mod path drop."""
        if not DND_AVAILABLE:
            return
        
        try:
            files = self.root.tk.splitlist(event.data)
            if files:
                path = Path(files[0])
                if path.is_dir():
                    self.mod_path_var.set(str(path))
        except:
            pass
    
    def _browse_mod(self):
        """Browse for mod directory."""
        path = filedialog.askdirectory(title="Select ToME Mod Directory")
        if path:
            self.mod_path_var.set(path)
    
    def _browse_output(self):
        """Browse for output directory."""
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path_var.set(path)
    
    def _on_mod_selected(self, event=None):
        """Handle mod selection change."""
        mod_key = self.mod_selector_var.get()
        if mod_key in self.mod_configs:
            config = self.mod_configs[mod_key]
            self.mod_path_var.set(config['path'])
            self.output_path_var.set(config['output_dir'])
            self.root.title(f"ToME Asset Generator - {config['name']}")
            # Reload talents
            self._load_talents()
    
    def _load_talents(self):
        """Load talents for the selected mod."""
        # Clear existing talent widgets
        for widget in self.talents_tab.winfo_children():
            widget.destroy()
        
        self.talent_vars = {}
        
        # Get current mod config
        mod_key = self.mod_selector_var.get()
        if mod_key not in self.mod_configs:
            ttk.Label(self.talents_tab, text="Invalid mod selection.").pack(padx=10, pady=10)
            return
        
        talents_json = Path(__file__).parent / self.mod_configs[mod_key]['talents_json']
        
        if talents_json.exists():
            import json
            with open(talents_json, 'r', encoding='utf-8') as f:
                talents_data = json.load(f)
            
            # Create scrollable frame for talents
            canvas = tk.Canvas(self.talents_tab)
            scrollbar = ttk.Scrollbar(self.talents_tab, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Select all checkbox
            select_all_var = tk.BooleanVar(value=True)
            def toggle_all():
                state = select_all_var.get()
                for var in self.talent_vars.values():
                    var['var'].set(state)
            
            ttk.Checkbutton(scrollable_frame, text="Select All Talents", variable=select_all_var, command=toggle_all).pack(anchor=tk.W, padx=5, pady=5)
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
            
            # Talent checkboxes
            for i, talent in enumerate(talents_data):
                var = tk.BooleanVar(value=True)
                talent_id = talent['id']
                talent_name = talent['name']
                self.talent_vars[talent_id] = {'var': var, 'name': talent_name, 'id': talent_id}
                ttk.Checkbutton(
                    scrollable_frame,
                    text=f"{talent_id}: {talent_name}",
                    variable=var
                ).pack(anchor=tk.W, padx=10, pady=2)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            ttk.Label(self.talents_tab, text=f"Talent list not found: {talents_json}\nRun extract_talents.py or extract_glutton_talents.py first.").pack(padx=10, pady=10)
    
    def _log(self, message: str):
        """Add message to log."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def _clear_log(self):
        """Clear the log."""
        self.log_text.delete(1.0, tk.END)
    
    def _start_generation(self):
        """Start asset generation."""
        if self.is_generating:
            messagebox.showwarning("Already Generating", "Generation is already in progress.")
            return
        
        mod_path = self.mod_path_var.get()
        output_path = self.output_path_var.get()
        
        if not mod_path:
            messagebox.showerror("Error", "Please specify a mod path.")
            return
        
        if not output_path:
            messagebox.showerror("Error", "Please specify an output path.")
            return
        
        # Check selected assets
        selected_assets = [k for k, v in self.asset_vars.items() if v['var'].get()]
        if not selected_assets:
            messagebox.showerror("Error", "Please select at least one asset type to generate.")
            return
        
        self.is_generating = True
        self.generate_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Start generation in thread
        self.generation_thread = threading.Thread(
            target=self._generate_assets_thread,
            args=(mod_path, output_path, selected_assets),
            daemon=True
        )
        self.generation_thread.start()
    
    def _stop_generation(self):
        """Stop asset generation."""
        if not self.is_generating:
            return
        
        self.is_generating = False
        self.status_var.set("Stopping...")
        # Note: Generation will stop at next check
    
    def _generate_assets_thread(self, mod_path: str, output_path: str, selected_assets: List[str]):
        """Generate assets in background thread."""
        try:
            self.root.after(0, self._log, "=" * 60)
            self.root.after(0, self._log, "Starting asset generation...")
            self.root.after(0, self._log, f"Mod path: {mod_path}")
            self.root.after(0, self._log, f"Output path: {output_path}")
            self.root.after(0, self._log, f"Variations per asset: {self.variations_var.get()}")
            self.root.after(0, self._log, "=" * 60)
            self.root.after(0, self._log, "")
            
            # Initialize generator
            self.root.after(0, self._log, "Initializing generator...")
            generator = AIEnhancedToMEGenerator(
                output_dir=output_path,
                mod_name="smog_devil_assets",
                mod_author="ToME Asset Generator",
                mod_version="1.0.0",
                use_ai=self.use_ai_var.get()
            )
            
            if generator.use_ai:
                self.root.after(0, self._log, f"AI Models: Code={generator.code_model}, Visual={generator.visual_model}")
            else:
                self.root.after(0, self._log, "AI: Disabled (using fallback)")
            
            self.root.after(0, self._log, "")
            
            # Asset definitions
            asset_defs = {
                'steam_staff': {
                    'type': AssetType.ITEM,
                    'shapes': [],
                    'output_dir': 'objects',
                    'filename_pattern': 'steam_staff_{:02d}.png'
                },
                'steam_overload': {
                    'type': AssetType.VFX,
                    'shapes': [ShapeModule.NOVA, ShapeModule.SPIRAL],
                    'output_dir': 'effects',
                    'filename_pattern': 'steam_overload_{:02d}.png'
                },
                'steam_mana_converter': {
                    'type': AssetType.VFX,
                    'shapes': [ShapeModule.RING, ShapeModule.SPIRAL],
                    'output_dir': 'effects',
                    'filename_pattern': 'steam_mana_converter_{:02d}.png'
                },
                'steam_mana_symphony': {
                    'type': AssetType.VFX,
                    'shapes': [ShapeModule.RING, ShapeModule.CLOUD],
                    'output_dir': 'effects',
                    'filename_pattern': 'steam_mana_symphony_{:02d}.png'
                },
                'smog_devil_apotheosis': {
                    'type': AssetType.VFX,
                    'shapes': [ShapeModule.NOVA, ShapeModule.SPIRAL],
                    'output_dir': 'effects',
                    'filename_pattern': 'smog_devil_apotheosis_{:02d}.png'
                },
            }
            
            # Load talents if available
            talents_data = []
            mod_key = self.mod_selector_var.get()
            if mod_key in self.mod_configs:
                talents_json = Path(__file__).parent / self.mod_configs[mod_key]['talents_json']
                if talents_json.exists():
                    import json
                    with open(talents_json, 'r', encoding='utf-8') as f:
                        talents_data = json.load(f)
            
            # Get selected talents
            selected_talents = []
            for t in talents_data:
                talent_id = t['id']
                if talent_id in self.talent_vars:
                    if self.talent_vars[talent_id]['var'].get():
                        selected_talents.append(t)
            
            # Calculate total assets
            main_assets = len(selected_assets) * self.variations_var.get()
            talent_assets = len(selected_talents) * self.variations_var.get()
            total_assets = main_assets + talent_assets
            total_generated = 0
            
            self.root.after(0, lambda: self.overall_progress.config(maximum=total_assets, value=0))
            self.root.after(0, lambda: self.overall_label.config(text=f"Overall Progress: 0 / {total_assets}"))
            
            # Generate each asset type
            seed_base = 10000
            all_generated = []
            
            for asset_key in selected_assets:
                if not self.is_generating:
                    break
                
                asset_def = asset_defs[asset_key]
                asset_label = self.asset_vars[asset_key]['label']
                variations = self.variations_var.get()
                
                self.root.after(0, self._log, f"Generating {asset_label} ({variations} variations)...")
                current_asset_label = asset_label
                current_variations = variations
                self.root.after(0, lambda al=current_asset_label: self.current_label.config(text=f"Current: {al}"))
                self.root.after(0, lambda v=current_variations: self.current_progress.config(maximum=v, value=0))
                
                asset_list = []
                
                for i in range(variations):
                    if not self.is_generating:
                        break
                    
                    seed = seed_base + i
                    variant = f"{asset_key}_{i:02d}"
                    
                    try:
                        # Update current progress (capture values in closure)
                        current_i = i + 1
                        current_variations = variations
                        self.root.after(0, lambda vi=current_i: self.current_progress.config(value=vi))
                        self.root.after(0, lambda vi=current_i, tv=current_variations: self.current_label.config(
                            text=f"Current: {asset_label} - {vi}/{tv}"
                        ))
                        
                        # Generate asset
                        asset = generator.generate(
                            template=asset_def['type'],
                            shapes=asset_def.get('shapes', []),
                            seed=seed,
                            variant=variant
                        )
                        
                        asset_list.append({
                            'asset': asset,
                            'seed': seed,
                            'variant': variant,
                            'output_dir': asset_def['output_dir'],
                            'filename': asset_def['filename_pattern'].format(i)
                        })
                        
                        total_generated += 1
                        # Capture values for lambda
                        current_total = total_generated
                        current_max = total_assets
                        self.root.after(0, lambda vt=current_total: self.overall_progress.config(value=vt))
                        self.root.after(0, lambda vt=current_total, tm=current_max: self.overall_label.config(
                            text=f"Overall Progress: {vt} / {tm}"
                        ))
                        
                        self.root.after(0, self._log, f"  [{i+1:2d}/{variations}] {asset['id']} (balance: {asset['balance']['total_score']:.2f})")
                        
                    except Exception as e:
                        self.root.after(0, self._log, f"  [ERROR] Failed to generate {variant}: {e}")
                        continue
                
                all_generated.append({
                    'name': asset_key,
                    'assets': asset_list,
                    'output_dir': asset_def['output_dir']
                })
                
                seed_base += 1000
                self.root.after(0, self._log, "")
            
            # Generate talent icons
            if selected_talents and self.is_generating:
                self.root.after(0, self._log, "Generating talent icons...")
                self.root.after(0, self._log, "-" * 60)
                
                talent_seed_base = 30000
                talent_assets_list = []
                
                # Determine theme based on talent name/ID and mod
                def get_talent_theme(talent_id, talent_name, mod_key):
                    id_lower = talent_id.lower()
                    name_lower = talent_name.lower()
                    
                    # Glutton-specific themes
                    if mod_key == 'glutton-remade':
                        if 'bile' in id_lower or 'bile' in name_lower or 'acid' in id_lower or 'acid' in name_lower:
                            return 'acid'
                        elif 'digest' in id_lower or 'consume' in id_lower or 'devour' in id_lower or 'maw' in id_lower:
                            return 'dark'
                        elif 'corrupt' in id_lower or 'void' in id_lower or 'horror' in id_lower:
                            return 'dark'
                        elif 'lightning' in id_lower or 'thunder' in id_lower:
                            return 'lightning'
                        elif 'fire' in id_lower or 'flame' in id_lower or 'inferno' in id_lower:
                            return 'fire'
                        elif 'ice' in id_lower or 'frost' in id_lower or 'cold' in id_lower:
                            return 'ice'
                        elif 'heal' in id_lower or 'regeneration' in id_lower:
                            return 'healing'
                        elif 'summon' in id_lower or 'tentacle' in id_lower:
                            return 'dark'
                        else:
                            return 'dark'  # Default for glutton
                    
                    # Smog Devil themes
                    else:
                        if 'steam' in id_lower or 'steam' in name_lower:
                            return 'steam'
                        elif 'arcane' in id_lower or 'mana' in id_lower or 'arcane' in name_lower:
                            return 'arcane'
                        elif 'corrupt' in id_lower or 'demon' in id_lower or 'hell' in id_lower or 'soul' in id_lower:
                            return 'dark'
                        elif 'vim' in id_lower:
                            return 'dark'
                        else:
                            return 'steam'  # Default
                
                for talent_idx, talent in enumerate(selected_talents):
                    if not self.is_generating:
                        break
                    
                    talent_id = talent['id']
                    talent_name = talent['name']
                    mod_key = self.mod_selector_var.get()
                    theme = get_talent_theme(talent_id, talent_name, mod_key)
                    
                    self.root.after(0, self._log, f"Generating {talent_name} ({self.variations_var.get()} variations)...")
                    current_talent_name = talent_name
                    current_talent_variations = self.variations_var.get()
                    self.root.after(0, lambda tn=current_talent_name: self.current_label.config(text=f"Current: {tn}"))
                    self.root.after(0, lambda v=current_talent_variations: self.current_progress.config(maximum=v, value=0))
                    
                    talent_icon_list = []
                    
                    for i in range(self.variations_var.get()):
                        if not self.is_generating:
                            break
                        
                        seed = talent_seed_base + (talent_idx * 1000) + i
                        variant = f"{talent_id}_{i:02d}"
                        
                        try:
                            # Update progress
                            current_i = i + 1
                            current_variations = self.variations_var.get()
                            self.root.after(0, lambda vi=current_i: self.current_progress.config(value=vi))
                            self.root.after(0, lambda vi=current_i, tv=current_variations, tn=current_talent_name: self.current_label.config(
                                text=f"Current: {tn} - {vi}/{tv}"
                            ))
                            
                            # Generate talent icon (as spell/icon)
                            asset = generator.generate(
                                template=AssetType.SPELL,
                                shapes=[ShapeModule.RING],
                                seed=seed,
                                variant=variant
                            )
                            
                            talent_icon_list.append({
                                'asset': asset,
                                'talent_id': talent_id,
                                'talent_name': talent_name,
                                'seed': seed,
                                'variant': variant
                            })
                            
                            total_generated += 1
                            current_total = total_generated
                            current_max = total_assets
                            self.root.after(0, lambda vt=current_total: self.overall_progress.config(value=vt))
                            self.root.after(0, lambda vt=current_total, tm=current_max: self.overall_label.config(
                                text=f"Overall Progress: {vt} / {tm}"
                            ))
                            
                            self.root.after(0, self._log, f"  [{i+1:2d}/{self.variations_var.get()}] {talent_id} (balance: {asset['balance']['total_score']:.2f})")
                            
                        except Exception as e:
                            self.root.after(0, self._log, f"  [ERROR] Failed to generate {variant}: {e}")
                            continue
                    
                    talent_assets_list.append({
                        'talent_id': talent_id,
                        'talent_name': talent_name,
                        'icons': talent_icon_list
                    })
                    
                    self.root.after(0, self._log, "")
                
                # Copy talent icons to mod
                if talent_assets_list:
                    mod_talents_gfx = Path(mod_path) / "data" / "gfx" / "talents"
                    mod_talents_gfx.mkdir(parents=True, exist_ok=True)
                    
                    self.root.after(0, self._log, "Copying talent icons to mod directory...")
                    self.root.after(0, self._log, "-" * 60)
                    
                    talent_files_to_keep = set()
                    talent_copied = 0
                    
                    for talent_group in talent_assets_list:
                        talent_id = talent_group['talent_id']
                        talent_name = talent_group['talent_name']
                        
                        if not talent_group['icons']:
                            continue
                        
                        # Use the best variation (highest balance score) as the main icon
                        best_icon = max(talent_group['icons'], key=lambda x: x['asset']['balance']['total_score'])
                        asset = best_icon['asset']
                        source_sprite = generator.mod_path / asset['sprite']
                        
                        # Use talent ID as filename (ToME convention: lowercase talent ID)
                        target_file = mod_talents_gfx / f"{talent_id.lower()}.png"
                        
                        self.root.after(0, self._log, f"  Copying {talent_name} ({talent_id})...")
                        
                        if source_sprite.exists():
                            shutil.copy2(source_sprite, target_file)
                            
                            # Copy metadata
                            meta_source = source_sprite.with_suffix('.meta.json')
                            if meta_source.exists():
                                meta_target = target_file.with_suffix('.meta.json')
                                shutil.copy2(meta_source, meta_target)
                                talent_files_to_keep.add(meta_target.name)
                            
                            talent_files_to_keep.add(target_file.name)
                            talent_copied += 1
                            self.root.after(0, self._log, f"    -> {target_file.name} (balance: {asset['balance']['total_score']:.2f})")
                        else:
                            self.root.after(0, self._log, f"    [ERROR] Source sprite not found: {source_sprite}")
                    
                    if talent_copied > 0:
                        self.root.after(0, self._log, f"Copied {talent_copied} talent icon files")
                    else:
                        self.root.after(0, self._log, "No talent icons copied")
                    
                    # Remove old talent icons if requested
                    if self.remove_old_var.get():
                        removed_talent_count = 0
                        for old_file in mod_talents_gfx.glob("*.png"):
                            # Only remove if it matches a talent ID we generated
                            file_stem = old_file.stem.lower()
                            if old_file.name not in talent_files_to_keep:
                                # Check if it's a talent we're generating
                                for talent_group in talent_assets_list:
                                    talent_id_lower = talent_group['talent_id'].lower()
                                    if file_stem.startswith(talent_id_lower):
                                        try:
                                            old_file.unlink()
                                            meta_file = old_file.with_suffix('.meta.json')
                                            if meta_file.exists():
                                                meta_file.unlink()
                                            removed_talent_count += 1
                                            self.root.after(0, self._log, f"  Removed old: {old_file.name}")
                                        except Exception as e:
                                            self.root.after(0, self._log, f"  [ERROR] Failed to remove {old_file.name}: {e}")
                        
                        if removed_talent_count > 0:
                            self.root.after(0, self._log, f"Removed {removed_talent_count} old talent icon files")
            
            if not self.is_generating:
                self.root.after(0, self._log, "Generation stopped by user.")
                self.root.after(0, lambda: self.status_var.set("Stopped"))
            else:
                # Copy assets to mod directory
                self.root.after(0, self._log, "Copying assets to mod directory...")
                self.root.after(0, self._log, "-" * 60)
                
                mod_gfx = Path(mod_path) / "data" / "gfx"
                mod_gfx.mkdir(parents=True, exist_ok=True)
                
                # Track which files we're keeping
                files_to_keep = set()
                
                copied_count = 0
                talent_copied = 0  # Initialize for case where no talents are selected
                for asset_group in all_generated:
                    target_dir = mod_gfx / asset_group['output_dir']
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.root.after(0, self._log, f"  Copying {asset_group['name']} to {target_dir}...")
                    
                    for item in asset_group['assets']:
                        asset = item['asset']
                        source_sprite = generator.mod_path / asset['sprite']
                        target_file = target_dir / item['filename']
                        
                        if source_sprite.exists():
                            shutil.copy2(source_sprite, target_file)
                            
                            # Copy metadata if exists
                            meta_source = source_sprite.with_suffix('.meta.json')
                            if meta_source.exists():
                                meta_target = target_file.with_suffix('.meta.json')
                                shutil.copy2(meta_source, meta_target)
                                files_to_keep.add(meta_target.name)
                            
                            files_to_keep.add(target_file.name)
                            copied_count += 1
                            self.root.after(0, self._log, f"    -> {target_file.name}")
                
                # Remove old assets if requested
                if self.remove_old_var.get():
                    self.root.after(0, self._log, "")
                    self.root.after(0, self._log, "Removing old/lower quality assets...")
                    self.root.after(0, self._log, "-" * 60)
                    
                    removed_count = 0
                    for asset_group in all_generated:
                        target_dir = mod_gfx / asset_group['output_dir']
                        if not target_dir.exists():
                            continue
                        
                        # Find old assets (not in our keep list)
                        asset_name_base = asset_group['name']
                        for old_file in target_dir.glob(f"{asset_name_base}*.png"):
                            if old_file.name not in files_to_keep:
                                try:
                                    old_file.unlink()
                                    # Remove metadata if exists
                                    meta_file = old_file.with_suffix('.meta.json')
                                    if meta_file.exists():
                                        meta_file.unlink()
                                    removed_count += 1
                                    self.root.after(0, self._log, f"  Removed: {old_file.name}")
                                except Exception as e:
                                    self.root.after(0, self._log, f"  [ERROR] Failed to remove {old_file.name}: {e}")
                    
                    self.root.after(0, self._log, f"Removed {removed_count} old asset files")
                
                # Generate manifest
                manifest_path = generator.generate_extended_manifest()
                
                self.root.after(0, self._log, "")
                self.root.after(0, self._log, "=" * 60)
                self.root.after(0, self._log, "Generation Complete!")
                self.root.after(0, self._log, "=" * 60)
                self.root.after(0, self._log, f"Generated: {total_generated} assets")
                self.root.after(0, self._log, f"  Main assets: {copied_count} files")
                if talent_copied > 0:
                    self.root.after(0, self._log, f"  Talent icons: {talent_copied} files")
                self.root.after(0, self._log, f"Total copied: {copied_count + talent_copied} files to mod")
                self.root.after(0, self._log, f"Manifest: {manifest_path}")
                
                total_copied = copied_count + talent_copied
                self.root.after(0, lambda: self.status_var.set(f"Complete: {total_generated} assets generated, {total_copied} files copied"))
                self.root.after(0, lambda tc=total_copied, tg=total_generated: messagebox.showinfo("Complete", f"Generated {tg} assets and copied {tc} files to mod directory."))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {e}"))
            self.root.after(0, self._log, f"ERROR: {e}")
            import traceback
            self.root.after(0, self._log, traceback.format_exc())
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.current_label.config(text=""))
            self.root.after(0, lambda: self.current_progress.config(value=0))
    
    def _export_manifest(self):
        """Export manifest."""
        if not self.generator:
            messagebox.showinfo("No Manifest", "Generate assets first to create a manifest.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                manifest_path = self.generator.mod_path / "manifest.json"
                if manifest_path.exists():
                    shutil.copy2(manifest_path, file_path)
                    messagebox.showinfo("Success", f"Manifest exported to {file_path}")
                else:
                    messagebox.showwarning("No Manifest", "Manifest not found. Generate assets first.")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")


def main():
    """Main entry point."""
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = AssetGeneratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

