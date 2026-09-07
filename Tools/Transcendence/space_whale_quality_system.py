#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Space Whale 20-Level Quality Assessment System
Provides granular quality scoring from 1-20 for precise asset evaluation.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

class QualityLevel(Enum):
    """20-level quality system for precise assessment."""
    # Excellent tier (17-20)
    PERFECT = 20      # Perfect quality, production-ready
    EXCEPTIONAL = 19  # Exceptional quality, minor polish needed
    EXCELLENT_PLUS = 18  # Excellent with minor enhancements
    EXCELLENT = 17    # Excellent quality
    
    # Very Good tier (13-16)
    VERY_GOOD_PLUS = 16  # Very good with enhancements
    VERY_GOOD = 15    # Very good quality
    GOOD_PLUS = 14    # Good with enhancements
    GOOD = 13         # Good quality
    
    # Acceptable tier (9-12)
    ACCEPTABLE_PLUS = 12  # Acceptable with minor improvements
    ACCEPTABLE = 11    # Acceptable quality
    FAIR_PLUS = 10     # Fair with minor improvements
    FAIR = 9           # Fair quality
    
    # Needs Improvement tier (5-8)
    NEEDS_WORK_PLUS = 8   # Needs work but close
    NEEDS_WORK = 7     # Needs significant work
    POOR_PLUS = 6      # Poor but salvageable
    POOR = 5           # Poor quality
    
    # Unacceptable tier (1-4)
    VERY_POOR = 4      # Very poor, major issues
    UNACCEPTABLE = 3   # Unacceptable quality
    CRITICAL = 2       # Critical issues
    REJECT = 1         # Should be rejected

@dataclass
class QualityScore20:
    """20-level quality score with detailed breakdown."""
    visual_quality: int = 1          # 1-20
    feature_completeness: int = 1    # 1-20
    technical_quality: int = 1       # 1-20
    aesthetic_appeal: int = 1        # 1-20
    overall: int = 1                 # 1-20 (weighted average)
    level: QualityLevel = QualityLevel.REJECT
    notes: List[str] = field(default_factory=list)
    
    @classmethod
    def from_scores(cls, visual: float, feature: float, technical: float, 
                   aesthetic: float, notes: List[str] = None) -> 'QualityScore20':
        """
        Create QualityScore20 from 0-5 scale scores (for backward compatibility).
        Maps 0-5 scale to 1-20 scale.
        """
        # Map 0-5 to 1-20: multiply by 4, add 1, clamp to 1-20
        visual_20 = max(1, min(20, int(visual * 4 + 1)))
        feature_20 = max(1, min(20, int(feature * 4 + 1)))
        technical_20 = max(1, min(20, int(technical * 4 + 1)))
        aesthetic_20 = max(1, min(20, int(aesthetic * 4 + 1)))
        
        # Weighted overall (same weights as before)
        overall_20 = max(1, min(20, int(
            (visual_20 * 0.3 +
             feature_20 * 0.25 +
             technical_20 * 0.25 +
             aesthetic_20 * 0.2)
        )))
        
        # Determine quality level
        level = get_quality_level(overall_20)
        
        return cls(
            visual_quality=visual_20,
            feature_completeness=feature_20,
            technical_quality=technical_20,
            aesthetic_appeal=aesthetic_20,
            overall=overall_20,
            level=level,
            notes=notes or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'visualQuality': self.visual_quality,
            'featureCompleteness': self.feature_completeness,
            'technicalQuality': self.technical_quality,
            'aestheticAppeal': self.aesthetic_appeal,
            'overallScore': self.overall,
            'level': self.level.name,
            'levelValue': self.level.value,
            'notes': self.notes
        }

def get_quality_level(score: int) -> QualityLevel:
    """
    Get QualityLevel enum from 1-20 score.
    
    Args:
        score: Quality score from 1-20
    
    Returns:
        QualityLevel enum value
    """
    if score >= 20:
        return QualityLevel.PERFECT
    elif score >= 19:
        return QualityLevel.EXCEPTIONAL
    elif score >= 18:
        return QualityLevel.EXCELLENT_PLUS
    elif score >= 17:
        return QualityLevel.EXCELLENT
    elif score >= 16:
        return QualityLevel.VERY_GOOD_PLUS
    elif score >= 15:
        return QualityLevel.VERY_GOOD
    elif score >= 14:
        return QualityLevel.GOOD_PLUS
    elif score >= 13:
        return QualityLevel.GOOD
    elif score >= 12:
        return QualityLevel.ACCEPTABLE_PLUS
    elif score >= 11:
        return QualityLevel.ACCEPTABLE
    elif score >= 10:
        return QualityLevel.FAIR_PLUS
    elif score >= 9:
        return QualityLevel.FAIR
    elif score >= 8:
        return QualityLevel.NEEDS_WORK_PLUS
    elif score >= 7:
        return QualityLevel.NEEDS_WORK
    elif score >= 6:
        return QualityLevel.POOR_PLUS
    elif score >= 5:
        return QualityLevel.POOR
    elif score >= 4:
        return QualityLevel.VERY_POOR
    elif score >= 3:
        return QualityLevel.UNACCEPTABLE
    elif score >= 2:
        return QualityLevel.CRITICAL
    else:
        return QualityLevel.REJECT

def get_quality_threshold(threshold_name: str = "production") -> int:
    """
    Get quality threshold score for different use cases.
    
    Args:
        threshold_name: Threshold type
            - "production": Minimum for production use (17/20 = 85%)
            - "high": High quality threshold (18/20 = 90%)
            - "excellent": Excellent quality threshold (19/20 = 95%)
            - "acceptable": Minimum acceptable (17/20 = 85%, B+ grade - EXCELLENT tier)
            - "review": Needs review threshold (12/20 = 60%)
    
    Returns:
        Threshold score (1-20)
    """
    thresholds = {
        "production": 17,   # 85% - minimum for production use (EXCELLENT tier)
        "high": 18,         # 90% - high quality (EXCELLENT_PLUS tier)
        "excellent": 19,    # 95% - excellent quality (EXCEPTIONAL tier)
        "acceptable": 17,   # 85% - minimum acceptable (B+ grade - EXCELLENT tier)
        "review": 12,       # 60% - needs review (ACCEPTABLE_PLUS tier)
        "reject": 10        # 50% - should be rejected (FAIR_PLUS tier)
    }
    return thresholds.get(threshold_name.lower(), 17)

def format_quality_score(score: int) -> str:
    """Format quality score for display."""
    level = get_quality_level(score)
    return f"{score}/20 ({level.name})"

def is_production_ready(score: int, threshold: int = None) -> bool:
    """Check if score meets production threshold."""
    if threshold is None:
        threshold = get_quality_threshold("production")
    return score >= threshold

def get_quality_description(score: int) -> str:
    """Get human-readable quality description."""
    level = get_quality_level(score)
    descriptions = {
        QualityLevel.PERFECT: "Perfect quality, production-ready without changes",
        QualityLevel.EXCEPTIONAL: "Exceptional quality, minor polish may enhance",
        QualityLevel.EXCELLENT_PLUS: "Excellent quality with minor enhancements possible",
        QualityLevel.EXCELLENT: "Excellent quality, production-ready",
        QualityLevel.VERY_GOOD_PLUS: "Very good quality, minor improvements recommended",
        QualityLevel.VERY_GOOD: "Very good quality, suitable for production",
        QualityLevel.GOOD_PLUS: "Good quality with room for enhancement",
        QualityLevel.GOOD: "Good quality, acceptable for production",
        QualityLevel.ACCEPTABLE_PLUS: "Acceptable quality, improvements recommended",
        QualityLevel.ACCEPTABLE: "Acceptable quality, may need review",
        QualityLevel.FAIR_PLUS: "Fair quality, significant improvements needed",
        QualityLevel.FAIR: "Fair quality, review recommended",
        QualityLevel.NEEDS_WORK_PLUS: "Needs work, close to acceptable",
        QualityLevel.NEEDS_WORK: "Needs significant work",
        QualityLevel.POOR_PLUS: "Poor quality but potentially salvageable",
        QualityLevel.POOR: "Poor quality, regeneration recommended",
        QualityLevel.VERY_POOR: "Very poor quality, should be regenerated",
        QualityLevel.UNACCEPTABLE: "Unacceptable quality, must be regenerated",
        QualityLevel.CRITICAL: "Critical issues, must be regenerated",
        QualityLevel.REJECT: "Should be rejected, regeneration required"
    }
    return descriptions.get(level, "Unknown quality level")
