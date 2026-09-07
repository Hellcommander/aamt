# Transcendence Mod Tools - Feature List

## 🚀 Implemented Features

### ✅ Core Features (Already Working)

1. **XML Checker Tab**
   - UTF-8 BOM detection
   - Raw `>` in content detection
   - Invalid TLisp symbol syntax
   - XML well-formedness checking
   - Unescaped XML in `xmlCreate` strings
   - Auto-fix with `.bak` backups
   - Double-click to open in VS Code

2. **Error Helper Tab**
   - Paste error messages for diagnosis
   - Pattern matching from engine source
   - Cause and solution explanations
   - Auto-fix suggestions

### ✅ NEW: Advanced Features (Just Added)

3. **XML Structure Validator** 🧩
   - Unclosed tag detection
   - Tag mismatch detection
   - Duplicate attribute detection
   - Unexpected closing tags
   - Line and column highlighting

4. **TLisp Expression Checker** 🔍
   - Parentheses balance checking
   - Unbalanced `(` and `)` detection
   - Extra closing parenthesis detection
   - Suspicious `(@ var)` construct detection
   - Works in `<Events>`, `<OnCreate>`, `<Globals>`, etc.

5. **UNID Reference Checker** 🧭
   - Duplicate UNID detection across files
   - Missing entity reference detection
   - Invalid UNID format warnings
   - Entity definition tracking
   - Cross-file UNID collision detection

6. **Multi-File Project Support** 📁
   - Scan entire mod folders
   - Recursive file scanning
   - Per-file status tracking
   - Project-wide issue aggregation

7. **Project Health Report** 🧰
   - Comprehensive project summary
   - Files with errors/warnings count
   - Total issues breakdown
   - UNID duplicate count
   - Per-file status display
   - Visual indicators (✓, ⚠, ❌)

8. **Documentation Lookup** 📚
   - Element documentation database
   - Attribute information
   - Child element lists
   - Example usage (ready for expansion)

## 🎯 How to Use

### Basic Scanning
1. Open `TranscendenceModTools.bat`
2. Go to **XML Checker** tab
3. Enter path or click **Browse**
4. Click **Scan**
5. Review issues in the grid
6. Double-click issues to open in VS Code

### Error Diagnosis
1. Go to **Error Helper** tab
2. Paste your error message
3. Click **Analyze Error**
4. Read the diagnosis and solution

### Project Health
1. Go to **Project Health** tab
2. Enter your mod folder path
3. Click **Generate Report**
4. Review comprehensive project status

### Auto-Fix
1. After scanning, click **Auto-Fix**
2. Tool creates `.bak` backups
3. Fixes what it can automatically
4. Rescans to show remaining issues

## ✅ Recently Implemented (Version 3.0)

- **XML Auto-Formatting**: ✅ Beautify XML button with indentation and attribute alignment
- **UNID Management**: ✅ UNID Manager tab with scanning, generation, and duplicate detection
- **Cross-Mod Compatibility**: ✅ Cross-Mod Check tab for detecting conflicts between mods

## ✅ Recently Implemented (Version 3.2)

- **Automatic XML Formatting**: ✅ Enhanced to match Transcendence 2.0.7 style
- **Dependency Graph**: ✅ Complete visualization of mod relationships

## 🔮 Future Enhancements (Not Yet Implemented)

These are optional future additions:

- **Syntax Highlighting**: XML and TLisp highlighting in editor
- **Real-Time Validation**: As-you-type error checking
- **Resource Preview**: Image/sound file previews
- **Visual Graph Diagrams**: Beyond text-based graphs
- **Simulation Sandbox**: Test TLisp expressions

## 📝 Technical Details

### File Structure
- `TranscendenceModTools.ps1` - Main tool with GUI
- `TranscendenceModTools_Advanced.ps1` - Advanced features module
- `TranscendenceModTools.bat` - Launcher script

### Advanced Features Module
The advanced features are in a separate module that gets loaded automatically:
- `Get-XmlStructureIssues` - Tag matching and validation
- `Get-TlispExpressionIssues` - TLisp syntax checking
- `Get-UnidReferenceIssues` - UNID validation
- `Get-ProjectHealthReport` - Comprehensive reporting

### Integration
The main tool automatically loads the advanced module if present, so all features work together seamlessly.

## 🎨 UI Features

- **Dark Theme**: Modern dark interface
- **Color Coding**: Red for errors, yellow for warnings
- **Tabbed Interface**: Organized by function
- **Status Updates**: Real-time progress feedback
- **VS Code Integration**: Double-click to open files
- **Rich Text Output**: Formatted reports

## 🔧 Requirements

- PowerShell 7+ (pwsh)
- Windows 10/11
- VS Code (optional, for file opening)

## 📚 Documentation

See `README_Checker.txt` for quick start guide and examples.

