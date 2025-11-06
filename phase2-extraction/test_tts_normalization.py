#!/usr/bin/env python3
"""
Test that extraction.py now uses TTS normalization.
"""

import subprocess
import sys
from pathlib import Path

def test_extraction_with_normalization():
    """Test that extraction.py properly normalizes text."""
    phase2_dir = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction")
    
    print("🧪 Testing Phase 2 Extraction with TTS Normalization")
    print("="*60)
    
    # Check that tts_normalizer.py exists
    normalizer_path = phase2_dir / "src" / "phase2_extraction" / "tts_normalizer.py"
    if not normalizer_path.exists():
        print(f"❌ ERROR: tts_normalizer.py not found at {normalizer_path}")
        return False
    
    print(f"✅ Found tts_normalizer.py")
    
    # Check extraction.py imports it
    extraction_path = phase2_dir / "src" / "phase2_extraction" / "extraction.py"
    with open(extraction_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'from tts_normalizer import normalize_for_tts' in code:
        print(f"✅ extraction.py imports TTS normalizer")
    else:
        print(f"❌ extraction.py does NOT import TTS normalizer")
        return False
    
    if 'normalize_for_tts(text)' in code:
        print(f"✅ extraction.py calls normalize_for_tts()")
    else:
        print(f"❌ extraction.py does NOT call normalize_for_tts()")
        return False
    
    print("\n" + "="*60)
    print("✅ Phase 2 is configured for TTS normalization!")
    print("="*60)
    print("\n💡 Next Steps:")
    print("  1. Re-run orchestrator on Systematic Theology")
    print("  2. Compare output to test version")
    print("  3. Verify 0 multiple-space issues")
    print("\nCommand:")
    print("  cd phase6_orchestrator")
    print("  python orchestrator.py \"C:/path/to/Systematic Theology.pdf\"")
    
    return True

if __name__ == "__main__":
    success = test_extraction_with_normalization()
    sys.exit(0 if success else 1)
