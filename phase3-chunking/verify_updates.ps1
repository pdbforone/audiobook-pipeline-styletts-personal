# verify_updates.ps1
Write-Host "Checking Phase 3 files..." -ForegroundColor Cyan

# Check main.py
$mainPath = "src\phase3_chunking\main.py"
$hasVerboseFlag = Select-String -Path $mainPath -Pattern 'parser.add_argument\("-v"' -Quiet
$hasChunkMetrics = Select-String -Path $mainPath -Pattern 'calculate_chunk_metrics' -Quiet

Write-Host "`nmain.py checks:" -ForegroundColor Yellow
Write-Host "  -v flag present: $hasVerboseFlag"
Write-Host "  calculate_chunk_metrics import: $hasChunkMetrics"

# Check utils.py
$utilsPath = "src\phase3_chunking\utils.py"
$hasCharChunking = Select-String -Path $utilsPath -Pattern '_chunk_by_char_count' -Quiet
$hasDurationPredict = Select-String -Path $utilsPath -Pattern 'predict_duration' -Quiet

Write-Host "`nutils.py checks:" -ForegroundColor Yellow
Write-Host "  _chunk_by_char_count present: $hasCharChunking"
Write-Host "  predict_duration present: $hasDurationPredict"

# Check models.py
$modelsPath = "src\phase3_chunking\models.py"
$hasChunkMetricsField = Select-String -Path $modelsPath -Pattern 'chunk_metrics.*Optional' -Quiet

Write-Host "`nmodels.py checks:" -ForegroundColor Yellow
Write-Host "  chunk_metrics field present: $hasChunkMetricsField"

if ($hasVerboseFlag -and $hasChunkMetrics -and $hasCharChunking -and $hasDurationPredict -and $hasChunkMetricsField) {
    Write-Host "`n✓ All updates are in place!" -ForegroundColor Green
} else {
    Write-Host "`n✗ Some updates are missing - files need to be updated" -ForegroundColor Red
}