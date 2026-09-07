#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Audio Quality Assessment System
Hybrid pipeline using audio embeddings, Whisper transcription, and LLM-based quality scoring.

Pipeline:
1. Embed audio with CLAP/Wav2Vec for objective similarity/feature checks
2. Transcribe with Whisper for text-based QA
3. Feed embeddings/transcripts into Ollama LLM for human-readable quality checks and scores

This module is shared across all Transcendence tools for consistent audio quality assessment.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass, field

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Optional dependencies with graceful fallback
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

# Audio embedding models (optional)
try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Whisper (optional)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Ollama integration
try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Quality system (optional - try to import from common locations)
QUALITY_20_AVAILABLE = False
QualityLevel = None
get_quality_level = None
try:
    # Try importing from Transcendence directory first
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Transcendence'))
    from space_whale_quality_system import (
        QualityLevel, get_quality_level
    )
    QUALITY_20_AVAILABLE = True
except ImportError:
    # Create a simple enum fallback
    from enum import Enum
    class QualityLevel(Enum):
        PERFECT = 20
        EXCEPTIONAL = 19
        EXCELLENT_PLUS = 18
        EXCELLENT = 17
        VERY_GOOD_PLUS = 16
        VERY_GOOD = 15
        GOOD_PLUS = 14
        GOOD = 13
        ACCEPTABLE_PLUS = 12
        ACCEPTABLE = 11
        FAIR_PLUS = 10
        FAIR = 9
        NEEDS_WORK_PLUS = 8
        NEEDS_WORK = 7
        POOR_PLUS = 6
        POOR = 5
        VERY_POOR = 4
        UNACCEPTABLE = 3
        CRITICAL = 2
        REJECT = 1
    
    def get_quality_level(score: int) -> QualityLevel:
        """Simple quality level mapping."""
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

@dataclass
class AudioQualityMetrics:
    """Objective audio quality metrics."""
    snr_db: float = 0.0  # Signal-to-noise ratio in dB
    clipping_percentage: float = 0.0  # Percentage of samples that clip
    dynamic_range_db: float = 0.0  # Dynamic range in dB
    rms_level: float = 0.0  # RMS level (0-1)
    peak_level: float = 0.0  # Peak level (0-1)
    spectral_centroid: float = 0.0  # Spectral centroid (Hz)
    zero_crossing_rate: float = 0.0  # Zero crossing rate
    spectral_rolloff: float = 0.0  # Spectral rolloff frequency (Hz)

@dataclass
class AudioQualityAssessment:
    """Complete audio quality assessment result."""
    audio_file: str
    overall_score: int = 1  # 1-20 scale
    level: Optional[QualityLevel] = None
    
    # Objective metrics
    metrics: AudioQualityMetrics = field(default_factory=AudioQualityMetrics)
    
    # Embedding-based similarity
    embedding_similarity: float = 0.0  # 0-1 similarity to reference
    embedding_distance: float = 1.0  # Distance from reference
    
    # Transcription
    transcript: str = ""
    transcription_confidence: float = 0.0
    intelligibility_score: float = 0.0  # 0-1
    
    # LLM assessment
    llm_score: int = 1
    llm_issues: List[str] = field(default_factory=list)
    llm_suggested_fixes: List[str] = field(default_factory=list)
    llm_severity: str = "unknown"
    llm_rationale: str = ""
    
    # Composite scores
    technical_score: int = 1  # Based on objective metrics
    semantic_score: int = 1  # Based on embedding/transcription
    perceptual_score: int = 1  # Based on LLM assessment
    
    # Notes
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set quality level after initialization."""
        if self.level is None:
            self.level = get_quality_level(self.overall_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'audioFile': self.audio_file,
            'overallScore': self.overall_score,
            'level': self.level.name if self.level else 'UNKNOWN',
            'levelValue': self.level.value if self.level else 0,
            'metrics': {
                'snrDb': self.metrics.snr_db,
                'clippingPercentage': self.metrics.clipping_percentage,
                'dynamicRangeDb': self.metrics.dynamic_range_db,
                'rmsLevel': self.metrics.rms_level,
                'peakLevel': self.metrics.peak_level,
                'spectralCentroid': self.metrics.spectral_centroid,
                'zeroCrossingRate': self.metrics.zero_crossing_rate,
                'spectralRolloff': self.metrics.spectral_rolloff
            },
            'embeddingSimilarity': self.embedding_similarity,
            'embeddingDistance': self.embedding_distance,
            'transcript': self.transcript,
            'transcriptionConfidence': self.transcription_confidence,
            'intelligibilityScore': self.intelligibility_score,
            'llmScore': self.llm_score,
            'llmIssues': self.llm_issues,
            'llmSuggestedFixes': self.llm_suggested_fixes,
            'llmSeverity': self.llm_severity,
            'llmRationale': self.llm_rationale,
            'technicalScore': self.technical_score,
            'semanticScore': self.semantic_score,
            'perceptualScore': self.perceptual_score,
            'notes': self.notes
        }
        return result

class AudioEmbeddingExtractor:
    """Extract audio embeddings using various models."""
    
    def __init__(self, model_type: str = "wav2vec"):
        """
        Initialize embedding extractor.
        
        Args:
            model_type: "wav2vec", "clap", or "vggish"
        """
        self.model_type = model_type
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        if not TORCH_AVAILABLE:
            return
        
        try:
            if self.model_type == "wav2vec":
                # Use Wav2Vec2 for embeddings
                from transformers import Wav2Vec2Processor, Wav2Vec2Model
                processor_name = "facebook/wav2vec2-base-960h"
                self.processor = Wav2Vec2Processor.from_pretrained(processor_name)
                self.model = Wav2Vec2Model.from_pretrained(processor_name)
                self.model.eval()
            elif self.model_type == "clap":
                # CLAP weights are not bundled; use Wav2Vec2 with an honest alias label.
                print("CLAP requested but not installed -- using wav2vec2 (wav2vec_as_clap_fallback)")
                self.model_type = "wav2vec"
                self._load_model()
                self.model_type = "wav2vec_as_clap_fallback"
            else:
                self.model_type = "wav2vec"
                self._load_model()
        except Exception as e:
            self.model = None
            self.processor = None
    
    def extract_embedding(self, audio_path: str, sample_rate: int = 16000) -> Optional[np.ndarray]:
        """
        Extract embedding from audio file.
        
        Args:
            audio_path: Path to audio file
            sample_rate: Target sample rate (default: 16000 for Wav2Vec2)
        
        Returns:
            Embedding vector or None if extraction fails
        """
        if not LIBROSA_AVAILABLE or not SOUNDFILE_AVAILABLE:
            return None
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
            
            if self.model is not None and self.processor is not None and TORCH_AVAILABLE:
                # Use model-based embedding
                if self.model_type == "wav2vec":
                    return self._extract_wav2vec_embedding(audio, sample_rate)
            else:
                # Fallback to spectral features
                return self._extract_spectral_features(audio, sr)
        except Exception as e:
            return None
    
    def _extract_wav2vec_embedding(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract Wav2Vec2 embedding."""
        try:
            # Prepare input
            inputs = self.processor(audio, sampling_rate=sample_rate, return_tensors="pt")
            
            # Extract features
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use mean pooling over time dimension
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            
            return embedding
        except Exception:
            return self._extract_spectral_features(audio, sample_rate)
    
    def _extract_spectral_features(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract basic spectral features as fallback."""
        if not LIBROSA_AVAILABLE:
            return np.zeros(128)  # Dummy feature vector
        
        try:
            # Extract multiple spectral features
            features = []
            
            # MFCCs (13 coefficients)
            mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
            features.extend(mfccs.mean(axis=1))
            
            # Spectral centroid
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
            features.append(spectral_centroid.mean())
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sample_rate)
            features.append(spectral_rolloff.mean())
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(audio)
            features.append(zcr.mean())
            
            # Chroma features (12)
            chroma = librosa.feature.chroma(y=audio, sr=sample_rate)
            features.extend(chroma.mean(axis=1))
            
            # Tonnetz (6)
            tonnetz = librosa.feature.tonnetz(y=audio, sr=sample_rate)
            features.extend(tonnetz.mean(axis=1))
            
            return np.array(features)
        except Exception:
            return np.zeros(128)

class AudioTranscriber:
    """Transcribe audio using Whisper."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_size: "tiny", "base", "small", "medium", "large"
        """
        self.model_size = model_size
        self.model = None
        if WHISPER_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load Whisper model."""
        try:
            self.model = whisper.load_model(self.model_size)
        except Exception:
            self.model = None
    
    def transcribe(self, audio_path: str) -> Tuple[str, float]:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Tuple of (transcript, confidence)
        """
        if not self.model or not WHISPER_AVAILABLE:
            return ("", 0.0)
        
        try:
            result = self.model.transcribe(audio_path)
            transcript = result.get("text", "").strip()
            # Whisper doesn't provide direct confidence, use language probability as proxy
            confidence = result.get("language_probs", {}).get(result.get("language", "en"), 0.0)
            return (transcript, confidence)
        except Exception:
            return ("", 0.0)

def compute_audio_metrics(audio_path: str) -> AudioQualityMetrics:
    """
    Compute objective audio quality metrics.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        AudioQualityMetrics object
    """
    if not LIBROSA_AVAILABLE or not SOUNDFILE_AVAILABLE:
        return AudioQualityMetrics()
    
    try:
        # Load audio
        audio, sr = librosa.load(audio_path, sr=None, mono=True)
        
        # Compute metrics
        metrics = AudioQualityMetrics()
        
        # RMS and peak levels
        metrics.rms_level = float(np.sqrt(np.mean(audio**2)))
        metrics.peak_level = float(np.max(np.abs(audio)))
        
        # Clipping detection
        clipping_threshold = 0.99
        clipped_samples = np.sum(np.abs(audio) >= clipping_threshold)
        metrics.clipping_percentage = (clipped_samples / len(audio)) * 100.0
        
        # Dynamic range
        if metrics.rms_level > 0:
            metrics.dynamic_range_db = 20 * np.log10(metrics.peak_level / metrics.rms_level)
        else:
            metrics.dynamic_range_db = 0.0
        
        # SNR estimation (simplified: signal power vs noise floor)
        signal_power = np.mean(audio**2)
        noise_floor = np.percentile(audio**2, 10)  # Estimate noise from bottom 10%
        if noise_floor > 0:
            metrics.snr_db = 10 * np.log10(signal_power / noise_floor)
        else:
            metrics.snr_db = 60.0  # Assume good SNR if no noise detected
        
        # Spectral features
        metrics.spectral_centroid = float(librosa.feature.spectral_centroid(y=audio, sr=sr).mean())
        metrics.zero_crossing_rate = float(librosa.feature.zero_crossing_rate(audio).mean())
        metrics.spectral_rolloff = float(librosa.feature.spectral_rolloff(y=audio, sr=sr).mean())
        
        return metrics
    except Exception:
        return AudioQualityMetrics()

def compute_embedding_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> Tuple[float, float]:
    """
    Compute similarity and distance between embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
    
    Returns:
        Tuple of (similarity 0-1, distance)
    """
    try:
        # Normalize embeddings
        emb1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        emb2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
        
        # Cosine similarity
        similarity = float(np.dot(emb1_norm, emb2_norm))
        similarity = max(0.0, min(1.0, (similarity + 1.0) / 2.0))  # Normalize to 0-1
        
        # Euclidean distance
        distance = float(np.linalg.norm(embedding1 - embedding2))
        
        return (similarity, distance)
    except Exception:
        return (0.0, 1.0)

def assess_audio_with_llm(
    audio_path: str,
    metrics: AudioQualityMetrics,
    embedding_similarity: float,
    transcript: str,
    ollama_url: str = "http://localhost:11434",
    model_name: str = "llama3.1:8b"
) -> Dict[str, Any]:
    """
    Use LLM to assess audio quality based on metrics, embeddings, and transcript.
    
    Args:
        audio_path: Path to audio file
        metrics: AudioQualityMetrics object
        embedding_similarity: Embedding similarity score (0-1)
        transcript: Whisper transcription
        ollama_url: Ollama API URL
        model_name: Ollama model name
    
    Returns:
        Dictionary with LLM assessment results
    """
    if not OLLAMA_AVAILABLE:
        return {
            'score': 10,
            'issues': ['LLM assessment unavailable'],
            'suggested_fixes': [],
            'severity': 'unknown',
            'rationale': 'LLM assessment not available'
        }
    
    # Build prompt
    prompt = f"""You are an audio quality assessment expert. Analyze the following audio file and provide a quality assessment.

Audio File: {os.path.basename(audio_path)}

Objective Metrics:
- SNR: {metrics.snr_db:.1f} dB
- Clipping: {metrics.clipping_percentage:.1f}%
- Dynamic Range: {metrics.dynamic_range_db:.1f} dB
- RMS Level: {metrics.rms_level:.3f}
- Peak Level: {metrics.peak_level:.3f}
- Spectral Centroid: {metrics.spectral_centroid:.1f} Hz
- Zero Crossing Rate: {metrics.zero_crossing_rate:.3f}
- Spectral Rolloff: {metrics.spectral_rolloff:.1f} Hz

Embedding Similarity: {embedding_similarity:.3f} (0-1 scale, higher is better)

Transcription: {transcript if transcript else 'No transcription available'}

Provide a JSON response with the following structure:
{{
    "score": <integer 1-20>,
    "issues": [<list of quality issues>],
    "suggested_fixes": [<list of suggested fixes>],
    "severity": "<low|medium|high|critical>",
    "rationale": "<explanation of the score and assessment>"
}}

Scoring Guidelines:
- 17-20: Excellent quality, production-ready
- 13-16: Very good quality, minor issues
- 9-12: Acceptable quality, some issues
- 5-8: Needs work, significant issues
- 1-4: Poor quality, major problems

Focus on:
1. Technical quality (SNR, clipping, dynamic range)
2. Perceptual quality (based on metrics and similarity)
3. Intelligibility (if transcription is available)
4. Overall production readiness

Respond with ONLY valid JSON, no additional text."""

    try:
        # Call Ollama API
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more deterministic results
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            
            # Extract JSON from response
            try:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    llm_result = json.loads(json_match.group())
                else:
                    # Fallback: try parsing entire response
                    llm_result = json.loads(response_text)
                
                # Validate and normalize
                score = int(llm_result.get('score', 10))
                score = max(1, min(20, score))  # Clamp to 1-20
                
                return {
                    'score': score,
                    'issues': llm_result.get('issues', []),
                    'suggested_fixes': llm_result.get('suggested_fixes', []),
                    'severity': llm_result.get('severity', 'medium'),
                    'rationale': llm_result.get('rationale', 'No rationale provided')
                }
            except json.JSONDecodeError:
                return {
                    'score': 10,
                    'issues': ['LLM response parsing failed'],
                    'suggested_fixes': [],
                    'severity': 'unknown',
                    'rationale': 'Could not parse LLM response'
                }
        else:
            return {
                'score': 10,
                'issues': ['LLM API error'],
                'suggested_fixes': [],
                'severity': 'unknown',
                'rationale': f'Ollama API returned status {response.status_code}'
            }
    except Exception as e:
        return {
            'score': 10,
            'issues': [f'LLM call failed: {str(e)}'],
            'suggested_fixes': [],
            'severity': 'unknown',
            'rationale': f'Error calling LLM: {str(e)}'
        }

def assess_audio_quality(
    audio_path: str,
    reference_embedding: Optional[np.ndarray] = None,
    embedding_extractor: Optional[AudioEmbeddingExtractor] = None,
    transcriber: Optional[AudioTranscriber] = None,
    ollama_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.1:8b"
) -> AudioQualityAssessment:
    """
    Complete audio quality assessment pipeline.
    
    Args:
        audio_path: Path to audio file
        reference_embedding: Optional reference embedding for comparison
        embedding_extractor: Optional AudioEmbeddingExtractor instance
        transcriber: Optional AudioTranscriber instance
        ollama_url: Ollama API URL
        ollama_model: Ollama model name
    
    Returns:
        AudioQualityAssessment object
    """
    assessment = AudioQualityAssessment(audio_file=audio_path)
    
    # 1. Compute objective metrics
    assessment.metrics = compute_audio_metrics(audio_path)
    
    # 2. Extract embedding
    if embedding_extractor is None:
        embedding_extractor = AudioEmbeddingExtractor(model_type="wav2vec")
    
    embedding = embedding_extractor.extract_embedding(audio_path)
    
    if embedding is not None and reference_embedding is not None:
        similarity, distance = compute_embedding_similarity(embedding, reference_embedding)
        assessment.embedding_similarity = similarity
        assessment.embedding_distance = distance
    elif embedding is not None:
        # No reference, use embedding norm as proxy
        assessment.embedding_similarity = 0.5  # Neutral
        assessment.embedding_distance = float(np.linalg.norm(embedding))
    
    # 3. Transcribe
    if transcriber is None:
        transcriber = AudioTranscriber(model_size="base")
    
    transcript, confidence = transcriber.transcribe(audio_path)
    assessment.transcript = transcript
    assessment.transcription_confidence = confidence
    assessment.intelligibility_score = confidence  # Use confidence as intelligibility proxy
    
    # 4. Compute technical score from metrics
    technical_score = 10  # Base score
    
    # Adjust based on metrics
    if assessment.metrics.snr_db > 30:
        technical_score += 3
    elif assessment.metrics.snr_db > 20:
        technical_score += 2
    elif assessment.metrics.snr_db < 10:
        technical_score -= 3
    
    if assessment.metrics.clipping_percentage < 0.1:
        technical_score += 2
    elif assessment.metrics.clipping_percentage > 1.0:
        technical_score -= 3
    
    if assessment.metrics.dynamic_range_db > 20:
        technical_score += 2
    elif assessment.metrics.dynamic_range_db < 10:
        technical_score -= 1
    
    technical_score = max(1, min(20, technical_score))
    assessment.technical_score = technical_score
    
    # 5. Compute semantic score from embedding/transcription
    semantic_score = 10  # Base score
    
    semantic_score += int(assessment.embedding_similarity * 5)  # +0 to +5
    semantic_score += int(assessment.intelligibility_score * 3)  # +0 to +3
    
    semantic_score = max(1, min(20, semantic_score))
    assessment.semantic_score = semantic_score
    
    # 6. LLM assessment
    llm_result = assess_audio_with_llm(
        audio_path,
        assessment.metrics,
        assessment.embedding_similarity,
        transcript,
        ollama_url,
        ollama_model
    )
    
    assessment.llm_score = llm_result['score']
    assessment.llm_issues = llm_result['issues']
    assessment.llm_suggested_fixes = llm_result['suggested_fixes']
    assessment.llm_severity = llm_result['severity']
    assessment.llm_rationale = llm_result['rationale']
    assessment.perceptual_score = assessment.llm_score
    
    # 7. Compute overall score (weighted average)
    overall = int(
        assessment.technical_score * 0.3 +
        assessment.semantic_score * 0.25 +
        assessment.perceptual_score * 0.45
    )
    overall = max(1, min(20, overall))
    assessment.overall_score = overall
    
    # 8. Determine quality level
    assessment.level = get_quality_level(overall)
    
    # 9. Build notes
    assessment.notes = []
    if assessment.metrics.clipping_percentage > 1.0:
        assessment.notes.append(f"High clipping: {assessment.metrics.clipping_percentage:.1f}%")
    if assessment.metrics.snr_db < 15:
        assessment.notes.append(f"Low SNR: {assessment.metrics.snr_db:.1f} dB")
    if assessment.embedding_similarity < 0.5:
        assessment.notes.append("Low embedding similarity to reference")
    if not transcript:
        assessment.notes.append("No transcription available")
    assessment.notes.extend(assessment.llm_issues[:3])  # Add top 3 LLM issues
    
    return assessment

def batch_assess_audio_quality(
    audio_dir: Path,
    min_score: int = 17,
    ollama_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.1:8b",
    embedding_model: str = "wav2vec",
    whisper_model: str = "base",
    reference_audio: Optional[str] = None,
    log_message=None
) -> Tuple[Dict[str, AudioQualityAssessment], int, int]:
    """
    Batch assess audio quality for all files in a directory.
    
    Args:
        audio_dir: Directory containing audio files
        min_score: Minimum score to keep (default: 17)
        ollama_url: Ollama API URL
        ollama_model: Ollama model name
        embedding_model: Embedding model type
        whisper_model: Whisper model size
        reference_audio: Optional reference audio file path
        log_message: Optional logging function
    
    Returns:
        Tuple of (assessments dict, total_count, filtered_count)
    """
    if log_message is None:
        log_message = lambda msg, level="INFO": print(f"[{level}] {msg}")
    
    assessments = {}
    total_count = 0
    filtered_count = 0
    
    # Find all audio files
    audio_files = list(audio_dir.rglob("*.wav")) + list(audio_dir.rglob("*.ogg"))
    
    if not audio_files:
        log_message(f"  No audio files found in {audio_dir}", "WARNING")
        return (assessments, 0, 0)
    
    log_message(f"  Assessing {len(audio_files)} audio files...", "INFO")
    
    # Extract reference embedding if provided
    reference_embedding = None
    if reference_audio and os.path.exists(reference_audio):
        extractor = AudioEmbeddingExtractor(model_type=embedding_model)
        reference_embedding = extractor.extract_embedding(reference_audio)
        if reference_embedding is not None:
            log_message(f"  Using reference audio: {reference_audio}", "INFO")
    
    # Create extractors (reuse for efficiency)
    embedding_extractor = AudioEmbeddingExtractor(model_type=embedding_model)
    transcriber = AudioTranscriber(model_size=whisper_model)
    
    # Assess each file
    for i, audio_file in enumerate(audio_files, 1):
        total_count += 1
        try:
            log_message(f"    [{i}/{len(audio_files)}] Assessing: {audio_file.name}", "INFO")
            
            assessment = assess_audio_quality(
                str(audio_file),
                reference_embedding=reference_embedding,
                embedding_extractor=embedding_extractor,
                transcriber=transcriber,
                ollama_url=ollama_url,
                ollama_model=ollama_model
            )
            
            assessments[str(audio_file)] = assessment
            
            # Check if below threshold
            if assessment.overall_score < min_score:
                filtered_count += 1
                log_message(f"      Score: {assessment.overall_score}/20 (below {min_score}) - will be filtered", "INFO")
            else:
                log_message(f"      Score: {assessment.overall_score}/20 (kept)", "SUCCESS")
        except Exception as e:
            log_message(f"      Error assessing {audio_file.name}: {e}", "ERROR")
            # Create a low-score assessment for failed files
            failed_assessment = AudioQualityAssessment(
                audio_file=str(audio_file),
                overall_score=1,
                notes=[f"Assessment failed: {str(e)}"]
            )
            assessments[str(audio_file)] = failed_assessment
            filtered_count += 1
    
    log_message(f"  Assessment complete: {total_count} files, {filtered_count} below threshold", "INFO")
    return (assessments, total_count, filtered_count)

def filter_audio_by_quality(
    audio_dir: Path,
    assessments: Dict[str, AudioQualityAssessment],
    min_score: int = 17,
    log_message=None
) -> int:
    """
    Filter audio files by removing those below quality threshold.
    
    Args:
        audio_dir: Directory containing audio files
        assessments: Dictionary of audio assessments
        min_score: Minimum score to keep
        log_message: Optional logging function
    
    Returns:
        Number of files removed
    """
    if log_message is None:
        log_message = lambda msg, level="INFO": print(f"[{level}] {msg}")
    
    removed_count = 0
    
    for audio_path_str, assessment in assessments.items():
        if assessment.overall_score < min_score:
            audio_path = Path(audio_path_str)
            if audio_path.exists():
                try:
                    audio_path.unlink()
                    removed_count += 1
                    log_message(f"    Removed: {audio_path.name} (score: {assessment.overall_score}/20)", "INFO")
                except Exception as e:
                    log_message(f"    Error removing {audio_path.name}: {e}", "ERROR")
    
    # Save assessment results
    assessment_file = audio_dir / "audio_quality_assessments.json"
    try:
        with open(assessment_file, 'w', encoding='utf-8') as f:
            assessments_dict = {k: v.to_dict() for k, v in assessments.items()}
            json.dump({
                'assessments': assessments_dict,
                'min_score_threshold': min_score,
                'total_assessed': len(assessments),
                'removed_count': removed_count
            }, f, indent=2, ensure_ascii=False)
        log_message(f"  Assessment results saved: {assessment_file}", "INFO")
    except Exception as e:
        log_message(f"  Error saving assessment results: {e}", "ERROR")
    
    return removed_count
