#!/usr/bin/env python3
"""
Helper script to get Ollama API options with CPU offload configured.
Can be called from PowerShell or other scripts to get the right settings.
"""

import sys
import json
from pathlib import Path

# Add the Common directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ollama_model_router import get_router

def main():
    """Get Ollama API options for a model with CPU offload."""
    if len(sys.argv) < 2:
        print("Usage: get_ollama_options.py <model_name> [num_thread] [num_predict] [temperature] [top_p] [num_ctx]")
        print("\nExample:")
        print("  get_ollama_options.py codellama:13b")
        print("  get_ollama_options.py llama3.1:8b 8 2048 0.7 0.9 4096")
        sys.exit(1)
    
    model_name = sys.argv[1]
    router = get_router()
    
    # Parse optional arguments
    num_thread = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
    num_predict = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else 0.7
    top_p = float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else 0.9
    num_ctx = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else None
    
    # Get options with CPU offload
    options = router.get_ollama_api_options(
        model_name=model_name,
        num_thread=num_thread,
        num_predict=num_predict,
        temperature=temperature,
        top_p=top_p,
        num_ctx=num_ctx
    )
    
    # Output as JSON for easy parsing
    print(json.dumps(options, indent=2))

if __name__ == "__main__":
    main()
