#!/usr/bin/env python3
"""
Local RAG (Retrieval-Augmented Generation) System for Mod Fixing
- Uses local vector stores (FAISS/Chroma) for code retrieval
- Local embedding models (sentence-transformers)
- Air-gapped, no cloud dependencies
- Optimized for <11 GB VRAM
"""

import os
import sys
import json
import hashlib
import pickle
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import re

# File locking for multi-instance coordination
try:
    if sys.platform == 'win32':
        import msvcrt
        HAS_FILE_LOCKING = True
    else:
        import fcntl
        HAS_FILE_LOCKING = True
except ImportError:
    HAS_FILE_LOCKING = False

# Try to import FAISS (preferred for local use)
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Try to import Chroma (alternative)
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# Try to import sentence-transformers for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Configuration
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Small, fast, local-only
DEFAULT_CHUNK_SIZE = 500  # Characters per chunk
DEFAULT_CHUNK_OVERLAP = 50  # Overlap between chunks
DEFAULT_TOP_K = 5  # Number of chunks to retrieve


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'block', 'file'
    metadata: Dict[str, Any]


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    chunks: List[CodeChunk]
    scores: List[float]
    query: str


class LocalEmbedder:
    """Local embedding model using sentence-transformers."""
    
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, device: str = "cpu"):
        """
        Initialize local embedding model.
        
        Args:
            model_name: Name of sentence-transformer model
            - "all-MiniLM-L6-v2" (default, ~80MB, fast, CPU-friendly)
            - "all-mpnet-base-v2" (better quality, ~420MB)
            - "paraphrase-MiniLM-L6-v2" (good for code)
        device: "cpu" or "cuda" (use CPU for air-gapped, low-VRAM setups)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not available. Install with: pip install sentence-transformers")
        
        try:
            # Load model locally (downloads once, then cached)
            print(f"  Loading local embedding model: {model_name}")
            print(f"  Device: {device} (use CPU for air-gapped/low-VRAM)")
            # Suppress warnings that might contain Unicode characters
            import warnings
            import sys
            import io
            # Capture stderr to prevent Unicode encoding errors from library output
            old_stderr = sys.stderr
            try:
                # Use a safe encoding for stderr
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
                self.model = SentenceTransformer(model_name, device=device)
            finally:
                sys.stderr = old_stderr
            print(f"  [OK] Embedding model loaded")
        except Exception as e:
            # Convert exception message to safe ASCII
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            raise RuntimeError(f"Failed to load embedding model {model_name}: {error_msg}")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        # Generate embeddings (local, no network calls)
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        return self.embed([query])[0]


class FAISSVectorStore:
    """Local FAISS vector store for code chunks with multi-instance support."""
    
    def __init__(self, index_path: Optional[Path] = None, dimension: int = 384, enable_locking: bool = True):
        """
        Initialize FAISS vector store.
        
        Args:
            index_path: Path to save/load FAISS index
            dimension: Embedding dimension (384 for all-MiniLM-L6-v2)
            enable_locking: Enable file locking for multi-instance coordination
        """
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.chunks: List[CodeChunk] = []
        self.metadata_path = None
        self.enable_locking = enable_locking and HAS_FILE_LOCKING
        self.lock_file: Optional[Path] = None
        self.lock_handle = None
        self._lock = threading.Lock()  # Thread-safe access
        
        # Setup file locking if enabled
        if self.enable_locking and index_path:
            self._setup_file_locking()
        
        if index_path:
            self.metadata_path = index_path.parent / f"{index_path.stem}_metadata.pkl"
            self.load()
        else:
            # Create new index
            self.index = faiss.IndexFlatL2(dimension)  # L2 distance
    
    def _setup_file_locking(self):
        """Setup file locking for multi-instance coordination."""
        if not self.index_path:
            return
        
        # Create lock file path
        self.lock_file = self.index_path.parent / f"{self.index_path.stem}.lock"
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create lock file if it doesn't exist
        if not self.lock_file.exists():
            self.lock_file.touch()
    
    def _check_lock_stale(self) -> bool:
        """Check if the lock file is stale (process no longer exists)."""
        if not self.lock_file or not self.lock_file.exists():
            return True
        
        try:
            with open(self.lock_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 1:
                    pid_str = lines[0].strip()
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        # Check if process is still running
                        try:
                            import psutil
                            if not psutil.pid_exists(pid):
                                return True  # Process is dead, lock is stale
                        except ImportError:
                            # psutil not available, try alternative method
                            if sys.platform == 'win32':
                                import subprocess
                                try:
                                    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                          capture_output=True, timeout=2)
                                    if pid_str not in result.stdout.decode('utf-8', errors='ignore'):
                                        return True  # Process doesn't exist
                                except:
                                    return True  # Assume stale if check fails
                            else:
                                # Unix: try to send signal 0 (doesn't kill, just checks)
                                try:
                                    os.kill(pid, 0)
                                    return False  # Process exists
                                except OSError:
                                    return True  # Process doesn't exist
        except Exception:
            pass
        
        return False  # Can't determine, assume not stale
    
    def _force_unlock_stale(self):
        """Force unlock if the lock is stale (process no longer exists)."""
        if self._check_lock_stale():
            try:
                if self.lock_file and self.lock_file.exists():
                    self.lock_file.unlink()
                    print("  [RAG] Removed stale lock file (previous process no longer running)")
            except Exception as e:
                print(f"  [RAG] Warning: Could not remove stale lock: {e}")
    
    def _acquire_lock(self, timeout: float = 10.0, retry_interval: float = 0.5):
        """
        Acquire file lock for index access (waits if another instance is using it).
        
        Args:
            timeout: Maximum time to wait for lock (default: 10 seconds)
            retry_interval: Time between retry attempts (default: 0.5 seconds)
        """
        if not self.enable_locking or not self.lock_file:
            return True
        
        # Check for stale lock first
        self._force_unlock_stale()
        
        start_time = time.time()
        attempt = 0
        while time.time() - start_time < timeout:
            attempt += 1
            try:
                if sys.platform == 'win32':
                    # Windows file locking (non-blocking)
                    self.lock_handle = open(self.lock_file, 'r+')
                    msvcrt.locking(self.lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    # Unix file locking (non-blocking)
                    self.lock_handle = open(self.lock_file, 'r+')
                    fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Write PID and timestamp to lock file for debugging
                self.lock_handle.seek(0)
                self.lock_handle.truncate()
                self.lock_handle.write(f"{os.getpid()}\n{time.time()}\n")
                self.lock_handle.flush()
                return True
            except (IOError, OSError):
                # Lock is held by another instance
                # Check if it's stale before waiting
                if attempt % 4 == 0:  # Check every 2 seconds (4 * 0.5s)
                    if self._check_lock_stale():
                        self._force_unlock_stale()
                        continue  # Retry immediately after unlocking stale lock
                
                if self.lock_handle:
                    try:
                        self.lock_handle.close()
                    except:
                        pass
                    self.lock_handle = None
                time.sleep(retry_interval)  # Wait before retry
            except Exception as e:
                # Other error - try to continue without lock
                if self.lock_handle:
                    try:
                        self.lock_handle.close()
                    except:
                        pass
                    self.lock_handle = None
                print(f"  [RAG] Warning: Error acquiring lock: {e}")
                time.sleep(retry_interval)
        
        # Final check for stale lock before giving up
        if self._check_lock_stale():
            self._force_unlock_stale()
            # Try one more time
            try:
                if sys.platform == 'win32':
                    self.lock_handle = open(self.lock_file, 'r+')
                    msvcrt.locking(self.lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    self.lock_handle = open(self.lock_file, 'r+')
                    fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lock_handle.seek(0)
                self.lock_handle.truncate()
                self.lock_handle.write(f"{os.getpid()}\n{time.time()}\n")
                self.lock_handle.flush()
                print("  [RAG] Acquired lock after removing stale lock")
                return True
            except:
                pass
        
        print(f"  [RAG] Warning: Could not acquire index lock after {timeout}s.")
        print(f"  [RAG] Continuing without RAG (will use basic prompts)")
        return False
    
    def _release_lock(self):
        """Release file lock (silently handles permission errors during cleanup)."""
        if self.lock_handle:
            try:
                if sys.platform == 'win32':
                    msvcrt.locking(self.lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
                self.lock_handle.close()
            except (OSError, IOError, PermissionError):
                # Permission errors are non-critical during cleanup
                # Silently ignore - file may already be closed or locked by another process
                pass
            except Exception:
                # Other errors are also non-critical during cleanup
                pass
            finally:
                self.lock_handle = None
    
    def add_chunks(self, chunks: List[CodeChunk], embeddings: List[List[float]]):
        """Add chunks and their embeddings to the index."""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        if not self.index:
            self.index = faiss.IndexFlatL2(self.dimension)
        
        # Convert embeddings to numpy array
        import numpy as np
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Add to index
        self.index.add(embeddings_array)
        
        # Store chunks
        self.chunks.extend(chunks)
    
    def search(self, query_embedding: List[float], top_k: int = DEFAULT_TOP_K) -> RetrievalResult:
        """Search for similar chunks (with lock handling - non-blocking)."""
        if not self.index or self.index.ntotal == 0:
            return RetrievalResult(chunks=[], scores=[], query="")
        
        # Try to acquire lock for read access (non-blocking, very short timeout)
        # If lock fails, return empty results immediately (don't block)
        lock_acquired = False
        if self.enable_locking:
            lock_acquired = self._acquire_lock(timeout=1.0)  # Very short timeout
            if not lock_acquired:
                # Lock failed - return empty results immediately (non-blocking)
                return RetrievalResult(chunks=[], scores=[], query="")
        
        try:
            import numpy as np
            query_array = np.array([query_embedding]).astype('float32')
            
            # Search
            distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
            
            # Get results
            results = []
            scores = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.chunks):
                    results.append(self.chunks[idx])
                    # Convert L2 distance to similarity score (lower distance = higher similarity)
                    scores.append(1.0 / (1.0 + distances[0][i]))
            
            return RetrievalResult(chunks=results, scores=scores, query="")
        except Exception as e:
            # If search fails (e.g., lock issue), return empty results
            return RetrievalResult(chunks=[], scores=[], query="")
        finally:
            if lock_acquired:
                self._release_lock()
    
    def save(self):
        """Save index and metadata to disk (with file locking)."""
        if not self.index_path:
            return
        
        # Acquire lock before saving (with shorter timeout for save operations)
        if not self._acquire_lock(timeout=5.0):
            print("  [RAG] Warning: Could not acquire lock, skipping save")
            print("  [RAG] Index will be saved on next successful lock acquisition")
            return
        
        try:
            with self._lock:  # Thread-safe
                # Save FAISS index
                faiss.write_index(self.index, str(self.index_path))
                
                # Save metadata
                if self.metadata_path:
                    with open(self.metadata_path, 'wb') as f:
                        pickle.dump(self.chunks, f)
        except Exception as e:
            print(f"  [RAG] Warning: Failed to save vector store: {e}")
        finally:
            self._release_lock()
    
    def load(self):
        """Load index and metadata from disk (with file locking)."""
        if not self.index_path or not self.index_path.exists():
            return
        
        # Acquire lock before loading (read-only, can be more lenient)
        if not self._acquire_lock(timeout=5.0):
            print("  [RAG] Warning: Could not acquire lock, may load stale index")
            print("  [RAG] Continuing with read-only access (no guarantees)")
        
        try:
            with self._lock:  # Thread-safe
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load metadata
                if self.metadata_path and self.metadata_path.exists():
                    with open(self.metadata_path, 'rb') as f:
                        self.chunks = pickle.load(f)
        except Exception as e:
            print(f"  Warning: Failed to load vector store: {e}")
            self.index = None
            self.chunks = []
        finally:
            self._release_lock()
    
    def __del__(self):
        """Cleanup: release lock on destruction."""
        self._release_lock()


class ChromaVectorStore:
    """Local Chroma vector store (alternative to FAISS)."""
    
    def __init__(self, persist_directory: Optional[Path] = None, collection_name: str = "code_chunks"):
        """
        Initialize Chroma vector store.
        
        Args:
            persist_directory: Directory to persist Chroma database
            collection_name: Name of the collection
        """
        if not CHROMA_AVAILABLE:
            raise ImportError("Chroma not available. Install with: pip install chromadb")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Configure Chroma for local-only use (no telemetry, no network)
        settings = Settings(
            anonymized_telemetry=False,  # Disable telemetry
            allow_reset=True,
            is_persistent=persist_directory is not None
        )
        
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def add_chunks(self, chunks: List[CodeChunk], embeddings: List[List[float]]):
        """Add chunks and their embeddings to Chroma."""
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        documents = [chunk.content for chunk in chunks]
        metadatas = [asdict(chunk) for chunk in chunks]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(self, query_embedding: List[float], top_k: int = DEFAULT_TOP_K) -> RetrievalResult:
        """Search for similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        chunks = []
        scores = []
        
        if results['documents'] and len(results['documents'][0]) > 0:
            for i, doc in enumerate(results['documents'][0]):
                # Reconstruct CodeChunk from metadata
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                chunk = CodeChunk(
                    content=doc,
                    file_path=metadata.get('file_path', ''),
                    start_line=metadata.get('start_line', 0),
                    end_line=metadata.get('end_line', 0),
                    chunk_type=metadata.get('chunk_type', 'block'),
                    metadata=metadata.get('metadata', {})
                )
                chunks.append(chunk)
                # Chroma returns distances, convert to similarity
                if results['distances']:
                    scores.append(1.0 / (1.0 + results['distances'][0][i]))
        
        return RetrievalResult(chunks=chunks, scores=scores, query="")


class CodeChunker:
    """Chunk code files into smaller pieces for indexing."""
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_file(self, file_path: Path, content: str) -> List[CodeChunk]:
        """
        Chunk a code file into smaller pieces.
        
        Tries to chunk at function/class boundaries when possible.
        """
        chunks = []
        lines = content.split('\n')
        
        # Try to chunk by functions/classes first
        if self._is_code_file(file_path):
            function_chunks = self._chunk_by_functions(file_path, content, lines)
            if function_chunks:
                return function_chunks
        
        # Fallback to sliding window chunking
        current_chunk = []
        current_start = 0
        current_line = 0
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            current_length = len('\n'.join(current_chunk))
            
            if current_length >= self.chunk_size:
                # Create chunk
                chunk_content = '\n'.join(current_chunk)
                chunks.append(CodeChunk(
                    content=chunk_content,
                    file_path=str(file_path),
                    start_line=current_line,
                    end_line=i,
                    chunk_type='block',
                    metadata={'language': self._detect_language(file_path)}
                ))
                
                # Start next chunk with overlap
                overlap_lines = self.chunk_overlap // (len(line) + 1) if line else 0
                current_chunk = current_chunk[-overlap_lines:] if overlap_lines > 0 else []
                current_line = i - overlap_lines + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk),
                file_path=str(file_path),
                start_line=current_line,
                end_line=len(lines) - 1,
                chunk_type='block',
                metadata={'language': self._detect_language(file_path)}
            ))
        
        return chunks
    
    def _is_code_file(self, file_path: Path) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.cs', '.java', '.py', '.cpp', '.c', '.h', '.hpp', '.js', '.ts'}
        return file_path.suffix.lower() in code_extensions
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
            '.cs': 'csharp',
            '.java': 'java',
            '.py': 'python',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.js': 'javascript',
            '.ts': 'typescript'
        }
        return ext_to_lang.get(file_path.suffix.lower(), 'unknown')
    
    def _chunk_by_functions(self, file_path: Path, content: str, lines: List[str]) -> List[CodeChunk]:
        """Try to chunk by function/class boundaries."""
        chunks = []
        
        # Simple regex-based function/class detection
        if file_path.suffix == '.cs':
            # C# patterns
            pattern = r'(public|private|protected|internal)?\s*(static)?\s*(class|interface|struct|enum|namespace)\s+\w+'
        elif file_path.suffix == '.java':
            # Java patterns
            pattern = r'(public|private|protected)?\s*(static)?\s*(class|interface|enum)\s+\w+'
        elif file_path.suffix == '.py':
            # Python patterns
            pattern = r'(class|def)\s+\w+'
        else:
            return []  # Not supported
        
        matches = list(re.finditer(pattern, content))
        if not matches:
            return []
        
        # Create chunks for each function/class
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            chunk_content = content[start_pos:end_pos]
            start_line = content[:start_pos].count('\n')
            end_line = content[:end_pos].count('\n')
            
            # Skip if chunk is too large
            if len(chunk_content) > self.chunk_size * 2:
                # Split large chunks
                sub_chunks = self._split_large_chunk(chunk_content, start_line)
                chunks.extend(sub_chunks)
            else:
                chunks.append(CodeChunk(
                    content=chunk_content,
                    file_path=str(file_path),
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type='function' if 'def' in match.group() or 'function' in match.group() else 'class',
                    metadata={'language': self._detect_language(file_path)}
                ))
        
        return chunks
    
    def _split_large_chunk(self, content: str, start_line: int) -> List[CodeChunk]:
        """Split a large chunk into smaller pieces."""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_start = start_line
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            if len('\n'.join(current_chunk)) >= self.chunk_size:
                chunks.append(CodeChunk(
                    content='\n'.join(current_chunk),
                    file_path='',  # Will be set by caller
                    start_line=current_start,
                    end_line=current_start + i,
                    chunk_type='block',
                    metadata={}
                ))
                current_chunk = []
                current_start = current_start + i + 1
        
        if current_chunk:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk),
                file_path='',
                start_line=current_start,
                end_line=current_start + len(current_chunk) - 1,
                chunk_type='block',
                metadata={}
            ))
        
        return chunks


class RAGSystem:
    """Complete RAG system for code retrieval and augmentation."""
    
    def __init__(
        self,
        source_path: Path,
        index_path: Optional[Path] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        use_faiss: bool = True,
        device: str = "cpu"
    ):
        """
        Initialize RAG system.
        
        Args:
            source_path: Path to source code directory
            index_path: Path to save/load vector store index
            embedding_model: Name of sentence-transformer model
            use_faiss: Use FAISS (True) or Chroma (False)
            device: "cpu" or "cuda" (use CPU for air-gapped/low-VRAM)
        """
        self.source_path = Path(source_path)
        self.index_path = index_path
        self.embedder = LocalEmbedder(model_name=embedding_model, device=device)
        self.chunker = CodeChunker()
        
        # Initialize vector store (with file locking for multi-instance support)
        if use_faiss and FAISS_AVAILABLE:
            dimension = self.embedder.model.get_sentence_embedding_dimension()
            self.vector_store = FAISSVectorStore(
                index_path=index_path,
                dimension=dimension,
                enable_locking=True  # Enable file locking for multi-instance coordination
            )
        elif CHROMA_AVAILABLE:
            self.vector_store = ChromaVectorStore(persist_directory=index_path)
        else:
            raise RuntimeError("Neither FAISS nor Chroma available. Install one: pip install faiss-cpu OR pip install chromadb")
        
        self.indexed = False
    
    def index_source_code(self, file_patterns: List[str] = None, force_reindex: bool = False):
        """
        Index source code files.
        
        Args:
            file_patterns: List of file patterns to index (e.g., ['*.cs', '*.java'])
            force_reindex: Force reindexing even if index exists
        """
        if self.indexed and not force_reindex:
            print("  Index already exists, skipping indexing")
            return
        
        if file_patterns is None:
            file_patterns = ['*.cs', '*.java', '*.py', '*.cpp', '*.c', '*.h']
        
        print(f"  Indexing source code from: {self.source_path}")
        print(f"  File patterns: {file_patterns}")
        
        all_chunks = []
        
        # Find and chunk all files
        for pattern in file_patterns:
            for file_path in self.source_path.rglob(pattern):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    chunks = self.chunker.chunk_file(file_path, content)
                    all_chunks.extend(chunks)
                    print(f"    Indexed {file_path.name}: {len(chunks)} chunks")
                except Exception as e:
                    print(f"    Warning: Failed to index {file_path}: {e}")
        
        if not all_chunks:
            print("  No chunks found to index")
            return
        
        print(f"  Generating embeddings for {len(all_chunks)} chunks...")
        print(f"  This may take a moment (running locally, no network calls)...")
        
        # Generate embeddings in batches to manage memory
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            batch_texts = [chunk.content for chunk in batch]
            batch_embeddings = self.embedder.embed(batch_texts)
            all_embeddings.extend(batch_embeddings)
            
            if (i // batch_size + 1) % 10 == 0:
                print(f"    Processed {i + len(batch)}/{len(all_chunks)} chunks...")
        
        print(f"  Adding chunks to vector store...")
        self.vector_store.add_chunks(all_chunks, all_embeddings)
        
        # Save index
        if self.index_path:
            print(f"  Saving index to: {self.index_path}")
            self.vector_store.save()
        
        self.indexed = True
        print(f"  [OK] Indexed {len(all_chunks)} chunks from source code")
    
    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> RetrievalResult:
        """
        Retrieve relevant code chunks for a query.
        
        Args:
            query: Search query (e.g., "GetIntProperty method")
            top_k: Number of chunks to retrieve
        
        Returns:
            RetrievalResult with relevant chunks (empty if lock fails or error occurs)
        """
        if not self.indexed:
            print(f"  [RAG] Warning: Index not built, returning empty results")
            return RetrievalResult(chunks=[], scores=[], query=query)
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(query)
            
            # Search vector store (handles locks internally)
            results = self.vector_store.search(query_embedding, top_k=top_k)
            results.query = query
            
            if not results.chunks:
                print(f"  [RAG] No chunks retrieved for query (lock may be held or index empty)")
            
            return results
        except Exception as e:
            print(f"  [RAG] Error during retrieval: {e}")
            # Return empty results instead of crashing
            return RetrievalResult(chunks=[], scores=[], query=query)
    
    def build_rag_prompt(
        self,
        query: str,
        retrieved_chunks: RetrievalResult,
        task_description: str,
        constraints: List[str] = None
    ) -> str:
        """
        Build a RAG-augmented prompt with retrieved context.
        
        Args:
            query: The original query/task
            retrieved_chunks: Retrieved code chunks
            task_description: Description of what needs to be done
            constraints: List of constraints (e.g., ["no external calls", "maintain compatibility"])
        
        Returns:
            Complete prompt with context
        """
        prompt_parts = [
            "# Task",
            task_description,
            "",
            "# Query",
            query,
            ""
        ]
        
        if constraints:
            prompt_parts.extend([
                "# Constraints",
                "\n".join(f"- {c}" for c in constraints),
                ""
            ])
        
        if retrieved_chunks.chunks:
            prompt_parts.append("# Relevant Code Context (from source code)")
            prompt_parts.append("")
            
            for i, (chunk, score) in enumerate(zip(retrieved_chunks.chunks, retrieved_chunks.scores), 1):
                prompt_parts.append(f"## Context {i} (similarity: {score:.3f})")
                prompt_parts.append(f"File: {chunk.file_path}")
                prompt_parts.append(f"Lines: {chunk.start_line}-{chunk.end_line}")
                prompt_parts.append(f"Type: {chunk.chunk_type}")
                prompt_parts.append("```")
                prompt_parts.append(chunk.content[:1000])  # Limit chunk size in prompt
                if len(chunk.content) > 1000:
                    prompt_parts.append("// ... (truncated) ...")
                prompt_parts.append("```")
                prompt_parts.append("")
        
        prompt_parts.extend([
            "# Instructions",
            "Using the relevant code context above, provide a fix that:",
            "1. Matches the patterns and style of the retrieved code",
            "2. Follows all constraints listed above",
            "3. Maintains compatibility with the existing codebase",
            "4. Includes proper error handling",
            "",
            "Provide only the fixed code, no explanations."
        ])
        
        return "\n".join(prompt_parts)

