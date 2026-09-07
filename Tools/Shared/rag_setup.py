#!/usr/bin/env python3
"""
Setup script for RAG system dependencies.
Installs required packages for local, air-gapped RAG.
"""

import subprocess
import sys

def install_package(package: str):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
        print(f"  [OK] Installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"  [FAIL] Failed to install {package}")
        return False

def main():
    print("Setting up RAG system dependencies...")
    print("=" * 60)
    print()
    print("Installing packages for local, air-gapped RAG:")
    print("  - FAISS (vector store)")
    print("  - Chroma (alternative vector store)")
    print("  - sentence-transformers (local embeddings)")
    print()
    
    packages = [
        "faiss-cpu",  # CPU version (no CUDA dependency)
        "chromadb",
        "sentence-transformers"
    ]
    
    success = True
    for package in packages:
        if not install_package(package):
            success = False
    
    print()
    if success:
        print("=" * 60)
        print("[OK] All packages installed successfully")
        print()
        print("Next steps:")
        print("1. Download embedding model (runs automatically on first use)")
        print("2. Index your source code")
        print("3. Use RAG system in mod fixer")
    else:
        print("=" * 60)
        print("[FAIL] Some packages failed to install")
        print("  You may need to install them manually:")
        for package in packages:
            print(f"    pip install {package}")

if __name__ == "__main__":
    main()

