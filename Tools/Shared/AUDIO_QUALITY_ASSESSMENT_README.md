# Shared Audio Quality Assessment System

## Overview

This is a **shared audio quality assessment module** for all Transcendence tools. It provides a hybrid pipeline combining:
1. **Audio embeddings** (CLAP/Wav2Vec) for objective similarity and feature checks
2. **Whisper transcription** for text-based QA and intelligibility checks
3. **LLM assessment** (Ollama models) for human-readable quality reports and scores

This combination provides **robust objective metrics plus explainable, editable judgments** that integrate seamlessly with quality systems across all tools.

## Location

**Shared Module**: `Tools/Shared/audio_quality_assessment.py`

This module is available to all tools in the Transcendence Tools directory structure.

## Usage in Your Tools

### Basic Import

```python
import sys
import os

# Add Shared directory to path
shared_path = os.path.join(os.path.dirname(__file__), "..", "Shared")
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from audio_quality_assessment import (
    assess_audio_quality,
    batch_assess_audio_quality,
    filter_audio_by_quality,
    AudioQualityAssessment,
    AudioEmbeddingExtractor,
    AudioTranscriber
)
```

### Single File Assessment

```python
from pathlib import Path
from audio_quality_assessment import assess_audio_quality

assessment = assess_audio_quality(
    "path/to/audio.wav",
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b"
)

print(f"Score: {assessment.overall_score}/20")
print(f"Level: {assessment.level.name}")
print(f"Issues: {assessment.llm_issues}")
```

### Batch Assessment

```python
from pathlib import Path
from audio_quality_assessment import batch_assess_audio_quality, filter_audio_by_quality

audio_dir = Path("path/to/audio/directory")

assessments, total, filtered = batch_assess_audio_quality(
    audio_dir,
    min_score=17,
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b"
)

# Filter out low-quality files
removed = filter_audio_by_quality(audio_dir, assessments, min_score=17)
```

## Features

- **Objective Metrics**: SNR, clipping detection, dynamic range, spectral analysis
- **Embedding-based Similarity**: Compare audio to reference examples using Wav2Vec2 or CLAP
- **Transcription**: Automatic transcription with Whisper for intelligibility checks
- **LLM Quality Scoring**: Human-readable quality reports with scores (1-20 scale)
- **Automatic Filtering**: Remove audio files below quality threshold
- **Batch Processing**: Assess entire directories of audio files

## Dependencies

### Required
- `numpy` - Numerical operations
- `requests` - Ollama API communication

### Optional (with graceful fallback)
- `librosa` - Audio processing
- `soundfile` - Audio file I/O
- `torch`, `torchaudio` - PyTorch for embedding models
- `transformers` - Wav2Vec2 model
- `openai-whisper` - Whisper transcription

Install with:
```bash
pip install numpy requests librosa soundfile torch torchaudio transformers openai-whisper
```

## Quality Scoring

The system uses a **20-level quality scale** (1-20):

- **17-20**: Excellent quality, production-ready
- **13-16**: Very good quality, minor issues
- **9-12**: Acceptable quality, some issues
- **5-8**: Needs work, significant issues
- **1-4**: Poor quality, major problems

### Composite Scoring

The overall score is a weighted average:
- **Technical Score (30%)**: Based on objective metrics (SNR, clipping, dynamic range)
- **Semantic Score (25%)**: Based on embedding similarity and transcription confidence
- **Perceptual Score (45%)**: Based on LLM assessment

## Integration Examples

### Example 1: Simple Integration

```python
import sys
import os
from pathlib import Path

# Add Shared to path
shared_path = os.path.join(os.path.dirname(__file__), "..", "Shared")
sys.path.insert(0, shared_path)

from audio_quality_assessment import assess_audio_quality

def check_audio_file(audio_path):
    assessment = assess_audio_quality(audio_path)
    return assessment.overall_score >= 17  # Production threshold
```

### Example 2: With Custom Logging

```python
from audio_quality_assessment import batch_assess_audio_quality

def log_message(msg, level="INFO"):
    print(f"[{level}] {msg}")

assessments, total, filtered = batch_assess_audio_quality(
    audio_dir,
    min_score=17,
    log_message=log_message
)
```

### Example 3: With Reference Audio

```python
from audio_quality_assessment import (
    assess_audio_quality,
    AudioEmbeddingExtractor
)

# Extract reference embedding
extractor = AudioEmbeddingExtractor()
reference_embedding = extractor.extract_embedding("reference.wav")

# Assess with reference
assessment = assess_audio_quality(
    "test.wav",
    reference_embedding=reference_embedding
)
```

## API Reference

### Main Functions

- `assess_audio_quality(audio_path, ...)` - Assess single audio file
- `batch_assess_audio_quality(audio_dir, ...)` - Assess directory of files
- `filter_audio_by_quality(audio_dir, assessments, min_score)` - Filter low-quality files

### Classes

- `AudioQualityAssessment` - Complete assessment result
- `AudioQualityMetrics` - Objective metrics
- `AudioEmbeddingExtractor` - Extract audio embeddings
- `AudioTranscriber` - Transcribe audio with Whisper

## Configuration

### Embedding Models
- `wav2vec` (default): Facebook Wav2Vec2-base-960h
- `clap`: CLAP model (requires specific setup)

### Whisper Models
- `tiny`: Fastest, least accurate
- `base` (default): Balanced speed/accuracy
- `small`: Better accuracy
- `medium`: High accuracy
- `large`: Best accuracy, slowest

### Ollama Models
Recommended:
- `llama3.1:8b` (default): Good balance
- `llama3.1:13b`: Higher quality
- `deepseek-r1:7b`: Fast inference

## Output Format

Assessment results include:

```python
{
    'audioFile': 'path/to/audio.wav',
    'overallScore': 18,
    'level': 'EXCELLENT_PLUS',
    'levelValue': 18,
    'metrics': {
        'snrDb': 32.5,
        'clippingPercentage': 0.1,
        'dynamicRangeDb': 24.3,
        ...
    },
    'embeddingSimilarity': 0.87,
    'transcript': 'Generated audio content',
    'llmScore': 18,
    'llmIssues': [],
    'llmSuggestedFixes': [],
    'llmSeverity': 'low',
    'llmRationale': 'Excellent quality audio...',
    'technicalScore': 17,
    'semanticScore': 18,
    'perceptualScore': 18,
    'notes': []
}
```

## Troubleshooting

### Missing Dependencies

The module gracefully handles missing dependencies. Install what you need:

```bash
pip install librosa soundfile  # For basic audio processing
pip install torch transformers  # For Wav2Vec2 embeddings
pip install openai-whisper  # For transcription
```

### Ollama Not Running

Ensure Ollama is running:

```bash
ollama serve
```

### Import Errors

Make sure the Shared directory is in your Python path:

```python
import sys
import os
shared_path = os.path.join(os.path.dirname(__file__), "..", "Shared")
sys.path.insert(0, shared_path)
```

## See Also

- **Space Whale Implementation**: `Tools/Transcendence/space_whale_comprehensive_asset_generator.py`
- **Quality System**: `Tools/Transcendence/space_whale_quality_system.py` (optional integration)

## License

Part of the Transcendence Tools shared library.
