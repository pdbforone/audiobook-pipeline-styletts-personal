from tests.master_harness import snapshot_comparator


def test_snapshot_consistency_detects_missing():
    before = {"phases": [1, 2], "engine": "xtts", "chunk_count": 2}
    after = {"phases": [1, 2], "engine": "xtts", "chunk_count": 2}
    res = snapshot_comparator.compare_snapshots(before, after)
    assert res["schema_valid"] is True
    snapshot_comparator.assert_consistency(before)
