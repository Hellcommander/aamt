# Space Whale Audio Quality Assessment System

> **Note**: The audio quality assessment system has been moved to the **Shared** directory for use across all tools.
> See `Tools/Shared/AUDIO_QUALITY_ASSESSMENT_README.md` for the shared module documentation.
>
> This document describes the Space Whale-specific integration.

## Overview

The Space Whale Audio Quality Assessment System uses a **hybrid pipeline** combining:
1. **Audio embeddings** (CLAP/Wav2Vec) for objective similarity and feature checks
2. **Whisper transcription** for text-based QA and intelligibility checks
3. **LLM assessment** (Ollama models) for human-readable quality reports and scores

This combination provides **robust objective metrics plus explainable, editable judgments** that integrate seamlessly with the existing 20-level quality system.

## Features

- **Objective Metrics**: SNR, clipping detection, dynamic range, spectral analysis
- **Embedding-based Similarity**: Compare audio to reference examples using Wav2Vec2 or CLAP
- **Transcription**: Automatic transcription with Whisper for intelligibility checks
- **LLM Quality Scoring**: Human-readable quality reports with scores (1-20 scale)
- **Automatic Filtering**: Removes audio files below quality threshold (default: 17/20)
- **Batch Processing**: Assess entire directories of audio files

## Installation

### Required Dependencies

```bash
# Core audio processing
pip install librosa soundfile numpy

# Optional: PyTorch for embedding models
pip install torch torchaudio

# Optional: Transformers for Wav2Vec2
pip install transformers

# Optional: Whisper for transcription
pip install openai-whisper

# Required: Requests for Ollama API
pip install requests
```

### Optional Dependencies

- **Wav2Vec2**: For audio embeddings (requires `transformers` and `torch`)
- **Whisper**: For transcription (requires `openai-whisper`)
- **CLAP**: For multimodal audio-text embeddings (requires specific setup)

## Usage

### Standalone Assessment

Assess a single audio file:

```bash
python space_whale_audio_quality_assessment.py audio_file.wav \
    --ollama-model llama3.1:8b \
    --output assessment.json
```

### Batch Assessment

Assess all audio files in a directory:

```bash
python space_whale_audio_quality_assessment.py /path/to/audio/dir \
    --batch \
    --min-score 17 \
    --filter \
    --ollama-model llama3.1:8b
```

### With Reference Audio

Compare against a reference audio file:

```bash
python space_whale_audio_quality_assessment.py audio_file.wav \
    --reference reference.wav \
    --ollama-model llama3.1:8b
```

### Integration with Comprehensive Generator

The audio quality assessment is automatically integrated into `space_whale_comprehensive_asset_generator.py`. When you run:

```bash
python space_whale_comprehensive_asset_generator.py --variations 150
```

The system will:
1. Generate all audio assets
2. Assess quality using the hybrid pipeline
3. Filter out files with scores < 17
4. Save assessment results to `Audio/audio_quality_assessments.json`

## Quality Scoring System

The system uses a **20-level quality scale** (1-20) aligned with the existing quality system:

- **17-20**: Excellent quality, production-ready
- **13-16**: Very good quality, minor issues
- **9-12**: Acceptable quality, some issues
- **5-8**: Needs work, significant issues
- **1-4**: Poor quality, major problems

### Composite Scoring

The overall score is a weighted average of:

1. **Technical Score (30%)**: Based on objective metrics (SNR, clipping, dynamic range)
2. **Semantic Score (25%)**: Based on embedding similarity and transcription confidence
3. **Perceptual Score (45%)**: Based on LLM assessment

## Pipeline Details

### 1. Objective Metrics

Computes:
- **SNR** (Signal-to-Noise Ratio): Audio clarity
- **Clipping Percentage**: Distortion detection
- **Dynamic Range**: Loudness variation
- **Spectral Features**: Centroid, rolloff, zero-crossing rate

### 2. Audio Embeddings

Extracts embeddings using:
- **Wav2Vec2** (default): Captures acoustic features and semantic content
- **CLAP** (optional): Multimodal embeddings linking audio to text
- **Spectral Features** (fallback): Basic features if models unavailable

### 3. Transcription

Uses **Whisper** to:
- Transcribe audio content
- Assess intelligibility
- Enable semantic quality checks

### 4. LLM Assessment

Feeds metrics, embeddings, and transcripts to Ollama LLM to produce:
- Quality score (1-20)
- Identified issues
- Suggested fixes
- Severity assessment
- Human-readable rationale

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

Recommended models:
- `llama3.1:8b` (default): Good balance
- `llama3.1:13b`: Higher quality
- `deepseek-r1:7b`: Fast inference

## Output Format

Assessment results are saved as JSON:

```json
{
  "audioFile": "path/to/audio.wav",
  "overallScore": 18,
  "level": "EXCELLENT_PLUS",
  "levelValue": 18,
  "metrics": {
    "snrDb": 32.5,
    "clippingPercentage": 0.1,
    "dynamicRangeDb": 24.3,
    "rmsLevel": 0.65,
    "peakLevel": 0.89
  },
  "embeddingSimilarity": 0.87,
  "transcript": "Generated whale song audio",
  "llmScore": 18,
  "llmIssues": [],
  "llmSuggestedFixes": [],
  "llmSeverity": "low",
  "llmRationale": "Excellent quality audio with good SNR and no clipping",
  "technicalScore": 17,
  "semanticScore": 18,
  "perceptualScore": 18,
  "notes": []
}
```

## Troubleshooting

### Missing Dependencies

If you see warnings about missing dependencies, install them:

```bash
pip install librosa soundfile torch transformers openai-whisper
```

### Ollama Not Running

Ensure Ollama is running:

```bash
ollama serve
```

### Model Download

First-time use will download models:
- Wav2Vec2: ~300MB
- Whisper: Varies by model size (base ~150MB)

### Performance

- **Embedding extraction**: ~1-2 seconds per file
- **Transcription**: ~2-5 seconds per file (depends on Whisper model)
- **LLM assessment**: ~3-10 seconds per file (depends on model)

For batch processing, consider using smaller models or processing in parallel.

## Integration Points

The system integrates with:

1. **space_whale_comprehensive_asset_generator.py**: Automatic quality assessment and filtering
2. **space_whale_quality_system.py**: 20-level quality scoring
3. **space_whale_quality_checker.py**: Quality reporting

## Best Practices

1. **Use reference audio**: Provide a reference file for better similarity comparisons
2. **Choose appropriate models**: Balance speed vs. accuracy for your use case
3. **Set min_score appropriately**: Default 17/20 ensures production-ready quality
4. **Review LLM rationales**: Human-readable explanations help understand scores
5. **Batch processing**: Use batch mode for efficiency when processing many files

## Example Workflow

```bash
# 1. Generate audio assets
python space_whale_audio_generator.py \
    --registry space_whale_audio_registry.json \
    --output Audio \
    --variations 150

# 2. Assess quality (optional standalone)
python space_whale_audio_quality_assessment.py Audio \
    --batch \
    --min-score 17 \
    --filter \
    --ollama-model llama3.1:8b

# 3. Or use comprehensive generator (includes assessment)
python space_whale_comprehensive_asset_generator.py \
    --variations 150 \
    --ollama-model llama3.1:8b
```

## References

- **Wav2Vec2**: [Facebook Research](https://github.com/facebookresearch/fairseq/tree/main/examples/wav2vec)
- **Whisper**: [OpenAI](https://github.com/openai/whisper)
- **CLAP**: [LAION-AI](https://github.com/LAION-AI/CLAP)
- **Ollama**: [Ollama.ai](https://ollama.ai/)

## License

Part of the Space Whale Asset Generation System.
