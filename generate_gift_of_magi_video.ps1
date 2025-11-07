# ==============================================================================
# Gift of The Magi - ELL-Optimized Audiobook Video Generator
# ==============================================================================
# This script:
# 1. Generates accurate subtitles using faster-whisper
# 2. Creates professional video with hardcoded, styled subtitles for ELL learners
# 3. Supports karaoke-style word highlighting with --Karaoke flag
# ==============================================================================

$ErrorActionPreference = "Stop"

# Parse command-line arguments
param(
    [switch]$Karaoke = $false
)

# Configuration
$PROJECT_ROOT = "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox"
$AUDIO_FILE = "$PROJECT_ROOT\Gift of The Magi.mp3"
$FILE_ID = "Gift_of_The_Magi"
$PHASE5_DIR = "$PROJECT_ROOT\phase5_enhancement"
$SUBTITLE_DIR = "$PHASE5_DIR\subtitles"
$OUTPUT_VIDEO = if ($Karaoke) {
    "$PROJECT_ROOT\Gift_of_The_Magi_ELL_KARAOKE.mp4"
} else {
    "$PROJECT_ROOT\Gift_of_The_Magi_ELL_FINAL.mp4"
}

# Subtitle styling for ELL learners
$FONT_NAME = "Arial"
$FONT_SIZE = 32
$OUTLINE_WIDTH = 3
$SHADOW_DEPTH = 2
$MARGIN_BOTTOM = 80

Write-Host "==== Gift of The Magi - ELL Video Generator ====" -ForegroundColor Cyan
if ($Karaoke) {
    Write-Host "Mode: KARAOKE (Word-by-word highlighting)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: STANDARD (Line-by-line subtitles)" -ForegroundColor Yellow
}
Write-Host ""

# Step 1: Check if audio file exists
Write-Host "[1/4] Checking audio file..." -ForegroundColor Yellow
if (-Not (Test-Path $AUDIO_FILE)) {
    Write-Host "ERROR: Audio file not found: $AUDIO_FILE" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Found: $AUDIO_FILE" -ForegroundColor Green
Write-Host ""

# Step 2: Generate subtitles using Phase 5.5
Write-Host "[2/4] Generating subtitles with faster-whisper..." -ForegroundColor Yellow
Write-Host "  This may take 15-30 minutes depending on audio length..." -ForegroundColor Gray

Set-Location $PHASE5_DIR

$subtitleCmd = "poetry run python -m phase5_enhancement.subtitles " +
               "--audio `"$AUDIO_FILE`" " +
               "--file-id `"$FILE_ID`" " +
               "--output-dir `"$SUBTITLE_DIR`" " +
               "--model small"

if ($Karaoke) {
    $subtitleCmd += " --karaoke"
    Write-Host "  Karaoke mode enabled - generating word-level timestamps..." -ForegroundColor Yellow
}

Write-Host "  Command: $subtitleCmd" -ForegroundColor Gray
Invoke-Expression $subtitleCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Subtitle generation failed!" -ForegroundColor Red
    exit 1
}

$SRT_FILE = "$SUBTITLE_DIR\$FILE_ID.srt"
$ASS_FILE = "$SUBTITLE_DIR\${FILE_ID}_karaoke.ass"

# Determine which subtitle file to use
if ($Karaoke) {
    if (-Not (Test-Path $ASS_FILE)) {
        Write-Host "ERROR: Karaoke ASS file not created: $ASS_FILE" -ForegroundColor Red
        exit 1
    }
    $SUBTITLE_FILE = $ASS_FILE
    Write-Host "  ✓ Karaoke subtitles generated: $ASS_FILE" -ForegroundColor Green
} else {
    if (-Not (Test-Path $SRT_FILE)) {
        Write-Host "ERROR: Subtitle file not created: $SRT_FILE" -ForegroundColor Red
        exit 1
    }
    $SUBTITLE_FILE = $SRT_FILE
    Write-Host "  ✓ Subtitles generated: $SRT_FILE" -ForegroundColor Green
}

Write-Host ""

# Step 3: Check subtitle metrics
$METRICS_FILE = "$SUBTITLE_DIR\${FILE_ID}_metrics.json"
if (Test-Path $METRICS_FILE) {
    Write-Host "[3/4] Subtitle Quality Metrics:" -ForegroundColor Yellow
    $metrics = Get-Content $METRICS_FILE | ConvertFrom-Json
    if ($metrics.coverage) {
        Write-Host "  Coverage: $([math]::Round($metrics.coverage * 100, 2))%" -ForegroundColor Green
    }
    if ($metrics.wer -ne $null) {
        Write-Host "  WER (Word Error Rate): $([math]::Round($metrics.wer * 100, 2))%" -ForegroundColor Green
    }
    Write-Host ""
}

# Step 4: Create video with burned-in subtitles
Write-Host "[4/4] Creating ELL-optimized video with hardcoded subtitles..." -ForegroundColor Yellow
Write-Host "  Font: $FONT_NAME (${FONT_SIZE}px)" -ForegroundColor Gray

Set-Location $PROJECT_ROOT

# Escape subtitle path for FFmpeg (Windows paths need backslash escaping AND colon escaping)
$subtitleEscaped = $SUBTITLE_FILE -replace '\\', '\\\\' -replace ':', '\\:'

# Build FFmpeg filter based on subtitle format
if ($Karaoke) {
    # For ASS files, use the ass filter (respects embedded styles including karaoke tags)
    $vfFilter = "ass=$subtitleEscaped"
    Write-Host "  Style: Karaoke word-by-word highlighting (yellow -> white)" -ForegroundColor Gray
} else {
    # For SRT files, use subtitles filter with force_style
    $vfFilter = "subtitles=$subtitleEscaped" +
                ":force_style='" +
                "FontName=$FONT_NAME," +
                "FontSize=$FONT_SIZE," +
                "PrimaryColour=&HFFFFFF&," +
                "OutlineColour=&H000000&," +
                "Outline=$OUTLINE_WIDTH," +
                "Shadow=$SHADOW_DEPTH," +
                "Bold=1," +
                "Alignment=2," +
                "MarginV=$MARGIN_BOTTOM'"
    Write-Host "  Style: White text, black outline, centered bottom" -ForegroundColor Gray
}

Write-Host "  Rendering video (this may take 5-10 minutes)..." -ForegroundColor Gray

# Use native FFmpeg command with proper escaping
$ffmpegArgs = @(
    '-y'
    '-f', 'lavfi'
    '-i', 'color=c=black:s=1920x1080:r=25'
    '-i', $AUDIO_FILE
    '-vf', $vfFilter
    '-c:v', 'libx264'
    '-c:a', 'copy'
    '-shortest'
    '-pix_fmt', 'yuv420p'
    $OUTPUT_VIDEO
)

& ffmpeg @ffmpegArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Video creation failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - Check that FFmpeg supports subtitle filters: ffmpeg -filters | findstr subtitles" -ForegroundColor Gray
    Write-Host "  - Verify SRT file is valid: notepad `"$SRT_FILE`"" -ForegroundColor Gray
    exit 1
}

if (-Not (Test-Path $OUTPUT_VIDEO)) {
    Write-Host "ERROR: Video file not created: $OUTPUT_VIDEO" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Video created: $OUTPUT_VIDEO" -ForegroundColor Green
Write-Host ""

# Final summary
Write-Host "==== SUCCESS ====" -ForegroundColor Green
Write-Host ""
Write-Host "Output Files:" -ForegroundColor Cyan
Write-Host "  Subtitles (SRT): $SRT_FILE" -ForegroundColor White
Write-Host "  Subtitles (VTT): $SUBTITLE_DIR\$FILE_ID.vtt" -ForegroundColor White
if ($Karaoke) {
    Write-Host "  Subtitles (ASS): $ASS_FILE" -ForegroundColor Yellow
    Write-Host "                   ^ Karaoke-style word highlighting!" -ForegroundColor Yellow
}
Write-Host "  Final Video:     $OUTPUT_VIDEO" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Preview the video to verify subtitle styling" -ForegroundColor White
if ($Karaoke) {
    Write-Host "     - Check that words highlight yellow as they're spoken" -ForegroundColor Gray
}
Write-Host "  2. Upload to YouTube with SEO-optimized metadata" -ForegroundColor White
Write-Host "  3. Enable monetization (estimated `$0.50-`$2 per 1,000 views)" -ForegroundColor White
Write-Host ""
Write-Host "YouTube Title Suggestion:" -ForegroundColor Yellow
if ($Karaoke) {
    Write-Host "  'The Gift of the Magi | Karaoke Audiobook for English Learners (ELL)'" -ForegroundColor Gray
} else {
    Write-Host "  'The Gift of the Magi by O. Henry | Full Audiobook with Subtitles | ELL'" -ForegroundColor Gray
}
Write-Host ""
