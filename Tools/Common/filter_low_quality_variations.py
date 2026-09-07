#!/usr/bin/env python3
"""Filter out low quality variations from generated palette variations"""

import json
import sys
import os

def filter_variations(input_path, output_path, min_score=7.0):
    """Filter variations by minimum quality score"""
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    variations = data.get('variations', [])
    original_count = len(variations)
    
    # Filter by score
    filtered = []
    for v in variations:
        score = v.get('quality', {}).get('score', 0)
        if score >= min_score:
            filtered.append(v)
    
    filtered_count = len(filtered)
    removed_count = original_count - filtered_count
    
    # Update data
    data['variations'] = filtered
    data['top_10'] = sorted(filtered, key=lambda x: x.get('quality', {}).get('score', 0), reverse=True)[:10]
    
    # Add metadata about filtering
    if 'filtering' not in data:
        data['filtering'] = {}
    data['filtering'] = {
        'min_score': min_score,
        'original_count': original_count,
        'filtered_count': filtered_count,
        'removed_count': removed_count
    }
    
    # Save filtered results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Filtered variations:")
    print(f"  Original: {original_count}")
    print(f"  Kept (score >= {min_score}): {filtered_count}")
    print(f"  Removed (score < {min_score}): {removed_count}")
    print(f"\nFiltered results saved to: {output_path}")
    
    # Score distribution of kept variations
    scores = [v.get('quality', {}).get('score', 0) for v in filtered]
    if scores:
        score_85 = sum(1 for s in scores if s == 8.5)
        score_70 = sum(1 for s in scores if 7.0 <= s < 8.5)
        avg_score = sum(scores) / len(scores)
        
        print(f"\nKept variations distribution:")
        print(f"  8.5 (Excellent): {score_85}")
        print(f"  7.0-8.4 (Good): {score_70}")
        print(f"  Average score: {avg_score:.2f}")

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "Output/OllamaVariations/ollama_palette_variations.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file  # Overwrite by default
    min_score = float(sys.argv[3]) if len(sys.argv) > 3 else 7.0
    
    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)
    
    print(f"Filtering variations (keeping score >= {min_score})...")
    filter_variations(input_file, output_file, min_score)
    print("\n[COMPLETE] Low quality variations removed.")

