#!/usr/bin/env python3
"""
Investigate why Phase 2 took 158 minutes.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
pipeline_json = PROJECT_ROOT / "pipeline.json"

print("🔍 Investigating Phase 2 Performance")
print("="*60)

try:
    with open(pipeline_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    phase2 = data.get('phase2', {})
    files = phase2.get('files', {})
    
    # Find Systematic Theology entry
    for file_id, file_data in files.items():
        if 'Systematic' in file_id or 'systematic' in file_id.lower():
            print(f"\n📄 File: {file_id}")
            print(f"="*60)
            
            # Timing info
            timestamps = file_data.get('timestamps', {})
            duration = timestamps.get('duration', 0)
            print(f"\n⏱️  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            
            # Tool used
            tool_used = file_data.get('tool_used', 'unknown')
            print(f"\n🔧 Tool Used: {tool_used}")
            
            # Status
            status = file_data.get('status', 'unknown')
            print(f"📊 Status: {status}")
            
            # Metrics
            metrics = file_data.get('metrics', {})
            print(f"\n📈 Metrics:")
            for key, value in metrics.items():
                print(f"   {key}: {value}")
            
            # Errors
            errors = file_data.get('errors', [])
            if errors:
                print(f"\n⚠️  Errors/Warnings:")
                for error in errors:
                    print(f"   - {error}")
            else:
                print(f"\n✅ No errors")
            
            # Text quality
            print(f"\n📝 Text Quality:")
            print(f"   Yield: {file_data.get('yield_pct', 0):.2f}%")
            print(f"   Gibberish score: {file_data.get('gibberish_score', 0):.3f}")
            print(f"   Perplexity: {file_data.get('perplexity', 0):.3f}")
            print(f"   Language: {file_data.get('language', 'unknown')} (confidence: {file_data.get('lang_confidence', 0):.3f})")
            
            break
    else:
        print("❌ No Systematic Theology entry found in pipeline.json")
        print(f"\nAvailable file IDs:")
        for file_id in files.keys():
            print(f"   - {file_id}")

except Exception as e:
    print(f"❌ Error reading pipeline.json: {e}")

print("\n" + "="*60)
print("💡 Analysis:")
print("="*60)

print("""
Possible causes of 158-minute duration:
1. EasyOCR was triggered (CPU-intensive, very slow)
2. Multiple extraction methods tried sequentially
3. Language detection on huge text corpus
4. Structure extraction taking too long
5. Retry logic triggering multiple times

To fix:
- Check if classification is correct (should be 'text', not 'mixed')
- Disable structure extraction if not needed
- Optimize language detection (sample text instead of full)
""")
