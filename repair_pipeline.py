import json
from pathlib import Path

pipeline_path = Path("pipeline.json")

# Read raw content
with open(pipeline_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the corruption point (char 1088625)
corrupt_start = 1088625

# Try to extract valid JSON before corruption
valid_content = content[:corrupt_start]

# Try to parse it
try:
    # Remove trailing incomplete data and close JSON properly
    # Find last complete '}' before corruption
    last_brace = valid_content.rfind("}")
    if last_brace > 0:
        valid_content = valid_content[: last_brace + 1]

    # Attempt to parse
    data = json.loads(valid_content)

    # Save backup
    backup_path = Path("pipeline_backup.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Extracted valid JSON to {backup_path}")
    print(f"   File contains {len(data)} top-level keys")

except json.JSONDecodeError as e:
    print(f"❌ Could not extract valid JSON: {e}")
    print("   Manual inspection required")
