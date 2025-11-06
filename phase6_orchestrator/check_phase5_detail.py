import json

with open('../pipeline.json', 'r') as f:
    data = json.load(f)
    
phase5 = data.get('phase5', {})
print('Phase 5 Status:', phase5.get('status'))
print('\nPhase 5 structure:')
print('  Keys:', list(phase5.keys()))

if 'metrics' in phase5:
    print('\nMetrics:')
    for key, val in phase5['metrics'].items():
        print(f'  {key}: {val}')

if 'chunks' in phase5:
    chunks = phase5['chunks']
    print(f'\nChunks: {len(chunks)} recorded')
    successful = [c for c in chunks if c.get('status', '').startswith('complete')]
    failed = [c for c in chunks if c.get('status') == 'failed']
    print(f'  Successful: {len(successful)}')
    print(f'  Failed: {len(failed)}')
    
    if failed:
        print('\nSample failures:')
        for c in failed[:5]:
            print(f'  Chunk {c.get("chunk_id")}: {c.get("error_message", "No error msg")}')
