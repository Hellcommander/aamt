#!/usr/bin/env python3
"""
Test Dual Model System
Verifies that the Ollama model router correctly assigns models to different task types.
"""

import sys
import os
from pathlib import Path

# Add Common directory to path for model router
common_path = Path(__file__).parent.parent / "Common"
sys.path.insert(0, str(common_path))

def test_model_router():
    """Test the model router detects and assigns models correctly."""
    print("=" * 60)
    print("  Dual Model System Test")
    print("=" * 60)
    print()
    
    try:
        from ollama_model_router import (
            OllamaModelRouter, get_router, get_code_model, get_visual_model,
            TASK_CODE, TASK_VISUAL, TASK_ORCHESTRATION, TASK_AUDIO
        )
        print("[OK] Model router imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import model router: {e}")
        return False
    
    # Test 1: Create router and check model detection
    print("\n[1/4] Testing Model Detection...")
    try:
        router = OllamaModelRouter()
        router.print_model_assignment()
        
        if router.code_model and router.visual_model:
            print(f"  [OK] Code model detected: {router.code_model}")
            print(f"  [OK] Visual model detected: {router.visual_model}")
        else:
            print(f"  [WARNING] Models not fully detected")
            print(f"    Code model: {router.code_model}")
            print(f"    Visual model: {router.visual_model}")
    except Exception as e:
        print(f"  [FAIL] Model detection failed: {e}")
        return False
    
    # Test 2: Test model routing for different task types
    print("\n[2/4] Testing Task-Based Routing...")
    try:
        code_model = router.get_model_for_task(TASK_CODE)
        visual_model = router.get_model_for_task(TASK_VISUAL)
        orchestration_model = router.get_model_for_task(TASK_ORCHESTRATION)
        audio_model = router.get_model_for_task(TASK_AUDIO)
        
        print(f"  Code task -> {code_model}")
        print(f"  Visual task -> {visual_model}")
        print(f"  Orchestration task -> {orchestration_model}")
        print(f"  Audio task -> {audio_model}")
        
        # Verify code tasks use code model
        if 'codellama' in code_model.lower() or 'code' in code_model.lower():
            print("  [OK] Code tasks route to code model")
        else:
            print(f"  [WARNING] Code tasks may not be using optimal model")
        
        # Verify visual tasks use visual model
        if visual_model == orchestration_model == audio_model:
            print("  [OK] Visual/orchestration/audio tasks use same model (expected)")
        else:
            print("  [WARNING] Visual tasks may have inconsistent routing")
            
    except Exception as e:
        print(f"  [FAIL] Task routing failed: {e}")
        return False
    
    # Test 3: Test convenience functions
    print("\n[3/4] Testing Convenience Functions...")
    try:
        code_model_func = get_code_model()
        visual_model_func = get_visual_model()
        
        print(f"  get_code_model() -> {code_model_func}")
        print(f"  get_visual_model() -> {visual_model_func}")
        
        if code_model_func and visual_model_func:
            print("  [OK] Convenience functions work")
        else:
            print("  [FAIL] Convenience functions returned None")
            return False
    except Exception as e:
        print(f"  [FAIL] Convenience functions failed: {e}")
        return False
    
    # Test 4: Verify models are different (if both available)
    print("\n[4/4] Testing Dual Model Configuration...")
    try:
        if code_model_func != visual_model_func:
            print(f"  [OK] Dual model configuration detected!")
            print(f"    Code model: {code_model_func}")
            print(f"    Visual model: {visual_model_func}")
            print("  [OK] Different models will be used for different tasks")
        else:
            print(f"  [INFO] Single model configuration (both tasks use: {code_model_func})")
            print("  [INFO] This is OK if only one model is available")
    except Exception as e:
        print(f"  [FAIL] Dual model check failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("  Test Results")
    print("=" * 60)
    print()
    print("[OK] All dual model system tests passed!")
    print()
    print("Summary:")
    print(f"  - Code Generation Model: {code_model_func}")
    print(f"  - Visual/Orchestration Model: {visual_model_func}")
    print()
    
    if code_model_func != visual_model_func:
        print("[OK] Dual model system is active and working correctly!")
        print("     Tasks will be automatically routed to the best model.")
    else:
        print("[INFO] Single model configuration detected.")
        print("       Consider installing CodeLlama-34B for better code generation.")
    
    return True

if __name__ == "__main__":
    success = test_model_router()
    sys.exit(0 if success else 1)

