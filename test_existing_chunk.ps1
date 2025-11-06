# Test All 14 Voices on Existing Gift of the Magi Chunk
# Uses existing Phase 3 chunk, only runs Phase 4

$voices = @(
    "landon_elkind",
    "pamela_nagami", 
    "hugh_mcguire",
    "david_barnes",
    "tom_weiss",
    "bella_bolster",
    "kara_shallenberg",
    "ruth_golding",
    "gareth_holmes",
    "wayne_cooke",
    "eric_metzler",
    "cori_samuel",
    "peter_yearsley",
    "neutral_narrator"
)

$sourceChunk = "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase3-chunking\chunks\Gift of the Magi_chunk_001.txt"
$outputDir = "voice_comparison_samples"

# Create output directory
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Check if source chunk exists
if (-not (Test-Path $sourceChunk)) {
    Write-Host "ERROR: Source chunk not found: $sourceChunk" -ForegroundColor Red
    exit 1
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Testing All 14 Voices on Gift of the Magi Chunk" -ForegroundColor Cyan
Write-Host "Using existing chunk: Gift of the Magi_chunk_001.txt" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Copy chunk content to temp file for each voice test
$chunkContent = Get-Content $sourceChunk -Raw

foreach ($voice in $voices) {
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Testing voice: $voice" -ForegroundColor Yellow
    
    # Create a test text file for this voice
    $testFile = "temp_magi_$voice.txt"
    $chunkContent | Out-File -FilePath $testFile -Encoding UTF8
    
    # Run Phase 3 to create chunk with selected voice
    cd phase3-chunking
    poetry run python -m phase3_chunking.main `
        --file_id "magi_voice_$voice" `
        --text_path "..\$testFile" `
        --voice $voice `
        2>&1 | Out-Null
    
    # Check if chunk was created
    $chunkCreated = Test-Path "chunks\magi_voice_${voice}_c0001.txt"
    if (-not $chunkCreated) {
        Write-Host "  ❌ Phase 3 failed to create chunk" -ForegroundColor Red
        cd ..
        continue
    }
    
    # Run Phase 4 TTS
    cd ..\phase4_tts
    
    Write-Host "  Running TTS synthesis..." -ForegroundColor Gray
    poetry run python src/main.py `
        --file_id "magi_voice_$voice" `
        --json_path ..\pipeline.json `
        2>&1 | Out-Null
    
    # Check for output audio
    $audioFile = Get-ChildItem audio_chunks -Filter "magi_voice_${voice}_c*.wav" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($audioFile) {
        # Copy to comparison folder
        $destFile = "$outputDir\magi_${voice}.wav"
        Copy-Item $audioFile.FullName $destFile
        
        $sizeMB = [math]::Round($audioFile.Length / 1MB, 2)
        Write-Host "  ✅ Generated: magi_${voice}.wav ($sizeMB MB)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to generate audio" -ForegroundColor Red
        
        # Check for error log
        $errorLog = Get-ChildItem -Filter "*error.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($errorLog) {
            Write-Host "  See error log: $($errorLog.Name)" -ForegroundColor Yellow
        }
    }
    
    cd ..
    
    # Clean up temp file
    Remove-Item $testFile -ErrorAction SilentlyContinue
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Voice Comparison Complete!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Count successful generations
$successCount = (Get-ChildItem $outputDir -Filter "*.wav" -ErrorAction SilentlyContinue).Count
Write-Host "`nGenerated: $successCount / 14 voices" -ForegroundColor $(if ($successCount -eq 14) { "Green" } else { "Yellow" })

if ($successCount -gt 0) {
    Write-Host "`nAudio samples saved in: $outputDir\" -ForegroundColor Cyan
    Write-Host "`nTo play all samples:" -ForegroundColor Yellow
    Write-Host "  cd $outputDir" -ForegroundColor White
    Write-Host "  Get-ChildItem *.wav | ForEach-Object { Write-Host `"Playing: `$(`$_.Name)`"; Start-Process `$_.FullName; Start-Sleep -Seconds 15 }" -ForegroundColor White
} else {
    Write-Host "`n⚠️ No audio files generated. Check error logs in phase4_tts/" -ForegroundColor Yellow
}
