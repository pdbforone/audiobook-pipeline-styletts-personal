"""
PHASE 4 TTS TEST SCRIPT
Tests 5 sample chunks for truncation and audio completeness.

Usage (from audiobook-pipeline directory):
    conda activate chatterbox_env
    python test_phase4_chunks.py
"""
import subprocess
import json
from pathlib import Path

# Test chunks: 1, 100, 200, 300, 624
TEST_CHUNKS = [1, 100, 200, 300, 624]
FILE_ID = "The_Analects_of_Confucius_20240228"
PIPELINE_JSON = "pipeline.json"

def test_chunk(chunk_id: int):
    """Test a single chunk with Phase 4 TTS"""
    print(f"\n{'='*60}")
    print(f"TESTING CHUNK {chunk_id}")
    print(f"{'='*60}")
    
    # Command to run Phase 4 in conda environment
    cmd = [
        "conda", "run", "-n", "chatterbox_env",
        "python", "-m", "phase4_tts.main",
        "--chunk_id", str(chunk_id),
        "--file_id", FILE_ID,
        "--json_path", PIPELINE_JSON
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,  # 5 min timeout per chunk
            cwd=Path.cwd()
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print(f"✅ Chunk {chunk_id} SUCCESS")
            
            # Check pipeline.json for chunk details
            with open(PIPELINE_JSON, 'r') as f:
                pipeline = json.load(f)
            
            phase4_data = pipeline.get('phase4', {}).get('files', {}).get(FILE_ID, {})
            chunk_data = phase4_data.get('chunks', {}).get(str(chunk_id), {})
            
            if chunk_data:
                print(f"  Split metadata: {chunk_data.get('metrics', {})}")
                if chunk_data.get('errors'):
                    print(f"  ⚠️  Failures: {chunk_data['errors']}")
        else:
            print(f"❌ Chunk {chunk_id} FAILED")
            print(f"Error: {result.stderr[-500:]}")  # Last 500 chars
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏱️  Chunk {chunk_id} TIMEOUT after 5 minutes")
        return False
    except Exception as e:
        print(f"💥 Chunk {chunk_id} EXCEPTION: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("PHASE 4 TTS CHUNK TESTING")
    print("="*60)
    print(f"Testing chunks: {TEST_CHUNKS}")
    print(f"File ID: {FILE_ID}")
    print(f"Pipeline JSON: {PIPELINE_JSON}")
    
    results = {}
    for chunk_id in TEST_CHUNKS:
        success = test_chunk(chunk_id)
        results[chunk_id] = success
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for chunk_id, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Chunk {chunk_id}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - check logs above")

if __name__ == "__main__":
    main()
