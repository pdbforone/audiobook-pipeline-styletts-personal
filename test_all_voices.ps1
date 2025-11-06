# Test All 14 Voices on Gift of the Magi Chunk
# Run from: audiobook-pipeline-chatterbox root

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

$outputDir = "voice_comparison_samples"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Testing All 14 Voices on Gift of the Magi Chunk" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

foreach ($voice in $voices) {
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Testing voice: $voice" -ForegroundColor Yellow
    
    # Update Phase 3 voice selection in pipeline.json
    cd phase3-chunking
    poetry run python -m phase3_chunking.main `
        --file_id "magi_test_$voice" `
        --text_path ..\test_magi_chunk.txt `
        --voice $voice `
        2>&1 | Out-Null
    
    # Run Phase 4 TTS
    cd ..\phase4_tts
    poetry run python src/main.py `
        --file_id "magi_test_$voice" `
        --json_path ..\pipeline.json `
        2>&1 | Out-Null
    
    # Copy output to comparison folder
    $chunkFile = Get-ChildItem audio_chunks -Filter "magi_test_${voice}_c*.wav" | Select-Object -First 1
    if ($chunkFile) {
        Copy-Item $chunkFile.FullName "$outputDir\magi_${voice}.wav"
        Write-Host "  ✅ Generated: magi_${voice}.wav" -ForegroundColor Green
    }
    else {
        Write-Host "  ❌ Failed to generate audio" -ForegroundColor Red
    }
    
    cd ..
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Complete! Audio samples in: $outputDir" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "`nTo listen to samples:" -ForegroundColor Yellow
Write-Host "  cd $outputDir" -ForegroundColor White
Write-Host "  ls *.wav" -ForegroundColor White