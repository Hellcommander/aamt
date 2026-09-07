# RAG Implementation Summary

## What Was Implemented

A complete **Retrieval-Augmented Generation (RAG)** system has been integrated into the mod fixer tools, providing:

1. **Local Vector Store** (FAISS/Chroma)
2. **Local Embedding Models** (sentence-transformers)
3. **Code Chunking & Indexing**
4. **Retrieval-Augmented Prompts**
5. **Air-Gapped Operation** (no network calls)

## Files Created

### 1. `Shared/rag_system.py`
Complete RAG system implementation:
- `LocalEmbedder`: Local sentence-transformer embeddings
- `FAISSVectorStore`: Fast local vector search
- `ChromaVectorStore`: Alternative vector store
- `CodeChunker`: Intelligent code chunking
- `RAGSystem`: Complete RAG pipeline

### 2. `Shared/rag_setup.py`
Setup script for installing dependencies:
- FAISS (CPU version)
- Chroma
- sentence-transformers

### 3. `RAG_SETUP_GUIDE.md`
Complete setup and usage guide

## Integration

### Qud Mod Fixer (`Qud/qud_mod_fixer.py`)

**Changes:**
- Added RAG system initialization in `ModFixer.__init__()`
- Auto-builds index on first run
- Uses RAG in `_build_api_fix_prompt()` for API fixes
- Uses RAG in `_build_asset_fix_prompt()` for asset fixes
- New arguments: `--no-rag`, `--rag-index`

**How It Works:**
1. On first run, indexes source code (one-time, ~5-15 min)
2. For each fix, retrieves relevant code chunks
3. Augments prompt with retrieved context
4. Generates fix using StarCoder/Code Llama 7B with context

## Features

### ✅ Local & Air-Gapped
- All processing is local
- No cloud APIs or network calls
- Models downloaded once, then cached
- Index stored locally

### ✅ Low VRAM (<11 GB)
- Embedding model: ~80MB RAM (CPU)
- FAISS index: ~10-100MB disk
- Code models: ~4-10 GB VRAM (quantized 7B)

### ✅ Better Code Context
- Retrieves relevant source code patterns
- No indexing issues (unlike CodeLlama 34B)
- Matches codebase style and patterns

### ✅ Automatic Operation
- RAG enabled by default
- Auto-builds index on first run
- Seamless integration with existing workflow

## Usage

### First Time Setup

```bash
# Install dependencies
python Shared/rag_setup.py

# Run mod fixer (will auto-build index)
python qud_mod_fixer.py "Mod Name"
```

### Normal Usage

```bash
# RAG enabled by default
python qud_mod_fixer.py "Mod Name"

# Disable RAG if needed
python qud_mod_fixer.py "Mod Name" --no-rag

# Custom index path
python qud_mod_fixer.py "Mod Name" --rag-index "path/to/index.faiss"
```

## Workflow

### Without RAG (Old)
```
Issue → Basic Prompt → AI Model → Fix
```

### With RAG (New)
```
Issue → Query Extraction → Vector Search → Retrieve Context
  ↓
Retrieved Context + Issue → Augmented Prompt → AI Model → Better Fix
```

## Benefits

1. **Better Fixes**: AI sees relevant code patterns from source
2. **No Indexing Issues**: Proper source code references
3. **Style Matching**: Fixes match codebase style
4. **Local Only**: Everything runs offline
5. **Low Resource**: Works on <11 GB VRAM systems

## Model Recommendations

### For Code Generation
- **StarCoder 7B** (default) - Best for raw code generation
- **Code Llama 7B Instruct** - Best for patch suggestions

### For Embeddings
- **all-MiniLM-L6-v2** (default) - Small, fast, CPU-friendly
- **all-mpnet-base-v2** - Better quality, larger

### VRAM Requirements
- StarCoder 7B (4-bit): ~4-6 GB
- Code Llama 7B (4-bit): ~4-6 GB
- Embedding model: CPU only (~80MB RAM)

## Security & Privacy

✅ **Air-Gapped Safe**
- No network calls during operation
- Models cached locally
- Index files stored locally
- No telemetry

✅ **Data Privacy**
- All code stays local
- No cloud sync
- Index can be encrypted
- Audit logs available

## Next Steps

1. **Install dependencies**: `python Shared/rag_setup.py`
2. **Run mod fixer**: Index will auto-build on first run
3. **Monitor performance**: Check retrieval times and fix quality
4. **Tune if needed**: Adjust chunk size, retrieval count, etc.

The RAG system is now fully integrated and ready to use!

