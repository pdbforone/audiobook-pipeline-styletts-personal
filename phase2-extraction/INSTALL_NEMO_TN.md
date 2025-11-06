# Installing NVIDIA NeMo Text Processing

## What is NeMo Text Processing?

NeMo Text Processing is NVIDIA's production-grade library for Text Normalization (TN). It converts text from written form into its verbalized form for TTS preprocessing. It uses Weighted Finite State Transducers (WFST) - battle-tested algorithms used by Google, Amazon, and other major TTS systems.

**Key Features:**
- Handles currency ($1.87 → "one dollar and eighty-seven cents"), dates, decimals, cardinals, measures, and more
- Fast, deterministic mode (no context) OR context-aware mode with neural LM for ambiguous cases
- Standalone package - doesn't require full NeMo toolkit
- CPU-only compatible (no GPU required)
- Apache 2.0 license (commercially free)

## Why Better Than Our Regex Solution?

| Feature | Our Regex | NeMo TN |
|---------|-----------|---------|
| Currency handling | Basic ($1.87 only) | Handles "$1.87", "1.87 dollars", "eighty-seven cents" |
| Numbers | Manual conversion | Handles cardinals, ordinals, fractions, ranges |
| Dates/Times | Not handled | Normalizes "3/4/2024", "3:45pm", etc. |
| Abbreviations | Not handled | "Mr.", "Dr.", "Inc.", state codes, etc. |
| Context-aware | No | Optional LM rescoring for "St." = "Saint" vs "Street" |
| Tested | Our tests only | Used in production by NVIDIA, tested on billions of sentences |

## Installation

### Option 1: Pip Install (Recommended)

```bash
cd phase2-extraction

# Install Pynini dependency first (required for WFST)
poetry run pip install Cython
poetry run conda install -c conda-forge pynini

# Install NeMo Text Processing
poetry add nemo-text-processing
```

**Important:** Pynini (the WFST library) requires conda on Windows. If you don't have conda, see Option 2.

### Option 2: Install with Conda (If Option 1 Fails)

If you're already using conda for Phase 4 (Chatterbox), use the same environment:

```bash
# Activate your existing conda env
conda activate chatterbox_env  # Or whatever you named it

# Install NeMo TN
pip install Cython
conda install -c conda-forge pynini
pip install nemo-text-processing
```

Then in Phase 2, you'd call it via subprocess to the conda environment (similar to how Phase 6 calls Phase 4).

### Option 3: From Source (Development)

```bash
git clone https://github.com/NVIDIA/NeMo-text-processing
cd NeMo-text-processing
pip install -e .
```

## Verification

Test the installation:

```python
from nemo_text_processing.text_normalization.normalize import Normalizer

normalizer = Normalizer(input_case='cased', lang='en')
text = "$1.87 is the price. Meet at 3:45pm on 3/4."
normalized = normalizer.normalize(text, verbose=False)
print(normalized)
# Expected: "one dollar and eighty-seven cents is the price. Meet at three forty-five p m on March fourth."
```

## Next Steps

Once installed, I'll update `cleaner.py` to use NeMo TN instead of regex hacks.

## Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'pynini'`
**Solution:** Pynini requires conda: `conda install -c conda-forge pynini`

**Issue:** Installation fails on Windows
**Solution:** Use WSL (Windows Subsystem for Linux) or install via conda

**Issue:** "Can't find OpenFst"
**Solution:** Pynini needs OpenFST. Use conda-forge: `conda install -c conda-forge pynini=2.1.6.post1`

## References

- [NeMo Text Processing GitHub](https://github.com/NVIDIA/NeMo-text-processing)
- [Official Documentation](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/nlp/text_normalization/wfst/wfst_text_normalization.html)
- [NVIDIA Blog: Text Normalization with NeMo](https://developer.nvidia.com/blog/text-normalization-and-inverse-text-normalization-with-nvidia-nemo/)
