# Create phase1-validation if needed
New-Item -ItemType Directory -Force -Path phase1-validation
Set-Location phase1-validation

# Initialize if not exists
if (-not (Test-Path pyproject.toml)) {
    poetry new .
}

# Assume manual edit for python pinning; add dependencies
poetry add pikepdf==9.11.0 pymupdf==1.26.4 ebooklib==0.19 python-docx==1.2.0 ftfy==6.3.1 chardet==5.2.0 pydantic==2.11.9 hachoir==3.3.0

# Install
poetry install

# Activate
Invoke-Expression (poetry env activate)

Write-Output "Phase 1 setup complete. Version: $(poetry --version). Run 'python validation.py --file C:/path/to/The_Analects_of_Confucius_20240228.pdf' to test."