# Phase 5.5: Subtitle Generation - Implementation Plan

## Overview
Generate .srt and .vtt subtitles from final audiobook for YouTube, Rumble, Spotify Video.

## File Structure
```
phase5_enhancement/
├── main.py              # Existing enhancement
├── phrase_cleaner.py    # Existing phrase removal
├── subtitles.py         # NEW: Subtitle generation
└── models.py            # Add SubtitleConfig class
```

## Dependencies (Add to phase5_enhancement/pyproject.toml)
```toml
faster-whisper = "^1.0.0"  # Already there for phrase_cleaner
webvtt-py = "^0.4.6"       # NEW: VTT format support
```

## Quality Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Coverage | >95% | Last subtitle timestamp / audio duration |
| Processing Time | <10 min for 1hr audio | time.perf_counter() |
| Max Segment Length | 84 chars | YouTube recommendation |
| Segment Duration | 1.5-7.0 sec | Readability balance |

## CLI Usage Examples

```bash
# Basic usage
poetry run python -m phase5_enhancement.subtitles \
  --audio processed/audiobook.mp3 \
  --file-id meditations_001

# With custom model
poetry run python -m phase5_enhancement.subtitles \
  --audio processed/audiobook.mp3 \
  --file-id meditations_001 \
  --model small  # More accurate but slower

# Called by orchestrator (automatic)
poetry run python -m phase6_orchestrator \
  --pipeline pipeline.json \
  --enable-subtitles
```

## Integration Point
Called by orchestrator AFTER Phase 5 completes successfully.

See full implementation code in attached subtitles.py file.
