# Phase 6.5: Publishing & Release Package Plan

## Brand: "Timeless Library"
**Tagline**: "Classic Books • Clear Voices • Free Knowledge"

## Output Structure
```
release/{file_id}/
├── audiobook.mp3           # Final audio
├── audiobook_video.mp4     # YouTube-ready (audio + cover)
├── cover.jpg               # 1400x1400 generated art
├── thumbnail.jpg           # 1280x720 YouTube thumbnail
├── subtitles.srt          # From Phase 5.5
├── subtitles.vtt          # From Phase 5.5
├── metadata.json          # Structured upload data
└── description_youtube.txt # Auto-generated description
```

## Key Features
1. **Auto-generate cover art** from title/author (PIL)
2. **Create video** with FFmpeg (audio + static image)
3. **Platform-specific descriptions** (Jinja2 templates)
4. **Metadata extraction** from pipeline.json

## Configuration (configs/publishing.yaml)
```yaml
channel:
  name: "Timeless Library"
  
branding:
  primary_color: "#1E2A38"   # Navy
  secondary_color: "#F5F2E7" # Cream
  accent_color: "#C7A84F"    # Gold
  
video:
  format: "mp4"
  codec: "h264"
  bitrate: "192k"
```

## CLI Usage
```bash
poetry run python -m phase6_orchestrator.publisher \
  --file-id meditations_001 \
  --pipeline pipeline.json
```

## Quality Targets
- Cover: 1400x1400px, <500KB
- Thumbnail: 1280x720px, <200KB
- Video: <1GB for 1hr audio
- Processing: <5 min

## Integration
Called by orchestrator AFTER Phase 5.5 (Subtitles) completes.

## Future: Auto-Upload (Phase 6.6)
- YouTube Data API v3
- Rumble API
- Spotify for Podcasters
- OAuth2 authentication

---

Full implementation code available - let me know when ready to build!
