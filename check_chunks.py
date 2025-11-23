import json

data = json.load(open("pipeline.json"))
phase3 = data.get("phase3", {})
files = phase3.get("files", {})
for fname, fdata in files.items():
    has_chunks = "chunks" in fdata
    print(f"{fname}: chunks={has_chunks}")
