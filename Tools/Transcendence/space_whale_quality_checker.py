#!/usr/bin/env python3
"""
Space Whale Asset Quality Checker
Details all results with quality scores using 20-level system (threshold: 14/20 for production)
"""

import json
import os
from pathlib import Path
from typing import Dict, List

# Import 20-level quality system
try:
    from space_whale_quality_system import (
        QualityLevel, get_quality_level, get_quality_threshold,
        format_quality_score, is_production_ready, get_quality_description
    )
    QUALITY_20_AVAILABLE = True
    PRODUCTION_THRESHOLD = get_quality_threshold("production")  # 17/20 (85%)
    REVIEW_THRESHOLD = get_quality_threshold("review")  # 12/20 (60%)
except ImportError:
    QUALITY_20_AVAILABLE = False
    PRODUCTION_THRESHOLD = 8.0  # Legacy threshold
    REVIEW_THRESHOLD = 6.0

def check_visual_language_quality(file_path: Path) -> Dict:
    """Check visual language asset quality."""
    if not file_path.exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    variations = data.get('variations', [])
    low_quality = []
    
    for var in variations:
        quality_data = var.get('quality', {})
        
        # Support both 20-level and legacy scoring
        if QUALITY_20_AVAILABLE:
            score = quality_data.get('overallScore', quality_data.get('score', 0))
            # Convert legacy 0-5 scale to 1-20 if needed
            if score <= 5.0:
                score = int(score * 4 + 1)  # Map 0-5 to 1-20
            score = int(score)
        else:
            score = quality_data.get('score', 0)
        
        if score < PRODUCTION_THRESHOLD:
            level_name = "UNKNOWN"
            if QUALITY_20_AVAILABLE:
                level = get_quality_level(score)
                level_name = level.name
            
            low_quality.append({
                'variation_id': var.get('variation_id', 'unknown'),
                'score': score,
                'score_max': 20 if QUALITY_20_AVAILABLE else 5,
                'level': level_name,
                'baseColor': var.get('baseColor', 'N/A'),
                'veinColor': var.get('veinColor', 'N/A'),
                'rationale': var.get('rationale', '')[:100],
                'notes': quality_data.get('notes', [])
            })
    
    return {
        'type': 'Visual Language',
        'total': len(variations),
        'low_quality_count': len(low_quality),
        'low_quality': low_quality
    }

def check_fx_quality(file_path: Path) -> Dict:
    """Check FX asset quality."""
    if not file_path.exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    effects = data.get('effects', [])
    total_vars = 0
    low_quality = []
    
    for effect in effects:
        base_id = effect.get('baseId', 'unknown')
        variations = effect.get('variations', [])
        total_vars += len(variations)
        
        for var in variations:
            quality = var.get('quality', {})
            
            # Support both 20-level and legacy scoring
            if QUALITY_20_AVAILABLE:
                score = quality.get('overallScore', quality.get('score', 0))
                # Convert legacy 0-5 scale to 1-20 if needed
                if isinstance(score, float) and score <= 5.0:
                    score = int(score * 4 + 1)  # Map 0-5 to 1-20
                score = int(score)
                level_name = quality.get('level', get_quality_level(score).name)
            else:
                score = quality.get('overallScore', 0)
                level_name = quality.get('tier', 'UNKNOWN')
            
            if score < PRODUCTION_THRESHOLD:
                # Get individual scores (convert if needed)
                visual = quality.get('visualQuality', 0)
                features = quality.get('featureCompleteness', 0)
                technical = quality.get('technicalQuality', 0)
                aesthetic = quality.get('aestheticAppeal', 0)
                
                # Convert legacy scores to 20-level if needed
                if QUALITY_20_AVAILABLE and isinstance(visual, float) and visual <= 5.0:
                    visual = int(visual * 4 + 1)
                    features = int(features * 4 + 1) if isinstance(features, float) else features
                    technical = int(technical * 4 + 1) if isinstance(technical, float) else technical
                    aesthetic = int(aesthetic * 4 + 1) if isinstance(aesthetic, float) else aesthetic
                
                low_quality.append({
                    'effect_id': base_id,
                    'variation_id': var.get('id', 'unknown'),
                    'score': score,
                    'score_max': 20 if QUALITY_20_AVAILABLE else 5,
                    'level': level_name,
                    'visual': visual,
                    'features': features,
                    'technical': technical,
                    'aesthetic': aesthetic,
                    'notes': quality.get('notes', [])
                })
    
    return {
        'type': 'FX Assets',
        'total': total_vars,
        'low_quality_count': len(low_quality),
        'low_quality': low_quality
    }

def generate_quality_report(output_dir: Path):
    """Generate comprehensive quality report for all assets."""
    
    reports = []
    
    # Check Visual Language
    visual_file = output_dir / "VisualLanguage" / "ollama_palette_variations.json"
    if visual_file.exists():
        result = check_visual_language_quality(visual_file)
        if result:
            reports.append(result)
    
    # Check FX Assets
    fx_files = [
        output_dir.parent / "space_whale_fx_registry_placeholders.json",
        output_dir.parent / "space_whale_fx_registry_best.json"
    ]
    
    for fx_file in fx_files:
        if fx_file.exists():
            result = check_fx_quality(fx_file)
            if result:
                result['type'] = f"FX Assets ({fx_file.name})"
                reports.append(result)
    
    # Generate markdown report
    report_path = output_dir / "QUALITY_REPORT_LOW_SCORES.md"
    
    score_max = 20 if QUALITY_20_AVAILABLE else 5
    threshold_text = f"{PRODUCTION_THRESHOLD}/{score_max}" if QUALITY_20_AVAILABLE else f"{PRODUCTION_THRESHOLD:.1f}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Space Whale Asset Quality Report - Below Production Threshold (< {threshold_text})\n\n")
        f.write(f"This report details all generated assets with quality scores below {threshold_text}.\n")
        if QUALITY_20_AVAILABLE:
            f.write(f"**Quality System**: 20-level system (1-20 scale)\n")
            f.write(f"**Production Threshold**: {PRODUCTION_THRESHOLD}/20 (85% - EXCELLENT tier)\n")
            f.write(f"**Review Threshold**: {REVIEW_THRESHOLD}/20 (60%)\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        total_all = 0
        total_low = 0
        
        for report in reports:
            total_all += report['total']
            total_low += report['low_quality_count']
            
            f.write(f"## {report['type']}\n\n")
            f.write(f"- **Total Variations**: {report['total']}\n")
            f.write(f"- **Below Threshold (< {threshold_text})**: {report['low_quality_count']}\n")
            f.write(f"- **Production Ready (>= {threshold_text})**: {report['total'] - report['low_quality_count']}\n")
            if report['total'] > 0:
                quality_rate = (report['total'] - report['low_quality_count']) / report['total'] * 100
                f.write(f"- **Production Ready Rate**: {quality_rate:.1f}%\n\n")
            else:
                f.write(f"- **Production Ready Rate**: N/A\n\n")
            
            if report['low_quality']:
                f.write("### Detailed Low Quality Results\n\n")
                f.write("| # | ID | Score | Details | Notes |\n")
                f.write("|---|----|----|---------|-------|\n")
                
                for i, item in enumerate(report['low_quality'], 1):
                    score_val = item.get('score', 0)
                    score_max_val = item.get('score_max', score_max)
                    level_name = item.get('level', 'UNKNOWN')
                    
                    if report['type'] == 'Visual Language':
                        f.write(f"| {i} | {item['variation_id']} | {score_val}/{score_max_val} ({level_name}) | ")
                        f.write(f"{item['baseColor']} / {item['veinColor']} | ")
                        f.write(f"{', '.join(item['notes'][:3])} |\n")
                    else:
                        f.write(f"| {i} | {item['variation_id']} | {score_val}/{score_max_val} ({level_name}) | ")
                        f.write(f"Effect: {item['effect_id']} | ")
                        f.write(f"Level: {level_name} |\n")
                
                f.write("\n")
                
                # Detailed breakdown for first 10
                f.write("### Detailed Breakdown (First 10)\n\n")
                for i, item in enumerate(report['low_quality'][:10], 1):
                    f.write(f"#### {i}. Variation {item.get('variation_id', 'unknown')}\n\n")
                    
                    score_val = item.get('score', 0)
                    score_max_val = item.get('score_max', score_max)
                    level_name = item.get('level', 'UNKNOWN')
                    
                    f.write(f"- **Score**: {score_val}/{score_max_val} ({level_name})\n")
                    if QUALITY_20_AVAILABLE:
                        f.write(f"- **Description**: {get_quality_description(score_val)}\n")
                    
                    if 'baseColor' in item:
                        f.write(f"- **Colors**: {item['baseColor']} / {item['veinColor']}\n")
                        f.write(f"- **Rationale**: {item.get('rationale', 'N/A')}\n")
                    else:
                        f.write(f"- **Effect**: {item['effect_id']}\n")
                        f.write(f"- **Level**: {level_name}\n")
                        f.write(f"- **Visual**: {item['visual']}/{score_max_val}\n")
                        f.write(f"- **Features**: {item['features']}/{score_max_val}\n")
                        f.write(f"- **Technical**: {item['technical']}/{score_max_val}\n")
                        f.write(f"- **Aesthetic**: {item['aesthetic']}/{score_max_val}\n")
                    
                    if item.get('notes'):
                        f.write(f"- **Notes**: {', '.join(item['notes'][:5])}\n")
                    
                    f.write("\n")
            
            f.write("\n" + "-" * 80 + "\n\n")
        
        # Summary
        f.write("## Overall Summary\n\n")
        f.write(f"- **Total Variations Generated**: {total_all}\n")
        f.write(f"- **Below Threshold (< {threshold_text})**: {total_low}\n")
        f.write(f"- **Production Ready (>= {threshold_text})**: {total_all - total_low}\n")
        if total_all > 0:
            quality_rate = (total_all - total_low) / total_all * 100
            f.write(f"- **Production Ready Rate**: {quality_rate:.1f}%\n\n")
        else:
            f.write(f"- **Production Ready Rate**: N/A\n\n")
        
        f.write("## Recommendations\n\n")
        if QUALITY_20_AVAILABLE:
            f.write(f"1. **Review variations below threshold** (< {PRODUCTION_THRESHOLD}/20) and consider regeneration\n")
            f.write(f"2. **Focus on production-ready variations** (>= {PRODUCTION_THRESHOLD}/20) for production use\n")
            f.write(f"3. **Manual review recommended** for variations scoring {REVIEW_THRESHOLD}-{PRODUCTION_THRESHOLD-1}/20 (may still be usable)\n")
            f.write(f"4. **Regenerate variations** scoring below {REVIEW_THRESHOLD}/20\n")
            f.write("5. **Use filtered placeholders** that exclude low-quality variations\n")
            f.write("6. **Consider adjusting generation parameters** for better results\n")
        else:
            f.write("1. **Review low-quality variations** and consider regeneration with adjusted parameters\n")
            if QUALITY_20_AVAILABLE:
                f.write(f"2. **Focus on production-ready variations** (score >= {PRODUCTION_THRESHOLD}/20) for production use\n")
            else:
                f.write("2. **Focus on high-quality variations** (score >= 8.0) for production use\n")
            f.write("3. **Use filtered placeholders** that exclude low-quality variations\n")
            f.write("4. **Consider adjusting generation parameters** for better results\n")
            f.write("5. **Manual review recommended** for variations scoring 7.0-7.9 (may still be usable)\n")
            f.write("6. **Regenerate variations** scoring below 7.0\n")
    
    score_max = 20 if QUALITY_20_AVAILABLE else 5
    threshold_text = f"{PRODUCTION_THRESHOLD}/{score_max}" if QUALITY_20_AVAILABLE else f"{PRODUCTION_THRESHOLD:.1f}"
    
    print(f"Quality report saved: {report_path}")
    print(f"\nSummary:")
    print(f"  Total variations: {total_all}")
    print(f"  Below threshold (< {threshold_text}): {total_low}")
    print(f"  Production ready (>= {threshold_text}): {total_all - total_low}")
    if total_all > 0:
        quality_rate = (total_all - total_low) / total_all * 100
        print(f"  Production ready rate: {quality_rate:.1f}%")
    else:
        print(f"  Production ready rate: N/A")

if __name__ == "__main__":
    import sys
    
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Output/SpaceWhaleComprehensive")
    generate_quality_report(output_dir)

