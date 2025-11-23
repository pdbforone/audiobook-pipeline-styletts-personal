import json

with open("../pipeline.json", "r") as f:
    data = json.load(f)

phase5 = data.get("phase5", {})
print("Phase 5 Status:", phase5.get("status"))
print("\nFiles in Phase 5:")
for file_id, file_data in phase5.get("files", {}).items():
    print(f"  File: {file_id}")
    print(f'  Status: {file_data.get("status")}')
    metrics = file_data.get("metrics", {})
    print(
        f'  Chunks processed: {metrics.get("chunks_processed", "NOT RECORDED")}'
    )
    print(f'  Total chunks: {metrics.get("total_chunks", "NOT RECORDED")}')
    print(
        f'  Duration: {metrics.get("total_duration_seconds", "NOT RECORDED")}s'
    )
    print(f'  Failures: {metrics.get("failed_chunks", 0)}')
    print(f'  Output: {file_data.get("output_path", "NOT RECORDED")}')
