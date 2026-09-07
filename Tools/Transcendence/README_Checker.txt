============================================================
Transcendence Mod Tools
============================================================

A suite of tools for Transcendence mod development.

============================================================
MAIN TOOL: TranscendenceModTools
============================================================

The integrated mod development tool with a modern GUI.

FEATURES:
  - XML Checker tab: Scan mods for common issues
  - Error Helper tab: Diagnose error messages
  - Auto-fix capabilities with backup
  - Double-click issues to open in VS Code

TO RUN:
  Double-click: TranscendenceModTools.bat

WHAT IT CHECKS:
  [Errors]
  - BOM_DETECTED: UTF-8 BOM before XML declaration
  - RAW_GT_IN_CONTENT: Raw '>' causing "content expected"
  - INVALID_SYMBOL_SYNTAX: TLisp 'symbol' with trailing quote
  
  [Warnings]
  - XMLCREATE_RAW_XML: Unescaped XML in xmlCreate strings

ERROR HELPER:
  Paste any Transcendence error message and get:
  - What caused the error
  - How to fix it
  - Whether it can be auto-fixed

SUPPORTED ERROR PATTERNS:
  - "content expected"
  - "Mismatched quote"
  - "Identifiers must not use single quote"
  - "close tag does not match"
  - "Reference to undeclared entity"
  - "<?XML prologue expected"
  - And more...

============================================================
LEGACY TOOLS
============================================================

These older tools are still available:

CheckTranscendenceXml.bat
  Command-line XML checker with configurable options

TranscendenceErrorHelper.bat
  Standalone error message analyzer

============================================================
USAGE EXAMPLES
============================================================

1. Scan a mod folder:
   - Open TranscendenceModTools.bat
   - Click Browse and select your mod folder
   - Click Scan

2. Diagnose an error:
   - Open TranscendenceModTools.bat
   - Go to Error Helper tab
   - Paste your error message
   - Click Analyze Error

3. Open issue in VS Code:
   - After scanning, double-click any issue row
   - VS Code opens at the exact line

4. Auto-fix issues:
   - After scanning, click Auto-Fix
   - Tool creates .bak backups
   - Fixes what it can automatically

============================================================
REQUIREMENTS
============================================================

- PowerShell 7+ (pwsh)
- Windows 10/11

============================================================
