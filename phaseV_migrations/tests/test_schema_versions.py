from phaseV_migrations import schema_versions


def test_schema_info_lookup():
    info = schema_versions.get_schema_info("pipeline_state")
    assert info is not None
    assert info.current_version
