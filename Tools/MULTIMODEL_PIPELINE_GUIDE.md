# Multimodel Pipeline Guide

## Overview

The mod fixer now uses a **multimodel pipeline** that intelligently routes tasks between:
- **Code Llama 7B (instruct)**: For reasoning, refactoring, explanations, and verification
- **StarCoder 7B**: For raw code generation, completions, and implementations

This provides the best balance of capability, accuracy, and VRAM efficiency.

## How It Works

### 1. Intent Classification

The router analyzes the task and classifies it:

**Reasoning Tasks** → Code Llama 7B:
- Fix, correct, update, compatibility issues
- Refactor, improve, optimize
- Explain, analyze, diagnose
- Keywords: `fix`, `correct`, `update`, `compatibility`, `deprecated`, `missing`

**Generation Tasks** → StarCoder 7B:
- Generate, create, implement
- Complete, scaffold, build
- Keywords: `generate`, `create`, `implement`, `complete`, `scaffold`

### 2. Routing Flow

```
Task → Intent Classification → Route to Primary Model
                                    ↓
                            [If Generation Task]
                                    ↓
                            StarCoder 7B generates code
                                    ↓
                            Code Llama 7B verifies output
                                    ↓
                            Confidence check → Accept/Reject
```

### 3. Verification Step

For generation tasks (StarCoder), Code Llama 7B reviews:
- Correctness: Does it solve the problem?
- Safety: Any logic errors or regressions?
- Compatibility: Matches codebase patterns?
- Style: Follows existing code style?

### 4. Confidence Scoring

Outputs are scored based on:
- Length (too short/long = lower confidence)
- Code block completeness
- Error indicators
- Completeness indicators

## Benefits

1. **Best Model for Each Task**
   - Code Llama excels at reasoning and verification
   - StarCoder excels at code generation

2. **Quality Assurance**
   - StarCoder outputs verified by Code Llama
   - Confidence thresholds filter poor outputs

3. **VRAM Efficient**
   - Both models are 7B (quantized: ~4-10 GB)
   - Only one model loaded at a time
   - CPU fallback available

4. **Air-Gapped Safe**
   - All processing is local
   - No network calls
   - Models cached locally

## Usage

### Automatic (Default)

The router is enabled by default. Just run the mod fixer:

```bash
python qud_mod_fixer.py "Mod Name"
```

You'll see output like:
```
[ROUTING] Intent: generation
[ROUTING] Primary model: starcoder:7b
[ROUTING] Confidence: 0.85
[ROUTING] Verification model: codellama:7b-instruct
[STEP 1] Generating fix with starcoder:7b...
[STEP 1] ✓ Generated fix (confidence: 0.82)
[STEP 2] Verifying with codellama:7b-instruct...
[STEP 2] ✓ Verification passed
```

### Manual Override

You can still override the model manually (disables routing):

```bash
# Use specific model (bypasses router)
# (Not currently supported via CLI, but can be modified in code)
```

## Model Requirements

### Required Models

```bash
# Primary models
ollama pull starcoder:7b              # For code generation
ollama pull codellama:7b-instruct     # For reasoning & verification

# Optional (fallbacks)
ollama pull codellama:7b              # Base variant
ollama pull codellama:34b             # Complex reasoning fallback
```

### VRAM Requirements

- **StarCoder 7B (4-bit)**: ~4-6 GB VRAM
- **Code Llama 7B (4-bit)**: ~4-6 GB VRAM
- **Both models**: Only one loaded at a time, so ~4-6 GB total

## Routing Examples

### Example 1: API Fix (Reasoning Task)

```
Task: "Fix API compatibility issues"
Intent: REASONING
Model: Code Llama 7B Instruct
Verification: None (reasoning tasks don't need verification)
```

### Example 2: Code Generation (Generation Task)

```
Task: "Generate new feature implementation"
Intent: GENERATION
Model: StarCoder 7B
Verification: Code Llama 7B Instruct (checks output)
```

### Example 3: Mixed Task

```
Task: "Fix and implement missing functionality"
Intent: GENERATION (generation keywords stronger)
Model: StarCoder 7B
Verification: Code Llama 7B Instruct
```

## Confidence Thresholds

### Default Threshold: 0.6

- **≥ 0.7**: High confidence, use without verification if verification fails
- **0.6 - 0.7**: Medium confidence, requires verification
- **< 0.6**: Low confidence, may be rejected

### Confidence Factors

- **Length**: Too short (<50 chars) or too long (>10k chars) reduces confidence
- **Code blocks**: Missing or incomplete code blocks reduce confidence
- **Error indicators**: Words like "error", "cannot" reduce confidence
- **Completeness**: Ending with "..." indicates incomplete output

## Verification Process

### Step 1: Primary Generation

StarCoder 7B generates the fix based on the prompt.

### Step 2: Verification Prompt

Code Llama 7B receives:
- Original code
- Generated code
- Task description
- Review criteria

### Step 3: Verdict

Code Llama returns:
- **APPROVE**: Code is correct and safe → Use output
- **REJECT**: Code has issues → Warn user, may still use if high confidence
- **REVISE**: Code needs minor changes → Use output with warning

## Configuration

### Disable Verification

Edit `qud_mod_fixer.py`:

```python
self.router = MultimodelRouter(use_verification=False)
```

### Adjust Confidence Threshold

Edit `multimodel_router.py`:

```python
if confidence_score >= 0.7:  # Change threshold
```

### Custom Routing Rules

Edit `multimodel_router.py`:

```python
REASONING_KEYWORDS = [
    'fix', 'correct', 'update',  # Add your keywords
    # ...
]
```

## Performance

### Typical Flow Times

- **Intent classification**: <1ms (heuristic rules)
- **Primary generation**: 30-60 seconds (StarCoder/Code Llama)
- **Verification**: 20-40 seconds (Code Llama)
- **Total**: ~50-100 seconds per fix (with verification)

### Without Verification

- **Total**: ~30-60 seconds per fix

## Troubleshooting

### "Multimodel router not available"

The router is built-in, but if you see this:
1. Check that `multimodel_router.py` exists in `Shared/`
2. Check Python imports are working

### Low Confidence Warnings

If you see "Low confidence output":
1. Check the output manually
2. May indicate incomplete or problematic generation
3. Consider adjusting threshold or improving prompt

### Verification Failures

If verification fails:
1. Check that Code Llama 7B Instruct is installed
2. High-confidence outputs (>0.7) are used anyway
3. Review the verification response for details

### Model Not Found

If router can't find models:
1. Install required models: `ollama pull starcoder:7b codellama:7b-instruct`
2. Router will fall back to available models
3. Check `ollama list` to see installed models

## Best Practices

1. **Install Both Models**: Have both StarCoder and Code Llama available
2. **Use Quantized Versions**: 4-bit/8-bit quantized for VRAM efficiency
3. **Monitor Confidence**: Review low-confidence outputs manually
4. **Check Verification**: Review verification responses for insights
5. **Keep Backups**: Always have backups (automatic in mod fixer)

## Comparison: Single vs Multimodel

### Single Model (Old)
- One model for all tasks
- May not be optimal for specific task types
- No verification step

### Multimodel (New)
- Best model for each task type
- Verification ensures quality
- Confidence scoring filters poor outputs
- Slightly slower (due to verification) but more accurate

## Integration with RAG

The multimodel router works seamlessly with RAG:

1. **RAG retrieves context** → Relevant code chunks
2. **Router classifies intent** → Reasoning or Generation
3. **Primary model generates** → With retrieved context
4. **Verification model checks** → Ensures correctness

This combines the best of both:
- **RAG**: Provides relevant code context
- **Multimodel**: Uses best model for task + verification

## Summary

The multimodel pipeline provides:
- ✅ Intelligent routing (right model for right task)
- ✅ Quality assurance (verification step)
- ✅ Confidence scoring (filters poor outputs)
- ✅ VRAM efficient (7B models, quantized)
- ✅ Air-gapped safe (all local)
- ✅ Seamless integration (works with RAG)

Just install the models and run - the router handles everything automatically!

