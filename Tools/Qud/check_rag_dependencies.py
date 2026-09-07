#!/usr/bin/env python3
"""Check RAG system dependencies."""

import sys
import os

# Add Shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Shared"))

print("=" * 60)
print("RAG System Dependency Check")
print("=" * 60)
print()

missing = []

# Check FAISS
try:
    import faiss
    print("[OK] faiss-cpu: Available")
except ImportError:
    print("[FAIL] faiss-cpu: MISSING")
    missing.append("faiss-cpu")

# Check sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    print("[OK] sentence-transformers: Available")
except ImportError:
    print("[FAIL] sentence-transformers: MISSING")
    missing.append("sentence-transformers")

# Check numpy
try:
    import numpy
    print("[OK] numpy: Available")
except ImportError:
    print("[FAIL] numpy: MISSING")
    missing.append("numpy")

# Check Chroma (optional)
try:
    import chromadb
    print("[OK] chromadb: Available (optional)")
except ImportError:
    print("[INFO] chromadb: Not installed (optional, FAISS is preferred)")

print()
if missing:
    print("=" * 60)
    print("[FAIL] Missing dependencies detected!")
    print()
    print("To install missing packages, run:")
    print(f"  python Shared/rag_setup.py")
    print()
    print("Or install manually:")
    for package in missing:
        print(f"  pip install {package}")
else:
    print("=" * 60)
    print("[OK] All required dependencies are available!")
    print("RAG system is ready to use.")

