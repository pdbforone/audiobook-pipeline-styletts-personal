#!/usr/bin/env python3
"""Check what Phase 1 classified this PDF as."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

pipeline_json = PROJECT_ROOT / "pipeline.json"

print("🔍 Checking Phase 1 Classification")
print("="*60)

try:
    with open(pipeline_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    phase1 = data.get('phase1', {})
    files = phase1.get('files', {})
    
    print(f"\n📋 Phase 1 Status: {phase1.get('status', 'unknown')}")
    print(f"\nFiles in Phase 1:")
    
    for file_id, file_data in files.items():
        if 'Systematic' in file_id or 'systematic' in file_id.lower():
            print(f"\n✅ Found: {file_id}")
            classification = file_data.get('classification', 'UNKNOWN')
            print(f"   Classification: {classification}")
            print(f"   Status: {file_data.get('status', 'unknown')}")
            
            if classification != 'text':
                print(f"\n   ⚠️  WARNING: Classification should be 'text', not '{classification}'!")
                print(f"   This is why EasyOCR was triggered!")
            else:
                print(f"\n   ✅ Classification is correct")
            break
    else:
        print("\n❌ Systematic Theology NOT found in Phase 1!")
        print("   This is why Phase 2 couldn't determine the classification!")
        print("\nAvailable files:")
        for file_id in files.keys():
            print(f"   - {file_id}")
        
        if not files:
            print("   (none)")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("💡 Solution:")
print("="*60)
print("""
To prevent EasyOCR from being triggered:

1. ALWAYS run Phase 1 before Phase 2:
   python orchestrator.py <file> --phases 1 2
   
2. OR ensure Phase 1 data exists in pipeline.json

3. OR add a fallback classification in extraction.py:
   classification = phase1_data.get("classification", "text")  # Default to 'text'

Phase 1 is FAST (< 5 seconds) and prevents this 158-minute waste!
""")
