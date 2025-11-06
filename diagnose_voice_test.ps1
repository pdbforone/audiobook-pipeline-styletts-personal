# Diagnostic Script for Voice Testing Failures
# Run from: audiobook-pipeline-chatterbox root

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Voice Testing Diagnostics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Check if test file exists
Write-Host "`n[1] Checking test file..." -ForegroundColor Yellow
if (Test-Path "test_magi_chunk.txt") {
    Write-Host "  ✅ test_magi_chunk.txt exists" -ForegroundColor Green
    $content = Get-Content "test_magi_chunk.txt" -Raw
    Write-Host "  Content length: $($content.Length) chars" -ForegroundColor White
} else {
    Write-Host "  ❌ test_magi_chunk.txt NOT FOUND" -ForegroundColor Red
    Write-Host "  Creating file now..." -ForegroundColor Yellow
    @"
One dollar and eighty-seven cents. That was all. And sixty cents of it was in pennies. Pennies saved one and two at a time by bulldozing the grocer and the vegetable man and the butcher until one's cheeks burned with the silent imputation of parsimony that such close dealing implied. Three times Della counted it. One dollar and eighty-seven cents. And the next day would be Christmas.
"@ | Out-File -FilePath test_magi_chunk.txt -Encoding UTF8
    Write-Host "  ✅ Created test_magi_chunk.txt" -ForegroundColor Green
}

# Test 2: Try Phase 3 with verbose logging
Write-Host "`n[2] Testing Phase 3 chunking..." -ForegroundColor Yellow
cd phase3-chunking

$testVoice = "neutral_narrator"
Write-Host "  Running Phase 3 for file_id: magi_diagnostic, voice: $testVoice" -ForegroundColor White

poetry run python -m phase3_chunking.main `
    --file_id magi_diagnostic `
    --text_path ..\test_magi_chunk.txt `
    --voice $testVoice `
    --verbose

# Check Phase 3 result
$phase3Status = jq -r ".phase3.files.magi_diagnostic.status" ..\pipeline.json 2>$null
if ($phase3Status -eq "success") {
    Write-Host "  ✅ Phase 3 completed successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ Phase 3 failed. Status: $phase3Status" -ForegroundColor Red
    Write-Host "`nPhase 3 errors:" -ForegroundColor Yellow
    jq ".phase3.files.magi_diagnostic.errors" ..\pipeline.json
}

# Test 3: Check if chunks were created
Write-Host "`n[3] Checking chunk files..." -ForegroundColor Yellow
$chunkFiles = Get-ChildItem chunks -Filter "magi_diagnostic*.txt" -ErrorAction SilentlyContinue
if ($chunkFiles) {
    Write-Host "  ✅ Found $($chunkFiles.Count) chunk file(s)" -ForegroundColor Green
    foreach ($chunk in $chunkFiles) {
        Write-Host "    - $($chunk.Name) ($($chunk.Length) bytes)" -ForegroundColor White
    }
} else {
    Write-Host "  ❌ No chunk files found in chunks/" -ForegroundColor Red
}

# Test 4: Check Phase 3 output in pipeline.json
Write-Host "`n[4] Checking Phase 3 pipeline.json output..." -ForegroundColor Yellow
$chunkPaths = jq -r ".phase3.files.magi_diagnostic.chunk_paths[]" ..\pipeline.json 2>$null
if ($chunkPaths) {
    Write-Host "  ✅ Chunk paths in pipeline.json:" -ForegroundColor Green
    foreach ($path in $chunkPaths) {
        Write-Host "    - $path" -ForegroundColor White
    }
} else {
    Write-Host "  ❌ No chunk_paths found in pipeline.json" -ForegroundColor Red
}

# Test 5: Try Phase 4 synthesis
Write-Host "`n[5] Testing Phase 4 TTS synthesis..." -ForegroundColor Yellow
cd ..\phase4_tts

Write-Host "  Running Phase 4 for file_id: magi_diagnostic" -ForegroundColor White
poetry run python src/main.py `
    --file_id magi_diagnostic `
    --json_path ..\pipeline.json

# Check Phase 4 result
$phase4Status = jq -r ".phase4.files.magi_diagnostic" ..\pipeline.json 2>$null
if ($phase4Status -and $phase4Status -ne "null") {
    Write-Host "  ✅ Phase 4 completed (check status below)" -ForegroundColor Green
    jq ".phase4.files.magi_diagnostic" ..\pipeline.json
} else {
    Write-Host "  ❌ Phase 4 failed or produced no output" -ForegroundColor Red
}

# Test 6: Check audio output
Write-Host "`n[6] Checking audio files..." -ForegroundColor Yellow
$audioFiles = Get-ChildItem audio_chunks -Filter "magi_diagnostic*.wav" -ErrorAction SilentlyContinue
if ($audioFiles) {
    Write-Host "  ✅ Found $($audioFiles.Count) audio file(s)" -ForegroundColor Green
    foreach ($audio in $audioFiles) {
        Write-Host "    - $($audio.Name) ($($audio.Length) bytes)" -ForegroundColor White
    }
} else {
    Write-Host "  ❌ No audio files found in audio_chunks/" -ForegroundColor Red
}

# Test 7: Check voice references
Write-Host "`n[7] Checking voice references..." -ForegroundColor Yellow
$voiceRefs = Get-ChildItem voice_references -Filter "*.wav" -ErrorAction SilentlyContinue
if ($voiceRefs) {
    Write-Host "  ✅ Found $($voiceRefs.Count) cached voice reference(s)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  No cached voice references (will download on first run)" -ForegroundColor Yellow
}

cd ..

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nIf you see ❌ errors above:" -ForegroundColor Yellow
Write-Host "1. Check Phase 3 errors for text processing issues" -ForegroundColor White
Write-Host "2. Check Phase 4 errors for TTS synthesis issues" -ForegroundColor White
Write-Host "3. Verify Conda environment is activated (Phase 4 needs it)" -ForegroundColor White
Write-Host "4. Check internet connection (for LibriVox downloads)" -ForegroundColor White
Write-Host "`nRun this script again after fixing issues.`n" -ForegroundColor White
