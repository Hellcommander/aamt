#!/usr/bin/env python3
"""
API Checker for Mod Fixer
Checks mod code against current Transcendence API source.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class ApiIssue:
    """Represents an API compatibility issue."""
    severity: str  # "error", "warning", "info"
    file: str
    line: Optional[int]
    code: str
    message: str
    suggestion: Optional[str] = None
    deprecated_item: Optional[str] = None
    replacement: Optional[str] = None


class ApiChecker:
    """Checks mod code against Transcendence API rules."""
    
    def __init__(self, api_rules_path: Optional[str] = None):
        """
        Initialize API checker.
        
        Args:
            api_rules_path: Path to api_rules.json (auto-detects if None)
        """
        if api_rules_path is None:
            # Auto-detect API rules file
            tools_dir = Path(__file__).parent
            # Try API 59 first (latest), then fall back
            for version in [59, 58, 57, 56]:
                rules_file = tools_dir / f"api_rules_{version}.json"
                if rules_file.exists():
                    api_rules_path = str(rules_file)
                    break
            
            # Fall back to default api_rules.json
            if api_rules_path is None:
                api_rules_path = str(tools_dir / "api_rules.json")
        
        self.api_rules_path = Path(api_rules_path)
        self.rules: Dict[str, Any] = {}
        self._load_rules()
    
    def _load_rules(self):
        """Load API rules from JSON file."""
        if not self.api_rules_path.exists():
            raise FileNotFoundError(f"API rules file not found: {self.api_rules_path}")
        
        with open(self.api_rules_path, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
    
    @property
    def api_version(self) -> int:
        """Get API version from rules."""
        return self.rules.get('ApiVersion', 57)
    
    @property
    def deprecated_tags(self) -> List[str]:
        """Get list of deprecated tags."""
        deprecated = self.rules.get('Deprecated', {})
        return deprecated.get('Tags', [])
    
    @property
    def deprecated_functions(self) -> List[str]:
        """Get list of deprecated functions."""
        deprecated = self.rules.get('Deprecated', {})
        return deprecated.get('Functions', [])
    
    @property
    def deprecated_attributes(self) -> Dict[str, List[str]]:
        """Get deprecated attributes by tag."""
        deprecated = self.rules.get('Deprecated', {})
        return deprecated.get('Attributes', {})
    
    @property
    def available_tags(self) -> Dict[str, Any]:
        """Get available tags from API."""
        return self.rules.get('Tags', {})
    
    @property
    def available_functions(self) -> Dict[str, Any]:
        """Get available functions from API."""
        return self.rules.get('Functions', {})
    
    def check_file(self, file_path: Path) -> List[ApiIssue]:
        """
        Check a single file for API compatibility issues.
        
        Args:
            file_path: Path to XML file to check
            
        Returns:
            List of ApiIssue objects
        """
        issues = []
        
        if not file_path.exists():
            return issues
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            issues.append(ApiIssue(
                severity="error",
                file=str(file_path),
                line=None,
                code="FILE_READ_ERROR",
                message=f"Cannot read file: {e}"
            ))
            return issues
        
        # Check API version
        api_version_issues = self._check_api_version(content, file_path)
        issues.extend(api_version_issues)
        
        # Check deprecated functions
        function_issues = self._check_deprecated_functions(content, lines, file_path)
        issues.extend(function_issues)
        
        # Check deprecated tags
        tag_issues = self._check_deprecated_tags(content, lines, file_path)
        issues.extend(tag_issues)
        
        # Check deprecated attributes
        attr_issues = self._check_deprecated_attributes(content, lines, file_path)
        issues.extend(attr_issues)
        
        # Check for unknown tags
        unknown_tag_issues = self._check_unknown_tags(content, lines, file_path)
        issues.extend(unknown_tag_issues)
        
        # Check for unknown functions
        unknown_func_issues = self._check_unknown_functions(content, lines, file_path)
        issues.extend(unknown_func_issues)
        
        return issues
    
    def _check_api_version(self, content: str, file_path: Path) -> List[ApiIssue]:
        """Check if mod declares correct API version."""
        issues = []
        
        # Look for apiVersion attribute
        api_version_match = re.search(r'apiVersion\s*=\s*["\'](\d+)["\']', content)
        if api_version_match:
            mod_api_version = int(api_version_match.group(1))
            current_api_version = self.api_version
            
            if mod_api_version < current_api_version:
                issues.append(ApiIssue(
                    severity="warning",
                    file=str(file_path),
                    line=None,
                    code="OUTDATED_API_VERSION",
                    message=f"Mod uses API {mod_api_version}, but current API is {current_api_version}",
                    suggestion=f"Update apiVersion=\"{current_api_version}\""
                ))
        else:
            # No API version declared
            issues.append(ApiIssue(
                severity="info",
                file=str(file_path),
                line=None,
                code="NO_API_VERSION",
                message="No apiVersion attribute found",
                suggestion=f"Add apiVersion=\"{self.api_version}\" to root element"
            ))
        
        return issues
    
    def _check_deprecated_functions(self, content: str, lines: List[str], file_path: Path) -> List[ApiIssue]:
        """Check for deprecated function usage."""
        issues = []
        deprecated_funcs = self.deprecated_functions
        
        for func_name in deprecated_funcs:
            # Pattern for function calls: (funcName ...) or funcName(...)
            patterns = [
                rf'\({re.escape(func_name)}\s+',  # (funcName ...
                rf'{re.escape(func_name)}\s*\(',  # funcName(...
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                    
                    issues.append(ApiIssue(
                        severity="error",
                        file=str(file_path),
                        line=line_num,
                        code="DEPRECATED_FUNCTION",
                        message=f"Deprecated function '{func_name}' used",
                        deprecated_item=func_name,
                        suggestion=f"Replace '{func_name}' with recommended alternative (check API migration guide)"
                    ))
        
        return issues
    
    def _check_deprecated_tags(self, content: str, lines: List[str], file_path: Path) -> List[ApiIssue]:
        """Check for deprecated tag usage."""
        issues = []
        deprecated_tags = self.deprecated_tags
        
        for tag_name in deprecated_tags:
            # Pattern for XML tags: <TagName ...> or <TagName/>
            pattern = rf'<{re.escape(tag_name)}\s+[^>]*>|<{re.escape(tag_name)}/>'
            
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                
                issues.append(ApiIssue(
                    severity="error",
                    file=str(file_path),
                    line=line_num,
                    code="DEPRECATED_TAG",
                    message=f"Deprecated tag '<{tag_name}>' used",
                    deprecated_item=tag_name,
                    suggestion=f"Replace '<{tag_name}>' with recommended alternative"
                ))
        
        return issues
    
    def _check_deprecated_attributes(self, content: str, lines: List[str], file_path: Path) -> List[ApiIssue]:
        """Check for deprecated attribute usage."""
        issues = []
        deprecated_attrs = self.deprecated_attributes
        
        for tag_name, attrs in deprecated_attrs.items():
            for attr_name in attrs:
                # Pattern: <TagName ... attrName="..." ...>
                pattern = rf'<{re.escape(tag_name)}\s+[^>]*\b{re.escape(attr_name)}\s*=\s*["\'][^"\']*["\']'
                
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count('\n') + 1
                    
                    issues.append(ApiIssue(
                        severity="warning",
                        file=str(file_path),
                        line=line_num,
                        code="DEPRECATED_ATTRIBUTE",
                        message=f"Deprecated attribute '{attr_name}' used in '<{tag_name}>'",
                        deprecated_item=attr_name,
                        suggestion=f"Remove or replace '{attr_name}' attribute"
                    ))
        
        return issues
    
    def _check_unknown_tags(self, content: str, lines: List[str], file_path: Path) -> List[ApiIssue]:
        """Check for tags that don't exist in current API."""
        issues = []
        available_tags = set(self.available_tags.keys())
        
        # Find all XML tags
        tag_pattern = r'<([a-zA-Z][a-zA-Z0-9_]*)\s'
        for match in re.finditer(tag_pattern, content):
            tag_name = match.group(1)
            
            # Skip common XML/DOCTYPE tags
            if tag_name.lower() in ['xml', 'doctype', 'transcendenceextension', 
                                   'transcendencelibrary', 'transcendencemodule',
                                   'transcendenceadventure', 'transcendenceuniverse']:
                continue
            
            if tag_name not in available_tags:
                line_num = content[:match.start()].count('\n') + 1
                
                issues.append(ApiIssue(
                    severity="warning",
                    file=str(file_path),
                    line=line_num,
                    code="UNKNOWN_TAG",
                    message=f"Tag '<{tag_name}>' not found in API {self.api_version}",
                    suggestion="Verify tag name or check if it's a custom tag"
                ))
        
        return issues
    
    def _check_unknown_functions(self, content: str, lines: List[str], file_path: Path) -> List[ApiIssue]:
        """Check for functions that don't exist in current API."""
        issues = []
        available_functions = set(self.available_functions.keys())
        
        # Find function calls: (funcName ...)
        func_pattern = r'\(([a-zA-Z][a-zA-Z0-9_]*)\s'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            
            # Skip common operators and keywords
            if func_name.lower() in ['block', 'if', 'switch', 'setq', 'set', 'obj', 'itm', 'shp', 'sys']:
                continue
            
            if func_name not in available_functions:
                line_num = content[:match.start()].count('\n') + 1
                
                issues.append(ApiIssue(
                    severity="info",
                    file=str(file_path),
                    line=line_num,
                    code="UNKNOWN_FUNCTION",
                    message=f"Function '{func_name}' not found in API {self.api_version}",
                    suggestion="Verify function name or check if it's a custom function"
                ))
        
        return issues
    
    def check_mod(self, mod_path: Path) -> Dict[str, List[ApiIssue]]:
        """
        Check entire mod for API compatibility issues.
        
        Args:
            mod_path: Path to mod directory
            
        Returns:
            Dictionary mapping file paths to lists of issues
        """
        all_issues = {}
        
        if not mod_path.exists():
            return all_issues
        
        # Find all XML files
        xml_files = list(mod_path.rglob("*.xml"))
        
        for xml_file in xml_files:
            issues = self.check_file(xml_file)
            if issues:
                all_issues[str(xml_file.relative_to(mod_path))] = issues
        
        return all_issues
    
    def generate_api_check_report(self, mod_path: Path) -> Dict[str, Any]:
        """
        Generate comprehensive API check report.
        
        Args:
            mod_path: Path to mod directory
            
        Returns:
            Dictionary with report data
        """
        issues_by_file = self.check_mod(mod_path)
        
        total_issues = sum(len(issues) for issues in issues_by_file.values())
        errors = sum(1 for issues in issues_by_file.values() for issue in issues if issue.severity == "error")
        warnings = sum(1 for issues in issues_by_file.values() for issue in issues if issue.severity == "warning")
        infos = sum(1 for issues in issues_by_file.values() for issue in issues if issue.severity == "info")
        
        return {
            "api_version": self.api_version,
            "api_rules_file": str(self.api_rules_path),
            "mod_path": str(mod_path),
            "total_issues": total_issues,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "issues_by_file": {
                file_path: [
                    {
                        "severity": issue.severity,
                        "line": issue.line,
                        "code": issue.code,
                        "message": issue.message,
                        "suggestion": issue.suggestion,
                        "deprecated_item": issue.deprecated_item,
                        "replacement": issue.replacement
                    }
                    for issue in issues
                ]
                for file_path, issues in issues_by_file.items()
            }
        }


def main():
    """CLI entry point for API checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check mod against Transcendence API")
    parser.add_argument('mod_path', help='Path to mod directory')
    parser.add_argument('--api-rules', help='Path to api_rules.json (auto-detects if not provided)')
    parser.add_argument('--output', help='Output JSON report file')
    parser.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"Error: Mod path not found: {mod_path}")
        return 1
    
    try:
        checker = ApiChecker(args.api_rules)
        print(f"Checking mod against API {checker.api_version}...")
        print(f"Using rules: {checker.api_rules_path}")
        print()
        
        report = checker.generate_api_check_report(mod_path)
        
        if args.format == 'json':
            output = json.dumps(report, indent=2)
            print(output)
        else:
            # Text format
            print("=" * 60)
            print("API COMPATIBILITY REPORT")
            print("=" * 60)
            print(f"API Version: {report['api_version']}")
            print(f"Total Issues: {report['total_issues']}")
            print(f"  Errors: {report['errors']}")
            print(f"  Warnings: {report['warnings']}")
            print(f"  Info: {report['infos']}")
            print()
            
            for file_path, issues in report['issues_by_file'].items():
                if issues:
                    print(f"\n{file_path}:")
                    for issue in issues:
                        severity_icon = {
                            "error": "✗",
                            "warning": "!",
                            "info": "i"
                        }.get(issue['severity'], "?")
                        
                        line_info = f" (line {issue['line']})" if issue['line'] else ""
                        print(f"  {severity_icon} [{issue['code']}]{line_info}: {issue['message']}")
                        if issue['suggestion']:
                            print(f"    → {issue['suggestion']}")
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {args.output}")
        
        return 0 if report['errors'] == 0 else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

