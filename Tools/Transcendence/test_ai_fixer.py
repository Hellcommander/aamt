#!/usr/bin/env python3
"""Test AI fixer on the smog-devil-class mod."""

import sys
from pathlib import Path
from tome_mod_checker import check_mod, OllamaModFixer, ModIssue, IssueSeverity

# Test mod path
mod_path = r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class"

print("=" * 60)
print("ToME Mod Checker - AI Fixer Test")
print("=" * 60)
print()

# Check the mod
print("Checking mod...")
result = check_mod(mod_path)

print(f"Found {len(result.issues)} issues:")
print(f"  Errors: {result.summary['errors']}")
print(f"  Warnings: {result.summary['warnings']}")
print(f"  Info: {result.summary['info']}")
print()

# Initialize AI fixer
print("Initializing AI fixer...")
fixer = OllamaModFixer()

if not fixer._check_ollama_available():
    print("ERROR: Ollama is not available!")
    print("Make sure Ollama is running: ollama serve")
    sys.exit(1)

print("[OK] Ollama is available")
if fixer.code_model:
    print(f"  Code Model: {fixer.code_model}")
if fixer.visual_model:
    print(f"  Visual Model: {fixer.visual_model}")
print()

# Get fixable issues
fixable_issues = [i for i in result.issues if i.fixable]
print(f"Found {len(fixable_issues)} fixable issues")
print()

# Test AI fixes on first few issues
for i, issue in enumerate(fixable_issues[:3], 1):
    print(f"{'='*60}")
    print(f"Issue {i}: {issue.file}")
    print(f"{'='*60}")
    print(f"Message: {issue.message}")
    print(f"Line: {issue.line or 'N/A'}")
    print()
    
    # Read file content for context
    file_path = Path(mod_path) / issue.file
    file_content = None
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            print(f"File exists, reading context...")
        except Exception as e:
            print(f"Error reading file: {e}")
    
    # Get AI suggestion
    print("Getting AI fix suggestion...")
    suggestion = fixer.suggest_fix(issue, file_content)
    
    if suggestion:
        print("[OK] AI Suggestion received:")
        print("-" * 60)
        print(suggestion)
        print("-" * 60)
    else:
        print("[FAIL] No AI suggestion available")
    
    print()
    
    # Get explanation
    print("Getting AI explanation...")
    explanation = fixer.explain_issue(issue)
    
    if explanation:
        print("[OK] AI Explanation:")
        print("-" * 60)
        print(explanation)
        print("-" * 60)
    else:
        print("[FAIL] No explanation available")
    
    print()
    print()

print("=" * 60)
print("AI Fixer Test Complete")
print("=" * 60)

