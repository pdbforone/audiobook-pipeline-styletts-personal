#!/usr/bin/env python3
"""Check what's actually in pipeline.json for Systematic Theology."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
pipeline_json = PROJECT_ROOT / "pipeline.json"

print("🔍 Checking pipeline.json Status")
print("="*60)

try:
    with open(pipeline_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check Phase 1
    phase1 = data.get('phase1', {})
    print(f"\n📋 Phase 1:")
    print(f"   Overall Status: {phase1.get('status', 'not set')}")
    
    files = phase1.get('files', {})
    for file_id, file_data in files.items():
        if 'Systematic' in file_id:
            print(f"   File: {file_id}")
            print(f"   Classification: {file_data.get('classification', 'unknown')}")
            print(f"   Status: {file_data.get('status', 'not set')}")
            print(f"   Duration: {file_data.get('timestamps', {}).get('duration', 0):.1f}s")
    
    # Check Phase 2
    phase2 = data.get('phase2', {})
    print(f"\n📋 Phase 2:")
    print(f"   Overall Status: {phase2.get('status', 'not set')}")
    
    files = phase2.get('files', {})
    for file_id, file_data in files.items():
        if 'Systematic' in file_id:
            print(f"   File: {file_id}")
            print(f"   Tool Used: {file_data.get('tool_used', 'unknown')}")
            print(f"   Status: {file_data.get('status', 'not set')}")
            print(f"   Duration: {file_data.get('timestamps', {}).get('duration', 0):.1f}s")
            print(f"   Extracted Path: {file_data.get('extracted_text_path', 'not set')}")
    
    # Check if there are multiple file_ids
    print(f"\n📊 All File IDs in pipeline.json:")
    all_file_ids = set()
    for phase_num in range(1, 6):
        phase_key = f"phase{phase_num}"
        phase_data = data.get(phase_key, {})
        files = phase_data.get('files', {})
        all_file_ids.update(files.keys())
    
    for file_id in sorted(all_file_ids):
        print(f"   - {file_id}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
