#!/usr/bin/env python3
"""
Analyze Phase 5 failures to understand why chunks are failing
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
pipeline_json = PROJECT_ROOT / "pipeline.json"
phase5_log = PROJECT_ROOT / "phase5_enhancement" / "audio_enhancement.log"

print("=" * 70)
print("PHASE 5 FAILURE ANALYSIS")
print("=" * 70)

# Load pipeline.json
if not pipeline_json.exists():
    print(f"❌ pipeline.json not found: {pipeline_json}")
    exit(1)

with open(pipeline_json, 'r') as f:
    data = json.load(f)

phase5_data = data.get('phase5', {})
chunks = phase5_data.get('chunks', [])

if not chunks:
    print("❌ No chunk data in pipeline.json")
    exit(1)

print(f"\n📊 Total chunks: {len(chunks)}")

# Analyze status
statuses = Counter(c.get('status', 'unknown') for c in chunks)
print("\n📈 Status breakdown:")
for status, count in statuses.most_common():
    print(f"   {status}: {count}")

# Find failed chunks
failed_chunks = [c for c in chunks if c.get('status') == 'failed']
print(f"\n❌ Failed chunks: {len(failed_chunks)}")

if failed_chunks:
    # Analyze error messages
    error_messages = [c.get('error_message', 'No error message') for c in failed_chunks]
    error_counts = Counter(error_messages)
    
    print("\n🔍 Top failure reasons:")
    for error, count in error_counts.most_common(10):
        # Truncate long errors
        display_error = error if len(error) < 80 else error[:77] + "..."
        print(f"   [{count}x] {display_error}")
    
    # Show sample failed chunk IDs
    print(f"\n📋 Sample failed chunk IDs:")
    sample_ids = [c.get('chunk_id', '?') for c in failed_chunks[:20]]
    print(f"   {sample_ids}")

# Analyze successful chunks
successful_chunks = [c for c in chunks if c.get('status', '').startswith('complete')]
print(f"\n✅ Successful chunks: {len(successful_chunks)}")

if successful_chunks:
    print("\n📋 Sample successful chunk IDs:")
    sample_ids = [c.get('chunk_id', '?') for c in successful_chunks[:20]]
    print(f"   {sample_ids}")

# Check quality metrics
print("\n📊 Quality metrics:")
snr_values = [c.get('snr_post', 0) for c in successful_chunks if c.get('snr_post')]
if snr_values:
    avg_snr = sum(snr_values) / len(snr_values)
    print(f"   Average SNR: {avg_snr:.1f} dB")

# Check log file for more details
print("\n📄 Log file analysis:")
if phase5_log.exists():
    print(f"   Log exists: {phase5_log}")
    
    # Read last 100 lines
    with open(phase5_log, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        last_100 = lines[-100:] if len(lines) > 100 else lines
    
    # Count error types
    error_lines = [l for l in last_100 if 'ERROR' in l or 'FAILED' in l or 'failed' in l.lower()]
    warning_lines = [l for l in last_100 if 'WARNING' in l or 'WARN' in l]
    
    print(f"   Recent errors: {len(error_lines)}")
    print(f"   Recent warnings: {len(warning_lines)}")
    
    if error_lines:
        print("\n🔴 Recent error samples:")
        for line in error_lines[:5]:
            print(f"   {line.strip()}")
    
    if warning_lines:
        print("\n🟡 Recent warning samples:")
        for line in warning_lines[:5]:
            print(f"   {line.strip()}")
else:
    print(f"   ❌ Log not found: {phase5_log}")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)

# Provide diagnosis
if len(failed_chunks) > len(successful_chunks):
    print("⚠️  MAJORITY OF CHUNKS ARE FAILING")
    print("\nPossible causes:")
    print("1. Quality validation is too strict (rejecting good audio)")
    print("2. Audio files are corrupted or malformed")
    print("3. Enhancement process has a bug")
    print("4. Resource exhaustion (memory, disk space)")
    
    print("\n💡 Recommendations:")
    print("1. Disable quality validation in config.yaml")
    print("2. Check disk space and memory")
    print("3. Try processing a single chunk to debug")
    print("4. Check Phase 5 log for detailed errors")

print("=" * 70)
