#!/usr/bin/env python3
"""
Check Phase 1 classification for Systematic Theology
"""
import json
from pathlib import Path

pipeline_path = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\pipeline.json")

try:
    with open(pipeline_path, 'r') as f:
        data = json.load(f)
    
    # Look for Systematic Theology in phase1
    if 'phase1' in data and 'files' in data['phase1']:
        print("=" * 80)
        print("PHASE 1 FILES")
        print("=" * 80)
        
        found = False
        for file_id, file_data in data['phase1']['files'].items():
            # Safe string checks - handle None values
            file_path = file_data.get('file_path') or ''
            artifacts_path = file_data.get('artifacts_path') or ''
            
            if 'Systematic Theology' in file_id or \
               'Systematic Theology' in file_path or \
               'Systematic Theology' in artifacts_path:
                found = True
                print(f"\n📄 File ID: {file_id}")
                print(f"   Status: {file_data.get('status', 'unknown')}")
                print(f"   Classification: {file_data.get('classification', 'unknown')}")
                print(f"   File Path: {file_data.get('file_path', 'N/A')}")
                
                if 'metrics' in file_data:
                    print(f"\n   📊 Metrics:")
                    for key, value in file_data['metrics'].items():
                        print(f"      {key}: {value}")
                
                if 'errors' in file_data and file_data['errors']:
                    print(f"\n   ⚠️  Errors:")
                    for error in file_data['errors']:
                        print(f"      - {error}")
        
        if not found:
            print("\n❌ Systematic Theology not found in Phase 1!")
            print("\nAll files in Phase 1:")
            for file_id in data['phase1']['files'].keys():
                print(f"   - {file_id}")
    else:
        print("❌ No Phase 1 data found in pipeline.json")
    
    # Check phase2
    if 'phase2' in data and 'files' in data['phase2']:
        print("\n" + "=" * 80)
        print("PHASE 2 FILES")
        print("=" * 80)
        
        found = False
        for file_id, file_data in data['phase2']['files'].items():
            extracted_path = file_data.get('extracted_text_path') or ''
            if 'Systematic Theology' in file_id or 'Systematic Theology' in extracted_path:
                found = True
                print(f"\n📄 File ID: {file_id}")
                print(f"   Status: {file_data.get('status', 'unknown')}")
                print(f"   Tool used: {file_data.get('tool_used', 'unknown')}")
                print(f"   Extracted path: {extracted_path}")
                
                if 'metrics' in file_data:
                    print(f"\n   📊 Metrics:")
                    for key, value in file_data.get('metrics', {}).items():
                        print(f"      {key}: {value}")
                
                # Additional extraction metrics
                print(f"\n   Quality Scores:")
                print(f"      Yield: {file_data.get('yield_pct', 0):.2f}%")
                print(f"      Gibberish score: {file_data.get('gibberish_score', 'N/A')}")
                print(f"      Perplexity: {file_data.get('perplexity', 'N/A')}")
                print(f"      Language: {file_data.get('language', 'unknown')}")
                print(f"      Lang confidence: {file_data.get('lang_confidence', 'N/A')}")
                
                if file_data.get('errors'):
                    print(f"\n   ⚠️  Errors:")
                    for error in file_data['errors']:
                        print(f"      - {error}")
        
        if not found:
            print("\n❌ Systematic Theology not found in Phase 2!")
            print("\nAll files in Phase 2:")
            for file_id in data['phase2']['files'].keys():
                print(f"   - {file_id}")
    else:
        print("\n❌ No Phase 2 data found in pipeline.json")

except FileNotFoundError:
    print(f"❌ Pipeline.json not found at {pipeline_path}")
except json.JSONDecodeError as e:
    print(f"❌ Error parsing pipeline.json: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
