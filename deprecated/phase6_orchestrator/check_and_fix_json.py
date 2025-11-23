import json
from pathlib import Path

# Load the JSON
json_path = Path("pipeline_magi.json")
with open(json_path, "r") as f:
    data = json.load(f)

# Check what file_ids are in phase4
phase4 = data.get("phase4", {})
files = phase4.get("files", {})

print("=== File IDs in phase4 ===")
for file_id in files.keys():
    chunk_paths = files[file_id].get("chunk_audio_paths", [])
    print(f"\nFile ID: {file_id}")
    print(f"  Chunks: {len(chunk_paths)}")
    if chunk_paths:
        print(f"  First chunk: {chunk_paths[0]}")
        print(f"  Last chunk: {chunk_paths[-1]}")

print("\n=== ACTION NEEDED ===")
if len(files) > 1:
    print("⚠️  Multiple file_ids found!")
    print("Phase 5 is processing ALL of them.")
    print("\nWe need to:")
    print("1. Keep only 'Gift of the Magi' in phase4")
    print("2. Remove other file_ids")

    # Ask for confirmation
    response = input("\nRemove non-Magi files from JSON? (y/n): ")
    if response.lower() == "y":
        # Keep only Gift of Magi
        magi_files = {}
        for file_id, file_data in files.items():
            if "Gift of the Magi" in file_id or "magi" in file_id.lower():
                magi_files[file_id] = file_data
                print(f"✓ Keeping: {file_id}")
            else:
                print(f"✗ Removing: {file_id}")

        # Update JSON
        phase4["files"] = magi_files
        data["phase4"] = phase4

        # Remove phase5 so it re-runs
        data.pop("phase5", None)

        # Save
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        print("\n✓ JSON updated!")
        print("✓ Removed phase5 status")
        print("\nNow run Phase 5 again")
else:
    print(f"✓ Only one file_id: {list(files.keys())[0]}")
    print("This is correct!")
