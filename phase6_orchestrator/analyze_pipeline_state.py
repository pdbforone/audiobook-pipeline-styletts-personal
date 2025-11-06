import json
from pathlib import Path

with open('../pipeline.json', 'r') as f:
    data = json.load(f)

# Check Phase 5 status
phase5 = data.get('phase5', {})
chunks = phase5.get('chunks', [])

complete = [c for c in chunks if c.get('status', '').startswith('complete')]
failed = [c for c in chunks if c.get('status') == 'failed']
pending = [c for c in chunks if c.get('status') == 'pending']

print('=' * 60)
print('PHASE 5 STATUS')
print('=' * 60)
print(f'Total chunks recorded: {len(chunks)}')
print(f'Complete: {len(complete)}')
print(f'Failed: {len(failed)}')
print(f'Pending: {len(pending)}')
print()

# Check Phase 4 to see how many chunks SHOULD exist
phase4 = data.get('phase4', {})
files = phase4.get('files', {})

print('=' * 60)
print('PHASE 4 AUDIO CHUNKS')
print('=' * 60)
for file_id, file_data in files.items():
    chunk_paths = file_data.get('chunk_audio_paths', [])
    print(f'\nFile ID: {file_id}')
    print(f'  Total chunks: {len(chunk_paths)}')
    print(f'  Status: {file_data.get("status")}')
    if chunk_paths:
        print(f'  First: {Path(chunk_paths[0]).name}')
        print(f'  Last: {Path(chunk_paths[-1]).name}')
        
        # Check how many exist
        exists = sum(1 for p in chunk_paths if Path(p).exists())
        print(f'  Files exist: {exists}/{len(chunk_paths)}')

# THE PROBLEM: Why only 433 chunks attempted?
print()
print('=' * 60)
print('DIAGNOSIS')
print('=' * 60)

if len(complete) > 0:
    print(f'❌ resume_on_failure=true is skipping {len(complete)} already-complete chunks')
    print(f'   Only {len(failed)} + {len(pending)} = {len(failed) + len(pending)} chunks being retried')
else:
    print(f'✓ No complete chunks found, all should be reprocessed')

phase4_total = sum(len(f.get('chunk_audio_paths', [])) for f in files.values())
phase5_attempted = len(chunks)

if phase4_total > phase5_attempted:
    print(f'\n❌ Phase 5 only attempted {phase5_attempted}/{phase4_total} chunks!')
    print(f'   Missing: {phase4_total - phase5_attempted} chunks')
    print(f'   Likely cause: Phase 5 couldn\'t find audio files or hit an early error')
elif phase4_total < phase5_attempted:
    print(f'\n⚠️  Phase 5 has MORE chunks ({phase5_attempted}) than Phase 4 ({phase4_total})')
    print(f'   This suggests duplicate processing or stale data')
else:
    print(f'\n✓ Phase 4 and Phase 5 chunk counts match ({phase4_total})')

# Show some failure details
if failed:
    print()
    print('=' * 60)
    print('SAMPLE FAILURES (first 5)')
    print('=' * 60)
    from collections import Counter
    errors = Counter(c.get('error_message', 'Unknown') for c in failed)
    for error, count in errors.most_common(5):
        print(f'{count:4d}x: {error[:80]}')
