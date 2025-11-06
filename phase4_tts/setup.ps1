# setup.ps1 - Fixed for Phase 4 in C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox
# Why: Resolves torch CUDA conflict, charset_normalizer warning, and tests TTS with src/ folder.

# Set root (why: Ensures script runs anywhere)
$root = "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox"
Set-Location $root
Write-Host "Setting up Phase 4 in root: $root" -ForegroundColor Cyan

# Step 1: Create phase4_tts dir (why: Isolates TTS)
$phase4Dir = "./phase4_tts"
if (-not (Test-Path $phase4Dir)) {
    New-Item -ItemType Directory -Path $phase4Dir -Force | Out-Null
    Write-Host "Created $phase4Dir" -ForegroundColor Green
}

# Step 2: Check Conda (why: Required for isolation)
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Conda not found. Install Miniconda: https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Red
    exit 1
}

# Step 3: Deactivate and recreate Conda env (why: Clean slate, Python 3.10)
$envName = "chatterbox_env"
conda deactivate
conda env remove -n $envName -y
conda create -n $envName python=3.10 -y
conda activate $envName

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create/activate env. Check Conda or disk (~3GB needed)." -ForegroundColor Red
    exit 1
}

# Step 4: Clone fork (why: Gets Chatterbox-TTS-Extended)
Set-Location $phase4Dir
$repoUrl = "https://github.com/petermg/Chatterbox-TTS-Extended.git"
$cloneDir = "./Chatterbox-TTS-Extended"
if (Test-Path $cloneDir) {
    Remove-Item -Path $cloneDir -Recurse -Force
}
git clone $repoUrl $cloneDir

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git clone failed. Install Git: https://git-scm.com/downloads" -ForegroundColor Red
    exit 1
}

# Step 5: Install charset_normalizer and requests (why: Fixes warning)
pip install charset_normalizer==3.4.3 requests==2.32.5

# Step 6: Install CPU-only torch (why: Prevents CUDA mismatch)
pip install torch==2.8.0+cpu torchvision==0.23.0+cpu torchaudio==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
Write-Host "Installed CPU-only PyTorch" -ForegroundColor Green

# Step 7: Modify requirements.txt to remove torch/torchaudio (why: Avoid CUDA override)
Set-Location $cloneDir
$reqFile = "requirements.txt"
$reqContent = Get-Content $reqFile
$newReqContent = $reqContent | Where-Object { $_ -notmatch "torch==" -and $_ -notmatch "torchaudio==" }
$newReqContent | Set-Content $reqFile
Write-Host "Modified $reqFile to remove torch/torchaudio" -ForegroundColor Green

# Step 8: Install fork deps (why: Force-reinstall avoids conflicts)
pip install --force-reinstall -r $reqFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: requirements.txt failed. Installing core deps manually." -ForegroundColor Yellow
    pip install gradio numpy==2.1.2 faster-whisper openai-whisper ffmpeg-python librosa==0.10.0 s3tokenizer spaces transformers==4.46.3 diffusers==0.29.0 omegaconf==2.3.0 resemble-perth==1.0.1 silero-vad==5.1.2 conformer==0.3.2 pyrnnoise==0.3.8 soundfile nltk
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dep installs failed. Run 'pip list' in env, ensure torch==2.8.0+cpu, retry." -ForegroundColor Red
    exit 1
}

# Step 9: Install NLTK punkt (why: Sentence splitting for long text)
python -m nltk.downloader punkt

# Step 10: Verify FFmpeg (why: Audio processing)
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "Installing Chocolatey..." -ForegroundColor Cyan
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
    choco install ffmpeg -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    refreshenv
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: FFmpeg failed. Download: https://ffmpeg.org/download.html, add bin/ to PATH." -ForegroundColor Red
    exit 1
}

# Step 11: Test TTS (why: Confirms model load without Gradio)
Write-Host "Testing TTS setup..." -ForegroundColor Green
$testScript = @"
import torch
from chatterbox.src.chatterbox.tts import ChatterboxTTS
model = ChatterboxTTS.from_pretrained(device='cpu')
wav = model.generate('Test sentence for TTS.', language_id='en')
import torchaudio
torchaudio.save('test.wav', wav, 24000)
print('Test WAV generated.')
"@
$testScript | Out-File -FilePath "test_tts.py" -Encoding UTF8
python test_tts.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: TTS test failed. Try: 'pip install transformers==4.46.3' or check internet for model download." -ForegroundColor Red
    exit 1
}

# Back to root
Set-Location $root
Write-Host "SUCCESS: Phase 4 ready at $phase4Dir. Ensure main.py, config.yaml, models.py, utils.py in $phase4Dir/src/. Run orchestrator.py." -ForegroundColor Green
Write-Host "Test manually: 'conda activate chatterbox_env && cd phase4_tts && python src/main.py --file_id The_Analects_of_Confucius_20240228 --json_path ../pipeline.json'" -ForegroundColor Cyan