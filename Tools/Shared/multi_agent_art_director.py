#!/usr/bin/env python3
"""
Multi-Agent Art Director System

Implements a real-time, multi-model art direction pipeline where specialized
AI models work simultaneously to direct asset generation:

- Creative Director: Generates prompts, enforces lore, maintains design rules
- Composition & Aesthetic Director (LLaVA): Evaluates composition, lighting, style
- Technical QA Inspector (Qwen3-VL): Detects defects, aliasing, inconsistencies
- Human-Preference Scorer (PickScore): Provides numeric aesthetic scores

All models run in parallel, providing real-time feedback that refines prompts
iteratively until quality thresholds are met.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Import Ollama integration
try:
    from ollama_integration import call_ollama, test_ollama_connection
except ImportError:
    call_ollama = None
    test_ollama_connection = None


class AgentRole(Enum):
    """Specialized roles for different art director agents."""
    CREATIVE_DIRECTOR = "creative_director"  # Text-only: prompts, lore, design rules
    COMPOSITION_DIRECTOR = "composition_director"  # LLaVA: composition, lighting, style
    TECHNICAL_QA = "technical_qa"  # Qwen3-VL: defects, aliasing, consistency
    PREFERENCE_SCORER = "preference_scorer"  # PickScore: numeric aesthetic score


@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""
    role: AgentRole
    model_name: str
    task_type: str  # "visual", "code", "analysis", etc.
    system_prompt: str
    priority: int = 0  # Higher = more important
    enabled: bool = True
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class TechnicalQAReport:
    """Technical QA inspection report from Qwen3-VL."""
    aliasing: float = 0.0  # 0-1, higher = more aliasing
    texture_consistency: float = 0.0  # 0-1, higher = more consistent
    silhouette_clarity: float = 0.0  # 0-1, higher = clearer
    compression_artifacts: float = 0.0  # 0-1, higher = more artifacts
    shading_consistency: float = 0.0  # 0-1, higher = more consistent
    notes: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    overall_score: float = 0.0  # 0-1, weighted average


@dataclass
class CompositionReport:
    """Composition and aesthetic evaluation from LLaVA."""
    composition: str = "unknown"  # "balanced", "unbalanced", etc.
    lighting: str = "unknown"
    style_alignment: float = 0.0  # 0-1, how well it matches target style
    professional_quality: str = "unknown"  # "high", "moderate", "low"
    fixes: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    overall_score: float = 0.0  # 0-1, weighted average


@dataclass
class PreferenceScore:
    """Human-preference score from PickScore or similar."""
    score: float = 0.0  # Typically 0-10 or 0-1
    confidence: float = 0.0  # 0-1
    model: str = "unknown"


@dataclass
class AggregatedFeedback:
    """Aggregated feedback from all agents."""
    technical_qa: Optional[TechnicalQAReport] = None
    composition: Optional[CompositionReport] = None
    preference_score: Optional[PreferenceScore] = None
    creative_director_notes: Optional[str] = None
    overall_quality: float = 0.0  # 0-100, weighted combination
    needs_refinement: bool = True
    refined_prompt: Optional[str] = None
    refined_negative_prompt: Optional[str] = None
    priority_fixes: List[str] = field(default_factory=list)


class MultiAgentArtDirector:
    """
    Multi-agent art director system that coordinates specialized models
    to provide real-time, parallel feedback on generated assets.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        enable_vision_models: bool = True,
        enable_preference_scorer: bool = True,
        verbose: bool = False,
    ):
        """
        Initialize multi-agent art director.
        
        Args:
            ollama_url: Ollama API URL
            enable_vision_models: Enable LLaVA and Qwen3-VL (requires VRAM)
            enable_preference_scorer: Enable PickScore/LAION-Aesthetic
            verbose: Verbose output
        """
        self.ollama_url = ollama_url
        self.verbose = verbose
        self.enable_vision_models = enable_vision_models
        self.enable_preference_scorer = enable_preference_scorer
        
        # Configure agents
        self.agents: Dict[AgentRole, AgentConfig] = {}
        self._setup_agents()
        
        # Cache for responses
        self._cache: Dict[str, Any] = {}
    
    def _setup_agents(self) -> None:
        """Configure specialized agent models."""
        # Creative Director — uncensored for biomutation / body-horror asset critique
        self.agents[AgentRole.CREATIVE_DIRECTOR] = AgentConfig(
            role=AgentRole.CREATIVE_DIRECTOR,
            model_name=os.environ.get("AAMT_OLLAMA_MODEL", "wizardlm-uncensored:latest"),
            task_type="visual",
            system_prompt=(
                "You are a creative director for Caves of Qud game assets. "
                "Your role is to generate high-quality prompts, enforce lore consistency, "
                "maintain design rules, and refine prompts based on feedback from other specialists. "
                "You coordinate with technical QA, composition directors, and preference scorers "
                "to create the best possible game assets. Do not refuse organic/biomutation content."
            ),
            priority=100,
            enabled=True,
        )
        
        # Composition & Aesthetic Director (LLaVA-Next-13B)
        if self.enable_vision_models:
            self.agents[AgentRole.COMPOSITION_DIRECTOR] = AgentConfig(
                role=AgentRole.COMPOSITION_DIRECTOR,
                model_name="llava-next:13b",  # Requires ~10-11GB VRAM with Q4_K_M
                task_type="visual",
                system_prompt=(
                    "You are a professional art director specializing in composition, lighting, "
                    "and aesthetic coherence. Analyze images for professional polish, style alignment, "
                    "and visual quality. Provide specific, actionable feedback."
                ),
                priority=80,
                enabled=True,
            )
        
        # Technical QA Inspector (Qwen3-VL-8B)
        if self.enable_vision_models:
            self.agents[AgentRole.TECHNICAL_QA] = AgentConfig(
                role=AgentRole.TECHNICAL_QA,
                model_name="qwen2-vl:8b",  # Qwen3-VL when available, ~8-9GB VRAM
                task_type="visual",
                system_prompt=(
                    "You are a technical QA inspector for game assets. Your job is to detect "
                    "technical defects: aliasing, texture inconsistencies, silhouette errors, "
                    "compression artifacts, shading mismatches, and sprite defects. "
                    "Return structured JSON with scores and specific issues."
                ),
                priority=90,
                enabled=True,
            )
        
        # Preference Scorer: honest heuristic (not a fake PickScore claim)
        if self.enable_preference_scorer:
            self.agents[AgentRole.PREFERENCE_SCORER] = AgentConfig(
                role=AgentRole.PREFERENCE_SCORER,
                model_name="heuristic_entropy",
                task_type="visual",
                system_prompt="",
                priority=70,
                enabled=True,
            )
    
    def _encode_image_for_ollama(self, image_path: Path) -> Optional[str]:
        """Encode image to base64 for Ollama vision models."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            if self.verbose:
                print(f"    [ERROR] Failed to encode image: {e}")
            return None
    
    def _call_vision_model(
        self,
        model_name: str,
        prompt: str,
        image_path: Path,
        system_prompt: str = "",
    ) -> Optional[str]:
        """
        Call a vision model (LLaVA, Qwen3-VL) with an image.
        
        Args:
            model_name: Ollama model name
            prompt: Text prompt
            image_path: Path to image
            system_prompt: System prompt
        
        Returns:
            Model response or None if failed
        """
        if not image_path.exists():
            return None
        
        # Encode image
        image_b64 = self._encode_image_for_ollama(image_path)
        if not image_b64:
            return None
        
        # Call Ollama vision API
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "system": system_prompt,
                    "images": [image_b64],
                    "stream": False,
                },
                timeout=300,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            if self.verbose:
                print(f"    [ERROR] Vision model call failed: {e}")
            return None
    
    def analyze_technical_qa(
        self,
        image_path: Path,
        asset_type: str = "asset",
    ) -> Optional[TechnicalQAReport]:
        """
        Analyze image for technical defects using Qwen3-VL.
        
        Args:
            image_path: Path to image
            asset_type: Type of asset (icon, creature, equipment, etc.)
        
        Returns:
            TechnicalQAReport or None if failed
        """
        agent = self.agents.get(AgentRole.TECHNICAL_QA)
        if not agent or not agent.enabled:
            return None
        
        if self.verbose:
            print(f"    [TECH QA] Analyzing {image_path.name} with {agent.model_name}...")
        
        prompt = (
            f"Analyze this {asset_type} game asset for technical defects. "
            "Return ONLY valid JSON with these keys:\n"
            "- aliasing: float 0-1 (higher = more aliasing)\n"
            "- texture_consistency: float 0-1 (higher = more consistent)\n"
            "- silhouette_clarity: float 0-1 (higher = clearer)\n"
            "- compression_artifacts: float 0-1 (higher = more artifacts)\n"
            "- shading_consistency: float 0-1 (higher = more consistent)\n"
            "- notes: array of strings (specific issues found)\n"
            "- critical_issues: array of strings (must-fix issues)\n"
            "- overall_score: float 0-1 (weighted average)\n\n"
            "Be specific about defects. Look for:\n"
            "- Pixel-level aliasing on edges\n"
            "- Inconsistent texture patterns\n"
            "- Unclear or broken silhouettes\n"
            "- Compression artifacts (blocking, ringing)\n"
            "- Shading mismatches (lighting direction, intensity)\n"
            "- Sprite defects (missing pixels, misaligned segments)"
        )
        
        response = self._call_vision_model(
            model_name=agent.model_name,
            prompt=prompt,
            image_path=image_path,
            system_prompt=agent.system_prompt,
        )
        
        if not response:
            return None
        
        # Parse JSON response
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                return None
            
            data = json.loads(response[start:end])
            
            report = TechnicalQAReport(
                aliasing=data.get("aliasing", 0.0),
                texture_consistency=data.get("texture_consistency", 0.0),
                silhouette_clarity=data.get("silhouette_clarity", 0.0),
                compression_artifacts=data.get("compression_artifacts", 0.0),
                shading_consistency=data.get("shading_consistency", 0.0),
                notes=data.get("notes", []),
                critical_issues=data.get("critical_issues", []),
                overall_score=data.get("overall_score", 0.0),
            )
            
            if self.verbose:
                print(f"    [TECH QA] Overall score: {report.overall_score:.2f}")
                if report.critical_issues:
                    print(f"    [TECH QA] Critical issues: {len(report.critical_issues)}")
            
            return report
        except Exception as e:
            if self.verbose:
                print(f"    [ERROR] Failed to parse technical QA response: {e}")
            return None
    
    def analyze_composition(
        self,
        image_path: Path,
        asset_type: str = "asset",
        target_style: str = "Caves of Qud roguelike pixel art",
    ) -> Optional[CompositionReport]:
        """
        Analyze composition and aesthetics using LLaVA.
        
        Args:
            image_path: Path to image
            asset_type: Type of asset
            target_style: Target style description
        
        Returns:
            CompositionReport or None if failed
        """
        agent = self.agents.get(AgentRole.COMPOSITION_DIRECTOR)
        if not agent or not agent.enabled:
            return None
        
        if self.verbose:
            print(f"    [COMPOSITION] Analyzing {image_path.name} with {agent.model_name}...")
        
        prompt = (
            f"Evaluate this {asset_type} game asset for composition, lighting, and aesthetic quality. "
            f"Target style: {target_style}\n\n"
            "Return ONLY valid JSON with these keys:\n"
            "- composition: string (\"balanced\", \"unbalanced\", \"cluttered\", etc.)\n"
            "- lighting: string (description of lighting quality and issues)\n"
            "- style_alignment: float 0-1 (how well it matches target style)\n"
            "- professional_quality: string (\"high\", \"moderate\", \"low\")\n"
            "- fixes: array of strings (specific improvements needed)\n"
            "- strengths: array of strings (what works well)\n"
            "- overall_score: float 0-1 (weighted average)\n\n"
            "Focus on:\n"
            "- Visual balance and composition\n"
            "- Lighting consistency and mood\n"
            "- Style coherence\n"
            "- Professional polish"
        )
        
        response = self._call_vision_model(
            model_name=agent.model_name,
            prompt=prompt,
            image_path=image_path,
            system_prompt=agent.system_prompt,
        )
        
        if not response:
            return None
        
        # Parse JSON response
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                return None
            
            data = json.loads(response[start:end])
            
            report = CompositionReport(
                composition=data.get("composition", "unknown"),
                lighting=data.get("lighting", "unknown"),
                style_alignment=data.get("style_alignment", 0.0),
                professional_quality=data.get("professional_quality", "unknown"),
                fixes=data.get("fixes", []),
                strengths=data.get("strengths", []),
                overall_score=data.get("overall_score", 0.0),
            )
            
            if self.verbose:
                print(f"    [COMPOSITION] Overall score: {report.overall_score:.2f}")
                print(f"    [COMPOSITION] Quality: {report.professional_quality}")
            
            return report
        except Exception as e:
            if self.verbose:
                print(f"    [ERROR] Failed to parse composition response: {e}")
            return None
    
    def score_preference(
        self,
        image_path: Path,
    ) -> Optional[PreferenceScore]:
        """
        Score image with an honest local heuristic (file size + pixel entropy).
        Not PickScore/LAION -- labeled heuristic_entropy so callers do not
        treat the score as a learned preference model.
        """
        if not self.enable_preference_scorer:
            return None
        
        try:
            file_size = image_path.stat().st_size
            size_score = min(10.0, (file_size / 50000.0) * 10.0)
            entropy_score = size_score
            try:
                from PIL import Image
                import math
                im = Image.open(image_path).convert("L").resize((64, 64))
                hist = im.histogram()
                total = sum(hist) or 1
                ent = 0.0
                for c in hist:
                    if c:
                        p = c / total
                        ent -= p * math.log2(p)
                entropy_score = min(10.0, (ent / 8.0) * 10.0)
            except Exception:
                pass
            score = 0.4 * size_score + 0.6 * entropy_score
            return PreferenceScore(
                score=score,
                confidence=0.35,
                model="heuristic_entropy",
            )
        except Exception:
            return None
    
    def aggregate_feedback(
        self,
        technical_qa: Optional[TechnicalQAReport],
        composition: Optional[CompositionReport],
        preference_score: Optional[PreferenceScore],
        original_prompt: str,
        asset_type: str,
        iteration: int,
        previous_feedback: Optional[str] = None,
    ) -> AggregatedFeedback:
        """
        Aggregate feedback from all agents and generate refined prompt.
        
        Args:
            technical_qa: Technical QA report
            composition: Composition report
            preference_score: Preference score
            original_prompt: Original SD3.5 prompt
            asset_type: Type of asset
            iteration: Current iteration
            previous_feedback: Previous feedback (if any)
        
        Returns:
            AggregatedFeedback with refined prompt
        """
        if self.verbose:
            print(f"    [AGGREGATE] Combining feedback from all agents...")
        
        # Calculate overall quality (weighted average)
        scores = []
        weights = []
        
        if technical_qa:
            scores.append(technical_qa.overall_score * 100)
            weights.append(0.3)  # 30% weight
        
        if composition:
            scores.append(composition.overall_score * 100)
            weights.append(0.4)  # 40% weight
        
        if preference_score:
            # Normalize to 0-100
            normalized_score = (preference_score.score / 10.0) * 100
            scores.append(normalized_score)
            weights.append(0.3)  # 30% weight
        
        if scores:
            overall_quality = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        else:
            overall_quality = 0.0
        
        # Determine if refinement is needed
        needs_refinement = overall_quality < 75.0  # Threshold
        
        # Collect priority fixes
        priority_fixes = []
        if technical_qa:
            priority_fixes.extend(technical_qa.critical_issues)
        if composition:
            priority_fixes.extend(composition.fixes[:3])  # Top 3 fixes
        
        # Generate refined prompt using Creative Director
        refined_prompt = None
        refined_negative = None
        
        if needs_refinement and call_ollama:
            agent = self.agents.get(AgentRole.CREATIVE_DIRECTOR)
            if agent and agent.enabled:
                feedback_summary = []
                
                if technical_qa:
                    feedback_summary.append(f"Technical QA: {technical_qa.overall_score:.2f}/1.0")
                    if technical_qa.critical_issues:
                        feedback_summary.append(f"Issues: {', '.join(technical_qa.critical_issues[:3])}")
                
                if composition:
                    feedback_summary.append(f"Composition: {composition.overall_score:.2f}/1.0")
                    if composition.fixes:
                        feedback_summary.append(f"Fixes needed: {', '.join(composition.fixes[:3])}")
                
                if preference_score:
                    feedback_summary.append(f"Preference score: {preference_score.score:.1f}/10")
                
                prompt_text = (
                    f"Refine this SD3.5 prompt based on feedback from specialized art directors.\n\n"
                    f"Original prompt: {original_prompt}\n\n"
                    f"Asset type: {asset_type}\n"
                    f"Iteration: {iteration + 1}\n\n"
                )
                
                if previous_feedback:
                    prompt_text += f"Previous feedback: {previous_feedback}\n\n"
                
                prompt_text += (
                    f"Current feedback:\n" + "\n".join(feedback_summary) + "\n\n"
                    f"Return ONLY valid JSON with keys:\n"
                    f"- refined_prompt: string (improved prompt addressing all feedback)\n"
                    f"- refined_negative_prompt: string (enhanced negative prompt)\n"
                    f"- reasoning: string (brief explanation of changes)\n\n"
                    f"Focus on:\n"
                    f"- Fixing technical defects mentioned\n"
                    f"- Improving composition and lighting\n"
                    f"- Maintaining style consistency\n"
                    f"- Enhancing overall quality"
                )
                
                try:
                    response = call_ollama(
                        prompt=prompt_text,
                        task_type=agent.task_type,
                        response_length="detailed",
                        system_prompt=agent.system_prompt,
                        model_name=agent.model_name,
                    )
                    
                    if response:
                        start = response.find("{")
                        end = response.rfind("}") + 1
                        if start >= 0 and end > start:
                            data = json.loads(response[start:end])
                            refined_prompt = data.get("refined_prompt", original_prompt)
                            refined_negative = data.get("refined_negative_prompt", "")
                except Exception as e:
                    if self.verbose:
                        print(f"    [ERROR] Failed to refine prompt: {e}")
        
        # Build feedback summary
        feedback_text = f"Overall quality: {overall_quality:.1f}/100\n"
        if technical_qa:
            feedback_text += f"Technical QA: {technical_qa.overall_score:.2f}/1.0\n"
        if composition:
            feedback_text += f"Composition: {composition.overall_score:.2f}/1.0\n"
        if preference_score:
            feedback_text += f"Preference: {preference_score.score:.1f}/10\n"
        if priority_fixes:
            feedback_text += f"Priority fixes: {', '.join(priority_fixes[:3])}\n"
        
        return AggregatedFeedback(
            technical_qa=technical_qa,
            composition=composition,
            preference_score=preference_score,
            overall_quality=overall_quality,
            needs_refinement=needs_refinement,
            refined_prompt=refined_prompt or original_prompt,
            refined_negative_prompt=refined_negative or "",
            priority_fixes=priority_fixes,
            creative_director_notes=feedback_text,
        )
    
    def _unload_ollama_quiet(self) -> None:
        """Free VRAM between sequential agent swaps (11GB card)."""
        try:
            from ollama_integration import unload_all_models
            unload_all_models(verbose=False)
        except Exception:
            pass

    def review_asset_sequential(
        self,
        image_path: Path,
        original_prompt: str,
        asset_type: str = "asset",
        iteration: int = 0,
        previous_feedback: Optional[str] = None,
        target_style: str = "Caves of Qud roguelike pixel art",
    ) -> AggregatedFeedback:
        """
        Review one asset with exclusive model residency: creative → composition →
        tech QA → preference. Unloads between GPU-heavy agents.
        """
        if self.verbose:
            print(f"    [MULTI-AGENT] Sequential review of {image_path.name} (VRAM-exclusive swaps)...")

        start_time = time.time()
        technical_qa = None
        composition = None
        preference_score = None

        # Composition (LLaVA) — vision, unload after
        comp_agent = self.agents.get(AgentRole.COMPOSITION_DIRECTOR)
        if comp_agent and comp_agent.enabled:
            if self.verbose:
                print(f"    [MULTI-AGENT] swap → {comp_agent.model_name} (composition)")
            composition = self.analyze_composition(image_path, asset_type, target_style)
            self._unload_ollama_quiet()

        # Technical QA (Qwen-VL)
        qa_agent = self.agents.get(AgentRole.TECHNICAL_QA)
        if qa_agent and qa_agent.enabled:
            if self.verbose:
                print(f"    [MULTI-AGENT] swap → {qa_agent.model_name} (technical QA)")
            technical_qa = self.analyze_technical_qa(image_path, asset_type)
            self._unload_ollama_quiet()

        # Preference heuristic (CPU)
        pref_agent = self.agents.get(AgentRole.PREFERENCE_SCORER)
        if pref_agent and pref_agent.enabled:
            preference_score = self.score_preference(image_path)

        # Creative director aggregates + refined prompts (text model last so it stays loaded for refine)
        feedback = self.aggregate_feedback(
            technical_qa=technical_qa,
            composition=composition,
            preference_score=preference_score,
            original_prompt=original_prompt,
            asset_type=asset_type,
            iteration=iteration,
            previous_feedback=previous_feedback,
        )

        elapsed = time.time() - start_time
        if self.verbose:
            print(f"    [MULTI-AGENT] Sequential review done in {elapsed:.1f}s "
                  f"quality={feedback.overall_quality:.1f} refine={feedback.needs_refinement}")
        return feedback

    def review_asset(
        self,
        image_path: Path,
        original_prompt: str,
        asset_type: str = "asset",
        iteration: int = 0,
        previous_feedback: Optional[str] = None,
        target_style: str = "Caves of Qud roguelike pixel art",
    ) -> AggregatedFeedback:
        """
        Complete multi-agent review. Defaults to sequential VRAM-safe swaps
        (parallel multi-vision OOMs a 2080 Ti 11GB).
        """
        return self.review_asset_sequential(
            image_path=image_path,
            original_prompt=original_prompt,
            asset_type=asset_type,
            iteration=iteration,
            previous_feedback=previous_feedback,
            target_style=target_style,
        )
