#!/bin/bash
mkdir -p ../audiobook-pipeline/phase1-validation
cd ../audiobook-pipeline/phase1-validation
poetry new .
# Add dependencies to pyproject.toml (manual edit or use poetry add)
poetry add pikepdf==9.11.0 pymupdf==1.26.4 ebooklib==0.19 python-docx==1.2.0 ftfy==6.3.1 chardet==5.2.0 pydantic==2.11.9 hachoir==3.3.0
poetry install
poetry shell
echo "Phase 1 setup complete. Run 'python validation.py --file path/to/file.pdf' to test."