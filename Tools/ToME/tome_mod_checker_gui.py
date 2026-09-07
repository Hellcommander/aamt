#!/usr/bin/env python3
"""
ToME Mod Checker GUI with Drag and Drop
Graphical interface for mod checking and Ollama-guided fixing.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
from pathlib import Path
from typing import Optional
import json
import os
import sys

# Try to import tkinterdnd2 for drag and drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("Warning: tkinterdnd2 not available. Install with: pip install tkinterdnd2")
    print("Drag and drop will be disabled.")

# Import checker
from tome_mod_checker import (
    ToMEModChecker,
    OllamaModFixer,
    ModCheckResult,
    ModIssue,
    IssueSeverity,
    check_mod,
    read_error_logs,
    show_model_menu,
    TOME_GAME_PATH,
    TOME_LOG_PATH,
    TOME_SOURCE_PATH,
    TOME_ENGINE_SOURCE,
    TOME_ADDONS_PATH
)


class ModCheckerGUI:
    """GUI for ToME mod checker."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ToME Mod Checker & Fixer")
        self.root.geometry("1200x800")
        
        self.mod_path: Optional[Path] = None
        self.check_result: Optional[ModCheckResult] = None
        self.fixer = OllamaModFixer()
        self.error_logs: Dict[str, List[str]] = {}
        self.preferred_model: Optional[str] = None
        self.last_backup: Optional[Path] = None
        self.last_file: Optional[Path] = None
        
        self._create_ui()
        self._setup_drag_drop()
    
    def _create_ui(self):
        """Create the UI."""
        # Top frame - File selection
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="ToME Mod Path:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=60)
        self.path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(top_frame, text="Browse", command=self._browse_mod).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Check Mod", command=self._check_mod).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Select Model", command=self._select_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Load Error Logs", command=self._load_error_logs).pack(side=tk.LEFT, padx=5)
        
        # Drag and drop area
        drop_frame = ttk.LabelFrame(self.root, text="Drag & Drop Mod Folder Here", padding="20")
        drop_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.drop_label = ttk.Label(
            drop_frame,
            text="Drop a ToME mod folder here to check it",
            font=("Arial", 12)
        )
        self.drop_label.pack(expand=True)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.root, text="Check Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary
        summary_frame = ttk.Frame(results_frame)
        summary_frame.pack(fill=tk.X, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="No mod checked yet", font=("Arial", 10, "bold"))
        self.summary_label.pack(side=tk.LEFT)
        
        ttk.Button(summary_frame, text="Export JSON", command=self._export_json).pack(side=tk.RIGHT, padx=5)
        ttk.Button(summary_frame, text="Get AI Fixes", command=self._get_ai_fixes).pack(side=tk.RIGHT, padx=5)
        
        # Issues tree
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        self.issues_tree = ttk.Treeview(
            tree_frame,
            columns=("severity", "file", "line", "message"),
            show="tree headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        tree_scroll_y.config(command=self.issues_tree.yview)
        tree_scroll_x.config(command=self.issues_tree.xview)
        
        # Configure columns
        self.issues_tree.heading("#0", text="")
        self.issues_tree.heading("severity", text="Severity")
        self.issues_tree.heading("file", text="File")
        self.issues_tree.heading("line", text="Line")
        self.issues_tree.heading("message", text="Message")
        
        self.issues_tree.column("#0", width=0, stretch=tk.NO)
        self.issues_tree.column("severity", width=80)
        self.issues_tree.column("file", width=200)
        self.issues_tree.column("line", width=60)
        self.issues_tree.column("message", width=400)
        
        self.issues_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection
        self.issues_tree.bind("<<TreeviewSelect>>", self._on_issue_select)
        
        # Details frame
        details_frame = ttk.LabelFrame(self.root, text="Issue Details & AI Suggestions", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, height=10, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Current file and backup status frame
        file_status_frame = ttk.LabelFrame(self.root, text="File Status", padding="5")
        file_status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_file_var = tk.StringVar(value="No file being processed")
        ttk.Label(file_status_frame, text="Current File:").pack(side=tk.LEFT, padx=5)
        self.current_file_label = ttk.Label(file_status_frame, textvariable=self.current_file_var, foreground="blue")
        self.current_file_label.pack(side=tk.LEFT, padx=5)
        
        self.backup_status_var = tk.StringVar(value="No backups")
        ttk.Label(file_status_frame, text="Backups:").pack(side=tk.LEFT, padx=5)
        self.backup_status_label = ttk.Label(file_status_frame, textvariable=self.backup_status_var, foreground="green")
        self.backup_status_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(file_status_frame, text="Restore Last Backup", command=self._restore_backup).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_drag_drop(self):
        """Setup drag and drop."""
        if not DND_AVAILABLE:
            self.drop_label.config(text="Drag & Drop not available. Install tkinterdnd2.\nUse Browse button instead.")
            return
        
        try:
            # Register drop target
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self._on_drop)
            self.path_entry.drop_target_register(DND_FILES)
            self.path_entry.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            print(f"Drag and drop setup failed: {e}")
            self.drop_label.config(text="Drag & Drop failed. Use Browse button instead.")
    
    def _on_drop(self, event):
        """Handle file drop."""
        if not DND_AVAILABLE:
            return
        
        try:
            files = self.root.tk.splitlist(event.data)
            if files:
                path = Path(files[0])
                if path.is_dir():
                    self.mod_path = path
                    self.path_var.set(str(path))
                    self._check_mod()
                else:
                    messagebox.showwarning("Invalid Drop", "Please drop a mod folder, not a file.")
        except Exception as e:
            messagebox.showerror("Drop Error", f"Error handling drop: {e}")
    
    def _browse_mod(self):
        """Browse for mod directory."""
        initial_dir = str(TOME_ADDONS_PATH) if TOME_ADDONS_PATH.exists() else None
        path = filedialog.askdirectory(
            title="Select ToME Mod Directory",
            initialdir=initial_dir
        )
        if path:
            self.mod_path = Path(path)
            self.path_var.set(str(path))
            self._check_mod()
    
    def _check_mod(self):
        """Check the mod."""
        if not self.mod_path:
            mod_path = self.path_var.get()
            if not mod_path:
                messagebox.showwarning("No Mod Selected", "Please select a mod directory first.")
                return
            self.mod_path = Path(mod_path)
        
        if not self.mod_path.exists():
            messagebox.showerror("Error", f"Mod directory does not exist: {self.mod_path}")
            return
        
        self.status_var.set("Checking mod...")
        self.root.update()
        
        # Try to auto-load error logs if available
        if not self.error_logs:
            mod_name = self.mod_path.name if self.mod_path else None
            self.error_logs = read_error_logs(mod_name=mod_name)
            if self.error_logs:
                self.status_var.set(f"Checking mod... (loaded {len(self.error_logs)} log file(s))")
        
        # Run check in thread to avoid blocking UI
        def check_thread():
            try:
                # Use default source path if available
                tome_source = str(TOME_ENGINE_SOURCE) if TOME_ENGINE_SOURCE.exists() else str(TOME_SOURCE_PATH) if TOME_SOURCE_PATH.exists() else None
                result = check_mod(str(self.mod_path), tome_source)
                self.root.after(0, self._display_results, result)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Check failed: {e}"))
                self.root.after(0, lambda: self.status_var.set("Error"))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _display_results(self, result: ModCheckResult):
        """Display check results."""
        self.check_result = result
        
        # Clear tree
        for item in self.issues_tree.get_children():
            self.issues_tree.delete(item)
        
        # Update summary
        summary = f"Errors: {result.summary['errors']} | Warnings: {result.summary['warnings']} | Info: {result.summary['info']}"
        self.summary_label.config(text=summary)
        
        # Add issues to tree
        for issue in result.issues:
            severity_color = {
                'error': 'red',
                'warning': 'orange',
                'info': 'blue'
            }.get(issue.severity.value, 'black')
            
            item = self.issues_tree.insert(
                "",
                tk.END,
                values=(
                    issue.severity.value.upper(),
                    issue.file,
                    issue.line or "?",
                    issue.message
                ),
                tags=(issue.severity.value,)
            )
            
            # Color code
            self.issues_tree.tag_configure(issue.severity.value, foreground=severity_color)
        
        self.status_var.set(f"Found {len(result.issues)} issues")
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "Select an issue to see details and AI suggestions.")
    
    def _on_issue_select(self, event):
        """Handle issue selection."""
        selection = self.issues_tree.selection()
        if not selection or not self.check_result:
            return
        
        item = selection[0]
        values = self.issues_tree.item(item, 'values')
        if not values:
            return
        
        # Find corresponding issue
        file_name = values[1]
        line_num = values[2]
        message = values[3]
        
        issue = None
        for i in self.check_result.issues:
            if i.file == file_name and str(i.line or "?") == line_num and i.message == message:
                issue = i
                break
        
        if issue:
            self._show_issue_details(issue)
    
    def _show_issue_details(self, issue: ModIssue):
        """Show issue details."""
        self.details_text.delete(1.0, tk.END)
        
        details = f"Issue Details\n"
        details += f"{'='*60}\n\n"
        details += f"Severity: {issue.severity.value.upper()}\n"
        details += f"File: {issue.file}\n"
        details += f"Line: {issue.line or 'N/A'}\n"
        details += f"Message: {issue.message}\n\n"
        
        if issue.code:
            details += f"Code:\n{issue.code}\n\n"
        
        if issue.fixable:
            details += "This issue can be fixed automatically.\n"
            details += "Click 'Get AI Fixes' to see suggestions.\n\n"
        else:
            details += "This issue requires manual fixing.\n\n"
        
        if issue.suggestion:
            details += f"Suggestion: {issue.suggestion}\n"
        
        self.details_text.insert(tk.END, details)
    
    def _select_model(self):
        """Select AI model."""
        selected = show_model_menu(current_model=self.preferred_model or "")
        if selected is not None:
            self.preferred_model = selected
            self.fixer = OllamaModFixer(preferred_model=selected)
            messagebox.showinfo("Model Selected", f"Using model: {selected if selected else 'default'}")
    
    def _load_error_logs(self):
        """Load error logs."""
        from tome_mod_checker import TOME_LOG_PATH, TOME_GAME_PATH
        
        # Try to auto-detect log file first
        auto_log = None
        if TOME_LOG_PATH.exists():
            auto_log = TOME_LOG_PATH
        elif TOME_GAME_PATH.exists():
            auto_log = TOME_GAME_PATH / "te4_log.txt"
        
        # Ask user if they want to use auto-detected log or select manually
        if auto_log and auto_log.exists():
            use_auto = messagebox.askyesno(
                "Auto-detect Log",
                f"Found log file at:\n{auto_log}\n\nUse this file? (Click No to select manually)"
            )
            if use_auto:
                log_paths = [auto_log]
            else:
                # Ask for log files
                log_files = filedialog.askopenfilenames(
                    title="Select Error Log Files",
                    initialdir=str(TOME_GAME_PATH) if TOME_GAME_PATH.exists() else None,
                    filetypes=[("Log files", "*.log *.txt"), ("Text files", "*.txt"), ("All files", "*.*")]
                )
                log_paths = [Path(f) for f in log_files] if log_files else None
        else:
            # Ask for log files
            log_files = filedialog.askopenfilenames(
                title="Select Error Log Files",
                initialdir=str(TOME_GAME_PATH) if TOME_GAME_PATH.exists() else None,
                filetypes=[("Log files", "*.log *.txt"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            log_paths = [Path(f) for f in log_files] if log_files else None
        
        if log_paths:
            mod_name = self.mod_path.name if self.mod_path else None
            self.error_logs = read_error_logs(log_paths=log_paths, mod_name=mod_name)
            if self.error_logs:
                messagebox.showinfo("Error Logs Loaded", f"Loaded {len(self.error_logs)} log file(s)")
            else:
                messagebox.showwarning("No Errors Found", "No errors found in selected log files.")
        else:
            # Try auto-detection
            mod_name = self.mod_path.name if self.mod_path else None
            self.error_logs = read_error_logs(mod_name=mod_name)
            if self.error_logs:
                messagebox.showinfo("Error Logs Auto-Loaded", f"Auto-loaded {len(self.error_logs)} log file(s)")
            else:
                messagebox.showwarning("No Logs Found", "Could not find error log files. Please specify manually.")
    
    def _get_ai_fixes(self):
        """Get AI suggestions for issues."""
        if not self.check_result:
            messagebox.showinfo("No Results", "Please check a mod first.")
            return
        
        fixable_issues = [i for i in self.check_result.issues if i.fixable]
        if not fixable_issues:
            messagebox.showinfo("No Fixable Issues", "No automatically fixable issues found.")
            return
        
        # Ask if user wants to apply fixes
        apply_fixes = messagebox.askyesno(
            "Apply Fixes",
            f"Found {len(fixable_issues)} fixable issue(s).\n\nApply fixes automatically with backups?"
        )
        
        self.status_var.set("Getting AI suggestions...")
        self.root.update()
        
        def get_fixes_thread():
            try:
                suggestions = []
                for issue in fixable_issues[:5]:  # Limit to 5 issues
                    file_path = self.mod_path / issue.file
                    
                    # Update current file status
                    self.root.after(0, lambda f=file_path: self.current_file_var.set(f"Processing: {f.name}"))
                    
                    file_content = None
                    if file_path.exists():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                        except:
                            pass
                    
                    suggestion = self.fixer.suggest_fix(issue, file_content, self.error_logs)
                    if suggestion:
                        # Apply fix if requested
                        if apply_fixes and file_path.exists():
                            success, backup_path = self.fixer.apply_fix(file_path, suggestion, create_backup=True)
                            if success and backup_path:
                                self.root.after(0, lambda bp=backup_path, fp=file_path: self._update_backup_status(bp, fp))
                        
                        suggestions.append((issue, suggestion, file_path if apply_fixes else None))
                
                self.root.after(0, lambda: self.current_file_var.set("No file being processed"))
                self.root.after(0, self._display_ai_suggestions, suggestions)
            except Exception as e:
                self.root.after(0, lambda: self.current_file_var.set("No file being processed"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"AI fix failed: {e}"))
                self.root.after(0, lambda: self.status_var.set("Error"))
        
        threading.Thread(target=get_fixes_thread, daemon=True).start()
    
    def _update_backup_status(self, backup_path: Path, file_path: Path):
        """Update backup status display."""
        self.last_backup = backup_path
        self.last_file = file_path
        self.backup_status_var.set(f"Last: {backup_path.name}")
    
    def _restore_backup(self):
        """Restore last backup."""
        if not self.last_backup or not self.last_file:
            messagebox.showinfo("No Backup", "No backup available to restore.")
            return
        
        if not self.last_backup.exists():
            messagebox.showerror("Backup Missing", f"Backup file not found: {self.last_backup}")
            return
        
        confirm = messagebox.askyesno(
            "Restore Backup",
            f"Restore {self.last_file.name} from backup?\n\nBackup: {self.last_backup.name}"
        )
        
        if confirm:
            success = self.fixer.restore_backup(self.last_file)
            if success:
                messagebox.showinfo("Success", f"Restored {self.last_file.name} from backup.")
                self.backup_status_var.set("Restored")
            else:
                messagebox.showerror("Error", "Failed to restore backup.")
    
    def _display_ai_suggestions(self, suggestions):
        """Display AI suggestions."""
        self.details_text.delete(1.0, tk.END)
        
        if not suggestions:
            self.details_text.insert(tk.END, "No AI suggestions available.\nMake sure Ollama is running.")
            self.status_var.set("No suggestions available")
            return
        
        text = "AI-Generated Fixes\n"
        text += f"{'='*60}\n\n"
        
        for item in suggestions:
            if len(item) == 3:
                issue, suggestion, file_path = item
                applied = file_path is not None
            else:
                issue, suggestion = item
                applied = False
            
            text += f"Issue: {issue.message}\n"
            text += f"File: {issue.file}\n"
            text += f"Line: {issue.line or 'N/A'}\n"
            if applied:
                text += f"Status: ✓ Applied (backup created)\n"
            text += f"\nSuggested Fix:\n"
            text += f"{'-'*60}\n"
            text += f"{suggestion}\n"
            text += f"{'-'*60}\n\n"
        
        self.details_text.insert(tk.END, text)
        self.status_var.set(f"Got {len(suggestions)} AI suggestions")
    
    def _export_json(self):
        """Export results to JSON."""
        if not self.check_result:
            messagebox.showinfo("No Results", "Please check a mod first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.check_result.to_json())
                messagebox.showinfo("Success", f"Results exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")


def main():
    """Main entry point."""
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = ModCheckerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

