# setup_phase3.ps1
Set-Location -Path $PSScriptRoot

# Initialize Poetry project if not exists
if (-not (Test-Path "pyproject.toml")) {
    poetry init --no-interaction --name phase3-chunking --description "Phase 3: Chunking for Audiobook Pipeline" --author "Grok <grok@x.ai>" --python "^3.12"
}

# Add dependencies
poetry add spacy@3.8.0 sentence-transformers@5.1.0 gensim@4.3.3 textstat@0.7.10 nltk@3.9.1 ftfy@6.3.1
poetry add --group dev pytest pytest-cov

# Download spaCy model
poetry run python -m spacy download en_core_web_lg

# Create directories
New-Item -ItemType Directory -Force -Path src/phase3_chunking, tests

Write-Host "Phase 3 setup complete. Edit src files and run 'poetry run pytest'."