# RAG System Setup Guide

## Overview

The mod fixer now includes a **Retrieval-Augmented Generation (RAG)** system that:
- Indexes source code locally using FAISS/Chroma
- Uses local embedding models (sentence-transformers)
- Retrieves relevant code context before generating fixes
- Works completely offline/air-gapped
- Optimized for <11 GB VRAM

## Benefits

1. **Better Code Context**: Retrieves relevant source code patterns before generating fixes
2. **No Indexing Issues**: Unlike CodeLlama 34B, RAG properly references source code
3. **Local Only**: Everything runs locally, no cloud dependencies
4. **Air-Gapped Safe**: No network calls, all data stays local
5. **Low VRAM**: Uses CPU-friendly embedding models (~80MB)

## Installation

### Step 1: Install Dependencies

```bash
# Run the setup script
python Shared/rag_setup.py

# Or install manually
pip install faiss-cpu sentence-transformers chromadb
```

### Step 2: First Run (Index Building)

On first run, the RAG system will automatically:
1. Index your source code (one-time operation)
2. Generate embeddings locally (no network calls)
3. Save the index to disk for future use

This may take 5-15 minutes depending on source code size.

### Step 3: Verify Setup

The mod fixer will show:
```
Initializing RAG system...
  Source: G:\CavesofQud-decompiledsource
  Index: C:\Users\...\rag_index\qud_source_index.faiss
  Index not found, building...
  This is a one-time operation (runs locally, no network calls)
  Indexing source code from: G:\CavesofQud-decompiledsource
  ...
  ✓ Indexed 1234 chunks from source code
```

## Usage

### Basic Usage (RAG Enabled by Default)

```bash
python qud_mod_fixer.py "Mod Name"
```

RAG is enabled by default and will automatically:
- Retrieve relevant code context for API fixes
- Retrieve relevant code context for asset fixes
- Augment prompts with retrieved context

### Disable RAG

```bash
python qud_mod_fixer.py "Mod Name" --no-rag
```

### Custom Index Path

```bash
python qud_mod_fixer.py "Mod Name" --rag-index "path/to/index.faiss"
```

## How It Works

### 1. Indexing Phase (One-Time)

```
Source Code → Chunking → Embeddings → Vector Store (FAISS/Chroma)
```

- **Chunking**: Splits code into function/class-level chunks
- **Embeddings**: Generates vector embeddings using local model
- **Storage**: Saves to FAISS index (fast, local-only)

### 2. Retrieval Phase (Per Fix)

```
Query (e.g., "GetIntProperty") → Embedding → Vector Search → Relevant Chunks
```

- **Query**: Extracted from issues (API calls, methods, etc.)
- **Search**: Finds top-k most similar code chunks
- **Context**: Retrieved chunks added to prompt

### 3. Generation Phase

```
Retrieved Context + Issue + Mod File → AI Model → Fixed Code
```

- **Augmented Prompt**: Includes retrieved code context
- **Better Fixes**: AI sees relevant patterns from source code
- **No Indexing Issues**: Proper code references

## Configuration

### Embedding Model

Default: `all-MiniLM-L6-v2` (~80MB, CPU-friendly)

To use a different model, edit `rag_system.py`:

```python
self.rag_system = RAGSystem(
    source_path=source_path,
    index_path=rag_index_path,
    embedding_model="all-mpnet-base-v2",  # Better quality, ~420MB
    device="cpu"  # or "cuda" if you have GPU
)
```

### Chunk Size

Default: 500 characters per chunk

Adjust in `rag_system.py`:

```python
self.chunker = CodeChunker(
    chunk_size=1000,  # Larger chunks
    chunk_overlap=100  # More overlap
)
```

### Retrieval Count

Default: 5 chunks per query

Adjust in retrieval calls:

```python
retrieved_chunks = self.rag_system.retrieve(query, top_k=10)
```

## VRAM Optimization

### For <11 GB VRAM

1. **Use CPU for embeddings** (default)
   - Embedding model runs on CPU
   - No VRAM usage for embeddings

2. **Use quantized code models**
   - StarCoder 7B (4-bit): ~4-6 GB VRAM
   - Code Llama 7B (4-bit): ~4-6 GB VRAM

3. **Small embedding model**
   - `all-MiniLM-L6-v2`: ~80MB RAM
   - Avoid larger models like `all-mpnet-base-v2`

4. **Batch processing**
   - Embeddings generated in batches of 32
   - Reduces peak memory usage

## Air-Gapped Setup

### Checklist

- [x] **No network calls**: All models and data are local
- [x] **No telemetry**: FAISS/Chroma run in local-only mode
- [x] **Encrypted storage**: Index files can be encrypted if needed
- [x] **Audit logs**: Check logs to verify no network connections

### Verification

1. **Disconnect network** before running
2. **Check process logs** for any network activity
3. **Monitor firewall** for outbound connections
4. **Verify model files** are local (sentence-transformers cache)

## Troubleshooting

### "RAG system not available"

Install dependencies:
```bash
python Shared/rag_setup.py
```

### "Index not found, building..."

This is normal on first run. The index will be built automatically.

### "Out of memory" during indexing

1. Reduce batch size in `rag_system.py`:
   ```python
   batch_size = 16  # Instead of 32
   ```

2. Use smaller embedding model:
   ```python
   embedding_model = "all-MiniLM-L6-v2"  # Smallest option
   ```

3. Index fewer files:
   ```python
   file_patterns = ['*.cs']  # Only C# files
   ```

### Slow retrieval

1. Use FAISS instead of Chroma (faster)
2. Reduce `top_k` (fewer chunks to retrieve)
3. Ensure index is on fast storage (SSD)

### Poor retrieval results

1. Rebuild index with better chunking:
   ```python
   chunk_size = 1000  # Larger chunks
   ```

2. Use better embedding model:
   ```python
   embedding_model = "all-mpnet-base-v2"  # Better quality
   ```

3. Increase retrieval count:
   ```python
   top_k = 10  # More chunks
   ```

## Performance

### Indexing Time
- Small codebase (<1000 files): ~2-5 minutes
- Medium codebase (1000-5000 files): ~5-15 minutes
- Large codebase (>5000 files): ~15-30 minutes

### Retrieval Time
- FAISS: ~1-5ms per query
- Chroma: ~10-50ms per query

### Memory Usage
- Embedding model: ~80-420MB RAM (depending on model)
- FAISS index: ~10-100MB (depending on codebase size)
- Total: <1 GB RAM for typical codebase

## Security & Privacy

### Data Storage
- **Index files**: Stored locally, can be encrypted
- **Embeddings**: Generated locally, never leave machine
- **No cloud sync**: Index files are local-only

### Network Isolation
- **No API calls**: All processing is local
- **No telemetry**: FAISS/Chroma configured for local-only
- **Model downloads**: Only on first use (sentence-transformers)

### Audit
- Check logs for network activity
- Monitor firewall for outbound connections
- Verify all files are local

## Advanced Usage

### Rebuild Index

```python
from rag_system import RAGSystem
from pathlib import Path

rag = RAGSystem(
    source_path=Path("G:/CavesofQud-decompiledsource"),
    index_path=Path("rag_index/qud_source_index.faiss")
)

# Force reindex
rag.index_source_code(force_reindex=True)
```

### Custom Chunking

```python
from rag_system import CodeChunker

chunker = CodeChunker(
    chunk_size=1000,      # Larger chunks
    chunk_overlap=100     # More overlap
)
```

### Manual Retrieval

```python
results = rag_system.retrieve("GetIntProperty method", top_k=5)
for chunk, score in zip(results.chunks, results.scores):
    print(f"File: {chunk.file_path}, Score: {score:.3f}")
    print(chunk.content)
```

## Comparison: With vs Without RAG

### Without RAG
- Basic prompts with limited context
- May have indexing issues (CodeLlama 34B)
- Less accurate fixes

### With RAG
- Augmented prompts with relevant code context
- Proper source code references
- More accurate fixes matching codebase patterns
- Better understanding of API usage

## Next Steps

1. **Install dependencies**: `python Shared/rag_setup.py`
2. **Run mod fixer**: RAG will auto-initialize on first run
3. **Monitor performance**: Check retrieval times and fix quality
4. **Tune if needed**: Adjust chunk size, retrieval count, etc.

The RAG system is designed to work seamlessly with the existing mod fixer - just install dependencies and it will automatically enhance your fixes with better code context!

