"""
Fix UNID encoding in XML files.
Transcendence expects literal & in UNIDs, not &amp;
This script fixes the encoding in generated XML files.
"""

import os
import sys
import argparse
import glob

def fix_unid_encoding(file_path):
    """Fix UNID encoding in an XML file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace &amp; with & in UNID attributes
    # Pattern: UNID="&amp;..." or unid="&amp;..."
    import re
    content = re.sub(r'(UNID|unid)="&amp;([^"]+)"', r'\1="&\2"', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Fix UNID encoding in XML files')
    parser.add_argument('--file', help='Single XML file to fix')
    parser.add_argument('--dir', help='Directory containing XML files to fix')
    parser.add_argument('--pattern', default='*.xml', help='File pattern (default: *.xml)')
    
    args = parser.parse_args()
    
    files_to_fix = []
    
    if args.file:
        if os.path.exists(args.file):
            files_to_fix.append(args.file)
        else:
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
    elif args.dir:
        pattern = os.path.join(args.dir, '**', args.pattern)
        files_to_fix = glob.glob(pattern, recursive=True)
    else:
        print("Error: Must specify --file or --dir")
        sys.exit(1)
    
    fixed_count = 0
    for file_path in files_to_fix:
        try:
            fix_unid_encoding(file_path)
            print(f"Fixed: {file_path}")
            fixed_count += 1
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
    
    print(f"\nFixed {fixed_count} file(s)")

if __name__ == "__main__":
    main()

