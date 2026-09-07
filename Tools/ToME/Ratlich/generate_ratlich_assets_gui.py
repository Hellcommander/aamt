#!/usr/bin/env python3
"""
GUI for generating high-quality Ratlich race assets.
Focuses on paperdoll system with fewer assets but higher quality.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
from typing import Optional
import json
import shutil
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from generate_ratlich_assets import RatlichAssetGenerator


class RatlichAssetGeneratorGUI:
    """GUI for Ratlich asset generation."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ratlich Race Asset Generator")
        self.root.geometry("900x700")
        
        self.is_generating = False
        self.generation_thread: Optional[threading.Thread] = None
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI."""
        # Main content area (will expand)
        main_content = ttk.Frame(self.root)
        main_content.pack(fill=tk.BOTH, expand=True)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_content, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Mod path
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="Mod Path:").pack(side=tk.LEFT, padx=5)
        self.mod_path_var = tk.StringVar(
            value=r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-ratlich-race"
        )
        self.mod_path_entry = ttk.Entry(path_frame, textvariable=self.mod_path_var, width=60)
        self.mod_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self._browse_mod).pack(side=tk.LEFT, padx=5)
        
        # AI settings
        ai_frame = ttk.Frame(config_frame)
        ai_frame.pack(fill=tk.X, pady=5)
        
        self.use_ai_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ai_frame, text="Use AI Enhancement", variable=self.use_ai_var).pack(side=tk.LEFT, padx=5)
        
        # Asset info
        info_frame = ttk.LabelFrame(main_content, text="Assets to Generate", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        info_text = """
High-Quality Ratlich Race Assets

This generator will create:
• Base body sprites (front & back) - 100 variations each
• Equipment overlays (head, body, hands, tail weapon) - 60-80 variations each
• Map display sprites (32x32, 64x64, 128x128) - 100 variations each
• Icon sprites (32x32, 128x128) - 100 variations each
• Talent icons (5 talents) - 100 variations each

Total: ~1,500 variations across 15 asset types
Best variation (highest balance score) will be selected for each asset.

The generator focuses on quality over quantity, generating many variations
and automatically selecting the best one for each asset type.

Talent Icons:
• Rat Lich Cunning - Intelligence/cunning theme
• Illusory Guise - Illusion/mystical theme
• Equip Tail Weapon - Weapon/equipment theme
• Dark Feed Rush - Dark/attack theme
• Summon Undead Rats - Summoning theme
        """
        
        info_label = ttk.Label(info_frame, text=info_text.strip(), justify=tk.LEFT)
        info_label.pack(anchor=tk.W, padx=10, pady=10)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_content, text="Generation Progress", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
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
        log_frame = ttk.LabelFrame(main_content, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar (pack at bottom of root)
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Buttons (pack above status bar at bottom of root)
        button_frame = ttk.Frame(self.root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Assets", command=self._start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop", command=self._stop_generation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
    
    def _browse_mod(self):
        """Browse for mod directory."""
        path = filedialog.askdirectory(title="Select Ratlich Race Mod Directory")
        if path:
            self.mod_path_var.set(path)
    
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
        if not mod_path:
            messagebox.showerror("Error", "Please specify a mod path.")
            return
        
        mod_path_obj = Path(mod_path)
        if not mod_path_obj.exists():
            messagebox.showerror("Error", f"Mod path does not exist: {mod_path}")
            return
        
        self.is_generating = True
        self.generate_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Generating...")
        
        # Start generation in thread
        self.generation_thread = threading.Thread(
            target=self._generate_assets_thread,
            args=(mod_path_obj,),
            daemon=True
        )
        self.generation_thread.start()
    
    def _stop_generation(self):
        """Stop asset generation."""
        if not self.is_generating:
            return
        
        self.is_generating = False
        self.status_var.set("Stopping...")
    
    def _generate_assets_thread(self, mod_path: Path):
        """Generate assets in background thread."""
        try:
            self.root.after(0, self._log, "=" * 60)
            self.root.after(0, self._log, "Starting Ratlich asset generation...")
            self.root.after(0, self._log, f"Mod path: {mod_path}")
            self.root.after(0, self._log, f"AI enhancement: {self.use_ai_var.get()}")
            self.root.after(0, self._log, "=" * 60)
            self.root.after(0, self._log, "")
            
            generator = RatlichAssetGenerator(mod_path, use_ai=self.use_ai_var.get())
            
            # Calculate total variations
            total_variations = sum(def_['variations'] for def_ in generator.asset_defs.values())
            self.root.after(0, lambda: self.overall_progress.config(maximum=total_variations, value=0))
            self.root.after(0, lambda: self.overall_label.config(text=f"Overall Progress: 0 / {total_variations}"))
            
            generated = 0
            
            def progress_callback(msg, current, total):
                if not self.is_generating:
                    return
                
                pct = (current / total * 100) if total > 0 else 0
                self.root.after(0, lambda m=msg, c=current, t=total: self._log(f"[{pct:5.1f}%] {m}"))
                self.root.after(0, lambda c=current: self.overall_progress.config(value=c))
                self.root.after(0, lambda c=current, t=total: self.overall_label.config(
                    text=f"Overall Progress: {c} / {t}"
                ))
            
            results = generator.generate_all(progress_callback=progress_callback)
            
            if not self.is_generating:
                self.root.after(0, self._log, "\nGeneration stopped by user.")
                return
            
            # Create paperdoll config
            self.root.after(0, self._log, "\nCreating paperdoll configuration...")
            config = generator.create_paperdoll_config(results)
            
            self.root.after(0, self._log, "\n" + "=" * 60)
            self.root.after(0, self._log, "Generation complete!")
            self.root.after(0, self._log, "=" * 60)
            self.root.after(0, self._log, "\nGenerated assets:")
            
            for key, result in results.items():
                self.root.after(0, self._log, f"  {key}: {result.get('path', 'N/A')} (score: {result.get('score', 0):.2f})")
            
            self.root.after(0, self._log, f"\nPaperdoll config: {generator.output_dir / 'ratlich_paperdoll_config.json'}")
            self.root.after(0, lambda: self.status_var.set("Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Complete", "Asset generation complete! Check the log for details."))
            
        except Exception as e:
            self.root.after(0, self._log, f"\nERROR: {e}")
            self.root.after(0, lambda: self.status_var.set("Error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {e}"))
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))


def main():
    """Main entry point."""
    root = tk.Tk()
    app = RatlichAssetGeneratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

