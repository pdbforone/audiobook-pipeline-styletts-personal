# pipeline.json Schema Reference

## Overview
`pipeline.json` is the pipeline’s single source of truth. Each phase updates a well-defined section so downstream stages (and tooling such as the orchestrator or batch runner) can reason about inputs, outputs, metrics, and errors without ad‑hoc scraping of logs.

## Top-Level Structure
```json
{
  "pipeline_version": "1.0",
  "created_at": "ISO8601 timestamp",
  "last_updated": "ISO8601 timestamp",
  "input_file": "/path/to/source",
  "file_id": "unique_identifier",
  "tts_profile": "auto|philosophy|fiction|...",
  "tts_voice": "voice_id or null",
  "phase1": { /* Phase 1 Schema */ },
  "phase2": { /* Phase 2 Schema */ },
  "phase3": { /* Phase 3 Schema */ },
  "phase4": { /* Phase 4 Schema */ },
  "phase5": { /* Phase 5 Schema */ },
  "phase5_5": { /* Phase 5.5 Schema */ },
  "phase6": { /* Optional orchestration telemetry */ },
  "phase7": { /* Optional batch telemetry */ }
}
```

> **Note**: Older pipeline files may omit some top-level metadata. The orchestrator populates missing keys lazily; consumers should treat the metadata fields as optional but recommended.

## Common Field Conventions
- **`status`**: String (`"pending"`, `"success"`, `"partial"`, `"failed"`). Phases promote their status after aggregating per-file or per-chunk results.
- **`timestamps`**: Objects containing `start`, `end`, and `duration` in seconds. Phases update these per file or per chunk.
- **`metrics`**: Numeric KPIs captured per phase (e.g. `yield_pct`, `avg_snr_improvement`). Structured as objects to simplify tabular reporting.
- **`errors`**: Arrays of descriptive error objects or plain strings. Each entry should include `type` and `message` when available.
- **`files`**: Object maps keyed by `file_id`. Each value follows the phase-specific schema listed below.

---

## Phase 1: Validation & Repair (`phase1`)

### Schema
```json
"phase1": {
  "files": {
    "<file_id>": {
      "title": "string|null",
      "author": "string|null",
      "creation_date": "string|null",
      "file_type": "pdf|epub|docx|txt",
      "classification": "text|scanned|mixed",
      "hash": "sha256_hex",
      "repair_status": "validated|repaired|skipped",
      "duplicate": false,
      "errors": [],
      "artifacts_path": "path|null",
      "timestamps": { "start": 0.0, "end": 0.0, "duration": 0.0 },
      "metrics": { "elapsed_time": 0.0 }
    }
  },
  "hashes": ["sha256_hex", "..."],
  "errors": [
    { "type": "IntegrityWarning", "message": "Duplicate hash ..." }
  ],
  "metrics": {
    "total_files": 1,
    "duplicates": 0,
    "repaired": 0
  }
}
```

### Example
```json
"phase1": {
  "files": {
    "Gift_of_the_Magi": {
      "title": "The Gift of the Magi",
      "author": "O. Henry",
      "creation_date": "1905-12-10",
      "file_type": "pdf",
      "classification": "text",
      "hash": "37fc…9a9",
      "repair_status": "validated",
      "duplicate": false,
      "errors": [],
      "artifacts_path": null,
      "timestamps": { "start": 1696214202.12, "end": 1696214204.48, "duration": 2.36 },
      "metrics": { "elapsed_time": 2.36 }
    }
  },
  "hashes": ["37fc…9a9"],
  "errors": [],
  "metrics": { "total_files": 1, "duplicates": 0, "repaired": 0 }
}
```

---

## Phase 2: Extraction (`phase2`)

### Schema
```json
"phase2": {
  "files": {
    "<file_id>": {
      "extracted_text_path": "path",
      "tool_used": "pdfplumber|pypdf|fitz|...",
      "yield_pct": 98.4,
      "quality_score": 0.92,
      "language": "en",
      "lang_confidence": 0.90,
      "status": "success|partial_success|failed",
      "errors": [],
      "timestamps": { "start": 0.0, "end": 0.0, "duration": 0.0 },
      "metrics": {
        "yield_pct": 98.4,
        "quality_score": 0.92,
        "duration": 65.2
      },
      "structure": [...],           // optional document structure metadata
      "cleanup_notes": "string"      // optional normalization notes
    }
  },
  "errors": [],
  "metrics": {
    "total_files": 1,
    "successful": 1,
    "failed": 0
  }
}
```

### Example
```json
"phase2": {
  "files": {
    "Gift_of_the_Magi": {
      "extracted_text_path": "phase2-extraction/extracted_text/Gift_of_the_Magi.txt",
      "tool_used": "pdfplumber",
      "yield_pct": 99.1,
      "quality_score": 0.95,
      "language": "en",
      "lang_confidence": 0.92,
      "status": "success",
      "errors": [],
      "timestamps": { "start": 1696214211.43, "end": 1696214276.12, "duration": 64.69 },
      "metrics": {
        "yield_pct": 99.1,
        "quality_score": 0.95,
        "duration": 64.69
      }
    }
  },
  "errors": [],
  "metrics": { "total_files": 1, "successful": 1, "failed": 0 }
}
```

---

## Phase 3: Chunking (`phase3`)

### Schema
```json
"phase3": {
  "files": {
    "<file_id>": {
      "text_path": "phase2-extraction/extracted_text/<file>.txt",
      "chunk_paths": ["phase3-chunking/chunks/<file>_chunk_001.txt", "..."],
      "coherence_scores": [0.91, 0.89, "..."],  // n-1 entries
      "readability_scores": [68.0, 71.2, "..."],
      "embeddings": [[0.1, 0.2, "..."], "..."],
      "status": "success|partial|failed",
      "errors": [],
      "timestamps": { "start": 0.0, "end": 0.0, "duration": 0.0 },
      "chunk_metrics": {
        "avg_chars": 1550,
        "min_chars": 980,
        "max_chars": 1890,
        "total_chunks": 34
      },
      "applied_profile": "fiction|philosophy|auto",
      "genre_confidence": 0.77,
      "suggested_voice": "neutral_narrator",
      "coherence_threshold": 0.87,
      "flesch_threshold": 60.0,
      "metrics": {
        "avg_chars": 1550,
        "total_chunks": 34,
        "duration": 48.2
      }
    }
  },
  "errors": [
    {
      "file_id": "<file_id>",
      "type": "Phase2Desync",
      "message": "Fallback used due to missing/invalid Phase 2 data",
      "timestamp": 1696214300.12
    }
  ],
  "metrics": {
    "total_files": 1,
    "successful": 1,
    "partial": 0,
    "failed": 0,
    "total_chunks": 34
  }
}
```

### Example
```json
"phase3": {
  "files": {
    "Gift_of_the_Magi": {
      "text_path": "phase2-extraction/extracted_text/Gift_of_the_Magi.txt",
      "chunk_paths": [
        "phase3-chunking/chunks/Gift_of_the_Magi_chunk_001.txt",
        "phase3-chunking/chunks/Gift_of_the_Magi_chunk_002.txt"
      ],
      "coherence_scores": [0.92],
      "readability_scores": [66.1, 68.4],
      "embeddings": [[0.04, 0.12], [0.07, 0.08]],
      "status": "success",
      "errors": [],
      "timestamps": { "start": 1696214284.17, "end": 1696214332.44, "duration": 48.27 },
      "chunk_metrics": {
        "avg_chars": 1420,
        "min_chars": 1088,
        "max_chars": 1795,
        "total_chunks": 2
      },
      "applied_profile": "fiction",
      "genre_confidence": 0.73,
      "suggested_voice": "neutral_narrator",
      "metrics": {
        "avg_chars": 1420,
        "total_chunks": 2,
        "duration": 48.27
      }
    }
  },
  "errors": [],
  "metrics": { "total_files": 1, "successful": 1, "partial": 0, "failed": 0, "total_chunks": 2 }
}
```

---

## Phase 4: TTS Synthesis (`phase4`)

### Schema
```json
"phase4": {
  "status": "partial|success|failed",
  "files": {
    "<file_id>": {
      "status": "partial|success|failed",
      "total_chunks": 34,              // optional convenience counter
      "chunk_audio_paths": ["phase4_tts/audio_chunks/chunk_0.wav", "..."],  // optional
      "<chunk_id>": {
        "chunk_id": "chunk_0",
        "audio_path": "phase4_tts/audio_chunks/chunk_0.wav",
        "status": "success|failed",
        "mos_score": 4.35,
        "metrics": {
          "duration_per_chunk": 3.8,
          "splitting_enabled": true,
          "selected_voice": "neutral_narrator",
          "validation": {
            "validation_passed": true,
            "tier1": { "passed": true, "reason": "", "duration_sec": 1.2, "details": {...} },
            "tier2": { "passed": true, "reason": "", "duration_sec": 35.0, "details": { "wer": 0.08 } }
          }
        },
        "errors": [],
        "timestamps": { "start": 1696214338.62, "end": 1696214345.44, "duration": 6.82 },
        "split_metadata": {
          "split_applied": false,
          "num_sub_chunks": 1,
          "failed_sub_chunks": []
        }
      }
    }
  }
}
```

### Example
```json
"phase4": {
  "status": "partial",
  "files": {
    "Gift_of_the_Magi": {
      "status": "success",
      "total_chunks": 34,
      "chunk_audio_paths": ["phase4_tts/audio_chunks/chunk_0.wav"],
      "chunk_0": {
        "chunk_id": "chunk_0",
        "audio_path": "phase4_tts/audio_chunks/chunk_0.wav",
        "status": "success",
        "mos_score": 4.52,
        "metrics": {
          "duration_per_chunk": 3.6,
          "splitting_enabled": false,
          "selected_voice": "neutral_narrator",
          "validation": {
            "validation_passed": true,
            "tier1": { "passed": true, "reason": "", "details": {}, "duration_sec": 1.1 },
            "tier2": null
          }
        },
        "errors": [],
        "timestamps": { "start": 1696214338.62, "end": 1696214342.21, "duration": 3.59 },
        "split_metadata": { "split_applied": false, "num_sub_chunks": 1, "failed_sub_chunks": [] }
      }
    }
  }
}
```

---

## Phase 5: Audio Enhancement (`phase5`)

### Schema
```json
"phase5": {
  "status": "success|failed",
  "metrics": {
    "successful": 33,
    "failed": 1,
    "total_duration": 542.8,
    "avg_snr_improvement": 6.2,
    "avg_volume_normalization_delta": -1.1,
    "volume_normalization_applied_count": 34,
    "phrases_removed_total": 4,
    "chunks_with_phrases": 3,
    "cleanup_errors": 0
  },
  "artifacts": ["phase5_enhancement/processed/audiobook.mp3"],
  "errors": ["Chunk 12 clipping detected"],
  "timestamps": { "start": 1696214401.21, "end": 1696214950.04, "duration": 548.83 },
  "chunks": [
    {
      "chunk_id": 0,
      "wav_path": "phase4_tts/audio_chunks/chunk_0.wav",
      "enhanced_path": "phase5_enhancement/processed/chunk_0.wav",
      "snr_pre": 14.2,
      "snr_post": 21.0,
      "rms_pre": -18.5,
      "rms_post": -23.2,
      "lufs_pre": -25.1,
      "lufs_post": -23.0,
      "status": "complete",
      "error_message": null,
      "duration": 3.6,
      "cleanup_status": "clean",
      "phrases_removed": 0,
      "cleanup_processing_time": 1.9
    }
  ]
}
```

### Example
```json
"phase5": {
  "status": "success",
  "metrics": {
    "successful": 34,
    "failed": 0,
    "total_duration": 512.4,
    "avg_snr_improvement": 5.8,
    "avg_volume_normalization_delta": -0.9,
    "volume_normalization_applied_count": 34,
    "phrases_removed_total": 6,
    "chunks_with_phrases": 5,
    "cleanup_errors": 0
  },
  "artifacts": [
    "phase5_enhancement/processed/audiobook.mp3",
    "phase5_enhancement/processed/audiobook.json"
  ],
  "errors": [],
  "timestamps": { "start": 1696214401.21, "end": 1696214913.62, "duration": 512.41 },
  "chunks": [
    {
      "chunk_id": 0,
      "wav_path": "phase4_tts/audio_chunks/chunk_0.wav",
      "enhanced_path": "phase5_enhancement/processed/chunk_0.wav",
      "snr_pre": 13.4,
      "snr_post": 19.8,
      "rms_pre": -18.9,
      "rms_post": -23.0,
      "lufs_pre": -24.9,
      "lufs_post": -23.0,
      "status": "complete",
      "error_message": null,
      "duration": 3.5,
      "cleanup_status": "clean",
      "phrases_removed": 0,
      "cleanup_processing_time": 1.7
    }
  ]
}
```

---

## Phase 5.5: Subtitle Generation (`phase5_5`)

### Schema
```json
"phase5_5": {
  "status": "success|failed",
  "timestamp": 1696214987.12,
  "duration": 1821.4,
  "srt_file": "phase5_enhancement/subtitles/<file_id>.srt",
  "vtt_file": "phase5_enhancement/subtitles/<file_id>.vtt",
  "metrics": {
    "coverage": 0.972,
    "wer": 0.12,
    "segments": 138,
    "average_segment_duration": 4.2,
    "max_drift_seconds": 0.9
  },
  "error": "stderr tail if failure"
}
```

- On **success** the orchestrator writes `status`, subtitle artifact paths, duration, and metric payload loaded from `<file_id>_metrics.json`.
- On **failure** the orchestrator overwrites the block with:
  ```json
  {
    "status": "failed",
    "error": "<stderr tail>",
    "timestamp": 1696214987.12
  }
  ```

### Example
```json
"phase5_5": {
  "status": "success",
  "timestamp": 1696214987.12,
  "duration": 1789.44,
  "srt_file": "phase5_enhancement/subtitles/Gift_of_the_Magi.srt",
  "vtt_file": "phase5_enhancement/subtitles/Gift_of_the_Magi.vtt",
  "metrics": {
    "coverage": 0.971,
    "wer": 0.11,
    "segments": 136,
    "average_segment_duration": 4.0,
    "max_drift_seconds": 1.2,
    "processing_host": "cpu-small",
    "model": "faster-whisper-small"
  }
}
```

---

## Common Patterns & Utilities

- **Voice selection**: `phase3.files[*].suggested_voice` feeds Phase 4 command construction. Phase 4 echoes the applied voice inside each chunk record.
- **Resume support**: The orchestrator inspects `status` fields and per-chunk maps to determine which steps still need work.
- **Validation traces**: Phase 4 embeds tiered validation results within `metrics.validation`. Downstream tooling should treat the block as optional (older runs may omit validation keys).
- **File discovery**: Phase 5.5 looks up Phase 5’s `files[*].path|output_file` along with Phase 2’s `files[*].path` to resolve audio and reference text. Maintaining those fields is critical when adding new phases.

---

## Migration Notes

1. **Phase 5.5 addition**: Earlier schemas stopped at Phase 5. All new tooling should anticipate a `phase5_5` block. When absent, treat subtitle generation as not yet attempted.
2. **Per-chunk metadata in Phase 4**: Some legacy runs used arrays rather than chunk-id maps. The modern schema uses a dictionary keyed by `chunk_id`. Migration scripts should normalize arrays into the keyed form.
3. **Metrics normalization**: Phase 1 and Phase 2 historically omitted the nested `metrics` object. When missing, orchestrator code backfills minimal metrics (duration-only). Consumers should use `dict.get("metrics", {})`.
4. **Subtitle metrics**: If `<file_id>_metrics.json` is absent (e.g., Whisper aborted), the orchestrator stores an empty `{}`. Downstream code should handle missing metrics gracefully.
5. **Top-level metadata**: If `pipeline_version`, `created_at`, or `tts_profile` are missing, the orchestrator writes them the next time it saves the file. New tooling should not consider their absence an error.

Maintaining these structures keeps every phase loosely coupled while preserving the historical trace necessary for auditing, retries, and batch automation.
