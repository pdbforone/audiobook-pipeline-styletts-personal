import json

with open('../pipeline.json', 'r') as f:
    data = json.load(f)
    
phase4 = data.get('phase4', {})
print('Phase 4 Status:', phase4.get('status'))
print('\nFiles in Phase 4:')
for file_id, file_data in phase4.get('files', {}).items():
    print(f'  File: {file_id}')
    print(f'  Status: {file_data.get("status")}')
    chunk_paths = file_data.get('chunk_audio_paths', [])
    print(f'  Chunk audio paths: {len(chunk_paths)} paths')
    if len(chunk_paths) > 0:
        print(f'    First: {chunk_paths[0]}')
        print(f'    Last: {chunk_paths[-1]}')
