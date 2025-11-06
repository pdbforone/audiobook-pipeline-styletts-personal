#!/usr/bin/env python3
"""Check Phase 2 and Phase 3 status in pipeline.json"""

import json
from pathlib import Path

pipeline_json = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\pipeline.json")

with open(pipeline_json, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("📊 Phase 2 Status")
print("="*60)

phase2 = data.get('phase2', {})
files = phase2.get('files', {})

for file_id, file_data in files.items():
    if 'Systematic' in file_id:
        print(f"File: {file_id}")
        print(f"  Tool used: {file_data.get('tool_used')}")
        print(f"  Quality score: {file_data.get('quality_score')}")
        print(f"  Status: {file_data.get('status')}")
        print(f"  Duration: {file_data.get('timestamps', {}).get('duration', 0):.1f}s")
        print(f"  Text path: {file_data.get('extracted_text_path')}")
        break

print(f"\n📊 Phase 3 Error")
print("="*60)

phase3 = data.get('phase3', {})
errors = phase3.get('errors', [])

if errors:
    for error in errors[-1:]:  # Last error
        print(f"Error: {error}")

print(f"\nPhase 3 status: {phase3.get('status', 'unknown')}")
