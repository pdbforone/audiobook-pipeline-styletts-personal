# Karaoke-Style Word Highlighting for Phase 5.5 Subtitles

## Overview

The Phase 5.5 subtitle generator now supports **karaoke-style word-by-word highlighting** for ELL (English Language Learner) content. When enabled, each word highlights in yellow as it's spoken, creating an engaging and educational viewing experience.

## Features

- ✅ Word-level timestamp extraction from faster-whisper
- ✅ ASS format subtitle generation with karaoke tags
- ✅ ELL-optimized styling (Arial 32px, high contrast)
- ✅ Yellow-to-white transition highlighting
- ✅ Backward compatible (standard SRT/VTT still generated)
- ✅ Integrated with video generation pipeline

## Quick Start

### Generate Karaoke Subtitles

```powershell
cd phase5_enhancement

poetry run python -m phase5_enhancement.subtitles `
  --audio "../audiobook.mp3" `
  --file-id "BookName" `
  --output-dir "subtitles" `
  --model small `
  --karaoke
```

### Output Files

When `--karaoke` flag is used:
- `BookName.srt` - Standard SRT format (compatibility)
- `BookName.vtt` - Standard VTT format (web)
- `BookName_karaoke.ass` - **Karaoke ASS format with word highlighting**
- `BookName_metrics.json` - Quality metrics including karaoke stats

### Generate Video with Karaoke Subtitles

```powershell
# Standard subtitles
.\generate_gift_of_magi_video.ps1

# Karaoke subtitles
.\generate_gift_of_magi_video.ps1 -Karaoke
```

## Technical Implementation

### 1. Word-Level Timestamp Extraction

The subtitle generator now captures word-level timestamps from faster-whisper:

```python
# In subtitles.py - transcribe() method
segments_iter, info = self.model.transcribe(
    str(self.config.audio_path),
    word_timestamps=True  # Enable word-level timestamps
)

# Process segments with word data
for segment in segments_iter:
    segment_data = {
        'start': segment.start,
        'end': segment.end,
        'text': segment.text.strip(),
        'words': [
            {
                'word': word.word,
                'start': word.start,
                'end': word.end,
                'probability': word.probability
            }
            for word in segment.words
        ]
    }
```

### 2. ASS Format with Karaoke Tags

Karaoke highlighting uses ASS format with `{\k##}` timing tags:

```ass
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\k25}One {\k30}dollar {\k35}and {\k40}eighty-seven {\k45}cents.
```

Where:
- `{\k##}` = duration in centiseconds (1/100th of a second)
- Each word highlights for its duration as audio plays

### 3. ELL-Optimized ASS Styling

The generated ASS files include ELL-friendly styling:

```ini
[V4+ Styles]
Style: Default,Arial,32,&H00FFFFFF,&H00FFFF00,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,2,2,10,10,80,1
```

Key parameters:
- **PrimaryColour**: `&H00FFFFFF` = White (default text color)
- **SecondaryColour**: `&H00FFFF00` = Yellow (highlighted word)
- **Fontname**: Arial
- **Fontsize**: 32 pixels
- **Outline**: 3 (high contrast black border)
- **Shadow**: 2 (drop shadow for readability)
- **Alignment**: 2 (bottom center)
- **MarginV**: 80 (mobile-safe area)

### 4. FFmpeg Integration

The video generator script automatically detects and uses ASS files:

```powershell
if ($Karaoke) {
    # Use ASS filter (respects embedded karaoke styles)
    $vfFilter = "ass=$subtitleEscaped"
} else {
    # Use subtitles filter with forced styles
    $vfFilter = "subtitles=$subtitleEscaped:force_style='...'"
}
```

## File Structure

```
phase5_enhancement/
├── src/
│   └── phase5_enhancement/
│       ├── subtitles.py             # Main subtitle generator (MODIFIED)
│       ├── subtitle_karaoke.py      # NEW: Karaoke ASS generator
│       ├── subtitle_validator.py    # SRT/VTT formatting
│       ├── subtitle_aligner.py      # Timestamp alignment
│       └── models.py                # Configuration dataclasses
└── subtitles/                        # Output directory
    ├── BookName.srt                  # Standard SRT
    ├── BookName.vtt                  # Standard VTT
    ├── BookName_karaoke.ass          # Karaoke ASS (NEW)
    └── BookName_metrics.json         # Quality metrics
```

## Usage Examples

### Example 1: Basic Karaoke Subtitles

```bash
# Linux/Mac
cd phase5_enhancement
poetry run python -m phase5_enhancement.subtitles \
  --audio "../Gift of The Magi.mp3" \
  --file-id "Gift_of_The_Magi" \
  --output-dir "subtitles" \
  --model small \
  --karaoke
```

### Example 2: High-Quality Karaoke

```bash
# Use 'base' model for better accuracy
poetry run python -m phase5_enhancement.subtitles \
  --audio "../audiobook.mp3" \
  --file-id "MyBook" \
  --output-dir "subtitles" \
  --model base \
  --karaoke
```

### Example 3: Test Karaoke Rendering

```bash
# Render a test video with karaoke subtitles
ffmpeg -y \
  -f lavfi -i color=c=black:s=1920x1080:r=25 \
  -i "audiobook.mp3" \
  -vf "ass=subtitles/MyBook_karaoke.ass" \
  -c:v libx264 -c:a copy -shortest -pix_fmt yuv420p \
  "MyBook_KARAOKE_TEST.mp4"
```

## Metrics and Quality Validation

The karaoke generator includes statistics in the metrics JSON:

```json
{
  "coverage": 0.98,
  "wer": 0.05,
  "segment_count": 245,
  "karaoke_enabled": true,
  "karaoke_stats": {
    "total_segments": 245,
    "total_words": 1250,
    "avg_word_duration": 0.45,
    "output_path": "subtitles/BookName_karaoke.ass"
  },
  "processing_time": 125.3
}
```

## Testing Checklist

- [ ] `--karaoke` flag works without errors
- [ ] ASS file generated with proper format
- [ ] Word-level timing accurate (±50ms)
- [ ] Video renders with word highlighting
- [ ] Highlighting color: yellow → white transition
- [ ] Styling matches ELL requirements (Arial 32px, high contrast)
- [ ] Compatible with existing pipeline (SRT/VTT still generated)
- [ ] Metrics JSON includes karaoke statistics

## Troubleshooting

### Issue: ASS file not generated

**Solution**: Ensure `--karaoke` flag is set:
```bash
poetry run python -m phase5_enhancement.subtitles \
  --audio "file.mp3" \
  --file-id "test" \
  --karaoke  # ← Required!
```

### Issue: No word-level timestamps

**Problem**: faster-whisper not extracting word data

**Solution**: Verify faster-whisper version:
```bash
poetry show faster-whisper
# Should be >= 0.9.0
```

### Issue: Video shows no highlighting

**Problem**: FFmpeg not rendering karaoke tags

**Solution**: Use `ass` filter (not `subtitles`) for ASS files:
```bash
# Correct:
ffmpeg -i audio.mp3 -vf "ass=file.ass" output.mp4

# Incorrect (won't show karaoke):
ffmpeg -i audio.mp3 -vf "subtitles=file.ass" output.mp4
```

### Issue: Highlighting too fast/slow

**Problem**: Word duration calculation issue

**Solution**: Check word timestamps in segments:
```python
# In your code, verify word timing
for word in segment['words']:
    duration = word['end'] - word['start']
    print(f"Word: {word['word']}, Duration: {duration:.3f}s")
```

## Color Reference (ASS Format)

ASS uses BGR color format (not RGB!):

| Color | ASS Code | Usage |
|-------|----------|-------|
| White | `&H00FFFFFF` | Default text (PrimaryColour) |
| Yellow | `&H00FFFF00` | Highlighted word (SecondaryColour) |
| Black | `&H00000000` | Outline and shadow |
| Red | `&H000000FF` | Error/debug (BGR: FF 00 00) |
| Green | `&H0000FF00` | Success/debug (BGR: 00 FF 00) |
| Blue | `&H00FF0000` | Info/debug (BGR: 00 00 FF) |

## Performance Notes

- **Word timestamp extraction** adds ~10-15% to transcription time
- Minimal impact on video rendering (ASS rendering is efficient)
- Recommended: Use `small` model for good balance of speed/accuracy
- For production: Use `base` model for best word-level accuracy

## Compatibility

- ✅ FFmpeg 4.0+ (with `ass` filter support)
- ✅ faster-whisper 0.9.0+
- ✅ Python 3.8+
- ✅ Windows PowerShell 5.1+
- ✅ Linux/Mac bash

## Future Enhancements

Potential improvements for future versions:

1. **Customizable Colors**: Allow users to specify highlight colors
2. **Multi-color Highlighting**: Different colors for different word types
3. **Syllable-level Timing**: More precise highlighting for long words
4. **Interactive Web Player**: HTML5 player with JavaScript karaoke
5. **Export to LRC Format**: Support for music player karaoke
6. **Style Templates**: Pre-configured styles for different use cases

## References

- [ASS Format Specification](https://fileformats.fandom.com/wiki/SubStation_Alpha)
- [faster-whisper Documentation](https://github.com/guillaumekln/faster-whisper)
- [FFmpeg ASS Filter](https://ffmpeg.org/ffmpeg-filters.html#ass)
- [YouTube Subtitle Guidelines](https://support.google.com/youtube/answer/2734796)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the test output in `BookName_metrics.json`
3. Verify ASS file format with a text editor
4. Test with a short audio clip first

## License

This feature is part of the audiobook-pipeline-styletts-personal project.

