#!/usr/bin/env python3
"""
Unity Asset Generator for Caves of Qud Mods
Creates Unity assets (.meta files, prefabs, UI elements) as needed.
Supports SpringUI assets and standard Unity asset structure.
"""

import os
import sys
import json
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class UnityMetaFile:
    """Represents a Unity .meta file structure."""
    guid: str
    file_format_version: int = 2
    native_format_importer: Optional[Dict] = None
    texture_importer: Optional[Dict] = None
    model_importer: Optional[Dict] = None
    prefab_importer: Optional[Dict] = None
    script_importer: Optional[Dict] = None
    mono_importer: Optional[Dict] = None
    default_importer: Optional[Dict] = None
    user_data: Optional[str] = None
    asset_bundle_name: Optional[str] = None
    asset_bundle_variant: Optional[str] = None


class UnityAssetGenerator:
    """Generates Unity assets for Caves of Qud mods."""
    
    def __init__(self, mod_path: Path):
        """
        Initialize Unity asset generator.
        
        Args:
            mod_path: Path to the mod directory
        """
        self.mod_path = Path(mod_path)
        self.assets_path = self.mod_path / "Assets"
        self.resources_path = self.assets_path / "Resources" if self.assets_path.exists() else None
        
    def generate_meta_file(self, asset_path: Path, asset_type: str = "DefaultAsset") -> bool:
        """
        Generate a Unity .meta file for an asset.
        
        Args:
            asset_path: Path to the asset file
            asset_type: Type of asset (Texture2D, TextAsset, MonoScript, etc.)
        
        Returns:
            True if meta file was created, False otherwise
        """
        meta_path = asset_path.with_suffix(asset_path.suffix + ".meta")
        
        # Don't overwrite existing meta files
        if meta_path.exists():
            return False
        
        # Generate GUID for the asset
        guid = self._generate_guid(asset_path)
        
        # Create appropriate importer settings based on file type
        meta_data = UnityMetaFile(guid=guid)
        
        if asset_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tga', '.bmp', '.gif']:
            # Texture importer
            meta_data.texture_importer = {
                "internalIDToNameTable": [],
                "externalObjects": {},
                "userData": "",
                "assetBundleName": "",
                "assetBundleVariant": ""
            }
            meta_data.default_importer = {
                "externalObjects": {}
            }
        elif asset_path.suffix.lower() == '.cs':
            # C# script
            meta_data.mono_importer = {
                "externalObjects": {},
                "serializedVersion": 2,
                "executionOrder": 0,
                "icon": {"instanceID": 0},
                "userData": "",
                "assetBundleName": "",
                "assetBundleVariant": ""
            }
        elif asset_path.suffix.lower() in ['.xml', '.json', '.txt', '.md', '.uxml', '.uss']:
            # Text asset (including SpringUI files)
            meta_data.text_importer = {
                "assetBundleName": "",
                "assetBundleVariant": ""
            }
        elif asset_path.suffix.lower() == '.prefab':
            # Prefab
            meta_data.prefab_importer = {
                "externalObjects": {},
                "userData": "",
                "assetBundleName": "",
                "assetBundleVariant": ""
            }
        else:
            # Default asset
            meta_data.default_importer = {
                "externalObjects": {}
            }
        
        # Write meta file
        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                # Unity meta files use YAML-like format but are actually JSON-like
                # We'll use a simplified format that Unity can read
                f.write(f"fileFormatVersion: {meta_data.file_format_version}\n")
                f.write(f"guid: {meta_data.guid}\n")
                
                if meta_data.texture_importer:
                    f.write("TextureImporter:\n")
                    f.write("  internalIDToNameTable: []\n")
                    f.write("  externalObjects: {}\n")
                    f.write("  userData: \n")
                    f.write("  assetBundleName: \n")
                    f.write("  assetBundleVariant: \n")
                elif meta_data.mono_importer:
                    f.write("MonoImporter:\n")
                    f.write("  externalObjects: {}\n")
                    f.write("  serializedVersion: 2\n")
                    f.write("  executionOrder: 0\n")
                    f.write("  icon: {instanceID: 0}\n")
                    f.write("  userData: \n")
                    f.write("  assetBundleName: \n")
                    f.write("  assetBundleVariant: \n")
                elif meta_data.text_importer:
                    if asset_path.suffix.lower() in ['.uxml']:
                        f.write("VisualTreeAssetImporter:\n")
                        f.write("  externalObjects: {}\n")
                        f.write("  userData: \n")
                        f.write("  assetBundleName: \n")
                        f.write("  assetBundleVariant: \n")
                    elif asset_path.suffix.lower() in ['.uss']:
                        f.write("StyleSheetImporter:\n")
                        f.write("  externalObjects: {}\n")
                        f.write("  userData: \n")
                        f.write("  assetBundleName: \n")
                        f.write("  assetBundleVariant: \n")
                    else:
                        f.write("TextScriptImporter:\n")
                        f.write("  assetBundleName: \n")
                        f.write("  assetBundleVariant: \n")
                elif meta_data.prefab_importer:
                    f.write("PrefabImporter:\n")
                    f.write("  externalObjects: {}\n")
                    f.write("  userData: \n")
                    f.write("  assetBundleName: \n")
                    f.write("  assetBundleVariant: \n")
                else:
                    f.write("DefaultImporter:\n")
                    f.write("  externalObjects: {}\n")
                
                if meta_data.user_data:
                    f.write(f"userData: {meta_data.user_data}\n")
                if meta_data.asset_bundle_name:
                    f.write(f"assetBundleName: {meta_data.asset_bundle_name}\n")
                if meta_data.asset_bundle_variant:
                    f.write(f"assetBundleVariant: {meta_data.asset_bundle_variant}\n")
            
            return True
        except Exception as e:
            print(f"      [Unity] Warning: Failed to create .meta file for {asset_path.name}: {e}")
            return False
    
    def _generate_guid(self, file_path: Path) -> str:
        """
        Generate a deterministic GUID for a file path.
        
        Args:
            file_path: Path to the file
        
        Returns:
            GUID string (32 hex characters)
        """
        # Use file path to generate deterministic GUID
        path_str = str(file_path.relative_to(self.mod_path)).replace('\\', '/')
        hash_obj = hashlib.md5(path_str.encode('utf-8'))
        guid_hex = hash_obj.hexdigest()
        # Format as Unity GUID (32 hex chars in groups of 8-4-4-4-12)
        return f"{guid_hex[:8]}{guid_hex[8:12]}{guid_hex[12:16]}{guid_hex[16:20]}{guid_hex[20:]}"
    
    def scan_and_create_meta_files(self, directory: Optional[Path] = None) -> int:
        """
        Scan directory for assets missing .meta files and create them.
        
        Args:
            directory: Directory to scan (default: mod_path)
        
        Returns:
            Number of meta files created
        """
        if directory is None:
            directory = self.mod_path
        
        directory = Path(directory)
        created_count = 0
        
        # Files that should have .meta files
        asset_extensions = {'.cs', '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.gif', 
                           '.xml', '.json', '.txt', '.prefab', '.mat', '.shader', 
                           '.asset', '.controller', '.anim', '.fbx', '.obj'}
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Skip existing .meta files
                if file_path.suffix == '.meta':
                    continue
                
                # Check if asset type needs .meta file
                if file_path.suffix.lower() in asset_extensions:
                    meta_path = file_path.with_suffix(file_path.suffix + ".meta")
                    if not meta_path.exists():
                        if self.generate_meta_file(file_path):
                            created_count += 1
                            print(f"      [Unity] Created .meta file for {file_path.relative_to(self.mod_path)}")
        
        return created_count
    
    def create_springui_assets(self, ui_name: str, ui_type: str = "Panel") -> Dict[str, Path]:
        """
        Create SpringUI assets for a UI element.
        
        Args:
            ui_name: Name of the UI element
            ui_type: Type of UI element (Panel, Button, Text, etc.)
        
        Returns:
            Dictionary of created asset paths
        """
        created_assets = {}
        
        # Create SpringUI directory structure
        springui_path = self.assets_path / "SpringUI" / ui_name
        springui_path.mkdir(parents=True, exist_ok=True)
        
        # Create UI document (.uxml file)
        uxml_path = springui_path / f"{ui_name}.uxml"
        if not uxml_path.exists():
            uxml_content = self._generate_uxml_content(ui_name, ui_type)
            with open(uxml_path, 'w', encoding='utf-8') as f:
                f.write(uxml_content)
            created_assets['uxml'] = uxml_path
            print(f"      [Unity] Created SpringUI UXML: {uxml_path.relative_to(self.mod_path)}")
            
            # Create .meta file for UXML
            self.generate_meta_file(uxml_path, "VisualTreeAsset")
        
        # Create stylesheet (.uss file)
        uss_path = springui_path / f"{ui_name}.uss"
        if not uss_path.exists():
            uss_content = self._generate_uss_content(ui_name)
            with open(uss_path, 'w', encoding='utf-8') as f:
                f.write(uss_content)
            created_assets['uss'] = uss_path
            print(f"      [Unity] Created SpringUI USS: {uss_path.relative_to(self.mod_path)}")
            
            # Create .meta file for USS
            self.generate_meta_file(uss_path, "StyleSheet")
        
        return created_assets
    
    def _generate_uxml_content(self, ui_name: str, ui_type: str) -> str:
        """Generate UXML content for SpringUI."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<ui:UXML xmlns:ui="UnityEngine.UIElements" xmlns:uie="UnityEditor.UIElements" xsi="http://www.w3.org/2001/XMLSchema-instance" engine="UnityEngine.UIElements" editor="UnityEditor.UIElements" noNamespaceSchemaLocation="../../UIElementsSchema/UIElements.xsd" editor-extension-mode="False">
    <ui:VisualElement name="{ui_name}" class="{ui_name.lower()}">
        <!-- SpringUI {ui_type} element -->
        <ui:VisualElement name="content">
            <!-- Add UI elements here -->
        </ui:VisualElement>
    </ui:VisualElement>
</ui:UXML>
"""
    
    def _generate_uss_content(self, ui_name: str) -> str:
        """Generate USS stylesheet content for SpringUI."""
        return f""".{ui_name.lower()} {{
    width: 100%;
    height: 100%;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}

.{ui_name.lower()} .content {{
    width: 100%;
    height: 100%;
}}
"""
    
    def create_unity_project_structure(self) -> bool:
        """
        Create basic Unity project structure if it doesn't exist.
        
        Returns:
            True if structure was created, False if it already exists
        """
        if self.assets_path.exists():
            return False
        
        # Create basic Unity project structure
        directories = [
            self.assets_path,
            self.assets_path / "Resources",
            self.assets_path / "SpringUI",
            self.assets_path / "Scripts",
            self.assets_path / "Editor"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create project settings placeholder
        project_settings = self.mod_path / "ProjectSettings"
        if not project_settings.exists():
            project_settings.mkdir(exist_ok=True)
        version_file = project_settings / "ProjectVersion.txt"
        if not version_file.exists():
            editor_ver = "6000.0.77f1"
            try:
                shared = Path(__file__).resolve().parent.parent / "Shared"
                if str(shared) not in sys.path:
                    sys.path.insert(0, str(shared))
                from unity_version import get_game_unity_version  # type: ignore

                detected = get_game_unity_version(
                    Path(r"E:\SteamLibrary\steamapps\common\Caves of Qud")
                )
                if detected:
                    editor_ver = detected
            except Exception:
                pass
            version_file.write_text(
                f"m_EditorVersion: {editor_ver}\n"
                f"m_EditorVersionWithRevision: {editor_ver} (aamt)\n",
                encoding="utf-8",
            )
        
        print(f"      [Unity] Created Unity project structure in {self.assets_path.relative_to(self.mod_path)}")
        return True
    
    def check_and_fix_assets(self) -> Dict[str, Any]:
        """
        Check for missing Unity assets and create them.
        
        Returns:
            Dictionary with results of asset creation
        """
        results = {
            'meta_files_created': 0,
            'springui_assets_created': 0,
            'project_structure_created': False
        }
        
        # Create Unity project structure if needed
        if self.create_unity_project_structure():
            results['project_structure_created'] = True
        
        # Scan and create missing .meta files
        if self.assets_path.exists():
            results['meta_files_created'] = self.scan_and_create_meta_files(self.assets_path)
        
        # Check for SpringUI references and create assets if needed
        springui_refs = self._find_springui_references()
        for ref in springui_refs:
            assets = self.create_springui_assets(ref['name'], ref.get('type', 'Panel'))
            if assets:
                results['springui_assets_created'] += len(assets)
        
        return results
    
    def _find_springui_references(self) -> List[Dict[str, str]]:
        """
        Find references to SpringUI in mod files.
        
        Returns:
            List of SpringUI references found
        """
        references = []
        
        # Look for SpringUI references in C# files
        for cs_file in self.mod_path.rglob('*.cs'):
            try:
                with open(cs_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Look for SpringUI class names or UI element references
                    if 'SpringUI' in content or 'UIElement' in content:
                        # Try to extract UI element names
                        import re
                        ui_matches = re.findall(r'(?:SpringUI|UIElement|UIPanel|UIButton)\s+(\w+)', content)
                        for match in ui_matches:
                            references.append({'name': match, 'type': 'Panel'})
            except Exception:
                pass
        
        return references

