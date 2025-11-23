from pathlib import Path

# Read first 1000 characters of the extracted file
PROJECT_ROOT = Path(__file__).resolve().parents[1]
file_path = (
    PROJECT_ROOT
    / "phase2-extraction"
    / "extracted_text"
    / "Systematic Theology.txt"
)

try:
    with open(file_path, "r", encoding="utf-8") as f:
        sample = f.read(1000)
    print("=== FIRST 1000 CHARACTERS ===")
    print(sample)
    print("\n=== CHARACTER ANALYSIS ===")
    print(f"Length: {len(sample)}")
    print(f"Unique chars: {len(set(sample))}")
    print(
        f"Printable ratio: {sum(c.isprintable() for c in sample) / len(sample):.2%}"
    )

    # Check for encoding issues
    print("\n=== BYTE REPRESENTATION (first 200 bytes) ===")
    print(sample[:200].encode("utf-8"))

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
