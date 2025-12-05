#!/usr/bin/env python3
"""Check voice overrides in pipeline.json"""

import json
from pathlib import Path

pipeline_json = Path("pipeline.json")
data = json.load(open(pipeline_json, encoding='utf-8'))

file_id = "376953453-The-World-of-Universals"
p3 = data.get('phase3', {}).get('files', {}).get(file_id, {})

print(f'Phase 3 data for {file_id}:')
print(f'  status: {p3.get("status")}')
print(f'  total_chunks: {len(p3.get("chunk_paths", []))}')
print(f'  chunk_voice_overrides: {len(p3.get("chunk_voice_overrides", {}))} entries')

overrides = p3.get('chunk_voice_overrides', {})
if overrides:
    sample_keys = list(overrides.keys())[:5]
    print(f'\nFirst 5 overrides:')
    for key in sample_keys:
        print(f'  {key}: {overrides[key]}')
else:
    print('\nNO VOICE OVERRIDES FOUND!')
    print('This means Phase 3 did not populate chunk_voice_overrides.')
    print('Phase 4 will use default voice instead of user selection.')
