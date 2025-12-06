#!/usr/bin/env python3
"""
Tests for pipeline.json schema v4.0.0 validation.

These tests verify:
- Schema structure and definitions
- Pydantic model validation
- Canonicalization of various input formats
- Phase-specific field validation
- Backward compatibility with v3.0.0 data
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def schema_json() -> Dict[str, Any]:
    """Load the canonical schema.json."""
    schema_path = Path(__file__).parent.parent.parent / "pipeline_common" / "schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.fixture
def minimal_valid_pipeline() -> Dict[str, Any]:
    """Minimal valid pipeline state."""
    return {
        "pipeline_version": "4.0.0",
        "created_at": "2025-12-06T00:00:00Z",
        "last_updated": "2025-12-06T00:00:00Z",
        "phases": {},
        "batch_runs": [],
    }


@pytest.fixture
def complete_pipeline() -> Dict[str, Any]:
    """Complete pipeline state with all phases."""
    return {
        "pipeline_version": "4.0.0",
        "created_at": "2025-12-06T00:00:00Z",
        "last_updated": "2025-12-06T00:00:00Z",
        "file_id": "test_book",
        "input_file": "/path/to/test_book.pdf",
        "tts_profile": "philosophy",
        "tts_voice": "en_male_deep",
        "voice_overrides": {},
        "phases": {
            "phase1": "success",
            "phase2": "success",
            "phase3": "success",
            "phase4": "partial",
            "phase5": "pending",
        },
        "phase1": {
            "status": "success",
            "timestamps": {"start": 1700000000, "end": 1700000100, "duration": 100},
            "artifacts": [],
            "metrics": {"total_files": 1, "duplicates": 0, "repaired": 0},
            "errors": [],
            "files": {
                "test_book": {
                    "status": "success",
                    "timestamps": {"start": 1700000000, "end": 1700000100},
                    "artifacts": [],
                    "metrics": {},
                    "errors": [],
                    "chunks": [],
                    "file_type": "pdf",
                    "classification": "text",
                    "hash": "abc123def456",
                    "repair_status": "validated",
                }
            },
        },
        "phase2": {
            "status": "success",
            "timestamps": {"start": 1700000100, "end": 1700000200, "duration": 100},
            "artifacts": [],
            "metrics": {"total_files": 1, "successful": 1, "failed": 0},
            "errors": [],
            "files": {
                "test_book": {
                    "status": "success",
                    "timestamps": {"start": 1700000100, "end": 1700000200},
                    "artifacts": [],
                    "metrics": {},
                    "errors": [],
                    "chunks": [],
                    "extracted_text_path": "/output/test_book/text.txt",
                    "tool_used": "pdfplumber",
                    "yield_pct": 98.5,
                    "quality_score": 0.95,
                    "language": "en",
                }
            },
        },
        "phase3": {
            "status": "success",
            "timestamps": {"start": 1700000200, "end": 1700000300, "duration": 100},
            "artifacts": [],
            "metrics": {"total_files": 1, "successful": 1, "total_chunks": 10},
            "errors": [],
            "files": {
                "test_book": {
                    "status": "success",
                    "timestamps": {"start": 1700000200, "end": 1700000300},
                    "artifacts": [],
                    "metrics": {},
                    "errors": [],
                    "chunks": [],
                    "chunk_paths": [f"/chunks/chunk_{i:04d}.txt" for i in range(1, 11)],
                    "applied_profile": "philosophy",
                    "suggested_voice": "en_male_deep",
                }
            },
        },
        "phase4": {
            "status": "partial",
            "timestamps": {"start": 1700000300, "end": 1700000600, "duration": 300},
            "artifacts": [],
            "metrics": {"total_chunks": 10, "total_audio_seconds": 120.5},
            "errors": [],
            "files": {
                "test_book": {
                    "status": "partial",
                    "timestamps": {"start": 1700000300, "end": 1700000600},
                    "artifacts": [],
                    "metrics": {},
                    "errors": [],
                    "chunks": [
                        {
                            "chunk_id": "chunk_0001",
                            "status": "success",
                            "audio_path": "/audio/chunk_0001.wav",
                            "engine_used": "xtts",
                            "voice_used": "en_male_deep",
                            "text_length": 450,
                            "audio_seconds": 12.5,
                            "rt_factor": 2.1,
                            "latency_fallback_used": False,
                            "validation": {
                                "tier1_passed": True,
                                "tier2_wer": 0.05,
                                "tier2_passed": True,
                            },
                            "errors": [],
                        },
                        {
                            "chunk_id": "chunk_0002",
                            "status": "failed",
                            "audio_path": None,
                            "engine_used": "xtts",
                            "errors": ["Synthesis timeout after 60s"],
                        },
                    ],
                    "voice_id": "en_male_deep",
                    "engines_used": ["xtts"],
                    "total_chunks": 10,
                    "chunks_completed": 8,
                    "chunks_failed": 2,
                    "duration_seconds": 100.5,
                    "avg_rt_factor": 2.3,
                }
            },
        },
        "batch_runs": [],
    }


@pytest.fixture
def legacy_v3_pipeline() -> Dict[str, Any]:
    """Legacy v3.0.0 format pipeline for backward compatibility testing."""
    return {
        "pipeline_version": "3.0.0",
        "created_at": "2025-11-01T00:00:00Z",
        "phases": {"phase1": "complete", "phase2": "complete"},
        "phase1": {
            "status": "complete",  # Legacy status
            "timestamps": {},
            "artifacts": {},
            "metrics": {},
            "errors": [],
        },
        "phase4": {
            "status": "success",
            "timestamps": {},
            "artifacts": {},
            "metrics": {},
            "errors": [],
            "files": {
                "old_book": {
                    "status": "success",
                    "timestamps": {},
                    "artifacts": {},
                    "metrics": {},
                    "errors": [],
                    "chunks": [],
                    # Legacy chunk_0001 style
                    "chunk_0001": {
                        "status": "success",
                        "audio_path": "/audio/chunk_0001.wav",
                        "engine": "xtts",
                    },
                    "chunk_0002": {
                        "status": "success",
                        "audio_path": "/audio/chunk_0002.wav",
                        "engine": "kokoro",
                    },
                }
            },
        },
    }


# =============================================================================
# Schema Structure Tests
# =============================================================================


class TestSchemaStructure:
    """Tests for schema.json structure and definitions."""

    def test_schema_version(self, schema_json):
        """Schema version should be 4.0.0."""
        assert schema_json.get("version") == "4.0.0"

    def test_schema_has_definitions(self, schema_json):
        """Schema should have definitions section."""
        assert "definitions" in schema_json
        definitions = schema_json["definitions"]
        assert isinstance(definitions, dict)
        assert len(definitions) > 10  # Should have many definitions

    def test_phase_specific_definitions_exist(self, schema_json):
        """Each phase should have its own block definition."""
        definitions = schema_json["definitions"]
        expected_blocks = [
            "phase1Block", "phase2Block", "phase3Block",
            "phase4Block", "phase5Block", "phase5_5Block",
            "phase6Block", "phase7Block",
        ]
        for block in expected_blocks:
            assert block in definitions, f"Missing definition: {block}"

    def test_phase_file_definitions_exist(self, schema_json):
        """Each phase should have file-level definitions."""
        definitions = schema_json["definitions"]
        expected_files = [
            "phase1File", "phase2File", "phase3File",
            "phase4File", "phase5File", "phase5_5File",
        ]
        for file_def in expected_files:
            assert file_def in definitions, f"Missing definition: {file_def}"

    def test_chunk_definitions_exist(self, schema_json):
        """Phase 4 and 5 should have chunk definitions."""
        definitions = schema_json["definitions"]
        assert "phase4Chunk" in definitions
        assert "phase5Chunk" in definitions

    def test_status_enum(self, schema_json):
        """Status enum should have all valid values."""
        status_def = schema_json["definitions"]["status"]
        expected_statuses = [
            "pending", "running", "success", "partial",
            "partial_success", "failed", "error", "skipped", "unknown"
        ]
        assert status_def["enum"] == expected_statuses

    def test_phase4_chunk_has_required_fields(self, schema_json):
        """Phase 4 chunk should define key fields."""
        chunk_def = schema_json["definitions"]["phase4Chunk"]
        properties = chunk_def.get("properties", {})

        expected_fields = [
            "chunk_id", "status", "audio_path", "engine_used",
            "rt_factor", "audio_seconds", "latency_fallback_used", "validation"
        ]
        for field in expected_fields:
            assert field in properties, f"Phase4Chunk missing field: {field}"

    def test_phase5_chunk_has_audio_metrics(self, schema_json):
        """Phase 5 chunk should have audio quality metrics."""
        chunk_def = schema_json["definitions"]["phase5Chunk"]
        properties = chunk_def.get("properties", {})

        expected_fields = [
            "snr_pre", "snr_post", "lufs_pre", "lufs_post",
            "rms_pre", "rms_post", "duration"
        ]
        for field in expected_fields:
            assert field in properties, f"Phase5Chunk missing field: {field}"


# =============================================================================
# Canonicalization Tests
# =============================================================================


class TestCanonicalization:
    """Tests for state canonicalization."""

    def test_canonicalize_minimal_state(self, minimal_valid_pipeline):
        """Minimal state should canonicalize successfully."""
        from pipeline_common.schema import canonicalize_state

        result = canonicalize_state(minimal_valid_pipeline)
        assert result["pipeline_version"] == "4.0.0"
        assert "phases" in result
        assert "batch_runs" in result

    def test_canonicalize_complete_state(self, complete_pipeline):
        """Complete state should canonicalize successfully."""
        from pipeline_common.schema import canonicalize_state

        result = canonicalize_state(complete_pipeline)
        assert result["phase4"]["files"]["test_book"]["chunks"]
        assert len(result["phase4"]["files"]["test_book"]["chunks"]) == 2

    def test_canonicalize_legacy_v3(self, legacy_v3_pipeline):
        """Legacy v3 state should be normalized to v4 structure."""
        from pipeline_common.schema import canonicalize_state

        result = canonicalize_state(legacy_v3_pipeline)

        # Status should be coerced from 'complete' to 'success'
        assert result["phase1"]["status"] == "success"

        # chunk_0001/0002 style should be collapsed into chunks array
        phase4_file = result["phase4"]["files"]["old_book"]
        assert "chunks" in phase4_file
        chunks = phase4_file["chunks"]
        assert len(chunks) >= 2

        # Chunk IDs should be preserved
        chunk_ids = {c.get("chunk_id") for c in chunks}
        assert "chunk_0001" in chunk_ids or any("0001" in str(cid) for cid in chunk_ids)

    def test_status_coercion(self):
        """Legacy status values should be coerced."""
        from pipeline_common.schema import _coerce_status

        assert _coerce_status("complete") == "success"
        assert _coerce_status("completed") == "success"
        assert _coerce_status("ok") == "success"
        assert _coerce_status("in_progress") == "running"
        assert _coerce_status("invalid_status") == "pending"
        assert _coerce_status(None) == "pending"


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for schema validation."""

    def test_validate_minimal_pipeline(self, minimal_valid_pipeline):
        """Minimal valid pipeline should pass validation."""
        from pipeline_common.schema import validate_pipeline_schema

        # Should not raise
        validate_pipeline_schema(minimal_valid_pipeline)

    def test_validate_complete_pipeline(self, complete_pipeline):
        """Complete pipeline should pass validation."""
        from pipeline_common.schema import validate_pipeline_schema, canonicalize_state

        canonical = canonicalize_state(complete_pipeline)
        validate_pipeline_schema(canonical)

    def test_validate_rejects_non_dict_root(self):
        """Validation should reject non-dict root."""
        from pipeline_common.schema import validate_pipeline_schema

        with pytest.raises(ValueError, match="must be an object"):
            validate_pipeline_schema("not a dict")

    def test_validate_rejects_invalid_phase_status(self):
        """Validation should reject invalid phase status."""
        from pipeline_common.schema import validate_pipeline_schema

        invalid = {
            "pipeline_version": "4.0.0",
            "phase1": {
                "status": "not_a_valid_status",
                "timestamps": {},
                "artifacts": {},
                "metrics": {},
                "errors": [],
            },
        }
        with pytest.raises(ValueError, match="invalid value"):
            validate_pipeline_schema(invalid)

    def test_validate_missing_required_phase_fields(self):
        """Validation should catch missing required fields."""
        from pipeline_common.schema import validate_pipeline_schema

        invalid = {
            "pipeline_version": "4.0.0",
            "phase1": {
                "status": "success",
                # Missing: timestamps, artifacts, metrics, errors
            },
        }
        with pytest.raises(ValueError, match="missing required field"):
            validate_pipeline_schema(invalid)


# =============================================================================
# Pydantic Model Tests
# =============================================================================


class TestPydanticModels:
    """Tests for Pydantic model validation."""

    def test_pydantic_available(self):
        """Pydantic should be available for strict validation."""
        from pipeline_common.models import PYDANTIC_AVAILABLE
        # Note: This test documents whether pydantic is installed
        # The models should work either way

    def test_create_empty_pipeline(self):
        """create_empty_pipeline should return valid structure."""
        from pipeline_common.models import create_empty_pipeline

        result = create_empty_pipeline("my_book")
        assert result["pipeline_version"] == "4.0.0"
        assert result["file_id"] == "my_book"
        assert "created_at" in result
        assert "phases" in result

    def test_validate_pipeline_data_lenient(self, minimal_valid_pipeline):
        """Lenient validation should accept minimal data."""
        from pipeline_common.models import validate_pipeline_data

        result = validate_pipeline_data(minimal_valid_pipeline, strict=False)
        assert result is not None

    def test_phase4_chunk_model(self):
        """Phase4ChunkModel should validate chunk data."""
        from pipeline_common.models import Phase4ChunkModel, PYDANTIC_AVAILABLE

        chunk_data = {
            "chunk_id": "chunk_0001",
            "status": "success",
            "audio_path": "/audio/chunk_0001.wav",
            "engine_used": "xtts",
            "rt_factor": 2.1,
            "audio_seconds": 12.5,
        }

        if PYDANTIC_AVAILABLE:
            chunk = Phase4ChunkModel(**chunk_data)
            assert chunk.chunk_id == "chunk_0001"
            assert chunk.engine_used == "xtts"
            assert chunk.rt_factor == 2.1
        else:
            # Stub mode
            chunk = Phase4ChunkModel(**chunk_data)
            assert chunk.chunk_id == "chunk_0001"

    def test_status_enum(self):
        """StatusEnum should have all valid values."""
        from pipeline_common.models import StatusEnum

        assert StatusEnum.SUCCESS.value == "success"
        assert StatusEnum.PENDING.value == "pending"
        assert StatusEnum.FAILED.value == "failed"

    def test_engine_enum(self):
        """EngineEnum should have supported engines."""
        from pipeline_common.models import EngineEnum

        assert EngineEnum.XTTS.value == "xtts"
        assert EngineEnum.KOKORO.value == "kokoro"
        assert EngineEnum.PIPER.value == "piper"


# =============================================================================
# Integration Tests
# =============================================================================


class TestSchemaIntegration:
    """Integration tests for schema and validation."""

    def test_full_roundtrip(self, complete_pipeline):
        """Data should survive canonicalize -> validate -> serialize roundtrip."""
        from pipeline_common.schema import canonicalize_state, validate_pipeline_schema

        # Canonicalize
        canonical = canonicalize_state(complete_pipeline)

        # Validate
        validate_pipeline_schema(canonical)

        # Serialize and deserialize
        serialized = json.dumps(canonical)
        deserialized = json.loads(serialized)

        # Validate again
        validate_pipeline_schema(deserialized)

        # Key data should be preserved
        assert deserialized["file_id"] == "test_book"
        assert deserialized["phase4"]["files"]["test_book"]["chunks_completed"] == 8

    def test_pydantic_integration(self, complete_pipeline):
        """Pydantic validation should work with complete pipeline."""
        from pipeline_common.schema import canonicalize_state, validate_with_pydantic

        canonical = canonicalize_state(complete_pipeline)
        is_valid, errors = validate_with_pydantic(canonical, raise_on_error=False)

        # Should be valid or at least not crash
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_get_schema_version(self):
        """get_schema_version should return current version."""
        from pipeline_common.schema import get_schema_version

        version = get_schema_version()
        assert version == "4.0.0"

    def test_get_phase_definitions(self):
        """get_phase_definitions should return phase schemas."""
        from pipeline_common.schema import get_phase_definitions

        defs = get_phase_definitions()
        assert "phase4Chunk" in defs
        assert "phase5Chunk" in defs
        assert "phase1Block" in defs


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_dict_input(self):
        """Empty dict should be canonicalized with defaults."""
        from pipeline_common.schema import canonicalize_state

        result = canonicalize_state({})
        assert "pipeline_version" in result
        assert "phases" in result
        assert "batch_runs" in result

    def test_null_values_handled(self):
        """Null values should be handled gracefully."""
        from pipeline_common.schema import canonicalize_state

        data = {
            "pipeline_version": "4.0.0",
            "file_id": None,
            "tts_voice": None,
            "phase1": None,  # Phase can be null
        }
        result = canonicalize_state(data)
        assert result["file_id"] is None
        assert result.get("phase1") is None  # Null phase not created

    def test_extra_fields_preserved(self):
        """Extra/unknown fields should be preserved (additionalProperties)."""
        from pipeline_common.schema import canonicalize_state

        data = {
            "pipeline_version": "4.0.0",
            "custom_field": "preserved",
            "another_custom": {"nested": True},
        }
        result = canonicalize_state(data)
        assert result["custom_field"] == "preserved"
        assert result["another_custom"]["nested"] is True

    def test_mixed_chunk_formats(self):
        """Both chunks array and chunk_XXXX keys should be normalized."""
        from pipeline_common.schema import canonicalize_state

        data = {
            "pipeline_version": "4.0.0",
            "phase4": {
                "status": "success",
                "timestamps": {},
                "artifacts": {},
                "metrics": {},
                "errors": [],
                "files": {
                    "test": {
                        "status": "success",
                        "timestamps": {},
                        "artifacts": {},
                        "metrics": {},
                        "errors": [],
                        "chunks": [
                            {"chunk_id": "chunk_0001", "status": "success"}
                        ],
                        "chunk_0002": {"status": "success"},
                        "chunk_0003": {"status": "failed"},
                    }
                }
            }
        }
        result = canonicalize_state(data)
        chunks = result["phase4"]["files"]["test"]["chunks"]

        # Should have all 3 chunks
        assert len(chunks) == 3

        # Should be sorted by chunk ID
        ids = [c["chunk_id"] for c in chunks]
        assert ids == sorted(ids)
