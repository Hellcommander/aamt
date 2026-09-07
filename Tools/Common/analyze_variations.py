#!/usr/bin/env python3
"""Analyze generated variations to verify AI generation"""

import json
import sys

def analyze_variations(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    variations = data['variations']
    model = data['generation']['model']
    
    print(f"Model used: {model}")
    print(f"Total variations: {len(variations)}")
    print()
    
    # Count AI-generated vs fallback
    ai_generated = []
    fallback = []
    
    for v in variations:
        rationale = v.get('rationale', '')
        if rationale.startswith('Programmatically generated'):
            fallback.append(v)
        else:
            ai_generated.append(v)
    
    print(f"AI-generated (with detailed rationale): {len(ai_generated)}")
    print(f"Fallback (programmatic): {len(fallback)}")
    print()
    
    # Unique color combinations
    unique_palettes = {}
    for v in variations:
        key = (v.get('baseColor'), v.get('veinColor'))
        if key not in unique_palettes:
            unique_palettes[key] = []
        unique_palettes[key].append(v.get('rationale', '')[:60])
    
    print(f"Unique color combinations: {len(unique_palettes)}")
    print()
    
    # Show top AI-generated variations
    print("Top 10 AI-Generated Variations (by score):")
    ai_sorted = sorted(ai_generated, key=lambda x: x.get('quality', {}).get('score', 0), reverse=True)
    for i, v in enumerate(ai_sorted[:10], 1):
        score = v.get('quality', {}).get('score', 0)
        base = v.get('baseColor', 'N/A')
        vein = v.get('veinColor', 'N/A')
        rationale = v.get('rationale', '')[:100]
        print(f"{i}. Score: {score} - {base} / {vein}")
        print(f"   {rationale}...")
        print()
    
    # Score distribution
    scores = [v.get('quality', {}).get('score', 0) for v in variations]
    score_85 = sum(1 for s in scores if s == 8.5)
    score_70 = sum(1 for s in scores if 7.0 <= s < 8.5)
    score_low = sum(1 for s in scores if s < 7.0)
    
    print(f"\nScore Distribution:")
    print(f"  8.5 (Excellent): {score_85}")
    print(f"  7.0-8.4 (Good): {score_70}")
    print(f"  <7.0 (Low): {score_low}")
    print(f"  Average: {sum(scores)/len(scores):.2f}")

if __name__ == "__main__":
    json_path = sys.argv[1] if len(sys.argv) > 1 else "Output/OllamaVariations/ollama_palette_variations.json"
    analyze_variations(json_path)

